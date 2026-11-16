#!/usr/bin/env python3
"""Obligation-level stable-baseline and evidence coordination.

The coordinator consumes the planner's assertion closure and existing
authorities. It does not execute checks and does not weaken any required gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


BASELINE_SCHEMA = "change_impact_verification.baseline.v1"
COORDINATION_SCHEMA = "change_impact_verification.coordination.v1"
FULL_SHA = frozenset("0123456789abcdef")


class BaselineError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BaselineError(message)


def _digest(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _full_sha(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 40 and set(text) <= FULL_SHA


def _receipt_matches(
    receipt: dict[str, Any],
    decision: dict[str, Any],
    environment_identity: dict[str, Any],
) -> bool:
    return (
        str(receipt.get("status") or "") in {"passed", "checked"}
        and receipt.get("input_fingerprint") == decision.get("input_fingerprint")
        and receipt.get("assertion_closure") is True
        and receipt.get("environment_identity") == environment_identity
        and str(receipt.get("evidence_authority") or "")
        in {"exact_run", "authorized_reuse"}
        and bool(receipt.get("evidence_sha256"))
    )


def _obligations_by_check(plan: dict[str, Any]) -> dict[str, list[str]]:
    return {
        str(row["check_id"]): sorted(row.get("obligations") or [])
        for row in (plan.get("trace") or {}).get("reverse") or []
    }


def build_baseline(
    plan: dict[str, Any],
    *,
    receipts: dict[str, dict[str, Any]],
    source_head: str,
    source_tree: str,
    merged_main_head: str,
    independent_review: str,
    remote_checks: str,
    main_tree_equivalent: bool,
) -> dict[str, Any]:
    _require(_full_sha(source_head), "source_head must be a full SHA")
    _require(_full_sha(source_tree), "source_tree must be a full tree SHA")
    _require(_full_sha(merged_main_head), "merged_main_head must be a full SHA")
    decisions = {row["check_id"]: row for row in plan.get("decisions") or []}
    obligations_by_check = _obligations_by_check(plan)
    proofs = []
    for check in plan.get("checks") or []:
        check_id = str(check["id"])
        decision = decisions.get(check_id) or {}
        receipt = receipts.get(check_id) or {}
        _require(
            _receipt_matches(
                receipt,
                decision,
                plan.get("environment_identity") or {},
            ),
            f"{check_id}: current receipt is not bound to the planned inputs/assertions/environment",
        )
        proofs.append(
            {
                "obligation_ids": obligations_by_check.get(check_id, []),
                "check_id": check_id,
                "input_fingerprint": decision["input_fingerprint"],
                "assertion_set_sha256": _digest(check.get("covered_assertions") or []),
                "toolchain_sha256": _digest(
                    {
                        "entrypoint": check.get("entrypoint"),
                        "kind": check.get("kind"),
                        "evidence_kind": check.get("evidence_kind"),
                    }
                ),
                "environment_identity": plan.get("environment_identity") or {},
                "evidence_authority": receipt["evidence_authority"],
                "evidence_sha256": receipt["evidence_sha256"],
            }
        )
    required = {
        obligation["id"] for obligation in plan.get("obligations") or []
    }
    covered = {
        obligation
        for proof in proofs
        for obligation in proof["obligation_ids"]
    }
    missing = sorted(required - covered)
    promotion_complete = (
        not missing
        and not plan.get("unknowns")
        and (plan.get("coverage") or {}).get("assertion_closure") is True
        and independent_review == "approved"
        and remote_checks == "passed"
        and main_tree_equivalent is True
    )
    body = {
        "schema": BASELINE_SCHEMA,
        "source": {"head": source_head, "tree": source_tree},
        "base_main": plan.get("identity", {}).get("base"),
        "proofs": sorted(proofs, key=lambda row: row["check_id"]),
        "coverage": {
            "required_obligations": len(required),
            "passed": len(covered),
            "reused": 0,
            "not_applicable": 0,
            "unknown": len(plan.get("unknowns") or []),
            "blocked": len(missing),
        },
        "promotion": {
            "candidate_head": plan.get("identity", {}).get("head"),
            "merged_main_head": merged_main_head,
            "main_tree_equivalent": main_tree_equivalent,
            "independent_review": independent_review,
            "remote_checks": remote_checks,
            "eligible": promotion_complete,
        },
    }
    body["digest"] = _digest(
        {
            "schema": body["schema"],
            "source": body["source"],
            "base_main": body["base_main"],
            "proofs": body["proofs"],
            "coverage": body["coverage"],
            "promotion": body["promotion"],
        }
    )
    return body


def validate_baseline(baseline: dict[str, Any]) -> None:
    _require(baseline.get("schema") == BASELINE_SCHEMA, "baseline schema mismatch")
    source = baseline.get("source") or {}
    _require(_full_sha(source.get("head")), "baseline source head is invalid")
    _require(_full_sha(source.get("tree")), "baseline source tree is invalid")
    _require(
        (baseline.get("promotion") or {}).get("eligible") is True,
        "baseline was not promoted from independently reviewed exact evidence",
    )
    expected = baseline.get("digest")
    actual = _digest(
        {
            "schema": baseline.get("schema"),
            "source": baseline.get("source"),
            "base_main": baseline.get("base_main"),
            "proofs": baseline.get("proofs"),
            "coverage": baseline.get("coverage"),
            "promotion": baseline.get("promotion"),
        }
    )
    _require(expected == actual, "baseline digest mismatch")


def coordinate(
    plan: dict[str, Any],
    baseline: dict[str, Any],
    *,
    receipts: dict[str, dict[str, Any]] | None = None,
    inherited_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Coordinate baseline reuse, current execution, and fail-closed blocking."""

    validate_baseline(baseline)
    receipts = receipts or {}
    decisions = {row["check_id"]: row for row in plan.get("decisions") or []}
    obligations_by_check = _obligations_by_check(plan)
    touched = {
        obligation["id"] for obligation in plan.get("obligations") or []
    }
    baselined = {
        obligation
        for proof in baseline.get("proofs") or []
        for obligation in proof.get("obligation_ids") or []
    }
    if inherited_plan is not None:
        touched.update(
            obligation["id"] for obligation in inherited_plan.get("obligations") or []
        )
        baselined.update(
            obligation["id"]
            for proof in baseline.get("proofs") or []
            for obligation in proof.get("obligation_ids") or []
        )
    required = sorted(baselined | touched)
    states: dict[str, str] = {}
    check_states = []
    covered: set[str] = set()
    reuse_count = 0
    run_count = 0
    for check in plan.get("checks") or []:
        check_id = str(check["id"])
        decision = decisions.get(check_id) or {}
        receipt = receipts.get(check_id) or {}
        obligations = set(obligations_by_check.get(check_id, []))
        if _receipt_matches(
            receipt,
            decision,
            plan.get("environment_identity") or {},
        ):
            state = "passed"
            run_count += 1
            covered.update(obligations)
        elif decision.get("decision") == "REUSE":
            state = "reused"
            reuse_count += 1
            covered.update(obligations)
        else:
            state = "run_required"
        check_states.append(
            {
                "check_id": check_id,
                "state": state,
                "obligation_ids": sorted(obligations),
            }
        )
    baseline_reused: set[str] = set()
    for proof in baseline.get("proofs") or []:
        proof_obligations = set(proof.get("obligation_ids") or [])
        if proof_obligations and proof_obligations <= (baselined - touched):
            baseline_reused.update(proof_obligations)
    covered.update(baseline_reused)
    missing = sorted(set(required) - covered)
    for obligation in required:
        if obligation in missing:
            states[obligation] = "BLOCK"
        elif obligation in baseline_reused:
            states[obligation] = "REUSE"
        else:
            states[obligation] = "PASSED"
    unknowns = list(plan.get("unknowns") or [])
    if inherited_plan is not None:
        unknowns.extend(inherited_plan.get("unknowns") or [])
    ready = (
        not unknowns
        and not missing
        and all(state != "run_required" for state in check_states)
        and bool(required)
    )
    return {
        "schema": COORDINATION_SCHEMA,
        "baseline_digest": baseline["digest"],
        "candidate": plan.get("identity"),
        "required_obligations": required,
        "states": dict(sorted(states.items())),
        "checks": check_states,
        "unknowns": sorted(set(unknowns)),
        "coverage": {
            "required": len(required),
            "covered": len(required) - len(missing),
            "missing": missing,
            "baseline_reused": sorted(baseline_reused),
            "current_execution": run_count,
            "authorized_reuse": reuse_count,
            "ratio": (len(required) - len(missing)) / len(required) if required else 1.0,
        },
        "ready_for_existing_gates": ready,
        "product_checks_executed": run_count,
        "plan_is_not_evidence": True,
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--baseline", type=Path, required=True)
    validate_parser.add_argument("--output", type=Path)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--plan", type=Path, required=True)
    build_parser.add_argument("--receipts", type=Path, required=True)
    build_parser.add_argument("--source-head", required=True)
    build_parser.add_argument("--source-tree", required=True)
    build_parser.add_argument("--merged-main-head", required=True)
    build_parser.add_argument("--independent-review", required=True)
    build_parser.add_argument("--remote-checks", required=True)
    build_parser.add_argument("--main-tree-equivalent", action="store_true")
    build_parser.add_argument("--output", type=Path)

    coordinate_parser = subparsers.add_parser("coordinate")
    coordinate_parser.add_argument("--plan", type=Path, required=True)
    coordinate_parser.add_argument("--baseline", type=Path, required=True)
    coordinate_parser.add_argument("--receipts", type=Path)
    coordinate_parser.add_argument("--inherited-plan", type=Path)
    coordinate_parser.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    if args.operation == "validate":
        document = load_json(args.baseline)
        validate_baseline(document)
        result = {
            "status": "valid",
            "baseline_digest": document["digest"],
            "source": document["source"],
        }
        exit_code = 0
    elif args.operation == "build":
        document = build_baseline(
            load_json(args.plan),
            receipts=load_json(args.receipts),
            source_head=args.source_head,
            source_tree=args.source_tree,
            merged_main_head=args.merged_main_head,
            independent_review=args.independent_review,
            remote_checks=args.remote_checks,
            main_tree_equivalent=args.main_tree_equivalent,
        )
        result = document
        exit_code = 0 if document["promotion"]["eligible"] else 3
    else:
        document = coordinate(
            load_json(args.plan),
            load_json(args.baseline),
            receipts=load_json(args.receipts) if args.receipts else {},
            inherited_plan=load_json(args.inherited_plan) if args.inherited_plan else None,
        )
        result = document
        exit_code = 0 if document["ready_for_existing_gates"] else 3
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaselineError as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
