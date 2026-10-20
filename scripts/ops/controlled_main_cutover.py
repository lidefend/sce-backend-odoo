#!/usr/bin/env python3
"""Fail-closed, paired GitHub/Gitee main cutover with exact leases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GITHUB_REPOSITORY = "lidefend/sce-backend-odoo"
GITEE_REPOSITORY = "leegege/sce-product-odoo"
GITEE_API = "https://gitee.com/api/v5"
GITHUB_REMOTE = "origin"
GITEE_REMOTE = "gitee-mirror"
GITHUB_URLS = {
    "https://github.com/lidefend/sce-backend-odoo.git",
    "https://github.com/lidefend/sce-backend-odoo",
}
GITEE_URL = "git@gitee.com:leegege/sce-product-odoo.git"
RULESET_NAME = "main-github-authoritative-pr"
REQUIRED_CHECKS = (
    "merge_policy_gate",
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+")


class CutoverError(RuntimeError):
    pass


def run(
    *args: str,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        text=True,
        input=input_text,
        capture_output=True,
    )
    if check and completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise CutoverError(f"command failed: {args[0]} ({detail[:400]})")
    return completed


def git(*args: str) -> str:
    return run("git", *args).stdout.strip()


def gh_json(*args: str) -> Any:
    return json.loads(run("gh", "api", *args).stdout)


def gh_write(method: str, path: str, payload: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".json", delete=False
    ) as handle:
        json.dump(payload, handle, sort_keys=True)
        payload_path = Path(handle.name)
    try:
        run("gh", "api", "--method", method, path, "--input", str(payload_path))
    finally:
        payload_path.unlink(missing_ok=True)


def read_token(path: Path) -> str:
    if not path.is_file():
        raise CutoverError("Gitee token file is missing")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode not in {0o400, 0o600}:
        raise CutoverError(f"Gitee token file mode must be 400 or 600, got {mode:o}")
    token = path.read_text(encoding="utf-8").strip()
    if "\n" in token or len(token) < 20:
        raise CutoverError("Gitee token file must contain exactly one token")
    return token


def gitee_api(
    token: str,
    method: str,
    path: str,
    fields: dict[str, Any] | None = None,
) -> Any:
    encoded = {
        key: str(value).lower() if isinstance(value, bool) else str(value)
        for key, value in (fields or {}).items()
    }
    url = f"{GITEE_API}{path}"
    body = None
    if method == "GET" and encoded:
        url += "?" + urllib.parse.urlencode(encoded)
    elif encoded:
        body = urllib.parse.urlencode(encoded).encode()
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("Authorization", f"token {token}")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        message = ""
        raw = exc.read()
        if raw:
            try:
                message = str(json.loads(raw).get("message", ""))
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
        raise CutoverError(
            f"Gitee API {method} {path} failed status={exc.code} message={message[:160]}"
        ) from exc
    return json.loads(raw) if raw else None


def remote_sha(remote: str, ref: str) -> str:
    rows = git("ls-remote", remote, ref).splitlines()
    if len(rows) != 1:
        raise CutoverError(f"remote ref is not unique: remote={remote} ref={ref}")
    sha, actual_ref = rows[0].split()
    if actual_ref != ref or not SHA_RE.fullmatch(sha):
        raise CutoverError(f"invalid remote ref response: remote={remote} ref={ref}")
    return sha


def ruleset_payload(ruleset: dict[str, Any], enforcement: str) -> dict[str, Any]:
    return {
        "name": ruleset["name"],
        "target": ruleset["target"],
        "enforcement": enforcement,
        "bypass_actors": ruleset.get("bypass_actors", []),
        "conditions": ruleset["conditions"],
        "rules": ruleset["rules"],
    }


def verify_required_checks(target_sha: str) -> dict[str, dict[str, Any]]:
    response = gh_json(
        f"repos/{GITHUB_REPOSITORY}/commits/{target_sha}/check-runs?per_page=100"
    )
    runs = response.get("check_runs", [])
    results: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_CHECKS:
        matches = [
            item
            for item in runs
            if item.get("name") == name
            and item.get("status") == "completed"
            and item.get("conclusion") == "success"
        ]
        if len(matches) != 1:
            raise CutoverError(
                f"required check is not uniquely successful: {name} matches={len(matches)}"
            )
        if matches[0].get("head_sha") != target_sha:
            raise CutoverError(f"required check SHA mismatch: {name}")
        check_id = matches[0].get("id")
        if not isinstance(check_id, int):
            raise CutoverError(f"required check ID is invalid: {name}")
        results[name] = {
            "result": "PASS",
            "check_run_id": check_id,
            "details_url": str(matches[0].get("details_url") or ""),
        }
    return results


def verify_bound_required_checks(
    target_sha: str, bound_checks: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Revalidate the exact preflight evidence, ignoring later same-name runs."""
    if set(bound_checks) != set(REQUIRED_CHECKS):
        raise CutoverError("bound required check names do not match policy")
    verified: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_CHECKS:
        check_id = bound_checks[name].get("check_run_id")
        if not isinstance(check_id, int):
            raise CutoverError(f"bound required check ID is invalid: {name}")
        item = gh_json(f"repos/{GITHUB_REPOSITORY}/check-runs/{check_id}")
        if item.get("id") != check_id or item.get("name") != name:
            raise CutoverError(f"bound required check identity mismatch: {name}")
        if item.get("head_sha") != target_sha:
            raise CutoverError(f"bound required check SHA mismatch: {name}")
        if item.get("status") != "completed" or item.get("conclusion") != "success":
            raise CutoverError(f"bound required check is no longer successful: {name}")
        verified[name] = {
            "result": "PASS",
            "check_run_id": check_id,
            "details_url": str(item.get("details_url") or ""),
        }
    return verified


