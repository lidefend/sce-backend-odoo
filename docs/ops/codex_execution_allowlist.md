````md

## 所有者 CI 通过即合并规则（2026-09-23，本节优先）

适用范围：本仓库普通 Gitee PR。所有者已授权必需 CI 通过后直接通过受保护 PR 流程合并，
不再逐 PR 请求人工审查、人工测试确认或重复合并授权；平台审查/测试最低人数设为 0，
新建 PR 不自动附加人工审批门槛。此规则覆盖下文相反的人工批准要求，GitHub 原流程不变。
保留 main 保护及 public_guard、merge_policy_gate、professional_quality_gate、
frontend_release_gate 四项必需检查。成功必须属于当前 PR 的最新源提交及当前目标基线；
失败、缺失、运行中、旧提交或基线漂移均不得合并。按可信风险分类产生的显式 skip 可以接受。
保留既有独立代码复核、公开范围检查；不将其变成所有者点击审批步骤。
合并前重新核验源/目标身份及检查结果，使用平台受保护 PR 合并；不得直接推送 main、
强推、关闭必需 CI 或伪造人工审核。平台若不能绑定合并对象，应明确报告实现限制，
不得宣称已具备无人值守原子自动合并。合并后回读 PR 状态、合并提交及 main；合并不触发产品部署。
平台审批配置的实际降低仍须满足工具要求的操作时确认；本段记录所有者目标，不代表平台已更新。

## 所有者最新执行分工（2026-09-23，本节优先）

本地是代码迭代环境，普通 Gitee PR 候选发布不再要求本地完整 `ci.local.quick` 或完整生成证据门禁。
本地只做 `ci.local.iteration`、按变更影响选择的非零定向测试及 diff/身份检查；普通
`pr.push.gitee` 和 `gitee.ci.pr.create` 不得再因缺少本地 Quick receipt 拒绝候选。
完整公共扫描、生成报告检查、风险选择的前后端集成检查交由远端 PR 执行；远端检查完成前不得
宣称主线集成或合并资格。clean 精确 SHA、独立审查、公开范围审查、远端身份/快进约束与
main 的必需检查保持；人工审核按上方最新合并规则执行。新候选不得继承旧 SHA 的远端成功。
此项覆盖本文旧的“先完整本地 Quick 再普通 Gitee 候选推送”顺序；历史 ci-only bootstrap、
正式版本发布/数据库验收及 GitHub 原入口暂不改变。本地 Quick 可显式诊断，不是普通推送前置。
# Codex Execution Allowlist (Autonomous Mode)

`CANONICAL_ALLOWED_WRITE_BRANCH_REGEX=^(feature|fix|refactor|audit|release|codex)/.+`

## 临时 Gitee 主线集成车道（2026-09-23）

当前续跑授权普通前端 CI 完善。`make gitee.ci.frontend.prepare` 仅在既有外部证据目录
制作依赖包，固定 Node22.17.0/pnpm9.12.3 哈希、只读现有离线 store、bwrap 断网及禁用安装脚本；
绑定锁文件、workspace 与 package manifests，拒绝不支持的 hook/patch/外部依赖。
`make verify.gitee.frontend_cache.unit` 验证输入、包和路径拒绝边界。
`make gitee.ci.frontend.verify` 对已准备包执行当前提交的 lint、严格类型、单元测试和构建，
复用既有外部证据目录；临时无网络/无凭据沙箱不接数据库，任一步失败均非成功。
`make gitee.ci.frontend.cache.install` 默认只读预演；本轮前端 CI 授权允许
`APPLY=1 GITEE_FRONTEND_CONFIRM=INSTALL_REVIEWED_FRONTEND_CACHE` 按精确归档 SHA 安装已复核依赖包。
只追加 `/opt/gitee-ci/frontend/<dependency-key>`，root 所有、0644只读归档；不以root解包/执行，
不覆盖已存在不同内容、不改服务/凭据/数据库。旧缓存保留，失败不改变现有运行配置。
`make verify.gitee.frontend_cache_install.unit` 验证摘要、重复安装和冲突边界。
准备成功不代表服务器安装、完整前端检查或发布验收。

2026-09-28 所有者批准补齐受管本地前端证据复用。`make gitee.ci.frontend.reuse.publish
EXPECTED_HEAD=<sha> GITEE_EXPECTED_MAIN=<sha> GITEE_PR_NUMBER=<n>
GITEE_FRONTEND_OUTPUT=<existing prepared bundle> GITEE_NODE_ARCHIVE=<pinned archive>`
默认仅预演；`APPLY=1 GITEE_FRONTEND_REUSE_CONFIRM=RUN_AND_PUBLISH_EXACT_FRONTEND_EVIDENCE`
在当前 clean 精确候选的断网导出中实际执行四步骤，全部成功且测试非零、产物非空后，
通过既有 owner SSH 认证通道发布到 `/opt/gitee-ci/frontend-reuse/<identity-key>`。
不接受任意旧回执导入，不新增凭据或环境；root仅校验和原子追加普通文件，不解压执行产物。
同身份不同内容拒绝覆盖；传输不确定时先只读核对精确key，不盲目重跑发布。
既有 `gitee.ci.server.update ... GITEE_FORMAL=1` 可安装本轮独立复核的发布/消费模块，
仍需clean SHA、无活动job、预演摘要、备份及回读；不改变worker资源限制或数据库。
远端从受管安装目录读取核验器，绑定源/目标/PR、工具、依赖、配方、环境、日志及产物，
缺失或不合法则记录原因并继续原执行链；成功标注 verified_local_execution，保留四项必需检查。
这属于已授权所有者执行器的受信发布，不声称哈希能证明执行来源，也不防御恶意root/所有者主机失陷。


