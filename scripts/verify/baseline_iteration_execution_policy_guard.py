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


def _target_declared(text: str, target: str) -> bool:
    return bool(re.search(rf"^(?:\.PHONY:\s+.*\b{re.escape(target)}\b.*|{re.escape(target)}\s*:)", text, re.MULTILINE))


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
