# 运行时性能正式基线与上线阻断规则

状态：受控回归基线已具备载体（本轮），并已声明成熟系统对标目标层（判定见下节，当前 `overall=failed`；
2026-10-17 取代：剖析样本不再参与绝对目标评分，判定改为 `overall=within_tolerance` + 首个可比目标
`first_contract_assembly=1567.16ms` 仍未达标，见「剖析样本与绝对目标不可比」），
整体仍未验收：日常体验层 `not_run`、上线容量层 `target_unresolved`。所有者于 2026-10-16 明确：
历史性能记录为实验；实际体验已慢，必须优化才能上线。
当前执行与证据索引唯一入口：`.agent/runs/MAIN-SCHEDULED-CI-CLOSEOUT-20261016/run.json`。

## 目标与职责

本批唯一目标是把动态契约系统的实际性能转为可复测、可归因、可阻断上线的证据。
P4 拥有负载声明、采集、比较和交付门禁；P0 拥有通用契约生成/消费的优化；P1/P2
保留各自业务和用户事实。不得通过删权限判断、削减契约语义、复用他人裁剪结果或降低
阈值制造性能通过。本批不新建数据库、端口、凭据、集群，不向生产施压。

## 基线不是预算

- 观测：某精确运行身份下的真实结果，可以失败。
- 实验观测：身份、负载或测量边界不完整，仅支持诊断。
- 正式基线：完整身份和代表性负载下，采集完整、可复测、经独立复核的原始观测集合。
- 达标：逐项满足已批准预算及正确性约束。正式记录失败基线也不能批准上线。
- 优化后结果：与优化前的可比集合比较，不覆盖或删除优化前数据。

现有 `frontend_delivery_performance_baseline_v1.json` 为历史实验观测。其18核环境与
2026-10-16 GitHub 4核环境不可直接用相对退化比例裁定。历史相对改善不再豁免绝对预算。
绝对预算继续来自 `config/frontend/release_performance_budgets_v1.json`，不在新文档
复制数值。新基线登记不得修改预算，预算调整必须独立说明产品依据。

## 三个互不替代的验收层

| 层 | 用途 | 完成条件 |
| --- | --- | --- |
| 受控回归 | 发现同环境下代码回归 | 冻结产品/工具/数据与执行条件，真实操作样本及正确性通过 |
| 日常体验 | 验证目标服务器上的实际用户等待 | 绑定部署、前端产物、实际网络和代表性角色/数据规模，关键流程达标 |
| 上线容量 | 验证目标负载下的稳定性 | 已确认目标并发、数据规模、吞吐和错误预算，容量运行与恢复通过 |

容量目标和生产等价资源尚未核定时，必须标记 `not_run/target_unresolved`，不能把单用户
五次采样当作容量验收。日常开发只使用登记的 demo 或客户隔离环境；不能用平台管理员
的空数据结果代表业务用户，也不能为测试把真实历史数据搬进通用 demo。

## 必备身份与负载

每份正式证据必须包含：源/目标代码身份、实际服务端部署身份、前端产物摘要、探针与
预算摘要、运行时间、运行时版本、CPU/内存和容器限制、浏览器/视口、网络路径、数据库
及数据快照身份、各关键模型可见规模、租户/公司/角色/项目范围、版次/策略版本、并发、
后台负载、冷暖状态和操作边界。身份不得仅以环境名称或端口代替。

原始样本不可省略。报告请求数量、服务端阶段和子阶段、SQL数量（有可用来源时）、
响应字节、请求往返与UI就绪时间，以及错误/超时/拒绝结果。未知值为缺口，禁止填零。
SQL/函数耗时不相加冒充端到端耗时；嵌套阶段/并行请求不得重复计时。
样本数不足以支持稳定p95/p99推断时明确样本上限；五样本nearest-rank仅为现行回归门，
不能包装成真实容量分位数。

首次进程调用、浏览器冷缓存、后端冷缓存和切公司后首次调用分别标记。不得通过清理
共享环境缓存制造冷态；冷态只在受管隔离生命周期内建立。暖态给出预热次数，不删除
慢样本或失败样本，也不反复重跑直到偶然通过。

