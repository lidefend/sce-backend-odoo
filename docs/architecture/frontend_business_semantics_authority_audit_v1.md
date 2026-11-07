# 前端业务语义权威与跨页面消费审计 v1

## 基线与边界

- Baseline：`5d184f4831ddbc4819bc5540341b05cd6fb413bb`。
- Formal Product Layer：P0 平台内核产品。
- Layer Target：Contract V2 前端语义解释与跨页面表达。
- 本审计不修改 Contract V2 Schema、Renderer Extension Protocol、行业 Renderer、
  `@sc/ui` 或原生 View 兼容链。

## 权威链

```text
Contract V2
  -> canonicalFormRenderModel / listProfile / fieldSemantics / statusContract
  -> shared frontend semantic adapters
  -> Sc primitives and legal visual adapters
```

结论：前端已经具备契约驱动骨架，但金额、日期、状态和空值尚未完全收口到同一条权威链。

## 跨页面消费矩阵

| 业务事实 | 表单 | 列表 | 详情 | Kanban | 审批摘要 | 行业组件 |
| --- | --- | --- | --- | --- | --- | --- |
| 金额 | `FormSection` / `ProfessionalBusinessValueControl` 消费 `digits + currency_field` | `ListPage` 消费 `field_semantics.data_type/precision/currency_field` | `FieldValue` 当前只走通用数值格式，未消费币种和精度 | `KanbanPage` 当前通过字段名推断金额 | `productMyWorkPresentation` 消费后端 `money` 对象 | 付款结算弹窗消费币种对象和共享金额格式 |
| 日期 | `fieldUtils` 归一输入值 | `listCellPresentation` 使用 compact 档 | `formatDisplayValue` 使用 full 档 | 当前直接字符串化，绕过统一日期解析 | 当前手工 `replace('T',' ').slice(0,16)` | 历史日期直接输出契约字符串 |
| 状态 | `sc.display.status` + selection label；tone 由本地映射 | `status_field/cellRole` + selection + `collectionStatusPresentation` | selection label，无统一 tone | 声明状态列走统一适配，其余字段仍可能被字段名推断为状态 | 状态 key/label 来自后端，tone 本地函数解释错误 | 付款历史状态使用行业局部样式 |
| 空值 | 字段声明 `readonly_empty_text`，缺省回退 `-` | 数值缺省被显示为 `0`，普通字段为 `--` | `--` | 普通字段 `--`，金额/百分比可能被推断后改变语义 | 缺省使用 `未填写/未知` | 多处使用 `—` 或空字符串 |

## 发现

### P1：详情金额没有消费契约币种和精度

证据：

- `components/FieldValue.vue` 只调用 `formatDisplayValue(value, field)`。
- `utils/display.ts` 对 `monetary` 只调用无币种、无精度的
  `formatNumericFieldValue`。
- 表单与列表已经使用 `formatMonetaryDisplayValue`。

影响：同一金额在表单/列表为 `¥1,234.50`，详情可能变成 `1,234.50`，且无法遵循币种精度。

### P1：Kanban 仍通过字段名推断业务语义

证据：

- `pages/KanbanPage.vue` 的普通事实格式化落到 `utils/semantic.ts::semanticValueByField`。
- 该函数以 `amount/total/cost/revenue/percent/_rate` 等字段名推断金额和百分比。
- Contract V2 已提供 `listProfile.metric_fields`、`status_field` 和列的
  `componentKey/data_type/currency_field/precision/selection`，但 Kanban 没有消费这些元数据。

影响：字段改名即改变表达；`budget_total` 和普通文本字段不能只靠名称获得业务身份。

### P1：状态存在第二套 label/tone 解释

证据：

- `utils/semantic.ts` 仍持有 `STATUS_TEXT` 字典。
- `professionalBusinessValueModel.ts::statusSemantic` 另有一套状态 tone 映射。
- `MyWorkApprovalWorkspace.vue::statusSemantic` 把后端状态 key 当成
  `success/warning/danger` tone 使用，导致 `pending`、`approved` 等状态显示为默认色。
- 平台唯一 tone 策略已经存在于 `collectionStatusPresentation.ts`。

契约边界：

- `statusContract` 是运行时可见性、权限、readonly/disabled 和原因码的权威。
- 业务状态 label 来自字段声明的 selection；tone 是前端设计系统决策，不从业务契约伪造。
- 因此不能把颜色写进 `statusContract`，也不能再用字段名推断状态字段。

### P1：空值口径不一致

证据：

- 平台字段空值为 `FIELD_VALUE_EMPTY_TEXT = '--'`。
- 表单和 Professional Base 缺省回退 `-`。
- 列表数值缺省被显示为 `0`，把“无值”错误表达成真实零值。
- 审批摘要缺省使用 `未填写/未知`。
- 行业组件多处使用 `—`。

合法差异只包括：契约显式声明的 `readonly_empty_text`，以及空集合/空页面文案。

### P2：日期展示入口不统一

证据：

- 表单输入使用 `toDateInputValue/toDatetimeInputValue`。
- 列表使用 `formatTemporalFieldValue(..., 'compact')`。
- 详情使用 full 档。
- Kanban、审批摘要和部分行业组件直接字符串切片或 `Intl.DateTimeFormat`。

契约缺口：

- 当前 Contract V2 页面没有向前端提供可消费的用户时区/日期格式声明。
- 本轮不自行使用浏览器时区猜测 Odoo datetime 的用户语义，也不把 UTC 字符串直接宣称为
  已做时区转换。时区转换需后续在契约声明层补齐后再实现。

### P2：金额工具被跨模块复用但没有明确权威模块

金额能力目前位于 `components/template/formSection.mapper.ts`，却被列表、审批、活动和
行业组件共同使用。功能方向正确，但归属名称会产生“表单专用工具”的误导，也容易再次长出
局部实现。

## 最小实施方案

1. 新建平台业务表达模块，集中金额、百分比、日期显示、状态 tone 和空值规则。
2. 将金额格式化从 `formSection.mapper` 提升为跨页面权威工具，所有正式业务消费者统一引用。
3. 详情 `FieldValue` 消费币种值和精度；原生 View 与 canonical form 只传声明元数据。
4. Kanban 改为消费 `listProfile` 和列元数据，不再使用字段名推断。
5. 状态 label 只从 selection/契约声明取得，tone 只走平台状态策略。
6. 普通字段空值统一为平台默认 `--`；数值缺失不得再显示为 `0`。
7. 审批摘要复用共享金额、日期、空值和状态规则。
8. 增加跨页面一致性测试与静态守卫，阻止重新出现字段名推断和金额/状态第二套实现。

## 本轮明确不完成

- 不修改 Contract V2 Schema 增加时区声明。
- 不声明用户时区转换已经完成。
- 不改造 `@sc/ui` 或 TDesign 官方组件映射。
- 不为付款结算行业组件新增业务语义；仅要求它继续复用平台金额适配器。
