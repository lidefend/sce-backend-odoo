# NATIVE-SCENE-01 / B-S3 · 原生 Widget 语义接管审计

Status: source audit complete; frontend source consumption traced; runtime and
browser business acceptance not executed.

Date: 2026-11-17

Baseline main: `ceaa207b716ed3e2157f49d315b72e071a722645`

## 1. 检查点边界

本检查点属于 P4 只读审计，目标是回答：

- Odoo View XML 中的字段 Widget、Widget options、Domain、Context 和 Modifier
  如何进入 `ui.contract.v2` Widget。
- 原生 Widget 如何映射到语义、组件身份和前端 Renderer。
- 哪些来源是 Odoo 显式事实，哪些是字段类型推导或兼容默认。
- 当 Widget 或语义无法解析时，链路是否真正 fail-closed。
- 下一项最小产品实现应补在现有哪一个契约和转换器位置。

本检查点不执行：

- 不修改产品源码、契约 Schema、Parser、Renderer 或前端行为。
- 不新增持久化模型、场景模型、数据库字段或运行时配置。
- 不执行浏览器、角色、权限或业务写入验收。
- 不实施 Calendar、Gantt、Pivot、Graph、Dashboard 或专业 Renderer。

职责声明：

- Formal Product Layer: P4 read-only audit supporting P0.
- Layer Target: Native View Widget/option/modifier fact 到 Contract V2 Widget、
  semantic/component identity 和通用前端消费。
- Module: `addons/smart_core`、`frontend/apps/web`，并以合同注册表
  `contracts/registry/` 为声明证据。
- Standard vs User-Specific: 平台中立的原生 View 语义，不属于行业或客户偏好。
- Blast Radius: 审计只覆盖现有转换与消费路径；运行态和真实业务行为未改变。

证据等级：

| 等级 | 本检查点状态 | 含义 |
| --- | --- | --- |
| L1 原生事实 | 源码级已验证 | XML Widget、字段类型、选项和嵌入 Widget 声明存在 |
| L2 后端契约 | 源码链已验证，当前运行态未验证 | 可追踪到 Parser、V2 Widget 和注册表输出 |
| L3 前端消费 | 源码消费已追踪，浏览器未验证 | 可确认解码、组件选择和局部专用分支 |
| L4 真实业务 | 未验证 | 未执行真实角色、数据、保存、错误和权限负例 |

## 2. 结论摘要

B-S3 的核心结论是：

1. 平台已经有可复用的 Widget 主链，不需要另建页面 Widget 系统。
2. 常见字段 Widget 已经有类型映射、语义推导、组件身份和前端 fail-closed 校验。
3. 当前契约没有显式区分“Odoo XML 显式 Widget”“字段类型推导 Widget”和
   “兼容默认 Widget”，并且会把推导值写进 `nativeWidget`。这会使自动接管资格
   和审计证据失真。
4. 未知原生 Widget 通常不会让契约失败，而是按字段类型降级成通用组件。
   前端只能拒绝“未知 componentKey”，无法发现后端已经把未知原生意图归一掉。
5. 字段级 Domain/Context 的 RAW 证据可以进入 occurrence identity，但没有统一
   编译到 Widget 的字段描述或组件配置，关系选择仍可能丢失原生约束。
6. `daterange`、`analytic_distribution`、附件集合、头像关系和 radio 等能力
   已经有真实消费，但部分实现仍靠 Parser 特例或前端名称分支，不是完全由注册表
   数据驱动。
7. 嵌入型 `<widget name="...">` 节点当前只有占位呈现。项目入口中的
   `sc_stage_requirements`、`sc_next_actions`、`sc_insight_banner` 不能被称为
   完整接管。
8. List/Kanban/Activity 的非 Form Widget 语义仍不完整。既有 P4 能力图已经把
   `non_form_widget` 标为 `unsupported / CAPABILITY_WIDGET_NOT_REGISTERED`。

因此，下一项产品工作不应先补某个专业组件，而应先收敛一个可复用边界：

```text
现有 Native Parser / Canonical AST
        |
        v
现有 Contract V2 Widget
  + explicit native provenance
  + resolved semantic
  + supported/unsupported reason
  + typed widget options
  + Domain/Context behavior
        |
        v
现有 semantic.yaml / component.yaml
        |
        v
现有通用 Renderer 和行业扩展 Renderer
```

这是一项现有链路的契约补齐，不是第三套 Widget 系统。

## 3. 当前原生 Widget 事实面

### 3.1 仓库源码盘点

对当前 HEAD 的 `addons/`、`addons_external/`、`customer_addons/` 和
`demo_addons/` 做只读 XML 扫描，得到：

