# 付款申请完整链路确认（PAYMENT-REQUEST-CHAIN-CONFIRMATION）

Status: 确认完成（confirmation-only run，无产品源码改动）
Baseline HEAD: `aeee27b0a6e30d5d3f6b9cd66953e4a999b48804`
Candidate fingerprint: `6506d7d167033abf4158a805b8f0a81aa9453d331cc2076fb445ead8474b5c35`
Runtime: `sc-local-dev` / `sc_dev_demo` / nginx `18081`，受管口令 `scdevpass`
受管目标：`demo_role_finance`(uid 43) · action 809 · menu 559 · fixture `DEMO-PR-FLOORPLAN-004`

## 0. 结论

| 链路环节 | 结论 | 依据 |
|---|---|---|
| 后端契约（列表面声明） | ✅ 完整且正确 | 活契约响应 + ACL 实测 |
| 语义注册表 + 解析链 | ✅ 通过 | `verify.semantic.registry.lint` 66 项、`verify.semantic_runtime_resolution` 123 项 |
| 列表页渲染 | ✅ 正常（有 1 个非致命投影缺陷） | 实机截图 + DOM 探针 |
| 创建表单渲染 | ✅ 契约驱动且完整 | 实机截图 + 29 字段 DOM 探针 |
| 受管入口 `verify.local.dev.payment_request.full_chain` | ❌ 失败 | 取证脚本相对 PR #525 漂移（非产品缺陷） |
| 保存 → 提交 → 审批 → 执行 → 台账 → 完成 | ⛔ 本轮未取证 | 受管入口在脚本漂移处中断 |

一句话：**契约与产品渲染是对的，阻断在“取证脚本没有跟上官方模板渲染”，因此业务写入链路本轮不能宣称已通过。**

## 1. 后端契约事实（列表面完整且正确）

直接抓取 action 809 的 `ui.contract.v2` 响应（`demo_role_finance`）：

- `layoutContract.listProfile.batch_policy = {enabled:true, available_actions:[export,archive,activate,delete], delete_mode:"unlink", …}`
- `layoutContract.listProfile.selection_policy = {enabled:true, mode:"multiple", scope:"current_page", …}`
- `actionContract.surfacePolicies.collection_capabilities = {enabled:true, actions:[export/archive/activate/delete(selection), import(collection)]}`
- ACL：`demo_role_finance`(uid 43) 对 `payment.request` `read/create/write/unlink` 均可用

即：**后端已产出全部所需声明**，列表面的声明层无缺口。

## 2. 受管入口失败的直接原因：取证脚本漂移（非产品缺陷）

失败位置：`main:list-before` 找不到「新建」按钮（`EXIT=2`，fixture 已自动回滚）。
经逐点核实，脚本有 3 处相对 **PR #525（`2d164a1f`，2026-10-01「adopt official template rendering」）** 之后的落位漂移；
脚本末次更新为 `a5805d62`（2026-09-24），**早于**该渲染改造。

### 2.1 列表操作按钮归属漂移

- `[data-product-page-header]` 内「新建」按钮 = **0**；`[data-list-surface-header]`（`section.product-list-query-bar`）内 = **1**。
- 机制：`ActionView.vue:5` header `#actions` 插槽带 `v-if="!standardListOperationsInCard"`；当 `kind==='list' && surfaceRendererDescriptor.outlet==='standard' && !renderErrorMessage` 时，操作（刷新/新建/…）改挂列表卡片 `#leading`（`ActionView.vue:471`），页头不再有按钮。
- 脚本第 1232 行仍按旧落位在页头内查找 → `count=0` 超时。

### 2.2 创建/编辑页面板标记漂移

- 现渲染 `CanonicalNativeFormSurface`（`[data-native-contract-structure]`），**不再产出** `[data-object-task-page]` / `[data-floorplan-region]`。
- `ObjectTaskPage` 仅在 `TaskFormPattern(presentationMode==='task')` 且 `!preserveAuthoritativeBusinessSections` 时渲染（`ContractFormDriverHost.vue:23-24,85`）。
- 脚本的 region 断言与部分 metrics 作用域因此全空。

### 2.3 业务分类上下文切换前置假设过时

