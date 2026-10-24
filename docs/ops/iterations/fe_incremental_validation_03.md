# FE-INCREMENTAL-VALIDATION-03 — 执行器交接

更新时间：2026-10-25（Asia/Shanghai）。Owner 要求停止当前执行器实施，完成排查、计划和交接，由新执行器接续。

## 动态契约边界（最高优先约束，Phase 1 收口时明确）

本仓库的最高职责界限是**运行时契约是唯一产品事实来源**：模型/字段/列、动作、可见性、
权限与只读、状态语义、呈现参数与默认值都由声明层（P0 `smart_core`、P1
`smart_construction_core`、P2 `smart_construction_custom`、P3 低代码运行时配置）在运行期
声明并生成运行时产物；前端只消费，不自造、不推导、不用默认值兜底。

因此验证体系里每个环节必须显式说清它**测的目标是什么**，并且四类目标不得互相冒充：

1. **P4 工具逻辑**：CI 调度/选择/回执工具自身的单元测试，证明工具行为正确；
2. **P4 验证表面积**：验证车道覆盖/债务棘轮，证明治理负债只减不增；
3. **产品动态契约**：运行期生效/发布契约（声明 → 生成 → 运行时产物）的 readback；
4. **产品事实数据**：运行期事实数据来源与初始化动作的 readback。

铁律：**静态 JSON 快照不是动态契约权威**；「CI 工具单测绿」「全量绿」都不能证明动态契约
完整。ORM 复用的 `runtime_contract_readback_missing` 与 `fact_scope_readback_missing` 正是
指：只有运行期 readback 才能闭合这两项，任何只读 JSON/源码树哈希等价都不足以授权 REUSE。

## 阶段模型（三阶段，各自独立收口；高效与准确的手段不同）

| 阶段 | 身份 | 高效手段 | 准确手段 | 复用 |
| --- | --- | --- | --- | --- |
| 迭代 iteration（本地日常） | HEAD + 显式 dirty scope | L1 静态 + 仅受影响非零 L2 | 精确身份 + 未变失败不盲重跑 + 契约缺口即停机 | `evidence_scope` 本地同循环复用（输入不变） |
| 集成 integration（PR 候选） | clean 冻结完整指纹 | scope-first 调度 + 认证复用（指纹等价，非祖先）+ 决策前移 | 精确 head 绑定 + 独立审查 + 必需远端 CI + 复用仅独立认证权威 | 跨 PR/分支/定时 run 的认证回执复用 |
| 候选发布 candidate release（显式/夜间） | 冻结候选完整指纹 | 只在显式路径/夜间跑，不塞进普通 PR | 全量释放门禁 + 升级 + smoke + 回滚就绪 | **无复用（全量强制）** |

四条不可违背的收口规则：
1. 复用只属于**集成**阶段；迭代只做本地复用，候选发布永不复用（定时/full dispatch 强制执行全部目标）。
2. 集成的复用靠**可验证输入等价（指纹等价）+ 独立认证权威**，不靠 Git ancestry——兄弟分支内容寻址相同时可复用。
3. 「高效」来自 scope-first（迭代+集成）+ 认证复用（仅集成）；「准确」来自精确身份绑定 + 独立证明 + fail-closed。
4. `--discover-receipts` 只在 `pull_request` 打开；schedule/workflow_dispatch（候选/full）不发现、不复用。

### Phase 1 `tool_checks` 的精确目标（已收口）

| 映射目标 | 测的是什么 | 不测什么 |
| --- | --- | --- |
| `verify.ci.workflow.contract` | P4 CI 调度/选择/回执工具逻辑单测 | 产品动态契约 |
| `verify.verification.lane_coverage` | P4 验证表面积债务棘轮 | 产品动态契约 |

控制面文件（`backend_impact_plan.py`、`backend_suite_plan.py`、`backend_test_receipt.py`、
`ci_risk_classifier.py`、`select_authoritative_workflow_run.py`）只要求其所属 P4 工具门禁跑通，
不触发 ORM，也不声称验证产品契约。该映射不得演化为手写免测表：每一条都必须能由对应 make
目标真实执行到该文件的测试。

## Phase 2 —— ORM 可复用输入闭合模型（设计，最高优先约束下）

ORM 收据 `reuse_ready=false` 的四类 blocker 各自对应一个闭合机制，**任一维度缺失即 RUN/BLOCK，
任何维度都不得从其他维度推断**。这是「每个环节测试什么目标」的精确落点：