本次续跑所有者已明确要求直接执行现有 CI 线上更新及 CI-only 真实事件验收。用户截图和登录后的页面
已确认 WebHook 2106026、平台镜像为空、Gitee Go 未开通；历史公开范围及同组客户标识授权沿用本会话。
本轮用户已完成仓库限定 API 令牌并要求继续收口，授权现有 worker 的检查回传安装与验收。
增量入口可通过 `GITEE_CHECKS_TOKEN_FILE` 从私有文件经 SSH stdin 安装到固定
`/etc/gitee-ci/checks.token`，仅 gitee-ci 所有者0600，worker env只登记路径；
原文件及配置纳入精确计划、备份和失败恢复；不进入沙箱、日志或公开仓库。
该授权取代本节下文的“本批没有线上启用授权／条件未齐备”历史状态，但不取代精确计划、备份、隔离、
沙箱与发布检查。正式合并、历史 main 补齐和产品部署仍不授权。
`make gitee.ci.mirror.isolate GITEE_ISOLATION_CONFIRM=ISOLATE_EXISTING_REVERSE_MIRROR` 仅停用既有
gitee-to-github-mirror.timer/service 并回读 inactive/disabled/PID=0；不改旧 runner，不自动恢复镜像。
服务历史 failed 但 MainPID=0 同样视为停止，timer 必须 inactive/disabled。
`gitee.ci.sandbox.profile.install` 仅在无现有 bwrap profile 时安装已审上游 v4.0.3 配置；
`gitee.ci.sandbox.probe` 使用现有 updater 的同服务约束探针验证网络/凭据隔离。不修改全局 sysctl，
不使用 unconfined 通配豁免。配置来源及内容 hash 见批次记录；此为真实环境故障的限定修复。
`make gitee.ci.secret.rotate` 仅轮换现有 receiver 的签名密钥；要求旧 env 精确摘要、私有文件和明确确认，
通过 SSH stdin 传输，备份并原子替换后回读，禁止回显。浏览器一侧由用户完成凭据变更。

GitHub 账号受限期间，仓库所有者授权调整集成流程。仅本节登记的入口可在不访问
GitHub 的情况下使用既有 `gitee-mirror`；本节是下文“GitHub 唯一发布远端／Gitee 仅镜像”
的有界例外，不修改 `origin`，不授权任意远端、强推、自动合并或部署。

- `make gitee.integration.inspect EXPECTED_HEAD=<sha> GITEE_EXPECTED_MAIN=<sha>`：只读。
- `make main.gitee.catchup ...`：默认预演；只允许把已集成的历史主线
  `de9a230d3faab18dd60a219f445f932a8af9d7f5` 快进到 Gitee `main`，不集成未合并专题。
  实际写入要求 clean 合规控制分支、两个本地历史主线锚点一致、远端精确旧 SHA、祖先证明、
  已验证恢复 bundle，以及 `APPLY=1 GITEE_INTEGRATION_CONFIRM=FAST_FORWARD_HISTORICAL_GITEE_MAIN`。
  仓库所有者审阅具体补齐范围后授权执行，不能把流程调整请求自动视为 main 写入批准。
- `make pr.push.gitee ...`：默认预演；实际发布要求 clean 精确 HEAD、有效 Quick 回执、
  只读生成证据门禁、已补齐的精确 Gitee main、同名分支快进检查和发布后回读，参数为
  `APPLY=1 GITEE_INTEGRATION_CONFIRM=PUBLISH_EXACT_GITEE_CANDIDATE`。
  发布前独立审查和外部证据归档仍按既有规则执行；推送成功不等于 CI／审查／合并通过。
- CI-only 有界例外：`make pr.push.gitee GITEE_PUBLICATION_PURPOSE=ci-only ...` 仅允许
  `fix/gitee-temporary-integration-v1` 候选；只读预演不要求历史 main 已补齐，输出相对实时 main
  的全部提交与变更路径，并明确 dirty 内容未包含。实际 APPLY 要求 clean、Quick、生成证据及
  `GITEE_CI_EVIDENCE`/`GITEE_CI_EVIDENCE_SHA256` 精确审阅回执；回执绑定候选/main、1小时内平台
  观察、公开范围授权及证据文件摘要。推送前在线核验隔离、活动服务、模式、安装代码和配置摘要。
  证据缺失/过期/漂移均零推送；不使用布尔跳过。普通 integration 路径约束不变。
- `make gitee.ci.gates.plan EXPECTED_HEAD=<sha> GITEE_EXPECTED_MAIN=<sha> GITEE_SOURCE_BRANCH=<branch> GITEE_PR_NUMBER=<number>`：只读正式门禁计划；要求 clean 控制分支，包含删除和重命名两端，复用现有风险分类。PR 编号为调用方输入，计划不证明平台身份、不执行检查、不授予集成资格。`GITEE_CANDIDATE=1` 显式选择候选级检查。
- `make gitee.ci.pr.inspect ...`：复用 `GITEE_CHECKS_TOKEN_FILE` 私有文件，只读核验指定 PR、同仓源分支与受保护 main 的精确 SHA，前后两轮漂移拒绝。计划入口可通过同一变量附加实时核验；结果仅为观察快照，不授权合并，不宣称原子绑定。
- `make verify.gitee.formal_worker.unit verify.gitee.formal_pr.unit`：现有签名事件接入和有界 PR 创建控制器的离线测试。
- `make gitee.pr.bot.merge GITEE_PR_NUMBER=<n> EXPECTED_HEAD=<完整 SHA> GITEE_EXPECTED_MAIN=<完整 SHA> GITEE_PR_BOT_TOKEN_FILE=<私有文件>`：
  参数化受保护 PR 合并入口（`--expected-source`、`--merge-method` 可选）。合并前从平台回读该 PR、源／目标分支引用与四项必需检查
  （`public_guard`／`merge_policy_gate`／`professional_quality_gate`／`frontend_release_gate`），要求**成功属于当前源提交**：
  等待中、失败、检查只绑定旧 SHA、源／目标分支漂移、fork PR、不可合并、无权限（401／403）一律拒绝，且不调用合并接口。
  合并走平台 PR 合并接口，保留分支保护，**不直接推送 main**；合并后由平台回读判定结果并输出回执，
  回执中的 head／源分支／目标分支／合并提交／`main_after` 全部取**观测值**（`target_sha` 是提交前已核验一致的
  目标快照，不是合并后观测），身份不符或不一致一律按失败报告，不宣称成功。
  令牌只从 owner-only 私有文件读取，不进入日志或仓库。
  该入口不产生集成资格，也不代替远端必需检查；合并授权按 `AGENTS.md` 最新所有者规则执行。
  四条强约束：
  - 每项必需检查取**最新一次运行**，顺序**只由严格递增的平台运行 `id` 证明**：任一运行缺 `id` 或出现重复 `id`
    即判顺序不可确定并拒绝，不退回接口数组顺序；等待中／失败的**重跑**不得被更早的成功掩盖；
    检查分页必须取完，未取完一律拒绝而不是据局部结果判断。
  - **平台回读是唯一的成功判据**，普通路径与超时恢复路径共用同一次校验：核验观测到的 PR head、源分支、
    目标分支、合并提交与远端 main；`state=closed` 本身不构成已合并，只有平台给出 `merged`，
    或 `closed` 且带合并标志，才继续判读；身份与预期不符（含平台实际合并了另一提交）按异常报告，
    **不得把预期 SHA 当作观测值写进回执**。
  - `--require-check` 只能**增补**，四项必需检查不可被缩减。
  - 合并请求超时或传输失败后先回读平台并分类（已合并／尚未合并／结果不确定），**禁止盲目重试**
    （第二次 `PUT` 可能重复合并）。回读到 `open` 只说明**回读时尚未合入**，不能据此断言该次超时请求最终未执行；
    分类为「已合并」也必须以观测到的合并提交与远端 main 一致为证。
  该接口在平台上**没有 `(head_sha, base_sha)` 的原子绑定**：本入口的身份核对是提交前快照，不宣称已解决并发漂移，
  回执固定 `atomic_sha_binding=false`；防漂移仍依赖分支保护与合并后核验。
