# BE-U06 Approval Contract Closure

## Scope

本批次从已复审的 `54dbbc1e9ae5864030ea9dfd8cd2b4409ef7f6cd` 继续，验证真实
`tier.review` 任务如何经过当前审批策略、当前身份和原生视图/动作，形成最终
`UiContractV2Handler` 页面契约，再由 `ExecuteButtonHandler` 使用交付动作身份执行并在
服务端重验。

模型级 Odoo ACL、记录规则和业务状态机继续由所属模型负责。本批次只收口这些既有事实
如何进入能力/页面契约、如何被前端消费，以及执行入口如何重验当前事实。

## Samples

| 样本 | 角色 | 已证明的链 |
| --- | --- | --- |
| 付款申请审批（主样本） | 财务审核人 | 真实任务 → 待办 → 最终页面 → 通过/拒绝动作 → reason 输入 → 服务端执行 → 任务与业务状态回读 → 工作列表返回 |
| 日常合同审批（非付款对照） | 财务审批人只有单据读权限 | 同一任务来源执行明确审批方法，不顺带取得合同普通写权限；完成后任务来源消失 |

## Integrated Corrections

| 缺口 | 所属层 | 收口结果 |
| --- | --- | --- |
| `record_button` 未收集、未发送契约声明的动作输入 | P0 `smart_core` + 通用前端运行时 | 前端先收集 `required_params`，后端只接受最终动作规则声明的参数；缺参或夹带未声明参数在执行前拒绝 |
| 工作流动作输入在 V2 投影中丢失 | P0 `unified_page_contract_v2_assembler` | `required_params`、`requires_reason`、`reason_input` 与同一动作身份完成投影，原生 presentation 权威保持 |
| 付款驳回视图仍调用无 reason 参数的 `reject_tier` | P1 `smart_construction_core` | 原生按钮改为现有 `action_approval_reject(reason)`，待办来源授权同步该身份 |
| 财务工作区重新发布 `reject_tier` 旧方法 | P1 业务动作投影 | 业务动作声明的 method 优先；旧别名仅兼容，付款最终契约不再出现 `reject_tier` |
| V2 schema 未声明动作输入字段 | P0 正式契约 schema | 正式 schema、示例摘要与运行时 schema 摘要同源绑定 |

没有新增权限引擎、审批状态机、页面路由或前端业务特判。

## Contract And Execution Evidence

| 层 | 结果 |
| --- | --- |
| 后端 ORM | `verify.approval.contract_closure.orm` 3/3 PASS。真实审批任务、最终 V2 契约和 `ExecuteButtonHandler` 使用同一动作身份；缺 reason 与未声明参数在副作用前返回 400；合法 reason 执行后任务和单据均为 `rejected`；旧动作重放返回 403。 |
| 通用执行边界 | `verify.execute_button.authority.unit` 37/37 PASS。待办来源仍只授权当前任务、当前审批人及明确决定方法。 |
| 前端契约消费 | `verify.frontend.approval_contract.closure.unit` 12 cases PASS。空/取消 reason 请求数为 0；填写 reason 后只发一次 `execute_button`，并携带同一动作身份及 `action_params.reason`。 |
| V2 契约 | assembler/action/status/runtime、schema 与 lifecycle 目标均 PASS；最终动作规则支持声明输入，schema digest 与示例一致。 |
| 增量门禁 | `make ci.local.iteration` 27/27 个映射目标零退出，零未映射路径；包含 ORM、类型、lint、契约和验收工具检查。 |

关键原始证据：

- `.runtime/test-baseline/1794315441716950134/odoo.log`（最终 27 目标增量聚合中的 ORM）
- `.runtime/frontend-dev-validation/executions/20261110T125713Z-2307750-553156593/receipt.json`
- `.runtime/final-acceptance/my-work-approval/report.json`

## Browser Journey

最终报告绑定：

| 身份 | SHA / 路径 |
| --- | --- |
| 实际后端产品 | `cd08cca11b677b3dda5a3cb3fc98e25b7b1c6552` |
| 当前测试脚本 | `ffe91a818270c57bae569d2913857a3468b4e49f` |
| 前端构建基线 | `40ad974c8c8791a3d045aaa5e1fa9d29d883e526` |
| preview entry | `/assets/index-DB_m0-mN.js` |
| preview entry SHA-256 | `b7ee25350da2bf6d2f7a0a076c331addf9b5f330155e9ae26d587fde269f190f` |
| report SHA-256 | `3ce863af4bc45353760d815561dbbfcae691f3797888dc2cc78f47d601a782ff` |

实际用户旅程：

- J07 待办计数、详情往返、提交、公司 A/B/A 隔离：PASS；`todo_before=6`、`initiated_before=7`。
- J08 从真实待办打开审批页，页面显示事项身份和后端金额；从审批页执行通过；`tier.review` 与付款申请回读批准；待办从 8 降至 7。
- 拒绝路径先经过后端声明的安全确认，再打开 reason dialog；空 reason 时请求数为 0；填写后请求使用 `action_approval_reject` 并携带 `action_params.reason`；服务端回读 `rejected`，同记录不再处于 `pending` 审批状态。
- 项目成员无法看到付款事实，直接访问审批记录进入拒绝页。
- 1440×900、1280×800、390×844 均无水平溢出。

未覆盖：

- 非付款对照已完成 ORM 契约与执行闭环，但本轮没有为它增加第二个浏览器页面旅程。
- 付款审批以单一审批级别样本验证；多级审批的中间状态仍由既有流程测试覆盖，不在本批次伪称已做浏览器验收。
- 本结果为候选批次验收，不代表推送、合并、部署或目标生产环境产品交付。

## Exit

- 审批页面、动作、reason 输入和执行目标来自同一最终契约。
- 执行时重新加载契约并重验任务、记录、权限和状态；旧页面不构成执行授权。
- 前端只负责收集声明输入、展示状态和调用执行，没有新增付款或审批业务判断。
- U06 增量已具备冻结和独立只读复审条件。
