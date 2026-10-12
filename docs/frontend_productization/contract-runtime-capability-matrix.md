# Contract Runtime 能力矩阵 v1（FE-CONTRACT-RUNTIME-00）

## 身份与范围

- 基线：`9cff283b59f72c4359294f9488c1f0240ad18370`
- 分支：`audit/fe-contract-runtime-00-20261012`
- 台账：`.agent/runs/FE-CONTRACT-RUNTIME-00/run.json`
- 类型：静态、只读工程基线扫描；未启动浏览器、服务、数据库或 fixture。
- Formal Product Layer：P4（扫描本身）；所记录的每项能力归属 P0/P1。
- 回答的问题：**现在已有的 Runtime 雏形在哪里。**

本文件只回答"我们有什么"。缺什么见 `contract-runtime-gap-list.md`；第一个闭环见
`payment-runtime-blueprint.md`。不重做架构文档，不逐组件评分，不统计文件维护者。

## 一、契约资产盘点（R0-01）

契约层实际是**两层**，不是一个仓：

| 层 | 载体 | 内容 | 权威 |
|---|---|---|---|
| 静态契约仓 | `contracts/` | domain / api / schema / extensions 声明 | `contracts/registry.yaml` |
| 运行时契约 | `ui.contract` v2 投影 | pageInfo / layout / status / action / data / runtime / formStructure / search / workflow | `.agent/decisions/contract-driven-runtime-authority.yaml`（ARCH-DECISION-002）|

### 1.1 静态契约仓数量

| 项 | 数量 |
|---|---:|
| `contracts/domain/*.yaml` | 15（14 已登记 + 1 未登记）|
| `contracts/product/*.yaml` | 5（1 已登记 + 4 未登记）|
| `contracts/schemas/*.yaml` | 12（6 已登记 + 6 未登记）|
| `contracts/api/*.yaml` | 2（全部登记）|
| `contracts/extensions/*.yaml` | 3（全部登记，均为占位说明）|
| `registry.yaml` 登记条目 | 26（product 1 / domain 14 / schema 6 / api 2 / extension 3）|

未登记契约文档（`verify.contract.preflight` 的 lint 判定）见缺口清单 G7。

### 1.2 覆盖矩阵（Entity × 契约维度）

`contracts/` 内**只有 domain 维度**是普遍声明；product/api/schema 高度不齐；
presentation / behavior / policy **在契约仓内没有任何实体声明**，其声明权威在运行时
`ui.contract` v2 投影（由原生视图 + 扩展装配产生）。

| Entity（domain contract） | Domain | Product | API/schema | Presentation | Behavior | Policy |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `payment_request` | ✓ v2 | ✓ v1 | ⚠️ 漂移 | 运行时投影 | 运行时投影 | 运行时投影 |
| `payment_execution` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `general_contract` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `settlement` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `expense_claim` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `invoice_registration` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `receipt_income` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `project_lifecycle` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `boq` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `boq_export` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `boq_dangerous_import` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `boq_line_patch` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `chart` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `write_idempotency` | ✓ v1 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |
| `overview_rich_text_patch` | ⚠️ 未登记 | ❌ | ❌ | 运行时投影 | 运行时投影 | 运行时投影 |

> 结论：`payment_request` 是**唯一**同时具备 domain + product + api + schema 的实体，
> 因此它是唯一能作为"第一个标准闭环"样本的实体。这不是偏好，是资产事实。

## 二、运行时契约的六个正交维度与载体

`docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json`
的顶层契约节，以及各自已存在的前端消费载体：