## 本轮载体（受控回归）

本轮只增加 P4 采集/归一化载体，未改动任何 P0–P3 产品语义：

- 唯一归一化入口 `scripts/verify/system_performance_baseline.py`（schema
  `system-performance-baseline/v1`），单测 `scripts/verify/test_system_performance_baseline.py`
  经 `make verify.system.performance.baseline.unit` 执行。缺计时记为缺口而非零值；
  嵌套阶段永不相加（`stage_sum_forbidden`）；样本观察数与保留数不相等即断言失败。
- 受管采集包装 `scripts/verify/local_dev_performance_baseline.sh` 只复用登记的
  `local.dev.*` 运行身份，身份只读采集器为 `scripts/ops/local_dev_performance_identity.py`。
- 采集入口 `make local.dev.runtime.performance.baseline`。本轮记录
  `artifacts/backend/system_performance_baseline.json` 为 `status=baseline`、`gaps=0`、
  样本 11/11，三层状态 `controlled_regression=passed` / `daily_experience=not_run` /
  `capacity=target_unresolved`；生成视图 `docs/ops/audit/system_performance_baseline.md`。
- 该记录绑定采集时的 worktree 身份（dirty），只用于受控回归与阶段定位，不构成浏览器、
  SLO、容量或生产验收，也不能替代日常体验层或容量层。

## 成熟系统对标目标层（2026-10-16 新增判定）

历史 `scripts/verify/baselines/platform_sla.json` 与 `platform_performance_smoke.json`
的 p95 预算（8000/5000/3000 ms）是本系统对自身历史的回归门，**不是产品目标**：它明显宽于
成熟企业系统对同类操作的要求。本轮把"对标成熟系统"的判定写成可机器校验的声明，禁止用叙述
代替证据，也禁止为了让现状"通过"而下调目标。

- 声明载体：仍是唯一归一化器 `scripts/verify/system_performance_baseline.py` 内的
  `BENCHMARK_SOURCES` / `BENCHMARK_LADDER` / `MATURE_SYSTEM_TARGETS`，schema
  `mature-system-performance-targets/v1`，与受控回归记录同一次生成；单测经
  `make verify.system.performance.baseline.unit` 执行。
- 外部参照来源（每条目标至少引用一条，声明含 publisher/title/url 与原文口径，禁止编造数值）：
  Google RAIL（0–100 ms 视为即时）、Core Web Vitals INP（p75 ≤200 ms good）、
  Nielsen Norman Group 0.1/1.0/10 s 三界、TTFB（≤800 ms good）、LCP（≤2.5 s good）、
  Salesforce Experience Page Time（健康 <3 s）、SAP Fiori Timing（1–3 s，>3 s 打断心流）。
- 判定规则：`met`（≤ target）/ `within_tolerance`（≤ tolerance）/ `failed`（> tolerance）/
  `not_evaluated`（样本不足或观测缺失，永不记为通过、永不记零）。p95 使用 nearest-rank 且带
  最小样本数下限；`overall` 取已评估目标中的最差判定；`capacity` 恒为 `target_unresolved`。
  目标声明本身非法（未知来源、目标值与阶梯层不一致、容差低于目标）时 fail-closed。
- 现状对照（本轮受管采集；principal `smart_construction_demo.user_demo_role_finance`
  uid45 / company1，action 878，`sc-local-dev` / `sc_dev_demo`）：

