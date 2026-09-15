#!/usr/bin/env python3
"""Govern removal of clean, non-primary linked worktrees.

This is deliberately local-only: it removes neither remote branches nor
standalone clones.  The caller must opt in with ``--apply``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|codex)/.+$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DETACH_CONFIRMATION = "DETACH_VERIFIED_WORKTREE_KEEP_BRANCH"


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str | None
    head: str


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
    rows = receipt.get("files")
    roles = {row.get("role") for row in rows or [] if isinstance(row, dict)}
    if roles != {"summary", "identity", "screenshot", "review"}:
        raise CleanupError("evidence receipt does not cover all required roles")
    for row in rows:
        archived = Path(row.get("archivePath", "")).resolve()
        if selected.path == archived or selected.path in archived.parents or not archived.is_file():
            raise CleanupError("archived evidence file is missing or inside the worktree")
        digest = hashlib.sha256(archived.read_bytes()).hexdigest()
        if archived.stat().st_size <= 0 or digest != row.get("sha256"):
            raise CleanupError(f"archived evidence verification failed: {archived}")


def plan_cleanup(root: Path, candidate: Path) -> Worktree:
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
    merged = run(
        root,
        "merge-base",
        "--is-ancestor",
        selected.head,
        "origin/main",
        check=False,
    )
    if merged.returncode != 0:
        raise CleanupError(f"worktree HEAD is not merged into origin/main: {selected.head}")
    return selected


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
    root: Path, candidate: Path, *, apply: bool, evidence_receipt: Path | None = None
) -> Worktree:
    selected = plan_cleanup(root, candidate)
    if apply:
        if evidence_receipt is None:
            raise CleanupError("apply requires an external verified evidence receipt")
        verify_evidence_receipt(selected, evidence_receipt)
        run(root, "worktree", "remove", "--", str(selected.path))
        run(root, "branch", "-d", "--", selected.branch or "")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--detach-keep-branch", action="store_true")
    parser.add_argument("--expected-head", default="")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--evidence-receipt", default="")
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
            selected = detach_worktree(
                root,
                Path(args.path),
                expected_head=args.expected_head,
                apply=args.apply,
                confirmation=args.confirm,
                evidence_receipt=Path(args.evidence_receipt) if args.evidence_receipt else None,
            )
        else:
            selected = cleanup(
                root,
                Path(args.path),
                apply=args.apply,
                evidence_receipt=Path(args.evidence_receipt) if args.evidence_receipt else None,
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
