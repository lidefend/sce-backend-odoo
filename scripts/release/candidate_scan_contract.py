#!/usr/bin/env python3
"""Parse a candidate scan into a fail-closed, identity-bound release record."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


class ScanContractError(ValueError):
    pass


def _load(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScanContractError(f"{label} is missing or invalid") from exc
    if not isinstance(value, dict):
        raise ScanContractError(f"{label} must be a JSON object")
    return value


def _required_text(payload: dict, field: str, label: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ScanContractError(f"{label}.{field} is required")
    return value


def build_summary(
    *,
    report: dict,
    trivy_version: dict,
    trivy_db_metadata: dict,
    syft_version: dict,
    image_manifest: dict,
    expected_source_sha: str,
    expected_image_digest: str,
    scanned_at: str,
) -> dict:
    if not FULL_SHA.fullmatch(expected_source_sha):
        raise ScanContractError("expected source SHA must be a full lowercase SHA")
    if not IMAGE_DIGEST.fullmatch(expected_image_digest):
        raise ScanContractError("expected image digest must be sha256:<64 hex>")
    if image_manifest.get("source_sha") != expected_source_sha:
        raise ScanContractError("scan source SHA does not match image manifest")
    if image_manifest.get("image_digest") != expected_image_digest:
        raise ScanContractError("scan image digest does not match image manifest")
    if (
        image_manifest.get("schema_version") != 2
        or image_manifest.get("registry_repository") != "ghcr.io/lidefend/sce-product"
        or image_manifest.get("publish_status") != "published"
    ):
        raise ScanContractError("scan requires a published formal registry manifest")
    registry_refs = image_manifest.get("registry_refs")
    expected_ref = f"ghcr.io/lidefend/sce-product@{expected_image_digest}"
    if not isinstance(registry_refs, list) or registry_refs != [expected_ref, expected_ref]:
        raise ScanContractError("scan registry references do not match image digest")
    if not isinstance(report.get("Results"), list):
        raise ScanContractError("Trivy Results is unavailable")

    counts = {severity: 0 for severity in SEVERITIES}
    counts["SECRET"] = 0
    observed_vulnerability_severities: set[str] = set()
    for result in report["Results"]:
        if not isinstance(result, dict):
            raise ScanContractError("Trivy result row is invalid")
        vulnerabilities = result.get("Vulnerabilities")
        secrets = result.get("Secrets")
        if vulnerabilities is not None and not isinstance(vulnerabilities, list):
            raise ScanContractError("Trivy vulnerability data is unavailable")
        if secrets is not None and not isinstance(secrets, list):
            raise ScanContractError("Trivy secret data is unavailable")
        for vulnerability in vulnerabilities or []:
            severity = str(vulnerability.get("Severity") or "").upper()
            if severity in counts:
                counts[severity] += 1
                observed_vulnerability_severities.add(severity)
        counts["SECRET"] += len(secrets or [])

    trivy = _required_text(trivy_version, "Version", "trivy")
    db_updated_at = _required_text(trivy_db_metadata, "UpdatedAt", "trivy_db_metadata")
    syft = _required_text(syft_version, "version", "syft")
    try:
        datetime.fromisoformat(scanned_at.replace("Z", "+00:00"))
        datetime.fromisoformat(db_updated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScanContractError("scan or vulnerability DB timestamp is invalid") from exc

    # Zero is a valid observation only because the scan command is contractually
    # required to request every severity. A missing Results/tool metadata field is
    # rejected above instead of being silently converted to zero.
    policy_pass = counts["CRITICAL"] == counts["HIGH"] == counts["SECRET"] == 0
    return {
        "schema_version": "candidate_scan.v2",
        "status": "completed",
        "source_sha": expected_source_sha,
        "image_digest": expected_image_digest,
        "counts": counts,
        "tools": {"trivy": trivy, "syft": syft},
        "vulnerability_db_updated_at": db_updated_at,
        "scanned_at": scanned_at,
        "policy": {
            "critical_max": 0,
            "high_max": 0,
            "secret_max": 0,
            "medium_blocking": False,
            "low_blocking": False,
            "result": "pass" if policy_pass else "fail",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trivy-report", required=True, type=Path)
    parser.add_argument("--trivy-version", required=True, type=Path)
    parser.add_argument("--trivy-db-metadata", required=True, type=Path)
    parser.add_argument("--syft-version", required=True, type=Path)
    parser.add_argument("--image-manifest", required=True, type=Path)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-image-digest", required=True)
    parser.add_argument(
        "--scanned-at",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        summary = build_summary(
            report=_load(args.trivy_report, "Trivy report"),
            trivy_version=_load(args.trivy_version, "Trivy version"),
            trivy_db_metadata=_load(args.trivy_db_metadata, "Trivy DB metadata"),
            syft_version=_load(args.syft_version, "Syft version"),
            image_manifest=_load(args.image_manifest, "image manifest"),
            expected_source_sha=args.expected_source_sha,
            expected_image_digest=args.expected_image_digest,
            scanned_at=args.scanned_at,
        )
    except ScanContractError as exc:
        raise SystemExit(f"CANDIDATE_SCAN_CONTRACT_BLOCKED: {exc}") from exc
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("[candidate.scan] " + json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0 if summary["policy"]["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
