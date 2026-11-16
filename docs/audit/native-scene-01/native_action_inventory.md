# NATIVE-SCENE-01 / A03 · Odoo Action 类型与接管盘点

状态：只读检查点，等待独立复核。

基线：`audit/native-scene-01-a01-a04-20261116@44cfed924b44b690dbb9f833ca9fcb605e8196cc`

## 1. 结论先行

当前仓库不是只有 Window Action：

- 源码中 unique XML Action XMLID 为 530 个：
  `ir.actions.act_window=427`、`ir.actions.server=101`、`ir.actions.client=2`。
- 另有 18 个 `ir.actions.act_window.view` 明确视图绑定声明。
- Python 中还有 96 个动态返回 Action 字典，没有稳定 XMLID：
  Window 76、Client 16、`act_window_close` 3、URL 1。
- Odoo Registry 历史只读快照中有 744 个 Window、173 个 Server、9 个 Client、
  3 个 URL、40 个 Report 和 969 个 `act_window_close`。
- 当前正式产品定义为 132 个入口，其中 131 个绑定 Action，1 个是 Scene Entry；
  92 个 `released`，40 个 `preview`。

因此，“Action 全量”必须同时覆盖：

1. 模块 XML 声明的持久 Action；
2. Python 运行时返回的上下文 Action；
3. 菜单直接引用；
4. Form/Kanban 按钮、Wizard 返回值和业务方法返回值；
5. Odoo/OCA 外部模块在 Registry 中存在但本仓库没有源码的 Action。

## 2. Action 源码盘点

### 2.1 唯一身份与模块归属

| 模块 | Unique XMLID（Action + View Binding） | Window | Server | Client | `act_window.view` |
|---|---:|---:|---:|---:|---:|
| `smart_construction_core` | 521 | 400 | 101 | 2 | 18 |
| `smart_core` | 13 | 13 | 0 | 0 | 0 |
| `sc_norm_engine` | 7 | 7 | 0 | 0 | 0 |
| `smart_construction_scene` | 3 | 3 | 0 | 0 | 0 |
| `smart_construction_demo` | 2 | 2 | 0 | 0 | 0 |
| `base_tier_validation` | 2 | 2 | 0 | 0 | 0 |

同一 XMLID 可能被多个 XML 文件后续更新，例如安全组补丁、导航重排和正式产品版面投影。
上表按 unique XMLID 统计，不把后续更新误算为多个 Action。

### 2.2 Python 动态 Action

| 类型 | 动态返回点 | 稳定身份判断 |
|---|---:|---|
| `ir.actions.act_window` | 76 | 无 XMLID；必须由调用模型/方法和 context 共同标识 |
| `ir.actions.client` | 16 | 无 XMLID；tag 和调用来源必须一起登记 |
| `ir.actions.act_window_close` | 3 | 关闭语义，不是页面入口 |
| `ir.actions.act_url` | 1 | 无 XMLID；URL 和来源方法共同决定行为 |

代表源码：

