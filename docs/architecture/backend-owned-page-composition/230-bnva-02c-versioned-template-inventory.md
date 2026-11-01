# 230 · BNVA-02B-02C-02C-01 · 版本化模板资产盘点

## 精确统计（84 条 VERSIONED 记录）

- 带 sections 的记录 65 条；sections 带 fields 的 46 条；带 identity_fields 仅 1 条。

## 纠正 03B 的误判

15 个 `*_form_productization_contract.xml` **不是 title-only**：其 section 普遍带
fields（sec_fields == sec_count）。它们的真实缺口是**缺少 identity_fields**，不是
缺 Section.fields。

真正的 title-only 是 `view_orchestration_form_section_contract_data.xml` 的
`*_form_sections_v1`（19 条，sec_fields=0，多数 active=False）。

## 分类

| 组 | 数量 | 特征 | 缺口 |
| --- | --- | --- | --- |
| form_productization | 46 | entry_semantic_surface，section 带 fields | 缺 Identity |
| form_sections_v1（title-only） | 19 | section 无 fields | 缺 Section.fields + Identity |
| identity-only 伴生 | 1 | 仅 identity_fields | 无 section |
| 其余（native/tree/search） | 18 | mode 非 entry | 非本轮对象 |