| 目标 | 阶梯层 | 聚合 | 样本 | 观测 ms | 目标 / 容差 ms | 现行历史门 ms（门宽比） | 判定 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `warm_contract_dispatch` | instant_interaction | p95 | 24 | 178.80 | 100 / 200 | 5000（50x） | `within_tolerance` |
| `cold_contract_assembly` | keeps_flow | max | 1 | 203.15 | 1000 / 3000 | 5000（5x） | `met` |
| `profile_first_contract_assembly` | keeps_flow | first | 2 | 3593.40 | 1000 / 3000 | 5000（5x） | `failed` |
| `startup_system_init_first` | good_ttfb | first | 1 | 1775.73 | 800 / 3000 | 8000（10x） | `within_tolerance` |
| `startup_system_init_http` | good_ttfb | p95 | 1 | 617.86 | 800 / 3000 | 8000（10x） | `met` |
| `warm_startup_repeat` | keeps_flow | p95 | 5 | 486.51 | 1000 / 3000 | 8000（8x） | `met` |

- 判定结论：现行 SLA 门比成熟系统对标目标宽 **5–50 倍**；唯一硬越界项是
  **进程首次 ui.contract 装配**（3.59 s > 3 s 容差），而现行 5000 ms 门会直接放行它。
  其余项虽在容差内，但热请求 dispatch p95（178.80 ms）距"即时"目标（100 ms）仍有距离。
  该层是**产品目标判定**，不放松、不替代历史 SLA 预算，也不是容量/SLO/生产验收；
  容量层保持 `target_unresolved`，整体仍不收口。

### 进程首次硬越界的时间窗归因（本轮新增）

唯一硬越界项 `profile_first_contract_assembly` 被拆成两层：可确证的**进程级一次性初始化**，
与**进程首次缓存构建 + 首次装配**（后者在稳态每请求中并不重复付出）。判据来自同一归一化器
对 `first_call_boundary: True` 目标附带的 `one_time_process_init` 注解：只取
`FIRST_CALL_ONE_TIME_MARKERS` 标记帧 cumulative 的**最大值**，嵌套帧永不相加；无可确证标记
时记 `not_declared`，不记零。

| 项 | 值 | 证据 |
| --- | ---: | --- |
| 进程首次装配（观测） | 3593.4 ms | `contract_profile` 样本 0，`ui_contract_v2.py:505 handle` |
| 一次性进程初始化（可确证） | 560.26 ms（15.6%） | `translate.py:545 __call__`，826 次调用 |
| 该一次性成本的来源 | `_get_code_translations` → `polib.parse` | 524.83 ms / 472.89 ms，由首个需翻译的视图读取触发 |
| 同流程第二次请求 | 143.97 ms（−96%） | 样本 1；SQL 1040 → 22 |
| 同进程冷重建 | 197.20 ms | `contract_request` 探针 `cold_rebuild` |
| `res.currency` ≈540 ms 归因 | 523.68 ms | `res_currency.py:332 _get_view` 是上述 `_get_code_translations`/`polib.parse` 的外层，非模型成本 |

- `res.currency` 的约 540 ms **不是模型成本**，而是 Odoo 代码翻译（PO 文件解析）的进程级
  一次性加载，由首个需要翻译的视图读取触发；不得按模型特判修复，也不得把该收益归给
  "按需物化"。
- 进程首次的其余成本（≈3033 ms）是**首次原生视图读取 + 首次契约编译/关系弹窗装配**
  （首次填充视图与投影缓存）：`_inject_relation_entry_contract` 1600.46 ms、
  `_build_relation_search_dialog_contract` 984.88 ms（17 次）、`deepcopy` 710.85 ms
  （765542 次）、`ir_ui_view.get_view` 734.86 ms（22 次，内含上述 523.68 ms 翻译）。
  这些帧互相嵌套，`stage_sum_forbidden=true`，**不得相加**，也不得当作互斥阶段预算。
- 因此该硬越界既不等于"进程初始化"，也不等于"每请求成本"：第二次请求与同进程冷重建
  证明缓存就绪后成本骤降。`one_time_process_init` 仅在含剖析的样本上可测，
  `cold_contract_assembly` 与 `startup_system_init_first` 当前记 `not_declared`。

## 本批实施顺序

1. 保全旧失败及原始环境，列出不可比原因。完成：原始证据可读且哈希绑定。
2. P4 补逐样本分段采集，保留原操作边界。完成：非零正负测试；无凭据、请求参数或
   业务正文输出；缺计时不能生成零值；异常不吞。再进入受管有限样本观测。
   本轮状态：采集与归一化载体已建立，见「本轮载体（受控回归）」。
