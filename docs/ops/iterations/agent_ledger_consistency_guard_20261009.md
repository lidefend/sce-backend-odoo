# Agent ledger consistency guard (2026-10-09)

## 1. 目的

把「`.agent` goal 与 run 状态不一致」从**每轮人工普查**改为**机械检出**。REPO 的
`AGENTS.md`/`.agent/README.md` 已规定 run 状态机（`planned` / `active` / `blocked` /
`verification_pending` / `completed` / `superseded`），但一直到本轮，判断 goal 与 run 是否
同步全靠人眼逐文件比对，因此同类漂移反复出现。本批把该检查固化为受管守卫。

## 2. 事实与根因

### 2.1 守卫在真实台账上首次运行即检出 4 项，逐条定性

```
- .agent/goals/CI-SCHEDULED-FULL-LANE-RECOVERY.yaml: not machine-readable YAML
  (mapping values are not allowed here)                     # 真缺陷：客观无法解析
- ENV-ACCEPTANCE-REBUILD-LANE-PREREQUISITE: goal status 'in_progress' is not in the
  canonical enum ... and is not a recorded residual          # 真缺陷：非规范值
- ENV-ACCEPTANCE-REBUILD-LANE-PREREQUISITE: run ... is completed but the goal
  status is 'in_progress'                                    # 真漂移
- P4-INCREMENTAL-RESUME: run ... is completed but the goal status is 'active'
                                                             # 既有裁决保留的开放项
```

- **`ENV-ACCEPTANCE-REBUILD-LANE-PREREQUISITE`**：其 run（PR #627 候选）已是
  `completed`，goal 仍为 `in_progress`。`in_progress` 也不在规范枚举内。**真缺项**，
  在本批翻为 `completed`。
- **`CI-SCHEDULED-FULL-LANE-RECOVERY.yaml`**：`objective` 是含 `": "` 的未加引号 plain
  scalar，`yaml.safe_load` 直接报 `mapping values are not allowed here`。任何按 YAML 读取
  台账的工具都读不到该 goal，只能退回正则。**真缺陷**，本批改为 `>-` 块标量。
- **`P4-INCREMENTAL-RESUME`**：run `completed`（PR #524 合入并已收口），goal `active`。
  该 goal 在既有裁决
  `docs/ops/iterations/product_delivery_mainline_ledger_closeout_20261008.md` §4.2 中已被**明确
  登记为未收口的元数据项**（goal 为 JSON-as-YAML、无 `schema_version`），属于按裁决保留的
  开放项，**不放宽也不擅自关闭**，以白名单条目连同出处固定。
- **`BACKEND-CONTRACT-SLO-TELEMETRY`**：run `completed`、goal `active`，同样由 §4.2 记录为
  所有者把关的后续项（b-residual 运行期归因探针 / c 签名级供应链溯源 / e 119 处陈旧快照再基线），
  白名单固定。

> 更正一处交接误记：`P4-INCREMENTAL-RESUME` 的 `run.json` **确实存在**（
> `.agent/runs/P4-INCREMENTAL-RESUME/run.json`，`status=completed`）。上一轮据「goal 文件为
> JSON-as-YAML 导致 `^\s*id:` 正则取不到 id」错误推断该 run 缺失；守卫按 run 记录反向解析
> goal 路径，得到的是磁盘事实。

### 2.2 未纳入本批的残项（记录而不泛化，不擅自归一）

`RECORDED_NON_CANONICAL` 是三处**非规范 goal 状态**的棘轮集合，必须与磁盘集合逐字相等，
新增或消失都会让守卫失败：

| goal | 状态 | 归属 |
| --- | --- | --- |
| `FE-HIERARCHICAL-WORKSHEET-USABLE-READY` | `in_progress` | 绑定分支 `fix/user-acceptance-detail-closure-20261009` 的**活动 run**，由该 run 自己收口时归一 |
| `FORM-PAGE-STRUCTURE-PROFESSIONALIZATION` | `verified` | 无 run 的历史值，§4.1 已载明**暂不动** |
| `PAYMENT-REQUEST-GOLDEN-FLOORPLAN` | `complete` | §4.2 载明**未归一、待确认后另行处理** |

## 3. 变更清单（P4）

- 新增 `scripts/verify/agent_ledger_consistency_guard.py`：只读、fail-closed。规则：
  1. goal 状态须落在 `.agent/context.yaml:run_statuses` 规范枚举内，且非规范值集合须与
     `RECORDED_NON_CANONICAL` 棘轮集合逐字相等；
  2. **终态 run（`completed`/`superseded`）不得留下非终态 goal**，例外仅限
     `TERMINAL_MISMATCH_ALLOWLIST`，且其 `authority` 必须指向**磁盘上真实存在**的裁决文档；
  3. `.agent/active-runs.json` 每项须指向存在、`branch` 自洽、且**非终态**的 run 记录；
  4. 每条 run 记录状态须规范，`goal`/`record` 路径须可解析；每个 goal 须声明 `id`/`status`
     且为可机器读取的 YAML，重复 id 报错。
- 新增 `scripts/verify/test_agent_ledger_consistency_guard.py`：15 条用例。**先断言合成台账
  基线为空（`check == []`）、真实台账为空，再逐个注入**（终态错配、未知非规范值、索引指向
  缺失/终态/分支不符的 run、非法 YAML、run 的 goal 不可解析、重复 id、白名单陈旧、白名单权威
  文档缺失、棘轮残项消失/漂移）证明被检出，并有反证：去掉白名单后同一形态转为硬失败。
- `make/codex.mk` 新增 `verify.agent.ledger.unit`（`py_compile` + 单测 + 守卫本体）。
- `make/ci.mk` 将 `verify.agent.ledger.unit` 接入 `ci.delivery.freeze.prepare`：**交付冻结车道
  禁止带着不一致的 `.agent` 台账放行**。
- `.agent/goals/ENV-ACCEPTANCE-REBUILD-LANE-PREREQUISITE.yaml`：`in_progress` → `completed`。
- `.agent/goals/CI-SCHEDULED-FULL-LANE-RECOVERY.yaml`：`objective` 改为合法 YAML 块标量。
- `scripts/verify/registry.yaml`：**无净变更**。初稿曾为本批两个脚本补条目，但守卫审计判定二者
  已被 `make/codex.mk` 以文件名形式引用（`wired`），`file-consumed` 条目属陈旧；按 `make
  verify.guard.registry` 的判定保持台账原样。

## 4. 证据

- `python3 scripts/verify/agent_ledger_consistency_guard.py` →
  `PASS goals=91 runs=69 pinned_residuals=3 open_run_allowlist=2`。
- `make verify.agent.ledger.unit` → 15 tests OK + 守卫 PASS。
- `make verify.guard.registry` →
  `AUDIT PASS: 1402 scripts (1314 referenced, 88/88 orphans acknowledged, 1 retired, 186/186 unwired dispositioned)`。
- `make verify.agent.resume.unit`、`make ci.local.iteration`、`git diff --check` 见同批 run 回执。

## 5. 状态边界

- **批次验收**：见本批 run 回执与 PR 检查。
- **主线集成**：以合入 PR 为准，本记录不预先主张。
- **版本发布 / 产品交付**：未主张，均不在本批范围。
- **环境 DENY 结论**：本批不涉及重建/快照环境前置，不改写、不泛化上一轮的 DENY 结论。

## 6. 回滚

还原本批提交即可（守卫、单测、make 接线、goal/run/record 文本与两处 goal 文档修复）；
不涉及产品代码、数据库或运行时状态。
