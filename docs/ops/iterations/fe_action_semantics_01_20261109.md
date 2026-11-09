# FE-ACTION-SEMANTICS-01：前后端业务动作语义统一

## 批次边界

- 批次基线：`ce5af3f04f5cbb7cb6b95ff659d79564808ef612`，包含 PR #848 的本地前端候选成果。
- Formal Product Layer：P0 platform kernel product。
- Layer Target：Contract V2 Action Semantics。
- Module：Action Rule、Button Status、Action Guidance、execute_button、P1 业务动作 Producer、前端 Action Presenter 与 CanonicalActionBar。
- Standard vs User-Specific：平台工程标准。
- Why Here：现有 Contract V2 已具备表达可见、授权、业务可用、disabled 和 reason 的字段。
- Why Not Elsewhere：不新建平行权限/动作 Registry；P1 业务资格仍由业务模块声明；前端只消费。
- Blast Radius：所有产生或消费动作状态的 P0/P1 路径；首批产品样板为付款申请“生成付款登记”。

## 设计目标

分离四个问题：

1. 动作是否向用户展示；
2. 用户是否有执行授权；
3. 当前业务状态是否允许推进；
4. 当前交互是否正在执行或等待。

## 状态矩阵

| 授权 | 业务状态 | 前端表现 | 执行结果 |
| --- | --- | --- | --- |
| 无权限 | 任意 | hidden | 后端拒绝 |
| 有权限 | 业务允许 | visible + enabled | 正常执行 |
| 有权限 | 状态不允许 | visible + disabled + reason | 阻止执行 |
| 有权限 | 数据条件待完善 | 按业务补录引导策略 | 服务端最终校验 |
| 有权限 | 正在执行 | 临时 disabled/loading | 防止重复提交 |
| 有权限 | 能力不支持 | hidden 或明确降级 | 不进入非法执行 |

## 字段职责

| 字段 | 职责 |
| --- | --- |
| visible | 是否向当前用户展示动作 |
| authorizationAllowed | 是否具有执行授权 |
| businessAvailable | 当前业务状态是否允许推进 |
| enabled | 当前投影动作是否可执行 |
| disabled | 是否处于不可执行状态 |
| reasonCode | 不可执行原因的稳定身份 |
| reasonMessage | 面向用户的原因说明 |
| allowed | 兼容执行许可，不得与业务可用性矛盾 |

前端 disabled 不是安全边界；`execute_button` 必须继续执行最终 ACL、状态、身份、并发和数据一致性校验。

## PR #848

- 保留 CanonicalActionBar Direct/Overflow disabled reason 技术成果。
- 不独立合并。
- 纳入本统一批次。
- 不得在没有权威业务依据时扩张 disabled reason 消费范围。

## 执行阶段

- 01A：全量 Producer 清查。
- 01B：冻结字段语义和责任矩阵。
- 01C：前后端统一实施。
- 01D：真实业务验收。

## 当前状态

- 01A：PASS（权威 Producer/Consumer 分类清单见 Action Semantics v1）
- 01B：PASS（字段责任与状态矩阵已冻结）
- 01C：IN_PROGRESS（核心投影、付款样板和审计工具已修正，正在完成门禁）
- 01D：NOT_STARTED
- 合并、部署：未执行

## 01C 首批实施

- P0 `authorizationAllowed=false`：隐藏动作，reason 保留为
  `ACTION_NOT_AUTHORIZED` 供诊断。
- P1 `businessAvailable=false`：保持 visible disabled + reason。
- 前端不再把 business denial 反写为 `authorizationAllowed=false`。
- 付款执行拆分为：
  - approved/type/fully-paid/active-execution 业务状态；
  - payment basis/payee account 数据完整性；
  - actor authorization；
  - `enabled` 仅在三个维度均满足时为 true。
- 投影 `blocked_message` 为 `reasonMessage`，使授权/业务/数据拒绝具有稳定
  reason code 与用户可读原因。
- 通用工作流目录仅作为状态候选和收紧输入，不充当执行授权；显式
  `authorizationAllowed=false` 不会再被改写为 `businessAvailable=false`。
- 组装缓存身份升级为 `ui-contract-v2-action-semantics-auth-business-v33`，
  并重钉装配输入摘要，防止旧动作语义继续从缓存供出。

## Producer 分类收口

- Contract V2 业务动作：原生表单按钮、付款申请动作、生成付款登记、单据
  创建入口和原生 Action Guidance。
- 支撑权威：工作流状态目录和 `execute_button` 最终执行边界。
- 非 Contract V2 表面：旧 `action_list` 项目引导、项目推荐动作、产品配置
  工具按钮、导航/路由入口、My Work 命令。它们不得被统一改写成
  `visible+disabled`，也不作为本轮业务动作交付证据。

## 门禁记录

- `test_unified_page_contract_v2_mobile_compact.py`：139 tests PASS。
- `verify.unified_page_contract.v2.runtime`：23 + 139 tests PASS，runtime guard
  score=6。
- `verify.unified_page_contract.v2.action`：PASS，actions=7。
- `verify.unified_page_contract.v2.status`：PASS，widgets=4 buttons=2。
- `verify.unified_page_contract.v2.assembler`：缓存身份重钉后 PASS。
- `verify.execute_button.authority.unit`：37 tests PASS。
- `verify.frontend.canonical_form_presenter.unit` 与
  `verify.frontend.contract_header_action.unit`：PASS。
- `workflow_inventory_profile_method_guard`：补齐已声明方法后 PASS。
- `ci.local.iteration`：PASS，实际执行 20 个目标；receipt
  `.runtime/frontend-dev-validation/executions/20261109T045112Z-2215379-628180713/receipt.json`。
- 付款能力 ORM：63 tests PASS，source unchanged，receipt
  `.runtime/test-baseline/1794199968022763220/receipt.json`。
- `TestWorkflowContractBackend` 单独运行仍存在历史夹具失败（31 tests 中
  1 failed / 13 errors），失败发生在测试构造付款/费用/收款记录时被现有业务
  guard 拒绝，不是本轮 action projection 断言失败；保留为独立基线问题。
