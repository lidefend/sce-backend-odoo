# 142 · BNVA-019 Stage 3C-03A · 迁移优先级

## 可迁移（3C-03B 范围）

| 逻辑 | 目标 | 优先级 |
| --- | --- | --- |
| `_standardize_form_container_semantics` 等名称启发式 | Layout Adapter 独立模块 | P1 |
| `_page_composition_contract` 旧 ownership 兜底 | Business Adapter（仅旧路径，或移除） | P2 |

## 必须留在 Assembler

- `_normalize_native_layout_nodes`（最终 containerTree 归一）。
- `normalize_form_structure_contract_roles`（legacy role → canonical）。
- `_project_form_structure_to_layout` / `_apply_form_structure_roles_to_tree`
  （业务结构投影到布局树，契约一致性）。
- 最终 V2 Contract 组装与 version/schema 维护。

## 原则

- 不重写 Assembler。
- 不改变公开契约。
- 不以代码行数减少为验收标准。

