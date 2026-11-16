# NATIVE-SCENE-01 / A04 · Odoo View 类型与 View Set 盘点

状态：只读检查点，等待独立复核。

基线：`audit/native-scene-01-a01-a04-20261116@44cfed924b44b690dbb9f833ca9fcb605e8196cc`

## 1. 结论先行

当前源码与运行态证据同时存在，但口径不同：

- 当前仓库 manifest 装载范围内有 797 个 unique `ir.ui.view` XMLID。
- 其中 676 个基础 View、121 个继承 View。
- 基础 View 类型：tree 242、form 221、search 158、pivot 29、qweb 14、graph 9、kanban 3。
- 21 个继承 View 的父 View 位于 Odoo/OCA 外部模块，仓库静态扫描无法得到最终类型，
  但运行时由 `get_view()` 合并解析，不能判为缺失。
- 历史 clean Registry 快照有 2,113 个 View：form 703、tree 592、search 327、
  qweb 317、kanban 75、pivot 48、graph 30、activity 10、calendar 8、hierarchy 3。
- 当前正式产品 132 个入口中，128 个仓库内 Action 有明确 view mode；4 个为
  1 个 Scene Entry + 3 个外部 `account` Action。
- Pivot/Graph 已从“可读降级”演进为专用解析、V2 profile、前端专用页面，但统计口径仍不是
  Odoo `read_group` 全范围统计。
- Calendar/Gantt/Dashboard 仍在前端明确降级为 `core.readable_records`。
- Activity 有专用后端 profile 和前端页面，但当前正式产品没有 Activity Action/View；
  运行态存在的外部 Activity View 仍需逐入口验收。

## 2. 源码 View 清单

### 2.1 按类型

| 类型 | Unique View XMLID | 基础 View | 说明 |
|---|---:|---:|---|
| tree | 333 | 242 | Odoo 17 XML 仍使用 `<tree>`；前端语义名可为 list |
| form | 230 | 221 | 含业务表单和 Wizard 表单 |
| search | 158 | 158 | filters、group by、search panel |
| pivot | 29 | 29 | measure/dimension/interval/aggregate |
| qweb | 14 | 14 | 登录、Portal、品牌和邮件/模板布局 |
| graph | 9 | 9 | bar/line/pie 等原生 graph arch |
| kanban | 3 | 3 | 项目生命周期和驾驶舱卡片 |
| 继承类型待运行态解析 | 21 | 0 | 父 View 位于 `project/account/purchase/product/base/base_setup` |
| 合计 | 797 | 676 | 121 个继承 View |

机器可读 View 清单：
[`native_view_inventory.json`](inventories/native_view_inventory.json)。

静态扫描按 manifest 的 `data`/`demo` 范围执行；一个 View 被后续文件更新时按
unique XMLID 计一次。父 View 在本仓库不存在时只标“待运行态解析”，不标不存在。

### 2.2 需要运行态解析的父 View

21 个继承 View 的父身份中包含：

- `project.edit_project`
- `project.view_project`
- `project.view_project_kanban`
- `project.view_task_form2`
- `project.view_task_tree2`
- `purchase.purchase_order_form`
- `account.view_move_tree`
- `account.view_move_form`
- `base.view_partner_form`
- `base.view_users_form`
- `base.edit_menu_access`
- `base_setup.res_config_settings_view_form`
- `product.product_template_only_form_view`

代表：

