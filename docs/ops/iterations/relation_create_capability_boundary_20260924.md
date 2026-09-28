# 关系创建能力边界收口（2026-09-24）

> 归档说明（2026-09-28）：本件迁入自 `audit/formal-entry-gap-intake@28d2e05e`，下文运行观察、对象 ID 和验收状态属于 2026-09-24 原候选及环境；不是当前 main 的新运行结果。拟议字段映射与创建能力仍待产品确认及责任层实施，本轮仅恢复交接文档，不升级任何入口验收状态。

来源缺口：`frontend_shared_foundation_gap_audit_20260909.md` → `G-F2-05 / B05`。
本文件按关系对象给出现有能力分类与待产品确认项。**`not_available` 是当前能力状态，不等于是缺陷，
也不等于产品已决定永不支持。** 前端只展示后端提供的原因/契约声明，不自行编造权限解释。

## 1. 机制（已核实的真实链路）

- 契约按 `(relation, model, field_name)` 逐项下发关系策略：
  `smart_construction_core/core_extension.py::smart_core_relation_entry_policy`；
  经 `smart_core/utils/contract_governance_labels.py:174` 投影为 `create_mode`（默认 `"disabled"`）。
- 前端 `pages/contractForm/relationDescriptor.ts:230 relationCreateMode` 仅在
  `create_mode` + `can_create` + `actionId`（dialog 另需 `menuId`）齐备时返回 `page/dialog/quick`，否则 `none`。
- 前端 `useRecordFormFieldSchemas.ts:129` 恒定提供 `many2oneCreateToken='__create__'`
  （token 不是权限位）；`ProfessionalMany2oneFieldControl.vue` 的 `createEntryVisible`
  = `relationCreateMode ∈ {page,dialog} && Boolean(token)`。
- 结论：创建入口是**契约门控**，不是前端缺失能力。

## 2. 关系对象分类

| # | 关系对象（model.field → relation） | 契约现状 | 分类 | 应有行为 |
|---|---|---|---|---|
| 1 | `construction.contract.tax_id` / `sc.general.contract.tax_id` → `account.tax` | `can_create: True`, `quick_create: True`，含 `default_vals` 与受限 `domain` | **产品允许，已有创建契约** | 验证创建入口与闭环（税率快速创建）；失败可恢复 |
| 2 | `construction.contract.original_contract_id` → `construction.contract` | 显式 `can_create: False`, `create_mode: "disabled"` | **产品明确不支持（显式禁用）** | 正确隐藏入口；保留「搜索更多」 |
| 3 | `sc.self.funding.registration.partner_id` → `res.partner`，category `finance.self_funding.refund` | `can_create: False`，domain 限定为有余额的承包人 | **产品明确不支持（受限选择集）** | 正确隐藏入口；只允许在受控集合内选择 |
| 4 | `sc.expense.claim.partner_id` → `res.partner`，category `finance.deduction.bill` | `can_create: False`，domain 限定为责任方 | **产品明确不支持（受限选择集）** | 同上 |
| 5 | `project.project.partner_id` → `res.partner`（上批受管验收所用对象） | 无策略条目（`None` → `create_mode="disabled"`） | **未声明** | 当前正确表现为无入口；是否应支持见 §3 |
| 6 | 其余未登记 `(relation, model, field)` | 无策略条目 | **未声明** | 同上，逐个按产品需要补齐，不批量开放 |

**当前角色无权限**（第 4 类，非矩阵行）：模型级 ACL 已在 `security/ir.model.access.csv` 收口，例如
`sc.finance.business.fact` 的项目用户/经理为 `(1,0,0,0)` 只读。此类**保留拒绝、不扩权**；
前端不做权限推断，直接呈现后端拒绝。

## 3. 待产品确认项（不自行决定）

1. `project.project.partner_id`（客户/业主关系）是否应提供内联创建入口？
   - 若「是」：由产品层在 `smart_core_relation_entry_policy` 增加最小策略条目
     （`can_create`、`create_mode`、`action_id`/`menu_id`、`domain`、`ui_labels`），并按该条目验收创建闭环。
   - 若「否」：保持无入口即为正确表达，本条可关闭为「产品明确不支持」，无需改代码。
2. §2 第 6 类里是否还有正式入口在业务上需要「新增关联对象」？需产品逐项确认，避免批量开放。
3. 关系创建失败后的重试语义（是否幂等、失败提示文案）是否作为统一产品要求下发。

## 4. 前端责任边界

- 只依据契约 `create_mode`/`can_create`/`action_id` 决定入口可见性；**不**依据角色名推断权限，
  也**不**在无契约时自行开放创建。
- 创建意图与已选值继续分离（上批已完成）；创建失败不得伪装成关联被清空。
- 本次**无前端改动**：分类结论表明现有前端消费正确。

## 5. 验收边界

- §2 第 1 类（税率快速创建）是唯一的「已有契约」可执行创建：其入口与闭环仍为**未验收**，
  待产品/受管环境给出可执行入口后单独验收；在此之前不宣称创建闭环通过。
- 第 2–4 类属「正确隐藏」，可由现有契约断言覆盖（`smart_core/tests/test_relation_entry_contract.py`）。
- 第 5–6 类保持 `not_available`，等待 §3 的产品结论。
