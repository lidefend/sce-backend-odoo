# NATIVE-SCENE-01 / B-S1 · 原生语义到统一契约转换审计

Status: source audit complete; runtime and frontend consumption not verified.

Date: 2026-11-16

Baseline: `ff6587d833f85469e1075c8ec3fcac09b9063462`

## 1. 检查点边界

本检查点属于 P4 只读审计，只回答以下问题：

- Odoo 原生 Action、View、字段、Modifier、Context 和 Domain 如何进入现有契约。
- 哪些转换规则由 P0 通用机制完成，哪些仍依赖 P1 行业 hook 或数据声明。
- 当前转换链在哪里保留原生身份，在哪里发生归一、降级、截断或重复转换。
- 后续应采用什么统一边界研究 Widget、交互、专业视图和自动接管。

本检查点不执行以下工作：

- 不修改产品源码、数据库、配置或业务数据。
- 不把 `payment.request`、`project.project` 当作普通页面交付验收样本。
- 不验证浏览器呈现、真实角色运行态或业务方法最终写入结果。
- 不实施 Action View Set、Widget、专业 Renderer 或自动接入修复。

证据等级严格区分如下：

| 等级 | 本检查点状态 | 含义 |
| --- | --- | --- |
| L1 原生事实 | 已验证 | 源码中的 Action、View、字段、方法和权限声明存在 |
| L2 后端契约 | 源码链已验证，运行态未验证 | 可追踪原生输入到契约组装和 seal；未重新采集真实数据库契约 |
| L3 前端消费 | 未验证 | 本检查点不检查 Renderer 是否真正消费全部契约 |
| L4 真实业务 | 未验证 | 本检查点不执行提交、审批、付款或权限负例 |

现有 `docs/contract/snapshots/*` 只能作为历史静态样本，不能冒充当前运行态。
例如 `payment_request_action_finance.json` 没有 `ui_contract`，只有
`ui_contract_raw`；`project_form_pm.json` 是 2026-08-23 的旧 v1 投影。
`ui_contract_v2_intent_admin.json` 是较新的单页 v2 样本，但仍是静态文件，
不是当前 HEAD 的运行态回执。

## 2. 结论摘要

当前平台已经具备一条可工作的“原生视图转统一页面契约”主链，但它不是单一
转换器，而是四段拼接：

1. Odoo `get_view()` 负责继承合并和当前用户视图裁剪。
2. `app.view.parser` 把 XML 转成兼容的 `ui.contract` 视图块。
3. `UiContractHandler`/`PageAssembler` 聚合字段、搜索、权限、动作和数据源。
4. Unified Page Contract V2 assembler 把视图块重组成 occurrence 级布局、
   Widget、状态、Action Rule，并执行 seal。

已有通用基础：

- Form 布局已经保留容器层级、字段重复 occurrence、native locator、
  raw modifiers、字段元数据和关系目标。
- Action 的模型、Domain、Context 会进入数据源和页面上下文。
- Model ACL、Record Rule、视图 group 裁剪、记录级能力有后端事实链。
- Pivot、Graph、Activity 已有专用 View Profile 投影外壳。
- 最终契约带生命周期、来源 authority、source hash 和 contract hash。

当前最关键的边界缺口：

1. 交付契约仍是**单个活动视图页面**，不是完整 Action View Set。它知道当前
   加载的是 list 或 form，但没有把同一 Action 的
   `tree + kanban + form + pivot + graph + ...` 作为同一可切换、可执行的视图族发布。
2. Action 的显式 `search_view_id` 没有在 Action Resolver 的标准化动作信息中保留；
   Search Contract 当前可能读取模型默认 search view，而不是 Action 指定的 search view。
3. Form 已有 Canonical Native View AST，但主路径仍由旧 parser 产出的 `ui.contract`
   驱动；AST 只用于部分 form structure 构建。存在两套解析与命名体系。
4. List 的重复列 occurrence 会在最终 `listProfile` 中按字段名或标签去重；
   原始 `column_occurrences` 没有成为 V2 list 的稳定交付单位。
5. 视图发生字段上的 Domain、Context、groups 和部分 options 虽可能保留在布局
   attributes，但没有统一的 occurrence 级语义编译出口。
6. 非 Form 视图仍保留兼容 fallback，fallback 可以合成列、打开动作或专业视图默认值。

因此，“原生能力是否可交付”已经不是问题；真正的问题是当前契约还没有把
Action View Set、View Profile 和 occurrence 级语义收敛成一个稳定边界。

## 3. 真实语义样本

### 3.1 `payment.request` 样本

当前正式付款申请入口不是单一视图，而是一个带明确 View Set 的原生 Action：

- Action XMLID：
  `smart_construction_core.action_payment_request_user_payment_apply`
- 模型：`payment.request`
- 视图族：`view_mode = tree,form`
- Tree View：
  `smart_construction_core.view_payment_request_tree`
- Form View：
  `smart_construction_core.view_payment_request_pay_form`
- Search View：
  `smart_construction_core.view_payment_request_search`
- Domain：
  `business_category_id.code = finance.payment.apply.pay`
- Context：
  `default_type=pay`、`default_business_category_code=...`、
  `search_default_type_pay=1`、`search_default_group_by_project_id=1`

源码：

- `addons/smart_construction_core/views/menu_business_taxonomy.xml:442-452`
  同时声明 `view_id`、`views`、`view_ids`、`search_view_id`、Domain、Context 和 groups。
- `addons/smart_construction_core/views/menu_business_taxonomy.xml:927-928`
  是两个菜单指向同一 Action。
