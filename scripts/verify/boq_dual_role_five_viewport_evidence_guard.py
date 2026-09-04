#!/usr/bin/python3
"""G3.3-B dual-role five-viewport BOQ acceptance evidence package guard.

Validates the evidence package emitted by
`scripts/verify/boq_dual_role_five_viewport_browser_acceptance.mjs` against
`config/frontend/acceptance_evidence_contract_v1.schema.json` and the
custom-frontend-integration master plan README §12 contract.

Checks (default mode):
  1. evidence.json exists, is loadable, and structurally matches the v1
     schema (schema / baseline / environment_assets / toolchain /
     collected_at / browser_evidence_contract).
  2. baseline_sha is a 40-char hex SHA traceable to origin/main.
  3. environment_assets contains 3 fixed assets (environments, tool matrix,
     schema) plus the harness script; all 4 sha256s match disk content.
  4. The four-environment profiles (local/test/daily/production) are
     declared both in the evidence and in acceptance_environments_v1.json.
  5. browser_evidence_contract.cross_env_reuse_forbidden == True and
     required_fields covers the 11 mandatory fields.
  6. matrix_spec declares 2 roles × 5 viewports × 2 datasets and the
     `cells` array has exactly cell_count = 20 entries.
  7. Each cell carries all 11 mandatory fields, with non-empty values
     and the correct types (e.g. screenshot_digest = 64-char hex).
  8. Cross-environment reuse forbidden (README §12: 跨环境不得复用截图):
     no screenshot_digest may appear in two different dataset × viewport
     combinations. Within one combination the two cost roles MAY share the
     same digest — a role-invariant readonly render is the acceptance goal
     itself (both cost roles must see the same authorized view). In that
     case independent capture is proven instead by role_session_digest
     (sha256 of the per-login session token, harness v0.3.0): every cell
     must carry one and all 20 must be pairwise distinct.
  9. Cell combinations cover the 2 × 5 × 2 cartesian product exactly
     (20 unique role/dataset/viewport triples).

--write regenerates a stub evidence.json with the env-assets fingerprints
for local re-write workflow (the harness itself overwrites this on every
real capture; the guard's --write is for the empty/missing-file case).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EVIDENCE_PATH = (
    ROOT / "artifacts" / "boq-dual-role-five-viewport" / "evidence.json"
)
SCHEMA_PATH = ROOT / "config" / "frontend" / "acceptance_evidence_contract_v1.schema.json"
ENVIRONMENTS_PATH = ROOT / "config" / "frontend" / "acceptance_environments_v1.json"
TOOL_MATRIX_PATH = ROOT / "config" / "frontend" / "acceptance_tool_matrix_v1.json"
HARNESS_PATH = ROOT / "scripts" / "verify" / "boq_dual_role_five_viewport_browser_acceptance.mjs"

EXPECTED_PROFILES = {"local", "test", "daily", "production"}
EXPECTED_ROLES = {"cost_manager", "cost_user"}
EXPECTED_VIEWPORTS = {"1440x900", "1280x800", "1024x768", "768x1024", "390x844"}
EXPECTED_DATASETS = {"boq_1k", "boq_10k"}
EXPECTED_CELL_COUNT = 20  # 2 × 5 × 2

MANDATORY_BROWSER_EVIDENCE_FIELDS = {
    "environment_id",
    "dataset_id",
    "role",
    "normalized_route",
    "browser_url",
    "viewport",
    "capture_mode",
    "browser_full_version",
    "screenshot_digest",
    "product_service_static_shas",
    "collected_at_and_tool_version",
}

# G3.3-B v0.3.0 扩展字段（README §12 的 11 个必填字段之外）：每 cell 登录
# 会话 token 的 sha256 摘要，用于在只读角色不变渲染（两角色截图字节级
# 一致）下证明 20 个 cell 各自独立采集（每次登录生成独立会话）。
MANDATORY_SESSION_DIGEST_FIELD = "role_session_digest"

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
ISO_DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _is_ancestor(sha: str) -> bool:
    base = _git(["rev-parse", "--verify", "--quiet", "origin/main"]) or _git(
        ["rev-parse", "--verify", "--quiet", "main"]
    )
    if not base:
        return False
    probe = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, base],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return probe.returncode == 0


def _add(errors: list[str], msg: str) -> None:
    errors.append(msg)


def _validate_evidence(evidence: dict, errors: list[str]) -> None:
    """Structural validation mirroring the v1 JSON schema (no jsonschema dep)."""
    if evidence.get("schema") != "frontend_acceptance_evidence_contract.v1":
        _add(errors, "schema must be 'frontend_acceptance_evidence_contract.v1'")

    baseline = evidence.get("baseline") or {}
    baseline_sha = baseline.get("baseline_sha")
    if not isinstance(baseline_sha, str) or not SHA1_RE.match(baseline_sha):
        _add(errors, "baseline.baseline_sha must be a 40-char lowercase hex SHA")
    if not isinstance(baseline.get("baseline_sha_source"), str) or not baseline.get("baseline_sha_source"):
        _add(errors, "baseline.baseline_sha_source must be a non-empty string")
    inventory = baseline.get("capability_inventory_path")
    if inventory != "docs/planning/custom-frontend-integration/G1_CAPABILITY_INVENTORY.md":
        _add(errors, "baseline.capability_inventory_path must point at the G1 inventory doc")

    env_assets = evidence.get("environment_assets") or {}
    profiles = env_assets.get("profiles_present")
    if not isinstance(profiles, list) or set(profiles) != EXPECTED_PROFILES:
        _add(
            errors,
            "environment_assets.profiles_present must be exactly "
            f"{sorted(EXPECTED_PROFILES)} (got {profiles!r})",
        )
    assets = env_assets.get("assets")
    if not isinstance(assets, list) or not assets:
        _add(errors, "environment_assets.assets must be a non-empty list")
    else:
        for asset in assets:
            if not isinstance(asset, dict):
                _add(errors, "environment_assets.assets entries must be objects")
                continue
            if not isinstance(asset.get("path"), str) or not asset.get("path"):
                _add(errors, "asset.path must be a non-empty string")
            digest = asset.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.match(digest):
                _add(errors, f"asset.sha256 for {asset.get('path')!r} must be 64-char hex")

    toolchain = evidence.get("toolchain") or {}
    for key in ("node", "playwright"):
        if not isinstance(toolchain.get(key), str) or not toolchain.get(key):
            _add(errors, f"toolchain.{key} must be a non-empty string")

    collected_at = evidence.get("collected_at")
    if not isinstance(collected_at, str) or not ISO_DT_RE.match(collected_at):
        _add(errors, "collected_at must be an ISO 8601 datetime string")

    contract = evidence.get("browser_evidence_contract") or {}
    fields = contract.get("required_fields")
    if not isinstance(fields, list):
        _add(errors, "browser_evidence_contract.required_fields must be a list")
    else:
        missing = MANDATORY_BROWSER_EVIDENCE_FIELDS - set(fields)
        if missing:
            _add(
                errors,
                "browser_evidence_contract.required_fields missing mandatory fields: "
                + ", ".join(sorted(missing)),
            )
    if contract.get("cross_env_reuse_forbidden") is not True:
        _add(errors, "browser_evidence_contract.cross_env_reuse_forbidden must be true")


def _validate_reproducibility(evidence: dict, errors: list[str]) -> None:
    """Recompute env-asset fingerprints; the core of 'evidence is reproducible'."""
    assets = (evidence.get("environment_assets") or {}).get("assets") or []
    for asset in assets:
        path = ROOT / asset["path"]
        if not path.is_file():
            _add(errors, f"tracked asset missing on disk: {asset['path']}")
            continue
        actual = _sha256_file(path)
        if actual != asset["sha256"]:
            _add(
                errors,
                f"fingerprint drift for {asset['path']}: recorded {asset['sha256'][:12]}..., "
                f"actual {actual[:12]}... — refresh by re-running the harness",
            )


def _validate_profiles_against_config(evidence: dict, errors: list[str]) -> None:
    config = json.loads(ENVIRONMENTS_PATH.read_text(encoding="utf-8"))
    profiles = set(config.get("profiles") or {})
    missing = EXPECTED_PROFILES - profiles
    if missing:
        _add(
            errors,
            "acceptance_environments_v1.json is missing profiles: " + ", ".join(sorted(missing)),
        )
    recorded = set((evidence.get("environment_assets") or {}).get("profiles_present") or [])
    if recorded != EXPECTED_PROFILES:
        _add(errors, "evidence profiles_present does not match the four-environment contract")


def _validate_schema_selfcheck(errors: list[str]) -> None:
    """The contract schema itself must freeze cross_env_reuse_forbidden = true."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    props = schema.get("properties", {}).get("browser_evidence_contract", {})
    if props.get("properties", {}).get("cross_env_reuse_forbidden", {}).get("const") is not True:
        _add(errors, "schema must freeze cross_env_reuse_forbidden = true")


