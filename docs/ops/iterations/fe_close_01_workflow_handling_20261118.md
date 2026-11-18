# FE-CLOSE-01 两入口工作流办理闭环

- 前端分支：`feature/fe-close-01-workflow-handling-20261118`
- 基线：`9821a9c688cbd4abb44f378051fc6c6362c5d8cd`
- 后端依赖：`BE-CLOSE-01`
- 业务范围：付款申请、项目启停管理
- 当前状态：消费链梳理

## 边界

前端只消费后端工作流事实：状态、稳定动作身份、授权和业务可用性、拒绝原因及
`refreshPolicy`。前端不新增审批规则，不按文案猜动作，不补造业务状态可用性。

## 当前交接

- 后端候选：`d3e2f8d4f6a3f3c7250316ee51a690dac470591a`
- 接受主线：`64f2e68ea1b80464fd080bb93b1a83312decc8c4`
- 后端 PR：[#933](https://github.com/lidefend/sce-backend-odoo/pull/933)
- 当前 FE 分支仍基于 `9821a9c6`；联调前必须用受管入口同步到 `64f2e68e`。
- 当前样本路径（后端 worktree）：
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/be_close_01_workflow_contract_samples_v1.json`
- 现有样本结构已可用于消费测试设计，但 `served_sha=54c0d25a`，尚未绑定
  `d3e2f8d4`；最终浏览器联调前必须重新采集真实 API 样本。

### 稳定动作身份

| 模型 | key | method |
| --- | --- | --- |
| `payment.request` | `save_draft` | `null`（普通表单保存） |
| `payment.request` | `submit` | `action_submit` |
| `payment.request` | `approve` | `action_approval_decision` |
| `payment.request` | `reject` | `action_approval_reject` |
| `payment.request` | `done` | `action_done` |
| `payment.request` | `cancel` | `action_cancel` |
| `project.project` | `submit` | `action_sc_submit` |
| `project.project` | `activate` | `action_sc_start` |
| `project.project` | `approve` | `validate_tier` |
| `project.project` | `reject` | `reject_tier` |
| `project.project` | `pause` | `action_sc_pause` |
| `project.project` | `resume` | `action_sc_resume` |
| `project.project` | `complete` | `action_sc_mark_done` |
| `project.project` | `advance_closing` | `action_sc_begin_closing` |
| `project.project` | `advance_warranty` | `action_sc_start_warranty` |
| `project.project` | `close` | `action_sc_close` |

### 已定位的最小前端缺口

1. `contractFormPresenter.ts` 在 workflow availability 为 disabled 时保留
   `reasonCode`，但把 `reasonMessage` 清空。后端已经提供
   `blocked_message`，这会让用户看到原因码却看不到可读原因。应直接消费
   workflow 行消息，不新增文案映射。
2. `workflowActionAvailability.ts` 在记录契约缺少动作行时返回通用
   `WORKFLOW_ACTION_NOT_AVAILABLE`。若 action contract 已按授权隐藏该动作，
   presenter 必须保持隐藏；“已授权但业务阻断”才显示 disabled 和后端原因。
   需要用真实样本区分这两类，不能在前端猜测 reason。
3. 主状态栏应由 `workflowContract.statusbar.field/current/states` 与同名字段
   的原生状态栏核对；不得继续把 `__workflow_phase` 当作真实状态字段，也不得
   用 Selection 顺序推导实际历史。
4. `useFormActionRuntime` 已按 `backendIdentity/actionId/sourceWidgetId`
   执行并在成功路径 `reload/refreshPolicy` 回读；接入时重点验证失败不解锁、
   不刷新掉输入，旧异步结果不覆盖切换后的页面。

### 接入改动清单

- `frontend/apps/web/src/app/presentation/contractFormPresenter.ts`：
  只修复 workflow disabled 原因消费和授权隐藏边界。
- `frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts`：
  核对主状态栏字段身份；不为两个入口增加模型特判。
- `frontend/apps/web/scripts/canonical_form_presenter_test.ts`：
  使用后端真实响应片段覆盖可操作、业务阻断、未授权省略、成功回读后的下一组动作。
- 既有 `useFormActionRuntime`、`actionExecutionPlan`、`canonicalFormActionExecutor`
  优先复用，不重写执行器。
- 浏览器只覆盖付款申请和项目启停两个入口：确认、执行中、成功回读、失败保留输入。

## 消费链盘点

### 状态栏

- `ContractFormPage.vue` 将 `nativeStatusbar` 传给 `ContractFormProductHeader`，页面可见状态来自
  `useRecordFormLayout` 解析出的原生 `statusbar` 字段/选择值。
- `useRecordFormLayout` 当前读取 `workflowContract.statusbar` 的 `field/readonly`，用于抑制字段和
  决定只读；`normalizeWorkflowPhaseStatusbar` 已有工作流阶段投影，但尚未作为页面状态栏的
  直接显示来源。
- 需要确认后端稳定的 `statusbar` 字段、状态值、顺序、当前值和只读语义，避免原生字段状态与
  工作流阶段形成两套显示口径。

### 页头动作、显隐和禁用

- `useRecordActionPresentation` 调 `buildContractFormActions`，输入来自 V2 `actionContract`
  和 `statusContract.buttonStatus`；标题、层级、scope、刷新策略和拒绝原因在这里形成。
- `contractFormPresenter` 通过 `backendIdentity`/`actionId` 匹配动作，并调用
  `resolveWorkflowActionAvailability` 以 `actionKey` 或 method 消费
  `workflowContract.actions/availableActions`。
- 显式 `authorizationAllowed=false`、`businessAvailable=false`、`disabled/reasonCode` 和唯一动作
  身份都已有 fail-closed 逻辑；不能退化为按 label 或 `includes()` 猜动作。

### 执行与回读

- `useFormActionRuntime.runAction` 先做确认、原因参数和保存前置检查，再通过
  `executeButton` 执行 `record_button`，使用 `backendIdentity/actionId/sourceWidgetId` 作为身份。
- 成功路径先走 `refreshPolicy`，没有声明时才 `reload()`；失败路径设置 `runAction` 错误反馈，
  不复用执行中的动作身份。
- `useRecordFormActions.saveRecord` 已有失败保留输入、冲突恢复和成功回读；本批只需要确保动作
  路径与合同刷新使用同一服务端事实。

### 当前前端风险

1. `workflowContract` 在 V2 decoder 只是 `optionalRecord`，前端没有严格结构校验；需要与后端
   Schema 对齐并 fail-closed。
2. 状态栏当前优先由原生表单字段形成，`workflow.statusbar` 主要是只读开关；需要核对两个入口
   是否实际显示同一状态值。
3. `workflowContract` 的可用动作只有 actionContract 规则能绑定到执行器；没有匹配动作规则的
   availableAction 不能被前端猜出执行 adapter。
4. `normalizeWorkflowActionRows` 是兼容辅助函数，当前页面主路径不依赖它；不能把它的存在当作
   workflow action 已完整消费。

## 验证与证据

等待后端稳定样本，再执行 `verify.frontend.canonical_form_presenter.unit`、
`verify.frontend.contract_v2_runtime_policy.unit`、镜头测试及两入口定向浏览器验收。