- `addons/smart_construction_core/views/core/payment_request_views.xml:3-39`
  的 tree 声明了列、`optional`、`sum`、隐藏表达式和行级 decoration。
- `addons/smart_construction_core/views/core/payment_request_views.xml:42-60`
  的 form header 声明按钮、groups、`invisible` 复合表达式和 statusbar。
- `addons/smart_construction_core/views/core/payment_request_views.xml:61-150`
  声明容器、字段 occurrence、`readonly`、`invisible`、`required`、relation domain、
  `relation_entry` 和附件 widget。
- `addons/smart_construction_core/views/core/payment_request_views.xml:151-223`
  声明 notebook/page、一多子视图、可编辑 tree 和只读历史 tree。
- `addons/smart_construction_core/views/core/payment_request_views.xml:233-393`
  是 primary inherited form，用 XPath 移动、替换、增加字段和语义锚点。
- `addons/smart_construction_core/views/core/payment_request_views.xml:394-437`
  声明 search fields、filter、domain 和 group_by。
- `addons/smart_construction_core/models/core/payment_request.py:103-123`
  声明模型、mail/tier mixins 和排序。
- `addons/smart_construction_core/models/core/payment_request.py:767-772`
  声明状态字段；`action_submit` 和审批方法分别位于
  `addons/smart_construction_core/models/core/payment_request.py:3286-3425`。

这个样本证明：视图结构、字段 Widget、Modifier、关系入口、按钮、Search、
Domain、Context 和业务方法都属于同一个原生业务场景，不能只抽取树列和表单字段。

### 3.2 `project.project` 样本

项目台账同样是完整 View Set：

- Action XMLID：`smart_construction_core.action_sc_project_list`
- 模型：`project.project`
- `view_mode = tree,kanban,form`
- Action-bound Tree：`view_project_my_list_tree`
- Action-bound Form：`view_project_overview_form`
- Action-bound Kanban：`view_sc_project_kanban_card`
- Search View：`view_project_project_search_sc_business`

源码：

- `addons/smart_construction_core/actions/project_list_actions.xml:3-20`
  声明模型、视图顺序、Domain、create/delete/duplicate context、委派新建入口和权限组。
- `addons/smart_construction_core/actions/project_native_action_overrides.xml:8-28`
  通过 `ir.actions.act_window.view` 把三种视图分别绑定到同一 Action。
- `addons/smart_construction_core/views/core/project_views.xml:82-160`
  使用继承视图替换 statusbar、增加审批和业务按钮、重建 stat button box、
  增加 tab/group、字段和 data-sc anchors。
- `addons/smart_construction_core/views/core/project_views.xml:369-448`
  继续通过多优先级继承修改 tree、form、kanban 和简化表单按钮。
- `addons/smart_construction_core/views/core/project_search_views.xml:3-63`
  声明搜索字段、filter、domain、group_by 和日期 interval。
- `addons/smart_construction_core/views/core/project_list_views.xml:3-22`
  声明列顺序、标签、optional、默认排序。
- `addons/smart_construction_core/models/core/project_core.py:386-449`
  声明阶段、负责人、生命周期状态等模型事实。
- `addons/smart_construction_core/models/core/project_core.py:517-530`
  声明责任矩阵、付款申请和资金基准的 one2many 关系。

这两个样本说明：一个原生业务入口的最小可交付身份至少是：

```text
Action identity
  + Model
  + ordered View Set
  + Search View
  + Domain / Context
  + Field / container / action semantics
  + Permission scope
  + business execution authority
```

## 4. 当前真实调用链

### 4.1 Action 解析

`UiContractHandler` 将 menu/action/model 入口分派给 `ActionDispatcher`：

- `addons/smart_core/handlers/ui_contract.py:181-193`
  识别 `menu/model/action_open/view`。
- `addons/smart_core/handlers/ui_contract.py:585-665`
  将 `action_open` 转为 Action 分发；当有 record 或 form profile 时优先完整 form。
- `addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py:86-133`
  根据 `ir.actions.act_window/server/client/url/report` 分流。
- `addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py:97-106`
  act_window 把 `res_model`、`view_mode` 和 menu context 交给 `PageAssembler`。
- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:98-144`
  标准化 Action 身份、模型、view_mode、Domain、Context 和 XMLID。
- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:148-176`
  Server Action 在契约读取期间不执行；只有显式 window mapping 可以进入页面装配。

当前优点：

- Action XMLID、ID、模型、view_mode、Domain 和 Context 都能解析。
- Server Action 不会因读取页面契约而执行代码。

当前缺口：

- `as_action_info()` 没有发布 `views`、`view_ids`、`search_view_id`。
- Action View Set 的精确绑定只在后续 `PageAssembler` 再次按 Action ID 查询数据库时恢复，
  标准化 Action 契约本身并不完整。

### 4.2 原生 View 获取与合并

- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:364-394`
  选择 Action，并扩展计划装配的视图类型。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:511-625`
  按视图类型获取原生 View，记录 `view_ids_by_type` 和 field requirements。
- `addons/smart_core/app_config_engine/models/app_view_config.py:110-187`
  用 Action 的 `(view_id, view_type)` 精确选择默认 View，并保留解析后的 source view ID。
- `addons/smart_core/app_config_engine/models/app_view_config.py:652-772`
  `get_view()` 使用当前用户，保留 Odoo 的继承合并和 groups 裁剪；仅在旧版本兼容时使用
  `fields_view_get()`。
- `addons/smart_core/app_config_engine/models/app_view_config.py:190-230`
  校验 `get_view()` 返回的 source view 与请求模型、视图类型一致。

结论：

