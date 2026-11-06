# BE-NAV-PROJECTION-01 批次记录

- 基线：`main@3629ae1a7027f82532b18f306ce926fd467affef`，分支 `fix/nav-projection-reconciliation-20261106`。
- 层级：P4 交付工具（scripts/verify、scripts/dev、make、config/ci）；不触碰产品/模块/ACL/manifest。
- 结果：
  - 离线守卫 18/18、聚合器校验 10/10、gate 11/11 通过。
  - 采集器对 `sc_frontend_acceptance` 四 fixture 主体实采 P0/P1；P1 ⊆ P0，9 项 P0→P1 由 `smart_construction_scene.filter_business_authority` 以 `BUSINESS_SCENARIO_CONFIGURATION_MISSING` 收窄。
  - 四角色完整发布对账 = `NOT_VERIFIED`（P0 与锁定 leaf_keys 不同口径：finance 46→31、pm 25→21、owner 6→16、project_a_member 10→2）。
- 未做：不回填 87/70/61，不做 warning 降级，不把“87 必须等于 fixture P0”设为硬规则。
