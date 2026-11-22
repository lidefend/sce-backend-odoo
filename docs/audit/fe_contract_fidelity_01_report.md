# FE-CONTRACT-FIDELITY-01

## 全量前端契约忠实度与表达完整性审计

### 最终结论

**NOT READY：当前自定义前端尚未达到契约忠实度交付标准。**

主 Contract V2 运行时、Form 主路径、List 的核心金额/精度路径、One2many、
动作合同和导航权威在源码与定向测试层面已有较强约束，但没有达到“后端声明
→ API 解码 → 前端解释 → 最终表达/执行”全链路闭合。

已确认 7 个 P1、1 个 P2 产品表达缺陷。它们不是视觉或易用性问题，而是：

- 前端展示原始 selection key；
- 只读集合桥接丢失字段语义；
- Page Block 将业务值字符串化；
- Page Block 自行补单位并夹取数值；
- My Work 自行补金额精度；
- 同一字段存在两套解释器；
- 通用只读控件忽略 componentKey；
- Kanban 标题回退绕开字段描述。

本阶段没有修改任何产品源码、后端契约、ACL、工作流、数据库或运行配置。

---

## 1. 审计身份与范围

| 项目 | 值 |
| --- | --- |
| Base | `b7bea61727e9bf75270e65292f523910a93a667c` |
| Branch | `audit/fe-contract-fidelity-01-20261122` |
| 产品源码修改 | 否 |
| 后端契约/ACL/工作流/数据库修改 | 否 |
| 前端源文件盘点 | 871 |
| `app` | 306 |
| `pages` | 166 |
| `views` | 77 |
| `components` | 238 |
| API | 28 |
| 审计表面 | 12 |
| 语义维度 | 14 |
| 矩阵单元 | 168 |

完整源码入口、路由和调用链见：

- `docs/audit/fe_contract_fidelity_01/inventory.json`
- `docs/audit/fe_contract_fidelity_01/matrix.json`

审计覆盖 Form、List、Kanban、One2many、Readonly Detail、My Work、Page Block、
Dialog/Drawer、Native View/Contract Runtime、Navigation、共享值解释器以及
Action Renderer。行政配置工作台的视觉和配置体验不属于本次表达忠实度结论。

---

## 2. 全量矩阵结论

| 结果 | 数量 |
| --- | ---: |
| PASS | 92 |
| MISSING | 0 |
| LOST | 19 |
| ALTERED | 2 |
| INFERRED | 2 |
| DUPLICATED | 6 |
| NOT_APPLICABLE | 28 |
| NOT_VERIFIED | 19 |

- 适用单元：`140`
- 已有源码级消费位置的适用单元：`140/140`
- 可裁判单元：`121`
- 可裁判单元正确率：`92/121 = 76.0%`
- 全部适用单元正确率：`92/140 = 65.7%`

`MISSING = 0` 只表示每个适用语义在源码中至少有一个消费位置，不表示表达
正确。19 个 LOST、2 个 ALTERED、2 个 INFERRED、6 个 DUPLICATED 都是实际
语义风险。

`NOT_VERIFIED = 19` 不得计为 PASS。主要集中在前端时区语义、部分附件路径和
缺少完整后端运行回读的页面。

---

## 3. 六个必答问题

### 3.1 前端是否存在越权决策？

**是，存在，但主要位于非主路径和通用回退。**

已确认：

- Progress Summary 在缺少 `unit` 时自行使用 `%`；
- Progress Summary 在前端夹取和取整业务值；
- My Work 在缺少金额 digits 时自行使用 2 位小数；
- List 在 selection label 缺失时显示原始 key；
- Page Block 自行把对象和值转成文本。

主 Contract Runtime 的按钮状态、动作规则、导航 route authority、字段 modifiers
和 Contract V2 解码没有发现等价的直接越权实现。

### 3.2 是否存在契约语义丢失？

**是，已确认 19 个 LOST 单元。**

最严重的是 Readonly Detail 和 Page Block：

- 字段类型/widget/componentKey 被丢弃；
- 关系记录身份退化为字符串；
- money、percentage、duration、date-time 的统一表达没有进入最终 DOM；
- attachment 引用被普通字符串化。

### 3.3 后端要求表达的内容是否全部有消费位置？

**源码级都有入口，但不能因此判定完整表达。**

没有发现完全无消费者的外层业务表面；但存在“有消费者，却在消费者中丢失语义”
的情况。这正是 LOST 与 MISSING 必须分开的原因。

### 3.4 是否存在多套解释逻辑造成语义不一致？

**是。至少存在两套主要业务值解释路径。**

- `presentDeclaredBusinessValue()` 是契约感知路径；
- `formatDisplayValue()` 是通用/兼容路径。

FormSection、ProfessionalBaseFieldControl、FieldValue、HierarchyPlanner、
HierarchyBrowser、HierarchicalWorksheet 和 Kanban 标题回退仍使用后者。

两者在未知 selection、裸关系 ID、componentKey、duration/percentage identity
上行为不同。另有 My Work、Payment Dialog、Activity Contract 的局部专用格式器，
进一步增加分支。

