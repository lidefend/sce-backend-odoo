#!/usr/bin/env python3
"""Replay the change-impact acceptance matrix against the shadow planner.

This is verification-system self-verification. It reads Git facts and selected
historical commits but does not execute product gates, databases or browsers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit.generate_change_impact_verification_inventory import (
    impact_analysis_acceptance_matrix,
)
from scripts.ops import change_impact_planner as planner
from scripts.verify.frontend_dev_incremental import select_targets


PRODUCT_LAYERS = frozenset({"L1", "L2", "L3"})
INPUT_PATHS = (
    "scripts/audit/generate_change_impact_verification_inventory.py",
    "scripts/ops/change_impact_acceptance.py",
    "scripts/ops/change_impact_evidence.py",
    "scripts/ops/change_impact_graph.py",
    "scripts/ops/change_impact_planner.py",
    "scripts/ops/typescript_change_facts.mjs",
    "scripts/verify/frontend_dev_incremental.py",
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def _input_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in INPUT_PATHS:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((ROOT / path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _ts_rows(*names: tuple[str, str, int, int]) -> dict[str, Any]:
    return {
        "before": {
            "ok": True,
            "symbols": [
                {"name": name, "kind": kind, "start_line": start, "end_line": end}
                for name, kind, start, end in names
            ],
            "fields": [],
            "imports": [],
            "import_bindings": [],
            "assertion_calls": [],
            "dynamic_dependency_possible": False,
        },
        "after": {
            "ok": True,
            "symbols": [
                {"name": name, "kind": kind, "start_line": start, "end_line": end}
                for name, kind, start, end in names
            ],
            "fields": [],
            "imports": [],
            "import_bindings": [],
            "assertion_calls": [],
            "dynamic_dependency_possible": False,
        },
    }


def _historical_paths(commit: str, sample_paths: list[str]) -> list[str]:
    changed = _git(
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        f"{commit}^",
        commit,
        "--",
        *sample_paths,
    ).split("\0")
    return sorted({path for path in changed if path})


def historical_plan(case: dict[str, Any]) -> dict[str, Any]:
    commit = str(case["sample"]["commit"])
    paths = _historical_paths(commit, list(case["sample"]["paths"]))
    return planner.plan_from_git(
        base=_git("rev-parse", f"{commit}^").strip(),
        head=_git("rev-parse", commit).strip(),
        paths=paths,
    )


def synthetic_plan(case_id: str) -> dict[str, Any]:
    base = "a" * 40
    head = "b" * 40
    if case_id == "css-responsive-only":
        return planner.analyze_change_set(
            [
                {
                    "path": "frontend/apps/web/src/pages/ListPage.css",
                    "before": ".record { min-height: 38px; }\n",
                    "after": "@media (max-width: 640px) { .record { min-height: 44px; } }\n",
                },
                {
                    "path": "frontend/apps/web/src/components/template/FormSection.css",
                    "before": ".section { display: grid; }\n",
                    "after": "@media (max-width: 390px) { .section { display: block; } }\n",
                },
            ],
            base=base,
            head=head,
        )
    if case_id == "dynamic-consumer-unresolved":
        facts = _ts_rows(("registry", "variable", 1, 3))
        facts["after"]["dynamic_dependency_possible"] = True
        return planner.analyze_change_set(
            [
                {
                    "path": "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
                    "before": "export const registry = {}\n",
                    "after": "export const registry = loadDynamicRegistry()\n",
                    "ts_facts": facts,
                }
            ],
            base=base,
            head=head,
        )
    if case_id == "contract-field-rename-delete":
        before = _ts_rows(("old_search_field", "field", 1, 1))
        after = _ts_rows(("new_search_field", "field", 1, 1))
        type_facts = _ts_rows(("SearchName", "type", 1, 1))
        return planner.analyze_change_set(
            [
                {
                    "path": "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "before": "export interface Search { old_search_field?: string }\n",
                    "after": "export interface Search { new_search_field?: string }\n",
                    "ts_facts": {"before": before["before"], "after": after["after"]},
                },
                {
                    "path": "frontend/apps/web/src/app/contracts/v2/types.ts",
                    "before": "export type SearchName = 'old_search_field'\n",
                    "after": "export type SearchName = 'new_search_field'\n",
                    "ts_facts": type_facts,
                },
            ],
            base=base,
            head=head,
        )
    if case_id == "acl-record-rule-change":
        return planner.analyze_change_set(
            [
                {
                    "path": "addons/smart_construction_core/security/ir.model.access.csv",
                    "before": "id,name,model_id:id,group_id:id,perm_read\n",
                    "after": (
                        "id,name,model_id:id,group_id:id,perm_read\n"
                        "access_project_user,project user,model_project_project,"
                        "group_project_user,1\n"
                    ),
                },
                {
                    "path": "addons/smart_construction_core/security/sc_record_rules.xml",
                    "before": "<odoo><data /></odoo>\n",
                    "after": (
                        "<odoo><data><record id='rule_project' "
                        "model='ir.rule'><field name='model_id' "
                        "ref='model_project_project'/></record></data></odoo>\n"
                    ),
                },
            ],
            base=base,
            head=head,
        )
    if case_id == "mixed-business-outcome":
        decode = _ts_rows(("decode", "function", 1, 4))
        registry = _ts_rows(("professionalComponentRegistry", "variable", 1, 3))
        page = _ts_rows(("ActionView", "class", 1, 12))
        return planner.analyze_change_set(
            [
                {
                    "path": "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "before": "export function decode(value: unknown) { return value }\n",
                    "after": "export function decode(value: unknown) { return value ?? {} }\n",
                    "ts_facts": decode,
                },
                {
                    "path": "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts",
                    "before": "export const professionalComponentRegistry = {}\n",
                    "after": "export const professionalComponentRegistry = { list: {} }\n",
                    "ts_facts": registry,
                },
                {
                    "path": "frontend/apps/web/src/views/ActionView.vue",
                    "before": "<template><main /></template>\n",
                    "after": "<template><main><section /></main></template>\n",
                    "ts_facts": page,
                },
                {
                    "path": "addons/smart_construction_core/models/project.py",
                    "before": "from odoo import models, fields\nclass Project(models.Model):\n    state = fields.Char()\n",
                    "after": (
                        "from odoo import models, fields\n"
                        "class Project(models.Model):\n"
                        "    state = fields.Char()\n"
                        "    def action_approve(self):\n"
                        "        self.write({'state': 'approved'})\n"
                    ),
                },
            ],
            base=base,
            head=head,
        )
    if case_id == "incorrect-evidence-reuse":
        facts = _ts_rows(("decode", "function", 1, 3))
        current = planner.analyze_change_set(
            [
                {
                    "path": "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "before": "export function decode(value: unknown) { return value }\n",
                    "after": "export function decode(value: unknown) { return value ?? {} }\n",
                    "ts_facts": facts,
                }
            ],
            base=base,
            head=head,
        )
        decision = current["decisions"][0]
        evidence = {
            "checks": {
                decision["check_id"]: {
                    "status": "passed",
                    "input_fingerprint": decision["input_fingerprint"],
                    "assertion_closure": True,
                    "environment_identity": current["environment_identity"],
                }
            }
        }
        changed = planner.analyze_change_set(
            [
                {
                    "path": "frontend/apps/web/src/app/contracts/v2/schema.ts",
                    "before": "export function decode(value: unknown) { return value }\n",
                    "after": "export function decode(value: unknown) { return value ?? { changed: true } }\n",
                    "ts_facts": facts,
                }
            ],
            base=base,
            head=head,
            evidence=evidence,
        )
        changed["evidence_reuse_check"] = {
            "stale_fingerprint_reused": any(
                item["decision"] == "REUSE" for item in changed["decisions"]
            )
        }
        return changed
    raise ValueError(f"unsupported synthetic acceptance case: {case_id}")


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case["id"])
    kind = str(case["replay_kind"])
    if kind == "historical-candidate":
        plan = historical_plan(case)
        observed_paths = _historical_paths(
            str(case["sample"]["commit"]),
            list(case["sample"]["paths"]),
        )
    else:
        plan = synthetic_plan(case_id)
        observed_paths = list(case["sample"]["paths"])
    legacy_targets = select_targets(observed_paths)
    semantic_checks = [check["id"] for check in plan.get("checks", [])]
    actual_layers = {
        obligation["layer"] for obligation in plan.get("obligations", [])
    }
    expected_layers = set(case["expected_layers"])
    if expected_layers == {"UNKNOWN"}:
        missing_layers: list[str] = []
        unexpected_layers: list[str] = []
        status_ok = plan["status"] == "blocked" and bool(plan["unknowns"])
    else:
        expected_product = expected_layers & PRODUCT_LAYERS
        actual_product = actual_layers & PRODUCT_LAYERS
        missing_layers = sorted(expected_product - actual_product)
        unexpected_layers = sorted(actual_product - expected_product)
        status_ok = plan["status"] in {"planned", "passed"}
    actual_obligations = {
        obligation["id"] for obligation in plan.get("obligations", [])
    }
    expected_obligations = set(case.get("expected_obligation_ids") or [])
    missing_obligations = sorted(expected_obligations - actual_obligations)
    actual_classes = {
        check_class
        for check in plan.get("checks", [])
        for check_class in check.get("classes", [])
    }
    missing_classes = sorted(set(case.get("selected_check_classes", [])) - actual_classes)
    assertion_closure = bool(
        (plan.get("coverage") or {}).get("assertion_closure", False)
    )
    evidence_reuse_error = bool(
        (plan.get("evidence_reuse_check") or {}).get("stale_fingerprint_reused", False)
    )
    false_negative = bool(
        missing_layers
        or missing_obligations
        or missing_classes
        or not status_ok
        or (plan["status"] == "planned" and not assertion_closure)
    )
    passed = not false_negative and not evidence_reuse_error
    return {
        "id": case_id,
        "replay_kind": kind,
        "status": "pass" if passed else "fail",
        "planner_status": plan["status"],
        "expected_layers": sorted(expected_layers),
        "actual_layers": sorted(actual_layers),
        "missing_layers": missing_layers,
        "unexpected_product_layers": unexpected_layers,
        "expected_obligations": sorted(expected_obligations),
        "actual_obligations": sorted(actual_obligations),
        "missing_obligations": missing_obligations,
        "missing_check_classes": missing_classes,
        "assertion_closure": assertion_closure,
        "unknowns": plan.get("unknowns", []),
        "false_negative": false_negative,
        "evidence_reuse_error": evidence_reuse_error,
        "dual_run_observation": {
            "current_path_router_targets": legacy_targets,
            "semantic_check_ids": semantic_checks,
            "equal_target_identity": False,
            "note": (
                "Target identity is intentionally different: path targets are execution "
                "units while semantic checks are assertion-covering units. This "
                "observation is not a cutover proof."
            ),
        },
    }


def run_matrix() -> dict[str, Any]:
    matrix = impact_analysis_acceptance_matrix()
    results = [evaluate_case(case) for case in matrix["cases"]]
    required_obligation_count = sum(
        len(case.get("expected_obligation_ids") or [])
        for case in matrix["cases"]
    )
    covered_obligation_count = sum(
        len(set(case.get("expected_obligation_ids") or []) - set(result["missing_obligations"]))
        for case, result in zip(matrix["cases"], results)
    )
    metrics = {
        "false_negative": sum(result["false_negative"] for result in results),
        "evidence_reuse_error": sum(result["evidence_reuse_error"] for result in results),
        "false_positive_product_layer": sum(
            bool(result["unexpected_product_layers"]) for result in results
        ),
        "obligation_coverage": (
            covered_obligation_count / required_obligation_count
            if required_obligation_count
            else 1.0
        ),
        "unknown_obligations": sum(bool(result["unknowns"]) and result["id"] != "dynamic-consumer-unresolved" for result in results),
        "cases": len(results),
        "passed_cases": sum(result["status"] == "pass" for result in results),
    }
    matrix_complete = (
        metrics["false_negative"] == 0
        and metrics["evidence_reuse_error"] == 0
        and metrics["obligation_coverage"] == 1.0
        and metrics["unknown_obligations"] == 0
        and metrics["passed_cases"] == metrics["cases"]
    )
    return {
        "schema": "change_impact_verification.acceptance_results.v1",
        "mode": "offline-shadow-replay",
        "planner_schema": "change_impact_plan.v2",
        "input_fingerprint": _input_fingerprint(),
        "input_paths": list(INPUT_PATHS),
        "matrix_conformance_complete": matrix_complete,
        "cutover_eligible": False,
        "cutover_blockers": [
            "required-gate dual-run has not been approved",
            "independent review has not approved cutover",
        ],
        "cutover_note": (
            "Matrix conformance is necessary but not sufficient. "
            "Required-gate cutover still needs dual-run and independent review."
        ),
        "metrics": metrics,
        "cases": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    result = run_matrix()
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if not result["matrix_conformance_complete"]:
        return 1
    if args.check:
        if not args.check.is_file() or args.check.read_text(encoding="utf-8") != text:
            print(f"acceptance result is stale: {args.check}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
