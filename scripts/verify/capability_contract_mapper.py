#!/usr/bin/env python3
"""Read-only Join exporter: existing assets -> standardized capability projection.

CAP-01C-ALL-04-R1 Phase 1 sample for ``project.lifecycle.transition``.

The Join associates facts the platform already owns; it never creates a new
registry, duplicates Odoo registration facts, reimplements the maturity
fingerprint or writes back to the formal candidate catalog. Every projected
field records its original source, and a missing / conflicting / non-unique
association is reported as ``unresolved`` instead of being guessed.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CATALOG = ROOT / "docs/product/capability_candidate_catalog_v1.json"
BINDING = ROOT / "docs/product/capability_provider_binding_v1.md"
REGISTRY = ROOT / "addons/smart_construction_core/services/capability_registry.py"
STATE_MACHINE = ROOT / "addons/smart_construction_core/models/support/state_machine.py"
PROJECT_CORE = ROOT / "addons/smart_construction_core/models/core/project_core.py"
INITIATION_APPROVAL = ROOT / "addons/smart_construction_core/models/core/project_initiation_approval.py"
LIFECYCLE_VIEW = ROOT / "addons/smart_construction_core/views/menu_product_contract_completion_v1.xml"

KEY = "project.lifecycle.transition"
LIFECYCLE_BUTTONS = {
    "action_sc_start", "action_sc_pause", "action_sc_resume", "action_sc_mark_done",
    "action_sc_begin_closing", "action_sc_start_warranty", "action_sc_close",
}


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ast_eval(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Set):
        return {_ast_eval(e) for e in node.elts}
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_ast_eval(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_ast_eval(k): _ast_eval(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "set" and not node.args:
        return set()
    raise ValueError(f"unsupported ast node: {type(node).__name__}")


def _find_line(path: Path, needle: str) -> int:
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            return i
    return 0


def join_identity() -> tuple[dict, str]:
    caps = json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]
    entry = next(c for c in caps if c["capability_key"] == KEY)
    return entry, str(CATALOG.relative_to(ROOT))


def join_provider_binding() -> tuple[dict, str]:
    """Associate provider from the CAP-01B provider binding table."""
    for line in BINDING.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("|") and KEY in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            return {
                "capability_key": cells[0],
                "provider_type": cells[1],
                "provider_ref": cells[2].strip("`"),
                "contract_source": cells[3],
            }, f"{BINDING.relative_to(ROOT)}:{_find_line(BINDING, KEY)}"
    return {}, ""


def join_state_machine() -> tuple[dict, str]:
    tree = ast.parse(STATE_MACHINE.read_text(encoding="utf-8"))
    states: list[str] = []
    transitions: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "PROJECT_STATES":
                for item in node.value.elts:
                    if isinstance(item, (ast.Tuple, ast.List)) and item.elts and isinstance(item.elts[0], ast.Constant):
                        states.append(str(item.elts[0].value))
            elif target.id == "PROJECT_TRANSITIONS":
                transitions = {str(k): {str(v) for v in vals} for k, vals in _ast_eval(node.value).items()}
    return {
        "states": states,
        "transitions": {k: sorted(v) for k, v in transitions.items()},
        "terminal_states": [s for s in states if s in transitions and not transitions[s]],
    }, f"{STATE_MACHINE.relative_to(ROOT)}:{_find_line(STATE_MACHINE, 'PROJECT_STATES')}-{_find_line(STATE_MACHINE, 'PROJECT_TRANSITIONS')}"


def join_methods() -> tuple[list[dict], list[str]]:
    """Map every lifecycle transition method to its target state and source."""
    methods: list[dict] = []
    unresolved: list[str] = []
    for path in (INITIATION_APPROVAL, PROJECT_CORE):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"def (action_sc_\w+)\(self\):", text):
            name = match.group(1)
            if name in {"action_sc_stage_sync", "action_sc_submit"}:
                continue
            body = text[match.end(): match.end() + 1000]
            target = re.search(r'action_set_lifecycle_state\("([a-z_]+)"\)', body)
            server_guard = bool(re.search(r"raise UserError|_assert_initiation_approved|_check_|_validate_", body))
            line = text[: match.start()].count("\n") + 1
            methods.append({
                "method": name,
                "target_state": target.group(1) if target else None,
                "server_guard": server_guard,
                "source": f"{path.relative_to(ROOT)}:{line}",
            })
            if target is None:
                unresolved.append(f"method without target state: {name} in {path.relative_to(ROOT)}:{line}")
    return methods, unresolved


def join_server_guard() -> tuple[dict, str]:
    line = _find_line(PROJECT_CORE, "def action_set_lifecycle_state")
    text = PROJECT_CORE.read_text(encoding="utf-8")
    m = re.search(r"def action_set_lifecycle_state\(self, target_state\):(.*?)def \w+", text, re.S)
    body = m.group(1) if m else ""
    checks = ["_check_lifecycle_transition_permission", "_validate_lifecycle_transition"]
    return {
        "method": "action_set_lifecycle_state",
        "checks": [c for c in checks if c in body],
        "writes": "lifecycle_state",
    }, f"{PROJECT_CORE.relative_to(ROOT)}:{line}"


def join_view_guards() -> tuple[list[dict], str]:
    guards: list[dict] = []
    text = LIFECYCLE_VIEW.read_text(encoding="utf-8")
    for match in re.finditer(r'<button name="(action_sc_\w+)"[^>]*invisible="([^"]*)"[^>]*>', text):
        if match.group(1) not in LIFECYCLE_BUTTONS:
            continue
        groups = ""
        gmatch = re.search(r'groups="([^"]+)"', match.group(0))
        if gmatch:
            groups = gmatch.group(1)
        line = text[: match.start()].count("\n") + 1
        guards.append({
            "button": match.group(1),
            "invisible": match.group(2),
            "groups": groups,
            "source": f"{LIFECYCLE_VIEW.relative_to(ROOT)}:{line}",
        })
    return guards, str(LIFECYCLE_VIEW.relative_to(ROOT))


def build_projection() -> dict:
    identity, identity_src = join_identity()
    binding, binding_src = join_provider_binding()
    machine, machine_src = join_state_machine()
    methods, method_unresolved = join_methods()
    guard, guard_src = join_server_guard()
    view_guards, view_src = join_view_guards()

    dependencies = {
        str(p.relative_to(ROOT)): _sha256(p)
        for p in (PROJECT_CORE, STATE_MACHINE, INITIATION_APPROVAL, LIFECYCLE_VIEW)
    }

    criteria = {
        "state_transition_contract": [
            "state_enum_declared",
            "transition_table_exhaustive",
            "terminal_state_declared",
            "every_transition_has_method",
            "server_guard_present",
            "view_guard_consistent_with_state_machine",
        ]
    }

    unresolved = list(method_unresolved)
    if not binding:
        unresolved.append("provider binding row not found in " + str(BINDING.relative_to(ROOT)))
    if len(methods) != 7:
        unresolved.append(f"expected 7 lifecycle transition methods, joined {len(methods)}")

    return {
        "schema": "capability.join.projection.v1",
        "capability_key": KEY,
        "head": _head(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "join": {
            "identity": {"value": identity, "source": identity_src},
            "provider_binding": {"value": binding, "source": binding_src},
            "state_machine": {"value": machine, "source": machine_src},
            "transition_methods": {"value": methods, "source": [str(INITIATION_APPROVAL.relative_to(ROOT)), str(PROJECT_CORE.relative_to(ROOT))]},
            "server_guard": {"value": guard, "source": guard_src},
            "view_guards": {"value": view_guards, "source": view_src},
            "dependencies": {"value": dependencies, "source": "provider + state machine + approval + view sources"},
        },
        "projection": {
            "capability_key": KEY,
            "providers": [
                {
                    "provider_type": "odoo_model",
                    "provider_ref": binding.get("provider_ref") or "project.project",
                    "contract_ref": str(PROJECT_CORE.relative_to(ROOT)),
                    "provider_status": "located",
                }
            ],
            "states": machine["states"],
            "transitions": machine["transitions"],
            "transition_methods": methods,
            "server_guard": guard,
            "view_guards": view_guards,
            "dependencies": dependencies,
            "criteria": criteria,
        },
        "unresolved": unresolved,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/backend/capability_join_projection_lifecycle.json")
    args = parser.parse_args()
    projection = build_projection()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(projection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PROJECTED",
        "capability_key": KEY,
        "head": projection["head"],
        "unresolved": projection["unresolved"],
        "output": str(args.out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