- View 继承不是在前端重新拼接，而是交给 Odoo `get_view()` 完成。
- `get_view()` 是当前用户敏感事实；使用 sudo 会改变继承节点的可见性。
- 单视图 source view identity 已保留；完整 Action View Set 只作为装配输入存在，
  不是最终交付契约的一等对象。

### 4.3 `ui.contract` 生成

- `addons/smart_core/app_config_engine/models/app_view_config.py:377-520`
  调用原生 parser，失败时进入兼容 fallback；只读 projection 使用 transient config，
  不写 `app.view.config`。
- `addons/smart_core/app_config_engine/services/native_parse_service.py:38-75`
  主 parser 使用当前请求用户环境，避免 sudo 改变视图组合。
- `addons/smart_core/app_config_engine/services/parse_fallback_service.py:38-54`
  parser 无有效结果时进入 fallback。
- `addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py:37-79`
  `app.view.parser` 是当前多视图 parser 入口。
- `addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py:82-180`
  获取最终 XML、补字段元数据、建立 lossless tree，并按 view type 分派。
- `addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py:183-246`
  使用 `fields_get`/view field snapshot 补齐 inline x2many 和 reference 所需字段。
- `addons/smart_core/app_config_engine/services/view_Parser/base.py:56-93`
  有直接 `get_view()` 兼容实现。
- `addons/smart_core/app_config_engine/services/view_Parser/base.py:163-199`
  对 attrs/readonly/required/invisible 做第一轮收集。

Form parser 输出：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:689-779`
  输出 layout、capabilities、statusbar、header/stat buttons、field_modifiers、
  subviews、chatter 和 attachments。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:1005-1230`
  DOM 布局保留原生容器、字段、按钮、native locator、source position 和 attributes。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:1435-1474`
  合并 fields_info modifiers 与 XML occurrence modifiers，同时保留 Domain、Context、
  widget 和 groups。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:1504-1620`
  收集 inline/reference x2many subviews。

Tree/Kanban/Pivot/Graph parser 输出：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:500-650`
  tree 输出列、列 occurrence、行操作、默认排序、分页、row class 和 capabilities。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:462-498`
  在字段 occurrence 上保留 modifiers、decoration 和关系 create/write 行为。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Kanban Pivot Graph.py:30-111`
  输出 kanban 字段、模板、group field、quick action 和 presentation。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Kanban Pivot Graph.py:127-155`
  输出 pivot measure/dimension/axis/interval/aggregate。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Kanban Pivot Graph.py:158-189`
  输出 graph type/measure/dimension/interval/aggregate/format。

Calendar/Gantt/Activity/Search parser 输出：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt Activity.py:36-76`
  calendar 输出 start/stop/color、scale、open-popup 和字段节点。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt Activity.py:79-131`
  gantt 输出 date/progress/group/dependency/scale/decoration。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt Activity.py:134-314`
  activity 输出字段/节点 occurrence、QWeb template 和 action occurrences。
- `addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt Activity.py:317-365`
  search 输出 filters、group_by、fields、native locator 和 source position。

### 4.4 `ui.contract` 聚合

- `addons/smart_core/handlers/ui_contract.py:324-362`
  先 finalize data，再注入 primary view projection，最后调用扩展 finalizer。
- `addons/smart_core/handlers/ui_contract.py:393-413`
  交付形状和 contract surface 仍可能被 governance 处理。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:496-509`
  从模型配置生成 fields，缺失时回退 `fields_get`。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:627-653`
  Search Contract 独立生成，并应用 Action search defaults。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:662-690`
  聚合 Model ACL、Record Rule 和记录 capabilities。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:692-711`
  聚合 Action 按钮和 toolbar。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:713-749`
  聚合 report、workflow 和 validator。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:751-799`
  发布 head、Domain、Context、collection presentation、create defaults 和 record version。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:3417-3566`
  将关系字段权限、导航、create mode、domain、order 和 search dialog 合成为
  `relation_entry`，并投影到每个字段 occurrence。

### 4.5 `ui.contract.v2`

- `addons/smart_core/handlers/ui_contract_v2.py:610-626`
  是 v2 对外入口，成功结果还要通过组件能力校验。
- `addons/smart_core/handlers/ui_contract_v2.py:662-700`
  解析 source type，强制只读 projection context，并用当前用户构建 projection env。
- `addons/smart_core/handlers/ui_contract_v2.py:704-760`
  解析 Action、menu、record、render profile 和缓存身份。
- `addons/smart_core/handlers/ui_contract_v2.py:849-925`
  命中缓存则复用 source；否则调用 native form source 或既有 `UiContractHandler`。
- `addons/smart_core/handlers/ui_contract_v2.py:1066-1102`
  合并 model/view/context/domain/record/source_meta。
- `addons/smart_core/handlers/ui_contract_v2.py:1104-1187`
  依次加入 action window、集合新建入口、业务类别、业务操作、
  standard submit、collaboration、group columns 和记录快照。
- `addons/smart_core/handlers/ui_contract_v2.py:1188-1217`
  调用 projected source hook，再执行 source normalizer 和 action group entitlements。
- `addons/smart_core/handlers/ui_contract_v2.py:1218-1233`
  调用 Unified Page Contract V2 assembler。
- `addons/smart_core/handlers/ui_contract_v2.py:1234-1308`
  再做字段策略、business config、V2 extension finalizer、Action Rule、
  workflow semantics 和 modifier hydration。
- `addons/smart_core/handlers/ui_contract_v2.py:1310-1355`
  验证原生节点、组件能力、裁剪和交付引用。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:977-1038`
  根据 source type 分派到 ui.contract/native form，再合并 action、生成布局 DSL 并 seal。

