# 字段渲染权威审计 v1（EXP-03B-03）

状态：只读审计。回答“谁解释字段契约、谁表达字段值、谁负责布局与校验、谁适配原生 View、哪些能组合、哪些不能互相替代”。

## 一、四条真实渲染链

### 链 A：V2 标准表单（权威主链）

契约 → `app/presentation/canonicalFormRenderModel.ts`（解析 `componentKey` + `componentResolution`）→ `components/template/formSection.mapper.ts`（生成 `FormSectionFieldSchema`，决定 `componentRenderer`）→ `components/template/FormSection.vue`（**单一调度器**）→ 最终组件。

`FormSection.vue` 按 `field.componentRenderer` 分发：

- `ProfessionalBusinessValueControl`：只读/可读业务值（money、percentage、status、duration）。
- `ProfessionalBaseFieldControl`：专业基础可编辑字段（按 field.type 分发 ScCheckbox/ScSelect/ScDateField/ScNumberInput/ScInput/ScTextarea）。
- `ProfessionalRelationFieldControl`：many2one / many2many。
- `ProfessionalDetailCollectionControl`：one2many 明细集合。
- `PaymentSettlementDetailCollectionControl`：付款结算明细（行业分支，见边界问题）。
- 默认路径：Sc 原语（ScInput/ScDateField/ScSelect/ScFormItem）。

### 链 B：原生 View 兼容链

View Contract → `components/view/ViewFieldRenderer.vue` → `FieldValue` / `ScInput` / `ScSelect` / `ViewRelationalRenderer`。

这是**原生 Odoo View** 的兼容入口，与 v2 契约主链分离，不消费 v2 `componentKey`。

### 链 C：列表与详情

字段语义 → `pages/listPage/listCellPresentation.ts`（空值/日期/状态 tone）+ Sc 表达原语（`ScStatusBadge`、`ScMoney`）+ `FieldValue`。列表与详情不经过 `FormSection`。

### 链 D：特殊专业字段

`componentKey` → `app/presentation/professionalComponentRegistry.ts`（fail-closed）→ `FormSection` 的 `componentRenderer` 分支 → Professional* 组件。

## 二、四类组件职责与依赖矩阵

| 组件 | 职责 | 是否 v2 主链 | 依赖 |
| --- | --- | --- | --- |
| `ProfessionalBaseFieldControl` | v2 专业基础字段的**值表达与交互**（readonly 分支 + 按 field.type 分发控件） | 是 | `FormSectionFieldSchema`、Sc 原语 |
| `ScField` | 设计系统**纯字段包装**（label/help/error/required 插槽），无 TDesign 依赖 | 否（业务/配置弹窗用） | 无 |
| `ScFormField` | 包装 TDesignFormItem 的**表单布局适配**，用于配置弹窗 | 否 | TDesign 桥 |
| `ViewFieldRenderer` | **原生 View 兼容**渲染入口 | 否（原生链） | `FieldValue`、`ViewRelationalRenderer` |

补充：v2 主链的字段布局项是 `ScFormItem`（`FormSection.vue` 使用），不是 `ScField`/`ScFormField`。三者是不同的布局层，不应互相替代。

## 三、V2 主链与原生兼容链的边界

- v2 主链：只经 `FormSection`，消费契约 `componentKey`/`componentRenderer`，fail-closed 注册表兜底。
- 原生兼容链：只经 `ViewFieldRenderer`，消费 View Contract，不消费 v2 `componentKey`。
- 两条链当前不交叉，边界成立；但要防止未来把 v2 字段误投到 `ViewFieldRenderer`。

## 四、重复实现与历史兼容入口清单

1. 字段布局包装有三套：`ScField`（纯）、`ScFormField`（TDesign 适配）、`ScFormItem`（v2 表单项）。三者消费者不同、职责不同，属**合法分层**，不是重复实现，但未在权威映射中登记。
2. 基础字段有两条渲染路径：`ProfessionalBaseFieldControl`（专业基础）与 FormSection 内 Sc 原语默认路径。是否由 `isProfessionalBaseFieldCandidate` 确定性分流，需补一个“同一字段永不双路径解释”的静态断言。
3. `ViewFieldRenderer` 是历史原生兼容入口，应保留，但不得接入 v2 契约。

## 五、发现的边界泄漏（最重要）

- `components/template/FormSection.vue` 直接 `import PaymentSettlementDetailCollectionControl`，并在模板里硬编码行业分支。**平台 v2 主调度器依赖了行业组件**，违反“平台不依赖行业模型”。
- 平台生成注册表 `app/presentation/semantic_registry.generated.ts` 含行业 componentKey `sc.payment.settlement_detail_collection`。行业语义进入了平台唯一组件词汇表。

## 六、建议的单一权威渲染规则

1. `FormSection` 是 v2 字段渲染的唯一调度器，保持不变。
2. 行业渲染器不得硬编码进 `FormSection`；改为经“渲染器扩展注册”注入（行业扩展层登记 componentKey + renderer），平台 FormSection 只消费注册结果。
3. `ScField` / `ScFormField` / `ScFormItem` 登记为三层：纯包装 / TDesign 适配 / v2 表单项，分别只用于各自消费者，不合并。
4. `ViewFieldRenderer` 保持原生兼容链，禁止 v2 契约字段进入。
5. 基础字段分流（ProfessionalBaseFieldControl vs Sc 默认路径）必须由 `isProfessionalBaseFieldCandidate` 单一判定，并加静态断言禁止同一 field 双路径。

## 七、G1–G10 守卫覆盖建议

- 新增 G-field-render-a：`FormSection` 是唯一 v2 字段调度器。
- 新增 G-field-render-b：平台 `FormSection`/`semantic_registry.generated.ts` 不得直接引用行业组件/行业 componentKey；行业扩展走注册注入。
- 新增 G-field-render-c：`ViewFieldRenderer` 只消费 View Contract，不消费 v2 `componentKey`。
- 现有 G5（关系）、G6（只读）、G8（校验）与上述守卫共同覆盖字段渲染链。

## 八、本轮边界

未修改任何 Vue 组件、未合并渲染器、未删除兼容入口、未改 Contract V2 Schema、未改原生 View 表达。发现的行业泄漏与双路径问题留待架构裁决后，由 EXP-03C 守卫与后续收敛处理。
