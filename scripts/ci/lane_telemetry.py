#!/usr/bin/env python3
"""Lane telemetry: real duration, outcome and failure attribution per lane.

Observability only.  Recording a lane never runs it, signs coverage, or relaxes
a gate: a record states what happened, not whether the lane passed.  Lane names
come from the same declaration the coverage audit measures, so telemetry cannot
invent a lane the execution lanes do not have, and a record for an entrypoint
that lane does not own is rejected rather than filed under a plausible name.

Three rates are reported, because a pass/fail counter hides the expensive
failure mode:

``pass_rate``
    passed runs over all recorded runs.
``degraded_rate``
    runs that finished correctly but did not get the cheap path they were
    entitled to (e.g. an incremental scan that silently fell back to a full
    scan).  A green lane with a high degraded rate is the "it passes, but it
    costs the full suite every time" case.
``integrity_failure_rate``
    records that are malformed, name an unknown lane, or bind a state the lane
    never ran in.  This one must be zero: a telemetry record that cannot be
    trusted must fail closed rather than average into the other two.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audit"))
import verification_lane_coverage as lanes  # noqa: E402

SCHEMA = "lane-telemetry/v1"
STATUSES = ("passed", "failed", "not_run", "cancelled")
DEGRADED_VOCABULARY = (
    "full_scan_fallback",
    "no_shard_reuse",
    "detached_from_main",
    "receipt_absent",
    "partial_lane",
)
FAILURE_OWNERS = (
    "product_defect",
    "baseline_evidence_defect",
    "environment_defect",
    "validation_tool_defect",
)
RECORD_FIELDS = (
    "schema_version",
    "lane",
    "entrypoint",
    "head",
    "worktree_dirty",
    "status",
    "duration_seconds",
    "degraded",
    "failure_owner",
    "recorded_at",
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class TelemetryError(RuntimeError):
    pass


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode:
        raise TelemetryError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process.stdout.strip()


def evidence_dir(root: Path) -> Path:
    raw = Path(git(root, "rev-parse", "--git-path", "codex/evidence/lane_telemetry"))
    return raw if raw.is_absolute() else root / raw


def lane_path(root: Path, lane: str) -> Path:
    return evidence_dir(root) / f"{lane}.jsonl"


def owned_entrypoints(lane: str) -> list[str]:
    return list(lanes.LANES.get(lane, ()))


def validated(record: object) -> tuple[dict | None, str | None]:
    """Return (record, None) or (None, reason) so callers never trust a half shape."""
    if not isinstance(record, dict):
        return None, "record is not an object"
    if set(record) != set(RECORD_FIELDS):
        return None, "record field set does not match the declared schema"
    if record["schema_version"] != SCHEMA:
        return None, "schema_version mismatch"
    lane = record["lane"]
    if not isinstance(lane, str) or lane not in lanes.LANES:
        return None, f"unknown lane {lane!r}"
    if record["entrypoint"] not in owned_entrypoints(lane):
        return None, f"entrypoint {record['entrypoint']!r} is not owned by lane {lane}"
    if not isinstance(record["head"], str) or not FULL_SHA.fullmatch(record["head"]):
        return None, "head is not a full lowercase commit SHA"
    if not isinstance(record["worktree_dirty"], bool):
        return None, "worktree_dirty is not a boolean"
    if record["status"] not in STATUSES:
        return None, f"unknown status {record['status']!r}"
    duration = record["duration_seconds"]
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0:
        return None, "duration_seconds is not a non-negative number"
    degraded = record["degraded"]
    if not isinstance(degraded, list) or any(item not in DEGRADED_VOCABULARY for item in degraded):
        return None, "degraded is not a list of declared reasons"
    if len(set(degraded)) != len(degraded):
        return None, "degraded repeats a reason"
    owner = record["failure_owner"]
    if record["status"] == "failed":
        if owner not in FAILURE_OWNERS:
            return None, "a failed run needs one declared failure owner"
    elif owner is not None:
        return None, "only a failed run may carry a failure owner"
    if isinstance(record["recorded_at"], bool) or not isinstance(record["recorded_at"], (int, float)):
        return None, "recorded_at is not a number"
    return record, None


def record(root: Path, lane: str, entrypoint: str, status: str, duration_seconds: float,
           degraded: tuple[str, ...] | list[str] = (), failure_owner: str | None = None,
           head: str | None = None) -> dict:
    """Append one validated lane observation.  Never runs, gates or signs anything."""
    root = Path(root).resolve()
    if head is None:
        head = git(root, "rev-parse", "HEAD")
    dirty = bool(git(root, "status", "--porcelain=v1", "--untracked-files=all"))
    payload = {
        "schema_version": SCHEMA,
        "lane": lane,
        "entrypoint": entrypoint,
        "head": head,
        "worktree_dirty": dirty,
        "status": status,
        "duration_seconds": round(float(duration_seconds), 3),
        "degraded": sorted(set(degraded)),
        "failure_owner": failure_owner,
        "recorded_at": time.time(),
    }
    _, reason = validated(payload)
    if reason is not None:
        raise TelemetryError(f"refusing to record an invalid observation: {reason}")
    path = lane_path(root, lane)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload


def load(root: Path, lane: str | None = None) -> tuple[list[dict], list[str]]:
    """Every readable record plus the integrity failures found while reading."""
    root = Path(root).resolve()
    folder = evidence_dir(root)
    selection = [lane] if lane else sorted(lanes.LANES)
    records: list[dict] = []
    failures: list[str] = []
    for name in selection:
        path = folder / f"{name}.jsonl"
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                failures.append(f"{path.name}:{number}: not JSON")
                continue
            entry, reason = validated(payload)
            if reason is not None:
                failures.append(f"{path.name}:{number}: {reason}")
                continue
            if entry["lane"] != name:
                failures.append(f"{path.name}:{number}: filed under lane {name} but declares {entry['lane']}")
                continue
            records.append(entry)
    return records, failures


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return round(ordered[index], 3)


def _rates(records: list[dict]) -> dict:
    total = len(records)
    statuses = defaultdict(int)
    degraded = defaultdict(int)
    owners = defaultdict(int)
    for entry in records:
        statuses[entry["status"]] += 1
        for reason in entry["degraded"]:
            degraded[reason] += 1
        if entry["failure_owner"]:
            owners[entry["failure_owner"]] += 1
    durations = [entry["duration_seconds"] for entry in records]
    degraded_runs = sum(1 for entry in records if entry["degraded"])
    return {
        "runs": total,
        "by_status": dict(sorted(statuses.items())),
        "pass_rate": round(statuses["passed"] / total, 4) if total else 0.0,
        "degraded_runs": degraded_runs,
        "degraded_rate": round(degraded_runs / total, 4) if total else 0.0,
        "degraded_by_reason": dict(sorted(degraded.items())),
        "failure_owners": dict(sorted(owners.items())),
        "heads": len({entry["head"] for entry in records}),
        "duration_seconds": {
            "p50": _percentile(durations, 0.50),
            "p95": _percentile(durations, 0.95),
            "max": round(max(durations), 3) if durations else 0.0,
        },
        "last_recorded_at": max((entry["recorded_at"] for entry in records), default=None),
    }


def summarise(root: Path, by_head: bool = False) -> dict:
    records, failures = load(root)
    summary = {
        "schema_version": SCHEMA,
        "lanes": {lane: _rates([entry for entry in records if entry["lane"] == lane])
                  for lane in sorted(lanes.LANES)},
        "integrity_failures": failures,
        "integrity_failure_rate": round(len(failures) / (len(records) + len(failures)), 4)
        if (records or failures) else 0.0,
    }
    if by_head:
        versions = defaultdict(list)
        for entry in records:
            versions[entry["head"]].append(entry)
        summary["by_head"] = {
            head: {
                "lanes": {lane: _rates([entry for entry in rows if entry["lane"] == lane])
                          for lane in sorted({entry["lane"] for entry in rows})},
                "worktree_dirty": any(entry["worktree_dirty"] for entry in rows),
            }
            for head, rows in sorted(versions.items(), key=lambda pair: max(
                entry["recorded_at"] for entry in pair[1]), reverse=True)
        }
    return summary


def render(summary: dict, by_head: bool = False) -> list[str]:
    lines = ["[lane-telemetry] real lane observations (observability only; no gate is relaxed)"]
    for lane, stats in summary["lanes"].items():
        if not stats["runs"]:
            lines.append(f"  lane {lane:<38}: no data")
            continue
        lines.append(
            f"  lane {lane:<38}: runs={stats['runs']} pass={stats['pass_rate']:.2f} "
            f"degraded={stats['degraded_rate']:.2f} p50={stats['duration_seconds']['p50']}s "
            f"p95={stats['duration_seconds']['p95']}s heads={stats['heads']}"
        )
        if stats["degraded_by_reason"]:
            lines.append(f"       degraded reasons: {stats['degraded_by_reason']}")
        if stats["failure_owners"]:
            lines.append(f"       failure owners : {stats['failure_owners']}")
    lines.append(
        f"  integrity failure rate: {summary['integrity_failure_rate']:.4f} "
        f"({len(summary['integrity_failures'])} record(s) rejected)"
    )
    if by_head:
        for head, version in summary.get("by_head", {}).items():
            dirty = " dirty" if version["worktree_dirty"] else ""
            lanes_text = " ".join(
                f"{lane}={stats['runs']}run/{stats['degraded_rate']:.2f}deg"
                for lane, stats in version["lanes"].items()
            )
            lines.append(f"  head {head[:12]}{dirty}: {lanes_text}")
    return lines


def check(root: Path) -> int:
    summary = summarise(root)
    for line in render(summary):
        print(line)
    if summary["integrity_failures"]:
        print("[lane-telemetry] FAIL integrity failures present:")
        for failure in summary["integrity_failures"]:
            print(f"  {failure}")
        return 2
    print("[lane-telemetry] PASS every recorded observation is schema-valid and lane-owned")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    record_parser = sub.add_parser("record")
    record_parser.add_argument("--root", type=Path, default=Path.cwd())
    record_parser.add_argument("--lane", required=True)
    record_parser.add_argument("--entrypoint", required=True)
    record_parser.add_argument("--status", required=True, choices=STATUSES)
    record_parser.add_argument("--duration-seconds", type=float, required=True)
    record_parser.add_argument("--degraded", action="append", default=[])
    record_parser.add_argument("--failure-owner", default=None)
    record_parser.add_argument("--head", default=None)
    report_parser = sub.add_parser("report")
    report_parser.add_argument("--root", type=Path, default=Path.cwd())
    report_parser.add_argument("--json", type=Path, default=None)
    report_parser.add_argument("--by-head", action="store_true")
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        if args.mode == "record":
            payload = record(args.root, args.lane, args.entrypoint, args.status,
                             args.duration_seconds, args.degraded, args.failure_owner, args.head)
            print(f"[lane-telemetry] RECORDED lane={payload['lane']} status={payload['status']} "
                  f"head={payload['head'][:12]}")
            return 0
        if args.mode == "report":
            summary = summarise(args.root, by_head=args.by_head)
            if args.json is not None:
                args.json.parent.mkdir(parents=True, exist_ok=True)
                args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                     encoding="utf-8")
            for line in render(summary, by_head=args.by_head):
                print(line)
            return 0
        return check(args.root)
    except TelemetryError as exc:
        print(f"[lane-telemetry] MISS {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
