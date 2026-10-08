# 产品交付主线台账彻底收口（2026-10-08）

## 1. 目的与边界

把 `.agent` 的目标台账与**已经合并的执行历史**对齐。产品交付主线链条，以及一批已完成的工作区 / CI / 契约台账，
其 run 早已 `completed`、工作早已合并进 main，但 goal 记录仍停留在 `active` / `in_progress`。本批把这些 goal
翻到终态，并把被取代的 `FE-TPL-OFFICIAL-TEMPLATE-ADOPTION` 标为 `superseded`。

**纯台账收口**：不改变任何产品、契约、测试、门禁、工作流、运行态或凭据行为。

- **本批不主张**：版本发布、整体产品交付。
- **仍真实开放**（本批不关闭、也不假装完成）的产品线见第 4 节。

## 2. 基线身份

- 收口基线 `origin/main` = `d89818e93d8127456c3071d5fe49b5e6690e886e`（PR #610 squash 合并提交，工作树干净）。
- 收口分支 `audit/product-delivery-mainline-ledger-closeout-20261008`。
- 收口 run：`.agent/runs/PRODUCT-DELIVERY-MAINLINE-LEDGER-CLOSEOUT/run.json`（离线，check `run_index_terminal_state` → `verify.agent.resume.unit`）。

## 3A. 产品交付主线链条 → `completed`（7）

| goal | 终态依据（均已合并进 main） |
| --- | --- |
| `DAILY-DEV-USER-ACCEPTANCE-COMPLETION` | PR #589（squash `dd75f83c`）+ PR #591（squash `b0f0dba5`）；89 条交付面在已部署 revision `24e05cd5` 上收口为剩余失败 0；最后一项产品策略观察（项目台账只读记录 `/f/` 打开器）由 `PROJECT-LEDGER-ENTRY-UNIFICATION`（PR #594）解决 |
| `PROJECT-LEDGER-ENTRY-UNIFICATION` | PR #594 合并（squash `90484d88`）；重复的「项目信息编辑」入口退役，台账记录表单完整承载主数据组合，由 `test_project_ledger_entry_owns_the_complete_record_composition` 锁定 |
| `DAILY-DEV-MAINLINE-DEPLOYMENT` | 主线 `a90faee8e` 已部署并运行于日常开发服务器；runtime_identity / frontend / login 探针通过 |
| `DAILY-RUNTIME-CANDIDATE-RETURN` | PR #576 交付归一入口、PR #577 关闭记录；日常运行态已精确跟踪 main |
| `MAINLINE-INTEGRATION-CLOSEOUT` | PR #531 合并（squash `9040028f`），五条工作流全绿 |
| `FE-TPL-RENDER-EVIDENCE-RECONCILIATION` | PR #543 合并（squash `3d777b47e`）；合并树与冻结候选 `dfa6fa496` 逐字节一致 |
| `FORMAL-SURFACE-RUNTIME-AUDIT-CONTRACT-BINDING` | PR #580 + PR #581 合并；主线集成 `239af48b`；日常验收绿 |

## 3B. 已完成的工作区 / CI / 契约台账 → `completed`（14）

| goal | 终态依据 |
| --- | --- |
| `ACTIVE-RUN-BINDING-RETIREMENT-GUARD` | PR #592 合并（merge `cb5ca646`）；退役入口拒绝退役「远端 main 仍绑定」的分支 |
| `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT` | 三处游离绑定清除、仅保留活跃绑定；`verify.agent.resume.unit` 30/30 |
| `BACKEND-CONTRACT-L4-CLOSURE` | 两半收口，PR #533 集成（squash `9abaa79d`）；隔离 profile 上运行车道 14/14 PASS |
| `BACKEND-CONTRACT-SUPPLY-CHAIN-ATTESTATION` | PR #535 合并（squash `08759706`）；本 run 无待办本地动作 |
| `CI-SCHEDULED-FULL-LANE-RECOVERY` | PR #529 合并（squash `84aae65b`）；定时全量车道恢复 |
| `CI-SCHEDULED-FULL-LANE-RECOVERY-B` | 关闭；残余移交给 `-C`，runner Docker 地址池根因已修 |
| `CI-SCHEDULED-FULL-LANE-RECOVERY-C` | PR #560 合并（squash `814bbc28`）；前端财务导航声明通过全量门禁导航段（28 面，0 失败）；残余移交 `-D`（已完成） |
| `CONTRACT-BATCHES-MAINLINE-INTEGRATION` | PR #533 合并（squash `9abaa79d`）；两个滞留契约批次带上主线 |
| `DAILY-ACCEPTANCE-ENTRY-DBNAME-CLI-CONSTRAINT` | 2026-10-06 完成；命令行 `DB_NAME` 约束写入两份运行手册（A/B/C 复现） |
| `DAILY-DEV-ACCEPTANCE-FIXTURE-LANE` | PR #549（`0250853e`）+ PR #550（`8a77c237`）合并；接受夹具三入口在 `sc_demo` @ `8a77c237` 通过。**状态由非规范的 `complete` 归一为 `completed`** |
| `GITHUB-RECOVERY` | PR #523 合并（merge `72ad88e6`）；分支头 `83ba64063` 是 main 祖先 |
| `REMOTE-BRANCH-BACKLOG-RETIREMENT-C` | 关闭；8 个无证据 `codex/*` origin 引用在授权下退役，附 8-头恢复包 |
| `WORKSPACE-SUPERSEDED-RETIREMENT-CLOSEOUT` | PR #539 合并（squash `3f927f19`）；无后续 |
| `WORKSPACE-WORKTREE-CLOSURE` | PR #536 合并（squash `4a3d2cd3`）；两个已集成工作树带外部恢复包退役 |

