#!/usr/bin/env python3
"""Systemic evidence reuse for declaration-driven checks.

Any governed check whose surface is a set of declared units (menu entries,
roles, pages, viewports, records) declares those units with an input
fingerprint.  This engine owns the reuse decision for every such check:

* a unit is reusable only when its fingerprint is unchanged;
* a changed or never-recorded unit is affected and must be executed;
* a check may never report a unit as covered that it did not execute.

The engine is intentionally check-agnostic and language-agnostic: adapters emit
a units document, the engine plans and records.  That keeps one reuse authority
instead of one bespoke cache per check.  It performs no IO beyond reading and
writing the units document and the ledger, and it never executes a check.

Units document (``evidence_scope.units.v1``)::

    {
      "schema": "evidence_scope.units.v1",
      "check": "verify.frontend.business_entry.matrix.browser",
      "identity": {"base_url": ..., "database": ..., "served_revision": ...},
      "units": [{"id": "<menu_xmlid>", "fingerprint": "<sha256>", "required": true}]
    }

Ledger (``evidence_scope.ledger.v1``) lives under ``.runtime/evidence-scope``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS_SCHEMA = "evidence_scope.units.v1"
LEDGER_SCHEMA = "evidence_scope.ledger.v1"
DEFAULT_LEDGER_DIR = ROOT / ".runtime" / "evidence-scope"
# Only these recorded outcomes may be carried forward. Anything else stays out of
# the reusable set so a failing unit is never silently reused, and never blindly
# retried either: it is reported as blocked until its inputs change or its
# recovery is proven.
SUCCESS_STATUSES = frozenset({"passed", "checked", "declared", "reused"})


class ScopeError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ScopeError(message)


def load_units(path: Path) -> dict:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(document.get("schema") == UNITS_SCHEMA, f"{path}: unexpected schema {document.get('schema')!r}")
    check = str(document.get("check") or "")
    _require(bool(check), f"{path}: check id is required")
    units = document.get("units")
    _require(isinstance(units, list) and bool(units), f"{path}: at least one unit is required")
    identifiers: set[str] = set()
    for unit in units:
        _require(isinstance(unit, dict), f"{path}: every unit must be an object")
        identifier = str(unit.get("id") or "")
        _require(bool(identifier), f"{path}: every unit needs a non-empty id")
        _require(identifier not in identifiers, f"{path}: duplicate unit id {identifier!r}")
        identifiers.add(identifier)
        fingerprint = str(unit.get("fingerprint") or "")
        _require(bool(fingerprint), f"{path}: unit {identifier!r} needs a fingerprint")
    document["units"] = [
        {"id": str(unit["id"]), "fingerprint": str(unit["fingerprint"]), "required": bool(unit.get("required", True))}
        for unit in units
    ]
    return document


def units_digest(document: dict) -> str:
    return hashlib.sha256(_canonical_units(document).encode("utf-8")).hexdigest()


def unit_ids(document: dict) -> list[str]:
    return sorted(str(unit["id"]) for unit in document["units"])


def _canonical_units(document: dict) -> str:
    canonical = json.dumps(
        {
            "check": document.get("check"),
            "identity": document.get("identity") or {},
            "units": sorted(
                ({"id": unit["id"], "fingerprint": unit["fingerprint"]} for unit in document["units"]),
                key=lambda item: item["id"],
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return canonical


def ledger_path(check: str, override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)
    safe = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in check)
    return DEFAULT_LEDGER_DIR / f"{safe}.json"


def load_ledger(path: Path, check: str) -> dict:
    if not path.exists():
        return {"schema": LEDGER_SCHEMA, "check": check, "identity": {}, "units": {}, "runs": []}
    document = json.loads(path.read_text(encoding="utf-8"))
    _require(document.get("schema") == LEDGER_SCHEMA, f"{path}: unexpected ledger schema")
    _require(document.get("check") == check, f"{path}: ledger belongs to {document.get('check')!r}, not {check!r}")
    document.setdefault("identity", {})
    document.setdefault("units", {})
    document.setdefault("runs", [])
    return document


def save_ledger(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def plan_units(document: dict, ledger: dict) -> dict:
    recorded = ledger.get("units") or {}
    affected: list[str] = []
    reusable: list[str] = []
    fresh: list[str] = []
    stale: list[str] = []
    blocked: list[str] = []
    identity_changed = bool(ledger.get("identity")) and (ledger.get("identity") != (document.get("identity") or {}))
    for unit in document["units"]:
        entry = recorded.get(unit["id"])
        if entry is None:
            fresh.append(unit["id"])
            affected.append(unit["id"])
            continue
        if str(entry.get("fingerprint")) != unit["fingerprint"] or identity_changed:
            stale.append(unit["id"])
            affected.append(unit["id"])
            continue
        if str(entry.get("status") or "") in SUCCESS_STATUSES:
            reusable.append(unit["id"])
        else:
            blocked.append(unit["id"])
    return {
        "schema": "evidence_scope.plan.v1",
        "check": document["check"],
        "identity": document.get("identity") or {},
        "identity_changed": identity_changed,
        "units_total": len(document["units"]),
        "affected": affected,
        "reusable": reusable,
        "never_recorded": fresh,
        "stale": stale,
        "blocked": blocked,
        "execution_required": bool(affected),
        "units_digest": units_digest(document),
    }


def record_units(document: dict, ledger: dict, results: dict, *, source: str = "") -> dict:
    """Fold an executed run into the ledger.

    Recording is the only place a unit may become reusable, so it enforces the
    reuse-first contract: the run must state exactly which units it executed,
    those units must belong to the declared set with matching fingerprints, and
    every unit the plan marked as affected must actually have been executed.
    A run can therefore never claim coverage it did not produce, and it can
    never skip the work its own plan required.
    """
    _require(results.get("schema") == "evidence_scope.results.v1", "results document schema mismatch")
    executed = results.get("executed_units")
    _require(isinstance(executed, list) and bool(executed), "results document must declare executed_units")
    declared = {unit["id"]: unit["fingerprint"] for unit in document["units"]}
    executed_ids: list[str] = []
    for unit in executed:
        _require(isinstance(unit, dict), "executed_units entries must be objects")
        identifier = str(unit.get("id") or "")
        _require(identifier in declared, f"results executed a unit outside the declared set: {identifier!r}")
        _require(
            str(unit.get("fingerprint") or "") == declared[identifier],
            f"executed unit {identifier!r} does not carry the fingerprint of the declared unit it claims",
        )
        _require(identifier not in executed_ids, f"executed unit {identifier!r} is duplicated")
        executed_ids.append(identifier)
    statuses = results.get("results")
    _require(isinstance(statuses, dict) and bool(statuses), "results document carries no per-unit result")
    _require(
        sorted(statuses) == sorted(executed_ids),
        "results must carry exactly one status per executed unit (no unexecuted unit may be recorded)",
    )
    planned_affected = [str(identifier) for identifier in (results.get("planned_affected") or [])]
    missing = [identifier for identifier in planned_affected if identifier not in set(executed_ids)]
    _require(not missing, f"the plan required these units to be executed but the run skipped them: {missing[:5]}")
    recorded = ledger.setdefault("units", {})
    fingerprints = {unit["id"]: unit["fingerprint"] for unit in document["units"]}
    stamp = datetime.now(timezone.utc).isoformat()
    for identifier, status in statuses.items():
        recorded[identifier] = {
            "fingerprint": fingerprints[identifier],
            "status": str(status),
            "recorded_at": stamp,
            "source": source or str(results.get("source") or ""),
        }
    ledger["identity"] = document.get("identity") or {}
    ledger.setdefault("runs", []).append(
        {
            "recorded_at": stamp,
            "units": sorted(statuses),
            "planned_affected": sorted(planned_affected),
            "source": source or str(results.get("source") or ""),
        }
    )
    return ledger


def covered_units(ledger: dict, document: dict) -> dict:
    """Per-unit coverage state for a declared surface, without executing anything."""
    recorded = ledger.get("units") or {}
    identity_changed = bool(ledger.get("identity")) and (ledger.get("identity") != (document.get("identity") or {}))
    report: dict[str, str] = {}
    for unit in document["units"]:
        entry = recorded.get(unit["id"])
        if entry is None:
            report[unit["id"]] = "never_recorded"
        elif identity_changed or str(entry.get("fingerprint")) != unit["fingerprint"]:
            report[unit["id"]] = "stale"
        else:
            report[unit["id"]] = str(entry.get("status") or "recorded")
    return report


def select_units(document: dict, plan: dict, requested: list[str], *, reason: str = "") -> dict:
    """Decide what a verification entry is allowed to execute.

    Reuse comes first: the affected set is always executed, and an already
    covered unit may only be re-executed when the caller states a justification.
    Requesting a covered unit without one is a fail-closed denial, so a batch
    entry can never silently turn a targeted rerun into re-collecting evidence
    that is already bound to unchanged inputs.
    """
    declared = {unit["id"] for unit in document["units"]}
    unknown = sorted({str(identifier) for identifier in requested} - declared)
    _require(not unknown, f"requested units are not declared in this surface: {unknown[:5]}")
    affected = [str(identifier) for identifier in plan["affected"]]
    reusable = {str(identifier) for identifier in plan["reusable"]}
    blocked = {str(identifier) for identifier in plan.get("blocked") or []}
    requested = [str(identifier) for identifier in requested]
    reevidence = sorted(set(requested) & reusable)
    _require(
        not reevidence or bool(str(reason).strip()),
        "these units are already covered with unchanged inputs and may only be re-executed "
        f"with an explicit justification: {reevidence[:5]}",
    )
    retry = sorted(set(requested) & blocked)
    _require(
        not retry or bool(str(reason).strip()),
        "these units failed on unchanged inputs and may only be retried once the owning input "
        f"changed or the recovery is stated: {retry[:5]}",
    )
    execute = affected + [identifier for identifier in requested if identifier not in set(affected)]
    return {
        "schema": "evidence_scope.selection.v1",
        "check": document["check"],
        "execute": execute,
        "affected": affected,
        "requested": requested,
        "reused": sorted(reusable),
        "re_evidenced": reevidence,
        "re_evidence_reason": str(reason).strip(),
        "reuse_first": True,
    }


def _emit(payload: dict, json_out: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(text + "\n", encoding="utf-8")
    print(text)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="evidence-scope plan/record")
    parser.add_argument("operation", choices=("plan", "select", "record", "status"))
    parser.add_argument("--check")
    parser.add_argument("--units", required=True)
    parser.add_argument("--results")
    parser.add_argument("--ledger")
    parser.add_argument("--json-out")
    parser.add_argument("--requested", default="", help="comma separated unit ids the caller wants re-executed")
    parser.add_argument("--reverify-reason", default="", help="justification required to re-execute covered units")
    parser.add_argument("--require-complete", action="store_true",
                        help="fail when any declared unit still needs execution after planning")
    parser.add_argument("--source", default="",
                        help="override the recorded provenance recorded for this run")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    units_path = Path(args.units)
    document = load_units(units_path)
    if args.check:
        _require(args.check == document["check"],
                 f"--check {args.check!r} does not match the units document check {document['check']!r}")
    ledger_file = ledger_path(document["check"], Path(args.ledger) if args.ledger else None)
    ledger = load_ledger(ledger_file, document["check"])
    json_out = Path(args.json_out) if args.json_out else None

    if args.operation == "plan":
        payload = plan_units(document, ledger)
        _emit(payload, json_out)
        if args.require_complete and payload["execution_required"]:
            return 3
        return 0

    if args.operation == "status":
        report = covered_units(ledger, document)
        counts: dict[str, int] = {}
        for state in report.values():
            counts[state] = counts.get(state, 0) + 1
        _emit({"schema": "evidence_scope.status.v1", "check": document["check"], "ledger": str(ledger_file),
               "state_counts": counts, "units": report}, json_out)
        return 0

    if args.operation == "select":
        requested = [value.strip() for value in str(args.requested or "").split(",") if value.strip()]
        plan = plan_units(document, ledger)
        payload = select_units(document, plan, requested, reason=args.reverify_reason)
        _emit(payload, json_out)
        return 0

    _require(bool(args.results), "record requires --results")
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    ledger = record_units(document, ledger, results, source=args.source)
    save_ledger(ledger_file, ledger)
    _emit({"schema": "evidence_scope.record.v1", "check": document["check"], "ledger": str(ledger_file),
           "recorded": sorted(results["results"])}, json_out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ScopeError as exc:
        print(f"[evidence-scope] DENY {exc}", file=sys.stderr)
        raise SystemExit(2)
