# 95 · Closure Commit Plan

## Formal Product Layer

- P0 · platform_kernel_product：fieldOwnership 通用生产/校验机制（smart_core）。
- P1 · construction_industry_standard_product：项目身份声明（smart_construction_core）。
- 前端：formal 页面 legacy 渲染门控（表现层，不承载业务语义）。
- P4 · ops_delivery_tool：Guard / Evidence Collector / 文档 / 测试（scripts/verify、docs）。

## Layer Target

- P0：`smart_core`（unified_page_contract_v2_assembler、form_structure_authority、
  view_orchestrator、ui_contract_v2、ui_contract_v2_form_structure）。
- P1：`smart_construction_core`（view_orchestration_form_section_contract_data.xml）。
- 前端：`frontend/apps/web`。

## 提交边界（建议）

1. P0 机制：fieldOwnership 生产者、slot/group 键统一、context 传播、
   native 投影富化 + 3 项生产者单测。
2. P1 声明：项目身份 identity_fields 声明（数据记录）。
3. 前端：formal 页面 legacy 门控。
4. 治理：ARCH-DECISION-004、Guard v1.1.0、Evidence Contract/Collector、
   94 份架构文档、运行时证据 bundle。

## PR 描述（模板）

- Architecture Impact：新增 fieldOwnership 生产链路；原生 group 保留为权限载体，
  role 降级为业务语义；Guard 对齐 group:identity 约定。
- Layer Target：P0 smart_core + P1 smart_construction_core + 前端。
- Affected Modules：smart_core、smart_construction_core、frontend/apps/web。

## 状态

批次验收（结构侧）完成；前端 shadow 目视复核、证据采集（PC-005/008～011）为
后续独立批次。
