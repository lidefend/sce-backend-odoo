#!/usr/bin/env python3
"""Atomically run the local Quick gate and verify its exact-head receipt."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
import subprocess
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
import trusted_scan_scope as scans

SCHEMA_VERSION = 3
SUITE = "ci.local.quick"
PRODUCER = scans.PRODUCER
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class EvidenceError(RuntimeError):
    pass


class QuickRunFailed(EvidenceError):
    def __init__(self, returncode: int):
        super().__init__(f"{SUITE} failed with exit {returncode}; receipt not issued")
        self.returncode = returncode


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode:
        raise EvidenceError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process.stdout.strip()


def repository_root(root: Path) -> Path:
    return Path(git(root, "rev-parse", "--show-toplevel")).resolve()


def require_exact_clean_head(root: Path, expected_head: str) -> tuple[Path, str]:
    if not FULL_SHA.fullmatch(expected_head):
        raise EvidenceError("expected head must be a full lowercase commit SHA")
    root = repository_root(root)
    actual_head = git(root, "rev-parse", "HEAD")
    if actual_head != expected_head:
        raise EvidenceError(
            f"worktree HEAD changed: expected={expected_head} actual={actual_head}"
        )
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise EvidenceError("worktree must be clean for exact-head quick evidence")
    tree = git(root, "rev-parse", "HEAD^{tree}")
    if not FULL_SHA.fullmatch(tree):
        raise EvidenceError("HEAD tree identity is invalid")
    return root, tree


def evidence_path(root: Path, head: str) -> Path:
    raw = Path(git(root, "rev-parse", "--git-path", f"codex/evidence/{SUITE}/{head}.json"))
    return raw if raw.is_absolute() else root / raw


def _write_receipt_after_success(root: Path, expected_head: str, coverage: dict) -> Path:
    root, tree = require_exact_clean_head(root, expected_head)
    path = evidence_path(root, expected_head)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "suite": SUITE,
        "producer": PRODUCER,
        "head": expected_head,
        "tree": tree,
        "coverage": coverage,
    }
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{expected_head}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def is_linked_worktree(root: Path) -> bool:
    git_dir = Path(git(root, "rev-parse", "--path-format=absolute", "--git-dir")).resolve()
    common_dir = Path(
        git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    ).resolve()
    return git_dir != common_dir


def require_safe_make_environment() -> None:
    if os.environ.get("MAKEFILES") or os.environ.get("MAKEOVERRIDES"):
        raise EvidenceError("makefile injection or command overrides cannot sign coverage")
    safe_long = {"--no-print-directory", "--print-directory", "--keep-going", "--silent", "--quiet",
                 "--no-builtin-rules", "--no-builtin-variables", "--always-make"}
    safe_values = ("--jobserver-auth=", "--jobserver-fds=", "--jobs=", "--load-average=", "--output-sync=")
    for key in ("MAKEFLAGS", "MFLAGS"):
        for token in shlex.split(os.environ.get(key, "")):
            if token in safe_long or token.startswith(safe_values): continue
            if re.fullmatch(r"-?[bBkrRsSwj0-9.]+", token): continue
            raise EvidenceError("make flags can skip scanner execution or alter its authority")


def run_quick(root: Path, runner=subprocess.run) -> Path | None:
    require_safe_make_environment()
    root = repository_root(root)
    start_status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    start_head = git(root, "rev-parse", "HEAD") if not start_status else None
    if start_head and not FULL_SHA.fullmatch(start_head): raise EvidenceError("Quick start HEAD identity is invalid")
    command = (["python3", "scripts/dev/local_dev_frontend_quick.py", "--full-ci-local-quick"]
               if is_linked_worktree(root) else ["make", "--no-print-directory", "ci.local.quick.run"])
    if start_head is None:
        print("[ci.local.quick] evidence disabled: worktree was not clean at suite start")
        completed = runner(command, cwd=root, check=False, text=True)
        if completed.returncode: raise QuickRunFailed(completed.returncode)
        return None
    root, tree = require_exact_clean_head(root, start_head)
    coverage = scans.coverage_snapshot(root)
    with tempfile.TemporaryDirectory(prefix="sce-quick-scan-proof-") as temporary:
        folder = Path(temporary)
        launch = {'root': str(root), 'head': start_head, 'tree': tree, 'coverage': coverage}
        (folder / 'launch.json').write_text(json.dumps(launch, sort_keys=True))
        environment = os.environ.copy()
        environment[scans.COVERAGE_ENV] = str(folder)
        completed = runner(command, cwd=root, env=environment, check=False, text=True)
        if completed.returncode: raise QuickRunFailed(completed.returncode)
        require_exact_clean_head(root, start_head)
        if scans.coverage_snapshot(root) != coverage: raise EvidenceError("scan authority or reference snapshot changed")
        for kind in scans.AUTHORITY:
            path = folder / (kind + '.json')
            try:
                if path.is_symlink(): raise ValueError('symlink proof')
                proof = json.loads(path.read_text())
                base = proof.get('base')
                expected = {'protocol': scans.COVERAGE_PROTOCOL, 'kind': kind, 'head': start_head, 'tree': tree,
                            'coverage': coverage['scanners'][kind], 'mode': 'incremental' if base else 'full', 'base': base}
                if proof != expected: raise ValueError('proof mismatch')
                if base:
                    if not isinstance(base, str) or not FULL_SHA.fullmatch(base): raise ValueError('invalid base')
                    git(root, 'merge-base', '--is-ancestor', base, start_head)
            except (OSError, ValueError, EvidenceError) as exc:
                raise EvidenceError(f"actual successful scanner proof missing or invalid: {kind}") from exc
        return _write_receipt_after_success(root, start_head, coverage)


def verify(root: Path, expected_head: str) -> Path:
    root, tree = require_exact_clean_head(root, expected_head)
    path = evidence_path(root, expected_head)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError("exact-head quick evidence is missing") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError("exact-head quick evidence is unreadable") from exc
    expected = {"schema_version": 2, "suite": SUITE, "producer": "atomic-ci-local-quick-runner-v1",
                "head": expected_head, "tree": tree}
    if payload != expected:
        try:
            coverage = payload['coverage']
            expected.update(schema_version=SCHEMA_VERSION, producer=PRODUCER, coverage=coverage)
            valid = (payload == expected and scans.valid_coverage(root, coverage, expected_head)
                     and scans.equivalent_coverage(root, coverage, scans.coverage_snapshot(root)))
        except (KeyError, TypeError, OSError, ValueError, subprocess.CalledProcessError): valid = False
        if not valid: raise EvidenceError("exact-head quick evidence does not match the current candidate")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-head")
    args = parser.parse_args()
    try:
        if args.mode == "run":
            if args.expected_head is not None:
                raise EvidenceError("run mode does not accept --expected-head")
            path = run_quick(args.root)
        else:
            if args.expected_head is None:
                raise EvidenceError("verify mode requires --expected-head")
            path = verify(args.root, args.expected_head)
    except QuickRunFailed as exc:
        print(f"[local_quick_evidence] FAIL {exc}")
        return exc.returncode
    except EvidenceError as exc:
        print(f"[local_quick_evidence] MISS {exc}")
        return 2
    if path is not None:
        print(f"[local_quick_evidence] {'RECORDED' if args.mode == 'run' else 'VERIFIED'} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