| 维度 | 契约载体（运行时） | 已枚举词表 | 前端消费载体 | 状态 |
|---|---|---|---|---|
| 页面职责 | `pageInfo.viewType` / `layoutType` | viewType 12 / layoutType 11 | `app/presentation/standardPageType.ts` | 🟢 |
| 布局 | `layoutContract.containerTree`（container/widget, `span` 1..24）| containerType 9 / widgetType 17 | `app/presentation/canonicalFormFloorplan.ts`、`components/template/formSection.mapper.ts` | 🟢 |
| 语义 | `widget.componentKey` + `layoutContract.componentRegistry` | **componentKey 未枚举** | `app/presentation/professionalComponentRegistry.ts`（26 项）| 🟡 |
| 行为（可见/只读/必填）| `statusContract.widgetStatus{visible,readonly,required,disabled,placeholder}` | — | `app/modifierEngine.ts` | 🟢 |
| 策略（权限投影）| `statusContract.widgetStatus.auth` ∈ none/read/edit/admin | authLevel 4 | `app/contracts/v2/actionRuleAuthority.ts` | 🟡 |
| 动作 | `actionContract.actionRuleList`（triggerType/dispatchMode/targetScope/actionSemantics）| triggerType 10 / dispatchMode 4 / targetScope 5 | `app/pageContractActionRuntime.ts`、`pages/contractForm/contractActionRules.ts`、`actionExecutionPlan.ts` | 🟡 |
| 状态机 | `workflowContract` + `availableActions` | — | `app/contracts/v2/workflowActionAvailability.ts` | 🟡 |
| 取数 | `dataContract` | — | `app/runtime/contractFormDataRuntime.ts`、`pages/contractForm/recordHydration.ts` | 🟢 |
| 运行时补丁 | `runtimeContract.patchOperations` ∈ replace/merge/append/remove/reorder/invalidate | patchOperation 6 | `pages/contractForm/runtimeStateApplier.ts`、`runtimeStateReducer.ts`、`app/x2manyCommands.ts` | 🟢 |
| 表单结构角色 | `formStructureContract.formStructureRole` | 7（summary/task/context/risk/relation/activity/audit）| `app/contracts/v2/formStructureRoles.ts` | 🟢 |
| 检索 | `searchContract` | — | `app/runtime/actionViewListPageSizeRuntime.ts`、`savedSearchSubmission.ts` | 🟢 |

后端生产者集中在：
`addons/smart_core/handlers/ui_contract_v2.py`、
`addons/smart_core/core/unified_page_contract_v2_assembler.py`、
`addons/smart_core/handlers/ui_contract_v2_projection.py`、
`addons/smart_core/core/unified_page_contract_v2_form_structure.py`。

### 2.1 页面模式运行时（Pattern Runtime）已成立

`standardPageType.ts` 只从契约的 `pageInfo` + 生效 renderProfile 判定页面职责，
判定结果 `query-list | record-form | record-detail | specialized`，
再经 `standardListComposition.ts` / `standardFormComposition.ts` /
`standardDetailComposition.ts` / `standardShellComposition.ts` 选择合成。
未识别即 `specialized`（fail-closed，保留原渲染器并公示未采纳），不按模型名/标签猜测。

### 2.2 语义组件注册表（Semantic Registry）已成立

`professionalComponentRegistry.ts` 声明 26 项 `componentKey`，含：

- 基础录入：`sc.input.text/binary/textarea/number/boolean/date/datetime`
- 选择与关系：`sc.select.remote`、`sc.select.tags`、`sc.relation.many2one/many2many/table`
- 集合：`sc.table.data`、`sc.tree.data`
- 业务值：`sc.value.money/percentage/duration`、`sc.display.status`
- 通用：`sc.button.action`、`sc.display.text`
- 认证面：`sc.auth.credential_entry/secret_confirmation/challenge_status/one_time_secret/support_action`
- 专项：`sc.payment.settlement_detail_collection`

渲染分发收敛到 6 个真实组件（`PROFESSIONAL_COMPONENT_RENDERERS`），未登记即抛错。

### 2.3 停机机制（FRONTEND-JUDGEMENT-STOP）已成立

`docs/architecture/frontend_contract_basis_ledger.json` 是已存在的运行时能力台账，三层强制：

| 层 | 入口 | 行为 |
|---|---|---|
| runtime | `frontend/apps/web/src/app/contract/contractGap.ts` | 声明缺失/非法即抛 `ContractGapError` 停机 |
| static | `scripts/verify/frontend_contract_basis_guard.py` | 未登记的前端判断站点即 FAIL |
| delivery | `make verify.frontend.contract_basis.enforce` | 存在未闭合契约缺陷（`openContractDefects`）即禁止冻结 |

台账当前已登记 4 条声明绑定（声明 → 消费 → onMissing=stop → 回归守卫 → 行为测试）、
若干 `registeredMechanismExemptions`（`carriesProductSemantics=false` 的传输/渲染常量）。

