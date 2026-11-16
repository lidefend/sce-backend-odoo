# 验证体系全量盘点与边界

## 1. 身份与口径

- 源码 HEAD：`7169230580faaeae971695ac232c1d27173ad121`
- 源码 tree：`3eed77292d6a0a7be3d236a68830d61174a518b2`
- 类型：P4 只读审计，不执行产品门禁、不写数据库、不改变断言。
- 验证项：workflow job、四个 gate anchor 可达的 Make target、其实际执行的脚本、
  acceptance suite，以及 guard registry 中的完整脚本生命周期。
- “实际执行”来自 Make recipe、workflow step、脚本路径和资源关键词；名称本身不构成
  验证责任证明。没有稳定 docstring 的项目明确记为需要源码追踪。

### 1.1 证据等级

本报告明确区分：

- `observed_declaration`：workflow/Make/registry 中可直接读取的声明边。
- `declared_metadata`：脚本自身 docstring 或文件头声明的责任。
- `static_inference`：资源、层和调用关系的静态线索，不等于运行时证明。
- `manual_review`：P4-00 作者对 workflow job 责任的逐项人工归纳。
- `unknown`：当前盘点没有建立的调用、断言、服务或重复覆盖关系。

| 指标 | 值 |
| --- | ---: |
| 盘点条目总数 | 2411 |
| 已关联 obligation 的条目 | 0 |
| 已关联具体 assertion 的条目 | 0 |
| 已人工审阅语义的条目 | 23 |
| 重复覆盖分析为 UNKNOWN 的条目 | 2411 |

`responsibility_status_counts`：

- `manually_characterized_not_assertion_verified`：23
- `partially_characterized_not_assertion_verified`：1014
- `unknown`：1374

重要限制：P4-00 是调用面和责任边界盘点，不是完整 assertion-level 审计。除 workflow job 的人工
归纳外，脚本的“验证什么”主要来自文件自身声明；传递调用、真实服务依赖、具体断言和重复覆盖
仍为 UNKNOWN，必须在 P4-01/P4-02 中用 AST/compiler/依赖图和真实断言关联关闭。

## 2. 全量规模

| 指标 | 数量 |
| --- | ---: |
| 原 Make 解析器定义计数 | 2460 |
| 归一化后的真实 Make target | 2460 |
| 原解析器非 target 变量形状节点 | 0 |
| `.PHONY` target | 2332 |
| gate anchor | 4 |
| 原仪器 anchor 可达节点并集 | 246 |
| 归一化后的真实 target | 240 |
| 原仪器非 target 变量形状节点 | 6 |
| 非 anchor 可达 target | 2220 |
| 零引用 target | 670 |
| `scripts/**` 在盘脚本 | 2494 |
| guard registry 脚本 | 1605 |
| anchor 可达实际脚本项 | 543 |
| 全仓零引用脚本 | 104 |
| recipe 引用不存在资产的 target | 22 |

四个 gate anchor：

- `ci.local.quick.run`：155 个可达 target
- `ci.professional.backend.shard-verify`：102 个可达 target
- `verify.frontend.pr.unit`：53 个可达 target
- `verify.frontend.release.audit`：112 个可达 target

## 3. Lane 结构与实际覆盖面

| lane | 可达 target | 脚本 | 静态成本等级 |
| --- | ---: | ---: | --- |
| `local.iteration` | 12 | 17 | bounded |
| `local.quick` | 156 | 274 | very_high |
| `remote.professional.backend.verify` | 102 | 211 | very_high |
| `remote.professional.backend.tests` | 6 | 9 | high |
| `remote.professional.backend.reports` | 4 | 9 | high |
| `remote.standard_backend` | 5 | 9 | high |
| `remote.frontend.standard` | 53 | 32 | high |
| `remote.frontend.full` | 112 | 109 | very_high |
| `runtime.feedback.acceptance` | 8 | 2 | bounded |
| `deployment.postverify` | 4 | 0 | bounded |

同一 target 可以同时属于多个 lane。lane 数量是“实际调度面”，不是唯一测试数。
`local.quick` 与远端 professional lane 的交集可以复用同一脚本，但只有在输入、环境和
证据身份均等价时才能复用结果。

## 4. Workflow job 边界

| workflow | job | 它证明什么 | 推断层 |
| --- | --- | --- | --- |
| `.github/workflows/backend_test_suite.yml` | `backend_suite` | planned Odoo/Python module tests in isolated databases and records non-zero execution receipts | L1, L3, L4 |
| `.github/workflows/backend_test_suite.yml` | `plan` | backend module scope, reuse decision and frozen execution-plan identity | L4 |
| `.github/workflows/backend_test_suite.yml` | `verify_coverage` | planned module identities equal executed plus independently authorized reused test evidence | L4 |
| `.github/workflows/demo-ci.yml` | `demo_ci` | manual disposable demo scenario setup, frontend build identity and scenario command | L3, L4 |
| `.github/workflows/frontend_release_evidence_bundle.yml` | `frontend_release_evidence_bundle` | a current-main frontend artifact and its exact check/run/artifact/branch-protection provenance | L4 |
| `.github/workflows/frontend_release_gate.yml` | `frontend_release_gate` | frontend lint, strict types, unit tests, build, release browser suite and exact-head release evidence in full mode | L1, L2, L4 |
| `.github/workflows/frontend_release_gate.yml` | `managed_orm` | selected managed Odoo ORM regressions in an isolated frontend acceptance runtime | L1, L3, L4 |
| `.github/workflows/infra-stage-gate.yml` | `infra_stage_gate` | manually dispatched legacy Compose startup, stage gates, E2E contract/scene and navigation audits | L1, L3 |
| `.github/workflows/merge_policy_gate.yml` | `classify` | selects and publishes the merge-policy lane from the candidate change set | L4 |
| `.github/workflows/merge_policy_gate.yml` | `fast` | cheap governance, security and release-version integrity for the FAST lane | L4 |
| `.github/workflows/merge_policy_gate.yml` | `merge_policy_gate` | exact-head completion of the declared fact workflows and final merge-policy aggregation | L4 |
| `.github/workflows/merge_policy_gate.yml` | `wait_for_fact_checks` | exact-head completion of public_guard, professional_quality_gate and frontend_release_gate | L4 |
| `.github/workflows/professional_quality_gate.yml` | `backend_impact_suite` | the reusable backend suite selected from exact base/head trees | L1, L3, L4 |
| `.github/workflows/professional_quality_gate.yml` | `professional_authorization` | repository/actor authorization, risk classification and backend impact planning | L4 |
| `.github/workflows/professional_quality_gate.yml` | `professional_quality_checks` | mode-selected static, contract, backend, generated-report and governance checks | L1, L3, L4 |
| `.github/workflows/professional_quality_gate.yml` | `professional_quality_gate` | all required professional jobs ran and their selected outcomes agree with the impact plan | L4 |
| `.github/workflows/professional_quality_gate.yml` | `python310_runtime_compatibility` | selected release tools compile and preserve negative guards on Python 3.10 | L4 |
| `.github/workflows/public_guard.yml` | `classify` | selects the public-guard lane from the candidate change set | L4 |
| `.github/workflows/public_guard.yml` | `public_guard` | repository history hygiene, workflow security policy, protected guard tests and clean product boundary | L4 |
| `.github/workflows/release_candidate_gate.yml` | `classify` | identity of the explicit release-candidate head | L4 |
| `.github/workflows/release_candidate_gate.yml` | `release_candidate_gate` | exact-head merge eligibility and explicit candidate workflow completion | L4 |
| `.github/workflows/release_candidate_gate.yml` | `wait_for_candidate_checks` | exact-head completion of all merge and candidate workflows | L4 |
| `.github/workflows/sc_smoke.yml` | `smoke` | manual disposable-container sc_smoke backend test; the data validator is non-blocking | L3 |

