# 104 · BNVA · 平台内核架构（利用 Odoo 体系能力）

## 定位

BNVA 不是优化 smart_core 模块内部，而是建立一层**薄的内核投影层**：把 Odoo 原生
`ir.*` 内核作为唯一事实来源，投影成契约，不重复实现、不猜测第二套结构。

## Odoo 原生内核能力（实测确认）

| Odoo 内核 | 提供什么 | 内核投影层应如何使用 |
| --- | --- | --- |
| ir.ui.view.get_view() | 合并继承后的 arch + id + model | 唯一视图组合入口 |
| ir.ui.view._get_combined_arch | 继承合并后的 arch | 视图组合真相 |
| ir.ui.view._postprocess_access_rights(tree) | 按 ACL 在 arch 上标记字段 readonly/不可见 | 权限投影（避免自建） |
| ir.model.fields | 字段 type / field_description / required / readonly | 字段元数据真相 |
| fields_get() | 用户可见字段元数据投影 | 字段描述投影 |
| ir.model.access | 模型级 CRUD 权限 | statusContract 权限 |
| ir.rule | 记录级 domain 规则 | 行级权限（domain） |
| ir.actions.act_window | view_mode / domain / context / search | 动作身份与默认域 |

## 内核投影层组成（P0 smart_core）

```text
Odoo 原生内核 (ir.ui.view / ir.model.fields / ir.model.access / ir.rule / act_window)
        ↓ 只读投影
NativeViewProjection      arch → Canonical AST（解析一次）
FieldMetadataProjection   fields_get / ir.model.fields → 字段描述符
PermissionProjection      _postprocess_access_rights + ir.model.access + ir.rule → status
BusinessSemanticEnrichment 仅补充配置声明的 identity/section，不按字段名猜
        ↓
ContractAssembler         统一输出 containerTree / slots / fieldGroups / fieldOwnership
        ↓
Vue Contract Renderer     消费契约，不做结构推导
```

## Canonical AST（内核投影层的唯一结构事实）

```text
NativeView
  identity(model, action_id, view_id, view_type)
  containers[](id, native_name, native_type, parent_ref, children[])
  fields[](field_code, occurrence_index, container_ref, native_locator, modifiers_raw, field_metadata)
  provenance(source_view_id, inherited_view_chain, runtime_context)
```

设计要点：

1. 原生 `<group name>` 是容器稳定身份，不是临时数组下标。
2. 同字段多次出现保留 occurrence_index，不合并丢失。
3. modifiers 保留 raw 表达式；后端仅解析静态字面量，记录相关表达式移交前端。
4. 权限裁剪后的结构必须与当前用户 get_view() 结果一致，不得用 sudo 补全结构。

## 关键架构决定

1. **权限投影复用 `_postprocess_access_rights`**：不再自建字段访问裁剪逻辑。
2. **fieldOwnership 由原生字段位置推导**：字段属于哪个 `<group name>` 就归属哪个组，
   删除 identity/relation/term/amount 字段名启发式。
3. **业务语义只来自显式声明**：identity/section 由 P1 配置声明，不由字段名推断。
4. **内核不承载业务语义**：smart_core 只做通用投影；行业语义留在 smart_construction_core。

## 与模块的关系

- `form_structure_authority.py` → 业务语义声明解析入口（P1 配置 → identity/section）。
- `ui_contract_v2_form_structure.py` → 原生结构投影（group → slot/group 映射）。
- `ui_contract_v2.py` → 内核投影编排（get_view + fields_get + 权限投影）。
- `unified_page_contract_v2_assembler.py` → 统一契约输出（消费 Canonical AST）。

## 实施顺序（对齐 BNVA 批次）

BNVA-004~007 建 Canonical AST（内核投影层第一块）→ BNVA-008~011 原生 group 映射 +
fieldOwnership 重构 → BNVA-015~017 收敛 modifiers / 字段元数据 / 权限投影。
