#!/usr/bin/env python3
"""Build the product-owner review of all released handling surfaces.

The output is a design contract, not runtime navigation. It organizes every
released menu exactly once into a user-understandable business handling loop,
while preserving the locked workbench-plus-ten-center center skeleton.
"""
from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "addons/smart_construction_core"
SOURCE_PATH = MODULE / "data/product_menu_source.json"
CENTER_PATH = ROOT / "config/product_primary_center_baseline_v1.json"
JSON_OUTPUT = ROOT / "config/product_scenario_organization_v1.json"
MARKDOWN_OUTPUT = ROOT / "docs/product/product_scenario_organization_v1.md"
SURFACE_OUTPUT = MODULE / "data/scenario_product_surface.json"
DIRECT_PLATFORM_PAGES = (
    ("smart_construction_core.menu_sc_workspace_home", "workbench_direct"),
    ("smart_construction_core.menu_sc_my_work", "workbench_direct"),
    ("smart_construction_core.menu_sc_operating_metrics_project", "workbench_direct"),
    ("smart_construction_core.menu_sc_project_kanban", "workbench_direct"),
    ("smart_construction_core.menu_sc_workbench_my_todo_fact", "workbench_direct"),
    ("smart_construction_core.menu_sc_product_message_notification_v1", "workbench_direct"),
    ("smart_construction_core.menu_sc_business_config_workbench", "configuration"),
    ("smart_construction_core.menu_sc_approval_policy", "configuration"),
    ("smart_construction_core.menu_ui_form_field_policy_business_config", "configuration"),
    ("smart_construction_core.menu_ui_menu_config_policy_business_config", "configuration"),
    ("smart_construction_core.menu_sc_enterprise_initialization", "platform_initialization"),
    ("smart_construction_core.menu_sc_product_data_permission_v1", "platform_initialization"),
    ("smart_construction_core.menu_sc_product_scenario_business_config", "platform_initialization"),
    ("smart_construction_core.menu_sc_product_system_parameter_v1", "platform_initialization"),
    ("smart_construction_core.menu_sc_product_numbering_rule_v1", "platform_initialization"),
    ("smart_construction_core.menu_sc_runtime_user_management", "platform_initialization"),
)
APPROVAL_STATUS = "APPROVED_FOR_IMPLEMENTATION"
APPROVAL_DATE = "2026-11-20"

MASTER_DATA_MENU_XMLIDS = frozenset({
    "smart_construction_core.menu_sc_organization_department",
    "smart_construction_core.menu_sc_product_job_management_v1",
    "smart_construction_core.menu_sc_runtime_user_management",
    "smart_construction_core.menu_sc_business_config_workbench",
    "smart_construction_core.menu_sc_approval_policy",
    "smart_construction_core.menu_ui_form_field_policy_business_config",
    "smart_construction_core.menu_ui_menu_config_policy_business_config",
    "smart_construction_core.menu_sc_product_data_permission_v1",
    "smart_construction_core.menu_sc_product_system_parameter_v1",
    "smart_construction_core.menu_sc_product_numbering_rule_v1",
    "smart_construction_core.menu_sc_customer_partner",
    "smart_construction_core.menu_sc_supplier_partner",
    "smart_construction_core.menu_sc_product_partner_blacklist_v1",
    "account.menu_action_account_form",
    "smart_construction_core.menu_sc_account_journal_foundation",
    "smart_construction_core.menu_sc_analytic_account_foundation",
    "smart_construction_core.menu_sc_analytic_distribution_foundation",
    "smart_construction_core.menu_sc_certificate_registration",
    "smart_construction_core.menu_sc_product_office_asset_v1",
    "smart_construction_core.menu_sc_product_policy_document_v1",
})
HANDLE_MODES = frozenset({"先办", "办理", "并列", "并列选择", "辅助办理"})


