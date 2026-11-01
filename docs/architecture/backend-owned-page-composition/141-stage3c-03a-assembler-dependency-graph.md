# 141 · BNVA-019 Stage 3C-03A · Assembler 依赖图

## 调用链

```text
ui_contract_v2._handle_contract（请求编排）
  ├─ _dispatch_native_form_source → page_assembler（LDP，get_view 一次）
  ├─ _enrich_native_form_composition → native_view_projection（NCP，Carrier 复用）
  └─ assemble_unified_page_contract_v2（V2 Assembler）
        ├─ 消费 source["formStructureContract"]（NCP 产物）
        ├─ 消费 source["views"]["form"]["layout"]（LDP 产物）
        ├─ _normalize_native_layout_nodes → containerTree
        ├─ _project_form_structure_to_layout / _apply_form_structure_roles_to_tree
        ├─ _page_composition_contract → fieldOwnership + pageComposition
        └─ 最终 V2 Contract
```

## 输入来源

| 输入 | 来源 | 是否重新解析 |
| --- | --- | --- |
| formStructureContract | NCP | 否 |
| views.form.layout | LDP | 否 |
| field_ownership | NCP | 否 |

## 输出

containerTree / formStructureContract / fieldOwnership / pageComposition /
statusContract / dataContract / layoutContract。