| 事实 | 数量 |
| --- | ---: |
| 带 `widget` 属性的字段声明 | 349 |
| Form View 中的字段 Widget 声明 | 291 |
| Tree View 中的字段 Widget 声明 | 56 |
| QWeb 模板中的字段 Widget 声明 | 1 |
| 无法解析 View type 的声明 | 1 |
| 独立 `<widget name="...">` 节点 | 4 |
| 唯一字段 Widget 名 | 18 |

349 个字段 Widget 声明按名称分布如下：

| Widget | 声明数 | 当前主要语义路径 |
| --- | ---: | --- |
| `statusbar` | 93 | 原生工作流状态 |
| `many2many_binary` | 83 | 附件关系集合 |
| `handle` | 43 | 排序手柄 |
| `many2many_tags` | 33 | 标签式多关系 |
| `badge` | 30 | 状态/徽标展示 |
| `json` | 29 | 只读结构化值 |
| `statinfo` | 13 | 统计信息/可读值 |
| `percentage` | 12 | 百分比业务值 |
| `domain` | 2 | OCA Domain 编辑器 |
| `res_partner_many2one` | 2 | 客户专用 many2one |
| `daterange` | 2 | 起止日期 |
| `radio` | 1 | 单选项 |
| `one2many_list` | 1 | 明细集合 |
| `many2one_avatar_user` | 1 | 用户头像关系 |
| `boolean_toggle` | 1 | 布尔开关 |
| `html` | 1 | 富文本 |
| `image` | 1 | 图片 |
| `tier_validation` | 1 | QWeb 模板专用 |

源码代表：

- `addons/smart_construction_core/views/core/payment_request_views.xml:59`
  声明原生 `statusbar`。
- `addons/smart_construction_core/views/core/payment_request_views.xml:149`
  声明带只读表达式的 `many2many_binary`。
- `addons/smart_construction_core/views/core/project_information_edit_views.xml:32`
  声明 `res_partner_many2one`。
- `addons/smart_construction_core/views/core/project_information_edit_views.xml:44`
  声明 `daterange` 及 `end_date_field` options。
- `addons/smart_construction_core/views/core/project_information_edit_views.xml:48`
  声明 `many2one_avatar_user`。
- `addons/smart_core/views/platform_company_access_views.xml:47`
  声明 `json` Widget。
- `addons_external/oca_server_ux/base_tier_validation/views/tier_definition_view.xml:104`
  声明 Domain 编辑器 Widget。

扫描范围说明：

- 这些数字来自当前仓库模块源码，不是“世界上所有 Odoo 模块”的结论。
- Odoo Enterprise/其他外部模块可能在运行时安装并提供当前仓库中不存在的 Widget；
  未在当前输入中发现，不能解释为 Odoo 不存在该能力。
- `contracts/generated/product_view_structure_contract.json` 还包含从已解析标准
  Odoo View 得到的事实，例如 `analytic_distribution`
  （`contracts/generated/product_view_structure_contract.json:3714`）。

### 3.2 嵌入型 Widget 节点

当前仓库有 4 个独立 Widget 节点：

- `addons/smart_construction_core/views/core/project_overview_views.xml:62`
  `sc_stage_requirements`
- `addons/smart_construction_core/views/core/project_overview_views.xml:85`
  `sc_next_actions`
- `addons/smart_construction_core/views/core/project_views.xml:127`
  `sc_insight_banner`
- `addons_external/oca_server_ux/base_tier_validation/views/tier_definition_view.xml:36`
  `web_ribbon`

这不是“当前没有声明”的情况。原生 View 明确声明了这些嵌入能力，但现有通用
契约和 Renderer 没有把它们变成可执行组件。

## 4. 真实调用链

### 4.1 Odoo 原生事实

Odoo 继续是唯一原生权威：

- `get_view()` 返回合并、继承和当前用户裁剪后的有效 View。
- `fields_get()` 或 resolved view fields 提供字段类型、关系、selection、
  currency 和 digits。
- View XML 直接声明字段 Widget、options、Domain、Context、readonly、required、
  invisible 和嵌入 Widget 节点。

Canonical AST 入口位于
`addons/smart_core/core/native_view_projection.py:165-229`，它只对有效 View
做一次投影，不重新做继承或权限推导。

### 4.2 旧 View Parser

当前主路径仍由
`addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py`
生成兼容的 `ui.contract`：

- `:462-498` 收集 occurrence modifiers、decoration 和关系 active action。
- `:529-587` 收集 Tree 列、列 Widget、attributes、modifiers 和 options。
- `:1166-1212` 生成 Form 字段节点，保留 XML attributes、native locator、
  source position、`fieldInfo`、options 和 widget semantics。
- `:1235-1249` 生成独立 Widget 节点，只保留 name、title、attributes 和
  invisible。
- `:1435-1474` 合并模型字段 modifiers 与 XML 字段的 Domain、Context、Widget
  和 groups。

