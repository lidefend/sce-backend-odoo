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
)

# 全量引入：from 'echarts' / import 'echarts'（含双引号变体），
# 但不含合法子路径（echarts/xxx）。
echarts_import = re.compile(r"""(?:from\s+|import\s*\(\s*|import\s+)['"](?P<module>echarts(?:/[^'"]*)?)['"]""")


def _source_roots(root: Path):
    yield root / "frontend/apps/web/src"
    for pkg in (root / "frontend/packages").glob("*/src"):
        if pkg.is_dir():
            yield pkg


def _iter_files(root: Path):
    yield from root.rglob("*.ts")
    yield from root.rglob("*.vue")
    yield from root.rglob("*.mjs")


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    # 1. 精确锁版
    package_path = root / WEB_PACKAGE.relative_to(ROOT)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    version = str(package.get("dependencies", {}).get("echarts") or "")
    if version != APPROVED_ECHARTS_VERSION:
        failures.append(f"echarts must be exact-pinned to {APPROVED_ECHARTS_VERSION} (found {version!r})")

    installed_package = root / f"frontend/node_modules/.pnpm/echarts@{version}/node_modules/echarts/package.json"
    if not installed_package.is_file():
        failures.append(f"installed echarts package metadata missing for {version}")
    else:
        exports = json.loads(installed_package.read_text(encoding="utf-8")).get("exports", {})
        for module in ALLOWED_SUBPATHS:
            if f"./{module.removeprefix('echarts/')}" not in exports:
                failures.append(f"installed echarts {version} does not export approved public entrypoint {module}")

    # 2/3. tree-shakeable + 单一 CanvasRenderer
    for source_root in _source_roots(root):
        for path in _iter_files(source_root):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = str(path.relative_to(root))
            modules = [match.group("module") for match in echarts_import.finditer(text)]
            for module in modules:
                if module == "echarts":
                    failures.append(f"full echarts import is forbidden: {rel}")
                elif module not in ALLOWED_SUBPATHS:
                    failures.append(f"echarts import is not an approved public entrypoint: {rel}: {module}")
            if "echarts/renderers" in modules:
                if "CanvasRenderer" not in text:
                    failures.append(f"renderer entrypoint must register CanvasRenderer: {rel}")
                if "SVGRenderer" in text:
                    failures.append(f"SVGRenderer is forbidden by the single-renderer contract: {rel}")
    return failures


def main() -> None:
    failures = validate()
    if failures:
        raise SystemExit("[verify.frontend.chart_engine.guard] FAIL " + "; ".join(failures))
    print(
        "[verify.frontend.chart_engine.guard] PASS "
        f"echarts@{APPROVED_ECHARTS_VERSION} exact-pinned, tree-shakeable imports clean"
    )


if __name__ == "__main__":
    main()