### 4.6 Action View Set 的实际去向

`PageAssembler` 会为多个 view type 分别生成 `views.*`，并发布
`view_ids_by_type`：

- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:511-625`
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:2157-2205`

但 V2 只选择当前页面的一种活动视图：

- `addons/smart_core/core/unified_page_contract_v2_assembler.py:1219-1252`
  用一个 `view_type` 生成一个 `pageInfo` 和一个 `layoutType`。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:369-451`
  基础契约只有单页面字段，没有 View Set 节点。
- `addons/smart_core/handlers/ui_contract_v2.py:1671-1743`
  虽重新读取 Action，但只注入 title、model、Domain 和 Context；没有注入 ordered views。
- `docs/contract/snapshots/ui_contract_v2_intent_admin.json:3257-3267`
  历史 v2 样本也只发布一个 `viewType: list`。

因此当前实际交付单位是“Action 当前选中的一个 View”，而不是完整 Action View Set。

### 4.7 最终 seal

- `addons/smart_core/core/contract_lifecycle.py:156-162`
  semantic payload 去除传输层 meta。
- `addons/smart_core/core/contract_lifecycle.py:186-242`
  生成 schema、source、runtime、integrity 和 authority evidence。
- `addons/smart_core/core/contract_lifecycle.py:245-260`
  对契约执行最终 seal。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:1017-1030`
  在 seal 时绑定 source type、request、client type 和 source authority。

seal 能证明交付数据与本次 source 一致，但不能证明 Action View Set 已完整表达。

## 5. 原生语义转换规则矩阵

| 原生语义 | 当前转换规则 | 身份保留情况 | 状态与缺口 |
| --- | --- | --- | --- |
| Action XMLID/ID | `ActionResolver` 读取 external ID，`action_info` 保留 ID/XMLID | 有 ID；不是所有视图定义都发布 XMLID | 已实现；完整 Action contract 未统一 |
| Action model | `res_model` 进入 PageAssembler 和 V2 pageInfo | 有 | 已实现 |
| Action Domain | 安全表达式求值，进入 head/source/dataSource params | 保留 parsed + raw 的多数路径 | 已实现；最终 action-level domain contract 未独立发布 |
| Action Context | 与请求上下文合并，进入 head/source/dataSource | 有 | 已实现；合并优先级分散在多个阶段 |
| View order/view_mode | PageAssembler 扩展并按类型装配 | 装配期有 | 最终契约只保留活动视图，无完整 View Set |
| `ir.actions.act_window.view` | `_projection_identity()` 按 view type绑定 source view | 装配置有 | 当前页正确；跨视图选择契约缺失 |
| View inheritance | Odoo `get_view()` 合并 | 有最终 source view ID | 已实现；原始每个继承层身份不交付 |
| Current-user view pruning | `get_view()` 使用请求用户 | 有 | 已实现；需专门权限运行态复验，不在本检查点 |
| Field metadata | `fields_get()` / resolved view fields | name/type/label/relation/selection 等 | 已实现；不同字段类型的覆盖需继续专项核验 |
| Form container tree | 旧 parser DOM → V2 formal container tree | 容器名、结构路径、attributes | 已实现；命名重复和匿名容器碰撞风险需验证 |
| Form field occurrence | native locator + occurrence index + source position | 每个 occurrence 有稳定 widget ID | 已实现 |
| Form labels | occurrence label 优先，模型 label 兜底 | occurrence 优先 | 已实现 |
| Tree columns | 字段名 + columns_schema | 列顺序有 | 重复同字段 occurrence 被按 name/label 收敛 |
| Tree column occurrence raw evidence | parser 产生 `column_occurrences` | source 中可能保留 | V2 listProfile 没有把它作为正式 occurrence 集 |
| Modifiers | raw/parsed expression 保留，最终按记录和依赖 hydration 求值 | 有 AST/静态值 | Form 较强；未知表达式 fail-closed |
| Modifier dependencies | 收集 `field_compare/field_truthy` 等字段并补读 | 有 | 有预算上限；跨 subview 依赖不进入 root hydration |
| Widget | 原生 widget 经 alias + semantic resolver 映射组件 | 保留 native widget + canonical widget | 已实现；手工专用 widget 仍需专项核验 |
| Widget options | options → widgetOptions / widgetSemantics | 常见语义有 | 任意 Widget 专属 options 未形成统一通行规则 |
| Relation target | `fields_get().relation` → relation descriptor | model/type 有 | 已实现；关系权限不由此推导 |
| Relation entry | 权限、action/menu、create mode、domain、order、dialog 合成 | 有稳定 entry | 已实现；P1 policy 和 native options 共同参与 |
| Field-level Domain/Context | 模型字段元数据可进入 descriptor；XML occurrence attributes 可留在节点 | 部分保留 | view occurrence 未统一编译到 widget 的 `domain_expression` |
| Search filters/group_by/fields | Search parser + `app.search.config` | 多数项有 native locator | 已实现 |
| Action search_view_id | 不在标准化 action_info 中 | 可能丢失 | Search 可能读取模型默认 search view，而非 Action 指定 View |
| Header/row/smart/body buttons | parser 归一，保留 native locator/type/name/context/domain/confirm | 多种 action 有 backend identity | 已实现；按钮权限与业务不可用原因需继续运行态核验 |
| Object/action/server/url buttons | action kind 分流 | object/action/url/server ID | 已实现；server contract read 不执行 |
| Workflow statusbar | 只认可原生 `widget=statusbar` | 显式字段和 states 有 | 已实现；无 statusbar 时不再按模型字段臆造 |
| Model ACL | PageAssembler `check_access_rights` | rights 有 | 已实现 |
| Record Rule | `check_access_rule` / `_filter_access_rules` | rights + denied reason | 已实现 |
| Field groups | 由 `get_view()` 裁剪 | 视图中不可见节点直接消失 | 已实现；单独字段权限事实未统一发布 |
| Multi-company | projection env 保留 company context，权限/规则按 company 执行 | context 有 | 已实现；多公司矩阵未运行验证 |
| Collection create | ACL × context × view capabilities × published route | 有 verdict 和目标 | 已实现；依赖多个 authority 合并 |
| Data source | 根据 view type 生成 default_get/read/list | fields/order/limit/context/domain | 已实现；字段数量有传输预算 |
| Pivot/Graph profile | native measures/dimensions/axes/intervals/aggregate | 有独立 profile | 已实现后端投影；真实全范围统计未验证 |
| Calendar/Gantt profile | native attrs 和 slots | 有独立 block | 已实现解析；仍含默认字段兜底，Renderer 不在本检查点 |
| Activity profile | field/node occurrences、template、actions | occurrence 证据较完整 | 已实现后端投影；真实运行行为未验证 |
| Dashboard | 通过 client action、场景或其他来源接入 | 来源不统一 | 未达到统一 native view profile |
| Report | `ir.actions.report` 独立适配 | report action 有 | 不是页面 View；执行闭环未在本检查点验证 |
| Contract identity | source authority + source hash + contract hash + lifecycle | 有 | 已实现 |

