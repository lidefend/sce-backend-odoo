# 02 · field_groups Audit

## Actual V2 output

Action 590 / View 1776：

```text
dataContract.dataMeta.fieldGroups = null
```

## Assessment

- 后端有 `field_groups` 数据通道，也能进入 `dataMeta.fieldGroups.groups`。
- 但本页真实 V2 没有 `fieldGroups`。
- 当前前端无法从该通道获得稳定分组和字段归属。

因此 `field_groups` 目前只是可选元数据通道，不是本页正式页面结构的权威输入。

