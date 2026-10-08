#!/usr/bin/env python3
"""Run the smallest registered frontend checks affected by live source changes.

This is a development feedback tool.  It deliberately never builds a candidate,
captures browser evidence, refreshes generated reports, or computes a candidate
fingerprint.  Those operations remain part of the one-shot exact-head
publication qualification flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ops.agent_run_context import RunError, resolve_run, delta_paths, evaluate

WATCH_ROOTS = (
    "frontend/apps/web/src",
    "frontend/apps/web/scripts",
    "frontend/packages/ui/src",
    "scripts/verify/frontend_",
)
STATE_PATH = ROOT / ".runtime/frontend-dev-validation/status.json"


@dataclass(frozen=True)
class Rule:
    fragments: tuple[str, ...]
    targets: tuple[str, ...]


RULES = (
    Rule((
        "/views/LoginView.vue",
        "/views/AccountActivationView.vue",
        "/views/PasswordRecoveryView.vue",
    ), (
        "verify.frontend.auth_credential.guard",
        "verify.frontend.auth_surface.guard",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("/layouts/AppShell.vue", "/layouts/AppShell.css", "/navigation/"), (
        "verify.frontend.navigation_shell.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("/views/SceneView.vue", "/app/sceneEntryContract.ts"), (
        "verify.frontend.scene_entry_contract.unit",
        "verify.frontend.navigation_shell.unit",
    )),
    Rule(("/components/design-system/", "frontend/packages/ui/"), (
        "verify.frontend.primitive_adapter.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    # These views/pages carry a size ratchet that only `style_system.guard`
    # enforces, so a growing file must be routed to it instead of falling
    # through to the generic typecheck fallback.
    Rule((
        "/layouts/AppShell.vue",
        "/pages/ListPage.vue",
        "/pages/ContractFormPage.vue",
        "/pages/ContractFormRoute.vue",
        "/views/ActionView.vue",
    ), (
        "verify.frontend.style_system.guard",
    )),
    # ActionView 的 surface 展示形态与列表分页声明都由契约投影消费；改动入口视图
    # 或两个消费运行时都要跑对应行为锁，否则契约消费回归只能在部署面上暴露。
    Rule((
        "/views/ActionView.vue",
        "/app/runtime/actionViewSurfaceGateRuntime.ts",
        "/app/runtime/actionViewListPageSizeRuntime.ts",
    ), (
        "verify.frontend.action_view_surface_gate_runtime.unit",
        "verify.frontend.action_view_page_size_runtime.unit",
        "verify.frontend.contract_basis.unit",
        "verify.frontend.style_system.guard",
    )),
    # 契约基础台账与它的守卫是 contract_basis 行为锁的直接输入。改台账/守卫
    # 却落到「未映射」会让这份完整性缺口只能靠人工挑目标，甚至漏跑到交付冻结。
    Rule((
        "docs/architecture/frontend_contract_basis_ledger.json",
        "scripts/verify/frontend_contract_basis_guard.py",
        "scripts/verify/test_frontend_contract_basis_guard.py",
    ), (
        "verify.frontend.contract_basis.unit",
        "verify.frontend.contract_basis.enforce",
    )),
    # 规划器自身的代码与它推荐的 make 目标定义是同一份契约：改规划器或改
    # make/frontend.mk 的目标名都要跑规划器自己的行为锁，否则「目标名漂移」会
    # 让最小复用变成 make 直接报错，又退回人工全量。
    Rule((
        "scripts/verify/frontend_dev_incremental.py",
        "scripts/verify/test_frontend_dev_incremental.py",
        "make/frontend.mk",
    ), (
        "verify.frontend.dev.incremental.unit",
    )),
    Rule(("/pages/contractForm/", "/components/template/"), (
        "verify.frontend.canonical_form_presenter.unit",
        "verify.frontend.primitive_adapter.unit",
        "verify.frontend.product_page_pattern.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
        # `useRecord*.ts` carry their own size ratchet in style_system.guard.
        "verify.frontend.style_system.guard",
    )),
    Rule(("/components/action/", "/components/product-list/"), (
        "verify.frontend.collection_action_toolbar.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("scripts/verify/frontend_page_pattern_reference_parity_guard.py",), (
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    # The business-entry matrix shares one pure model, one scope adapter and one
    # reuse engine. A change to any of them moves the derivation or the reuse
    # decision, so route all of them to the engine unit test instead of letting
    # the matrix scripts fall through to the typecheck fallback.
    # The released list-surface acceptance probe carries a contract lock: editing the
    # probe without running its lock let a stale assertion survive until the daily
    # lane failed. Route the probe and its lock to the same non-zero unit target.
    Rule((
        "scripts/verify/frontend_list_surface_structure_browser.mjs",
        "scripts/verify/test_frontend_list_surface_search_contract.py",
    ), (
        "verify.frontend.list_surface_search_contract.unit",
    )),
    Rule((
        "scripts/verify/business_entry_matrix_",
        "scripts/verify/business_entry_negative_closures.mjs",
        "scripts/ops/evidence_scope.py",
        # The focused behaviour tests are part of the same contract: editing the
        # entry's tests without running them let the suite that locks the reuse
        # decision fall through to the generic typecheck fallback.
        "scripts/verify/test_business_entry_matrix_incremental.py",
        "scripts/verify/business_entry_matrix_scope_seed.py",
    ), (
        "verify.frontend.business_entry.evidence_scope.unit",
    )),
)
FALLBACK_TARGET = "verify.frontend.typecheck.strict"
FORBIDDEN_DEVELOPMENT_TARGET_PARTS = ("quick", "build", "browser", "release", "fingerprint")
# Run bookkeeping and narrative documentation carry no frontend source input:
# reconciling `.agent/` state or writing an iteration record must never be reported
# as an unmapped product path, otherwise every continuation or record update would
# demand a manual L2 selection that has nothing to select. Narrative docs are a
# documentation-only change, which the recorded reuse decision
# (.agent/decisions/evidence-reuse-identity.yaml) states does not invalidate a unit.
NON_SOURCE_PATH_PREFIXES = (".agent/", "docs/")


def select_targets(paths: list[str]) -> list[str]:
    selected: set[str] = set()
    frontend_changed = False
    for path in paths:
        normalized = path.replace("\\", "/")
        frontend_changed = frontend_changed or normalized.startswith(
            ("frontend/apps/web/", "frontend/packages/ui/")
        )
        for rule in RULES:
            if any(fragment in normalized for fragment in rule.fragments):
                selected.update(rule.targets)
    if frontend_changed and not selected:
        selected.add(FALLBACK_TARGET)
    targets = sorted(selected)
    if any(part in target for target in targets for part in FORBIDDEN_DEVELOPMENT_TARGET_PARTS):
        raise RuntimeError("development validation selected a candidate-only target")
    return targets


def watched_files() -> list[Path]:
    files: set[Path] = set()
    for relative in WATCH_ROOTS:
        source = ROOT / relative
        if source.is_file():
            files.add(source)
        elif source.is_dir():
            files.update(path for path in source.rglob("*") if path.is_file())
    return sorted(files)


def content_snapshot() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in watched_files():
        relative = path.relative_to(ROOT).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def _git_paths(root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [value.decode("utf-8") for value in result.stdout.split(b"\0") if value]


def worktree_changed_paths(root: Path = ROOT, base_ref: str = "origin/main") -> list[str]:
    merge_base = subprocess.run(
        ["git", "-C", str(root), "merge-base", "HEAD", base_ref],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    paths = set(_git_paths(root, "diff", "--no-renames", "--name-only", "-z", f"{merge_base}..HEAD"))
    paths.update(_git_paths(root, "diff", "--no-renames", "--name-only", "-z"))
    paths.update(_git_paths(root, "diff", "--no-renames", "--cached", "--name-only", "-z"))
    paths.update(_git_paths(root, "ls-files", "--others", "--exclude-standard", "-z"))
    return sorted(paths)


def iteration_plan(root: Path = ROOT) -> int:
    selected = resolve_run(root)
    if selected is None:
        raise RunError("no registered run; select/register one goal before iteration")
    relative, run = selected
    if run["status"] in ("completed", "superseded"):
        raise RunError("selected run is closed; register/select the next task")
    checks = {key: evaluate(root, run, key) for key in run["checks"]}
    return print_plan(delta_paths(root, run["baseline_sha"]), source=relative, checks=checks)


def print_plan(paths: list[str], *, source: str = "explicit_paths", checks: dict | None = None) -> int:
    targets = set(select_targets(paths))
    grouped: dict[str, list[str]] = {}
    for check in (checks or {}).values():
        grouped.setdefault(check["target"], []).append(check["status"])
    reusable = {target for target, states in grouped.items() if all(state == "reusable" for state in states)}
    blocked = {target for target, states in grouped.items() if "failed" in states}
    targets.update(grouped)
    targets.difference_update(reusable | blocked)
    unmapped_paths = [
        path
        for path in paths
        if not select_targets([path])
        and not path.replace("\\", "/").startswith(NON_SOURCE_PATH_PREFIXES)
    ]
    payload = {
        "schemaVersion": 1,
        "scopeSource": source,
        "recordedChecks": checks or {},
        "mode": "development_incremental_plan",
        "status": "recommendation_only",
        "changedPathCount": len(paths),
        "targets": sorted(targets),
        "reusedTargets": sorted(reusable),
        "blockedTargets": sorted(blocked),
        "unmappedPathCount": len(unmapped_paths),
        "unmappedPaths": unmapped_paths,
        "candidateEvidence": False,
        "testsRun": False,
        "manualNonZeroL2Required": bool(unmapped_paths),
    }
    print(f"[frontend.dev.incremental.plan] {json.dumps(payload, sort_keys=True)}")
    return 0


def write_state(*, status: str, paths: list[str], targets: list[str], returncode: int | None) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": 1,
        "mode": "development_incremental",
        "status": status,
        "changedPaths": paths,
        "targets": targets,
        "returncode": returncode,
        "candidateEvidence": False,
        "heavyValidationIncluded": False,
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_targets(paths: list[str]) -> int:
    targets = select_targets(paths)
    if not targets:
        write_state(status="no_relevant_change", paths=paths, targets=[], returncode=0)
        print("[frontend.dev.incremental] no relevant frontend validation")
        return 0
    print(f"[frontend.dev.incremental] paths={len(paths)} targets={','.join(targets)}", flush=True)
    write_state(status="running", paths=paths, targets=targets, returncode=None)
    result = subprocess.run(["make", "--no-print-directory", *targets], cwd=ROOT, check=False)
    status = "passed" if result.returncode == 0 else "failed"
    write_state(status=status, paths=paths, targets=targets, returncode=result.returncode)
    print(f"[frontend.dev.incremental] {status.upper()} returncode={result.returncode}")
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="watch source content and validate after each settled batch")
    parser.add_argument(
        "--plan-worktree",
        action="store_true",
        help="recommend affected frontend L2 targets without running them",
    )
    parser.add_argument("--plan-branch", action="store_true", help="explicit whole-branch comparison for review; not daily continuation")
    parser.add_argument("--path", action="append", default=[], help="validate an explicit repository-relative path")
    parser.add_argument("--interval", type=float, default=0.75)
    parser.add_argument("--debounce", type=float, default=0.8)
    return parser.parse_args()


def watch(interval: float, debounce: float) -> int:
    previous = content_snapshot()
    write_state(status="watching", paths=[], targets=[], returncode=None)
    print("[frontend.dev.watch] watching; candidate build/browser/fingerprint are excluded", flush=True)
    try:
        while True:
            time.sleep(interval)
            current = content_snapshot()
            paths = changed_paths(previous, current)
            if not paths:
                continue
            time.sleep(debounce)
            settled = content_snapshot()
            paths = changed_paths(previous, settled)
            run_targets(paths)
            previous = settled
    except KeyboardInterrupt:
        write_state(status="stopped", paths=[], targets=[], returncode=0)
        print("[frontend.dev.watch] stopped")
        return 0


def main() -> int:
    args = parse_args()
    if sum((args.watch, args.plan_worktree, args.plan_branch)) > 1:
        raise SystemExit("--watch, --plan-worktree and --plan-branch are mutually exclusive")
    if args.plan_branch:
        if args.path:
            raise SystemExit("--plan-branch does not accept --path")
        return print_plan(worktree_changed_paths(), source="explicit_whole_branch_review")
    if args.watch:
        return watch(args.interval, args.debounce)
    if args.plan_worktree:
        if args.path:
            raise SystemExit("--plan-worktree does not accept --path")
        try:
            return iteration_plan()
        except RunError as exc:
            raise SystemExit(f"run reconciliation required: {exc}") from exc
    if not args.path:
        raise SystemExit("at least one --path is required outside --watch mode")
    return run_targets(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