## 6. 两套视图投影体系

### 6.1 旧 parser → ui.contract

主路径：

```text
get_view
  -> app.view.parser
  -> ui.contract.views.*
  -> PageAssembler aggregation
  -> ui.contract
```

这个 parser 覆盖面广，包含 tree/form/kanban/pivot/graph/calendar/gantt/activity/search。
但它是按 view type 组装的字典型 parser，术语、节点字段和 occurrence 规则并不完全统一。

### 6.2 Canonical Native View AST

- `addons/smart_core/core/native_view_projection.py:2-14`
  明确其为单一 thin projection，不是第二套公共 schema。
- `addons/smart_core/core/native_view_projection.py:48-80`
  定义 canonical field occurrence、container 和 native view。
- `addons/smart_core/core/native_view_projection.py:165-229`
  一次 `get_view()`，必要时 `fields_get()`。
- `addons/smart_core/core/native_view_projection.py:239-300`
  保留完整容器层级、field occurrence、locator、raw modifiers 和 relation descriptor。
- `addons/smart_core/core/native_view_projection.py:304-372`
  当字段只属于一个具名 group 时才产生候选 primary owner；重复字段保持 unowned。
- `addons/smart_core/core/native_view_projection.py:375-552`
  由 AST 生成 form structure contract。

当前使用范围：

- `addons/smart_core/handlers/ui_contract_v2.py:2795-2861`
  在 business operation profile 需要 form structure 时调用 AST。
- `addons/smart_core/handlers/ui_contract_v2.py:4103-4242`
  在 native form composition enrichment 时调用 AST。

结论：

- Canonical AST 的保真方向是正确的，但还没有成为所有 View Profile 的统一原生输入。
- 当前 Form 同时存在旧 parser layout 和 AST form structure，两者的容器/字段身份、
  角色分类和 fallback 需要收敛。
- 不应再新建第三套 parser；后续应决定由 AST 扩展，还是把旧 parser 明确降为
  view-type adapter。

## 7. Modifier 与最终状态

当前 modifier 处理不是简单布尔过滤，而是四阶段：

1. parser 保留原生 expression/literal。
2. V2 组装把 raw modifier 写入节点、field descriptor 和 widget status。
3. 最终 hydration 补读 expression 依赖字段。
4. 最终 status pass 统一求值，未知表达式 fail-closed。

