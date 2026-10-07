# 字段策略声明一致性（field policy declaration parity）v1

## 1. 适用对象与责任层

- Formal Product Layer: P1 施工行业标准产品（`smart_construction_core`）。
- Layer Target: `ui.business.config.contract` 的模型级 `*_p1_form_business_facts_v1` 声明体
  与同一模型上 action 级入口契约声明之间的字段策略一致性。
- 机制（P0 通用投影）不在本文范围：`smart_core` 的契约装配 / 字段策略投影只做“收紧”，
  前端只做通用契约渲染。本文约束的是 P1 声明体不得与入口声明自相矛盾。

## 2. 规则（判定口径）

一个 **模型级** 表单契约（`action_id` 为空，因此作用于该模型的所有界面）不得对某个字段声明
**无条件 `readonly: True`**，当且仅当：

1. 该模型存在 action 级入口契约声明了同一字段；且
2. 这些入口契约中**没有任何一个**把该字段声明为只读。

满足以上两条即为 **矛盾声明**，门禁直接 FAIL。

判据的理由（泄漏机制，已在运行态复现）：

- `smart_core/core/view_orchestrator.py::_apply_field_display_policy` 只置 `true`、不回松。
  模型级契约的无条件只读会把交付字段节点压成只读。
- `statusContract.widgetStatus` 仍然按原生 arch 取模量结果（例如 `auth=edit`）。
  同一个交付事实的两个投影互相矛盾。
- 前端读只事实规则（`frontend/apps/web/src/components/template/formSection.mapper.ts`
  的 `readonlyFactIsPresentable`）会丢弃“只读且空值”的字段，该字段因此从页面正文消失
  （实际现象：借款办理的 `due_date` 到期日消失，同 arch 的同族字段 `document_date` /
  `amount` / `purpose` 仍渲染）。

## 3. 必须区分的情形（不得误判为矛盾）

- **真实字段权限 / ACL 拒绝**：`auth="none"`、组权限拒绝、记录规则导致不可见，属于真实权限
  边界，**不得**用本门禁或任何 `critical` 覆盖。
- **合法隐藏规则**：原生 arch 的 `invisible` 条件（如 `state == 'legacy_confirmed'`）是合法
  业务口径；本门禁只针对“无条件只读”与入口声明的冲突，不改变条件表达式。
- **未识别 widget 造成的错误默认值**：属于 P0 投影责任，按投影缺陷修复，不得在此加模型特判。
- **系统生成 / 计算 / 工作流字段**：`name`(ir.sequence)、`create_date`、`amount`、`state` 等
  由系统或工作流书写，模型级无条件只读是正确声明，不构成矛盾（因为入口契约不会把它们声明为
  可编辑）。

## 4. 本批次收口的清单（14 个字段 / 6 个模型级声明体）

修复动作：仅移除“应由用户录入”字段上的无条件 `readonly`，保留 `sequence` 排序语义；
`*_display` 镜像事实的只读策略仍由这些模型级声明体承载，声明体不退役。

| 模型 | 模型级声明记录 | 移除的无条件只读字段 |
| --- | --- | --- |
| `sc.financing.loan` | `business_config_contract_sc_financing_loan_p1_form_business_facts_v1` | `due_date` |
| `payment.request` | `business_config_contract_payment_request_p1_form_business_facts_v1` | `name` |
| `sc.fund.account.operation` | `business_config_contract_sc_fund_account_operation_p1_form_business_facts_v1` | `note` |
| `sc.labor.request` | `business_config_contract_sc_labor_request_p1_form_business_facts_v1` | `request_date`, `contractor_id`, `note` |
| `sc.equipment.request` | `business_config_contract_sc_equipment_request_p1_form_business_facts_v1` | `project_id`, `supplier_id`, `request_date`, `note` |
| `sc.equipment.settlement` | `business_config_contract_sc_equipment_settlement_p1_form_business_facts_v1` | `name`, `project_id`, `settlement_date`, `supplier_id` |

修复前：`contradiction_count = 14`（门禁 FAIL，逐条列出）。修复后：`contradiction_count = 0`。

## 5. 门禁入口与证据

