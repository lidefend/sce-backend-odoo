# BE-CLOSE-01 工作流契约正确性收口

- 分支：`feature/be-close-01-workflow-contract-20261118`
- 接受主线：`64f2e68ea1b80464fd080bb93b1a83312decc8c4`
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
- `workflow_contract_backend` 最初在 fresh `sc_test` 中暴露了旧夹具没有业务
  公司/项目负责人、共享审批模板仍声明重复 `submit`、以及直接写终态等既有
  问题。这些问题已按正式状态转换、受管业务公司和真实合同方向修正；
  当前完整标签 32 tests PASS，没有跳过或削弱断言。

## 验证复用机制修复

- 根因：receipt 把每个声明的 Make 片段整体哈希。主线在同一
  `make/ci.mk` 增加无关目标后，所有声明该片段的检查都被判 stale。
- 第二个根因：`ci.local.iteration` 的规划报告已经列出 reusable target，
  但执行入口只计算 blocked，没有把 reusable 传给执行器；因此即使 receipt
  全量有效，仍会重新运行目标。
- 修复：`agent_run_context` 对声明片段计算所选目标的 recipe、递归字面
  prerequisite、相关 `$(MAKE)` 调用、`.PHONY` 身份、被引用变量和活动
  include 闭包；同片段无关目标变化不再失效。
- 受保护反例：目标 recipe、到达的前置目标、相关变量、include override
  仍使 receipt 失效。
- 旧 whole-file receipt 只在 Git 能证明 receipt head 的片段字节/模式一致、
  执行时没有 dirty Make 源、历史与当前目标材料一致时投影；非 Make 输入
  继续逐项比较，不能被 Make 投影掩盖。
- 修复：规划器和执行器共用同一组 `reusable_check_targets`；执行入口只运行
  非 reusable、非 blocked 的目标，并分别记录 `requiredTargets`、
  `reusedTargets` 与实际 `targetResults`。全部可复用时写成未运行测试的
  `passed` 复用回执，不伪造 target 结果。
- 修复后的同一 `make ci.local.iteration` 实测：23 个 required target 中
  18 个直接复用，只执行 5 个目标（2 个未登记目标、3 个 stale 检查）；
  receipt 为
  `.runtime/frontend-dev-validation/executions/20261118T071401Z-145006-118439703/receipt.json`。
- stale 检查完成定向回填后，同一 runtime 候选最终为 21 个 registered target
  全部复用，只执行 2 个仍未在 run 登记的目标；receipt 为
  `.runtime/frontend-dev-validation/executions/20261118T072300Z-202686-564824002/receipt.json`。
  这两个目标不是同文件无关变更造成的重复，而是 planner 明确报告的
  registration gap。
- 在本次主线同步场景中，修复后的首次 resume 将 19 个检查中的 17 个恢复为
  reusable；其余 2 个的原因是原始日志字节被后续命令覆盖，不是模型/工具
  输入变化。
- `frontend_dev_incremental` 的另一项既有断言仍要求验收入口只选择
  `verify.ci.scheduled_gates`，但同一入口已明确同时服务
  `verify.frontend.standard_preview.unit`。已修正测试期望为两条路由的并集，
  没有删除标准预览覆盖。

## 稳定基线偏差与恢复

- 远端 `professional_quality_gate` 首次运行本候选时暴露了本地增量计划漏掉
  既有付款测试族的问题。原因不是主线基线失效，而是本地模型改动只选择了
  BE-CLOSE-01 新标签，没有纳入消费 `payment_request` 和
  `workflow_contract_service` 的既有测试责任。
- 已修正生产语义：提交前置检查和动作可用性仍共享 blocker，但 action 执行
  不再绕开调用方传入的 advisory 集合重复计算风险策略；原生明细校验保留
  `ValidationError` 类型和用户可读原因。
- 已修正共享审批档案：`submitted` 只声明 `approve/cancel`，不再保留
  已提交状态重复 `submit` 的死动作。
- 已修正测试夹具：合同工作流测试使用受管业务公司、项目负责人、税组和
  正式状态转换；收款契约使用真实 `type=out` 合同。API 兼容测试不再跟随
  `/web/login` 重定向，并在直接 ORM 对比前显式等待
  `odoo.service.http.request.*` 线程退出，确保只验证 `/api/v1/intent`。
- `TestIntentSmoke`：10 tests PASS，独立 target
  `verify.smart_core.intent_smoke.orm` 耗时约 43s；此前测试文件变化会误触发
  整套权限真相 ORM。
- `workflow_contract_backend`：32 tests PASS。
- 付款动作可用性、P1 付款能力和并发：73 tests PASS。
- 完整 `smart_construction_core` 模块 ORM 基线：563 tests PASS；
  receipt `.runtime/test-baseline/1794991644912767587/receipt.json`。
- 稳定基线约束已独立整理为
  `docs/architecture/stable_baseline_iteration_invariants_v1.md`：模块基线是
  可复用的覆盖责任，不是每次无条件全量重跑；未变化的 receipt 和测试环境
  可按身份复用，受影响测试族必须重新执行，依赖映射无法证明时才回退到完整
  模块基线。
- 测试环境默认改为身份绑定的模板复用：每次仍从 `sc_test_template` 克隆
  fresh `sc_test`，但不再重复安装整套模块。本次 schema 变化后的模板准备
  为 246.9s，紧接着的隔离 ORM 回执为 19.3s；此前每个小标签约需 4 分钟。
  `verify.local.development_lifecycle.unit`：54 tests PASS。

## 验证

- `verify.workflow_contract.be_close_01.unit`：11 tests PASS；日志
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
- 验证复用机制修复后的 `verify.agent.resume.unit`：64 tests PASS。
- 修正路由期望与 reuse 执行后的
  `verify.frontend.dev.incremental.unit`：177 tests PASS。
- `ci.local.iteration`：PASS；稳定基线复用后 21 个已登记 target 直接复用，
  只执行实际受影响的 intent smoke、guard registry 和 2 个尚未登记目标。
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