## 3C. 被取代 → `superseded`（1）

| goal | 依据 |
| --- | --- |
| `FE-TPL-OFFICIAL-TEMPLATE-ADOPTION` | 其 run 已被 `FE-TPL-RENDER-EVIDENCE-RECONCILIATION` 取代；后者的 run 经 PR #543（squash `3d777b47e`）达到 `overall_goal=completed`。该 adoption run 不再是独立交付线 |

## 4. 仍真实开放（本批不关闭，仍阻断「产品交付完成」主张）

### 4.1 产品能力（真实未完成）
- `P1-BUSINESS-FACT-PROFESSIONALIZATION`：Batch-G `review_pending`，Batch-H / I / J `planned`。
- `BUSINESS-ENTRY-SURFACE-NORMALIZATION`：batch-2 `verification_pending`（人员档案与授权边界），batch-3 `planned`（入口清单收口）。
- `FORM-FIELD-GRID-ALIGNMENT-CLOSURE`、`FORM-RESPONSIVE-CONTAINER-READING-WIDTH-CLOSURE`、
  `FORM-SECTION-NAVIGATION-CONTENT-CONSISTENCY`、`FORM-VISUAL-HIERARCHY-FIRST-VIEW-CLOSURE`：均 `verification_pending`（实现完成、受管检查未跑或未通过）。
- `FORM-PAGE-STRUCTURE-PROFESSIONALIZATION`：状态 `verified`（非规范状态），其子收口仍在上面挂起，暂不动。
- `NATIVE-VIEW-CONTRACT-CAPABILITY-CLOSURE`：`planned`（Q0/Q1 完成，Q2–Q5 进行中）。其绑定分支的生成产物
  `contracts/generated/product_view_structure_contract.json` 仍引用已退役的 `sc_product_project_edit_v1`，属该 goal 自己的
  时点产物，**不是** main 的漂移（main 的权威菜单策略 `formal_business_product_menu_policy_v1.json` 已随 PR #594 更新）。

### 4.2 平台 / 元数据（未收口）
- `BACKEND-CONTRACT-SLO-TELEMETRY`：交付已集成（PR #533），但 run 记录有**由所有者把关的后续项**（b-residual 运行期归因探针、c 签名级供应链溯源、e 119 处陈旧快照再基线决策）→ 保守保留 `active`。
- `GITEE-TEMPORARY-INTEGRATION`：`verification_pending`，阻塞项 `full_required_gate_equivalence_not_verified`、`protected_exact_head_merge_not_available`。
- `AGENT-CONTROLLER-CHECKPOINT-RECOVERY`（无 run）、`P4-INCREMENTAL-RESUME`（goal 文件为 JSON-as-YAML，无 `schema_version`）、
  `REPO-BASELINE-AUDIT`（`verification_pending`，无 run）、`P4-GOVERNED-DELIVERY-FREEZE-EFFICIENCY`（`verification_pending`，无 run）。
- `PAYMENT-REQUEST-GOLDEN-FLOORPLAN`：状态为非规范的 `complete`（Batch-A 亦为 `complete`），无 run、无可引用的合并证据，**未归一**，待确认后另行处理。

## 5. 终态动作与复验

- 21 个 goal → `completed`；1 个 goal → `superseded`；其余真实开放项保持原状并如实登记（第 4 节）。
- `.agent/active-runs.json` 在 main 上保持空终止态 `{"schema_version":1,"branches":{}}`，任何索引项都不指向已合并分支。
- 复验：`make verify.agent.resume.unit`（`run_index_terminal_state` 的离线 check）；main 上 `make agent.run.resume` → `unregistered`
  （沿用 `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT` 先例）。
- 已合并分支的删除属于独立的 `branch.retire.historical` 车道，**不在本批**（且按 `MERGED-BRANCH-RETIREMENT-RETENTION` 的裁决仍为受管保留）。

## 6. 状态边界（最终）

- **批次验收**：完成。**主线集成**：完成（本批 PR）。
- **版本发布**：未主张。**整体产品交付**：未主张 —— 第 4.1 节的产品能力项仍未完成，此判定归所有者。
