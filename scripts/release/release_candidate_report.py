#!/usr/bin/env python3
"""Validate a local immutable candidate and emit its machine-readable readiness report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_REPOSITORY = "ghcr.io/lidefend/sce-product"
EXPECTED_REQUIRED_CHECKS = {
    "public_guard",
    "professional_authorization",
    "professional_quality_gate",
}


class CandidateReportError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateReportError(f"{label} is missing or invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise CandidateReportError(f"{label} must be a JSON object")
    return payload


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_build_artifacts(
    artifacts: Path,
    *,
    expected_source_sha: str,
    expected_source_tree: str,
    expected_version: str,
    expected_pipeline_contract: str,
) -> dict:
    if not FULL_SHA.fullmatch(expected_source_sha):
        raise CandidateReportError("expected source SHA must be full lowercase SHA")
    if not FULL_SHA.fullmatch(expected_source_tree):
        raise CandidateReportError("expected source tree must be full lowercase SHA")
    if not CHECKSUM.fullmatch(expected_pipeline_contract):
        raise CandidateReportError("expected pipeline contract digest is invalid")
    try:
        recorded_contract = (artifacts / "candidate-contract.sha256").read_text(
            encoding="utf-8"
        ).strip()
    except OSError as exc:
        raise CandidateReportError("candidate tool contract binding is missing") from exc
    if recorded_contract != expected_pipeline_contract:
        raise CandidateReportError("candidate tool contract binding differs")

    image_manifest = load_json(artifacts / "image-manifest.json", "image manifest")
    required = {
        "candidate-image.tar",
        "frontend-build.sha256",
        "image-manifest.json",
        "reloaded-image-id.txt",
    }
    missing = sorted(name for name in required if not (artifacts / name).is_file())
    if missing:
        raise CandidateReportError(f"build outputs are incomplete: {', '.join(missing)}")
    if image_manifest.get("schema_version") != 2:
        raise CandidateReportError("image manifest schema must be v2")
    for field in ("source_sha", "oci_revision", "container_source_revision"):
        if image_manifest.get(field) != expected_source_sha:
            raise CandidateReportError(f"image manifest {field} does not match source SHA")
    if image_manifest.get("source_tree_sha") != expected_source_tree:
        raise CandidateReportError("image manifest source tree does not match")
    if image_manifest.get("product_version") != expected_version:
        raise CandidateReportError("image manifest product version does not match")
    if image_manifest.get("registry_repository") != EXPECTED_REPOSITORY:
        raise CandidateReportError("candidate registry repository is not approved")
    if image_manifest.get("publish_status") != "not_published":
        raise CandidateReportError("candidate must remain unpublished")
    if image_manifest.get("image_digest") is not None:
        raise CandidateReportError("unpublished candidate must not claim a registry digest")

    local_image_id = str(image_manifest.get("local_image_id") or "")
    reloaded_image_id = (artifacts / "reloaded-image-id.txt").read_text(
        encoding="utf-8"
    ).strip()
    if not DIGEST.fullmatch(local_image_id) or reloaded_image_id != local_image_id:
        raise CandidateReportError("archive reload image ID does not match built image")

    archive = artifacts / "candidate-image.tar"
    if archive.stat().st_size <= 0:
        raise CandidateReportError("candidate archive is empty")
    archive_sha = sha256_file(archive)
    if archive_sha != image_manifest.get("archive_sha256"):
        raise CandidateReportError("candidate archive checksum does not match image manifest")
    frontend_sha = (artifacts / "frontend-build.sha256").read_text(
        encoding="utf-8"
    ).strip()
    if not CHECKSUM.fullmatch(frontend_sha):
        raise CandidateReportError("frontend build checksum is invalid")
    if frontend_sha != image_manifest.get("frontend_build_sha256"):
        raise CandidateReportError("frontend checksum does not match image manifest")

    expected_tags = [
        f"{EXPECTED_REPOSITORY}:{expected_version}",
        f"{EXPECTED_REPOSITORY}:sha-{expected_source_sha[:12]}",
    ]
    if image_manifest.get("image_tags") != expected_tags:
        raise CandidateReportError("candidate image tags do not match version/source identity")
    try:
        with tarfile.open(archive, "r") as handle:
            rows = json.load(handle.extractfile("manifest.json"))
    except (OSError, KeyError, json.JSONDecodeError, tarfile.TarError) as exc:
        raise CandidateReportError("candidate archive is not independently readable") from exc
    if not isinstance(rows, list) or len(rows) != 1:
        raise CandidateReportError("candidate archive must contain exactly one image")
    if rows[0].get("RepoTags") != expected_tags:
        raise CandidateReportError("candidate archive tags do not match image manifest")
    archive_config = str(rows[0].get("Config") or "")
    if archive_config != str(image_manifest.get("archive_config_digest") or "").replace(
        "sha256:", "blobs/sha256/", 1
    ):
        raise CandidateReportError("candidate archive config does not match image manifest")
    return image_manifest


def build_ready_report(
    artifacts: Path,
    *,
    attempt_id: str,
    attempt_number: int,
    retry_of_attempt_id: str | None,
    created_at: str,
    expected_source_sha: str,
    expected_source_tree: str,
    expected_version: str,
    expected_pipeline_contract: str,
    remote_main: dict[str, str],
    required_checks: dict[str, str],
    required_checks_head_sha: str,
    image_architecture: str,
) -> dict:
    image = validate_build_artifacts(
        artifacts,
        expected_source_sha=expected_source_sha,
        expected_source_tree=expected_source_tree,
        expected_version=expected_version,
        expected_pipeline_contract=expected_pipeline_contract,
    )
    scan = load_json(artifacts / "security-summary.json", "security summary")
    sbom_path = artifacts / "sbom.cyclonedx.json"
    sbom = load_json(sbom_path, "CycloneDX SBOM")

    if scan.get("status") != "completed" or scan.get("source_sha") != expected_source_sha:
        raise CandidateReportError("security scan is incomplete or source identity differs")
    if scan.get("identity_kind") != "local_image_id":
        raise CandidateReportError("pre-publication scan must bind the local immutable image ID")
    if scan.get("local_image_id") != image.get("local_image_id"):
        raise CandidateReportError("security scan image identity does not match build")
    if scan.get("image_digest") is not None or scan.get("publish_status") != "not_published":
        raise CandidateReportError("pre-publication scan must not claim registry publication")
    counts = scan.get("counts")
    if not isinstance(counts, dict):
        raise CandidateReportError("security scan counts are unavailable")
    if any(int(counts.get(key, -1)) != 0 for key in ("CRITICAL", "HIGH", "SECRET")):
        raise CandidateReportError("security policy blocks the candidate")
    if (scan.get("policy") or {}).get("result") != "pass":
        raise CandidateReportError("security scan policy did not pass")
    if sbom.get("bomFormat") != "CycloneDX":
        raise CandidateReportError("SBOM is not a CycloneDX document")
    if set(remote_main) != {"github", "gitee"} or set(remote_main.values()) != {
        expected_source_sha
    }:
        raise CandidateReportError("GitHub/Gitee main identities are not aligned")
    if (
        set(required_checks) != EXPECTED_REQUIRED_CHECKS
        or set(required_checks.values()) != {"success"}
    ):
        raise CandidateReportError("required checks are incomplete")
    if not FULL_SHA.fullmatch(required_checks_head_sha):
        raise CandidateReportError("required-check head SHA is invalid")
    if image_architecture != "amd64":
        raise CandidateReportError("candidate image architecture must be amd64")

    files = {
        name: sha256_file(artifacts / name)
        for name in (
            "candidate-image.tar",
            "candidate-contract.sha256",
            "frontend-build.sha256",
            "image-manifest.json",
            "reloaded-image-id.txt",
            "sbom.cyclonedx.json",
            "security-summary.json",
            "syft-version.json",
            "trivy-db-metadata.json",
            "trivy-version.json",
            "trivy.json",
        )
    }
    return {
        "schema_version": "release_candidate_report.v1",
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "retry_of_attempt_id": retry_of_attempt_id,
        "created_at": created_at,
        "finished_at": utc_now(),
        "status": "ready",
        "CANDIDATE_READY": True,
        "source": {
            "commit_sha": expected_source_sha,
            "tree_sha": expected_source_tree,
            "product_version": expected_version,
            "pipeline_contract_sha256": expected_pipeline_contract,
            "remote_main": remote_main,
            "required_checks": required_checks,
            "required_checks_head_sha": required_checks_head_sha,
        },
        "image": {
            "reference": image["image"],
            "tags": image["image_tags"],
            "local_image_id": image["local_image_id"],
            "oci_revision": image["oci_revision"],
            "architecture": f"linux/{image_architecture}",
            "publish_status": "not_published",
        },
        "verification": {
            "archive_reload": "pass",
            "frontend_digest": "pass",
            "security_scan": "pass",
            "sbom": "pass",
            "critical": counts["CRITICAL"],
            "high": counts["HIGH"],
            "secret": counts["SECRET"],
        },
        "artifacts": {
            "directory": str(artifacts),
            "sha256": files,
        },
        "external_effects": {
            "registry_push": False,
            "git_tag": False,
            "release_publication": False,
            "deployment": False,
        },
        "completed_at": utc_now(),
    }


def write_ready_outputs(output: Path, report: dict) -> None:
    atomic_write_json(output, report)
    summary = output.with_name("release-summary.txt")
    atomic_write_text(
        summary,
        "\n".join(
            (
                "CANDIDATE_READY=true",
                f"VERSION={report['source']['product_version']}",
                f"SOURCE_SHA={report['source']['commit_sha']}",
                f"SOURCE_TREE={report['source']['tree_sha']}",
                f"IMAGE={report['image']['reference']}",
                f"IMAGE_ID={report['image']['local_image_id']}",
                f"EVIDENCE={output}",
                "PUBLISHED=false",
                "DEPLOYED=false",
            )
        )
        + "\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--attempt-number", required=True, type=int)
    parser.add_argument("--retry-of-attempt-id")
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-source-tree", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-pipeline-contract", required=True)
    parser.add_argument("--github-main-sha", required=True)
    parser.add_argument("--gitee-main-sha", required=True)
    parser.add_argument("--required-check", action="append", default=[])
    parser.add_argument("--required-checks-head-sha", required=True)
    parser.add_argument("--image-architecture", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        checks = dict(item.split("=", 1) for item in args.required_check)
        report = build_ready_report(
            args.artifacts,
            attempt_id=args.attempt_id,
            attempt_number=args.attempt_number,
            retry_of_attempt_id=args.retry_of_attempt_id,
            created_at=args.created_at,
            expected_source_sha=args.expected_source_sha,
            expected_source_tree=args.expected_source_tree,
            expected_version=args.expected_version,
            expected_pipeline_contract=args.expected_pipeline_contract,
            remote_main={
                "github": args.github_main_sha,
                "gitee": args.gitee_main_sha,
            },
            required_checks=checks,
            required_checks_head_sha=args.required_checks_head_sha,
            image_architecture=args.image_architecture,
        )
        write_ready_outputs(args.output, report)
    except (CandidateReportError, OSError, ValueError) as exc:
        raise SystemExit(f"RELEASE_CANDIDATE_REPORT_BLOCKED: {exc}") from exc
    print(f"[release.candidate.report] CANDIDATE_READY=true evidence={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