3. 复用 `local.dev.runtime.performance.observe` 作后端定位，以及既有
   `verify.frontend.delivery_hardening.release.performance_probe` 作浏览器测量。
   前者不是浏览器/上线验收；后者必须通过已登记profile的身份和fixture前置。
   只跑变化影响集合，不以完整CI代替定位。
4. 根据阶段证据选最大成本，进行单请求调用/查询剖析；剖析本身的扰动样本单列。
   完成：瓶颈有可复现的次数、耗时及代码所有者，才进入该所有者层修复。
5. 每项优化先证明契约和权限等价，再测同环境前后。角色/公司/项目/数据用途隔离、
   策略发布和权限撤销后的失效必须有反例。只考虑已证明输入一致的请求内复用；
   持久缓存需要完整键、版本、失效和一致性协议，不能先缓存再补安全约束。
6. 日常体验和容量按已核定身份执行并独立复核；性能达标、无语义退化、所有必需门禁
   通过后才能冻结发布。任何未完成层保持显式阻断。

## 验证、停机与回滚

L0绑定身份；L1语法/边界；L2采集器、判断器和所有者的非零正负测试；L3只在模块变化
需要时升级；L4执行影响集合；L5独立复核及冻结候选CI。P4采集变更不要求产品契约快照
刷新；产品优化则比较实际契约并验证角色/版本边界。浏览器采集不是纯源码断言可替代。

环境漂移、身份不明、前置失败、缺样本、超预算、权限/契约不等价均阻断后续交付。
采集器和CI改动可按文件回滚；产品优化按独立提交回滚，恢复代码不能伪造旧环境证据。
原始失败记录保留。基线通过、主线集成、部署和产品交付分别报告。

## 后端全链路专项（本批新增执行范围）

以一次实际用户操作为入口，串联 login/session.bootstrap/system.init、ui.contract、
列表查询、表单读取和业务动作。每条链先声明角色、公司、数据规模、请求依赖和响应边界；
尚未观测的链标记 not_run，不用启动链结果代表所有接口。

| 阶段 | 必须取得的证据 | 优化约束 |
| --- | --- | --- |
| 路由、认证与会话 | 请求数量、串并行关系、处理/等待耗时 | 不减少身份核验 |
| ACL、记录规则、能力裁剪 | 调用次数、SQL指纹计数、公司/角色输入 | 不跨权限复用 |
| 事实读取与契约编译 | 每阶段自身/累计耗时、重复读取与编译次数 | 保持事实来源唯一 |
| 场景与导航投影 | 各中间载体节点数、最终保留集合、提供者加载次数 | 先证明消费者依赖再裁剪 |
| ORM与数据库 | 查询次数、重复模式、慢查询与执行计划 | 无证据不加索引、不改规则 |
| 清理、复制与序列化 | 对象展开次数、响应字节、耗时与内存 | 保持返回结构及对象隔离 |
| 业务动作及完成反馈 | 写入/校验/提交边界与端到端时间 | 保留事务、审计与幂等 |

先完成启动/切公司已超预算链，再按测得耗时处理契约、列表、表单与写操作。
剖析结果与无剖析样本分离；优化前后须同环境交替采样且完整契约相等。
不把 Python 调用数量下降当作请求延迟改善，不以删除契约或放宽权限换性能。

## 角色维度契约变化（本批新增执行范围）

单 principal 基线看不到契约随角色变化。角色维度纳入同一唯一归一化器与同一条 record，
不新增第二套口径，也不据此改写历史测量。

