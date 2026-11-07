# 前端业务语义表达矩阵 v1

状态：EXP-01 诊断产物，用于确定九类高频业务事实的“单源权威”。本矩阵先立规则，不立即改动组件。

## 三条核心原则

1. 统一的是**业务语义**，不是要求所有页面用同一个组件。同一业务事实允许多种展示形态（适配器），但不允许多套互相矛盾的语义解释。
2. 平台分层：平台设计系统（视觉原语）→ 平台表达层（语义映射/字段渲染/页面组合）→ 行业扩展层（专业组件/领域模型/业务规则）→ 企业配置层（实际启用能力）。
3. 公共组件必须有明确权威消费者：禁止组件存在却被绕过、两个组件无职责区分地承担同一语义、同一字段在不同入口结果不同、行业模块重复实现平台已有规则。

## 九类事实矩阵

| 业务事实 | 语义由谁定义 | 契约来源 | 权威消费者 | 允许的适配器 | 禁止的重复实现 | 一致性证明 |
| --- | --- | --- | --- | --- | --- | --- |
| 金额 | 模型字段类型 + `currency_id` 的币种/精度 | `dataContract.mainData` + `fields[].type=monetary` + 币种字段 | `ScMoney` + 唯一共享格式化器 `formatMoney(value, currency, precision, locale)` | 列表单元格、详情只读、表单输入、审批金额摘要 | 组件内局部 `fmtMoney`（现 `PaymentSettlementIntroduceDialog.vue:271`）；各业务自定千位/负数/精度 | 静态守卫：仅 `utils/money.ts` 可导出金额格式化器；`ScMoney` 只接收格式化后的 `display` |
| 日期 | 字段类型 date/datetime + 用户语言/时区 | `fields[].type` + `statusContract` 只读/必填 | 分层：`ScDatePicker`=日期选择交互原语；`ScDateField`=标准表单日期字段表达；`formatTemporalFieldValue(value,'compact')`=列表日期展示适配 | 列表单元格、详情只读、表单字段 | 业务组件绕过两层直接内联日期控件或自定格式化 | 组件层级图 + 静态守卫：表单日期只经 `ScDateField`；列表/详情只经 `formatTemporalFieldValue` |
| 状态 | 契约 `statusContract` + 字段 status | `statusContract.widgetStatus/containerStatus/globalStatus` + 字段状态 | `ScStatusBadge`（原语）← `ProductRecordStatus`（记录级包装） | 列表状态列、详情状态、表单状态条 | 业务组件自行映射状态文案/颜色，形成第二套状态语义 | 状态 tone/label 只由 `statusContract` 决定；守卫禁止组件内硬编码状态映射 |
| 空值 | 平台统一空值常量 | 契约缺失/null/false | `FIELD_VALUE_EMPTY_TEXT`（`utils/fieldSemantics.ts:49`） | 列表、详情、表单、摘要 | 各页面自定 `'-'`/`'--'`/`'暂无'`；数值空与文本空未区分说明 | 唯一常量 + 守卫禁止新空值字面量 |
| 关系 | `relation_entry` 声明 + 字段类型 | 字段 descriptor 的 `relation_entry` | v2 表单：`ProfessionalBaseFieldControl` 关系分支；视图：`ViewRelationalRenderer`；原语：`ScRelationField` | many2one/many2many/one2many 标签、搜索、只读、明细 | 业务组件直接读写关系并自造弹窗/搜索（现 `PaymentSettlementIntroduceDialog` 需归入行业层） | 关系入口只经 relation_entry；守卫禁止绕过统一关系渲染 |
| 只读 | 字段策略 + 记录能力 | 字段 readonly 策略 + `effectiveRecordCapabilities` | `ProfessionalBusinessValueControl`（只读值）与 `ProfessionalBaseFieldControl`（读写判定） | 表单、详情、列表 | 组件用自身判断绕过契约 readonly | 只读判定只来自契约；守卫禁止前端特判模型/字段只读 |
| 权限 | 契约授权结果 | `statusContract.globalStatus.effectiveRecordCapabilities` + 动作 authority + 关系 can_* | 契约授权结果 + `contractGapError` fail-closed | 按钮禁用、操作入口、关系打开/新建 | 前端从方法名/模型名推断权限（`app/contract/contractGap.ts` 已 fail-closed） | 权限消费只读契约；守卫禁止未登记的前端权限判断 |
| 校验 | 契约 `validation_rules` + 后端错误 | `validation_rules` + `BusinessFieldError` 回执 | `ProductFormErrorSummary`（包装 `ScErrorSummary`）为唯一摘要；字段级提示同一错误源 | 摘要、字段提示、聚焦定位 | 页面自建第二套错误聚合或字段错误映射 | 错误源唯一；守卫禁止第二套 `fieldErrors` 生产者 |
| 动作 | `actionContract.actionRuleList` + workflow 语义 + 授权 | `actionContract` + `workflowActionAvailability` + `actionRuleAuthority` | Action Renderer Registry（`app/renderers/actionSurfaceRendererRegistry.ts`） | 页头、行内、批量、审批 | 业务页面绕过 registry 直接 dispatch 动作；同一动作多个入口不同去向 | 动作只经 registry；守卫禁止未登记动作分发 |

## 当前已知偏差（治理对象，不在本轮修改）

- 金额：`PaymentSettlementIntroduceDialog.vue` 内局部 `fmtMoney`。
- 日期：`ScDatePicker` 与 `ScDateField` 职责未在文档明确。
- 状态：`StatusPanel` 是页面错误/建议面板，与业务状态 badge 语义不同，需在文档中区分，避免误用。
- 关系：行业专用结算弹窗位于通用 `professional-fields`。
- 空值：存在 `COLLECTION_NUMERIC_EMPTY_TEXT` 与文本空值的合法差异，需登记为两种已声明空值，而非散落实现。

## 落地顺序

1. 按 EXP-01A/01B/01C 分别收敛金额、日期与字段渲染、行业边界。
2. EXP-02 把本矩阵转成可执行静态守卫。
3. EXP-03 用付款申请完整旅程验证。
