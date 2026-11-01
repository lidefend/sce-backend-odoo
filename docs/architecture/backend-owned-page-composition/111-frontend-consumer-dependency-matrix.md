# 111 · BNVA-019-06 · 前端消费依赖盘点

> 目标：把 V2 契约每个子结构与其前端消费者一一对应，防止 declared-but-unconsumed。

## 1. 消费者矩阵

| 契约子结构 | 前端消费者 |
| --- | --- |
| `layoutContract.containerTree` | `canonicalFormRenderer` / `nativeSectionNavigation` |
| `formStructureContract.slots` | `nativeSectionNavigation` / `formFieldLabels` |
| `formStructureContract.fieldRoles` | `legacyLayoutNormalizer` / `canonicalNativeFormBridge` |
| `formStructureContract.fieldOwnership` | 治理/诊断（`schema.ts` 解码） |
| `formStructureContract.structureAuthority` | `legacyLayoutNormalizer` |
| `dataContract.mainData` | `useRecordFormLayout` / `readonlyMainDataCoverage` |
| `dataContract.dataMeta.fieldGroups` | `BoundFormSettingsPanel` / 配置面 |
| `statusContract.widgetStatus` | `contractFormPresenter` |
| `modifiers`（raw） | `nativeModifierComparison` / 运行时求值 |
| `relation_entry` | `RelationSearchDialog` / `record_relation_roundtrip` |

## 2. 关键消费事实

- 关系导航（openable）由 `relation_entry` 与字段描述符类型驱动，不由
  `fieldRoles.role === "relation"` 驱动。
- `fieldRoles.role` 只允许 canonical 集合：summary/task/context/risk/
  relation/activity/audit（`formStructureRoles.ts`）。
- `fieldOwnership` 解码只读 `ownerSlotRef` / `ownerGroupRef`
  （`schema.ts` `decodeFieldOwnership`），未知键被拒绝。

## 3. 约束

- 任何契约子结构的新增字段，必须同时核对该字段的 schema 解码器
  （`rejectUnknownKeys`）与下游消费者，不能悄悄加键。
- 前端不得重新推导后端已确定的 fieldOwnership / businessRole。

