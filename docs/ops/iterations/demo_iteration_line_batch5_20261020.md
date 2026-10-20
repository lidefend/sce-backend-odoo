# Demo 迭代线 Batch 5（scenario tick 离线核心，2026-10-20）

## 0. 身份与边界

- 分支：`feature/demo-iteration-line-20261020`
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
- Formal Product Layer：P4（demo delivery tooling）
- Layer Target：`scripts/verify`、`make/dev_test.mk`
- 本批性质：纯逻辑离线核心，不写库、不改 timer。

## 1. 变更

- 新增 `scripts/verify/demo_scenario_step.py`：步骤契约 + 幂等 tick 调度——
  `system_fact` 自动推进、`role_draft` 只备草稿、`role_decision` 只生成待办绝不自动审批、
  `showcase_history` 独立展示轨道；幂等键 `scenario_id::business_date::step_key`。
- 新增 `scripts/verify/test_demo_scenario_step.py`：7 个离线单测覆盖契约校验、幂等、
  重复键拒绝、actor_mode 分类与“决策不自动推进”不变量。
- 新增 `verify.demo.scenario_step.unit`（`make/dev_test.mk`）。
- 新增 `demo_addons/smart_construction_demo/data/scenario/demo_scenario_manifest.json`：
  黄金业务链 3 日压缩时钟（D1–D3）步骤声明，`system_fact`/`role_draft`/`role_decision`
  各归其类，幂等键为 `scenario_id::business_date::step_key`。

## 2. 验证

- `python3 -m unittest scripts.verify.test_demo_scenario_step` → 8 tests OK（非零），
  含 3 日压缩时钟演练：3 个不同业务日、无重复键、`role_decision` 绝不自动推进。

## 3. 完成边界

- 本批落地 tick 的调度与幂等纯逻辑；运行时接库（ir.cron / 压缩 3 日时钟、心跳）与
  scoped experience reset（以 demo 声明的体验集合为清理键）为 Batch 5 后续。

## 4. 下一批

Batch 5 后续：把 tick 引擎接入 demo 场景 manifest 与受管运行时，补 3 日压缩时钟 +
心跳 + 基线指纹不变 + 体验增量清零；随后 Batch 6 角色 UI 验收。
