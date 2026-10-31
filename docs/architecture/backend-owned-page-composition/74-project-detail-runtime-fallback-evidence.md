# 74 · Project Detail Runtime Fallback Evidence（PC-007）

## 样本

- project.project / Action 590 / View 1776
- project.project / Action 652 / View 944

## 结论

PC-007 = NOT_VERIFIED（两个入口一致）

源码存在与调用链可达已核验，运行时实际执行与实际影响 DOM 仍未闭环。

## 四个证据等级

| 等级 | 状态 |
| --- | --- |
| 源码存在 | SOURCE_VERIFIED（文件 + SHA-256 已核验） |
| 调用链可达 | 静态可达（代码路径确认） |
| 运行时实际执行 | NOT_VERIFIED |
| 实际影响最终 DOM | NOT_VERIFIED |

## 源码链

- `useRecordFormFieldSchemas.ts:106`：`layoutNodes` 计算属性无条件调用
  `buildLegacyLayoutNodes`，传 `order: []`、`fallbackFieldNames:[...coreFieldNames,
  ...advancedFieldNames]`。
- `nativeLayoutUtils.ts:691`：`buildLegacyLayoutNodes` 定义。
- `nativeLayoutUtils.ts:758`：`order` 为空时进入 fallback 分支，用
  `visibleFields` 或 `fallbackFieldNames` 补齐字段。
- `ContractFormPage.vue:2084`：`formStructureContract.structureAuthority ===
  'container_tree'` 时采用 native container-tree 快照，否则为空。
- `layoutNodes` 消费点：`ContractFormPage.vue:820/1415/1427/1727/1873/1888`。

## 关键判断

- 源码存在不证明运行时执行；本轮不把源码存在等同于页面依赖 fallback。
- 先前的运行时观察（`data-form-composition = legacy-form-section +
  official-standard-detail`、NativeFormTreeRenderer 30 实例）来自历史会话，
  本轮未重新取得 DOM 级运行时证据，故不据此断言。
- 两个入口必须分别采集运行时证据，不互相套用。

## 证据

机器可读：`evidence-bundle-project-590.json` / `evidence-bundle-project-652.json`
（PC-007 两条 SOURCE_STATIC 证据：nativeLayoutUtils.ts、useRecordFormFieldSchemas.ts）。