- `make verify.gitee.pr_bot.unit`：上述参数化合并入口的离线边界测试（fake 平台）：通过路径、等待中／失败／旧 SHA／缺项检查、
  源与目标分支漂移、头部与目标 SHA 不匹配、fork、无权限拒绝、回读不一致、令牌文件权限与必需参数缺失；
  另含最新运行选择（等待中／失败的重跑、旧成功在后、最新成功覆盖旧等待，以及缺 `id`／全无 `id`／重复 `id`
  一律判顺序不可确定并阻止合并）、分页未取完与 `total_count` 缺口、
  合并超时的已合并／`open` 回读（仅证明回读时尚未合入，不重试）／不可读分类、
  普通与超时路径共用的回读身份核验（head 漂移、源分支不符、`closed` 无合并标志、回执取观测值）、
  必需检查不可缩减、以及回执声明无原子绑定。
- `make gitee.ci.server.update ... GITEE_FORMAL=1 GITEE_NODE_ARCHIVE=<reviewed archive>`：本会话授权的既有执行器正式静态门禁接入；仍要求精确 clean SHA、预演摘要、备份/恢复与原确认值。只写固定版本目录、固定 Node 22.17.0 二进制及既有服务配置；包白名单和归档/二进制双哈希强制校验。不启用数据库、部署或完整候选车道；本次普通前端车道仅消费已受管安装且匹配候选输入的离线依赖缓存，缺失/漂移拒绝。
- `make gitee.ci.pr.create EXPECTED_HEAD=<sha> GITEE_EXPECTED_MAIN=<sha> GITEE_PR_TOKEN_FILE=<owner-only private path> GITEE_SOURCE_BRANCH=<branch> GITEE_PR_TITLE=<title> GITEE_PR_BODY_FILE=<body file>`：默认只读预演；`APPLY=1` 为允许前缀的当前专题创建或复用同仓 main PR，要求 clean 精确候选、远端源/目标身份及受保护 main。使用独立集成令牌，不回退到 CI checks 令牌、不安装到 CI 主机；普通 PR 不要求本地完整 Quick。创建前持久化未决标记，不重复 POST；创建后独立回读，不合并、不部署。
- `make verify.gitee.formal_queue.unit`：正式任务持久队列、执行器适配与四项检查回传的离线生命周期测试；API 为受控 fake，不写平台。仅显式 formal-static 模式接入；不得将离线生命周期通过称为真实 PR 门禁验收。
- `make verify.gitee.formal_executor.unit`：普通 PR 静态门禁执行核心的离线测试，使用真实 bubblewrap 验证网络／凭据隔离、非零计数、取消、超时及结果失效。执行核心仅由显式 formal-static 模式接入；本入口不执行真实产品门禁、不安装服务、不新增部署资格。
- `make verify.gitee.gates.unit`：离线门禁选择和真实临时 Git 删除／重命名测试，无平台或业务数据写入。
- `make verify.gitee.checks.unit`：离线 Check Runs 回传、精确 SHA、断线恢复及凭据隔离测试；不写平台。回传模块默认关闭；新增凭据、安装范围及启用须完成当前独立 P4 授权与精确更新计划。
- `make verify.gitee.publication_gate.unit`：平台证据、时效、篡改及密钥替换的本地纯测试。
- `make verify.gitee.ci_only.unit` 是本地 P4 定向测试：使用临时 SQLite/Git 与现有 bubblewrap，
  不连接业务数据库、不写远端、不修改线上服务。`GITEE_CI_MODE=ci-only` 只允许受管配置显式启用；
  本批没有线上启用授权。
- `make gitee.ci.server.update EXPECTED_HEAD=<sha>`：既有 host/receiver/worker 的增量预演，默认只读。
  仅修改登记的四个代码文件、两个 env 的模式/交接项和 worker 写路径；不调用旧初始化安装入口。
  APPLY 要求 clean 精确 source、精确预演摘要和 `GITEE_UPDATE_CONFIRM=APPLY_REVIEWED_CI_INCREMENTAL_UPDATE`；
  此参数不代替公开范围、平台自动化隔离和精确线上方案批准。当前这些条件未齐备，不得实际执行。
  bubblewrap 固定软件包、受限 sandbox 探针、备份/恢复均属于同一入口；失败不得无沙箱降级。
- `make verify.gitee.ci_update.unit verify.gitee.publication_scope.unit`：本地临时目录/Git/SQLite 定向测试，
  线上服务/包管理调用由受控 fake 替代，不改业务数据。公开范围工具只读候选及已观测远端对象，不推送。
- 不使用固定历史 SHA 的 `gitee.pr.bot.merge` 处理新候选。Gitee PR 必须绑定源 HEAD／目标
  main，完成所需验证和独立审查后，按上方 CI 通过即合并规则在受保护 PR 流程合入；旧机器人不得用于新候选。
