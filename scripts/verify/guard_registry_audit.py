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
                 at a missing script, or when a retired script is still
                 referenced by make/CI.
* ``--seed``     Merge missing orphan acknowledgements into registry.yaml
                 with default review metadata (first-round onboarding).
* ``--retire``   Move a script into scripts/verify/retired/ and mark it
                 retired in registry.yaml (the retirement mechanism).

Static-analysis caveat: references are matched by script filename across
make files, scripts/** and .github/workflows. A script invoked only through
fully dynamic name construction may be a false orphan; acknowledge it in
registry.yaml with ``status: active-dynamic`` and a reason.
"""

from __future__ import annotations

import argparse
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

STATUS_ACTIVE = "active"
STATUS_ACTIVE_DYNAMIC = "active-dynamic"
STATUS_ORPHAN = "orphan"
STATUS_RETIRED = "retired"


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


def build_corpus(exclude: Path | None = None) -> tuple[str, dict[str, str]]:
    """Reference corpus text + per-file map for attribution."""
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
    return "\n".join(parts.values()), parts


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
    ]


def classify(scripts: list[Path]) -> list[dict]:
    corpus, parts = build_corpus()
    targets = parse_make_targets()
    inventory = []
    for script in scripts:
        name = script.name
        patterns = _reference_patterns(name)
        external_hits = [
            key
            for key, text in parts.items()
            if key != script.relative_to(ROOT).as_posix()
            and any(p.search(text) for p in patterns)
        ]
        referenced_by_targets = [
            target
            for target, text in targets.items()
            if any(p.search(text) for p in patterns)
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
    retired = sorted(
        p.name
        for pattern in ("*.py", "*.sh")
        for p in RETIRED_DIR.glob(pattern)
        if p.is_file()
    ) if RETIRED_DIR.exists() else []
    counts = {
        STATUS_ACTIVE: sum(1 for e in inventory if e["status"] == STATUS_ACTIVE),
        STATUS_ORPHAN: sum(1 for e in inventory if e["status"] == STATUS_ORPHAN),
        STATUS_RETIRED: len(retired),
    }
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
        f"{counts[STATUS_ORPHAN]} orphan, {counts[STATUS_RETIRED]} retired "
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
    if failures:
        print("[guard-registry] AUDIT FAIL:")
        for failure in failures:
            print(f"  ✗ {failure}")
        return 1
    print(
        f"[guard-registry] AUDIT PASS: {total} scripts "
        f"({total - orphans} referenced, {acked}/{orphans} orphans acknowledged, "
        f"{len(retired_files)} retired)"
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
        f"-{dropped} stale entries -> {REGISTRY_PATH.relative_to(ROOT)}"
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
