#!/usr/bin/env python3
"""Fail-closed main-baseline sync for an unpublished local delivery branch.

This is the only governed path that may invoke ``git rebase``.  It never pushes
or alters a public branch, and it leaves a locally verifiable recovery bundle
before replaying the branch's responsibility commits on an exact origin/main.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CONFIRMATION = "REBASE_UNPUBLISHED_BRANCH_ON_EXACT_MAIN"
EXTENDED_CONFIRMATION = "REBASE_APPROVED_FROZEN_BRANCH_ON_EXACT_MAIN"
GENERATED_CONFIRMATION = "REBASE_AND_REBUILD_GENERATED_EVIDENCE_ON_EXACT_MAIN"
MAX_RESPONSIBILITY_COMMITS = 12
MAX_EXTENDED_RESPONSIBILITY_COMMITS = 64
APPEND_ONLY_CONFLICT_PATH = "docs/ops/iterations/delivery_context_switch_log_v1.md"
ACTIVE_RUNS_INDEX_PATH = ".agent/active-runs.json"
PERSONAL_DATA_FALSE_POSITIVES_PATH = "scripts/ci/personal_data_false_positives.json"
SEMANTIC_UNION_CONFLICT_PATH = (
    "scripts/verify/frontend_my_work_approval_browser.mjs"
)
SEMANTIC_UNION_REQUIRED_MARKERS = (
    (
        "upstream approval-detail readback",
        ("const approvedForm", "approvedAmountField", "cross_page_readout"),
    ),
    (
        "U06 approval-page decision flow",
        ("rejectSafetyDialog", "action_approval_reject", "action_params?.reason"),
    ),
)
GENERATED_EVIDENCE_CONFLICT_PATHS = (
    "contracts/generated/contract_structure_fingerprint.json",
    "docs/audit/test_coverage_registry/test_coverage_registry.json",
    "docs/engineering_convergence/complexity_budget_report.md",
    "docs/engineering_convergence/e2e_journey_matrix.md",
    "docs/engineering_convergence/github_remote_execute.sh",
    "docs/engineering_convergence/github_remote_execution_plan.md",
    "docs/engineering_convergence/module_dependency_map.md",
    "docs/engineering_convergence/split_plan_queue.md",
    "docs/engineering_convergence/test_inventory.csv",
    "docs/engineering_convergence/test_inventory_summary.md",
    "docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json",
    "docs/engineering_convergence/p4_p0_03_contract_form_split_evidence.md",
    "addons/smart_core/core/contract_runtime/semantic_registry_generated.py",
    "addons/smart_core/core/contract_runtime/domain_field_semantics_generated.py",
    "frontend/apps/web/src/app/presentation/semantic_registry.generated.ts",
)
# The original refresh entry and its producer implementation must come from
# exact main. In particular, governance registries are inputs, never outputs.
GENERATOR_SOURCE_PATHS = (
    "Makefile", "make", "scripts/ci", "scripts/audit", "scripts/contract",
    "scripts/verify/test_coverage_registry_audit.py",
)
CANONICAL_ORIGIN_URLS = {
    "https://github.com/lidefend/sce-backend-odoo.git",
    "git@github.com:lidefend/sce-backend-odoo.git",
}


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncPlan:
    root: Path
    branch: str
    head: str
    old_base: str
    new_main: str
    commit_count: int
    paths: tuple[str, ...]
    recovery_bundle: Path
    extended_history: bool = False
    dependency_head: str | None = None
    covered_prefix: str | None = None
    covered_merge: str | None = None
    regenerate_evidence: bool = False

    @property
    def replay_base(self) -> str:
        return self.covered_prefix or self.dependency_head or self.old_base


@dataclass(frozen=True)
class SyncResult:
    head: str
    generated_evidence_conflicts: tuple[str, ...] = ()
    metadata_conflicts: tuple[str, ...] = ()
    main_equivalent_paths: tuple[str, ...] = ()
    generated_commit: str | None = None
    generated_evidence_replay_paths: tuple[str, ...] = ()
    semantic_conflicts: tuple[str, ...] = ()


def sanitized_environment() -> dict[str, str]:
    """Do not inherit caller-controlled Git execution identity."""
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def run(root: Path, *args: str, check: bool = True, input: str | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=root, env=sanitized_environment(), text=True,
        input=input, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if check and result.returncode:
        raise SyncError(f"git {' '.join(args)} failed: {result.stdout.strip()}")
    return result


def git_output(root: Path, *args: str) -> str:
    return run(root, *args).stdout.strip()


def ensure_sha(label: str, value: str) -> None:
    if not FULL_SHA.fullmatch(value):
        raise SyncError(f"{label} must be a full 40-character lowercase SHA")


def has_open_pr(branch: str) -> bool:
    """Published or review-visible work must never have its history rewritten."""
    result = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--head", branch, "--json", "number", "--jq", "length"],
        env=sanitized_environment(), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode:
        raise SyncError("unable to verify open PR state; refuse branch sync")
    return result.stdout.strip() != "0"


def has_canonical_origin(root: Path) -> bool:
    return git_output(root, "remote", "get-url", "origin") in CANONICAL_ORIGIN_URLS


def merged_dependency(pr: int) -> dict:
    result = subprocess.run(
        ["gh", "pr", "view", str(pr), "--repo", "lidefend/sce-backend-odoo",
         "--json", "number,state,baseRefName,headRefOid,mergeCommit"],
        env=sanitized_environment(), text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise SyncError("unable to verify merged dependency PR")
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise SyncError("invalid merged dependency PR response") from exc
    if not isinstance(value, dict):
        raise SyncError("invalid merged dependency PR response")
    return value


def validate_dependency(root: Path, *, pr: int, head: str, merge: str,
                        candidate: str, old_base: str, main: str,
                        reader: Callable[[int], dict]) -> None:
    ensure_sha("DEPENDENCY_HEAD", head)
    ensure_sha("DEPENDENCY_MERGE", merge)
    if pr <= 0:
        raise SyncError("dependency PR must be positive")
    info = reader(pr)
    if (info.get("number") != pr or info.get("state") != "MERGED"
            or info.get("baseRefName") != "main" or info.get("headRefOid") != head
            or not isinstance(info.get("mergeCommit"), dict)
            or info["mergeCommit"].get("oid") != merge):
        raise SyncError("merged dependency PR identity mismatch")
    for sha in (head, merge):
        if not commit_exists(root, sha):
            raise SyncError("dependency commit is unavailable")
    for left, right in ((old_base, head), (head, candidate), (merge, main)):
        if run(root, "merge-base", "--is-ancestor", left, right, check=False).returncode:
            raise SyncError("dependency ancestry mismatch")
    if head == old_base or head == candidate or head == merge:
        raise SyncError("dependency must leave a distinct responsibility range")
    if len(git_output(root, "rev-list", "--parents", "-n", "1", merge).split()) != 2:
        raise SyncError("dependency merge must be a single-parent squash commit")
    if git_output(root, "rev-parse", f"{head}^{{tree}}") != git_output(root, "rev-parse", f"{merge}^{{tree}}"):
        raise SyncError("dependency source and squash trees differ")


def has_exact_quick_evidence(root: Path, governance_root: Path, head: str) -> bool:
    verifier = governance_root / "scripts/ops/local_quick_evidence.py"
    result = subprocess.run(
        [
            sys.executable,
            str(verifier),
            "verify",
            "--root",
            str(root),
            "--expected-head",
            head,
        ],
        cwd=root,
        env=sanitized_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.returncode == 0


def require_clean(root: Path) -> None:
    if git_output(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise SyncError("worktree must be clean, including untracked files")


def common_git_dir(root: Path) -> Path:
    return Path(git_output(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()


def require_no_writer(root: Path) -> None:
    common = common_git_dir(root)
    locks = (common / "index.lock", common / "packed-refs.lock", common / "rebase-merge", common / "rebase-apply")
    if any(path.exists() for path in locks):
        raise SyncError("Git writer or unfinished history operation is active")
    if run(root, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0:
        raise SyncError("unfinished merge is active")


def ref_exists(root: Path, ref: str) -> bool:
    return run(root, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0


def commit_exists(root: Path, sha: str) -> bool:
    return run(root, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode == 0


def commit_paths(root: Path, left: str, right: str) -> tuple[str, ...]:
    return tuple(sorted(filter(None, git_output(root, "diff", "--name-only", left, right).splitlines())))


def path_equals_revision(root: Path, left: str, right: str, path: str) -> bool:
    return run(root, "diff", "--quiet", left, right, "--", path, check=False).returncode == 0


def generated_only_commit_count(plan: SyncPlan, paths: tuple[str, ...]) -> int:
    """Count responsibility commits whose complete diff is invalidated evidence.

    Rebase may legitimately drop such a commit after a registered generated
    evidence conflict is resolved to the exact new-main version.  This count is
    only a ceiling for commit-count shrinkage; aggregate path and patch identity
    checks still prove that no stable responsibility change disappeared.
    """
    allowed = set(paths)
    if not allowed:
        return 0
    commits = filter(
        None,
        git_output(
            plan.root,
            "rev-list",
            "--reverse",
            f"{plan.replay_base}..{plan.head}",
        ).splitlines(),
    )
    count = 0
    for commit in commits:
        changed = set(
            filter(
                None,
                git_output(
                    plan.root,
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    commit,
                ).splitlines(),
            )
        )
        if changed and changed.issubset(allowed):
            count += 1
    return count


def patch_id(root: Path, left: str, right: str, *, exclude: tuple[str, ...] = ()) -> str:
    args = ["diff", "--binary", left, right]
    if exclude:
        args.extend(("--", "."))
        args.extend(f":(exclude){path}" for path in exclude)
    diff = run(root, *args).stdout
    result = subprocess.run(
        ["git", "patch-id", "--stable"], cwd=root, env=sanitized_environment(), input=diff,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode or not result.stdout.strip():
        raise SyncError("unable to calculate responsibility patch identity")
    return result.stdout.split()[0]


def recovery_path(root: Path, branch: str, head: str) -> Path:
    safe_branch = branch.replace("/", "-")
    return common_git_dir(root) / "codex-recovery" / "branch-sync" / f"{safe_branch}-{head}.bundle"


def validate(
    *, root: Path, expected_root: Path, governance_root: Path, expected_branch: str, expected_head: str,
    expected_old_base: str, expected_main: str, pr_checker: Callable[[str], bool] = has_open_pr,
    origin_checker: Callable[[Path], bool] = has_canonical_origin,
    allow_extended_history: bool = False, expected_commit_count: int | None = None,
    quick_evidence_checker: Callable[[Path, Path, str], bool] = has_exact_quick_evidence,
    dependency_pr: int | None = None, dependency_head: str | None = None,
    dependency_merge: str | None = None,
    dependency_reader: Callable[[int], dict] = merged_dependency,
    covered_prefix: str | None = None,
    covered_merge: str | None = None,
    regenerate_evidence: bool = False,
) -> SyncPlan:
    root = root.resolve()
    expected_root = expected_root.resolve()
    governance_root = governance_root.resolve()
    for label, value in (("EXPECTED_HEAD", expected_head), ("EXPECTED_OLD_BASE", expected_old_base), ("EXPECTED_MAIN", expected_main)):
        ensure_sha(label, value)
    actual_root = Path(git_output(root, "rev-parse", "--show-toplevel")).resolve()
    if root != actual_root or expected_root != actual_root:
        raise SyncError("worktree path and expected repository root must match")
    actual_governance_root = Path(
        git_output(governance_root, "rev-parse", "--show-toplevel")
    ).resolve()
    if governance_root != actual_governance_root:
        raise SyncError("governance root must be a repository root")
    if common_git_dir(root) != common_git_dir(governance_root):
        raise SyncError("worktree must share the governance repository identity")
    actual_branch = git_output(root, "branch", "--show-current")
    if actual_branch != expected_branch or not ALLOWED_BRANCH.fullmatch(actual_branch):
        raise SyncError("current branch does not match a write-eligible expected branch")
    actual_head = git_output(root, "rev-parse", "HEAD")
    if actual_head != expected_head:
        raise SyncError("current HEAD does not match EXPECTED_HEAD")
    require_clean(root)
    require_no_writer(root)
    if not origin_checker(root):
        raise SyncError("origin remote does not match the governed repository identity")
    run(root, "fetch", "--no-tags", "origin", "main")
    if not ref_exists(root, "refs/remotes/origin/main"):
        raise SyncError("origin/main is unavailable")
    actual_main = git_output(root, "rev-parse", "origin/main")
    if actual_main != expected_main:
        raise SyncError("origin/main does not match EXPECTED_MAIN")
    if not commit_exists(root, expected_old_base):
        raise SyncError("EXPECTED_OLD_BASE does not name an available commit")
    if not commit_exists(root, expected_main):
        raise SyncError("EXPECTED_MAIN does not name an available commit")
    if git_output(root, "merge-base", "HEAD", "origin/main") != expected_old_base:
        raise SyncError("merge base does not match EXPECTED_OLD_BASE")
    if run(root, "merge-base", "--is-ancestor", expected_old_base, expected_main, check=False).returncode:
        raise SyncError("EXPECTED_OLD_BASE must be an ancestor of EXPECTED_MAIN")
    if ref_exists(root, f"refs/remotes/origin/{actual_branch}"):
        raise SyncError("remote branch already exists; published history cannot be rewritten")
    remote = run(root, "ls-remote", "--heads", "origin", f"refs/heads/{actual_branch}").stdout.strip()
    if remote:
        raise SyncError("remote branch already exists; published history cannot be rewritten")
    if pr_checker(actual_branch):
        raise SyncError("open PR exists; published history cannot be rewritten")
    if dependency_head and covered_prefix:
        raise SyncError("merged dependency and covered prefix are mutually exclusive")
    covered_values = (covered_prefix, covered_merge)
    if any(value is not None for value in covered_values):
        if not all(value is not None for value in covered_values):
            raise SyncError("covered prefix and covered merge must be supplied together")
        if not allow_extended_history:
            raise SyncError("covered prefix requires the extended frozen sync path")
        prefix, prefix_merge = covered_values
        ensure_sha("COVERED_PREFIX", prefix)
        ensure_sha("COVERED_MERGE", prefix_merge)
        for sha in (prefix, prefix_merge):
            if not commit_exists(root, sha):
                raise SyncError("covered prefix commit is unavailable")
        for left, right in (
            (expected_old_base, prefix),
            (prefix, expected_head),
            (expected_old_base, prefix_merge),
            (prefix_merge, expected_main),
        ):
            if run(root, "merge-base", "--is-ancestor", left, right, check=False).returncode:
                raise SyncError("covered prefix ancestry mismatch")
        if prefix in {expected_old_base, expected_head}:
            raise SyncError("covered prefix must leave a distinct responsibility range")
        if len(git_output(root, "rev-list", "--parents", "-n", "1", prefix_merge).split()) != 2:
            raise SyncError("covered merge must be a single-parent squash commit")
        prefix_paths = set(commit_paths(root, expected_old_base, prefix))
        merge_paths = set(commit_paths(root, expected_old_base, prefix_merge))
        uncovered = sorted(prefix_paths - merge_paths)
        if uncovered:
            raise SyncError(
                "covered merge does not touch every prefix path: " + ", ".join(uncovered[:8])
            )
    dependency_values = (dependency_pr, dependency_head, dependency_merge)
    if any(value is not None for value in dependency_values):
        if not all(value is not None for value in dependency_values):
            raise SyncError("dependency PR, head and merge must be supplied together")
        validate_dependency(root, pr=dependency_pr, head=dependency_head, merge=dependency_merge,
                            candidate=expected_head, old_base=expected_old_base, main=expected_main,
                            reader=dependency_reader)
    replay_base = dependency_head or covered_prefix or expected_old_base
    merges = git_output(root, "rev-list", "--merges", f"{replay_base}..{expected_head}")
    if merges:
        raise SyncError("responsibility branch contains merge commits")
    commits = tuple(filter(None, git_output(root, "rev-list", "--reverse", f"{replay_base}..{expected_head}").splitlines()))
    if allow_extended_history:
        if not quick_evidence_checker(root, governance_root, expected_head):
            raise SyncError("extended sync requires valid worktree-local exact-head Quick evidence")
        if expected_commit_count is None or expected_commit_count != len(commits):
            raise SyncError("extended sync requires an exact matching EXPECTED_COMMIT_COUNT")
        minimum = 1 if covered_prefix else MAX_RESPONSIBILITY_COMMITS + 1
        if not minimum <= len(commits) <= MAX_EXTENDED_RESPONSIBILITY_COMMITS:
            raise SyncError(
                "extended responsibility commit count must be within "
                f"{minimum}..{MAX_EXTENDED_RESPONSIBILITY_COMMITS}"
            )
    elif not 1 <= len(commits) <= MAX_RESPONSIBILITY_COMMITS:
        raise SyncError(f"responsibility commit count must be within 1..{MAX_RESPONSIBILITY_COMMITS}")
    paths = commit_paths(root, replay_base, expected_head)
    if not paths:
        raise SyncError("responsibility branch has no changed paths")
    if allow_extended_history:
        stable_paths = tuple(
            path
            for path in paths
            if path not in {APPEND_ONLY_CONFLICT_PATH, *GENERATED_EVIDENCE_CONFLICT_PATHS}
        )
        if not stable_paths:
            raise SyncError("extended sync requires at least one non-generated responsibility path")
    return SyncPlan(
        root, actual_branch, actual_head, expected_old_base, expected_main,
        len(commits), paths, recovery_path(root, actual_branch, actual_head),
        extended_history=allow_extended_history,
        dependency_head=dependency_head,
        covered_prefix=covered_prefix,
        covered_merge=covered_merge,
        regenerate_evidence=regenerate_evidence,
    )


def create_bundle(plan: SyncPlan) -> None:
    plan.recovery_bundle.parent.mkdir(parents=True, exist_ok=True)
    run(
        plan.root,
        "bundle",
        "create",
        str(plan.recovery_bundle),
        f"refs/heads/{plan.branch}",
        f"^{plan.old_base}",
    )
    run(plan.root, "bundle", "verify", str(plan.recovery_bundle))


def text_at_revision(root: Path, revision: str, path: str) -> str:
    result = run(root, "show", f"{revision}:{path}", check=False)
    if result.returncode:
        raise SyncError(f"append-only conflict source is unavailable: {path}")
    return result.stdout


def resolve_append_only_log_conflict(plan: SyncPlan, conflicts: tuple[str, ...]) -> bool:
    """Resolve only a pure append conflict in the formal delivery log.

    Both branch versions must retain the old-base text verbatim and only append
    new entries. The result keeps main's entries first, then appends the local
    branch's suffix. Any other conflict remains a fail-closed abort.
    """
    if APPEND_ONLY_CONFLICT_PATH not in conflicts:
        return False
    base = text_at_revision(plan.root, plan.replay_base, APPEND_ONLY_CONFLICT_PATH)
    main = text_at_revision(plan.root, plan.new_main, APPEND_ONLY_CONFLICT_PATH)
    topic = text_at_revision(plan.root, plan.head, APPEND_ONLY_CONFLICT_PATH)
    if not main.startswith(base) or not topic.startswith(base):
        return False
    target = plan.root / APPEND_ONLY_CONFLICT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(main + topic[len(base):], encoding="utf-8")
    run(plan.root, "add", "--", APPEND_ONLY_CONFLICT_PATH)
    return True


def generated_output_path(root: Path, path: str) -> Path:
    target = root / path
    for item in (target, *target.parents):
        if item == root:
            break
        if item.is_symlink():
            raise SyncError(f"generated output must not traverse a symlink: {path}")
    return target


def resolve_generated_evidence_conflicts(
    plan: SyncPlan, conflicts: tuple[str, ...]
) -> tuple[str, ...]:
    resolved = tuple(
        path for path in conflicts if path in GENERATED_EVIDENCE_CONFLICT_PATHS
    )
    for path in resolved:
        target = generated_output_path(plan.root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text_at_revision(plan.root, plan.new_main, path), encoding="utf-8")
        run(plan.root, "add", "--", path)
    return resolved


def verify_semantic_union_text(path: str, text: str) -> None:
    """Require both reviewed behaviours before preserving the prepared file."""
    if "<<<<<<<" in text or ">>>>>>>" in text:
        raise SyncError(f"semantic union source still contains conflict markers: {path}")
    for label, markers in SEMANTIC_UNION_REQUIRED_MARKERS:
        missing = [marker for marker in markers if marker not in text]
        if missing:
            raise SyncError(
                f"semantic union source for {path} is missing {label}: "
                + ", ".join(missing)
            )


def resolve_semantic_union_conflict(
    plan: SyncPlan, conflicts: tuple[str, ...]
) -> tuple[str, ...]:
    """Preserve one pre-reviewed path whose competing hunks form a semantic union.

    The topic head is already the reviewed union of the upstream readback
    assertions and the U06 approval-page execution journey.  Replaying its
    final form at the first collision is deterministic; later topic commits for
    the same path may become empty because their aggregate content is already
    present.  Aggregate path and patch identity still prove that no stable
    responsibility disappeared, and the journey must be rerun after the sync.
    """
    resolved = tuple(
        path for path in conflicts if path == SEMANTIC_UNION_CONFLICT_PATH
    )
    if not resolved:
        return ()
    if not plan.extended_history:
        raise SyncError("semantic union conflicts require the extended frozen sync")
    text = text_at_revision(plan.root, plan.head, SEMANTIC_UNION_CONFLICT_PATH)
    verify_semantic_union_text(SEMANTIC_UNION_CONFLICT_PATH, text)
    target = generated_output_path(plan.root, SEMANTIC_UNION_CONFLICT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    run(plan.root, "add", "--", SEMANTIC_UNION_CONFLICT_PATH)
    return resolved


def merge_active_runs_index(plan: SyncPlan) -> None:
    """Three-way merge the branch-to-run index without inventing entries."""
    try:
        base = json.loads(text_at_revision(plan.root, plan.replay_base, ACTIVE_RUNS_INDEX_PATH))
        main = json.loads(text_at_revision(plan.root, plan.new_main, ACTIVE_RUNS_INDEX_PATH))
        topic = json.loads(text_at_revision(plan.root, plan.head, ACTIVE_RUNS_INDEX_PATH))
    except (ValueError, TypeError) as exc:
        raise SyncError("active-runs index is not valid JSON") from exc
    rows = []
    for label, payload in (("base", base), ("main", main), ("topic", topic)):
        branches = payload.get("branches") if isinstance(payload, dict) else None
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise SyncError(f"active-runs {label} schema_version must be 1")
        if not isinstance(branches, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in branches.items()
        ):
            raise SyncError(f"active-runs {label} branches must map strings to strings")
        rows.append(branches)
    base_rows, main_rows, topic_rows = rows
    merged = dict(base_rows)
    for key, value in main_rows.items():
        if key not in topic_rows or topic_rows[key] == value or base_rows.get(key) == topic_rows[key]:
            merged[key] = value
    for key, value in topic_rows.items():
        if key not in main_rows or main_rows[key] == value or base_rows.get(key) == main_rows[key]:
            merged[key] = value
        elif main_rows.get(key) != value and base_rows.get(key) not in {None, value}:
            raise SyncError(f"active-runs index conflicts for branch {key}")
    target = plan.root / ACTIVE_RUNS_INDEX_PATH
    target.write_text(
        json.dumps({"schema_version": 1, "branches": dict(sorted(merged.items()))}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    run(plan.root, "add", "--", ACTIVE_RUNS_INDEX_PATH)


def verify_active_runs_resolution(plan: SyncPlan) -> None:
    base = json.loads(text_at_revision(plan.root, plan.replay_base, ACTIVE_RUNS_INDEX_PATH))
    main = json.loads(text_at_revision(plan.root, plan.new_main, ACTIVE_RUNS_INDEX_PATH))
    topic = json.loads(text_at_revision(plan.root, plan.head, ACTIVE_RUNS_INDEX_PATH))
    current = json.loads((plan.root / ACTIVE_RUNS_INDEX_PATH).read_text(encoding="utf-8"))
    base_rows, main_rows, topic_rows = base["branches"], main["branches"], topic["branches"]
    expected = dict(base_rows)
    for key, value in main_rows.items():
        if key not in topic_rows or topic_rows[key] == value or base_rows.get(key) == topic_rows[key]:
            expected[key] = value
    for key, value in topic_rows.items():
        if key not in main_rows or main_rows[key] == value or base_rows.get(key) == main_rows[key]:
            expected[key] = value
    if current != {"schema_version": 1, "branches": dict(sorted(expected.items()))}:
        raise SyncError("active-runs index merge changed during sync")


def personal_data_false_positives_union(plan: SyncPlan) -> dict:
    """Union exact scan exemptions without accepting conflicting metadata."""
    try:
        revisions = [
            json.loads(text_at_revision(plan.root, revision, PERSONAL_DATA_FALSE_POSITIVES_PATH))
            for revision in (plan.replay_base, plan.new_main, plan.head)
        ]
    except (ValueError, TypeError) as exc:
        raise SyncError("personal-data false-positive registry is not valid JSON") from exc
    merged: dict[tuple[str, str, str, str], dict] = {}
    for revision, payload in zip(
        ("base", "main", "topic"), revisions, strict=True
    ):
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise SyncError(
                f"personal-data false-positive {revision} schema_version must be 1"
            )
        if not isinstance(entries, list):
            raise SyncError(
                f"personal-data false-positive {revision} entries must be a list"
            )
        for entry in entries:
            if not isinstance(entry, dict):
                raise SyncError(
                    f"personal-data false-positive {revision} entries must be objects"
                )
            key = tuple(
                str(entry.get(field) or "").strip()
                for field in ("rule_id", "path", "blob_id", "classification")
            )
            if not all(key):
                raise SyncError(
                    "personal-data false-positive entries require rule_id, path, "
                    "blob_id and classification"
                )
            current = merged.get(key)
            if current is not None and current != entry:
                changed_fields = {
                    field
                    for field in set(current) | set(entry)
                    if current.get(field) != entry.get(field)
                }
                if (
                    revision == "topic"
                    and changed_fields == {"reason"}
                    and current.get("reason")
                    and entry.get("reason")
                ):
                    # Exact blob identity makes the reason explanatory metadata;
                    # retain main's reviewed wording on a concurrent registration.
                    continue
                raise SyncError(
                    "personal-data false-positive metadata conflicts for exact key: "
                    + ":".join(key)
                )
            merged[key] = entry
    return {
        "schema_version": 1,
        "entries": [merged[key] for key in sorted(merged)],
    }


def merge_personal_data_false_positives(plan: SyncPlan) -> None:
    target = plan.root / PERSONAL_DATA_FALSE_POSITIVES_PATH
    target.write_text(
        json.dumps(
            personal_data_false_positives_union(plan),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    run(plan.root, "add", "--", PERSONAL_DATA_FALSE_POSITIVES_PATH)


def verify_personal_data_false_positives_resolution(plan: SyncPlan) -> None:
    try:
        current = json.loads(
            (plan.root / PERSONAL_DATA_FALSE_POSITIVES_PATH).read_text(
                encoding="utf-8"
            )
        )
    except (ValueError, TypeError) as exc:
        raise SyncError(
            "personal-data false-positive registry is not valid JSON"
        ) from exc
    if current != personal_data_false_positives_union(plan):
        raise SyncError("personal-data false-positive registry merge changed during sync")


def run_rebase(
    plan: SyncPlan,
) -> tuple[bool, tuple[str, ...], tuple[str, ...], tuple[str, ...]] | None:
    append_only_log_resolved = False
    generated_evidence_conflicts: set[str] = set()
    metadata_conflicts: set[str] = set()
    semantic_conflicts: set[str] = set()
    result = run(plan.root, "rebase", "--onto", plan.new_main, plan.replay_base, check=False)
    while result.returncode:
        conflicts = tuple(
            sorted(
                filter(
                    None,
                    git_output(plan.root, "diff", "--name-only", "--diff-filter=U").splitlines(),
                )
            )
        )
        allowed = {APPEND_ONLY_CONFLICT_PATH, ACTIVE_RUNS_INDEX_PATH}
        if plan.extended_history or plan.regenerate_evidence:
            allowed.update(GENERATED_EVIDENCE_CONFLICT_PATHS)
        if plan.extended_history:
            allowed.add(SEMANTIC_UNION_CONFLICT_PATH)
            allowed.add(PERSONAL_DATA_FALSE_POSITIVES_PATH)
        if not conflicts or any(path not in allowed for path in conflicts):
            diagnostic = plan.recovery_bundle.with_suffix(".conflict.json")
            diagnostic.parent.mkdir(parents=True, exist_ok=True)
            diagnostic.write_text(json.dumps({
                "head": plan.head, "main": plan.new_main,
                "conflicts": list(conflicts), "git_output": result.stdout,
            }, indent=2) + "\n", encoding="utf-8")
            raise SyncError("unsupported rebase conflict paths: " +
                            ", ".join(conflicts or ("<none>",)) +
                            f"; diagnostic={diagnostic}")
        if APPEND_ONLY_CONFLICT_PATH in conflicts:
            if not resolve_append_only_log_conflict(plan, conflicts):
                return None
            append_only_log_resolved = True
        generated_evidence_conflicts.update(
            resolve_generated_evidence_conflicts(plan, conflicts)
        )
        semantic_conflicts.update(
            resolve_semantic_union_conflict(plan, conflicts)
        )
        if ACTIVE_RUNS_INDEX_PATH in conflicts:
            merge_active_runs_index(plan)
            metadata_conflicts.add(ACTIVE_RUNS_INDEX_PATH)
        if PERSONAL_DATA_FALSE_POSITIVES_PATH in conflicts:
            merge_personal_data_false_positives(plan)
            metadata_conflicts.add(PERSONAL_DATA_FALSE_POSITIVES_PATH)
        result = run(plan.root, "-c", "core.editor=true", "rebase", "--continue", check=False)
    return (
        append_only_log_resolved,
        tuple(sorted(generated_evidence_conflicts)),
        tuple(sorted(metadata_conflicts)),
        tuple(sorted(semantic_conflicts)),
    )


def verify_append_only_log_resolution(plan: SyncPlan) -> None:
    base = text_at_revision(plan.root, plan.replay_base, APPEND_ONLY_CONFLICT_PATH)
    main = text_at_revision(plan.root, plan.new_main, APPEND_ONLY_CONFLICT_PATH)
    topic = text_at_revision(plan.root, plan.head, APPEND_ONLY_CONFLICT_PATH)
    current = (plan.root / APPEND_ONLY_CONFLICT_PATH).read_text(encoding="utf-8")
    if not main.startswith(base) or not topic.startswith(base):
        raise SyncError("append-only conflict inputs changed during sync")
    if current != main + topic[len(base):]:
        raise SyncError("append-only delivery log suffix was not preserved")


def restore_original_head(plan: SyncPlan) -> None:
    """Restore the exact pre-sync branch without using a destructive hard reset."""
    current_head = git_output(plan.root, "rev-parse", "HEAD")
    run(
        plan.root,
        "update-ref",
        f"refs/heads/{plan.branch}",
        plan.head,
        current_head,
    )
    run(plan.root, "restore", "--source", plan.head, "--staged", "--worktree", "--", ".")
    if git_output(plan.root, "rev-parse", "HEAD") != plan.head:
        raise SyncError("failed to restore original HEAD; use recovery bundle")
    require_clean(plan.root)


def abort_rebase_and_restore(plan: SyncPlan) -> None:
    aborted = run(plan.root, "rebase", "--abort", check=False)
    if aborted.returncode == 0:
        if git_output(plan.root, "rev-parse", "HEAD") != plan.head:
            raise SyncError("rebase abort did not restore original HEAD; use recovery bundle")
        require_clean(plan.root)
        return
    restore_original_head(plan)


def untracked_paths(root: Path) -> set[str]:
    return set(filter(None, run(root, "ls-files", "--others", "--exclude-standard", "-z").stdout.split("\0")))


def cleanup_new_untracked(root: Path, original: set[str]) -> None:
    # No recursive clean and no removal of pre-existing evidence/dependencies.
    for name in untracked_paths(root) - original:
        path = root / name
        if path.is_file() or path.is_symlink():
            path.unlink()


def regenerate_reports(plan: SyncPlan) -> str | None:
    for path in GENERATED_EVIDENCE_CONFLICT_PATHS:
        generated_output_path(plan.root, path)
    if git_output(plan.root, "diff", plan.new_main, "--", *GENERATOR_SOURCE_PATHS):
        raise SyncError("generated rebuild requires unchanged main producer sources and Make recipes")
    before = git_output(plan.root, "rev-parse", "HEAD")
    log = plan.recovery_bundle.with_suffix(".generation.log")
    environment = sanitized_environment()
    for key in ("MAKEFLAGS", "MFLAGS", "MAKEFILES", "MAKELEVEL"):
        environment.pop(key, None)
    allowed = set(GENERATED_EVIDENCE_CONFLICT_PATHS)

    def verify_writes() -> tuple[str, ...]:
        changed = set(git_output(plan.root, "diff", "--name-only", before).splitlines())
        changed.update(untracked_paths(plan.root))
        unexpected = sorted(changed - allowed)
        if unexpected:
            raise SyncError("generator/hook changed non-generated paths: " + ", ".join(unexpected))
        for path in changed:
            generated_output_path(plan.root, path)
        return tuple(sorted(changed))

    with log.open("w", encoding="utf-8") as stream:
        for target in ("refresh.generated_evidence", "ci.generated_evidence.preflight"):
            stream.write(f"make {target}\n")
            stream.flush()
            result = subprocess.run(["make", "--no-print-directory", target], cwd=plan.root,
                                    env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                    check=False, timeout=300)
            verify_writes()
            if result.returncode:
                raise SyncError(f"original generator/check failed: {target}; log={log}")
    changed = verify_writes()
    if not changed:
        return None
    run(plan.root, "add", "--", *changed)
    # Real commit hooks remain enabled. Their writes are checked as well.
    run(plan.root, "commit", "-m", "chore: regenerate reports after governed main sync")
    verify_writes()
    if git_output(plan.root, "rev-parse", "HEAD^") != before:
        raise SyncError("generator commit changed responsibility history")
    require_clean(plan.root)
    return git_output(plan.root, "rev-parse", "HEAD")


def sync(plan: SyncPlan) -> SyncResult:
    original_untracked = untracked_paths(plan.root)
    create_bundle(plan)
    try:
        rebase_result = run_rebase(plan)
    except Exception as exc:
        cleanup_new_untracked(plan.root, original_untracked)
        abort_rebase_and_restore(plan)
        raise SyncError(f"rebase conflict aborted; original HEAD was restored: {exc}") from exc
    if rebase_result is None:
        abort_rebase_and_restore(plan)
        raise SyncError("rebase conflict; aborted and restored original HEAD")
    (
        append_only_log_resolved,
        generated_evidence_conflicts,
        metadata_conflicts,
        semantic_conflicts,
    ) = rebase_result
    try:
        new_head = git_output(plan.root, "rev-parse", "HEAD")
        require_clean(plan.root)
        new_commits = tuple(filter(None, git_output(plan.root, "rev-list", "--reverse", f"{plan.new_main}..{new_head}").splitlines()))
        new_paths = commit_paths(plan.root, plan.new_main, new_head)
        # Replaying a generated change and later revert may create drift even
        # without a Git conflict (main may already contain the first change).
        # Only explicit regeneration lets the original producer replace these
        # derived diffs; all other responsibility paths keep exact comparison.
        rebuild_paths = set(GENERATED_EVIDENCE_CONFLICT_PATHS) if plan.regenerate_evidence else set()
        generated_replay_paths = tuple(sorted((set(plan.paths) | set(new_paths)) & rebuild_paths))
        excluded_paths = tuple(sorted({
            *generated_evidence_conflicts,
            *metadata_conflicts,
            *semantic_conflicts,
            *rebuild_paths,
        }))
        old_stable_paths = tuple(path for path in plan.paths if path not in excluded_paths)
        new_stable_paths = tuple(path for path in new_paths if path not in excluded_paths)
        extra_paths = sorted(set(new_stable_paths) - set(old_stable_paths))
        if extra_paths:
            raise SyncError("responsibility path set changed after sync: " + ", ".join(extra_paths[:8]))
        main_equivalent_paths = tuple(
            path
            for path in old_stable_paths
            if path not in set(new_stable_paths)
            and path_equals_revision(plan.root, plan.head, plan.new_main, path)
        )
        missing_paths = sorted(
            set(old_stable_paths) - set(new_stable_paths) - set(main_equivalent_paths)
        )
        if missing_paths:
            raise SyncError(
                "responsibility path set changed after sync: "
                + ", ".join(missing_paths[:8])
            )
        maximum_drop = generated_only_commit_count(
            plan,
            tuple(
                sorted(
                    {
                        *generated_evidence_conflicts,
                        *rebuild_paths,
                        *metadata_conflicts,
                        *semantic_conflicts,
                        *main_equivalent_paths,
                    }
                )
            ),
        )
        if not plan.commit_count - maximum_drop <= len(new_commits) <= plan.commit_count:
            raise SyncError("responsibility commit count changed after sync")
        if append_only_log_resolved:
            verify_append_only_log_resolution(plan)
        if metadata_conflicts:
            if ACTIVE_RUNS_INDEX_PATH in metadata_conflicts:
                verify_active_runs_resolution(plan)
            if PERSONAL_DATA_FALSE_POSITIVES_PATH in metadata_conflicts:
                verify_personal_data_false_positives_resolution(plan)
        for path in semantic_conflicts:
            if not path_equals_revision(plan.root, new_head, plan.head, path):
                raise SyncError(
                    f"semantic union path changed during sync: {path}"
                )
            verify_semantic_union_text(
                path,
                text_at_revision(plan.root, new_head, path),
            )
        patch_excludes = tuple(
            sorted(
                {
                    *excluded_paths,
                    *main_equivalent_paths,
                    *([APPEND_ONLY_CONFLICT_PATH] if append_only_log_resolved else []),
                }
            )
        )
        stable_identity_paths = tuple(
            path
            for path in old_stable_paths
            if path not in patch_excludes and path not in set(main_equivalent_paths)
        )
        if stable_identity_paths and patch_id(
            plan.root, plan.replay_base, plan.head, exclude=patch_excludes
        ) != patch_id(plan.root, plan.new_main, new_head, exclude=patch_excludes):
            raise SyncError("responsibility patch identity changed after sync")
        generated_commit = regenerate_reports(plan) if plan.regenerate_evidence else None
        new_head = git_output(plan.root, "rev-parse", "HEAD")
    except Exception as exc:
        cleanup_new_untracked(plan.root, original_untracked)
        restore_original_head(plan)
        if isinstance(exc, SyncError):
            raise SyncError(f"{exc}; original HEAD restored") from exc
        raise SyncError(f"post-sync verification failed; original HEAD restored: {exc}") from exc
    return SyncResult(
        new_head,
        generated_evidence_conflicts,
        metadata_conflicts,
        main_equivalent_paths,
        generated_commit,
        generated_replay_paths,
        semantic_conflicts,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-root", required=True)
    parser.add_argument("--governance-root", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-old-base", required=True)
    parser.add_argument("--expected-main", required=True)
    parser.add_argument("--expected-commit-count", type=int)
    parser.add_argument("--dependency-pr", type=int)
    parser.add_argument("--dependency-head")
    parser.add_argument("--dependency-merge")
    parser.add_argument("--covered-prefix")
    parser.add_argument("--covered-merge")
    parser.add_argument("--allow-extended-history", action="store_true")
    parser.add_argument("--regenerate-evidence", action="store_true")
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    expected_confirmation = (EXTENDED_CONFIRMATION if args.allow_extended_history else
                             GENERATED_CONFIRMATION if args.regenerate_evidence else CONFIRMATION)
    if args.confirm != expected_confirmation:
        print(
            "[workspace.branch.sync-main] DENY confirmation must equal "
            f"{expected_confirmation}",
            file=sys.stderr,
        )
        return 2
    try:
        plan = validate(
            root=Path.cwd(), expected_root=Path(args.expected_root), governance_root=Path(args.governance_root),
            expected_branch=args.expected_branch,
            expected_head=args.expected_head, expected_old_base=args.expected_old_base,
            expected_main=args.expected_main,
            allow_extended_history=args.allow_extended_history,
            expected_commit_count=args.expected_commit_count,
            dependency_pr=args.dependency_pr, dependency_head=args.dependency_head,
            dependency_merge=args.dependency_merge,
            covered_prefix=args.covered_prefix,
            covered_merge=args.covered_merge,
            regenerate_evidence=args.regenerate_evidence,
        )
        result = sync(plan)
    except SyncError as exc:
        print(f"[workspace.branch.sync-main] DENY {exc}", file=sys.stderr)
        return 2
    invalidated = ",".join(result.generated_evidence_conflicts) or "none"
    semantic = ",".join(result.semantic_conflicts) or "none"
    next_validation = ("exact-new-head-Quick-and-affected-acceptance" if plan.extended_history
                       else "current-head-risk-selected-validation")
    print(
        f"[workspace.branch.sync-main] PASS branch={plan.branch} old_head={plan.head} "
        f"new_head={result.head} recovery_bundle={plan.recovery_bundle} "
        f"common_base={plan.old_base} replay_base={plan.replay_base} "
        f"generated_evidence_invalidated={invalidated} "
        f"semantic_conflicts_preserved={semantic} "
        f"generated_commit={result.generated_commit or 'none'} "
        f"generated_evidence_replay_paths={','.join(result.generated_evidence_replay_paths) or 'none'} "
        f"candidate_evidence=false next={next_validation}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
