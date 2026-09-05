#!/usr/bin/env python3
"""ADR-002 图表引擎引入纪律守卫（G6.1）。

钉死三件事：
1. 精确锁版：frontend/apps/web 生产依赖 echarts 必须是精确版本（无 ^/~ 前缀），
   与已批准版本 6.1.0 一致；patch 升级须过门禁（改版本即改本守卫基线）。
2. tree-shakeable 引入：禁止 `from 'echarts'` 全量引入；只允许
   echarts/core、echarts/charts、echarts/components、echarts/renderers、
   echarts/features、echarts/types 子路径（ADR-002 条件 1）。
3. 单一 CanvasRenderer：renderers 子路径只允许 CanvasRenderer，
   禁止 SVGRenderer（ADR-002 条件 1「单一 CanvasRenderer」）。

范围：frontend/apps/web/src 与 frontend/packages/*/src（共享层同样
不得全量引入）。违反任一条即 FAIL。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_PACKAGE = ROOT / "frontend/apps/web/package.json"

APPROVED_ECHARTS_VERSION = "6.1.0"

ALLOWED_SUBPATHS = (
    "echarts/core",
    "echarts/charts",
    "echarts/components",
    "echarts/renderers",
    "echarts/features",
    "echarts/types",
)

# 全量引入：from 'echarts' / import 'echarts'（含双引号变体），
# 但不含合法子路径（echarts/xxx）。
full_import = re.compile(r"""(?:from\s+|import\s*\(\s*|import\s+)['"]echarts['"]""")
any_echarts_import = re.compile(r"""(?:from\s+|import\s*\(\s*|import\s+)['"]echarts[/'"]""")
renderer_import = re.compile(
    r"""import\s*\{([^}]*)\}\s*from\s*['"]echarts/renderers['"]"""
)


def _source_roots():
    yield ROOT / "frontend/apps/web/src"
    for pkg in (ROOT / "frontend/packages").glob("*/src"):
        if pkg.is_dir():
            yield pkg


def _iter_files(root: Path):
    yield from root.rglob("*.ts")
    yield from root.rglob("*.vue")
    yield from root.rglob("*.mjs")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"[verify.frontend.chart_engine.guard] FAIL {message}")


def main() -> None:
    # 1. 精确锁版
    package = json.loads(WEB_PACKAGE.read_text(encoding="utf-8"))
    version = str(package.get("dependencies", {}).get("echarts") or "")
    require(
        version == APPROVED_ECHARTS_VERSION,
        f"echarts must be exact-pinned to {APPROVED_ECHARTS_VERSION} in web "
        f"dependencies (found {version!r}; patch bump requires gate + guard baseline update)",
    )

    # 2/3. tree-shakeable + 单一 CanvasRenderer
    offenders: list[str] = []
    renderer_offenders: list[str] = []
    for root in _source_roots():
        for path in _iter_files(root):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = str(path.relative_to(ROOT))
            for match in any_echarts_import.finditer(text):
                snippet = match.group(0)
                if full_import.search(snippet):
                    offenders.append(f"{rel}: {snippet.strip()}")
            for match in renderer_import.finditer(text):
                names = [n.strip() for n in match.group(1).split(",") if n.strip()]
                bad = [n for n in names if n != "CanvasRenderer"]
                if bad:
                    renderer_offenders.append(f"{rel}: {bad}")

    require(
        not offenders,
        f"full echarts imports are forbidden (ADR-002 condition 1, "
        f"use echarts/core + on-demand subpaths): {offenders}",
    )
    require(
        not renderer_offenders,
        f"only CanvasRenderer is allowed from echarts/renderers "
        f"(ADR-002 condition 1): {renderer_offenders}",
    )
    print(
        "[verify.frontend.chart_engine.guard] PASS "
        f"echarts@{APPROVED_ECHARTS_VERSION} exact-pinned, tree-shakeable imports clean"
    )


if __name__ == "__main__":
    main()
