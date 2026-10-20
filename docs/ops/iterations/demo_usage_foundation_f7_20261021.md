# Demo 用户使用基础数据迭代 · F7 批次记录（2026-10-21，DUF-01）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F6 提交：`b9d84ce6d5182d1d410231f060291eec36914aeb`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（active）
- Runtime：`sc-local-dev`（db=sc_dev_demo）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling）
- Layer Target：`demo_addons/smart_construction_demo/models/scenario_tick.py`（tick 的
  system_fact 绑定）
- Why Here：每日事实由 demo tick 通过公开 action/回读产生，不承载产品语义
- Why Not Elsewhere：不写产品模型状态、不绕过审批、不伪造事实
- Blast Radius：scenario_tick 的 system_fact 分支 + 一个 tick 测试断言

## 3. 本批单一目标

解决 DUF-01：让每日 tick 的 `system_fact` 从「全部 unbound」变为绑定到可验证的真实事实；
未绑定或绑定失败的步骤仍 fail-closed（记 unbound + 原因），绝不伪报已推进。

## 4. 实现

`scenario_tick.py` 新增 `_FACT_BINDINGS` 注册表与三类绑定：

- `project_lifecycle`：`project_approved` 通过 `step_20_projects_demo._apply_lifecycle`
  的公开动作 `action_set_lifecycle_state` 把 DEMO-PJ-EXEC 从 draft 驱动到 in_progress；
- `lifecycle`：`material_plan`/`construction_log`/`purchase_order`/`material_arrival`
  经 `_advance_scenario_lifecycle` 走既有种子记录的公开动作链；
- `readback`：`wbs_boq_published` 通过 `project.boq.version`/WBS 只读回读验证。

`run_tick` 对 system_fact 调用 `_bind_system_fact`，成功记 `advanced`，失败记
`unbound` 并返回 `unbound_reasons`。

## 5. 验证结果

| 命令 | 状态 | 层 | 测试数 |
|---|---|---|---|
| `make verify.local.dev.scenario_tick.orm` | passed | L3 | 3 |

测试 `test_run_tick_advances_three_days_and_records_heartbeat` 现在断言 12 步 = 6 todo +
6 advanced，且无 unbound；3 日推进、心跳、幂等、体验重置范围规划全部通过。

## 6. F7 剩余：DUF-05

manifest `business_days=10`，当前仅 D1–D3（12 步）。剩余工作：按同一节奏扩写 D4–D10
（每个业务日 2 个 system_fact + 2 个 role 步骤），并把新增 fact 绑定到既有生命周期场景
（s60/s65/s66/s68/s70/s73/s78/s85/s86/s88/s89）。此为本批下一精确动作。

## 7. 回滚

撤销 `scenario_tick.py` 的绑定改动与测试断言，恢复「system_fact 一律 unbound」；
不涉及数据库数据写入（测试事务回滚）。

## 8. 下一步精确动作

扩写 D4–D10 场景步骤并补齐 `_FACT_BINDINGS`，再跑 `scenario_tick.orm` 验证 10 日连续推进。
