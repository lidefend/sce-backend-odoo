````md
# Codex Execution Allowlist (Autonomous Mode)

`CANONICAL_ALLOWED_WRITE_BRANCH_REGEX=^(feature|fix|refactor|audit|release|codex)/.+`

## 临时 Gitee 主线集成车道（2026-09-23）

本次续跑所有者已明确要求直接执行现有 CI 线上更新及 CI-only 真实事件验收。用户截图和登录后的页面
已确认 WebHook 2106026、平台镜像为空、Gitee Go 未开通；历史公开范围及同组客户标识授权沿用本会话。
该授权取代本节下文的“本批没有线上启用授权／条件未齐备”历史状态，但不取代精确计划、备份、隔离、
沙箱与发布检查。正式合并、历史 main 补齐和产品部署仍不授权。
`make gitee.ci.mirror.isolate GITEE_ISOLATION_CONFIRM=ISOLATE_EXISTING_REVERSE_MIRROR` 仅停用既有
gitee-to-github-mirror.timer/service 并回读 inactive/disabled/PID=0；不改旧 runner，不自动恢复镜像。
服务历史 failed 但 MainPID=0 同样视为停止，timer 必须 inactive/disabled。
`gitee.ci.sandbox.profile.install` 仅在无现有 bwrap profile 时安装已审上游 v4.0.3 配置；
`gitee.ci.sandbox.probe` 使用现有 updater 的同服务约束探针验证网络/凭据隔离。不修改全局 sysctl，
不使用 unconfined 通配豁免。配置来源及内容 hash 见批次记录；此为真实环境故障的限定修复。

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
  的全部提交与变更路径，并明确 dirty 内容未包含。实际 APPLY 仍要求 clean，且在平台自动化证据
  未核验期间由工具硬拒绝；没有环境布尔开关可放行。普通 integration 路径约束不变。
- `make verify.gitee.ci_only.unit` 是本地 P4 定向测试：使用临时 SQLite/Git 与现有 bubblewrap，
  不连接业务数据库、不写远端、不修改线上服务。`GITEE_CI_MODE=ci-only` 只允许受管配置显式启用；
  本批没有线上启用授权。
- `make gitee.ci.server.update EXPECTED_HEAD=<sha>`：既有 host/receiver/worker 的增量预演，默认只读。
  仅修改登记的三个代码文件、两个 env 的模式/交接项和 worker 写路径；不调用旧初始化安装入口。
  APPLY 要求 clean 精确 source、精确预演摘要和 `GITEE_UPDATE_CONFIRM=APPLY_REVIEWED_CI_INCREMENTAL_UPDATE`；
  此参数不代替公开范围、平台自动化隔离和精确线上方案批准。当前这些条件未齐备，不得实际执行。
  bubblewrap 固定软件包、受限 sandbox 探针、备份/恢复均属于同一入口；失败不得无沙箱降级。
- `make verify.gitee.ci_update.unit verify.gitee.publication_scope.unit`：本地临时目录/Git/SQLite 定向测试，
  线上服务/包管理调用由受控 fake 替代，不改业务数据。公开范围工具只读候选及已观测远端对象，不推送。
- 不使用固定历史 SHA 的 `gitee.pr.bot.merge` 处理新候选。Gitee PR 必须绑定源 HEAD／目标
  main，完成所需验证和独立审查后，由所有者批准并在受保护 PR 流程合入；暂不提供自动合并入口。

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
* `make branch.retire.historical`

  * 仅按已审查的精确 JSON manifest 处理历史本地／远端分支引用；本地和远端
    SHA 分开核验，远端不存在必须显式声明。
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
