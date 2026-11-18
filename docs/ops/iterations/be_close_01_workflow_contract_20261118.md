# BE-CLOSE-01 工作流契约正确性收口

- 分支：`feature/be-close-01-workflow-contract-20261118`
- 基线：`9821a9c688cbd4abb44f378051fc6c6362c5d8cd`
- 状态：`in_progress`
- 范围：付款申请、项目启停管理
- 排除：前端消费、搜索、草稿恢复、Renderer、transitions

## 接口规则

1. `workflowContract` 只有两种形态：`workflowActionCatalogContract` 和
   `workflowRecordContract`。新建目录不发布 `record_id`、记录 target 或
   `availableActions`；记录契约必须绑定真实记录身份。
2. `key` 是业务命令身份，`method` 是执行目标，不要求同名。动作目录内 key
   唯一；记录动作必须精确引用目录，`method`、`target.method`、intent、
   kind 和 semantics 必须一致。付款的 `complete` 已迁移为 `done`，所有引用
   必须同步。
3. `save_draft` 继续走普通表单保存：`intent=data.write`、`kind=save`、
   `method=null` 合法。对象方法动作必须有有效 method 和匹配的
   `target.method`。
4. 主状态栏使用真实模型字段：付款为 `state`，项目为 `lifecycle_state`。
   `field/current/states` 同源；`businessPhase` 是可保留的归一化摘要，
   `approvalPhase` 是独立审批摘要，二者不能与主状态栏争用当前状态。
5. 契约可用性和真实执行共用模型拥有的只读业务检查。读取契约时不试执行
   action，不通过回滚探测；执行时仍重新校验。相同事实下契约 enabled 但
   模型守卫必然拒绝，属于本批必须修复的缺陷。
6. `action_domains` 只用于未授权或明确不适用排除。已授权但业务状态、证据
   或前置事实不足的动作保留为 disabled，并提供稳定原因与可读说明。规则
   求值异常按生产缺陷停机和上报。
7. enabled 动作的 `reason_code="OK"`、disabled 的 `reason_code` 非空且
   `blocked_message` 非空；severity 在生产、Schema、前端使用同一规范。
   Warning 可与 enabled 并存，不自动禁用。

## 当前实现

- 已建立 create/record 两类 Schema、动作身份和禁用原因约束。
- 已修正付款 approved 状态的 `done -> action_done` 身份及 references。
- 已为付款完成动作增加“必须通过专业付款登记”的业务阻断。
- 付款与项目都把授权、可见性和业务阻断拆开：未授权动作省略；已授权但业务
  状态/事实不足的动作保留为 disabled，并输出原因。
- 项目生命周期终态守卫已抽成模型只读 blocker，契约投影和真实状态变更共用；
  状态机合法性先校验，再执行事实守卫。
- statusbar 的 `field/current/states` 已回到 `state` 和 `lifecycle_state`
  的真实字段与 Selection，并增加运行时一致性自检。
- 已增加 schema、HTTP probe、运行时身份解析和 BE-CLOSE-01 定向测试入口。
- 正在用已提交候选启动受管验收 carrier，采集最终 API 样本。

## 发现

- 旧 Schema 只约束 `submissionRequirements`，无法区分创建目录与记录执行。
- `statusbar.field=__workflow_phase` 与原生状态栏主字段存在双口径风险。
- 项目 `close/warranty` 的结算/付款守卫此前只存在于实际 action，未进入
  契约可用性。
- payment `complete` 与原生 `action_done` 的命名需要统一 identity/reference。
- 旧 workflow-samples 是手写结构负例，不能作为前后端联合验收证据；现已移除。
  Schema 单测中的对象仅作为结构测试输入。联合交接证据
  必须由真实 HTTP 请求生成。
- 全量 `workflow_contract_backend` 标签在 fresh `sc_test` 中会运行非本批模型
  的旧夹具假设，当前 receipt
  `.runtime/test-baseline/1794976835787170135/receipt.json` 为 1 failed / 13
  errors；失败集中在共享审批模板的既有声明漂移和缺少 demo/fixture 数据，
  不属于本批固定标签。该失败未记为本批通过，也未通过削弱断言处理。

## 验证

- `verify.workflow_contract.be_close_01.unit`：10 tests PASS；日志
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/be_close_01_unit.log`。
- `verify.workflow_contract.be_close_01.orm`：8 tests PASS；fresh isolated
  `sc_test` receipt
  `.runtime/test-baseline/1794978881822833353/receipt.json`；日志
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/be_close_01_orm.log`。
- `verify.workflow_action_semantics.guard`：20 tests PASS；日志
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/workflow_semantics.log`。
- `verify.payment.approval_state_machine.unit`：203 tests PASS；日志
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/payment_state_machine.log`。
- `verify.model.ui_dependency.guard`、`verify.backend.boundary_guard`：PASS。
- `bash -n`（受管验收入口）、相关 Python `py_compile`、`git diff --check` PASS。
- `verify.workflow_contract.be_close_01.samples`：NOT RUN。必须先提交当前
  候选，使 acceptance artifact 与 HTTP carrier 绑定同一精确 SHA。
