# FE-CLOSE-01 两入口工作流办理闭环

- 前端分支：`feature/fe-close-01-workflow-handling-20261118`
- 接受主线：`64f2e68ea1b80464fd080bb93b1a83312decc8c4`
- 后端依赖：`BE-CLOSE-01` PR
  [#933](https://github.com/lidefend/sce-backend-odoo/pull/933)
- 后端候选：`d3e2f8d4f6a3f3c7250316ee51a690dac470591a`
- 业务范围：付款申请、项目启停管理
- 当前状态：批次产品验证通过，等待提交、发布和远端门禁

## 边界

前端只消费后端工作流事实：真实状态字段、当前状态、稳定动作身份、授权和业务
可用性、拒绝原因及刷新策略。前端不新增审批或生命周期规则，不按按钮文字猜动作，
不用原生状态顺序推导实际流程历史。

本批不包含搜索、草稿自动恢复、Renderer 扩展、性能控制或全量 91 入口验收。

## 最终契约交接

真实 API 样本绑定：

- `served_sha = expected_sha = d3e2f8d4f6a3f3c7250316ee51a690dac470591a`
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
| `verify.frontend.dev.incremental.unit` | PASS，174 |
| `ci.local.iteration` | PASS，退出码 0 |

最终后端 API 样本已注入 `verify.frontend.canonical_form_presenter.unit`，输出
`workflow-contract-sample PASS contracts=8`。

### 付款申请真实办理

浏览器入口：

```text
SC_ENTRY_BROWSER_MODE=workflow \
  make verify.frontend.business_entry.payment_request.browser
```

结果：

- `draft`：声明 `save_draft/submit/cancel`。
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

- BE-CLOSE-01 PR #933 的四个远端后端分片和依赖门禁仍在运行；本批不宣称主线
  集成完成。
- 本批尚未提交或发布前端 PR；发布时必须以当前前端提交和
  `d3e2f8d4f6a3f3c7250316ee51a690dac470591a` 后端候选作为同一验收组合。
- 合并、部署和目标环境产品交付均未宣称。

## 回滚

回退本批前端工作流消费提交及其浏览器验证入口即可；不需要恢复 schema、数据库迁移
或部署状态。验收 fixture 已在浏览器完成后通过受管入口恢复。
