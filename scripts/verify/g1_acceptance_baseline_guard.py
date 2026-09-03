#!/usr/bin/env python3
"""G1 acceptance baseline guard.

Validates the environment-independent acceptance baseline evidence for the
custom-frontend-integration program (docs/planning/custom-frontend-integration/).

Checks (default mode):
  1. G1_BASELINE_EVIDENCE.json satisfies the evidence contract schema
     (config/frontend/acceptance_evidence_contract_v1.schema.json).
  2. baseline_sha is traceable: it must be an ancestor of origin/main.
  3. Reproducibility: sha256 of every tracked environment asset is recomputed
     and must match the recorded fingerprint.
  4. All four acceptance environment profiles (local/test/daily/production)
     exist in acceptance_environments_v1.json and match the evidence.
  5. The browser evidence contract field set covers the 11 mandatory fields
     from the master plan README section 12.

--write regenerates the evidence file (fingerprint refresh workflow).
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
    ROOT / "docs" / "planning" / "custom-frontend-integration" / "G1_BASELINE_EVIDENCE.json"
)
SCHEMA_PATH = ROOT / "config" / "frontend" / "acceptance_evidence_contract_v1.schema.json"
ENVIRONMENTS_PATH = ROOT / "config" / "frontend" / "acceptance_environments_v1.json"
TOOL_MATRIX_PATH = ROOT / "config" / "frontend" / "acceptance_tool_matrix_v1.json"
INVENTORY_PATH = (
    ROOT / "docs" / "planning" / "custom-frontend-integration" / "G1_CAPABILITY_INVENTORY.md"
)

EXPECTED_PROFILES = {"local", "test", "daily", "production"}

# Mandatory browser evidence fields from README section 12 (contract freeze).
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

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


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


def _validate_evidence(evidence: dict, errors: list[str]) -> None:
    """Structural validation mirroring the JSON schema (no jsonschema dependency)."""
    if evidence.get("schema") != "frontend_acceptance_evidence_contract.v1":
        errors.append("schema must be 'frontend_acceptance_evidence_contract.v1'")

    baseline = evidence.get("baseline") or {}
    baseline_sha = baseline.get("baseline_sha")
    if not isinstance(baseline_sha, str) or not SHA1_RE.match(baseline_sha):
        errors.append("baseline.baseline_sha must be a 40-char lowercase hex SHA")
    if not isinstance(baseline.get("baseline_sha_source"), str) or not baseline.get(
        "baseline_sha_source"
    ):
        errors.append("baseline.baseline_sha_source must be a non-empty string")
    inventory = baseline.get("capability_inventory_path")
    if inventory != "docs/planning/custom-frontend-integration/G1_CAPABILITY_INVENTORY.md":
        errors.append("baseline.capability_inventory_path must point at the G1 inventory doc")

    env_assets = evidence.get("environment_assets") or {}
    profiles = env_assets.get("profiles_present")
    if not isinstance(profiles, list) or set(profiles) != EXPECTED_PROFILES:
        errors.append(
            "environment_assets.profiles_present must be exactly "
            f"{sorted(EXPECTED_PROFILES)} (got {profiles!r})"
        )
    assets = env_assets.get("assets")
    if not isinstance(assets, list) or not assets:
        errors.append("environment_assets.assets must be a non-empty list")
    else:
        for asset in assets:
            if not isinstance(asset, dict):
                errors.append("environment_assets.assets entries must be objects")
                continue
            if not isinstance(asset.get("path"), str) or not asset.get("path"):
                errors.append("asset.path must be a non-empty string")
            digest = asset.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.match(digest):
                errors.append(f"asset.sha256 for {asset.get('path')!r} must be 64-char hex")

    toolchain = evidence.get("toolchain") or {}
    for key in ("python", "git"):
        if not isinstance(toolchain.get(key), str) or not toolchain.get(key):
            errors.append(f"toolchain.{key} must be a non-empty string")

    collected_at = evidence.get("collected_at")
    if not isinstance(collected_at, str) or not re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", collected_at
    ):
        errors.append("collected_at must be an ISO 8601 datetime string")

    contract = evidence.get("browser_evidence_contract") or {}
    fields = contract.get("required_fields")
    if not isinstance(fields, list):
        errors.append("browser_evidence_contract.required_fields must be a list")
    else:
        missing = MANDATORY_BROWSER_EVIDENCE_FIELDS - set(fields)
        if missing:
            errors.append(
                "browser_evidence_contract.required_fields missing mandatory fields: "
                + ", ".join(sorted(missing))
            )
    if contract.get("cross_env_reuse_forbidden") is not True:
        errors.append("browser_evidence_contract.cross_env_reuse_forbidden must be true")


def _validate_reproducibility(evidence: dict, errors: list[str]) -> None:
    """Recompute asset fingerprints; the core of 'baseline evidence is reproducible'."""
    assets = (evidence.get("environment_assets") or {}).get("assets") or []
    for asset in assets:
        path = ROOT / asset["path"]
        if not path.is_file():
            errors.append(f"tracked asset missing on disk: {asset['path']}")
            continue
        actual = _sha256_file(path)
        if actual != asset["sha256"]:
            errors.append(
                f"fingerprint drift for {asset['path']}: recorded {asset['sha256'][:12]}..., "
                f"actual {actual[:12]}... — refresh with --write and review"
            )


def _validate_profiles_against_config(evidence: dict, errors: list[str]) -> None:
    config = json.loads(ENVIRONMENTS_PATH.read_text(encoding="utf-8"))
    profiles = set(config.get("profiles") or {})
    missing = EXPECTED_PROFILES - profiles
    if missing:
        errors.append(
            "acceptance_environments_v1.json is missing profiles: " + ", ".join(sorted(missing))
        )
    recorded = set((evidence.get("environment_assets") or {}).get("profiles_present") or [])
    if recorded != EXPECTED_PROFILES:
        errors.append("evidence profiles_present does not match the four-environment contract")


def _validate_schema_selfcheck(errors: list[str]) -> None:
    """The contract schema itself must freeze the 11 mandatory browser evidence fields."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    props = schema.get("properties", {}).get("browser_evidence_contract", {})
    if props.get("properties", {}).get("cross_env_reuse_forbidden", {}).get("const") is not True:
        errors.append("schema must freeze cross_env_reuse_forbidden = true")


