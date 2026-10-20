# Demo 迭代线 Batch 3（黄金业务链 + 角色快照，2026-10-20）

## 0. 身份与边界

- 分支：`feature/demo-iteration-line-20261020`
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
- Formal Product Layer：P4（demo delivery tooling）
- Layer Target：`demo_addons/smart_construction_demo/tests`、`make/dev.mk`、`docs/demo`
- 只读回读：不改数据库、不改种子、不写业务数据。

## 1. 变更

- 新增 `demo_addons/smart_construction_demo/tests/test_demo_golden_chain.py`：
  黄金业务链只读回读（结算 → 付款申请 → 付款台账 → 收款 → 资金台账 → 核销），
  固化金额/状态/日期存在性与角色接力。
- 在 `demo_addons/smart_construction_demo/tests/__init__.py` 注册该测试。
- 新增 `verify.local.dev.golden_chain.orm`（`make/dev.mk`）。

## 2. 验证

- 离线语法：`python3 -m py_compile` 通过。
- 运行时回读：`make verify.local.dev.golden_chain.orm` → 0 failed / 0 error / 1 tests，
  `DB=sc_dev_demo`。结算 `approve|done`、台账 120000 已付、收款 1200000 资金入账、
  核销 confirmed、草稿付款 5000000，角色（结算经办）可见均自洽。

结论：黄金业务链跨记录金额/状态/日期与角色接力自洽。

## 3. 风险与回滚

- 回滚：删除黄金链测试文件，撤销 `tests/__init__.py`、`make/dev.mk` 改动。
- 风险：日期“非递减顺序”由种子业务日历保证，压缩时钟下的日期连续性在 Batch 5 再验。

## 4. 下一批

Batch 4：API 场景驱动与验证（真实角色四级审批、幂等、负例）。
