````md
# Codex Execution Allowlist (Autonomous Mode)

`CANONICAL_ALLOWED_WRITE_BRANCH_REGEX=^(feature|fix|refactor|audit|release|codex)/.+`

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

* `make pr.open`

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
    * 选定 remote 必须精确指向 `https://github.com/lidefend/sce-backend-odoo.git`
    * 在 push 前通过只读可访问性预检；失败则零 push 退出

  * 禁止 `pr.push` 写入 `main`、Gitee 或其他远端；GitHub push 失败时必须以非零状态报告并给出 `make pr.push` 恢复命令
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

---

### 1.4.2 明确禁止的 Git 命令（Hard Ban）

以下命令 **任何情况下都禁止**：

* ❌ `git push`
  （**除非** 通过 `make pr.push` / `make branch.cleanup.feature` 执行）
* ❌ `git push --force / -f`
  （唯一例外：获得仓库所有者逐次明确授权后，通过
  `make main.cutover.controlled` 执行双远端 `main` 历史切换。该入口必须使用完整
  SHA 精确 lease、外部不可变恢复 bundle、配对完成或回退、保护规则恢复及
  required checks 复验；禁止直接调用底层 push。）
* ❌ `git reset --hard`
* ❌ `git rebase`
* ❌ `git cherry-pick`
* ❌ `git merge`
* ❌ `git tag`
* ❌ `git branch -d / -D`
  （**除非** 通过 `make branch.cleanup.feature` 执行）
* ❌ 裸用 `git worktree`
  （创建只能通过 `make workspace.worktree.create`，清理只能通过
  `make workspace.worktree.cleanup`；两个入口均为本地操作并执行路径、分支、
  精确基线和状态校验）
* ❌ `git config`
* ❌ `git clean -fdx`

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

已注销且原路径不存在的部分清理残留，只能通过同一治理入口按完整 SHA 恢复：

```bash
make workspace.worktree.cleanup \
  CLEAN_WORKTREE=/absolute/missing/path \
  CLEAN_WORKTREE_BRANCH=fix/example \
  CLEAN_WORKTREE_EXPECTED_HEAD=<full-40-character-sha> \
  APPLY=1 \
  CLEAN_WORKTREE_CONFIRM=DELETE_VERIFIED_ORPHAN_BRANCH
```

该模式只删除经 `origin/main` 吸收证明验证的本地孤立分支引用，不修改远端。

不再被任何工作树占用的已合并本地分支，可通过独立入口清理：

```bash
make workspace.branch.cleanup.local \
  LOCAL_CLEAN_BRANCH=fix/example \
  LOCAL_CLEAN_EXPECTED_HEAD=<full-40-character-sha> \
  APPLY=1 \
  LOCAL_CLEAN_CONFIRM=DELETE_VERIFIED_LOCAL_BRANCH
```

该入口同样只更新本地引用；分支仍被工作树占用、SHA 漂移或缺少主线吸收证据时均拒绝执行。

大量 squash 合并残留可用批量入口一次刷新并先整批验证：

```bash
make workspace.branch.cleanup.local.batch \
  LOCAL_CLEAN_SPECS='fix/one=<full-sha>,feature/two=<full-sha>' \
  APPLY=1 \
  LOCAL_CLEAN_CONFIRM=DELETE_VERIFIED_LOCAL_BRANCH
```

批量模式在删除任何引用前验证全部分支；任一分支仍被占用、SHA 漂移或未被主线吸收时整体拒绝。

已合并 PR 的早期本地分支可通过精确 supersession 入口清理：

```bash
make workspace.branch.cleanup.local.superseded-pr \
  SUPERSEDED_LOCAL_BRANCH=codex/example \
  SUPERSEDED_LOCAL_EXPECTED_HEAD=<full-local-sha> \
  SUPERSEDING_MERGED_PR=<number> \
  SUPERSEDING_PR_EXPECTED_HEAD=<full-pr-head-sha> \
  APPLY=1 \
  SUPERSEDED_LOCAL_CONFIRM=DELETE_VERIFIED_SUPERSEDED_LOCAL_BRANCH
```

该入口实时读取 GitHub PR 的合并状态、`main` base、精确 head 和 merge commit，
确认 merge commit 已进入 `origin/main`，并证明本地分支 tip 是该 PR head 的祖先后，
才以精确旧 SHA 删除本地引用。它不删除或修改任何远端引用。

目标必须是主仓库同级且以 `<repository-name>-` 开头的新目录；目标分支必须符合
自治写入分支规则且尚不存在；基线必须是本地或 `origin` 分支可达的既有提交。

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
* `make pr.open`
* `make pr.update`
* `make pr.status`
* `make pr.push`
* `make codex.sync-main`
* `make branch.cleanup.feature`
* `make main.cutover.controlled`

  * 仅用于仓库所有者已明确授权的双远端 `main` 非快进历史治理；
  * 默认 dry-run，`APPLY=1` 仍须精确确认字符串；
  * 必须提供两个 live `main` 的完整旧 SHA、目标 SHA/TREE、私有权限 Gitee
    管理 token 文件、仓库外恢复目录和证据目录；
  * 不属于生产部署授权，不得连接数据库、filestore 或生产运行环境。
* `make candidate.required_checks.dispatch CANDIDATE_EXPECTED_SHA=<full-sha>`

  * 仅为当前合规候选分支的精确远端 SHA 派发既有 required-check 工作流；
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

一次自治周期内，Codex **必须产出**：

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
