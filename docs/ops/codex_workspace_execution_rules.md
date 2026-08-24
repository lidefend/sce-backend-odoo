# Codex Workspace Execution Rules (Hard Guard)

`CANONICAL_ALLOWED_WRITE_BRANCH_REGEX=^(feature|fix|refactor|audit|release|codex)/.+`

## 目标
- 防止 Codex 在错误仓库、错误路径、错误分支下执行改动。
- 将“执行前校验”变成强制步骤，而不是可选习惯。

## 适用范围
- 本仓库内所有 Codex 代码改动、文档改动、开发验证执行。
- 不适用于人工监督下的服务器生产部署协助；该场景适用
  `docs/ops/codex_production_assist_policy.md`。
- 生产协助模式下，Codex 不得修改仓库文件、不得执行 Git 写操作，只能执行只读检查和
  `docs/ops/prod_command_policy.md` 允许的 Makefile target。

## 基线迭代执行锁（Hard Lock）

`BASELINE_ITERATION_EXECUTION_POLICY=v1`

### 阶段事实

- 仓库已经具备正式产品基线、隔离工作树入口、分层门禁、模块增量升级、固定 acceptance
  profile、角色 fixture、release snapshot、浏览器审计、证据指纹和 PR 发布入口。
- 默认动作是复用这些能力，不是重新建设环境或重新发明脚本。
- “任务需要验证”不构成创建新 Compose project、数据库、端口、卷、凭据或 profile 的授权。

### 每个专题的唯一执行顺序

1. **盘点已有能力（只读、零副作用）**
   - 确认主线 SHA、候选工作树、分支、dirty 状态及并行写入者。
   - 从仓库 Makefile、runtime profile 和既有证据中解析权威测试、升级、fixture、运行与清理入口。
   - 明确将复用的 project、database/dbfilter、ports、volumes、credential authority、fixture 和 evidence tool。
   - 若入口或身份无法解析，立即停止；禁止凭经验手工补齐环境变量。

2. **冻结候选与边界**
   - 声明 `Formal Product Layer / Layer Target / Module / Why Here / Why Not Elsewhere / Blast Radius`。
   - 同一候选工作树只能有一个写入者。
   - 冻结完整候选指纹：必须覆盖 tracked diff、staged diff、untracked 路径和内容；仅 `git diff`
     哈希不完整。
   - 范围 manifest 必须同时覆盖 dirty 态和提交后的 `baseline_sha..HEAD`，不得在 clean CI 中退化为空。

3. **按风险逐级验证**
   - Quick：语法、lint/type、纯单元、范围/架构/契约守卫、生成报告一致性。
   - Targeted：通过已登记入口执行受影响模块、权限、迁移或业务专项测试；测试必须真实收集。
   - 日常开发只能使用 `local.dev.*`、`sc_dev_demo`、18081 和对应 targeted tests；其报告是迭代
     证据，不得标记为 release snapshot、发布候选或最终验收证据，也不得触发 `make pr.push`。
   - Full Release：仅在产品结果已确定且明确进入最终验收后，消费正式隔离 profile 完成增量
     升级、fixture、release snapshot、生产构建、浏览器用户旅程和证据包。本地入口必须使用
     `CONFIRM_FRONTEND_RELEASE_AUDIT=RUN_FROZEN_FRONTEND_RELEASE_AUDIT make verify.frontend.release.local`；
     该确认不得写入日常脚本、别名或默认环境。
   - 日常开发与 Full Release 是互斥证据通道。发布审计一旦开始，候选必须冻结；若发现需要修改
     产品代码，立即终止发布审计并回到 `local.dev.*`，不得在同一轮中边修边生成发布证据。
   - 任何 `0 tests`、未收集测试、错误标签或错误模块都按失败处理，禁止以退出码 0 计通过。
   - 合成测试数据仅允许通过个人数据误报登记表做精确豁免；登记必须绑定规则、路径、完整 Git
     blob SHA、分类与合成夹具原因。禁止目录级、通配符或测试树整体豁免，内容变化自动失效。

4. **正式运行态串行**
   - 模块升级、fixture reset、正式 acceptance 数据库写入和业务写路径必须串行。
   - 只允许使用 profile 冻结的 project、database/dbfilter、ports、volumes 和 credential authority。
   - 禁止直接调用 `docker compose`、底层 up/down、Odoo CLI 或手工导入容器凭据替代正式 Make 入口。
   - 禁止在业务专题中新增 acceptance profile；只有明确授权的 P4 环境专题可以修改环境底座。

5. **验收与发布**
   - 验收先验证 normalized contract/权限/状态事实，再执行六态和真实用户任务闭环。
   - 已知静态、后端、身份或 normalized-contract 阻断未关闭时，禁止重复跑完整浏览器验收。
   - 每份报告绑定 exact HEAD、完整候选指纹、数据库、公司、角色、action/menu、URL、视口与证据哈希。
   - 独立复核通过后，刷新并审核生成报告；发布只能走 `make pr.push`，Ready/merge 继续要求精确 SHA
     和人工授权。

### 以产品结果组织工作树（Hard Lock）

工作树、运行环境与最终验收围绕一个可独立验收的 PFL 产品结果组织。P0、P1、P2、P3、P4
仍是强制责任标签和代码归属边界，但责任层不同不构成拆工作树、拆分支、拆 PR 或重复运行环境
的理由。同一产品目标中允许按责任层形成多个清晰提交，并在一次集成用户旅程中验收。

