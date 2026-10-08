# 验收运行时 rebuild/snapshot 车道「环境独占前置」复核与落档（2026-10-09）

## 1. 专题边界

**Formal Product Layer**：P4（ops 交付工具 / 环境与验收运行时治理）。
**Layer Target**：`acceptance_runtime_rebuild_prerequisite`（`make acceptance.runtime.baseline_recovery.audit`）、
`scripts/dev/frontend_acceptance_baseline_rebuild.sh`、`.agent/runs/` 台账。
**Standard vs User-Specific**：平台机制（环境独占与 fail-closed 审计）。
**Why Here**：卷挂载独占前置的规则与入口都在该层，只有这里能给出权威结论。
**Why Not Elsewhere**：不属 P0/P1 产品语义、不属前端渲染、不是低代码配置。
**Blast Radius**：仅 rebuild/snapshot 车道的环境前置结论与台账；无产品代码、无数据库写入、无容器操作。

## 2. 历史 DENY 的原始事实（出处：`FE-TPL-OFFICIAL-TEMPLATE-ADOPTION`）

- 命令：`make acceptance.runtime.baseline_recovery.audit`
- 结果：`rc=2 DENY volume=sc_fe_r2_p1_01_odoo expected one mount consumer service=odoo actual=2`
- 两个挂载者：
  - `sc-backend-odoo-acceptance` —— 受管验证后端，端口 **18082**，由 `make backend.acceptance.up/down`
    （`BACKEND_ACCEPTANCE_NAME`）管理其生命周期。
  - `sc-fe-r2-p1-01-odoo-1` —— `sc-fe-r2-p1-01` compose carrier，端口 19083。
- 结论：二者同属 `sc-fe-r2-p1-01`，**同项目成员不构成独占证明**；规则 fail-closed 且有单测锁定，
  **不得放宽**；处置必须走该项目的既有受管入口，**禁止直接 docker 操作绕过**。

## 3. 本轮复验（2026-10-09，受管只读，无任何写动作）

- `make acceptance.runtime.baseline_recovery.audit` → **rc=0 PASS**。
  precheck 逐卷：`sc_fe_r2_p1_01_db / _redis / _odoo` 均 `owner_project=sc-fe-r2-p1-01`、`declared_consumers=1`。
  audit 行：`classification=platform_internal_acceptance`、`fixture_allowed=true`、
  `customer_business_data_allowed=false`、`secondary_database=sc_odoo`（无 public tables、无 odoo registry）。
  日志：`.runtime/environment-rebuild-lane-20261009/audit.log`。
- 挂载消费者身份（`docker ps -aq --filter volume=<v>` 逐个 `inspect`）：

  | 卷 | 消费者 | project | service | oneoff | status |
  | --- | --- | --- | --- | --- | --- |
  | `sc_fe_r2_p1_01_db` | `sc-fe-r2-p1-01-db-1` | `sc-fe-r2-p1-01` | `db` | False | running |
  | `sc_fe_r2_p1_01_redis` | `sc-fe-r2-p1-01-redis-1` | `sc-fe-r2-p1-01` | `redis` | False | running |
  | `sc_fe_r2_p1_01_odoo` | `sc-fe-r2-p1-01-odoo-1` | `sc-fe-r2-p1-01` | `odoo` | False | running |

  证据：`.runtime/environment-rebuild-lane-20261009/consumer_inventory.txt`。
- **非当前挂载者已不存在**：`docker inspect sc-backend-odoo-acceptance` → `no such object`，18082 无监听。
  因此本轮**不需要**通过受管入口去处理第二个挂载者 —— 不是绕过 DENY，而是 DENY 的前提已经消失。
- 车道 carrier 前置：`/tmp/sc-frontend-acceptance.pid` 不存在（受管前端 carrier 已停）；
  无 `ssh -L/-R`、`socat`、`sshuttle`、`autossh` 端口转发残留。

## 4. 规则完整性（证明「没有放宽审计」）

- `make verify.acceptance.runtime.baseline_rebuild.unit` → **Ran 50 tests OK** +
  `[frontend_acceptance_environment_source_guard] PASS`。
  该测试集覆盖 fail-closed 负例：foreign owner（不同 project/service）拒绝、undeclared one-off 名称拒绝、
  非 `odoo` 卷的多消费者拒绝。
- 现行规则（main，`f9d2f1d9` 起）：`odoo` 卷要求**恰好一个非 one-off compose carrier**，
  另仅接受名字为 `BACKEND_ACCEPTANCE_NAME` 的声明式 one-off；任何第三方/未声明挂载者仍 DENY。
  当前环境即使按**未放宽的严格计数**（`consumers == 1`）也同样满足。

## 5. 另一项历史 standing 环境项

- `make verify.frontend.fixture.guard` 现已 **PASS**：`denied DB_NAME=sc_demo / postgres / arbitrary_database / <empty>` 各 `exit=20`，
  且 `PASS sc_dev_demo fingerprint unchanged`。此前记录在 `CI-SCHEDULED-FULL-LANE-RECOVERY-D` 的
  「`KeyError 'project.project'` on main（pre-existing）」不再是 main 上的失败项。

