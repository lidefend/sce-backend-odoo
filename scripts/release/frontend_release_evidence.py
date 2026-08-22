#!/usr/bin/env python3
"""Build and verify a tamper-detectable frontend release evidence bundle."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/releases/frontend_release_evidence_bundle_v1.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
QUALIFIED = "QUALIFIED_FOR_FREEZE_REVIEW"
SENSITIVE_PATTERNS = (
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"ghp_[A-Za-z0-9_]{30,}"),
    re.compile(rb"sk-[A-Za-z0-9_-]{32,}"),
    re.compile(rb"AKIA[A-Z0-9]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(rb"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~+/-]{16,}"),
    re.compile(rb"(?i)(?:postgres|postgresql)://[^/\s:@]+:[^@\s/]+@"),
    re.compile(rb'''(?i)["']api_key["']\s*:\s*["'][0-9a-f]{40}["']'''),
)
SENSITIVE_NAMES = {".env", "storageState.json", "cookies.json"}


class EvidenceBundleError(ValueError):
    pass


def fail(reason: str) -> None:
    raise EvidenceBundleError(reason)


def read_json(path: Path, reason: str = "JSON_INVALID") -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail(reason)
    if not isinstance(value, dict):
        fail(reason)
    return value


def authoritative_navigation_total() -> int:
    policy = read_json(
        ROOT / "config/frontend/authoritative_navigation.json",
        "AUTHORITATIVE_NAVIGATION_POLICY_INVALID",
    )
    roles = policy.get("roles") or {}
    total = 0
    for role, row in roles.items():
        leaf_keys = (row or {}).get("leaf_keys") or []
        count = int((row or {}).get("expected_count") or 0)
        if count <= 0 or count != len(leaf_keys):
            fail(f"AUTHORITATIVE_NAVIGATION_POLICY_INVALID:{role}")
        total += count
    if total <= 0:
        fail("AUTHORITATIVE_NAVIGATION_POLICY_EMPTY")
    return total


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scan_sensitive_paths(paths: list[Path]) -> None:
    for root in paths:
        candidates = [root] if root.is_file() else [item for item in root.rglob("*") if item.is_file()]
        for path in candidates:
            if path.name in SENSITIVE_NAMES or path.suffix in {".pem", ".key", ".p12", ".dump"}:
                fail(f"SENSITIVE_FILE_FORBIDDEN:{path.name}")
            try:
                payload = path.read_bytes()
            except OSError:
                fail("SENSITIVE_SCAN_READ_FAILED")
            if any(pattern.search(payload) for pattern in SENSITIVE_PATTERNS):
                fail(f"SENSITIVE_CONTENT_DETECTED:{path.name}")


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def safe_relative(name: str) -> str:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
        or "\\" in name
        or "\x00" in name
    ):
        fail("ARCHIVE_PATH_UNSAFE")
    return path.as_posix()


def validate_archive_members(archive: Path, policy: dict[str, Any]) -> list[zipfile.ZipInfo]:
    try:
        members = zipfile.ZipFile(archive).infolist()
    except (OSError, zipfile.BadZipFile):
        fail("ARCHIVE_INVALID")
    limits = policy["archive_limits"]
    if len(members) > int(limits["maximum_files"]):
        fail("ARCHIVE_FILE_LIMIT")
    names: set[str] = set()
    folded: set[str] = set()
    total_size = 0
    for member in members:
        name = safe_relative(member.filename.rstrip("/"))
        if name in names or name.casefold() in folded:
            fail("ARCHIVE_DUPLICATE_NAME")
        names.add(name)
        folded.add(name.casefold())
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            fail("ARCHIVE_SYMLINK_FORBIDDEN")
        total_size += member.file_size
        if member.compress_size == 0 and member.file_size:
            fail("ARCHIVE_COMPRESSION_RATIO")
        if member.compress_size and member.file_size / member.compress_size > int(
            limits["maximum_compression_ratio"]
        ):
            fail("ARCHIVE_COMPRESSION_RATIO")
    if total_size > int(limits["maximum_uncompressed_bytes"]):
        fail("ARCHIVE_SIZE_LIMIT")
    return members


def extract_archive(archive: Path, target: Path, policy: dict[str, Any]) -> Path:
    members = validate_archive_members(archive, policy)
    with zipfile.ZipFile(archive) as source:
        for member in members:
            if member.is_dir():
                continue
            destination = target / safe_relative(member.filename)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    return target


def frontend_sources(root: Path) -> dict[str, Path]:
    return {
        "frontend/frontend-release-report.json": root / "frontend-release-audit/report.json",
        "frontend/frontend-release-gate-result.json": root
        / "frontend-release-audit/gate-result.json",
        "frontend/navigation-report.json": root / "frontend-page-identity/navigation-report.json",
        "frontend/accessibility.json": root / "frontend-delivery-hardening/accessibility.json",
        "frontend/performance.json": root / "frontend-delivery-hardening/performance.json",
        "frontend/browser-journeys.json": root / "frontend-delivery-hardening/report.json",
        "frontend/responsive.json": root / "frontend-delivery-hardening/responsive.json",
        "frontend/recovery.json": root / "frontend-delivery-hardening/error-recovery.json",
    }


def check_run_id(details_url: str) -> str:
    match = re.search(r"/actions/runs/(\d+)/job/\d+$", details_url)
    if not match:
        fail("CHECK_DETAILS_URL_INVALID")
    return match.group(1)


def normalize_checks(
    raw_checks: dict[str, Any],
    run_metadata: dict[str, Any],
    statuses: dict[str, Any],
    artifacts: dict[str, Any],
    *,
    candidate_sha: str,
    candidate_tree: str,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = raw_checks.get("check_runs")
    if not isinstance(rows, list):
        fail("CHECK_RUNS_INVALID")
    required = policy["required_checks"]
    result: list[dict[str, Any]] = []
    for name in required:
        matches = [row for row in rows if row.get("name") == name]
        if len(matches) != 1:
            fail(f"CHECK_{name.upper()}_{'MISSING' if not matches else 'DUPLICATE'}")
        row = matches[0]
        app = row.get("app") or {}
        if (
            row.get("status") != "completed"
            or row.get("conclusion") != "success"
            or row.get("head_sha") != candidate_sha
            or app.get("slug") != "github-actions"
        ):
            fail(f"CHECK_{name.upper()}_UNTRUSTED")
        run_id = check_run_id(str(row.get("details_url") or ""))
        run = run_metadata.get(run_id)
        if not isinstance(run, dict):
            fail(f"CHECK_{name.upper()}_RUN_METADATA_MISSING")
        if (
            str(run.get("id")) != run_id
            or run.get("head_sha") != candidate_sha
            or run.get("event") != "push"
            or run.get("head_branch") != "main"
            or run.get("conclusion") != "success"
        ):
            fail(f"CHECK_{name.upper()}_RUN_IDENTITY_MISMATCH")
        normalized = {
                "check_name": name,
                "conclusion": "success",
                "workflow": run.get("name"),
                "job_id": name,
                "run_id": run_id,
                "run_attempt": str(run.get("run_attempt")),
                "event": run.get("event"),
                "head_sha": candidate_sha,
                "tree_sha": candidate_tree,
                "head_branch": run.get("head_branch"),
                "started_at": row.get("started_at"),
                "completed_at": row.get("completed_at"),
                "url": row.get("details_url"),
                "app_slug": app.get("slug"),
                "manual_commit_status": False,
                "verification_result": "PASS",
            }
        if name == "frontend_release_gate":
            expected_artifact = (
                f"frontend-release-evidence-{run_id}-{run.get('run_attempt')}-{candidate_sha}"
            )
            matches_artifact = [
                item
                for item in artifacts.get("artifacts") or []
                if item.get("name") == expected_artifact
                and str((item.get("workflow_run") or {}).get("id")) == run_id
                and item.get("expired") is False
            ]
            if len(matches_artifact) != 1:
                fail("FRONTEND_SOURCE_ARTIFACT_IDENTITY")
            artifact = matches_artifact[0]
            digest = str(artifact.get("digest") or "")
            if digest and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                fail("FRONTEND_SOURCE_ARTIFACT_DIGEST")
            normalized["artifact"] = {
                "id": str(artifact.get("id")),
                "name": expected_artifact,
                "digest": digest or "GITHUB_DIGEST_NOT_EXPOSED",
                "size_in_bytes": artifact.get("size_in_bytes"),
                "created_at": artifact.get("created_at"),
            }
        result.append(normalized)
    manual = statuses.get("statuses")
    if not isinstance(manual, list):
        fail("COMMIT_STATUSES_INVALID")
    required_statuses = [row for row in manual if row.get("context") in required]
    if required_statuses:
        fail("MANUAL_COMMIT_STATUS_FOR_REQUIRED_CHECK")
    return result


def validate_frontend_reports(files: dict[str, Path], sha: str, tree: str) -> dict[str, Any]:
    payloads = {name: read_json(path, "FRONTEND_EVIDENCE_INVALID") for name, path in files.items()}
    release = payloads["frontend/frontend-release-report.json"]
    gate = payloads["frontend/frontend-release-gate-result.json"]
    if (
        release.get("schema_version") != "frontend-release-audit/v2"
        or release.get("result") != "PASS"
        or release.get("git_sha") != sha
        or release.get("git_tree") != tree
        or release.get("blocking_failures")
        or release.get("missing_evidence")
    ):
        fail("FRONTEND_RELEASE_REPORT_NOT_PASS")
    if (
        gate.get("result") != "PASS"
        or gate.get("git_sha") != sha
        or gate.get("git_tree") != tree
    ):
        fail("FRONTEND_RELEASE_GATE_RESULT_NOT_PASS")
    sections = release.get("sections") or {}
    if not sections or any((row or {}).get("result") != "PASS" for row in sections.values()):
        fail("FRONTEND_REQUIRED_SECTION_NOT_PASS")
    for name, payload in payloads.items():
        if payload.get("git_sha") != sha:
            fail(f"FRONTEND_EVIDENCE_SHA_MISMATCH:{name}")
    navigation = payloads["frontend/navigation-report.json"]
    total = navigation.get("total") or {}
    expected_navigation_total = authoritative_navigation_total()
    if (
        total.get("result") != "PASS"
        or int(total.get("expected_count", -1)) != expected_navigation_total
        or int(total.get("actual_count", -1)) != expected_navigation_total
        or int(total.get("matched_count", -1)) != expected_navigation_total
        or total.get("missing_leaf_keys")
        or total.get("unexpected_leaf_keys")
        or total.get("duplicate_leaf_keys")
        or total.get("invalid_leaf_keys")
    ):
        fail("NAVIGATION_IDENTITY_NOT_AUTHORITATIVE_TOTAL")
    accessibility = payloads["frontend/accessibility.json"]
    if (
        accessibility.get("result") != "PASS"
        or int(accessibility.get("critical", -1)) != 0
        or int(accessibility.get("serious", -1)) != 0
        or not accessibility.get("scans")
    ):
        fail("ACCESSIBILITY_NOT_PASS")
    performance = payloads["frontend/performance.json"]
    if performance.get("result") != "PASS" or not performance.get("budget_source"):
        fail("PERFORMANCE_NOT_PASS")
    scenarios = performance.get("scenarios") or {}
    if not scenarios or any(int((row or {}).get("sample_count", 0)) < 5 for row in scenarios.values()):
        fail("PERFORMANCE_SAMPLES_INSUFFICIENT")
    browser = payloads["frontend/browser-journeys.json"]
    runtime = browser.get("runtime") or {}
    if (
        browser.get("pass") is not True
        or not browser.get("journeys")
        or any(value != "PASS" for value in browser["journeys"].values())
        or any(runtime.get(name) for name in ("console", "pageerror", "unhandled", "http"))
    ):
        fail("BROWSER_JOURNEYS_NOT_PASS")
    responsive = payloads["frontend/responsive.json"]
    if (
        not responsive.get("pages")
        or int(responsive.get("horizontal_overflow", -1)) != 0
        or any(row.get("pass") is not True for row in responsive["pages"])
    ):
        fail("RESPONSIVE_NOT_PASS")
    recovery = payloads["frontend/recovery.json"]
    if any(
        recovery.get(name) != "PASS"
        for name in ("network_retry", "conflict_refresh", "session_expired")
    ):
        fail("RECOVERY_NOT_PASS")
    return {
        "result": "PASS",
        "required_sections": sorted(sections),
        "report_sha256": sha256_file(files["frontend/frontend-release-report.json"]),
    }


def create_build_manifest(
    dist: Path,
    *,
    candidate_sha: str,
    candidate_tree: str,
    build_metadata: dict[str, Any],
) -> dict[str, Any]:
    if not dist.is_dir():
        fail("BUILD_OUTPUT_MISSING")
    output_files = []
    for path in sorted(item for item in dist.rglob("*") if item.is_file()):
        relative = path.relative_to(dist).as_posix()
        output_files.append(
            {"path": relative, "size": path.stat().st_size, "sha256": sha256_file(path)}
        )
    if not output_files:
        fail("BUILD_OUTPUT_EMPTY")
    lockfile = ROOT / "frontend/pnpm-lock.yaml"
    if not lockfile.is_file():
        fail("LOCKFILE_MISSING")
    return {
        "schema_version": "frontend-build-identity/v1",
        "candidate_sha": candidate_sha,
        "candidate_tree": candidate_tree,
        "package_manager": "pnpm",
        "lockfile": "frontend/pnpm-lock.yaml",
        "lockfile_sha256": sha256_file(lockfile),
        "node_version": build_metadata.get("node_version"),
        "pnpm_version": build_metadata.get("pnpm_version"),
        "frontend_package_version": build_metadata.get("frontend_package_version"),
        "build_command": "pnpm -C frontend/apps/web build",
        "build_started_at": build_metadata.get("build_started_at"),
        "build_completed_at": build_metadata.get("build_completed_at"),
        "build_exit_code": 0,
        "production_mode": True,
        "source_map_policy": build_metadata.get("source_map_policy", "repository-build-config"),
        "public_environment_keys": build_metadata.get("public_environment_keys", []),
        "sensitive_value_scan": "PASS",
        "output_file_count": len(output_files),
        "output_files": output_files,
    }


def verify_branch_protection(payload: dict[str, Any], policy: dict[str, Any]) -> None:
    if payload.get("enforcement") != "active" or payload.get("bypass_actors"):
        fail("BRANCH_PROTECTION_UNTRUSTED")
    contexts: list[str] = []
    for rule in payload.get("rules") or []:
        if rule.get("type") == "required_status_checks":
            contexts.extend(
                item.get("context") for item in (rule.get("parameters") or {}).get("required_status_checks") or []
            )
    if sorted(contexts) != sorted(policy["required_checks"]):
        fail("BRANCH_PROTECTION_REQUIRED_CHECKS_MISMATCH")


def generate_bundle(
    output: Path,
    *,
    frontend_root: Path,
    dist: Path,
    raw_checks: Path,
    run_metadata: Path,
    statuses: Path,
    artifacts: Path,
    branch_protection: Path,
    build_metadata: Path,
    candidate_sha: str,
    candidate_tree: str,
    source_run_id: str,
    source_run_attempt: str,
) -> dict[str, Any]:
    policy = read_json(POLICY_PATH, "POLICY_INVALID")
    if not HEX40.fullmatch(candidate_sha) or not HEX40.fullmatch(candidate_tree):
        fail("CANDIDATE_IDENTITY_INVALID")
    if git_value("rev-parse", "HEAD") != candidate_sha or git_value("rev-parse", "HEAD^{tree}") != candidate_tree:
        fail("CHECKOUT_IDENTITY_MISMATCH")
    sources = frontend_sources(frontend_root)
    if any(not path.is_file() for path in sources.values()):
        fail("FRONTEND_REQUIRED_EVIDENCE_MISSING")
    frontend_summary = validate_frontend_reports(sources, candidate_sha, candidate_tree)
    check_rows = normalize_checks(
        read_json(raw_checks, "CHECK_RUNS_INVALID"),
        read_json(run_metadata, "RUN_METADATA_INVALID"),
        read_json(statuses, "COMMIT_STATUSES_INVALID"),
        read_json(artifacts, "ARTIFACT_METADATA_INVALID"),
        candidate_sha=candidate_sha,
        candidate_tree=candidate_tree,
        policy=policy,
    )
    protection = read_json(branch_protection, "BRANCH_PROTECTION_INVALID")
    verify_branch_protection(protection, policy)
    build = create_build_manifest(
        dist,
        candidate_sha=candidate_sha,
        candidate_tree=candidate_tree,
        build_metadata=read_json(build_metadata, "BUILD_METADATA_INVALID"),
    )
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name, source in sources.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    scan_sensitive_paths([*sources.values(), dist])
    governance_names = {
        "public_guard": "public-guard.json",
        "professional_authorization": "professional-authorization.json",
        "professional_quality_gate": "professional-quality-gate.json",
        "frontend_release_gate": "frontend-release-gate.json",
    }
    for row in check_rows:
        write_json(output / "governance" / governance_names[row["check_name"]], row)
    write_json(output / "governance/branch-protection.json", protection)
    write_json(output / "governance/manual-statuses.json", {"statuses": []})
    write_json(output / "checks.json", {"schema_version": "release-checks/v1", "checks": check_rows})
    write_json(output / "build/build-manifest.json", build)
    build_output = output / "build/output"
    shutil.copytree(dist, build_output)
    bundle_contents: list[dict[str, Any]] = []
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        relative = path.relative_to(output).as_posix()
        bundle_contents.append(
            {"path": relative, "size": path.stat().st_size, "sha256": sha256_file(path)}
        )
    checks_map = {row["check_name"]: row for row in check_rows}
    manifest = {
        "schema_version": policy["bundle_schema"],
        "evidence_bundle_version": "1",
        "qualification_state": QUALIFIED,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repository": policy["repository"],
        "branch": "main",
        "candidate_sha": candidate_sha,
        "candidate_tree": candidate_tree,
        "commit_timestamp": git_value("show", "-s", "--format=%cI", candidate_sha),
        "source_event": "workflow_dispatch",
        "source_workflow": "frontend_release_evidence_bundle",
        "source_run_id": source_run_id,
        "source_run_attempt": source_run_attempt,
        "source_job": "frontend_release_evidence_bundle",
        "source_actor_type": "repository_owner_dispatch",
        "checks": checks_map,
        "required_evidence": sorted(
            ["checks.json", *policy["required_frontend_files"], *policy["required_governance_files"], *policy["required_build_files"]]
        ),
        "optional_evidence": [],
        "build_identity": {
            "manifest": "build/build-manifest.json",
            "output_file_count": build["output_file_count"],
            "lockfile_sha256": build["lockfile_sha256"],
        },
        "bundle_digest_algorithm": "SHA-256",
        "bundle_contents": bundle_contents,
        "policy_versions": {
            "evidence": policy["schema_version"],
            "evidence_policy_sha256": sha256_file(POLICY_PATH),
            "frontend_gate": "frontend-release-gate-policy/v1",
            "frontend_gate_policy_sha256": sha256_file(
                ROOT / "config/ci/frontend_release_gate_v1.json"
            ),
        },
        "reason_codes": [],
        "known_limitations": [
            "SHA-256 detects modification but is not a cryptographic signature",
            "non-frontend gate internals are represented by immutable GitHub Actions check/run metadata",
        ],
        "prohibited_claims": {
            "release_candidate_frozen": False,
            "production_deployment_authorized": False,
            "production_deployed": False,
            "release_tag_created": False,
            "github_release_created": False,
        },
        "database_access": {"daily": False, "production": False},
        "sensitive_data_scan": {"result": "PASS"},
        "frontend_summary": frontend_summary,
        "verification_command": (
            "python3 scripts/verify/frontend_release_evidence_bundle.py "
            f"--bundle <path> --expected-sha {candidate_sha} --expected-tree {candidate_tree}"
        ),
    }
    write_json(output / "manifest.json", manifest)
    all_files = sorted(item for item in output.rglob("*") if item.is_file())
    sums = [
        f"{sha256_file(path)}  {path.relative_to(output).as_posix()}"
        for path in all_files
        if path.relative_to(output).as_posix() != "digests/SHA256SUMS"
    ]
    sums_path = output / "digests/SHA256SUMS"
    sums_path.parent.mkdir(parents=True, exist_ok=True)
    sums_path.write_text("\n".join(sums) + "\n", encoding="utf-8")
    return manifest


def create_deterministic_zip(source: Path, archive: Path) -> str:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            name = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            target.writestr(info, path.read_bytes())
    return sha256_file(archive)


def verify_bundle_directory(
    bundle: Path, expected_sha: str, expected_tree: str
) -> dict[str, Any]:
    policy = read_json(POLICY_PATH, "POLICY_INVALID")
    manifest = read_json(bundle / "manifest.json", "MANIFEST_MISSING_OR_INVALID")
    if manifest.get("schema_version") != policy["bundle_schema"]:
        fail("SCHEMA_UNSUPPORTED")
    if manifest.get("candidate_sha") != expected_sha:
        fail("CANDIDATE_SHA_MISMATCH")
    if manifest.get("candidate_tree") != expected_tree:
        fail("CANDIDATE_TREE_MISMATCH")
    if manifest.get("branch") != "main" or manifest.get("source_event") != "workflow_dispatch":
        fail("SOURCE_IDENTITY_INVALID")
    if manifest.get("qualification_state") not in policy["allowed_qualification_states"]:
        fail("QUALIFICATION_STATE_FORBIDDEN")
    if manifest.get("qualification_state") != QUALIFIED:
        fail("QUALIFICATION_NOT_GRANTED")
    claims = manifest.get("prohibited_claims") or {}
    if any(value is not False for value in claims.values()):
        fail("PROHIBITED_CLAIM_ENABLED")
    database = manifest.get("database_access") or {}
    if database.get("daily") is not False or database.get("production") is not False:
        fail("DATABASE_ACCESS_FORBIDDEN")
    if (manifest.get("sensitive_data_scan") or {}).get("result") != "PASS":
        fail("SENSITIVE_DATA_SCAN_FAILED")
    expected_files = {row["path"]: row for row in manifest.get("bundle_contents") or []}
    required = set(manifest.get("required_evidence") or [])
    if not required.issubset(expected_files):
        fail("REQUIRED_EVIDENCE_NOT_DECLARED")
    actual_files = {
        path.relative_to(bundle).as_posix(): path
        for path in bundle.rglob("*")
        if path.is_file()
        and path.relative_to(bundle).as_posix()
        not in {"manifest.json", "digests/SHA256SUMS"}
    }
    if set(actual_files) != set(expected_files):
        fail("BUNDLE_FILE_SET_MISMATCH")
    for name, row in expected_files.items():
        path = actual_files[name]
        if path.stat().st_size != int(row.get("size", -1)) or sha256_file(path) != row.get("sha256"):
            fail(f"FILE_DIGEST_MISMATCH:{name}")
    sums_path = bundle / "digests/SHA256SUMS"
    if not sums_path.is_file():
        fail("SHA256SUMS_MISSING")
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if not separator or not HEX64.fullmatch(digest) or not (bundle / safe_relative(name)).is_file():
            fail("SHA256SUMS_INVALID")
        if sha256_file(bundle / name) != digest:
            fail(f"SHA256SUMS_MISMATCH:{name}")
    checks = read_json(bundle / "checks.json", "CHECKS_INVALID").get("checks") or []
    if len(checks) != len(policy["required_checks"]):
        fail("REQUIRED_CHECK_COUNT")
    for name in policy["required_checks"]:
        matches = [row for row in checks if row.get("check_name") == name]
        if len(matches) != 1:
            fail(f"CHECK_{name.upper()}_COUNT")
        row = matches[0]
        if (
            row.get("conclusion") != "success"
            or row.get("event") != "push"
            or row.get("head_sha") != expected_sha
            or row.get("tree_sha") != expected_tree
            or row.get("app_slug") != "github-actions"
            or row.get("manual_commit_status") is not False
        ):
            fail(f"CHECK_{name.upper()}_INVALID")
        manifest_check = (manifest.get("checks") or {}).get(name)
        if manifest_check != row:
            fail(f"CHECK_{name.upper()}_MANIFEST_MISMATCH")
        governance_names = {
            "public_guard": "public-guard.json",
            "professional_authorization": "professional-authorization.json",
            "professional_quality_gate": "professional-quality-gate.json",
            "frontend_release_gate": "frontend-release-gate.json",
        }
        if read_json(
            bundle / "governance" / governance_names[name],
            "GOVERNANCE_CHECK_INVALID",
        ) != row:
            fail(f"CHECK_{name.upper()}_GOVERNANCE_MISMATCH")
    statuses = read_json(
        bundle / "governance/manual-statuses.json", "MANUAL_STATUSES_INVALID"
    )
    if statuses.get("statuses") != []:
        fail("MANUAL_COMMIT_STATUS_FOR_REQUIRED_CHECK")
    verify_branch_protection(
        read_json(
            bundle / "governance/branch-protection.json",
            "BRANCH_PROTECTION_INVALID",
        ),
        policy,
    )
    frontend_files = {
        name: bundle / name for name in policy["required_frontend_files"]
    }
    validate_frontend_reports(frontend_files, expected_sha, expected_tree)
    build = read_json(bundle / "build/build-manifest.json", "BUILD_MANIFEST_INVALID")
    if build.get("candidate_sha") != expected_sha or build.get("candidate_tree") != expected_tree:
        fail("BUILD_IDENTITY_MISMATCH")
    if sha256_file(ROOT / "frontend/pnpm-lock.yaml") != build.get("lockfile_sha256"):
        fail("LOCKFILE_DIGEST_MISMATCH")
    outputs = build.get("output_files") or []
    if len(outputs) != int(build.get("output_file_count", -1)):
        fail("BUILD_OUTPUT_COUNT_MISMATCH")
    for row in outputs:
        path = bundle / "build/output" / safe_relative(str(row.get("path") or ""))
        if (
            not path.is_file()
            or path.stat().st_size != int(row.get("size", -1))
            or sha256_file(path) != row.get("sha256")
        ):
            fail("BUILD_OUTPUT_DIGEST_MISMATCH")
    if (bundle / "verification/verification-report.json").exists():
        fail("PREFORGED_VERIFICATION_REPORT")
    return {
        "schema_version": "frontend-release-evidence-verification/v1",
        "result": "PASS",
        "reason_codes": [],
        "verified_sha": expected_sha,
        "verified_tree": expected_tree,
        "file_count": len(actual_files) + 2,
        "required_evidence_count": len(required),
        "qualification_state": manifest["qualification_state"],
    }


def verify_bundle(
    bundle: Path,
    expected_sha: str,
    expected_tree: str,
    expected_bundle_sha256: str = "",
) -> dict[str, Any]:
    policy = read_json(POLICY_PATH, "POLICY_INVALID")
    if bundle.is_dir():
        if expected_bundle_sha256:
            fail("ARCHIVE_DIGEST_NOT_APPLICABLE_TO_DIRECTORY")
        return verify_bundle_directory(bundle, expected_sha, expected_tree)
    if expected_bundle_sha256:
        if not HEX64.fullmatch(expected_bundle_sha256):
            fail("EXPECTED_BUNDLE_DIGEST_INVALID")
        if sha256_file(bundle) != expected_bundle_sha256:
            fail("BUNDLE_DIGEST_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="frontend-release-evidence-verify-") as directory:
        extracted = extract_archive(bundle, Path(directory), policy)
        return verify_bundle_directory(extracted, expected_sha, expected_tree)
