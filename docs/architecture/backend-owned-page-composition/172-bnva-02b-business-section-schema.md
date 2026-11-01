# 172 · BNVA-02B-01 · 业务 Section 显式声明规范

## 现有表达

`ui.business.config.contract` 的 `contract_json.view_orchestration.views.form.sections`
已是 Section 载体。单个 section 条目现有字段：

```json
{"key": "identity", "title": "项目身份", "fields": ["name", "project_code"],
 "semantic_role": "identity", "columns": 1, "visible": true}
```

`form_structure_authority` 仅在 section 带非空 `fields` 时才生成 `field_groups` 与
`configured_sections`；只有 `title` 的 section 只进入 `section_titles`。

## 最小规范（不新增平行 Schema）

每个业务 Section 必须声明：

| 键 | 必填 | 语义 |
| --- | --- | --- |
| key | 是（Formal） | 稳定业务 Section 身份，不随标题变化 |
| title | 是 | 显示标题 |
| fields | 是，非空 | 字段成员列表 |
| semantic_role | 否 | 摘要/上下文/明细/审计等 |
| native_group | 否（见 175） | 原生 Group 显式映射 |
| columns | 否 | 24 格布局列数 |

## 准入规则

- 只有 `title` 没有 `fields` 的 section 不得获得 Formal 准入（ERROR）。
- `fields` 空数组视为缺失（ERROR）。
- `fields` 引用不存在的模型字段（ERROR）。
- 同一 section 内字段去重；跨 section 重复必须声明辅助投影（见 174）。
- `key` 缺失时 `title` 只能作为兼容显示键，不构成稳定身份（WARNING）。

## 反向样本解释

- project 590：native_semantic_surface，section 由原生 group 提供，含字段。
- payment.request `views.form={}`：无 section → ERROR（占位配置）。
- execution/receipt 的 entry_semantic_surface：仅有 title section → 缺 fields，ERROR。

