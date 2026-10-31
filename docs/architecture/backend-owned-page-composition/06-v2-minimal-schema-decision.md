# 06 · V2 Minimal Schema Decision

## Decision

REUSE + MINIMAL EXTEND。

## Reasons

- `formStructureContract` 已有 slots / fieldRefs，可承载页面结构。
- `field_groups` 已有数据通道，但本页未填充，可复用。
- `page_orchestration` 未进入本页，暂不新增。
- 缺的是“字段主展示职责唯一”的显式声明。

## Recommended minimal extension

在现有 V2 结构内增加可选的 `fieldOwnership`：

```text
fieldOwnership:
  project_code: identity
  user_id: identity
  manager_id: identity
  owner_id: section:basic_information
  cost_manager_id: section:responsibility
  doc_manager_id: section:responsibility
```

不新增独立 page.composition 顶层结构，避免与 formStructureContract 重复。

## Next

1. 用现有 `formStructureContract.slots` 表达 identity / business sections。
2. 用 `field_groups` 表达分组。
3. 用 `fieldOwnership` 表达唯一归属。
4. 正式页面关闭 `coreFieldNames` / `advancedFieldNames` 隐式补齐。