def _load_product_source():
    spec = importlib.util.spec_from_file_location(
        "scenario_organization_product_menu_source",
        MODULE / "services/product_menu_source.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("product menu source is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_source()


def page(menu_xmlid, purpose, mode="办理"):
    return {"menu_xmlid": menu_xmlid, "purpose": purpose, "mode": mode}


def scenario(
    key,
    name,
    owner_center,
    objective,
    roles,
    prerequisites,
    result_objects,
    result,
    pages,
    *,
    dependencies=(),
    next_steps=(),
    exclusions=(),
    context="当前公司",
    references=(),
):
    return {
        "key": key,
        "name": name,
        "owner_center": owner_center,
        "objective": objective,
        "roles": list(roles),
        "prerequisites": list(prerequisites),
        "result_objects": list(result_objects),
        "result": result,
        "pages": list(pages),
        "dependencies": list(dependencies),
        "next_steps": list(next_steps),
        "exclusions": list(exclusions),
        "context": context,
        "references": list(references),
    }


SCENARIOS = [
    scenario(
        "work.my_queue",
        "处理我的工作与消息",
        "workspace.home.workbench",
        "让当前用户从自己的角色首页发现并处理待办、提醒和消息。",
        ["all_authenticated"],
        ["已登录且处于有效企业上下文", "角色工作空间已发布"],
        [],
        "用户进入具体业务事项，或完成消息查看。",
        [
            page("smart_construction_core.menu_sc_workspace_home", "查看当前角色的首页入口和工作提示。", "先办"),
            page("smart_construction_core.menu_sc_my_work", "查看本人跨业务待办、审批和最近事项。", "并列"),
            page("smart_construction_core.menu_sc_workbench_my_todo_fact", "处理本人的待办事项并进入来源业务。", "并列"),
            page("smart_construction_core.menu_sc_product_message_notification_v1", "查看业务消息并返回对应办理。", "并列"),
        ],
        next_steps=["待办和消息按目标办理打开对应业务场景，完成后返回工作台。"],
        exclusions=["工作台不产生项目、合同、资金等业务事实。"],
        references=[
            "所有已授权业务场景可把自己的待办、消息和结果链接投影到工作台。",
        ],
    ),
    scenario(
        "project.initiation",
        "项目立项与启用",
        "construction.center.project",
        "建立项目主档、确认客户和项目起始资料，并使项目进入可办理状态。",
        ["pm", "operation_user", "business_full"],
        ["有效企业上下文", "客户档案可用", "项目必填字段和公司范围已满足"],
        ["project.project", "res.partner"],
        "形成原公司下的项目记录，并明确项目启停状态。",
        [
            page("smart_construction_core.menu_sc_customer_partner", "维护客户档案，作为项目立项和后续合同的建设单位依据。", "依据"),
            page("smart_construction_core.menu_sc_project_initiation", "填写项目基本信息并发起正式项目立项。", "先办"),
            page("smart_construction_core.menu_sc_project_quick_create", "快速创建资料完整的项目主档；与正式立项并列。", "并列"),
            page("smart_construction_core.menu_sc_product_project_lifecycle_v1", "启用、停用或调整项目办理生命周期。", "办理"),
            page("smart_construction_core.menu_sc_project_project", "通过项目台账回读项目主档和生命周期结果。", "回读"),
        ],
        next_steps=[
            "项目进入投标阶段：project.tender",
            "项目进入计划阶段：project.planning",
            "项目建立后可编制预算：cost.budgeting",
        ],
        exclusions=["企业创建和首个管理员开立不在项目场景内。"],
        context="当前公司；新建项目时补全项目组织、客户和责任人",
        references=["项目台账被工作台、报表和多个业务场景引用。"],
    ),
    scenario(
        "project.tender",
        "投标准备、开标与中标确认",
        "construction.center.project",
        "从招标机会开始办理投标，记录标书、保证金、开标和中标结果。",
        ["operation_user", "pm", "business_full"],
        ["项目或潜在项目上下文", "客户档案", "投标资料和保证金责任人"],
        ["tender.opportunity", "tender.bid", "tender.document", "tender.guarantee", "tender.doc.purchase", "tender.opening", "project.project"],
        "形成投标项目、标书、保证金、开标和中标事实，并把中标结果关联到项目。",
        [
            page("smart_construction_core.menu_sc_product_tender_information_v1", "登记招标机会、招标人和招标条件。", "先办"),
            page("smart_construction_core.menu_sc_project_tender", "建立投标项目并绑定拟投标项目。", "办理"),
            page("smart_construction_core.menu_sc_product_tender_document_v1", "编制、审核和归档标书资料。", "并列"),
            page("smart_construction_core.menu_sc_tender_registration_fee", "申请和登记投标报名费用。", "并列"),
            page("smart_construction_core.menu_sc_tender_guarantee", "登记投标保证金及退还状态。", "并列"),
            page("smart_construction_core.menu_sc_tender_opening", "记录开标时间、报价和开标结果。", "办理"),
            page("smart_construction_core.menu_sc_tender_won", "确认中标结果并形成后续合同依据。", "办理"),
        ],
        dependencies=["project.initiation"],
        next_steps=["中标后进入合同登记：contract.registration，携带项目、招标和中标记录。"],
        exclusions=["合同登记本身不在投标场景完成。"],
        context="当前公司＋投标项目；从项目中心进入，完成后回项目台账",
    ),
    scenario(
        "project.planning",
        "计划编制与汇报",
        "construction.center.project",
        "形成可执行计划，并接收现场对计划执行情况的汇报。",
        ["pm", "project_member", "business_full"],
        ["启用中的项目", "项目组织或责任人", "计划周期"],
        ["sc.plan", "sc.plan.report"],
        "形成项目计划及计划执行汇报记录。",
        [
            page("smart_construction_core.menu_sc_plan", "编制、确认并下达项目计划。", "先办"),
            page("smart_construction_core.menu_sc_plan_report", "登记计划执行情况并回读偏差。", "回读"),
        ],
        dependencies=["project.initiation"],
        next_steps=["计划结果供现场记录、成本和报表使用。"],
        context="当前公司＋项目；从项目中心进入，完成后回项目台账",
    ),
    scenario(
        "project.delivery_record",
        "施工过程记录与工程签证",
        "construction.center.project",
        "持续记录现场施工、进度、资料和签证事实，保留可追溯项目过程。",
        ["pm", "project_member", "business_full"],
        ["启用中的项目", "项目组织", "现场责任人和施工周期"],
        ["sc.construction.diary", "project.progress.entry", "sc.project.document", "sc.site.variation"],
        "形成施工日志、进度、项目资料和签证记录。",
        [
            page("smart_construction_core.menu_sc_construction_diary", "记录每日施工内容、人员、机械和现场事项。", "先办"),
            page("smart_construction_core.menu_sc_construction_progress", "提交本期施工进度和完成事实。", "并列"),
            page("smart_construction_core.menu_sc_project_documents", "归档施工过程资料和附件。", "并列"),
            page("smart_construction_core.menu_sc_product_site_variation_v1", "登记现场签证和变更依据，保留原始事实。", "并列"),
        ],
        dependencies=["project.initiation", "project.planning"],
        next_steps=[
            "签证事实转入合同变更：contract.change，携带项目、签证和原始附件。",
            "进度和资源事实供成本归集与报表使用。",
        ],
        context="当前公司＋项目；从项目中心进入，完成后回项目台账",
    ),
    scenario(
        "project.quality",
        "质量检查、整改与复验",
        "construction.center.project",
        "按质量标准检查现场，记录问题，完成整改并复验关闭。",
        ["pm", "project_member", "business_full"],
        ["启用中的项目", "质量标准和检查责任人", "现场检查范围"],
        ["sc.check.standard", "sc.quality.acceptance", "sc.quality.issue", "sc.quality.rectification", "sc.quality.recheck", "sc.site.photo.batch"],
        "形成质量验收、问题、整改、复验和影像证据。",
        [
            page("smart_construction_core.menu_sc_quality_standard_v2", "查阅质量标准并作为验收和问题判定依据。", "依据"),
            page("smart_construction_core.menu_sc_product_quality_acceptance_v1", "登记工程质量验收和验收结论。", "先办"),
            page("smart_construction_core.menu_sc_quality_issue", "登记质量问题和责任信息。", "办理"),
            page("smart_construction_core.menu_sc_quality_site_photo_v2", "上传现场影像，作为问题与整改证据。", "并列"),
            page("smart_construction_core.menu_sc_quality_rectification", "提交整改措施和整改结果。", "办理"),
            page("smart_construction_core.menu_sc_quality_recheck", "复验整改并形成关闭结果。", "回读"),
        ],
        dependencies=["project.initiation"],
        next_steps=["关闭的质量事实供项目台账和经营报表使用。"],
        context="当前公司＋项目；从项目中心进入，完成后回质量列表",
    ),
    scenario(
        "project.safety",
        "安全方案、交底、巡检与整改",
        "construction.center.project",
        "建立安全依据，完成方案交底和巡检，对发现的问题整改复验。",
        ["pm", "project_member", "business_full"],
        ["启用中的项目", "安全责任人和项目风险范围"],
        ["sc.safety.plan", "sc.safety.disclosure", "sc.risk.library", "sc.hazard.source", "sc.safety.patrol.task", "sc.safety.issue", "sc.safety.rectification", "sc.safety.recheck"],
        "形成安全方案、交底、巡检、问题和整改复验事实。",
        [
            page("smart_construction_core.menu_sc_safety_risk_library_v2", "查阅安全风险库，作为方案和巡检依据。", "依据"),
            page("smart_construction_core.menu_sc_safety_hazard_source_v2", "维护本项目危险源和风险来源。", "依据"),
            page("smart_construction_core.menu_sc_safety_plan_v2", "编制并确认项目安全方案。", "先办"),
            page("smart_construction_core.menu_sc_safety_disclosure_v2", "完成安全方案交底并保留签认。", "办理"),
            page("smart_construction_core.menu_sc_safety_patrol_v2", "执行安全巡检并记录现场结果。", "办理"),
            page("smart_construction_core.menu_sc_safety_issue", "登记巡检发现的安全问题。", "办理"),
            page("smart_construction_core.menu_sc_safety_rectification", "提交安全整改措施和结果。", "办理"),
            page("smart_construction_core.menu_sc_safety_recheck", "复验整改并关闭安全问题。", "回读"),
        ],
        dependencies=["project.initiation"],
        next_steps=["关闭的安全事实供项目台账和经营风险分析使用。"],
        context="当前公司＋项目；从项目中心进入，完成后回安全列表",
    ),
    scenario(
        "contract.registration",
        "合同登记",
        "construction.center.contract",
        "登记收入、支出或日常合同，形成后续变更、结算和资金办理的合同依据。",
        ["operation_user", "pm", "business_full"],
        ["有效企业上下文", "合同相对方", "项目或责任中心", "合同金额和签署资料"],
        ["construction.contract", "construction.contract.income", "construction.contract.expense", "sc.general.contract"],
        "形成已确认合同及合同台账，供变更、结算、发票和资金办理引用。",
        [
            page("smart_construction_core.menu_sc_p1_income_contract", "登记收入合同并确认履约和经济信息。", "先办"),
            page("smart_construction_core.menu_sc_p1_expense_contract", "登记支出合同并确认相对方和项目归属。", "并列"),
            page("smart_construction_core.menu_sc_p1_daily_contract", "登记无项目主合同关系的一次性日常合同。", "并列"),
        ],
        dependencies=["project.initiation"],
        next_steps=[
            "合同变更：contract.change",
            "合同结算：contract.settlement",
            "支出合同可进入付款申请：finance.payment_approval",
        ],
        context="当前公司；收入/支出合同可带项目和客户/供应商；完成后回合同列表",
    ),
    scenario(
        "contract.change",
        "合同变更",
        "construction.center.contract",
        "基于现场签证或合同履约事实形成正式合同变更，不以签证替代合同变更。",
        ["operation_user", "pm", "business_full"],
        ["已确认合同", "项目或合同上下文", "变更依据和金额资料"],
        ["sc.contract.change"],
        "形成已确认合同变更，并保留与原合同、项目和现场依据的关系。",
        [
            page("smart_construction_core.menu_sc_p1_contract_change", "登记合同变更原因、范围、金额和依据并完成确认。", "办理"),
        ],
        dependencies=["contract.registration", "project.delivery_record"],
        next_steps=["变更结果进入合同结算：contract.settlement。"],
        context="当前公司＋合同＋项目；从合同中心进入，可回看来源签证",
    ),
    scenario(
        "contract.settlement",
        "合同结算",
        "construction.center.contract",
        "依据合同及已确认变更办理收入、支出或日常合同结算。",
        ["operation_user", "pm", "cost", "finance", "business_full"],
        ["已确认合同", "合同范围及变更事实", "结算周期和金额依据"],
        ["project.settlement", "sc.settlement.order"],
        "形成已审批结算单，作为收付款、发票和成本确认依据。",
        [
            page("smart_construction_core.menu_sc_p1_income_settlement", "办理收入合同结算并形成应收依据。", "先办"),
            page("smart_construction_core.menu_sc_p1_expense_settlement", "办理支出合同结算并形成应付依据。", "并列"),
            page("smart_construction_core.menu_sc_product_general_contract_settlement_v1", "办理日常合同结算。", "并列"),
            page("smart_construction_core.menu_sc_settlement_order", "查询统一结算单及其审批和完成结果，不在此新建业务记录。", "回读"),
        ],
        dependencies=["contract.registration", "contract.change"],
        next_steps=[
            "支出结算进入付款申请：finance.payment_approval",
            "收入结算进入收款登记：finance.receipt",
            "结算依据供销项开票：tax.output_invoice",
            "结算结果供成本归集和会计记账。",
        ],
        context="当前公司＋合同＋项目；从合同中心进入，完成后回结算单列表",
    ),
    scenario(
        "cost.budgeting",
        "目标成本与成本计划",
        "construction.center.cost",
        "建立项目目标成本和控制计划，作为采购、资源使用和成本归集的执行基准。",
        ["pm", "cost", "business_full"],
        ["启用中的项目", "项目清单或预算基础", "成本科目和审批策略"],
        ["project.budget", "project.cost.plan"],
        "形成已确认项目预算和成本计划。",
        [
            page("smart_construction_core.menu_sc_p1_project_budget", "建立并确认项目目标成本和预算控制口径。", "先办"),
            page("smart_construction_core.menu_sc_p1_cost_plan", "按项目范围编制成本执行计划。", "办理"),
        ],
        dependencies=["project.initiation"],
        next_steps=["采购与资源计划引用成本计划：supply.procurement、resource.labor、resource.equipment。"],
        context="当前公司＋项目；从成本中心进入，完成后回成本计划列表",
    ),
    scenario(
        "cost.collection",
        "实际成本归集",
        "construction.center.cost",
        "从合同、材料、劳务、机械和分包事实归集项目实际成本。",
        ["cost", "pm", "business_full"],
        ["有效成本计划", "合同或资源结算事实", "项目成本归属条件"],
        ["project.cost.ledger"],
        "形成可追溯项目成本台账。",
        [
            page("smart_construction_core.menu_sc_p1_cost_ledger", "查看和核对项目实际成本归集结果。", "回读"),
        ],
        dependencies=["contract.settlement", "material.settlement", "resource.labor", "resource.equipment", "resource.subcontract"],
        next_steps=["实际成本供项目盈亏分析：cost.analysis 和报表中心。"],
        context="当前公司＋项目；从成本中心进入，完成后回成本台账",
    ),
    scenario(
        "cost.analysis",
        "项目盈亏分析",
        "construction.center.cost",
        "比较项目收入、目标成本和实际成本，识别利润与偏差。",
        ["pm", "cost", "executive", "owner"],
        ["项目收入事实", "目标成本和实际成本"],
        ["project.profit.compare"],
        "形成项目盈亏分析和偏差结论。",
        [
            page("smart_construction_core.menu_sc_p1_profit_analysis", "按项目查看收入、成本和利润偏差。", "回读"),
        ],
        dependencies=["cost.budgeting", "cost.collection"],
        next_steps=["分析结果供经营报表：reporting.operating_review。"],
        context="当前公司＋项目；从成本中心进入，完成后回分析列表",
    ),
    scenario(
        "supply.supplier_management",
        "供应商准入与停用",
        "construction.center.supply_chain",
        "维护可采购供应商，并明确黑名单和暂停合作状态。",
        ["operation_user", "business_full"],
        ["有效企业上下文", "供应商主体资料", "准入或停用依据"],
        ["res.partner"],
        "形成可用或受限供应商主档。",
        [
            page("smart_construction_core.menu_sc_supplier_partner", "登记和维护供应商档案及合作范围。", "先办"),
            page("smart_construction_core.menu_sc_product_partner_blacklist_v1", "登记暂停或禁止合作的供应商。", "并列"),
        ],
        next_steps=["合格供应商供采购、分包和结算引用。"],
        context="当前公司；从供应链与资源中心进入，完成后回供应商列表",
    ),
    scenario(
        "supply.procurement",
        "材料需求、采购申请与询比价",
        "construction.center.supply_chain",
        "把项目材料需求转为采购申请，完成询比价和采购依据确认。",
        ["pm", "operation_user", "business_full"],
        ["启用中的项目", "合格供应商", "材料需求和成本控制"],
        ["project.material.plan", "sc.material.purchase.request", "sc.material.rfq", "sc.material.acceptance"],
        "形成材料计划、采购申请、询比价和采购验收依据。",
        [
            page("smart_construction_core.menu_project_material_plan", "编制项目材料需求和进场计划。", "先办"),
            page("smart_construction_core.menu_sc_material_purchase_request", "把材料需求转为采购申请并提交审批。", "办理"),
            page("smart_construction_core.menu_sc_material_rfq", "向合格供应商询价并比较报价。", "并列"),
            page("smart_construction_core.menu_sc_material_acceptance", "登记采购到货和进场验收结果。", "办理"),
        ],
        dependencies=["project.initiation", "cost.budgeting", "supply.supplier_management"],
        next_steps=["验收入库：supply.inventory，携带采购申请、供应商和验收记录。"],
        context="当前公司＋项目；从供应链与资源中心进入，完成后回材料管理列表",
    ),
    scenario(
        "supply.inventory",
        "材料入库、出库与库存移动",
        "construction.center.supply_chain",
        "办理材料入库、出库、调拨、退库和损耗，形成项目库存事实。",
        ["pm", "business_full"],
        ["材料验收或库存来源", "项目/仓库范围", "经办人和数量"],
        ["sc.material.inbound", "sc.material.outbound", "sc.material.supplier.return"],
        "形成可追溯材料收发存和异常损耗记录。",
        [
            page("smart_construction_core.menu_sc_material_inbound", "依据采购验收办理材料入库。", "先办"),
            page("smart_construction_core.menu_sc_material_outbound", "办理项目领用或现场出库。", "并列"),
            page("smart_construction_core.menu_sc_material_transfer", "办理项目或仓库之间的材料调拨。", "并列"),
            page("smart_construction_core.menu_sc_product_material_return_v1", "办理不合格或剩余材料退库/退货。", "并列"),
            page("smart_construction_core.menu_sc_material_loss", "登记盘亏、损耗和责任结果。", "并列"),
        ],
        dependencies=["supply.procurement"],
        next_steps=["材料消耗和结算事实进入材料结算、成本归集和报表。"],
        context="当前公司＋项目/仓库；从供应链与资源中心进入，完成后回材料收发列表",
    ),
    scenario(
        "material.settlement",
        "材料结算",
        "construction.center.supply_chain",
        "依据采购、验收、入库和退货事实结算供应商材料款。",
        ["pm", "cost", "finance", "business_full"],
        ["采购/验收/库存事实", "供应商", "结算数量和价格"],
        ["sc.material.settlement"],
        "形成材料结算及应付依据。",
        [
            page("smart_construction_core.menu_sc_material_settlement", "核对采购和库存事实并形成材料结算。", "办理"),
        ],
        dependencies=["supply.procurement", "supply.inventory"],
        next_steps=[
            "材料结算进入付款申请：finance.payment_approval",
            "成本事实进入：cost.collection",
        ],
        context="当前公司＋项目＋供应商；从供应链与资源中心进入，完成后回材料结算列表",
    ),
    scenario(
        "resource.labor",
        "劳务资源使用与结算",
        "construction.center.supply_chain",
        "完成劳务计划、申请、实名制、用量确认、扣款和结算。",
        ["pm", "cost", "business_full"],
        ["启用中的项目", "劳务班组/人员资料", "成本计划和现场用量"],
        ["sc.labor.plan", "sc.labor.request", "sc.labor.worker", "sc.labor.usage", "sc.labor.deduction", "sc.labor.settlement"],
        "形成劳务资源使用、扣款和结算事实。",
        [
            page("smart_construction_core.menu_sc_labor_plan", "编制项目劳务资源需求计划。", "先办"),
            page("smart_construction_core.menu_sc_labor_request", "提交劳务队伍或人员使用申请。", "办理"),
            page("smart_construction_core.menu_sc_product_labor_realname_v1", "维护实名制人员资料，作为现场用量依据。", "依据"),
            page("smart_construction_core.menu_sc_product_labor_cost_v1", "登记劳务实际用量和成本。", "办理"),
            page("smart_construction_core.menu_sc_product_labor_deduction_v1", "登记应由劳务承担或扣回的款项。", "并列"),
            page("smart_construction_core.menu_sc_labor_settlement", "汇总劳务用量和扣款并形成结算。", "回读"),
        ],
        dependencies=["project.initiation", "cost.budgeting"],
        next_steps=["劳务结算进入付款申请：finance.payment_approval，并供成本归集。"],
        context="当前公司＋项目；从供应链与资源中心进入，可回看项目劳务成本",
    ),
    scenario(
        "resource.equipment",
        "机械设备使用与结算",
        "construction.center.supply_chain",
        "完成设备计划、申请、台班使用和结算。",
        ["pm", "cost", "business_full"],
        ["启用中的项目", "设备资源", "施工计划和现场台班"],
        ["sc.equipment.plan", "sc.equipment.request", "sc.equipment.usage", "sc.equipment.settlement"],
        "形成设备使用台班和结算事实。",
        [
            page("smart_construction_core.menu_sc_equipment_plan", "编制项目机械设备使用计划。", "先办"),
            page("smart_construction_core.menu_sc_equipment_request", "提交设备进场或使用申请。", "办理"),
            page("smart_construction_core.menu_sc_product_equipment_shift_v1", "登记设备实际台班和使用成本。", "办理"),
            page("smart_construction_core.menu_sc_equipment_settlement", "汇总设备台班和费用形成结算。", "回读"),
        ],
        dependencies=["project.initiation", "cost.budgeting"],
        next_steps=["设备结算进入付款申请：finance.payment_approval，并供成本归集。"],
        context="当前公司＋项目；从供应链与资源中心进入，可回看项目机械成本",
    ),
    scenario(
        "resource.rental",
        "周转材料租赁与结算",
        "construction.center.supply_chain",
        "办理周转材料租赁计划、租赁确认和租赁结算。",
        ["pm", "cost", "business_full"],
        ["启用中的项目", "租赁供应商或资源", "周转材料使用计划"],
        ["sc.material.rental.plan", "sc.material.rental.order", "sc.material.rental.settlement"],
        "形成周转材料租赁单和结算事实。",
        [
            page("smart_construction_core.menu_sc_material_rental_plan", "编制周转材料租赁计划。", "先办"),
            page("smart_construction_core.menu_sc_material_rental_order", "登记实际租赁、进场和归还信息。", "办理"),
            page("smart_construction_core.menu_sc_material_rental_settlement", "按租赁事实形成结算。", "回读"),
        ],
        dependencies=["project.initiation", "cost.budgeting"],
        next_steps=["租赁结算进入付款申请：finance.payment_approval，并供成本归集。"],
        context="当前公司＋项目＋供应商；从供应链与资源中心进入，完成后回租赁列表",
    ),
    scenario(
        "resource.subcontract",
        "专业分包履约与结算",
        "construction.center.supply_chain",
        "完成分包计划、申请、成本/签证记录和分包结算。",
        ["pm", "cost", "finance", "business_full"],
        ["启用中的项目", "合格分包方", "分包范围、价格和合同依据"],
        ["sc.subcontract.plan", "sc.subcontract.request", "sc.subcontract.register", "sc.subcontract.settlement", "sc.site.variation"],
        "形成分包履约、成本、签证和结算事实。",
        [
            page("smart_construction_core.menu_sc_subcontract_plan", "编制专业分包计划和使用范围。", "先办"),
            page("smart_construction_core.menu_sc_subcontract_request", "提交分包申请并取得审批。", "办理"),
            page("smart_construction_core.menu_sc_product_subcontract_cost_v1", "登记分包关系与成本，承担分包登记职责，作为签证和结算依据。", "办理"),
            page("smart_construction_core.menu_sc_product_subcontract_variation_v1", "登记分包签证费用和依据。", "并列"),
            page("smart_construction_core.menu_sc_subcontract_settlement", "汇总分包履约和费用形成结算。", "回读"),
        ],
        dependencies=["project.initiation", "contract.registration"],
        next_steps=[
            "分包签证依据进入：contract.change",
            "分包结算进入付款申请：finance.payment_approval",
        ],
        exclusions=["分包合同权威仍属于合同中心；本场景不另建合同事实。"],
        context="当前公司＋项目＋分包方；从供应链与资源中心进入，可回看项目分包成本",
    ),
    scenario(
        "finance.receipt",
        "收款确认与登记",
        "construction.center.finance",
        "登记客户、公司或工程进度款收款，形成可核对的资金流入事实。",
        ["finance", "pm", "business_full"],
        ["有效公司/项目", "客户和收款账户", "合同、结算或收款依据"],
        ["sc.receipt.income"],
        "形成已确认收款登记和资金台账来源。",
        [
            page("smart_construction_core.menu_sc_receipt_income", "登记项目或客户收款并关联结算/合同依据。", "先办"),
            page("smart_construction_core.menu_sc_user_income", "登记公司层面的非项目收入。", "并列"),
            page("smart_construction_core.menu_sc_engineering_progress_income", "登记工程进度款收入。", "并列"),
        ],
        dependencies=["contract.settlement"],
        next_steps=["收款结果进入资金台账：finance.cash_ledger，并供会计记账。"],
        context="当前公司＋项目/客户；从财务中心进入，完成后回收款列表",
    ),
    scenario(
        "finance.payment_approval",
        "付款申请与审批",
        "construction.center.finance",
        "依据合同、结算或资源费用提交付款申请并取得业务审批。",
        ["pm", "finance", "business_full"],
        ["有效合同/结算或费用依据", "收款方、金额和资金用途", "适用的审批策略"],
        ["payment.request"],
        "形成已审批付款申请；尚未形成实际付款。",
        [
            page("smart_construction_core.menu_sc_user_payment_apply", "提交付款申请，查看审批状态和审批结论。", "先办"),
        ],
        dependencies=["contract.settlement", "material.settlement", "resource.labor", "resource.equipment", "resource.rental", "resource.subcontract"],
        next_steps=["审批完成转实付登记：finance.payment_execution，携带付款申请和收款方。"],
        exclusions=["申请审批不等于已经付款；付款必须在实付登记确认。"],
        context="当前公司＋项目＋合同/结算；从财务中心进入，完成后回付款申请列表",
    ),
    scenario(
        "finance.payment_execution",
        "实付登记",
        "construction.center.finance",
        "依据已审批付款申请执行实际付款并登记银行流水。",
        ["finance", "business_full"],
        ["已审批付款申请", "有效银行/资金账户", "实际付款日期和流水"],
        ["sc.payment.execution"],
        "形成实际付款登记，并关闭对应付款申请。",
        [
            page("smart_construction_core.menu_sc_payment_execution", "登记实际付款、账户和银行流水。", "先办"),
            page("smart_construction_core.menu_sc_company_finance_expense", "登记公司层面实际支出并形成资金事实。", "并列"),
        ],
        dependencies=["finance.payment_approval"],
        next_steps=["实际付款进入资金台账、成本归集和会计记账。"],
        context="当前公司＋付款申请；从财务中心进入，完成后回实付列表",
    ),
    scenario(
        "finance.expense_advance",
        "费用报销与备用金",
        "construction.center.finance",
        "办理员工费用报销和备用金申请/核销。",
        ["pm", "finance", "business_full"],
        ["费用发生事实", "项目/公司归属", "经办人和凭证"],
        ["sc.expense.claim"],
        "形成费用报销或备用金业务事实，并进入后续付款/核销。",
        [
            page("smart_construction_core.menu_sc_reimbursement_request", "提交费用报销并关联项目、费用类别和凭证。", "先办"),
            page("smart_construction_core.menu_sc_advance_fund", "申请或登记备用金及后续核销。", "并列"),
        ],
        next_steps=["需付款的报销或备用金进入：finance.payment_approval → finance.payment_execution。"],
        context="当前公司＋项目；从财务中心进入，完成后回费用列表",
    ),
    scenario(
        "finance.deduction",
        "公司项目扣款",
        "construction.center.finance",
        "登记应从业务对象或往来中扣减的款项。",
        ["finance", "cost", "business_full"],
        ["扣款来源事实", "被扣款对象", "金额与依据"],
        ["sc.expense.claim"],
        "形成可追溯扣款事实。",
        [
            page("smart_construction_core.menu_sc_deduction_bill", "登记公司或项目扣款并关联来源依据。", "办理"),
        ],
        dependencies=["contract.settlement", "resource.labor"],
        next_steps=["扣款结果进入资金台账和会计记账。"],
        context="当前公司＋项目/往来对象；从财务中心进入，完成后回扣款列表",
    ),
    scenario(
        "finance.intercompany",
        "公司项目往来与借还款",
        "construction.center.finance",
        "办理公司、项目、班组之间的借款、还款和往来核对。",
        ["finance", "pm", "business_full"],
        ["往来单位和项目", "借还款或退款依据", "资金账户"],
        ["sc.current.account.workspace", "sc.company.project.refund.workspace", "sc.team.loan.deduction.workspace"],
        "形成公司项目往来、退款和班组借扣款事实。",
        [
            page("smart_construction_core.menu_sc_product_current_account_v1", "登记和核对公司项目之间的往来款。", "先办"),
            page("smart_construction_core.menu_sc_product_company_project_refund_v1", "办理公司、项目之间的退款及核销。", "并列"),
            page("smart_construction_core.menu_sc_product_team_loan_deduction_v1", "登记班组借款和后续扣款。", "并列"),
        ],
        next_steps=["往来结果进入资金台账、成本确认和会计记账。"],
        context="当前公司＋项目/往来对象；从财务中心进入，可回看项目往来",
    ),
    scenario(
        "finance.cash_ledger",
        "资金计划与收支台账",
        "construction.center.finance",
        "查看资金计划、实际支付和资金余额，核对资金执行结果。",
        ["finance", "executive", "owner", "business_full"],
        ["收付款和账户事实", "资金计划期间"],
        ["project.funding.baseline", "payment.ledger", "sc.treasury.ledger"],
        "形成可追踪资金计划和资金台账视图。",
        [
            page("smart_construction_core.menu_sc_funding_plan_summary", "查看和核对资金计划与实际执行。", "依据"),
            page("smart_construction_core.menu_payment_ledger", "查看实际支付流水及其业务来源。", "回读"),
            page("smart_construction_core.menu_sc_treasury_ledger", "查看账户资金和资金变动台账。", "回读"),
        ],
        dependencies=["finance.receipt", "finance.payment_execution"],
        next_steps=["资金台账供会计报表和经营分析使用。"],
        context="当前公司；从财务中心进入，完成后回资金台账",
    ),
    scenario(
        "tax.external_certificate",
        "外经证办理",
        "construction.center.tax",
        "登记和管理跨区域经营所需外经证。",
        ["finance", "accounting", "business_full"],
        ["公司税务资料", "项目跨区域经营信息"],
        ["sc.tax.certificate.registration"],
        "形成外经证登记及其有效状态。",
        [
            page("smart_construction_core.menu_sc_tax_certificate_registration_user", "登记外经证、项目、有效期和办理结果。", "办理"),
        ],
        context="当前公司＋项目；从税务中心进入，完成后回外经证列表",
    ),
    scenario(
        "tax.prepayment",
        "税款预缴",
        "construction.center.tax",
        "按项目或属地规则登记预缴税款。",
        ["finance", "accounting", "business_full"],
        ["项目税务信息", "预缴依据和缴款凭证"],
        ["sc.invoice.registration"],
        "形成税款预缴登记。",
        [
            page("smart_construction_core.menu_sc_invoice_prepaid_tax_user", "登记预缴税款金额、项目和缴款凭证。", "办理"),
        ],
        dependencies=["tax.external_certificate"],
        next_steps=["预缴结果进入税额抵扣和税务申报。"],
        context="当前公司＋项目；从税务中心进入，完成后回预缴列表",
    ),
    scenario(
        "tax.output_invoice",
        "销项开票与红冲",
        "construction.center.tax",
        "依据收入结算或收款申请开票，并处理错误或退回发票。",
        ["finance", "accounting", "business_full"],
        ["已确认收入依据", "客户开票信息", "税率和开票条件"],
        ["sc.invoice.registration", "sc.output.invoice.adjustment"],
        "形成销项发票及必要的红冲记录。",
        [
            page("smart_construction_core.menu_sc_invoice_application_user", "发起开票申请并关联收入合同/结算。", "先办"),
            page("smart_construction_core.menu_sc_invoice_registration_user", "确认并登记销项发票。", "办理"),
            page("smart_construction_core.menu_sc_output_invoice_change_registration", "对错误或退回销项发票办理红冲。", "并列"),
        ],
        dependencies=["contract.settlement", "finance.receipt"],
        next_steps=["发票结果进入税务台账、会计记账和税务申报。"],
        context="当前公司＋项目＋客户；从税务中心进入，完成后回发票列表",
    ),
    scenario(
        "tax.input_invoice",
        "进项发票登记",
        "construction.center.tax",
        "登记供应商或分包方进项发票并关联业务成本。",
        ["finance", "accounting", "business_full"],
        ["供应商/分包方发票", "材料、劳务或分包结算依据"],
        ["sc.invoice.registration"],
        "形成可抵扣进项发票事实。",
        [
            page("smart_construction_core.menu_sc_invoice_input", "登记进项发票并关联项目、供应商和成本依据。", "办理"),
        ],
        dependencies=["material.settlement", "resource.subcontract"],
        next_steps=["进项发票进入税额抵扣和会计记账。"],
        context="当前公司＋项目＋供应商；从税务中心进入，完成后回进项发票列表",
    ),
    scenario(
        "tax.deduction",
        "税额抵扣",
        "construction.center.tax",
        "依据进项发票和项目专项规则登记可抵扣税额。",
        ["finance", "accounting", "business_full"],
        ["有效进项发票", "项目/公司抵扣归属", "可抵扣税额"],
        ["sc.tax.deduction.registration"],
        "形成税额抵扣登记及余额结果。",
        [
            page("smart_construction_core.menu_sc_tax_deduction_registration_user", "登记公司层面可抵扣税额。", "先办"),
            page("smart_construction_core.menu_sc_product_project_tax_deduction_v1", "登记项目专项抵扣及归属。", "并列"),
        ],
        dependencies=["tax.input_invoice"],
        next_steps=["抵扣结果进入税务申报和会计记账。"],
        context="当前公司＋项目；从税务中心进入，完成后回抵扣列表",
    ),
    scenario(
        "tax.filing",
        "税务申报",
        "construction.center.tax",
        "汇总销项、进项、预缴和抵扣事实，形成税务申报记录。",
        ["finance", "accounting", "business_full"],
        ["有效税期", "发票、预缴和抵扣事实"],
        ["sc.tax.filing"],
        "形成税务申报结果和申报状态。",
        [
            page("smart_construction_core.menu_sc_product_tax_filing_v1", "编制、确认和登记税期申报结果。", "回读"),
        ],
        dependencies=["tax.output_invoice", "tax.input_invoice", "tax.deduction", "tax.prepayment"],
        next_steps=["申报结果进入税务报表、会计报表和经营分析。"],
        context="当前公司＋税期；从税务中心进入，完成后回税务申报列表",
    ),
    scenario(
        "accounting.foundation",
        "会计基础配置",
        "construction.center.accounting",
        "建立会计科目、日记账及分析核算基础。",
        ["accounting", "business_config_admin"],
        ["企业会计准则和本位币", "公司经营范围", "分析维度要求"],
        ["account.account", "account.journal", "account.analytic.account", "account.analytic.distribution.model"],
        "形成可使用的会计科目、日记账和分析核算配置。",
        [
            page("account.menu_action_account_form", "维护会计科目和核算属性。", "先办"),
            page("smart_construction_core.menu_sc_account_journal_foundation", "配置日记账和记账用途。", "并列"),
            page("smart_construction_core.menu_sc_analytic_account_foundation", "建立项目或部门分析账户。", "并列"),
            page("smart_construction_core.menu_sc_analytic_distribution_foundation", "配置分析维度自动分配规则。", "并列"),
        ],
        next_steps=["基础配置供凭证记账、对账和会计账簿使用。"],
        context="当前公司；从会计账务中心进入，完成后回会计基础列表",
    ),
    scenario(
        "accounting.entry_posting",
        "凭证编制与记账",
        "construction.center.accounting",
        "编制和复核会计凭证，查询分录并完成记账结果核对。",
        ["accounting"],
        ["会计基础配置", "有效会计期间", "业务或手工记账依据"],
        ["account.move", "account.move.line"],
        "形成会计分录和账簿结果。",
        [
            page("account.menu_action_move_journal_line_form", "编制和确认会计分录。", "先办"),
            page("account.menu_action_account_moves_all", "查询记账分录和业务来源，完成结果回读。", "回读"),
        ],
        dependencies=["accounting.foundation", "finance.cash_ledger", "tax.filing"],
        next_steps=["会计分录供会计报表和经营分析使用。"],
        context="当前公司＋会计期间；从会计账务中心进入，完成后回分录列表",
    ),
    scenario(
        "reporting.project_portfolio",
        "项目经营态势查看",
        "construction.center.reporting",
        "从工作台快速识别项目阶段、关键指标和异常项目。",
        ["pm", "executive", "owner", "business_full"],
        ["已授权项目范围", "项目及经营指标事实"],
        ["sc.operating.metrics.project", "project.project"],
        "形成项目组合状态判断，并进入需要处理的项目。",
        [
            page("smart_construction_core.menu_sc_operating_metrics_project", "查看项目经营指标和异常提示。", "依据"),
            page("smart_construction_core.menu_sc_project_kanban", "按项目阶段浏览项目并进入项目办理。", "办理"),
        ],
        dependencies=["project.initiation", "cost.analysis", "finance.cash_ledger"],
        next_steps=["点击项目后进入项目台账或对应业务办理面；返回工作台。"],
        context="当前用户授权公司/项目范围；从工作台或报表中心进入，返回来源处",
    ),
    scenario(
        "reporting.operating_review",
        "跨业务经营分析",
        "construction.center.reporting",
        "从项目、成本、资金、税务和劳务分包报表完成综合经营分析。",
        ["executive", "owner", "pm", "cost", "finance", "accounting"],
        ["已发布的经营事实", "当前公司/项目授权范围", "口径已声明"],
        ["sc.operating.metrics.project", "sc.comprehensive.cost.summary", "sc.fund.daily.summary", "sc.tax.filing", "sc.labor.subcontract.report"],
        "形成跨业务经营判断和后续办理入口。",
        [
            page("smart_construction_core.menu_sc_project_operation_statistics_report", "查看项目经营统计并钻取项目事实。", "依据"),
            page("smart_construction_core.menu_sc_comprehensive_cost_statistics_report", "查看成本汇总和偏差。", "并列"),
            page("smart_construction_core.menu_sc_fund_daily_summary", "查看资金日报和收支执行。", "并列"),
            page("smart_construction_core.menu_sc_product_tax_report_v1", "查看税务台账和申报结果。", "并列"),
            page("smart_construction_core.menu_sc_product_labor_subcontract_report_v1", "查看劳务和分包执行结果。", "并列"),
        ],
        dependencies=["cost.analysis", "finance.cash_ledger", "tax.filing", "resource.labor", "resource.subcontract"],
        next_steps=["报表异常按来源返回项目、成本、资金、税务或资源办理面。"],
        context="当前公司；从报表中心或工作台进入，完成后返回原报表",
    ),
    scenario(
        "admin.organization",
        "组织、岗位与人员",
        "construction.center.administration",
        "建立企业部门、岗位和人员档案，为账号、权限和业务责任提供组织基础。",
        ["business_config_admin"],
        ["当前企业", "合法上级部门", "岗位和人员资料"],
        ["hr.department", "hr.job", "hr.employee", "res.users"],
        "形成部门、岗位和人员/账号关联。",
        [
            page("smart_construction_core.menu_sc_organization_department", "维护部门和上下级关系。", "先办"),
            page("smart_construction_core.menu_sc_product_job_management_v1", "维护岗位并关联所属部门。", "并列"),
            page("smart_construction_core.menu_sc_runtime_user_management", "维护人员、账号、部门和岗位关系。", "办理"),
        ],
        next_steps=["人员进入：config.enterprise_access 配置角色和公司范围。"],
        context="当前企业；从行政中心或企业初始化进入，完成后返回原上下文",
    ),
    scenario(
        "admin.payroll",
        "薪酬社保办理",
        "construction.center.administration",
        "办理社保、工资核算和项目薪资发放。",
        ["business_config_admin", "finance", "pm"],
        ["人员与岗位档案", "薪酬规则和期间", "项目薪资归属"],
        ["sc.hr.payroll.document", "sc.hr.salary.payment"],
        "形成工资核算和薪资发放事实。",
        [
            page("smart_construction_core.menu_sc_product_social_fund_v1", "登记社保和公积金基础与缴纳事实。", "依据"),
            page("smart_construction_core.menu_sc_payroll_management", "核算企业工资薪酬并形成发放依据。", "先办"),
            page("smart_construction_core.menu_sc_product_project_payroll_v1", "核算项目人员工资清单。", "并列"),
            page("smart_construction_core.menu_sc_product_project_salary_payment_v1", "登记项目薪资实际发放。", "回读"),
        ],
        dependencies=["admin.organization"],
        next_steps=["薪资发放进入资金台账、成本归集和会计记账。"],
        context="当前公司＋项目/人员；从行政中心进入，完成后回薪酬列表",
    ),
    scenario(
        "admin.documents",
        "证照与制度文件",
        "construction.center.administration",
        "维护企业证照和制度文件的有效性与留存。",
        ["business_config_admin"],
        ["企业主体", "文件原件或扫描件", "有效期限和责任人"],
        ["sc.document.admin.document"],
        "形成证照和制度文件记录。",
        [
            page("smart_construction_core.menu_sc_certificate_registration", "登记企业证照、有效期和附件。", "先办"),
            page("smart_construction_core.menu_sc_product_policy_document_v1", "维护企业制度文件及版本。", "并列"),
        ],
        context="当前公司；从行政中心进入，完成后回文档列表",
    ),
    scenario(
        "admin.assets",
        "行政资产管理",
        "construction.center.administration",
        "登记企业内部办公资产及使用状态。",
        ["business_config_admin"],
        ["企业/部门范围", "资产基础资料", "使用责任人"],
        ["sc.office.asset"],
        "形成办公资产和责任人记录。",
        [
            page("smart_construction_core.menu_sc_product_office_asset_v1", "登记、领用和归还行政办公资产。", "办理"),
        ],
        context="当前公司；从行政中心进入，完成后回资产列表",
    ),

]


# New scenario/page facts are declared by the P1 product source. This tool only
# validates and projects their placement, never invents new business entries.
def apply_declared_page_extensions(scenarios, declarations):
    known = {row["key"]: row for row in scenarios}
    used = {item["menu_xmlid"] for row in scenarios for item in row["pages"]}
    direct = []
    for declaration in declarations:
        key = declaration["scenario_key"]
        xmlid = declaration["menu_xmlid"]
        if key not in known or xmlid in used:
            raise ValueError("unknown scenario or duplicate page extension: " + xmlid)
        if declaration["intent"] not in {"master_data", "handle", "view", "approve", "report"}:
            raise ValueError("invalid declared page intent: " + xmlid)
        if not declaration["purpose"] or not declaration["mode"]:
            raise ValueError("page extension requires purpose and mode: " + xmlid)
        known[key]["pages"].append({**page(xmlid, declaration["purpose"], declaration["mode"]),
                                    "declared_intent": declaration["intent"]})
        used.add(xmlid)
        if declaration.get("direct_kind"):
            direct.append((xmlid, declaration["direct_kind"]))
    return tuple(direct)


def apply_declared_scenarios(scenarios, declarations):
    known = {row["key"] for row in scenarios}
    used = {item["menu_xmlid"] for row in scenarios for item in row["pages"]}
    direct = {}
    for declaration in declarations:
        row = scenario(**declaration)
        if row["key"] in known or not row["pages"]:
            raise ValueError("duplicate or empty declared scenario: " + row["key"])
        for item in row["pages"]:
            xmlid = item["menu_xmlid"]
            if xmlid in used:
                raise ValueError("duplicate declared scenario page: " + xmlid)
            if item.get("declared_intent") not in {None, "master_data", "handle", "view", "approve", "report"}:
                raise ValueError("invalid declared scenario intent: " + xmlid)
            used.add(xmlid)
            if item.get("direct_kind"):
                direct[xmlid] = item["direct_kind"]
        scenarios.append(row)
        known.add(row["key"])
    return direct


_declared_direct = apply_declared_scenarios(
    SCENARIOS, json.loads(SOURCE_PATH.read_text(encoding="utf-8")).get("scenario_definitions", []),
)
DIRECT_PLATFORM_PAGES = tuple({**dict(DIRECT_PLATFORM_PAGES), **_declared_direct}.items())


DIRECT_PLATFORM_PAGES += apply_declared_page_extensions(
    SCENARIOS, json.loads(SOURCE_PATH.read_text(encoding="utf-8")).get("scenario_page_extensions", []),
)


PAGE_REFERENCE_OVERRIDES = {
    "smart_construction_core.menu_sc_customer_partner": "项目立项主归属；投标场景引用同一客户身份。",
    "smart_construction_core.menu_sc_project_project": "项目立项结果回读；工作台和报表按项目身份继续引用。",
    "smart_construction_core.menu_project_material_plan": "采购场景主归属；成本场景引用材料计划作为成本控制依据。",
    "smart_construction_core.menu_sc_p1_income_contract": "合同登记主归属；结算、开票和收款场景引用同一合同。",
    "smart_construction_core.menu_sc_p1_expense_contract": "合同登记主归属；结算、进项和付款场景引用同一合同。",
    "smart_construction_core.menu_sc_p1_daily_contract": "合同登记主归属；日常合同结算引用同一合同。",
    "smart_construction_core.menu_sc_product_site_variation_v1": "项目中心保留签证事实；合同中心引用为变更依据。",
    "smart_construction_core.menu_sc_product_subcontract_variation_v1": "项目中心保留分包签证成本事实；分包场景引用为结算依据。",
    "smart_construction_core.menu_sc_product_labor_cost_v1": "项目中心回读劳务成本；劳务场景引用为结算依据。",
    "smart_construction_core.menu_sc_product_equipment_shift_v1": "项目中心回读机械台班成本；设备场景引用为结算依据。",
    "smart_construction_core.menu_sc_product_project_payroll_v1": "项目中心回读项目薪资；行政薪酬场景引用为发放依据。",
    "smart_construction_core.menu_sc_product_project_salary_payment_v1": "项目中心回读薪资发放；行政薪酬场景负责主办理。",
    "smart_construction_core.menu_sc_product_team_loan_deduction_v1": "项目中心提供项目入口；财务往来场景负责主办理。",
    "smart_construction_core.menu_sc_operating_metrics_project": "工作台展示经营指标；报表场景负责口径解释。",
    "smart_construction_core.menu_sc_project_kanban": "工作台提供项目卡片；项目台账和报表继续办理或分析。",
}

PAGE_DISPLAY_OVERRIDES = {
    "smart_construction_core.menu_sc_product_subcontract_cost_v1":
        "分包登记与成本确认（原菜单：分包成本登记）",
}

MODE_OVERRIDES = {
    "smart_construction_core.menu_sc_workspace_home": "查看",
    "smart_construction_core.menu_sc_my_work": "查看",
    "smart_construction_core.menu_sc_workbench_my_todo_fact": "办理",
    "smart_construction_core.menu_sc_product_message_notification_v1": "查看",
    "smart_construction_core.menu_sc_customer_partner": "辅助办理",
    "smart_construction_core.menu_sc_quality_standard_v2": "辅助办理",
    "smart_construction_core.menu_sc_safety_risk_library_v2": "辅助办理",
    "smart_construction_core.menu_sc_safety_hazard_source_v2": "辅助办理",
    "smart_construction_core.menu_sc_product_labor_realname_v1": "辅助办理",
    "smart_construction_core.menu_sc_operating_metrics_project": "查看",
    "smart_construction_core.menu_sc_project_kanban": "查看",
    "smart_construction_core.menu_sc_plan_report": "办理",
    "smart_construction_core.menu_sc_quality_recheck": "办理",
    "smart_construction_core.menu_sc_safety_recheck": "办理",
    "smart_construction_core.menu_sc_product_labor_cost_v1": "办理",
    "smart_construction_core.menu_sc_product_labor_deduction_v1": "办理",
    "smart_construction_core.menu_sc_product_equipment_shift_v1": "办理",
    "smart_construction_core.menu_sc_product_subcontract_cost_v1": "办理",
    "smart_construction_core.menu_sc_product_subcontract_variation_v1": "办理",
    "smart_construction_core.menu_sc_labor_settlement": "办理",
    "smart_construction_core.menu_sc_equipment_settlement": "办理",
    "smart_construction_core.menu_sc_material_rental_settlement": "办理",
    "smart_construction_core.menu_sc_subcontract_settlement": "办理",
    "smart_construction_core.menu_sc_product_project_salary_payment_v1": "办理",
    "smart_construction_core.menu_sc_product_social_fund_v1": "办理",
    "smart_construction_core.menu_sc_product_tax_filing_v1": "办理",
    "smart_construction_core.menu_sc_product_data_permission_v1": "办理",
    "account.menu_action_account_moves_all": "查看",
    "smart_construction_core.menu_sc_project_operation_statistics_report": "查看",
    "smart_construction_core.menu_sc_comprehensive_cost_statistics_report": "查看",
    "smart_construction_core.menu_sc_fund_daily_summary": "查看",
    "smart_construction_core.menu_sc_product_tax_report_v1": "查看",
    "smart_construction_core.menu_sc_product_labor_subcontract_report_v1": "查看",
}

ALTERNATIVE_GROUPS = {
    "project.create": {
        "label": "新项目立项或快速创建项目",
        "pages": {
            "smart_construction_core.menu_sc_project_initiation",
            "smart_construction_core.menu_sc_project_quick_create",
        },
    },
    "payment.execution.kind": {
        "label": "按付款申请实付或直接登记公司支出",
        "pages": {
            "smart_construction_core.menu_sc_payment_execution",
            "smart_construction_core.menu_sc_company_finance_expense",
        },
    },
    "contract.kind": {
        "label": "收入合同、支出合同或日常合同",
        "pages": {
            "smart_construction_core.menu_sc_p1_income_contract",
            "smart_construction_core.menu_sc_p1_expense_contract",
            "smart_construction_core.menu_sc_p1_daily_contract",
        },
    },
    "settlement.kind": {
        "label": "收入结算、支出结算或日常合同结算",
        "pages": {
            "smart_construction_core.menu_sc_p1_income_settlement",
            "smart_construction_core.menu_sc_p1_expense_settlement",
            "smart_construction_core.menu_sc_product_general_contract_settlement_v1",
        },
    },
    "receipt.kind": {
        "label": "项目收款、公司收入或工程进度款收入",
        "pages": {
            "smart_construction_core.menu_sc_receipt_income",
            "smart_construction_core.menu_sc_user_income",
            "smart_construction_core.menu_sc_engineering_progress_income",
        },
    },
    "expense.funding_kind": {
        "label": "费用报销或备用金",
        "pages": {
            "smart_construction_core.menu_sc_reimbursement_request",
            "smart_construction_core.menu_sc_advance_fund",
        },
    },
    "intercompany.kind": {
        "label": "公司项目往来、退款或班组借扣款",
        "pages": {
            "smart_construction_core.menu_sc_product_current_account_v1",
            "smart_construction_core.menu_sc_product_company_project_refund_v1",
            "smart_construction_core.menu_sc_product_team_loan_deduction_v1",
        },
    },
    "tax.deduction.kind": {
        "label": "公司税额抵扣或项目专项抵扣",
        "pages": {
            "smart_construction_core.menu_sc_tax_deduction_registration_user",
            "smart_construction_core.menu_sc_product_project_tax_deduction_v1",
        },
    },
}

INDEPENDENT_PAGES = {
    "smart_construction_core.menu_sc_workspace_home",
    "smart_construction_core.menu_sc_my_work",
    "smart_construction_core.menu_sc_workbench_my_todo_fact",
    "smart_construction_core.menu_sc_product_message_notification_v1",
    "smart_construction_core.menu_sc_certificate_registration",
    "smart_construction_core.menu_sc_product_policy_document_v1",
    "smart_construction_core.menu_sc_product_office_asset_v1",
    "smart_construction_core.menu_sc_product_system_parameter_v1",
    "smart_construction_core.menu_sc_product_numbering_rule_v1",
    "smart_construction_core.menu_sc_business_config_workbench",
    "smart_construction_core.menu_ui_form_field_policy_business_config",
    "smart_construction_core.menu_ui_menu_config_policy_business_config",
    "smart_construction_core.menu_sc_account_journal_foundation",
    "smart_construction_core.menu_sc_analytic_account_foundation",
    "smart_construction_core.menu_sc_analytic_distribution_foundation",
}

PAGE_OUTPUT_OVERRIDES = {
    "smart_construction_core.menu_sc_workspace_home": "显示当前角色可用的工作台入口和提示",
    "smart_construction_core.menu_sc_my_work": "返回当前用户的跨业务工作和最近事项",
    "smart_construction_core.menu_sc_workbench_my_todo_fact": "产生或更新工作台待办处理状态",
    "smart_construction_core.menu_sc_product_message_notification_v1": "返回当前用户消息并保留已读状态",
    "smart_construction_core.menu_sc_operating_metrics_project": "返回项目经营指标和异常结果",
    "smart_construction_core.menu_sc_project_kanban": "返回按阶段组织的项目卡片",
    "smart_construction_core.menu_sc_plan_report": "形成计划执行汇报记录",
    "smart_construction_core.menu_sc_quality_recheck": "形成质量复验结论和关闭状态",
    "smart_construction_core.menu_sc_safety_recheck": "形成安全复验结论和关闭状态",
    "smart_construction_core.menu_sc_product_data_permission_v1": "更新目标用户的业务角色和允许公司范围",
    "smart_construction_core.menu_sc_product_social_fund_v1": "产生或更新社保公积金业务记录",
    "smart_construction_core.menu_sc_product_tax_filing_v1": "形成税务申报记录和申报状态",
    "smart_construction_core.menu_sc_project_operation_statistics_report": "返回项目经营统计查询结果",
    "smart_construction_core.menu_sc_comprehensive_cost_statistics_report": "返回综合成本统计查询结果",
    "smart_construction_core.menu_sc_fund_daily_summary": "返回资金日报查询结果",
    "smart_construction_core.menu_sc_product_tax_report_v1": "返回税务申报查询结果",
    "smart_construction_core.menu_sc_product_labor_subcontract_report_v1": "返回劳务分包分析结果",
}

PAGE_CONTEXT_OVERRIDES = {
    "smart_construction_core.menu_sc_customer_partner":
        "必须已有：当前公司及客户维护权限；可新建或更新客户；续办时携带 res.partner ID",
    "smart_construction_core.menu_sc_product_project_lifecycle_v1":
        "必须已有：目标项目；选择已有项目调整启停状态；续办时携带 project_id",
    "smart_construction_core.menu_sc_project_project":
        "必须已有：当前公司及项目查询权限；选择查询范围，不新建项目；续办时携带 project_id 和筛选上下文",
    "smart_construction_core.menu_sc_quality_standard_v2":
        "必须已有：当前公司及质量配置权限；可新建或更新质量标准；续办时携带 sc.check.standard ID",
    "smart_construction_core.menu_sc_product_labor_realname_v1":
        "必须已有：当前公司、项目及实名制维护权限；可新建或更新劳务人员资料；续办时携带 sc.labor.worker ID",
    "smart_construction_core.menu_sc_labor_plan":
        "必须已有：启用项目、劳务需求和计划权限；可新建劳务计划；实际用量不作为计划前置；续办时携带 sc.labor.plan ID",
    "smart_construction_core.menu_sc_equipment_plan":
        "必须已有：启用项目、施工计划和设备需求；可新建设备计划；实际台班不作为计划前置；续办时携带 sc.equipment.plan ID",
    "smart_construction_core.menu_sc_product_tender_information_v1":
        "必须已有：当前公司；可新建招标机会；续办时携带 tender.opportunity ID",
    "smart_construction_core.menu_sc_project_tender":
        "必须已有：启用项目；新建投标记录后产生 tender.bid；续办时携带 bid ID",
    "smart_construction_core.menu_sc_p1_income_contract":
        "必须已有：公司、项目、发包人；可新建收入合同；续办时携带 construction.contract ID",
    "smart_construction_core.menu_sc_p1_expense_contract":
        "必须已有：公司、项目、相对方；可新建支出合同；续办时携带 construction.contract ID",
    "smart_construction_core.menu_sc_p1_daily_contract":
        "必须已有：公司；项目可选；可新建日常合同；续办时携带 sc.general.contract ID",
    "smart_construction_core.menu_sc_p1_income_settlement":
        "必须已有：已确认收入合同及其项目；续办时携带合同 ID 和结算单 ID",
    "smart_construction_core.menu_sc_p1_expense_settlement":
        "必须已有：已确认支出合同及其项目；续办时携带合同 ID 和结算单 ID",
    "smart_construction_core.menu_sc_product_general_contract_settlement_v1":
        "必须已有：公司及日常合同；项目按日常合同可选；续办时携带 general_contract ID 和结算单 ID",
    "smart_construction_core.menu_sc_reimbursement_request":
        "必须已有：当前公司、经办人和费用依据；项目按费用归属可选；续办时携带 sc.expense.claim ID",
    "smart_construction_core.menu_sc_advance_fund":
        "必须已有：当前公司、经办人和备用金依据；项目按业务归属可选；续办时携带 sc.expense.claim ID",
    "smart_construction_core.menu_sc_receipt_income":
        "必须已有：当前公司、客户和资金账户；项目可选；续办时携带收款单 ID，合同/结算依据按实际带入",
    "smart_construction_core.menu_sc_user_income":
        "必须已有：当前公司、付款客户和资金账户；不要求项目；续办时携带收款单 ID",
    "smart_construction_core.menu_sc_engineering_progress_income":
        "必须已有：当前公司、项目和进度款依据；续办时携带收款单 ID",
    "smart_construction_core.menu_sc_payment_execution":
        "必须已有：已审批付款申请、资金账户和实际付款事实；续办时携带付款申请 ID 和实付登记 ID",
    "smart_construction_core.menu_sc_company_finance_expense":
        "必须已有：当前公司、资金账户和公司支出依据；不要求已有付款申请；续办时携带公司支出记录 ID",
    "smart_construction_core.menu_sc_labor_settlement":
        "必须已有：启用项目、已确认劳务用量/成本；无扣款时可直接结算，有扣款时引用实际扣款记录；续办时携带结算单 ID",
    "smart_construction_core.menu_sc_subcontract_settlement":
        "必须已有：启用项目、分包登记/履约确认；无签证时可直接结算，有签证时引用实际签证记录；续办时携带结算单 ID",
    "smart_construction_core.menu_sc_safety_risk_library_v2":
        "必须已有：当前公司及安全配置权限；可维护风险分类和风险库；续办时携带风险库 ID",
    "smart_construction_core.menu_sc_safety_hazard_source_v2":
        "必须已有：启用项目及安全维护权限；可维护项目危险源；续办时携带危险源 ID",
    "smart_construction_core.menu_sc_product_data_permission_v1":
        "必须已有：目标用户及其当前角色、公司范围；只能选择已有 res.users，不在权限页新建用户；续办时携带 user_id",
}

RELATION_OVERRIDES = {
    "smart_construction_core.menu_sc_labor_plan":
        "计划依据：启用项目、劳务需求和成本控制目标；实际用工量在后续登记",
    "smart_construction_core.menu_sc_equipment_plan":
        "计划依据：启用项目、施工计划和设备需求；实际台班在后续登记",
    "smart_construction_core.menu_sc_construction_progress":
        "基于项目实际进度事实；施工日志可同期记录，不要求先办施工日志",
    "smart_construction_core.menu_sc_project_documents":
        "基于已形成项目资料；可随业务发生归档，不要求先办施工日志",
    "smart_construction_core.menu_sc_product_site_variation_v1":
        "基于现场签证事实；施工日志和工程资料可作依据，不要求先办某一页面",
    "smart_construction_core.menu_sc_material_outbound":
        "基于现有库存或实际领用需求；不要求先办理当期材料入库",
    "smart_construction_core.menu_sc_material_transfer":
        "基于调出方现有库存和调入项目；不要求先办理当期材料入库",
    "smart_construction_core.menu_sc_product_material_return_v1":
        "基于原领用、验收或库存事实；不要求先办理当期材料入库",
    "smart_construction_core.menu_sc_material_loss":
        "基于库存差异或现场损耗事实；不要求先办理当期材料入库",
    "smart_construction_core.menu_sc_product_tender_document_v1":
        "依赖：已建立投标项目 tender.bid；标书与报名费、保证金可并列准备",
    "smart_construction_core.menu_sc_tender_registration_fee":
        "依赖：已建立投标项目 tender.bid；报名费与标书、保证金可并列准备",
    "smart_construction_core.menu_sc_tender_guarantee":
        "依赖：已建立投标项目 tender.bid；保证金与标书、报名费可并列准备",
    "smart_construction_core.menu_sc_quality_site_photo_v2":
        "依赖：质量检查或问题记录；现场影像作为问题与整改证据",
    "smart_construction_core.menu_sc_product_partner_blacklist_v1":
        "依赖：已登记供应商身份；黑名单更新不新建平行供应商",
    "smart_construction_core.menu_sc_material_rfq":
        "依赖：已审批采购申请和采购范围；询价结果供验收使用",
    "smart_construction_core.menu_sc_output_invoice_change_registration":
        "依赖：原销项发票及其登记事实；红冲不改变原发票历史",
    "smart_construction_core.menu_sc_product_job_management_v1":
        "依赖：目标部门；岗位登记后供人员维护选择",
    "smart_construction_core.menu_sc_product_project_payroll_v1":
        "依赖：已核算工资薪酬及项目人员范围；项目薪资清单供后续发放",
    "smart_construction_core.menu_sc_product_labor_deduction_v1":
        "条件步骤：存在应扣减事项时办理；无扣款事项不影响劳务结算",
    "smart_construction_core.menu_sc_labor_settlement":
        "依赖：已确认劳务用量/成本；存在扣款时引用劳务扣款明细，无扣款可直接结算",
    "smart_construction_core.menu_sc_product_subcontract_variation_v1":
        "条件步骤：发生分包签证时办理；无签证事项不影响分包结算",
    "smart_construction_core.menu_sc_subcontract_settlement":
        "依赖：分包登记/履约确认；发生签证时引用分包签证费用，无签证可直接结算",
    "smart_construction_core.menu_sc_company_finance_expense":
        "按业务类型选择：公司直接支出使用本页，付款申请形成的实付使用实付登记",
    "smart_construction_core.menu_sc_product_numbering_rule_v1":
        "独立配置项：只依赖当前公司编码规则权限，不以系统参数为前置",
    "smart_construction_core.menu_sc_product_office_asset_v1":
        "独立维护项：资产登记不依赖制度文件或证照",
    "smart_construction_core.menu_sc_product_policy_document_v1":
        "独立维护项：制度文件不依赖证照",
}

NEXT_OVERRIDES = {
    "smart_construction_core.menu_sc_p1_income_settlement":
        "按需进入收款登记：finance.receipt；需要销项开票时进入 tax.output_invoice；结果供成本归集与会计记账",
    "smart_construction_core.menu_sc_p1_expense_settlement":
        "按需进入付款申请：finance.payment_approval；取得进项发票时进入 tax.input_invoice；结果供成本归集与会计记账",
    "smart_construction_core.menu_sc_product_general_contract_settlement_v1":
        "按日常合同方向分流：支出进入付款申请，收入进入收款登记；结果供成本归集与会计记账",
    "smart_construction_core.menu_sc_settlement_order":
        "按来源合同类型回读收付款和开票结果，不复制其他结算页面的后续",
    "smart_construction_core.menu_sc_product_system_parameter_v1":
        "系统参数保存后供对应的已声明业务能力消费",
}


KNOWN_GAPS = [
    {
        "id": "GAP-01",
        "status": "release_scope_change_required",
        "evidence": "原生菜单树存在 menu_sc_material_catalog，但 product_menu_source 未发布该入口；project.material.plan 在提交前强制要求 material_catalog_id。",
        "issue": "132 个已发布办理面缺少“材料档案”。",
        "impact": "材料计划提交要求 material_catalog_id，但当前用户没有已发布的材料档案维护入口。",
        "recommendation": "接受为发布范围变更候选：复用既有 menu_sc_material_catalog 作为供应链与资源中心正式入口；该入口纳入发布前，材料计划保留“依赖未发布主数据”，不能标记为完整可运行。",
        "affected_paths": "supply.procurement → supply.inventory → material.settlement",
    },
    {
        "id": "GAP-02",
        "status": "resolved_reuse_existing_page",
        "evidence": "原生 XML 存在 menu_sc_subcontract_register 和 action_sc_subcontract_register，但产品菜单源未发布该入口。",
        "issue": "专业分包办理面缺少独立的“分包登记”发布菜单。",
        "impact": "已发布“分包成本登记”实际绑定 action_sc_subcontract_register，与原生“分包登记”使用同一动作和模型。",
        "recommendation": "不新增页面。将已发布“分包成本登记”在本组织目录中命名为“分包登记与成本确认”，承接分包登记职责，再进入分包结算。",
        "affected_paths": "resource.subcontract → contract.change → finance.payment_approval",
    },
    {
        "id": "GAP-03",
        "status": "connection_fix_required",
        "evidence": "sc.workbench.item 保存 source_model/source_res_id，但模型没有来源打开动作，发布列表也没有目标动作。",
        "issue": "工作台待办保存了来源对象，却没有声明统一的“打开来源办理”动作。",
        "impact": "用户能从待办知道存在业务，但当前页面无法按来源模型和记录 ID 稳定进入具体办理面。",
        "recommendation": "在待办契约中声明 source_model → target scene/menu/action 映射及返回参数，不新增业务页面；七类工作台路径中仅此直达动作可以基于对象身份接通。",
        "affected_paths": "work.my_queue → 项目、合同、结算、付款、发票和资源办理面",
    },
    {
        "id": "GAP-04",
        "status": "connection_fix_required",
        "evidence": "menu_sc_runtime_user_management 与 menu_sc_product_data_permission_v1 都作用于 res.users，但属于两个独立原生动作面。",
        "issue": "人员档案与业务权限配置使用同一 res.users 身份，但位于不同原生维护面。",
        "impact": "管理员可能把账号维护、员工关联、角色授权和公司范围误认为四个独立用户；当前没有声明双向对象上下文。",
        "recommendation": "保留原生两个入口，固定同一 user_id；从人员档案带入用户到数据权限，返回时定位原用户并回读角色与公司范围。",
        "affected_paths": "admin.organization → config.enterprise_access",
    },
    {
        "id": "GAP-05",
        "status": "release_scope_or_connection_required",
        "evidence": "项目中心已发布 tender.guarantee；财务保证金收退动作存在于原生 XML，但 132 个已发布办理面中没有对应入口。",
        "issue": "投标保证金的项目登记与财务收退没有在已发布产品面接通。",
        "impact": "用户可以在项目中心登记保证金，却无法从 132 个已发布办理面进入对应的保证金收退和资金结果。",
        "recommendation": "优先核对现有费用报销页能否通过业务类别安全承接；不能承接时发布既有投标保证金缴纳/退回动作，并保留 tender.guarantee 来源 ID。未裁定前保证金收退路径不得标记为可运行。",
        "affected_paths": "project.tender → finance.cash_ledger / accounting.entry_posting",
    },
]

WORKBENCH_ROUTES = [
    {
        "entry": "我的工作 / 待办事项",
        "route": "按待办来源对象打开对应业务办理面",
        "target": "来源对象声明的目标场景与办理面；覆盖项目、合同、结算、付款、发票和资源结算",
        "context": "当前公司、source_model、source_res_id、待办 ID",
        "result_location": "来源业务保存后的详情或结果页；工作台待办状态同时回读",
        "navigation_return": "任务有进入来源时回原来源；从工作台打开时回原待办列表",
        "availability": "目标设计；当前 sc.workbench.item 缺少来源打开动作，待接通",
    },
    {
        "entry": "消息通知",
        "route": "按消息关联对象打开来源业务",
        "target": "消息声明的来源场景或业务页面",
        "context": "当前公司、消息 ID、来源对象类型与对象 ID",
        "result_location": "来源业务结果页；消息已读状态在消息列表中单独回读",
        "navigation_return": "返回工作台消息列表",
        "availability": "目标设计；需声明消息到来源对象的稳定目标",
    },
    {
        "entry": "快捷办理：新建项目",
        "route": "项目中心 → 项目立项与启用 → 新项目立项",
        "target": "`project.initiation` / `smart_construction_core.menu_sc_project_initiation`",
        "context": "当前公司；可选带入客户和当前组织",
        "result_location": "项目保存后进入项目台账回读新建记录",
        "navigation_return": "从工作台发起时回工作台；从项目中心发起时回项目台账",
        "availability": "目标设计；当前工作台未声明该快捷入口",
    },
    {
        "entry": "快捷办理：登记合同",
        "route": "合同中心 → 合同登记 → 按合同类型选择收入/支出/日常合同",
        "target": "`contract.registration` / 三个合同登记办理面",
        "context": "当前公司；收入/支出合同需项目，日常合同项目可选",
        "result_location": "合同保存后进入对应合同类型的列表并定位新记录",
        "navigation_return": "有项目/中标来源时回原来源；从工作台发起时回工作台；从合同中心发起时回合同台账",
        "availability": "目标设计；当前工作台未声明该快捷入口",
    },
    {
        "entry": "快捷办理：付款申请",
        "route": "财务中心 → 付款申请与审批 → 付款申请",
        "target": "`finance.payment_approval` / `smart_construction_core.menu_sc_user_payment_apply`",
        "context": "当前公司＋项目＋合同/结算；带入收款方和可用金额",
        "result_location": "付款申请保存后进入付款申请列表并回读审批状态",
        "navigation_return": "从结算/资源页发起时回原来源；从工作台发起时回工作台；从财务中心发起时回付款申请列表",
        "availability": "目标设计；当前工作台未声明该快捷入口",
    },
    {
        "entry": "快捷办理：材料计划",
        "route": "供应链与资源中心 → 材料需求、采购申请与询比价 → 材料计划",
        "target": "`supply.procurement` / `smart_construction_core.menu_project_material_plan`",
        "context": "当前公司＋项目；带入当前项目",
        "result_location": "材料计划保存后进入材料计划列表并定位新记录",
        "navigation_return": "从项目发起时回项目台账；从工作台发起时回工作台；从供应链中心发起时回材料管理列表",
        "availability": "目标设计；当前工作台未声明该快捷入口",
    },
    {
        "entry": "快捷办理：费用报销",
        "route": "财务中心 → 费用报销与备用金 → 费用报销",
        "target": "`finance.expense_advance` / `smart_construction_core.menu_sc_reimbursement_request`",
        "context": "当前公司；项目按费用归属可选；带入当前经办人",
        "result_location": "报销保存后进入费用列表并回读单据状态",
        "navigation_return": "从工作台发起时回工作台；从财务中心发起时回费用列表",
        "availability": "目标设计；当前工作台未声明该快捷入口",
    },
]

CROSS_CENTER_LINKS = [
    {
        "source_entry": "中标管理",
        "source_menu_xmlid": "smart_construction_core.menu_sc_tender_won",
        "condition": "中标事实已确认并选择按项目合同承接",
        "source_model": "tender.bid",
        "source_record_id": "bid_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_p1_income_contract",
        "target_location": "合同中心／合同登记／收入合同",
        "carried_object": "company_id、project_id、bid_id、中标金额、中标资料附件",
        "result_location": "收入合同详情和合同台账",
        "return": "返回中标记录并回读关联 construction.contract ID",
        "availability": "合同模型已有 project_id，中标记录已有 contract_id，可建立目标映射",
    },
    {
        "source_entry": "签证变更",
        "source_menu_xmlid": "smart_construction_core.menu_sc_product_site_variation_v1",
        "condition": "现场签证已确认且需要形成合同变更",
        "source_model": "sc.site.variation",
        "source_record_id": "site_variation_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_p1_contract_change",
        "target_location": "合同中心／合同变更／合同变更",
        "carried_object": "project_id、contract_id、site_variation_id、变更金额与原始附件",
        "result_location": "合同变更详情和结算依据",
        "return": "返回原签证记录并回读关联合同变更结果",
        "availability": "目标设计；需按来源合同建立对象级进入上下文",
    },
    {
        "source_entry": "收入结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_p1_income_settlement",
        "condition": "收入结算已审批完成且达到收款条件",
        "source_model": "sc.settlement.order",
        "source_record_id": "settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_receipt_income",
        "target_location": "财务中心／收款确认与登记／收款登记",
        "carried_object": "settlement_id、contract_id、project_id、customer_id、应收金额",
        "result_location": "收款登记详情和资金台账",
        "return": "返回原收入结算单并回读收款结果",
        "availability": "收款模型已声明 contract_id/payment_request_id；结算关系可落地",
    },
    {
        "source_entry": "支出结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_p1_expense_settlement",
        "condition": "支出结算已审批完成且达到付款条件",
        "source_model": "sc.settlement.order",
        "source_record_id": "settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "target_location": "财务中心／付款申请与审批／付款申请",
        "carried_object": "settlement_id、contract_id、project_id、supplier_id、应付金额",
        "result_location": "付款申请详情和审批状态",
        "return": "返回原支出结算单并回读付款申请结果",
        "availability": "付款申请已声明 settlement_id/contract_id 关系",
    },
    {
        "source_entry": "日常合同结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_product_general_contract_settlement_v1",
        "condition": "结算方向为支出",
        "source_model": "sc.settlement.order",
        "source_record_id": "settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "target_location": "财务中心／付款申请与审批／付款申请",
        "carried_object": "general_contract_id、settlement_id、partner_id、应付金额、project_id（可为空）",
        "result_location": "付款申请详情和审批状态",
        "return": "返回原日常合同结算单并回读付款申请结果",
        "availability": "结算模型已声明 general_contract_id 和来源合同投影",
    },
    {
        "source_entry": "日常合同结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_product_general_contract_settlement_v1",
        "condition": "结算方向为收入",
        "source_model": "sc.settlement.order",
        "source_record_id": "settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_receipt_income",
        "target_location": "财务中心／收款确认与登记／收款登记",
        "carried_object": "general_contract_id、settlement_id、partner_id、应收金额、project_id（可为空）",
        "result_location": "收款登记详情和资金台账",
        "return": "返回原日常合同结算单并回读收款结果",
        "availability": "目标设计；需允许无项目的日常合同资金上下文",
    },
    {
        "source_entry": "收入结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_p1_income_settlement",
        "condition": "收入结算已确认且需要销项开票",
        "source_model": "sc.settlement.order",
        "source_record_id": "settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_invoice_application_user",
        "target_location": "税务中心／销项开票与红冲／开票申请",
        "carried_object": "settlement_id、contract_id、customer_id、可开票金额",
        "result_location": "开票申请及后续销项发票",
        "return": "返回原收入结算单并回读发票结果",
        "availability": "目标设计；需把结算作为开票申请来源对象",
    },
    {
        "source_entry": "材料进场验收",
        "source_menu_xmlid": "smart_construction_core.menu_sc_material_acceptance",
        "condition": "验收通过且需要入库",
        "source_model": "sc.material.acceptance",
        "source_record_id": "acceptance_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_material_inbound",
        "target_location": "供应链与资源中心／材料入库、出库与库存移动／材料入库",
        "carried_object": "purchase_request_id、acceptance_id、supplier_id、数量",
        "result_location": "材料入库单和项目库存",
        "return": "返回材料验收记录并回读入库结果",
        "availability": "目标设计；需声明验收到入库的对象上下文",
    },
    {
        "source_entry": "材料结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_material_settlement",
        "condition": "材料结算已确认且形成应付",
        "source_model": "sc.material.settlement",
        "source_record_id": "material_settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "target_location": "财务中心／付款申请与审批／付款申请",
        "carried_object": "material_settlement_id、supplier_id、project_id、应付金额",
        "result_location": "付款申请详情和审批状态",
        "return": "返回材料结算并回读付款结果",
        "availability": "付款模型已声明 material_settlement_id",
    },
    {
        "source_entry": "劳务结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_labor_settlement",
        "condition": "劳务结算已确认且形成应付",
        "source_model": "sc.labor.settlement",
        "source_record_id": "labor_settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "target_location": "财务中心／付款申请与审批／付款申请",
        "carried_object": "labor_settlement_id、labor_team_id、project_id、应付金额",
        "result_location": "付款申请详情和审批状态",
        "return": "返回劳务结算并回读付款结果",
        "availability": "目标设计；需核对付款申请现有劳务结算关系字段",
    },
    {
        "source_entry": "设备结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_equipment_settlement",
        "condition": "设备结算已确认且形成应付",
        "source_model": "sc.equipment.settlement",
        "source_record_id": "equipment_settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "target_location": "财务中心／付款申请与审批／付款申请",
        "carried_object": "equipment_settlement_id、supplier_id、project_id、应付金额",
        "result_location": "付款申请详情和审批状态",
        "return": "返回设备结算并回读付款结果",
        "availability": "目标设计；需核对付款申请现有设备结算关系字段",
    },
    {
        "source_entry": "租赁结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_material_rental_settlement",
        "condition": "租赁结算已确认且形成应付",
        "source_model": "sc.material.rental.settlement",
        "source_record_id": "rental_settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "target_location": "财务中心／付款申请与审批／付款申请",
        "carried_object": "rental_settlement_id、supplier_id、project_id、应付金额",
        "result_location": "付款申请详情和审批状态",
        "return": "返回租赁结算并回读付款结果",
        "availability": "付款模型已声明 rental_settlement_id",
    },
    {
        "source_entry": "分包结算",
        "source_menu_xmlid": "smart_construction_core.menu_sc_subcontract_settlement",
        "condition": "分包结算已确认且形成应付",
        "source_model": "sc.subcontract.settlement",
        "source_record_id": "subcontract_settlement_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "target_location": "财务中心／付款申请与审批／付款申请",
        "carried_object": "subcontract_settlement_id、subcontractor_id、project_id、应付金额",
        "result_location": "付款申请详情和审批状态",
        "return": "返回分包结算并回读付款结果",
        "availability": "付款模型已声明 subcontract_settlement_id",
    },
    {
        "source_entry": "实付登记",
        "source_menu_xmlid": "smart_construction_core.menu_sc_payment_execution",
        "condition": "实际付款已确认并形成资金事实",
        "source_model": "sc.payment.execution",
        "source_record_id": "payment_execution_id",
        "target_menu_xmlid": "account.menu_action_move_journal_line_form",
        "target_location": "会计账务中心／凭证编制与记账／日记账分录",
        "carried_object": "cash_fact_id、company_id、金额、业务来源模型与来源 ID",
        "result_location": "会计凭证及分录",
        "return": "返回实付登记并回读会计凭证",
        "availability": "目标设计；需声明资金事实到凭证的对象映射",
    },
    {
        "source_entry": "收款登记",
        "source_menu_xmlid": "smart_construction_core.menu_sc_receipt_income",
        "condition": "收款已确认并形成资金事实",
        "source_model": "sc.receipt.income",
        "source_record_id": "receipt_id",
        "target_menu_xmlid": "account.menu_action_move_journal_line_form",
        "target_location": "会计账务中心／凭证编制与记账／日记账分录",
        "carried_object": "cash_fact_id、company_id、金额、业务来源模型与来源 ID",
        "result_location": "会计凭证及分录",
        "return": "返回收款登记并回读会计凭证",
        "availability": "目标设计；需声明资金事实到凭证的对象映射",
    },
    {
        "source_entry": "销项开票",
        "source_menu_xmlid": "smart_construction_core.menu_sc_invoice_registration_user",
        "condition": "销项发票已登记",
        "source_model": "sc.invoice.registration",
        "source_record_id": "invoice_registration_id",
        "target_menu_xmlid": "account.menu_action_move_journal_line_form",
        "target_location": "会计账务中心／凭证编制与记账／日记账分录",
        "carried_object": "invoice_id、tax_fact_id、company_id、金额与税额",
        "result_location": "会计凭证及分录",
        "return": "返回销项发票并回读会计凭证",
        "availability": "目标设计；需按发票类型声明税务事实到凭证的映射",
    },
    {
        "source_entry": "进项发票",
        "source_menu_xmlid": "smart_construction_core.menu_sc_invoice_input",
        "condition": "进项发票已登记",
        "source_model": "sc.invoice.registration",
        "source_record_id": "invoice_registration_id",
        "target_menu_xmlid": "account.menu_action_move_journal_line_form",
        "target_location": "会计账务中心／凭证编制与记账／日记账分录",
        "carried_object": "invoice_id、tax_fact_id、company_id、金额与税额",
        "result_location": "会计凭证及分录",
        "return": "返回进项发票并回读会计凭证",
        "availability": "目标设计；需按发票类型声明税务事实到凭证的映射",
    },
    {
        "source_entry": "人员档案",
        "source_menu_xmlid": "smart_construction_core.menu_sc_runtime_user_management",
        "condition": "目标用户及其员工、部门、岗位关系已建立",
        "source_model": "res.users",
        "source_record_id": "user_id",
        "target_menu_xmlid": "smart_construction_core.menu_sc_product_data_permission_v1",
        "target_location": "产品配置／企业人员权限配置／数据权限",
        "carried_object": "user_id、company_id、employee_id、department_id、job_id",
        "result_location": "目标用户角色与允许公司范围",
        "return": "返回原人员记录并回读角色和公司范围",
        "availability": "两个办理面均为 res.users；需接通目标用户上下文",
    },
]


PRODUCT_CENTERS = json.loads(CENTER_PATH.read_text(encoding="utf-8"))["primary_centers"]
CENTER_BY_XMLID = {row["native_menu_xmlid"]: row for row in PRODUCT_CENTERS}
CENTER_BY_STABLE_KEY = {row["stable_key"]: row for row in PRODUCT_CENTERS}


def flatten_product_pages():
    source = _load_product_source()
    rows = {}
    for center in source["product_contract"]["centers"]:
        for item in center["level_two"]:
            for leaf in item.get("children") or [item]:
                binding = leaf.get("binding") or {}
                xmlid = binding.get("menu_xmlid")
                if not xmlid:
                    continue
                rows[xmlid] = {
                    "menu_xmlid": xmlid,
                    "name": leaf["name"],
                    "center_key": center["center_key"],
                    "center_name": center["name"],
                    "group_name": item["name"] if item.get("children") else "",
                    "model": binding.get("res_model") or binding.get("model") or "",
                    "action_xmlid": binding.get("action_xmlid") or "",
                }
    return rows


def validate_organization(product_pages):
    errors = []
    center_keys = [row["stable_key"] for row in PRODUCT_CENTERS]
    if len(center_keys) != 11:
        errors.append(f"expected one workbench plus ten centers, got {len(center_keys)}")
    if not center_keys or center_keys[0] != "workspace.home.workbench":
        errors.append("workbench must be the first product entry")
    placements = Counter()
    known_scenarios = set()
    allowed_roles = {
        "all_authenticated", "system_admin", "business_full",
        "business_config_admin", "executive", "owner", "pm",
        "operation_user", "finance", "cost", "accounting",
        "project_member",
    }
    for scenario_row in SCENARIOS:
        key = scenario_row["key"]
        if key in known_scenarios:
            errors.append(f"duplicate scenario key: {key}")
        known_scenarios.add(key)
        if scenario_row["owner_center"] not in CENTER_BY_STABLE_KEY:
            errors.append(f"unknown owner center for {key}: {scenario_row['owner_center']}")
        for field in ("objective", "roles", "prerequisites", "result", "pages"):
            if not scenario_row[field]:
                errors.append(f"{key} has empty {field}")
        unknown_roles = sorted(set(scenario_row["roles"]) - allowed_roles)
        if unknown_roles:
            errors.append(f"{key} has unknown roles: {unknown_roles}")
        if not scenario_row["result_objects"] and key != "work.my_queue":
            errors.append(f"{key} must declare result objects")
        for row in scenario_row["pages"]:
            menu_xmlid = row["menu_xmlid"]
            placements[menu_xmlid] += 1
            if menu_xmlid not in product_pages:
                errors.append(f"unknown released menu {menu_xmlid} in {key}")
            mode = page_mode(row)
            if mode not in {"先办", "办理", "并列", "并列选择", "辅助办理", "依据", "回读", "查看", "独立"}:
                errors.append(f"invalid mode {row['mode']} for {menu_xmlid}")
    missing = sorted(set(product_pages) - set(placements))
    extra = sorted(set(placements) - set(product_pages))
    duplicates = sorted(key for key, count in placements.items() if count != 1)
    errors.extend(f"unassigned released menu: {key}" for key in missing)
    errors.extend(f"unknown organization menu: {key}" for key in extra)
    errors.extend(f"menu must have exactly one primary organization row: {key}" for key in duplicates)
    for center_key in center_keys:
        if not any(row["center_key"] == center_key for row in product_pages.values()):
            errors.append(f"product center has no released page: {center_key}")
    return {
        "ok": not errors,
        "errors": errors,
        "released_page_count": len(product_pages),
        "organized_page_count": len(placements),
        "scenario_count": len(SCENARIOS),
        "unique_page_count": len(set(placements)),
        "duplicate_page_count": len(duplicates),
        "unassigned_page_count": len(missing),
        "unknown_page_count": len(extra),
    }


def relation_text(scenario_row, pages, index, product_pages):
    current = pages[index]
    override = RELATION_OVERRIDES.get(current["menu_xmlid"])
    current_mode = page_mode(current)
    previous = next(
        (
            row
            for row in reversed(pages[:index])
            if page_mode(row) in {"先办", "办理", "并列选择"}
        ),
        None,
    )
    following = pages[index + 1] if index + 1 < len(pages) else None
    references = [
        row for row in pages
        if page_mode(row) in {"依据", "辅助办理"} and row is not current
    ]
    peers = [
        row for row in pages
        if page_mode(row) == "并列" and row is not current
    ]
    parts = []
    if override:
        parts.append(override)
        if references:
            parts.append(
                "可引用："
                + "、".join(product_pages[row["menu_xmlid"]]["name"] for row in references)
            )
        return clean_join(parts)
    alternative = alternative_group_for(current["menu_xmlid"])
    if alternative:
        members = [
            product_pages[item["menu_xmlid"]]["name"]
            for item in pages
            if alternative_group_for(item["menu_xmlid"]) == alternative
        ]
        parts.append(f"并列选择：{' / '.join(members)}；按适用业务类型选择一项")
    elif current_mode == "独立":
        parts.append("本组独立维护项，无同组前置")
    elif current_mode == "辅助办理":
        parts.append("辅助办理：可在主流程前或办理中按需维护，不作为固定前置")
    elif current_mode == "并列":
        parts.append(
            "并列办理："
            + "、".join(product_pages[row["menu_xmlid"]]["name"] for row in peers)
            if peers
            else "同组并列办理"
        )
        if previous:
            parts.append(f"共同承接：{product_pages[previous['menu_xmlid']]['name']}")
    elif current_mode == "依据":
        parts.append("依据查阅，无独立办理顺序")
    elif previous:
        previous_alternative = alternative_group_for(previous["menu_xmlid"])
        if previous_alternative:
            parts.append(f"同组前序：{ALTERNATIVE_GROUPS[previous_alternative]['label']}（按类型选择）")
        else:
            parts.append(f"同组前序：{product_pages[previous['menu_xmlid']]['name']}")
    else:
        parts.append("启动依据：" + "；".join(scenario_row["prerequisites"][:3]))
    if references:
        parts.append("依据查阅：" + "、".join(product_pages[row["menu_xmlid"]]["name"] for row in references))
    if current_mode == "并列":
        parts.append("可与同组办理面并列使用")
    return clean_join(parts)


def next_text(scenario_row, pages, index, product_pages):
    current = pages[index]
    override = NEXT_OVERRIDES.get(current["menu_xmlid"])
    if override:
        return override
    current_mode = page_mode(current)
    current_alternative = alternative_group_for(current["menu_xmlid"])
    following = next(
        (
            row
            for row in pages[index + 1:]
            if page_mode(row) in {"先办", "办理"}
            and (
                not current_alternative
                or alternative_group_for(row["menu_xmlid"]) != current_alternative
            )
        ),
        None,
    )
    parts = []
    if current_mode == "依据":
        parts.append("作为同组办理面的查阅依据")
    elif current_mode == "辅助办理":
        parts.append("维护结果供同组办理面引用")
    elif current_mode in {"查看", "回读"}:
        parts.append("以当前页面显示查询或回读结果")
    elif following:
        parts.append(f"同组后续：{product_pages[following['menu_xmlid']]['name']}")
    parts.extend(scenario_row["next_steps"])
    if not parts:
        parts.append("无已发布后续办理面；完成后在本页或默认列表回读本页结果")
    return clean_join(parts)


def context_text(scenario_row, page_row, product_pages, index):
    reference = PAGE_REFERENCE_OVERRIDES.get(page_row["menu_xmlid"])
    product_page = product_pages[page_row["menu_xmlid"]]
    center = product_page["center_name"]
    group_label = product_page["group_name"] or product_page["name"]
    context = PAGE_CONTEXT_OVERRIDES.get(page_row["menu_xmlid"])
    relation = RELATION_OVERRIDES.get(page_row["menu_xmlid"])
    if not context:
        mode = page_mode(page_row)
        current_alternative = alternative_group_for(page_row["menu_xmlid"])
        previous = next(
            (
                row for row in reversed(scenario_row["pages"][:index])
                if page_mode(row) in {"先办", "办理", "并列选择"}
            ),
            None,
        ) if not current_alternative else None
        if mode in {"辅助办理", "独立"}:
            required = scenario_row["context"].split("；从", 1)[0]
        elif relation:
            required = clean_join([
                scenario_row["context"].split("；从", 1)[0],
                relation,
            ])
        elif previous:
            previous_alternative = alternative_group_for(previous["menu_xmlid"])
            previous_name = (
                ALTERNATIVE_GROUPS[previous_alternative]["label"]
                if previous_alternative
                else product_pages[previous["menu_xmlid"]]["name"]
            )
            required = clean_join([
                scenario_row["context"].split("；从", 1)[0],
                f"前置办理：{previous_name}",
            ])
        else:
            required = clean_join(scenario_row["prerequisites"][:3])
        if mode in {"查看", "回读", "依据"}:
            create_or_choose = "仅选择查询范围或业务对象，不新建业务记录"
            carry = f"续办时携带 {product_page['model'] or '业务对象'} ID 和筛选上下文"
        else:
            create_or_choose = f"可新建或选择{product_page['name']}对应的业务记录"
            carry = f"续办时携带 {product_page['model'] or '业务记录'} ID"
        context = clean_join([
            f"必须已有：{required}",
            f"可选择或新建：{create_or_choose}",
            carry,
        ])
    base = (
        f"必须/可选事实：{context}；结果展示：{page_output(page_row, product_page)}后"
        f"到{center}/{group_label}回读；执行返回：有来源则回原来源，无来源则回该列表"
    )
    return f"{base}；{reference}" if reference else base


def result_for_alternative(xmlid):
    for key, value in ALTERNATIVE_GROUPS.items():
        if xmlid in value["pages"]:
            return key
    return ""


def alternative_group_for(xmlid):
    return result_for_alternative(xmlid)


def page_mode(page_row):
    if alternative_group_for(page_row["menu_xmlid"]):
        return "并列选择"
    if page_row["menu_xmlid"] in INDEPENDENT_PAGES:
        return "独立"
    return MODE_OVERRIDES.get(page_row["menu_xmlid"], page_row["mode"])


def page_output(page_row, product_page):
    xmlid = page_row["menu_xmlid"]
    if xmlid in PAGE_OUTPUT_OVERRIDES:
        return PAGE_OUTPUT_OVERRIDES[xmlid]
    mode = page_mode(page_row)
    if mode in {"查看", "回读", "依据"}:
        return f"返回{product_page['name']}的当前查询结果"
    model = product_page.get("model")
    if model:
        return f"产生或更新 {model} 业务记录（{product_page['name']}）"
    return f"完成{product_page['name']}的页面动作"


def clean_join(parts):
    values = []
    for part in parts:
        value = str(part or "").strip().rstrip("。；")
        if value and value not in values:
            values.append(value)
    return "；".join(values)


def build_payload(product_pages):
    scenarios = []
    for scenario_index, row in enumerate(SCENARIOS):
        pages = []
        for index, page_row in enumerate(row["pages"]):
            product_page = product_pages[page_row["menu_xmlid"]]
            pages.append({
                **page_row,
                "mode": page_mode(page_row),
                "source_menu_name": product_page["name"],
                "menu_name": PAGE_DISPLAY_OVERRIDES.get(
                    page_row["menu_xmlid"],
                    product_page["name"],
                ),
                "center_key": product_page["center_key"],
                "center_name": product_page["center_name"],
                "native_group_name": product_page["group_name"],
                "alternative_group": alternative_group_for(page_row["menu_xmlid"]),
                "page_output": page_output(page_row, product_page),
                "preceding_or_related": relation_text(row, row["pages"], index, product_pages),
                "following": next_text(row, row["pages"], index, product_pages),
                "entry_context_and_return": context_text(row, page_row, product_pages, index),
                "shared_reference": PAGE_REFERENCE_OVERRIDES.get(page_row["menu_xmlid"], ""),
                "scenario_sequence": scenario_index,
                "page_sequence": index,
            })
        scenarios.append({**row, "pages": pages})
    validation = validate_organization(product_pages)
    return {
        "schema": "sce.product_scenario_organization.v1",
        "status": APPROVAL_STATUS,
        "approved_at": APPROVAL_DATE,
        "formal_product_layer": "P1",
        "module": "smart_construction_core",
        "basis": {
            "center_count": len(PRODUCT_CENTERS),
            "center_source": "config/product_primary_center_baseline_v1.json",
            "page_source": "addons/smart_construction_core/data/product_menu_source.json",
            "page_identity": "menu_xmlid",
            "multi_reference_rule": "One primary organization row per released page; shared use is described as references to the same identity.",
        },
        "validation": validation,
        "scenarios": scenarios,
        "workbench_routes": WORKBENCH_ROUTES,
        "cross_center_links": CROSS_CENTER_LINKS,
        "gaps": KNOWN_GAPS,
    }


def runtime_intent(page_row):
    if page_row.get("declared_intent"):
        return page_row["declared_intent"]
    menu_xmlid = page_row["menu_xmlid"]
    if menu_xmlid in MASTER_DATA_MENU_XMLIDS:
        return "master_data"
    if page_row["center_key"] == "construction.center.reporting":
        return "report"
    if page_row["mode"] in HANDLE_MODES:
        return "handle"
    return "view"


def build_runtime_surface(payload):
    scenarios = []
    binding_count = 0
    for scenario_sequence, scenario_row in enumerate(payload["scenarios"], start=1):
        intents = {}
        bindings = []
        for page_sequence, page_row in enumerate(scenario_row["pages"], start=1):
            intent = runtime_intent(page_row)
            intents.setdefault(intent, []).append(page_row["menu_xmlid"])
            bindings.append({
                "menu_key": page_row["menu_xmlid"],
                "intent": intent,
                "sequence": page_sequence,
                "center_key": page_row["center_key"],
                "center_name": page_row["center_name"],
                "center_sequence": next(
                    center["sequence"]
                    for center in PRODUCT_CENTERS
                    if center["stable_key"] == page_row["center_key"]
                ),
            })
            binding_count += 1
        scenarios.append({
            "key": scenario_row["key"],
            "name": scenario_row["name"],
            "owner_center": scenario_row["owner_center"],
            "owner_center_name": CENTER_BY_STABLE_KEY[scenario_row["owner_center"]]["name"],
            "type": "COMPOSITE",
            "active": True,
            "sequence": scenario_sequence,
            "intents": intents,
            "bindings": bindings,
        })
    return {
        "schema": "construction.scenario_product_surface.v2",
        "status": "APPROVED_AS_PROJECTION_INPUT",
        "approved_at": APPROVAL_DATE,
        "module": "smart_construction_core",
        "product_layer": "P1",
        "coverage_scope": "released",
        "source_design": [
            "config/product_scenario_organization_v1.json",
            "config/product_primary_center_baseline_v1.json",
            "addons/smart_construction_core/data/product_menu_source.json",
        ],
        "taxonomy": {
            "L0": "product_center",
            "L1": "product_scenario",
            "L2": "user_intent",
            "L3": "capability_menu_action",
            "note": (
                "Centers and center membership come from the published product policy. "
                "The 46 scenarios are the approved business-result organization over the "
                "132 released pages. Counts are derived from those declarations."
            ),
        },
        "authority_note": (
            "Business-loop composition over the released standard menus. The released "
            "menu set is resolved from product_menu_source, never fixed here. This is NOT "
            "a scene registry and NOT scene content; scene content/version authority "
            "remains sc.scene / smart_construction_scene.scene_registry."
        ),
        "intent_labels": {
            "handle": "办理",
            "view": "查看",
            "approve": "审批",
            "report": "报表",
            "master_data": "基础信息维护",
        },
        "direct_platform_pages": [
            {"menu_xmlid": menu_xmlid, "kind": kind}
            for menu_xmlid, kind in DIRECT_PLATFORM_PAGES
        ],
        "scenarios": scenarios,
        "validation": {
            "scenario_count": len(scenarios),
            "binding_count": binding_count,
            "unique_menu_count": len({
                binding["menu_key"]
                for scenario in scenarios
                for binding in scenario["bindings"]
            }),
            "direct_platform_count": len(DIRECT_PLATFORM_PAGES),
        },
    }


def md_escape(value):
    return str(value or "").replace("|", "\\|").replace("\n", "<br>")


def render_markdown(payload):
    lines = [
        "# 132 个办理面业务组织整合",
        "",
        f"- 状态：`{payload['status']}`",
        f"- 批准日期：`{payload['approved_at']}`",
        f"- 已发布办理面：`{payload['validation']['released_page_count']}`",
        f"- 已组织办理面：`{payload['validation']['organized_page_count']}`",
        f"- 业务办理分组（已定稿场景）：`{payload['validation']['scenario_count']}`",
        f"- 去重覆盖：`{payload['validation']['unique_page_count']}/{payload['validation']['released_page_count']}`",
        f"- 运行时场景种子：`{SURFACE_OUTPUT.relative_to(ROOT)}`",
        "",
        "## 组织口径",
        "",
        "- 十个业务中心和工作台是固定导航骨架，不随场景数量变化。",
        "- 办理面以稳定菜单 XMLID 标识；每个办理面在总表中只有一个主归属。",
        "- 工作台和跨中心业务通过引用同一办理面身份衔接，不复制页面或业务事实。",
        "- “先办、办理、并列、依据、回读”只描述用户办理关系，不改变后端权限和业务状态。",
        "",
        "## 场景定义摘要",
        "",
        "| 主责中心 | 场景 | 用户完成的结果 | 主要角色 | 前置事实 | 结果对象 | 后续衔接 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for scenario_row in payload["scenarios"]:
        center = CENTER_BY_STABLE_KEY[scenario_row["owner_center"]]
        lines.append(
            "| %s | %s<br>`%s` | %s | %s | %s | %s | %s |"
            % (
                md_escape(center["name"]),
                md_escape(scenario_row["name"]),
                md_escape(scenario_row["key"]),
                md_escape(scenario_row["objective"]),
                md_escape(", ".join(scenario_row["roles"])),
                md_escape(clean_join(scenario_row["prerequisites"])),
                md_escape(", ".join(scenario_row["result_objects"]) or scenario_row["result"]),
                md_escape(clean_join(scenario_row["next_steps"]) or scenario_row["result"]),
            )
        )
    lines.extend([
        "",
        "## 一、完整组织总表",
        "",
        "| 中心／工作台 | 业务办理分组 | 办理面身份及名称 | 在办理中的用途 | 前置或关联办理面 | 后续办理面 | 进入上下文与返回位置 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    center_rows = defaultdict(list)
    for scenario_row in payload["scenarios"]:
        for page_row in scenario_row["pages"]:
            center_rows[page_row["center_key"]].append((scenario_row, page_row))
    for center in sorted(PRODUCT_CENTERS, key=lambda row: row["sequence"]):
        for scenario_row, page_row in sorted(
            center_rows[center["stable_key"]],
            key=lambda item: (
                item[1]["scenario_sequence"],
                item[1]["page_sequence"],
                item[0]["key"],
            ),
        ):
            usage = (
                f"{page_row['mode']}：{page_row['purpose'].rstrip('。')}"
                f"；本页产出：{page_row['page_output']}"
            )
            if page_row["shared_reference"]:
                usage = clean_join([usage, page_row["shared_reference"]])
            lines.append(
                "| %s | %s<br>`%s` | `%s`<br>%s | %s | %s | %s | %s |"
                % (
                    md_escape(center["name"]),
                    md_escape(scenario_row["name"]),
                    md_escape(scenario_row["key"]),
                    md_escape(page_row["menu_xmlid"]),
                    md_escape(page_row["menu_name"]),
                    md_escape(usage),
                    md_escape(page_row["preceding_or_related"]),
                    md_escape(page_row["following"]),
                    md_escape(page_row["entry_context_and_return"]),
                )
            )
    lines.extend([
        "",
        "## 二、按中心展开的完整目录",
        "",
    ])
    scenarios_by_owner = defaultdict(list)
    for scenario_row in payload["scenarios"]:
        scenarios_by_owner[scenario_row["owner_center"]].append(scenario_row)
    for center in sorted(PRODUCT_CENTERS, key=lambda row: row["sequence"]):
        lines.append(f"### {center['name']}")
        lines.append("")
        owner_scenarios = scenarios_by_owner[center["stable_key"]]
        if not owner_scenarios:
            lines.append("- 当前没有已发布办理面。")
            lines.append("")
            continue
        for scenario_row in owner_scenarios:
            lines.append(
                f"- **{scenario_row['name']}** (`{scenario_row['key']}`)"
                f"：{scenario_row['objective']}"
            )
            for page_row in scenario_row["pages"]:
                if page_row["center_key"] == center["stable_key"]:
                    ownership = "主归属"
                else:
                    ownership = (
                        f"共享引用既有页面，实际主归属：{page_row['center_name']}；"
                        f"{page_row['entry_context_and_return']}"
                    )
                cross = page_row["following"]
                if page_row["following"]:
                    cross = f"；后续：{page_row['following']}"
                else:
                    cross = ""
                lines.append(
                    f"  - {page_row['menu_name']}（`{page_row['menu_xmlid']}`，"
                    f"{page_row['mode']}；{ownership}；本页产出：{page_row['page_output']}）{cross}"
                )
        lines.append("")
    lines.extend([
        "## 三、工作台入口安排",
        "",
        "| 工作台入口 | 进入路径 | 目标办理面 | 进入上下文 | 保存后的结果展示 | 执行返回位置 | 当前状态 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in payload["workbench_routes"]:
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s |"
            % (
                md_escape(row["entry"]),
                md_escape(row["route"]),
                md_escape(row["target"]),
                md_escape(row["context"]),
                md_escape(row["result_location"]),
                md_escape(row["navigation_return"]),
                md_escape(row["availability"]),
            )
        )
    lines.extend([
        "",
        "## 四、跨中心与跨分组衔接",
        "",
        "| 来源办理面 | 触发条件 | 来源模型/记录 | 目标办理面 XMLID | 目标中心／分组 | 携带对象 | 结果展示 | 返回位置 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in payload["cross_center_links"]:
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                md_escape(
                    f"{row['source_entry']}<br>`{row['source_menu_xmlid']}`"
                ),
                md_escape(row["condition"]),
                md_escape(f"{row['source_model']} / {row['source_record_id']}"),
                md_escape(row["target_menu_xmlid"]),
                md_escape(row["target_location"]),
                md_escape(row["carried_object"]),
                md_escape(row["result_location"]),
                md_escape(row["return"]),
            )
        )
    lines.extend([
        "",
        "## 五、组织缺口清单",
        "",
        "| 编号／状态 | 事实依据 | 问题 | 影响 | 裁定／处理 | 受影响路径 |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for gap in payload["gaps"]:
        lines.append(
            "| %s<br>`%s` | %s | %s | %s | %s | %s |"
            % (
                md_escape(gap["id"]),
                md_escape(gap["status"]),
                md_escape(gap["evidence"]),
                md_escape(gap["issue"]),
                md_escape(gap["impact"]),
                md_escape(gap["recommendation"]),
                md_escape(gap["affected_paths"]),
            )
        )
    lines.extend([
        "",
        "缺口裁定状态：",
        "",
        "- `resolved_reuse_existing_page`：已由现有办理面承接，不需要新增同名页面。",
        "- `connection_fix_required`：页面存在，但只有对象上下文、目标动作和返回链补齐后才能标记为完整可运行。",
        "- `release_scope_change_required` / `release_scope_or_connection_required`：当前 132 面不能独立闭合，受影响路径保持待实现，不计入组织定稿后的已运行结果。",
    ])
    lines.extend([
        "",
        "## 定稿与实施门禁",
        "",
        "- 132 个已发布办理面必须全部出现在总表中且身份唯一。",
        "- 每个中心和工作台必须保持既定产品身份；场景只能组织中心内或跨中心的办理关系。",
        "- 工作台快捷办理和待办必须能回到来源业务对象与返回位置。",
        "- 组织设计已定稿：46 个业务分组作为产品场景种子输入，五项缺口继续保留其处理状态。",
        "- 候选种子与发布组合生成：必须忠实保留缺口状态和待实现连接，不能把目标设计转换为已可用能力。",
        "- 可运行发布：只有受影响路径的实际缺口关闭并完成对应运行验证后，才计入可运行结果。",
        "",
    ])
    return "\n".join(lines)


def main():
    product_pages = flatten_product_pages()
    payload = build_payload(product_pages)
    runtime_surface = build_runtime_surface(payload)
    if not payload["validation"]["ok"]:
        for error in payload["validation"]["errors"]:
            print(f"[FAIL] {error}")
        raise SystemExit(1)
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    MARKDOWN_OUTPUT.write_text(render_markdown(payload), encoding="utf-8")
    SURFACE_OUTPUT.write_text(
        json.dumps(runtime_surface, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        **payload["validation"],
        "runtime_surface": runtime_surface["validation"],
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
