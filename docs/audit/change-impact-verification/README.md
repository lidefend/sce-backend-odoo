# Change Impact Driven Verification

本专题是 P4 独立的验证体系治理专项。目标不是继续扩展路径规则，而是根据候选实际改变的
契约语义、呈现行为和业务执行影响，选择最小充分验证集合，并保留能够证明这些影响的证据。

当前 PR 是“盘点 + 设计方案”审查包，不落地新门禁：

- `verification_system_inventory.md`
- `verification_mapping_matrix.json`
- `verification_execution_graph.json`
- `verification_cost_baseline.json`
- `impact_analysis_acceptance_matrix.json`
- `change_impact_verification_design_v1.md`
- `review_remediation_v1.md`
- `p4-01-shadow-planner-v1.md`
- `verification_governance_v2.md`
- `impact_analysis_acceptance_results.json`

`verification_mapping_matrix.json` is the bounded index. Its four companion part files retain the
complete workflow, target, gate-script and script-lifecycle inventories below the repository history
blob threshold:

- `verification_mapping_matrix.workflow_jobs.json`
- `verification_mapping_matrix.make_targets.json`
- `verification_mapping_matrix.gate_scripts.json`
- `verification_mapping_matrix.script_lifecycle.NN.json` shards

设计审查合格前，不修改现有验证映射、必需门禁、产品代码、数据库或验收断言。

## 治理原则

1. 不相关的验证不执行。
2. 相关的验证必须有证据。
3. 未覆盖的风险不能通过路径分类或历史 PASS 自动放行。

## 验证架构

### L1 Contract Verification

证明后端产生的事实正确，前端准确理解契约。责任包括 Schema、Strict Decoder、Contract
Producer、Contract Consumer、Action/View/Search Identity、关系字段规范化与契约兼容性。

核心问题：后端产生的事实是否正确，前端是否准确理解？

### L2 Presentation Verification

证明契约在真实前端中被正确呈现和消费。责任包括 Renderer 选择、组件装配、布局和视觉、
字段/列/顺序、响应式、键盘/焦点/ARIA 与页面交互。

核心问题：契约在真实前端中是否被正确呈现和消费？

### L3 Business Acceptance

证明用户真实操作产生正确业务结果。责任包括业务状态转换、ORM 写入和持久化、权限正负例、
审批及执行、跨模型关联、事务/并发与端到端业务流程。

核心问题：用户真实操作是否产生正确业务结果？

### L4 Delivery Governance

证明版本可以交付。责任包括代码质量、安全、类型检查、依赖与构建、变更范围、精确 HEAD、
CI 与合并前审查。

核心问题：这份代码是否满足工程和发布要求？

L1、L2、L3 是产品行为验证层。L4 贯穿所有层，是交付治理，不得被浏览器验收或其他产品行为
证据替代。

## 变更分类矩阵

| 变更类型 | L1 | L2 | L3 |
| --- | --- | --- | --- |
| Schema 字段扩展 | 必须 | 不需要 | 不需要 |
| Decoder 兼容规则 | 必须 | 通常不需要 | 不需要 |
| 后端契约 Producer | 必须 | 视影响 | 视业务影响 |
| Renderer 注册表 | 必须 | 必须 | 视操作影响 |
| 组件装配与布局 | 必须 | 必须 | 视操作影响 |
| 样式、文案、响应式 | 不重复整套契约验证，按需检查 | 必须 | 通常不需要 |
| 用户交互行为 | 检查对应契约 | 必须 | 视是否改变业务结果 |
| ACL / Record Rules | 必须 | 视可见性变化 | 必须 |
| ORM 写入、业务状态 | 必须 | 视页面影响 | 必须 |
| 跨模型业务流程 | 必须 | 视页面影响 | 必须 |

“不需要”是该变化没有引入相应风险时不重复执行整套验收，不是永久豁免。分类粒度必须落实到
文件、符号、契约字段和行为影响，不能给整个 PR 贴一个唯一标签。

## 混合变更

一个候选可以同时包含多层变化。例如修改 Search Contract、搜索栏组件和筛选业务 Domain 时，
必须分别证明对应契约、呈现和业务层影响，不能因为主要改动属于 L1 而忽略另外两层。

路径只能作为语义分类的候选输入。尤其不能把
`frontend/apps/web/src/app/contracts/v2/schema.ts`
直接映射为 `frontend_presentation`：该文件位置不能证明它修改的是 Renderer、组件行为或页面
消费；必须先识别符号级契约变化、Producer/Decoder/Consumer 关系及实际页面依赖。

## 批次路线

专题按八个批次推进，以保持每批可独立审查、验证和回滚。当前只授权并登记 P4-00；P4-01 的
范围已记录为下一批，剩余批次必须在 P4-00 交付物和成本基线完成审查后按证据拆分。

### P4-00 现有验证体系全量盘点

当前批次只做只读审计，不改产品代码、测试断言、门禁映射、数据库或运行环境。交付物：

- `verification_system_inventory.md`
- `verification_mapping_matrix.json`
- `verification_execution_graph.json`
- `verification_cost_baseline.json`

每个验证项必须回答：验证什么、由什么触发、实际执行什么、依赖哪些服务和数据库、能发现
什么缺陷、能证明什么、不能证明什么、与哪些验证重复。不得仅凭文件名描述测试作用。

### P4-01 变更影响分类引擎

P4-00 审查通过后再进入本批。分类引擎必须支持 L1/L2/L3 多层变更、符号级影响、Schema 字段级
影响、Producer/Decoder/Consumer、Renderer/Component/Page、ORM Model/Business
Method/Workflow 关系；未知影响范围保守处理，并输出分类理由和相关测试集合。

后续批次必须在 P4-00 的实际执行图、成本基线和失败模式上拆分，不一次性重写全部门禁。
