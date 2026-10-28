# FEPC-04 角色首页契约与展示一致性矩阵

基线 main：`a49742c31d1a08e053187c1ab146ab914108ad11`
运行时：Demo source_revision `3f46dd7e`，前端构建 `5690cde9`

## 角色 × 区块 × 实际展示

| 区块 | 项目经理 | 项目成员 | 企业负责人 | 契约来源 | 差异裁定 |
| --- | --- | --- | --- | --- | --- |
| 当前状态（待我处理/我发起的） | 28 / 0 | 0 / 0 | 0 / 0 | session.workspaceHome 派生 | 数据量差异，非缺陷 |
| 今日工作 | 付款申请 3 条 | 当前没有待处理事项 | 当前没有待处理事项 | session.workspaceHome.today_actions | 数据量差异，非缺陷 |
| 风险与提醒 | 风险处置（已升级/已认领） | 同项目经理 | 项目风险预警（项目健康状态异常） | build_risk_action_rows 可见性 fallback | 有业务依据的角色差异 |
| 我的项目与业务对象 | 有（项目+合同） | 有（项目+合同） | 有（项目+合同，数量更多） | session.workspaceHome.my_objects | 数据量差异，非缺陷 |
| 常用入口与最近访问 | 有（6 项） | 有（8 项，多证书管理/行政中心） | 有（6 项） | workspace quick_links + navigation | 角色权限差异 |
| 工作入口（能力地图） | 有（暂无首页快捷入口） | 有（同） | 有（同） | productCapabilityCatalog loginBlocks | 合法空状态，非缺陷 |

## 契约来源（关键）

- 实际渲染的 `session.workspaceHome` 由 `smart_core/core/workspace_home_contract_builder.py`
  生成（`SOURCE_KIND=workspace_home_startup_surface_projection`，经 system.init 返回），
  字段含 hero / advice / metrics / today_actions / risk / my_objects / ops / scene_groups / group_overview。
- 另存在 `smart_construction_core/services/workspace_contract_builder.py`
  （`workspace.home.enter` handler，SOURCE_KIND=workspace_home_odoo_native_capability_projection），
  其区块为 metric_card / shortcut_grid / todo_list / warning_list / native_view_ref，
  与 `session.workspaceHome` 区块不一致。该 handler 是否仍被前端消费需核实。

## 风险区差异（风险处置 vs 项目风险预警）

- `build_risk_action_rows`：存在 project.risk.action（open/claimed/escalated）时输出“风险处置”；
  否则 fallback 到 project.risk / project.project 的 health_state，输出“项目风险预警”。
- 企业负责人展示“项目风险预警”，说明其运行时会话读不到 risk action 行
  （ACL/domain 可见性），fallback 生效。该差异有业务依据，不是展示缺陷。

## 待核实

- `workspace_home_contract_builder.py` 与 `workspace_contract_builder.py` 的双重契约关系：
  前者是 system.init 生效契约，后者的 workspace.home.enter 是否冗余/遗留。
- 企业负责人读不到 project.risk.action 的确切原因（ACL vs 记录规则），避免误判为缺陷。
