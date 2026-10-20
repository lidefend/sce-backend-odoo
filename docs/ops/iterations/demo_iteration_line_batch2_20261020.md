# Demo 迭代线 Batch 2（G0–G4 基线就绪回读，2026-10-20）

## 0. 身份与边界

- 分支：`feature/demo-iteration-line-20261020`
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
- Formal Product Layer：P4（demo delivery tooling）
- Layer Target：`demo_addons/smart_construction_demo/tests`、`make/dev.mk`、`scripts/verify`、`docs/demo`
- 只读回读：不改数据库、不改种子、不写业务数据；仅用 model count 探测存在性。

## 1. 变更

- 新增 `demo_addons/smart_construction_demo/tests/test_demo_baseline_readiness.py`：
  G0–G4 硬性就绪的只读 ORM 回读（主公司 + `DEMO-PJ-EXEC`），任一硬性项缺失即 fail-closed。
- 在 `demo_addons/smart_construction_demo/tests/__init__.py` 注册该测试。
- 新增 `verify.local.dev.baseline_readiness.orm`（`make/dev.mk`）。
- 在 `scripts/verify/test_baseline_readiness_verifier.py` 增加 `HARD_KEYS` 与 manifest 的漂移守卫。

## 2. 验证

- 离线：`python3 -m unittest scripts.verify.test_baseline_readiness_verifier` → 11 tests OK。
- 运行时回读：`make verify.local.dev.baseline_readiness.orm` →
  0 failed / 0 error / 1 tests，`DB=sc_dev_demo`，`project=sc-local-dev`。

结论：G0–G4 硬性项对主公司与 `DEMO-PJ-EXEC` 全部 present，`missing=[]`；无需数据补齐。

## 3. 风险与回滚

- 回滚：删除 ORM 测试文件，撤销 `tests/__init__.py`、`make/dev.mk`、漂移守卫改动。
- 风险：探针以 search_count 存在性为主，不含金额/日期/状态自洽；这些属于 Batch 3。

## 4. 下一批

Batch 3：黄金业务链 + 角色快照（跨记录金额/日期/状态自洽、角色可见）。
