## 背景

日常库完整用户级验收入口 `make release.daily_dev.acceptance.publish`（在 `sc-root`
运行仓执行）在 `verify.daily_dev.acceptance.env.guard` 处失败：

```
- ACCEPTANCE_PROBE_OUTPUT must be 'artifacts/backend/dev_acceptance_release_probe.json',
  got 'artifacts/backend/daily_dev_acceptance_probe.json'
```

同一入口的依赖 `env.matrix.check`（`scripts/verify/environment_topology_guard.py`）也
因 Makefile token 与门店实际前置串不一致而失败。二者均属 P4 交付工具层的
**声明自洽缺陷**，不涉及产品语义、运行库数据或权限。

## 根因（钉住首次产生偏差的位置）

- `make/dev.mk` 的 `release.daily_dev.acceptance.publish` 目标级变量
  `ACCEPTANCE_PROBE_OUTPUT := $(DAILY_ACCEPTANCE_PROBE_OUTPUT)` 覆盖了受管默认值。
  make 的目标级变量会传递到全部前置，因此 env guard、`release.dev.acceptance.publish`
  与其探针链都看到 daily 产物名。
- 三处独立声明一致要求日常发布绑定 release 探针产物：
  1. `docs/ops/environment_tiers_unified_runbook_v1.md`（日常发布车道条款）；
  2. `scripts/verify/daily_dev_acceptance_env_guard.py`（`expected["ACCEPTANCE_PROBE_OUTPUT"]`）；
  3. `scripts/verify/release_v2_0_0_evidence_manifest_guard.py`（证据清单）。
  唯一偏差是上述 make 覆盖 → 修 make 目标，**不放宽守卫**。
- `environment_topology_guard.py` 的 `REQUIRED_TOKENS["makefile"]` 仍是加入
  `verify.daily_dev.product_menu_release_gate.guard` 之前的旧串。

## 改动

- `make/dev.mk`：删除发布目标的 `ACCEPTANCE_PROBE_OUTPUT` 目标级覆盖，使其继承受管
  默认 `artifacts/backend/dev_acceptance_release_probe.json`；`verify.daily_dev.acceptance.readonly.probe`
  车道的 `daily_dev_acceptance_probe.json` 归属不变。
- `scripts/verify/environment_topology_guard.py`：`makefile` token 补
  `verify.daily_dev.product_menu_release_gate.guard`（依赖串与 `.PHONY` 期望）。
- `scripts/verify/test_dev_acceptance_release_identity.py`：新增
  `DailyAcceptanceLaneSelfConsistencyTest`，锁定「发布目标不得重绑探针产物」「两处守卫
  绑定同一 release 产物」「topology token 必须匹配实际前置串」，并保留只读探针仍用
  daily 产物的正向断言。

## 验证（离线 L1/L2，本仓）

- `make verify.environment.topology.guard` = PASS（9 + 6 项单测 + guard）。
- `make verify.frontend.acceptance.environment.guard` = PASS（42 项单测 + 源守卫）。
- `python3 scripts/verify/environment_topology_guard.py` = PASS。
- `make -n release.daily_dev.acceptance.publish` 展开确认 env guard 收到
  `ACCEPTANCE_PROBE_OUTPUT="artifacts/backend/dev_acceptance_release_probe.json"`；
  `verify.daily_dev.acceptance.readonly.probe` 仍为 daily 产物。
- `env.matrix.check` 在本仓因缺 `.env.test/.env.prod`（`.env*` 已 gitignore，本地仅有
  `.env.dev`）停在本环境前置，属既有本地条件；真实车道在 `sc-root` 运行仓执行。

运行态回执（`sc_demo` 复合入口 + 后续用户级验收）在合入后经日常运行仓受管入口执行。