@dataclass(frozen=True)
class Preflight:
    branch: str
    target_sha: str
    target_tree: str
    github_old_sha: str
    gitee_old_sha: str
    github_ruleset_id: int
    github_ruleset: dict[str, Any]
    gitee_protected: bool
    required_checks: dict[str, dict[str, Any]]


def preflight(args: argparse.Namespace, token: str) -> Preflight:
    branch = git("branch", "--show-current")
    if not BRANCH_RE.fullmatch(branch):
        raise CutoverError(f"current branch is not write-allowed: {branch}")
    if git("status", "--porcelain"):
        raise CutoverError("worktree is not clean")
    if git("remote", "get-url", GITHUB_REMOTE) not in GITHUB_URLS:
        raise CutoverError("GitHub authoritative remote mismatch")
    if git("remote", "get-url", GITEE_REMOTE) != GITEE_URL:
        raise CutoverError("Gitee mirror remote mismatch")
    if git("cat-file", "-t", args.target_sha) != "commit":
        raise CutoverError("target SHA is not a local commit")
    actual_tree = git("rev-parse", f"{args.target_sha}^{{tree}}")
    if actual_tree != args.target_tree:
        raise CutoverError("target tree mismatch")
    if git("rev-parse", "HEAD") != args.target_sha:
        raise CutoverError("HEAD must equal target SHA")

    github_live = remote_sha(GITHUB_REMOTE, "refs/heads/main")
    gitee_live = remote_sha(GITEE_REMOTE, "refs/heads/main")
    if github_live != args.github_old_sha:
        raise CutoverError("GitHub live main drifted from exact lease")
    if gitee_live != args.gitee_old_sha:
        raise CutoverError("Gitee live main drifted from exact lease")
    if remote_sha(GITHUB_REMOTE, f"refs/heads/{branch}") != args.target_sha:
        raise CutoverError("GitHub candidate branch does not equal target SHA")

    target_tree_remote = gh_json(
        f"repos/{GITHUB_REPOSITORY}/git/commits/{args.target_sha}"
    ).get("tree", {}).get("sha")
    if target_tree_remote != args.target_tree:
        raise CutoverError("GitHub target tree mismatch")
    checks = verify_required_checks(args.target_sha)

    rulesets = gh_json(f"repos/{GITHUB_REPOSITORY}/rulesets")
    matches = [item for item in rulesets if item.get("name") == RULESET_NAME]
    if len(matches) != 1:
        raise CutoverError("GitHub authority ruleset is not unique")
    ruleset_id = int(matches[0]["id"])
    ruleset = gh_json(f"repos/{GITHUB_REPOSITORY}/rulesets/{ruleset_id}")
    if ruleset.get("enforcement") != "active":
        raise CutoverError("GitHub authority ruleset is not active")
    if ruleset.get("bypass_actors"):
        raise CutoverError("GitHub authority ruleset unexpectedly has bypass actors")

    gitee_user = gitee_api(token, "GET", "/user")
    if str(gitee_user.get("login", "")).lower() != "leegege":
        raise CutoverError("Gitee token owner mismatch")
    gitee_repo = gitee_api(token, "GET", f"/repos/{GITEE_REPOSITORY}")
    if str(gitee_repo.get("full_name", "")).lower() != GITEE_REPOSITORY:
        raise CutoverError("Gitee token repository mismatch")
    gitee_branch = gitee_api(
        token, "GET", f"/repos/{GITEE_REPOSITORY}/branches/main"
    )
    if str(gitee_branch.get("commit", {}).get("sha", "")) != args.gitee_old_sha:
        raise CutoverError("Gitee API main SHA differs from exact lease")

    run("python3", "scripts/verify/repository_clean_history_guard.py")
    return Preflight(
        branch=branch,
        target_sha=args.target_sha,
        target_tree=args.target_tree,
        github_old_sha=args.github_old_sha,
        gitee_old_sha=args.gitee_old_sha,
        github_ruleset_id=ruleset_id,
        github_ruleset=ruleset,
        gitee_protected=bool(gitee_branch.get("protected")),
        required_checks=checks,
    )


