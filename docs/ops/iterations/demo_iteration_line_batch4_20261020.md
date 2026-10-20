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

## 3. 完成边界

- 本批完成“驱动前置与审批链表面”回读。
- 完整四级角色驱动（submit → 四级 approve，幂等 + 负例）由产品层
  `test_payment_request_action_surface_backend` / `test_smoke_3waymatch_flow` 覆盖机制，
  demo 层完整驱动用例留作 Batch 4 收尾，需先映射各 tier 的 finance-approve 评审角色。

## 4. 下一批

Batch 4 收尾：demo 场景四级审批角色驱动（幂等 + 负例）；随后 Batch 5：日推进 +
体验重置分离（先确认 `scems-demo-tenant.timer` 目标租户身份）。
