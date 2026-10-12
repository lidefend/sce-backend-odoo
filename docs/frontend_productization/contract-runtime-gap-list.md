# Contract Runtime 缺口清单 v1（FE-CONTRACT-RUNTIME-00）

## 身份与范围

- 基线：`9cff283b59f72c4359294f9488c1f0240ad18370`
- 台账：`.agent/runs/FE-CONTRACT-RUNTIME-00/run.json`
- 类型：静态、只读；所有条目均给出可复核文件路径，无推测项。
- 回答的问题：**哪些能力应该沉淀为 Runtime，而不是继续写在业务页面里。**

优先级定义：P0 = 直接阻塞"改契约即可改行为"这个根本目标；P1 = 影响契约自洽或可维护性；
P2 = 治理效率。本轮不排期、不改契约，只登记。

## 一、缺口表

| # | 缺口 | 层 | 影响 | 优先级 |
|---|---|---|---|---|
| G1 | 语义组件词表（`componentKey`）没有契约声明权威 | Semantic | 前后端各持一半，无静态校验；后端可产出前端未登记的键 | **P0** |
| G2 | `payment_request` 的 api/schema 与 domain v2 状态词汇漂移 | Contract / State | 同一实体两套状态词与字段名 | **P0** |
| G3 | domain 契约声明的转移集与 `ScStateMachine` 不完全一致 | State | 运行时可走契约未声明的转移 | **P0** |
| G4 | `widgetStatus.auth` 只区分 `edit`/非 `edit`，`none`/`read`/`admin` 三档无独立行为 | Policy | 投影口径是契约驱动的，但档位语义未落满 | P1 |
| G5 | domain 契约引用 `SettlementRef`，但没有对应 schema 定义 | Semantic | 类型引用悬空 | P1 |
| G6 | 前端注册表 6/26 个组件键无平台生产声明 | Semantic | 声明单向，注册表可能长期存在死项 | P1 |
| G7 | 11 份契约文档未登记，`verify.contract.lint` 49 issues | Contract 治理 | 契约资产不可枚举 | P1 |
| G8 | 静态契约的 extensions 维度仍是占位 | Contract | domain 之外的声明维度名义存在、实际不可用 | P1 |
| G9 | 记录表单页（`ContractFormPage.vue` 1962 行 + `pages/contractForm/` 约 150 文件）存在 legacy/canonical 双渲染开关 | Behavior | 业务行为最可能仍留在页面层，需二次取证 | P1 |

## 二、逐条证据

### G1 语义组件词表没有契约声明权威（P0）

- 契约 schema 把 `componentKey` 声明为自由字符串：
  `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json`
  → `$defs/widget/properties/componentKey = { "$ref": "#/$defs/id" }`。
- `docs/architecture/unified_page_contract_v2/enum_registry.json` 枚举了
  `viewType`(12) / `layoutType`(11) / `containerType`(9) / `widgetType`(17) /
  `componentCapability`(14) / `authLevel`(4) / `triggerType`(10) /
  `dispatchMode`(4) / `targetScope`(5) / `patchOperation`(6)，
  **没有 `componentKey`**。
- 后端实际词表是一个私有映射函数：
  `addons/smart_core/core/unified_page_contract_v2_assembler.py::_component_key()`
  （monetary→`sc.value.money`、statusbar/badge→`sc.display.status`、…，缺省回落 `sc.display.text`）。
- 前端词表在：`frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts`（26 项）。
- 判定：同一语义词表由**后端映射函数**与**前端注册表**共同持有，契约层既不枚举也不校验。
  这违反 `ARCH-DECISION-002` 的"每个产品语义必须在契约层声明"。
- 另注：`_component_key()` 的**缺省回落**（未识别 widget 一律 `sc.display.text`）是一种
  前端可观察的隐式默认；缺失声明时应停机而不是回落，需一并纳入修复设计。

### G2 payment_request api/schema 与 domain v2 漂移（P0）

| 项 | `contracts/domain/payment-request.yaml`（v2） | `contracts/schemas/payment-request.yaml` |
|---|---|---|
| 状态 | `draft submit approve approved rejected done cancel` | `draft submitted approved rejected paid reversed` |
| 字段 | `name project_id contract_id settlement_id amount state` | `code project contract amount reason status` |

- domain v2 的 `notes` 自称："v1 的 submitted/approved 直连与 paid/reversed 终态为产品
  语义命名，与模型状态机不一致，已在 v2 废弃。"——但 schema 未同步废弃。
