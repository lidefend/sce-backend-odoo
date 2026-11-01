# 145 · BNVA-019 Stage 3C-03B · Assembler 职责核验

## 核验

- `unified_page_contract_v2_assembler.py` 不再定义或调用容器名称启发式。
- 容器语义归一由 `layout_semantics.py` 承担。
- Assembler 仍承担 `_normalize_native_layout_nodes`（布局归一）、
  `normalize_form_structure_contract_roles`、业务结构投影应用、最终组装。

## 结论

Assembler 只剩契约规范化与最终组装，不再承担容器名称启发式。

