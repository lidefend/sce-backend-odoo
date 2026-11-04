#!/usr/bin/env python3
"""Read-only Join exporter: existing assets -> standardized capability projection.

CAP-01C-ALL-04-R1. Joins identity (candidate catalog), provider (provider
binding doc + capability registry), state machine / model facts and dependency
digests into one capability projection per Keep atomic capability.

Join associates facts the platform already owns; it never creates a registry,
duplicates Odoo registration facts, reimplements the maturity fingerprint or
writes back to the formal candidate catalog. Every projected field records its
original source, and a missing / conflicting / non-unique association is
reported as ``unresolved`` instead of being guessed.
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
SETTLEMENT_ORDER = ROOT / "addons/smart_construction_core/models/core/settlement_order.py"

LIFECYCLE_BUTTONS = {
    "action_sc_start", "action_sc_pause", "action_sc_resume", "action_sc_mark_done",
    "action_sc_begin_closing", "action_sc_start_warranty", "action_sc_close",
}

SPECS = {
    "project.lifecycle.transition": {
        "template": "state-transition",
        "provider_model": "project.project",
        "state_machine": "PROJECT",
        "method_sources": [PROJECT_CORE, INITIATION_APPROVAL],
        "view": LIFECYCLE_VIEW,
    },
    "construction.plan.report": {
        "template": "business-write",
        "provider_model": "sc.plan.report",
        "action": "action_sc_plan_report",
    },
    "cost.progress.report": {
        "template": "business-write",
        "provider_model": "project.progress.entry",
        "action": "action_project_progress_entry",
    },
    "contract.expense.track": {
        "template": "read-only-query",
        "provider_model": "construction.contract.expense",
        "action": "action_construction_contract_expense",
    },
    "contract.income.track": {
        "template": "read-only-query",
        "provider_model": "construction.contract.income",
        "action": "action_construction_contract_income",
    },
    "contract.settlement.audit": {
        "template": "audit-state-transition",
        "provider_model": "sc.settlement.order",
        "state_machine": "SETTLEMENT_ORDER",
        "method_sources": [SETTLEMENT_ORDER],
    },
}


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_line(path: Path, needle: str) -> int:
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if needle in line:
            return i
    return 0


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


def _catalog_map() -> dict[str, dict]:
    return {c["capability_key"]: c for c in json.loads(CATALOG.read_text(encoding="utf-8"))["capabilities"]}


def _join_binding(key: str) -> tuple[dict, str]:
    for line in BINDING.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("|") and key in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            return {
                "capability_key": cells[0],
                "provider_type": cells[1],
                "provider_ref": cells[2].strip("`"),
                "contract_source": cells[3],
            }, f"{BINDING.relative_to(ROOT)}:{_find_line(BINDING, key)}"
    return {}, ""


def _join_registry() -> dict[str, dict]:
    tree = ast.parse(REGISTRY.read_text(encoding="utf-8"))
    caps: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_cap" or len(node.args) < 4:
            continue
        args = [a.value if isinstance(a, ast.Constant) else None for a in node.args]
        access_action, groups, roles = "", [], []
        for kw in node.keywords:
            if kw.arg == "access_action" and isinstance(kw.value, ast.Constant):
                access_action = str(kw.value.value)
            elif kw.arg == "required_groups" and isinstance(kw.value, (ast.List, ast.Tuple)):
                groups = [str(e.value) for e in kw.value.elts if isinstance(e, ast.Constant)]
            elif kw.arg == "required_roles" and isinstance(kw.value, (ast.List, ast.Tuple)):
                roles = [str(e.value) for e in kw.value.elts if isinstance(e, ast.Constant)]
        caps[args[0]] = {
            "label": args[1], "hint": args[2], "group": args[3],
            "access_action": access_action, "required_groups": groups, "required_roles": roles,
        }
    return caps


def _join_state_machine(sm_name: str) -> tuple[dict, str]:
    tree = ast.parse(STATE_MACHINE.read_text(encoding="utf-8"))
    states: list[str] = []
    transitions: dict[str, set[str]] = {}
    states_attr = f"{sm_name}_STATES"
    transitions_attr = f"{sm_name}_TRANSITIONS"
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == states_attr:
                if not isinstance(node.value, (ast.List, ast.Tuple)):
                    continue
                for item in node.value.elts:
                    if isinstance(item, (ast.Tuple, ast.List)) and item.elts and isinstance(item.elts[0], ast.Constant):
                        states.append(str(item.elts[0].value))
            elif target.id == transitions_attr:
                if not isinstance(node.value, ast.Dict):
                    continue
                transitions = {str(k): {str(v) for v in vals} for k, vals in _ast_eval(node.value).items()}
    return {
        "states": states,
        "transitions": {k: sorted(v) for k, v in transitions.items()},
        "terminal_states": [s for s in states if s in transitions and not transitions[s]],
    }, f"{STATE_MACHINE.relative_to(ROOT)}:{_find_line(STATE_MACHINE, states_attr)}"


def _join_methods(paths: list[Path]) -> tuple[list[dict], list[str]]:
    methods: list[dict] = []
    unresolved: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"def (action_(?:sc_)?\w+)\(self[^)]*\):", text):
            name = match.group(1)
            if name in {"action_sc_stage_sync", "action_sc_submit"}:
                continue
            body = text[match.end(): match.end() + 1000]
            target = re.search(r'action_set_lifecycle_state\("([a-z_]+)"\)', body)
            server_guard = bool(re.search(r"raise UserError|_assert_|_check_|_validate_|_ensure_", body))
            line = text[: match.start()].count("\n") + 1
            methods.append({
                "method": name,
                "target_state": target.group(1) if target else None,
                "server_guard": server_guard,
                "source": f"{path.relative_to(ROOT)}:{line}",
            })
    return methods, unresolved


def _join_server_guard() -> tuple[dict, str]:
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


def _find_action_res_model(action: str) -> tuple[str, str]:
    """Find an ir.actions.act_window record's res_model via rg (fail-closed)."""
    try:
        proc = subprocess.run(
            ["rg", "-l", f'id="{action}"', str(ROOT / "addons")],
            cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "", "action_resolution_tool_failure"
    files = [f for f in proc.stdout.splitlines() if f.strip()]
    if not files:
        return "", "action_not_found"
    for f in files:
        text = Path(f).read_text(encoding="utf-8")
        m = re.search(rf'id="{re.escape(action)}"[^>]*>.*?<field name="res_model">([^<]+)</field>', text, re.S)
        if not m:
            m = re.search(rf'<field name="res_model">([^<]+)</field>.*?id="{re.escape(action)}"', text, re.S)
        if m:
            return m.group(1).strip(), f"{Path(f).relative_to(ROOT)}"
    return "", "res_model_not_found_in_action_record"


def _find_model_facts(model: str) -> tuple[dict, str]:
    try:
        proc = subprocess.run(
            ["rg", "-l", f'_name\\s*=\\s*["\']{re.escape(model)}["\']', str(ROOT / "addons")],
            cwd=ROOT, text=True, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}, "model_resolution_tool_failure"
    files = [f for f in proc.stdout.splitlines() if f.strip()]
    if not files:
        return {}, "model_not_found"
    path = Path(files[0])
    text = path.read_text(encoding="utf-8")
    required = sorted(set(re.findall(r'^\s+(\w+)\s*=\s*fields\.\w+\([^)]*required=True[^)]*\)', text, re.M)))
    inherit = re.findall(r'_inherit\s*=\s*\[([^\]]+)\]', text)
    inherits = re.findall(r'_inherits\s*=\s*\{([^}]+)\}', text)
    mail_thread = "mail.thread" in text
    return {
        "model": model,
        "required_fields": required,
        "inherit": inherit[0] if inherit else "",
        "inherits": inherits[0] if inherits else "",
        "mail_thread": mail_thread,
    }, str(path.relative_to(ROOT))


def _projection_for(key: str, spec: dict) -> dict:
    catalog = _catalog_map()
    registry = _join_registry()
    binding, binding_src = _join_binding(key)
    unresolved: list[str] = []
    template = spec["template"]

    provider: dict = {}
    dependencies: dict[str, str] = {}
    machine: dict = {}
    methods: list[dict] = []
    view_guards: list[dict] = []
    server_guard: dict | None = None

    if template in {"state-transition", "audit-state-transition"}:
        machine, machine_src = _join_state_machine(spec["state_machine"])
        methods, _ = _join_methods(spec["method_sources"])
        if template == "state-transition":
            methods = [m for m in methods if m["target_state"] is not None]
        else:
            audit_actions = {
                "action_submit", "action_approve", "action_done", "action_cancel",
                "action_bind_contract", "action_unbind_contract",
            }
            methods = [m for m in methods if m["method"] in audit_actions]
        for p in spec["method_sources"]:
            dependencies[str(p.relative_to(ROOT))] = _sha256(p)
        dependencies[str(STATE_MACHINE.relative_to(ROOT))] = _sha256(STATE_MACHINE)
        if template == "state-transition":
            guard, guard_src = _join_server_guard()
            server_guard = {"value": guard, "source": guard_src}
            text = spec["view"].read_text(encoding="utf-8")
            for match in re.finditer(r'<button name="(action_sc_\w+)"[^>]*invisible="([^"]*)"[^>]*>', text):
                if match.group(1) not in LIFECYCLE_BUTTONS:
                    continue
                g = re.search(r'groups="([^"]+)"', match.group(0))
                view_guards.append({
                    "button": match.group(1),
                    "invisible": match.group(2),
                    "groups": g.group(1) if g else "",
                    "source": f"{spec['view'].relative_to(ROOT)}:{text[:match.start()].count(chr(10)) + 1}",
                })
            dependencies[str(spec["view"].relative_to(ROOT))] = _sha256(spec["view"])
    else:
        action = spec["action"]
        res_model, action_src = _find_action_res_model(action)
        if res_model != spec["provider_model"]:
            unresolved.append(f"{key}: action {action} resolves to {res_model or 'NOT_FOUND'}, expected model {spec['provider_model']}")
        model_facts, model_src = _find_model_facts(spec["provider_model"])
        provider = {
            "provider_type": "odoo_action + odoo_model",
            "action": action,
            "action_res_model": res_model,
            "action_source": action_src,
            "model_facts": model_facts,
            "model_source": model_src,
        }
        if model_src and not model_src.startswith("model_"):
            dependencies[model_src] = _sha256(ROOT / model_src)

    if not binding:
        unresolved.append(f"provider binding row not found: {key}")

    criteria = {
        "state-transition": ["state_enum_declared", "transition_table_exhaustive", "terminal_state_declared", "every_transition_has_method", "server_guard_present"],
        "audit-state-transition": ["audit_actions_declared", "approval_state_declared", "immutable_final_states_declared", "contract_association_boundary_declared"],
        "business-write": ["input_required_fields_declared", "output_record_shape_declared", "error_codes_declared", "side_effect_declared"],
        "read-only-query": ["query_model_declared", "result_columns_declared", "read_side_effect_free", "data_scope_declared"],
    }[template]

    return {
        "capability_key": key,
        "template": template,
        "identity": {
            "value": {k: v for k, v in catalog[key].items() if k != "providers"},
            "source": str(CATALOG.relative_to(ROOT)),
        },
        "provider_binding": {"value": binding, "source": binding_src},
        "registry_projection": {"value": registry.get(key, {}), "source": str(REGISTRY.relative_to(ROOT))},
        "state_machine": {"value": machine, "source": machine_src} if machine else None,
        "transition_methods": methods if methods else None,
        "view_guards": view_guards if view_guards else None,
        "server_guard": server_guard,
        "provider": provider if provider else None,
        "dependencies": dependencies,
        "criteria": criteria,
        "unresolved": unresolved,
    }


def build_all() -> dict:
    projections = [_projection_for(key, spec) for key, spec in SPECS.items()]
    return {
        "schema": "capability.join.projection.v1",
        "head": _head(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "capabilities": projections,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/backend/capability_join_projection_all.json")
    args = parser.parse_args()
    payload = build_all()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "status": "PROJECTED",
        "head": payload["head"],
        "capabilities": {
            c["capability_key"]: {"template": c["template"], "unresolved": c["unresolved"]}
            for c in payload["capabilities"]
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