def create_recovery_bundle(
    pre: Preflight, recovery_root: Path, run_id: str
) -> dict[str, str]:
    root = recovery_root.resolve()
    try:
        root.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise CutoverError("recovery root must be outside the product repository")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    bundle = root / f"controlled-main-cutover-{run_id}.bundle"
    if bundle.exists():
        raise CutoverError("recovery bundle already exists")

    git("fetch", "--no-tags", GITHUB_REMOTE, pre.github_old_sha)
    git("fetch", "--no-tags", GITEE_REMOTE, pre.gitee_old_sha)
    prefix = f"refs/cutover-recovery/{run_id}"
    refs = {
        f"{prefix}/github-main": pre.github_old_sha,
        f"{prefix}/gitee-main": pre.gitee_old_sha,
        f"{prefix}/target": pre.target_sha,
    }
    try:
        for ref, sha in refs.items():
            git("update-ref", ref, sha)
        run("git", "bundle", "create", str(bundle), *refs.keys())
    finally:
        for ref in refs:
            run("git", "update-ref", "-d", ref, check=False)
    run("git", "bundle", "verify", str(bundle))
    os.chmod(bundle, 0o400)
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    return {
        "bundle": str(bundle),
        "sha256": digest,
        "github_old_sha": pre.github_old_sha,
        "gitee_old_sha": pre.gitee_old_sha,
        "target_sha": pre.target_sha,
    }


def push_main(remote: str, target_sha: str, lease_sha: str) -> None:
    run(
        "git",
        "push",
        f"--force-with-lease=refs/heads/main:{lease_sha}",
        remote,
        f"{target_sha}:refs/heads/main",
    )
    if remote_sha(remote, "refs/heads/main") != target_sha:
        raise CutoverError(f"post-push main mismatch: remote={remote}")


def set_github_ruleset(pre: Preflight, enforcement: str) -> None:
    gh_write(
        "PUT",
        f"repos/{GITHUB_REPOSITORY}/rulesets/{pre.github_ruleset_id}",
        ruleset_payload(pre.github_ruleset, enforcement),
    )


def set_gitee_protection(token: str, protected: bool) -> None:
    branch = gitee_api(token, "GET", f"/repos/{GITEE_REPOSITORY}/branches/main")
    current = bool(branch.get("protected"))
    if current == protected:
        return
    gitee_api(
        token,
        "PUT" if protected else "DELETE",
        f"/repos/{GITEE_REPOSITORY}/branches/main/protection",
    )


def rollback_changed_mains(pre: Preflight) -> None:
    states = (
        (GITEE_REMOTE, pre.gitee_old_sha),
        (GITHUB_REMOTE, pre.github_old_sha),
    )
    for remote, old_sha in states:
        live = remote_sha(remote, "refs/heads/main")
        if live == old_sha:
            continue
        if live != pre.target_sha:
            raise CutoverError(
                f"cannot rollback unexpected live main: remote={remote} sha={live}"
            )
        push_main(remote, old_sha, pre.target_sha)


def restore_protections(token: str, pre: Preflight) -> None:
    errors: list[str] = []
    if pre.gitee_protected:
        try:
            set_gitee_protection(token, True)
        except BaseException as exc:
            errors.append(f"gitee:{type(exc).__name__}")
    try:
        set_github_ruleset(pre, "active")
    except BaseException as exc:
        errors.append(f"github:{type(exc).__name__}")
    if errors:
        raise CutoverError("protection restoration failed: " + ",".join(errors))


