#!/usr/bin/env python3
"""Match an owner-approved contract-only PR scope without trust on wildcards."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
SCOPE_PATH = ROOT / "config/ci/contract_only_scopes.json"


def _normalize(path: str) -> str:
    pure = PurePosixPath(str(path or "").strip().replace("\\", "/"))
    if not str(pure) or pure.is_absolute() or ".." in pure.parts:
        return ""
    return pure.as_posix()


def load_scopes(path: Path = SCOPE_PATH) -> tuple[dict, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("CONTRACT_ONLY_SCOPE_SCHEMA_UNSUPPORTED")
    scopes = data.get("scopes")
    if not isinstance(scopes, list):
        raise ValueError("CONTRACT_ONLY_SCOPE_LIST_INVALID")
    result: list[dict] = []
    for index, raw in enumerate(scopes):
        if not isinstance(raw, dict):
            raise ValueError(f"CONTRACT_ONLY_SCOPE_INVALID:{index}")
        scope_id = str(raw.get("id") or "").strip()
        branch = str(raw.get("branch") or "").strip()
        base_sha = str(raw.get("base_sha") or "").strip()
        allowed = raw.get("allowed_paths")
        targets = raw.get("targets")
        excluded = raw.get("excluded_targets")
        if (
            not scope_id
            or not branch
            or len(base_sha) != 40
            or not isinstance(allowed, list)
            or not allowed
            or not isinstance(targets, list)
            or not targets
            or not isinstance(excluded, list)
        ):
            raise ValueError(f"CONTRACT_ONLY_SCOPE_INVALID:{index}")
        normalized_allowed = tuple(_normalize(value) for value in allowed)
        normalized_targets = tuple(str(value or "").strip() for value in targets)
        normalized_excluded = tuple(str(value or "").strip() for value in excluded)
        if (
            "" in normalized_allowed
            or "" in normalized_targets
            or "" in normalized_excluded
            or any("*" in value or "?" in value for value in normalized_allowed)
        ):
            raise ValueError(f"CONTRACT_ONLY_SCOPE_WILDCARD_FORBIDDEN:{scope_id}")
        result.append({
            **raw,
            "id": scope_id,
            "branch": branch,
            "base_sha": base_sha,
            "allowed_paths": normalized_allowed,
            "targets": normalized_targets,
            "excluded_targets": normalized_excluded,
        })
    return tuple(result)


def match_scope(
    paths: Iterable[str],
    *,
    branch: str,
    base_sha: str,
    scopes: Iterable[dict] | None = None,
) -> dict | None:
    changed = tuple(sorted({_normalize(path) for path in paths if _normalize(path)}))
    if not changed or not str(branch or "").strip() or len(str(base_sha or "")) != 40:
        return None
    for scope in scopes or load_scopes():
        if scope["branch"] != branch or scope["base_sha"] != base_sha:
            continue
        if set(changed).issubset(set(scope["allowed_paths"])):
            return scope
    return None