- 门禁：`make verify.business_config.field_policy_declaration_parity`
  （只读 Odoo shell 门禁，脚本 `scripts/verify/business_config_field_policy_declaration_parity.py`）。
- 报告：`artifacts/backend/business_config_field_policy_declaration_parity.json`
  （字段：`model_count_with_model_wide_policy` / `entry_model_count` /
  `contradiction_count` / `contradictions`）。
- 声明源：`addons/smart_construction_core/data/p1_daily_business_form_orchestration_contract_data.xml`
  （相关记录上方带本文件与门禁入口说明）。

## 6. 边界与禁止事项

- 本收口不放宽任何字段权限、ACL、记录规则或合法隐藏规则。
- 不为具体模型添加特判；同类矛盾统一按上述两条判据判定。
- 不把 `readonly` 从模型级声明体整体移除（那会丢失 `*_display` 镜像事实的只读策略），
  只按字段职责逐项收口。

## 7. 声明消费口径：新建态与「未保存记录哨兵」（2026-10-08 补）

本节约束的是**声明消费侧**（任何按声明求值 `invisible` 的消费者：验收探针、前端修饰符引擎、
后续代码生成器），不是声明体本身。把这条写下来的原因：同一现象（“声明可见可编辑，页面却不渲染”）
本仓库已出现两次，第一次是真实投影缺陷（`due_date`），第二次是消费口径错误
（`settlement.income`）。二者外观相同，必须按下面的判据区分，不能靠个案判断。

### 7.1 判据

1. 交付契约 `dataContract.mainData.id` 在 `render_profile=create` 下是 **Odoo ORM 的未保存
   记录虚拟 id**（`models.NewId`，序列化为 `NewId_0x<hex>`）。这是本仓库既有且已冻结的契约约定，
   已记录在 `docs/contract/snapshots/api_onchange_intent_admin.json`
   （`ui_contract_raw.patch.id = "NewId_0x..."`），**不得**为迎合消费方改成 `false` 或删除。
2. 因此对 `not id` 这类原生 `invisible` 表达式求值时，`NewId_*` **必须**解析为“未保存”
   （即 `id` 为假），与交付页面的真实记录状态一致；把它当字符串真值会把声明整体倒置。
3. 反之，若 create 契约下发的是**已持久化 id**（既不是缺省、假值，也不是 `NewId_*`），
   则该 create 契约绑定了另一条记录，凡按这些值求值的结论全部无效，必须 fail-closed。

### 7.2 与投影缺陷的区分

- **投影缺陷**（第一次，`due_date`）：声明体自相矛盾（模型级无条件 `readonly` 与入口声明冲突），
  消费方按声明求值得到的结论本身正确，只是与页面不一致。修在声明体所属层。
- **消费口径错误**（第二次，`settlement.income`）：声明体一致且正确，页面也正确
  （`sc.settlement.order` 原生表单的 `执行与匹配`/`发票信息`/`付款申请`/`扣款调整`/`采购订单`/
  `系统办理信息` 六组明确声明 `invisible="not id"`，即“记录保存后才显示”），错的是消费方把
  `NewId_*` 当成了持久化 id。修在消费侧，**不改**声明体、**不改**页面。

判定这两类的可复用问句：**声明之间是否互相一致？页面渲染是否符合声明？** 两者都为“是”时，
剩下的分歧一定在消费口径，不能去改产品。

### 7.3 门禁与锁定

`verify.system_user_experience.business_form_user_perspective` 的汇总守卫
（`frontend/apps/web/scripts/business_form_user_perspective_summary_guard.mjs`）现锁定三条：

- `createRecordIdKind` 不得为 `persisted`（create 契约必须描述未保存记录；缺省、假值、
  `unsaved_sentinel` 三者合法）；
- `declaredVisibleNotRendered` 必须为空：交付契约声明“本 profile 可见且可编辑”、且自身与全部
  祖先 `invisible` 均解析为假 的字段，必须真实渲染（由“证据项”升级为硬门禁）；
- 每个 create 用例必须声明到非空的可见可编辑字段集，防止“全判隐藏”让门禁空转。

阈值 `MIN_CASE_COUNT=20` 不变；本题材不新增第二套全局测试框架。