- 脚本等待 URL `current_business_category_code=finance.payment.apply.pay`（选分类后触发）。
- 现产品在新建时**已默认该分类**（`ActionView.vue:1724-1729` fallback 到首个分类选项），选择同值不触发 route 更新 → 30s 超时。
- 机制本身仍在（`relationSelectionRuntime.ts:80`），属脚本前置假设过时。

### 2.4 诊断性复跑证实的“产品其实是对的”

在 `/tmp` 的诊断副本中（**不改仓库**）仅调整上述 3 类过时假设后，创建面指标**全部通过**：

- 29 个 `data-field-name`（`project_id/partner_id/business_category_id/date_request/amount/outflow_line_ids/attachment_ids/...`）、无字段重复
- 12 个互异 `data-group-title`（基本信息/项目与收款对象/付款依据/合同与结算依据/申请金额/本次付款事实/收付款信息/本次收款账户快照/付款单位与默认账户/说明与附件/履约与追溯/执行结果）
- `project_id/partner_id/business_category_id` 必填权威 = `required`；只读控件 0；空禁用控件 0；主操作 1；无横向溢出
- 动作栏：`保存草稿 / 提交审批 / 取消`
- 截图：`.runtime/evidence-logs/payment-chain-confirmation-20261013/create-product-floorplan-desktop.png`

### 2.5 `funding_baseline_id` 的“契约 vs 渲染”分歧（需裁定）

脚本 `assertRelationCreateAuthority` 判定不一致：契约 `relation_entry = {canCreate:true, createMode:'page', actionId:645, menuId:541, reasonCode:'PAGE_ENTRY_READY'}`，而渲染字段 `fieldState=readonly`、无新建入口。
后端测试断言 `readonly_empty_texts['funding_baseline_id'] == {'提交审批时生成'}`（`test_p1_payment_request_capability.py:2465`）证明**只读是产品意图**，故属“断言未排除只读字段”（或契约侧 `relation_entry` 未随只读收敛）。需裁定归属。

## 3. 前端契约投影责任缺陷（真实，非致命）

### 3.1 契约前求值 → `ContractGapError`（PR #647 引入）

- 位置：`frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts` `extractListProfile()`
- 机制：`batchPolicy` **对象字面量无条件先求值** `requireDeclaredBoolean(rawBatchPolicy.enabled, …)`，而“无声明即 `return null`”的短路判断在**其后**。契约未到达（或列表面未声明 `batch_policy`）时 `rawProfile={}` → 必抛 `ContractGapError: 契约缺少合法声明 list_profile.batch_policy.enabled`。
- 引入：`34a4f6ad`（PR #647，2026-10-12 19:54）把 `enabled: rawBatchPolicy.enabled === true` 改为 fail-closed 断言。
- 首次求值点：`ActionView.vue:3240` `watch(..., { immediate: true })` 的 source getter 读取 `listColumnOptions.value` → `listProfile`(1334) → `extractListProfile(actionContract.value=null)`。
- 时序证据：`ContractGapError t=2824` **早于** `ui.contract.v2 req t=2878 / res t=3580`（`probe-precontract-timing.json`、`probe-intent-timeline.json`）。
- 严重度：**非致命**——列表页随后仍渲染成功（“共 72 条”+ 行数据）。

### 3.2 契约后 `TypeError: … reading 'map'`

契约返回后（t≈3610）同页再抛一次 `TypeError: Cannot read properties of undefined (reading 'map')`（ActionViewShell chunk）。同样未中断渲染。与 3.1 同属“投影在契约边界处缺少就绪门控”。

### 3.3 `wutao` 403 属已知事实

`wutao` 访问 `/a/809?menu_id=559` 返回 403「用户无权访问菜单 付款申请」；该事实已在 `FE-CONTRACT-RUNTIME-01/run.json` 的 blockers 中登记（out-of-scope finding），**非本批新增**。

## 4. 域契约 transitions 与代码状态机漂移（早于本批）

