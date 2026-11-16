# NATIVE-SCENE-01 / B-S2 · Native Action Contract 与 Occurrence 设计

Status: source design complete; implementation and runtime consumption not included.

Date: 2026-11-16

Baseline: `89ce5325085c89513c83773787ff353e0ba2f5ce`

Prerequisite research:

- NATIVE-SCENE-01 / A01-A04 capability inventory.
- NATIVE-SCENE-01 / B-S1 semantic conversion audit.

## 1. 检查点边界

本检查点属于 P4 只读契约设计，研究三个问题：

1. Action View Set 如何成为原生业务场景的一等身份。
2. Action-bound Search View 如何保持身份和权威优先级。
3. Form/List 的字段、按钮、容器 occurrence 如何获得稳定身份和明确语义出口。

本轮不做：

- 不修改产品源码、数据库、配置或业务数据。
- 不新增 Odoo 模型、场景模型或持久化契约表。
- 不修改 Unified Page Contract V2 schema。
- 不修改 Renderer、组件、路由或前端消费逻辑。
- 不执行浏览器、角色、权限或业务方法运行态验收。
- 不实施本设计。

L1/L2 状态：

- L1 原生 Action/View/Search/字段事实：源码级已验证。
- L2 现有后端转换和前端既有消费入口：源码级已验证。
- L3 对新 Native Action Contract 的真实前端消费：未实现、未验证。
- L4 真实业务闭环：未验证。

## 2. 技术裁定

建议采用以下交付单元：

```text
Native Action Contract
        +
Active Unified Page Contract V2
```

其中：

- `Native Action Contract` 是 Action 级身份和控制面，回答“这是什么原生场景、有哪些视图、
  当前使用哪个视图、Search 来自哪里”。
- `Unified Page Contract V2` 继续表达当前活动视图的完整页面数据面，包括布局、状态、
  Action Rule、数据和运行策略。
- View Set 不复制所有页面的完整布局。切换视图时继续调用现有
  `ui.contract.v2`，以同一个 Action 身份加载目标 View 的页面契约。

这不是新建业务系统，也不是替代 V2。它只补足 V2 当前缺少的 Action 级上层身份。

## 3. 为什么当前缺口成立

### 3.1 PageAssembler 已经具备多视图装配能力

- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:389-394`
  确定装配的 view types。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:511-625`
  逐视图获取原生 View，生成 `views.<type>`、`view_ids_by_type` 和字段需求。
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:2157-2205`
  用 Action 的 `views`/`view_mode` 补齐后端装配的视图族。
- `addons/smart_core/app_config_engine/models/app_view_config.py:110-187`
  对每个 view type 按 Action-bound View ID 解析 source view。

这说明后端不是“不会装多个视图”，而是没有把结果提升成一等 Action View Set。

### 3.2 V2 只交付一个活动页面

- `addons/smart_core/core/unified_page_contract_v2_assembler.py:1219-1252`
  从请求 view type 生成一个 `pageInfo` 和一个 `layoutType`。
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:369-451`
  根契约没有 Action View Set 节点。
- `addons/smart_core/handlers/ui_contract_v2.py:1671-1743`
  后续 Action 注入只补 title、model、Domain、Context，未补 ordered views。
- `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json:5-109`
  根对象闭合，当前没有 Action View Set 声明。

### 3.3 Action Resolver 丢失搜索和视图绑定字段

- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:98-144`
  标准化 Action 时只保留 `res_model`、`view_mode`、Domain、Context 等，不保留
  `views`、`view_ids`、`search_view_id`。
- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:180-205`
  第二套 normalize 同样没有这些字段。

PageAssembler 后续通过 Action ID 再次读取数据库补回部分视图绑定，但 Search 没有同样恢复。

## 4. 可复用的现有机制

