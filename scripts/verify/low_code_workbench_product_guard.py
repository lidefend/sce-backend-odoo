#!/usr/bin/env python3
"""Guard the LC-PRO-01 workbench product and safe-open contract."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SURFACE_ROOT = ROOT / "frontend/apps/web/src/views/businessConfigSurface"
ROOT_VIEW = ROOT / "frontend/apps/web/src/views/BusinessConfigSurfaceView.vue"
FORMATTERS = SURFACE_ROOT / "formatters.ts"
# Side-car templates carry the workbench DOM, so they are scanned too.
FILES = [
    ROOT_VIEW,
    *sorted(SURFACE_ROOT.glob("*.vue")),
    *sorted(SURFACE_ROOT.glob("*.ts")),
    *sorted(SURFACE_ROOT.glob("*.html")),
]
FORBIDDEN_DEFAULT_LANGUAGE = ("保存并预览", "预览页面")
# Names the configuration contract already declares (sections[].label,
# boundary_labels). A view that re-declares them keeps a second vocabulary that
# can drift from the contract, and the browser probe then verifies the copy
# instead of the contract.
CONTRACT_DECLARED_NAMES = (
    "表单字段与布局",
    "列表与搜索",
    "菜单入口",
    "审批规则",
    "仅页面设置",
    "业务默认配置",
    "菜单显示规则",
    "版本记录",
    "覆盖检查",
    "行业业务规则",
    "非偏好来源",
    "非偏好配置",
)
FORBIDDEN_SHADOW_SYMBOLS = ("sectionDisplayLabel", "BUSINESS_FIELD_LABEL_OVERRIDES")
SECTION_TITLE_BINDING = "section-display-label"
REQUIRED_TOKENS = (
    "openCurrentEffectivePage",
    "inspectListSearchDraft",
    "inspectAnalysisDraft",
    "当前版本不支持未发布效果预览",
    "BusinessConfigContextBar",
    "BusinessConfigImpactDialog",
    "ScButton",
    "ScStatusBadge",
)
LAST_AST_REPORT: dict = {}


def validate(sources: dict[Path, str]) -> list[str]:
    global LAST_AST_REPORT
    errors: list[str] = []
    combined = "\n".join(sources.values())
    for phrase in FORBIDDEN_DEFAULT_LANGUAGE:
        if phrase in combined:
            errors.append(f"default workbench still exposes unsafe preview wording: {phrase}")
    for token in REQUIRED_TOKENS:
        if token not in combined:
            errors.append(f"workbench product contract missing token: {token}")
    ast_guard = subprocess.run(
        ["node", str(ROOT / "scripts/verify/low_code_publish_boundary_guard.mjs")],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    ast_report = json.loads((ast_guard.stdout or "{}").splitlines()[-1])
    LAST_AST_REPORT = ast_report
    errors.extend(str(item) for item in (ast_report.get("errors") or []))
    if ast_guard.returncode:
        errors.append("AST publish boundary guard failed")
    sc_usage = len(re.findall(r"<Sc[A-Z][A-Za-z0-9]*\b", combined))
    if sc_usage < 20:
        errors.append(f"design-system usage regressed below LC-PRO-01 floor: {sc_usage} < 20")
    if ROOT_VIEW in sources and len(sources[ROOT_VIEW].splitlines()) > 600:
        errors.append("BusinessConfigSurfaceView.vue exceeds route assembly limit (600 lines)")
    formatters_text = sources.get(FORMATTERS, "")
    for symbol in FORBIDDEN_SHADOW_SYMBOLS:
        if symbol in formatters_text:
            errors.append(f"workbench re-declared a contract-declared name map: {symbol}")
    for name in CONTRACT_DECLARED_NAMES:
        if f"'{name}'" in formatters_text or f'"{name}"' in formatters_text:
            errors.append(f"workbench re-declared a contract-declared name literal: {name}")
    for path, text in sources.items():
        if SECTION_TITLE_BINDING in text:
            errors.append(f"{path.name} still binds a view-owned section title prop")
    return errors


def main() -> int:
    sources = {path: path.read_text(encoding="utf-8") for path in FILES if path.is_file()}
    errors = validate(sources)
    negative_sources = dict(sources)
    negative_sources[ROOT_VIEW] = negative_sources.get(ROOT_VIEW, "") + "\n保存并预览\n"
    negative_self_test = bool(validate(negative_sources))
    if not negative_self_test:
        errors.append("negative self-test accepted deliberately unsafe preview wording")
    shadow_sources = dict(sources)
    shadow_sources[FORMATTERS] = shadow_sources.get(FORMATTERS, "") + "\nexport function sectionDisplayLabel() { return '菜单入口'; }\n"
    shadow_self_test = bool(validate(shadow_sources))
    if not shadow_self_test:
        errors.append("negative self-test accepted a re-declared contract section name")
    binding_sources = dict(sources)
    binding_sources[ROOT_VIEW] = binding_sources.get(ROOT_VIEW, "") + '\n      :section-display-label="sectionDisplayLabel"\n'
    binding_self_test = bool(validate(binding_sources))
    if not binding_self_test:
        errors.append("negative self-test accepted a view-owned section title prop")
    combined = "\n".join(sources.values())
    report = {
        "guard": "low_code_workbench_product_guard",
        "scanned_files": len(sources),
        "component_files": sum(path.suffix == ".vue" for path in sources),
        "design_system_usages": len(re.findall(r"<Sc[A-Z][A-Za-z0-9]*\b", combined)),
        "raw_controls": len(re.findall(r"<(?:button|input|select|textarea)\b", combined)),
        "assertions": (
            len(FORBIDDEN_DEFAULT_LANGUAGE)
            + len(REQUIRED_TOKENS)
            + len(CONTRACT_DECLARED_NAMES)
            + len(FORBIDDEN_SHADOW_SYMBOLS)
            + 5
        ),
        "negative_self_test": "pass" if negative_self_test else "fail",
        "name_authority_self_test": "pass" if shadow_self_test and binding_self_test else "fail",
        "publish_boundary": LAST_AST_REPORT,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print(f"[low_code_workbench_product_guard] {'FAIL' if errors else 'PASS'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
