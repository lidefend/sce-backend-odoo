#!/usr/bin/env python3
"""Atomically run the local Quick gate and verify its exact-head receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shlex
import shutil
import sys
import subprocess
import tempfile
import threading
import time
import traceback
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ci"))
import trusted_scan_scope as scans
import trusted_scan_group as scan_group

SCHEMA_VERSION = 3
COMPOSITION_SCHEMA = 1
SUITE = "ci.local.quick"
PRODUCER = scans.PRODUCER
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
# The default sharded lane: one bounded shard is one make invocation over a
# strided slice of the declared target list, so an interrupted or partially
# failed candidate keeps the parts that did pass instead of proving nothing.
DEFAULT_SHARDS = 4
# Shard workers. One shard is one make invocation over a strided slice of the
# declared target list, and shards are independent by construction: each writes
# only its own part receipt, its own scan proofs and its own bounded log, and
# the declared target list carries no shared fixed write path. Running a few of
# them at once therefore costs no evidence and no coverage, and it removes the
# serial sum from every iteration. The worker budget itself lives with the scan
# group, which is the other lane that has to bound concurrency by the machine.
# Receipts are also the incremental-scan base source (see trusted_scan_scope),
# so the retained window is the newest receipts by issue time, never a bare age
# cutoff that could strand the only usable ancestor.
RECEIPT_RETENTION = 50
# Recipe lines of ci.local.quick.run that the sharded lane reproduces. Anything
# else fails closed so a new monolithic-only check cannot be silently dropped.
REPRODUCED_RECIPE_PREFIXES = ("git diff --check", "echo ")


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
    try:
        prune_receipts(root, current_head=expected_head)
    except (OSError, EvidenceError) as exc:
        # Retention is storage governance, not evidence integrity: the receipt
        # above is already written and verifiable, so a prune failure must not
        # turn a passing Quick into a failing one. It is reported, not swallowed.
        print(f"[local_quick_evidence] WARN receipt retention failed: {exc}")
    return path


def _newest_ancestor_receipt(root: Path, head: str, candidates: list[tuple[float, str, Path]]) -> str | None:
    """The most recently issued receipt head that is still an ancestor of head.

    Receipts drive incremental-scan base selection, so dropping every ancestor
    would silently force later scans back to full runs. Candidates arrive
    newest-first, so the first ancestor found is the strongest base candidate
    and the search stops there.
    """
    for _, stem, _ in candidates:
        if stem == head:
            continue
        probe = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", stem, head],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if probe.returncode == 0:
            return stem
    return None


def prune_receipts(root: Path, keep: int = RECEIPT_RETENTION, current_head: str | None = None) -> list[str]:
    """Keep the newest exact-head receipts (and their shard folders); drop older ones.

    Receipts feed incremental-scan base selection, so the window is the newest
    ``keep`` receipts by issue time plus the receipt just signed for
    ``current_head``; a bare age cutoff could remove the only usable ancestor and
    silently force every later scan back to a full run. Removal is confined to
    this worktree's receipt folder and the shard folder of each removed head.
    Unlike the evidence write itself, an under- or over-retention here never
    changes what a receipt proves.
    """
    if isinstance(keep, bool) or not isinstance(keep, int) or keep < 1:
        raise EvidenceError("receipt retention must be a positive integer")
    head = current_head or git(root, "rev-parse", "HEAD")
    if not FULL_SHA.fullmatch(head):
        raise EvidenceError("receipt retention needs a full HEAD identity")
    folder = evidence_path(root, head).parent
    if not folder.is_dir():
        return []
    receipts: list[tuple[float, str, Path]] = []
    for path in folder.glob("*.json"):
        try:
            if path.is_symlink() or not path.is_file() or not FULL_SHA.fullmatch(path.stem):
                continue
            receipts.append((path.stat().st_mtime, path.stem, path))
        except OSError:
            continue
    receipts.sort(key=lambda row: (row[0], row[1]), reverse=True)
    retained = {stem for _, stem, _ in receipts[:keep]} | {head}
    outside = receipts[keep:]
    anchor = _newest_ancestor_receipt(root, head, outside)
    if anchor is not None:
        retained.add(anchor)
    removed: list[str] = []
    for _, stem, path in outside:
        if stem in retained:
            continue
        path.unlink()
        shard = shard_root(root, stem)
        if shard.is_dir() and not shard.is_symlink():
            shutil.rmtree(shard)
        removed.append(stem)
    return removed


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


def quick_runner_command(root: Path) -> list[str]:
    """The governed single-shot suite command for this worktree kind."""
    return (
        ["python3", "scripts/dev/local_dev_frontend_quick.py", "--full-ci-local-quick"]
        if is_linked_worktree(root)
        else ["make", "--no-print-directory", "ci.local.quick.run"]
    )


def _require_clean_start(root: Path, purpose: str) -> str:
    if git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise EvidenceError(
            f"{purpose} requires a clean worktree because one receipt is bound to one exact "
            "HEAD; commit or stash the change, or run the receipt-free diagnostic entry "
            "`make ci.local.quick.diagnostic`"
        )
    head = git(root, "rev-parse", "HEAD")
    if not FULL_SHA.fullmatch(head):
        raise EvidenceError("HEAD identity is invalid")
    return head


def run_quick(root: Path, runner=subprocess.run, diagnostic: bool = False) -> Path | None:
    require_safe_make_environment()
    root = repository_root(root)
    start_status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    start_head = git(root, "rev-parse", "HEAD") if not start_status else None
    if start_head and not FULL_SHA.fullmatch(start_head): raise EvidenceError("Quick start HEAD identity is invalid")
    command = quick_runner_command(root)
    if start_head is None:
        if not diagnostic:
            # A dirty tree can only produce a receipt for a state that does not
            # exist, so the lane fails closed instead of running the full suite
            # with a silent "evidence disabled" and a zero exit status.
            raise EvidenceError(
                "worktree is not clean: the exact-head quick lane signs one receipt for one "
                "committed HEAD, so it refuses to run. Commit or stash the change, or use the "
                "explicit receipt-free diagnostic entry `make ci.local.quick.diagnostic`."
            )
        print("[ci.local.quick] DIAGNOSTIC: worktree is not clean; the suite runs but no receipt is issued")
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


def declared_quick_recipe(root: Path) -> list[str]:
    """The literal recipe lines of the monolithic ci.local.quick.run entry."""
    try:
        source = (root / "make/ci.mk").read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceError(f"cannot read the declared quick recipe: {exc}") from exc
    lines = source.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith("ci.local.quick.run:")]
    if len(starts) != 1:
        raise EvidenceError("ci.local.quick.run must be declared exactly once")
    recipe: list[str] = []
    for line in lines[starts[0] + 1:]:
        if not line.startswith("\t"):
            break
        recipe.append(line[1:].strip().removeprefix("@"))
    return recipe


def assert_quick_recipe_covered(root: Path) -> list[str]:
    """Fail closed if the monolithic recipe carries a check the sharded lane drops.

    The sharded entry runs the same declared target list but, unlike a single
    ``make ci.local.quick.run``, never executes that target's own recipe. Every
    recipe line must therefore be reproduced by the sharded path; a new line
    fails here instead of silently disappearing from the composed receipt.
    """
    recipe = declared_quick_recipe(root)
    if not recipe:
        raise EvidenceError("ci.local.quick.run declares no recipe for the sharded lane to reproduce")
    for line in recipe:
        if line.startswith(REPRODUCED_RECIPE_PREFIXES):
            continue
        raise EvidenceError(
            "ci.local.quick.run recipe line is not reproduced by the sharded lane: "
            f"{line!r}; teach scripts/ops/local_quick_evidence.py to reproduce it before sharding"
        )
    return recipe


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


def run_shard(root: Path, shards: int, index: int, runner=subprocess.run, reuse: bool = True) -> Path:
    """Run one bounded shard of the declared quick target list and record its part receipt."""
    require_safe_make_environment()
    shards, index = _checked_shard_layout(shards, index)
    root = repository_root(root)
    if is_linked_worktree(root):
        raise EvidenceError("sharded quick evidence is only supported in the primary worktree")
    start_head = _require_clean_start(root, "shard evidence")
    root, tree = require_exact_clean_head(root, start_head)
    manifest = required_targets(root)
    targets = manifest[index::shards]
    if not targets:
        raise EvidenceError("this shard covers no required target")
    part_path = shard_part_path(root, start_head, index, shards)
    if reuse:
        try:
            existing = _loaded_shard_part(root, start_head, tree, manifest, shards, index)
        except EvidenceError:
            existing = None
        # A part receipt is reusable only for the identical candidate and while
        # the scan authority/reference snapshot is unchanged; otherwise it is
        # re-run. This is what makes an interrupted candidate resume from its
        # remaining shards instead of repeating the ones that already passed.
        if existing is not None and existing["coverage"] == scans.coverage_snapshot(root):
            print(f"[local_quick_evidence] REUSE shard {index}/{shards - 1}: {len(targets)} targets already passed")
            return part_path
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
    atomic_json(part_path, part)
    return part_path


def shard_command(root: Path, shards: int, index: int) -> list[str]:
    """The governed shard entry point, so a concurrent shard is a real shard.

    A worker never reimplements a shard: it runs the same public ``shard`` mode
    a developer or a resumed run would run, so part receipts, reuse and every
    fail-closed check stay in one place.
    """
    return [sys.executable, str(Path(__file__).resolve()), "shard",
            "--root", str(root), "--shards", str(shards), "--shard", str(index)]


def _shard_popen(command: list[str], handle, root: Path):
    return subprocess.Popen(command, cwd=root, stdout=handle, stderr=subprocess.STDOUT, text=True)


def requested_shard_jobs(jobs: int | None) -> int | None:
    """Explicit worker count, else the environment, else None for the machine default."""
    if jobs is not None:
        return jobs
    if os.environ.get("SC_QUICK_SERIAL") == "1":
        return 1
    raw = os.environ.get("QUICK_JOBS")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise EvidenceError(f"QUICK_JOBS={raw!r} is not an integer") from exc


def concurrent_log_dir(root: Path) -> Path:
    """Where a concurrent shard keeps its log without ever dirtying the tree.

    The preferred ``.runtime/`` follows the repository convention and is
    git-ignored, but the lane that proves a clean tree must not be the one that
    breaks it: on a tree where that path is not ignored, the logs move inside the
    Git directory instead of turning the candidate dirty mid-run.
    """
    preferred = root / ".runtime"
    if not preferred.exists():
        try:
            git(root, "check-ignore", "-q", str(preferred / "probe.log"))
            return preferred
        except EvidenceError:
            pass
    elif preferred.is_dir():
        return preferred
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    return common / "codex" / "quick-logs"


def run_shards_concurrently(root: Path, shards: int, jobs: int, head: str,
                            popen=_shard_popen, log_dir: Path | None = None) -> None:
    """Run at most ``jobs`` shards at once and fail the run on the first failure.

    Concurrency is an execution detail, not an evidence property: each shard
    still proves its own slice against the identical head, tree and scan
    authority, still refuses to record when any of that moved, and the composed
    receipt is still signed only by :func:`compose` over the complete union.
    """
    folder = log_dir if log_dir is not None else concurrent_log_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    pending: queue.Queue[int] = queue.Queue()
    for index in range(shards):
        pending.put(index)
    outcomes: dict[int, tuple[int, float, Path]] = {}
    crashes: dict[int, BaseException] = {}
    lock = threading.Lock()

    def worker() -> None:
        while True:
            try:
                index = pending.get_nowait()
            except queue.Empty:
                return
            path = folder / f"quick-shard-{head[:12]}-{index}-of-{shards}.log"
            started = time.monotonic()
            try:
                with path.open("w", encoding="utf-8") as handle:
                    process = popen(shard_command(root, shards, index), handle, root)
                    returncode = process.wait()
            except BaseException as exc:  # noqa: BLE001 - report the real shard failure, not a missing outcome
                with lock:
                    crashes[index] = exc
                return
            with lock:
                outcomes[index] = (returncode, time.monotonic() - started, path)

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(max(1, min(jobs, shards)))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if crashes:
        first = min(crashes)
        for index in sorted(crashes):
            print(f"[local_quick_evidence] FAILED shard {index}/{shards - 1} raised "
                  f"{type(crashes[index]).__name__}: {crashes[index]}")
            print("".join(traceback.format_exception(crashes[index])))
        raise EvidenceError(
            f"concurrent quick shard {first} raised {type(crashes[first]).__name__}: {crashes[first]}")
    if len(outcomes) != shards:
        raise EvidenceError("a concurrent quick shard produced no outcome")
    for index in range(shards):
        returncode, duration, path = outcomes[index]
        print(f"[local_quick_evidence] shard {index}/{shards - 1} "
              f"status={'passed' if returncode == 0 else 'failed'} {duration:.1f}s log={path}")
    failed = [index for index in range(shards) if outcomes[index][0]]
    for index in failed:
        print(f"[local_quick_evidence] FAILED shard {index}/{shards - 1} output:")
        print(outcomes[index][2].read_text(encoding="utf-8", errors="replace"))
    if failed:
        raise QuickRunFailed(outcomes[failed[0]][0])


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
    assert_quick_recipe_covered(root)
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
    # The monolithic entry runs its recipe after the declared targets; the
    # sharded path never executes that recipe, so reproduce its only semantic
    # line here instead of dropping the check from the composed receipt.
    git(root, "diff", "--check")
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


def quick_degraded_reasons(root: Path) -> list[str]:
    """Why this run did not get the cheap scan path it was entitled to.

    A full scan is legitimate when the repository has no usable ancestor receipt
    or the authority genuinely changed. It is a degradation when the lane could
    not even prove its own identity (a detached or unreachable mainline), because
    then every later run pays the full scan for a reason the lane already knows.
    """
    reasons: set[str] = set()
    for kind in scans.AUTHORITY:
        try:
            scope = scans.select_scope(root, kind)
        except Exception:
            reasons.add("full_scan_fallback")
            continue
        if scope.base is not None:
            continue
        if scope.reason in ("coverage_identity_unprovable", "untrusted_origin"):
            reasons.add("detached_from_main")
        elif scope.reason == "verified_coverage_receipt_missing":
            reasons.add("receipt_absent")
    return sorted(reasons)


def _observe_quick(root: Path, status: str, duration: float, degraded: list[str],
                   owner: str | None) -> None:
    """File one lane observation. Telemetry is observability, not a gate, so a
    recording failure is reported and never rewrites the Quick outcome."""
    try:
        import lane_telemetry

        payload = lane_telemetry.record(
            root, "local.quick", "ci.local.quick", status, duration, tuple(degraded), owner,
        )
        print(f"[local_quick_evidence] telemetry lane={payload['lane']} status={status} "
              f"degraded={payload['degraded'] or 'none'}")
    except Exception as exc:
        print(f"[local_quick_evidence] WARN lane telemetry not recorded: {exc}")


def run_default(root: Path, shards: int | None = None, diagnostic: bool = False,
                runner=subprocess.run, jobs: int | None = None,
                popen=_shard_popen) -> Path | None:
    """The default ci.local.quick entry.

    The primary worktree shards the declared target list so an interrupted
    candidate keeps every part that already passed and a re-run resumes only the
    remainder. Independent shards run concurrently, bounded by the machine, so a
    full rescan stops paying the serial sum of its own shards. A linked worktree
    keeps the single governed runner, because shard parts are only supported in
    the primary worktree. ``diagnostic`` is the explicit receipt-free mode for a
    dirty development tree.
    """
    if diagnostic:
        return run_quick(root, runner=runner, diagnostic=True)
    root = repository_root(root)
    started = time.monotonic()
    status, owner, degraded = "passed", None, []
    try:
        if is_linked_worktree(root):
            return run_quick(root, runner=runner)
        shards = DEFAULT_SHARDS if shards is None else shards
        _checked_shard_layout(shards, 0)
        _require_clean_start(root, "the sharded quick lane")
        head = git(root, "rev-parse", "HEAD")
        workers = scan_group.resolve_jobs(requested_shard_jobs(jobs), shards)
        if workers == 1:
            print(f"[local_quick_evidence] serial shards shards={shards} jobs=1")
            for index in range(shards):
                run_shard(root, shards, index, runner=runner)
        else:
            print(f"[local_quick_evidence] concurrent shards shards={shards} jobs={workers}")
            run_shards_concurrently(root, shards, workers, head, popen=popen)
        receipt = compose(root, shards, head)
        degraded = quick_degraded_reasons(root)
        return receipt
    except QuickRunFailed:
        status, owner = "failed", "product_defect"
        raise
    except EvidenceError:
        status, owner = "not_run", "validation_tool_defect"
        raise
    finally:
        _observe_quick(root, status, time.monotonic() - started, degraded, owner)


def result_label(mode: str) -> str:
    """Only `verify` reports a pure verification; the other modes write evidence."""
    return "VERIFIED" if mode == "verify" else "RECORDED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "verify", "shard", "compose", "prune"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-head")
    parser.add_argument("--shards", type=int)
    parser.add_argument("--shard", type=int, dest="shard_index")
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument("--jobs", type=int)
    parser.add_argument("--keep", type=int)
    args = parser.parse_args()
    try:
        if args.mode == "run":
            if args.expected_head is not None or args.shard_index is not None or args.keep is not None:
                raise EvidenceError("run mode does not accept --expected-head, --shard or --keep")
            path = run_default(args.root, args.shards, args.diagnostic, jobs=args.jobs)
        elif args.mode == "verify":
            if args.expected_head is None:
                raise EvidenceError("verify mode requires --expected-head")
            if (args.shards is not None or args.shard_index is not None or args.keep is not None
                    or args.diagnostic or args.jobs is not None):
                raise EvidenceError("verify mode does not accept --shards, --shard, --keep, --jobs or --diagnostic")
            path = verify(args.root, args.expected_head)
        elif args.mode == "shard":
            if args.shards is None or args.shard_index is None:
                raise EvidenceError("shard mode requires --shards and --shard")
            if args.expected_head is not None or args.keep is not None or args.diagnostic or args.jobs is not None:
                raise EvidenceError("shard mode does not accept --expected-head, --keep, --jobs or --diagnostic")
            path = run_shard(args.root, args.shards, args.shard_index)
        elif args.mode == "prune":
            if (args.shards is not None or args.shard_index is not None or args.expected_head is not None
                    or args.diagnostic or args.jobs is not None):
                raise EvidenceError("prune mode does not accept --shards, --shard, --expected-head, --jobs or --diagnostic")
            keep = RECEIPT_RETENTION if args.keep is None else args.keep
            removed = prune_receipts(repository_root(args.root), keep)
            print(f"[local_quick_evidence] PRUNED {len(removed)} receipt(s); keep={keep}")
            for stem in removed:
                print(f"[local_quick_evidence]   removed {stem}")
            path = None
        else:
            if args.shards is None:
                raise EvidenceError("compose mode requires --shards")
            if args.shard_index is not None or args.keep is not None or args.diagnostic or args.jobs is not None:
                raise EvidenceError("compose mode does not accept --shard, --keep, --jobs or --diagnostic")
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
        print(f"[local_quick_evidence] {result_label(args.mode)} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
