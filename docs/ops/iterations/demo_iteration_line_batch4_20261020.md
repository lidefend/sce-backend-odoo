# Demo 迭代线 Batch 4（API 场景驱动表面回读，2026-10-20）

## 0. 身份与边界

- 分支：`feature/demo-iteration-line-20261020`
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
- Formal Product Layer：P4（demo delivery tooling）
- Layer Target：`demo_addons/smart_construction_demo/tests`、`make/dev.mk`
- 只读回读：不改数据库、不写业务数据。

## 1. 变更

- 新增 `demo_addons/smart_construction_demo/tests/test_demo_api_scenario.py`：
  API 场景驱动表面回读——floorplan 付款 fixture 可驱动（draft、金额>0、合同依据），
  `payment.request` 多级审批定义与 `sc.approval.policy` 已接线，submit/approve 动作存在。
- 在 `demo_addons/smart_construction_demo/tests/__init__.py` 注册。
- 新增 `verify.local.dev.api_scenario.orm`（`make/dev.mk`）。

## 2. 验证

- 运行时回读：`make verify.local.dev.api_scenario.orm` → 0 failed / 0 error / 1 tests，
  `DB=sc_dev_demo`。

## 3. 完成边界（含收尾）

- 表面回读：`payment.request` 多级审批已接线、fixture 可驱动、submit/approve 动作存在。
- 角色驱动用例 `test_four_tier_approval_role_driven`：以发起人提交 → 审批链初始化 →
  非财务角色拒绝（负例）→ 重复提交拒绝（幂等）→ 按 `review_ids` 泛化逐级审批到
  `approved|done`，且审批过程不产生重复 review。
- 审批链级数与评审角色是运行时可配置的（P3/P1 配置，非产品写死）；用例按配置的
  `review.reviewer_ids` 泛化驱动，不把“四级”写成产品不变量。

## 4. 下一批

Batch 5：demo scenario tick（日推进）与 scoped experience reset（体验用户角色落地前
以 demo 声明的体验集合为清理键）；公开 demo 租户 timer 保持不变。