源码：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:52-195`
  将 native 表达式归一为 `field_compare/field_truthy/all/any/not`。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:2299-2397`
  namespace alias 归一、容器 invisible 和字段节点状态生成。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:3235-3360`
  读取 modifiers，并生成初步 field status。
- `addons/smart_core/core/unified_page_contract_v2_modifier_dependencies.py:118-164`
  收集 modifier 的字段依赖。
- `addons/smart_core/core/unified_page_contract_v2_modifier_dependencies.py:386-541`
  按最终契约补读依赖字段；缺失值保持 fail-closed。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:4175-4233`
  对静态值、context 比较、字段比较、all/any/not 求值。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:4615-4713`
  最后按最终记录数据同步容器和 occurrence 级控件状态。

这种机制适合继续作为通用规则复用，但还需要回答两个边界：

- `parent.*` 和 subview modifier 当前不全部进入 root record hydration，子表上下文需要
  自己的求值 scope。
- 未知表达式、缺失字段和预算截断必须继续产生结构化原因码，不能退回静态 true/false。

## 8. P0 通用机制与 P1 专用 hook

### 8.1 P0 通用机制

- Action 解析和类型分流。
- `get_view()` / `fields_get()` 调用。
- View type parser。
- 字段、容器、Widget、Modifier、Search、Action Rule、DataSource 的统一装配。
- 权限读取、记录级 verdict、关系入口和创建入口。
- Unified Page Contract V2 shell、trim、validation 和 seal。

P0 中仍混有需要收敛的通用产品规则：

- `business_category` form policy。
- standard submit button。
- platform form save action。
- relation entry policy。
- list/default visibility policy。

这些规则是产品语义，不应藏在 parser 默认值里；现状多数已通过数据或独立 hook 声明，
但调用点仍分布在 PageAssembler 和 UiContractV2Handler 多个阶段。

### 8.2 P1 行业 hook

`smart_core_finalize_projected_contract_data()`：

- `addons/smart_construction_core/core_extension.py:1559-1580`
  对 `sc.plan` 和 `project.project` 做行业结构/表面治理。
- `addons/smart_construction_core/core_extension.py:1581-1593`
  对 partner form 做行业字段治理。
- `addons/smart_construction_core/core_extension.py:1594-1650`
  对正式列表 Action 应用 action-scoped column lock。

`smart_core_finalize_unified_page_contract_v2()`：

- `addons/smart_construction_core/core_extension.py:594-620`
  移除行业 finalizer 中误入的渲染 adapter/fallback。
- `addons/smart_construction_core/core_extension.py:621-646`
  对 `construction.work.breakdown` 注入层级治理。
- `addons/smart_construction_core/core_extension.py:647-655`
  注入 workflow、financial workspace 和声明字段 presentation。

`smart_core_normalize_projected_contract_data()`：

- `addons/smart_construction_core/core_extension.py:659-678`
  只在 general contract/tax 场景执行行业 normalizer，避免全量 deepcopy。

结论：

- P1 hook 当前承担行业语义后处理，尚不是“安装即自动接管”的统一 View Profile。
- 下一步应优先保留 hook 作为声明扩展点，而不是继续在 hook 中重建 layout。

## 9. Search Contract 缺口

`app.search.config` 自身实现：

- `addons/smart_core/app_config_engine/models/app_search_config.py:52-106`
  解析 search view、`ir.filters`、group_by 候选和 defaults。
- `addons/smart_core/app_config_engine/models/app_search_config.py:419-444`
  获取 search view；参数未提供时调用 `Model.get_view(view_type='search')`。
- `addons/smart_core/app_config_engine/models/app_search_config.py:446-500`
  保留 filter native locator、source position 和 attributes。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:1806-1853`
  将 filters、group_by、fields、favorites、search panel 放入最终 `searchContract`。

PageAssembler 调用：

- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:627-653`
  `search_view_data=view_projection_sources.get("search")`。

问题：

- Action 明确绑定 `search_view_id` 时，`ActionResolver.as_action_info()` 未保留该字段。
- 当 `search` 不在装配的 view_types 中，`view_projection_sources["search"]` 为空，
  `app.search.config` 会使用模型默认 search view。
- `payment.request` 和 `project.project` 都显式绑定了业务 search view，因此这是一个
  可直接用真实样本验证的契约缺口。

该缺口不要求前端修复；它属于后端 Action → Search Contract 的身份保真问题。

## 10. List 与 Form occurrence 的非对称

Form：

- parser 保留每个 field occurrence。
- V2 使用 `nativeLocator`、`occurrenceIndex`、`sourcePosition`。
- 重复字段具有不同 widget ID。
- 重复 label 不会被强制合并。

List：

- parser 提供 `column_occurrences`。
- 最终 `listProfile.columns/fact_columns` 以字段名列表为主。
- `_merge_business_list_profile()` 在没有明确保留条件时按标签或字段名去重。
- V2 list 只消费 `columns`、`columns_schema` 和 `listProfile`，没有消费
  `column_occurrences` 形成 occurrence 级列。

源码：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:529-566`
  收集 column occurrence 和去重后的 columns。
- `addons/smart_core/handlers/ui_contract_v2.py:3241-3353`
  生成最终列、标签并去重。
- `addons/smart_core/handlers/ui_contract_v2.py:3490-3519`
  用 name-keyed `columns_schema` 重写 native tree block。

影响：

- 普通台账通常没有重复列，因此影响有限。
- 专业列、同字段不同 Widget、同字段不同 modifier、重复金额/状态列无法稳定表达。
- 后续预算/WBS/专业树必须明确是否需要 list occurrence contract，避免又引入页面特判。

## 11. View-level 字段 Domain/Context

当前 Form parser 会保留：

- `node["attributes"]` 中的完整 XML attributes。
- `field_modifiers[field]` 中的 Domain、Context、groups、widget。

但在 V2 归一阶段：

- `_assemble_ui_contract()` 只把 `readonly/required/invisible/column_invisible`
  从 `field_modifiers` 合入字段源。
- `_field_source_with_node_info()` 从 node 复制一组白名单语义和 selected fieldInfo，
  没有把 occurrence attributes 中的 Domain/Context 统一编译到 widget。
- `_field_widget()` 只有在字段源已有 `domain` 时生成 `domain_expression`。

源码：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:1435-1474`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:1290-1301`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:2046-2113`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:2180-2225`

结论：

- 原生 XML 值可能仍存在于布局节点 attributes 中，但 Widget 消费者没有统一得到它。
- 这属于“已保留、未统一编译”的中间状态，不应被表述为已完整接管。
- `payment.request.contract_id` 的视图 Domain 是可直接验证该问题的样本。

## 12. Fallback 与默认语义

Form 运行时保护：

- `addons/smart_core/app_config_engine/services/native_parse_service.py:69-74`
  只读 form parser 失败时不再使用兼容 fallback。
- `addons/smart_core/app_config_engine/models/app_view_config.py:577-630`
  Form 在无显式 statusbar 时发布 `field=None/states=[]`，不按 state 字段臆造。

仍需关注：

- Tree fallback 在无列时按“业务优先字段”推断列。
- Tree fallback 在无按钮时合成 `open_form` 行动作。
- Tree fallback 有 `id desc`、50 条分页等默认。
- Kanban fallback 默认 `quick_create=True`、`stages_field=stage_id`。
- Calendar parser 默认 `date_start/date_end/user_id`。
- Gantt parser 默认 `date_start/date_end/progress`。
- `get_contract_api()` 对缺失专业块仍提供最小默认 dict。