### 3.5 是否存在没有契约依据的前端业务规则？

**是。**

- 缺失进度单位补 `%`；
- 缺失 My Work 金额精度补 `2`；
- List 未知 selection 回退原始 key；
- Page Block 指标值默认使用字符串化；
- Kanban 标题回退不携带字段语义。

这些规则不能由前端以“兼容”为理由长期保留。

### 3.6 问题责任是否可定位？

**是。8 个明确缺陷全部定位到前端表达/适配层，没有证据表明需要修改后端业务模型。**

仍需契约或运行回读确认的潜在缺口单独标记为 `NOT_VERIFIED`：

- 用户时区权威与传送格式；
- Page Block 的统一业务值载体；
- My Work percentage/currency 身份是否完整；
- 所有附件入口的稳定语义角色。

---

## 4. 确认缺陷

### FCF-01 P1 ALTERED：List 显示原始 selection key

调用链：

`ListPage.selectionLabel()` → `presentListCell()` → `String(displayRaw)`

源码：

- `frontend/apps/web/src/pages/ListPage.vue:734-753`
- `frontend/apps/web/src/pages/listPage/listCellPresentation.ts:73-111`
- `frontend/apps/web/src/app/presentation/collectionStatusPresentation.ts:112-142`

`resolveCollectionCell()` 已经实现未知 selection fail-closed，但没有生产调用者。
当文案被翻译、改名或缺少选择项时，页面会显示 `submitted`、`won` 之类的存储 key。

责任：前端消费层。

### FCF-02 P1 LOST：Readonly Collection 桥接移除字段语义

调用链：

`Contract V2` → `sceneReadonlyCollectionBridge` → `String(record[field] ?? '')`
→ `normalizedCollectionAdapter` → readonly table

源码：

- `frontend/apps/web/src/app/renderers/sceneReadonlyCollectionBridge.ts:145-156`
- `frontend/packages/ui/src/contracts/normalizedCollectionAdapter.ts:20-30`
- `frontend/packages/ui/src/contracts/normalizedCollectionAdapter.ts:123-170`

Normalized widget 只保留 `widgetId/fieldCode/label`；记录值在进入适配器前已字符串化。
关系 ID、selection、money、percentage、duration、date-time 和 attachment 语义
无法由下游恢复。

责任：前端只读集合桥接与通用适配器。

### FCF-03 P1 LOST：Page Block 字符串化业务值

源码：

- `frontend/apps/web/src/components/page/blocks/BlockMetricRow.vue:62-103`
- `frontend/apps/web/src/components/scene/SceneBlocksRenderer.vue:242-278`
- `frontend/apps/web/src/components/page/blocks/BlockRecordSummary.vue:50-66`
- `frontend/apps/web/src/components/page/blocks/BlockRecordTable.vue:47-65`

组件直接 `String(value)` 或 `JSON.stringify(value)`。没有消费 field type、
componentKey、digits、currency、unit、relation identity 或 temporal profile。

责任：Page Block 消费层。

### FCF-04 P1 INFERRED/ALTERED：Progress Summary 自造单位和数值

源码：

- `frontend/apps/web/src/components/page/blocks/BlockProgressSummary.vue:32-58`

逻辑：

- `row.unit || '%'`
- `%` 时 `clampPercent`
- 非 `%` 时 `normalizeCount`

这使得缺失单位变成百分比，并改变真实数值。单位和数值范围不能由该组件决定。

责任：Page Block 前端；若后端确实没有 unit，则应补契约而非兜底。

### FCF-05 P1 INFERRED/LOST：My Work 金额精度和百分比表达

源码：

- `frontend/apps/web/src/app/presentation/productMyWorkPresentation.ts:10-31`

`normalizedDigits()` 在缺失时返回 `2`。非 money/datetime fact 直接
`String(fact.value)`，没有 percentage 专用表达。

责任：My Work 前端消费层；必要身份缺失时回到后端契约。

### FCF-06 P2 LOST：Kanban 标题回退忽略字段描述

源码：

- `frontend/apps/web/src/pages/KanbanPage.vue:259-260`
- `frontend/apps/web/src/pages/KanbanPage.vue:342-344`

`formatValue()` 调用 `formatDisplayValue(value, undefined)`，主字段回退无法应用
selection、relation、money、percentage 或 precision。

责任：Kanban 前端。

### FCF-07 P1 DUPLICATED：两套业务值解释器

契约感知路径：

- `frontend/apps/web/src/app/presentation/businessValuePresentation.ts:247-405`

通用兼容路径：

- `frontend/apps/web/src/utils/display.ts:213-268`
- `frontend/apps/web/src/components/FieldValue.vue:39-52`
- `frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue:174-180`
- `frontend/apps/web/src/components/template/FormSection.vue:945-964`
- `frontend/apps/web/src/components/action/HierarchyPlanner.vue:256`
- `frontend/apps/web/src/components/action/HierarchyBrowser.vue:201`

