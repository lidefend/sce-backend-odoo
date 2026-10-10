#!/usr/bin/env python3
"""Guard registry: inventory, audit and retirement for scripts/verify/.

R7 (productization audit) deliverable. The verify-script corpus grew to
1200+ files across generations of guards with no lifecycle control. This
tool provides:

* ``--export``   Inventory every script under scripts/verify/, resolve which
                 make targets / CI workflows reference it, and write a
                 deterministic JSON registry to docs/audit/guard_registry.json.
* ``--audit``    Fail (exit 1) when a script on disk is referenced nowhere
                 (an "orphan") yet is not acknowledged in
                 scripts/verify/registry.yaml, when a registry entry points
                 at a missing script, when a retired script is still
                 referenced by make/CI, or when an active script that no
                 make target/workflow references ("unwired") lacks a
                 machine-checkable ``wire_or_retire`` disposition
                 (file-consumed / wire-pending / retire-pending).
* ``--seed``     Merge missing orphan acknowledgements into registry.yaml
                 with default review metadata (first-round onboarding).
* ``--retire``   Move a script into scripts/verify/retired/ and mark it
                 retired in registry.yaml (the retirement mechanism).

Static-analysis caveat: references are matched by script filename, by python
import statements, and by ``scripts.verify.<module>`` module invocations
(``python3 -m unittest scripts.verify.<module>``) across make files,
scripts/** and .github/workflows. A script invoked only through fully dynamic
name construction may be a false orphan; acknowledge it in registry.yaml with
``status: active-dynamic`` and a reason.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VERIFY_DIR = ROOT / "scripts" / "verify"
RETIRED_DIR = VERIFY_DIR / "retired"
REGISTRY_PATH = VERIFY_DIR / "registry.yaml"
EXPORT_PATH = ROOT / "docs" / "audit" / "guard_registry" / "guard_registry.json"

MAKE_FILES = sorted([ROOT / "Makefile", *(ROOT / "make").glob("*.mk")])
WORKFLOW_FILES = sorted(
    (*ROOT.glob(".github/workflows/*.yml"), *ROOT.glob(".github/workflows/*.yaml"))
)
SCRIPT_CORPUS_GLOBS = ("scripts/**/*.py", "scripts/**/*.sh")
SCRIPT_REFERENCE_RE = re.compile(r"\b([A-Za-z0-9_./-]+\.(?:py|sh))\b")
IMPORT_REFERENCE_RE = re.compile(
    r"\b(?:from|import)\s+([A-Za-z_][A-Za-z0-9_\.]*)\b"
)
# ``python3 -m unittest scripts.verify.<module>`` is a static reference even
# though it never spells out the ``.py`` filename.
MODULE_INVOCATION_REFERENCE_RE = re.compile(
    r"\bscripts\.verify\.([A-Za-z_][A-Za-z0-9_]*)\b"
)

STATUS_ACTIVE = "active"
STATUS_ACTIVE_DYNAMIC = "active-dynamic"
STATUS_ORPHAN = "orphan"
STATUS_RETIRED = "retired"

# Wire-or-retire disposition for active scripts that no make target and no CI
# workflow references ("unwired"). The disposition is machine-checkable:
#
# * ``file-consumed``   the script is consumed only by other scripts/tests
#                       (referenced_by_files non-empty); it stays active as a
#                       library/helper without its own governed entry.
# * ``wire-pending``    an owner intends to wire it to a make target/workflow;
#                       requires a ``review_by`` deadline.
# * ``retire-pending``  an owner intends to retire it; requires ``review_by``.
WIRE_OR_RETIRE_VALUES = ("file-consumed", "wire-pending", "retire-pending")


def disposition_failures(name: str, entry: dict | None, item: dict) -> list[str]:
    """Validate the wire-or-retire disposition of one classified script.

    ``item`` is a classify() inventory entry; ``entry`` is the matching
    registry.yaml entry (or None). Returns a list of audit failure strings.
    """
    wired = bool(
        item.get("referenced_by_make_targets") or item.get("referenced_by_workflows")
    )
    disposition = (entry or {}).get("wire_or_retire")
    if wired:
        if disposition:
            return [
                f"'{name}' carries wire_or_retire '{disposition}' but is wired to "
                f"make/CI (stale entry: run make guard.registry.seed)"
            ]
        return []
    if not disposition:
        return [
            f"unwired active script '{name}' lacks a wire-or-retire disposition "
            f"(run: make guard.registry.seed, then review)"
        ]
    if disposition not in WIRE_OR_RETIRE_VALUES:
        return [f"registry entry '{name}' has unknown wire_or_retire '{disposition}'"]
    failures: list[str] = []
    if disposition == "file-consumed" and not item.get("referenced_by_files"):
        failures.append(
            f"'{name}' claims file-consumed but no file reference exists "
            f"(classify as orphan instead)"
        )
    if disposition in ("wire-pending", "retire-pending") and not (entry or {}).get(
        "review_by"
    ):
        failures.append(
            f"registry entry '{name}' wire_or_retire '{disposition}' lacks a "
            f"review_by deadline"
        )
    return failures


MAKE_RULE_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._/-]*)\s*:(?!=)(.*)$")


def parse_make_graph() -> dict[str, set[str]]:
    """Target -> declared prerequisite targets, accumulating duplicate rules.

    Recipe lines are ignored: reachability must follow declared prerequisites
    rather than shell text, otherwise a target whose only action is ``echo``
    would count as a gate for every script mentioned in its recipe. Prerequisite
    tokens carrying make syntax (``$(...)``, ``%`` patterns, ``=``) are dropped
    because they cannot be resolved statically.
    """
    graph: dict[str, set[str]] = {}
    for makefile in MAKE_FILES:
        lines = makefile.read_text(encoding="utf-8", errors="replace").splitlines()
        index = 0
        while index < len(lines):
            raw = lines[index]
            if raw.startswith("\t") or raw.startswith(".PHONY"):
                index += 1
                continue
            match = MAKE_RULE_RE.match(raw)
            if not match:
                index += 1
                continue
            name = match.group(1)
            rest = match.group(2)
            while (
                rest.rstrip().endswith("\\")
                and index + 1 < len(lines)
                and lines[index + 1].startswith((" ", "\t"))
            ):
                index += 1
                rest = rest.rstrip()[:-1] + " " + lines[index].strip()
            if "$" not in name and "%" not in name:
                prereqs: set[str] = set()
                for token in rest.replace("|", " ").split():
                    if token.startswith("#"):
                        break
                    if any(char in token for char in "$%()="):
                        continue
                    prereqs.add(token)
                graph.setdefault(name, set()).update(prereqs)
            index += 1
    return graph


def reachable_targets(graph: dict[str, set[str]], roots: list[str]) -> set[str]:
    """Every target reachable from ``roots`` by following declared prerequisites."""
    seen: set[str] = set()
    stack = [root for root in roots if root in graph]
    while stack:
        target = stack.pop()
        if target in seen:
            continue
        seen.add(target)
        stack.extend(graph.get(target, ()))
    return seen


def gate_anchor_failures(doc: dict, graph: dict[str, set[str]]) -> list[str]:
    """Validate that every declared gate anchor is a substantiated entrypoint."""
    anchors = doc.get("gate_anchors")
    if not anchors:
        return [
            "registry.yaml declares no gate_anchors: required-gate reachability "
            "cannot be established"
        ]
    failures: list[str] = []
    for anchor in anchors:
        target = (anchor or {}).get("target") if isinstance(anchor, dict) else None
        if not target:
            failures.append("gate anchor entry lacks a target")
            continue
        if target not in graph:
            failures.append(f"gate anchor '{target}' is not a make target")
            continue
        sources = [s for s in (anchor.get("invoked_by") or []) if s]
        if not sources:
            failures.append(f"gate anchor '{target}' declares no invoked_by source")
            continue
        if not any(
            (ROOT / source).is_file()
            and target
            in (ROOT / source).read_text(encoding="utf-8", errors="replace")
            for source in sources
        ):
            failures.append(
                f"gate anchor '{target}' is not invoked by any declared source "
                f"{sources} (stale or aspirational anchor)"
            )
    return failures


MAKE_MODULE_INVOCATION_RE = re.compile(
    r"-m\s+unittest\s+((?:scripts\.verify\.)?[A-Za-z_][A-Za-z0-9_]*)"
)


def make_module_invocations() -> dict[str, set[str]]:
    """Module stem -> make targets that run it through ``python3 -m unittest``.

    ``classify()`` matches the ``.py`` filename textually, so a test invoked only
    as ``-m unittest scripts.verify.<stem>`` looks unwired. Gate reachability
    must not reproduce that blind spot.
    """
    invocations: dict[str, set[str]] = collections.defaultdict(set)
    for target, text in parse_make_targets().items():
        for stem in MAKE_MODULE_INVOCATION_RE.findall(text):
            invocations[stem.rsplit(".", 1)[-1]].add(target)
    return invocations


def gate_reachability(
    doc: dict, inventory: list[dict]
) -> tuple[set[str], dict[str, bool]]:
    """Map each script to whether a required gate actually reaches its wiring."""
    graph = parse_make_graph()
    anchors = [
        anchor["target"]
        for anchor in (doc.get("gate_anchors") or [])
        if isinstance(anchor, dict) and anchor.get("target") in graph
    ]
    reachable = reachable_targets(graph, anchors)
    module_invocations = make_module_invocations()
    enforced: dict[str, bool] = {}
    for item in inventory:
        targets = set(item.get("referenced_by_make_targets") or ())
        path = item.get("path") or ""
        if path.endswith(".py"):
            targets |= module_invocations.get(Path(path).stem, set())
        enforced[item["script"]] = bool(
            item.get("referenced_by_workflows")
        ) or any(target in reachable for target in targets)
    return reachable, enforced


def gate_required_failures(name: str, enforced: bool) -> list[str]:
    """A ``gate_required`` script must be reached by a declared gate anchor."""
    if enforced:
        return []
    return [
        f"'{name}' claims gate enforcement but no referencing make target is "
        f"reachable from a declared gate anchor (wired only to a lane no required "
        f"gate runs)"
    ]


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"version": 1, "entries": []}
    doc = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    doc.setdefault("entries", [])
    return doc


def save_registry(doc: dict) -> None:
    REGISTRY_PATH.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def collect_scripts() -> list[Path]:
    files = []
    for pattern in ("**/*.py", "**/*.sh"):
        for path in VERIFY_DIR.glob(pattern):
            if not path.is_file() or RETIRED_DIR in path.parents:
                continue
            files.append(path)
    return sorted(files)


def parse_make_targets() -> dict[str, str]:
    """Minimal make parser: target name -> concatenated prereq+recipe text."""
    targets: dict[str, str] = {}
    target_re = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9._/%-]*)\s*:")
    current: str | None = None
    buffer: list[str] = []
    for makefile in MAKE_FILES:
        for raw in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw.startswith("\t"):
                if current:
                    buffer.append(raw)
                continue
            match = target_re.match(raw)
            if match and not raw.startswith(".PHONY"):
                if current:
                    targets[current] = " ".join(buffer)
                current = match.group(1)
                buffer = [raw]
            elif raw.strip() and current:
                buffer.append(raw)
            elif not raw.strip() and current:
                targets[current] = " ".join(buffer)
                current = None
                buffer = []
        if current:
            targets[current] = " ".join(buffer)
            current, buffer = None, []
    return targets


def build_corpus(exclude: Path | None = None) -> dict[str, str]:
    """Reference corpus text keyed by repository-relative file path."""
    parts: dict[str, str] = {}
    for makefile in MAKE_FILES:
        parts[makefile.relative_to(ROOT).as_posix()] = makefile.read_text(
            encoding="utf-8", errors="replace"
        )
    for workflow in WORKFLOW_FILES:
        parts[workflow.relative_to(ROOT).as_posix()] = workflow.read_text(
            encoding="utf-8", errors="replace"
        )
    for pattern in SCRIPT_CORPUS_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            if exclude and path == exclude:
                continue
            key = path.relative_to(ROOT).as_posix()
            if key not in parts:
                parts[key] = path.read_text(encoding="utf-8", errors="replace")
    return parts


def build_reference_index(
    parts: dict[str, str],
) -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]:
    """Index file texts once so per-script classification stays linear-ish."""
    filename_hits: dict[str, set[str]] = collections.defaultdict(set)
    import_hits: dict[str, set[str]] = collections.defaultdict(set)
    module_hits: dict[str, set[str]] = collections.defaultdict(set)
    for key, text in parts.items():
        for match in SCRIPT_REFERENCE_RE.findall(text):
            filename_hits[Path(match).name].add(key)
        for module in IMPORT_REFERENCE_RE.findall(text):
            import_hits[module.rsplit(".", 1)[-1]].add(key)
        for module in MODULE_INVOCATION_REFERENCE_RE.findall(text):
            module_hits[module].add(key)
    return filename_hits, import_hits, module_hits


def _reference_patterns(name: str) -> list[re.Pattern[str]]:
    """Filename match + Python import-by-stem match (``import x`` / ``from x import``).

    Bare-stem matching would drown in false positives (e.g. ``release``),
    so stem references only count inside import statements.
    """
    stem = re.escape(name.rsplit(".", 1)[0])
    escaped = re.escape(name)
    return [
        re.compile(escaped),
        re.compile(rf"\b(?:import|from)\s+{stem}\b"),
        re.compile(rf"\bscripts\.verify\.{stem}\b"),
    ]


def resolve_external_hits(
    script_key: str,
    script_name: str,
    parts: dict[str, str],
    filename_hits: dict[str, set[str]],
    import_hits: dict[str, set[str]],
    module_hits: dict[str, set[str]] | None = None,
) -> list[str]:
    stem = script_name.rsplit(".", 1)[0]
    candidates = set(filename_hits.get(script_name, set())) | set(
        import_hits.get(stem, set())
    )
    if module_hits:
        candidates |= set(module_hits.get(stem, set()))
    candidates.discard(script_key)
    if not candidates:
        return []
    patterns = _reference_patterns(script_name)
    return sorted(
        key
        for key in candidates
        if any(pattern.search(parts[key]) for pattern in patterns)
    )


def classify(scripts: list[Path]) -> list[dict]:
    parts = build_corpus()
    filename_hits, import_hits, module_hits = build_reference_index(parts)
    targets = parse_make_targets()
    inventory = []
    for script in scripts:
        script_key = script.relative_to(ROOT).as_posix()
        name = script.name
        external_hits = resolve_external_hits(
            script_key, name, parts, filename_hits, import_hits, module_hits
        )
        referenced_by_targets = [
            target
            for target, text in targets.items()
            if name in text
        ]
        referenced_by_workflows = [
            key for key in external_hits if key.startswith(".github/workflows/")
        ]
        self_text = script.read_text(encoding="utf-8", errors="replace")
        inventory.append(
            {
                "script": name,
                "path": script.relative_to(ROOT).as_posix(),
                "status": STATUS_ACTIVE if external_hits else STATUS_ORPHAN,
                "referenced_by_make_targets": sorted(
                    set(referenced_by_targets)
                ),
                "referenced_by_workflows": sorted(set(referenced_by_workflows)),
                "referenced_by_files": sorted(set(external_hits)),
                "lines": len(self_text.splitlines()),
            }
        )
    return inventory


def cmd_export() -> int:
    scripts = collect_scripts()
    inventory = classify(scripts)
    registry = load_registry()
    entries = {e["script"]: e for e in registry.get("entries", [])}
    for item in inventory:
        entry = entries.get(item["script"])
        if entry and entry.get("wire_or_retire"):
            item["wire_or_retire"] = entry["wire_or_retire"]
    retired = sorted(
        p.name
        for pattern in ("*.py", "*.sh")
        for p in RETIRED_DIR.glob(pattern)
        if p.is_file()
    ) if RETIRED_DIR.exists() else []
    unwired = [
        e
        for e in inventory
        if e["status"] == STATUS_ACTIVE
        and not e["referenced_by_make_targets"]
        and not e["referenced_by_workflows"]
    ]
    disposition_counts = {
        value: sum(1 for e in unwired if e.get("wire_or_retire") == value)
        for value in WIRE_OR_RETIRE_VALUES
    }
    counts = {
        STATUS_ACTIVE: sum(1 for e in inventory if e["status"] == STATUS_ACTIVE),
        STATUS_ORPHAN: sum(1 for e in inventory if e["status"] == STATUS_ORPHAN),
        STATUS_RETIRED: len(retired),
        "unwired": len(unwired),
        "unwired_undispositioned": sum(
            1 for e in unwired if not e.get("wire_or_retire")
        ),
        "wire_or_retire": disposition_counts,
    }
    _, gate_enforced = gate_reachability(registry, inventory)
    gate_required = [name for name in (registry.get("gate_required") or []) if name]
    counts["gate_anchors"] = len(
        [a for a in (registry.get("gate_anchors") or []) if isinstance(a, dict)]
    )
    counts["gate_enforced"] = sum(
        1 for e in inventory if gate_enforced.get(e["script"])
    )
    counts["manual_lane_only"] = sum(
        1
        for e in inventory
        if e["status"] == STATUS_ACTIVE and not gate_enforced.get(e["script"])
    )
    counts["gate_required"] = len(gate_required)
    counts["gate_required_unenforced"] = sum(
        1 for name in gate_required if not gate_enforced.get(name, False)
    )
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "counts": counts,
        "scripts": sorted(inventory, key=lambda e: e["script"]),
        "retired": retired,
    }
    EXPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"[guard-registry] export: {counts[STATUS_ACTIVE]} active, "
        f"{counts[STATUS_ORPHAN]} orphan, {counts[STATUS_RETIRED]} retired, "
        f"{counts['unwired']} unwired "
        f"({counts['unwired_undispositioned']} undispositioned) "
        f"-> {EXPORT_PATH.relative_to(ROOT)}"
    )
    return 0


def cmd_audit() -> int:
    doc = load_registry()
    entries = {e["script"]: e for e in doc.get("entries", [])}
    scripts = collect_scripts()
    inventory = classify(scripts)
    by_name = {e["script"]: e for e in inventory}
    retired_files = (
        sorted(
            p.name
            for pattern in ("*.py", "*.sh")
            for p in RETIRED_DIR.glob(pattern)
            if p.is_file()
        )
        if RETIRED_DIR.exists()
        else []
    )
    failures: list[str] = []

    for entry_name, entry in entries.items():
        status = entry.get("status")
        if status == STATUS_RETIRED:
            if entry_name not in retired_files:
                failures.append(
                    f"registry entry '{entry_name}' is retired but not present in "
                    f"scripts/verify/retired/"
                )
        elif entry_name not in by_name:
            failures.append(
                f"registry entry '{entry_name}' does not match any script under "
                f"scripts/verify/ (typo or already deleted?)"
            )
        if status not in {
            STATUS_ACTIVE,
            STATUS_ACTIVE_DYNAMIC,
            STATUS_ORPHAN,
            STATUS_RETIRED,
        }:
            failures.append(f"registry entry '{entry_name}' has unknown status '{status}'")
        if status == STATUS_ORPHAN and not entry.get("review_by"):
            failures.append(
                f"orphan '{entry_name}' lacks review_by deadline (retire or re-activate)"
            )

    for retired_name in retired_files:
        entry = entries.get(retired_name)
        if not entry:
            failures.append(
                f"retired script '{retired_name}' has no registry.yaml entry"
            )
        elif entry.get("status") != STATUS_RETIRED:
            failures.append(
                f"retired script '{retired_name}' registry status is "
                f"'{entry.get('status')}', expected '{STATUS_RETIRED}'"
            )

    for item in inventory:
        name = item["script"]
        entry = entries.get(name)
        if item["status"] == STATUS_ORPHAN and not entry:
            failures.append(
                f"orphan script '{name}' is not acknowledged in registry.yaml "
                f"(run: make guard.registry.seed, then review)"
            )
        if item["status"] == STATUS_ACTIVE:
            failures.extend(disposition_failures(name, entry, item))
        if entry and entry.get("status") == STATUS_RETIRED and item["status"] != STATUS_RETIRED:
            failures.append(
                f"'{name}' is marked retired in registry.yaml but still lives in "
                f"scripts/verify/ (move it to retired/ or fix the entry)"
            )
        if entry and entry.get("status") == STATUS_ACTIVE_DYNAMIC and item["status"] != STATUS_ACTIVE:
            failures.append(
                f"'{name}' claims active-dynamic but no static reference exists "
                f"and it is not orphan-acknowledged"
            )
        if (
            entry
            and entry.get("status") == STATUS_ORPHAN
            and item["status"] == STATUS_ACTIVE
        ):
            failures.append(
                f"'{name}' is acknowledged as orphan but is referenced by "
                f"make/CI (stale entry: run make guard.registry.seed)"
            )

    graph = parse_make_graph()
    failures.extend(gate_anchor_failures(doc, graph))
    _, gate_enforced = gate_reachability(doc, inventory)
    gate_required = [name for name in (doc.get("gate_required") or []) if name]
    for required in gate_required:
        if required not in by_name:
            failures.append(
                f"gate_required script '{required}' does not match any script "
                f"under scripts/verify/ (typo or already deleted?)"
            )
            continue
        failures.extend(
            gate_required_failures(required, gate_enforced.get(required, False))
        )
    enforced_required = sum(
        1 for name in gate_required if gate_enforced.get(name, False)
    )

    # Retired scripts must not be referenced by make targets or workflows.
    make_text = "\n".join(
        m.read_text(encoding="utf-8", errors="replace") for m in MAKE_FILES
    )
    workflow_text = "\n".join(
        w.read_text(encoding="utf-8", errors="replace") for w in WORKFLOW_FILES
    )
    for retired_name in retired_files:
        if any(
            p.search(text)
            for p in _reference_patterns(retired_name)
            for text in (make_text, workflow_text)
        ):
            failures.append(
                f"retired script '{retired_name}' is still referenced by make/CI"
            )

    total = len(inventory)
    orphans = sum(1 for e in inventory if e["status"] == STATUS_ORPHAN)
    acked = sum(
        1 for e in inventory if e["status"] == STATUS_ORPHAN and e["script"] in entries
    )
    unwired = sum(
        1
        for e in inventory
        if e["status"] == STATUS_ACTIVE
        and not e["referenced_by_make_targets"]
        and not e["referenced_by_workflows"]
    )
    dispositioned = sum(
        1
        for e in inventory
        if e["status"] == STATUS_ACTIVE
        and (entries.get(e["script"]) or {}).get("wire_or_retire")
    )
    if failures:
        print("[guard-registry] AUDIT FAIL:")
        for failure in failures:
            print(f"  ✗ {failure}")
        return 1
    print(
        f"[guard-registry] AUDIT PASS: {total} scripts "
        f"({total - orphans} referenced, {acked}/{orphans} orphans acknowledged, "
        f"{len(retired_files)} retired, {dispositioned}/{unwired} unwired "
        f"dispositioned, {enforced_required}/{len(gate_required)} gate_required "
        f"enforced)"
    )
    return 0


def cmd_seed() -> int:
    doc = load_registry()
    entries = doc.get("entries", [])
    known = {e["script"] for e in entries}
    inventory = classify(collect_scripts())
    referenced = {e["script"] for e in inventory if e["status"] == STATUS_ACTIVE}
    added = 0
    dropped = 0
    dispositions_added = 0
    dispositions_dropped = 0
    for item in inventory:
        if item["status"] == STATUS_ORPHAN and item["script"] not in known:
            entries.append(
                {
                    "script": item["script"],
                    "status": STATUS_ORPHAN,
                    "owner": "platform-team",
                    "date": subprocess.run(
                        ["git", "log", "-1", "--format=%as", "--", item["path"]],
                        cwd=ROOT, capture_output=True, text=True,
                    ).stdout.strip()
                    or "unknown",
                    "review_by": "2026-09-30",
                    "reason": "unreferenced by make/CI at R7 first-round onboarding",
                }
            )
            added += 1
    # Wire-or-retire dispositions for unwired active scripts (machine-checkable).
    entry_by_name = {e["script"]: e for e in entries}
    for item in inventory:
        name = item["script"]
        if item["status"] != STATUS_ACTIVE:
            continue
        wired = bool(
            item["referenced_by_make_targets"] or item["referenced_by_workflows"]
        )
        entry = entry_by_name.get(name)
        if wired:
            if entry and entry.get("wire_or_retire"):
                entry.pop("wire_or_retire")
                dispositions_dropped += 1
            continue
        if entry and entry.get("wire_or_retire"):
            continue
        if entry is None:
            entry = {
                "script": name,
                "status": STATUS_ACTIVE,
                "owner": "platform-team",
                "date": subprocess.run(
                    ["git", "log", "-1", "--format=%as", "--", item["path"]],
                    cwd=ROOT, capture_output=True, text=True,
                ).stdout.strip()
                or "unknown",
            }
            entries.append(entry)
            entry_by_name[name] = entry
        # An active script always has at least one file reference (otherwise
        # classify() would have marked it orphan), so the default disposition
        # is file-consumed; wire-pending/retire-pending are deliberate manual
        # classifications that must carry their own review_by deadline.
        entry["wire_or_retire"] = "file-consumed"
        entry.setdefault(
            "reason",
            "consumed only by scripts/tests; no governed make/workflow entry",
        )
        dispositions_added += 1
    # Drop stale orphan acknowledgements whose scripts are referenced again.
    kept = []
    for entry in entries:
        if (
            entry.get("status") == STATUS_ORPHAN
            and entry["script"] in referenced
        ):
            dropped += 1
            continue
        kept.append(entry)
    doc["entries"] = sorted(kept, key=lambda e: e["script"])
    save_registry(doc)
    print(
        f"[guard-registry] seed: +{added} orphan acknowledgements, "
        f"-{dropped} stale entries, +{dispositions_added} wire-or-retire "
        f"dispositions, -{dispositions_dropped} stale dispositions "
        f"-> {REGISTRY_PATH.relative_to(ROOT)}"
    )
    return 0


def cmd_retire(script_name: str, reason: str) -> int:
    if not reason or not reason.strip():
        print("[guard-registry] --reason is required for retirement audit trail")
        return 2
    matches = [p for p in collect_scripts() if p.name == script_name]
    if not matches:
        print(f"[guard-registry] script '{script_name}' not found under scripts/verify/")
        return 2
    if len(matches) > 1:
        print(
            f"[guard-registry] ambiguous name '{script_name}' matches: "
            + ", ".join(str(m.relative_to(VERIFY_DIR)) for m in matches)
        )
        return 2
    source = matches[0]
    make_text = "\n".join(
        m.read_text(encoding="utf-8", errors="replace") for m in MAKE_FILES
    )
    workflow_text = "\n".join(
        w.read_text(encoding="utf-8", errors="replace") for w in WORKFLOW_FILES
    )
    if any(
        p.search(text)
        for p in _reference_patterns(script_name)
        for text in (make_text, workflow_text)
    ):
        print(
            f"[guard-registry] refusing to retire '{script_name}': still referenced "
            f"by make/CI (remove the reference first)"
        )
        return 2
    RETIRED_DIR.mkdir(parents=True, exist_ok=True)
    dest = RETIRED_DIR / script_name
    if dest.exists():
        print(f"[guard-registry] destination already exists: {dest}")
        return 2
    shutil.move(str(source), str(dest))
    doc = load_registry()
    entries = doc.get("entries", [])
    entry = next((e for e in entries if e["script"] == script_name), None)
    if entry is None:
        entry = {"script": script_name}
        entries.append(entry)
    entry.update(
        {
            "status": STATUS_RETIRED,
            "date": subprocess.run(
                ["git", "log", "-1", "--format=%as", "--", str(source.relative_to(ROOT))],
                cwd=ROOT, capture_output=True, text=True,
            ).stdout.strip()
            or "unknown",
            "reason": reason.strip(),
        }
    )
    entry.pop("review_by", None)
    doc["entries"] = sorted(entries, key=lambda e: e["script"])
    save_registry(doc)
    print(
        f"[guard-registry] retired: {script_name} -> "
        f"{dest.relative_to(ROOT)} (reason recorded in registry.yaml)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--export", action="store_true", help="write JSON inventory")
    mode.add_argument("--seed", action="store_true", help="acknowledge new orphans")
    mode.add_argument("--retire", metavar="SCRIPT", help="retire a script by filename")
    parser.add_argument("--reason", default="", help="retirement reason (required with --retire)")
    args = parser.parse_args()
    if args.export:
        return cmd_export()
    if args.seed:
        return cmd_seed()
    if args.retire:
        return cmd_retire(args.retire, args.reason)
    return cmd_audit()


if __name__ == "__main__":
    sys.exit(main())
