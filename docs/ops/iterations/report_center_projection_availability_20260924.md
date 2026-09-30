# 报表中心投影页可用性与显式创建入口定性（2026-09-24）

> 归档说明（2026-09-28）：本件迁入自 `audit/formal-entry-gap-intake@28d2e05e`，下文运行观察、对象 ID 和验收状态属于 2026-09-24 原候选及环境；不是当前 main 的新运行结果。拟议字段映射与创建能力仍待产品确认及责任层实施，本轮仅恢复交接文档，不升级任何入口验收状态。

来源缺口：`frontend_shared_foundation_gap_audit_20260909.md` → `G-F3-03 / B04`、`G-F2-05 / B05`。
本记录只写定位结论与处置归属，不改产品代码、不伪造前端行、不放宽过滤或权限。

## 层与边界声明

- Formal Product Layer：P1 建设行业标准产品的投影/契约边界 + P4 验证记录。
- Layer Target：`smart_construction_core` 的 `sc.optional.product.projection` 边界与
  `models/projection_relation_lifecycle.py`；前端关系控件只做契约消费。
- Standard vs User-Specific：投影内容归属由架构注册表裁定，不属前端或运行时配置。
- Why Here：0 行的成因在投影边界与投影刷新路径，不在列表查询或渲染。
- Why Not Elsewhere：不改前端渲染、不改 action domain、不新增角色权限。
- Blast Radius：报表中心三个菜单（资金报表/成本报表/项目报表）与 AR/AP 汇总页行内对象按钮。

## 一、报表中心投影页恒为 0 行（G-F3-03 / B04）

### 复现

受管 `local.dev`（`sc_dev_demo`），menu 366「资金报表」→ action 699 → `sc.fund.daily.summary`；
menu 592「成本报表」→ action 826 → `sc.comprehensive.cost.summary`。列表 0 行，行内「收款登记」
对象按钮无行可点。

### 定位（三种候选原因逐一排除）

| 候选原因 | 判定 | 依据 |
|---|---|---|
| 查询或上下文错误 | **排除** | `pg_get_viewdef` 三个视图均以 `WHERE false` 结尾，恒空不是查询结果问题 |
| 角色权限过滤 | **排除** | 视图定义层即恒空（管理员同为 0 行），非记录规则过滤 |
| 环境确实没有符合条件的数据 | **排除** | 来源事实存在：`sc_finance_business_fact` 3 行；投影根本不读事实 |

实际成因：**P1 可选产品投影边界未填充**。

- `addons/smart_construction_core/models/optional_product_projection.py` 的
  `_create_empty_projection_view()` 以 `CREATE OR REPLACE VIEW <table> AS SELECT <typed columns> WHERE FALSE`
  建立强制类型视图；`init()` 调用它，所以 `sc_fund_daily_summary`、`sc_comprehensive_cost_summary`、
  `sc_ar_ap_report_summary` 恒为空。实测定义尾部：`... WHERE false;`，行数均为 0。
- 该 mixin 在架构注册表 `docs/architecture/backend_business_model_family_registry_v1.json`
  登记为 `family="compatibility bridges and native extensions"`、`responsibility_type="compatibility/bridge"`、
  `boundary_rule="Extensions may add anchors and hooks; they must not duplicate native transaction ownership."`、
  `status="clear"`。即：P1 只声明类型化边界，内容由可选/客户产品层拥有，不在本构建内。
- 守卫测试 `addons/smart_construction_core/tests/test_ar_ap_projection_relation_lifecycle.py`
  `OptionalProjectionProductIndependenceTests` 明确断言该层**不得**读取客户交接契约或 `ir_module_module`，
  并保留 `PRODUCT_PROJECTION_RELATION_CONFLICT` 冲突保护。
- `sc_ar_ap_project_summary` / `sc_ar_ap_company_summary` 是真实表（`relkind='r'`、0 行），
  只由迁移期 `models/projection_relation_lifecycle.py::refresh_ar_ap_project_summary(cr, projection_select_sql, …)`
  写入（`migrations/17.0.0.73/pre-migration.py` 引用）；当前环境无运行时/cron 入口。

### 正确呈现要求与最小修改路径

- 前端不得为让按钮出现而伪造行、移除过滤或扩权；当前空列表是契约的正确表达。
- 「收款登记」按钮目标为 `smart_construction_core.action_sc_receipt_income`（= action 637），
  即已经验收过的同一收款列表 URL（`/a/637?menu_id=338&action_id=637`）。缺的只是**投影行的触发**，
  不是目标路由。
- 最小修改路径（后端/产品层，不由 Web 执行器改）：由投影所属层按既定事实源填充投影
  （迁移期 refresh 的运行时化，或可选产品模块提供的视图替换）；在此之前该菜单与行内按钮
  保持「可用但无数据」的真实状态，不做前端补偿。

## 二、显式创建入口 `not_available` 定性（G-F2-05 / B05）

### 定位

入口可见性由契约驱动，前端消费正确：

- `frontend/apps/web/src/pages/contractForm/useRecordFormFieldSchemas.ts:129` 固定提供
  `many2oneCreateToken:'__create__'`、`many2oneSearchToken:'__search_more__'`、`many2oneOpenToken:'__open_record__'`。
- `ProfessionalMany2oneFieldControl.vue` 的 `createEntryVisible`
  = `relationCreateMode ∈ {page,dialog} && Boolean(many2oneCreateToken)`。
- `frontend/apps/web/src/pages/contractForm/relationDescriptor.ts:230` 的 `relationCreateMode`
  仅在契约关系描述符同时给出 `create_mode`、`can_create` 与 `actionId`（dialog 另需 `menuId`，quick 需 `can_create`）
  时才返回 `page/dialog/quick`，否则 `none`。
- 契约关系策略按 `(relation, model, field_name)` **逐项可选**下发：`core_extension.py` 中
  `account.tax`+`construction.contract` 给出 `can_create: True, quick_create: True`；
  `construction.contract.original_contract_id` 明确 `can_create: False, create_mode: "disabled"`；
  未登记的 `(relation, model, field)` 走默认（无策略 → 无创建入口）。

### 归属判定

属**后端能力/契约缺失（产品层范围决定）**，不属前端未消费已有能力：

- 受管验收所用对象的关联字段在契约中**未声明**可执行创建模式，故前端不渲染创建入口——这是正确表达。
- 因此不能为「闭环」强行开放创建；若业务确需该页内联创建，应由产品层新增最小关系策略条目，
  再按该条目的 `actionId`/权限验收。该产品决策不在 Web 执行器权限内。
- 「无权限时不提供可执行创建入口」在无入口时无法与「入口不存在」区分，故保持未验收。

## 验收边界

- 本记录为定位与归属结论 + 缺口清单更新，未改产品代码。
- 未纳入：投影内容实现（后端/产品层任务）、为验收伪造投影行、放宽权限或过滤。