源码：

- `addons/smart_core/app_config_engine/models/app_view_config.py:776-887`
- `addons/smart_core/app_config_engine/models/app_view_config.py:889-930`
- `addons/smart_core/app_config_engine/models/app_view_config.py:613-630`
- `addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt Activity.py:36-92`

这些 fallback 对兼容有价值，但不能无条件视为原生语义。后续必须区分：

- `native_explicit`
- `model_metadata_derived`
- `compatibility_default`
- `unresolved`

只有前两类可以进入正式自动接管路径；兼容默认值应在契约中显式标注或 fail closed。

## 13. 数据与传输预算

当前 V2 对 data source 有固定预算：

- `addons/smart_core/core/unified_page_contract_v2_assembler.py:2790-2859`
  Form 最多请求 80 个字段，list/kanban 最多 40 个字段，固定初始 limit=20。
- `addons/smart_core/core/unified_page_contract_v2_modifier_dependencies.py:14-23`
  初始记录快照预算 80，可见布局 hydration 预算 40。
- `addons/smart_core/handlers/ui_contract_v2.py:3295-3320`
  非 strict list 最多 24 个可见列。

这些数字属于受控传输/渲染常量，不是业务事实，但仍会产生产品可见边界：

- 超过预算的 layout facts 需要后续请求补齐，当前第一屏契约可能不是完整数据。
- 非 strict 列表可能裁掉原生列。
- 必须确保被裁掉的是展示事实，不是权限、必填、状态或 Action 判定依赖。

本检查点不判定这些常量是否正确，只登记它们必须作为后续 L2/L3 核验对象。

## 14. 缺口登记

| 编号 | 严重度 | 结论 | 责任层 | 证据 |
| --- | --- | --- | --- | --- |
| B-S1-G01 | High | 最终契约没有完整 Action View Set，只交付活动视图 | P0 | `unified_page_contract_v2_assembler.py:1219-1252`、`ui_contract_v2.py:1671-1743` |
| B-S1-G02 | High | Action 显式 `search_view_id` 未进入标准 Action contract，Search 可能取模型默认 View | P0 | `action_resolver.py:98-144`、`app_search_config.py:419-444`、`page_assembler.py:627-653` |
| B-S1-G03 | High | 旧 parser 与 Canonical Native View AST 并行，AST 尚未成为统一入口 | P0 | `contract_Parser.py:37-41`、`native_view_projection.py:2-14`、`ui_contract_v2.py:2823-2837` |
| B-S1-G04 | Medium | List 重复 occurrence 未成为 V2 稳定单位 | P0 | `parsers Tree Form.py:529-566`、`ui_contract_v2.py:3241-3353` |
| B-S1-G05 | Medium | View-level Domain/Context 保留在 attributes，但未统一编译到 Widget | P0 | `parsers Tree Form.py:1435-1474`、`unified_page_contract_v2_assembler.py:2046-2225` |
| B-S1-G06 | Medium | 非 Form 兼容 fallback 仍会合成列、动作或专业视图默认值 | P0 | `app_view_config.py:776-930`、`parsers_Calendar_Gantt Activity.py:36-92` |
| B-S1-G07 | Medium | Action Domain/Context 合并分散在 PageAssembler 与 V2 handler，缺少单一 Action Contract 节点 | P0 | `page_assembler.py:404-428`、`ui_contract_v2.py:1703-1743` |
| B-S1-G08 | Medium | 固定数据/列/依赖预算可能影响完整第一屏事实 | P0 | `unified_page_contract_v2_assembler.py:2790-2859`、`modifier_dependencies.py:14-23` |
| B-S1-G09 | Medium | P1 行业 finalizer 仍在契约完成后改写布局和业务字段呈现 | P1/P0 boundary | `core_extension.py:594-655`、`core_extension.py:1559-1650` |
| B-S1-G10 | Medium | 当前静态快照不足以证明 payment/project 的当前 v2 契约 | P4 evidence | `project_form_pm.json` 为旧 v1；`ui_contract_v2_intent_admin.json` 为静态单页 |
| B-S1-G11 | High | L3/L4 未验证：没有证明前端实际消费全部字段、Search、Action 和权限 verdict | L3/L4 | 本检查点明确排除浏览器和真实角色运行态 |

## 15. 应当保留和复用的机制

应保留：

1. Odoo `get_view()` 作为继承合并和当前用户裁剪唯一权威。
2. `fields_get()` / resolved view fields 作为字段元数据权威。
3. Canonical `NativeFieldOccurrence` / `NativeContainer` 的 occurrence 身份思路。
4. raw modifier + 最终依赖 hydration + fail-closed 求值。
5. Model ACL、Record Rule 和 relationship entry 的服务端事实。
6. `ui.contract.v2` shell、component identity、status/action/data/runtime 分区。
7. contract lifecycle 的 source hash / integrity hash / authority evidence。
8. 现有 P1 hook 作为行业声明扩展点。

不应重复建设：

- 前端业务页面和业务方法。
- 第二套字段权限或状态机。
- 用场景模型重写 Odoo Action/View。
- 为单一行业页面再造通用 Form/List Renderer。
- 在前端按 model/name 推断缺失 Widget、动作或权限。

## 16. 推荐的统一边界

后续架构应收敛为：

```text
Native Action Contract
  + Action View Set
  + selected active View
  + Native View Contract
      + identity
      + model
      + security
      + data
      + actions
      + status
      + view_profile
```