| 机制 | 当前职责 | B-S2 复用方式 |
| --- | --- | --- |
| `ActionResolver` | XMLID/ID/menu 解析、Action 类型分流 | 扩展为完整 Action identity 解析，不另建 resolver |
| `PageAssembler` | 多视图、字段、Search、权限、按钮、数据源聚合 | 提取 Action View Set，不重写 View 转换 |
| `app.view.config._projection_identity()` | Action-bound View ID 精确解析 | 作为 view entry identity 与默认 fallback 规则 |
| `get_view()` | 继承合并、当前用户裁剪 | 保持唯一原生 View 组合权威 |
| `app.view.parser` | 各 View Profile 解析 | 继续作为当前 View 解析适配器 |
| Canonical Native View AST | Form 容器与 occurrence 内核 | 作为 Form occurrence 和未来 Profile 收敛基础 |
| `app.search.config` | Search profile 生成 | 增加 Action Search View 身份输入，不重建搜索器 |
| UCP V2 | 当前活动视图页面契约 | 保持完整页面数据面 |
| `actionContract.nativeIdentity` | 原生按钮身份 | 复用为按钮 occurrence 的既有承载 |
| `listProfile` | 列表展示和列策略 | 承载 List column occurrences 扩展 |
| `sourceAuthority` | 投影来源声明 | 承载 Action/Search/occurrence provenance |
| `ActionView` view mode runtime | 模式选择、路由持久化、重新加载 | 后续改为消费 Action Contract，不重写 Renderer |
| Action Surface Renderer Registry | 专业视图 renderer 状态和原因码 | 保留终端能力状态，不把 fallback 伪装成 native |

## 5. Native Action Contract 放置位置

### 5.1 不应复用的现有节点

| 候选 | 不适用原因 |
| --- | --- |
| `pageInfo` | 只描述一个页面身份；不能承载 ordered View Set |
| `actionContract` | 已定义为页内事件/按钮执行规则，不是 Action 路由身份 |
| `runtimeContract` | 运行机制、缓存、补丁和交互策略，不是业务入口身份 |
| `meta` | 传输、生命周期和完整性证据，不是产品语义 |
| `pageComposition` | 只负责页面结构分类和诊断 |
| `searchContract` | 只表达当前 Search Profile，不能单独证明 Action 的搜索身份 |

### 5.2 推荐增加受控可选根节点

后续实现建议增加：

```text
nativeActionContract
```

理由：

- 它是同一 Action 的稳定上层身份。
- 它需要与活动 View 的页面契约同次交付，前端才能验证一致性。
- 它不属于某个页面的布局、状态或页内动作。
- 它是可重建的投影，不需要新模型或持久化表。

当前 schema 根对象和前端 decoder 都是闭合的：

- `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json:5-109`
- `frontend/apps/web/src/app/contracts/v2/schema.ts:2680-2688`
- `scripts/verify/unified_page_contract_v2_schema_guard.py:19-36`

因此后续实施不能直接把未知字段塞入响应，必须同时完成：

1. schema 增加受控 optional top-level field；
2. schema guard 白名单；
3. TS 类型和 decoder；
4. client capability；
5. contract version/capability negotiation；
6. 契约 fixture 与 snapshot。

建议版本策略：

- 当前 B-S2 不修改版本。
- 实施时若旧客户端会拒绝未知根字段，必须升级契约版本并同步客户端 decoder。
- 建议新增能力标识 `action_view_set.v1`、`search_identity.v1`、`occurrence_identity.v1`。
- 旧客户端可继续消费单页 V2，但不得宣称已获得完整 Native Action 场景。

## 6. Native Action Contract 建议结构

```json
{
  "nativeActionContract": {
    "schemaVersion": "1.0.0",
    "identity": {
      "actionType": "ir.actions.act_window",
      "actionId": 123,
      "actionXmlId": "module.action_xmlid",
      "model": "payment.request"
    },
    "routeRef": {
      "menuId": 456,
      "menuXmlId": "module.menu_xmlid",
      "sceneKey": "finance.payment_requests"
    },
    "actionScope": {
      "domainRaw": "[('business_category_id.code', '=', '...')]",
      "domain": [],
      "contextRaw": "{'default_type': 'pay'}",
      "context": {},
      "sourceAuthority": {
        "kind": "ir.actions.act_window"
      }
    },
    "authorization": {
      "allowed": true,
      "reasonCode": "",
      "authority": "existing_route_or_action_policy"
    },
    "search": {
      "viewId": 234,
      "viewXmlId": "module.view_search_xmlid",
      "authority": "action_search_view",
      "profileRef": "searchContract"
    },
    "viewSet": {
      "defaultViewType": "tree",
      "activeViewType": "tree",
      "orderedViews": [
        {
          "viewType": "tree",
          "viewId": 345,
          "viewXmlId": "module.view_tree_xmlid",
          "sequence": 10,
          "surfaceRole": "collection",
          "selectable": true,
          "nativeAvailable": true,
          "rendererStatus": "ready",
          "reasonCode": "",
          "profile": "list"
        },
        {
          "viewType": "form",
          "viewId": 346,
          "viewXmlId": "module.view_form_xmlid",
          "sequence": 20,
          "surfaceRole": "record_detail",
          "selectable": false,
          "nativeAvailable": true,
          "rendererStatus": "ready",
          "reasonCode": "",
          "profile": "form"
        }
      ]
    },
    "automaticTakeover": {
      "eligible": true,
      "reasonCodes": []
    },
    "sourceAuthority": {
      "kind": "native_action_contract_projection",
      "projectionOnly": true,
      "noBusinessFactAuthority": true
    }
  }
}
```

