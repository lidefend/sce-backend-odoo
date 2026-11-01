# 168 · BNVA-02A · 业务结构覆盖

## 结构事实来源

| 结构 | 来源 | 说明 |
| --- | --- | --- |
| slots | Business Adapter（原生 group / 配置 sections） | 业务区域 |
| fieldGroups | 配置 field_groups / 原生命名 group | 字段分组 |
| fieldOwnership | Business Adapter 投影 | 唯一主归属 |
| containerTree | Layout Adapter | 布局拓扑 |
| Identity | 显式 `identity_fields` 声明 | 不按类型/名称/顺序推断 |
| Section | 配置 sections / 原生 group | 业务分区 |
| primary owner | fieldOwnership 唯一记录 | 不自动选首次出现 |

## 覆盖缺口（系统性）

`entry_semantic_surface` 配置普遍只声明 `sections: [{title: ...}]`，不含字段成员。
`form_structure_authority` 仅在 section 带 `fields` 时才生成 `field_groups`；仅有
title 的 section 只进入 `section_titles`。结果是 `task_sections` 权威 + 空
fieldGroups/ownership，页面被判 `unclassified_historical`。

结论：**section 标题 ≠ 字段归属**。这是 BNVA-02B 首先要补的最小表达缺口。