- 项目表单扩展：
  [`project_views.xml:82`](../../../addons/smart_construction_core/views/core/project_views.xml#L82)。
- 任务表单扩展：
  [`task_sc_state_views.xml:2`](../../../addons/smart_construction_core/views/support/task_sc_state_views.xml#L2)。
- 采购单表单扩展：
  [`purchase_extend_views.xml:13`](../../../addons/smart_construction_core/views/core/purchase_extend_views.xml#L13)。
- 会计凭证明细扩展：
  [`account_extend_views.xml:3`](../../../addons/smart_construction_core/views/support/account_extend_views.xml#L3)。

`get_view()` 是唯一正确的最终合并入口，当前 parser 使用当前用户 env 调用：
[`contract_Parser.py:88`](../../../addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py#L88)。
因此 B03 必须比较“最终合并 XML”，不能只比较本仓库中新增的 inheritance record。

## 3. Action View Set

### 3.1 View 模式声明

源码 Action 中观察到的 `view_mode` token：

| Token | 声明次数 |
|---|---:|
| `form` | 391 |
| `tree` | 385 |
| `pivot` | 37 |
| `graph` | 17 |
| `kanban` | 5 |
| `calendar` | 0 |
| `gantt` | 0 |
| `activity` | 0 |
| `dashboard` | 0 |

这个结果是“本仓库定制 Action 的激活面”，不是 Odoo 全域视图支持表。Odoo Registry 中
外部模块仍可提供 activity/calendar 等 View；Gantt 是否需要企业版模块仍应运行态检查。

### 3.2 正式产品的 View Set 分布

正式菜单定义位于：
[`product_menu_source.json:95`](../../../addons/smart_construction_core/data/product_menu_source.json#L95)。

| View mode 组合 | 入口数 |
|---|---:|
| `tree,form` | 112 |
| `form` | 6 |
| `tree,form,pivot` | 3 |
| `tree,form,pivot,graph` | 3 |
| `kanban,tree,form` | 1 |
| `tree,kanban,form` | 1 |
| `pivot,graph,tree` | 1 |
| `pivot,graph,tree,form` | 1 |
| Scene Entry | 1 |
| 外部 Odoo Action，运行态解析 View Set | 3 |
| 合计 | 132 |

正式产品中：

- 8 个入口包含 Pivot。
- 5 个入口包含 Graph。
- 2 个入口包含 Kanban。
- 没有 Calendar/Gantt/Activity/Dashboard view mode。

这个分布说明“安装行业模块后自动交付全部专业视图”尚不成立；当前正式产品实际只激活了
少量 Pivot/Graph 和 Kanban 入口。

## 4. View 解析链

统一 parser 入口为 `app.view.parser`：
[`contract_Parser.py:37`](../../../addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py#L37)。

| View | 后端解析位置 | 前端位置 | A04 判断 |
|---|---|---|---|
| Tree | [`contract_Parser.py:135`](../../../addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py#L135) | `ActionView` ListPage / `core.standard_collection` | 已解析、已注册；B06 验列、排序、分页、分组、聚合和行操作 |
| Form | [`contract_Parser.py:141`](../../../addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py#L141) | Form contract / canonical form renderer | 已解析；B05 验布局、modifier、onchange、关系子视图和按钮 |
| Kanban | [`contract_Parser.py:156`](../../../addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py#L156) | KanbanPage / `core.standard_collection` | 已解析、已注册；B07 验卡片、分组和状态 |
| Search | [`contract_Parser.py:111`](../../../addons/smart_core/app_config_engine/services/view_Parser/contract_Parser.py#L111) | Action toolbar | 已解析；B04 验默认搜索、筛选、收藏、上下文 |
| Pivot | [`parsers Kanban Pivot Graph.py:127`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers%20Kanban%20Pivot%20Graph.py#L127) | AnalysisPage Pivot | 解析和专用 Renderer 已存在；统计口径不完整 |
| Graph | [`parsers Kanban Pivot Graph.py:158`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers%20Kanban%20Pivot%20Graph.py#L158) | AnalysisPage Graph | 解析和专用 Renderer 已存在；图表类型/多度量和 read_group 语义不完整 |
| Calendar | [`parsers_Calendar_Gantt Activity.py:36`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt%20Activity.py#L36) | `core.readable_records` | 有解析，无专用 Renderer |
| Gantt | [`parsers_Calendar_Gantt Activity.py:79`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt%20Activity.py#L79) | `core.readable_records` | 有解析，无专用 Renderer |
| Activity | [`parsers_Calendar_Gantt Activity.py:134`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt%20Activity.py#L134) | ActivityPage / `core.activity` | 解析和专用 Renderer 已存在；当前正式产品未激活 |
| Dashboard | `contract_Parser` 无独立 `_parse_dashboard` 分支；normalizer 仅规范 `cards/kpis` | `core.readable_records` | 没有统一原生 Dashboard 接管；行业 Dashboard 走已有自定义 Scene/Intent |
| Hierarchy | 原生 tree `js_class` 派生语义 | HierarchyBrowser/Planner/Worksheet | 不是独立 Odoo view type；自定义专业 Renderer 已注册 |

## 5. 专业视图状态

### 5.1 Pivot

事实：

- 后端保存 measure、dimension、axis、interval、aggregate：
  [`parsers Kanban Pivot Graph.py:127`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers%20Kanban%20Pivot%20Graph.py#L127)。
- V2 输出 `pivotProfile`：
  [`unified_page_contract_v2_assembler.py:1498`](../../../addons/smart_core/core/unified_page_contract_v2_assembler.py#L1498)。
- 前端注册 `core.pivot=ready`：
  [`actionSurfaceRendererRegistry.ts:40`](../../../frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts#L40)。
- 当前解析器把前端收到的 `records` 在浏览器内按 dimension 求和：
  [`actionViewAnalysisContract.ts:91`](../../../frontend/apps/web/src/app/contracts/actionViewAnalysisContract.ts#L91)。

缺口：

- 没有证明 Pivot 使用 Odoo `read_group` 的全范围统计。
- 当前 `ActionView` 传入的是 `records.value`：
  [`ActionView.vue:1173`](../../../frontend/apps/web/src/views/ActionView.vue#L1173)。
- 行/列双维、日期区间、展开折叠、下钻和全量聚合未在 A04 验证。

结论：`renderer_registered`，不是 `statistical_semantics_complete`。

### 5.2 Graph

事实：

- 后端提取 graph type、measure、dimension 和 interval：
  [`parsers Kanban Pivot Graph.py:158`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers%20Kanban%20Pivot%20Graph.py#L158)。
- 前端注册 `core.graph=ready`。
- AnalysisPage 当前只绘制第一条 measure 的横向条形：
  [`AnalysisPage.vue:56`](../../../frontend/apps/web/src/pages/AnalysisPage.vue#L56)。

缺口：

- Bar/Line/Pie、多 measure、多 dimension、全范围聚合、图表/数据联动和下钻未完整验收。
- 与 Pivot 相同，当前数据来自页内 records，而不是后端 `read_group`。

### 5.3 Calendar/Gantt

事实：

- 后端 parser 已提取 calendar 起止日期、颜色、scale、quick-add、字段：
  [`parsers_Calendar_Gantt Activity.py:36`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt%20Activity.py#L36)。
- Gantt parser 已提取起止日期、progress、resource/dependency/scale/decoration：
  [`parsers_Calendar_Gantt Activity.py:79`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt%20Activity.py#L79)。
- 前端 registry 明确为 fallback，reason code 为 `RENDERER_CALENDAR_PLANNED` /
  `RENDERER_GANTT_PLANNED`：
  [`actionSurfaceRendererRegistry.ts:42`](../../../frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts#L42)。

源码内没有 Calendar/Gantt View 或激活它们的 Action。运行态历史快照有 8 个 Calendar View，
没有 Gantt。当前结论只能是“有解析契约、无专业交付”。

### 5.4 Activity

事实：

- Activity parser 保留 QWeb template、field/node occurrence、actions、deadline/assignee/type slots：
  [`parsers_Calendar_Gantt Activity.py:134`](../../../addons/smart_core/app_config_engine/services/view_Parser/parsers_Calendar_Gantt%20Activity.py#L134)。
- V2 输出 `activityProfile`：
  [`unified_page_contract_v2_assembler.py:1477`](../../../addons/smart_core/core/unified_page_contract_v2_assembler.py#L1477)。
- 前端 decoder 和 ActivityPage 存在：
  [`actionViewActivityContract.ts:116`](../../../frontend/apps/web/src/app/contracts/actionViewActivityContract.ts#L116)。
- 前端注册 `core.activity=ready`。

边界：

- 当前仓库没有带 `view_mode=activity` 的正式产品 Action。
- 历史 Registry 有 10 个 Activity View，但不能证明它们已进入正式产品。
- A04 只确认构造链；C05 需要验证 action/template/激活入口和活动操作。

### 5.5 Dashboard

事实：

- 统一 UI contract 接受 `dashboard` 名称：
  [`ui_contract.py:30`](../../../addons/smart_core/handlers/ui_contract.py#L30)。
- 旧 normalizer 只对 `cards/kpis` 做通用结构兜底：
  [`normalizer.py:365`](../../../addons/smart_core/app_config_engine/services/normalizer.py#L365)。
- `contract_Parser` 没有 dashboard 专用解析分支。
- 前端 registry 把 dashboard 映射为 `core.readable_records`：
  [`actionSurfaceRendererRegistry.ts:45`](../../../frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts#L45)。
- 行业项目/公司驾驶舱已有自定义 Intent、Block 和场景服务，属于另一条组合链，不是
  Odoo 原生 View 直接接管。

源码中名为“项目驾驶舱/公司驾驶舱”的入口，实际是 Kanban 或投影模型 Action。
例如项目驾驶舱 `view_mode=kanban,tree,form`：
[`project_dashboard_kanban.xml:430`](../../../addons/smart_construction_core/views/projection/project_dashboard_kanban.xml#L430)。
不能因为名称含“驾驶舱”就判定它使用了 Odoo dashboard view type。

### 5.6 Hierarchy 与专业树

Hierarchy 不是新的 Odoo 原生 view type，而是原生 tree 上的 `js_class` 语义：

[`native_collection_presentation.py:4`](../../../addons/smart_core/utils/native_collection_presentation.py#L4)。

当前源码有 11 个专业 tree 实例：

- `smart_hierarchy_browser` 4
- `smart_hierarchical_worksheet` 5
- `smart_hierarchy_planner` 2

代表：

- WBS：
  [`execution_structure_views.xml:8`](../../../addons/smart_construction_core/views/core/execution_structure_views.xml#L8)。
- BOQ 层级：
  [`boq_views.xml:143`](../../../addons/smart_construction_core/views/core/boq_views.xml#L143)。
- 成本计划规划器：
  [`cost_plan_views.xml:172`](../../../addons/smart_construction_core/views/core/cost_plan_views.xml#L172)。

前端三个语义均为 `ready`：
[`actionSurfaceRendererRegistry.ts:37`](../../../frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts#L37)。
但预算递归汇总、服务端重算、大数据分页和行内编辑仍属于 D02/F06。

## 6. 原生 Widget、QWeb 与布局事实

当前源码 View 中出现 18 类、349 次 widget 声明：

| Widget | 次数 |
|---|---:|
| `statusbar` | 93 |
| `many2many_binary` | 83 |
| `handle` | 43 |
| `many2many_tags` | 33 |
| `badge` | 30 |
| `json` | 29 |
| `statinfo` | 13 |
| `percentage` | 12 |
| `res_partner_many2one` | 2 |
| `daterange` | 2 |
| `domain` | 2 |
| `radio` / `one2many_list` / `image` / `boolean_toggle` / `html` / `many2one_avatar_user` / `tier_validation` | 各 1 |

QWeb View 共 14 个，主要用于登录、注册、Portal、语言切换和品牌布局。
A04 不把这些模板当作通用业务视图 Renderer；它们是否需要接管由 C07/D 场景决定。

## 7. 验证状态

本轮执行并通过：

```text
make verify.frontend.view_type_render_coverage.guard
make verify.frontend.view_type_contract_semantic.guard
make verify.native_view.workflow_action_coverage
```

`view_type_render_coverage.guard` 的 9 个测试通过，并明确输出：

- Pivot/Graph → governed profile resolver → AnalysisPage
- Calendar/Gantt/Dashboard → `core.readable_records`
- Activity → decoder → store → resolver → ActivityPage
- `action_route=false`、`browser_delivery=false`

这证明的是当前代码可执行架构，不是真实 Action Route 或浏览器交付。

## 8. 支持矩阵

| 能力 | 原生事实 | 后端解析 | 前端注册 | 当前终态 |
|---|---|---|---|---|
| Form | 强 | 有 | 有 | 已接入，完整语义待 B05 |
| Tree/List | 强 | 有 | 有 | 已接入，完整语义待 B06 |
| Search | 强 | 有 | 有 | 已接入，待 B04 |
| Kanban | 强 | 有 | 有 | 已接入，待 B07 |
| Pivot | 强 | 有 | `core.pivot` | 专用 Renderer 已注册；全范围统计待补 |
| Graph | 强 | 有 | `core.graph` | 专用 Renderer 已注册；图表语义待补 |
| Calendar | 运行态有 | 有 | fallback | 专业 Renderer 缺失 |
| Gantt | 运行态未证 | 有 | fallback | 专业 Renderer 缺失 |
| Activity | 运行态有 | 有 | `core.activity` | 专用链存在；产品入口/L4 未证 |
| Dashboard | 外部/行业多条来源 | 无统一原生解析 | fallback | 统一接管缺失 |
| Hierarchy | tree `js_class` | 有 | 三个 ready | 专业树已接入；业务约束待 D02/D03 |
| Report | Action 层 | 有 | 无 | 不是 View 接管，归 C07 |

## 9. A04 判定

- Odoo 原生 Form/Tree/Search/Kanban/Pivot/Graph 的 View 事实已大范围进入源码与契约链。
- Pivot/Graph 的“已注册”不能等同于“统计口径已正确”；当前最明显缺口是前端仅对页内记录聚合。
- Calendar/Gantt 没有专业 Renderer；Dashboard 没有统一原生 View 接管。
- Activity 专用链存在，但正式产品没有激活入口，因此不能以注册表 ready 代替 C05 验收。
- View inheritance 最终合并、Action 的全部 view mode、权限裁剪和真实角色交互必须进入 B02/B03。