### 6.1 字段含义

| 字段 | 必要性与约束 |
| --- | --- |
| `actionType` | B-S2 v1 只完整定义 `ir.actions.act_window` |
| `actionId/actionXmlId` | 同一 Action 切换视图时保持不变 |
| `model` | 必须与 `pageInfo.model` 和每个 View 的模型一致 |
| `routeRef` | 可选；菜单不是 Action 本体，不能反向改写 Action |
| `actionScope` | 发布 Action 自身的 Domain/Context；页面 dataSource 继续承载当前请求有效参数 |
| `authorization` | 只引用现有路由/发布/权限决定，不新增前端 group evaluator |
| `search` | 表达 Action-bound Search View 身份，有效 Search Profile 仍在顶层 |
| `viewSet` | 有序视图、默认视图、活动视图和每个视图状态 |
| `automaticTakeover` | 聚合 provenance；含兼容默认或 unresolved 时不得为 eligible |

### 6.2 `surfaceRole`

原生 `view_mode` 中的 View 并非都用于工具栏切换：

- `tree/kanban/pivot/graph/calendar/gantt/activity/dashboard` 通常是集合视图。
- `form` 通常是记录详情，不应出现在集合模式选择器中。
- Search View 独立于 `view_mode`，不属于 `orderedViews`。

建议枚举：

```text
collection
record_detail
```

`selectable` 必须由后端明确发布，前端不得仅按 view type 猜测。

### 6.3 `rendererStatus`

现有 Registry 已定义：

- `ready`
- `fallback`
- `unsupported`

源码：

- `frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts:3-15`
- `frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts:33-45`
- `frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts:52-105`

建议区分：

- `nativeAvailable`：后端能否解析、授权并形成该视图契约。
- `rendererStatus`：当前终端是否存在正式、fallback 或 unsupported 实现。

两者不能合成一个 `enabled`：

- 原生视图存在但 Renderer 未实现：`nativeAvailable=true`、`rendererStatus=unsupported`。
- 原生视图无权或不存在：`nativeAvailable=false`、稳定 `reasonCode`。
- 兼容默认：不得标为 `native_explicit`。

## 7. Action View Set 投影规则

### 7.1 View 顺序

建议 canonical order：

1. 以 `action.view_mode` 的声明顺序为主。
2. 以 `action.views` / `ir.actions.act_window.view.sequence` 绑定 view ID。
3. `view_mode` 中缺失显式 View ID 的项保留位置，并记录解析来源。
4. 配置新增的 Profile 只能以显式 `origin=business_config` 追加，不能悄悄插到原生顺序前面。
5. `list` 统一归一为 `tree`，保留原 spelling 仅用于诊断。

源码基础：

- `addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py:97-106`
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:259-267`
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:2157-2205`
- `addons/smart_core/app_config_engine/models/app_view_config.py:148-172`

不能使用 dict 遍历顺序代替原生 View 顺序。

### 7.2 View ID 解析优先级

每个 view entry：

1. 请求显式 `view_id`：只能用于匹配 view type。
2. Action `views` 中同 view type 的绑定 ID。
3. Action `view_id`，且其类型与当前 view type 一致。
4. `model.get_view(view_type=...)` 的模型默认解析 ID。

这与 `_projection_identity()` 当前规则一致，应被提升为共享纯投影函数。

