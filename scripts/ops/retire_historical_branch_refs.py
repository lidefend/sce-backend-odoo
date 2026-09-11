#!/usr/bin/env python3
"""Retire an explicitly approved set of historical branch references.

The command is a read-only dry-run by default.  Apply mode is bound to the
SHA-256 of the exact manifest and creates (or verifies) a recovery bundle
before deleting any reference.  Local and remote identities are checked
independently and every unsafe entry is skipped rather than broadened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
CONFIRMATION = "RETIRE_APPROVED_HISTORICAL_REFERENCES"


class RetirementError(RuntimeError):
    """Raised when the manifest or repository cannot be handled safely."""


@dataclass(frozen=True)
class RefEntry:
    branch: str
    local_sha: str
    remote_state: str
    remote_sha: str | None
    reason: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class EntryAssessment:
    entry: RefEntry
    status: str
    reasons: tuple[str, ...]


def run_git(
    root: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and process.returncode:
        raise RetirementError(
            f"git {' '.join(args)} failed ({process.returncode}): "
            f"{process.stdout.strip()}"
        )
    return process


def manifest_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RetirementError(f"{label} must be a non-empty string")
    return value.strip()


def load_manifest(path: Path) -> tuple[dict[str, Any], tuple[RefEntry, ...]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RetirementError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RetirementError("manifest schema_version must be 1")
    repository = payload.get("repository")
    if not isinstance(repository, dict):
        raise RetirementError("manifest repository must be an object")
    require_text(repository.get("name"), "repository.name")
    require_text(repository.get("origin_url"), "repository.origin_url")
    entries_payload = payload.get("references")
    if not isinstance(entries_payload, list) or not entries_payload:
        raise RetirementError("manifest references must be a non-empty list")

    entries: list[RefEntry] = []
    seen: set[str] = set()
    for index, raw in enumerate(entries_payload):
        label = f"references[{index}]"
        if not isinstance(raw, dict):
            raise RetirementError(f"{label} must be an object")
        branch = require_text(raw.get("branch"), f"{label}.branch")
        if branch in seen:
            raise RetirementError(f"duplicate branch in manifest: {branch}")
        seen.add(branch)
        if (
            not ALLOWED_BRANCH.fullmatch(branch)
            or branch in {"main", "master"}
            or branch.startswith("release/")
        ):
            raise RetirementError(f"unsafe branch in manifest: {branch}")
        local = raw.get("local")
        remote = raw.get("remote")
        if not isinstance(local, dict) or not isinstance(remote, dict):
            raise RetirementError(f"{label} local and remote must be objects")
        local_sha = require_text(local.get("sha"), f"{label}.local.sha")
        if not FULL_SHA.fullmatch(local_sha):
            raise RetirementError(f"{label}.local.sha must be a full lowercase SHA")
        remote_state = require_text(remote.get("state"), f"{label}.remote.state")
        if remote_state not in {"present", "absent"}:
            raise RetirementError(f"{label}.remote.state must be present or absent")
        remote_sha = remote.get("sha")
        if remote_state == "present":
            remote_sha = require_text(remote_sha, f"{label}.remote.sha")
            if not FULL_SHA.fullmatch(remote_sha):
                raise RetirementError(f"{label}.remote.sha must be a full lowercase SHA")
        elif remote_sha is not None:
            raise RetirementError(f"{label}.remote.sha must be null when absent")
        reason = require_text(raw.get("reason"), f"{label}.reason")
        evidence_raw = raw.get("evidence")
        if not isinstance(evidence_raw, list) or not evidence_raw:
            raise RetirementError(f"{label}.evidence must be a non-empty list")
        evidence = tuple(
            require_text(item, f"{label}.evidence") for item in evidence_raw
        )
        entries.append(
            RefEntry(
                branch=branch,
                local_sha=local_sha,
                remote_state=remote_state,
                remote_sha=remote_sha,
                reason=reason,
                evidence=evidence,
            )
        )
    return payload, tuple(entries)


def local_ref_sha(root: Path, branch: str) -> str | None:
    result = run_git(
        root,
        "show-ref",
        "--verify",
        "--hash",
        f"refs/heads/{branch}",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def remote_ref_sha(root: Path, branch: str) -> str | None:
    result = run_git(
        root,
        "ls-remote",
        "--heads",
        "origin",
        f"refs/heads/{branch}",
        check=False,
    )
    if result.returncode:
        raise RetirementError(
            f"cannot read origin branch {branch}: {result.stdout.strip()}"
        )
    line = result.stdout.strip()
    if not line:
        return None
    fields = line.split()
    if len(fields) != 2 or fields[1] != f"refs/heads/{branch}":
        raise RetirementError(f"unexpected ls-remote result for {branch}: {line}")
    return fields[0]


def occupied_branches(root: Path) -> dict[str, str]:
    occupied: dict[str, str] = {}
    path = ""
    for line in run_git(root, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif line.startswith("branch refs/heads/"):
            occupied[line.removeprefix("branch refs/heads/")] = path
    return occupied


def github_open_branches(root: Path) -> set[str]:
    if shutil.which("gh") is None:
        raise RetirementError("gh is required to verify related open pull requests")
    process = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            "500",
            "--json",
            "headRefName",
        ],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode:
        raise RetirementError(
            f"cannot verify related open pull requests: {process.stdout.strip()}"
        )
    try:
        rows = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RetirementError("gh returned malformed pull request data") from exc
    if not isinstance(rows, list):
        raise RetirementError("gh pull request data must be a list")
    return {
        row["headRefName"]
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("headRefName"), str)
    }


def assess_entries(
    root: Path,
    entries: Iterable[RefEntry],
    *,
    open_branches: set[str],
    related_work_error: str = "",
) -> tuple[EntryAssessment, ...]:
    occupied = occupied_branches(root)
    assessments: list[EntryAssessment] = []
    for entry in entries:
        reasons: list[str] = []
        actual_local = local_ref_sha(root, entry.branch)
        try:
            actual_remote = remote_ref_sha(root, entry.branch)
        except RetirementError as exc:
            actual_remote = None
            reasons.append(str(exc))
        if actual_local != entry.local_sha:
            reasons.append(
                f"local SHA drift: expected {entry.local_sha}, actual {actual_local or 'absent'}"
            )
        expected_remote = entry.remote_sha if entry.remote_state == "present" else None
        if actual_remote != expected_remote:
            reasons.append(
                "remote SHA drift: expected "
                f"{expected_remote or 'absent'}, actual {actual_remote or 'absent'}"
            )
        if entry.branch in occupied:
            reasons.append(f"branch is checked out at {occupied[entry.branch]}")
        if entry.branch in open_branches:
            reasons.append("branch has an open pull request")
        if related_work_error:
            reasons.append(f"related-work evidence unavailable: {related_work_error}")
        assessments.append(
            EntryAssessment(
                entry=entry,
                status="skip" if reasons else "eligible",
                reasons=tuple(reasons),
            )
        )
    return tuple(assessments)


def recovery_refs(
    digest: str,
    entries: Iterable[RefEntry],
) -> dict[str, tuple[str, str | None]]:
    prefix = f"refs/codex/historical-retirement/{digest[:16]}"
    return {
        entry.branch: (
            f"{prefix}/local/{entry.branch}",
            (
                f"{prefix}/remote/{entry.branch}"
                if entry.remote_state == "present"
                else None
            ),
        )
        for entry in entries
    }


def ensure_commit_available(root: Path, entry: RefEntry, sha: str) -> None:
    if run_git(root, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0:
        return
    if entry.remote_sha != sha:
        raise RetirementError(
            f"expected commit is unavailable locally and is not a declared remote tip: {sha}"
        )
    result = run_git(
        root,
        "fetch",
        "--no-tags",
        "origin",
        f"refs/heads/{entry.branch}",
        check=False,
    )
    if result.returncode:
        raise RetirementError(
            f"cannot fetch declared remote tip for {entry.branch}: {result.stdout.strip()}"
        )
    fetched = run_git(root, "rev-parse", "FETCH_HEAD").stdout.strip()
    if fetched != sha or run_git(
        root, "cat-file", "-e", f"{sha}^{{commit}}", check=False
    ).returncode:
        raise RetirementError(
            f"fetched remote tip drift for {entry.branch}: expected {sha}, actual {fetched}"
        )


def verify_bundle(
    root: Path,
    bundle: Path,
    digest: str,
    entries: Iterable[RefEntry],
) -> dict[str, str]:
    result = run_git(root, "bundle", "verify", str(bundle), check=False)
    if result.returncode:
        raise RetirementError(f"recovery bundle verification failed: {result.stdout.strip()}")
    heads = run_git(root, "bundle", "list-heads", str(bundle)).stdout.splitlines()
    parsed_heads = {
        fields[1]: fields[0]
        for line in heads
        if len(fields := line.split()) == 2
    }
    expected: set[str] = set()
    expected_heads: dict[str, str] = {}
    refs = recovery_refs(digest, entries)
    for entry in entries:
        expected.add(entry.local_sha)
        local_recovery, remote_recovery = refs[entry.branch]
        expected_heads[local_recovery] = entry.local_sha
        if entry.remote_sha:
            expected.add(entry.remote_sha)
            assert remote_recovery
            expected_heads[remote_recovery] = entry.remote_sha
    missing = sorted(expected - set(parsed_heads.values()))
    if missing:
        raise RetirementError(
            "recovery bundle does not expose every expected commit: " + ", ".join(missing)
        )
    missing_or_changed_heads = sorted(
        ref for ref, sha in expected_heads.items() if parsed_heads.get(ref) != sha
    )
    if missing_or_changed_heads:
        raise RetirementError(
            "recovery bundle is not bound to the exact manifest heads: "
            + ", ".join(missing_or_changed_heads)
        )
    return {"path": str(bundle), "verify": "pass", "head_count": str(len(heads))}


def create_recovery_bundle(
    root: Path,
    bundle: Path,
    digest: str,
    entries: tuple[RefEntry, ...],
) -> dict[str, str]:
    if not entries:
        raise RetirementError("no eligible references available for recovery bundle")
    bundle = bundle.resolve(strict=False)
    bundle.parent.mkdir(parents=True, exist_ok=True)
    if bundle.exists():
        return verify_bundle(root, bundle, digest, entries)

    refs = recovery_refs(digest, entries)
    created: list[tuple[str, str]] = []
    try:
        for entry in entries:
            ensure_commit_available(root, entry, entry.local_sha)
            if entry.remote_sha:
                ensure_commit_available(root, entry, entry.remote_sha)
            local_recovery, remote_recovery = refs[entry.branch]
            run_git(root, "update-ref", local_recovery, entry.local_sha)
            created.append((local_recovery, entry.local_sha))
            if remote_recovery and entry.remote_sha:
                run_git(root, "update-ref", remote_recovery, entry.remote_sha)
                created.append((remote_recovery, entry.remote_sha))
        with tempfile.NamedTemporaryFile(
            prefix=f".{bundle.name}.", dir=bundle.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        temporary.unlink()
        try:
            run_git(root, "bundle", "create", str(temporary), *[ref for ref, _ in created])
            temporary.replace(bundle)
        finally:
            if temporary.exists():
                temporary.unlink()
    finally:
        for ref, sha in reversed(created):
            run_git(root, "update-ref", "-d", ref, sha, check=False)
    return verify_bundle(root, bundle, digest, entries)


def delete_entry(root: Path, entry: RefEntry) -> tuple[str, tuple[str, ...]]:
    actions: list[str] = []
    if entry.remote_state == "present" and entry.remote_sha:
        lease = f"--force-with-lease=refs/heads/{entry.branch}:{entry.remote_sha}"
        result = run_git(
            root,
            "push",
            lease,
            "origin",
            f":refs/heads/{entry.branch}",
            check=False,
        )
        if result.returncode:
            return "partial", (f"remote delete failed: {result.stdout.strip()}",)
        actions.append("remote_deleted")
    else:
        actions.append("remote_absent_confirmed")

    result = run_git(
        root,
        "update-ref",
        "-d",
        f"refs/heads/{entry.branch}",
        entry.local_sha,
        check=False,
    )
    if result.returncode:
        return "partial", tuple(actions + [f"local delete failed: {result.stdout.strip()}"])
    actions.append("local_deleted")
    return "retired", tuple(actions)


def build_report(
    *,
    mode: str,
    manifest: Path,
    digest: str,
    assessments: Iterable[EntryAssessment],
    bundle: dict[str, str] | None,
    execution: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": mode,
        "manifest": str(manifest.resolve()),
        "manifest_sha256": digest,
        "bundle": bundle,
        "references": [
            {
                "branch": assessment.entry.branch,
                "local_expected_sha": assessment.entry.local_sha,
                "remote_expected_state": assessment.entry.remote_state,
                "remote_expected_sha": assessment.entry.remote_sha,
                "assessment": assessment.status,
                "assessment_reasons": list(assessment.reasons),
                "execution": (execution or {}).get(assessment.entry.branch),
            }
            for assessment in assessments
        ],
    }


def write_report(report: dict[str, Any], path: Path | None) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(rendered, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    print(f"[historical.branch.retire] report={path}")


def execute(
    root: Path,
    manifest_path: Path,
    *,
    mode: str,
    bundle_path: Path | None,
    approved_digest: str,
    confirmation: str,
    open_branch_provider: Callable[[Path], set[str]] = github_open_branches,
) -> dict[str, Any]:
    payload, entries = load_manifest(manifest_path)
    expected_origin = payload["repository"]["origin_url"]
    actual_origin = run_git(root, "remote", "get-url", "origin").stdout.strip()
    if actual_origin != expected_origin:
        raise RetirementError(
            f"origin URL drift: expected {expected_origin}, actual {actual_origin}"
        )
    digest = manifest_digest(manifest_path)
    related_work_error = ""
    try:
        open_branches = open_branch_provider(root)
    except RetirementError as exc:
        open_branches = set()
        related_work_error = str(exc)
    assessments = assess_entries(
        root,
        entries,
        open_branches=open_branches,
        related_work_error=related_work_error,
    )
    eligible = tuple(
        assessment.entry for assessment in assessments if assessment.status == "eligible"
    )

    if mode == "apply":
        if approved_digest != digest:
            raise RetirementError(
                "apply requires --approved-manifest-sha256 matching the exact manifest"
            )
        if confirmation != CONFIRMATION:
            raise RetirementError(f"apply requires --confirm {CONFIRMATION}")

    bundle_result: dict[str, str] | None = None
    if mode in {"prepare-bundle", "apply"}:
        if bundle_path is None:
            raise RetirementError(f"{mode} requires --bundle-output")
        bundle_result = create_recovery_bundle(root, bundle_path, digest, eligible)

    if mode != "apply":
        return build_report(
            mode=mode,
            manifest=manifest_path,
            digest=digest,
            assessments=assessments,
            bundle=bundle_result,
        )

    if any(assessment.status != "eligible" for assessment in assessments):
        # Per-entry skip remains explicit; eligible entries may still be retired.
        pass
    execution: dict[str, dict[str, Any]] = {}
    for assessment in assessments:
        if assessment.status != "eligible":
            execution[assessment.entry.branch] = {
                "status": "skipped",
                "details": list(assessment.reasons),
            }
            continue
        status, details = delete_entry(root, assessment.entry)
        execution[assessment.entry.branch] = {
            "status": status,
            "details": list(details),
        }
    return build_report(
        mode=mode,
        manifest=manifest_path,
        digest=digest,
        assessments=assessments,
        bundle=bundle_result,
        execution=execution,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--prepare-bundle", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--bundle-output", type=Path)
    parser.add_argument("--approved-manifest-sha256", default="")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.prepare_bundle and args.apply:
        print(
            "[historical.branch.retire] DENY choose prepare-bundle or apply",
            file=sys.stderr,
        )
        return 2
    mode = "apply" if args.apply else "prepare-bundle" if args.prepare_bundle else "dry-run"
    try:
        root = Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
        )
        report = execute(
            root,
            args.manifest,
            mode=mode,
            bundle_path=args.bundle_output,
            approved_digest=args.approved_manifest_sha256,
            confirmation=args.confirm,
        )
        write_report(report, args.report)
    except (RetirementError, OSError, subprocess.CalledProcessError) as exc:
        print(f"[historical.branch.retire] DENY {exc}", file=sys.stderr)
        return 2
    eligible = sum(item["assessment"] == "eligible" for item in report["references"])
    skipped = len(report["references"]) - eligible
    print(
        f"[historical.branch.retire] {mode.upper()} eligible={eligible} skipped={skipped} "
        f"manifest_sha256={report['manifest_sha256']}"
    )
    if mode == "apply":
        partial = [
            item
            for item in report["references"]
            if item["execution"] and item["execution"]["status"] == "partial"
        ]
        return 1 if partial else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