补充：字段级已有等价停机——
`frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts:112`，
当某个 occurrence 找不到 `widgetStatus`/`buttonStatus`/`containerStatus` 时返回
`{invisible:true, visible:false, readonly:true, required:true, disabled:true,
reasonCode:'V2_OCCURRENCE_STATUS_MISSING'}`，即**缺声明即不可见+只读+禁用并带原因码**，
不回落任何默认控件。这正是 `FE-CONTRACT-RUNTIME-01` 要复用的"删声明→停机"既有行为。

### 2.4 语义类型盘点（R0-02）

问题：当前系统**已隐含**多少语义，以及各语义是否已有渲染支持。

领域契约实际出现的字段类型（`contracts/domain/*.yaml` 计数）：
`string 59` / `integer 22` / `ProjectRef 8` / `Money 7` / `date 6` / `boolean 6` /
`ContractRef 5` / `float 4` / `list 3` / `ref`·`object`·`json`·`datetime`·`SettlementRef` 各 1。

| 语义词 | 契约来源 | 渲染支持 | 状态 |
|---|---|---|---|
| `string` / 枚举 | domain `type: string` | `sc.input.text` / `sc.select.remote` | 🟢 |
| `integer` / `float` | domain `type` | `sc.input.number` | 🟢 |
| `boolean` | domain `type: boolean` | `sc.input.boolean` | 🟢 |
| `date` / `datetime` | domain `type` | `sc.input.date` / `sc.input.datetime` | 🟢 |
| `Money` | domain `type: Money` | `sc.value.money`（`contractFormPresenter.ts` 处理 `currencyField`）| 🟢 |
| `ProjectRef` / `ContractRef` | domain `type` | `sc.relation.many2one`；但前端注册表无 `ProjectRef`/`ContractRef` 符号 | ⚠️ |
| `SettlementRef` | domain `type` | **契约仓无该 schema 符号**（缺口 G5）| ❌ |
| `list` / one2many | 模型 `ttype` | `sc.relation.table` / `sc.table.data` | 🟢 |
| 状态徽标 | Odoo `statusbar`/`badge` | `sc.display.status` | 🟢 |
| 关系多选 | `many2many` / `many2many_tags` | `sc.relation.many2many` / `sc.select.tags` | 🟢 |
| 附件 | `binary` | `sc.input.binary` | 🟢 |
| 审批 | 无独立语义 | 无独立控件，走通用动作+字段 | ❌ |
| 行项目（line items）| 无独立语义 | 走 one2many `sc.relation.table`，无专用行编辑器 | ⚠️ |

判断：语义**不在契约层枚举**——`type` 是 domain 的字段类型，`componentKey` 由后端
`_component_key()`（实测 20 个键）映射产生。也就是说"语义"是**后端函数产物**而不是
**契约声明项**（缺口 G1）。这是 01 的首要收敛对象。

### 2.5 行为落点扫描（R0-04）

问题：状态/只读/禁用这类判断，有多少落在页面而不是契约。

| 位置 | `state/status` 等值判断 | 归因 |
|---|---:|---|
| 契约/运行时模块（`app/contracts`、`app/presentation`、`app/runtime`、`app/modifierEngine.ts`、`app/pageContractActionRuntime.ts`）| 214 | 契约消费主战场（应然）|
| 页面目录 `pages/` | 31（14 个文件）| 见下 |

对 `pages/` 31 条逐条归因：

- **异步/加载态**：`status === 'error' | 'loading' | 'empty'`
  占绝大多数（`ListPage.vue`、`KanbanPage.vue`、`ContractFormPage.vue` 的
  `status === 'error'/'loading'` 分支）。
- **HTTP 态**：`err.status === 403` / `professionalCollaborationModel.ts:29`
  `status === 403 || status === 404`。
- **表单配置草稿态**：`BoundFormSettingsPanel.vue:188/215`
  `draft.value.state === 'published'`，是配置发布草稿，不是业务状态机。