Provenance：

- 1-3：`native_explicit`
- 4：`model_metadata_derived`
- 解析失败：`unresolved`

### 7.3 默认视图

定义两个不同身份：

- `nativeDefault`：Action 原生 `view_mode` 的第一项及对应 View。
- `active`：当前请求实际打开的 View。

当路由明确请求 `view_mode=kanban`：

- `nativeDefault=tree`
- `active=kanban`

不能用 active 覆盖 default，否则切换和面包屑会丢失原生入口默认身份。

记录打开时：

- 行点击显式请求 `form`。
- `active=form`，但 `nativeDefault` 仍可保持 `tree`。

### 7.4 切换视图

当前前端已有可复用切换框架：

- `frontend/apps/web/src/app/contracts/v2/client.ts:94-114`
  已支持以 Action、View Type、View ID、Menu、Context 请求新页面。
- `frontend/apps/web/src/app/contracts/actionViewSurfaceContract.ts:152-180`
  已实现 available modes 和 renderable mode 解析。
- `frontend/apps/web/src/app/runtime/actionViewContractLoadRuntime.ts:7-29`
  已实现 route/current/available 优先级。
- `frontend/apps/web/src/app/action_runtime/useActionViewModeRuntime.ts:33-41`
  切换模式后重新加载。
- `frontend/apps/web/src/app/runtime/collectionViewRuntime.ts:3-15`
  切换只更新 `view_mode`，保留现有 Action/Menu/Context route 参数。

后续实现只需让这些现有入口读取 `nativeActionContract.viewSet`，不重写 Renderer：

```text
select target view
-> validate target in orderedViews and selectable
-> request ui.contract.v2 with
       same action_id
       same menu_id/context
       target_view_type
       exact target_view_id
-> validate returned active view identity
```

### 7.5 共享 Domain、Context 和权限

切换时不重新拼业务入口：

- Action ID 保持不变。
- Menu/route context 保持不变。
- Action Domain/Context 由服务端每次重新投影。
- Record Rules、ACL、字段 rights 由新页面契约重新计算。
- 不将上一页面的 `actionRuleList` 或 `statusContract` 当作下一视图权限。

Action Contract 中保存 Action 源 Domain/Context；页面契约继续保存当前请求的有效
DataSource 参数。两者不能互相冒充：

- `nativeActionContract.actionScope`：Action 声明。
- `dataContract.dataSource.primary`：当前页面执行参数。

### 7.6 不支持原因

每个 view entry 至少区分：

| 原因 | 含义 |
| --- | --- |
| `ACTION_VIEW_NOT_BOUND` | Action 声明了类型但没有可解析 View |
| `ACTION_VIEW_ACCESS_DENIED` | 当前用户无权形成该 View |
| `ACTION_VIEW_PARSE_FAILED` | 原生 View 无法形成有效 Profile |
| `ACTION_VIEW_PROFILE_UNRESOLVED` | 后端没有对应语义 profile |
| `ACTION_VIEW_RENDERER_UNSUPPORTED` | 当前终端 Renderer 不支持 |
| `ACTION_VIEW_RENDERER_FALLBACK` | 使用已登记 fallback renderer |

不能把不支持视图从 View Set 静默删除；否则菜单存在但视图消失，无法解释。

## 8. Search View 身份设计

### 8.1 当前事实链

Action 明确声明：

- `payment.request`：
  `addons/smart_construction_core/views/core/payment_request_views.xml:440-477`
- `project.project`：
  `addons/smart_construction_core/actions/project_native_action_overrides.xml:8-28`

当前丢失点：

- `ActionResolver.as_action_info()` 不发布 `search_view_id`。
- `PageAssembler` 只在 Search 作为普通 view type 装入时才传 `search_view_data`。
- `app.search.config` 无显式数据时读取 `Model.get_view(view_type='search')`。

源码：

