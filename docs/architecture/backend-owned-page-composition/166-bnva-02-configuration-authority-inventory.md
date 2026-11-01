# 166 · BNVA-02A · 配置事实权威清单

## 唯一运行时权威

| 权威 | 载体 | 职责 |
| --- | --- | --- |
| 业务配置事实 | `ui.business.config.contract` | 业务结构/展示职责/加载策略的声明 |
| 原生结构事实 | `native_view_projection.project_native_view` | Odoo 原生视图规范化 |
| 配置解析 | `form_structure_authority.resolve_form_structure_governance` | 选择生效配置并转治理字典 |
| 业务结构投影 | `ui_contract_v2_form_structure.py` | slots/fieldGroups/fieldOwnership |
| 布局结构投影 | `view_Parser` + `layout_semantics.py` | containerTree/columns/widget |
| 最终组装 | `unified_page_contract_v2_assembler.py` | 契约规范化与组装 |

## 边界分类（`backend_contract_boundaries.py`）

- user_preference / tenant_lowcoding / generated_industry_baseline /
  industry_standard 四层，`view_orchestration_apply_order_key` 据此定覆盖。

## 无平行 Schema

按 ARCH-DECISION-004：业务结构（slots/fieldGroups/fieldOwnership）与布局拓扑
（containerTree）两层分离，前端只做表现；无第二套低代码 Schema。

## 现有配置载体

- `smart_construction_core/data/view_orchestration_form_section_contract_data.xml`
  等 P1 产品发布配置；`source_status=product_release`。
- 低代码运行时配置：`smart_core.lowcode.business_config` 来源。
- 原生 XML 视图：`smart_construction_core/views/**` 作为原生结构基线。