def _validate_matrix_spec(evidence: dict, errors: list[str]) -> None:
    spec = evidence.get("matrix_spec") or {}
    roles = set(spec.get("roles") or [])
    viewports = set(spec.get("viewports") or [])
    datasets = set(spec.get("datasets") or [])
    if roles != EXPECTED_ROLES:
        _add(
            errors,
            f"matrix_spec.roles must equal {sorted(EXPECTED_ROLES)} (got {sorted(roles)})",
        )
    if viewports != EXPECTED_VIEWPORTS:
        _add(
            errors,
            f"matrix_spec.viewports must equal {sorted(EXPECTED_VIEWPORTS)} (got {sorted(viewports)})",
        )
    if datasets != EXPECTED_DATASETS:
        _add(
            errors,
            f"matrix_spec.datasets must equal {sorted(EXPECTED_DATASETS)} (got {sorted(datasets)})",
        )
    if spec.get("cell_count") != EXPECTED_CELL_COUNT:
        _add(
            errors,
            f"matrix_spec.cell_count must be {EXPECTED_CELL_COUNT} (got {spec.get('cell_count')!r})",
        )


def _validate_cell(cell: dict, index: int, errors: list[str]) -> str:
    """Validate one cell. Returns the {role,dataset,viewport} combo key for combo checks."""
    if not isinstance(cell, dict):
        _add(errors, f"cell[{index}] must be an object")
        return ""

    missing_fields = MANDATORY_BROWSER_EVIDENCE_FIELDS - set(cell.keys())
    if missing_fields:
        _add(
            errors,
            f"cell[{index}] missing mandatory fields: " + ", ".join(sorted(missing_fields)),
        )

    if cell.get("role") not in EXPECTED_ROLES:
        _add(errors, f"cell[{index}].role must be one of {sorted(EXPECTED_ROLES)} (got {cell.get('role')!r})")
    if cell.get("viewport") not in EXPECTED_VIEWPORTS:
        _add(errors, f"cell[{index}].viewport must be one of {sorted(EXPECTED_VIEWPORTS)} (got {cell.get('viewport')!r})")
    if cell.get("dataset_id") not in EXPECTED_DATASETS:
        _add(errors, f"cell[{index}].dataset_id must be one of {sorted(EXPECTED_DATASETS)} (got {cell.get('dataset_id')!r})")

    if not isinstance(cell.get("normalized_route"), str) or not cell["normalized_route"].startswith("/s/project.management"):
        _add(errors, f"cell[{index}].normalized_route must be a /s/project.management path")
    if not isinstance(cell.get("browser_url"), str) or not cell["browser_url"]:
        _add(errors, f"cell[{index}].browser_url must be a non-empty string")
    if cell.get("capture_mode") != "readonly":
        _add(errors, f"cell[{index}].capture_mode must be 'readonly' (got {cell.get('capture_mode')!r})")
    if not isinstance(cell.get("environment_id"), str) or not cell["environment_id"]:
        _add(errors, f"cell[{index}].environment_id must be a non-empty string")
    if not isinstance(cell.get("browser_full_version"), str) or not cell["browser_full_version"]:
        _add(errors, f"cell[{index}].browser_full_version must be a non-empty string")
    screenshot_digest = cell.get("screenshot_digest")
    if not isinstance(screenshot_digest, str) or not SHA256_RE.match(screenshot_digest):
        _add(errors, f"cell[{index}].screenshot_digest must be a 64-char hex SHA256")
    session_digest = cell.get(MANDATORY_SESSION_DIGEST_FIELD)
    if not isinstance(session_digest, str) or not SHA256_RE.match(session_digest):
        _add(
            errors,
            f"cell[{index}].{MANDATORY_SESSION_DIGEST_FIELD} must be a 64-char hex SHA256 "
            "(re-capture with harness >= 0.3.0)",
        )
    pss = cell.get("product_service_static_shas")
    if not isinstance(pss, dict) or not pss:
        _add(errors, f"cell[{index}].product_service_static_shas must be a non-empty object")
    else:
        for key in ("frontend_sha", "backend_sha", "contract_schema_sha"):
            if not isinstance(pss.get(key), str) or not pss[key]:
                _add(errors, f"cell[{index}].product_service_static_shas.{key} must be a non-empty string")
    cat = cell.get("collected_at_and_tool_version")
    if not isinstance(cat, str) or "|" not in cat:
        _add(errors, f"cell[{index}].collected_at_and_tool_version must be '<iso>|<tool_version>'")

    return f"role={cell.get('role')}|dataset={cell.get('dataset_id')}|viewport={cell.get('viewport')}"


