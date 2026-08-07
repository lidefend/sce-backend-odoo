#!/usr/bin/env python3
"""Inventory industry knowledge embedded in the production custom frontend.

The frontend is a generic contract renderer. Business-domain facts may occur in
test fixtures and browser acceptance manifests, but production sources must not
select structure or behavior from industry identifiers. During M0 the audit
emits a truthful report without approving a baseline. Set
``FRONTEND_INDUSTRY_AGNOSTIC_ENFORCE=1`` only when the inventory has reached
zero; that mode is intended for the release gate after convergence.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "frontend/apps/web/src"
REPORT = Path(
    os.environ.get(
        "FRONTEND_INDUSTRY_AGNOSTIC_REPORT",
        ROOT / "artifacts/frontend-product-stable-baseline/industry-knowledge-audit.json",
    )
)
ENFORCE = os.environ.get("FRONTEND_INDUSTRY_AGNOSTIC_ENFORCE", "0") == "1"


@dataclass(frozen=True)
class Finding:
    rule: str
    file: str
    line: int
    excerpt: str
    reason: str


RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "business_context_identifier",
        re.compile(
            r"\b(?:projectContext|project_context|projectScopePolicy|project_scope_policy|"
            r"financialWorkspace|financial_workspace|FinancialRelationshipWorkspace|"
            r"ProjectManagement|ProjectsIntake|ProjectMetric|paymentRequest|payment_request)\b"
        ),
        "生产前端不得拥有项目、财务或付款等业务上下文标识。",
    ),
    (
        "industry_model_or_xmlid",
        re.compile(
            r"['\"`][^'\"`\r\n]*(?:smart_construction|project\.project|sc\.(?:project|contract|payment|settlement)|"
            r"payment[._-](?:request|application)|construction[._-]|settlement[._-])[^'\"`\r\n]*['\"`]",
            re.IGNORECASE,
        ),
        "生产前端不得识别行业模块、业务模型或行业 XML ID。",
    ),
    (
        "industry_literal",
        re.compile(r"['\"`]([^'\"`\r\n]*(?:项目|合同|施工|付款|结算|财务|经营|材料|供应商|客户)[^'\"`\r\n]*)['\"`]"),
        "行业标题、说明和回退文案必须来自后端契约。",
    ),
    (
        "industry_regex_inference",
        re.compile(r"/(?:[^/\\\r\n]|\\.)*(?:项目|合同|施工|付款|结算|财务|经营|材料|供应商|客户)(?:[^/\\\r\n]|\\.)*/[a-z]*"),
        "生产前端不得通过行业词汇正则推断字段语义或交互。",
    ),
    (
        "industry_text_anywhere",
        re.compile(r"项目|合同|施工|付款|结算|财务|经营|材料|供应商|客户"),
        "生产前端源码不得携带行业文案；展示文案必须由后端契约提供。",
    ),
    (
        "industry_behavior_identifier",
        re.compile(
            r"\b(?:projectCreateMode|projectIntake|projectId|selectedProject|resolveProject|"
            r"open_projects?|project_code|contract_no|project_query|record_project_field)\b|"
            r"project\.management|projects\.dashboard"
        ),
        "生产前端不得保留按行业对象命名的分支、适配器或上下文参数。",
    ),
    (
        "business_field_inference",
        re.compile(
            r"\b(?:project_id|contract_id|payment_id|settlement_id|project_manager_id|project_owner_id)\b"
        ),
        "生产前端不得按行业字段名推断布局、上下文或行为。",
    ),
    (
        "industry_route_special_case",
        re.compile(r"['\"`](?:projects-intake|project-management-dashboard|/pm/dashboard|/s/projects\.intake)['\"`]"),
        "行业场景必须走通用 scene/action/record 路由。",
    ),
)

FORBIDDEN_ASSETS = {
    "frontend/apps/web/src/api/paymentRequest.ts": "业务动作必须由通用 action capability 契约执行。",
    "frontend/apps/web/src/app/financialWorkspaceContract.ts": "财务详情必须归一为通用页面契约。",
    "frontend/apps/web/src/components/business/FinancialRelationshipWorkspace.vue": "生产前端不得维护财务专用详情模板。",
    "frontend/apps/web/src/components/role-home/ContractRoleHome.vue": "首页必须由通用角色首页契约渲染。",
    "frontend/apps/web/src/composables/shared-surface/useContractRoleHome.ts": "首页 composable 不得携带业务产品命名或推断。",
    "frontend/apps/web/src/views/ProjectManagementDashboardView.vue": "行业工作台必须由通用场景契约装配。",
    "frontend/apps/web/src/views/ProjectsIntakeView.vue": "行业新建入口必须由通用场景/记录契约装配。",
    "frontend/apps/web/src/app/action_runtime/useActionViewProjectMetricRuntime.ts": "列表指标必须消费通用 metric 契约。",
    "frontend/apps/web/src/app/runtime/actionViewProjectScopeRuntime.ts": "作用域与汇总事实必须由后端契约裁决。",
    "frontend/apps/web/src/pages/contractForm/useProjectContextChangeRuntime.ts": "通用表单不得维护项目上下文特例。",
    "frontend/apps/web/src/pages/contractForm/financialFormScope.ts": "通用表单不得维护财务作用域特例。",
}


def source_files() -> list[Path]:
    return sorted(
        path
        for path in SOURCE_ROOT.rglob("*")
        if path.is_file() and path.suffix in {".ts", ".vue", ".css"} and not path.name.endswith(".d.ts")
    )


def line_excerpt(text: str, line: int) -> str:
    rows = text.splitlines()
    return rows[line - 1].strip()[:240] if 0 < line <= len(rows) else ""


def main() -> int:
    findings: list[Finding] = []
    for relative, reason in FORBIDDEN_ASSETS.items():
        if (ROOT / relative).is_file():
            findings.append(Finding("industry_asset", relative, 1, Path(relative).name, reason))

    for path in source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(ROOT).as_posix()
        for rule, pattern, reason in RULES:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(Finding(rule, relative, line, line_excerpt(text, line), reason))

    findings = sorted(set(findings), key=lambda item: (item.file, item.line, item.rule, item.excerpt))
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.rule] = counts.get(finding.rule, 0) + 1

    report = {
        "schema_version": "sce.frontend_industry_agnostic_audit.v1",
        "source_root": SOURCE_ROOT.relative_to(ROOT).as_posix(),
        "files_scanned": len(source_files()),
        "enforced": ENFORCE,
        "finding_count": len(findings),
        "counts": counts,
        "findings": [asdict(item) for item in findings],
        "policy": {
            "frontend_role": "generic_contract_renderer",
            "target": "zero",
            "baseline_approval": "forbidden",
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = "PASS" if not findings else ("FAIL" if ENFORCE else "AUDIT")
    print(f"[frontend_industry_agnostic_audit] {status} files={len(source_files())} findings={len(findings)} report={REPORT}")
    for rule, count in sorted(counts.items()):
        print(f"- {rule}: {count}")
    return 1 if ENFORCE and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
