# Payment Runtime Blueprint v1（FE-CONTRACT-RUNTIME-00）

## 身份与范围

- 基线：`9cff283b59f72c4359294f9488c1f0240ad18370`
- 台账：`.agent/runs/FE-CONTRACT-RUNTIME-00/run.json`
- 回答的问题：**付款申请能否作为第一个标准样板闭环。**
- 结论：能。它是 `contracts/` 中唯一同时具备 domain + product + api + schema 的实体
  （`contract-runtime-capability-matrix.md` §1.2），且列表/表单/动作/状态四类运行时
  载体都已存在，不需要新建渲染框架。

## 一、Payment Runtime Map

链路与逐层状态（🟢 已存在 / 🟡 部分存在 / 🔴 缺失）：

```
payment.request
   │
   ├─ 1  Odoo Model            🟢
   ├─ 2  Domain Contract       🟡  声明存在，但运行时未消费
   ├─ 3  Product Contract      🟡  只有导航/能力/角色，无 presentation/behavior/policy
   ├─ 4  Runtime Resolver      🟢
   ├─ 5  Form Pattern          🟢
   ├─ 6  Semantic Mapping      🟡  词表双权威（G1）
   ├─ 7  Action Runtime        🟡
   └─ 8  State Runtime         🟡/🔴 契约与状态机不一致（G3）
```

| # | 层 | 现状载体（证据） | 状态 |
|---|---|---|---|
| 1 | Odoo Model | `addons/smart_construction_core/models/core/payment_request.py`（`_name = "payment.request"`，`tier.validation`/`mail.thread`/责任上下文 mixin）；行模型 `payment_request_line.py`；状态表 `models/support/state_machine.py::ScStateMachine.PAYMENT_REQUEST` | 🟢 |
| 2 | Domain Contract | `contracts/domain/payment-request.yaml` v2（7 状态 / 8 转移 / 6 字段 / `source_of_truth.state_machine`）| 🟡 |
| 3 | Product Contract | `contracts/product/payment-request.yaml` v1（`navigation`、`pages` list/detail/create、`capabilities` 7 项、`roles` 3 个、`constraints.page_variants`）| 🟡 |
| 4 | Runtime Resolver | 后端 `handlers/ui_contract_v2.py` + `core/unified_page_contract_v2_assembler.py` + `core/unified_page_contract_v2_form_structure.py` + `core/form_structure_authority.py`；前端 `app/contracts/v2/store.ts`（`createContractV2Store`）、`client.ts`、`runtime.ts`、`types.ts` | 🟢 |
| 5 | Form Pattern | `app/presentation/standardPageType.ts` → `standardFormComposition.ts`；`components/product-page-patterns/TaskFormPattern.vue` / `WorkspaceFormPattern.vue`；`app/presentation/canonicalFormFloorplan.ts`；`pages/contractForm/CanonicalFormNodeRenderer.vue` | 🟢 |
| 6 | Semantic Mapping | 后端 `unified_page_contract_v2_assembler.py::_component_key()`（隐式映射 20 键）；前端 `app/presentation/professionalComponentRegistry.ts`（26 键）+ `components/template/formSection.mapper.ts` + `FormSection.vue` 分发到 6 个真实渲染器 | 🟡 |
| 7 | Action Runtime | 后端 `handlers/payment_request_approval.py`（submit/approve/reject/done/create_execution/cancel）、`handlers/payment_request_available_actions.py`；前端 `app/pageContractActionRuntime.ts`、`pages/contractForm/contractActionRules.ts`、`actionExecutionPlan.ts`、`app/contracts/v2/actionRuleAuthority.ts` | 🟡 |
| 8 | State Runtime | `workflowContract` + `app/contracts/v2/workflowActionAvailability.ts`；状态本体在 `ScStateMachine`（模型级） | 🟡 |

## 二、必须先说清的一处结构问题

**`contracts/domain/payment-request.yaml` 的 `states` / `transitions` 当前不被任何运行时消费。**

证据：

- `scripts/contract/export_contract_registry.py` 读 domain 文档只取 `path` / `version` 与
  版本一致性，不读内容。
- `addons/` 中对 domain 契约文件只出现**文档字符串引用**，例如
  `handlers/overview_rich_text_patch.py:4`「数据契约：contracts/domain/overview-rich-text-patch.yaml v1」。
- `scripts/verify/` 中 `workflow_state_phase_coverage_guard.py`、
  `test_payment_approval_state_machine.py`、`industry_module_product_boundary_guard.py`
  都**不读** `contracts/domain`；它们绑定的是 `ScStateMachine` 的常量。
- `scripts/verify/contract_schema_declaration_sync.py` 读的是
  `docs/architecture/unified_page_contract_v2/enum_registry.json`，不是 domain 契约。

