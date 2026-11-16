# Change Impact Driven Verification · P4-00 批次记录

## 身份

- 分支：`codex/change-impact-verification-aligned-20261116`
- 主线基线：`730b82cf60f60399a70901a7fcd65476dc718f93`
- 工作树：
  `/home/lidefend/workspace/sce-backend-odoo-change-impact-verification-20261116-aligned`
- 当前阶段：`active`，P4-00 盘点与设计方案已完成，等待独立审查

早先误开并已关闭 Draft PR #907。该 PR 只用于审查讨论，未合入主线。其后 `origin/main`
更新到 `730b82cf60f60399a70901a7fcd65476dc718f93`，本候选已从该精确主线重新建立对齐
工作树；旧工作树保留为恢复来源，不再继续写入，也不会再开中间 PR。只有验证体系全部收敛后
才形成一次最终集成 PR。

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

对齐最新 main `730b82cf` 后，`frontend/apps/web/src/app/contracts/v2/schema.ts` 已从旧的
`frontend-contract-form-consumer` 改为 `frontend-contract-v2-codec`，只要求
`frontend_contract`，不再自动要求 presentation evidence。该变化是真实主线改进；审计保留
Renderer registry 仍缺 presentation evidence 的欠触发问题，不能把单个 codec 规则修复当作
完整影响引擎已经完成。

新的产品验证架构固定为：

- L1 Contract Verification
- L2 Presentation Verification
- L3 Business Acceptance

代码质量、安全、类型、依赖、构建、精确身份、CI 和审查归 L4 Delivery Governance，
不再与浏览器或业务验收混为一谈。

所有者追加边界（2026-11-16）：后端迭代只需要证明契约正确，不要求浏览器结果。纯后端候选默认
执行 L1；只有业务状态、ORM、ACL 或跨模型流程变化时追加 L3。浏览器 L2 只由真实前端
runtime/Renderer/组件/交互变化触发，或由明确登记的真实页面兼容缺陷复现触发。后端契约消费
正确性由 strict decoder、producer/consumer 和 contract unit 证明。

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

本批新增可复现只读审计器：

- `scripts/audit/generate_change_impact_verification_inventory.py`
- `scripts/audit/test_generate_change_impact_verification_inventory.py`
- 手工入口 `make audit.change_impact.verification`

手工入口只生成 P4-00 四份审计物，不进入 local.quick、professional、merge 或 frontend release
的必需闭包。设计交付物为
`docs/audit/change-impact-verification/change_impact_verification_design_v1.md`。

`verification_mapping_matrix.json` 是 98 KB 索引；完整内容拆分到 workflow、Make target、
gate script 和 script lifecycle 分片，全部低于仓库历史扫描的 5 MiB threshold。拆分不减少
覆盖，每项仍保留八问责任。

首次远端 `public_guard` 因单文件 6.5 MiB 触发 RH007 oversized-blob 失败；`merge_policy_gate`
准确传播该失败。随后按覆盖不变原则拆分索引与 part 文件，最大 part 约 3.5 MiB，重新生成、
定向测试和 local iteration 均通过，未添加 oversized-blob 例外。

独立审查后的 P4-00 修订：

- 事实、静态推断、人工审阅和 UNKNOWN 分开记录。
- `duplicate_or_overlap` 未完成 assertion 级分析时固定输出 UNKNOWN，不输出空数组。
- 当前 `obligation_linked_items=0`、`assertion_linked_items=0`，明确 P4-00 不是完整语义审计。
- 新增 `impact_analysis_acceptance_matrix.json`，覆盖 Decoder、Renderer、CSS、ORM/ACL、
  混合变更、动态 UNKNOWN、rename/delete、测试/fixture、文档和错误证据复用。
- 新增 False Negative、Evidence Reuse Error、Obligation Coverage、Unknown 和 stale-proof
  cutover 指标。
- 修订说明和未解决问题见 `docs/audit/change-impact-verification/review_remediation_v1.md`。

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
- 审计器：passed，`make verify.change_impact.verification.unit`，12 tests；原始日志
  `.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/change_impact_inventory.final.log`。
- CI workflow contract：passed，`make verify.ci.workflow.contract`，434 tests；原始日志
  `.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/ci_workflow_contract.final.log`。
- 前端增量路由器：passed，`make verify.frontend.dev.incremental.unit`，156 tests；原始日志
  `.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/frontend_incremental.log`。
- 增量路由修复后：`make ci.local.iteration` PASS，执行 6 个必需 target，结果
  `ready_for_existing_gates`；原始日志
  `.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/iteration.design.after_mapping.log`。
- L2-L4 产品验证：not_run，本批没有产品代码、路径映射、执行器或产品行为变更。
- L5 审查/发布：not_run。

`make ci.local.iteration` 首次运行在 `verify.frontend.console.guard` 停止：
`frontend/apps/web/node_modules/.bin/esbuild` 在新工作树中不存在。该失败分类为
`environment_defect`，不是本专题元数据或文档检查失败，也不据此宣称入口通过。原始日志为
`.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/iteration.log`。

随后通过既有受管入口 `make fe.install.cached` 完成离线、锁定、禁用安装脚本的依赖恢复；
未手工拼装 pnpm 或修改锁文件。环境恢复后重新执行 `make ci.local.iteration`：PASS，结果
`ready_for_existing_gates`，最终增量检查为 `verify.agent.ledger.unit` 18 tests PASS。原始日志为
`.runtime/agent-runs/CHANGE-IMPACT-VERIFICATION-20261116/iteration.after_deps.log`。

`verify.docs.links` 在未声明环境下命中 72 条仓库既有坏链并拒绝通过；报告中没有本专题新增
文档，属于仓库既有链接基线。随后按仓库登记的 `ENV=dev` 本地基线（允许最多 200 条既有
坏链）重新执行并通过。未修改坏链、阈值或工具以掩盖该基线。

## 下一精确动作

完成审计器、台账、设计文档和生成物的本地定向验证，提交并发布设计 PR。PR 审查合格且合入前，
不得实施 P4-01，不得修改现有验证映射或必需门禁。