| 收据 blocker | 闭合机制 | 测的目标 | 未闭合时的行为 |
| --- | --- | --- | --- |
| `platform_source_not_authenticated` | `verify_github_origin`：run/attempt/artifact/head/仓库/tree 平台级认证 | 执行来源真实性 | RUN（不 REUSE） |
| `artifact_attempt_not_attested` / `execution_definition_not_attested` | `attest_execution_definition`：PR 复用工作流 referenced_workflows + merge parent + 完整 tree + workflow blob | 执行定义与重试归属 | RUN |
| `runtime_contract_readback_missing` | 运行期 readback 探针的 `observation`（source/contract/structure 摘要） | 动态契约声明→生成→运行时产物一致 | RUN |
| `fact_scope_readback_missing` | 同探针的 `business_facts_sha256` + `value_parity`（source/projection/facts 三方） | 事实数据来源与投影一致 | RUN |
| `target_dependency_closure_not_certified` | 内容寻址 whole-tree 绑定 + 查询依赖/关联模型权限闭包 | 目标依赖与权限闭包 | RUN |

动态契约权威铁律的落地：`value_parity` 只对 `DIRECT_SCALAR_TYPES` 且三方齐备的存储字段做
`checked`；关系字段、compute/related/translate/company 依赖、非标量投影一律 `uncovered`，并挂
`projection_value_coverage_incomplete`。`uncovered` 非空时该目标**不得 REUSE**（不能把全量绿、
源码树哈希或静态 JSON 快照冒充动态契约完整）。当前 readback 实测 `checked=18 / uncovered=77`，
故 ORM 复用仍被正确阻断。

闭合的受管前提（未满足前不宣称可复用）：
1. readback 探针必须在 CI 的逐模块 fresh database 环境内执行（当前只在 `local.dev` 跑，`not_ci_execution`）；
2. 查询依赖闭包（`query_dependency_closure_incomplete`）与关联模型权限闭包
   （`related_model_permission_closure_incomplete`）必须逐模块证明；
3. 平台执行认证（`platform_execution_not_attested`）走 `verify_github_origin`。

实现落点（已加入 `scripts/ci/backend_test_receipt.py`，并由
`scripts/ci/test_backend_test_receipt.py` 覆盖，保持既有 blocker 词表不变）：
- `reuse_closure(...)`：五个闭合维度的单一事实源，`reuse_ready` 仅在全部维度独立认证后为真；
- `readback_witness_closure(witness)`：把运行期 readback 报告映射到契约/事实两维，
  `uncovered_fields` 非空即保持事实维度开放（`projection_value_coverage_incomplete`）。

## Phase 3/4 —— 安全复用决策（体系化，已落成并测试）

复用的唯一权威仍是 `evidence_scope.plan_units`（指纹不变 + status ∈ SUCCESS_STATUSES）。本轮把
「认证 → 复用授权 → 决策」体系化，并钉死安全边界：

- `receipt_reuse_authorized(receipt)`：**只信任独立认证的权威**。当前唯一授权来源是 isolated
  纯 Python profile 的 `verified_workflow_execution` 权威；生产者回执里的 `reuse_ready=true`
  声明**绝不单独采信**（这是既有的 `test_source_authentication_does_not_authorize_reuse`
  守护的语义）。ORM 目标在契约/事实 readback 与依赖闭包被独立验证前保持不授权。
- `select_historical_receipts`：由 RUN/BLOCK 升级为 **RUN/REUSE/BLOCK**。REUSE 仅在
  `receipt_reuse_authorized` 为真且指纹匹配时产生；认证失败（存在被拒候选且无成功历史）
  保持 fail-closed BLOCK（不静默 RUN）；指纹变更或从未记录才 RUN。

决策仍是 `mode: shadow_only`——即已算出并可信，但尚未接入 workflow 的预分配阶段。下一步
（Phase 4 收口）是把该决策前移到 `plan` 阶段、只 partition RUN 集，并让最终 gate 验证
「有效 REUSE + 实际成功 RUN = 完整覆盖」。

### Phase 4 决策前移（已落成并测试）

`apply_reuse_decision(plan, decisions)`：只对 `RUN` 集调用 `partition`；`REUSE`/`BLOCK`
目标仅登记不执行。全 REUSE 或全 BLOCK 时 `shards=[]`（零分片 → 不建测试分片/容器/数据库）。
覆盖完整性强制：每个选中模块必须且仅被 RUN/REUSE/BLOCK 之一覆盖，部分/重复/越界决策一律拒绝。
`main()` 已把 `--receipt-history` 的决策结果接进 `apply_reuse_decision`，`required` 输出随
RUN 集变化（全复用则 `required=false`）。工作流层级的「最终 gate 验证 REUSE+RUN 覆盖」仍未接线。

