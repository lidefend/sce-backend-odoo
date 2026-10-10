#!/usr/bin/env python3
"""Test coverage registry: bind declared Odoo test groups to a governed entry.

Why this exists (2026-10-10 nightly triage): the repository declared a large
number of Odoo test groups through ``@tagged(...)`` and shipped
``scripts/ci/test_*.py`` unit scripts, but nothing proved that a declared
group was ever *executed* by a governed entry. The 2026-10-09 nightly proved
the gap is not theoretical:

* the ``Run backend test suite per module`` step aborted on its first failing
  module (errexit was never disabled), so every later module - and its group
  coverage - was silently skipped and still reported as a pass;
* ``uc4_native_lowcode`` (16 test files) was "verified" once by hand and then
  had no recurring gate at all;
* ``scripts/ci/test_backend_test_suite_dispatch_contract.py`` existed with
  zero make/workflow references.

This tool makes the gap machine-checkable. It inventories every declared
group and every ``scripts/ci/test_*.py`` unit script, resolves whether a
governed test-selection entry reaches it, and fails closed when a group is
neither gated nor explicitly dispositioned in
``scripts/verify/test_coverage_registry.yaml``.

Reachability tiers (deliberately conservative):

* ``gated``     - the tag token appears in a test-selection expression of a
                  CI workflow, or of a make target that a workflow invokes
                  directly. This is the only tier treated as covered.
* ``on-demand`` - the tag (or a test class carrying it) appears only in a
                  hand-invoked make/test entry. Reachable, but nothing
                  re-runs it on a schedule or on a PR, so it needs a
                  disposition.
* ``unwired``   - no governed entry references the tag at all. Needs a
                  disposition and a ``review_by`` deadline.

A passing audit is a *coverage bookkeeping* result. It states that every
declared group is either gated or recorded with an owner; it does not claim
the group passes, and it is not a substitute for running the group.

Modes:

* ``--export``  write the deterministic JSON inventory to
                ``docs/audit/test_coverage_registry/test_coverage_registry.json``.
* ``--seed``    append registry entries for newly detected un-gated groups
                and unwired ``scripts/ci/test_*.py`` scripts.
* (default)     audit; exit 1 on any undispositioned group, stale entry,
                inconsistent status or missing required field.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "scripts" / "verify" / "test_coverage_registry.yaml"
EXPORT_PATH = (
    ROOT / "docs" / "audit" / "test_coverage_registry" / "test_coverage_registry.json"
)

MAKE_FILES = sorted([ROOT / "Makefile", *(ROOT / "make").glob("*.mk")])
WORKFLOW_FILES = sorted(
    (*ROOT.glob(".github/workflows/*.yml"), *ROOT.glob(".github/workflows/*.yaml"))
)
SCRIPT_SELECTION_GLOBS = (
    "scripts/**/*.py",
    "scripts/**/*.sh",
    "scripts/**/*.js",
    "scripts/**/*.mjs",
)

ADDON_ROOTS = ("addons", "demo_addons")
CI_UNIT_GLOB = "test_*.py"

STATUS_GATED = "gated"
STATUS_ON_DEMAND = "on-demand"
STATUS_UNWIRED = "unwired"

DISPOSITIONS = ("class-selected", "wire-pending", "retire-pending", "known-gap")

STANDARD_TAGS = {
    "standard",
    "at_install",
    "post_install",
    "-at_install",
    "-post_install",
}

TAGGED_RE = re.compile(r"@tagged\((.*?)\)", re.DOTALL)
CLASS_RE = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)")
STRING_LITERAL_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')

SELECTION_KEYS = (
    "TEST_TAGS_INPUT",
    "TEST_TAGS",
    "test_tags",
    "test-tags",
    "SC_AUTHORIZATION_ORM_TEST_TAGS",
)
SELECTION_RE = re.compile(
    r"(?:TEST_TAGS|test_tags|test-tags|TEST_TAGS_INPUT|SC_AUTHORIZATION_ORM_TEST_TAGS)"
    r'\s*[:=]?\s*["\']?([^\n"\']*)'
)
SELECTION_DEFAULT_RE = re.compile(
    r"\$\{(?:TEST_TAGS|test_tags|test-tags|TEST_TAGS_INPUT|"
    r"SC_AUTHORIZATION_ORM_TEST_TAGS):-([^}]*)\}"
)

MAKE_TARGET_RE = re.compile(r"^([a-zA-Z0-9][a-zA-Z0-9._/%-]*)\s*:")
WORKFLOW_MAKE_RE = re.compile(
    r"\bmake\s+(?:--no-print-directory\s+)?([a-zA-Z0-9][a-zA-Z0-9._-]*)"
)

# Owner routing mirrors .github/CODEOWNERS at module-family granularity so a
# disposition names a real owning team instead of a placeholder.
OWNER_RULES = (
    ("demo_addons/", "demo-team"),
    ("addons/smart_core/", "platform-team"),
    ("addons/smart_owner", "platform-team"),
    ("addons/smart_license", "platform-team"),
    ("addons/smart_scene", "platform-team"),
    ("addons/sc_norm_engine", "platform-team"),
    ("addons/smart_construction_", "construction-product"),
)
DEFAULT_OWNER = "platform-team"


def owner_for(path: str) -> str:
    for prefix, owner in OWNER_RULES:
        if path.startswith(prefix):
            return owner
    return DEFAULT_OWNER


def tag_token_pattern(tag: str) -> re.Pattern[str]:
    """Whole-token match for Odoo test-tag expressions.

    Odoo qualifies a tag by module as ``tag/<module>`` and joins alternatives
    with commas, so a trailing ``/`` must stay allowed - otherwise the real
    expression ``sc_smoke/${module},sc_gate/${module}`` would be reported as
    not selecting ``sc_gate``. A trailing ``_`` or ``-`` is still rejected so
    ``sc_gate`` never matches inside ``sc_gate_v2``.
    """
    return re.compile(r"(?<![\w/-])" + re.escape(tag) + r"(?![\w-])")


def parse_make_targets() -> tuple[dict[str, str], dict[str, str]]:
    """Return (target -> prerequisites, target -> recipe/body text)."""
    prereqs: dict[str, str] = {}
    bodies: dict[str, str] = {}
    for makefile in MAKE_FILES:
        current: str | None = None
        buffer: list[str] = []
        for raw in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
            if raw.startswith("\t"):
                if current:
                    buffer.append(raw)
                continue
            match = MAKE_TARGET_RE.match(raw)
            if match and not raw.startswith(".PHONY"):
                if current:
                    bodies[current] = "\n".join(buffer)
                current = match.group(1)
                buffer = [raw]
            elif raw.strip() and current:
                buffer.append(raw)
            elif not raw.strip() and current:
                bodies[current] = "\n".join(buffer)
                current, buffer = None, []
        if current:
            bodies[current] = "\n".join(buffer)
    for name, body in bodies.items():
        header = body.splitlines()[0] if body.splitlines() else ""
        _, _, rhs = header.partition(":")
        prereqs[name] = " ".join(rhs.split())
    return prereqs, bodies


def workflow_invoked_targets() -> set[str]:
    names: set[str] = set()
    for workflow in WORKFLOW_FILES:
        text = workflow.read_text(encoding="utf-8", errors="replace")
        names.update(WORKFLOW_MAKE_RE.findall(text))
    return names


def selection_expressions(sources: dict[str, str]) -> list[dict]:
    """Extract test-selection expressions with their source and authority."""
    expressions: list[dict] = []
    for key, text in sources.items():
        for match in SELECTION_RE.finditer(text):
            expressions.append(
                {"source": key, "expression": match.group(1).strip(), "origin": "assign"}
            )
        for match in SELECTION_DEFAULT_RE.finditer(text):
            expressions.append(
                {"source": key, "expression": match.group(1).strip(), "origin": "default"}
            )
    return expressions


def parse_tagged_declarations(text: str) -> list[tuple[str, str | None]]:
    """Parse ``@tagged(...)`` decorators from one test module's text.

    Returns ``(tag, class_name_or_None)`` pairs. ``@tagged`` arguments may
    span multiple lines and may be stacked under other decorators; the class
    is attached only when a ``class`` statement is the next real line.
    """
    declarations: list[tuple[str, str | None]] = []
    for match in TAGGED_RE.finditer(text):
        decorator_tags = [
            (double or single)
            for double, single in STRING_LITERAL_RE.findall(match.group(1))
        ]
        klass: str | None = None
        for line in text[match.end():].split("\n")[:8]:
            stripped = line.strip()
            if not stripped or stripped.startswith("@"):
                continue
            klass_match = CLASS_RE.match(stripped)
            if klass_match:
                klass = klass_match.group(1)
            break
        for tag in decorator_tags:
            declarations.append((tag, klass))
    return declarations


def collect_tag_declarations() -> dict[str, dict]:
    """tag -> {files: set, classes: set, declarations: int}.

    ``@tagged`` arguments span multiple lines in several files, so the
    decorator is matched across newlines. Every declaration is counted at
    least at file level; the carrying test class is attached when the
    decorator (possibly stacked under other decorators) sits directly above a
    ``class`` statement. A decorator applied to a test method still registers,
    so no declared group can be hidden from the audit by formatting.
    """
    tags: dict[str, dict] = collections.OrderedDict()

    def record(tag: str, rel: str, klass: str | None) -> None:
        if tag in STANDARD_TAGS:
            return
        entry = tags.setdefault(
            tag, {"files": set(), "classes": set(), "declarations": 0}
        )
        entry["files"].add(rel)
        if klass:
            entry["classes"].add(klass)
        entry["declarations"] += 1

    for addon_root in ADDON_ROOTS:
        for path in sorted((ROOT / addon_root).rglob("test*.py")):
            if "/tests/" not in path.as_posix():
                continue
            rel = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            for tag, klass in parse_tagged_declarations(text):
                record(tag, rel, klass)
    return tags


def collect_ci_unit_scripts() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "scripts" / "ci").glob(CI_UNIT_GLOB)
        if path.is_file()
    )


def build_gate_sources() -> tuple[dict[str, str], dict[str, str]]:
    """Split selection sources into workflow-level and make-level corpora.

    Workflow sources and make targets invoked directly by a workflow are the
    ``gated`` authority. Everything else is ``on-demand``.
    """
    gated: dict[str, str] = {}
    on_demand: dict[str, str] = {}

    for workflow in WORKFLOW_FILES:
        key = workflow.relative_to(ROOT).as_posix()
        gated[key] = workflow.read_text(encoding="utf-8", errors="replace")

    _, bodies = parse_make_targets()
    invoked = workflow_invoked_targets()
    for name, body in bodies.items():
        if name in invoked:
            gated[f"make:{name}"] = body
        else:
            on_demand[f"make:{name}"] = body

    for pattern in SCRIPT_SELECTION_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file() or "__pycache__" in path.as_posix():
                continue
            key = path.relative_to(ROOT).as_posix()
            on_demand[key] = path.read_text(encoding="utf-8", errors="replace")

    return gated, on_demand


def classify() -> tuple[list[dict], list[dict]]:
    tags = collect_tag_declarations()
    gated_sources, on_demand_sources = build_gate_sources()
    gated_exprs = selection_expressions(gated_sources)
    on_demand_exprs = selection_expressions(on_demand_sources)

    inventory: list[dict] = []
    for tag, record in tags.items():
        pattern = tag_token_pattern(tag)
        gated_hits = [
            f"{entry['source']} :: {entry['expression'][:80]}"
            for entry in gated_exprs
            if pattern.search(entry["expression"])
        ]
        if gated_hits:
            inventory.append(
                {
                    "group": tag,
                    "status": STATUS_GATED,
                    "kind": "odoo_tag",
                    "declarations": record["declarations"],
                    "files": sorted(record["files"]),
                    "owner": owner_for(min(record["files"])),
                    "evidence": sorted(set(gated_hits))[:3],
                }
            )
            continue
        on_demand_hits = [
            f"{entry['source']} :: {entry['expression'][:80]}"
            for entry in on_demand_exprs
            if pattern.search(entry["expression"])
        ]
        if not on_demand_hits:
            for klass in sorted(record["classes"]):
                klass_pattern = re.compile(r"(?<![\w.])" + re.escape(klass) + r"(?![\w])")
                for entry in on_demand_exprs:
                    if klass_pattern.search(entry["expression"]):
                        on_demand_hits.append(
                            f"{entry['source']} :: /{klass} (class selection)"
                        )
        inventory.append(
            {
                "group": tag,
                "status": STATUS_ON_DEMAND if on_demand_hits else STATUS_UNWIRED,
                "kind": "odoo_tag",
                "declarations": record["declarations"],
                "files": sorted(record["files"]),
                "owner": owner_for(min(record["files"])),
                "evidence": sorted(set(on_demand_hits))[:3],
            }
        )

    # A script is "wired" only when a make target or a CI workflow actually
    # invokes it. A mention inside another Python script (a docstring, a
    # registry list) is not execution - this audit's own docstring naming
    # test_backend_test_suite_dispatch_contract.py is the proof.
    script_corpus = _corpus_files()
    script_inventory: list[dict] = []
    for script in collect_ci_unit_scripts():
        name = Path(script).name
        hits = sorted(
            key for key, text in script_corpus.items() if name in text
        )
        script_inventory.append(
            {
                "group": script,
                "status": STATUS_GATED if hits else STATUS_UNWIRED,
                "kind": "ci_unit_script",
                "declarations": 1,
                "files": [script],
                "owner": owner_for(script),
                "evidence": hits[:3],
            }
        )
    return inventory, script_inventory


def _corpus_files() -> dict[str, str]:
    parts: dict[str, str] = {}
    for makefile in MAKE_FILES:
        parts[makefile.relative_to(ROOT).as_posix()] = makefile.read_text(
            encoding="utf-8", errors="replace"
        )
    for workflow in WORKFLOW_FILES:
        parts[workflow.relative_to(ROOT).as_posix()] = workflow.read_text(
            encoding="utf-8", errors="replace"
        )
    return parts


def load_registry() -> dict:
    if not REGISTRY_PATH.is_file():
        return {"version": 1, "entries": []}
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {
        "version": 1,
        "entries": [],
    }


def save_registry(doc: dict) -> None:
    REGISTRY_PATH.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def default_entry(item: dict) -> dict:
    entry = {
        "group": item["group"],
        "kind": item["kind"],
        "status": item["status"],
        "owner": item["owner"],
    }
    if item["status"] == STATUS_ON_DEMAND:
        entry["dispose"] = "class-selected"
        entry["gate"] = item["evidence"][0] if item["evidence"] else "unknown"
        entry["reason"] = (
            "Reachable only through a hand-invoked make/test entry; no recurring "
            "workflow selects this group. Keep as an on-demand disposition until a "
            "scheduled or PR gate selects it."
        )
    else:
        entry["dispose"] = "wire-pending"
        entry["reason"] = (
            "Declared test group with no governed selection entry. Recorded as "
            "known coverage debt; wire it to a gate or retire the group."
        )
        entry["review_by"] = "2026-12-31"
    return entry


def build_export_payload(inventory: list[dict], scripts: list[dict], registry: dict) -> dict:
    entries = {entry["group"]: entry for entry in registry.get("entries", [])}
    for item in [*inventory, *scripts]:
        entry = entries.get(item["group"])
        if entry:
            item["disposition"] = entry.get("dispose")
    counts = collections.Counter(item["status"] for item in inventory)
    script_counts = collections.Counter(item["status"] for item in scripts)
    return {
        "version": 1,
        "generated_by": "scripts/verify/test_coverage_registry_audit.py --export",
        "counts": {
            "odoo_tags": len(inventory),
            "gated": counts.get(STATUS_GATED, 0),
            "on_demand": counts.get(STATUS_ON_DEMAND, 0),
            "unwired": counts.get(STATUS_UNWIRED, 0),
            "odoo_tag_declarations": sum(item["declarations"] for item in inventory),
            "gated_declarations": sum(
                item["declarations"]
                for item in inventory
                if item["status"] == STATUS_GATED
            ),
            "uncovered_declarations": sum(
                item["declarations"]
                for item in inventory
                if item["status"] != STATUS_GATED
            ),
            "ci_unit_scripts": len(scripts),
            "ci_unit_scripts_wired": script_counts.get(STATUS_GATED, 0),
            "ci_unit_scripts_unwired": script_counts.get(STATUS_UNWIRED, 0),
        },
        "odoo_tags": sorted(
            inventory, key=lambda item: (-item["declarations"], item["group"])
        ),
        "ci_unit_scripts": sorted(scripts, key=lambda item: item["group"]),
    }


def cmd_export() -> int:
    inventory, scripts = classify()
    payload = build_export_payload(inventory, scripts, load_registry())
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "[test-coverage] exported "
        f"{payload['counts']['odoo_tags']} tag groups "
        f"({payload['counts']['gated']} gated, "
        f"{payload['counts']['on_demand']} on-demand, "
        f"{payload['counts']['unwired']} unwired) and "
        f"{payload['counts']['ci_unit_scripts']} ci unit scripts -> "
        f"{EXPORT_PATH.relative_to(ROOT)}"
    )
    return 0


def cmd_seed() -> int:
    inventory, scripts = classify()
    registry = load_registry()
    entries = registry.setdefault("entries", [])
    known = {entry["group"] for entry in entries}
    added = 0
    for item in [*inventory, *scripts]:
        if item["status"] == STATUS_GATED or item["group"] in known:
            continue
        entries.append(default_entry(item))
        known.add(item["group"])
        added += 1
    entries.sort(key=lambda entry: entry["group"])
    save_registry(registry)
    print(f"[test-coverage] seeded {added} new registry entr(ies)")
    return 0


def audit_failures(inventory: list[dict], scripts: list[dict], registry: dict) -> list[str]:
    entries = {}
    for entry in registry.get("entries", []):
        group = entry.get("group")
        if not group:
            continue
        entries[group] = entry
    failures: list[str] = []
    declared = {item["group"]: item for item in [*inventory, *scripts]}

    for item in [*inventory, *scripts]:
        group = item["group"]
        entry = entries.get(group)
        if item["status"] == STATUS_GATED:
            if entry and entry.get("status") not in (None, STATUS_GATED):
                failures.append(
                    f"'{group}' is now selected by a governed gate but registry.yaml "
                    f"still records status '{entry.get('status')}'"
                )
            continue
        if not entry:
            failures.append(
                f"test group '{group}' ({item['status']}, {item['declarations']} "
                "declaration(s)) is not dispositioned in registry.yaml "
                "(run: make test.coverage.registry.seed, then review)"
            )
            continue
        for field in ("owner", "reason", "dispose"):
            if not entry.get(field):
                failures.append(f"registry entry '{group}' lacks required field '{field}'")
        if entry.get("dispose") not in DISPOSITIONS:
            failures.append(
                f"registry entry '{group}' has unknown dispose "
                f"'{entry.get('dispose')}' (expected one of {', '.join(DISPOSITIONS)})"
            )
        if entry.get("dispose") == "class-selected" and not entry.get("gate"):
            failures.append(
                f"registry entry '{group}' dispose 'class-selected' must name its gate"
            )
        if item["status"] == STATUS_UNWIRED and not entry.get("review_by"):
            failures.append(
                f"unwired group '{group}' lacks review_by deadline (wire or retire)"
            )

    for group, entry in entries.items():
        if group not in declared:
            failures.append(
                f"registry entry '{group}' does not match any declared group "
                "(typo, or the group was renamed/removed?)"
            )
    return failures


def export_freshness_failure(payload: dict) -> str | None:
    """The tracked JSON snapshot must match the live tree.

    A tracked generated artifact that silently drifts is how an un-gated group
    can look covered; the snapshot has to fail closed instead.
    """
    if not EXPORT_PATH.is_file():
        return (
            f"tracked coverage snapshot {EXPORT_PATH.relative_to(ROOT)} is missing "
            "(run: make test.coverage.registry.export)"
        )
    try:
        on_disk = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"tracked coverage snapshot is not valid JSON: {exc}"
    if on_disk != payload:
        return (
            f"tracked coverage snapshot {EXPORT_PATH.relative_to(ROOT)} is stale "
            "(run: make test.coverage.registry.export)"
        )
    return None


def cmd_audit() -> int:
    inventory, scripts = classify()
    registry = load_registry()
    failures = audit_failures(inventory, scripts, registry)
    freshness = export_freshness_failure(
        build_export_payload(inventory, scripts, registry)
    )
    if freshness:
        failures.append(freshness)
    counts = collections.Counter(item["status"] for item in inventory)
    print(
        f"[test-coverage] odoo tag groups={len(inventory)} "
        f"(gated={counts.get(STATUS_GATED, 0)}, "
        f"on-demand={counts.get(STATUS_ON_DEMAND, 0)}, "
        f"unwired={counts.get(STATUS_UNWIRED, 0)}), "
        f"ci unit scripts={len(scripts)}"
    )
    if failures:
        print("[test-coverage] FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("[test-coverage] PASS all declared groups are gated or dispositioned")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--export", action="store_true", help="write JSON inventory")
    mode.add_argument("--seed", action="store_true", help="add missing registry entries")
    args = parser.parse_args()
    if args.export:
        return cmd_export()
    if args.seed:
        return cmd_seed()
    return cmd_audit()


if __name__ == "__main__":
    sys.exit(main())