| 维度 | 采集方式 | 本轮结果 |
| --- | --- | --- |
| 角色集合 | 9 个已登记 demo principal | `role_count=9` |
| 请求场景 | `list_action_open`（action 878 + 该角色自己的 menu carrier）、`form_action_open`（action 878 + 该角色自己可读的 `payment.request` 记录） | 两场景逐角色独立记账 |
| 契约身份 | 逐角色 `identity_ref` / 契约面摘要 | `contract_identity_varies_by_role=true`、`contract_surface_varies_by_role=true`、`surface_digest_stable_within_dispatched_role=true` |
| 导航能力 | 该角色是否持有 action 878 的发布路由/menu carrier | 仅 `role_finance` present，其余 8 个 absent |
| 关系面 | 递归 relation 节点的目标数 / search dialog 数 / 导航权威数 | form 场景 4 个已派发角色均为 3 target + 3 dialog，但导航权威仅 `role_finance=3`，其余 0 |
| 字段事实 | relation field map 的 `can_read` / `can_create` / `reason_code` | form 场景随角色变化（`payment_execution_ids`） |
| 拒绝语义 | 门禁拒绝 vs handler 失败 vs 无可读记录 | 三者严格区分；拒绝角色**绝不**返回替代契约 |

约束：

- 场景只使用该角色**自己**可读的记录；无记录记 `unavailable` 并**跳过**，不得借用他角色记录。
- 冷角色阶段**只清进程本地 `CONTRACT_PROJECTION_HOT_CACHE`**；原生视图与翻译保持热，
  以免把一次性翻译加载误记成角色成本。
- 首个角色的 `assembly_first` 付进程首次成本，须如实记为该角色首触、不得归为其稳态成本。
- 逐 role/case 样本全部保留并计入样本账目（`observed==retained`）；缺计时记 `gap`，永不补零。
- 结论只作"角色可变"的反例证据，不构成 SLO、容量或发布验收，也不证明任何单项优化的收益。

归一化账目（本轮）：`role-matrix` entry `96/96`、`identity_match=match`；
record `status=baseline entries=5 gaps=0 samples=142/142`；mature 目标 `overall=failed`、
`capacity=target_unresolved`。

### 剖析扰动隔离（硬约束）

剖析会显著放大被剖析路径：同环境交替采样中，剖析首次 `3814.6 ms` 对未剖析首次 `1962.52 ms`
（同 SQL 1040）约 `1.94×`，热路径中位对中位 `148.74` 对 `76.35 ms` 约 `1.95×`。
因此：

- 剖析样本只用于定位所有者与调用次数，**不得**作为基线数值，也不得与 HTTP/浏览器数字比较。
- 前后对比必须使用同一种采样方式（剖析对剖析、未剖析对未剖析），并与未剖析稳态分别报告。
- 剖析本身不产生额外 SQL；若前后 SQL 数不同，必须先解释查询差异，不能归因于剖析。

### 剖析样本与绝对目标不可比（判定规则，2026-10-17）

上一轮的唯一硬越界 `profile_first_contract_assembly` 用的是**剖析样本**（`profiled:true`，`3814.6 ms`），
而同一份基线里已存在**未剖析**的首次样本 `process_first=1567.163 ms`。把 cProfile 放大的数值判给绝对
毫秒目标属于**口径错误**，不是系统结论，因此新增判定规则而不是放宽阈值：

- **规则**：剖析样本永不参与绝对目标评分（`profiled` 样本只上报、只在行内保留
  `profiled_values_ms`）；只有未剖析样本可判定。目标可声明 `measurement_basis`（`unprofiled`/`profiled`）
  与 `diagnostic_only`；声明为剖析或 `diagnostic_only` 的目标**永不产生通过或失败**，只产出
  `not_evaluated` + 理由。`diagnostic_only` 必须声明 `measurement_basis=profiled`，
  防止用它把**本可判定的未剖析测量**藏起来（声明校验 fail-closed）。
- **新增可比目标**：`first_contract_assembly`（`selector.sample_labels=[process_first]`，与
  `profile_first_contract_assembly` 同 tier `keeps_flow` 1000/3000），承接同一个"首个契约装配"问题。
- **判定变化（同一批 payload，仅评分口径变）**：