workflow 的 final gate job 通常只聚合子 job，不自行执行产品断言。父 workflow 成功不能扩张
子 job 的证明边界；skip、required=false、non-blocking step 也不能被写成产品 PASS。

## 5. 产品验证层

### L1 Contract Verification

只证明 Schema、Strict Decoder、Producer/Consumer、Action/View/Search Identity、关系字段规范化
和契约兼容性。静态 schema guard 能证明声明/结构约束，不能单独证明真实前端已经消费该契约，
也不能证明业务状态正确。

### L2 Presentation Verification

只证明真实 Renderer 选择、组件装配、布局/视觉、字段列顺序、响应式、键盘/焦点/ARIA 和页面
交互。浏览器出现、页面可打开或选择器命中不等于契约正确；浏览器签名也不能替代 L1。

### L3 Business Acceptance

只证明业务状态转换、ORM 写入/持久化、权限正负例、审批执行、跨模型关系、事务并发和端到端
业务结果。后端单元测试若不是通过真实 Odoo runtime/数据库执行，不能声称持久化或 ACL 证明。

### L4 Delivery Governance

只证明代码质量、安全、类型、依赖、构建、变更范围、精确 HEAD、CI 与合并前审查。L4 可以阻断
交付，但不能替代 L1/L2/L3 的产品行为证明。

## 6. 当前触发与分类事实

### 6.1 风险分类和验收绑定的代表路径

| 路径 | risk lane | acceptance rule | 验收 suites |
| --- | --- | --- | --- |
| `frontend/apps/web/src/app/contracts/v2/schema.ts` | `STANDARD` | `frontend-contract-v2-codec` | frontend_contract |
| `frontend/apps/web/src/app/contracts/v2/legacyLayoutNormalizer.ts` | `STANDARD` | `frontend-contract-v2-codec` | frontend_contract |
| `frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts` | `STANDARD` | `frontend-runtime` | frontend_contract |
| `frontend/apps/web/src/app/presentation/contractFormPresenter.ts` | `STANDARD` | `frontend-contract-form-consumer` | frontend_contract, frontend_presentation |
| `frontend/apps/web/src/pages/contractForm/ContractForm.vue` | `STANDARD` | `frontend-contract-form-consumer` | frontend_contract, frontend_presentation |
| `frontend/apps/web/src/pages/listPage/ListPage.vue` | `STANDARD` | `frontend-list-surface-consumer` | frontend_contract, list_surface_structure |
| `frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue` | `STANDARD` | `frontend-presentation` | frontend_contract, frontend_presentation |
| `frontend/apps/web/src/app/runtime/businessListQueryRuntime.ts` | `STANDARD` | `frontend-list-surface-consumer` | frontend_contract, list_surface_structure |
| `addons/smart_core/contracts/schema.py` | `STANDARD` | `smart-core-runtime` | backend_contract, daily_runtime_entry |
| `addons/smart_construction_core/models/project.py` | `STANDARD` | `construction-product-runtime` | backend_contract |
| `addons/smart_construction_core/data/approval_policy_seed.xml` | `STANDARD` | `approval-policy-initialization` | backend_contract |
| `scripts/verify/frontend_page_contract_boundary_guard.py` | `STANDARD` | `governance-static` | governance_static |
| `docs/audit/change-impact-verification/README.md` | `FAST` | `docs-bookkeeping` | none |

当前已确认两个方向的结构性问题：

1. `frontend/apps/web/src/app/contracts/v2/**` 被 `frontend-contract-form-consumer` 同时归入
   `frontend_contract` 和带真实浏览器证据的 `frontend_presentation`，因此契约/Decoder 修改会
   要求页面验收。
2. `professionalComponentRegistry.ts` 当前只命中通用 `frontend-runtime -> frontend_contract`，
   没有自动进入 presentation evidence；Renderer 注册变化可能只得到通用前端验证，无法证明
   受影响页面实际呈现了变化。

这两项是“路径分类不能代表实际能力影响”的直接证据，不是对整个 PR 的唯一标签结论。

### 6.2 混合变更

分类必须按文件和符号取并集。一个候选同时修改 Search Contract、搜索栏组件和业务 Domain 时，
L1、L2、L3 风险同时存在，不能因为主要路径属于一类而降级其他层。未知路径必须保守处理。

## 7. Acceptance Evolution 边界

