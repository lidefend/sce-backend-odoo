#!/usr/bin/env python3
"""Atomically run the local Quick gate and verify its exact-head receipt."""

from __future__ import annotations

import argparse
import hashlib
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
COMPOSITION_SCHEMA = 1
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


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def required_targets(root: Path) -> list[str]:
    """The declared required target list, derived from the makefile so it cannot drift."""
    try:
        source = (root / "make/ci.mk").read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceError(f"cannot read the declared quick target list: {exc}") from exc
    rows = [line for line in source.splitlines() if line.startswith("ci.local.quick.run:")]
    if len(rows) != 1:
        raise EvidenceError("ci.local.quick.run must be declared exactly once")
    row = rows[0]
    if row.rstrip().endswith("\\"):
        raise EvidenceError("ci.local.quick.run prerequisites must not be line-continued")
    tokens = row.split(":", 1)[1].split()
    if not tokens or tokens[0] != "guard.prod.forbid":
        raise EvidenceError("ci.local.quick.run prerequisites must start with guard.prod.forbid")
    if any(token.startswith("$") or "%" in token or ":" in token for token in tokens):
        raise EvidenceError("ci.local.quick.run prerequisites must be literal target names")
    if len(set(tokens)) != len(tokens):
        raise EvidenceError("ci.local.quick.run prerequisites must not repeat a target")
    return tokens


def shard_root(root: Path, head: str) -> Path:
    return evidence_path(root, head).with_suffix("")


def shard_part_path(root: Path, head: str, index: int, shards: int) -> Path:
    return shard_root(root, head) / "parts" / f"shard-{index}-of-{shards}.json"


def _checked_shard_layout(shards: object, index: object) -> tuple[int, int]:
    if isinstance(shards, bool) or not isinstance(shards, int) or not 1 <= shards <= 64:
        raise EvidenceError("shards must be an integer between 1 and 64")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < shards:
        raise EvidenceError("shard index must be inside [0, shards)")
    return shards, index


def run_shard(root: Path, shards: int, index: int, runner=subprocess.run) -> Path:
    """Run one bounded shard of the declared quick target list and record its part receipt."""
    require_safe_make_environment()
    shards, index = _checked_shard_layout(shards, index)
    root = repository_root(root)
    if is_linked_worktree(root):
        raise EvidenceError("sharded quick evidence is only supported in the primary worktree")
    if git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise EvidenceError("shard evidence requires a clean worktree at start")
    start_head = git(root, "rev-parse", "HEAD")
    if not FULL_SHA.fullmatch(start_head):
        raise EvidenceError("shard start HEAD identity is invalid")
    root, tree = require_exact_clean_head(root, start_head)
    manifest = required_targets(root)
    targets = manifest[index::shards]
    if not targets:
        raise EvidenceError("this shard covers no required target")
    folder = shard_root(root, start_head) / "scan-proofs"
    folder.mkdir(parents=True, exist_ok=True)
    coverage = scans.coverage_snapshot(root)
    atomic_json(folder / "launch.json", {"root": str(root), "head": start_head, "tree": tree, "coverage": coverage})
    environment = os.environ.copy()
    environment[scans.COVERAGE_ENV] = str(folder)
    completed = runner(
        ["make", "--no-print-directory", *targets],
        cwd=root,
        env=environment,
        check=False,
        text=True,
    )
    if completed.returncode:
        raise QuickRunFailed(completed.returncode)
    require_exact_clean_head(root, start_head)
    part = {
        "schema_version": COMPOSITION_SCHEMA,
        "suite": SUITE,
        "head": start_head,
        "tree": tree,
        "shards": shards,
        "index": index,
        "targets": targets,
        "status": "passed",
        "coverage": coverage,
    }
    path = shard_part_path(root, start_head, index, shards)
    atomic_json(path, part)
    return path


def _loaded_shard_part(root: Path, head: str, tree: str, manifest: list[str], shards: int, index: int) -> dict:
    path = shard_part_path(root, head, index, shards)
    try:
        part = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"shard {index} of {shards} has no part receipt") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"shard {index} of {shards} part receipt is unreadable") from exc
    if not isinstance(part, dict) or set(part) != {
        "schema_version", "suite", "head", "tree", "shards", "index", "targets", "status", "coverage",
    }:
        raise EvidenceError(f"shard {index} of {shards} part receipt shape is invalid")
    if part["schema_version"] != COMPOSITION_SCHEMA or part["suite"] != SUITE:
        raise EvidenceError(f"shard {index} of {shards} part receipt identity is invalid")
    if part["head"] != head or part["tree"] != tree:
        raise EvidenceError(f"shard {index} of {shards} part receipt binds another candidate")
    if part["shards"] != shards or part["index"] != index:
        raise EvidenceError(f"shard {index} of {shards} part receipt layout is invalid")
    if part["status"] != "passed":
        raise EvidenceError(f"shard {index} of {shards} is not a passed shard")
    if part["targets"] != manifest[index::shards]:
        raise EvidenceError(f"shard {index} of {shards} does not carry the declared shard targets")
    return part


