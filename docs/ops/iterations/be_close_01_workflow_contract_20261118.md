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
- 已用受管 acceptance carrier 采集真实最终 API 样本；付款提交后回读
  `state=submit`，项目提交/启动后回读 `lifecycle_state=in_progress`。
- 项目业务阻断样本的 `close` 因存在未完结付款申请而 disabled，原因码
  `P0_PROJECT_TERMINAL_BLOCKED`；付款 approved 样本的 `done` 因必须走
  专业付款登记而 disabled，原因码 `PAYMENT_EXECUTION_REQUIRED`。
- V2 Schema 字节变化后，契约生命周期摘要和四个示例中的
  `schemaSha256` 已通过唯一同步入口重新绑定。

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
- `verify.approval.contract_closure.orm`：3 tests PASS。
- `verify.backend.contract_lifecycle.authority`：57 tests PASS，
  schema digest=`f06471c4c2cdb7c5bcbd0877303ee46b6bf29523a3a2f1f5b37bd4d6cd5ad139`。
- `verify.ci.workflow.contract`：440 tests PASS。
- `verify.frontend.standard_preview.unit`：181 tests PASS。
- `verify.unified_page_contract.v2.{action,assembler,runtime,schema,status}`：
  178 assertions PASS。
- `verify.frontend.dev.incremental.unit`：170 tests PASS。
- `ci.local.iteration`：PASS，受影响 target 集合 21 项全部真实执行通过。
- `bash -n`（受管验收入口）、相关 Python `py_compile`、`git diff --check` PASS。
- `verify.workflow_contract.be_close_01.samples`：已生成 2 个新建目录、4 个
  记录契约、2 个动作执行后回读；8 份 workflow contract 全部通过 Schema。
  该证据需在最终后端提交后重新生成一次，避免 `contract_lifecycle.py` 和
  示例摘要更新造成 served SHA 与样本读取不一致。

## 交接

- 后端最终样本：
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/be_close_01_workflow_contract_samples_v1.json`
- 运行时身份：
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/be_close_01_workflow_contract_runtime_ids_v1.json`
- 验收环境：`sc-frontend-acceptance` profile，`sc-local` project
  `sc-fe-r2-p1-01`，database `sc_frontend_acceptance`，backend HTTP
  `127.0.0.1:18082`。
- 最终样本必须在最终提交 SHA 上重新采集并登记后，才可交给前端联调。
- 后端产品候选：`a94d6c093595019f97e1e1c14690cba32f8d80c9`。
- 最终 API 样本 `served_sha=expected_sha=a94d6c0935...`；8 份
  workflow contract 已再次通过 Schema，付款提交和项目启动均完成回读。
- 前端消费入口：
  `.runtime/agent-runs/BE-CLOSE-01-WORKFLOW-CONTRACT-20261118/be_close_01_workflow_contract_samples_v1.json`
  与验收环境 `http://127.0.0.1:18082`（entry namespace `acceptance`）。