| suite | 描述 | stage | evidence |
| --- | --- | --- | --- |
| `backend_contract` | 后端契约、单测与影响面套件 | merge, deployment | no evidence adapter |
| `frontend_contract` | 前端组件、契约消费与发布单测 | merge, deployment | no evidence adapter |
| `frontend_presentation` | 纯呈现组件的轻量页面证据：页面身份、契约消费、零写入、零运行错误与响应式无溢出 | merge, deployment | presentation_header |
| `governance_static` | 静态守卫、结构锁与治理清单 | merge, deployment | no evidence adapter |
| `daily_runtime_entry` | 日常入口、双实例分流、发布身份与 Odoo 运行态验收 | deployment | entry_verify |
| `path_namespace_identity` | 路径命名空间身份、跨域重放、退出与公司边界 | deployment | path_ns_c |
| `list_surface_structure` | 列表页结构、几何与运行时错误浏览器验收 | merge, deployment | list_surface |
| `relation_roundtrip` | 关系字段回环、入口与操作恢复浏览器验收 | merge, deployment | relation_roundtrip |

`acceptance_evolution` 只决定路径需要哪些 suite 和证据 adapter；实际命令仍由 suite
entrypoint 执行。`validation_delivery_plan` 是只读计划/证据诊断，不是执行器、不是通过回执，
也不替代远端 required CI。

## 8. 证据生命周期

| 权威 | 绑定什么 | 允许复用的最小条件 | 不能证明什么 |
| --- | --- | --- | --- |
| `agent_run_context` | run、check、声明输入哈希、原始日志哈希、source head、环境 | 所有声明输入、上游输入、环境和日志未变；offline 或带权威 readback 的 runtime check | 未声明依赖、当前远端 CI、产品行为越出断言 |
| `acceptance_evolution` | suite descriptor、匹配输入及 Make target/variable 指纹、exact head evidence | suite 输入指纹与当前 revision 相同，adapter 验证 record 绑定当前 head | suite 未覆盖的页面、角色或业务结果 |
| `evidence_scope` | 每个声明 unit 的 fingerprint 和 runtime identity | unit fingerprint、identity 和成功状态均未变 | 未声明 unit，或由部署版本号本身推断行为 |
| `local_quick_receipt` | clean exact head/tree、target coverage、scan coverage | 精确 head；或 bookkeeping-only 祖先且 runtime tree digest 与扫描权威不变 | 未在 Quick 内的远端检查、数据库升级或浏览器旅程 |
| `backend_test_receipt` | source/context、执行定义、readback、依赖闭包、平台认证 | 只有独立认证的隔离执行或六维闭合可授权 REUSE | 生产者自报 `reuse_ready=true`；缺失契约/事实 readback 的 ORM |
| `frontend_release_evidence_bundle` | 当前 main artifact、check/run/artifact/ruleset 与 tree | bundle 校验当前 SHA/tree 且来源 run/artifact 可核验 | 新候选、部署或用户验收 |

统一规则：

- HEAD 是来源身份，不自动是复用有效性键。
- 输入、断言、工具、依赖或环境变化使相关证据失效。
- 文档变化不自动使页面行为证据失效；运行时/chrome/artifact 变化必须触发对应失效。
- `PASS`、`skip`、`not_run`、`unknown` 必须分开；零测试不是 PASS。
- 历史证据只有在独立复用权威验证后才可引用，不能复制成当前执行回执。

## 9. 执行依赖与成本边界

| 资源类 | anchor target 数 |
| --- | ---: |
| `browser` | 24 |
| `container` | 27 |
| `database_or_orm` | 48 |
| `frontend_toolchain` | 56 |
| `network` | 2 |
| `static_or_unknown` | 83 |

仓库当前 lane telemetry 没有实际运行记录，所以本基线不编造 target 耗时。可引用的实测历史区间
仅限 `docs/ops/ci_feedback_latency_v1.md`：

- `public_guard`：4–5 分钟
- `professional_quality_gate`：9–14 分钟
- `frontend_release_gate`：10–16 分钟
- `merge_policy_gate` 关键路径：14–16 分钟

高成本来源主要是：扫描权威变化导致的 trusted full scan、ORM 容器/新库/fixture、Playwright
安装与完整页面矩阵、以及同一脚本在 local/remote lanes 的重复调度。

## 10. 不得自动放行的边界

以下情况必须 BLOCK 或 RUN，不能靠路径/历史 PASS 放行：

- 路径未分类、unknown、rename/delete 只取单端。
- 修改了执行器、选择器、断言、fixture、schema、生成器、锁文件或 Make/workflow 权威，相关回执未失效。
- suite/evidence adapter 没有 required checks，或 required check 缺失/失败/未知。
- ORM receipt 缺平台来源、执行定义、动态契约、事实范围、目标依赖或关联权限闭包。
- 浏览器页面只是 HTTP 200、元素出现或控制台无错，却没有对应 Renderer/交互/业务结果断言。
- CI 绿但目标变更集只经过路径规则；没有实际执行受影响的 L1/L2/L3 断言。
- 结构扫描、生成报告一致、类型检查或构建通过，被描述成页面或业务验收完成。

## 11. 长尾与不可执行面

guard registry 生命周期统计：

- `file_reference_only`：169
- `gate_enforced`：247
- `manual_or_non_gate_dispatch`：1097
- `orphan`：92

- `manual_or_non_gate_dispatch`、`file_reference_only`、`orphan`、`unwired` 不是 merge gate。
- 零引用 target、零引用脚本和 missing-asset target 只能说明“当前没有自动执行路径”，不能说明
  验证已覆盖或产品已通过。
- target/script 共享同一执行文件只登记为 `shared_*_candidates`；实际断言是否重复为 UNKNOWN。
- 本轮没有删除、接线、豁免或退役任何长尾项；P4-00 只建立边界和基线。

## 12. Gate-enforced 脚本责任索引

下表只列四个 anchor 可达、实际被执行脚本中的一部分元数据。完整八问责任、调用 target、
资源信号、层提示和重叠关系由 `verification_mapping_matrix.json` 索引到四个 part 文件。

