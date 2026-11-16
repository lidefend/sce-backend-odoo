# Change Impact Driven Verification · P4-00 批次记录

## 身份

- 分支：`codex/change-impact-verification-20261116`
- 主线基线：`3c7682647352cdf52b790e9a46b893e2535be77d`
- 工作树：
  `/home/lidefend/workspace/sce-backend-odoo-change-impact-verification-20261116`
- 当前阶段：`active`，P4-00 尚未开始执行盘点

## 责任层声明

- Formal Product Layer：P4 ops delivery tool
- Layer Target：变更影响分类、验证选择、执行图与证据治理
- Module：CI planning、contract verification、presentation acceptance、backend/ORM
  acceptance、delivery governance
- Standard vs User-Specific：repository-wide verification governance
- Why Here：验证触发、执行、复用和门禁属于 P4 交付工具，不定义产品契约或业务语义。
- Why Not Elsewhere：本批不改 P0-P3 契约、前端呈现、业务规则、ACL、ORM 或运行数据；
  路径规则不能替代实际契约与消费关系识别。
- Blast Radius：仅 `.agent/` 专题元数据与该专题审计文档；无数据库、浏览器、服务或部署访问。

## 已登记的治理切入点

当前最高优先级假设是：验证门禁把代码位置当成产品影响范围的主要代理，而非判断代码实际改变
了什么能力、影响了哪一层消费。P4-00 必须用命令、依赖和断言证据确认该假设覆盖哪些入口，
并记录未覆盖范围；不得把已识别案例直接推广成未经审计的全局结论。

新的产品验证架构固定为：

- L1 Contract Verification
- L2 Presentation Verification
- L3 Business Acceptance

代码质量、安全、类型、依赖、构建、精确身份、CI 和审查归 L4 Delivery Governance，
不再与浏览器或业务验收混为一谈。

## 当前批次边界

P4-00 是只读盘点。范围包括 CI workflows、merge/publish preflight、acceptance evolution、
frontend presentation、managed ORM/backend shards、contract/schema/decoder tests、browser
and business acceptance、evidence lifecycle、database upgrade/environment preparation。

每个验证项必须回答八个问题：

1. 验证什么？
2. 由什么变更触发？
3. 实际执行哪些测试？
4. 依赖哪些服务和数据库？
5. 能发现什么缺陷？
6. 能证明什么？
7. 不能证明什么？
8. 是否与其他验证重复覆盖？

`frontend-contract-form-consumer` 等名称不得作为作用证明；必须追踪实际调用组件、页面创建、
浏览器依赖、布局断言和业务写入。

## 明确排除

- 不实施 P4-01 或后续批次。
- 不修改产品代码、契约 Schema、Decoder、Renderer、组件或业务逻辑。
- 不修改验证断言、豁免、必需门禁或当前路径映射。
- 不执行数据库升级、fixture、浏览器矩阵或运行态验收。
- 不推送、合并、发布或部署。

## 验证状态

- L0 身份：passed，新工作树位于精确主线基线且初始 clean。
- L1 台账：passed，`make verify.agent.ledger.unit`，18 tests；原始日志
  `.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/agent_ledger.log`。
- L1 文档基线：passed，`ENV=dev make verify.docs.links`，1 check；原始日志
  `.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/docs_links.env-dev.log`。
- L1 执行策略：passed，`make verify.baseline.iteration.execution.policy`，19 tests；原始日志
  `.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/iteration_policy.log`。
- L2-L4 产品验证：not_run，本批尚未产生路径映射、执行器或产品行为变更。
- L5 审查/发布：not_run。

`make ci.local.iteration` 首次运行在 `verify.frontend.console.guard` 停止：
`frontend/apps/web/node_modules/.bin/esbuild` 在新工作树中不存在。该失败分类为
`environment_defect`，不是本专题元数据或文档检查失败，也不据此宣称入口通过。原始日志为
`.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/iteration.log`。

`verify.docs.links` 在未声明环境下命中 72 条仓库既有坏链并拒绝通过；报告中没有本专题新增
文档，属于仓库既有链接基线。随后按仓库登记的 `ENV=dev` 本地基线（允许最多 200 条既有
坏链）重新执行并通过。未修改坏链、阈值或工具以掩盖该基线。

## 下一精确动作

执行 P4-00-01：逐项盘点 `.github/workflows/**`，从 workflow job、Make 入口和命令追踪到
实际测试、服务、数据库、断言、可证明与不可证明范围，并将结果写入四项 P4-00 交付物。