- `addons/smart_core/app_config_engine/services/resolvers/action_resolver.py:133-142`
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:627-653`
- `addons/smart_core/app_config_engine/models/app_search_config.py:58-74`
- `addons/smart_core/app_config_engine/models/app_search_config.py:419-444`

### 8.2 权威优先级

建议固定为：

1. 请求中的受权显式 Search View 覆盖，仅用于已登记预览/配置场景。
2. Action `search_view_id`。
3. Action 其它显式 search 绑定，如未来 `views` 明确包含 search。
4. 当前模型原生默认 search view。
5. 无法解析：`unresolved`。

正式自动接管中：

- 1-3：`native_explicit`
- 4：`model_metadata_derived`
- 无显式绑定不代表错误，但必须标记来源。
- Action 显式绑定存在却解析失败，必须 fail closed，不能退回模型默认 Search View。

### 8.3 Search Contract 增量

建议在现有 `searchContract` 内增加：

```json
{
  "nativeIdentity": {
    "model": "payment.request",
    "actionId": 123,
    "viewId": 234,
    "viewXmlId": "module.view_payment_search",
    "authority": "action_search_view",
    "sourceLocator": "ir.actions.act_window.search_view_id"
  }
}
```

现有 filters、group_by、fields、panel、favorites、defaults 保持不变。

### 8.4 跨契约一致性

必须验证：

- `nativeActionContract.search.viewId == searchContract.nativeIdentity.viewId`
- `nativeActionContract.identity.model == searchContract.nativeIdentity.model`
- `searchContract.nativeIdentity.authority` 与 Action 声明一致
- Search filter/group/filter native locator 仍来自该 Search View

## 9. Occurrence 语义设计

### 9.1 统一 occurrence identity

建议所有 View Profile 使用同一原生身份形状：

```json
{
  "nativeIdentity": {
    "viewType": "form",
    "viewId": 346,
    "kind": "field",
    "name": "amount",
    "nativeLocator": "/form[1]/sheet[1]/group[3]/field[4]",
    "occurrenceIndex": 1,
    "sourcePosition": 27,
    "authoritative": true
  }
}
```

约束：

- `nativeLocator + occurrenceIndex + viewId + kind` 构成结构身份。
- `sourcePosition` 是证据/顺序，不是身份。
- `name` 是字段/动作名称，不是唯一 occurrence key。
- display label、widget、文案均不得进入稳定身份。
- 容器不得只用 `name` 作为唯一身份；同一具名 group 重复时必须依赖 locator。
- 前端不得使用数组位置重新生成发生身份。

### 9.2 Form

Form 已有最强基础：

- `addons/smart_core/core/native_view_projection.py:48-80`
- `addons/smart_core/core/native_view_projection.py:239-300`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:2299-2397`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:2116-2177`

建议复用：

- `widgetId` 作为当前渲染 occurrence ID。
- `nativeLocator/occurrenceIndex/sourcePosition` 继续作为源证据。
- 增加统一 `nativeIdentity`，不再让表单字段、容器和按钮各自使用不同形状。
- 容器 `containerId` 与 `nativeIdentity.nativeLocator` 同时存在，前者是布局 ID，后者是原生身份。

### 9.3 List

当前问题：

- `column_occurrences` 已在 parser 产生。
- `columns` 同时按字段名去重。
- 最终 `listProfile` 以 name-keyed schema 为主。

源码：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:529-566`
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:633-649`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:1875-1915`
- `addons/smart_core/handlers/ui_contract_v2.py:3241-3353`
- `addons/smart_core/handlers/ui_contract_v2.py:3490-3519`

建议 `listProfile` 增加：

```json
{
  "columnOccurrences": [
    {
      "occurrenceKey": "column.amount.5f4d...",
      "fieldCode": "amount",
      "nativeIdentity": {
        "viewType": "tree",
        "viewId": 345,
        "kind": "field",
        "nativeLocator": "/tree[1]/field[18]",
        "occurrenceIndex": 1,
        "sourcePosition": 17,
        "authoritative": true
      },
      "label": "申请金额",
      "widget": "monetary",
      "optional": "show",
      "sum": "申请金额合计",
      "state": {
        "visible": true,
        "readonly": false,
        "required": false
      },
      "relation": {},
      "domain": {},
      "context": {},
      "options": {}
    }
  ]
}
```

保留现有 `columns`/`columns_schema` 作为兼容投影，但不能作为重复 occurrence 的唯一真相。

去重规则：

- 只按相同 `occurrenceKey` 去重。
- 不按 label 去重。
- 不把两个同名字段的不同 widget/modifier 合并。

### 9.4 Container

容器身份用于：

