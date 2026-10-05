# 定时车道收口：必需检查并发组按事件类型隔离（2026-10-05）

Goal `CI-SCHEDULED-LANE-CONCURRENCY-CLOSURE` / 批次 A。基线 main `0c5eaab3`（PR #571 后）。
本轮只改五个必需检查工作流的 `concurrency.group` 键与既有 CI 契约测试的一处锁定断言，
不改任何 trigger / cron / lane 选择 / job / 必需检查，不放宽 `cancel-in-progress` 或任何断言。

## 1. 责任层

- **Formal Product Layer**：P4（ops 交付 / CI 验证工具）。
- **Layer Target**：`.github/workflows` 必需检查工作流的并发组键 + `scripts/ci` 契约测试。
- **Module**：`.github/workflows`、`scripts/ci`。
- **Standard vs User-Specific**：平台验证机制。
- **Why Here**：并发组键决定定时候选门能否观测到同批兄弟 schedule 的成功，是同一验证层的工具正确性。
- **Why Not Elsewhere**：不涉及 P0 前端契约 / 平台机制、P1 行业语义、P2 客户偏好或数据基线、P3 运行配置，
  也不做数据库 / 夹具 / 迁移 / 发布 / 部署。
- **Blast Radius**：五个必需检查工作流各一行 `group:` 键 + 一处契约断言；无产品代码变更。

## 2. 根因（远端运行记录坐实，非猜测）

五个必需检查工作流（`public_guard` / `professional_quality_gate` / `merge_policy_gate` /
`frontend_release_gate` / `release_candidate_gate`）的 `concurrency.group` 对非 PR 事件回退到
`github.ref`，而 `push`（`refs/heads/main`）与 `schedule`（同为 `refs/heads/main`）落在**同一并发组**，
且 `cancel-in-progress: true`。当 nightly schedule 窗口撞上 main 合并 push 时，push 运行会取消
in-flight 的 schedule 运行；`release_candidate_gate` 却只承认**同 SHA 的 schedule 事件**成功，
于是 `wait_for_candidate_checks` 判失败。

原始运行记录（GitHub Actions，SHA `425c0118`）：

- `frontend_release_gate` schedule id=`37237523388`：`created=2026-10-04T21:47:48Z`，
  `status=completed`，`conclusion=cancelled`，`updated=2026-10-04T22:06:41Z`。
- 同工作流 main push id=`37238726059`：`created=2026-10-04T22:06:18Z`，`sha=b6fe93f4`，
  `conclusion=success` —— 即取消源头（同组、`cancel-in-progress`）。
- `release_candidate_gate` schedule id=`37237690077`：同 SHA `425c0118`，`conclusion=failure`
  —— 因缺少同 SHA 的 schedule 兄弟成功而失败。
- 同 SHA 的 push 侧 `frontend_release_gate` id=`37226436966` = success，证明门本身可过，
  失败纯粹来自并发组抢占。

**排除项（旧提交绑定，已随主线前进消除）**：10-01～10-03 的失败为旧提交上
`verify.frontend.scene_component_bridge.guard` 判 `frontend/apps/web/src/app/contracts/v2/store.ts`
读 `document`；现行 main 复跑该守卫 `checks=129` PASS，无需在本轮修复。

## 3. 修复（最小键隔离）

五个工作流的 `group:` 在原有键前加 `github.event_name`：

```
group: <lane>-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
```

结果：`push` / `schedule` / `pull_request` 各占独立组，互不取消；**同类** re-run 仍在同组且
`cancel-in-progress: true`，折叠行为不变（如 push id=`37216773364` 被后续 push 折叠）。

## 4. 证据（受管入口，本机 offline）

- L1 `make ci.local.iteration` → rc=0 PASS；`[baseline_iteration_execution_policy_guard] PASS`，
  16 tests OK；`[ci.local.iteration] PASS ... receipt=none next=risk_selected_non_zero_L2_targets_required`
  （内环，非交付证据）。
- L2 `make verify.ci.scheduled_gates` → rc=0，`[verify.ci.scheduled_gates] PASS`（含契约测试 11+13+2+14 用例）。
- L2 `make verify.ci.orm_selection.unit` → rc=0，28+14 tests OK。
- 契约锁定：`scripts/ci/test_ci_risk_workflow_contract.py`
  `test_nightly_candidate_is_separate_from_main_push` 新增断言——五个工作流各自**恰好一行** `group:`，
  且该行**必须含** `github.event_name`。
- 负例对照：抽掉 `public_guard.yml` 的 `group:` 行 `github.event_name` 后重跑契约测试 →
  `FAIL: test_nightly_candidate_is_separate_from_main_push ... AssertionError: 'github.event_name' not found ... public_guard.yml`，
  rc=1；从备份复原后 → `Ran 14 tests OK`。证明断言真正检出注入，非复述缺陷。

（运行日志：`.runtime/agent-runs/CI-SCHEDULED-LANE-CONCURRENCY-CLOSURE/`，本地 receipt，非交付证据。）

## 5. 排除项

- 不改任何 trigger / cron / lane 选择 / job / 必需检查；不放宽 `cancel-in-progress` 或断言。
- 不新增全局测试框架；不改 Gitee 镜像 / 分支前缀策略。
- `backend_test_suite.yml` 已是 `cancel-in-progress: false`，不属本轮 5 个必需门，未改。

## 6. 台账与索引约定

- `.agent/active-runs.json` 按本仓先例在**提交态收敛为空索引**；分支运行指针只在本地工作树用于
  `make agent.run.resume` / `ci.local.iteration` 解析。因此 L1 为内环证据（采集时索引已注册），
  冻结 HEAD 只跑一次 `ci.local.quick`。
- run 状态与 goal 状态置 `completed`；主线集成以受保护 PR 合并后为准。

## 7. 四层状态

- 批次验收：本批次完成（五处并发组键隔离 + 契约锁定 + L1/L2 + 负例对照）。
- 主线集成：待本候选经受保护 PR 流程合并后推进。
- 版本发布：未主张。
- 产品交付：未主张。
