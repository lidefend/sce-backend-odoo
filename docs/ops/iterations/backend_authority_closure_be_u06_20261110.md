# BE-U06 Approval Contract Closure

## Scope

本批次从已复审的 `54dbbc1e9ae5864030ea9dfd8cd2b4409ef7f6cd` 继续，验证真实
`tier.review` 任务如何经过当前审批策略、当前身份和原生视图/动作，形成最终
`UiContractV2Handler` 页面契约，再由 `ExecuteButtonHandler` 使用交付动作身份执行并在
服务端重验。

本批次不改前端、模型 ACL、记录规则、审批引擎或发布数据。模型级 Odoo ACL 只作为既有前提，
验收重点是原生视图、动作与当前权限加工成契约，以及执行时对最新任务事实的重验。

## Samples

| 样本 | 角色 | 要证明的链 |
| --- | --- | --- |
| 付款申请审批（主样本） | 财务审核人 | 审批策略创建真实任务 → 当前待办 → 最终页面 → 两个审批动作 → 任务来源执行 → 付款申请与任务回读 → 过期动作拒绝 |
| 日常合同审批（非付款对照） | 财务审批人只有单据读权限，不具备普通业务写权限 | 同一任务来源可执行明确审批方法，且不顺带取得合同普通写权限；结束后待办消失 |

## Confirmed Differences And Minimal Corrections

1. 付款申请最终页面交付的通过动作是 `action_approval_decision`，而
   `authorize_review_origin()` 原先只接受 `validate_tier/reject_tier`。结果是页面可见、
   任务也分配给当前用户，但工作项来源执行会先被来源授权拒绝。

   修复只增加 `payment.request` 的两个已声明决定方法
   `action_approval_decision/reject_tier`；其他模型仍保持
   `validate_tier/reject_tier`，任意 `action_cancel/action_signed` 等业务方法继续拒绝。

2. 前端 `buildContractFormActions()` 读取动作 `required_params/requires_reason`
   时，归一化中间对象没有复制这两个声明字段，导致只靠 `required_params` 声明原因输入
   的契约可能丢失输入要求。修复在归一化时保留原声明，不增加模型或审批特判。

## Verification

| 层 | 事实 |
| --- | --- |
| 后端契约／ORM | `verify.approval.contract_closure.orm`：2/2 PASS；付款主样本和日常合同对照均从真实审批策略生成 `tier.review`，最终契约由 `UiContractV2Handler` 输出，`ExecuteButtonHandler` 使用契约行的完整动作身份执行，并同时回读任务与业务状态。旧页面动作在任务完成后再次执行返回 403。 |
| 授权方法边界 | `verify.general_contract.review_authority.unit`：17/17 PASS；包含付款决定方法被接受、任意业务方法被拒绝的检查。 |
| 前端契约消费 | `verify.frontend.approval_contract.closure.unit`：10 cases PASS；只渲染交付的两个决定动作，保留 reason 必填要求，缺少原因不执行，忙态禁用，任务完成后两个动作消失。 |
| 前端回归 | `verify.frontend.canonical_form_presenter.unit`：253 个具名 cases 及无计数子检查 PASS；`verify.frontend.contract_header_action.unit`：143 checks/cases PASS，并包含真实浏览器 reason dialog、结果通知和单次提交链。 |
| 增量子门 | `make ci.local.iteration` PASS；执行 15 个必需目标，零未映射路径。前端 lint 为 0 error，严格类型检查通过。 |

原始日志：

- `.runtime/test-baseline/1794304682197884470/odoo.log`
- `.runtime/be-u06-approval-contract-frontend-second.log`
- `.runtime/be-u06-canonical-form-presenter.log`
- `.runtime/be-u06-contract-header-action.log`
- `.runtime/frontend-dev-validation/executions/20261110T095754Z-781786-617504500/receipt.json`

## Browser Status

首次调用 `verify.frontend.my_work_approval.browser` 时，受管入口在浏览器启动前拒绝：
候选仍有未提交变化，且既存 acceptance backend 仍绑定旧基线
`54dbbc1e9ae5864030ea9dfd8cd2b4409ef7f6cd`。这是预期的冻结/环境前提，不是产品失败，
也没有产生浏览器请求或业务写入。

该入口要求 clean 精确 HEAD，并把 acceptance backend 重建到同一 SHA。因此浏览器闭环保持
`not_run`，必须在 U06 实现提交后通过受管 Make 入口重建并执行。预期覆盖：
真实待办 → 审批摘要 → 决定 → 结果反馈 → 回读；缺原因驳回；未授权隔离；
1440×900 与 390×844。

## Exit

- 最终契约只从真实 `UiContractV2Handler` 结果取证，不直接检查中间 resolver。
- 审批动作必须使用契约行中的 `actionId`、`backendIdentity`、`sourceWidgetId` 和
  `button.name`，不能由测试伪造动作权限。
- 执行后同时回读 `tier.review` 和业务单据状态。
- 已完成任务不能继续使用旧页面动作执行；服务端必须重新拒绝。
- 当前批次仅完成源码、ORM 和前端契约消费验证；浏览器办理闭环仍未完成，不宣称部署或产品交付完成。