字段类型的默认 Widget 由
`addons/smart_core/app_config_engine/services/view_Parser/base.py:244-262`
生成。这里会把 `char`、`float`、`many2one` 等字段类型转换成默认 Widget 名。

### 4.3 Unified Page Contract V2

`addons/smart_core/core/unified_page_contract_v2_assembler.py` 完成归一：

- `:2303-2320` 生成一个 Widget，选择 canonical `widgetType` 和 `componentKey`。
- `:2325-2373` 发布 `componentConfig`、`fieldDescriptor`、relation、
  selection、currency/digits、`nativeWidget`、`widgetOptions`、
  `widgetSemantics`。
- `:2376-2444` 把 native occurrence、modifier、source position 和字段描述写入
  最终布局节点。
- `:2566-2751` 递归归一原生布局，生成字段 owner、Widget ID、status 和
  component registry。
- `:830-1038` 为 Form 字段、容器、按钮和 List 列绑定 P0-4 occurrence identity。

Canonical Widget 集合和原生别名位于同一文件：

- `:310-314` 是当前 canonical Widget 集合。
- `:316-335` 是原生 Widget alias。
- `:338-355` 是原生 Widget 到 canonical Widget 的入口。

### 4.4 语义与组件注册表

`contracts/registry/semantic.yaml` 是“字段意味着什么”的数据权威：

- `:23-87` 是有序推导规则。
- `:89-117` 是 semantic 到 componentKey 的映射。
- `:29-40` 明确 money、percentage、duration、status 和会计只读摘要语义。
- `:46-52` 区分关系集合、明细集合和标签集合。
- `:75-83` 把 Gantt 映射到通用集合渲染，并明确没有独立 Gantt 组件。

`contracts/registry/component.yaml` 是组件身份、字段类型、Renderer、
capabilities 和 readiness 的数据权威：

- `:41-64` 是平台和行业组件注册。
- `:24-34` 规定无专业控件时使用类型导向 Renderer。

`addons/smart_core/core/contract_runtime/semantic_resolver.py`：

- `:129-159` 解析显式 semantic 或推导 semantic。
- `:167-173` 只返回已登记 semantic 的 componentKey。
- `:252-274` 拒绝未登记 componentKey，并发布组件身份/version。

### 4.5 前端消费

前端已经具备严格消费外壳：

- `frontend/apps/web/src/app/contracts/v2/types.ts:351-394` 定义 Widget、
  field descriptor 和组件身份形状。
- `frontend/apps/web/src/app/contracts/v2/store.ts:428-489` 把 Widget 投影为字段
  descriptor map，并读取 relation、selection、Domain、Context、widget options。
- `frontend/apps/web/src/app/presentation/contractFormPresenter.ts:252-368`
  根据 componentKey/字段类型选择组件并构造表单字段。
- `frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts:436-493`
  校验组件是否注册、字段类型、presentation profile、契约版本和 capabilities。
- `frontend/apps/web/src/components/template/FormSection.vue:714-724` 对未知
  componentKey 或 Renderer 显示显式 fail-closed 状态。

因此，L3 的问题不是“前端完全没有消费者”，而是消费者只拿到了后端归一后的结果，
无法识别归一前丢失的原生 Widget 语义。

## 5. Widget 来源与身份

### 5.1 当前可用的身份

现有 V2 Widget 已有以下可复用身份：

```text
widgetId
widgetType
fieldCode
componentKey
componentConfig
fieldDescriptor
nativeLocator
occurrenceIndex
sourcePosition
nativeIdentity
```

Form 字段 `widgetId` 由 native locator 和 occurrence index 确定性生成
（`unified_page_contract_v2_assembler.py:2315-2317`）。P0-4 再绑定统一的
`nativeIdentity` 与 `occurrenceKey`
（`native_view_occurrence.py:130-227`）。

这部分可以直接复用，不需要新造 Widget occurrence 身份。

### 5.2 当前缺少 Widget 来源

B-S2 要求的四类来源应保持区分：

| 来源 | 含义 | 当前显式字段 |
| --- | --- | --- |
| `native_explicit` | XML 明确声明 `widget=...` | 无 |
| `model_metadata_derived` | 根据字段类型生成的默认 Widget | 无 |
| `compatibility_default` | Parser 为兼容自行生成的缺省值 | 无 |
| `unresolved` | 原生声明存在但无法形成合法组件语义 | 无 |

`NativeFieldOccurrence.native_attributes` 只记录 XML 真正出现的属性
（`native_view_projection.py:39-42`、`:253-257`），这是正确的方向。
但旧 Parser 的 `_field_info_for_layout()` 会先把字段类型转换为默认 Widget
（`base.py:244-271`），随后 V2 无法再区分显式值和推导值：

```text
字段类型 char
  -> _widget_for_field() 产生 char
  -> fieldInfo.widget = char
  -> V2 componentConfig.nativeWidget = char
```

相关源码：

