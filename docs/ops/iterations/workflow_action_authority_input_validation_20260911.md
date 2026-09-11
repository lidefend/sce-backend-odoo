# Workflow authority 输入校验批次

## 1. 本轮变更

- 目标：证明并关闭 workflow authority 在重复身份、畸形 carrier 与非布尔 `enabled` 输入下错误授予可执行状态的通用 P0 缺口。
- 完成：新增逐动作 authority resolver；同一动作的 exact method、exact action key 与声明 alias 匹配并集必须唯一。可归属到目标动作的非法行失败关闭，无法识别归属的坏节点隔离；合法同标签不同动作与非 workflow 动作保持兼容。
- 消费范围：Canonical Form presenter 与旧表单 workflow bridge 共用同一裁决；非法行不再被 `normalizeWorkflowActionRows` 投影为可执行动作。
- 未完成：收入合同页面产品审查、controller checkpoint 恢复、旧付款/demo 分支退役均不属于本批。

## 2. 影响范围

- Formal Product Layer：P0 platform kernel product。
- Layer Target：前端 Contract V2 workflow action authority 解析与表单动作呈现。
- Module：`frontend/apps/web`。
- Standard vs User-Specific：所有契约驱动表单共用的平台机制，不含施工行业或客户语义。
- Why Here：`workflowContract.availableActions` 已是后端裁决的显示、禁用与去重权威；前端只验证载体类型和身份唯一性并消费结论。
- Why Not Elsewhere：不修改 P1 流程、付款模型、P2/P3 配置或 P4 fixture；后端动作方法仍是最终写操作权限防线。
- Blast Radius：Canonical Form action bar、原生表单 workflow 按钮归一化与可用性；普通非 workflow 动作、路由和数据提交协议不变。
- 启动链：否。Contract/schema：否。default route：否。public intent：否。

## 3. 正确性边界

| 输入 | 结果 |
|---|---|
| 一个合法匹配行，`enabled=true` | 保持可执行 |
| 一个合法匹配行，`enabled=false` | 保持禁用并消费既有原因 |
| 多行命中同一动作的 method/key/alias 并集 | `WORKFLOW_ACTION_IDENTITY_AMBIGUOUS`，不可执行 |
| 命中行的 identity/target/`enabled` 类型非法 | `WORKFLOW_ACTION_AVAILABILITY_INVALID`，仅该动作失败关闭 |
| `availableActions` carrier 非数组且请求为已知流程动作 | carrier 无法安全解释，流程动作失败关闭 |
| 无法识别归属的坏节点或其他动作的坏节点 | 隔离，不禁用无关合法动作 |
| 合法同显示名称但 key/method 不同 | 分别解析，不视为重复 |
| 非 workflow 动作 | unmanaged，保持原 action/status authority |

## 4. 验证

- 修复前：`make verify.frontend.canonical_form_presenter.unit` 非零失败，首个反例显示重复 `action_submit` 身份仍返回第一行。
- 修复后定向：同一命令通过，覆盖重复身份、非布尔 `enabled`、匹配畸形行、不可归属坏节点、无关坏节点、合法禁用、合法同标签不同身份及 Canonical presenter 消费。
- 开发 Quick 首轮：`make ci.local.quick` 在新增文件后按预期阻断于 stale complexity report；已用生成器更新扫描文件数，未降低门禁。
- 修复后开发 Quick：`make ci.local.quick` 完整通过；严格类型、开发构建、lint（0 error，32 个既有 warning）及仓库门禁均通过。因套件启动时工作区仍含本批改动，本次不签发 exact-HEAD receipt。
- 最终受管 Quick：待本地交付提交形成 clean HEAD 后执行；结果以 exact-HEAD receipt 为准。
- 未运行：浏览器、真实保存/审批/支付、fixture、数据库、模块升级与发布验收；本批不需要这些写路径。

## 5. 风险与回滚

- 风险级别：P0 通用动作呈现。主要风险是把合法 workflow 行误判为歧义，已用不同 key/method 但同标签反例及无关坏节点隔离覆盖。
- 缓解：无 `workflowContract` 时保持原行为；只有已知流程动作或明确命中的 carrier 行进入该权威。
- 回滚：回退本批提交即可恢复旧前端解析；没有 schema、数据库或 fixture 回滚步骤。

## 6. 产物与下一步

- 源码：`frontend/apps/web/src/app/contracts/v2/workflowActionAvailability.ts`。
- 定向测试：`frontend/apps/web/scripts/canonical_form_presenter_test.ts`。
- 浏览器/e2e/contract snapshot：N/A，本批无运行态与契约形状修改。
- 下一步：冻结 clean HEAD，取得受管 Quick 证据后进入独立复核与 PR 授权；不提前实施收入合同或 controller 专题。