- Status mapping。
- 低代码结构目标。
- 页面结构诊断。
- 专业 Profile 语义锚点。

建议：

- `containerId` 保持正式布局消费 ID。
- `nativeIdentity` 保存 view/locator/occurrence。
- `nativeName` 与标题继续作为业务呈现名，不替代身份。

### 9.5 Button / Action

现有按钮已有较完整 `nativeIdentity`：

- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:830-920`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:3699-3711`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py:4774-4815`

建议统一为：

- `actionId`：页内 Action Rule 消费 key。
- `backendIdentity`：后端方法/Action 权威。
- `nativeIdentity`：原生 occurrence 来源。
- `occurrenceKey`：如与 `backendIdentity` 不同，显式发布，不由前端计算。

同一方法在 header/body/row 出现多次时，不得只按 method name 合并。

## 10. Domain、Context、Groups、Options 出口

| 语义 | 建议位置 | 说明 |
| --- | --- | --- |
| Page Action Domain | `nativeActionContract.actionScope.domain/domainRaw` | Action 声明 |
| Page effective Domain | `dataContract.dataSource.primary.params.domain/domain_raw` | 当前页面执行事实 |
| Page Action Context | `nativeActionContract.actionScope.context/contextRaw` | Action 声明 |
| Page effective Context | `dataSource.params.context/context_raw` 和 `dataMeta.sourceContext` | 当前请求 |
| Field relation Domain | `widget.fieldDescriptor.domain/domainExpression` | 保留 raw + 编译 AST |
| Field relation Context | `widget.fieldDescriptor.context` | 只放字段/关系选择上下文 |
| Action selection context | 动作 rule 的 context/raw | 不能混入字段选择 context |
| Relation business authority | `componentConfig.relationEntry` | create/open/search/dialog 语义 |
| Widget parameters | `componentConfig.widgetOptions` | 只放已登记组件选项 |
| Native XML groups | `nativeIdentity.provenance` 或诊断 | 不作为前端授权规则 |
| Effective visibility/readonly/required | `statusContract` | 权限和状态求值结果 |

### 10.1 Domain

当前已有：

- parser 保存 XML `domain` attributes。
- `compile_relation_domain()` 可把 raw domain 编译为受控 AST。
- `_field_widget()` 只有字段源已有 domain 时才生成 `domain_expression`。

后续应：

- 将 view occurrence `domain` 明确合入字段源。
- 同时发布 raw 与 compiled expression。
- 编译失败必须 `unresolved`，不得回退成“无 domain”。

### 10.2 Context

当前没有等价的 occurrence 级统一编译出口。

建议：

- 字段 context 与 page/action context 分开。
- 只发布可由后端安全解析和可审计的值。
- 动态表达式若无法解析，返回 `unresolved` 原因，不把原始字符串交给前端执行。
- Context 依赖字段供 modifier/关系引擎使用，不由前端猜测。

### 10.3 Groups

Odoo `get_view()` 已按当前用户裁剪继承节点和 group 受限节点。

因此：

- 不把 `groups` 交给前端作为第二权限引擎。
- 契约的生效可见/可办结果来自 `get_view` + 后端 entitlement + status。
- 为审计可保留 declaration provenance，但必须声明 `evaluatedAt=native_get_view`。
- 未消除的受限 group 或不可证明的权限来源应 `unresolved`，不能用前端 group 判断补齐。

### 10.4 Options

分三类：

1. `relationEntry`：关系创建、打开、搜索、domain、order、dialog。
2. `widgetOptions`：已登记 Widget 的呈现/输入参数。
3. `unsupportedOptions`：当前没有标准消费者或有业务歧义的选项。

正式自动接管：

- 1 和 2 可以进入契约。
- 3 必须显式原因，不能静默丢弃后宣称原生已接管。

## 11. 四类来源与自动接管资格

| 来源 | 典型例子 | 正式自动接管 |
| --- | --- | --- |
| `native_explicit` | Action View ID、XML domain、field widget、Search View ID | 允许 |
| `model_metadata_derived` | `fields_get()` 类型/关系、模型默认 `get_view()` | 允许，但必须标记 |
| `compatibility_default` | parser fallback 推断列、默认 stage/date/progress | 不允许 |
| `unresolved` | 无法解析 View、权限、Domain/Context/option | 不允许，fail closed |

建议 `automaticTakeover.eligible` 是聚合结论：

```json
{
  "eligible": false,
  "reasonCodes": [
    "ACTION_SEARCH_VIEW_UNRESOLVED",
    "LIST_OCCURRENCE_COMPATIBILITY_DEFAULT"
  ]
}
```

不得只靠“页面能加载”判定 eligible。

## 12. 跨契约不变量

后续实现至少验证：

1. `nativeActionContract.identity.model == pageInfo.model`
2. `nativeActionContract.viewSet.activeViewType == pageInfo.viewType`
3. `viewSet.orderedViews[default].viewType == viewSet.defaultViewType`
4. `active` 必须存在于 ordered views。
5. `activeViewId` 与 `dataMeta.sourceContext.formViewId` 等现有 view identity 一致。
6. Action 的显式 `search_view_id` 若存在，`searchContract.nativeIdentity.viewId` 必须相同。
7. SearchContract 中的 filters/group/fields 只能来自该 Search View 或显式已授权 overlay。
8. Form widget 的 `nativeIdentity.viewId == activeViewId`。
9. List column occurrence 的 `nativeIdentity.viewId == activeViewId`。
10. 按钮 native identity 与 action rule backend identity 不可冲突。
11. `automaticTakeover.eligible=true` 时不得含 compatibility default 或 unresolved。
12. 页面切换 Action ID 不得变化；Model 变化必须来自 Action 权威，不能由前端重定向。

## 13. 契约版本与兼容策略

当前 V2 schema：

- `contractVersion` 必须是 `2.x`。
- 根对象闭合。
- 前端 decoder 拒绝未知根字段。

因此实施顺序必须是：

1. 设计评审通过。
2. 更新 schema、contract 版本和能力协商。
3. 后端 producer 输出 `nativeActionContract`。
4. 前端 decoder 接受并校验。
5. ActionView 改为优先消费该节点。
6. 才允许逐步切换严格模式。

不能先让后端输出、再等前端日后适配；这会让当前前端进入显式契约错误。

## 14. 现有机制复用方案

### 14.1 Action

复用 `ActionResolver`，补充：

- `views`
- `view_ids`
- `view_id`
- `search_view_id`
- action XMLID

不新建 Action parser 服务。

### 14.2 View Set

复用 `PageAssembler` 的 view type 展开和 `_projection_identity()` 的 View ID 解析。

建议抽出纯投影函数：

```text
resolve_native_action_view_set(action, model, current_user_env, requested_view)
```

输入仍由现有环境提供；输出仅 Action Contract 结构，不读数据库新表。

### 14.3 Search

复用 `app.search.config`：

- 输入增加 Action-bound `search_view_data`。
- 输出结构保持现有 `searchContract`。
- 只增加 native identity 和 provenance。

### 14.4 Current active page

继续走现有：

```text
UiContractHandler
  -> PageAssembler
  -> app.view.parser
  -> Unified Page Contract V2