- `contracts/registry.yaml` 中 domain v2 与 product v1 并存，schema 无版本键。
- 判定：同一实体存在两套对外词汇，消费方按哪一套都"有依据"。

### G3 domain 契约转移集与状态机不一致（P0，本轮已实测确认）

`addons/smart_construction_core/models/support/state_machine.py`：

```python
PAYMENT_REQUEST_TRANSITIONS = {
    "draft": {"submit", "cancel"},
    "submit": {"approve", "approved", "rejected", "cancel"},
    "approve": {"approved", "rejected", "cancel"},
    "approved": {"done", "cancel"},
    "rejected": {"draft", "submit", "cancel"},
    "done": {"approved"},
    "cancel": set(),
}
```

`contracts/domain/payment-request.yaml` 的 `transitions` 与 `states[].actions`：

- 无 `submit → approved` 直连（契约是 `submit --approve--> approve --approve_pass--> approved`）。
- `rejected` 只能 `resubmit → draft`，无 `rejected → submit`。
- `done` 的 `actions: []`，无 `done → approved`（冲销恢复审批）。

本轮已逐条比对 `contracts/domain/payment-request.yaml` 的 `states`/`transitions`
（实测 7 状态 / 8 转移）与上面常量，**差异确认成立**，不是读取误差：

| 运行时允许 | 契约是否声明 |
|---|---|
| `submit → approved` | ❌ 未声明 |
| `rejected → submit` | ❌ 未声明 |
| `done → approved`（冲销恢复）| ❌ 未声明（契约 `done.actions` 为空）|

而契约自身注释声称"状态机逐字对齐"——**该断言与事实不符**。
叠加蓝图 §二 的结论（domain 契约的 `states`/`transitions` 当前不被任何运行时消费），
本条的定性是：**两份声明互不消费、且内容不一致**，运行时实际走的是 `ScStateMachine`。
因此不存在"运行时可走契约未声明转移"的越界问题——契约根本没被读；
真正的缺陷是**声明冗余且漂移**，由 `FE-CONTRACT-RUNTIME-01` 的权威决策（A/B）消除。

### G4 `widgetStatus.auth` 已消费，但档位语义未落满（P1）

- 契约声明：`$defs/widgetStatus.auth ∈ {none, read, edit, admin}`，并带 `reasonCode`；
  `enum_registry.authLevel` 为 4。
- **动作维度**已确认消费：
  `frontend/apps/web/src/app/contracts/v2/actionRuleAuthority.ts`
  消费 `actionRule.authorizationAllowed / businessAvailable`（显式 `false` 才拒绝）。
- **字段维度**已确证消费（本轮补证）：
  `frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts:123`
  `const authorityReadonly = (declaredAuthority && widgetStatus?.auth !== 'edit') || …`
  → `auth` 直接驱动字段只读态；同文件 `:112` 在 status 缺失时返回
  `V2_OCCURRENCE_STATUS_MISSING`（fail-closed）。
  另 `app/contracts/v2/schema.ts:2269-2275` 在客户端强制校验：
  每个 form occurrence 必须有 `auth` 字符串，且 `(readonly|disabled) && auth==='edit'` 判为冲突。
- **残余缺口（自然收敛后的一条）**：`none` / `read` / `admin` 三者在上面的消费式里
  被合并为"非 edit"，即三档没有各自独立的可观察行为。
  这不影响 payment 样板闭环（payment 只需 `edit`/非 `edit`），但要在 01 决定
  是补齐档位语义，还是在契约层把 `authLevel` 收窄到实际消费的两档。
- 判定：不再是"未取证"，而是"已取证、结论比原假设窄"。

### G5 `SettlementRef` 无 schema 定义（P1）

- 引用方：`contracts/domain/payment-request.yaml`（`settlement_id: type: SettlementRef`）。
- `contracts/schemas/` 已定义符号：`Money` / `ProjectRef` / `ContractRef` /
  `PaymentRequest` / `CreatePaymentRequest` / `UpdatePaymentRequest` /
  `PaymentRequestList` / `NavigationContract` / `RouteAuthorityContract` / `SystemInitContract`。
- **无 `SettlementRef`。**

### G6 前端注册表 6/26 键无平台生产声明（P1）

- `sc.auth.credential_entry`、`sc.auth.secret_confirmation`、`sc.auth.challenge_status`、
  `sc.auth.one_time_secret`、`sc.auth.support_action`：
  全仓检索只命中前端注册表、其单测与 `scripts/verify/frontend_auth_surface_guard.py`，
  **无后端生产者**（`sc.auth.*` 在后端出现的是模型名 `sc.auth.credential.policy` 等，不是组件键）。
