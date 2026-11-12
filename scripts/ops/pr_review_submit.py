#!/usr/bin/env python3
"""Submit one exact-head pull-request review with a dedicated identity."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_BRANCH = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ALLOWED_ACTIONS = ("APPROVE", "COMMENT", "REQUEST_CHANGES")
EXPECTED_STATE = {
    "APPROVE": "APPROVED",
    "COMMENT": "COMMENTED",
    "REQUEST_CHANGES": "CHANGES_REQUESTED",
}
REQUIRED_CHECKS = (
    "public_guard",
    "merge_policy_gate",
    "professional_quality_gate",
    "frontend_release_gate",
)
FAILED_CONCLUSIONS = {
    "action_required",
    "cancelled",
    "failure",
    "startup_failure",
    "timed_out",
}
CONFIRMATION = "SUBMIT_EXACT_HEAD_INDEPENDENT_REVIEW"
MAX_REVIEW_BODY = 60_000


class ReviewError(RuntimeError):
    pass


def _run(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        raise ReviewError(f"git {' '.join(args)} failed: {result.stdout.strip()}")
    return result.stdout.strip()


def repository_from_origin(root: Path) -> str:
    remote = _run(root, "remote", "get-url", "origin")
    patterns = (
        r"^https://github\.com/([^/]+/[^/]+?)(?:\.git)?$",
        r"^ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?$",
        r"^git@github\.com:([^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, remote)
        if match:
            repository = match.group(1)
            if REPOSITORY.fullmatch(repository):
                return repository
    raise ReviewError("origin is not a supported github.com repository URL")


def verify_local_repository(
    root: Path,
    expected_head: str,
    expected_main: str,
) -> tuple[str, str]:
    if not FULL_SHA.fullmatch(expected_head) or not FULL_SHA.fullmatch(expected_main):
        raise ReviewError("expected head and main must be full lowercase commit SHAs")
    branch = _run(root, "branch", "--show-current")
    if not ALLOWED_BRANCH.fullmatch(branch):
        raise ReviewError(f"branch is not review-eligible: {branch or '<detached>'}")
    if _run(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReviewError("worktree must be clean")
    head = _run(root, "rev-parse", "HEAD")
    if head != expected_head:
        raise ReviewError(f"local HEAD {head} does not match expected head {expected_head}")
    remote = _run(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    remote_head = remote.split()[0] if remote else ""
    if remote_head != expected_head:
        raise ReviewError(f"remote branch HEAD {remote_head or '<missing>'} does not match expected head")
    main = _run(root, "ls-remote", "--heads", "origin", "refs/heads/main")
    main_head = main.split()[0] if main else ""
    if main_head != expected_main:
        raise ReviewError(f"remote main HEAD {main_head or '<missing>'} does not match expected main")
    return branch, repository_from_origin(root)


def _private_path(path: Path, *, directory: bool) -> None:
    if path.is_symlink():
        raise ReviewError(f"review credential path must not be a symlink: {path}")
    try:
        metadata = path.stat()
    except OSError as exc:
        raise ReviewError(f"review credential path is unreadable: {path}") from exc
    expected_type = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected_type(metadata.st_mode):
        raise ReviewError(f"review credential path has the wrong type: {path}")
    if metadata.st_uid != os.geteuid():
        raise ReviewError(f"review credential path is not owned by the current user: {path}")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ReviewError(f"review credential path must not grant group or other access: {path}")


def load_reviewer_token(config_dir: Path, expected_login: str) -> str:
    config_dir = config_dir.expanduser()
    if not config_dir.is_absolute():
        raise ReviewError("review credential directory must be absolute")
    _private_path(config_dir, directory=True)
    hosts = config_dir / "hosts.yml"
    _private_path(hosts, directory=False)
    try:
        document = yaml.safe_load(hosts.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ReviewError("review credential file is unreadable") from exc
    entry = document.get("github.com") if isinstance(document, dict) else None
    if not isinstance(entry, dict):
        raise ReviewError("review credential file has no github.com entry")
    users = entry.get("users") if isinstance(entry.get("users"), dict) else {}
    selected_name = ""
    selected = {}
    for login, row in users.items():
        if str(login).casefold() == expected_login.casefold() and isinstance(row, dict):
            selected_name = str(login)
            selected = row
            break
    if not selected:
        active_name = str(entry.get("user") or "").strip()
        if active_name.casefold() == expected_login.casefold():
            selected_name = active_name
            selected = entry
    if not selected:
        raise ReviewError(f"expected reviewer {expected_login!r} is not present in the dedicated credential")
    if selected_name.casefold() != expected_login.casefold():
        raise ReviewError("dedicated credential resolves to another reviewer identity")
    token = str(selected.get("oauth_token") or "").strip()
    if not token:
        raise ReviewError(f"reviewer {expected_login!r} has no stored OAuth token")
    return token


class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com"):
        self.token = token
        self.api_url = api_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict | None = None):
        if not path.startswith("/"):
            raise ReviewError("GitHub API path must begin with /")
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.api_url + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "sce-governed-pr-review",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            try:
                message = json.loads(raw_error).get("message", "")
            except (json.JSONDecodeError, AttributeError):
                message = raw_error[:300]
            raise ReviewError(f"GitHub API {exc.code}: {message or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise ReviewError(f"GitHub API connection failed: {exc.reason}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReviewError("GitHub API returned invalid JSON") from exc


def _check_ci(client: GitHubClient, repository: str, head: str) -> None:
    payload = client.request("GET", f"/repos/{repository}/commits/{head}/check-runs?per_page=100")
    rows = payload.get("check_runs") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ReviewError("GitHub check-runs response is invalid")
    latest = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if name:
            previous = latest.get(name)
            if previous is None or str(row.get("started_at") or "") >= str(previous.get("started_at") or ""):
                latest[name] = row
    failed = sorted(
        name for name, row in latest.items()
        if str(row.get("conclusion") or "").lower() in FAILED_CONCLUSIONS
    )
    pending = sorted(name for name, row in latest.items() if row.get("status") != "completed")
    missing = sorted(name for name in REQUIRED_CHECKS if str((latest.get(name) or {}).get("conclusion") or "") != "success")
    if failed:
        raise ReviewError(f"failed checks: {', '.join(failed)}")
    if pending:
        raise ReviewError(f"checks still pending: {', '.join(pending)}")
    if missing:
        raise ReviewError(f"required checks are not successful: {', '.join(missing)}")


def submit_review(
    client: GitHubClient,
    *,
    repository: str,
    pr_number: int,
    expected_head: str,
    expected_main: str,
    expected_login: str,
    action: str,
    body: str,
    require_ci: bool,
    apply: bool,
    confirmation: str,
) -> dict:
    if not REPOSITORY.fullmatch(repository):
        raise ReviewError("repository must be owner/name")
    if pr_number <= 0:
        raise ReviewError("PR must be a positive number")
    if action not in ALLOWED_ACTIONS:
        raise ReviewError(f"unsupported review action: {action}")
    if not body.strip() or len(body) > MAX_REVIEW_BODY:
        raise ReviewError(f"review body must contain 1..{MAX_REVIEW_BODY} characters")

    viewer = client.request("GET", "/user")
    reviewer = str((viewer or {}).get("login") or "").strip()
    if reviewer.casefold() != expected_login.casefold():
        raise ReviewError(f"credential resolves to {reviewer or '<unknown>'}, expected {expected_login}")

    pull = client.request("GET", f"/repos/{repository}/pulls/{pr_number}")
    author = str(((pull or {}).get("user") or {}).get("login") or "").strip()
    head = str(((pull or {}).get("head") or {}).get("sha") or "").strip()
    base = pull.get("base") if isinstance((pull or {}).get("base"), dict) else {}
    base_sha = str(base.get("sha") or "").strip()
    base_ref = str(base.get("ref") or "").strip()
    if action == "APPROVE" and reviewer.casefold() == author.casefold():
        raise ReviewError("reviewer must differ from the PR author")
    if pull.get("state") != "open" or bool(pull.get("draft")):
        raise ReviewError("pull request must be open and not draft")
    if head != expected_head:
        raise ReviewError(f"PR head {head} does not match expected head {expected_head}")
    if base_ref != "main" or base_sha != expected_main:
        raise ReviewError(f"PR base {base_ref}@{base_sha} does not match main@{expected_main}")
    if require_ci:
        _check_ci(client, repository, expected_head)

    reviews = client.request("GET", f"/repos/{repository}/pulls/{pr_number}/reviews?per_page=100")
    existing = [
        row for row in reviews if isinstance(row, dict)
        and str((row.get("user") or {}).get("login") or "").casefold() == reviewer.casefold()
        and row.get("state") == EXPECTED_STATE[action]
        and str(row.get("commit_id") or "") == expected_head
    ] if isinstance(reviews, list) else []
    if existing:
        return {
            "status": "PASS",
            "idempotent": True,
            "review_id": int(existing[-1].get("id") or 0),
            "reviewer": reviewer,
            "author": author,
            "head": expected_head,
            "state": EXPECTED_STATE[action],
        }
    if not apply:
        return {
            "status": "DRY_RUN",
            "idempotent": False,
            "reviewer": reviewer,
            "author": author,
            "head": expected_head,
            "state": EXPECTED_STATE[action],
        }
    if confirmation != CONFIRMATION:
        raise ReviewError(f"apply requires confirmation {CONFIRMATION}")
    result = client.request(
        "POST",
        f"/repos/{repository}/pulls/{pr_number}/reviews",
        {"commit_id": expected_head, "body": body, "event": action},
    )
    if not isinstance(result, dict):
        raise ReviewError("GitHub review response is invalid")
    if (
        str((result.get("user") or {}).get("login") or "").casefold() != reviewer.casefold()
        or result.get("state") != EXPECTED_STATE[action]
        or str(result.get("commit_id") or "") != expected_head
    ):
        raise ReviewError("submitted review does not match reviewer, state and exact head")
    return {
        "status": "PASS",
        "idempotent": False,
        "review_id": int(result.get("id") or 0),
        "reviewer": reviewer,
        "author": author,
        "head": expected_head,
        "state": result.get("state"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-main", required=True)
    parser.add_argument("--expected-login", required=True)
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--action", required=True, choices=ALLOWED_ACTIONS)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--api-url", default="https://api.github.com")
    parser.add_argument("--skip-ci-check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args(argv)

    try:
        root = Path(args.root).resolve()
        branch, repository = verify_local_repository(root, args.expected_head, args.expected_main)
        body_path = Path(args.body_file)
        if not body_path.is_absolute():
            body_path = root / body_path
        body = body_path.read_text(encoding="utf-8")
        token = load_reviewer_token(Path(args.config_dir), args.expected_login)
        result = submit_review(
            GitHubClient(token, args.api_url),
            repository=repository,
            pr_number=args.pr,
            expected_head=args.expected_head,
            expected_main=args.expected_main,
            expected_login=args.expected_login,
            action=args.action,
            body=body,
            require_ci=not args.skip_ci_check,
            apply=args.apply,
            confirmation=args.confirm,
        )
    except (OSError, ReviewError) as exc:
        print(f"[pr.review] DENY {exc}", file=sys.stderr)
        return 2
    print(
        f"[pr.review] {result['status']} "
        f"branch={branch} reviewer={result['reviewer']} author={result['author']} "
        f"head={args.expected_head} state={result['state']} "
        f"review_id={result['review_id'] or 'pending'} idempotent={str(result['idempotent']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