- `base.py:244-262` 生成类型默认 Widget。
- `base.py:264-271` 把它写入 field descriptor。
- `parsers Tree Form.py:1183-1212` 只在 XML 显式 Widget 存在时覆盖它。
- `unified_page_contract_v2_assembler.py:2318-2340` 把最终字段值统一写成
  `nativeWidget`。

影响：

- 任意新模块安装后，审计无法从契约判断某个 Widget 是否真是 Odoo 原生声明。
- 自动接管资格无法只依赖 `nativeWidget` 是否存在。
- 类型默认映射发生变化时，历史审计无法区分“Odoo 视图变更”与“Smart Core
  兼容规则变更”。
- 现有静态快照中出现 `nativeWidget: "char"`、`"float"`、`"datetime"` 等值，
  不能自动解释成原生显式 Widget。

### 5.3 未知 Widget 当前会静默降级

未知原生 Widget 当前走字段类型默认：

- `unified_page_contract_v2_assembler.py:338-355`：
  canonical、alias 都未命中时调用 `_widget_type_from_field()`。
- `semantic_resolver.py:129-159`：
  未知显式 semantic 只记录 error，随后返回推导 semantic。
- `addons/smart_core/tests/test_contract_runtime_semantic_resolver.py:95-99`
  明确把 `unregistered_widget` 固定为 `sc.display.text` 的成功结果。
- `test_contract_runtime_semantic_resolver.py:123-131`
  明确把未知 semantic 固定为“记录错误后降级”。

这与仓库的 fail-closed 原则不一致。前端只会拒绝未知 componentKey
（`FormSection.vue:714-719`、`professionalComponentRegistry.ts:441`），
但后端已经为未知原生意图生成了一个合法 componentKey，所以到达前端的契约
看起来仍然有效。

具体风险实例：

- OCA `widget="domain"` 会被字段类型推导为普通文本/控件，而不是 Domain 编辑器。
- `widget="res_partner_many2one"` 会变成普通 many2one，客户选择上下文和专用行为
  不被契约明确记录。
- `widget="handle"` 会变成普通数值字段或通用表格列，不表达排序拖拽能力。

这说明“有 Renderer 能显示一些内容”不等于“原生 Widget 已接管”。

## 6. Domain、Context 与 Options

### 6.1 RAW 证据已经保留一部分

旧 Parser 在字段节点上保留完整 XML attributes
（`parsers Tree Form.py:1171-1176`），并在 modifiers 聚合中识别
Domain、Context、groups
（`:1435-1474`）。

P0-4 的 occurrence identity 会把节点上的 Domain、Context、options 写成
`nativeBehavior`
（`addons/smart_core/core/native_view_occurrence.py:215-227`）。
List column occurrence 也会独立发布 `domainRaw`、`contextRaw`、`optionsRaw`
（`unified_page_contract_v2_assembler.py:1014-1026`），前端严格核对它们与
`nativeIdentity.nativeBehavior` 一致
（`frontend/apps/web/src/app/contracts/v2/schema.ts:2835-2843`）。

### 6.2 但 Widget 消费出口没有闭环

Form 的 V2 组装只从 `field_modifiers` 合并四个状态 modifier：
`readonly`、`required`、`invisible`、`column_invisible`
（`unified_page_contract_v2_assembler.py:1545-1554`）。

`_field_source_with_node_info()` 只从 Node attributes 显式取出 Widget
（`:2488-2491`），没有把同一 attributes 中的 Domain/Context 编译进字段源。

`_field_widget()` 只有在字段源已经存在 `domain` 时才生成
`domain_expression`
（`:2303-2307`），但前端字段 descriptor map 的 Domain/Context 只读取
`componentConfig` 或 `fieldDescriptor`
（`frontend/apps/web/src/app/contracts/v2/store.ts:476-480`）。
它不会从 `nativeIdentity.nativeBehavior` 恢复关系选择约束。

真实样本：

- `addons/smart_construction_core/views/core/payment_request_views.xml:100`
  `contract_id` 的 Domain 受 `project_id` 约束。
- 同文件 `:109`、`:115` 的结算关系也带项目 Domain 和 `no_create` options。
- 同文件 `:169-170` 的子表关系还带状态和项目双重 Domain。

结论：

- RAW 证据存在，可用于审计和一致性校验。
- 选择控件的实际执行输入仍可能缺失 `domain_expression` 或结构化 Context。
- 这属于“已保留、未完整编译/消费”，不能表述为已完整接管。

### 6.3 Options 是任意对象，没有支持矩阵

V2 会把 options 原样写入 `componentConfig.widgetOptions`
（`unified_page_contract_v2_assembler.py:2357-2359`），Schema 把
`componentConfig` 定义为开放 object。

关系选择的 `no_create`、`no_create_edit`、`no_quick_create` 和
`relation_entry` 已有后端解释
（`page_assembler.py:3990-4014`、`:4058-4173`）。这证明 options 并非完全丢失。