def _validate_cells(evidence: dict, errors: list[str]) -> None:
    cells = evidence.get("cells")
    if not isinstance(cells, list):
        _add(errors, "evidence.cells must be a list")
        return
    if len(cells) != EXPECTED_CELL_COUNT:
        _add(
            errors,
            f"evidence.cells must contain exactly {EXPECTED_CELL_COUNT} entries (got {len(cells)})",
        )

    combo_keys: set[str] = set()
    # screenshot_digest → 出现过的 dataset×viewport 组合集合
    digest_combos: dict[str, set[tuple[str, str]]] = {}
    # role_session_digest → 出现次数（每 cell 须唯一）
    session_digest_counts: dict[str, int] = {}
    for index, cell in enumerate(cells):
        key = _validate_cell(cell, index, errors)
        if key:
            if key in combo_keys:
                _add(errors, f"duplicate cell combination at index {index}: {key}")
            combo_keys.add(key)
        digest = cell.get("screenshot_digest")
        if isinstance(digest, str) and SHA256_RE.match(digest):
            combo = (str(cell.get("dataset_id")), str(cell.get("viewport")))
            digest_combos.setdefault(digest, set()).add(combo)
        session_digest = cell.get(MANDATORY_SESSION_DIGEST_FIELD)
        if isinstance(session_digest, str) and SHA256_RE.match(session_digest):
            session_digest_counts[session_digest] = session_digest_counts.get(session_digest, 0) + 1

    # cross_env_reuse_forbidden（README §12：跨环境不得复用截图）：
    # 同一 screenshot_digest 不允许出现在两个不同的 dataset×viewport 组合。
    # 同组合内两角色允许一致 —— 只读角色不变渲染是 G3.3-B 的验收目标本身，
    # 此时独立采集由 role_session_digest 的两两不同来证明。
    cross_reuse = {d: cs for d, cs in digest_combos.items() if len(cs) > 1}
    if cross_reuse:
        _add(
            errors,
            "cross_env_reuse_forbidden violated: screenshot_digest reused across "
            "dataset×viewport combinations: "
            + ", ".join(f"{d[:12]}...×{len(cs)}combos" for d, cs in cross_reuse.items()),
        )

    session_dups = {d: n for d, n in session_digest_counts.items() if n > 1}
    if session_dups:
        _add(
            errors,
            "role_session_digest must be unique per cell (independent authenticated "
            "session per capture): duplicates "
            + ", ".join(f"{d[:12]}...×{n}" for d, n in session_dups.items()),
        )

    expected_combos = {
        f"role={r}|dataset={d}|viewport={v}"
        for r in EXPECTED_ROLES
        for d in EXPECTED_DATASETS
        for v in EXPECTED_VIEWPORTS
    }
    missing = expected_combos - combo_keys
    if missing:
        _add(
            errors,
            "missing cell combinations (must cover 2×5×2 cartesian): "
            + ", ".join(sorted(missing)),
        )