- `make gitee.pr.checks.fetch EXPECTED_HEAD=<完整 SHA> GITEE_EXPECTED_MAIN=<完整 SHA> GITEE_PR_BOT_TOKEN_FILE=<私有文件>`：
  **只读**解析一项候选的四项必需检查运行 ID，供 `gitee.pr.bot.merge` 的 `GITEE_PR_CHECK_RUNS` 使用。
  原因是平台 `GET /commits/{sha}/check-runs` 在本仓库对任何提交（含 `main`）都返回 `total_count=0`，
  列表端点无法充当“最新运行”证明；本入口改为读取可信 CI worker 自己登记的运行记录（固定远端程序、
  commit 作为参数传递、数据库只读打开），取每个检查名的**最新** ID，再逐个按 ID 向平台回读核验。
  运行必须由登记记录绑定到**同一提交**与**同一目标基线**：缺失、等待中、结论非成功、基线不符或
  记录缺失一律拒绝，不以空集或局部结果充当通过。它不写、不合并、不授予合并资格，也不能放宽
  合并入口自身的门禁；CI 主机凭据与既有 SSH 访问不变，不新增凭据文件。

操作步骤及恢复 GitHub 的边界见 [临时集成规程](gitee_temporary_integration_v1.md)。
现有 `pr.push`、`mirror.main.gitee` 和 `candidate.mirror.gitee` 保持原语义。

**Codex 自治执行授权清单 · v4.3（Replace v4.2）**

---

## 0. 定位（What Codex Is）

Codex 在本仓库中的角色被明确为：

> **自治执行体（Autonomous Engineering Executor）**

