# Change Impact Verification Governance v2

## 1. 状态与裁决边界

本文件描述 P4-01 至 P4-06 已落地的可执行 shadow 治理能力。

当前结论：

- 影响分析矩阵 13/13 通过。
- False Negative = 0。
- Evidence Reuse Error = 0。
- Obligation Coverage = 1.0。
- 非预期 Unknown Obligations = 0。
- `cutover_eligible=false`。

矩阵通过只证明 planner、graph、obligation、check selection、assertion closure
和 evidence reuse 负例满足设计契约。它不证明新 planner 已可接管现有必需门禁。
接管仍要求真实 old/new 双跑、独立审查和受保护合并。

本专题不修改：

- 产品 Schema、Decoder、Renderer、ORM、ACL 或业务状态。
- `config/ci/path_ownership_v1.json`。
- `config/acceptance/evolution_binding.v1.json`。
- 任何现有必需 CI 检查或门禁裁决。

公开审计生成物不得复制客户身份或品牌标识。盘点器在序列化边界把已登记身份 token
替换为稳定的 `customer-identity-<digest>`；测试同时验证所有生成分片和报告不再包含
原 token。该处理只影响公开审计物，不改变源仓库事实或验证责任。

## 2. 分层边界

| 层 | 证明责任 | 不证明 |
| --- | --- | --- |
| L1 Contract | Schema、Strict Decoder、Producer、Consumer、Action/View/Search Identity、关系规范化、兼容性 | 页面呈现、ORM 持久化、真实用户业务结果 |
| L2 Presentation | Renderer 选择、组件装配、布局、字段/列/顺序、响应式、键盘/焦点/ARIA、页面交互 | 后端事实正确、业务写入成功 |
| L3 Business | 状态转换、ORM 写入、ACL 正负例、审批执行、跨模型关系、事务、端到端业务结果 | 未观察到的页面呈现、部署可用性 |
| L4 Delivery | 类型、质量、安全、依赖、构建、范围、精确 HEAD、CI、审查 | 任何 L1/L2/L3 产品行为 |

L4 贯穿交付，但不是产品验证层。L1-L3 也不能互相替代。

### 2.1 后端与前端边界

- 纯后端 Contract Producer、Schema、Decoder 变化默认只要求 L1；ORM、ACL、状态和业务流程变化按语义追加 L3。
- 后端变化不因“可能影响页面”启动浏览器。
- 只有真实前端 runtime、Renderer、组件装配、布局、交互或明确页面兼容缺陷进入 L2。
- 前后端混合变更分别产生各层 obligation，取并集，不选择“主层”覆盖其他层。

## 3. Change Fact

Change Fact 记录实际变化的文件和可解析语义：

- TypeScript/Vue：Compiler API symbols、fields、imports、import bindings、assertion calls、dynamic import 线索。
- Python：AST model/class/method、ORM 调用、import bindings。
- XML：结构化 record/model/field/tag。
- JSON：结构化声明与菜单/action identity 线索，不按目录整体猜测。
- 测试：assertion calls 与真实 import 的 consumer，不因文件名相似直接认定覆盖。

每个 fact 包含：

- `id`
- `path`
- `change_kind`
- `semantic_kinds`
- `obligation_ids`
- `capabilities`
- `confidence`
- `basis`
- `unknown_reasons`
- `consumer_nodes.forward/reverse`
- `graph_resolution`

无法解析时必须输出 UNKNOWN。UNKNOWN 默认 BLOCK，不会自动成为 `NOT_APPLICABLE`。

plan 同时输出 L1/L2/L3 disposition：

- `required`：存在该层 obligation。
- `not_applicable`：无该层语义，且附确定性理由与反向触发条件。
- `blocked_unknown`：未知语义存在，禁止生成 N/A。

L4 不由 planner 宣告 N/A；它始终委托给现有 exact-head delivery gates。

## 4. Semantic Dependency Graph

图 schema：`change_impact.semantic_graph.v1`。

已支持的边：

| Edge | 来源 |
| --- | --- |
| `imports` | TypeScript Compiler local imports / Python AST imports |
| `asserts_consumer` | 测试真实 import 被测 consumer |
| `contract_producer_to_decoder` | 契约族 transport identity，标记 medium confidence |
| `renderer_registry_to_component` | semantic registry renderer 名称与 compiler import 的交集 |
| `component_to_page` | compiler reverse-import closure |
| `business_method_to_orm` | Python AST 方法实际调用 `create/write/unlink/copy` |

所有边包含 `source`、`target`、`kind`、`confidence`、`basis` 和 `reason`。

边界：

- Compiler/AST 本地边是高置信 observed fact。
- 跨语言契约族边是显式 static inference，不允许伪装成运行时证明。
- 动态组件、字符串路由、反射和无法解析的跨模型调用仍是 UNKNOWN。
- 文件级 import 图不是完整类型检查器；动态和运行态依赖仍需后续 probe 或真实执行。

## 5. Obligation 与 Check

Obligation 是语义验证单位，Make/Workflow 是执行单位。

每个 obligation 声明：

- 所属 L1/L2/L3/L4。
- 必需 assertion 集合。
- 相关 Change Fact source。
- 对应产品 capability。

Check 选择按 assertion 覆盖与相对成本做确定性集合覆盖。只覆盖相邻层的 check
不能替换目标行为断言。无 check 覆盖 assertion 时进入 BLOCK。

当前检查目录保持 shadow 性质，但入口均绑定真实仓库命令或 workflow，包括：

- `verify.unified_page_contract.v2`
- `verify.frontend.pr.unit`
- `verify.frontend.professional_component_registry.unit`
- `verify.frontend.presentation.browser`
- backend contract/ORM workflow
- migration compatibility ORM
- changed assertion execution
- CI workflow contract
- planner self-check
- docs links