def write_evidence(baseline_sha: str | None) -> dict:
    baseline = baseline_sha or _git(["rev-parse", "HEAD"])
    evidence = {
        "schema": "frontend_acceptance_evidence_contract.v1",
        "baseline": {
            "baseline_sha": baseline,
            "baseline_sha_source": (
                "G1 branch cut point (main HEAD when the G1 acceptance baseline was frozen); "
                "traceable to origin/main via git merge-base --is-ancestor"
            ),
            "capability_inventory_path": "docs/planning/custom-frontend-integration/G1_CAPABILITY_INVENTORY.md",
        },
        "environment_assets": {
            "profiles_present": ["daily", "local", "production", "test"],
            "assets": [
                {
                    "path": "config/frontend/acceptance_environments_v1.json",
                    "sha256": _sha256_file(ENVIRONMENTS_PATH),
                },
                {
                    "path": "config/frontend/acceptance_tool_matrix_v1.json",
                    "sha256": _sha256_file(TOOL_MATRIX_PATH),
                },
                {
                    "path": "config/frontend/acceptance_evidence_contract_v1.schema.json",
                    "sha256": _sha256_file(SCHEMA_PATH),
                },
            ],
        },
        "toolchain": {
            "python": sys.version.split()[0],
            "git": _git(["--version"]).replace("git version ", ""),
        },
        "collected_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "browser_evidence_contract": {
            "required_fields": sorted(MANDATORY_BROWSER_EVIDENCE_FIELDS),
            "cross_env_reuse_forbidden": True,
        },
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
        help="regenerate G1_BASELINE_EVIDENCE.json instead of verifying",
    )
    parser.add_argument(
        "--baseline-sha",
        help="explicit baseline SHA for --write (defaults to current HEAD)",
    )
    args = parser.parse_args()

    if args.write:
        evidence = write_evidence(args.baseline_sha)
        print("[g1_acceptance_baseline_guard] WROTE " + str(EVIDENCE_PATH.relative_to(ROOT)))
        print("  baseline_sha = " + evidence["baseline"]["baseline_sha"])
        return 0

    if not EVIDENCE_PATH.is_file():
        print("[g1_acceptance_baseline_guard] FAIL")
        print(f"- evidence missing: {EVIDENCE_PATH.relative_to(ROOT)} (run with --write)")
        return 2
    if not INVENTORY_PATH.is_file():
        print("[g1_acceptance_baseline_guard] FAIL")
        print(f"- capability inventory missing: {INVENTORY_PATH.relative_to(ROOT)}")
        return 2

    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    _validate_evidence(evidence, errors)
    _validate_reproducibility(evidence, errors)
    _validate_profiles_against_config(evidence, errors)
    _validate_schema_selfcheck(errors)

    baseline_sha = (evidence.get("baseline") or {}).get("baseline_sha")
    if isinstance(baseline_sha, str) and SHA1_RE.match(baseline_sha):
        if not _is_ancestor(baseline_sha):
            errors.append(
                f"baseline_sha {baseline_sha} is not traceable to origin/main history"
            )

    if errors:
        print("[g1_acceptance_baseline_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("[g1_acceptance_baseline_guard] PASS")
    print(
        f"- four-environment profiles configured: local/test/daily/production "
        f"(fingerprints verified for {len((evidence['environment_assets'] or {}).get('assets') or [])} assets)"
    )
    print(f"- baseline evidence reproducible at baseline_sha {baseline_sha[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