def _baseline_ancestor_check(evidence: dict, errors: list[str]) -> None:
    baseline_sha = (evidence.get("baseline") or {}).get("baseline_sha")
    if isinstance(baseline_sha, str) and SHA1_RE.match(baseline_sha):
        if not _is_ancestor(baseline_sha):
            _add(
                errors,
                f"baseline_sha {baseline_sha} is not traceable to origin/main history",
            )


def write_evidence(baseline_sha: str | None) -> dict:
    """Write a stub evidence.json with env-asset fingerprints.

    The harness overwrites this on every real capture. The guard's --write
    exists for the missing-file case so the guard can be re-run after a
    partial capture (the harness will overwrite it again on the next run).
    """
    baseline = baseline_sha or _git(["rev-parse", "HEAD"])
    evidence = {
        "schema": "frontend_acceptance_evidence_contract.v1",
        "baseline": {
            "baseline_sha": baseline,
            "baseline_sha_source": (
                "G3.3-B acceptance run baseline (origin/main HEAD at capture time)"
            ),
            "capability_inventory_path": "docs/planning/custom-frontend-integration/G1_CAPABILITY_INVENTORY.md",
        },
        "environment_assets": {
            "profiles_present": ["daily", "local", "production", "test"],
            "assets": [
                {"path": "config/frontend/acceptance_environments_v1.json", "sha256": _sha256_file(ENVIRONMENTS_PATH)},
                {"path": "config/frontend/acceptance_tool_matrix_v1.json", "sha256": _sha256_file(TOOL_MATRIX_PATH)},
                {"path": "config/frontend/acceptance_evidence_contract_v1.schema.json", "sha256": _sha256_file(SCHEMA_PATH)},
                {"path": "scripts/verify/boq_dual_role_five_viewport_browser_acceptance.mjs", "sha256": _sha256_file(HARNESS_PATH)},
            ],
        },
        "toolchain": {
            "node": "stub (overwritten by harness on next capture)",
            "playwright": "stub (overwritten by harness on next capture)",
        },
        "collected_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "browser_evidence_contract": {
            "required_fields": sorted(MANDATORY_BROWSER_EVIDENCE_FIELDS),
            "cross_env_reuse_forbidden": True,
        },
        "matrix_spec": {
            "roles": sorted(EXPECTED_ROLES),
            "viewports": sorted(EXPECTED_VIEWPORTS),
            "datasets": sorted(EXPECTED_DATASETS),
            "cell_count": EXPECTED_CELL_COUNT,
        },
        "cells": [],
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write a stub evidence.json (env-assets only) instead of verifying",
    )
    parser.add_argument(
        "--baseline-sha",
        help="explicit baseline SHA for --write (defaults to current HEAD)",
    )
    args = parser.parse_args()

    if args.write:
        evidence = write_evidence(args.baseline_sha)
        print("[boq_dual_role_five_viewport_evidence_guard] WROTE "
              + str(EVIDENCE_PATH.relative_to(ROOT)))
        print("  baseline_sha = " + evidence["baseline"]["baseline_sha"])
        return 0

    if not EVIDENCE_PATH.is_file():
        print("[boq_dual_role_five_viewport_evidence_guard] FAIL")
        print(f"- evidence missing: {EVIDENCE_PATH.relative_to(ROOT)} "
              "(run scripts/verify/boq_dual_role_five_viewport_browser_acceptance.mjs or pass --write)")
        return 2

    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    _validate_evidence(evidence, errors)
    _validate_reproducibility(evidence, errors)
    _validate_profiles_against_config(evidence, errors)
    _validate_schema_selfcheck(errors)
    _validate_matrix_spec(evidence, errors)
    _validate_cells(evidence, errors)
    _baseline_ancestor_check(evidence, errors)

    if errors:
        print("[boq_dual_role_five_viewport_evidence_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("[boq_dual_role_five_viewport_evidence_guard] PASS")
    print(
        f"- {EXPECTED_CELL_COUNT} cells (2 roles × 5 viewports × 2 datasets) "
        f"all 11 mandatory browser evidence fields present"
    )
    print(
        "- cross_env_reuse_forbidden honored: screenshot_digest unique across "
        "dataset×viewport combinations; cross-role digest equality within one "
        "combination is the expected readonly role-invariant render, backed by "
        "pairwise-distinct role_session_digest (independent sessions)"
    )
    print(
        f"- baseline evidence reproducible at baseline_sha "
        f"{evidence['baseline']['baseline_sha'][:12]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