## 6. 结论与边界

- 结论：rebuild/snapshot 车道的**环境独占前置在当前环境已满足**，且其判定入口（受管 audit）与规则单测均通过；
  历史 DENY 叙述属于**已消失前提的残留文本**，本轮据实更新，**不改写历史提交**。
- 未主张：未执行 rebuild/snapshot；未启动/停止任何容器、服务或数据库；未改动审计规则、断言或 fail-closed 边界。
- 复用：本专题为纯台账/复核交付，按仓库门禁（bookkeeping-only 候选不单独合并）随下一个产品候选进入 PR。

## 7. 分支清理盘点、陈旧 run 退役与本专题终局（2026-10-09）

### 7.1 远端历史分支退休评估（只读 dry-run，未删除任何引用）

- 入口：`make branch.retire.historical`，`HISTORICAL_RETIREMENT_EXPECTED_MAIN=b28d4499`、`HISTORICAL_RETIREMENT_REMOTE=origin`。
- 库存：`reference_count=90`；本次评估候选 6 条（`contained in origin/main b28d4499`）。
- 结果：`retirement_outcome=assessment_only`、**`eligible=0` / `skipped=6`**、`deleted=0`、`apply_invoked=false`，`mode=dry-run`。
- 6 条全部因 **run ledger 承重引用**被 skip：`resolve_run` 要求 `run.branch == 当前分支`，
  该字段是台账执行身份，删除引用会让台账自相矛盾。既有裁决
  `.agent/runs/MERGED-BRANCH-RETIREMENT-RETENTION/run.json`（completed）已确认**已合并分支按设计保留**。
- 本地独有分支（无远端同名，不在远端退休范围）：`audit/environment-rebuild-lane-prerequisite-20261009`（本专题）、
  `codex/daily-runtime-main-sync-20261008`（内容已含于 main）、`main`。
- 证据：`.runtime/environment-rebuild-lane-20261009/branch_inventory.json`、`branch_manifest.json`（sha256 `1e92d1b0…6314`）、`branch_retire_report.json`。
- **结论**：不删除任何引用、不放宽任何前缀策略或审计。分支清理在本轮就是「按设计保留 + 记录」。

### 7.2 陈旧 run 退役：`DAILY-DEV-MAINLINE-ACCEPTANCE-REFRESH` → `superseded`

- 该 run 唯一未决项是 2/89 声明业务入口 `exception`（`menu_sc_p1_expense_contract`、`menu_sc_payment_execution`），
  根因是整表 `HierarchicalWorksheet` 的可用性缺陷（见 `docs/ops/iterations/daily_dev_mainline_acceptance_refresh_20261008.md` 第 5 节）。
- **该缺陷已由 `FE-HIERARCHICAL-WORKSHEET-USABLE-READY` 处理**：契约声明工作表 `page_size` + 前端消费 +
  「首屏可用即 `ready`、后台加载单独声明」的数据态语义，经 PR #621…#626 进入 `main b28d4499`。
- 现行台账：`docs/product/frontend_business_entry_acceptance_v1.csv` → **89/89 `acceptance_status=passed`**。
- 处置：run 与 goal 置 `superseded` 并指向 `FE-HIERARCHICAL-WORKSHEET-USABLE-READY`；
  `.agent/active-runs.json` 移除其分支映射；**不改写历史提交**。

### 7.3 活动 run 索引一致性（dangling 清理）

- 同类清理属既有先例 `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT`：一个 run 只能绑定一个 `branch`，
  同一 run 名下的其它分支键无法 `resolve`（`run schema or branch mismatch`）。
- 本轮移除三条不可解析/已退役的映射，仅保留与自身 `run.branch` 相等的键：
  保留 `fix/user-acceptance-detail-closure-20261009` → `FE-HIERARCHICAL-WORKSHEET-USABLE-READY`。

### 7.4 本专题终局（terminal）

- 本专题的独立价值（rebuild/snapshot 车道环境独占前置的复核与落档）已交付并复验，唯一残留「可选动作」属所有者协调的重建/快照窗口，
  不在本 run 的授权范围内。因此本 run 置 `completed`，`.agent/active-runs.json` 移除本分支映射，索引回到终局态。
- 复跑记录：`make acceptance.runtime.baseline_recovery.audit` → **rc=0 PASS**（三卷 `declared_consumers=1`），日志
  `.runtime/environment-rebuild-lane-20261009/audit_20261009b.log`；规则单测 `make verify.acceptance.runtime.baseline_rebuild.unit` → **Ran 50 tests OK**；
  `make verify.guard.registry` → **AUDIT PASS：1400 scripts / 1312 referenced / 88 of 88 orphan acknowledgements / 186 of 186 unwired dispositioned**（工具单测 10 tests OK）。
- 边界重申：**未**执行 rebuild/snapshot；**未**启动/停止任何容器、服务或数据库；**未**改动审计规则、断言或 fail-closed 边界；
  「环境 DENY 已解除」的结论**只**绑定 rebuild/snapshot 车道的环境前置，**不**泛化为「环境全部通过」。