但通用 Widget 仍没有：

- 该 Widget 支持哪些 options；
- 哪些 options 已消费；
- 哪些 options 被忽略；
- options 值非法时的 reason code；
- options 变化是否需要重建 component identity。

因此，安装一个声明新 options 的第三方模块时，平台可能保留原始 JSON，
却无法证明对应行为已交付。

## 7. 当前 Widget 覆盖矩阵

状态定义：

- `数据驱动`：语义和组件由 `semantic.yaml` / `component.yaml` 决定。
- `专用实现`：已有明确 Parser 或前端分支，但仍有代码内名称判断。
- `条件接管`：依赖字段类型、relation model 或其他字段共同决定。
- `降级`：可显示通用值，但原生 Widget 行为不完整。
- `未接管`：只有 RAW/占位，不能执行原生意图。

| Widget | 后端语义/组件 | 前端证据 | 当前判断 |
| --- | --- | --- | --- |
| `statusbar` | `status` / `sc.display.status` | `parsers Tree Form.py:1291-1316`；工作流 Header | 数据驱动 + 专用工作流 |
| `badge` | `status` / `sc.display.status` | `businessValuePresentation.ts:248-250` | 数据驱动 |
| `percentage` | `percentage` / `sc.value.percentage` | `ProfessionalBusinessValueControl` | 数据驱动 |
| `json` | 字段类型强制 `display` / `sc.display.text` | `unified_page_contract_v2_assembler.py:343-344`；`FormSection.vue:281-301` | 明确只读，Editor 未接管 |
| `many2many_tags` | form 为 `sc.select.tags`；List 原生 widget 未完整进入列组件选择 | `ProfessionalManyToManySelect` | Form 已接管；List 部分 |
| `one2many_list` | `sc.relation.table` | `X2ManyRelationRenderer.vue` | 数据驱动 |
| `many2many_binary` | 类型推导为 collection；前端再按 `ir.attachment` 选择附件 UI | `formSection.mapper.ts:141-144`；`X2ManyRelationRenderer.vue:959-962` | 条件接管，非 Widget 注册驱动 |
| `daterange` | date + `widgetSemantics.kind=date_range` | `contractFormPresenter.ts:318-325`；`FormSection.vue:921-923` | 专用实现 |
| `analytic_distribution` | JSON + `widgetSemantics.kind=weighted_relation` | `FormSection.vue:745-747`；`X2ManyRelationRenderer.vue:85-86` | 专用实现 |
| `radio` | `choice` / `sc.select.remote` | `FormSection.vue:917-919` 另有 radio 分支 | 数据驱动 + 专用表现 |
| `many2one_avatar_user` | `relation` / `sc.relation.many2one` | `ProfessionalMany2oneFieldControl.vue:127-132` | 条件接管 |
| `res_partner_many2one` | 回落到通用 relation | 未发现对应 Widget 专用分支 | 降级 |
| `handle` | alias 为 number；List 通用表格 | 未发现排序手柄/拖拽执行分支 | 未完整接管 |
| `boolean_toggle` | 回落到 checkbox/boolean | 未发现 toggle 专用注册 | 降级 |
| `image` | 回落到 binary/file | 未发现 image 专用注册 | 降级 |
| `html` | long text/textarea | readonly 时可用 RichText 展示 | 部分接管 |
| `statinfo` | readable value | smart button 由 Form Parser 独立抽取 | Widget 本体只读接管 |
| `domain` | 回落字段类型默认 | 未注册 Domain Editor Renderer | 未接管 |
| `tier_validation` | QWeb 字段 Widget | 通用 Form Widget 链不处理 QWeb 模板 | 未接管 |

这个矩阵说明：当前覆盖不是“全有或全无”，但也没有达到“安装即识别”的数据驱动
标准。尤其是 `many2many_binary` 和 `analytic_distribution` 虽能工作，仍需要
上下文或前端名称判断才能恢复行为。

## 8. List、Kanban 与 Activity 的特殊问题

现有 P4 能力图已经给出正式分类：

- `contracts/product/native-view-frontend-capability-map-v1.yaml:32`
  将 `tree`、`kanban`、`activity` 的 `field.widget` / `field.options`
  标为：
  - `frontend_status: missing`
  - `terminal_status: unsupported`
  - `reason_code: CAPABILITY_WIDGET_NOT_REGISTERED`

源码原因包括：

1. `_field_widget()` 对 `layout_type=table` 强制
   `widgetType="table"`（`unified_page_contract_v2_assembler.py:2318-2320`）。
2. List 前端从 Widgets 提取列 schema 时使用 `widget.widgetType`
   （`useActionViewContractShapeRuntime.ts:220-229`），因此 `handle`、
   `many2many_tags` 等原生名称不能直接成为列 Renderer 身份。
