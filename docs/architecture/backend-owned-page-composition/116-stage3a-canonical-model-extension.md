# 116 · BNVA-019 Stage 3A · Canonical Model Extension 实施记录

## 目标与范围

在 `native_view_projection.py` 完善统一内部模型，只扩展内部字段，不改变
formStructureContract / layoutContract 输出。

## 新增内部字段

### NativeContainer.native_attributes

保留布局适配器需要的原生节点属性（全部为字符串，可序列化）：

```text
class, colspan, col, span, groups, attrs
```

不采集全部 XML 属性；每条都有明确消费对象。

### NativeFieldOccurrence.native_attributes

```text
string, widget, options, placeholder, nolabel, colspan, sum,
attrs, invisible, readonly, required, groups
```

### NativeFieldOccurrence.relation_descriptor

由当前用户 `fields_get()` 元数据派生：

```text
field_type / relation_type / relation_model
```

仅 `many2one / one2many / many2many` 生成；非关系字段为 `None`。不含
`relation_capabilities`（暂无明确依据，预留），且明确不是权限授权来源。

## 结构身份（未改变）

occurrence_index / container_ref / native_locator / parent_ref / provenance 保持
不变；第一次出现不自动成为 primary owner（沿用 Stage 前的单命名 group 规则）。

## 契约隔离

`build_native_form_structure_contract` 的输出不含 `native_attributes` /
`relation_descriptor`，新增内部字段不自动进入 formStructureContract /
layoutContract / fieldOwnership / pageComposition。