def compose(root: Path, shards: int, expected_head: str) -> Path:
    """Compose passed shards of one identical candidate into the standard exact-head receipt."""
    shards, _ = _checked_shard_layout(shards, 0)
    root, tree = require_exact_clean_head(root, expected_head)
    manifest = required_targets(root)
    covered: list[str] = []
    parts: list[dict] = []
    coverage = scans.coverage_snapshot(root)
    for index in range(shards):
        part = _loaded_shard_part(root, expected_head, tree, manifest, shards, index)
        if part["coverage"] != coverage:
            raise EvidenceError(f"shard {index} of {shards} coverage snapshot changed")
        covered.extend(part["targets"])
        path = shard_part_path(root, expected_head, index, shards)
        parts.append({
            "index": index,
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    # Strided parts concatenate to a permutation of the manifest, so order is
    # bound by the per-part target check above; here the union must still cover
    # the declared list exactly, with no missing, extra or duplicated target.
    if sorted(covered) != sorted(manifest):
        raise EvidenceError("the shard union does not cover the declared quick target list exactly")
    folder = shard_root(root, expected_head) / "scan-proofs"
    for kind in scans.AUTHORITY:
        path = folder / (kind + ".json")
        try:
            if path.is_symlink():
                raise ValueError("symlink proof")
            proof = json.loads(path.read_text(encoding="utf-8"))
            base = proof.get("base") if isinstance(proof, dict) else None
            expected = {
                "protocol": scans.COVERAGE_PROTOCOL, "kind": kind, "head": expected_head, "tree": tree,
                "coverage": coverage["scanners"][kind],
                "mode": "incremental" if base else "full", "base": base,
            }
            if proof != expected:
                raise ValueError("proof mismatch")
            if base:
                if not isinstance(base, str) or not FULL_SHA.fullmatch(base):
                    raise ValueError("invalid base")
                git(root, "merge-base", "--is-ancestor", base, expected_head)
        except (OSError, ValueError, KeyError, TypeError, EvidenceError) as exc:
            raise EvidenceError(f"actual successful scanner proof missing or invalid: {kind}") from exc
    receipt = _write_receipt_after_success(root, expected_head, coverage)
    atomic_json(shard_root(root, expected_head) / "composition.json", {
        "schema_version": COMPOSITION_SCHEMA,
        "suite": SUITE,
        "head": expected_head,
        "tree": tree,
        "shards": shards,
        "parts": parts,
        "manifest_sha256": hashlib.sha256(json.dumps(manifest).encode("utf-8")).hexdigest(),
        "coverage_sha256": hashlib.sha256(json.dumps(coverage, sort_keys=True).encode("utf-8")).hexdigest(),
        "receipt": receipt.relative_to(root).as_posix() if receipt.is_relative_to(root) else str(receipt),
    })
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "verify", "shard", "compose"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-head")
    parser.add_argument("--shards", type=int)
    parser.add_argument("--shard", type=int, dest="shard_index")
    args = parser.parse_args()
    try:
        if args.mode == "run":
            if args.expected_head is not None or args.shards is not None or args.shard_index is not None:
                raise EvidenceError("run mode does not accept --expected-head, --shards or --shard")
            path = run_quick(args.root)
        elif args.mode == "verify":
            if args.expected_head is None:
                raise EvidenceError("verify mode requires --expected-head")
            if args.shards is not None or args.shard_index is not None:
                raise EvidenceError("verify mode does not accept --shards or --shard")
            path = verify(args.root, args.expected_head)
        elif args.mode == "shard":
            if args.shards is None or args.shard_index is None:
                raise EvidenceError("shard mode requires --shards and --shard")
            if args.expected_head is not None:
                raise EvidenceError("shard mode does not accept --expected-head")
            path = run_shard(args.root, args.shards, args.shard_index)
        else:
            if args.shards is None:
                raise EvidenceError("compose mode requires --shards")
            if args.shard_index is not None:
                raise EvidenceError("compose mode does not accept --shard")
            head = args.expected_head
            if head is None:
                head = subprocess.run(
                    ["git", "-C", str(args.root), "rev-parse", "HEAD"],
                    check=True, text=True, stdout=subprocess.PIPE,
                ).stdout.strip()
            path = compose(args.root, args.shards, head)
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