- **业务状态机判断：0 条。** 全库 `pages/` 中 `'draft'|'approved'|'submitted'|'rejected'`
  业务状态字面量仅命中 chatter 活动动作（`'done' | 'cancel'`）、
  表单配置操作日志状态（`'pending'|'saved'|'reverted'`）与一个 `'draft'` 兜底默认值，
  无一处在判断 `payment.request` 的业务状态。

只读/禁用侧：`:readonly=`/`:disabled=` 属性绑定 85 处、表达式 94 处；
抽样（`fieldOccurrenceWritability.ts`、`contractHeaderActionPresentation.ts`）显示
取值来自契约节点 `field.readonly/field.disabled` 或 `primarySubmitAction.enabled`，
而非页面自算业务状态。

**结论（修正原假设）**：这不是"状态机未契约化 → 大量页面判断"。
页面几乎不判断业务状态；真正的缺口是**声明与运行时的单一权威尚未建立**（G1/G2/G3），
而不是前端逻辑外溢。`FE-CONTRACT-RUNTIME-01` 因此可以聚焦契约权威收敛，
不需要先做一次大规模前端逻辑回迁。

### 2.6 页面模式抽样（R0-03）

三类核心模式各取一个真实样本，只问"这个模式由契约决定还是页面自己决定"：

| 模式 | 样本 | 契约驱动 | 页面自定义残留 |
|---|---|---|---|
| Form | `pages/ContractFormPage.vue` + `pages/contractForm/CanonicalFormNodeRenderer.vue` | `pageInfo`→`standardFormComposition`；字段 `visible/readonly/required/disabled` 取自 `widgetStatus`（缺则 `V2_OCCURRENCE_STATUS_MISSING` 停机）| `canonicalProductRendererActive` 的 legacy/canonical 双渲染开关（缺口 G9）|
| List | `pages/ListPage.vue` + `app/presentation/standardListComposition.ts` | 页面职责来自 `props.contractPageType`（缺省 `specialized`，注释明示"never re-derives it"）；声明式取数走 `requireDeclaredNumber(..., requiredDeclarationLayer:'P0:smart_core:…')` | 无业务语义自算 |
| Detail | `app/presentation/standardDetailComposition.ts` | 只消费契约给出的 page-type decision 与其 reason，不二次推导 | 无业务语义自算 |

共性：三种模式都通过 `standardPageType.ts` 的同一判定进入，
未识别即 `specialized`（fail-closed），**不存在"按模型名猜页面类型"的分支**。
所以 Form/List/Detail 的**模式选择**已经是契约驱动的；
唯一成规模的不确定面是 Form 内部 legacy/canonical 双渲染（G9），需在 01 用行为证据定性。

> 说明：这里不给"契约驱动 x% / 硬编码 y%"这类百分比——
> 按本仓库证据口径，没有可复核的分子分母，给数字等于造数。
> 可复核的结论是上面这张"谁决定模式、谁还有残留"的归属表。

## 三、能力矩阵：分层结论

| 层 | 能力 | 结论 |
|---|---|---|
| Model | Odoo 模型 + `ScStateMachine` 状态表 | 🟢 |
| Domain Contract | 15 份 domain 契约（状态/转移/字段）| 🟢 |
| Product Contract | 1 份（payment_request）| 🟡 |
| Runtime Resolver | `ui.contract` v2 装配 + `ContractV2NormalizedStore` | 🟢 |
| Page Pattern | 4 标准合成 + 契约判定 | 🟢 |
| Semantic Mapping | 26 项注册表 | 🟡 词表无契约枚举权威 |
| Behavior | `widgetStatus` + `modifierEngine` | 🟢 |
| Action | `actionRule` + `actionRuleAuthority` + `actionExecutionPlan` | 🟡 |
| State | `workflowContract` + `workflowActionAvailability` | 🟡 |
| Stop mechanism | 运行时/静态/交付三层 fail-closed | 🟢 |

**总判断**：Contract Runtime 的骨架已经在运行，不是从零开始。真正缺的是
（a）语义词表的单一声明权威、（b）payment 契约自身的自洽、（c）状态/动作层的完整度。
这三项就是 `FE-CONTRACT-RUNTIME-01` 的最小闭环对象。

## 四、本轮不覆盖

未做全量页面扫描、未统计全部字段、未给组件评分、未重写架构文档、
未改任何契约声明或前端代码、未启动运行环境。
