#!/usr/bin/env python3
"""Plan and execute only the acceptance evidence suites that are not reusable."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "verify"))

from scripts.ops import acceptance_evolution_record as recorder  # noqa: E402
from scripts.verify import acceptance_evolution_binding_guard as binding  # noqa: E402


SCHEMA = "acceptance_evolution_integration_plan.v1"
DEFAULT_REGISTRY = ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
DEFAULT_MANIFEST = ROOT / ".runtime" / "acceptance-evolution" / "evidence.v1.json"
DEFAULT_OUTPUT = ROOT / ".runtime" / "acceptance-evolution" / "integration-plan.json"


class IntegrationError(RuntimeError):
    """The acceptance evidence run cannot be planned or executed safely."""


def _integration_contract(registry: dict, suite_id: str) -> dict:
    suite = registry["suites"].get(suite_id)
    if not isinstance(suite, dict):
        raise IntegrationError(f"unknown acceptance suite: {suite_id}")
    integration = suite.get("integration")
    if not isinstance(integration, dict):
        raise IntegrationError(
            f"required evidence suite {suite_id} has no governed integration runbook"
        )
    return integration


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_run_plan(
    registry: dict,
    acceptance_plan: dict,
    manifest_path: Path,
    head: str,
    *,
    full: bool = False,
    full_reason: str = "",
    reverify_suites: tuple[str, ...] = (),
    reverify_reason: str = "",
) -> dict:
    """Return RUN/REUSE decisions without executing a suite or writing evidence."""

    required = list(acceptance_plan["required_evidence_suites"])
    reverify = tuple(sorted(set(reverify_suites)))
    if full and not full_reason.strip():
        raise IntegrationError("full acceptance rerun requires a non-empty reason")
    if reverify and not reverify_reason.strip():
        raise IntegrationError("suite reverify requires a non-empty reason")
    unknown = sorted(set(reverify) - set(required))
    if unknown:
        raise IntegrationError(
            "cannot reverify suites outside the current required set: " + ", ".join(unknown)
        )
    previous = recorder._load_previous(Path(manifest_path))
    run: list[dict] = []
    reuse: list[dict] = []
    for suite_id in required:
        integration = _integration_contract(registry, suite_id)
        reusable = None if full or suite_id in reverify else recorder._reuse_suite_record(
            registry, previous, suite_id, head
        )
        if reusable is not None:
            reuse.append(
                {
                    "suite": suite_id,
                    "bound_head": reusable.get("bound_head"),
                    "input_sha256": reusable.get("input_sha256"),
                    "targets": integration["targets"],
                    "evidence": integration["evidence"],
                }
            )
            continue
        if full:
            reason = full_reason.strip()
        elif suite_id in reverify:
            reason = reverify_reason.strip()
        else:
            reason = "no reusable evidence for the current suite inputs"
        run.append(
            {
                "suite": suite_id,
                "reason": reason,
                "targets": integration["targets"],
                "evidence": integration["evidence"],
                "status": "pending",
            }
        )
    evidence_suites = [
        suite_id
        for suite_id, suite in registry["suites"].items()
        if suite.get("evidence")
    ]
    deferred = list(acceptance_plan.get("deferred_evidence_suites", []))
    not_required = [
        suite_id
        for suite_id in evidence_suites
        if suite_id not in required and suite_id not in deferred
    ]
    return {
        "schema": SCHEMA,
        "head_sha": head,
        "base_sha": acceptance_plan["base_sha"],
        "acceptance_stage": acceptance_plan.get("stage", "merge"),
        "required_suites": required,
        "deferred_suites": deferred,
        "run": run,
        "reuse": reuse,
        "not_required": not_required,
        "status": "planned" if run else "reuse_only",
        "candidate_evidence": False,
        "writes_authorized": False,
    }


def _run_command(
    command: list[str],
    *,
    root: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> int:
    result = runner(command, cwd=root, check=False)
    return int(result.returncode)


def _resolve_evidence(root: Path, patterns: list[str], head: str) -> list[Path]:
    selected: list[Path] = []
    for pattern in patterns:
        matches = [
            path
            for path in root.glob(pattern.replace("{head}", head))
            if path.is_file()
        ]
        if not matches:
            raise IntegrationError(f"acceptance evidence is missing for pattern: {pattern}")
        matches.sort(key=lambda path: (path.stat().st_mtime_ns, path.as_posix()))
        candidate = matches[-1]
        if candidate not in selected:
            selected.append(candidate)
    return selected


def execute_run_plan(
    registry: dict,
    acceptance_plan: dict,
    manifest_path: Path,
    run_plan: dict,
    *,
    head: str,
    output: Path,
    prepare_target: str = "",
    root: Path = ROOT,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict:
    """Execute the planned suites, then record only their validated evidence."""

    recorder._require_clean_worktree()
    _write_json(output, run_plan)
    if not run_plan["run"]:
        run_plan["status"] = "reuse_only"
        run_plan["candidate_evidence"] = True
        return run_plan
    if prepare_target:
        exit_code = _run_command(
            ["make", "--no-print-directory", prepare_target],
            root=root,
            runner=runner,
        )
        if exit_code:
            run_plan.update(
                status="failed",
                failure_owner="validation_tool_defect",
                failure_step=prepare_target,
                exit_code=exit_code,
            )
            _write_json(output, run_plan)
            return run_plan
    for row in run_plan["run"]:
        for target in row["targets"]:
            exit_code = _run_command(
                ["make", "--no-print-directory", target],
                root=root,
                runner=runner,
            )
            row.setdefault("executed_targets", []).append(
                {"target": target, "exit_code": exit_code}
            )
            if exit_code:
                row["status"] = "failed"
                run_plan.update(
                    status="failed",
                    failure_owner="validation_tool_defect",
                    failure_step=target,
                    exit_code=exit_code,
                )
                _write_json(output, run_plan)
                return run_plan
        row["status"] = "passed"
    try:
        provided = {}
        for row in run_plan["run"]:
            integration = _integration_contract(registry, row["suite"])
            provided[row["suite"]] = _resolve_evidence(root, integration["evidence"], head)
            row["evidence_paths"] = [
                path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
                for path in provided[row["suite"]]
            ]
        manifest, recorded, carried = recorder.record_manifest(
            registry,
            acceptance_plan,
            manifest_path,
            head,
            provided,
        )
    except (binding.BindingError, IntegrationError, OSError, ValueError) as exc:
        run_plan.update(
            status="failed",
            failure_owner="validation_tool_defect",
            failure_step="acceptance evidence recording",
            reason=str(exc),
        )
        _write_json(output, run_plan)
        return run_plan
    run_plan.update(
        status="passed",
        candidate_evidence=True,
        writes_authorized=True,
        recorded_suites=recorded,
        carried_suites=carried,
        manifest=str(manifest_path),
        manifest_recorded_at=manifest["recorded_at"],
    )
    return run_plan


def _build_acceptance_plan(registry: dict, base: str | None, head: str) -> dict:
    resolved_head = binding.resolve_head(head)
    resolved_base = binding.resolve_base(base, resolved_head)
    plan = binding.build_plan(
        registry,
        binding.changed_files(resolved_base, resolved_head),
        resolved_base,
        resolved_head,
    )
    if plan["status"] != "PASS":
        raise IntegrationError(
            "change set is not fully classified: " + ", ".join(plan["unclassified"])
        )
    return binding.plan_for_stage(registry, plan, "merge")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--prepare-target", default="")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--full-reason", default="")
    parser.add_argument("--reverify-suite", action="append", default=[])
    parser.add_argument("--reverify-reason", default="")
    args = parser.parse_args(argv)
    try:
        recorder._require_clean_worktree()
        registry = binding.load_registry(args.registry)
        acceptance_plan = _build_acceptance_plan(registry, args.base, args.head)
        run_plan = build_run_plan(
            registry,
            acceptance_plan,
            args.manifest,
            acceptance_plan["head_sha"],
            full=args.full,
            full_reason=args.full_reason,
            reverify_suites=tuple(args.reverify_suite),
            reverify_reason=args.reverify_reason,
        )
        _write_json(args.output, run_plan)
        if args.execute:
            run_plan = execute_run_plan(
                registry,
                acceptance_plan,
                args.manifest,
                run_plan,
                head=acceptance_plan["head_sha"],
                output=args.output,
                prepare_target=args.prepare_target,
            )
            _write_json(args.output, run_plan)
            if run_plan["status"] == "failed":
                print(
                    "[acceptance.integration] FAIL "
                    f"step={run_plan.get('failure_step')} output={args.output}"
                )
                return run_plan.get("exit_code", 1)
        print(
            "[acceptance.integration] "
            + json.dumps(
                {
                    "status": run_plan["status"],
                    "head": run_plan["head_sha"],
                    "run": [row["suite"] for row in run_plan["run"]],
                    "reuse": [row["suite"] for row in run_plan["reuse"]],
                    "not_required": run_plan["not_required"],
                    "output": str(args.output),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (binding.BindingError, IntegrationError, OSError, ValueError) as exc:
        print(f"[acceptance.integration] FAIL {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
