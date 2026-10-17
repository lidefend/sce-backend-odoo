#!/usr/bin/env python3
"""Parse candidate scans into a fail-closed, identity-bound release record."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
ODOO_REGISTRY_REPOSITORY = "ghcr.io/lidefend/sce-product"
FRONTEND_REGISTRY_REPOSITORY = "ghcr.io/lidefend/sce-frontend"


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


def _identity(
    manifest: dict,
    *,
    label: str,
    publish_status: str,
    repository: str,
    expected_digest: str | None,
    expected_local_image_id: str | None,
    digest_field: str,
    local_field: str,
    refs_field: str,
) -> dict:
    if publish_status == "published":
        if not expected_digest or not IMAGE_DIGEST.fullmatch(expected_digest):
            raise ScanContractError(
                f"published {label} scan requires a registry image digest"
            )
        if manifest.get(digest_field) != expected_digest:
            raise ScanContractError(
                f"scan {label} image digest does not match image manifest"
            )
        expected_ref = f"{repository}@{expected_digest}"
        if manifest.get(refs_field) != [expected_ref, expected_ref]:
            raise ScanContractError(
                f"scan {label} registry references do not match image digest"
            )
        return {
            "image_digest": expected_digest,
            "local_image_id": manifest.get(local_field),
            "identity_kind": "registry_digest",
        }
    if publish_status == "not_published":
        if expected_digest:
            raise ScanContractError(
                f"unpublished {label} scan must not claim a registry digest"
            )
        if manifest.get(digest_field) is not None:
            raise ScanContractError(
                f"unpublished {label} image manifest must not contain a registry digest"
            )
        if not expected_local_image_id or not IMAGE_DIGEST.fullmatch(
            expected_local_image_id
        ):
            raise ScanContractError(
                f"unpublished {label} scan requires a local image ID"
            )
        if manifest.get(local_field) != expected_local_image_id:
            raise ScanContractError(
                f"scan {label} local image ID does not match image manifest"
            )
        if manifest.get(refs_field) not in (None, []):
            raise ScanContractError(
                f"unpublished {label} image manifest must not contain registry refs"
            )
        return {
            "image_digest": None,
            "local_image_id": expected_local_image_id,
            "identity_kind": "local_image_id",
        }
    raise ScanContractError("image manifest publish status is invalid")


def _counts(report: dict, label: str) -> dict:
    if not isinstance(report.get("Results"), list):
        raise ScanContractError(f"Trivy Results is unavailable for {label}")
    counts = {severity: 0 for severity in SEVERITIES}
    counts["SECRET"] = 0
    for result in report["Results"]:
        if not isinstance(result, dict):
            raise ScanContractError(f"Trivy result row is invalid for {label}")
        vulnerabilities = result.get("Vulnerabilities")
        secrets = result.get("Secrets")
        if vulnerabilities is not None and not isinstance(vulnerabilities, list):
            raise ScanContractError(
                f"Trivy vulnerability data is unavailable for {label}"
            )
        if secrets is not None and not isinstance(secrets, list):
            raise ScanContractError(f"Trivy secret data is unavailable for {label}")
        for vulnerability in vulnerabilities or []:
            severity = str(vulnerability.get("Severity") or "").upper()
            if severity in counts:
                counts[severity] += 1
        counts["SECRET"] += len(secrets or [])
    return counts


def _policy(counts: dict) -> dict:
    # Zero is a valid observation only because the scan command is contractually
    # required to request every severity. A missing Results/tool metadata field is
    # rejected above instead of being silently converted to zero.
    policy_pass = counts["CRITICAL"] == counts["HIGH"] == counts["SECRET"] == 0
    return {
        "critical_max": 0,
        "high_max": 0,
        "secret_max": 0,
        "medium_blocking": False,
        "low_blocking": False,
        "result": "pass" if policy_pass else "fail",
    }


def build_summary(
    *,
    report: dict,
    frontend_report: dict,
    trivy_version: dict,
    trivy_db_metadata: dict,
    syft_version: dict,
    image_manifest: dict,
    expected_source_sha: str,
    expected_image_digest: str | None,
    expected_frontend_image_digest: str | None,
    scanned_at: str,
    expected_local_image_id: str | None = None,
    expected_frontend_local_image_id: str | None = None,
) -> dict:
    if not FULL_SHA.fullmatch(expected_source_sha):
        raise ScanContractError("expected source SHA must be a full lowercase SHA")
    if image_manifest.get("source_sha") != expected_source_sha:
        raise ScanContractError("scan source SHA does not match image manifest")
    if image_manifest.get("schema_version") != 3:
        raise ScanContractError("image manifest schema must be v3")
    if image_manifest.get("registry_repository") != ODOO_REGISTRY_REPOSITORY:
        raise ScanContractError("scan registry repository is not approved")
    if image_manifest.get("frontend_registry_repository") != FRONTEND_REGISTRY_REPOSITORY:
        raise ScanContractError("scan frontend registry repository is not approved")
    if not str(image_manifest.get("frontend_image") or "").strip():
        raise ScanContractError("scan frontend image reference is missing")

    publish_status = image_manifest.get("publish_status")
    odoo = _identity(
        image_manifest,
        label="odoo",
        publish_status=publish_status,
        repository=ODOO_REGISTRY_REPOSITORY,
        expected_digest=expected_image_digest,
        expected_local_image_id=expected_local_image_id,
        digest_field="image_digest",
        local_field="local_image_id",
        refs_field="registry_refs",
    )
    frontend = _identity(
        image_manifest,
        label="frontend",
        publish_status=publish_status,
        repository=FRONTEND_REGISTRY_REPOSITORY,
        expected_digest=expected_frontend_image_digest,
        expected_local_image_id=expected_frontend_local_image_id,
        digest_field="frontend_image_digest",
        local_field="frontend_local_image_id",
        refs_field="frontend_registry_refs",
    )

    trivy = _required_text(trivy_version, "Version", "trivy")
    db_updated_at = _required_text(trivy_db_metadata, "UpdatedAt", "trivy_db_metadata")
    syft = _required_text(syft_version, "version", "syft")
    try:
        datetime.fromisoformat(scanned_at.replace("Z", "+00:00"))
        datetime.fromisoformat(db_updated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScanContractError("scan or vulnerability DB timestamp is invalid") from exc

    odoo_counts = _counts(report, "odoo")
    frontend_counts = _counts(frontend_report, "frontend")
    odoo_policy = _policy(odoo_counts)
    frontend_policy = _policy(frontend_counts)
    aggregate_pass = (
        odoo_policy["result"] == "pass" and frontend_policy["result"] == "pass"
    )
    tools = {"trivy": trivy, "syft": syft}
    return {
        "schema_version": "candidate_scan.v3",
        "status": "completed",
        "source_sha": expected_source_sha,
        "image_digest": odoo["image_digest"],
        "local_image_id": odoo["local_image_id"],
        "identity_kind": odoo["identity_kind"],
        "publish_status": publish_status,
        "counts": odoo_counts,
        "tools": tools,
        "vulnerability_db_updated_at": db_updated_at,
        "scanned_at": scanned_at,
        "policy": {
            "critical_max": 0,
            "high_max": 0,
            "secret_max": 0,
            "medium_blocking": False,
            "low_blocking": False,
            "result": "pass" if aggregate_pass else "fail",
        },
        "frontend": {
            "image": str(image_manifest.get("frontend_image")),
            "image_digest": frontend["image_digest"],
            "local_image_id": frontend["local_image_id"],
            "identity_kind": frontend["identity_kind"],
            "counts": frontend_counts,
            "tools": tools,
            "vulnerability_db_updated_at": db_updated_at,
            "scanned_at": scanned_at,
            "policy": frontend_policy,
        },
        "images": {
            "odoo": {
                "image": str(image_manifest.get("image")),
                "counts": odoo_counts,
                "policy": odoo_policy,
            },
            "frontend": {
                "image": str(image_manifest.get("frontend_image")),
                "counts": frontend_counts,
                "policy": frontend_policy,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trivy-report", required=True, type=Path)
    parser.add_argument("--frontend-trivy-report", required=True, type=Path)
    parser.add_argument("--trivy-version", required=True, type=Path)
    parser.add_argument("--trivy-db-metadata", required=True, type=Path)
    parser.add_argument("--syft-version", required=True, type=Path)
    parser.add_argument("--image-manifest", required=True, type=Path)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-image-digest")
    parser.add_argument("--expected-frontend-image-digest")
    parser.add_argument("--expected-local-image-id")
    parser.add_argument("--expected-frontend-local-image-id")
    parser.add_argument(
        "--scanned-at",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        summary = build_summary(
            report=_load(args.trivy_report, "Trivy report"),
            frontend_report=_load(args.frontend_trivy_report, "frontend Trivy report"),
            trivy_version=_load(args.trivy_version, "Trivy version"),
            trivy_db_metadata=_load(args.trivy_db_metadata, "Trivy DB metadata"),
            syft_version=_load(args.syft_version, "Syft version"),
            image_manifest=_load(args.image_manifest, "image manifest"),
            expected_source_sha=args.expected_source_sha,
            expected_image_digest=args.expected_image_digest,
            expected_frontend_image_digest=args.expected_frontend_image_digest,
            expected_local_image_id=args.expected_local_image_id,
            expected_frontend_local_image_id=args.expected_frontend_local_image_id,
            scanned_at=args.scanned_at,
        )
    except ScanContractError as exc:
        raise SystemExit(f"CANDIDATE_SCAN_CONTRACT_BLOCKED: {exc}") from exc
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("[candidate.scan] " + json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0 if summary["policy"]["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