def rollback_to_old(token: str, pre: Preflight) -> None:
    github_live = remote_sha(GITHUB_REMOTE, "refs/heads/main")
    gitee_live = remote_sha(GITEE_REMOTE, "refs/heads/main")
    if github_live not in {pre.github_old_sha, pre.target_sha}:
        raise CutoverError(f"unexpected GitHub main during rollback: {github_live}")
    if gitee_live not in {pre.gitee_old_sha, pre.target_sha}:
        raise CutoverError(f"unexpected Gitee main during rollback: {gitee_live}")
    if gitee_live == pre.target_sha and pre.gitee_protected:
        set_gitee_protection(token, False)
    if github_live == pre.target_sha:
        set_github_ruleset(pre, "disabled")
    rollback_changed_mains(pre)
    restore_protections(token, pre)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(
    args: argparse.Namespace,
    token: str,
    pre: Preflight,
    evidence_dir: Path,
) -> dict[str, Any]:
    recovery = create_recovery_bundle(pre, args.recovery_root, args.run_id)
    write_json(evidence_dir / "recovery-bundle.json", recovery)
    try:
        if pre.gitee_protected:
            set_gitee_protection(token, False)
        set_github_ruleset(pre, "disabled")
        push_main(GITHUB_REMOTE, pre.target_sha, pre.github_old_sha)
        push_main(GITEE_REMOTE, pre.target_sha, pre.gitee_old_sha)
    except BaseException as exc:
        rollback_to_old(token, pre)
        raise CutoverError(
            f"paired cutover rolled back: {type(exc).__name__}"
        ) from exc

    try:
        restore_protections(token, pre)
    except BaseException as exc:
        rollback_to_old(token, pre)
        raise CutoverError(
            f"protection restoration failed; paired cutover rolled back: "
            f"{type(exc).__name__}"
        ) from exc

    github_main = remote_sha(GITHUB_REMOTE, "refs/heads/main")
    gitee_main = remote_sha(GITEE_REMOTE, "refs/heads/main")
    if github_main != pre.target_sha or gitee_main != pre.target_sha:
        raise CutoverError("paired post-cutover SHA mismatch")
    checks = verify_bound_required_checks(pre.target_sha, pre.required_checks)
    ruleset = gh_json(
        f"repos/{GITHUB_REPOSITORY}/rulesets/{pre.github_ruleset_id}"
    )
    if ruleset.get("enforcement") != "active":
        raise CutoverError("GitHub authority ruleset was not restored")
    gitee_branch = gitee_api(
        token, "GET", f"/repos/{GITEE_REPOSITORY}/branches/main"
    )
    if pre.gitee_protected and not gitee_branch.get("protected"):
        raise CutoverError("Gitee main protection was not restored")
    return {
        "result": "PASS",
        "github_main": github_main,
        "gitee_main": gitee_main,
        "tree": pre.target_tree,
        "required_checks": checks,
        "github_ruleset_restored": True,
        "gitee_protection_restored": bool(gitee_branch.get("protected"))
        if pre.gitee_protected
        else "NOT_PREVIOUSLY_PROTECTED",
        "recovery_bundle_sha256": recovery["sha256"],
        "production_deployed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--target-tree", required=True)
    parser.add_argument("--github-old-sha", required=True)
    parser.add_argument("--gitee-old-sha", required=True)
    parser.add_argument("--gitee-token-file", type=Path, required=True)
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    for name in ("target_sha", "target_tree", "github_old_sha", "gitee_old_sha"):
        if not SHA_RE.fullmatch(getattr(args, name)):
            parser.error(f"--{name.replace('_', '-')} must be a full lowercase SHA")
    if args.run_id is None:
        args.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", args.run_id):
        parser.error("--run-id must use YYYYMMDDTHHMMSSZ")
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{7,79}", args.authorization_id):
        parser.error("--authorization-id must be an auditable task identifier")
    if args.apply and args.confirm != "CONTROLLED_MAIN_CUTOVER_APPLY":
        parser.error("--apply requires --confirm CONTROLLED_MAIN_CUTOVER_APPLY")
    return args


def main() -> int:
    args = parse_args()
    evidence_dir = args.evidence_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    try:
        token = read_token(args.gitee_token_file.resolve())
        pre = preflight(args, token)
        write_json(
            evidence_dir / "preflight.json",
            {
                "result": "PASS",
                "mode": "apply" if args.apply else "dry-run",
                "authorization_id": args.authorization_id,
                "branch": pre.branch,
                "target_sha": pre.target_sha,
                "target_tree": pre.target_tree,
                "github_old_sha": pre.github_old_sha,
                "gitee_old_sha": pre.gitee_old_sha,
                "github_ruleset_id": pre.github_ruleset_id,
                "github_ruleset_active": True,
                "gitee_main_protected": pre.gitee_protected,
                "required_checks": pre.required_checks,
                "writes": 0,
            },
        )
        if not args.apply:
            print(
                "[controlled_main_cutover] PASS mode=dry-run "
                f"target={pre.target_sha} writes=0"
            )
            return 0
        result = execute(args, token, pre, evidence_dir)
        write_json(evidence_dir / "result.json", result)
        print(
            "[controlled_main_cutover] PASS mode=apply "
            f"target={pre.target_sha} dual_remote_main_consistency=PASS"
        )
        return 0
    except (CutoverError, OSError, json.JSONDecodeError) as exc:
        write_json(
            evidence_dir / "failure.json",
            {
                "result": "BLOCKED",
                "classification": type(exc).__name__,
                "message": str(exc)[:500],
                "remote_write_attempted": False
                if not args.apply
                else "SEE_REMOTE_AUDIT",
                "production_deployed": False,
            },
        )
        print(
            f"[controlled_main_cutover] BLOCKED {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