| 目标 | 旧判定 | 新判定 |
| --- | --- | --- |
| `profile_first_contract_assembly` | `failed` 3814.60（剖析） | `not_evaluated`（剖析 3814.60 仍上报） |
| `first_contract_assembly` | 无此目标 | `within_tolerance` 1567.16（未剖析 `process_first`） |
| overall | `failed` | `within_tolerance`（met 3 / within 3 / failed 0 / not_evaluated 1） |

- **口径不变的部分**：`samples=142/142`、`entries=5`、`gaps=0`、`stage_sum_forbidden=true`、
  `capacity=target_unresolved` 均未变；首个契约装配 `1567.16 ms` **仍高于** 1000 ms 的
  `keeps_flow` 目标，即**仍未达标**，只是不再由剖析数值充当证据。完整性标志改为
  `complete_over_comparable_targets`（只在"每个有可比依据的目标都有判定"时为真），
  `ungradeable_by_declaration=1` 单独上报，绝不计入通过。
- **生成方式（可复算）**：本轮**未重新采集** payload，只用唯一归一化器对**同一批**
  hash 绑定的 payload 重放，因此判定变化只能归因于规则。重放命令、输入 sha256、前后判定见
  `artifacts/backend/system-performance-baseline/comparability-rule-replay.json`
  （`494ff82b…`）；制品 `artifacts/backend/system_performance_baseline.json`（`f894ccee…`）、
  报告 `docs/ops/audit/system_performance_baseline.md`（`20f2ccfc…`）。重放两次除
  `generated_at` 外逐字节一致。
- **边界**：这不是收益、不是放宽阈值（阈值与 ladder 未动）、不是容量或发布结论；
  完整重采（全部 source）在任何交付冻结前仍需执行。

## 偏好路径不再整页装配（R5，2026-10-17）

偏好读取曾是契约装配的一个隐式调用者（每读一次偏好会走一次 `PageAssembler`，观测到
27 次 `get_contract_api/build_final_contract` 与 24 个关系 search dialog 构建）。R5 把偏好身份与
装配解耦，性能口径如下：

| 项 | 本轮结论 | 证据 |
| --- | --- | --- |
| 身份校验 | 后端强校验；非法身份 400、无读权限 403、无可解析策略 422；SET 写前失败 | `verify.local.dev.user_view_preference.runtime.orm` 10 tests、两份只读记录探针 |
| stored 路径 | 只返回存储事实，**不编译页面、不解析 list profile** | ORM 测试 patch `PageAssembler.__init__` / `assemble_page_contract` 均未被实例化 |
| effective 路径 | 走 `ListPreferencePolicy.project` 已声明策略投影，**缺策略 422 明确失败**，不返回空策略兜底 | 同上 + 契约快照 |
| 应用次数 | **恰好一次**：服务端不再用存储顺序重排契约列；前端唯一应用点为 `ActionView.vue:3092/3130` | `verify.contract.list_preference.single_application` 静态锁 PASS |

约束与边界：

- 本项只证明"偏好路径不再触发完整页面装配"，**不证明端到端延迟收益**，也不改变
  `profile_first_contract_assembly` 的硬越界结论；mature 目标仍 `overall=failed`、
  `capacity=target_unresolved`。（2026-10-17 取代：剖析样本已退出绝对目标评分，
  `profile_first_contract_assembly` 改为 `not_evaluated`、`overall=within_tolerance`；
  首个可比目标 `first_contract_assembly=1567.16ms` 仍未达标）
- 这不是按模型特判：`res.users`、`res.partner` 等目标仍保留其字段事实、权限与治理分支所需的关系权威；
  被取消的只是**经完整依赖证明不被消费的弹窗生成**。
- 开放项：SET 响应 `data.id` 未在已声明契约中（前端仅消费 `scope_key` + `preference`），属环境分配句柄；
  应按用例声明的响应易变字段归一，须在绑定本写树 source mount 的快照重导轮执行。

## 首次权限成本：进程初始化与每请求成本的实测分离（R4，2026-10-17）

