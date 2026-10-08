#!/usr/bin/env python3
"""Fail-closed consistency guard for the .agent run/goal ledger.

Rule: the ledger must be internally consistent, so "goal and run status are out
of sync" is a mechanically detected defect instead of a recurring manual audit.

* a terminal run (completed/superseded) must not leave a non-terminal goal behind;
* the active-run index must point at an existing, branch-matching, non-terminal run;
* every run record keeps a canonical status and resolvable goal/record paths;
* every goal declares an id, a status and, when it names a run, a resolvable path.

Owner-kept ledger residuals are pinned with their recorded authority. The pins are
ratchets: the on-disk set must equal the pinned set exactly, so a new residual
cannot appear silently and a closed one must be removed here in the same change.
This guard only reads the .agent ledger and never mutates it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

GOALS_DIR = ".agent/goals"
RUNS_DIR = ".agent/runs"
INDEX_PATH = ".agent/active-runs.json"
CONTEXT_PATH = ".agent/context.yaml"
RUN_TEMPLATE_DIR = "template"

CANONICAL_DEFAULT = (
    "planned",
    "active",
    "blocked",
    "verification_pending",
    "completed",
    "superseded",
)
TERMINAL = ("completed", "superseded")

# A terminal run whose goal intentionally stays open. Each entry must carry the
# recorded authority and reason that justify keeping it open. The authority must
# point at an existing recorded decision, so an exception cannot cite fiction.
TERMINAL_MISMATCH_ALLOWLIST: dict[str, dict] = {
    "BACKEND-CONTRACT-SLO-TELEMETRY": {
        "run_status": "completed",
        "goal_status": "active",
        "authority": "docs/ops/iterations/product_delivery_mainline_ledger_closeout_20261008.md#4.2",
        "reason": (
            "delivered via PR #533; owner-gated follow-ups (b-residual runtime attribution "
            "probe, c signature-level supply-chain provenance, e 119 stale-snapshot re-baseline "
            "decision) keep the goal open until the owner closes them"
        ),
    },
    "P4-INCREMENTAL-RESUME": {
        "run_status": "completed",
        "goal_status": "active",
        "authority": "docs/ops/iterations/product_delivery_mainline_ledger_closeout_20261008.md#4.2",
        "reason": (
            "delivered via PR #524 and closed at the run layer; the ledger-closeout ledger keeps "
            "the goal open as a recorded owner-held metadata item (JSON-as-YAML, no schema_version) "
            "pending its own normalisation"
        ),
    },
}

# Non-canonical goal status values that are recorded, owner-owned and intentionally
# not normalised in this batch. The set is a ratchet: it must equal the real
# on-disk set exactly.
RECORDED_NON_CANONICAL: dict[str, dict] = {
    "FORM-PAGE-STRUCTURE-PROFESSIONALIZATION": {
        "status": "verified",
        "owner": (
            "legacy pre-enum value with no run record, kept unchanged by "
            "docs/ops/iterations/product_delivery_mainline_ledger_closeout_20261008.md#4.1; "
            "equivalent to completed, retained until its own retirement"
        ),
    },
    "PAYMENT-REQUEST-GOLDEN-FLOORPLAN": {
        "status": "complete",
        "owner": (
            "owner-pending normalisation recorded in "
            "docs/ops/iterations/product_delivery_mainline_ledger_closeout_20261008.md#4.2"
        ),
    },
}

_ID_RE = re.compile(r"^\s*id:\s*(\S+)\s*$", re.M)
_STATUS_RE = re.compile(r"^\s*status:\s*(\S+)\s*$", re.M)
_RUN_RE = re.compile(r"^\s*run:\s*(\S+)\s*$", re.M)


def canonical_statuses(root: Path = ROOT) -> tuple[str, ...]:
    """Read the canonical run/goal status enum from .agent/context.yaml."""
    try:
        data = yaml.safe_load((root / CONTEXT_PATH).read_text(encoding="utf-8"))
        values = data["run_statuses"]
    except Exception:
        return CANONICAL_DEFAULT
    if isinstance(values, list) and values and all(isinstance(v, str) for v in values):
        return tuple(values)
    return CANONICAL_DEFAULT


def load_goals(root: Path, errors: list[str]) -> dict[str, dict]:
    goals: dict[str, dict] = {}
    directory = root / GOALS_DIR
    if not directory.is_dir():
        errors.append(f"missing goals directory: {GOALS_DIR}")
        return goals
    for path in sorted(directory.glob("*.yaml")):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        parsed: object = None
        try:
            parsed = yaml.safe_load(text)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("goal"), dict):
                raise ValueError("goal document must be a mapping with a 'goal' mapping")
        except Exception as exc:
            first_line = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
            errors.append(f"{relative}: not machine-readable YAML ({first_line})")
            parsed = None
        if isinstance(parsed, dict):
            goal = parsed["goal"]
            gid = goal.get("id")
            status = goal.get("status")
            declared_run = goal.get("run")
        else:
            match = _ID_RE.search(text)
            gid = match.group(1) if match else None
            match = _STATUS_RE.search(text)
            status = match.group(1) if match else None
            match = _RUN_RE.search(text)
            declared_run = match.group(1) if match else None
        if not isinstance(gid, str) or not gid:
            errors.append(f"{relative}: goal is missing an id")
            continue
        if gid in goals:
            errors.append(f"{gid}: duplicate goal id also declared in {goals[gid]['path']}")
            continue
        if not isinstance(status, str) or not status:
            errors.append(f"{gid}: goal is missing a status ({relative})")
            status = None
        if isinstance(declared_run, str) and declared_run and not (root / declared_run).is_file():
            errors.append(f"{gid}: declares run {declared_run} but the record is missing")
        goals[gid] = {"path": relative, "status": status}
    return goals


def load_runs(root: Path, errors: list[str]) -> dict[str, dict]:
    runs: dict[str, dict] = {}
    directory = root / RUNS_DIR
    if not directory.is_dir():
        errors.append(f"missing runs directory: {RUNS_DIR}")
        return runs
    for path in sorted(directory.glob("*/run.json")):
        if path.parent.name == RUN_TEMPLATE_DIR:
            continue
        relative = path.relative_to(root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{relative}: unreadable run record ({exc})")
            continue
        if not isinstance(data, dict):
            errors.append(f"{relative}: run record must be an object")
            continue
        for field in ("goal", "record"):
            value = data.get(field)
            if not isinstance(value, str) or not (root / value).is_file():
                errors.append(f"{relative}: {field} does not resolve ({value!r})")
        runs[relative] = {
            "status": data.get("status"),
            "branch": data.get("branch"),
            "goal": data.get("goal"),
        }
    return runs


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    canonical = set(canonical_statuses(root))
    goals = load_goals(root, errors)
    runs = load_runs(root, errors)

    # 1. canonical enum plus the recorded-residual ratchet.
    actual = {
        gid: rec["status"]
        for gid, rec in goals.items()
        if isinstance(rec.get("status"), str) and rec["status"] not in canonical
    }
    expected = {gid: rec["status"] for gid, rec in RECORDED_NON_CANONICAL.items()}
    for gid in sorted(set(actual) | set(expected)):
        got = actual.get(gid)
        want = expected.get(gid)
        if got == want:
            continue
        if got is None:
            errors.append(
                f"{gid}: recorded non-canonical residual {want!r} is gone; remove it from "
                "RECORDED_NON_CANONICAL in the same change"
            )
        elif want is None:
            errors.append(
                f"{gid}: goal status {got!r} is not in the canonical enum {sorted(canonical)} "
                "and is not a recorded residual"
            )
        else:
            errors.append(f"{gid}: recorded non-canonical residual drifted {want!r} -> {got!r}")
    for gid, rec in sorted(RECORDED_NON_CANONICAL.items()):
        if not rec.get("owner"):
            errors.append(f"{gid}: recorded non-canonical residual needs an owner/rationale")

    # 2. a terminal run must not leave a non-terminal goal behind.
    for relative, run in sorted(runs.items()):
        if run["status"] not in TERMINAL:
            continue
        goal = next(
            ((gid, rec) for gid, rec in goals.items() if rec["path"] == run.get("goal")),
            None,
        )
        if goal is None or goal[1].get("status") in TERMINAL:
            continue
        gid, rec = goal
        allowance = TERMINAL_MISMATCH_ALLOWLIST.get(gid)
        if (
            allowance
            and allowance.get("goal_status") == rec.get("status")
            and allowance.get("run_status") == run["status"]
        ):
            continue
        errors.append(
            f"{gid}: run {relative} is {run['status']} but the goal status is {rec.get('status')!r}; "
            "close the goal, correct the run, or record an owner-justified allowlist entry"
        )
    for gid, allowance in sorted(TERMINAL_MISMATCH_ALLOWLIST.items()):
        if not allowance.get("authority") or not allowance.get("reason"):
            errors.append(f"{gid}: terminal-mismatch allowlist needs an authority and a reason")
        authority_path = str(allowance.get("authority", "")).split("#", 1)[0]
        if not authority_path or not (root / authority_path).is_file():
            errors.append(
                f"{gid}: terminal-mismatch allowlist authority {authority_path!r} does not exist"
            )
        rec = goals.get(gid)
        matched = rec is not None and rec.get("status") == allowance.get("goal_status") and any(
            run.get("goal") == rec["path"] and run["status"] == allowance.get("run_status")
            for run in runs.values()
        )
        if not matched:
            errors.append(
                f"{gid}: allowlist entry run={allowance.get('run_status')} "
                f"goal={allowance.get('goal_status')} no longer matches the ledger; remove or update it"
            )

    # 3. active-run index integrity.
    index_file = root / INDEX_PATH
    if not index_file.is_file():
        errors.append(f"missing active-run index: {INDEX_PATH}")
    else:
        try:
            index = json.loads(index_file.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{INDEX_PATH}: unreadable ({exc})")
            index = None
        if index is not None:
            branches = index.get("branches")
            if not isinstance(branches, dict):
                errors.append(f"{INDEX_PATH}: branches must be an object")
                branches = {}
            for branch, relative in sorted(branches.items()):
                if not isinstance(relative, str) or not relative.startswith(".agent/runs/"):
                    errors.append(f"{INDEX_PATH}: {branch} -> {relative!r} is not a .agent/runs path")
                    continue
                if not (root / relative).is_file():
                    errors.append(f"{INDEX_PATH}: {branch} -> {relative} does not exist")
                    continue
                run = runs.get(relative)
                if run is None:
                    continue
                if run.get("branch") != branch:
                    errors.append(
                        f"{INDEX_PATH}: {branch} -> {relative} declares branch {run.get('branch')!r}"
                    )
                if run.get("status") in TERMINAL:
                    errors.append(
                        f"{INDEX_PATH}: {branch} -> {relative} is {run.get('status')} and must be "
                        "removed from the index"
                    )

    # 4. run record status must be canonical.
    for relative, run in sorted(runs.items()):
        if run.get("status") not in canonical:
            errors.append(
                f"{relative}: run status {run.get('status')!r} is not in the canonical enum "
                f"{sorted(canonical)}"
            )
    return errors


def main() -> int:
    if "--list-residuals" in sys.argv:
        for gid, rec in sorted(RECORDED_NON_CANONICAL.items()):
            print(f"non-canonical\t{gid}\t{rec['status']}\t{rec['owner']}")
        for gid, rec in sorted(TERMINAL_MISMATCH_ALLOWLIST.items()):
            print(f"open-run\t{gid}\trun={rec['run_status']} goal={rec['goal_status']}\t{rec['authority']}")
        return 0
    errors = check()
    if errors:
        print("[agent_ledger_consistency_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    goals = len(list((ROOT / GOALS_DIR).glob("*.yaml")))
    runs = len([p for p in (ROOT / RUNS_DIR).glob("*/run.json") if p.parent.name != RUN_TEMPLATE_DIR])
    print(
        "[agent_ledger_consistency_guard] PASS "
        f"goals={goals} runs={runs} pinned_residuals={len(RECORDED_NON_CANONICAL)} "
        f"open_run_allowlist={len(TERMINAL_MISMATCH_ALLOWLIST)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
