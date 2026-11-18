# FE-CLOSE-01 两入口工作流办理闭环

- 前端分支：`feature/fe-close-01-workflow-handling-20261118`
- 接受主线：`ea3d5541dd00ac3aaf048c91e685dc60e2ac3ac9`
- 后端依赖：`BE-CLOSE-01` PR
  [#933](https://github.com/lidefend/sce-backend-odoo/pull/933)
- 后端 PR 合并前 head：`f4bf008483bfed462eb72e0f033e2f024c9c308d`
- 后端合并主线：`ea3d5541dd00ac3aaf048c91e685dc60e2ac3ac9`
- 业务范围：付款申请、项目启停管理
- 当前状态：`ea3d5541` 上的两入口产品验证通过，等待最终本地门禁、提交与 PR 远端门禁

## 边界

前端只消费后端工作流事实：真实状态字段、当前状态、稳定动作身份、授权和业务
可用性、拒绝原因及刷新策略。前端不新增审批或生命周期规则，不按按钮文字猜动作，
不用原生状态顺序推导实际流程历史。

本批不包含搜索、草稿自动恢复、Renderer 扩展、性能控制或全量 91 入口验收。

## 最终契约交接

真实 API 样本绑定：

- `served_sha = expected_sha = ea3d5541dd00ac3aaf048c91e685dc60e2ac3ac9`
- `database = sc_frontend_acceptance`
- actor：`fixture_role_config_admin`，公司 `FE Company A`
- 2 个新建动作目录、4 个记录样本、2 组真实执行回读，共校验 8 份 V2 契约
- 样本路径：
  `sce-backend-odoo-acceptance-scope-20261109-be-close-01-20261118/.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/be_close_01_workflow_contract_samples_v1.json`

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

## 前端实现

1. 完整 `workflowContract.statusbar` 现在是记录页主状态栏来源。字段、当前状态、
   合法选项、只读约束和来源在消费端严格核对；字段与原生 statusbar occurrence
   冲突时抛出 `ContractGapError`。状态选项顺序不再被解释为实际流程历史。
2. workflow 动作继续按声明身份消费。`save` 动作允许 `method=null`，普通对象动作
   仍要求有效 method；缺失或互相矛盾的身份失败关闭。
3. 已授权但业务不可用（`authorizationAllowed=true`、
   `businessAvailable=false`）的动作保持可见、禁用，并直接展示后端
   `blocked_message`。只有未授权动作隐藏。
4. 既有 `useFormActionRuntime`、确认框、busy、错误反馈和服务端回读链保持不变；
   成功后使用声明的刷新策略重新读取记录、状态和下一组动作。
5. 新增付款申请定向浏览器入口，覆盖失败时保留用户输入、纠正后重试、审批动作、
   状态自动刷新和业务阻断原因展示。

## 验证

### 静态与单元

| 检查 | 结果 |
| --- | --- |
| `verify.frontend.canonical_form_presenter.unit` | PASS，177 |
| `verify.frontend.product_page_header.unit` | PASS，162 |
| `verify.frontend.contract_header_action.unit` | PASS |
| `verify.frontend.contract_v2_runtime_policy.unit` | PASS，6 |
| `verify.frontend.contract_basis.unit` | PASS，15，open defects 0 |
| `verify.frontend.typecheck.strict` | PASS |
| `verify.frontend.dev.incremental.unit` | PASS，183 |
| `verify.agent.resume.unit` | PASS，66 |
| `ci.local.iteration` | PASS，退出码 0 |
| `ci.delivery.freeze.prepare` | PASS，生成证据已刷新并审阅 |

最终后端 API 样本已注入 `verify.frontend.canonical_form_presenter.unit`，输出
`workflow-contract-sample PASS contracts=8`。

### 运行台账 readback 修复

付款入口首次真实执行通过后，`make agent.run.record` 拒绝回执：运行台账把测试将要
生成的 runtime readback 与源码一起冻结，导致测试更新 readback 后被误判为输入漂移。
分类为 `validation_tool_defect`，仅修复 P4 台账工具：

- `begin` 冻结源码、工具、上游回执、candidate 与 environment 声明；
- 声明的 runtime readback 允许由本次检查创建或刷新；
- `record` 将刷新后的 readback 写入最终回执，之后 readback 再变化仍会使回执失效；
- 源码或上游在运行期间变化仍拒绝记录；新增正向和反向单测覆盖该边界。

修复后首次记录尝试仍受验收数据前置状态影响：

- 直接重跑付款入口时记录已在上一轮变为 `approved`，安全失败于
  “`payment submit action is not contract-declared`”；
- 通过 `acceptance.frontend.fixture` 恢复夹具后，旧 resolver 产物仍指向重置前的记录
  ID，再次安全失败于未被前端观察到的旧契约；
- 通过 `verify.dev.acceptance.record_identity.resolve` 重解析真实记录身份后重跑通过。

原始失败日志均保留；没有放宽入口断言，也没有把夹具污染伪装成产品通过。

### 付款申请真实办理

浏览器入口：

```text
SC_ENTRY_BROWSER_MODE=workflow \
  make verify.frontend.business_entry.payment_request.browser
```

结果：

- `draft`：声明 `save_draft/submit/cancel`。
- 当前真实记录身份由 resolver 解析为 `payment.request#414`。
- 注入一次传输失败：备注输入保持，页面显示可读错误，状态保持 `draft`。
- 重试提交：确认提交提示出现，服务端回读为 `submit`，下一组动作为
  `approve/reject/cancel`。
- 审批通过：确认审批提示出现，服务端回读为 `approved`。
- `done` 保持可见且 disabled，原因码 `PAYMENT_EXECUTION_REQUIRED`，原因文案与
  后端 `blocked_message` 一致。
- 控制台无意外错误；注入的 503 作为预期失败单独记录。

证据：

`.runtime/agent-runs/FE-CLOSE-01/payment_workflow_browser/summary.json`

### 项目启停真实办理

浏览器入口：

```text
make verify.frontend.business_entry.lifecycle.browser
```

结果：

`draft → submit/approved → in_progress → done → closing → warranty → closed`

每一步都使用运行时契约声明的动作和方法，确认框、服务端回读、主状态栏和下一组
动作均一致；终态 `closed` 不再提供可执行动作。

证据：

`.runtime/agent-runs/FE-CLOSE-01/project_lifecycle_browser/summary.json`

## 未完成边界

- BE-CLOSE-01 PR #933 已合入 `ea3d5541`；前端 #935 已同步该主线，但新 head
  仍需当前组合的最终验证和远端检查。
- 发布时必须以同步后的前端提交和 `ea3d5541` 后端主线作为同一验收组合。
- 浏览器完成后已通过受管 `acceptance.frontend.fixture` 恢复验收夹具；恢复后
  lifecycle carrier 重新生成，因此其运行时数值 ID 变化不影响已绑定的原始证据。
- 合并、部署和目标环境产品交付均未宣称。

## 回滚

回退本批前端工作流消费提交、浏览器验证入口及 runtime readback 记录修复即可；
不需要恢复 schema、数据库迁移或部署状态。验收 fixture 已在浏览器完成后通过受管
入口恢复。
