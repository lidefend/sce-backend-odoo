# 101 · BNVA-001 · Odoo View API 能力审计

## 结论

Odoo 17 的 `get_view()` 是唯一可用的视图入口，但返回形状与现有自定义代码的假设
不一致；同时原生 arch 已携带完整业务分组（`<group name>`），而当前 fieldOwnership
推导没有复用它。

## 实测返回（candidate，project.project，view 1776，action 590）

### get_view()

```text
keys: ['arch', 'id', 'model', 'models']
arch len: 14917
fields: 0          ← get_view() 不返回 fields
toolbar: 无         ← get_view() 不返回 toolbar
```

### arch 内容

- field 节点 50 个。
- 带 `modifiers` JSON 的节点 0 个（modifiers 未预求值）。
- 带原始 `invisible` 属性的节点 11 个（如 `invisible='1'`、`invisible='not reject_reason'`）。
- 原始 `readonly` 18 个、`required` 2 个。
- `<group name>` 11 个：sc_project_submission_readiness、sc_project_information_identity、
  entity、contact、arrangement、schedule、responsible、responsibility、description、
  collaboration、trace。

### fields_view_get()

Odoo 17 已移除：`AttributeError: 'project.project' object has no attribute 'fields_view_get'`。

### fields_get()

- 返回 235 个模型字段（string / type / required / readonly）。
- reject_reason=text、validation_status=selection、source_created_at=datetime 等都在。

### ir.ui.view 可用钩子

- `_get_combined_arch`（合并继承）
- `_postprocess_access_rights`（ACL 字段访问裁剪）
- `_postprocess_on_change`

自定义代码未使用 `_postprocess_access_rights`。

## 能力矩阵

| Odoo 原生能力 | 实际返回 | 现有代码用法 | 判定 |
| --- | --- | --- | --- |
| get_view() | arch + id + model（无 fields/toolbar） | _safe_get_view_data 期望 fields/toolbar（得空） | 假设错误，需修正 |
| fields_view_get() | 已移除 | 版本兼容 fallback | 死代码，可删 |
| fields_get() | 235 模型字段元数据 | 用于字段元数据补齐 | 正确 |
| arch <group name> | 11 个原生业务组 | containerTree 保留，但 slot/group 推导未复用 | 核心问题 |
| arch modifiers | 原始表达式（未求值） | 自定义 safe_eval 求值 | 必要（或移交前端） |
| _postprocess_access_rights | ACL 字段访问 | 未使用 | 权限投影可复用 |

## 对 #99 的修正

1. **modifiers 不是纯重复**：`get_view()` 返回的是未求值的原始表达式，后端要么自行
   求值（当前 safe_eval），要么移交前端求值。不能简单说“Odoo 已算好”。
2. **fields/toolbar 假设错误**：自定义 `_safe_get_view_data` 期望 get_view 返回 fields，
   但 Odoo 17 不返回，所以 fields 全靠 fields_get 补齐——这条链是“绕”但部分必要。
3. **业务结构双轨仍是核心**：原生 `<group name>` → 字段成员就是权威业务结构，
   fieldOwnership 应直接由此推导，而不是字段名启发式。

## 后续任务

- BNVA-002：追踪 contract_Parser / page_assembler / ui_contract_v2 的解析链重复。
- BNVA-003：modifiers 求值职责边界（后端 safe_eval vs 前端运行时求值）。
