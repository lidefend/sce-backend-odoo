# 140 · BNVA-019 Stage 3C-03A · 重复逻辑矩阵

## 分类

| 类别 | Assembler 内 | 归属 | 判定 |
| --- | --- | --- | --- |
| 原生 arch 重读 | 无 | — | 已收敛 |
| XML 重解析 | 无 | — | 已收敛 |
| 容器结构重建 | `_normalize_native_layout_nodes` | Layout Adapter（最终归一） | 规范化，可保留 |
| 业务 role 推导 | `_apply_form_structure_roles_to_tree` | Business Adapter（投影结果应用） | 投影，非重推导 |
| fieldOwnership 归一 | `_page_composition_contract` | Business Adapter | 归一 + 旧兜底 |
| 容器语义名称启发式 | `_standardize_form_container_semantics` / `_semantic_group_label` / `_is_technical_container_identifier` | Layout Adapter | 应迁移 |
| 旧 ownership 兜底 | `_page_composition_contract` 的 primary_facts/other_facts catch-all | Business Adapter（或移除） | 仅旧启发式路径 |

## 结论

无原生 arch 重读/重解析。剩余是「契约归一」与「容器语义名称启发式」的职责迁移。

