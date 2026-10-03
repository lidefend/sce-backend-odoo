#!/usr/bin/env python3
"""Govern removal of clean, non-primary linked worktrees.

Removal is local by default and never touches standalone clones.  The single
remote mutation in this entry is the legacy retirement path: once a topic is
proven integrated and its reviewed retirement record plus recovery bundle
verify, the corresponding ``origin/<branch>`` ref is deleted under an exact
``--force-with-lease`` lease so a moved remote branch can never be destroyed.
The caller must opt in with ``--apply``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import archive_worktree_delivery_evidence as evidence_archive


ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|codex)/.+$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DETACH_CONFIRMATION = "DETACH_VERIFIED_WORKTREE_KEEP_BRANCH"
SQUASH_RETIREMENT_CONFIRMATION = "RETIRE_SQUASH_INTEGRATED_WORKTREE_WITHOUT_ARCHIVED_EVIDENCE"
SUPERSEDED_RETIREMENT_CONFIRMATION = "RETIRE_SUPERSEDED_LOCAL_TOPIC_WITH_RECOVERY"
INTEGRATION_BASELINE = "origin/main"


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str | None
    head: str


@dataclass(frozen=True)
class IntegrationProof:
    """How a worktree HEAD is known to be integrated into ``origin/main``."""

    kind: str
    tree: str
    merge_commit: str = ""
    pull_request: int = 0
    # Paths the topic adds that the baseline never had.  Only a ``superseded``
    # proof fills this, so the reviewed retirement record has to enumerate them
    # and nothing new can be introduced silently.
    branch_added: tuple[str, ...] = ()


def run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and process.returncode:
        raise CleanupError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process


def parse_worktrees(output: str) -> list[Worktree]:
    worktrees: list[Worktree] = []
    for block in output.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if not fields.get("worktree") or not fields.get("HEAD"):
            continue
        branch_ref = fields.get("branch")
        branch = branch_ref.removeprefix("refs/heads/") if branch_ref else None
        worktrees.append(
            Worktree(path=Path(fields["worktree"]).resolve(), branch=branch, head=fields["HEAD"])
        )
    return worktrees


def verify_evidence_receipt(selected: Worktree, receipt_path: Path) -> None:
    receipt_path = receipt_path.resolve()
    if selected.path == receipt_path or selected.path in receipt_path.parents:
        raise CleanupError("evidence receipt must be outside the worktree")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupError(f"cannot read evidence receipt: {exc}") from exc
    if receipt.get("schemaVersion") != 1 or receipt.get("status") != "verified":
        raise CleanupError("evidence receipt is not verified schemaVersion 1")
    if Path(receipt.get("candidateWorktree", "")).resolve() != selected.path:
        raise CleanupError("evidence receipt worktree identity mismatch")
    if receipt.get("candidateHead") != selected.head:
        raise CleanupError("evidence receipt HEAD mismatch")
    topic = receipt.get("topic")
    manifest_path = Path(receipt.get("manifestPath", "")).resolve()
    if not isinstance(topic, str) or not topic:
        raise CleanupError("evidence receipt topic is missing")
    if selected.path not in manifest_path.parents or not manifest_path.is_file():
        raise CleanupError("evidence receipt manifest is missing or outside the worktree")
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if manifest_digest != receipt.get("manifestSha256"):
        raise CleanupError("evidence receipt manifest hash mismatch")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupError(f"cannot read evidence manifest: {exc}") from exc
    if (
        manifest.get("schemaVersion") != 1
        or manifest.get("topic") != topic
        or manifest.get("candidateHead") != selected.head
    ):
        raise CleanupError("evidence receipt does not match its batch manifest")
    rows = receipt.get("files")
    roles = {row.get("role") for row in rows or [] if isinstance(row, dict)}
    if roles != {"summary", "identity", "screenshot", "review"}:
        raise CleanupError("evidence receipt does not cover all required roles")
    receipt_entries = sorted(
        (row.get("role"), row.get("sourcePath")) for row in rows if isinstance(row, dict)
    )
    manifest_entries = sorted(
        (row.get("role"), row.get("path"))
        for row in manifest.get("files", [])
        if isinstance(row, dict)
    )
    if receipt_entries != manifest_entries:
        raise CleanupError("evidence receipt files do not match its batch manifest")
    for row in rows:
        archived = Path(row.get("archivePath", "")).resolve()
        if selected.path == archived or selected.path in archived.parents or not archived.is_file():
            raise CleanupError("archived evidence file is missing or inside the worktree")
        digest = hashlib.sha256(archived.read_bytes()).hexdigest()
        if archived.stat().st_size <= 0 or digest != row.get("sha256"):
            raise CleanupError(f"archived evidence verification failed: {archived}")
        try:
            evidence_archive.validate_evidence_file(row.get("role"), archived, selected.head)
        except evidence_archive.ArchiveError as exc:
            raise CleanupError(f"archived evidence role validation failed: {exc}") from exc


def plan_cleanup(
    root: Path, candidate: Path, *, allow_superseded: bool = False
) -> Worktree:
    root = root.resolve()
    candidate = candidate.resolve()
    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    primary = worktrees[0] if worktrees else None
    selected = next((item for item in worktrees if item.path == candidate), None)
    if primary is None:
        raise CleanupError("primary worktree is not registered")
    if selected is None:
        raise CleanupError(f"target is not a registered linked worktree: {candidate}")
    if selected.path == primary.path:
        raise CleanupError("refusing to remove the primary worktree")
    if not selected.branch:
        raise CleanupError("detached worktree cleanup is not permitted")
    if not ALLOWED_BRANCH.fullmatch(selected.branch):
        raise CleanupError(f"branch is not cleanup-eligible: {selected.branch}")
    if not selected.path.is_dir():
        raise CleanupError(f"worktree path is missing: {selected.path}")

    status = run(
        root,
        "-C",
        str(selected.path),
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    ).stdout.strip()
    if status:
        raise CleanupError(f"worktree is not clean: {selected.path}")

    run(root, "fetch", "--prune", "origin")
    prove_integration(root, selected, allow_superseded=allow_superseded)
    return selected


def merged_pull_request(root: Path, branch: str, head: str) -> dict | None:
    """Return the exact-head merged PR for ``branch``, or ``None``.

    A squash integration leaves the candidate HEAD outside ``origin/main``'s
    ancestry, so the same proof the branch cleanup entry already uses applies:
    a merged PR whose ``headRefOid`` is the exact worktree HEAD.
    """
    if not branch or shutil.which("gh") is None:
        return None
    process = subprocess.run(
        [
            "gh", "pr", "list", "--state", "merged", "--head", branch,
            "--json", "number,headRefOid,mergeCommit,state",
        ],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode:
        # Fail closed: an unverifiable merge is treated as "no proof" so the
        # caller denies the cleanup instead of assuming integration.
        return None
    try:
        rows = json.loads(process.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise CleanupError("gh pr list returned unreadable JSON") from exc
    for row in rows:
        if not isinstance(row, dict) or str(row.get("state") or "").upper() != "MERGED":
            continue
        if str(row.get("headRefOid") or "") != head:
            continue
        merge = row.get("mergeCommit")
        merge_oid = str(merge.get("oid") or "") if isinstance(merge, dict) else ""
        if FULL_SHA.fullmatch(merge_oid):
            return {"number": int(row.get("number") or 0), "mergeCommit": merge_oid}
    return None


def last_touch_times(root: Path, ref: str) -> dict[str, int]:
    """Return the newest commit time that touched each path reachable from ``ref``."""
    output = run(root, "log", ref, "--no-renames", "--format=C%ct", "--name-only").stdout
    times: dict[str, int] = {}
    current = 0
    for line in output.splitlines():
        if line.startswith("C") and line[1:].isdigit():
            current = int(line[1:])
            continue
        path = line.strip()
        if path and current > times.get(path, 0):
            times[path] = current
    return times


def prove_superseded(
    root: Path, selected: Worktree, baseline: str = INTEGRATION_BASELINE
) -> tuple[str, ...]:
    """Machine-check that a local-only topic carries nothing newer than ``baseline``.

    Admissible only when the topic is local-only (an unreadable remote is a denial,
    never an absence) and unmerged, when no path that differs from the baseline is
    newer on the topic side, and when every baseline-absent path the topic adds is
    returned so the reviewed record has to enumerate it.  Nothing here is inferred
    from the record: the record is compared against this recomputation.
    """
    if run(root, "rev-parse", "--verify", f"{baseline}^{{commit}}", check=False).returncode:
        raise CleanupError(f"integration baseline is unreadable: {baseline}")
    # "Local-only" has to hold for every configured remote, not just ``origin``:
    # a live topic could equally sit on the mirror remote.  Any unreadable remote
    # raises from ``remote_branch_sha``, so an unknown remote is a denial too.
    if selected.branch:
        for remote in remote_names(root):
            if remote_branch_sha(root, selected.branch, remote=remote) is not None:
                raise CleanupError(
                    "a superseded topic must be local-only; "
                    f"{remote}/{selected.branch} still exists"
                )
    rows = run(
        root, "diff", "--name-status", "--no-renames", baseline, selected.head
    ).stdout
    compared: list[str] = []
    branch_added: list[str] = []
    for row in rows.splitlines():
        if not row.strip():
            continue
        fields = row.split("\t")
        status, path = fields[0], fields[-1]
        if status.startswith("A"):
            branch_added.append(path)
        elif status.startswith("D"):
            # Present in the baseline and absent from the topic: the topic cannot
            # be newer than a file it does not contain.
            continue
        else:
            compared.append(path)
    topic_times = last_touch_times(root, selected.head)
    baseline_times = last_touch_times(root, baseline)
    newer = sorted(
        path
        for path in compared
        if topic_times.get(path, 0) > baseline_times.get(path, 0)
    )
    if newer:
        raise CleanupError(
            "worktree HEAD is not superseded; the topic side is newer for: "
            + ", ".join(newer[:5])
            + (f" (+{len(newer) - 5} more)" if len(newer) > 5 else "")
        )
    return tuple(sorted(branch_added))


def prove_integration(
    root: Path, selected: Worktree, *, allow_superseded: bool = False
) -> IntegrationProof:
    """Prove the worktree HEAD is integrated into ``origin/main``.

    Two integrations are admissible. ``ancestor``: the HEAD is contained in
    ``origin/main`` directly, and a merged PR for the exact HEAD is recorded
    when one can be read. ``squash``: the HEAD is not an ancestor, but a merged
    PR for the exact HEAD has a single-parent merge commit on ``origin/main``
    whose tree is byte-identical to the worktree HEAD tree, i.e. a squash
    integration that carried the whole candidate.
    """
    tree = run(root, "rev-parse", f"{selected.head}^{{tree}}").stdout.strip()
    if run(
        root, "merge-base", "--is-ancestor", selected.head, "origin/main", check=False
    ).returncode == 0:
        # Ancestor containment alone already proves this exact HEAD is integrated.
        # A merged pull request for the same HEAD is still recorded when one can be
        # read, so a retirement record can be bound to the integration it retires.
        # The lookup is best effort here; the retirement path separately enforces
        # that it succeeded before admitting an ancestor-integrated topic.
        row = merged_pull_request(root, selected.branch or "", selected.head)
        return IntegrationProof(
            kind="ancestor",
            tree=tree,
            merge_commit=str(row.get("mergeCommit") or "") if row else "",
            pull_request=int(row["number"]) if row and row.get("number") else 0,
        )
    row = merged_pull_request(root, selected.branch or "", selected.head)
    if row is None:
        if not allow_superseded:
            raise CleanupError(
                f"worktree HEAD is not merged into origin/main: {selected.head}"
            )
        return IntegrationProof(
            kind="superseded",
            tree=tree,
            branch_added=prove_superseded(root, selected),
        )
    merge_commit = row["mergeCommit"]
    if run(
        root, "merge-base", "--is-ancestor", merge_commit, "origin/main", check=False
    ).returncode:
        raise CleanupError(f"squash merge commit is not on origin/main: {merge_commit}")
    ancestry = run(root, "rev-list", "--parents", "-n", "1", merge_commit).stdout.split()
    if len(ancestry) != 2:
        raise CleanupError(f"squash proof requires a single-parent merge commit: {merge_commit}")
    merge_tree = run(root, "rev-parse", f"{merge_commit}^{{tree}}").stdout.strip()
    if merge_tree != tree:
        raise CleanupError(
            f"squash merge tree does not match the worktree HEAD tree: {merge_commit}"
        )
    return IntegrationProof(
        kind="squash",
        tree=tree,
        merge_commit=merge_commit,
        pull_request=row["number"],
    )


def remote_names(root: Path) -> tuple[str, ...]:
    """Return every configured remote name, sorted for deterministic messages."""
    return tuple(sorted(name for name in run(root, "remote").stdout.split() if name))


def remote_branch_sha(root: Path, branch: str, remote: str = "origin") -> str | None:
    """Return the SHA of ``<remote>/<branch>``, or ``None`` when it is absent.

    The locally cached ``refs/remotes/origin/*`` namespace is not authoritative
    here: this repository fetches only ``main``, so a live remote topic branch
    would look absent and a retired topic would look gone.  The retirement path
    therefore asks the remote itself, once, and fails closed: an unreadable
    answer is a denial rather than an assumption.
    """
    process = run(
        root, "ls-remote", "--heads", remote, f"refs/heads/{branch}", check=False
    )
    if process.returncode:
        raise CleanupError(
            f"cannot read {remote}/{branch} (remote state must be known): "
            f"{process.stdout.strip()}"
        )
    rows = [line.split() for line in process.stdout.splitlines() if line.strip()]
    if not rows:
        return None
    sha = rows[0][0] if rows[0] else ""
    if not FULL_SHA.fullmatch(sha):
        raise CleanupError(
            f"unexpected ls-remote result for {remote}/{branch}: {rows[0]!r}"
        )
    return sha


def verify_retirement_record(
    root: Path,
    selected: Worktree,
    record_path: Path,
    bundle_path: Path,
    proof: IntegrationProof,
) -> None:
    """Verify the tracked legacy retirement record and its recovery bundle.

    Legacy product worktrees delivered before delivery-evidence archiving existed
    have no archived evidence to preserve. Retiring them therefore requires a
    reviewed repository record that discloses the absence and pins an external
    recovery bundle; the original evidence must never be fabricated.

    The record is read from the committed ``HEAD`` blob, not from the working
    tree, so an uncommitted edit can neither widen nor narrow a retirement.
    """
    root = root.resolve()
    record_path = record_path.resolve()
    bundle_path = bundle_path.resolve()
    for candidate_path in (record_path, bundle_path):
        if selected.path == candidate_path or selected.path in candidate_path.parents:
            raise CleanupError("retirement record and recovery bundle must be outside the worktree")
    if run(root, "ls-files", "--error-unmatch", "--", str(record_path), check=False).returncode:
        raise CleanupError("retirement record must be a tracked repository file")
    try:
        relative_record = record_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise CleanupError("retirement record must live inside the repository") from exc
    committed = run(root, "show", f"HEAD:{relative_record}", check=False)
    if committed.returncode:
        raise CleanupError("retirement record must be committed at HEAD")
    if not bundle_path.is_file() or bundle_path.stat().st_size <= 0:
        raise CleanupError("recovery bundle is missing or empty")
    try:
        record = json.loads(committed.stdout)
    except json.JSONDecodeError as exc:
        raise CleanupError(f"cannot read committed retirement record: {exc}") from exc
    if record.get("schemaVersion") != 1:
        raise CleanupError("retirement record schemaVersion must be 1")
    rows = record.get("worktrees")
    if not isinstance(rows, list):
        raise CleanupError("retirement record worktrees must be a list")
    entry = next(
        (
            row
            for row in rows
            if isinstance(row, dict)
            and row.get("path") == str(selected.path)
            and row.get("branch") == selected.branch
            and row.get("head") == selected.head
        ),
        None,
    )
    if entry is None:
        raise CleanupError("retirement record has no entry for this worktree identity")
    if entry.get("evidenceStatus") != "absent":
        raise CleanupError("retirement record entry must declare evidenceStatus=absent")
    if not str(entry.get("reason") or "").strip():
        raise CleanupError("retirement record entry must state why no evidence exists")
    if entry.get("integrationKind") == "superseded":
        # A superseded topic has no merge to bind to; the reviewed record instead has
        # to enumerate exactly what the topic adds on top of the baseline, so nothing
        # baseline-absent can enter through the record instead of through review.
        if proof.kind != "superseded":
            raise CleanupError(
                "retirement record declares a superseded topic but the worktree is integrated"
            )
        declared_superseded = entry.get("supersededBy")
        if not isinstance(declared_superseded, dict):
            raise CleanupError("superseded retirement record requires a supersededBy block")
        if str(declared_superseded.get("baseline") or "") != INTEGRATION_BASELINE:
            raise CleanupError(
                f"superseded retirement record baseline must be {INTEGRATION_BASELINE}"
            )
        if list(declared_superseded.get("branchNewer") or []):
            raise CleanupError(
                "superseded retirement record must declare an empty branchNewer list"
            )
        declared_added = declared_superseded.get("branchAdded")
        if not isinstance(declared_added, list) or not all(
            isinstance(value, str) for value in declared_added
        ):
            raise CleanupError(
                "superseded retirement record branchAdded must be a string list"
            )
        if tuple(sorted(declared_added)) != proof.branch_added:
            raise CleanupError(
                "superseded retirement record branchAdded does not match the verified evidence"
            )
    else:
        declared_pr = entry.get("mergedPr")
        if not isinstance(declared_pr, int) or isinstance(declared_pr, bool):
            raise CleanupError("retirement record mergedPr must be an integer")
        if declared_pr != proof.pull_request:
            raise CleanupError("retirement record merged PR does not match the verified merge proof")
        if str(entry.get("mergeCommit") or "") != proof.merge_commit:
            raise CleanupError("retirement record merge commit does not match the verified merge proof")
    if str(entry.get("tree") or "") != proof.tree:
        raise CleanupError("retirement record tree does not match the verified merge proof")
    bundle = entry.get("recoveryBundle")
    if not isinstance(bundle, dict) or str(bundle.get("path") or "") != str(bundle_path):
        raise CleanupError("retirement record recovery bundle path does not match")
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    if digest != bundle.get("sha256"):
        raise CleanupError("recovery bundle hash does not match the retirement record")
    listed = {
        line.split()[0]
        for line in run(root, "bundle", "list-heads", str(bundle_path)).stdout.splitlines()
        if line.split()
    }
    if selected.head not in listed:
        raise CleanupError("recovery bundle does not cover the worktree HEAD")
    verified = run(root, "bundle", "verify", str(bundle_path), check=False)
    if verified.returncode:
        raise CleanupError(f"recovery bundle failed verification: {verified.stdout.strip()}")


def plan_detach(root: Path, candidate: Path, *, expected_head: str) -> Worktree:
    root = root.resolve()
    candidate = candidate.resolve()
    if not FULL_SHA.fullmatch(expected_head):
        raise CleanupError("worktree detach requires a full lowercase expected HEAD")
    worktrees = parse_worktrees(run(root, "worktree", "list", "--porcelain").stdout)
    primary = worktrees[0] if worktrees else None
    selected = next((item for item in worktrees if item.path == candidate), None)
    if primary is None:
        raise CleanupError("primary worktree is not registered")
    if selected is None:
        raise CleanupError(f"target is not a registered linked worktree: {candidate}")
    if selected.path == primary.path:
        raise CleanupError("refusing to detach the primary worktree")
    if not selected.branch:
        raise CleanupError("detached worktree detach is not permitted")
    if selected.head != expected_head:
        raise CleanupError(
            f"worktree HEAD changed: expected={expected_head} actual={selected.head}"
        )
    status = run(
        root, "-C", str(selected.path), "status", "--porcelain=v1", "--untracked-files=all"
    ).stdout.strip()
    if status:
        raise CleanupError(f"worktree is not clean: {selected.path}")
    ref_head = run(root, "rev-parse", "--verify", f"refs/heads/{selected.branch}").stdout.strip()
    if ref_head != expected_head:
        raise CleanupError(
            f"branch HEAD changed: expected={expected_head} actual={ref_head}"
        )
    return selected


def detach_worktree(
    root: Path,
    candidate: Path,
    *,
    expected_head: str,
    apply: bool,
    confirmation: str,
    evidence_receipt: Path | None = None,
) -> Worktree:
    selected = plan_detach(root, candidate, expected_head=expected_head)
    if apply:
        if evidence_receipt is None:
            raise CleanupError("apply requires an external verified evidence receipt")
        verify_evidence_receipt(selected, evidence_receipt)
        if confirmation != DETACH_CONFIRMATION:
            raise CleanupError(
                f"worktree detach apply requires confirmation={DETACH_CONFIRMATION}"
            )
        run(root.resolve(), "worktree", "remove", "--", str(selected.path))
        retained = run(
            root.resolve(), "rev-parse", "--verify", f"refs/heads/{selected.branch}"
        ).stdout.strip()
        if retained != selected.head:
            raise CleanupError("retained branch identity changed after worktree detach")
    return selected


def cleanup(
    root: Path,
    candidate: Path,
    *,
    apply: bool,
    evidence_receipt: Path | None = None,
    retirement_record: Path | None = None,
    recovery_bundle: Path | None = None,
    confirmation: str = "",
    allow_superseded: bool = False,
) -> Worktree:
    selected = plan_cleanup(root, candidate, allow_superseded=allow_superseded)
    proof = prove_integration(root, selected, allow_superseded=allow_superseded)
    branch = selected.branch or ""
    if apply:
        # Destructive steps are recorded as they succeed so that a later denial can
        # name what already happened instead of only the step that failed.
        completed: list[str] = []
        try:
            if evidence_receipt is not None:
                verify_evidence_receipt(selected, evidence_receipt)
            elif retirement_record is not None and recovery_bundle is not None:
                if proof.kind == "superseded":
                    if confirmation != SUPERSEDED_RETIREMENT_CONFIRMATION:
                        raise CleanupError(
                            "superseded retirement apply requires "
                            f"confirmation={SUPERSEDED_RETIREMENT_CONFIRMATION}"
                        )
                elif confirmation != SQUASH_RETIREMENT_CONFIRMATION:
                    raise CleanupError(
                        "legacy retirement apply requires "
                        f"confirmation={SQUASH_RETIREMENT_CONFIRMATION}"
                    )
                if proof.kind not in {"squash", "ancestor", "superseded"}:
                    raise CleanupError(
                        "retirement record is only admissible for integrated topics"
                    )
                # An ancestor-integrated topic is provably contained in origin/main,
                # but unlike a squash integration it has no tree-identical
                # single-parent merge commit. Bind it to the verified merged pull
                # request of the exact HEAD so the reviewed record still names the
                # integration it retires, and fail closed when that cannot be read.
                if proof.kind == "ancestor" and not (
                    proof.pull_request and proof.merge_commit
                ):
                    raise CleanupError(
                        "ancestor retirement requires a verified merged pull request "
                        "for the exact worktree HEAD"
                    )
                # A retirement retires the whole topic, so the remote ref is part of
                # the transaction: delete it under an exact lease, and refuse when it
                # has moved away from the integrated HEAD.  Every verification above
                # and below runs before this, the first destructive step.
                remote_sha = remote_branch_sha(root, branch)
                if remote_sha is not None and remote_sha != selected.head:
                    raise CleanupError(
                        f"origin/{branch} moved: expected={selected.head} actual={remote_sha}"
                    )
                verify_retirement_record(
                    root, selected, retirement_record, recovery_bundle, proof
                )
                if remote_sha is not None:
                    run(
                        root,
                        "push",
                        "origin",
                        "--delete",
                        f"--force-with-lease=refs/heads/{branch}:{remote_sha}",
                        "--",
                        branch,
                    )
                    completed.append(f"remote ref origin/{branch} deleted")
            else:
                raise CleanupError(
                    "apply requires an external verified evidence receipt or a tracked "
                    "retirement record with a recovery bundle"
                )
            run(root, "worktree", "remove", "--", str(selected.path))
            completed.append(f"worktree removed ({selected.path})")
            ref_head = run(root, "rev-parse", "--verify", f"refs/heads/{branch}").stdout.strip()
            if ref_head != selected.head:
                raise CleanupError(
                    f"branch ref moved before deletion: expected={selected.head} actual={ref_head}"
                )
            run(
                root,
                "branch",
                "-D" if proof.kind in {"squash", "superseded"} else "-d",
                "--",
                branch,
            )
            completed.append(f"local branch {branch} deleted")
        except (CleanupError, subprocess.CalledProcessError) as exc:
            if not completed:
                raise
            detail = str(exc).strip() or exc.__class__.__name__
            raise CleanupError(
                f"{detail}; destructive steps already completed: {'; '.join(completed)}"
            ) from exc
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--detach-keep-branch", action="store_true")
    parser.add_argument("--superseded-retirement", action="store_true")
    parser.add_argument("--expected-head", default="")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--evidence-receipt", default="")
    parser.add_argument("--retirement-record", default="")
    parser.add_argument("--recovery-bundle", default="")
    args = parser.parse_args()
    try:
        root = Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
        )
        if args.detach_keep_branch:
            if args.superseded_retirement:
                raise CleanupError(
                    "worktree detach cannot be combined with a superseded retirement"
                )
            selected = detach_worktree(
                root,
                Path(args.path),
                expected_head=args.expected_head,
                apply=args.apply,
                confirmation=args.confirm,
                evidence_receipt=Path(args.evidence_receipt) if args.evidence_receipt else None,
            )
        else:
            if args.superseded_retirement and not (
                args.retirement_record and args.recovery_bundle
            ):
                raise CleanupError(
                    "superseded retirement requires both --retirement-record and "
                    "--recovery-bundle"
                )
            selected = cleanup(
                root,
                Path(args.path),
                apply=args.apply,
                evidence_receipt=Path(args.evidence_receipt) if args.evidence_receipt else None,
                retirement_record=(
                    Path(args.retirement_record) if args.retirement_record else None
                ),
                recovery_bundle=Path(args.recovery_bundle) if args.recovery_bundle else None,
                confirmation=args.confirm,
                allow_superseded=args.superseded_retirement,
            )
    except (CleanupError, subprocess.CalledProcessError) as exc:
        print(f"[workspace.worktree.cleanup] DENY {exc}", file=sys.stderr)
        return 2
    mode = "APPLIED" if args.apply else "DRY_RUN"
    print(
        f"[workspace.worktree.cleanup] {mode} "
        f"path={selected.path} branch={selected.branch} head={selected.head}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
