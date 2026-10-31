# Backend-Owned Page Composition v1

## Goal

后端配置与 Unified Page Contract / V2 是页面结构、字段归属和展示职责的唯一
权威来源；前端只消费契约，不自行生成第二套业务结构。

## Current findings

### Existing backend capabilities

- `formStructureContract`：已承载 form surfaces / slots / fieldRefs。
- `field_groups`：已作为 `dataContract.dataMeta.fieldGroups.groups` 进入 V2。
- `page_orchestration`：已存在页面编排通道。
- `semantic_page`：已承载 list/relation 语义。

因此后端并非完全没有字段分组能力，但还没有形成“字段主展示职责唯一”的
页面级治理。

### Frontend fallback that still owns structure

`useRecordFormFieldSchemas.ts`：

```ts
buildLegacyLayoutNodes({
  fields: formFields.value,
  order: [],
  visibleFields: contractVisibleFields.value,
  fallbackFieldNames: [...coreFieldNames, ...advancedFieldNames],
  ...
})
```

`buildLegacyLayoutNodes` 在 `order` 为空时，会用
`visibleFields` / `fallbackFieldNames` 自行补齐字段。这是正式页面第二套
字段来源，也是 B1 身份重复的上游原因之一。

## Required governance model

建议契约增加或显式使用以下结构语义：

```text
page.composition.identity.fields
page.composition.business_sections[].fields
page.field_ownership.<field> = identity | section_id | relation
```

目标是区分：

- 字段主展示职责。
- 关联对象引用。
- 业务明细。
- 只读摘要。

不能简单按字段名全局去重。

## Governance constraints

1. 页面结构只能有一个权威来源：
   - `formStructureContract` 负责结构、Slot、字段引用。
   - `field_groups` 负责字段分组与组织关系。
   - `page_orchestration` 负责页面区域组合与呈现顺序。
   - 三者必须由统一 V2 页面结构协调，前端不能分别消费后自行拼装。

2. 字段所有权必须有明确语义：
   - `identity`
   - `section:<section_id>`
   - `relation:<relation_id>`
   - `detail:<detail_id>`
   - 不同业务对象引用同一用户，不等于字段重复。

3. 正式页面禁止隐式补齐：
   - 正式业务页面禁止 `coreFieldNames` / `advancedFieldNames` 补齐。
   - Legacy fallback 只能用于配置编辑器或诊断模式，并显式标记来源。
   - 契约缺失必须失败关闭或明确报告，不得静默补出看似正常的页面。

4. 权限仍由服务端决定：
   - 页面结构声明不能授予权限。
   - 展示字段必须继续受 ACL、Record Rules、字段 groups 和只读状态约束。

## Implementation stages

1. 契约治理：建立唯一页面结构声明，补 identity/section ownership 和校验。
2. 前端收缩：正式页面停止隐式补齐，Legacy fallback 转为诊断能力。
3. 页面迁移：先以 PC-01 项目身份页验证，再迁移基本信息、责任信息、关系与协作。

## Platform gate

新增 `Page Composition Integrity Guard`：

- 正式页面必须声明唯一结构来源。
- 同一字段不得被重复分配主展示职责。
- Section 必须有稳定身份。
- 字段引用必须存在且适用。
- 正式页面不得隐式 fallback 补齐。
- 展示声明不得与服务端权限冲突。
- 新旧机制不得同时作为权威来源。

重复字段校验必须结合模型、业务对象、字段角色和 Section 身份，不能只按字段名。

## Migration and exit criteria

- `coreFieldNames` / `advancedFieldNames` 只能用于校验和配置编辑器，
  不得用于正式页面字段补齐。
- `buildLegacyLayoutNodes` 的 fallback 只在契约缺失且允许的诊断模式下使用，
  不应成为正式页面第二权威来源。
- 正式页面必须由 V2 `formStructureContract` / `fieldGroups` 决定 Section 字段。

## Status

- B1 身份重复根因：页头摘要与原生表单 group 字段所有权重叠。
- 后端权威配置机制：已有部分能力，缺少页面级字段主展示职责治理。
- 实施顺序：先补契约声明，再收缩前端 fallback，最后迁移旧页面。