3. `resolveListColumnOptions()` 当前只把 `sc.value.duration` 作为扩展
   componentKey 传递（`:232-282`），其他列 componentKey 仍被收窄。
4. P0-4 已经发布 `listProfile.columnOccurrences`，前端严格解码并校验
   （`frontend/apps/web/src/app/contracts/v2/schema.ts:1300-1373`），
   但列表 UI 目前主要消费 `columnsSchema`/Widget，不是 occurrence 中的
   Widget 语义。

因此，List occurrence 身份已经补齐，但 occurrence 上的 Widget 语义还没有成为
真正的列 Renderer 选择权威。Kanban 和 Activity 仍需要各自 View Profile 的
Widget 形状，不应直接复用 Form 字段控件推断。

## 9. 嵌入 Widget 与 QWeb

独立 Widget 节点当前只有占位链：

- 后端只生成 `type="widget"`、name、label、attributes
  （`parsers Tree Form.py:1235-1249`）。
- 前端 presenter 只把节点 name 写入 `nativeWidget`
  （`frontend/apps/web/src/app/presentation/contractFormPresenter.ts:507`）。
- `CanonicalFormNodeRenderer.vue:38-40` 只显示标题或 Widget 名称。

这条链路没有：

- 组件注册；
- options schema；
- 数据源；
- 动作/执行协议；
- renderer readiness；
- unsupported reason。

同一类问题也存在于 Web ribbon 和 QWeb template 字段。安装一个声明
`<widget name="custom_widget">` 的模块时，页面可能“看起来打开成功”，实际只显示
Widget 名称占位。这必须保持为显式未接管。

## 10. Canonical AST 复用判断

Canonical Native View AST 应继续作为统一原生投影候选，但当前不能直接替代旧
Parser：

- AST 已经保留字段 occurrence、locator、字段元数据、容器和 relation target
  （`native_view_projection.py:48-80`、`:239-300`）。
- AST 的 curated field attributes 包含 `widget`、`options`、modifiers 和 groups，
  但 `_FIELD_ATTRIBUTE_KEYS` 当前没有列 `domain`、`context`
  （`native_view_projection.py:39-42`）。
- AST 当前只用于 Form structure 等部分装配，不是所有 View Profile 的主输入。

判断：

- 现在重写整个 Parser 风险高且没有必要性。
- 应先把 AST 和旧 Parser 对 Widget 的公共语义投影到同一个契约形状。
- AST 补 Domain/Context 捕获时，应补“实际消费方”，避免形成声明未消费字段。

## 11. 缺口登记

| 编号 | 严重度 | 结论 | 责任层 | 证据 |
| --- | --- | --- | --- | --- |
| B-S3-G01 | High | `nativeWidget` 混入字段类型推导值，无法区分原生显式与兼容默认 | P0 | `base.py:244-271`、`parsers Tree Form.py:1183-1212`、`unified_page_contract_v2_assembler.py:2318-2340` |
| B-S3-G02 | High | 未知原生 Widget/显式 semantic 静默降级为类型默认，前端无法 fail-closed | P0 | `unified_page_contract_v2_assembler.py:338-355`、`semantic_resolver.py:129-159`、测试 `:95-99`、`:123-131` |
| B-S3-G03 | High | 字段 View Domain/Context 只有 RAW occurrence 证据，未统一编译到 Widget 选择行为 | P0 | `parsers Tree Form.py:1435-1474`、`unified_page_contract_v2_assembler.py:1545-1554`、`:2488-2491`、`store.ts:476-480` |
| B-S3-G04 | High | 嵌入 `<widget name>` 只有占位呈现，项目原生 Widget 未接管 | P0 | `project_overview_views.xml:62,85`、`project_views.xml:127`、`parsers Tree Form.py:1235-1249`、`CanonicalFormNodeRenderer.vue:38-40` |
| B-S3-G05 | High | List/Kanban/Activity 的 Widget/options 组件选择仍不完整 | P0/P4 evidence | `native-view-frontend-capability-map-v1.yaml:32`、`unified_page_contract_v2_assembler.py:2318-2320`、`useActionViewContractShapeRuntime.ts:220-282` |
| B-S3-G06 | Medium | `daterange`、`analytic_distribution`、附件、radio 等依赖专用名称分支，未完全进入统一声明 | P0 | `parsers Tree Form.py:197-234`、`FormSection.vue:745-747`、`:917-923`、`formSection.mapper.ts:141-144` |
| B-S3-G07 | Medium | Widget options 是开放对象，没有 supported/unsupported/非法原因的合同分类 | P0 | `unified_page_contract_v2_assembler.py:2357-2359`、Schema `widget.componentConfig`、`page_assembler.py:3990-4173` |
| B-S3-G08 | Medium | 无源码级 Widget 全表覆盖守卫，新增模块可发布“有效但降级”的契约 | P4 | 当前唯一词表测试集中于少量语义和 registry case；`native_view_frontend_capability_map-v1.yaml:32` 仍是静态分类 |
| B-S3-G09 | Medium | `handle`、`res_partner_many2one`、`domain`、`boolean_toggle`、`image` 等有声明无完整专用 Renderer | P0/L3 | 第 7 节覆盖矩阵；前端未发现对应通用注册分支 |
| B-S3-G10 | Medium | Canonical AST 的 field attribute 白名单未包含 Domain/Context，迁移前存在事实截断风险 | P0 | `native_view_projection.py:39-42` |