工作流接线已落成：`discover_receipt_locators()` 有界发现 attempt-1 远端 artifact locator（API
失败降级为空→RUN）；`--discover-receipts` 仅在 `pull_request` 打开，自动发现把 BLOCK 映射为
RUN（优化未命中，不是正确性信号）；`verify_coverage` 终检强制「`required=true` → suite
success；`required=false` → skipped 且 reuse_authority 为布尔」。`select_historical_receipts`
已移除 ancestry 检查，复用改为**指纹等价 + 独立认证权威**（兄弟分支内容相同即可复用）。

Readback 身份与绑定已落成：`candidate_head_identity()` 把探针报告绑定到精确
`CANDIDATE_GIT_HEAD`/`CANDIDATE_GIT_TREE`；`readback_closure_blockers()` 仅在 head 精确匹配且
三方 parity 完整时闭合契约/事实维度；`record()` 新增 `--readback` 把 witness 绑入收据。

## 状态与工作区

- 状态：`implementation_in_progress / verification_pending`，不是完成、冻结、准入通过或已发布。
- 仓库：`/home/lidefend/workspace/sce-backend-odoo-entry-validation`。
- 分支：`fix/ci-incremental-scheduling-20261025`，复用原工作树；旧分支和旧证据保留。
- 基线 HEAD：`2694b00718297d03e491f9801e154b7fe7473876`。
- 基线 tree：`a0ee17a6fce38cf085b6367ceb17a32506ba62f5`。
- 当前有未提交改动；本轮无新 commit、push、PR、merge、deploy。
- 分支由 `origin/main` 新建，当前 upstream 仍是 `origin/main`；发布前使用受管入口并核对功能分支目标，禁止直接 `git push`。
- Run：`.agent/runs/FE-INCREMENTAL-VALIDATION-03/run.json`，已登记 `.agent/active-runs.json`。
- P4：既有 CI 选择器、执行回执、workflow 编排。不改产品逻辑、权限、daily、生产、业务数据或测试断言来迎合门禁。
- 本轮授权为系统性修复和验证。不能把昨天 #723 的合并授权无条件套用到新候选；远端更新/合并仍按本轮授权和仓库规则处理。

## 已证实事实（无需重新全量排查）

1. PR #723 已合并，主线是上述 HEAD。其最终候选 `6d565e46647ed761c3a10176bb08b5c52f7e7cfd` 的四个后端分片通过。
2. PR run `40107769835` 的 authorization 日志明确选了 14 个模块。原因既有 `smart_core`、`smart_construction_core` 的真实产品修改，也有过宽的 `shared_runtime` / `unknown_impact`。
3. 日志实际全量触发包括：整份 `make/ci.mk`、两份 workflow、选择器、`scripts/test/test.sh`；unknown 包括 registry disposition、其他 Make 文件及工具脚本。不能称第一次广泛验证全无依据，也不能把所有 P4 都免测。
4. 纯 `frontend/**` 原先已经可产生空后端范围。主要缺陷是 P4 误归类和每次后续小修改都重新消费 PR 相对 main 的累计范围。
5. Owner 手动触发的主线 full run `40109044346` 已 `success`：14 份回执，合计 673 项测试。下载的原始回执均绑定 main HEAD。
6. 其中 13 个 ORM 目标没有闭合的复用 profile；71 项 Python 目标有隔离 profile。全量绿色不等于 ORM 已可复用。
7. ORM 当前 `config/requirements-test.txt` 未固定版本；Compose 使用 `postgres:15`、`redis:7-alpine` 等可变标签。容器镜像 ID 又包含 SOURCE_SHA 造成候选间变化。不能只比较源码或镜像标签就复用。
8. ORM 回执绑定全 tracked tree，包含观察到的 Python 包与镜像身份，但 `reuse_ready=false`，缺目标依赖、动态契约及事实输入绑定。不要篡改旧回执字段制造能力。
9. 当前 Python profile 也把所有 addons/demo_addons 和整份 workflow 当输入，过宽；历史发现只查询全仓最近 30 个成功 run，可能被无关 run 挤出；复用判断发生在分片和容器启动之后。
10. GitHub PR run API 实际提供 `referenced_workflows`。#723 的 backend workflow 由 merge revision `fc71fa61d8f0c1b2cad0e2a1b09681fc300b3152` 执行，测试源码为 PR head，二者必须分别核验，不应一概排除 PR。

## 已做的未提交修改（半成品，需接续审查）

