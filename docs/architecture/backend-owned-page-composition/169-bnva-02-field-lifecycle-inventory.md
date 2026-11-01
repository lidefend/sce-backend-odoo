# 169 · BNVA-02A · 字段生命周期清单

## 五类字段与生产者

| 集合 | 生产者 |
| --- | --- |
| ViewField | `native_view_projection`（get_view/fields_get 投影） |
| BusinessField | `derive_native_field_ownership` |
| HydrationField | `collect_visible_layout_hydration_fields` / `collect_fact_hydration_fields` |
| TechnicalDependency | `collect_modifier_dependency_fields` |
| RelationField | `_inject_relation_entry_contract` |

## 预算

- `FORM_RECORD_SNAPSHOT_FIELD_BUDGET = 80`
- `FORM_VISIBLE_LAYOUT_HYDRATION_BUDGET = 40`

预算只约束机会性补齐；modifier 依赖与 fact 字段不受限。

## manager_id 已是通用规则

`native_view_projection.field_role`：role 来自所属原生 group（`group_role`），
不来自 ORM 类型；many2one 的 `manager_id` 在 context group 内是主业务事实。
关系导航由字段描述符类型独立表达（`contract_governance_field_semantics.
classify_field_semantic_type` 返回 `relation` 能力）。这是通用规则，不是单字段补丁。

## 重复定义检查

字段技术性判定集中在 `contract_governance_field_semantics.py` 与
`ui_contract_v2_constants`；未发现第二套独立分类器，但两处常量需在 BNVA-02B/C
核对是否收敛为单一字段生命周期入口。

