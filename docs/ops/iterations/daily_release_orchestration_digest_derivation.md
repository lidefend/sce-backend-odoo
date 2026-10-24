# daily 发布编排 digest 派生与先校验后写入

- 责任层：P4 运维 / 交付工具（`scripts/ops/daily_runtime_release_orchestration.py`）。
- 目标：修复 `daily.runtime.main.release` / `daily.runtime.candidate.release` 编排的三个缺陷，
  使一次发布要么完整通过、要么在任何远端写入前拒绝，且可续跑。

## 三个缺陷与修复

1. **受管 digest 手工输入**：`--declaration-digest`/`--entry-digest` 原为必填外部输入，而
   declaration digest 是对「模板 + 远端受管实例合并」后的结果，手工必错。修复：新增
   `derive_digests()`，先跑受管 `daily.runtime.database.duty.plan`（只读）并从报告读出两个
   digest；两个参数改为可选，提供时交叉校验、缺省时派生。

2. **先写后验**：原 digest 校验发生在第 3 步 `duty-refresh`，而 `sync`/`frontend-build` 已改远端。
   修复：digest 派生（含声明/入口/身份校验）前置到任何 make 步骤执行之前。

3. **不可续跑**：fail-fast 后无续跑入口，半部署态只能手工逐步补。修复：新增 `--resume-from <step>`，
   `resume_steps()` 跳过前置步骤，未知 step 名拒绝（fail-closed）。

## 验证

- `verify.daily.runtime.release_orchestration.unit`：10 项 PASS。
- `derive_digests` 实跑派生 `43abc992…` / `ab1845b2…`，与受管 plan 一致。
- 改动文件仅 `scripts/ops/daily_runtime_release_orchestration.py` 与同名测试。