| script | lifecycle | inferred layers | declared summary |
| --- | --- | --- | --- |
| `scripts/verify/acceptance_evolution_binding_guard.py` | gate_enforced | L1, L2, L3, L4 | Bind the acceptance surface to every code change. A change is only "covered" when the paths it touches are declared in the acceptance evolution registry and the acceptance suites t |
| `scripts/verify/action_view_responsibility_map_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/auth_credential_frontend_guard.py` | gate_enforced | L2, L4 | no docstring |
| `scripts/verify/backend_contract_lifecycle_authority_guard.py` | gate_enforced | L1, L4 | no docstring |
| `scripts/verify/backend_model_field_declaration_guard.py` | gate_enforced | L3, L4 | Fail closed on any field declared by more than one class block. One field fact has exactly one declaration site. A second class that re-declares the same field does not override th |
| `scripts/verify/backend_model_field_declarations.py` | gate_enforced | L3, L4 | Canonical scanner for backend model field declarations. Odoo merges same-name field definitions from every class block on a model attribute by attribute. Two declarations are there |
| `scripts/verify/baseline_iteration_execution_policy_guard.py` | gate_enforced | L1, L2, L3, L4 | Lock the repository's baseline-backed iteration execution policy. |
| `scripts/verify/branch_governance_consistency_guard.py` | gate_enforced | L3, L4 | Fail when documented and executable write-branch policy diverges. |
| `scripts/verify/collection_capability_rights_projection_test.py` | gate_enforced | L3, L4 | Falsifiable, container-free assertions for the collection-capability rule. The list surface publishes one declared action list; ``import`` may only appear there when the caller's * |
| `scripts/verify/collection_view_semantics_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/construction_core_extension_actor_roles_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_capability_rows_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_contract_helpers_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_contract_normalizers_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_hook_facts_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_intent_handlers_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_policy_accessors_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_policy_maps_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_project_layout_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_relation_entry_policy_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_responsibility_map_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_service_builders_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/construction_core_extension_system_init_rows_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/contract_form_action_plan_builder_guard.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/contract_form_behavior_regression_runbook_guard.py` | gate_enforced | L1, L2, L4 | no docstring |
| `scripts/verify/contract_form_onchange_normalization_guard.py` | gate_enforced | L1, L4 | no docstring |
| `scripts/verify/contract_form_runtime_state_behavior_guard.sh` | gate_enforced | unknown | no docstring |
| `scripts/verify/contract_form_runtime_state_protocol_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/contract_form_save_payload_builder_guard.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/contract_form_side_effect_regression_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_access_policy_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/contract_governance_canonicalization_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/contract_governance_capabilities_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/contract_governance_contract_detection_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_create_profile_split_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_domain_overrides_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/contract_governance_enterprise_forms_split_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_field_semantics_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_form_actions_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/contract_governance_form_fields_split_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_form_layout_split_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_form_render_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_form_validation_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/contract_governance_labels_split_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_list_surface_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_native_bridge_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/contract_governance_project_form_split_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_registry_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/contract_governance_responsibility_map_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_scenes_split_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/contract_governance_surface_mapping_split_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/contract_governance_user_surface_split_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/contract_schema_declaration_sync.py` | gate_enforced | L1, L4 | Derive the producer's Contract V2 schema declaration from the schema authority. The sealed contract publishes ``schemaId``/``schemaVersion``/``schemaSha256``/ ``normativeStatus`` i |
| `scripts/verify/contract_v2_entry_equivalence_guard.py` | gate_enforced | L1, L2, L3, L4 | The action entry and the model entry must project the same business facts. `ui.contract.v2` is addressed two ways, and both are real product paths: * ``loadActionContractV2(actionI |
| `scripts/verify/data_space_provisioning_guard.py` | gate_enforced | L1, L3, L4 | Fail-closed structure check for business data-space onboarding. One question only: can this repository onboard a business company before any industry/demo initialization writes bus |
| `scripts/verify/database_strategy_guard.py` | gate_enforced | L3 | Fail-closed guard for the declarative platform/industry initialization strategy. Owns one question only: is the database strategy of each environment role declared, known, and poli |
| `scripts/verify/determinism_probe.py` | gate_enforced | unknown | Determinism probe: same command, same output, or the baseline is not real. The precondition for any reproducible baseline is "same input -> same output". This probe runs one govern |
| `scripts/verify/fact_layer_authority_guard.py` | gate_enforced | L3 | Fact-layer authority guard (ARCH-DECISION-010). Facts (model/view/permission/groups) are the only maintained layer. Mechanisms (role_surface, scenario projection, frontend) must on |
| `scripts/verify/fact_source_coverage_guard.py` | gate_enforced | L1, L3, L4 | Fail-closed check that the money fact of every product model has one source. The company ceiling guard owns the question "which rows may this caller read". This guard owns the adja |
| `scripts/verify/file_line_budget_uniform_guard.py` | gate_enforced | L4 | Keep file line budgets in one place, and keep them advisory. Two regressions this guard exists to stop: 1. A guard freezing its own numeric line budget again. That is how one file  |
| `scripts/verify/formal_product_field_purity_guard.py` | gate_enforced | L4 | Fail closed when customer migration aliases enter the standard product. |
| `scripts/verify/frontend_acceptance_login_probe.py` | gate_enforced | L1 | Fail-fast, secret-safe HTTP login probe for the governed acceptance route. |
| `scripts/verify/frontend_action_view_page_actions_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_auth_surface_guard.py` | gate_enforced | L1, L2 | no docstring |
| `scripts/verify/frontend_boq_import_preview_guard.py` | gate_enforced | L2, L3 | G3.2 BOQ 导入预检快照只读投影前端守卫。 校验三件套（API 封装 / presentation Model / 只读面板组件）与单测的 契约准入标记： - API 封装必须走专用 intent（project.boq.import.preview.fetch）， 不得绕过 intent 直接调用通用 data 通道； - Model 必须实现四态视 |
| `scripts/verify/frontend_chart_engine_guard.py` | gate_enforced | L1, L2 | ADR-002 图表引擎引入纪律守卫（G6.1）。 钉死三件事： 1. 精确锁版：frontend/apps/web 生产依赖 echarts 必须是精确版本（无 ^/~ 前缀）， 与已批准版本 6.1.0 一致；patch 升级须过门禁（改版本即改本守卫基线）。 2. tree-shakeable 引入：禁止 `from 'echarts'` 全量引入；只 |
| `scripts/verify/frontend_contract_consumer_intrusion_guard.py` | gate_enforced | L1, L3 | no docstring |
| `scripts/verify/frontend_contract_prompt_action_presentation_guard.py` | gate_enforced | L1, L2 | no docstring |
| `scripts/verify/frontend_dashboard_state_guard.py` | gate_enforced | L2 | no docstring |
| `scripts/verify/frontend_decision_authority.py` | gate_enforced | L1, L2, L3, L4 | Single authority for the frontend decision-authority ledger. Why this module exists ---------------------- The product goal is: "a customised frontend derives everything except ren |
| `scripts/verify/frontend_decision_authority_guard.py` | gate_enforced | L1, L2, L3, L4 | Fail-closed guard for the frontend decision-authority ledger. The guard answers one decidable question: *does every frontend decision inside the declared scopes either come from th |
| `scripts/verify/frontend_dev_incremental.py` | gate_enforced | L1, L2, L3, L4 | Run the smallest registered frontend checks affected by live source changes. This is a development feedback tool. It deliberately never builds a candidate, captures browser evidenc |
| `scripts/verify/frontend_dev_process_isolation_guard.py` | gate_enforced | L1 | no docstring |
| `scripts/verify/frontend_form_header_action_primitives_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/frontend_low_code_field_create_dialog_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_mobile_viewport_guard.py` | gate_enforced | L1, L2 | Mobile viewport contract guard (G4 incremental closure). R-G4-01: the SPA declares `env(safe-area-inset-*)` paddings in shell and form pages. Without `viewport-fit=cover` in the vi |
| `scripts/verify/frontend_navigation_shell_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_official_icon_resource_guard.py` | gate_enforced | L1, L2 | Fail closed when product UI bypasses the official icon adapter. |
| `scripts/verify/frontend_page_contract_boundary_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_page_contract_orchestration_consumption_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_primitive_adapter_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_primitive_port_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_product_page_header_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_product_page_pattern_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_professional_audit_guard.py` | gate_enforced | L1, L3 | no docstring |
| `scripts/verify/frontend_professional_base_field_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_professional_business_value_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_professional_collaboration_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_professional_component_registry_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_professional_detail_collection_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_professional_relation_field_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_professional_relation_lifecycle_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_professional_workflow_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_relational_action_primitives_guard.py` | gate_enforced | L2, L3 | no docstring |
| `scripts/verify/frontend_release_audit.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_release_ci_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/frontend_scene_component_bridge_guard.py` | gate_enforced | L1, L2, L3, L4 | Static architecture guard for the production scene-component bridge. |
| `scripts/verify/frontend_scene_primitive_adapter_guard.py` | gate_enforced | L1, L2, L4 | no docstring |
| `scripts/verify/frontend_shared_surface_semantic_boundary_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/frontend_state_presentation_guard.py` | gate_enforced | L1, L2 | no docstring |
| `scripts/verify/frontend_static_release_audit.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/frontend_v2_policy_projection_guard.py` | gate_enforced | L1, L2, L3, L4 | Guard frontend consumers prefer formal V2 policy projections. |
| `scripts/verify/g1_acceptance_baseline_guard.py` | gate_enforced | L1, L2, L3, L4 | G1 acceptance baseline guard. Validates the environment-independent acceptance baseline evidence for the custom-frontend-integration program (docs/planning/custom-frontend-integrat |
| `scripts/verify/github_actions_security_guard.py` | gate_enforced | L1, L2, L3, L4 | Enforce the public/professional GitHub Actions trust boundary. |
| `scripts/verify/guard_registry_audit.py` | gate_enforced | L3, L4 | Guard registry: inventory, audit and retirement for scripts/verify/. R7 (productization audit) deliverable. The verify-script corpus grew to 1200+ files across generations of guard |
| `scripts/verify/intent_cases_integrity_guard.py` | gate_enforced | L1 | no docstring |
| `scripts/verify/js_contract_consumer_markers.py` | gate_enforced | L1, L3 | Strict lexical recognizers shared by JavaScript contract-consumer guards. |
| `scripts/verify/layout_vocabulary_lint.py` | gate_enforced | L1, L2, L4 | Fail-closed lint for the delivered form-structure vocabulary. Contract Runtime boundary fix (FE-CONTRACT-RUNTIME-01): the delivered contract used to publish one ``layoutPolicy`` st |
| `scripts/verify/list_field_semantic_integrity_guard.py` | gate_enforced | L1, L3 | no docstring |
| `scripts/verify/list_preference_single_application_guard.py` | gate_enforced | L1, L3, L4 | Single-application lock for the list preference contract. The product contract is declared by the server and applied exactly once, by the frontend consumer, against the declared `` |
| `scripts/verify/list_surface_evidence_binding_guard.py` | gate_enforced | L1, L3, L4 | Fail when a list-surface claim is bound to evidence that does not support it. The page-pattern ledgers bind a conclusion to a concrete observation, e.g. ``... gates 108/108 list-su |
| `scripts/verify/local_dev_runtime_contract_role_matrix_probe.py` | gate_enforced | L1, L2, L3, L4 | Bounded role-dimension contract observation (P4 diagnostic). The product contract is not one fixed object: the same ``ui.contract.v2`` request produces a different contract identit |
| `scripts/verify/local_dev_runtime_performance.py` | gate_enforced | L1, L2, L3, L4 | Bounded backend observation, not browser/SLO or production acceptance. Only the registered local demo finance principal, up to two already assigned companies, one process-first obs |
| `scripts/verify/local_dev_runtime_permission_probe.py` | gate_enforced | L1, L3, L4 | Bounded permission-gate attribution probe for R4 (P4 diagnostic). The controller ``permission`` segment for the process-first ``ui.contract.v2`` list request was observed at ~215 m |
| `scripts/verify/local_dev_runtime_projection_cache_identity_probe.py` | gate_enforced | L1, L3 | Read-only runtime probe for assembled-cache identity invalidation (P0/P4). The record-free assembled hit returns after re-sealing; it does not re-run the entitlement, policy, actio |
| `scripts/verify/local_dev_runtime_record_form_probe.py` | gate_enforced | L1, L3, L4 | Uninstrumented read-only probe for record-bound form requests (P4 diagnostic). The role-matrix and contract-request probes intentionally instrument SQL, ``copy.deepcopy`` and GC to |
| `scripts/verify/login_envelope_consumption_guard.py` | gate_enforced | L1, L4 | Fail-closed guard for login-envelope token consumers under ``scripts/``. Declared shape (addons/smart_core/handlers/login.py): the login intent publishes the bearer token at ``data |
| `scripts/verify/menu_config_tree_editor_behavior_guard.sh` | gate_enforced | unknown | no docstring |
| `scripts/verify/narrow_importer_group_guard.py` | gate_enforced | L4 | Static fail-closed guard for the signed tenant-payload importer group. |
| `scripts/verify/native_view_workflow_action_coverage_guard.py` | gate_enforced | L1, L3, L4 | Every native object button on a workflow-adopted model is accounted for. The workflow contract publishes a subset of the native form actions. Anything the contract does not publish |
| `scripts/verify/page_contract_v1_zero_residue_guard.py` | gate_enforced | L1, L4 | no docstring |
| `scripts/verify/platform_database_governance_guard.py` | gate_enforced | L3, L4 | Fail-closed guard for the platform database governance product capability. Owns one question only: is the database governance declaration still the single source, and does the plat |
| `scripts/verify/playwright_vendor_coupling_guard.py` | gate_enforced | L1, L2, L3 | Hardening guard: keep the browser test/probe layer off vendor-internal DOM. The adopted official template is consumed through its documented public surface (roles, semantic markers |
| `scripts/verify/product_client_action_boundary_guard.py` | gate_enforced | L1, L2 | Keep Odoo client actions outside the contract-driven product runtime. |
| `scripts/verify/product_image_tenant_neutral_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/product_release_version_guard.py` | gate_enforced | L1, L2, L4 | no docstring |
| `scripts/verify/product_to_customer_dependency_guard.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/production_blocker_image.sh` | gate_enforced | L1, L4 | no docstring |
| `scripts/verify/production_blocker_runtime_assets.sh` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/repository_clean_history_guard.py` | gate_enforced | L1, L3, L4 | Fail closed on forbidden reachable Git history and release-local objects. Diagnostics intentionally contain only rule IDs, paths, object prefixes and classifications. Blob contents |
| `scripts/verify/role_surface_exposure_declaration_guard.py` | gate_enforced | L1, L3, L4 | Lock the declared divergence between menu-layer capability reachability and the published navigation surface. ``ROLE_SURFACE_OVERRIDES`` (and the frontend navigation manifest) deci |
| `scripts/verify/sc_data_scope_ceiling_generate.py` | gate_enforced | L2, L3, L4 | Generate the global company-scope ceilings from the data-scope declaration. scripts/verify/data_scope_declarations.json is the single source: an ``enforced`` entry contributes its  |
| `scripts/verify/sc_data_scope_rule_coverage_guard.py` | gate_enforced | L1, L3, L4 | Fail-closed check that every product-owned company model is accounted for. The registered 744-model registry is inspection scope, not a rewrite list. This guard reads source only ( |
| `scripts/verify/scenario_center_projection_guard.py` | gate_enforced | L3 | Pure guard for the scenario-center navigation projection. Exercises ``project_authorized_nav_with_env`` against a fake Odoo environment: centers come from scenario-entry compositio |
| `scripts/verify/scenario_surface_projection_guard.py` | gate_enforced | L1, L3 | Static guard for the scenario product surface projection. Pure Python (no Odoo). Loads the P1 scenario surface contract and the released 92 menu identities from product_menu_source |
| `scripts/verify/static_suite_frontend_toolchain_guard.py` | gate_enforced | L1, L4 | The remote required backend gate must not need the frontend toolchain. ``verify.contract.architecture.suite`` is a prerequisite of ``ci.professional.backend.shard-verify``, which ` |
| `scripts/verify/system_performance_baseline.py` | gate_enforced | L1, L2, L3, L4 | Normalize already-produced managed performance probes into one system baseline record. P4 owns load declaration, collection, comparison and the delivery gate (``docs/ops/runtime_pe |
| `scripts/verify/tenant_data_responsibility_boundary.py` | gate_enforced | L4 | Verify that release module sets do not contain demo, fixture, or unresolved data. |
| `scripts/verify/tenant_delivery_protocol_guard.py` | gate_enforced | L1 | no docstring |
| `scripts/verify/tenant_extension_storage_guard.py` | gate_enforced | L1, L3, L4 | Fail closed when tenant extensions mutate the public product schema. |
| `scripts/verify/tenant_legacy_xmlid_boundary.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/tenant_module_set_matrix.py` | gate_enforced | L4 | Fail closed when tenant module sets overlap or import another data layer. |
| `scripts/verify/tenant_p04_p0_debt_guard.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/tenant_product_fresh_install.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/tenant_product_legacy_boundary.py` | gate_enforced | unknown | Fail closed when customer history implementation leaks into product runtime. |
| `scripts/verify/tenant_product_payload_boundary_guard.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_acceptance_evolution_binding_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_backend_model_field_declaration_guard.py` | gate_enforced | L3 | no docstring |
| `scripts/verify/test_baseline_iteration_execution_policy_guard.py` | gate_enforced | L1, L4 | no docstring |
| `scripts/verify/test_branch_governance_consistency_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/test_common_env_explicit_path.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/test_contract_gate_case_normalisation.py` | gate_enforced | L1, L3 | Unit lock on the contract gate's declared per-case volatile response keys. The gate compares a regenerated snapshot against the tracked reference. A case whose response carries a v |
| `scripts/verify/test_contract_v2_entry_equivalence_guard.py` | gate_enforced | L1, L3 | Falsification test for the contract-v2 entry-equivalence guard. The guard reads shipped carriers (a TypeScript contract client, the backend entry branch, the permission resolver an |
| `scripts/verify/test_controlled_main_cutover.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_coverage_registry_audit.py` | gate_enforced | L3, L4 | Test coverage registry: bind declared Odoo test groups to a governed entry. Why this exists (2026-10-10 nightly triage): the repository declared a large number of Odoo test groups  |
| `scripts/verify/test_daily_acceptance_fixture_lane.py` | gate_enforced | L1, L3, L4 | Locks the daily development acceptance fixture lane. The daily runtime is a separate declared profile from the isolated acceptance database, so the fixture scope must be declared,  |
| `scripts/verify/test_data_space_provisioning.py` | gate_enforced | L3, L4 | Pure decision tests for the governed business data-space onboarding module. The module under test imports nothing from odoo, so these tests drive it with a plain mapping. Real ORM  |
| `scripts/verify/test_database_strategy_guard.py` | gate_enforced | L3 | Unit tests for the declarative database-strategy guard (pure file checks). |
| `scripts/verify/test_external_customer_addons_runtime_boundary.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/test_fact_source_coverage_guard.py` | gate_enforced | L1, L3 | Negative controls for the money-fact source guard. |
| `scripts/verify/test_formal_product_field_purity_guard.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_frontend_acceptance_login_probe.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/test_frontend_action_view_page_actions_guard.py` | gate_enforced | L1, L3 | no docstring |
| `scripts/verify/test_frontend_boq_import_preview_guard.py` | gate_enforced | L2 | no docstring |
| `scripts/verify/test_frontend_contract_prompt_action_presentation_guard.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/test_frontend_dashboard_state_guard.py` | gate_enforced | L2 | no docstring |
| `scripts/verify/test_frontend_decision_authority_guard.py` | gate_enforced | L1, L2, L4 | no docstring |
| `scripts/verify/test_frontend_delivery_hardening_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_dev_incremental.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_form_header_action_primitives_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_low_code_field_create_dialog_guard.py` | gate_enforced | L1 | no docstring |
| `scripts/verify/test_frontend_mobile_viewport_guard.py` | gate_enforced | L2 | no docstring |
| `scripts/verify/test_frontend_navigation_shell_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/test_frontend_product_page_header_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_product_page_pattern_guard.py` | gate_enforced | L2, L3 | no docstring |
| `scripts/verify/test_frontend_professional_audit_guard.py` | gate_enforced | L3 | no docstring |
| `scripts/verify/test_frontend_professional_base_field_guard.py` | gate_enforced | L2, L3 | no docstring |
| `scripts/verify/test_frontend_professional_business_value_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/test_frontend_professional_collaboration_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/test_frontend_professional_component_registry_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_professional_detail_collection_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/test_frontend_professional_relation_field_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_professional_relation_lifecycle_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_professional_workflow_guard.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_relational_action_primitives_guard.py` | gate_enforced | L2, L3 | no docstring |
| `scripts/verify/test_frontend_release_audit.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_release_ci_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_release_evidence_bundle.py` | gate_enforced | L1, L2, L4 | no docstring |
| `scripts/verify/test_frontend_release_gate.py` | gate_enforced | L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_release_local_entry.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_frontend_state_presentation_guard.py` | gate_enforced | L1, L2, L3 | no docstring |
| `scripts/verify/test_g1_acceptance_baseline_guard.py` | gate_enforced | L1, L4 | Unit tests for g1_acceptance_baseline_guard (function-level, hermetic). The guard's main() reads repository-relative paths; these tests exercise the validation functions against sy |
| `scripts/verify/test_gitee_to_github_mirror.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_gitee_webhook_ci.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_github_actions_security_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/test_group_assignment.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_guard_registry_audit.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_js_contract_consumer_markers.py` | gate_enforced | L1 | Regression tests for shared JavaScript contract-consumer markers. |
| `scripts/verify/test_layout_vocabulary_lint.py` | gate_enforced | L1, L2, L3, L4 | Focused tests for the delivered form-structure vocabulary lint. Positive case: the real repository payload surface must be self-consistent. Negative cases: every assertion below mu |
| `scripts/verify/test_local_dev_runtime_performance.py` | gate_enforced | L1, L3, L4 | Execute the diagnostic script against a fake environment; no database needed. |
| `scripts/verify/test_local_dev_runtime_permission_probe.py` | gate_enforced | L1, L3 | Governed guard for the R4 permission-attribution probe; no database needed. The probe is a P4 read-only diagnostic that runs the real permission gate with a request shim. These tes |
| `scripts/verify/test_local_dev_runtime_record_form_probe.py` | gate_enforced | L1, L3 | Non-zero tests for the record-form probe's metric and semantic helpers. The probe runs inside ``odoo shell``; these tests import only its pure helpers, so no runtime, database or n |
| `scripts/verify/test_local_quick_evidence.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/test_menu_metadata_batch.py` | gate_enforced | L1, L3 | Exercise the production batching and permission consumer without Odoo boot. |
| `scripts/verify/test_native_form_declarations.py` | gate_enforced | L3 | Current native form and interaction declarations. |
| `scripts/verify/test_native_view_workflow_action_coverage_guard.py` | gate_enforced | L1, L3, L4 | Pin the native-button coverage guard to a two-way, fail-closed registry. An uncovered native object button must be registered; a registration that has outlived its gap (method decl |
| `scripts/verify/test_onchange_feedback_evaluation_schema.py` | gate_enforced | L1 | Validate the controlled draft-feedback schema with positive and negative cases. |
| `scripts/verify/test_path_ns_c_s4_browser_probe_credentials.py` | gate_enforced | L1, L2 | Guard the S4 browser probe's per-entry credential contract. The probe signs the same-name ``admin`` into two namespaces. It must never carry a literal password: each entry's secret |
| `scripts/verify/test_platform_database_governance.py` | gate_enforced | L3, L4 | Pure decision tests for the platform database governance vocabulary. The module under test imports nothing from odoo, so these tests drive it with plain values. Real ORM enforcemen |
| `scripts/verify/test_pr_publish_preflight.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/test_product_release_version_guard.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/test_repository_clean_history_guard.py` | gate_enforced | L1, L3, L4 | no docstring |
| `scripts/verify/test_role_surface_exposure_declaration_guard.py` | gate_enforced | L1 | no docstring |
| `scripts/verify/test_sc_data_scope_ceiling_generate.py` | gate_enforced | L2, L3 | Negative controls for the derived company-scope ceiling generator. |
| `scripts/verify/test_sc_data_scope_rule_coverage_guard.py` | gate_enforced | L1, L3, L4 | Negative controls for the data-scope rule coverage guard. |
| `scripts/verify/test_static_suite_frontend_toolchain_guard.py` | gate_enforced | L2, L4 | no docstring |
| `scripts/verify/test_system_performance_baseline.py` | gate_enforced | L1, L3 | Non-zero tests for the system performance baseline normalizer. Every case runs against synthetic payloads; no runtime, database or network is touched. Positive cases must reach ``s |
| `scripts/verify/test_system_permission_concurrency_probe.py` | gate_enforced | L4 | Probe safety prerequisites, not evidence that database races passed. |
| `scripts/verify/test_system_permission_runtime_observation.py` | gate_enforced | unknown | no docstring |
| `scripts/verify/test_tenant_delivery_manifest.py` | gate_enforced | L3 | no docstring |
| `scripts/verify/test_tenant_extension_storage_guard.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/test_tenant_payload_v1.py` | gate_enforced | L3, L4 | no docstring |
| `scripts/verify/test_tenant_product_payload_boundary_guard.py` | gate_enforced | L4 | no docstring |
| `scripts/verify/test_unified_page_contract_v2_schema_guard.py` | gate_enforced | L3 | Pin the Web business-purpose derivation check to an exact predicate. `DECLARED_BUSINESS_PURPOSES` must be the complement of `NON_BUSINESS_PURPOSES`. Matching only the `ACTION_PURPO |
| `scripts/verify/test_user_permission_view_contract_boundary_guard.py` | gate_enforced | L1, L3 | Offline safety tests for the read-only personnel contract probe. |
| `scripts/verify/test_web_unified_page_contract_v2_guard_row_identity.py` | gate_enforced | L1, L4 | Self-test: the row-activation identity guard must reject placement inference. The guard previously only asserted that the literal string ``row_click`` existed in the navigation run |
| `scripts/verify/test_workflow_action_semantics_completeness_guard.py` | gate_enforced | L1, L3, L4 | Pin the approval-verdict check to a real control-flow use. `can_review` must decide whether an approval action is offered. Counting a bare mention would also accept a verdict that  |
| `scripts/verify/test_workflow_contract_profile_loader.py` | gate_enforced | L1, L3, L4 | Pin the workflow contract profile loader to a complete, fail-closed read. The registry mixes inline literals with helper-built entries. A reader that only sees the inline half sile |
| `scripts/verify/test_workflow_state_phase_coverage_guard.py` | gate_enforced | L1, L3, L4 | Tests for the workflow state_phase coverage guard. |
| `scripts/verify/ui_contract_v2_contract_boundary_guard.py` | gate_enforced | L1, L2 | Guard UiContractV2 handler/assembler contract ownership boundaries. |
| `scripts/verify/ui_contract_v2_responsibility_map_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/unified_page_contract_v2_action_guard.py` | gate_enforced | L1, L3 | Guard ActionContract v2+ consolidation without requiring Odoo. |
| `scripts/verify/unified_page_contract_v2_assembler_guard.py` | gate_enforced | L1, L2, L3, L4 | Guard the v2+ backend assembler without requiring an Odoo runtime. |
| `scripts/verify/unified_page_contract_v2_client_guard.py` | gate_enforced | L1, L2 | Guard client trimming for Unified Page Contract v2+. |
| `scripts/verify/unified_page_contract_v2_data_guard.py` | gate_enforced | L1, L3 | Guard DataContract v2+ consolidation without requiring Odoo. |
| `scripts/verify/unified_page_contract_v2_guard_inventory.py` | gate_enforced | L1 | Guard Unified Page Contract v2 verification targets stay complete. |
| `scripts/verify/unified_page_contract_v2_intent_guard.py` | gate_enforced | L1, L2, L3, L4 | Guard the platform-level Unified Page Contract v2 intent. |
| `scripts/verify/unified_page_contract_v2_runtime_guard.py` | gate_enforced | L1 | Guard RuntimeContract v2+ control-plane semantics without requiring Odoo. |
| `scripts/verify/unified_page_contract_v2_schema_guard.py` | gate_enforced | L1, L3, L4 | Static guard for Unified Page Contract v2+ protocol assets. |
| `scripts/verify/unified_page_contract_v2_status_guard.py` | gate_enforced | L1 | Guard StatusContract v2+ source consolidation without requiring Odoo. |
| `scripts/verify/unified_page_contract_v2_web_consumer_guard.py` | gate_enforced | L1, L2, L3 | Guard the web Unified Page Contract v2 consumer surface. |
| `scripts/verify/v1_1_convergence_status_guard.py` | gate_enforced | L1, L2, L3, L4 | no docstring |
| `scripts/verify/web_contract_v2_frontend_architecture_guard.py` | gate_enforced | L1, L2, L3, L4 | Guard the Web frontend Contract V2 architecture boundary. The default mode is a debt-lock guard: existing violations are reported and bounded, while new default-path violations fai |
| `scripts/verify/web_unified_page_contract_v2_guard.py` | gate_enforced | L1, L2, L3, L4 | Guard web contract API migration to Unified Page Contract v2. |
| `scripts/verify/workflow_action_semantics_completeness_guard.py` | gate_enforced | L1, L3, L4 | Prove the backend's own action-declaration side is complete. A transition the backend lets a user execute must carry a published business purpose, because the Web is not allowed to |
| `scripts/verify/workflow_contract_profile_loader.py` | gate_enforced | L1, L3, L4 | Single static reader for the workflow contract profile registry. ``workflow_contract_service.PROFILE_BY_MODEL`` mixes inline literals with helper-generated entries:: PROFILE_BY_MOD |
| `scripts/verify/workflow_state_phase_coverage_guard.py` | gate_enforced | L1, L3, L4 | Every raw workflow state a profile can meet is mapped to a business phase. ``WorkflowContractService.describe_record`` derives the published phase with:: business_phase = profile[" |

## 13. 执行图

`verification_execution_graph.json` 包含 workflow → job → step → make target → script →
resource/evidence 的有向边，并保留 Make prerequisite、recursive make、acceptance suite entrypoint
和证据权威节点。共 1073 个节点、2224 条边。

## 14. 结论边界

现有体系不是缺少几个 guard，而是没有把“调度入口、执行体、行为责任、证据权威”四者统一到
同一变更影响模型。P4-00 的证据支持以下结论：

1. 路径分类可以用于路由候选检查，但不可作为产品影响或验证充分性的证明。
2. L1、L2、L3 必须分别绑定实际执行体和行为断言；L4 只做交付治理。
3. 未执行、未覆盖、未知依赖和环境失败都不得由历史 PASS、skip 或父 workflow 成功替代。
4. 当前契约消费者路径的 presentation 过度触发，与 Renderer 注册表的 presentation 欠触发
   同时存在，必须由符号/字段/依赖影响模型修复。
5. 长尾手工验证不能继续被叙述为自动门禁；先建立接线或明确“不适用”的证据责任，再谈复用。

本报告不声称当前验证体系已经完成重构，也不声称任何产品行为或交付已经通过。
