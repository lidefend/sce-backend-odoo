# 109 · BNVA-019-04 · 字段生命周期分类

> 目标：一个原生字段从 View 出现到最终渲染，分属不同集合；这些集合不是同一个集合。

## 1. 五类字段

```text
NativeFieldOccurrences
  ├── ViewField          原生视图声明字段（fields map / arch field 节点）
  ├── BusinessField      有业务归属 → fieldOwnership
  ├── HydrationField     当前页面需要记录值 → mainData
  ├── TechnicalDependency 表达式/计算依赖 → modifier evaluation
  └── RelationField      关系导航 → relation descriptor / relation_entry
```

## 2. 各类字段的生产者（当前代码）

| 集合 | 生产者 | 代码位置 |
| --- | --- | --- |
| ViewField | `get_view()` / `fields_get()` 投影 | `native_view_projection.py` |
| BusinessField | `derive_native_field_ownership` | `native_view_projection.py:198` |
| HydrationField（首屏） | `collect_visible_layout_hydration_fields` | `unified_page_contract_v2_modifier_dependencies.py:77` |
| HydrationField（hidden fact） | `collect_fact_hydration_fields` | 同文件 `:143` |
| TechnicalDependency | `collect_modifier_dependency_fields` | 同文件 `:28` |
| RelationField | `_inject_relation_entry_contract` | `page_assembler.py:3403` |

## 3. 预算边界

| 预算 | 值 | 语义 |
| --- | --- | --- |
| `FORM_RECORD_SNAPSHOT_FIELD_BUDGET` | 80 | 初始记录快照的模型字段序截断 |
| `FORM_VISIBLE_LAYOUT_HYDRATION_BUDGET` | 40 | 首屏可见布局字段闭包 |

预算只约束「机会性补齐」，不约束 modifier 依赖（正确性输入）和 fact 字段。

## 4. manager_id 生命周期示例

```text
manager_id
  ORM type        = many2one
  native group    = sc_project_information_responsible
  business role   = context（来自 group，不来自 ORM type）
  field capability= relation（many2one 描述符，独立于 role）
  hydration       = 首屏必须有值（context 角色优先）
```

教训：不能因为 many2one 就把字段归入从属 relation 区域；`role`（业务语义）与
`relation capability`（字段类型能力）是两个独立维度。

## 5. 生命周期判定规则

1. ViewField 是 Native Projection 的事实，不自动等于业务字段。
2. BusinessField 必须有唯一命名 group 归属证据。
3. HydrationField 按「首屏事实 + 表达式依赖 + fact 标记」三路闭包选择。
4. TechnicalDependency 只服务表达式求值，不作为业务展示。
5. RelationField 由字段描述符类型 + relation_entry 契约决定，不由 role 决定。

