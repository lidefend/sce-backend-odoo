# 付款申请表达基线 v1（EXP-03A）

状态：只读真实基线。以 `payment.request` 为样板，对六阶段、九类事实做契约→组件→页面→可见结果的映射，区分 `PASS / DEVIATION / NOT_VERIFIED`。本轮未改产品代码。

## 六阶段调用链

### 1. 列表

- 页面：`pages/ListPage.vue`；单元格语义：`pages/listPage/listCellPresentation.ts`。
- 金额：`ListPage.vue:1978 formatNumericCellValue` → `ScMoney`（`ListPage.vue:1650`）。
- 日期：`formatTemporalFieldValue(value,'compact')`。
- 状态：`resolveStatusTone`（`app/presentation/collectionStatusPresentation.ts`）。
- 空值：`FIELD_VALUE_EMPTY_TEXT` / `COLLECTION_NUMERIC_EMPTY_TEXT`。

### 2. 详情 / 只读

- 页面：`pages/ContractFormPage.vue` → `ContractFormDriverHost` → `canonicalFormRenderState.model`。
- 字段渲染主链：`app/presentation/canonicalFormRenderModel.ts` → `professionalComponentRegistry.ts`（fail-closed）。
- 只读金额：`components/professional-fields/ProfessionalBusinessValueControl.vue` → `ScMoney`，`display` 来自 `formSection.mapper.formatMonetaryDisplayValue`。

### 3. 新建

- 字段输入：`ProfessionalBaseFieldControl.vue` 按 `field.type` 分发：date/datetime → `ScDateField`，integer/float → `ScNumberInput`，selection/many2one → `ScSelect`。
- 金额输入：`FormSection.vue` monetary 分支用 `formatMonetaryInputValue` + `monetaryInputStep`。

### 4. 编辑

- 只读判定：`ProfessionalBaseFieldControl` 的 `field.readonly` 分支。
- 记录状态与冲突：`pages/contractForm/useRecordPageLifecycle.ts`（record version token、冲突回读）。

### 5. 提交审批

- 动作：`app/renderers/actionSurfaceRendererRegistry.ts` + `workflowActionAvailability.ts` + `actionRuleAuthority.ts`。
- 校验：`ProductFormErrorSummary.vue` ← `ScErrorSummary.vue`；字段错误由 `saveRecordHelpers.ts` 从契约校验 + 后端回执生成。

### 6. 异常恢复

- 错误映射：`composables/useStatus.ts`（ApiError → StatusError + suggestedAction）。
- 回读：`useRecordPageLifecycle` 冲突/失败后按版本 token 重读权威记录。

## 九类事实基线

| 业务事实 | 结论 | 证据与偏差 |
| --- | --- | --- |
| 金额 | DEVIATION | 渲染权威 `ScMoney` 成立（列表/只读/首页/审批均消费）。但格式化器分叉：`formSection.mapper.ts`（表单）、`ListPage.vue:1978`（列表）、`PaymentSettlementIntroduceDialog.vue:271`（行业局部）三处，未形成单一 `formatMoney` 来源 |
| 日期 | PASS | 表单权威为 `ScDateField`（`ProfessionalBaseFieldControl` 只经它）；`ScDatePicker` 为底层交互原语；列表日期走 `formatTemporalFieldValue`。层级事实成立，但未在权威映射中显式登记 |
| 状态 | PASS | `ScStatusBadge` 原语 ← `ProductRecordStatus` 记录级；列表 tone 由 `resolveStatusTone` 从 statusContract 解析。`StatusPanel` 是页面错误面板，需与业务状态区分（未误用） |
| 空值 | PASS | 单一 `FIELD_VALUE_EMPTY_TEXT`；数值空为已登记 `COLLECTION_NUMERIC_EMPTY_TEXT` 变体 |
| 关系 | DEVIATION | 平台关系统一（many2one 走 `ScSelect` + relationOptions；视图走 `ViewRelationalRenderer`）。行业专用结算弹窗 `PaymentSettlementIntroduceDialog` 位于通用 `professional-fields`，属边界泄漏（不改注册表，迁至行业层） |
| 只读 | PASS | `ProfessionalBusinessValueControl` + `ProfessionalBaseFieldControl.readonly` 分支，只读判定来自契约字段策略 |
| 权限 | NOT_VERIFIED | 结构上消费契约授权 + `contractGapError` fail-closed；真实角色矩阵未跑，需浏览器验收确认 |
| 校验 | NOT_VERIFIED | 结构上单错误源（`ProductFormErrorSummary` + `saveRecordHelpers.fieldErrors`）；摘要/字段/聚焦同源需真实提交验证 |
| 动作 | NOT_VERIFIED | 结构上经 Action Renderer Registry；付款申请提交/审批的实际去向与失败恢复需真实旅程验证 |

## 已知偏差清单（EXP-03B 处理对象）

1. 金额格式化器三处，未单源（`formSection.mapper`、`formatNumericCellValue`、局部 `fmtMoney`）。
2. `PaymentSettlementIntroduceDialog` 及两个 `paymentSettlement*Model.ts` 位于通用 `professional-fields`。
3. `ScDatePicker` / `ScDateField` 层级未在 authority map 登记（事实成立，缺声明）。

## 本轮边界

- 未改任何组件、未改契约、未改权限。
- NOT_VERIFIED 项待 EXP-03 浏览器旅程（隔离验收数据）补齐。
