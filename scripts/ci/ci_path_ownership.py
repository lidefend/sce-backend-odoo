#!/usr/bin/env python3
"""Single path-ownership registry shared by CI risk and backend impact selection."""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "config/ci/path_ownership_v1.json"
RISK_VALUES = frozenset({"fast", "standard", "high"})
TOOL_TARGET_RE = re.compile(r"^verify\.[A-Za-z0-9_.-]+$")


class OwnershipError(ValueError):
    pass


@dataclass(frozen=True)
class OwnershipCategory:
    id: str
    patterns: tuple[str, ...]
    risk: str
    frontend: bool
    backend: bool
    backend_runtime: bool
    control_plane: bool
    frontend_full: bool
    agent_run_registration: bool
    agent_governance: bool
    backend_tooling: bool
    tool_checks: tuple[str, ...]


@dataclass(frozen=True)
class OwnershipSummary:
    assignments: dict[str, str]
    categories: dict[str, OwnershipCategory]
    unknown_paths: tuple[str, ...]
    invalid_paths: tuple[str, ...]

    def paths_for(self, category_id: str) -> tuple[str, ...]:
        return tuple(sorted(path for path, value in self.assignments.items() if value == category_id))

    def category_for(self, path: str) -> OwnershipCategory | None:
        category_id = self.assignments.get(path)
        return self.categories.get(category_id) if category_id else None

    @property
    def tool_checks(self) -> tuple[str, ...]:
        return tuple(sorted({
            target
            for category_id in set(self.assignments.values())
            if category_id in self.categories
            for target in self.categories[category_id].tool_checks
        }))

    @property
    def frontend_changed(self) -> bool:
        return any(self.category_for(path) and self.category_for(path).frontend
                   for path in self.assignments)

    @property
    def backend_changed(self) -> bool:
        return any(self.category_for(path) and self.category_for(path).backend
                   for path in self.assignments)

    @property
    def backend_runtime_changed(self) -> bool:
        return any(self.category_for(path) and self.category_for(path).backend_runtime
                   for path in self.assignments)

    @property
    def control_plane_changed(self) -> bool:
        return any(self.category_for(path) and self.category_for(path).control_plane
                   for path in self.assignments)

    @property
    def frontend_full_required(self) -> bool:
        return any(self.category_for(path) and self.category_for(path).frontend_full
                   for path in self.assignments)

    @property
    def high_risk(self) -> bool:
        return any(self.category_for(path) and self.category_for(path).risk == "high"
                   for path in self.assignments)

    @property
    def fast_only(self) -> bool:
        categories = [
            self.category_for(path) for path in self.assignments
            if path not in self.unknown_paths and path not in self.invalid_paths
        ]
        return bool(categories) and all(
            category is not None and category.risk == "fast" for category in categories
        )


def _bool(data: dict, key: str) -> bool:
    value = data.get(key, False)
    if type(value) is not bool:
        raise OwnershipError(f"{key} must be boolean")
    return value


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, OwnershipCategory]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise OwnershipError(f"unreadable path ownership registry: {exc}") from exc
    if data.get("schema_version") != "ci-path-ownership/v1":
        raise OwnershipError("invalid path ownership schema")
    rows = data.get("categories")
    if not isinstance(rows, list) or not rows:
        raise OwnershipError("path ownership categories must be a nonempty list")
    categories: dict[str, OwnershipCategory] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise OwnershipError("path ownership category must be an object")
        category_id = row.get("id")
        if not isinstance(category_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", category_id):
            raise OwnershipError(f"invalid category id: {category_id!r}")
        if category_id in categories:
            raise OwnershipError(f"duplicate category id: {category_id}")
        patterns = row.get("patterns")
        if (not isinstance(patterns, list) or not patterns
                or not all(isinstance(value, str) and value for value in patterns)):
            raise OwnershipError(f"{category_id}: patterns must be a nonempty string list")
        risk = row.get("risk")
        if risk not in RISK_VALUES:
            raise OwnershipError(f"{category_id}: invalid risk {risk!r}")
        checks = row.get("tool_checks")
        if (not isinstance(checks, list)
                or not all(isinstance(value, str) and TOOL_TARGET_RE.fullmatch(value)
                           for value in checks)):
            raise OwnershipError(f"{category_id}: invalid tool_checks")
        categories[category_id] = OwnershipCategory(
            id=category_id,
            patterns=tuple(patterns),
            risk=risk,
            frontend=_bool(row, "frontend"),
            backend=_bool(row, "backend"),
            backend_runtime=_bool(row, "backend_runtime"),
            control_plane=_bool(row, "control_plane"),
            frontend_full=_bool(row, "frontend_full"),
            agent_run_registration=_bool(row, "agent_run_registration"),
            agent_governance=_bool(row, "agent_governance"),
            backend_tooling=_bool(row, "backend_tooling"),
            tool_checks=tuple(sorted(set(checks))),
        )
    return categories


def normalize_path(raw: str) -> tuple[str, bool]:
    value = raw.strip().replace("\\", "/")
    if value.startswith("__INVALID_PATH__/"):
        return value, True
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts:
        return f"__INVALID_PATH__/{value}", True
    return pure.as_posix(), False


def category_for_path(path: str, categories: dict[str, OwnershipCategory]) -> OwnershipCategory | None:
    for category in categories.values():
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in category.patterns):
            return category
    return None


def classify_paths(
    paths: Iterable[str],
    *,
    registry_path: Path = REGISTRY_PATH,
) -> OwnershipSummary:
    categories = load_registry(registry_path)
    assignments: dict[str, str] = {}
    invalid: list[str] = []
    unknown: list[str] = []
    for raw in paths:
        path, is_invalid = normalize_path(str(raw))
        if is_invalid:
            assignments[path] = "__invalid__"
            invalid.append(path)
            continue
        category = category_for_path(path, categories)
        if category is None:
            assignments[path] = "__unknown__"
            unknown.append(path)
        else:
            assignments[path] = category.id
    return OwnershipSummary(
        assignments=assignments,
        categories=categories,
        unknown_paths=tuple(sorted(unknown)),
        invalid_paths=tuple(sorted(invalid)),
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="+")
    args = parser.parse_args()
    result = classify_paths(args.path)
    payload = {
        "assignments": result.assignments,
        "unknown_paths": result.unknown_paths,
        "invalid_paths": result.invalid_paths,
        "frontend_changed": result.frontend_changed,
        "backend_changed": result.backend_changed,
        "backend_runtime_changed": result.backend_runtime_changed,
        "control_plane_changed": result.control_plane_changed,
        "tool_checks": result.tool_checks,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 2 if result.unknown_paths or result.invalid_paths else 0


if __name__ == "__main__":
    raise SystemExit(main())