差异包括：

- 未知 selection：契约路径抛 `ContractGapError`，通用路径可能显示原值；
- 裸关系 tuple：通用路径可能暴露 ID；
- percentage/duration：契约路径根据 componentKey 解释，通用路径只按普通数值；
- 空值、boolean 和对象值的行为不完全一致。

责任：前端共享表达层。第二阶段应先统一“语义决定”，再让各表面选择视觉密度，
不是把所有组件合并成巨型格式化函数。

### FCF-08 P1 LOST：通用只读控件忽略 componentKey

源码：

- `frontend/apps/web/src/components/FieldValue.vue:39-52`
- `frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue:174-180`

非 money 路径直接进入 `formatDisplayValue()`，没有把 componentKey 交给
`presentDeclaredBusinessValue()`。percentage、duration、status 身份可能丢失。

责任：通用只读字段适配层。

---

## 5. 已通过的权威边界

以下不代表产品全量运行验收，只表示源码和定向门禁已证明对应机制存在：

| 边界 | 结论 |
| --- | --- |
| Contract V2 schema 解码 | PASS，静态门禁通过 |
| field modifiers / required / readonly | PASS，静态门禁通过 |
| action button status / target / reason | PASS，静态门禁通过 |
| Contract action executor | PASS，定向测试通过 |
| canonical navigation / route authority | PASS，导航测试通过 |
| semantic registry 声明与前端 key | PASS，0 drift |
| contract-basis gap closure | PASS，0 open defects |
| list aggregate currency identity | PASS，真实 ListPage 组件浏览器 1440/390 |
| core percentage/duration/money presentation | PASS，真实组件浏览器 |
| One2many relation/number/row identity | PASS，实际 FormSection/NativeFormTreeRenderer/X2ManyRelationRenderer |

---

## 6. 验证证据与限制

已执行并通过：

- `verify.frontend.contract_basis.enforce`
- `verify.frontend.decision_authority.guard`
- `verify.frontend.shared_surface_semantic_boundary.guard`
- `verify.frontend.contract_shape_projection.unit`，16 cases
- `verify.frontend.collection_view_semantics.unit`
- `verify.frontend.business_semantics.unit`
- `verify.frontend.native_action_contract_consumption.unit`，7 cases
- `verify.frontend.action_view_page_actions.unit`
- `verify.frontend.navigation_shell.unit`
- `verify.semantic.registry.lint`
- `verify.frontend.professional_business_value.unit`，Chromium 34 assertions
- `verify.frontend.collection_aggregate_footer.unit`，真实 ListPage 9 scenarios/1440/390
- `verify.frontend.professional_detail_collection.unit`，实际 Form/One2many 组件

未执行：

- 全站逐路由真实后端浏览器矩阵；
- 用户时区的跨环境运行回读；
- 所有 Page Block 的逐业务类型后端数据验收；
- 全角色、全公司、全状态权限矩阵。

因此时区、附件和部分页面保持 `NOT_VERIFIED`，没有用静态测试替换运行事实。

---

## 7. 责任层归集

| 责任层 | 结论 |
| --- | --- |
| 后端业务模型/ACL/工作流 | 本批没有确认缺陷 |
| P0 契约生产/解码 | 主要 schema、semantic registry、button/navigation authority 通过 |
| 前端共享表达 | 存在重复解释路径，需收敛 |
| 前端页面适配 | Readonly、Page Block、Kanban、List、My Work 存在确认缺陷 |
| 契约定义 | Page Block 统一值载体、时区、附件角色和 My Work 身份仍需单独核实 |
| 验证体系 | 现有门禁较强，但未覆盖上述旁路和全站运行表达 |

---

## 8. 建议的第二阶段修复边界

第二阶段应一次性按共享能力收敛，而不是逐页修补：

1. 建立“契约语义决定”唯一权威，保留场景级呈现适配。
2. 修复 List selection/relation fail-closed。
3. 重建 Readonly Collection 的契约值载体，禁止提前字符串化。
4. 统一 Page Block 的 value/unit/currency/precision/relation/attachment 载体。
5. 去掉 Progress 和 My Work 的前端默认业务值。
6. 让 Kanban 标题回退和通用只读控件消费字段描述/componentKey。
7. 对时区、附件、Page Block 值载体和 My Work 身份先完成契约缺口裁定。

修复阶段不得用 selector、字符串或测试数量替代业务语义闭环。

---

## 9. 裁定

当前前端不是“完全不忠实”，也不是“已经达到交付标准”。

更准确的结论是：

- 主 Contract Runtime 的授权、动作、导航和基本 Contract V2 消费已经成立；
- 业务值解释和次级表达表面尚未统一；
- 一旦业务字段进入 readonly collection、page block、Kanban fallback、
  My Work metric 或 generic readonly control，就可能出现语义丢失或前端补规则。

在 FCF-01 至 FCF-08 未逐项闭合、19 个 NOT_VERIFIED 未取得足够证据之前，
不应宣告前端契约忠实度通过，也不应开始零散视觉美化。