```

不在 Action View Set compiler 中复制页面组装逻辑。

### 14.5 Occurrence

- Form 复用 Canonical Native View AST + 现有 widget occurrence。
- List 复用 parser `column_occurrences`，提升到 `listProfile` 正式字段。
- Button 复用现有 action `nativeIdentity`。
- Container 补齐同一身份形状。

### 14.6 Frontend

现有视图切换代码已经存在：

```text
available modes
-> preferred mode
-> switch mode
-> route persists view_mode
-> same Action load
```

后续只需替换候选来源和增加契约一致性校验，不重写 ActionView/Renderer。

## 15. 被否定的替代方案

### 15.1 不把全部 View 页面嵌套进一个响应

原因：

- 每个 View 的数据源、字段、状态和记录上下文不同。
- 会重复布局和设备裁剪。
- 容易让无权页面内容进入同一响应。
- 切换时仍要重新验证权限和记录。

### 15.2 不继续只靠 NavMeta `view_modes`

原因：

- 它没有 Action-bound View ID。
- 它没有默认/active 分离。
- 它没有 Search View identity。
- 它没有 provenance、capability 和 reason code。

### 15.3 不把 View Set 放进 `actionContract`

原因：

- `actionContract` 是页内按钮、触发和刷新规则。
- 放入 Action 路由视图族会使两个职责混为一层。

### 15.4 不立即重写旧 parser

原因：

- 当前 parser 已覆盖所有主要视图类型。
- B-S2 的缺口可通过身份和控制面补齐。
- 先重写 parser 会扩大范围并引入回归风险。

### 15.5 不在前端通过 mode 名称猜语义

原因：

- 是否可切换、是否记录详情、是否 fallback 必须由契约和注册 Renderer 声明。
- 前端不得从 `form`、`tree` 或 model name 发明业务语义。

## 16. 后续实施顺序建议

本轮不实施。获得设计批准后，建议按以下顺序分 PR：

### P0-1：Action identity 完整化

- `ActionResolver` 保留 views/search/view ID。
- 增加纯单测和样本 Action。
- 不改 UCP schema。

### P0-2：Search View 身份闭环

- PageAssembler 将 Action-bound Search View 数据传入 `app.search.config`。
- SearchContract 增加 native identity/provenance。
- 覆盖显式 View、无显式 View、View 失效和权限拒绝。

### P0-3：Native Action Contract 协议扩展

- 设计 schema 2.3.0。
- 增加受控根节点和能力协商。
- 生成 View Set 描述，但页面内容仍由当前 V2 表达。

### P0-4：Occurrence 统一

- Form widget/container 补统一 native identity。
- List 增加 columnOccurrences。
- Domain/Context/options provenance 完整化。

### P0-5：前端消费

- decoder 接受新节点。
- ActionView 读取 `nativeActionContract.viewSet`。
- 保留现有 Renderer Registry 和 view mode switch。
- 增加缺失/非法契约 fail-closed。

Widget、交互执行、Calendar/Gantt/Dashboard 和行业专业视图仍留在后续专题。

## 17. 未来验收要求

### L1

- 真实 Action XMLID、ordered views、search_view_id、View IDs 和模型可追溯。
- 两个样本 Action 身份不依赖模型默认猜测。

### L2

- 每个 view entry 都能形成唯一 View Profile。
- active/default/supporting view 身份一致。
- Search Contract 绑定正确 Search View。
- occurrence 在相同 View ID 下稳定，不被 label/name 去重。

### L3

- 前端能从契约获得 mode 列表和 disabled/fallback 原因。
- 不读取 model/menu 猜测。
- 切换后仍使用同一 Action Domain/Context，并正确加载目标 View。
- 缺失或非法 Action Contract 显式停机。

### L4

- 至少覆盖两个不同角色。
- 有权限/无权限、可切换/不可切换、View 缺失、Search View 缺失。
- 真实记录打开 form、返回 list 后 Action identity 和 route context 保持不变。

本轮不执行 L3/L4。

## 18. 对三个研究问题的直接回答

### 18.1 Action View Set 如何成为一等契约

新增受控 `nativeActionContract.viewSet`，只发布有序 View 身份、默认/活动 View、
能力、来源和原因。每个活动 View 的完整页面仍由现有 V2 表达。

### 18.2 Search View 身份如何保真

Action Resolver 必须保留 `search_view_id`；PageAssembler 必须把该 View 的原生数据传给
Search Config；SearchContract 必须发布自己的 native identity。Action 显式 Search View
解析失败时 fail closed，不退回模型默认 View。

### 18.3 Occurrence 如何统一

统一使用 `viewType + viewId + nativeLocator + occurrenceIndex + kind`。
Form 复用现有 widget occurrence；List 把 `column_occurrences` 提升为正式
`columnOccurrences`；按钮复用 native/backend identity；容器补同一 shape。
Domain/Context、groups、widget options 和 relation entry 各归显式出口。

## 19. 最终决策

本检查点的建议是：

- 继续使用现有 Unified Page Contract V2。
- 在其上增加一个受控 Native Action Contract，而不是另建页面系统。
- View Set 只做身份和控制面，不嵌套复制所有页面。
- Search 身份由 Action 明确下传，不再依赖模型默认视图。
- Occurrence 统一原生身份，禁止按 name/label 合并不同语义。
- 兼容 fallback 只能作为非正式交付，不能伪装成原生事实。
- 本轮不实施、不新增模型、不改 Renderer。

本检查点到此停止，等待独立复核和后续实施授权。
