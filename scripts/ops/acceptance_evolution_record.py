#!/usr/bin/env python3
"""Record exact-head acceptance evidence for the evolution binding guard.

Every ``--suite`` value is validated against the suite's declared adapter
before it is written to the manifest. The recorder therefore cannot turn an
arbitrary JSON file into "acceptance evidence": the file must carry the suite's
schema, a passing status, and the head at which it was executed. Suites whose
declared inputs are unchanged are carried forward from the previous manifest;
changed suites must be supplied again for the current head.

Usage:
  python3 scripts/ops/acceptance_evolution_record.py \
    --base <merge-base> --head <head> \
    --suite daily_runtime_entry=.runtime/final-acceptance/daily-runtime-entry-verify.json \
    --suite path_namespace_identity=.runtime/final-acceptance/path-ns-c-acceptance.json \
    --output .runtime/acceptance-evolution/evidence.v1.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "verify"))

import acceptance_evolution_binding_guard as binding  # noqa: E402

DEFAULT_REGISTRY = ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
DEFAULT_OUTPUT = ROOT / ".runtime" / "acceptance-evolution" / "evidence.v1.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_suite_args(values: list[str]) -> dict[str, list[Path]]:
    suites: dict[str, list[Path]] = {}
    for value in values:
        suite_id, separator, raw_path = value.partition("=")
        if not separator or not suite_id or not raw_path:
            raise binding.BindingError(f"--suite must be ID=PATH, got {value!r}")
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / raw_path
        suites.setdefault(suite_id, []).append(path)
    return suites


def _now() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _require_clean_worktree() -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=binding.ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        raise binding.BindingError("unable to read the worktree state")
    if status.stdout.strip():
        raise binding.BindingError("evidence recording requires a clean worktree at the evaluated head")


def _load_previous(manifest_path: Path) -> dict:
    if not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise binding.BindingError(f"evidence manifest unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise binding.BindingError("evidence manifest must be a JSON object")
    return payload


def _reuse_suite_record(
    registry: dict, previous: dict, suite_id: str, head: str
) -> dict | None:
    """Return a validated record when this suite's inputs are unchanged.

    HEAD is provenance, not an invalidation key.  The suite's declared inputs
    are the key: if they hash identically at the source head and the new head,
    the earlier execution still proves the same layer.  The evidence file is
    revalidated against the source head so a changed artifact cannot ride along.
    """

    suites = previous.get("suites")
    if not isinstance(suites, dict):
        return None
    record = suites.get(suite_id)
    if not isinstance(record, dict):
        return None
    bound_head = str(record.get("bound_head") or previous.get("head_sha") or "")
    if not binding.SHA_RE.match(bound_head):
        return None
    current_input = binding.suite_input_sha256(registry, suite_id, head)
    source_input = binding.suite_input_sha256(registry, suite_id, bound_head)
    if current_input != source_input:
        return None
    saved_input = record.get("input_sha256")
    if saved_input is not None and saved_input != current_input:
        return None
    candidate = dict(record)
    candidate["bound_head"] = bound_head
    candidate["input_sha256"] = current_input
    try:
        binding.validate_suite_record(
            registry,
            suite_id,
            candidate,
            head,
            str(previous.get("recorded_at") or ""),
        )
    except binding.BindingError:
        return None
    if bound_head != head:
        candidate["carried_from"] = bound_head
        candidate["carried_at"] = _now()
    else:
        candidate.pop("carried_from", None)
        candidate.pop("carried_at", None)
    return candidate


def _record_new_suite(
    registry: dict, suite_id: str, paths: list[Path], head: str
) -> dict:
    evidence_contract = registry["suites"][suite_id].get("evidence")
    if not evidence_contract:
        raise binding.BindingError(
            f"suite {suite_id} is covered by its governed lane and takes no evidence file"
        )
    adapter = evidence_contract["adapter"]
    items = []
    for path in paths:
        if not path.is_file():
            raise binding.BindingError(f"evidence file missing: {path}")
        counts = binding.validate_evidence_file(path, adapter, head, evidence_contract)
        items.append(
            {
                "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "sha256": _sha256(path),
                "adapter": adapter,
                **counts,
            }
        )
        print(f"[acceptance_evolution.record] {suite_id} <= {path}")
    return {
        "status": "pass",
        "evidence": items,
        "bound_head": head,
        "input_sha256": binding.suite_input_sha256(registry, suite_id, head),
        "verified_at": _now(),
    }


def record_manifest(
    registry: dict,
    plan: dict,
    manifest_path: Path,
    head: str,
    provided: dict[str, list[Path]],
    *,
    carry_only: bool = False,
) -> tuple[dict, list[str], list[str]]:
    """Record new suite evidence and carry forward only unchanged suites."""

    if carry_only and provided:
        raise binding.BindingError("--carry-forward does not accept --suite")
    _require_clean_worktree()
    previous = _load_previous(manifest_path)
    suites: dict[str, dict] = {}
    carried: list[str] = []
    for suite_id in registry["suites"]:
        candidate = _reuse_suite_record(registry, previous, suite_id, head)
        if candidate is not None:
            suites[suite_id] = candidate
            if str(candidate.get("bound_head")) != head:
                carried.append(suite_id)
    if carry_only and not carried:
        raise binding.BindingError("no suite evidence can be carried forward")
    newly_recorded: list[str] = []
    for suite_id, paths in provided.items():
        suites[suite_id] = _record_new_suite(registry, suite_id, paths, head)
        if suite_id in carried:
            carried.remove(suite_id)
        newly_recorded.append(suite_id)
    missing = sorted(set(plan["required_evidence_suites"]) - set(suites))
    if missing:
        raise binding.BindingError(
            "missing evidence for required suites: " + ", ".join(missing)
        )
    unrequested = sorted(set(newly_recorded) - set(plan["required_evidence_suites"]))
    if unrequested:
        print(
            "[acceptance_evolution.record] note: non-required suites recorded: "
            + ", ".join(unrequested)
        )
    manifest = {
        "schema": binding.EVIDENCE_SCHEMA,
        "head_sha": head,
        "base_sha": plan["base_sha"],
        "recorded_at": _now(),
        "suites": suites,
    }
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    try:
        binding.write_json(temporary, manifest)
        binding.validate_manifest(registry, plan, temporary, head)
        temporary.replace(manifest_path)
    finally:
        temporary.unlink(missing_ok=True)
    return manifest, newly_recorded, carried


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--base", help="base commit; defaults to BASE_SHA or origin/main merge-base")
    parser.add_argument("--head", help="head commit; defaults to HEAD_SHA or HEAD")
    parser.add_argument("--stage", choices=("all", "merge", "deployment"), default="all")
    parser.add_argument("--suite", action="append", default=[], metavar="ID=PATH")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--carry-forward",
        action="store_true",
        help="re-anchor only suites whose declared inputs are unchanged",
    )
    args = parser.parse_args(argv)
    try:
        registry = binding.load_registry(Path(args.registry))
        head = binding.resolve_head(args.head)
        base = binding.resolve_base(args.base, head)
        plan = binding.build_plan(registry, binding.changed_files(base, head), base, head)
        if plan["status"] != "PASS":
            raise binding.BindingError(
                "change set is not fully classified; fix the registry before recording evidence"
            )
        plan = binding.plan_for_stage(registry, plan, args.stage)
        provided = parse_suite_args(args.suite)
        unknown = sorted(set(provided) - set(registry["suites"]))
        if unknown:
            raise binding.BindingError(f"unknown suites: {unknown}")
        manifest, recorded, carried = record_manifest(
            registry,
            plan,
            Path(args.output),
            head,
            provided,
            carry_only=args.carry_forward,
        )
        print(
            f"[acceptance_evolution.record] PASS head={head[:12]} "
            f"recorded={','.join(recorded) or 'none'} "
            f"carried={','.join(carried) or 'none'} output={args.output}"
        )
        return 0
    except binding.BindingError as exc:
        print(f"[acceptance_evolution.record] FAIL {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