也就是说，运行时的状态权威实际是**模型级 `ScStateMachine` + 运行时 `workflowContract` 投影**，
而静态 domain 契约是一份**平行且未被消费的声明**。这正好命中
`ARCH-DECISION-002` 明令禁止的 `declared_but_unconsumed_contract_fields_are_a_boundary_gap`。

这不影响 payment 作为样板闭环的可行性，但它决定了 01 必须先做的**唯一未决项**：

> **哪一份是 payment 状态/字段的单一权威？**

- 方案 A：运行时 `ui.contract` v2 投影是消费权威（与 ARCH-DECISION-002 一致），
  `contracts/domain/*.yaml` 要么成为装配器的输入源，要么明确降级为文档并停止声明
  `states`/`transitions` 这类可执行语义。
- 方案 B：静态 domain 契约成为装配器输入，运行时投影由它生成。

两方案都能自洽；**不能自洽的是继续保留两份互不消费的声明。** 这是 owner 决策项，
本轮只登记，不擅自选择。以下 01 范围对 A/B 都成立。

## 三、FE-CONTRACT-RUNTIME-01 最小闭环

### 目标（唯一验收口径）

> 修改 payment 的契约声明，可以改变页面行为，**而不需要改 Vue**。

### 范围：只做 payment 一个闭环，五件事

| 序 | 闭环件 | 现在的缺口 | 完成后应能证明 |
|---|---|---|---|
| 1 | 字段语义 | G1：`componentKey` 词表双权威、缺省回落 `sc.display.text` | payment 表单每个 widget 的语义控件来自契约枚举；未登记即停机而非回落 |
| 2 | 表单模式 | 已成立，只需取证 | create/edit/readonly 由 `pageInfo` + 生效 renderProfile 决定，页面不自行判定 |
| 3 | 校验 | 已确证：`useRecordFormLayout.ts:105-127` 的 required/readonly/disabled 全部取自 `widgetStatus`，缺声明即 `V2_OCCURRENCE_STATUS_MISSING` 停机 | 改声明即改必填/只读，页面零特殊处理；删声明即停机不回落 |
| 4 | 动作 | 已确证：动作维度消费 `actionRule.authorizationAllowed/businessAvailable`（`actionRuleAuthority.ts`）；G4 已收窄为"`auth` 只区分 edit/非 edit" | 按钮集合、禁用态与禁用原因全部来自声明 |
| 5 | 状态 | G3：契约转移集 ≠ `ScStateMachine`；且按 §二 结论，domain 契约未被消费 | 状态与允许转移单一权威，运行时与声明一致（由 §二 的 A/B 决策决定权威方）|

### 不在 01 范围

- 不推广到合同/项目/分包/采购（那是 02）。
- 不改页面视觉，不重构 `ContractFormPage.vue` 的 1962 行（G9 的双渲染迁移按其自身节奏）。
- 不新增 fixture 或运行环境，不放宽任何既有断言。

## 四、验收口径（防止"看起来对"）

正确性证明必须是**行为证据**，下列都不算证明：

- 选择器字符串出现在页面；
- `44px` / `60px` 等样式文本出现；
- 某个 handler 被调用；
- 契约字段"已声明"本身。

必须证明的是同一组对应关系：

```
声明（契约）  ──消费──▶  实际行为
    │                        │
    └── 改声明 → 行为随之改变（不改 Vue）
    └── 删声明 → 停机，而不是回落默认值
```

## 五、建议执行顺序

1. 先定 §二的 A/B（owner 决策，阻塞其余全部）。
2. 修 G1：把语义词表收敛到契约枚举，删除 `_component_key()` 的隐式缺省回落；
   同步 `professionalComponentRegistry.ts` 与 `enum_registry.json`。
3. 修 G2：`payment_request` 的 api/schema 与 domain 状态词汇归一。
4. 修 G3：按 §二 决定的权威方，使状态/转移集只有一份。
5. G4 收敛：`auth` 消费落点已确证（`useRecordFormLayout.ts:123` 驱动只读；`schema.ts:2269` 强制必填）。
   仅需决定 `none`/`read`/`admin` 是补齐档位语义还是收窄为两档。
6. 用 payment 的 create/edit/readonly 三个 profile 各跑一次
   "改声明 → 行为变" 的真实闭环，作为 01 的交付证据。

## 六、可复用、不要重做

- 运行时能力台账：`docs/architecture/frontend_contract_basis_ledger.json`
- V2 渲染权威矩阵：`docs/frontend_productization/rendering-detail/contract-v2-render-authority-matrix-v1.json`
- 渲染面归属：`docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json`
- 页面模式规范：`docs/frontend_productization/product-page-patterns-v1.md`
- 既有守卫：`verify.frontend.contract_basis.*`、`verify.frontend.professional_component_registry.unit`、
  `verify.unified_page_contract.v2.*`、`verify.workflow_contract.*`
