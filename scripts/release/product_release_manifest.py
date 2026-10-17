#!/usr/bin/env python3
"""Generate and validate the repository-external release manifest v2."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_REPOSITORY = "lidefend/sce-backend-odoo"
EXPECTED_BRANCH = "main"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FIELDS = (
    "repository",
    "branch",
    "release_version",
    "source_sha",
    "image",
    "image_tags",
    "registry_repository",
    "registry_refs",
    "image_digest",
    "local_image_id",
    "frontend_image",
    "frontend_image_tags",
    "frontend_registry_repository",
    "frontend_registry_refs",
    "frontend_image_digest",
    "frontend_local_image_id",
    "frontend_sha256",
    "frontend_sbom_sha256",
    "frontend_archive_sha256",
    "frontend_archive_config_digest",
    "frontend_archive_reload_image_id",
    "oci_revision",
    "container_source_revision",
    "base_image_digests",
    "baseline_checksum",
    "scan",
    "archive_sha256",
    "archive_config_digest",
    "archive_reload_image_id",
    "candidate_status",
    "deployment_status",
)
FRONTEND_REGISTRY_REPOSITORY = "ghcr.io/lidefend/sce-frontend"
BASE_IMAGE_KEYS = {"frontend_builder", "frontend_runtime", "odoo_runtime"}


class ManifestContractError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_release_module():
    path = ROOT / "scripts" / "release" / "product_release.py"
    spec = importlib.util.spec_from_file_location("sce_product_release_manifest_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("product release reader unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestContractError(f"{label} is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise ManifestContractError(f"{label} must be an object")
    return payload


def validate_manifest(
    payload: dict,
    *,
    expected_source_sha: str,
    expected_image_digest: str,
    expected_frontend_image_digest: str,
) -> None:
    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if value is None or value == "" or value == [] or value == {}:
            raise ManifestContractError(f"required manifest field is missing or empty: {field}")
    if payload.get("schema_version") != "product_release_manifest.v4":
        raise ManifestContractError("manifest schema_version must be product_release_manifest.v4")
    if payload["repository"] != EXPECTED_REPOSITORY:
        raise ManifestContractError("manifest repository is not the approved authority")
    if payload["branch"] != EXPECTED_BRANCH:
        raise ManifestContractError("manifest branch must be main")
    if not FULL_SHA.fullmatch(expected_source_sha):
        raise ManifestContractError("expected source SHA must be full lowercase SHA")
    if not DIGEST.fullmatch(expected_image_digest):
        raise ManifestContractError("expected image digest is invalid")
    if not DIGEST.fullmatch(expected_frontend_image_digest):
        raise ManifestContractError("expected frontend image digest is invalid")
    for field in ("source_sha", "oci_revision", "container_source_revision"):
        if payload[field] != expected_source_sha:
            raise ManifestContractError(f"manifest {field} does not match source SHA")
    if payload["image_digest"] != expected_image_digest:
        raise ManifestContractError("manifest image_digest does not match registry digest")
    if payload["registry_repository"] != "ghcr.io/lidefend/sce-product":
        raise ManifestContractError("manifest registry repository is not approved")
    expected_ref = f"{payload['registry_repository']}@{expected_image_digest}"
    if payload["registry_refs"] != [expected_ref, expected_ref]:
        raise ManifestContractError("manifest registry refs do not match image digest")
    if payload["frontend_registry_repository"] != FRONTEND_REGISTRY_REPOSITORY:
        raise ManifestContractError("manifest frontend registry repository is not approved")
    if payload["frontend_image_digest"] != expected_frontend_image_digest:
        raise ManifestContractError(
            "manifest frontend image_digest does not match registry digest"
        )
    frontend_ref = f"{FRONTEND_REGISTRY_REPOSITORY}@{expected_frontend_image_digest}"
    if payload["frontend_registry_refs"] != [frontend_ref, frontend_ref]:
        raise ManifestContractError(
            "manifest frontend registry refs do not match image digest"
        )
    for field in (
        "local_image_id",
        "frontend_local_image_id",
        "archive_config_digest",
        "archive_reload_image_id",
        "frontend_archive_config_digest",
        "frontend_archive_reload_image_id",
    ):
        if not DIGEST.fullmatch(str(payload[field])):
            raise ManifestContractError(f"manifest {field} is invalid")
    tags = payload["image_tags"]
    if not isinstance(tags, list) or len(tags) != 2 or payload["image"] != tags[0]:
        raise ManifestContractError("manifest must contain version and source image tags")
    if not tags[1].endswith(expected_source_sha[:12]):
        raise ManifestContractError("source image tag does not match source SHA")
    frontend_tags = payload["frontend_image_tags"]
    if (
        not isinstance(frontend_tags, list)
        or len(frontend_tags) != 2
        or payload["frontend_image"] != frontend_tags[0]
    ):
        raise ManifestContractError(
            "manifest must contain version and source frontend image tags"
        )
    if not frontend_tags[1].endswith(expected_source_sha[:12]):
        raise ManifestContractError(
            "source frontend image tag does not match source SHA"
        )
    base_images = payload["base_image_digests"]
    if set(base_images) != BASE_IMAGE_KEYS:
        raise ManifestContractError(
            "frontend builder, frontend runtime and Odoo base image digests are required"
        )
    if any(not DIGEST.fullmatch(str(value)) for value in base_images.values()):
        raise ManifestContractError("base image digest is invalid")
    if not CHECKSUM.fullmatch(str(payload["baseline_checksum"])):
        raise ManifestContractError("baseline checksum is invalid")
    if not CHECKSUM.fullmatch(str(payload["archive_sha256"])):
        raise ManifestContractError("archive checksum is invalid")
    for field in ("frontend_sha256", "frontend_sbom_sha256", "frontend_archive_sha256"):
        if not CHECKSUM.fullmatch(str(payload[field])):
            raise ManifestContractError(f"{field} is invalid")
    scan = payload["scan"]
    if not isinstance(scan, dict):
        raise ManifestContractError("scan record is invalid")
    if scan.get("source_sha") != expected_source_sha or scan.get("image_digest") != expected_image_digest:
        raise ManifestContractError("scan identity does not match manifest")
    counts = scan.get("counts")
    if not isinstance(counts, dict) or set(("CRITICAL", "HIGH", "MEDIUM", "LOW", "SECRET")) - set(counts):
        raise ManifestContractError("scan severity counts are incomplete")
    if scan.get("status") != "completed" or (scan.get("policy") or {}).get("result") != "pass":
        raise ManifestContractError("scan is incomplete or policy did not pass")
    frontend_scan = scan.get("frontend")
    if not isinstance(frontend_scan, dict):
        raise ManifestContractError("frontend scan record is invalid")
    if frontend_scan.get("image_digest") != expected_frontend_image_digest:
        raise ManifestContractError("frontend scan identity does not match manifest")
    frontend_counts = frontend_scan.get("counts")
    if (
        not isinstance(frontend_counts, dict)
        or set(("CRITICAL", "HIGH", "MEDIUM", "LOW", "SECRET")) - set(frontend_counts)
    ):
        raise ManifestContractError("frontend scan severity counts are incomplete")
    if (frontend_scan.get("policy") or {}).get("result") != "pass":
        raise ManifestContractError("frontend scan policy did not pass")
    if payload["candidate_status"] != "rc":
        raise ManifestContractError("candidate_status must be rc")
    if payload["deployment_status"] not in {"not_deployed", "blocked"}:
        raise ManifestContractError("deployment_status must be not_deployed or blocked")


def build_manifest(
    *,
    image: dict,
    scan: dict,
    sbom_sha256: str,
    frontend_sbom_sha256: str,
    archive_sha256: str,
    frontend_archive_sha256: str,
    archive_reload_image_id: str,
    frontend_archive_reload_image_id: str,
    release: dict,
    expected_source_sha: str,
) -> dict:
    expected_digest = str(image.get("image_digest") or "")
    expected_frontend_digest = str(image.get("frontend_image_digest") or "")
    payload = {
        "schema_version": "product_release_manifest.v4",
        "repository": EXPECTED_REPOSITORY,
        "branch": EXPECTED_BRANCH,
        "release_version": release["product_version"],
        "product_version": release["product_version"],
        "source_sha": image.get("source_sha"),
        "source_tree_sha": image.get("source_tree_sha"),
        "image": image.get("image"),
        "image_tags": image.get("image_tags"),
        "registry_repository": image.get("registry_repository"),
        "registry_refs": image.get("registry_refs"),
        "image_digest": expected_digest,
        "local_image_id": image.get("local_image_id"),
        "frontend_image": image.get("frontend_image"),
        "frontend_image_tags": image.get("frontend_image_tags"),
        "frontend_registry_repository": image.get("frontend_registry_repository"),
        "frontend_registry_refs": image.get("frontend_registry_refs"),
        "frontend_image_digest": expected_frontend_digest,
        "frontend_local_image_id": image.get("frontend_local_image_id"),
        "frontend_sha256": image.get("frontend_build_sha256"),
        "frontend_sbom_sha256": frontend_sbom_sha256,
        "frontend_archive_sha256": frontend_archive_sha256,
        "frontend_archive_config_digest": image.get("frontend_archive_config_digest"),
        "frontend_archive_reload_image_id": frontend_archive_reload_image_id,
        "oci_revision": image.get("oci_revision"),
        "container_source_revision": image.get("container_source_revision"),
        "base_image_digests": image.get("base_image_digests"),
        "baseline_checksum": image.get("baseline_checksum"),
        "scan": scan,
        "archive_sha256": archive_sha256,
        "archive_config_digest": image.get("archive_config_digest"),
        "archive_reload_image_id": archive_reload_image_id,
        "sbom_sha256": sbom_sha256,
        "module_version_matrix": image.get("module_version_matrix"),
        "tenant_payload_contract": release["contracts"]["tenant_payload"],
        "route_authority_contract": release["contracts"]["route_authority"],
        "built_at": image.get("build_time"),
        "candidate_status": "rc",
        "deployment_status": "not_deployed",
    }
    validate_manifest(
        payload,
        expected_source_sha=expected_source_sha,
        expected_image_digest=expected_digest,
        expected_frontend_image_digest=expected_frontend_digest,
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-manifest", required=True, type=Path)
    parser.add_argument("--sbom", required=True, type=Path)
    parser.add_argument("--frontend-sbom", required=True, type=Path)
    parser.add_argument("--scan-summary", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--frontend-archive", required=True, type=Path)
    parser.add_argument("--archive-reload-digest-file", required=True, type=Path)
    parser.add_argument("--frontend-archive-reload-digest-file", required=True, type=Path)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        image = _load(args.image_manifest, "image manifest")
        scan = _load(args.scan_summary, "scan summary")
        release = load_release_module().load_release_config()
        if image.get("product_version") != release["product_version"]:
            raise ManifestContractError("product version mismatch")
        archive_sha = sha256_file(args.archive)
        if archive_sha != image.get("archive_sha256"):
            raise ManifestContractError("archive checksum does not match image manifest")
        frontend_archive_sha = sha256_file(args.frontend_archive)
        if frontend_archive_sha != image.get("frontend_archive_sha256"):
            raise ManifestContractError(
                "frontend archive checksum does not match image manifest"
            )
        reload_image_id = args.archive_reload_digest_file.read_text(encoding="utf-8").strip()
        frontend_reload_image_id = args.frontend_archive_reload_digest_file.read_text(
            encoding="utf-8"
        ).strip()
        payload = build_manifest(
            image=image,
            scan=scan,
            sbom_sha256=sha256_file(args.sbom),
            frontend_sbom_sha256=sha256_file(args.frontend_sbom),
            archive_sha256=archive_sha,
            frontend_archive_sha256=frontend_archive_sha,
            archive_reload_image_id=reload_image_id,
            frontend_archive_reload_image_id=frontend_reload_image_id,
            release=release,
            expected_source_sha=args.expected_source_sha,
        )
    except (ManifestContractError, OSError) as exc:
        raise SystemExit(f"RELEASE_MANIFEST_CONTRACT_BLOCKED: {exc}") from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha = sha256_file(args.output)
    args.output.with_name("product-release-manifest.sha256").write_text(
        f"{manifest_sha}  {args.output.name}\n", encoding="utf-8"
    )
    print(f"[product.release.manifest] PASS sha256={manifest_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