## 6. 双向追踪

正向：

```text
ChangeFact
  -> Consumer nodes
  -> Obligation
  -> Assertion
  -> Check
  -> Evidence
```

反向：

```text
Evidence
  -> Assertions proved
  -> Obligations covered
  -> Capabilities affected
  -> Inputs that invalidate the evidence
```

反向 trace 为每个 check 计算局部 `invalidation_fingerprint`，只绑定相关输入、
assertion 和相邻图边。图任意位置变化不会无条件使全部证据失效。

## 7. 三身份与 Stable Baseline

三个身份必须分开：

| 身份 | 责任 |
| --- | --- |
| `main_head` | 当前集成目标 |
| `verified_baseline` | 最近一次满足完整 obligation 证明和 promotion 条件的稳定点 |
| `candidate_head/tree` | 当前候选 |

基线记录 schema：`change_impact_verification.baseline.v1`。

仅在以下条件同时成立时可推进：

1. 当前 receipt 精确匹配 planned input fingerprint。
2. assertion closure 为 true。
3. environment identity 完全一致。
4. evidence authority 合法且 evidence digest 存在。
5. 所有 required obligation 都有 proof。
6. `unknown=0`、`blocked=0`。
7. clean exact candidate。
8. 独立审查通过。
9. 当前 source/base 的必需远端检查通过。
10. 受保护合并后 main tree 与已证明候选树等价。

基线 digest 被篡改、promotion 不完整或树不等价时拒绝复用。

## 8. 高效增量迭代

协调器把当前 candidate delta 和 `inherited_unverified_delta` 分别展开语义义务：

```text
candidate =
  verified_baseline
  + inherited_unverified_delta
  + candidate_delta
```

规则：

- 被任一 delta 触及的 obligation 不得仅凭 baseline 复用。
- 未被 delta 触及且 baseline proof 完整的 obligation 可以 unit 级复用。
- 当前执行 receipt 必须匹配 input、assertion、tool、environment 和 evidence digest。
- 零产品 delta 时产品检查执行数为 0，只重验身份和 baseline 完整性。
- 同一 check + input + environment 只执行一次。
- 依赖安装、编译、服务和 fixture 按输入复用，不按 PR 次数重复。

协调器只输出 RUN/REUSE/BLOCK 和 readiness；它不执行检查，也不自行签发通过。

## 9. 验收矩阵

离线 shadow replay 覆盖：

| Case | 结果 |
| --- | --- |
| Decoder/Producer/Action-view contract | L1，无 browser |
| Renderer/component/page | L1 + L2 |
| CSS/responsive | L2，无 ORM/DB |
| ORM/business | L1 + L3，无 browser |
| ACL/Record Rules | L1 + L3 正负例 |
| Backend + frontend contract/presentation | L1 + L2 |
| Backend + frontend + business mixed | L1 + L2 + L3 |
| Dynamic consumer | UNKNOWN -> BLOCK |
| Field rename/delete | old/new identity -> L1 |
| Assertion/migration fixture | L1 + L3 + L4 |
| Docs only | L4 |
| Incorrect evidence reuse | BLOCK stale reuse |
| CI selector/evidence tooling | L4 only |

机器结果：

- `impact_analysis_acceptance_results.json`
- `impact_analysis_acceptance_matrix.json`

结果同时记录 current path router 的 observed targets 与 semantic check IDs。两者是不同
抽象，target identity 不要求相等；该并排观察用于定位覆盖差异，不构成本次 cutover proof。

矩阵结果不允许替代真实产品测试执行。它是验证体系自身的 conformance test。

## 10. Cutover 门槛

Cutover 必须同时满足：

- False Negative = 0。
- Evidence Reuse Error = 0。
- Obligation Coverage = 1.0。
- 非预期 Unknown = 0。
- False Positive 均有解释。
- old/new dual-run 未发现新 planner 漏掉旧系统实际覆盖的风险。
- 独立审查批准。
- 保留关闭新 planner 并恢复旧门禁的 rollback。

当前完成前四项的离线矩阵证明，但缺少经过批准的 required-gate dual-run 和独立审查，
因此 `cutover_eligible=false`。

## 11. 可执行入口

```text
make verify.change_impact.plan.unit
make verify.change_impact.acceptance
make verification.change-impact.plan \
  CHANGE_IMPACT_BASE=<full-sha> \
  CHANGE_IMPACT_OUTPUT=.runtime/change-impact/plan.json
```

直接生成完整图：

```text
python3 scripts/ops/change_impact_planner.py \
  --base <full-sha> \
  --head <full-sha> \
  --output .runtime/change-impact/plan.json \
  --graph-output .runtime/change-impact/graph.json
```

Stable baseline/evidence coordinator：

```text
python3 scripts/ops/change_impact_evidence.py validate --baseline baseline.json
python3 scripts/ops/change_impact_evidence.py build \
  --plan plan.json --receipts receipts.json ...
python3 scripts/ops/change_impact_evidence.py coordinate \
  --plan candidate-plan.json --baseline baseline.json \
  --inherited-plan inherited-plan.json --receipts current-receipts.json
```

## 12. 未解决问题

- 语义图仍以本地 import/AST 和明确契约族推断为主，不是运行时依赖追踪器。
- `business_method_to_orm` 能发现直接 ORM 调用，但反射、字符串调用和外部脚本闭包仍为 UNKNOWN。
- 当前未把每个 Make/Workflow 的全部 assertion adapter 自动反向登记；未登记项目不能获得 cutover credit。
- 当前没有接管必需门禁，也没有替换 `path_ownership_v1` 或 acceptance binding。
- required-gate dual-run、独立审查、真实候选 CI 和受保护合并完成前，不得宣称验证体系 cutover 完成。
