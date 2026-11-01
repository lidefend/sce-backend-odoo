# 106 · BNVA-019-01 · Odoo 原生信息全集盘点

> 目标：把 Odoo 原生视图实际提供的信息逐项盘点，作为 Contract Admission 的输入。
> 本轮只读，不修改产品代码。

## 1. 信息来源（Odoo 17 内核）

| 来源 | 提供内容 | 在代码中的消费点 |
| --- | --- | --- |
| `ir.ui.view.get_view()` | 合并继承后的 `arch` + `id` + `model` | `core/native_view_projection.py:114` |
| `ir.ui.view._get_combined_arch` | 继承合并后的 XML | `get_view()` 内部 |
| `ir.ui.view._postprocess_access_rights` | 按 ACL 在 arch 上标记字段 readonly/不可见 | Odoo 内核 |
| `ir.model.fields` | 字段 type / string / required / readonly / relation | `fields_get()` 内部 |
| `model.fields_get()` | 当前用户可见字段元数据投影 | `native_view_projection.py:119` |
| `ir.model.access` | 模型级 CRUD 权限 | `page_assembler._model_access_allows` |
| `ir.rule` | 记录级 domain 规则 | `page_assembler._record_rule_*` |
| `ir.actions.act_window` | view_mode / domain / context / search | `action_dispatcher` / `page_assembler` |

## 2. 原生 arch 节点信息（form）

`native_view_projection.project_native_view` 把合并 arch 解析为 `NativeView`：

- `containers[]`：`container_ref` / `native_name` / `native_type` /
  `native_string` / `parent_ref` / `native_locator` / `children`。
- `fields[]`：`field_code` / `occurrence_index` / `container_ref` /
  `native_locator` / `modifiers_raw` / `field_metadata`。
- `provenance`：`source_view_id` + 受控的 `runtime_context`（lang / tz /
  allowed_company_ids / contract_action_id）。

结构容器标签集合（`_STRUCTURAL_TAGS`）：

```text
form, sheet, group, notebook, page
```

### 已保留的原生事实

| 原生事实 | 是否保留 | 位置 |
| --- | --- | --- |
| 容器层级 | 保留 | `containers[].children/parent_ref` |
| 原生 group name | 保留（稳定身份） | `containers[].native_name` |
| 字段出现次数 | 保留（不合并） | `fields[].occurrence_index` |
| 原生定位 | 保留 | `fields[].native_locator` |
| 原始 modifiers | 保留（不求值） | `fields[].modifiers_raw` |
| 字段元数据 | 保留 | `fields[].field_metadata` |

### 已知缺口（BNVA-019-03 处理）

- `div` 等非结构容器被遍历但**不作为独立容器保留**，深层嵌套字段的容器归属
  可能退化为 `sheet` 级，不能完整表达任意 Odoo Form Layout。
- `build_native_form_structure_contract` 目前只投影 sheet 的直接
  `group/notebook/page` 子节点；嵌套 notebook/page 内部的 group 未被完整投影。

## 3. 原生 field 属性（modifiers / widget / placeholder）

`modifiers_raw` 目前只投影 `invisible` / `readonly` / `required` 三个属性；
`widget` / `placeholder` / `options` 等原生 field 属性由
`page_assembler` / `ui_contract_v2` 的既有字段描述符路径承载，不在 Canonical
AST 内统一。

## 4. 关系字段与子视图

- `fields_get()` 提供 `relation` / `relation_field` 描述符。
- 子视图（form 内的 one2many/many2many 内嵌 tree/form）由
  `page_assembler._inject_relation_entry_contract` 与
  `unified_page_contract_v2_assembler` 的关系描述符路径处理。

## 5. 权限相关原生信息

| 信息 | 归属 | 是否进入页面结构契约 |
| --- | --- | --- |
| 用户可见字段集 | Odoo `get_view()` / `fields_get()` 裁剪结果 | 是（作为当前用户事实） |
| 字段 readonly/required/invisible | 原始表达式 | 是（原始表达式） |
| ACL / Record Rules 原始规则 | Odoo 权限服务 | 否（只投影结果） |
| 超级用户环境 | 服务端执行上下文 | 否 |

