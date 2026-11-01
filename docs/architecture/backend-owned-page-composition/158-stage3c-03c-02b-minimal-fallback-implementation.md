# 158 · BNVA-019 Stage 3C-03C-02B · 最小回退实现

## 目标

替换 `build_form_structure_contract` 的 DEFAULT 字段名启发式回退。

## 变更

- `addons/smart_core/handlers/ui_contract_v2_form_structure.py`
  - 删除字段名启发式（identity / relation / term / amount / status / history 等）。
  - 回退返回最小结构：`slots=[]`、`fieldRoles={}`、`fieldOwnership={}`。
  - 保留权威标记：`entry_semantic_surface` 仍输出
    `structureSource=entry_semantic_surface / structureAuthority=task_sections /
    mode=business_task_form / presentationMode=task`。
  - 其余回退输出 schema 合法值：`structureSource=native_view /
    structureAuthority=container_tree / mode=minimal_fallback /
    presentationMode=workspace`。
  - `governance_source` 恢复使用 `formal_governance_source(governance)`，保留
    `formColumns` 等溯源。

## 约束

- 不回退猜测业务归属。
- 不伪装为成功空结构；`pageComposition` 因空 ownership 分类为
  `unclassified_historical` 并携带 V10 诊断。
- 显式 `entry_semantic_surface` 路径保持可区分。

