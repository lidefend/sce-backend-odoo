# 144 · BNVA-019 Stage 3C-03B · Layout 语义迁移实施

## 迁移

将 V2 Assembler 中的容器名称启发式迁移到 Layout Adapter：

`app_config_engine/services/view_Parser/layout_semantics.py`

迁移函数：`_node_field_names` / `_node_field_types` / `_node_text_fingerprint` /
`_node_has_token` / `_node_has_x2many` / `_node_has_direct_group_child` /
`_is_generic_container_label` / `_is_technical_container_identifier` /
`_semantic_group_label` / `_apply_semantic_container_label` /
`_apply_semantic_container_annotation` / `_business_group_label_for_node` /
`standardize_form_container_semantics`。

同时移除无操作的 `_standardize_business_form_default_tabs`。

## Assembler 侧

`_assemble_ui_contract` 改为惰性导入并调用
`standardize_form_container_semantics`，不再定义这些函数。

## 边界

只做布局语义标记（semanticTitle / semanticAnchor / 技术容器识别），不推导
Identity / Section / fieldOwnership / businessRole。