- `scripts/ci/backend_impact_plan.py`：新增 6 个精确控制面路径到现有工具测试的映射；移除 selector 自身的 unconditional GLOBAL；具体测试文件读取优先保留；输出 `tool_checks` 和 `scope_status`；精确空 diff 不再强制全量。
- **重要限制**：`tool_checks` 目前只是输出，尚未建立逐项强制执行/结果消费闭环；不能仅凭此映射宣称 P4 调度完整。需从既有登记与实际依赖核验，避免长期变成另一张手写免测表。
- `scripts/ci/backend_suite_plan.py`：空模块集合允许 `shards=[]`；输出 `required`。`partition([])` 自身仍拒绝，防止误把非法分片当执行成功。
- `.github/workflows/backend_test_suite.yml`：plan 输出 required；backend job 在 required=true 才启动。仅完成“不适用空范围”接线，尚未接入预分片 REUSE；空 matrix 与最终 required gate 语义仍需 workflow 回归。
- `scripts/ci/backend_test_receipt.py`：新增 `attest_execution_definition`，允许同仓 PR 通过平台 referenced_workflows、merge commit parent、完整 tree 和 caller/callee workflow blobs 核验后进入已有 Python 历史选择。将 authority 标记改为 `verified_workflow_execution`。
- 来源校验仍保留 attempt=1 限制；未证明重试 artifact 归属时拒绝复用，不得仅改名字放行。远端实际 PR 回执完整链尚未验证。
- `scripts/ci/test_backend_impact_plan.py`：控制面/实际读取反例、空 diff 语义测试。
- `scripts/ci/test_backend_test_receipt.py`：PR 工作流证明正例和缺平台证明、错误 parent、定义变化、tree 截断负例。
- 新增 goal/run/本交接文档，active-runs 增加本分支索引。
- 没有修改 `scripts/ops/evidence_scope.py`，继续以其为唯一复用决策权威；没有创建新的缓存服务或并行测试登记体系。

## 已完成定向验证

以下在 dirty 候选上执行，不能冒充主线/远端/冻结验收：

| 命令 | 结果 | 原始日志 |
| --- | --- | --- |
| `python3 -m unittest discover -s scripts/ci -p test_backend_test_receipt.py` | 60 PASS，3.064s | `.runtime/fe-incremental-validation-02/scheduling-receipt-tests.log` |
| `python3 -m unittest discover -s scripts/ci -p test_backend_impact_plan.py` | 26 PASS，0.167s | `.runtime/fe-incremental-validation-02/scheduling-impact-tests.log` |
| `python3 -m unittest discover -s scripts/ci -p test_backend_suite_plan.py` | 32 PASS，0.014s | `.runtime/fe-incremental-validation-02/scheduling-plan-tests.log` |
| `git diff --check` | PASS | 交接终端结果 |

共 118 项定向测试。未执行完整 Quick、workflow/security 回归、远端 CI 或新 ORM 运行；不要为了交接重跑已有效的测试。新变更后仅重跑受影响部分。

## 后续实施计划（依赖顺序）

### 1. 补齐 scope-first 调度

- 将集成覆盖范围（PR 对 main）与当前候选相对有效历史执行的输入变化分开。
- 对无关目标输出 NOT_APPLICABLE；它不是测试 PASS，也不因缺历史回执而进入运行队列。
- 从既有 Make 目标、真实执行脚本、依赖和输入读取关系确定 P4 测试范围。审查当前 CONTROL_PLANE 初稿，并把工具检查结果接入最终 gate。
- 对 Make/workflow 不能简单整文件忽略；区分实际执行定义与调度/说明变更。无法证明影响范围时明确 BLOCK 或保守 RUN 并给出原因，不伪装精准。
- 处理多个选择器口径：`ci_risk_classifier.py` 的 orm_required 与 backend impact、professional quality 路由不可互相覆盖或再次启动无关 ORM。

### 2. 闭合可复用执行输入，尤其 ORM

- 按内容寻址 action 模型绑定源码/测试/参数、实际依赖、执行定义、工具链、环境，而非仅 SHA、目录或分支。
- 核验并锁定测试 Python 依赖（含传递依赖与包内容）、服务镜像及实际测试入口；不要从旧包版本猜造 lock。
- 对既有逐模块 fresh database 路径证明：模块安装、fixture、角色权限、动态契约声明→生成→运行时产物、事实数据来源与初始化动作可重建且绑定。只读 JSON 快照不得冒充动态契约权威。
- 运行时读外部状态、动态未解析输入、随机/时间敏感测试的影响必须明确；不具备等价证明的目标继续 RUN/BLOCK，不能以“全量通过”替代证明。
- 可采用受约束、内容绑定的执行环境来闭合可见输入；复用既有 CI profile，不擅自创建持久数据库/新凭据权威。测试数据库、端口、容器仍按现有 run 隔离清理。
- 避免把 SOURCE_SHA provenance label 当整个环境有效性 key；也不能简单抹去 label 后忽略真实镜像字节差异。