View Set 至少应声明：

- ordered view type；
- action-bound view ID；
- per-view capabilities；
- default/active view；
- search view ID；
- Action Domain/Context；
- 可用性和不可用原因；
- 切换视图时复用的数据源和权限 scope。

View Profile 应分别扩展：

- `list_profile`
- `form_profile`
- `kanban_profile`
- `pivot_profile`
- `graph_profile`
- `calendar_profile`
- `gantt_profile`
- `activity_profile`
- `hierarchy_profile`
- `dashboard_profile`
- `report_execution`

不需要把专业 Profile 塞入一个巨型通用字段；应共享统一外壳、身份、权限、数据和执行协议，
专业语义由显式 profile 扩展。这样既不会重复业务能力，也不会把所有视图降级成普通列表。

## 17. 对 B-S2 的具体输入

下一检查点不应再做普通页面验收。建议 B-S2 只研究以下三项：

1. Action View Set 契约：
   - 是否已有可复用的 view selector/tabs 契约。
   - 如何绑定 Action XMLID/ID、ordered views、search view 和当前 active view。
   - 如何保证切换视图仍使用同一 Domain、Context、权限和数据事实。
2. Search View 身份：
   - 以 `payment.request` 和 `project.project` 的两个显式 Search View 为样本。
   - 明确 Action `search_view_id` 的优先顺序。
   - 判断现有 `app.search.config` 只需补身份，还是需要重构 search projection。
3. occurrence 语义出口：
   - 定义 field/button/container 在 Form/List 中的最小 occurrence 身份。
   - 明确 Domain、Context、groups、options 应进入哪个 profile 字段。
   - 不实施 Renderer，只形成契约字段与转换规则。

Widget、交互执行、Calendar/Gantt/Dashboard 专项继续留到后续检查点。

## 18. 回答本轮五个问题

### 18.1 已具备哪些 Odoo 原生业务能力？

已有后端事实链可覆盖：

- Window Action 及其模型、Domain、Context、视图类型。
- Form、Tree/List、Kanban、Search、Pivot、Graph、Calendar、Gantt、Activity 的视图解析。
- 字段、关系、容器、Widget、Modifier 和字段 occurrence。
- Model ACL、Record Rule、当前用户视图裁剪和记录能力。
- Header/row/stat/body buttons、relation entry、create entry。
- Client/URL/Report/Server Action 的类型分流。
- 统一页面契约、状态契约、动作契约、数据源和生命周期 seal。

这只是“后端能力存在或已进入契约”的结论，不等于 L3/L4 交付完成。

### 18.2 一个原生菜单、Action、View Set 如何构成独立业务场景？

可以，但当前交付契约尚未直接表达完整场景。实际必须保留：

- 菜单身份和发布权限；
- Action 身份、模型、Domain、Context；
- ordered View Set 和 Action-bound view IDs；
- Search View 身份；
- 每个 View 的完整原生语义；
- 记录级权限、状态和动作；
- 业务方法和执行回执。

当前 `ui.contract.v2` 表达的是其中“一个活动 View 页面”。完整场景仍由菜单/发布层、
Action Resolver 和 PageAssembler 的临时装配输入共同维持，尚未收敛成单一稳定契约。

### 18.3 哪些复杂专业视图已具备原生事实与后端解析？

具备较明确后端投影：

- Pivot：measure、dimension、row/col axis、interval、aggregate。
- Graph：type、measure、dimension、interval、aggregate、format。
- Activity：field/node occurrence、deadline/type/assignee slots、template、actions。
- Form hierarchy/structure：Canonical AST、container、field ownership 候选。
- Search：filter、group_by、search fields、search panel 的部分数据。

仍不能宣称完整接管：

- Calendar/Gantt 有解析 block，但仍含默认字段和独立 Renderer/交互缺口。
- Dashboard 来源多，尚未统一 View Profile。
- Report 是执行类型，不是页面 View，未完成闭环验证。
- List occurrence、Action View Set、Action-bound Search View 仍不完整。

### 18.4 哪些 Action 或 View 类型尚未接入？

后端已有入口但未完成统一场景交付：

- Window Action 的完整 View Set。
- Server Action 的受管页面映射和业务返回 Action 的通用处理。
- Client Action 的 Dashboard/Workspace 统一来源。
- Report Action 的页面入口、参数、执行和回执闭环。
- URL Action 的统一导航结果。
- Calendar、Gantt、Dashboard 的统一专业 View Profile。
- Search View 的 Action 级身份和完整收藏/上下文语义。

本检查点不能判定这些类型“不存在”；它们只是尚未成为统一接管契约的一部分。

### 18.5 下一轮优先检查哪些真实入口？

不再做普通页面交付验收。优先顺序：

1. `payment.request` Action View Set + Search View identity。
2. `project.project` 多视图 Action、继承后视图和切换语义。
3. Form/List occurrence 契约出口。

这三个对象足以验证 Action、多视图、Search、继承、Modifier、Widget、关系和专业扩展边界。

## 19. 最终判断

本轮审计建议：

- 保留现有 Unified Page Contract V2，不重新开发契约体系。
- 把 Canonical Native View AST 视为后续统一 View Profile 的候选内核。
- 把完整 Action View Set 和 Action-bound Search View 作为下一轮最小、最高价值缺口。
- 继续把 P1 hook 保留为行业声明扩展，不把行业布局逻辑下沉到 P0 或前端。
- 在 B-S2 完成前，不对 Widget、交互执行、专业 Renderer 和自动接管作“已解决”结论。

本检查点到此停止，等待独立复核和下一轮调度。
