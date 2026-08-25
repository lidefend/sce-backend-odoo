#!/usr/bin/env python3
"""Classify a change set into a fail-closed CI risk lane."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/ci/risk_tiering_v1.json"


@dataclass(frozen=True)
class Classification:
    lane: str
    paths: tuple[str, ...]
    reasons: tuple[str, ...]
    frontend_changed: bool
    backend_changed: bool
    frontend_full_required: bool

    @property
    def frontend_mode(self) -> str:
        if self.lane == "RELEASE" or self.frontend_full_required:
            return "full"
        if self.frontend_changed:
            return "standard"
        return "skip"

    @property
    def professional_mode(self) -> str:
        if self.lane in {"HIGH_RISK", "RELEASE"}:
            return "full"
        if self.lane == "STANDARD" and self.backend_changed:
            return "standard_backend"
        if self.lane == "STANDARD":
            return "standard_frontend"
        return "fast"

    def outputs(self) -> dict[str, str]:
        return {
            "lane": self.lane,
            "frontend_mode": self.frontend_mode,
            "professional_mode": self.professional_mode,
            "frontend_changed": str(self.frontend_changed).lower(),
            "backend_changed": str(self.backend_changed).lower(),
            "frontend_full_required": str(self.frontend_full_required).lower(),
            "changed_path_count": str(len(self.paths)),
            "changed_paths_json": json.dumps(self.paths, separators=(",", ":")),
            "reasons_json": json.dumps(self.reasons, separators=(",", ":")),
        }


def load_policy(path: Path = POLICY_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("default_lane") != "HIGH_RISK":
        raise ValueError("CI risk policy must fail closed to HIGH_RISK")
    return data


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _normalize_paths(paths: Iterable[str]) -> tuple[str, ...]:
    normalized: set[str] = set()
    for raw in paths:
        value = raw.strip().replace("\\", "/")
        if not value:
            continue
        pure = PurePosixPath(value)
        if pure.is_absolute() or ".." in pure.parts:
            normalized.add(f"__INVALID_PATH__/{value}")
        else:
            normalized.add(pure.as_posix())
    return tuple(sorted(normalized))


def classify(
    paths: Iterable[str],
    *,
    event_name: str,
    ref: str = "",
    policy: dict | None = None,
) -> Classification:
    policy = policy or load_policy()
    changed = _normalize_paths(paths)
    if event_name == "workflow_dispatch" or _matches(ref, policy["release_refs"]):
        return Classification("RELEASE", changed, ("release_event",), True, True, True)
    if not changed:
        return Classification("HIGH_RISK", changed, ("empty_change_set_fail_closed",), True, True, True)

    frontend_owned = tuple(
        path for path in changed
        if _matches(path, policy.get("standard_frontend_owned_paths", ()))
    )
    high_risk_override = tuple(
        path for path in changed
        if _matches(path, policy.get("high_risk_override_paths", ()))
    )
    high = tuple(
        path for path in changed
        if _matches(path, policy["high_risk_paths"]) and path not in high_risk_override
    )
    invalid = tuple(path for path in changed if path.startswith("__INVALID_PATH__/"))
    frontend = tuple(path for path in changed if _matches(path, policy["standard_frontend_paths"]))
    backend = tuple(
        path for path in changed
        if _matches(path, policy["standard_backend_paths"]) and path not in frontend_owned
    )
    frontend_full = tuple(path for path in changed if _matches(path, policy["frontend_full_paths"]))
    fast = tuple(path for path in changed if _matches(path, policy["fast_paths"]))
    known = set(high) | set(frontend) | set(backend) | set(fast)
    unknown = tuple(path for path in changed if path not in known)

    if high or invalid or unknown:
        reasons = []
        if high:
            reasons.append("high_risk_path")
        if invalid:
            reasons.append("invalid_path")
        if unknown:
            reasons.append("unknown_path_fail_closed")
        return Classification(
            "HIGH_RISK",
            changed,
            tuple(reasons),
            bool(frontend),
            bool(backend),
            bool(frontend_full),
        )
    if frontend or backend:
        return Classification(
            "STANDARD",
            changed,
            ("standard_runtime_change",),
            bool(frontend),
            bool(backend),
            bool(frontend_full),
        )
    return Classification("FAST", changed, ("non_runtime_change",), False, False, False)


def changed_paths(base: str, head: str) -> tuple[str, ...]:
    if not base or not head:
        raise ValueError("base and head SHA are required")
    command = ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", f"{base}...{head}", "--"]
    result = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True)
    return tuple(result.stdout.splitlines())


def write_github_output(path: Path, values: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            if "\n" in value:
                raise ValueError(f"multiline GitHub output is forbidden: {key}")
            stream.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--event", required=True)
    parser.add_argument("--ref", default="")
    parser.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    paths = tuple(args.paths or ())
    if not paths and args.event != "workflow_dispatch":
        paths = changed_paths(args.base or "", args.head or "")
    result = classify(paths, event_name=args.event, ref=args.ref)
    outputs = result.outputs()
    report = {
        "schema_version": "ci-risk-classification/v1",
        **outputs,
        "changed_paths": list(result.paths),
        "reasons": list(result.reasons),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    output_path = args.github_output or (
        Path(os.environ["GITHUB_OUTPUT"]) if os.environ.get("GITHUB_OUTPUT") else None
    )
    if output_path:
        write_github_output(output_path, outputs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