## 12. 应保留的机制

必须复用：

1. `get_view()` 与 `fields_get()` 的原生权威。
2. 旧 Parser 的 View type 解释和当前兼容适配能力。
3. Canonical Native View AST 的容器、字段 occurrence、locator 和 relation
   descriptor。
4. P0-4 的确定性 `nativeIdentity` / `occurrenceKey`。
5. `semantic.yaml` 的 semantic 推导。
6. `component.yaml` 的组件身份、字段类型、Renderer 和 capabilities。
7. Contract V2 Widget 的 `widgetId`、`componentKey`、`componentConfig`、
   `fieldDescriptor` 和 `widgetStatus`。
8. 前端专业组件注册表、行业 Renderer 扩展和现有 fail-closed 外壳。
9. 关系入口、Domain compiler、options 到 relation entry 的现有解释。

不应新增：

- 第二套 Widget 组件词典；
- 第二套 Renderer 注册表；
- 按 model/name 推断 Widget 的前端业务字典；
- 为单个页面重写 Form/List；
- 把 Odoo XML 原样交给前端解析；
- 为尚未消费的字段提前扩展公共 Schema。

## 13. 推荐的最小实施边界

后续实施应在现有 Widget 上增加一个受控的 Native Widget Profile，而不是新建
页面系统。建议复用现有 `componentConfig` 或 Widget 同级字段，最终形成：

```json
{
  "nativeWidgetProfile": {
    "nativeWidget": "daterange",
    "widgetSource": "native_explicit",
    "resolvedWidgetType": "date",
    "semantic": "date_range",
    "semanticSource": "declared",
    "resolutionStatus": "ready",
    "reasonCode": "",
    "options": {
      "raw": {
        "end_date_field": "date",
        "always_range": "1"
      },
      "recognized": {
        "end_date_field": "date"
      },
      "unsupported": {}
    },
    "behavior": {
      "domainRaw": "",
      "domainExpression": null,
      "contextRaw": ""
    }
  }
}
```

实施约束：

1. `nativeWidget` 只表示 XML 显式值。
2. 字段类型默认使用 `derivedWidgetType`，不能伪装成 native fact。
3. 未知 Widget 必须发布 `unresolved` 和稳定 reason code，或在不支持提交时阻断；
   不能没有声明就回字段类型默认。
4. Domain/Context 必须与 occurrence RAW 证据一致，并进入实际关系选择输入。
5. options 必须区分 recognized / unsupported，不要求所有选项立刻实现。
6. `componentKey` 继续来自现有 semantic/component registry。
7. Renderer readiness、后端契约 readiness、业务执行 readiness 继续分轴表达。
8. 任何新字段必须同步升级 Contract V2 Schema、前端 Decoder 和兼容范围。
9. 不复制 View XML 到 Widget；只发布已登记且可消费的语义。

建议实施顺序：

1. **Widget Provenance + fail-closed 分类**
   - 修正 `nativeWidget` 混用。
   - 建立 explicit / derived / compatibility / unresolved 来源。
   - 为未知 Widget 增加 reason code 和阻断策略。
2. **Field Behavior 出口**
   - 将 XML occurrence Domain/Context/options 编译到字段选择语义。
   - 对齐 `nativeIdentity.nativeBehavior`、`fieldDescriptor` 和
     `componentConfig`。
3. **数据驱动 Widget Variant**
   - 将 `daterange`、`analytic_distribution`、附件集合、avatar、radio 的语义
     收敛到现有注册表，而不是继续增加名称分支。
4. **List/Kanban/Activity Widget Profile**
   - 让列 occurrence 成为列语义和 Renderer 选择权威。
   - 接入 `handle`、`many2many_tags`、状态和关系列能力。
5. **嵌入 Widget 节点契约**
   - 为 `<widget name>` 增加 node semantic、options、data source、
     renderer readiness 和 unsupported reason。
6. **全表覆盖守卫**
   - 扫描实际安装模块的 View Widget 名，要求每项命中注册表或显式 unsupported；
   - 增加 Producer/Decoder 同批测试，防止后端发布前端不理解的新字段。

## 14. 验收边界

本检查点完成后应验证：

