#!/usr/bin/env python3
"""Lock the repository's baseline-backed iteration execution policy."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MARKER = "BASELINE_ITERATION_EXECUTION_POLICY=v1"

DOCUMENT_REQUIREMENTS = {
    Path("AGENTS.md"): (
        "complete tracked+untracked fingerprint",
        "zero tests is a failure",
        "full immutable Git blob SHA",
        "Shared acceptance database mutations are serialized",
        "one independently acceptable product result (PFL)",
        "All five conditions are mandatory",
        "At most two active worktrees are allowed",
        "Layered Validation Efficiency (Hard Lock)",
        "Never run a broad gate to discover a defect that a cheaper owning-layer check can determine",
        "Do not rerun unchanged passing layers for reassurance",
        "resume from the earliest invalidated layer",
        "Do not retry an unchanged failure",
        "the full required matrix runs once at the frozen delivery head",
        "make ci.local.iteration",
        "make ci.local.quick` is reserved for a clean frozen delivery HEAD",
    ),
    Path("docs/ops/codex_execution_allowlist.md"): (
        "禁止新增或派生 Compose project",
        "personal_data_false_positives.json",
        "codex_workspace_execution_rules.md",
    ),
    Path("docs/ops/codex_workspace_execution_rules.md"): (
        "任何 `0 tests`",
        "baseline_sha..HEAD",
        "禁止目录级、通配符或测试树整体豁免",
        "禁止直接调用 `docker compose`",
        "acceptance 凭据不得注入 dev/test project",
        "`make pr.push`",
        "以产品结果组织工作树（Hard Lock）",
        "同时活跃工作树硬上限为两个",
        "同一 PFL 内的 P0/P1 修改继续留在同一产品工作树",
        "高效分层验证红线（Hard Lock）",
        "不得先跑昂贵门禁再回头定位便宜层缺陷",
        "满足条件时禁止为了“更放心”机械重跑",
        "失效只向下游传播",
        "同因失败不得原样重试",
        "完整发布门禁只在冻结 delivery HEAD 上集中执行一次",
        "日志不完整或测试数未知不能判定通过",
        "本地入口分车道",
        "make ci.local.iteration",
        "make ci.local.quick` 仅在",
    ),
}

MAKE_TARGET_REQUIREMENTS = {
    Path("make/codex.mk"): (
        "workspace.worktree.create",
        "pr.push",
    ),
    Path("make/runtime_ops.mk"): (
        "acceptance.module.upgrade",
        "acceptance.frontend.fixture",
        "acceptance.frontend.release_snapshot",
    ),
    Path("make/dev.mk"): (
        "backend.acceptance.up",
        "frontend.acceptance.up",
    ),
    Path("make/ci.mk"): (
        "ci.generated_reports.guard",
    ),
}

ITERATION_TARGET = "ci.local.iteration"
ITERATION_REQUIRED = (
    "guard.prod.forbid",
    "verify.baseline.iteration.execution.policy",
    "git diff --check",
    "git status --porcelain=v1 --untracked-files=all",
    "change_state=clean",
    "change_state=dirty",
    "scope=unclassified_by_design",
    "coverage=L1_only",
    "receipt=none",
    "next=risk_selected_non_zero_L2_targets_required",
)
ITERATION_FORBIDDEN = (
    "ci.local.quick",
    "verify.contract.page_v1_zero_residue.guard",
    "security.legacy_credential_guard",
    "architecture.complexity_baseline_lock",
    "security.secrets.scan",
    "security.personal_data_scan",
    "verify.repository.clean_history",
    "verify.frontend.build",
    "verify.frontend.typecheck.strict",
    "acceptance",
    "browser",
)

QUICK_TARGET = "ci.local.quick.run"
QUICK_DIRECT_REQUIRED = (
    "verify.unified_page_contract.v2",
    "verify.frontend.lint.src",
)
QUICK_DIRECT_FORBIDDEN = ("verify.frontend.typecheck.strict",)
QUICK_FORBIDDEN_DIRECT_COMMANDS = (
    "pnpm_exec.sh -C frontend/apps/web lint:src",
    "pnpm_exec.sh -C frontend/apps/web typecheck:strict",
)

TYPECHECK_CHAIN = (
    ("verify.unified_page_contract.v2", "verify.unified_page_contract.v2.frontend_static"),
    ("verify.unified_page_contract.v2.frontend_static", "verify.frontend.typecheck.strict"),
)
TYPECHECK_TARGET = "verify.frontend.typecheck.strict"
TYPECHECK_COMMAND = "pnpm_exec.sh -C frontend/apps/web typecheck:strict"


def _target_declared(text: str, target: str) -> bool:
    return bool(re.search(rf"^(?:\.PHONY:\s+.*\b{re.escape(target)}\b.*|{re.escape(target)}\s*:)", text, re.MULTILINE))


def _target_block(text: str, target: str) -> str:
    match = re.search(
        rf"^{re.escape(target)}\s*:[^\n]*(?:\n\t[^\n]*)*",
        text,
        re.MULTILINE,
    )
    return match.group(0) if match else ""


def _target_dependencies(text: str, target: str) -> tuple[str, ...]:
    match = re.search(rf"^{re.escape(target)}\s*:\s*([^\n]*)", text, re.MULTILINE)
    return tuple(match.group(1).split()) if match else ()


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative, required_fragments in DOCUMENT_REQUIREMENTS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"{relative}: missing policy document")
            continue
        text = path.read_text(encoding="utf-8")
        if text.count(MARKER) != 1:
            errors.append(f"{relative}: policy marker must appear exactly once")
        for fragment in required_fragments:
            if fragment not in text:
                errors.append(f"{relative}: missing locked rule {fragment!r}")

    for relative, targets in MAKE_TARGET_REQUIREMENTS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"{relative}: missing Make authority")
            continue
        text = path.read_text(encoding="utf-8")
        for target in targets:
            if not _target_declared(text, target):
                errors.append(f"{relative}: authoritative target missing: {target}")

    ci_make = root / "make/ci.mk"
    if ci_make.is_file():
        ci_text = ci_make.read_text(encoding="utf-8")
        block = _target_block(ci_text, ITERATION_TARGET)
        if not block:
            errors.append(f"make/ci.mk: authoritative target missing: {ITERATION_TARGET}")
        else:
            for fragment in ITERATION_REQUIRED:
                if fragment not in block:
                    errors.append(
                        f"make/ci.mk: {ITERATION_TARGET} missing lightweight contract {fragment!r}"
                    )
            for fragment in ITERATION_FORBIDDEN:
                if fragment in block:
                    errors.append(
                        f"make/ci.mk: {ITERATION_TARGET} includes forbidden broad gate {fragment!r}"
                    )
        quick_block = _target_block(ci_text, QUICK_TARGET)
        if not quick_block:
            errors.append(f"make/ci.mk: authoritative target missing: {QUICK_TARGET}")
        else:
            quick_dependencies = _target_dependencies(ci_text, QUICK_TARGET)
            for fragment in QUICK_DIRECT_REQUIRED:
                if fragment not in quick_dependencies:
                    errors.append(
                        f"make/ci.mk: {QUICK_TARGET} missing deduplicated prerequisite {fragment!r}"
                    )
            for fragment in QUICK_DIRECT_FORBIDDEN:
                if fragment in quick_dependencies:
                    errors.append(
                        f"make/ci.mk: {QUICK_TARGET} duplicates transitive prerequisite {fragment!r}"
                    )
            for fragment in QUICK_FORBIDDEN_DIRECT_COMMANDS:
                if fragment in quick_block:
                    errors.append(
                        f"make/ci.mk: {QUICK_TARGET} repeats prerequisite command {fragment!r}"
                    )
        for owner, dependency in TYPECHECK_CHAIN:
            if dependency not in _target_dependencies(ci_text, owner):
                errors.append(
                    f"make/ci.mk: strict typecheck chain broken: {owner} -> {dependency}"
                )
        frontend_make = root / "make/frontend.mk"
        if not frontend_make.is_file():
            errors.append("make/frontend.mk: missing Make authority")
        else:
            typecheck_block = _target_block(
                frontend_make.read_text(encoding="utf-8"),
                TYPECHECK_TARGET,
            )
            if typecheck_block.count(TYPECHECK_COMMAND) != 1:
                errors.append(
                    f"make/frontend.mk: {TYPECHECK_TARGET} must invoke strict typecheck exactly once"
                )
    return errors


def main() -> int:
    errors = validate(ROOT)
    if errors:
        print("[baseline_iteration_execution_policy_guard] FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "[baseline_iteration_execution_policy_guard] PASS "
        f"policy={MARKER} documents={len(DOCUMENT_REQUIREMENTS)} "
        f"make_authorities={sum(len(items) for items in MAKE_TARGET_REQUIREMENTS.values())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