只有下列五项同时成立时，才允许建立独立工作树：

1. 候选可以独立合并并独立产生用户或平台价值；
2. 候选不依赖另一个专题才能完成验收；
3. 候选不修改另一专题的同一批文件；
4. 候选不争用同一个受控运行环境或共享写入数据；
5. 候选失败时能够独立回滚，不破坏另一专题的可验收结果。

缺少任一条件时，继续使用现有产品交付工作树；通过提交边界、范围清单、专项门禁和独立复核
维持 P0/P1 责任分离。禁止因发现一个新的责任层问题就自动派生 `-p0-*`、`-p1-*` 子工作树。

同时活跃工作树硬上限为两个：

- 一个产品交付工作树；
- 一个真正独立、满足上述五项条件的平台或环境专题工作树。

超过两个时必须暂停创建，先通过治理入口完成、冻结或清理现有工作树。只读审查者绑定同一
冻结指纹，不因审查身份另建候选工作树。产品交付完成后再单独执行无业务改动的工作树清理。

### 禁止混用的身份域

- `dev`、`test`、`acceptance`、`prod-sim` 是不同身份域，凭据、project、database、volume 与端口不得
  交叉注入。
- acceptance 凭据不得注入 dev/test project；test 数据库不得在 acceptance project 中临时创建；
  dev 数据库不得被专项测试入口重建。
- 新 project/network/database 的创建必须来自已登记入口及明确任务授权。普通 P0-P3/PFL 专题无此授权。

### 失败分流

- 入口或身份失败：归 P4，只修治理入口；业务候选保持冻结。
- normalized contract/通用装配失败：归 P0，禁止在 P1/PFL 写特判。
- 行业模型、字段、状态、权限能力失败：归 P1，禁止进入通用前端。
- 验收定位器或证据采集失败：只修验收工具，不改变产品合同以迁就脚本。
- 每次只修当前责任层；新发现但不阻断本专题的数据安全/权限越权问题除外，其余登记待办。

## 强制执行步骤（每次开始改动前）
1. **工作目录校验**
   - 必须执行：`pwd`
   - 必须执行：`git rev-parse --show-toplevel`
   - 结果必须指向当前仓库根目录。

2. **分支校验**
   - 必须执行：`git branch --show-current`
   - 分支必须匹配 allowlist：`feature/*`、`fix/*`、`refactor/*`、`audit/*`、`release/*`、`codex/*`。
   - 若不匹配，立即停止执行。
   - 例外：人工监督的生产部署协助允许 `main`、tag 或冻结 commit，但仅限只读检查和
     生产策略允许的 Makefile target，禁止任何写文件或 Git 写操作。

3. **仓库标识校验**
   - 必须执行：`git status --short`
   - 必须执行：`git rev-parse --short HEAD`
   - 在执行日志中记录当前分支与短 SHA，作为本轮上下文锚点。

4. **目标模块存在性校验**
   - 变更前必须确认目标模块路径存在（例如 `addons/smart_core`、`frontend/apps/web`）。
   - 若路径不存在，立即停止执行并报告“疑似错误仓库/路径”。

## 执行中防漂移规则
- 每次大批量 `apply_patch` 前，必须再次执行：
  - `git branch --show-current`
  - `git rev-parse --show-toplevel`
- 若与本轮起始锚点不一致，立即停止并回报。

## 并行工作区

- 只有满足“以产品结果组织工作树”五项拆分条件的并行任务，才使用独立工作区和独立合规
  分支；同一 PFL 内的 P0/P1 修改继续留在同一产品工作树，不得机械拆分。
- 不得在同一目录切换多个任务分支；同一候选工作树仍只能有一个写入者。
- 禁止直接执行 `git worktree`；创建必须使用 `make workspace.worktree.create`，
  清理必须使用 `make workspace.worktree.cleanup`。
- 创建入口默认 dry-run；实际创建要求精确 40 位基线 SHA、仓库同级受控路径、
  未占用的合规分支和显式确认短语。
- 创建后的工作区必须再次执行本文件规定的完整 preflight，才能开始写入。
- 已完成本地责任提交但尚未发布的合规分支，如需同步最新 main，只能使用
  `make workspace.branch.sync-main`。该入口要求完整 expected branch/head/old
  base/main 身份、clean worktree、无开放 PR/远端分支和可验证 recovery bundle；
  禁止裸 `git rebase`、`git merge`、`git cherry-pick` 和任何 force push。
  当目标工作树仍使用缺少该 target 的旧基线时，可从主工作树调用同一 Make
  target，并显式传入 `WORKSPACE_BRANCH_SYNC_ROOT=<absolute-linked-worktree-path>`。
  入口会在目标目录执行，并要求目标与调用者共享同一 Git common directory。

## 禁止行为
- 未完成上述校验即直接改文件。
- 在未确认仓库与分支的情况下执行连续迭代。

## 失败处理
- 一旦发现上下文错位：
  1. 立即停止改动。
  2. 输出当前 `pwd`、`git branch --show-current`、`git rev-parse --show-toplevel`。
  3. 等待人工确认后再继续。

## 审计要求
- 每个迭代批次在 `docs/ops/iterations/delivery_context_switch_log_v1.md` 记录：
  - 当前分支
  - 当前短 SHA
  - 本轮 Layer Target / Module / Reason