### 3. 统一成功证据发现、认证与决策

- PR、主线、分支、手动和定时成功结果均可申请复用；逐目标按可验证输入等价裁决，不要求历史提交一定是 main 或最近父提交。
- 在现有 verifier 上接入实际 GitHub run/attempt/job/artifact digest 和源码/执行定义证明。PR merge SHA 与 source head 必须区分。
- 查询相关 workflow 历史并分页到合理 TTL/上限，避免全仓 30-run 搜索误失效；失败 API 只能显式转 RUN/BLOCK。
- 将经过认证的回执交给 `evidence_scope`，输出 RUN/REUSE/BLOCK、原因、当前输入指纹、旧回执定位与摘要、时效和历史耗时。
- REUSE 记录绑定当前候选，但引用原始执行，不能续期旧证据、复制 PASS 或为 skipped 目标伪造新执行回执。

### 4. 把决策放到资源分配之前

- plan 阶段先完成目标分类及证据决策，只 partition RUN 集合；全部 REUSE 或 NOT_APPLICABLE 时不创建测试分片、Docker build、数据库或前端构建。
- 给执行者传递可校验的计划；执行阶段重新核对精确候选和计划范围，防止 matrix 缩小覆盖。
- 最终 gate 验证完整覆盖集合 = 有效 REUSE + 实际成功 RUN；BLOCK/失败/缺证据/计划漂移均不得放行。
- 定时和明确 full dispatch 强制执行所有目标，但保留统一回执格式；普通 PR 不应走这个 full 逻辑。

### 5. 验证与量化

先离线回归与历史证据回放，再受控远端验证，不立即重跑全量：

1. 纯前端：后端 RUN=0、后端分片=0。
2. P4 registry/说明变更：仅所属工具检查；无关 ORM 不启动。
3. 单模块/实际 JSON 输入变更：只选真实依赖消费者。
4. 运行器、测试断言、生成器、契约、事实、角色或环境变化：相关回执失效。
5. 同 PR 连续小改、不同分支同输入、合并后同输入：有效证据可复用，基线不限 main。
6. 缺回执、伪造/跨仓来源、过期、错误 merge parent、未绑定 retry、截断树、未知依赖：不得 REUSE。
7. 全 REUSE 或零适用：无 backend matrix，最终 gate 明确接受完整决策，不把零测试报为执行通过。
8. scheduled/full：不因缓存命中而跳过。
9. 回放 #723 最后几次 registry-only 变化，列原策略目标数/耗时、新策略 RUN/REUSE/NOT_APPLICABLE/BLOCK、输入失效原因。
10. 用同环境实测区分测试省时与 BuildKit/pip 缓存省时；只有历史数据则明确估算。

## 证据定位与参考

- 调查：`.runtime/fe-incremental-validation-02/scheduling-correction-analysis.json`。
- #723 实际选择原因：`.runtime/fe-incremental-validation-02/pr723-authorization-audit.log`。
- 手动全量 artifacts：`.runtime/fe-incremental-validation-02/main-full-baseline-40109044346/`。
- 昨天交付结果：`.runtime/fe-incremental-validation-02/closeout-final-status.json`、`final-remote-pr.json`、`final-main-readback.json`。
- 手动全量：https://github.com/lidefend/sce-backend-odoo/actions/runs/40109044346 。
- 成熟模型：https://bazel.build/versions/7.1.0/remote/caching 、https://github.com/bazelbuild/remote-apis 。
- Workflow 机制：https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows 。
- 采用内容指纹/依赖图原则，不迁移整仓到 Bazel，不叠加通用治理框架。

## 新执行器首步

1. 在上述原工作树读取 AGENTS.md、.agent/context.yaml、本记录及 run；确认 HEAD/branch/dirty 文件范围。
2. `make agent.run.resume`，保留所有未提交改动及历史证据，不 reset、不清理工作区、不重跑原 UX 浏览器。
3. 先审查当前半成品，补“空计划→workflow→最终 gate”和“控制面检查真实消费”的回归，然后完成环境/契约/事实闭合设计再扩展 ORM 复用。
4. 不把本交接或 118 项单测当作减负完成。达到上述验收再冻结和走正常候选流程。

当前执行器已按 Owner 指令停止实施；没有后台代码写入任务。
