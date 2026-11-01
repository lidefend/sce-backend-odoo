# 173 · BNVA-02B-01 · Identity 显式声明规则

## 现有载体

`views.form.identity_fields`（字符串列表）是唯一 Identity 声明载体，已由
`form_structure_authority` 读取、`build_native_form_structure_contract` /
Business Adapter 消费。

## 规则

1. Identity 必须来自 `identity_fields` 显式声明；不得按字段名、ORM 类型或
   occurrence 顺序推断。
2. Identity 字段必须同时出现在某个 Section.fields 中，并具备唯一 fieldOwnership。
3. Identity 缺失时 Formal 发布判 ERROR；不得用 first-field 或字段名兜底。
4. Identity 与原生 Group 的关系由 native_group 映射表达，不由 group 名称推断。
5. Identity 与 Section 的关系：Identity 字段可在其所属 Section 内标记
   `semantic_role: identity`，但 authority 仍以 `identity_fields` 为准。

## 反向样本

- project 590 的 `identity_fields`（name/project_code/user_id/manager_id/owner_id）
  完整，可作 Formal 样板。
- payment.request / execution / receipt 未声明 `identity_fields` → 需补齐。

