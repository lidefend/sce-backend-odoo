#!/usr/bin/env python3
"""Fail-closed consistency guard for the FE-CONTRACT-FIDELITY-02 plan.

This guard validates planning artifacts only. It does not implement or claim the
future Contract Fidelity Guard, and it does not inspect product behavior.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = Path("docs/audit/fe_contract_fidelity_01/matrix.json")
PLAN_PATH = Path("docs/architecture/fe_contract_fidelity_02/remediation_plan.json")
GUARD_PATH = Path("docs/architecture/fe_contract_fidelity_02/guard_catalog.json")

BRANCHES = {
    "sufficient": "unlock",
    "not_applicable": "unlock",
    "contract_gap": "redirect_to_p0_producer",
}


def read_json(root: Path, relative: Path, errors: list[str]) -> dict[str, Any]:
    path = root / relative
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{relative}: unreadable JSON ({exc})")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{relative}: root must be an object")
        return {}
    return data


def audit_not_verified(matrix: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(surface.get("id")), str(semantic))
        for surface in matrix.get("surfaces", [])
        for semantic in surface.get("statuses", {}).get("NOT_VERIFIED", [])
    }


def unique_values(items: list[Any], label: str, errors: list[str]) -> list[str]:
    values = [str(item) for item in items]
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        errors.append(f"{label}: duplicate values {duplicates}")
    return values


def check_dependency_graph(
    plan: dict[str, Any],
    batches: dict[str, dict[str, Any]],
    gap_ids: set[str],
    errors: list[str],
) -> None:
    edges = plan.get("dependency_edges", [])
    if not isinstance(edges, list):
        errors.append("dependency_edges must be a list")
        return
    edge_ids = unique_values([edge.get("id") for edge in edges], "dependency_edges.id", errors)
    if any(not edge_id or edge_id == "None" for edge_id in edge_ids):
        errors.append("dependency_edges: every edge requires an id")

    node_ids = set(batches) | gap_ids
    pairs: set[tuple[str, str]] = set()
    adjacency = {node: set() for node in node_ids}
    indegree = {node: 0 for node in node_ids}
    for edge in edges:
        source = str(edge.get("from") or "")
        target = str(edge.get("to") or "")
        kind = str(edge.get("kind") or "")
        if source not in node_ids or target not in batches:
            errors.append(f"dependency edge {edge.get('id')}: invalid endpoints {source!r}->{target!r}")
            continue
        if (source, target) in pairs:
            errors.append(f"dependency edge duplicate: {source}->{target}")
        pairs.add((source, target))
        if kind == "contract_gate":
            if source not in gap_ids:
                errors.append(f"dependency edge {edge.get('id')}: contract_gate source must be a gap probe")
            if edge.get("branches") != BRANCHES:
                errors.append(f"dependency edge {edge.get('id')}: contract_gate branches must be exact")
        elif kind != "batch":
            errors.append(f"dependency edge {edge.get('id')}: kind must be batch or contract_gate")
        if target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1

    for batch_id, batch in batches.items():
        for dependency in batch.get("depends_on", []):
            if (str(dependency), batch_id) not in pairs:
                errors.append(
                    f"{batch_id}: depends_on {dependency} without a matching dependency edge"
                )
    for source, target in pairs:
        if source not in batches[target].get("depends_on", []):
            errors.append(
                f"dependency edge {source}->{target}: missing from {target}.depends_on"
            )

    queue = [node for node, degree in indegree.items() if degree == 0]
    visited: list[str] = []
    while queue:
        node = queue.pop()
        visited.append(node)
        for target in adjacency[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(visited) != len(node_ids):
        errors.append("dependency_edges: graph contains a cycle")


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    matrix = read_json(root, MATRIX_PATH, errors)
    plan = read_json(root, PLAN_PATH, errors)
    guard = read_json(root, GUARD_PATH, errors)
    if errors:
        return errors

    if plan.get("status") != "planning_only" or plan.get("product_fix_authorized") is not False:
        errors.append("plan must remain planning_only with product_fix_authorized=false")
    if guard.get("status") != "planned_not_implemented" or guard.get("not_a_runtime") is not True:
        errors.append("guard catalog must remain planned_not_implemented and not_a_runtime")

    probes = plan.get("contract_gap_probes", [])
    probe_ids = unique_values([probe.get("id") for probe in probes], "contract_gap_probes.id", errors)
    if any(not probe_id or probe_id == "None" for probe_id in probe_ids):
        errors.append("contract_gap_probes: every probe requires an id")
    if set(probe_ids) != {f"CFG-GAP-{index:02d}" for index in range(1, 8)}:
        errors.append("contract_gap_probes must be exactly CFG-GAP-01..07")

    cells = plan.get("not_verified_cells", [])
    cell_ids = unique_values([cell.get("id") for cell in cells], "not_verified_cells.id", errors)
    if any(not cell_id or cell_id == "None" for cell_id in cell_ids):
        errors.append("not_verified_cells: every cell requires an id")
    plan_pairs = {(str(cell.get("surface")), str(cell.get("semantic"))) for cell in cells}
    audit_pairs = audit_not_verified(matrix)
    if plan_pairs != audit_pairs:
        errors.append(
            "NOT_VERIFIED matrix mismatch: "
            f"audit_only={sorted(audit_pairs - plan_pairs)} "
            f"plan_only={sorted(plan_pairs - audit_pairs)}"
        )
    if len(cells) != 19 or len(cell_ids) != 19:
        errors.append(f"not_verified_cells must contain 19 unique cells, got {len(cells)}")

    cell_by_id = {str(cell.get("id")): cell for cell in cells}
    expected_responsibility = {"NV-11": "CFG-GAP-04", "NV-15": "CFG-GAP-07"}
    for cell_id, gap_id in expected_responsibility.items():
        if cell_by_id.get(cell_id, {}).get("gap_probe") != gap_id:
            errors.append(f"{cell_id}: gap_probe must be {gap_id}")

    expected_blocks: dict[str, set[str]] = {gap_id: set() for gap_id in probe_ids}
    for cell_id, cell in cell_by_id.items():
        gap_id = str(cell.get("gap_probe") or "")
        if gap_id not in expected_blocks:
            errors.append(f"{cell_id}: unknown gap_probe {gap_id!r}")
            continue
        expected_blocks[gap_id].add(cell_id)
    for probe in probes:
        gap_id = str(probe.get("id") or "")
        blocks = probe.get("blocks", [])
        if not isinstance(blocks, list):
            errors.append(f"{gap_id}: blocks must be a list")
            continue
        unique_values(blocks, f"{gap_id}.blocks", errors)
        actual_cells = {str(item) for item in blocks if str(item).startswith("NV-")}
        if actual_cells != expected_blocks.get(gap_id, set()):
            errors.append(
                f"{gap_id}: NV blocks mismatch "
                f"expected={sorted(expected_blocks.get(gap_id, set()))} "
                f"actual={sorted(actual_cells)}"
            )
        if probe.get("fallback_allowed") is not False:
            errors.append(f"{gap_id}: frontend fallback must remain forbidden")

    policy = plan.get("gap_resolution_policy", {})
    policy_branches = policy.get("branches", {}) if isinstance(policy, dict) else {}
    if set(policy_branches) != set(BRANCHES):
        errors.append("gap_resolution_policy must declare sufficient/not_applicable/contract_gap")
    contract_gap = policy_branches.get("contract_gap", {})
    if not isinstance(contract_gap, dict):
        errors.append("gap_resolution_policy.contract_gap must be an object")
    else:
        if contract_gap.get("frontend_fallback_forbidden") is not True:
            errors.append("contract_gap must forbid frontend fallback")
        if contract_gap.get("dependent_frontend_batch_locked") is not True:
            errors.append("contract_gap must lock the dependent frontend batch")
        required = set(contract_gap.get("required_before_frontend_unlock", []))
        expected = {
            "owning P0 producer declaration",
            "consumer contract decoding",
            "independent review",
            "registered verification",
        }
        if required != expected:
            errors.append("contract_gap unlock requirements are incomplete")

    batches = plan.get("batches", [])
    batch_ids = unique_values([batch.get("id") for batch in batches], "batches.id", errors)
    batch_by_id = {str(batch.get("id")): batch for batch in batches}
    if batch_by_id.get("FCF-02-1", {}).get("depends_on") != []:
        errors.append("FCF-02-1 must remain independently startable")
    required_gap_dependencies = {
        "FCF-02-2": {"CFG-GAP-02", "CFG-GAP-04", "CFG-GAP-05"},
        "FCF-02-3": {"CFG-GAP-03"},
        "FCF-02-4": set(probe_ids),
    }
    for batch_id, required in required_gap_dependencies.items():
        present = set(batch_by_id.get(batch_id, {}).get("depends_on", []))
        if not required <= present:
            errors.append(f"{batch_id}: missing gap dependencies {sorted(required - present)}")
    if "NV-11" in batch_by_id.get("FCF-02-3", {}).get("findings", []):
        errors.append("FCF-02-3 must not own My Work attachment verification")
    if "NV-15" in batch_by_id.get("FCF-02-3", {}).get("findings", []):
        errors.append("FCF-02-3 must not own Dialog duration verification")

    audit_findings = {
        str(finding.get("id"))
        for finding in matrix.get("findings", [])
        if str(finding.get("id", "")).startswith("FCF-")
    }
    planned_findings = {
        str(finding)
        for batch in batches
        for finding in batch.get("findings", [])
        if str(finding).startswith("FCF-")
    }
    if planned_findings != audit_findings:
        errors.append(
            "FCF finding coverage mismatch: "
            f"missing={sorted(audit_findings - planned_findings)} "
            f"unknown={sorted(planned_findings - audit_findings)}"
        )

    check_dependency_graph(plan, batch_by_id, set(probe_ids), errors)

    carrier_requirements = guard.get("semantic_carrier_requirements", [])
    carrier_ids = unique_values(
        [item.get("id") for item in carrier_requirements],
        "semantic_carrier_requirements.id",
        errors,
    )
    expected_carriers = {f"CARRIER-{index:02d}" for index in range(1, 7)}
    if set(carrier_ids) != expected_carriers:
        errors.append("semantic carrier requirements must be exactly CARRIER-01..06")
    design_gate = set(batch_by_id.get("FCF-02-2", {}).get("design_gate", []))
    expected_design_gate = {
        "raw_value_type_preservation",
        "complete_field_descriptor",
        "verifiable_relation_identity",
        "complete_attachment_identity_and_actions",
        "page_block_action_and_feedback_identity",
        "authoritative_currency_and_timezone",
        "display_write_separation",
    }
    if design_gate != expected_design_gate:
        errors.append("FCF-02-2 design_gate is incomplete or contains unknown criteria")

    rules = guard.get("rules", [])
    rule_ids = unique_values([rule.get("id") for rule in rules], "rules.id", errors)
    rule_by_id = {str(rule.get("id")): rule for rule in rules}
    if set(rule_ids) != {f"CFG-{index:03d}" for index in range(1, 12)}:
        errors.append("guard rules must be exactly CFG-001..011")
    for phase in guard.get("rollout", []):
        unknown = set(phase.get("rules", [])) - set(rule_ids)
        if unknown:
            errors.append(f"guard rollout {phase.get('phase')}: unknown rules {sorted(unknown)}")

    numeric_rule = rule_by_id.get("CFG-003", {})
    numeric_text = " ".join(
        [
            str(numeric_rule.get("pass_condition", "")),
            *map(str, numeric_rule.get("negative_cases", [])),
        ]
    ).lower()
    for token in ("never clamps", "rounds", "125.75", "12.345", "raw count -1"):
        if token not in numeric_text:
            errors.append(f"CFG-003 must explicitly cover {token!r}")

    page_rule = rule_by_id.get("CFG-011", {})
    required_page_semantics = {
        "action target",
        "permission result",
        "disabled reason",
        "error reason code",
        "message",
        "trace identity",
    }
    if set(page_rule.get("required_semantics", [])) != required_page_semantics:
        errors.append("CFG-011 Page Block action/feedback semantics are incomplete")
    if page_rule.get("enforce_from_batch") != "FCF-02-2":
        errors.append("CFG-011 must be enforced from FCF-02-2")
    if "FCF-03" not in page_rule.get("maps_findings", []):
        errors.append("CFG-011 must map to FCF-03")

    return errors


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print(f"CONTRACT_FIDELITY_PLAN: FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "CONTRACT_FIDELITY_PLAN: PASS "
        "not_verified=19 gap_probes=7 guard_rules=11 dependency_graph=consistent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