- `contracts/domain/payment-request.yaml` `transitions`：`submit/approve/approve_pass/reject/resubmit(→draft)/done(→done)/cancel/create_execution(自环)`
- `state_machine.py PAYMENT_REQUEST_TRANSITIONS`：`submit→{approve,approved,rejected,cancel}`；`approved→{done,cancel}`；`rejected→{draft,submit,cancel}`；`done→{approved}`
- `workflow_contract_service.PROFILE_BY_MODEL['payment.request'].state_actions`：`draft→[save_draft,submit,cancel]`；`submit→[approve,reject,cancel]`；`approve→[approve,reject,cancel]`；`approved→[complete,cancel]`；`rejected→[submit,cancel]`
- 运行时权威是 `workflow_contract_service`；域契约 `transitions` **无运行时消费方**（`generate_semantic_registry.py` 只读 `source_of_truth.model` + fields）。
- 因此契约 `notes` 自称“逐字对齐 `ScStateMachine.PAYMENT_REQUEST_TRANSITIONS`”**不成立**。

## 5. 未取证 / 不得声称已通过

- 保存 → 提交 → 审批 → 付款执行 → 台账 → 完成 的**写入链路本轮未取得证据**：受管入口在取证脚本漂移处中断；第二段 `full_chain.mjs` 需要第一段产出的“已提交夹具”，无法独立起跑（实测：`payment approval-chain resolution requires the submitted governed fixture`）。
- 未重跑浏览器矩阵、未改仓库、未改契约、未新增探针框架。

## 6. 最小修复建议（待裁定）

| 编号 | 层 | 内容 | 归属 |
|---|---|---|---|
| F1 | 验证仪器 | 更新 `local_dev_payment_request_floorplan_submit.mjs` 的 3 处过时假设（新建按钮归 `[data-list-surface-header]`；创建/编辑面 metrics 作用域改 `CanonicalNativeFormSurface`；relation-create 断言跳过 `readonly` 字段；业务分类“同值不触发切换”） | P4 验证工具 |
| F2 | 前端投影责任 | `extractListProfile` 在契约缺失/无 `batch_policy` 声明时短路返回 `null`，不在对象字面量中提前求值 fail-closed 断言；并对未就绪消费点加门控 | P0 前端渲染机制 |
| F3 | 契约治理 | 修正或显式退役 `contracts/domain/payment-request.yaml` 的 `transitions`（声明其非运行时权威，或与 `state_machine` 对齐） | P1/P0 契约 |
| F4 | 契约边界 | 裁定 `funding_baseline_id`：契约 `relation_entry.can_create` 应收敛到只读事实，或验证断言排除只读字段 | 待裁定 |

## 7. 证据索引

`.runtime/evidence-logs/payment-chain-confirmation-20261013/`

- `probe-list-dom.json` — 列表页「新建」按钮归属（`inHeader:false`）
- `probe-create-surface-dom.json` — 创建面 29 字段 / 12 分组 / driver
- `probe-locator-ownership.json` — 定位器归属计数（header 0 / list-surface 1）
- `probe-intent-timeline.json` — intent 时序（崩溃早于契约返回）
- `probe-precontract-timing.json` — 契约前求值时序
- `probe-wutao-403.json` — `wutao` 403
- `create-product-floorplan-desktop.png` — 创建面实机渲染
- `journey-run5-failure.png` / `journey-run5-summary.json` — 诊断复跑（业务分类切换超时处）

原始受管日志：`.runtime/evidence-logs/chain_payment_full_chain.log`（`EXIT=2`）。

## 8. Run 台账状态（本次交回）

- `.agent/runs/PAYMENT-REQUEST-CHAIN-CONFIRMATION/run.json`：`status = blocked`（非终态，保留在 `.agent/active-runs.json`）。
- 回执：`semantic_registry_lint`(66)、`semantic_runtime_resolution`(123) 已录；`payment_full_chain` 仍为 `not_run`。
- 工具缺口（P4）：`agent_run_context.py` 的 `begin/record` 要求全部声明输入存在，含运行时 readback 产物
  `artifacts/playwright/local-dev-payment-request-full-chain/summary.json`；受管运行时检查在产出该产物前即中止，
  因此**连 failed 回执也无法录入**。失败事实以本记录 + `.runtime/evidence-logs/chain_payment_full_chain.log`（`EXIT=2`）为准。
- 若 F1 获批：更新取证仪器后在本候选上重跑受管入口，即可补齐写入链路证据；F2/F3/F4 本轮只报告不修复。