- `sc.payment.settlement_detail_collection`：由 P1 行业模块生产，
  `addons/smart_construction_core/core_extension_contract_normalizers.py::PAYMENT_SETTLEMENT_DETAIL_COMPONENT_KEY`。

### G7 契约文档未登记与 lint 现状（P1）

`make verify.contract.lint` 在**当前基线与 `origin/main` 上同为红**（`contracts/` 与 main 逐字节相同），
49 issues，分类如下（`artifacts/contracts_lint_report.json`）：

| 类别 | 数量 | 说明 |
|---|---:|---|
| contract file not registered | 11 | 1 domain + 4 product + 6 schema |
| contracts must be versioned | 4 | 4 份 `product/native-view-*.yaml` 无 `version` |
| product 契约缺必需键（id/title/pages/capabilities/roles）| 20 | 同上 4 份 × 5 键 |
| domain 契约缺 `states`/`transitions` | 14 | 7 份非生命周期契约（boq-export / boq-line-patch / boq-dangerous-import / chart / overview-rich-text-patch / write-idempotency 等）× 2 |

- 判定：这**不是 49 个独立缺陷**，而是 lint 的契约分类假设与实际契约分类不匹配：
  `product/native-view-*.yaml` 与 `schemas/native-view-*.yaml` 被 `gate.contract.native_view_normalized_map`
  等门禁当作**数据**消费，却被 lint 当作**契约文档**要求登记。
- 该 lint 只经 `verify.contract.preflight` → `verify.round.v0_6.mini` 到达，不在必需 CI 车道上，
  因此长期未被发现。本轮登记，不修复（非本任务范围）。

### G8 静态契约 extensions 维度是占位（P1）

- `contracts/extensions/ui.yaml`：注释 "保留扩展层，当前首阶段仅说明：UI 仅消费 formStructureRole/component 元信息"，
  内容为 3 个 render_profile 与 3 个 semantic_components 字符串。
- `contracts/extensions/permission.yaml`：注释 "保留扩展层，当前首阶段不纳入自动化执行"。
- `contracts/extensions/workflow.yaml`：仅 5 个 payment_request 动作字符串。
- 判定：domain 之外的声明维度名义存在、实际不是权威；presentation/behavior/policy 的真实声明权威
  完全在运行时 `ui.contract` v2 投影。

### G9 记录表单页的双渲染开关（P1，需二次取证）

- `frontend/apps/web/src/pages/ContractFormPage.vue` 1962 行，
  模板上同时绑定 `data-form-composition` / `data-detail-composition` 与
  `data-v2-shadow-*` 系列，并以 `canonicalProductRendererActive` 在
  legacy 动作与 canonical 动作之间切换（`:direct-actions` / `:canonical-direct-actions`）。
- `frontend/apps/web/src/pages/contractForm/` 约 150 个文件。
- 判定：这是双渲染路径并存的迁移中间态，本身不是缺陷；
  但是"业务行为是否已全部回契约"的最大不确定面，需在 01 用行为证据定性。
- 已存在的机制约束：`scripts/verify/frontend_contract_basis_guard.py` 当前 PASS，
  意味着按该守卫的口径**没有未登记的前端判断站点**；本清单不重复证明，
  只登记"守卫自身检出完整度"未在本次量化。

## 三、可直接复用的既有资产（不要重做）

| 资产 | 路径 | 复用点 |
|---|---|---|
| 运行时能力台账 | `docs/architecture/frontend_contract_basis_ledger.json` | 声明绑定、豁免、未闭合缺陷 |
| V2 渲染权威矩阵 | `docs/frontend_productization/rendering-detail/contract-v2-render-authority-matrix-v1.json` | 契约节字段归属 |
| 渲染面归属 | `docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json` | 页面与渲染器归属 |
| 页面面清单 | `docs/frontend_productization/page-surface-inventory.json` | 页面/入口规模 |
| 组件覆盖清单 | `docs/frontend_productization/component-coverage-inventory.json` | 组件覆盖 |
| 页面模式规范 | `docs/frontend_productization/product-page-patterns-v1.md` | 四标准模式定义 |
| 决策权威清单 | `docs/frontend_productization/decision-authority-inventory-v1.json` | 决策归属 |

## 四、本轮不覆盖

不排期、不改契约、不改前端、不启动运行环境、不重跑既有证据、不扩测试框架。
