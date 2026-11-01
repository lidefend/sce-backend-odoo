# 108 · BNVA-019-03 · Native AST 与 V2 字段映射

> 目标：把 Canonical NativeView 的每个字段逐项映射到 V2 契约输出，消除歧义。

## 1. 映射总表

| NativeView 字段 | V2 输出 | 规则 |
| --- | --- | --- |
| `identity.model` | `pageInfo.model` | 原样 |
| `identity.action_id` | `pageInfo` / action 契约 | 原样 |
| `identity.view_id` | `pageInfo.viewId` / provenance | 原样 |
| `identity.view_type` | `pageInfo.viewType` | 原样 |
| `containers[]` | `layoutContract.containerTree` | 保结构身份 |
| `containers[].native_name` | container `name` / group identity | 保原生身份 |
| `containers[].native_type` | container `type` | 原样 |
| `containers[].native_locator` | provenance（内部） | 保定位 |
| `fields[].field_code` | FieldRef / widgetId | 原样 |
| `fields[].occurrence_index` | widgetId `.occ.*` / occurrence | 不去重 |
| `fields[].container_ref` | group / slot 映射 | 保留 |
| `fields[].modifiers_raw` | Modifier Contract（raw） | 不求值 |
| `fields[].field_metadata` | Field Descriptor | 按字段描述符投影 |

## 2. 字段身份与出现次数

同一字段在 Form View 多次出现必须保留多个 occurrence，每个 occurrence 有独立的
invisible/readonly。字段名不是唯一节点身份；稳定身份是
`field_code + occurrence_index + native_locator`。

## 3. 容器 → slot/group 映射

| Odoo 原生 | V2 业务 |
| --- | --- |
| sheet | slot 候选（默认一个） |
| `<group name>` | group（稳定身份 = 原生 name） |
| `<field>` | FieldRef（归属其所在 group / sheet） |
| notebook / page | 保留层级，不强行压平 |

`identity_fields` 只标记 identity 语义，不改变字段原生位置。

## 4. FieldOwnership 生成约束

- 字段只出现在一个命名 group → 候选 primary owner。
- 字段出现在多个命名 group → 不按出现顺序选主，保持 unowned（NOT_VERIFIED）。
- 技术字段、隐藏依赖、关系子视图字段有独立处理语义，不塞进 ownership map。

## 5. 契约最小充分原则

V2 不是 Odoo XML 的 JSON 翻译器，也不是 ORM 全量序列化。只输出当前页面需要、
可追溯到原生节点或业务配置、且有明确消费对象的信息。

