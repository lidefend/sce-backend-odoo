#!/usr/bin/env python3
"""Fail closed on forbidden reachable Git history and release-local objects.

Diagnostics intentionally contain only rule IDs, paths, object prefixes and
classifications. Blob contents and matching values are never emitted.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/security/repository_clean_history_policy.v1.json"

CUSTOMER_MODULE_PATH = re.compile(
    r"(?:^|/)(?:smart_construction_custom|sce_customer_(?!sample(?:/|$)|template(?:/|$))[a-z0-9_]+)(?:/|$)",
    re.IGNORECASE,
)
CUSTOMER_SOURCE_TOKEN = re.compile(
    r"\b(?:C_[A-Z0-9_]{3,}|CWGL_[A-Z0-9_]+|ZJGL_[A-Z0-9_]+|BGGL_[A-Z0-9_]+|"
    r"T_KK_[A-Z0-9_]+|UP_USP_[A-Z0-9_]+|LEGACY_DIRECT_DIRECT_[A-Z0-9_]+)\b"
)
CUSTOMER_SQL_ID = re.compile(
    r"\blegacy_\d{8,}\b|\bsc_legacy_(?:legacy_source_[a-z0-9_]+|file_index)\b",
    re.IGNORECASE,
)
CUSTOMER_MODEL = re.compile(r"_name\s*=\s*['\"]sc\.legacy\.[^'\"]+['\"]")
DATABASE_URL_CREDENTIALS = re.compile(
    rb"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s/@:]+:[^\s/@]+@",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"(?<![A-Za-z0-9_])ghp_[A-Za-z0-9_]{30,}"),
    re.compile(rb"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{32,}"),
    re.compile(rb"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
)
PERSONAL_DATA_RULES = (
    (
        "PD001",
        "GOVERNMENT_ID_PATTERN",
        re.compile(rb"(?<![0-9A-Za-z])[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?![0-9A-Za-z])"),
    ),
    (
        "PD002",
        "MOBILE_PHONE_PATTERN",
        re.compile(rb"(?<![0-9A-Za-z])1[3-9]\d{9}(?![0-9A-Za-z])"),
    ),
    (
        "PD003",
        "BANK_ACCOUNT_PATTERN",
        re.compile(
            rb"(?i)(?:account(?:_no|_number)?|bank(?:_account)?|card(?:_no|_number)?|"
            rb"receiving_account_no|payer_account|payee_account|\xe9\x93\xb6\xe8\xa1\x8c(?:\xe5\x8d\xa1|\xe8\xb4\xa6\xe5\x8f\xb7)|\xe8\xb4\xa6\xe5\x8f\xb7)"
            rb"[^\d\n]{0,80}\d{12,24}(?!\d)"
        ),
    ),
)


@dataclass(frozen=True, order=True)
class Finding:
    rule_id: str
    path: str
    classification: str


@dataclass(frozen=True)
class ObjectRow:
    object_id: str
    object_type: str
    size: int
    path: str


def run_git(
    root: Path,
    *args: str,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(root: Path, *args: str, check: bool = True, input_text: str | None = None) -> str:
    return run_git(root, *args, check=check, input_text=input_text).stdout


def load_policy(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "sce.repository_clean_history_policy.v1":
        raise ValueError("unsupported clean-history policy")
    return payload


def load_personal_data_false_positives(
    root: Path,
    rules: dict[str, object],
) -> set[tuple[str, str, str, str]]:
    relative = str(rules.get("personal_data_false_positive_registry") or "")
    if not relative:
        return set()
    registry_path = Path(relative)
    if registry_path.is_absolute() or ".." in registry_path.parts:
        raise ValueError("personal-data false-positive registry path must be repository-relative")
    payload = json.loads((root / registry_path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("entries"), list):
        raise ValueError("personal-data false-positive registry schema is invalid")
    known_rules = {
        (rule_id, classification)
        for rule_id, classification, _pattern in PERSONAL_DATA_RULES
    }
    allowed: set[tuple[str, str, str, str]] = set()
    for entry in payload["entries"]:
        rule_id = str(entry.get("rule_id") or "")
        path = str(entry.get("path") or "")
        blob_id = str(entry.get("blob_id") or "")
        classification = str(entry.get("classification") or "")
        reason = str(entry.get("reason") or "")
        if not re.fullmatch(r"[0-9a-f]{40}", blob_id):
            raise ValueError("personal-data false-positive blob_id must be a full SHA-1")
        if not path or path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("personal-data false-positive path must be repository-relative")
        if (rule_id, classification) not in known_rules or not reason:
            raise ValueError("personal-data false-positive entry is incomplete")
        allowed.add((rule_id, path, blob_id, classification))
    return allowed


def load_oversized_blob_exceptions(
    root: Path,
    rules: dict[str, object],
) -> set[tuple[str, str, str, str]]:
    relative = str(rules.get("oversized_blob_exception_registry") or "")
    if not relative:
        return set()
    registry_path = Path(relative)
    if registry_path.is_absolute() or ".." in registry_path.parts:
        raise ValueError("oversized-blob exception registry path must be repository-relative")
    payload = json.loads((root / registry_path).read_text(encoding="utf-8"))
    if (
        payload.get("schema_version") != "sce.repository_oversized_blob_exceptions.v1"
        or not isinstance(payload.get("entries"), list)
    ):
        raise ValueError("oversized-blob exception registry schema is invalid")
    allowed: set[tuple[str, str, str, str]] = set()
    for entry in payload["entries"]:
        rule_id = str(entry.get("rule_id") or "")
        path = str(entry.get("path") or "")
        blob_id = str(entry.get("blob_id") or "")
        classification = str(entry.get("classification") or "")
        reason = str(entry.get("reason") or "")
        if not re.fullmatch(r"[0-9a-f]{40}", blob_id):
            raise ValueError("oversized-blob exception blob_id must be a full SHA-1")
        if not path or path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("oversized-blob exception path must be repository-relative")
        if rule_id != "RH007" or classification != "OVERSIZED_BLOB" or not reason:
            raise ValueError("oversized-blob exception entry is incomplete")
        allowed.add((rule_id, path, blob_id, classification))
    if len(allowed) != len(payload["entries"]):
        raise ValueError("oversized-blob exception entries must be unique")
    return allowed


def object_rows(root: Path, revision_args: tuple[str, ...]) -> list[ObjectRow]:
    rev_list = git(root, "rev-list", "--objects", *revision_args, check=False)
    if not rev_list.strip():
        return []
    metadata = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)"],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        input=rev_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    rows: list[ObjectRow] = []
    for line in metadata.splitlines():
        parts = line.split(" ", 3)
        if len(parts) == 4 and parts[2].isdigit():
            rows.append(ObjectRow(parts[0], parts[1], int(parts[2]), parts[3]))
    return rows


def public_revision_args() -> tuple[str, ...]:
    """Return refs that can participate in repository publication.

    ``--all`` also includes local-only refs such as ``refs/stash``.  A shared
    multi-worktree repository may legitimately have a stash whose root is
    unrelated to the current product history, so publication checks must not
    confuse that local recovery state with candidate history.  ``HEAD`` is
    explicit because governed CI checks out the exact candidate SHA in a
    detached repository without creating branch or remote-tracking refs.
    Local-only refs remain governed by ``--local-hygiene``.
    """

    return ("HEAD", "--branches", "--tags", "--remotes")


def trusted_incremental_revision_args(root: Path, trusted_base: str) -> tuple[str, ...]:
    if not re.fullmatch(r"[0-9a-f]{40}", trusted_base):
        raise ValueError("trusted base must be a full lowercase commit SHA")
    if run_git(root, "cat-file", "-e", f"{trusted_base}^{{commit}}", check=False).returncode != 0:
        raise ValueError("trusted base commit is unavailable")
    if run_git(root, "merge-base", "--is-ancestor", trusted_base, "HEAD", check=False).returncode != 0:
        raise ValueError("trusted base must be an ancestor of HEAD")
    return ("HEAD", f"^{trusted_base}")


def incremental_authority_paths(rules: dict[str, object]) -> set[str]:
    paths = {
        "scripts/verify/repository_clean_history_guard.py",
        ".github/workflows/public_guard.yml",
    }
    for key in (
        "_policy_relative",
        "personal_data_false_positive_registry",
        "oversized_blob_exception_registry",
    ):
        value = str(rules.get(key) or "")
        if value:
            paths.add(value)
    return paths


def incremental_authority_changed(root: Path, trusted_base: str, rules: dict[str, object]) -> bool:
    changed = set(
        git(
            root,
            "diff",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            f"{trusted_base}...HEAD",
            "--",
            check=False,
        ).splitlines()
    )
    return bool(changed & incremental_authority_paths(rules))


def current_changed_tree_rows(root: Path, trusted_base: str) -> list[ObjectRow]:
    paths = git(
        root,
        "diff",
        "--name-only",
        "--diff-filter=ACMRTUXB",
        f"{trusted_base}...HEAD",
        "--",
        check=False,
    ).splitlines()
    rows: list[ObjectRow] = []
    for path in paths:
        line = git(root, "ls-tree", "-l", "HEAD", "--", path, check=False).strip()
        if not line:
            continue
        metadata, _separator, resolved_path = line.partition("\t")
        parts = metadata.split()
        if len(parts) == 4 and parts[1] == "blob" and parts[3].isdigit():
            rows.append(ObjectRow(parts[2], parts[1], int(parts[3]), resolved_path))
    return rows


def read_blob(root: Path, object_id: str) -> bytes:
    return subprocess.run(
        ["git", "cat-file", "blob", object_id],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout


def is_runtime_env_path(path: str) -> bool:
    name = Path(path).name
    return name.startswith(".env") and not name.endswith(".example")


def is_customer_runtime_scope(path: str) -> bool:
    return (
        path.startswith("addons/smart_construction_core/")
        and "/tests/" not in path
        and "/migrations/" not in path
    )


def path_findings(path: str, object_id: str, rules: dict[str, object]) -> set[Finding]:
    findings: set[Finding] = set()
    display = f"{path}@{object_id[:12]}"
    prefixes = tuple(str(item) for item in rules.get("forbidden_path_prefixes", []))
    suffixes = tuple(str(item).lower() for item in rules.get("forbidden_archive_suffixes", []))
    if path.startswith(prefixes):
        findings.add(Finding("RH005", display, "FORBIDDEN_HISTORY_PATH"))
    if CUSTOMER_MODULE_PATH.search(path):
        findings.add(Finding("RH014", display, "CUSTOMER_MODULE_PATH"))
    if is_runtime_env_path(path):
        findings.add(Finding("RH011", display, "TRACKED_RUNTIME_ENV_FILE"))
    if path.lower().endswith(suffixes):
        findings.add(Finding("RH006", display, "ARCHIVE_OR_DATABASE_BLOB"))
    return findings


def blob_findings(
    root: Path,
    row: ObjectRow,
    rules: dict[str, object],
    *,
    rule_prefix: str = "",
    scan_repository_identity: bool = False,
) -> set[Finding]:
    findings = path_findings(row.path, row.object_id, rules)
    display = f"{row.path}@{row.object_id[:12]}"
    maximum = int(rules.get("maximum_blob_bytes", 0))
    if maximum and row.size > maximum:
        exception = ("RH007", row.path, row.object_id, "OVERSIZED_BLOB")
        exceptions = rules.get("_oversized_blob_exceptions", set())
        if rule_prefix or exception not in exceptions:
            findings.add(Finding("RH007", display, f"{rule_prefix}OVERSIZED_BLOB"))
            return findings
        used_exceptions = rules.get("_used_oversized_blob_exceptions")
        if isinstance(used_exceptions, set):
            used_exceptions.add(exception)
    data = read_blob(root, row.object_id)
    if b"\0" in data:
        return findings
    text = data.decode("utf-8", errors="ignore")
    forbidden_tokens = tuple(str(item).encode("utf-8") for item in rules.get("forbidden_repository_tokens", []))
    repository_token_exempt_paths = {
        str(item) for item in rules.get("repository_token_exempt_paths", [])
    }
    policy_relative = str(rules.get("_policy_relative", ""))
    if (
        scan_repository_identity
        and row.path != policy_relative
        and row.path not in repository_token_exempt_paths
        and any(token in data for token in forbidden_tokens)
    ):
        findings.add(Finding("RH008", display, f"{rule_prefix}OLD_REPOSITORY_REFERENCE"))
    if is_customer_runtime_scope(row.path) and (CUSTOMER_SOURCE_TOKEN.search(text) or CUSTOMER_SQL_ID.search(text)):
        findings.add(Finding("RH015", display, f"{rule_prefix}CUSTOMER_CONFIG_SQL_SOURCE_ID"))
    if is_customer_runtime_scope(row.path) and CUSTOMER_MODEL.search(text):
        findings.add(Finding("RH016", display, f"{rule_prefix}CUSTOMER_LEGACY_MODEL"))
    if DATABASE_URL_CREDENTIALS.search(data) or any(pattern.search(data) for pattern in SECRET_PATTERNS):
        findings.add(Finding("RH017", display, f"{rule_prefix}SECRET_MATERIAL"))
    false_positives = rules.get("_personal_data_false_positives", set())
    for rule_id, classification, pattern in PERSONAL_DATA_RULES:
        if pattern.search(data) and (
            rule_id,
            row.path,
            row.object_id,
            classification,
        ) not in false_positives:
            findings.add(
                Finding("RH018", display, f"{rule_prefix}PERSONAL_DATA:{classification}")
            )
    return findings


def remote_errors(root: Path, allowed_remotes: dict[str, object]) -> set[Finding]:
    errors: set[Finding] = set()
    configured = set(git(root, "remote").splitlines())
    if not configured or not configured.issubset(allowed_remotes):
        errors.add(Finding("RH002", "<repository>", "REMOTE_SET"))
    for name in configured:
        expected = allowed_remotes.get(name)
        actual = git(root, "remote", "get-url", name, check=False).strip()
        approved = {expected} if isinstance(expected, str) else set(expected or [])
        if not actual or actual not in approved:
            errors.add(Finding("RH003", f"remote:{name}", "OLD_OR_UNEXPECTED_REMOTE"))
    return errors


def fsck_integrity_errors(root: Path) -> set[Finding]:
    result = run_git(root, "fsck", "--full", "--no-reflogs", check=False)
    if result.returncode == 0:
        return set()
    return {Finding("RH019", "<object-database>", "GIT_FSCK_INTEGRITY_FAILURE")}


def tree_rows(root: Path, object_id: str) -> list[ObjectRow]:
    output = git(root, "ls-tree", "-r", "-l", object_id, check=False)
    rows: list[ObjectRow] = []
    for line in output.splitlines():
        metadata, separator, path = line.partition("\t")
        parts = metadata.split()
        if separator and len(parts) == 4 and parts[1] == "blob" and parts[3].isdigit():
            rows.append(ObjectRow(parts[2], parts[1], int(parts[3]), path))
    return rows


def local_hygiene_errors(root: Path, rules: dict[str, object]) -> tuple[set[Finding], dict[str, int]]:
    errors: set[Finding] = set()
    reachable_commits = set(git(root, "rev-list", "--all", check=False).splitlines())
    reflog_commits = set(git(root, "reflog", "--all", "--format=%H", check=False).splitlines())
    reflog_only = sorted(item for item in reflog_commits - reachable_commits if item)
    for commit_id in reflog_only:
        errors.add(Finding("RH009", f"commit:{commit_id[:12]}", "REFLOG_ONLY_COMMIT"))
        for row in tree_rows(root, commit_id):
            errors.update(blob_findings(root, row, rules, rule_prefix="REFLOG_ONLY_"))

    fsck = run_git(root, "fsck", "--full", "--unreachable", "--no-reflogs", check=False)
    unreachable: list[tuple[str, str]] = []
    for line in (fsck.stdout + fsck.stderr).splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] in {"unreachable", "dangling"}:
            unreachable.append((parts[1], parts[-1]))
    scanned_blobs: set[str] = set()
    for object_type, object_id in unreachable:
        errors.add(Finding("RH010", f"{object_type}:{object_id[:12]}", "UNREACHABLE_OBJECT"))
        if object_type in {"commit", "tree"}:
            for row in tree_rows(root, object_id):
                scanned_blobs.add(row.object_id)
                errors.update(blob_findings(root, row, rules, rule_prefix="UNREACHABLE_"))
        elif object_type == "blob" and object_id not in scanned_blobs:
            size_text = git(root, "cat-file", "-s", object_id, check=False).strip()
            if size_text.isdigit():
                row = ObjectRow(object_id, "blob", int(size_text), "<unreachable-blob>")
                errors.update(blob_findings(root, row, rules, rule_prefix="UNREACHABLE_"))

    tags = git(root, "for-each-ref", "--format=%(refname)", "refs/tags", check=False).splitlines()
    for ref in tags:
        errors.add(Finding("RH012", ref, "TAG_REF_PRESENT"))

    stash_refs = git(root, "for-each-ref", "--format=%(refname) %(objectname)", "refs/stash", check=False).splitlines()
    for row in stash_refs:
        ref, _separator, object_id = row.partition(" ")
        errors.add(Finding("RH020", ref, "LOCAL_STASH_REF_PRESENT"))
        if object_id:
            for blob in tree_rows(root, object_id):
                errors.update(blob_findings(root, blob, rules, rule_prefix="STASH_"))

    current = git(root, "branch", "--show-current", check=False).strip()
    allowed_remote_suffixes = {"main", "HEAD", current}
    remote_refs = git(root, "for-each-ref", "--format=%(refname)", "refs/remotes", check=False).splitlines()
    stale_refs = []
    for ref in remote_refs:
        suffix = ref.split("/", 3)[-1]
        if suffix not in allowed_remote_suffixes:
            stale_refs.append(ref)
            errors.add(Finding("RH013", ref, "STALE_REMOTE_TRACKING_REF"))
    return errors, {
        "reflog_only": len(reflog_only),
        "unreachable": len(unreachable),
        "tags": len(tags),
        "stash_refs": len(stash_refs),
        "stale_remote_refs": len(stale_refs),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--local-hygiene", action="store_true")
    parser.add_argument("--trusted-base")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    try:
        rules = load_policy(args.policy.resolve())
        rules["_personal_data_false_positives"] = load_personal_data_false_positives(
            root, rules
        )
        rules["_oversized_blob_exceptions"] = load_oversized_blob_exceptions(
            root, rules
        )
        rules["_used_oversized_blob_exceptions"] = set()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[repository_clean_history_guard] FAIL rule=RH000 classification={type(exc).__name__}", file=sys.stderr)
        return 2
    try:
        rules["_policy_relative"] = args.policy.resolve().relative_to(root).as_posix()
    except ValueError:
        rules["_policy_relative"] = ""

    errors: set[Finding] = set()
    publication_revisions = public_revision_args()
    scan_revisions = publication_revisions
    scan_mode = "public_refs"
    trusted_base = str(args.trusted_base or "")
    if trusted_base:
        try:
            incremental_revisions = trusted_incremental_revision_args(root, trusted_base)
        except ValueError as exc:
            print(
                f"[repository_clean_history_guard] FAIL rule=RH022 classification=TRUSTED_BASE_INVALID detail={exc}",
                file=sys.stderr,
            )
            return 2
        if incremental_authority_changed(root, trusted_base, rules):
            scan_mode = "public_refs_authority_fallback"
        else:
            scan_revisions = incremental_revisions
            scan_mode = "trusted_base_incremental"
    roots = [
        line
        for line in git(
            root,
            "rev-list",
            "--max-parents=0",
            *publication_revisions,
            check=False,
        ).splitlines()
        if line
    ]
    if len(roots) != 1:
        errors.add(Finding("RH001", "<repository>", "ROOT_COMMIT_COUNT"))
    allowed_remotes = rules.get("allowed_remotes", {})
    if not isinstance(allowed_remotes, dict):
        errors.add(Finding("RH000", str(args.policy), "INVALID_POLICY"))
        allowed_remotes = {}
    errors.update(remote_errors(root, allowed_remotes))
    errors.update(fsck_integrity_errors(root))

    forbidden_commits = {str(item) for item in rules.get("forbidden_commit_objects", [])}
    for commit_id in forbidden_commits:
        if run_git(root, "cat-file", "-e", f"{commit_id}^{{commit}}", check=False).returncode == 0:
            errors.add(Finding("RH004", f"object:{commit_id[:12]}", "OLD_COMMIT_IMPORTED"))

    scan_rows = object_rows(root, scan_revisions)
    if scan_mode == "trusted_base_incremental":
        scan_rows.extend(current_changed_tree_rows(root, trusted_base))
    for row in sorted(
        set(scan_rows),
        key=lambda item: (item.object_id, item.path, item.object_type, item.size),
    ):
        if row.object_type == "blob" and row.path:
            errors.update(blob_findings(root, row, rules))

    # Repository identity is mutable governance state, unlike secrets and
    # customer payloads. Preserve migration/audit history while rejecting a
    # stale executable identity in the current authoritative tree.
    for row in tree_rows(root, "HEAD"):
        errors.update(blob_findings(root, row, rules, scan_repository_identity=True))

    oversized_exceptions = rules.get("_oversized_blob_exceptions", set())
    used_oversized_exceptions = rules.get("_used_oversized_blob_exceptions", set())
    if scan_mode != "trusted_base_incremental" and isinstance(oversized_exceptions, set) and isinstance(used_oversized_exceptions, set):
        for _rule_id, path, object_id, _classification in sorted(
            oversized_exceptions - used_oversized_exceptions
        ):
            errors.add(
                Finding(
                    "RH021",
                    f"{path}@{object_id[:12]}",
                    "STALE_OVERSIZED_BLOB_EXCEPTION",
                )
            )

    hygiene = {
        "reflog_only": 0,
        "unreachable": 0,
        "tags": 0,
        "stash_refs": 0,
        "stale_remote_refs": 0,
    }
    if args.local_hygiene:
        local_errors, hygiene = local_hygiene_errors(root, rules)
        errors.update(local_errors)

    if errors:
        print("[repository_clean_history_guard] FAIL", file=sys.stderr)
        for finding in sorted(errors):
            print(
                f"- rule={finding.rule_id} path={finding.path} classification={finding.classification}",
                file=sys.stderr,
            )
        print("sensitive_values_recorded=false", file=sys.stderr)
        return 1
    print(
        f"[repository_clean_history_guard] PASS roots={len(roots)} reachable_scan={scan_mode} "
        f"local_hygiene={args.local_hygiene} reflog_only={hygiene['reflog_only']} "
        f"unreachable={hygiene['unreachable']} tags={hygiene['tags']} "
        f"stash_refs={hygiene['stash_refs']} "
        f"stale_remote_refs={hygiene['stale_remote_refs']} sensitive_values_recorded=false"
        f" oversized_exceptions={len(used_oversized_exceptions)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