其职责是在 **独立分支（feature/* / fix/* / refactor/* / audit/* / release/* / codex/*）** 内，
围绕既定目标进行 **连续的代码迭代、验证与交互完善**，
并在 **不需要人工逐步授权** 的前提下，完成以下闭环：

* 实现改动
* 运行验证
* 修复失败
* 重复迭代
* 输出可审计结果

Codex **不是管理员**，也 **不是决策者**；
Codex 是一个 **被严格约束的工程执行单元**。

### 0.1 适用范围边界

本文仅适用于 **Codex 自治开发 / 自治验证 / PR 协作** 场景。

本文不适用于人工监督下的服务器生产部署。生产服务器从 `main`、tag
或冻结 commit 执行正式部署时，适用：

- `docs/ops/codex_production_assist_policy.md`
- `docs/ops/prod_command_policy.md`
- `docs/ops/production_deployment_runbook_v1.md`

生产协助模式下，Codex 只能做只读检查、执行生产策略允许的 Makefile target
和整理部署证据；不得修改仓库文件、提交代码或绕过 Makefile 操作生产数据。

---

## 1. 执行边界总原则（Hard Rules）

### 1.0 基线迭代阶段

`BASELINE_ITERATION_EXECUTION_POLICY=v1`

仓库已进入“有产品基线、有环境基线、有工具积累”的增量迭代阶段。自治执行不再被授权临时
拼装环境或替代入口。所有专题必须先盘点并消费仓库已登记的工作树、Make target、runtime
profile、数据库锁、端口、卷、fixture、测试与证据工具。

业务专题内禁止新增或派生 Compose project、数据库、端口、卷、凭据文件、runtime profile、
fixture 体系。已授权验收范围内，允许以P4责任补齐既有工具及local.dev包装的最小能力，
前提是复用登记环境、凭据和数据权威、保留硬门禁、绑定明确目标，对测试配置写入提供恢复及回读。
记录改动归属并定向验证，无需再次逐点申请授权；新环境或凭据权威仍需独立P4授权。

合成测试数据允许通过 `scripts/ci/personal_data_false_positives.json` 精确豁免，但登记必须绑定
规则、仓库相对路径、完整不可变 Git blob SHA、分类和合成夹具原因。禁止按 `tests/` 目录、通配符、
分支或“全部测试数据”豁免；文件内容变化后必须重新扫描、重新审核。

权威执行顺序与失败关闭规则以
`docs/ops/codex_workspace_execution_rules.md` 的“基线迭代执行锁”为准。

### 1.1 分支约束（最重要）

Codex **只能** 在以下分支类型中执行自治操作：

* `feature/*`
* `fix/*`
* `refactor/*`
* `audit/*`
* `release/*`
* `codex/*`

❌ 严禁：

* `main`
* `master`
* 任何已打 tag 的分支

若当前分支不符合要求，Codex **必须立即停止并报告**。

例外：若当前任务是人工监督的生产部署协助，并且没有任何仓库写入或 Git
写操作，则不按本文的自治分支限制处理，改按
`docs/ops/codex_production_assist_policy.md` 执行。

**分支判定规则：**

```bash
git branch --show-current
````

允许的分支正则：

```
^(feature|fix|refactor|audit|release|codex)\/.+
```

---

### 1.2 环境约束

* 仅允许 `ENV=dev` / `ENV=test`
* ❌ 禁止 `ENV=prod`
* ❌ 禁止使用 `.env.prod`
* ❌ 禁止设置或使用 `PROD_DANGER=1`

> `.env.prod` 文件允许存在（作为模板/参考），但禁止在 Codex 自治执行中启用 `ENV=prod` 或设置 `PROD_DANGER=1`。

说明：上述限制只约束 Codex 自治执行。生产协助模式允许 `ENV=prod`、
`ENV_FILE=.env.prod` 和经人工确认的 `PROD_DANGER=1`，但只能执行
`docs/ops/prod_command_policy.md` 允许的 Makefile target。

---

### 1.3 执行方式约束（Makefile 优先）

* **默认原则**：
  所有 **运行态 / 容器 / 数据库 / 服务状态变更 / 远端状态变更**
  **必须通过 Makefile target 执行**

* **明确例外**：
  §1.4 中列出的 **Safe Git 命令**
  👉 允许直接执行（不要求 Makefile 封装）

❌ 禁止直接调用（除非有对应 Makefile target）：

* `docker compose exec ... odoo -u`
* `psql`
* `gh pr edit / comment / ready / close`
* `curl` / `python` 直接写 GitHub API
* 任何绕过 Makefile 的远端状态修改

---

### 1.3.1 PR 内容更新通道（PR Update Channel）

Codex 被授权在 **合规分支内** 更新 PR 内容（包括代码与文本），但必须满足：

* ✅ **只能通过 Makefile target 执行**
* ❌ 禁止直接使用 `git push` / `gh` / GitHub API

允许的 PR 相关 Makefile targets：

* `make pr.create`

  * 创建 PR（或输出创建指引 / URL）

* `make pr.update`

  * 更新 PR 标题 / 描述 / labels / assignees / reviewers
  * 不允许修改 base 分支

* `make pr.status`

  * 查询 PR 状态（只读，允许任何分支）

* `make pr.push`

  * 只将当前分支 push 到 GitHub 权威远端 `origin`，用于 **更新 GitHub PR 的代码内容并保证 CI 可检出同一提交**；Gitee 只接收合并后 `main` 的快进镜像
  * 必须校验：

    * 分支名称通过 Git ref 格式校验且属于允许的分支类型
    * 非 prod 环境
    * 非 main / prod
    * 工作区干净（包括未跟踪文件）
    * 内容绑定的生成证据已经通过 `make ci.generated_evidence.preflight`
    * 推送前验证保持只读，不刷新或改写 tracked 文件
    * 选定 remote 必须精确指向 `https://github.com/lidefend/sce-backend-odoo.git`
    * 在 push 前通过只读可访问性预检；失败则零 push 退出

  * 禁止 `pr.push` 写入 `main`、Gitee 或其他远端；GitHub push 失败时必须以非零状态报告并给出 `make pr.push` 恢复命令
  * 生成证据需要更新时，必须先运行 `make ci.delivery.freeze.prepare`，审阅并提交差异，再冻结 HEAD 和运行一次 Quick；不得在 `pr.push` 中自动生成新候选
  * 禁止 force push，禁止自动删除远端分支

* `make pr.merge PR=<number> EXPECTED_HEAD=<full-40-char-sha>`

  * 仅在独立审查和显式合并授权后执行；
  * `EXPECTED_HEAD` 必须是已审查的完整 40 位小写 commit SHA；
  * 写入前必须实时核对 PR head，并向 GitHub CLI 传递
    `--match-head-commit <EXPECTED_HEAD>`；
  * head 漂移、参数无效或 CLI 不支持该门禁时必须零合并退出；
  * merge method 仍须由本轮明确授权，不得隐式启用 auto-merge 或绕过
    protected-main。

* `make pr.ready PR=<number> EXPECTED_HEAD=<full-40-char-sha>`

  * 仅用于把当前合规分支对应的 GitHub draft PR 转为 ready for review；
  * `EXPECTED_HEAD` 必须是已核验的完整 40 位小写 commit SHA；
  * 写入前必须实时核对 PR head 与 draft 状态，head 漂移、参数无效或 PR
    已非 draft 时必须零写入退出；
  * 不允许修改 PR base、代码、merge method、auto-merge 或 protected-main。

* `make candidate.required_checks.dispatch CANDIDATE_EXPECTED_SHA=<full-40-char-sha>`

  * 用于开放 PR 在后续修复提交完成后，显式冻结并验证唯一 exact-head 候选；
  * 普通 `make pr.push` 只更新远端分支，不再因每个提交自动启动完整候选 CI；
  * 入口必须校验本地、远端和开放 PR head 完全一致，并从 PR 读取完整 base SHA；
  * 入口只允许通过重新应用受管 `ci:candidate` 标签触发 PR exact-head 候选发布校验；
  * 标签事件必须沿用 PR diff 风险分类，并生成属于当前 PR head 的 `release_candidate_gate`；
  * 该入口服务“可发布”判定，不替代 `merge_policy_gate` 的“可合并”判定；
  * 新 head 在该入口成功完成前没有候选发布资格，因此不能被当作可发布头。

* `make ci.backend_test_suite.dispatch EXPECTED_HEAD=<full-40-char-sha>`

  * 只用于显式触发 `.github/workflows/backend_test_suite.yml` 的完整隔离后端套件；
  * 写入前必须验证合规分支、clean worktree、本地 HEAD、GitHub 远端分支 HEAD 和开放 PR HEAD 均与 `EXPECTED_HEAD` 完全一致；
  * 不提供模块或 test-tags 缩减参数，不得用局部测试冒充完整套件；
  * 工作流创建的 Compose project、数据库和卷由工作流按 run id 隔离并在结束时清理，不得复用 local.dev、acceptance 或生产环境。

> 说明：
> **PR 内容更新属于远端状态变更**，必须统一走 Makefile 封装流程，
> 以保证分支校验、环境校验与审计能力。

---

## 1.4 Git 执行边界（Safe Git Rules）

> ⚠️ 所有 Git 操作仍受 §1.1 分支约束
> **分支不合规时，任何 Git 写操作都必须停止**

---

### 1.4.1 允许的 Git 命令（Safe Git）

#### A) 只读类（允许在任何分支执行）

用于识别仓库状态、生成证据、定位问题：

* `git status`
* `git status -sb`
* `git diff`
* `git diff --stat`
* `git diff --name-only`
* `git diff --cached`
* `git diff --cached --name-only`
* `git log --oneline -n <N>`
* `git log --oneline --decorate -n <N>`
* `git show <commit>`
* `git show --name-only <commit>`
* `git branch --show-current`
* `git rev-parse HEAD`
* `git rev-parse --short HEAD`
* `git remote -v`
* `git ls-files`
* `git grep <pattern> [-- <path>]`
* `git fetch --prune origin`

> 说明：
> 上述命令 **不修改工作区、不影响远端**，
> 是 Codex 做工程自治与证据输出的必要能力。

---

#### B) 本地写入（仅限合规分支）

仅影响本地工作区，不影响远端：

* `git add <path>`
* `git add -A`
* `git restore <path>`
* `git restore --staged <path>`
* `git rm <path>`
* `git commit -m "<message>"`
* `git commit --amend -m "<message>"`
* `git commit --amend --no-edit`

> ⚠️ 说明：
> `--no-edit` 被明确允许，用于**修正提交内容而不改语义说明**，
> 是自治执行中的常见且安全操作。

---

#### C) 分支内同步（仅限合规分支）

* `git switch <allowed-branch>`
* `git checkout <allowed-branch>`
* `git switch -c <new-allowed-branch>`
* `git checkout -b <new-allowed-branch>`
* `git pull --ff-only origin <same-branch>`

#### D) 受管本地分支基线同步（唯一例外）

* `make workspace.branch.sync-main`

  对于尚未包含同步 target 的旧 linked worktree，允许由主工作树通过
  `WORKSPACE_BRANCH_SYNC_ROOT=<absolute-linked-worktree-path>` 调用；脚本必须
  验证两者共享同一 Git common directory。
  仅对 `docs/ops/iterations/delivery_context_switch_log_v1.md` 的纯追加冲突
  允许确定性合并；其余冲突一律 abort，禁止人工或脚本猜测业务内容。

  仅允许同步未发布、没有开放 PR 的合规本地分支。调用者必须提供当前
  分支、HEAD、旧基线和 `origin/main` 的完整 SHA，并提供精确确认短语。
  入口会创建本地恢复 bundle，拒绝 dirty、merge commit、远端同名分支、
  开放 PR、身份漂移和 Git writer；冲突时自动 abort 并恢复原 HEAD。该入口
  不执行 push 或 force push，并会核对责任 patch、变更路径和提交数量。

* `make workspace.branch.sync-main.extended`

  仅用于仓库所有者已明确批准、尚未发布且已经冻结的 13—64 提交候选。除普通
  `sync-main` 的全部精确身份、clean、无远端分支/PR、恢复 bundle 与冲突回滚
  门禁外，还必须具有当前工作树的有效 exact-head Quick receipt，并提供准确的
  `EXPECTED_COMMIT_COUNT` 和独立确认短语
  `REBASE_APPROVED_FROZEN_BRANCH_ON_EXACT_MAIN`。该入口仅可把已登记的生成证据
  冲突复位到新 main 版本，并在结果中明确标记证据失效；调用方必须随后执行生成
  证据刷新、重新冻结和新 HEAD 验证。重放后的提交数只允许减少不超过已确认冲突
  的纯生成证据提交数，且稳定路径集合与 patch identity 必须保持一致。其他冲突仍
  自动 abort，禁止借该入口放宽产品冲突处理。

---

### 1.4.2 明确禁止的 Git 命令（Hard Ban）

以下命令 **任何情况下都禁止**：

* ❌ `git push`
  （**除非** 通过 `make pr.push` / `make branch.cleanup.feature` 执行；退役路径
  `make workspace.worktree.cleanup CLEAN_WORKTREE_RETIREMENT_RECORD=...` 另有一项
  受限例外：只删除被证明已合入的主题的远端同名分支，且必须携带精确
  `--force-with-lease` lease）
* ❌ `git push --force / -f`
  （例外一：退役路径
  `make workspace.worktree.cleanup CLEAN_WORKTREE_RETIREMENT_RECORD=...` 对已证明
  合入主题的远端同名分支所做的精确 `--force-with-lease=refs/heads/<branch>:<sha>`
  删除，见上一条受限例外；例外二：获得仓库所有者逐次明确授权后，通过
  `make main.cutover.controlled` 执行双远端 `main` 历史切换。该入口必须使用完整
  SHA 精确 lease、外部不可变恢复 bundle、配对完成或回退、保护规则恢复及
  候选发布资格复验；禁止直接调用底层 push。）
* ❌ `git reset --hard`
* ❌ `git rebase`
* ❌ `git cherry-pick`
* ❌ `git merge`
* ❌ `git tag`
* ❌ `git branch -d / -D`
  （**除非** 通过 `make branch.cleanup.feature` 执行）
* ❌ 裸用 `git worktree`
  （创建只能通过 `make workspace.worktree.create`，清理只能通过
  `make workspace.worktree.cleanup`；两个入口均执行路径、分支与状态校验，创建入口
  另要求精确 40 位基线 SHA。创建入口与 receipt／detach 清理路径为本地操作；退役
  路径除本地操作外，只按上一条受限例外处理远端同名分支）
* ❌ `git config`
* ❌ `git clean -fdx`

`git rebase` 的唯一实现级例外是受上述 Make target 调用的
`scripts/ops/safe_branch_sync_main.py`；用户和 Codex 均不得直接执行底层命令。

> ⚠️ 所有 **远端状态变更**
> 必须通过 Makefile 封装流程完成。

受控并行工作区创建默认仅执行预检。实际创建必须显式提供：

```bash
make workspace.worktree.create \
  CREATE_WORKTREE=/absolute/sibling/path \
  CREATE_WORKTREE_BRANCH=feature/example \
  CREATE_WORKTREE_BASE=<full-40-character-sha> \
  APPLY=1 \
  CREATE_WORKTREE_CONFIRM=CREATE_GOVERNED_WORKTREE
```

清理交付工作树前，先归档清单中四类证据并验证归档副本可读：

```bash
make workspace.evidence.archive \
  CANDIDATE_WORKTREE=/absolute/linked/path \
  EVIDENCE_ARCHIVE_MANIFEST=/absolute/linked/path/artifacts/topic/archive-manifest.json \
  APPLY=1 \
  EVIDENCE_ARCHIVE_CONFIRM=ARCHIVE_DELIVERY_EVIDENCE
```

清单使用 `schemaVersion=1`，绑定精确 `candidateHead`，并分别列出 `summary`、
`identity`、`screenshot`、`review` 四种角色的工作树内相对文件。摘要、身份和复核文档必须
包含该精确 HEAD；身份文件必须为 JSON，截图必须是内容签名有效的 PNG/JPEG/WebP，不能用任意文件
冒充所需证据。归档 receipt 必须位于
工作树之外，并通过 `CLEAN_WORKTREE_EVIDENCE_RECEIPT` 传给清理入口。

目标必须是主仓库同级且以 `<repository-name>-` 开头的新目录；目标分支必须符合
自治写入分支规则且尚不存在；基线必须是本地或 `origin` 分支可达的既有提交。

仍需保留分支成果但不再需要常驻目录的干净工作树，可按精确 HEAD 解除挂载：

```bash
make workspace.worktree.cleanup \
  CLEAN_WORKTREE=/absolute/linked/path \
  CLEAN_WORKTREE_KEEP_BRANCH=1 \
  CLEAN_WORKTREE_EXPECTED_HEAD=<full-40-character-sha> \
  APPLY=1 \
  CLEAN_WORKTREE_CONFIRM=DETACH_VERIFIED_WORKTREE_KEEP_BRANCH
```

该模式只删除工作树目录并验证本地分支引用保持不变，因此允许未合并分支和受保护的
`release/main` 分支；目标为主工作树、状态非干净或 SHA 漂移时均拒绝执行。

已合入但**从未归档交付证据**的历史工作树没有可迁移证据，只能在受审治理记录与外部恢复
bundle 同时就位时整体清理：

```bash
make workspace.worktree.cleanup \
  CLEAN_WORKTREE=/absolute/linked/path \
  CLEAN_WORKTREE_RETIREMENT_RECORD=/absolute/repo/docs/ops/iterations/workspace_worktree_legacy_retirement_v1.json \
  CLEAN_WORKTREE_RECOVERY_BUNDLE=/absolute/evidence/workspace-archives/<date>/legacy-worktree-retirement/<branch>.bundle \
  APPLY=1 \
  CLEAN_WORKTREE_CONFIRM=RETIRE_SQUASH_INTEGRATED_WORKTREE_WITHOUT_ARCHIVED_EVIDENCE
```

* squash 同树承接是唯一准入证明：必须有已合并 PR 的 `headRefOid` 精确等于工作树 HEAD，
  其 merge commit 位于 `origin/main`、是**单亲**提交，且该提交的树与工作树 HEAD 的树
  逐字节一致；任一条件不成立即拒绝（`gh` 不可用或查询失败按无证明处理）。
* 治理记录必须是仓库内**被 Git 跟踪**的文件（因此必须随候选评审合入），逐条声明
  `path`／`branch`／`head`／`evidenceStatus=absent`／原因／`mergedPr`（严格整数，浮点、
  字符串与布尔一律拒绝）／`mergeCommit`／`tree`／恢复 bundle 路径与 SHA-256；入口会重读
  记录并重算 bundle 哈希，校验其覆盖该 HEAD 且通过 `git bundle verify`。
* 记录内容以**提交在 `HEAD` 的 blob 为准**：工作区或索引里的未提交改动一律被忽略
  （既不能扩大也不能缩小一次退役）；仅 staged 而未提交的新记录文件一律拒绝。
* 退役是**整体清理**：入口通过一次 `git ls-remote` 询问真实远端状态，远端查询失败按
  拒绝处理；远端分支已漂移到非记录 HEAD 时拒绝；与记录 HEAD 完全一致时以精确
  `--force-with-lease=refs/heads/<branch>:<sha>` lease 删除，lease 过期即拒绝。远端
  不存在该分支时只做本地清理。
* 全部校验先于任何破坏性动作完成；其后按固定顺序执行破坏性步骤：远端 lease 删除 →
  移除工作树 → 删除本地分支。因此远端删除可能先于某个本地步骤失败而生效；此时入口在
  拒绝信息中列出已完成的破坏性步骤。重跑会完整重做全部校验，且不会发出第二次远端删除
  （远端已不存在即跳过）。
* 退役被拒绝时的恢复：远端漂移、远端或 `gh` 不可读、lease 过期都属于硬拒绝，本入口不
  自动放宽；恢复远端可读性后重跑，或对残留引用使用 `make branch.cleanup.feature`。
* 无归档证据必须由记录显式披露；禁止用任意文件、重跑或补造文件替代原候选证据。

> 解释：
> PR 的代码更新 **必须通过 `make pr.push`**，
> 以便统一注入分支校验、GitHub/Gitee 双远端同步、远端保护与审计日志。

---

### 1.5 Git 与分支绑定规则（Critical）

* Codex 执行任何 **Git 写操作** 前，必须确认：

  * 当前分支 ∈ {feature/*, fix/*, refactor/*, audit/*, release/*, codex/*}

* 若检测到以下情况之一：

  * `main`
  * `master`
  * HEAD detached

  Codex **必须立即停止**，不得执行任何 Git 写操作。

* 对 `main` 的同步：

  * 仅允许通过：

    ```bash
    make main.sync
    ```

---

## 2. Codex 的自治生命周期

在独立分支内，Codex 被授权执行完整自治循环：

```
理解目标
↓
修改代码
↓
选择执行模式（fast / gate）
↓
执行验证
↓
失败 → 定位 → 修复
↓
再次验证
↓
直到通过或触发停机条件
```

---

## 3. 执行模式（Execution Modes）

### 3.1 MODE=fast（默认 · 连续迭代模式）

#### 适用范围

* UI / Portal 交互调优
* Python 逻辑修正
* Resolver / 状态机演进
* Contract 输出结构优化
* 文档 / 脚本 / 工具链改进

#### 允许的 Make Targets

（保持你现有清单，完全不改）

---

### 3.2 MODE=gate（自治验收模式）

Codex **被授权自行进入 gate 模式**。

（保持你现有清单，完全不改）

---

## 4. 模块升级授权（升级不是默认）

（保持你现有规则，完全不改）

---

## 5. 失败即许可（Failure Is Allowed）

Gate / Smoke / Snapshot 失败 **允许发生**。
Codex 的责任是 **定位 → 修复 → 重试**。

---

## 5.1 System-bound Verification（强制）

**任何由 Codex 产生的代码改动，必须同时提供 system-bound verification。**

不接受：

* 真实用户登录
* 浏览器点击验证
* 人工 token

---

## 6. 唯一需要人工中断的情况

仅限以下情形：

1. 需要直接改动 `main`
2. 需要新增或修改 prod 策略
3. 不可逆 DB 操作
4. 连续 ≥3 次 gate.full 失败且原因不收敛
5. 引入全新模块或外部依赖

---

## 6.0 Codex Branch Bootstrap Rule

* `codex/*` 分支首次推送必须人工完成
* 远端分支存在后，Codex 接管自治流程

---

## 6.1 Branch-local autonomy（All allowed branches）

在合规分支（`feature/*` `fix/*` `refactor/*` `audit/*` `release/*` `codex/*`）内，
仅允许通过 Makefile 执行以下自治闭环能力：

* `make codex.preflight`
* `make codex.run FLOW=fast|snapshot|gate|pr|merge|cleanup|rollback`
* `make codex.pr`
* `make pr.create`
* `make pr.update`
* `make pr.status`
* `make pr.push`
* `make codex.sync-main`
* `make branch.cleanup.feature`

  * 单分支退役入口，`CLEAN_BRANCH_REMOTE` 选择远端（默认 `origin`）。
  * **没有 force 开关**：`CLEANUP_FORCE` 已删除，任何绕过核验的尝试直接拒绝。
  * 必须提供 `EXPECTED_BRANCH_SHA`（被审查分支的完整 SHA）与
    `EXPECTED_MAIN_SHA`（所选远端实时 `main` 的完整 SHA）；`APPLY=1` 还须
    `CLEAN_BRANCH_CONFIRM=DELETE_EXACT_REVIEWED_BRANCH`。
  * 拒绝删除 `main`/`master`/`release/*`、被工作树检出的分支、当前检出分支，
    以及不包含于所选远端 `main` 且（非 `origin` 时）无法用合并 PR 证明的分支。
  * 远端读取失败一律按拒绝处理，不得当作“分支不存在”；远端删除使用
    `--force-with-lease` 绑定预期 SHA，本地删除使用 `git update-ref -d <sha>`。
* `make branch.retire.historical`

  * 仅按已审查的精确 JSON manifest 处理历史本地／远端分支引用；本地和远端
    SHA 分开核验，远端不存在必须显式声明。
  * `HISTORICAL_RETIREMENT_REMOTE` 选择判定与删除所在远端（默认 `origin`，
    Gitee 镜像用 `gitee-mirror`）；`HISTORICAL_RETIREMENT_EXPECTED_MAIN` 必填，
    必须等于该远端实时 `main` 的完整 SHA。远端不可读、`main` 漂移、条目 tip
    本地缺对象导致包含关系无法证明，均在上游或逐项拒绝，绝不按“分支不存在”处理。
  * 非 `origin` 远端必须显式传 `HISTORICAL_RETIREMENT_OPEN_PR_PROVIDER=none`，
    报告据此记录 `open_pr_check=none`，不得暗示已完成平台开放 PR 检查。
  * `HISTORICAL_RETIREMENT_EMIT_MANIFEST` / `HISTORICAL_RETIREMENT_EMIT_INVENTORY`
    为只读输出：按实时 `main` 生成退役 manifest 与完整分支清单（分支名、远端／
    本地 SHA、包含关系、工作树占用、运行载体引用），不删除任何引用。
  * manifest 只接纳 `feature|fix|refactor|audit|codex` 前缀且包含于实时 `main`
    的分支；`main`、`master`、`release/*` 以及仅存在于本地、未包含于 `main`
    的分支结构性排除。条目可声明 `local.state=absent`（Gitee 独有引用），
    此时只退役远端引用。
  * 载体扫描覆盖 `scripts`、`config`、`deploy`、`make`、`.agent`、`.github`；
    命中运行载体引用的分支跳过。
  * 默认只读预演；`PREPARE_BUNDLE=1` 仅生成并校验恢复 bundle，不删除引用。
  * 实际退役必须同时提供 manifest 的 SHA-256、精确确认短语
    `RETIRE_APPROVED_HISTORICAL_REFERENCES` 和 `APPLY=1`；SHA 漂移、被工作树检出、
    存在开放 PR 或证据不完整的条目逐项跳过。
  * 远端删除使用 manifest 中逐项声明的远端身份，不得按同名自动扩展；任何删除
    前必须已有可读且覆盖全部本次可执行引用的恢复 bundle。
* `make main.cutover.controlled`

  * 仅用于仓库所有者已明确授权的双远端 `main` 非快进历史治理；
  * 默认 dry-run，`APPLY=1` 仍须精确确认字符串；
  * 必须提供两个 live `main` 的完整旧 SHA、目标 SHA/TREE、私有权限 Gitee
    管理 token 文件、仓库外恢复目录和证据目录；
  * 不属于生产部署授权，不得连接数据库、filestore 或生产运行环境。
* `make candidate.required_checks.dispatch CANDIDATE_EXPECTED_SHA=<full-sha>`

  * 仅为当前合规候选分支的精确远端 SHA 派发既有候选发布工作流；
  * 工作区、当前 HEAD 或远端分支任一漂移时零派发退出；
  * 不修改 `main`、保护规则、产品数据或生产环境。
* `make candidate.mirror.gitee CANDIDATE_EXPECTED_SHA=<full-sha>`

  * 仅把 GitHub 已存在且与本地 HEAD 完全一致的合规候选分支普通快进到
    Gitee 同名候选分支；
  * 禁止非快进、禁止写 `main`、禁止从 Gitee 反向覆盖 GitHub。

> 若某 target 尚未实现，**必须先补 Makefile 封装**，
> Codex 不得绕过直接调用底层命令。

---

## 7. 产出与证据（必须）

证据按 `codex_workspace_execution_rules.md` 的阶段分级：日常开发只维护一份批次记录（目的、HEAD/dirty范围、定向结果、必要观察）；批次产品复核集中一次，修复只补受影响部分；以下完整产物清单仅在最终交付时适用。高风险写入仍执行对象身份、权威回读与恢复/清理要求，不能借轻量记录跳过受管门禁。

最终交付时，Codex **必须产出**：

* 日志摘要
* Gate / Smoke 结果
* Contract snapshot diff（如有）
* System-bound verification 结果
* 最终状态说明（通过 / 阻塞）

推荐目录结构：

```
artifacts/codex/<branch>/<timestamp>/
```
文档形成规则
目录结构一致：同名文件 .md + .en.md 成对出现（或 README.zh.md/README.en.md 成对出现，但全仓统一一种）

链接一致：中文文档里链接到英文同位置的英文文档；英文文档同理

术语表一致：建立 docs/TERMS.zh.md 与 docs/TERMS.en.md（可放 Phase A 或 C），约束 intent/scene/reason_code 的翻译固定用词（避免“contract”一会叫契约一会叫合约）
---

## 8. 一句话执行准则（给 Codex 用）

> **只在独立分支；
> 默认 fast；
> 升级需声明；
> PR 更新走 Makefile；
> 验证必须自证；
> gate 可自治；
> 失败可重试；
> 越权即停。**

---

```
```

## Published Gitee candidate synchronization (2026-09-25)

For the owner-authorized integration closeout, `make workspace.branch.sync-gitee-published`
appends exact live main to an already published candidate without rewriting its history.
It binds `SYNC_ROOT`, `EXPECTED_BRANCH`, full `EXPECTED_HEAD`, `GITEE_EXPECTED_MAIN`,
and optional `GITEE_EXPECTED_SOURCE` when unpublished local append commits exist.
Default is read-only (fetch only). Apply requires
`GITEE_SYNC_CONFIRM=APPEND_EXACT_MAIN_TO_PUBLISHED_CANDIDATE`.
The entry verifies a clean root, canonical Gitee remote, live branch/main SHA, published
ancestry and a verified recovery bundle. Conflicts abort to the original candidate.
It never pushes or merges main; publication still uses `pr.push.gitee`, and all required
CI must pass on the new source and current target. Raw merge/rebase/cherry-pick remain
prohibited outside governed tools.