- Wizard 返回 Window Action：
  [`funding_authority_wizard.py:49`](../../../addons/smart_construction_core/wizard/funding_authority_wizard.py#L49)。
- 项目快速创建返回 URL Action：
  [`project_quick_create_wizard.py:35`](../../../addons/smart_construction_core/wizard/project_quick_create_wizard.py#L35)。
- Wizard 返回 Client Action：
  [`quota_import_wizard.py:285`](../../../addons/smart_construction_core/wizard/quota_import_wizard.py#L285)。
- 业务模型返回 Client Action：
  [`project_core.py:95`](../../../addons/smart_construction_core/models/core/project_core.py#L95)。

这些动态 Action 不能仅靠 XMLID 管理。A08 和 B01 需要把
`(source_model, source_method, action_type, target)` 纳入调用链身份。

## 3. Odoo Registry Action 事实

只读 Registry 快照
[`navigation_capability_inventory_v1.json:3`](../../../artifacts/backend/navigation_capability_inventory_v1.json#L3)
身份为 `sc_dev_demo@cb769bd0e7004ab8cff9b3d533ce02987d923f35`，生成于
`2026-11-11T07:15:34Z`。Action 总量：

| Action 类型 | Registry 记录数 |
|---|---:|
| `ir.actions.act_window` | 744 |
| `ir.actions.server` | 173 |
| `ir.actions.client` | 9 |
| `ir.actions.act_url` | 3 |
| `ir.actions.report` | 40 |
| `ir.actions.act_window_close` | 969 |

数据位置：
[`navigation_capability_inventory_v1.json:274`](../../../artifacts/backend/navigation_capability_inventory_v1.json#L274)。
该快照同时记录 520 个 Action 被至少一个菜单引用，555 次菜单引用，31 个 Action 被多个菜单
复用，未解析菜单 Action 引用为 0：
[`navigation_capability_inventory_v1.json:283`](../../../artifacts/backend/navigation_capability_inventory_v1.json#L283)。

重要边界：

- “菜单未引用”不等于“没有业务能力”。Context Action、Wizard、按钮、报表、嵌入 Action
  和 `act_window_close` 本来就可能没有菜单。
- 菜单存在也不等于完整业务能力。权限、View Set、业务方法和事务仍要验证。
- Action XMLID 不是唯一场景身份。当前对账已证明 16 个 Action XMLID 被多个菜单复用，
  覆盖 34 个入口，必须使用 `(menu_xmlid, action_xmlid)` 复合键：
  [`historical_reconciliation_20261115.md:75`](../capability-explorer-05/historical_reconciliation_20261115.md#L75)。

## 4. Action 类型执行与当前接管

| 类型 | Odoo 语义 | 后端当前证据 | 前端当前证据 | 状态 |
|---|---|---|---|---|
| Window | 打开模型 View Set，携带 model/domain/context/view mode | [`action_dispatcher.py:97`](../../../addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py#L97) 进入 PageAssembler | `ActionView` 根据 contract/action view modes 加载 List/Form/Kanban/高级视图 | `implemented_partial`：普通窗口链存在，完整 View Set 语义待 B01-B12 |
| Server | 执行服务端代码或返回后续 Action | 契约读取不执行任意代码；无受管映射时诊断：[`action_dispatcher.py:112`](../../../addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py#L112) | 用户点击按钮时由 `execute_button` 执行：[`execute_button.py:512`](../../../addons/smart_core/handlers/execute_button.py#L512) | `implemented_for_button`；菜单级通用执行和回执链待 B12 |
| Client | 通过 tag 交给客户端组件 | 输出 tag 契约：[`client_url_report.py:25`](../../../addons/smart_core/app_config_engine/services/assemblers/client_url_report.py#L25) | 自定义 SPA 没有通用 Odoo client tag 注册表；无 model 时进入 `ACT_NO_MODEL` 工作台诊断：[`actionViewLoadGuardRuntime.ts:52`](../../../frontend/apps/web/src/app/runtime/actionViewLoadGuardRuntime.ts#L52) | `declared_only`：后端契约存在，通用 tag Renderer 未接管 |
| URL | 按 `url/target` 跳转 | URL 契约：[`client_url_report.py:49`](../../../addons/smart_core/app_config_engine/services/assemblers/client_url_report.py#L49) | 自定义 SPA 解析并执行 self/new 跳转：[`useActionViewActionMetaRuntime.ts:49`](../../../frontend/apps/web/src/app/action_runtime/useActionViewActionMetaRuntime.ts#L49) | `implemented`；空 URL 有明确诊断 |
| Report | 调用 `ir.actions.report` 生成 PDF/HTML | 报表契约适配：[`client_url_report.py:72`](../../../addons/smart_core/app_config_engine/services/assemblers/client_url_report.py#L72)；`app.report.config` 扫描 Registry | `frontend/apps/web/src` 未发现 `report_name/report_type` 消费点 | `backend_only`：原生报表引擎未被自定义前端接管 |
| `act_window_close` | 关闭当前窗口/Dialog | Python 动态结果可见 | 未发现通用关闭结果消费点 | `not_integrated` |

`backend_only` 与 `declared_only` 都是明确缺口；不能用“后端有契约”或“前端不报错”代替交付。

### 4.1 Window Action 的 View Set 身份

Odoo 的 Window Action 可以同时声明：

- `res_model`
- `view_mode`
- `view_id`
- `search_view_id`
- `views`
- `view_ids`
- `domain`
- `context`
- `groups_id`

当前产品定义中，必须把 Action 的完整 View Set 消费，而不是只取第一个默认 List。
源码存在以下不同形态：

- 只声明 `view_mode`，由 Odoo 按模型默认视图解析。
- `view_id` 指定默认视图。
- `views/view_ids` 显式绑定多个 View。
- `ir.actions.act_window.view` 作为持久子记录绑定。

样板 `payment.request` 同时包含 `view_id`、`views`、`view_ids` 和 `search_view_id`：
[`menu_business_taxonomy.xml:442`](../../../addons/smart_construction_core/views/menu_business_taxonomy.xml#L442)。
`project.project` 台账则通过 `view_mode=tree,kanban,form` 和 context 控制创建入口：
[`project_list_actions.xml:3`](../../../addons/smart_construction_core/actions/project_list_actions.xml#L3)。

## 5. 当前正式产品的 Action 覆盖

正式菜单源：
[`product_menu_source.json:95`](../../../addons/smart_construction_core/data/product_menu_source.json#L95)；
发布策略：
[`formal_business_product_menu_policy_v1.json:20`](../../../addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json#L20)。

| 事实 | 数量 |
|---|---:|
| 正式入口 | 132 |
| Action 入口 | 131 |
| Scene Entry | 1 |
| `released` | 92 |
| `preview` | 40 |
| 仓库内已知 View Set 的 Action 入口 | 128 |
| 外部 `account` Action，View Set 需运行态解析 | 3 |

外部 `account` Action 只调整正式产品中的导航位置和名称，Action、Model、权限仍由 Odoo
模块提供，声明理由见：
[`product_menu_source.json:501`](../../../addons/smart_construction_core/data/product_menu_source.json#L501)
至 `:543`。

该边界是正确的：行业模块可以发布原生 Action 的产品位置，不能复制原生 Action 的业务事实。

## 6. 业务执行入口

除 Window Action 菜单外，XML 内还有大量按钮：

| 按钮形态 | 出现次数 | Unique 名称/引用 | 含义 |
|---|---:|---:|---|
| `type="object"` | 612 | 208 | 调用模型业务方法 |
| `type="action"` | 24 | 23 | 直接返回/打开另一个 Action |
| 其他/空 type | 19 | - | 技术或非标准按钮，需 B08 逐项确认 |
| `type="server"` | 0 | 0 | 当前源码未直接声明；不表示 Odoo 无 Server Action |

高频对象方法是审批和状态推进，不是简单 CRUD：

- `action_cancel` 62 次
- `validate_tier` 54 次
- `reject_tier` 54 次
- `action_submit` 49 次
- `action_reset_draft` 41 次
- `action_confirm` 31 次

这说明 B08/B12 的核心不是“按钮能否点击”，而是原生按钮身份、状态可见性、组权限、
后端方法执行、失败原因和事务结果是否一致。

## 7. 接管状态分类

| 状态 | Action 范围 | 说明 |
|---|---|---|
| `implemented` | URL Action | 后端契约和前端重定向链均存在 |
| `implemented_partial` | Window Action + tree/form/kanban/pivot/graph | View 类型分支存在；完整 View Set、Wizard、权限和业务事务未全验收 |
| `implemented_for_button` | 被按钮调用的 Server/Object Action | `execute_button` 是执行边界；菜单级 Server Action 未通用执行 |
| `backend_only` | Report | 后端投影存在，无前端消费 |
| `declared_only` | Client Action | 后端 tag 契约存在，无通用客户端组件注册表 |
| `not_integrated` | `act_window_close` | 未发现通用结果消费 |
| `external_runtime_resolved` | 3 个 `account` Action | 源码不在本仓库，必须运行态验证 |
| `not_verified` | 132 个正式入口的逐入口权限/状态/事务 | B 阶段范围，不能由 A03 代替 |

## 8. A03 判定

- 已具备覆盖 Window、Server、Client、URL、Report、Close 的源码识别与后端入口。
- 当前自定义前端真正闭环最好的是 URL 和基础 Window 页面。
- Server Action 的业务执行依赖按钮边界，不能把“导航时未执行代码”误判为不支持。
- Client 与 Report 是明确未接入类型；Dashboard 类 Client Action 也不能因存在 tag 就判定已接管。
- 正式产品的 131 个 Action 入口只是“有稳定原生身份”，不是“逐入口完整交付”。