| 层 | 验收 |
| --- | --- |
| L1 | 所有当前源码 Widget 名有源码位置、来源模块和分类 |
| L2 | Widget 来源、semantic、componentKey、options、Domain/Context 可追踪 |
| L3 | 前端 Decoder 能严格识别新版 Widget Profile；未知能力不被静默补齐 |
| L4 | 后续实施再按真实原生页面验证 UI、权限、保存和错误闭环 |

本检查点没有完成 L4。源码中看到 `daterange` 分支、附件分支或 fail-closed UI，
不等于真实角色和真实数据下的业务行为已经通过。

## 15. 本轮验证与证据限制

已执行的只读检查：

- 当前 HEAD 源码扫描：349 个字段 Widget 声明、18 个唯一名称、4 个独立 Widget
  节点。
- 源码调用链核对：Odoo View/fields -> Parser/AST -> V2 Widget -> registry ->
  frontend presenter/registry。
- 交叉核对现有 P4 native-view capability map：
  `tree/kanban/activity` 的 Widget/options 仍标记为 unsupported。

发现并修复的基线证据问题：

- 初次执行 `verify.docs.all` 时，A01 的
  `inventory_manifest.json` 因 source revision 落后于当前 HEAD 而检查失败。
- 该问题属于 `baseline_evidence_defect`，不是本只读审计引入的产品回归。
- 已使用仓库既有生成器 `python3 scripts/audit/native_scene_inventory.py`
  从当前 HEAD 刷新模型、菜单、Action、View 和 manifest；
  `python3 scripts/audit/native_scene_inventory.py --check` 随后通过。
- 刷新后的 manifest source revision 为
  `ceaa207b716ed3e2157f49d315b72e071a722645`，inputs SHA256 为
  `0e61a142cae8359ff02b455891c80853007d43d7a3f308d9f12a1072ad117c4d`。

另执行的只读静态分类检查：

- `PYTHONPATH=. python3 scripts/verify/native_view_frontend_capability_map_guard.py`
  - `status: PASS`
  - `classified_atom_count: 32651`
  - `mapping_count: 22`
  - `unmapped_atom_count: 0`
  - `ambiguous_atom_count: 0`

该检查证明 P4 能力分类表本身完整一致；它不证明 `non_form_widget` 已被 Renderer
实现，后者的事实仍是 `unsupported`。

未执行：

- 浏览器渲染矩阵；
- 真实角色/公司/Record Rule 运行态；
- Widget 输入保存、错误、权限拒绝和状态转换；
- 全量可见 Odoo 模块安装后的 Widget 自动发现；
- Contract schema、Parser、Renderer 或测试代码修改。

## 16. 回答本轮核心问题

### 16.1 我们已经具备什么 Widget 接管能力？

- Form 字段 occurrence、stable Widget ID 和原生 locator。
- 常见字段类型的 canonical Widget 和 componentKey。
- status、money、percentage、duration、relations、selection、boolean、
  date/datetime 等语义推导。
- 注册表驱动的 Renderer identity/version/capability 校验。
- 关系入口、附件集合、daterange、analytic distribution、avatar、radio 等
  局部真实实现。
- 未知 componentKey 的前端 fail-closed 外壳。

### 16.2 安装新 Module 后能否自动交付所有 Widget？

不能。当前可以自动交付命中现有字段类型和语义规则的大量普通字段，但不能保证：

- 新 Widget 被识别；
- Widget 的 options 被消费；
- 嵌入 Widget 节点有 Renderer；
- 非 Form View 的 Widget 有专业组件；
- 原生 View Domain/Context 成为实际选择约束；
- 未支持能力会显式失败而不是降级。

### 16.3 最优先缺口是什么？

不是某一个 Renderer，而是 Widget 契约的来源和失败边界：

```text
原生显式 Widget
  != 字段类型默认 Widget
  != compatibility default
  != unresolved
```

没有这个区分，后续新增任何 Renderer 都无法可靠判断它是否真正承接了原生事实。

### 16.4 下一检查点应做什么？

进入一个独立 P0 实施检查点，只完成最小 Widget 契约闭环：

1. Widget provenance；
2. 未知 Widget fail-closed；
3. occurrence Domain/Context/options 的 Widget 出口；
4. 现有语义/组件注册表的数据化扩展；
5. Producer、Schema、Decoder 同批升级与非零测试。

不应同时扩展到 Calendar、Gantt、Dashboard 或场景组合。

## 17. 最终判断

本轮不批准“Odoo 原生 Widget 已可自动完整接管”的结论。

可以确认的是：

- 当前平台已有正确的复用基座；
- 普通字段和若干专用 Widget 已有真实消费；
- 下一步不需要重写 Parser 或 Renderer；
- 需要先补齐 Widget 来源、语义支持状态、options 和 Domain/Context 的统一契约出口。

本检查点到此停止，等待独立复核后再决定是否进入 Widget Contract Closure
实施批次。