首次契约请求的控制器 `permission` 段观测到 `215.173 ms`，而清 registry 缓存后的重建只有 `132.648 ms`，
热请求只有 `1.5–1.7 ms`。此前把差额记为「进程首次模块/ORM 冷」，但**未实测**；本轮补测并分离。结论只维护于
同一 run 的 `backend_runtime_investigation.permission_gate_attribution.closure`。

**关键前提（旧读数的解释）。** 旧探针的「进程首次」`2.373 ms` 实际上不是首次：探针 setup 推导菜单 carrier 时
调用了 `sc.product.policy.published_route_authority()`，它是 `@tools.ormcache` 进程级缓存，已经把发布路由权威
建好并缓存。因此在同一 principal 上再跑门禁只会命中缓存。要测真正的首次，必须让门禁成为**本进程第一次**
接触权威的调用。

**四个量级（同一 principal、`menu_id=559`）。**

| 量级 | 门耗时 | ACL / SQL |
| --- | --- | --- |
| 热请求（每请求成本） | 中位 **1.81–1.96 ms**（无 `menu_id` 0.242–0.262 ms） | 2 / 3 |
| 清 registry 缓存后重建 | **125.286 ms** | 133 / 288 |
| 进程首次门禁（真） | **484.830 ms** | 219 / 371 |
| 控制器实测首段（重启后首个契约请求） | **215.173 ms** | — |

**拆解。**

- 进程首次门禁 = `principal_group_signature` **263.464 ms**（缓存键/角色集合指纹）+ `_build_runtime_route_authority`
  **218.245 ms**（权威主体）；主体内 `MenuService.build_nav` 107.078、`build_route_authority` 86.167、
  `ProductPolicyService.get_policy` 13.694、`_load_platform_release_gate` 3.123、`user_group_xmlids` 5.237、
  `_normalize_delivery_nav_refs` 5.617 ms。
- **进程首次溢价 = 484.830 − 125.286 = 359.544 ms**，全部落在 `principal_group_signature`（占首次门禁 54.3%），
  即 `registry.clear_cache()` **无法复现**的进程级模型/字段/组集合首次装配；同一调用在清缓存后仅 1.03 ms、热态 1.09 ms。
- 观测的 **215.173 ms 落在实测包络 [125.286, 484.830] 内**，且与进程首次权威主体 218.245 ms 相差 −3.072 ms（98.57%）。
- **无重复调用**：一次门禁内 `build_runtime_route_authority` 1 次、`_build_runtime_route_authority` 首次 1 次 / 热态 0 次。

**对性能基线的口径影响。**

- 首次权限的 `215 ms` 与 `~132 ms` 都**不得**作为每请求基线；稳态每请求基线是 **~1.8–2.0 ms**（带 `menu_id`）
  与 **~0.25 ms**（不带）。任何把首次冷值计入容量的比较都是口径错误。
- `registry.clear_cache()` 只能复现**部分**冷成本；进程级装配溢价必须用「真正的第一次门禁」测量，不能用一个
  已被 setup 预热的调用冒充首次，也不能用清缓存后的读数冒充首次。
- 本项只证明**成本归属**，**不产生时延收益**，也不改变 `profile_first_contract_assembly` 的硬越界结论；
  mature 目标仍 `overall=failed`、`capacity=target_unresolved`。（2026-10-17 取代：剖析样本已退出
  绝对目标评分，见「剖析样本与绝对目标不可比」；`capacity` 仍 `target_unresolved`）
- 未覆盖并保持登记：company 切换（demo finance 仅一个公司）、控制器 ingress/session/transport 残差、
  既有 P0 `act_window.groups_id` 缺口、R3 缓存复制、gen-2 GC 停顿、偏好 SET 响应 `id` 未声明。
  （2026-10-17 取代：`ctime` **不再**充当代码身份，它只是文件变化检测信号；代码身份是受管源码
  `.py/.xml` 的内容 sha256 摘要，正式部署仍须绑定不可变构建或内容摘要。见
  `docs/ops/iterations/main_scheduled_ci_closeout_20261016.md` 的「代码身份内容绑定（2026-10-17）」一节。）
