# 前端主线契约对接手册 v2

## 1. 文档定位

本文是当前 Web 前端接入 SCE 后端主线契约的实施手册，覆盖：

- 统一传输协议与认证；
- 启动链路；
- `Unified Page Contract v2` 页面契约；
- 数据读取、保存、联动与按钮执行；
- 字段语义、错误处理、缓存、权限和兼容边界；
- `frontend/apps/web` 当前列表、筛选、详情、字段与动作的实际渲染链；
- 推荐接入顺序、代码入口和验收清单。

本文记录的是下列取证基线上的仓库事实，不把历史设计稿或兼容协议当成默认主线。分支继续演进时，
应以实际源码、Schema 和运行时响应重新核对尚未闭环的能力：

| 项目 | 当前基线 |
| --- | --- |
| 仓库 | `sce-backend-odoo` |
| 候选分支 | `feature/p0-page-pattern-reference-parity-v1` |
| 文档取证 HEAD | `782f2617ebcbdd66d14185946e69f63c272b3abc` |
| `origin/main` / 分叉基线 | `5e5b1f5f5bc0cbe502ca862155c5268be69f09fc` |
| HTTP 入口 | `POST /api/v1/intent` |
| 页面主契约 intent | `ui.contract.v2` |
| 当前页面契约版本 / 可接受版本族 | `2.2.0` / Web 客户端声明 `2.0.x`、`2.1.x`、`2.2.x` |
| 启动契约版本 | `system.init = 2.0.0` |
| Dispatcher 默认信封版本 | `1.0.0`；具体 handler 可在成功响应中覆盖 |

> 注意：上述 SHA 用于追溯本文依据。前端联调时必须以部署环境实际返回的
> `meta.contract_version`、`data.pageInfo.contractVersion` 和
> `data.meta.lifecycle` 为运行时事实，不能把文档 SHA 写进业务代码。

## 2. 权威来源与冲突处理

出现描述冲突时，按以下顺序判断：

1. `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json`：页面载荷结构约束；
2. `addons/smart_core/controllers/intent_dispatcher.py`：HTTP、认证、事务和统一信封；
3. `addons/smart_core/handlers/*.py`：具体 intent 的参数和行为；
4. `frontend/apps/web/src/app/contracts/v2/schema.ts`：当前 Web 客户端实际执行的失败关闭解码规则；
5. `frontend/apps/web/src/app/contracts/v2/types.ts` 与 `frontend/packages/schema/src/index.ts`：客户端类型；
6. 本文：面向接入方的解释与示例。

若 Schema 与客户端解码器暂时存在宽严差异，接入方应满足两者的交集。不要依赖
`additionalProperties`、历史别名或客户端容错来承载新业务语义。

## 3. 总体设计意图

主链路固定为：

```text
Odoo 原生 view/action/field/ACL
  -> 后端解析与语义治理
  -> Unified Page Contract v2
  -> 前端严格解码与标准化 store
  -> 通用渲染器
  -> intent 交互与局部/完整刷新
```

核心责任边界：

| 责任 | 后端 | 前端 |
| --- | --- | --- |
| 页面结构 | 解析原生视图并输出 `layoutContract` | 按容器树和组件注册表渲染 |
| 权限/状态 | 输出 `statusContract` 与原因码 | 展示裁决结果，不重新推断 |
| 行为 | 输出 `actionContract` 与后端身份 | 原样回传权威身份并执行 intent |
| 数据 | 输出 `dataContract`，业务事实由 ORM/领域模型拥有 | 展示、编辑暂存、提交 |
| 运行策略 | 输出 `runtimeContract` | 严格解码；仅消费已接线策略，未接线字段不得被宣称已生效 |
| 业务语义 | 后端和正式产品契约拥有 | 禁止按 model、菜单名、角色码猜测 |

这套协议是 UI Runtime 的中间表示，不是让前端执行任意规则的 DSL。前端不得解析
Odoo XML，不得执行后端下发的脚本/表达式，也不得自行计算权限、工作流或业务指标。

## 4. 统一 HTTP 与 Intent 协议

### 4.1 请求

所有主线接口共用一个 HTTP 入口：

```http
POST /api/v1/intent?db=<database>
Content-Type: application/json
X-Trace-Id: <uuid>
X-Tenant: <tenant-key>
X-Odoo-DB: <database>
Authorization: Bearer <token>
```

统一请求体：

```json
{
  "intent": "ui.contract.v2",
  "params": {},
  "context": {},
  "meta": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `intent` | string | 是 | 处理器名称；必须使用本文列出的 canonical 名称 |
| `params` | object | 按 intent | 业务参数；主线统一使用 `snake_case` |
| `context` | object | 否 | 跨 intent 的请求上下文；当前记录上下文会由 Web 客户端自动合并 |
| `meta` | object | 否 | 传输/调用元信息，例如按钮执行所需的 `action_id`、`menu_id` |

HTTP 头：

| Header | 必填 | 说明 |
| --- | --- | --- |
| `Content-Type: application/json` | 是 | 统一 JSON 请求 |
| `X-Trace-Id` | 建议 | 客户端生成；服务端响应会回传/补齐，排障必须记录 |
| `X-Odoo-DB` | 多库环境是 | 数据库权威；官方客户端还会把 `db` 放入 intent URL，消除多库歧义 |
| `X-Tenant` | 官方客户端固定发送 | 租户标识，由运行时配置提供 |
| `Authorization: Bearer ...` | 除匿名 intent 外 | 登录返回 token；不要发送 Odoo session cookie |
| `X-Anonymous-Intent: 1` | 匿名 intent | `login`、`session.bootstrap`、`sys.intents` 等匿名白名单入口 |
| `X-SC-Client-Type` | 可选 | 终端类型；页面请求更推荐在 `params.client_type` 明确声明 |
| `If-None-Match` | 可选 | 支持 ETag 的读取请求；命中时返回 HTTP 304 空体 |

官方 Web 客户端固定 `credentials: "omit"`，使用 Bearer token，不混用浏览器中的 Odoo Cookie。

### 4.2 成功响应

当前统一成功信封：

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "trace_id": "7ef1...",
    "intent": "ui.contract.v2",
    "elapsed_ms": 18,
    "api_version": "v1",
    "contract_version": "2.2.0",
    "schema_version": "1.0.0"
  },
  "status": "success"
}
```

| 字段 | 类型 | 必填 | 消费规则 |
| --- | --- | --- | --- |
| `ok` | boolean | 是 | 只有严格 `true` 才进入成功路径 |
| `data` | any | 是 | intent 的业务载荷 |
| `meta` | object | 是 | 传输和契约元数据；不得与 `data.meta` 混淆 |
| `meta.trace_id` | string | 是 | 端到端排障 ID |
| `meta.intent` | string | 是 | 服务端规范化后的 intent |
| `meta.elapsed_ms` | integer | 是 | 服务端处理耗时 |
| `meta.api_version` | string | 是 | HTTP intent API 版本，当前 `v1` |
| `meta.contract_version` | string | 是 | handler 声明的接口版本；当前 `ui.contract.v2=2.2.0`、`system.init=2.0.0`，其余未覆盖时为 `1.0.0` |
| `meta.schema_version` | string | 是 | 当前 intent 响应 Schema 版本 |
| `status` | string | 否 | 部分 handler 提供的人类可读状态，不替代 `ok` |
| `code` | integer | 否 | 特殊 HTTP 状态提示；正常成功通常省略 |

页面接口中存在两层 `meta`：

- 信封 `response.meta`：HTTP intent 调用信息；
- 页面 `response.data.meta`：页面快照、ETag、生命周期和完整性信息。

接入代码必须分别命名，例如 `envelopeMeta` 与 `contract.meta`。

### 4.3 错误响应

```json
{
  "ok": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "permission denied",
    "reason_code": "PERMISSION_DENIED",
    "hint": "...",
    "retryable": false,
    "details": {
      "intent": "api.data",
      "model": "project.project",
      "op": "write"
    }
  },
  "meta": {
    "trace_id": "7ef1...",
    "api_version": "v1",
    "contract_version": "1.0.0"
  }
}
```

标准 HTTP/错误码：

| HTTP | `error.code` | 前端动作 |
| --- | --- | --- |
| 400 | `BAD_REQUEST` | 标记请求/契约错误，不盲目重试 |
| 401 | `AUTH_REQUIRED` | 清理本地会话并转登录页 |
| 403 | `PERMISSION_DENIED` / `FEATURE_DISABLED` | 展示后端原因；禁止前端绕过 |
| 404 | `INTENT_NOT_FOUND` | 记录 intent/资源缺失，失败关闭 |
| 410 | 交付策略阻断 | 切换正式 scene route，不回退到原生页面猜测 |
| 422 | `VALIDATION_ERROR` | 将 `fields/details` 映射到表单错误 |
| 429 | `LIMIT_EXCEEDED` | 仅在 `retryable` 或策略允许时退避重试 |
| 500 | `INTERNAL_ERROR` | 展示通用错误并携带 `trace_id` 上报 |

`reason_code` 比 message 稳定；分支逻辑必须优先使用 `reason_code/code`，message 只用于展示。

### 4.4 事务语义

- 读取 intent 不主动提交事务；
- 写 intent 仅在 HTTP `< 400` 且 `ok=true` 时提交；
- 写 intent 失败时显式回滚；
- HTTP 304 返回空体，不能调用 JSON 解码；
- 前端超时不代表后端一定未执行，非幂等写操作不能自动重放。

## 5. 启动链路

### 5.1 顺序

```text
login -> 保存 token/session.db -> system.init -> initStatus=ready -> 其他 intent
```

登录后、`system.init` 成功前，官方客户端只允许启动白名单 intent。其他调用应在客户端以
`STARTUP_CHAIN_REQUIRED` 失败关闭，避免页面在缺少导航、角色和 route authority 时运行。

### 5.2 `login`

请求：

```json
{
  "intent": "login",
  "params": {
    "login": "user@example.com",
    "password": "***",
    "contract_mode": "default",
    "db": "sc_dev_demo"
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `login` | string | 是 | 登录名 |
| `password` | string | 是 | 密码；禁止日志记录 |
| `contract_mode` | `default\|compat\|debug` | 否 | 默认 `default`；生产前端不得常态使用 `debug` |
| `db` | string | 视路由策略 | 数据库已由登录路由固定时应省略，不能覆盖权威路由 |

`data` 关键字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `token` / `session.token` | string | Bearer token；客户端兼容两处，推荐读 `session.token ?? token` |
| `token_type` / `session.token_type` | string | 通常为 bearer 类型 |
| `expires_at` / `session.expires_at` | number | 到期时间 |
| `session.db` | string | 后续请求必须使用的数据库 |
| `user` | object | `id/name/login/lang/tz/company/allowed_company_ids` |
| `entitlement` | object | 角色和公司切换能力摘要 |
| `bootstrap.next_intent` | string | 仅接受 `system.init` 或受控的 `session.bootstrap` |
| `contract` | object | 登录响应版本与兼容模式状态 |

### 5.3 `session.bootstrap`

该入口用于受控 dev/test 会话启动，不是正式用户登录的通用替代。生产前端应遵循
`login` 返回的 `bootstrap.next_intent`，不得自行切换为 `session.bootstrap`。

### 5.4 `system.init`

请求：

```json
{
  "intent": "system.init",
  "params": {
    "scene": "web",
    "root_xmlid": "smart_construction_core.menu_root",
    "with": ["workspace_home"]
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `scene` | string | 否 | 默认 `web` |
| `root_xmlid` | string | 否 | 产品导航根；应来自部署配置，不写死到通用组件 |
| `with` | string/string[] | 否 | 可选附加载荷；`workspace_home` 会内联首页契约 |
| `with_preload` | boolean | 否 | 兼容预取开关；更推荐显式 `with` |
| `contract_mode` | `user\|hud` | 否 | 默认 `user`；`hud` 仅用于授权诊断。`native` 是页面 `contract_surface`，不是启动 mode |
| `delivery_*` / `edition_*` | string | 否 | 交付身份选择，仅由正式运行配置提供 |

`data` 现行关键字段：

| 字段 | 类型 | 必填 | 设计意图 |
| --- | --- | --- | --- |
| `user` | object | 是 | 当前登录用户、公司、语言、时区和平台管理员状态 |
| `navigation` | object | 是 | 唯一正式导航载荷，见下表 |
| `capabilities` | array | 否 | 已裁决能力；可能是 key 或带状态的对象 |
| `capability_groups` | array | 否 | 能力分组与状态计数 |
| `role_surface` | object | 否 | 当前角色落点；不是让前端反推业务语义 |
| `role_surface_map` | object | 否 | 多角色可用 surface 摘要 |
| `record_context` | object | 否 | 当前公司/项目等业务上下文及可选项 |
| `default_route` | object/string | 否 | 后端裁决默认落点 |
| `workspace_home` | object | 否 | 仅请求预取时内联 |
| `workspace_home_ref` | object | 否 | 首页延迟加载引用 |
| `page_contracts` | object | 否 | 页面级编排载荷 |
| `scene_ready_contract` | object | 否 | 正式 scene-ready 页面入口集合 |
| `scene_governance` | object | 否 | scene 治理/诊断；普通页面不应依赖诊断字段 |
| `feature_flags` | object | 否 | 已裁决功能开关 |
| `intents` / `intents_meta` | array/object | 否 | 最小启动 intent surface，不等于完整 API 文档 |
| `intent_catalog_ref` | object | 否 | 完整 intent 目录的延迟引用 |

`navigation`：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `contract_version` | `2.0.0` | 是 | 导航契约版本 |
| `schema_version` | `2.0.0` | 是 | 导航 Schema 版本 |
| `source` | string | 是 | 当前为 `system_init.navigation` |
| `nav` | array | 是 | 当前用户可见导航树 |
| `route_authority` | object | 是 | 路由授权事实；导航动作必须与其一致 |
| `contextual_routes` | array | 否 | 依赖记录上下文的路由 |
| `integrity` | object | 是 | 可见动作数、授权动作数、缺失授权数；`missing_authority_count` 必须为 0 |
| `meta` | object | 否 | 导航生成和治理元信息 |

现行 `system.init` 会移除历史并行 carrier：`nav`、`nav_legacy`、`route_authority` 等。
前端只消费 `data.navigation.nav` 和 `data.navigation.route_authority`，不要恢复根级兼容读取。

## 6. 页面主接口：`ui.contract.v2`

### 6.1 两种标准请求

按 action 打开：

```json
{
  "intent": "ui.contract.v2",
  "params": {
    "op": "action_open",
    "action_id": 120,
    "menu_id": 45,
    "scene_key": "project.list",
    "view_type": "tree",
    "delivery_profile": "full",
    "client_type": "web_pc",
    "accepted_contract_versions": ["2.0.x", "2.1.x", "2.2.x"],
    "client_contract_capabilities": [
      "container_tree.v2",
      "data_source.v2",
      "action_rule.v2",
      "relation_entry.v2",
      "status_contract.v2",
      "form_layout.children_owner.v1"
    ]
  }
}
```

按 model 打开：

```json
{
  "intent": "ui.contract.v2",
  "params": {
    "op": "model",
    "model": "project.project",
    "view_type": "form",
    "record_id": 42,
    "render_profile": "edit",
    "action_id": 120,
    "menu_id": 45,
    "delivery_profile": "full",
    "client_type": "web_pc",
    "accepted_contract_versions": ["2.0.x", "2.1.x", "2.2.x"]
  }
}
```

### 6.2 请求参数

| 参数 | 类型 | 必填 | 约束/说明 |
| --- | --- | --- | --- |
| `op` | `action_open\|model` | 是 | action 导航或 model 页面 |
| `action_id` | positive integer | `action_open` 是 | Odoo window action ID；表单行为权威也需要它 |
| `menu_id` | positive integer | 导航进入建议是 | 用于 scene/route/action 权威绑定 |
| `model` | string | `model` 是 | Odoo model 技术名；action 模式由后端解析 |
| `view_type` | string | 否 | 默认 form；支持 form/tree/list/kanban/pivot/graph/calendar/gantt/activity/dashboard 等 |
| `view_id` | positive integer | 否 | 指定原生视图，必须属于当前 action/model 权威范围 |
| `record_id` | positive integer | 编辑/只读表单 | 单记录上下文；创建态省略 |
| `render_profile` | `create\|edit\|readonly` | 表单建议是 | 客户端可按 `record_id` 解析；后端最终裁决 |
| `scene_key` | string | scene 导航时 | 与 scene action binding 校验 |
| `client_type` | `web_pc\|wx_mini\|harmony_h5` | 建议是 | 决定终端裁剪；Web 当前固定 `web_pc` |
| `delivery_profile` | string | 建议是 | Web 当前主线使用 `full` |
| `accepted_contract_versions` | string[] | Web 主线必发 | 客户端声明可接受版本族；客户端解码仍须对不兼容响应失败关闭 |
| `client_contract_capabilities` | string[] | Web 主线必发 | 客户端已实现能力，不能虚报；当前 handler 将其作为能力协商输入 |
| `contract_surface` | `user\|native\|hud` | 否 | 默认用户治理面；native/hud 仅诊断 |
| `source_mode` | string | 否 | 受控来源模式；普通接入不自行指定 |
| `source_type` | `ui.contract\|scene_contract` | 否 | 默认 `ui.contract`；scene 模式必须有 `scene_key` |
| `context` | object | 否 | 结构化 Odoo/业务上下文 |
| `context_raw` | string | 否 | Odoo action 原始 context 兼容载荷；不要由用户输入拼接 |
| `domain_raw` | string | 否 | action 原始 domain 兼容载荷；不要由用户输入拼接 |
| `request_id` | string | 否 | 页面请求身份；缺省回退 trace ID |
| `preview_token` | string | 否 | 低代码草稿预览，仅授权配置管理员 |
| `preview_role_key` | string | 否 | 预览角色；正式表单角色仍以认证会话为权威 |

`actionId/menuId/viewId/recordId/renderProfile/...` 等 camelCase 只属于兼容读取。
新接入请求统一发送 snake_case。

### 6.3 返回顶层

`response.data` 是页面快照。七个核心字段必填，三个扩展字段受控可选：

| 字段 | 必填 | 职责 | 前端入口 |
| --- | --- | --- | --- |
| `pageInfo` | 是 | 页面身份 | 路由标题、页面类型、版本检查 |
| `layoutContract` | 是 | 容器、控件和适配布局 | 通用 renderer |
| `statusContract` | 是 | 可见、只读、必填、禁用、权限原因 | normalized status store |
| `actionContract` | 是 | 动作、触发、目标、刷新和后端身份 | action runtime |
| `dataContract` | 是 | 主数据、集合、关系和数据源 | data source runtime |
| `runtimeContract` | 是 | 补丁、缓存、重试、渲染策略 | strict decoder + 已登记的 runtime consumers |
| `meta` | 是 | ETag、快照、追踪、生命周期与完整性 | cache/diagnostics |
| `formStructureContract` | 否 | 产品级表单结构角色 | canonical form presenter |
| `searchContract` | 否 | 搜索、筛选、分组和收藏 | collection search runtime |
| `workflowContract` | 否 | 受控工作流扩展 | 专用通用适配器 |

顶层未知字段默认拒绝。新增能力应进入既有子契约；不能因为前端需要就自行增加平级字段。

## 7. 页面契约字段详解

### 7.1 `pageInfo`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `pageId` | string | 稳定页面 ID；用于 page/layout 对齐，不用作业务主键 |
| `sceneKey` | string | 场景键；来源于后端 scene 绑定 |
| `pageName` | string | 后端裁决的显示名 |
| `model` | string | 数据模型技术名；只用于 API 参数，不用于前端业务分支 |
| `viewType` | enum | 原始/语义视图类型 |
| `layoutType` | enum | 实际布局类型；list 可能规范化为 table |
| `renderMode` | `governed` | 默认用户面只允许治理渲染 |
| `contractVersion` | string | 页面载荷版本；解码前必须验证兼容性 |
| `clientType` | enum | `web_pc/wx_mini/harmony_h5`，必须与请求终端一致 |

设计意图：页面身份与结构/数据分离。不得在 `pageInfo` 中塞权限、记录值或组件配置。

### 7.2 `layoutContract`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `pageId` | string | 是 | 必须与 `pageInfo.pageId` 一致 |
| `layoutType` | enum | 是 | 当前布局类型 |
| `adaptMode` | `pc\|mobile` | 是 | 终端适配模式 |
| `containerTree` | container[] | 是 | 权威结构树 |
| `layoutHints` | object | 是 | 通用布局提示；不能承载业务规则 |
| `componentRegistry` | object | 是 | `componentKey -> adapter/fallback` 注册表 |
| `listProfile` | object | 否 | 列表/集合表现语义 |
| `activityProfile` | object | 否 | activity 原生视图保真投影 |

容器/节点关键字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `containerId` | string | 稳定容器身份；状态表通过它寻址 |
| `containerType` | enum/string | group/tab/card/tree/section 等结构类型 |
| `title` / `label` / `string` | string | 后端来源的显示语义；不能由 model 名猜测 |
| `span` / `cols` / `columns` | integer | 栅格与列数；前端可做响应式收缩，不改变顺序 |
| `styleToken` | string | 受控样式 token，不是任意 CSS |
| `children` | node[] | 子结构，保持后端顺序和原生出现次数 |
| `widgetList` | widget[] | 当前容器直接拥有的控件 |
| `nativeLocator` | string | 原生节点定位证据，主要用于保真与诊断 |
| `occurrenceIndex` | integer | 同一字段/节点重复出现时的 occurrence 身份 |
| `sourcePosition` | integer | 原生结构顺序证据 |
| `modifiers` | object | 原生 modifier 载荷；最终状态仍以 `statusContract` 为准 |
| `formStructureRole` | object | 当前节点的 summary/task/context/risk/relation/activity/audit 角色 |

Widget：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `widgetId` | string | 是 | 控件实例身份；重复字段不能只按 fieldCode 合并 |
| `widgetType` | string | 是 | 语义控件类型 |
| `fieldCode` | string | 是 | Odoo 字段名 |
| `label` | string | 是 | 后端字段/视图标签 |
| `span` | integer | 是 | 当前布局跨度 |
| `componentKey` | string | 是 | 组件注册键，例如通用 input/select/relation adapter |
| `capabilities` | string[] | 是 | 显式能力列表；未知能力必须走 fallback/unsupported |
| `componentConfig` | object | 是 | 组件参数，不允许作为无限业务规则袋 |
| `ownerContainerId` | string | 是 | 直接父容器 |
| `fieldDescriptor` | object | 否 | 类型、relation、selection、domain、widget options 等字段描述 |
| `nativeLocator/occurrenceIndex/sourcePosition` | mixed | 否 | 原生成员关系和顺序证据 |

`componentRegistry` 每项：

```json
{
  "version": "1.0",
  "adapter": { "web_pc": "ScInput" },
  "selectedAdapter": "ScInput",
  "fallback": "ScUnsupportedField"
}
```

前端按 `componentKey + clientType` 解析适配器。未知 key 或声明不完整时显示明确 unsupported，
禁止按字段名/model 写页面特判。

### 7.3 `formStructureContract`

该字段仅在 form 页面出现，用于区分“任务办理表单”和“对象工作台”，不替代原生容器树。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source` | 固定字符串 | `ui.contract.v2.form_structure_contract` |
| `structureVersion` | `1.0\|1.1` | 结构协议版本 |
| `model` | string | 目标模型 |
| `viewType` | `form` | 只适用于表单 |
| `mode` | string | 当前结构模式 |
| `presentationMode` | `task\|workspace` | 任务式办理或对象工作台 |
| `layoutPolicy` | string | 正式布局策略 |
| `columns` | integer | 总列数（可选） |
| `objectProfile` | object | `model/kind/factAuthority`，指出业务事实权威 |
| `navigation.title` | string | 页面导航标题 |
| `slots` | slot[] | 语义槽位及其字段/分组 |
| `fieldRoles` | object | `fieldCode -> {role,slot,group}` |
| `sourceAuthority` | object | 来源、投影和治理证据 |

语义角色枚举：`summary`、`task`、`context`、`risk`、`relation`、`activity`、`audit`。

消费规则：

- 先用 `layoutContract.containerTree` 保持原生结构；
- 再用 `formStructureContract` 做产品级呈现分区；
- 同一字段多 occurrence 时保留各自 `widgetId/nativeLocator`；
- `fieldRoles` 缺失时不得按字段名推断角色；
- `sourceAuthority.no_business_fact_authority=true` 表示它只编排结构，不拥有字段值。

### 7.4 `statusContract`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `globalStatus` | object | 页面、模型、记录、工作流和 render profile 的总体状态 |
| `containerStatus` | array | 以 `containerId` 寻址的容器可见/禁用状态 |
| `widgetStatus` | array | 以 `widgetId` 寻址的字段状态 |
| `buttonStatus` | array | 以 `btnId/backendIdentity` 寻址的按钮状态 |
| `selectorStatus` | array | 以稳定 selector 寻址的状态补充 |

状态行：

| 对象 | 身份字段 | 状态字段 |
| --- | --- | --- |
| container | `containerId` | `visible/disabled/reasonCode` |
| widget | `widgetId` | `visible/readonly/required/disabled/placeholder/auth/reasonCode` |
| button | `btnId` + 可选 `backendIdentity` | `visible/disabled/reasonCode` |
| selector | `selector` | `visible/readonly/required/disabled/reasonCode` |

关键规则：

- boolean 必须是真正 JSON boolean；字符串 `"false"` 是契约错误，不能做 truthy 转换；
- 字段缺省表示“未在该状态面声明”，不是自动等于 false；
- 展示禁用原因使用 `reasonCode` 映射通用文案，不重新计算权限；
- action 是否可执行必须同时满足 action rule 与 button status，任一缺失均失败关闭。

### 7.5 `actionContract`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `actionRuleList` | actionRule[] | 是 | 当前页面所有交互规则 |
| `dependencyGraph` | object | 是 | action/控件间 ID 边集合，不是可执行表达式 |
| `deletePolicy` | object | 否 | 删除授权和确认策略 |
| `surfacePolicies` | object | 否 | 动作表面策略 |
| `identityPolicy` | object | 否 | 动作身份校验策略 |
| `primaryResolution` | object | 否 | 主动作解析结果 |

Action rule 核心字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `actionId` | string | 是 | 前端/后端共同校验的稳定动作 ID |
| `backendIdentity` | string | 执行后端动作时 | 后端动作身份；必须原样回传 |
| `sourceWidgetId` | string | 是 | 动作来源控件；必须匹配当前页面实例 |
| `triggerType` | enum | 是 | change/click/select/submit 等 |
| `targetIds` | string[] | 是 | 影响目标 |
| `dispatchMode` | enum | 是 | local/server/serverDebounced/serverBlocking |
| `targetScope` | enum | 是 | widget/container/page/dataSource/runtime |
| `refreshMode` | enum | 是 | none/partial/full |
| `intent` | string | 否 | 服务端分发 intent |
| `button` | object | 否 | `name/type/server_action_id/xml_id` 等后端按钮事实 |
| `target` | object | 否 | 导航/action 目标 |
| `allowed/enabled/disabled` | boolean | 后端动作应有 | 最终可执行状态 |
| `entitlementEvaluated` | boolean | 后端动作应有 | 表示权限已由后端裁决 |
| `reasonCode` | string | 否 | 禁止/降级原因 |
| `presentation` | object | 否 | 展示语义，不改变执行身份 |
| `refreshPolicy/submitPolicy/tracePolicy` | object | 否 | 运行策略 |

前端执行按钮时不得只传 method 名。必须从同一快照回传：

```json
{
  "intent": "execute_button",
  "params": {
    "model": "project.project",
    "res_id": 42,
    "button": {
      "name": "action_confirm",
      "type": "object",
      "action_id": "project.confirm",
      "backend_identity": "...",
      "source_widget_id": "button.confirm"
    }
  },
  "meta": {
    "action_id": 120,
    "menu_id": 45
  }
}
```

后端会重新加载当前记录的页面契约，核对 action ID、backend identity、source widget、按钮方法、
权限、状态、action/menu 和单记录范围。契约已漂移时应重新加载页面，不得绕过重试旧动作。

### 7.6 `dataContract`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `mainData` | object | 是 | 表单主记录或页面主数据 |
| `tableRows` | object | 是 | `dataSourceKey -> row[]` |
| `relationRows` | object | 是 | `relationKey -> row[]` |
| `treeData` | object | 否 | 树形数据源 |
| `ganttData` | object | 否 | 甘特数据源 |
| `dictData` | object | 是 | 字典/selection 等展示数据 |
| `pagination` | object | 是 | 数据源分页状态 |
| `dataSource` | object | 是 | 数据源定义、model/domain/context/fields 等 |
| `dataMeta` | object | 是 | 可见字段、分组、业务操作 profile 与 source context |

`dataMeta`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `businessOperationProfile` | object | 正式业务操作表面的字段和呈现摘要 |
| `visibleFields.fields` | string[] | 后端裁决的可见业务字段 |
| `visibleFields.sourceAuthority` | object | 可见字段来源证据 |
| `fieldGroups.groups` | object[] | 字段分组语义 |
| `sourceContext.context/domain` | object/array | 已规范化的 action 上下文和 domain |
| `sourceContext.contextRaw/domainRaw` | string | 原始兼容证据；前端不执行 |
| `sourceContext.renderProfile` | enum | create/edit/readonly |
| `sourceContext.order/limit` | string/integer | 集合默认排序和限制 |

业务值由 ORM/领域模型拥有；`sourceAuthority.projection_only=true` 的结构字段不能被当作业务事实。

### 7.7 `searchContract`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `default_sort/default_order` | string | 后端默认排序 |
| `mode` | string | 搜索模式 |
| `filters` | array | 正式过滤器 |
| `saved_filters` | array | 已授权保存筛选 |
| `group_by` | array | 分组项 |
| `fields` | array | 搜索字段 |
| `search_panel` | object | 搜索面板结构 |
| `favorites` | object | 收藏能力和状态 |
| `custom` | object | 受控扩展 |
| `ui_labels` | object | 后端提供的展示文案 |
| `defaults` | object | 默认激活项 |

前端将选中项转换为 `api.data` 的 domain/group_by/order 参数；不能自己维护一套与后端冲突的
业务过滤字典。

### 7.8 `runtimeContract`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `patchStrategy` | `incremental\|full` | 是 | 允许增量补丁还是完整刷新 |
| `cachePolicy` | `none\|etag\|snapshot` | 是 | 缓存模式 |
| `optimistic` | boolean | 是 | 是否允许乐观表现；不改变提交事实 |
| `lazyContainer` | string[] | 是 | 延迟加载容器 ID |
| `virtualization` | object | 是 | 大集合虚拟化参数 |
| `retryPolicy` | object | 是 | 可重试条件和退避 |
| `renderStrategy` | enum | 否 | sync/scheduled/virtualized |
| `hydration` | object | 否 | 首屏/延迟数据装配策略 |
| `patchOperations` | enum[] | 否 | 只允许 replace/merge/append/remove/reorder/invalidate |
| `tracePolicy` | object | 否 | 追踪要求 |
| `complexityBudget` | object | 否 | 页面复杂度预算 |
| `aiEnvelope` | object | 否 | 仅建议，不可执行 |
| `collaboration/businessWorkspace/businessActions` | mixed | 否 | 受控运行扩展 |

禁止把 runtime 字段扩展为脚本、函数、eval、JSON Logic、循环或工作流 VM。

当前 Web 主线会严格解码 `runtimeContract`，并消费已经明确接入页面运行链的交互、动作目标、协作和
工作区信息。`patchStrategy`、`cachePolicy`、`retryPolicy`、`renderStrategy`、`virtualization`、
`complexityBudget` 与 `aiEnvelope` 等字段在本文取证 HEAD 上尚不能整体视为生产执行权威：Schema
存在和解码通过只证明载体合法，不证明对应 controller 已执行其语义。接入方必须逐字段核对正式
consumer、正反例测试和运行态证据；未接线策略不得由页面自行猜测，也不得用客户端默认行为冒充
契约消费。

### 7.9 页面 `meta` 与生命周期

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `etag` | string | 是 | 快照缓存身份 |
| `snapshotId` | string | 是 | 页面快照 ID |
| `traceId` | string | 是 | 页面生成追踪 ID |
| `requestId` | string | 是 | 页面请求 ID |
| `sourceType` | string | 是 | `ui.contract`、`native_form_projection` 等来源 |
| `lifecycle` | object | 是 | 定义、生成、运行、完整性和权威链 |

`lifecycle`：

| 分区 | 关键字段 | 用途 |
| --- | --- | --- |
| `definition` | `schemaId/schemaVersion/schemaSha256/contractVersion/normativeStatus` | 绑定正式 Schema |
| `generation` | `generator/generatorVersion/sourceType/sourceSha256` | 绑定生成器与源快照 |
| `runtime` | `requestId/traceId/clientType/traceSource` | 绑定本次运行身份 |
| `integrity` | `algorithm/contractSha256` | 页面内容完整性 |
| `authority` | source authority | 说明谁拥有语义、谁只是投影 |

客户端缓存键至少应包含数据库、用户 token/主体、当前上下文 epoch 和完整请求参数。切换公司、
项目/记录上下文、角色会话或数据库时必须清理相关缓存。

## 8. 数据与交互接口

### 8.1 `api.data`：读取与基础保存

统一请求：`intent=api.data`，用 `params.op` 选择操作。

#### list

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `op` | `list` | - | 固定 |
| `model` | string | - | 必填 |
| `fields` | string[]/`*` | `id,name` | 只请求契约允许且页面需要的字段 |
| `domain` | array | `[]` | 结构化 domain |
| `domain_raw` | string | `""` | action 原始 domain；与 domain 同时存在时 AND 合并 |
| `context/context_raw` | object/string | `{}`/`""` | 上下文；raw 只作可信 action 兼容输入 |
| `limit/offset` | integer | `40/0` | 记录分页 |
| `order` | string | `""` | 后端校验的排序表达式 |
| `search_term` | string | 空 | 通用搜索词 |
| `need_total` | boolean | false | 是否计算总数；有成本 |
| `need_aggregates` | boolean | false | 是否计算聚合；有成本 |
| `field_semantics` | object[] | `[]` | 契约下发的字段语义，用于合法排序/聚合 |
| `group_by` | string/string[] | 空 | 分组字段 |
| `group_offset/group_limit` | integer | `0`/受控 | 分组窗口分页 |
| `group_page_size` | integer | 受控 | 每组记录页大小，后端有上限 |
| `group_page_offsets` | object | `{}` | 各组独立页偏移 |
| `need_group_total` | boolean | false | 是否计算分组总数 |

返回 `data`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `records` | object[] | 当前普通列表记录 |
| `next_offset` | integer/null | 下一页记录偏移 |
| `total` | integer | 仅 `need_total=true` |
| `aggregates` | object | 仅请求聚合时 |
| `group_summary` | object[] | 分组摘要、label/count/domain |
| `grouped_rows` | object[] | 分组样本和组内分页数据 |
| `group_paging` | object | 分组窗口 identity、前后偏移、fingerprint/digest |
| 信封 `meta.record_scope/project_scope` | object | 后端应用的业务范围证据；不在 `data` 记录数组内 |

分组继续加载时应原样保留 `group_paging.window_identity/query_fingerprint/window_digest` 所对应的
查询条件。搜索、domain、排序或上下文变化后必须新建查询窗口，不能沿用旧 offset。

#### read/default_get/count

```json
{ "op": "read", "model": "project.project", "ids": [42], "fields": ["id", "name"] }
```

| op | 必要参数 | 返回 `data` |
| --- | --- | --- |
| `read` | `model/ids/fields` | `{records: object[]}` |
| `default_get` | `model/fields/context` | `{record: object}` |
| `count` | `model/domain/context` | 计数载荷 |

#### create/write

```json
{
  "intent": "api.data",
  "params": {
    "op": "write",
    "model": "project.project",
    "ids": [42],
    "vals": { "name": "新名称" },
    "if_match": "2026-08-27 10:00:00",
    "context": {}
  }
}
```

| op | 参数 | 返回 |
| --- | --- | --- |
| `create` | `model/vals/context` | `{id}` |
| `write` | `model/ids/vals/context/if_match?` | `{ids}` |

`if_match` 用于并发写保护；冲突时刷新记录/契约并让用户确认，不覆盖他人更新。

### 8.2 `api.data.write` / `api.data.create`

显式写接口支持更完整的幂等元信息：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `model` | string | 必填 |
| `id` / `ids` | integer/integer[] | 更新目标；创建时省略 |
| `values` / `vals` | object | 写值 |
| `context` | object | 当前业务上下文 |
| `if_match` | string | 并发版本 |
| `request_id` | string | 请求身份 |
| `idempotency_key` | string | 重放去重键；缺省可由 request ID 提供 |
| `dry_run` | boolean | 仅验证，不提交 |

更新返回：`id/model/written_fields/values`，并附幂等状态；创建返回新记录身份。

### 8.3 `api.data.unlink`

```json
{
  "intent": "api.data.unlink",
  "params": {
    "model": "project.project",
    "ids": [42],
    "request_id": "req-...",
    "idempotency_key": "delete-project-42-...",
    "dry_run": false,
    "context": {}
  }
}
```

返回 `data.ids/model/dry_run` 和幂等信息。删除前必须遵守 `actionContract.deletePolicy`；
不能仅凭前端按钮可见就调用删除。

### 8.4 `api.onchange`

请求：

```json
{
  "intent": "api.onchange",
  "params": {
    "model": "project.project",
    "res_id": 42,
    "values": { "partner_id": 7, "name": "项目 A" },
    "changed_fields": ["partner_id"],
    "context": {}
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `model` | string | 是 | 当前模型 |
| `res_id` | positive integer | 编辑态 | 创建态省略 |
| `values` | object | 是 | 当前表单快照，不只是变更字段 |
| `changed_fields` | string[] | 是 | 本次触发字段；兼容别名 `changed` |
| `context` | object | 否 | 当前上下文 |

返回：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `schema_version` | string | 当前 onchange 载荷为 `v1` |
| `patch` | object | 字段值补丁 |
| `modifiers_patch` | object | 字段 readonly/required/domain 等状态补丁 |
| `line_patches` | array | x2many 行补丁，含 row key/id/state/command hint |
| `warnings` | array | 标题、消息、reason code |
| `applied_fields` | string[] | 后端实际处理的触发字段 |

应用顺序建议：值 patch -> x2many line patch -> modifier patch -> warnings。响应到达前若表单上下文
epoch 已变化，应丢弃旧响应。不要把 onchange 结果当作已保存事实。

### 8.5 `execute_button`

请求字段见 7.5。仅支持单记录，按钮类型为 `object/action/server/server_action`。

返回：

```json
{
  "result": {
    "type": "refresh",
    "status": "success",
    "success": true,
    "reason_code": "OK",
    "res_model": "project.project",
    "res_id": 42
  },
  "effect": {
    "type": "reload_record"
  }
}
```

| `result.type` | 含义 |
| --- | --- |
| `refresh` | 按 `effect` 刷新记录或 action |
| `action` | 导航到标准化 action/entry target |
| `noop` | 成功但不需页面动作 |
| `dry_run` | 只完成授权/参数校验 |

`effect.type` 支持 `reload_record/reload_action/navigate/toast`。前端按 effect 执行，不读取后端
原始 action 后自行猜路由。

## 9. 页面级接入与交互流程

### 9.1 菜单栏（App Shell Navigation）

#### 9.1.1 唯一数据源

菜单栏只能使用 `system.init.data.navigation`：

```text
navigation.nav
  + navigation.route_authority
  + navigation.integrity
  + role_surface / record_context
  -> CanonicalNavigationModel
  -> App Shell 菜单栏
```

`navigation.nav` 决定可见树、名称、图标和顺序；`route_authority` 决定某个菜单动作是否能被
当前用户、公司、角色和记录上下文打开。两者必须精确配对，不能只渲染 `nav` 后直接信任 URL。

#### 9.1.2 菜单节点字段

| 字段 | 类型 | 用途 |
| --- | --- | --- |
| `key` | string | 节点稳定键；优先来自 XML ID/canonical carrier |
| `id/menu_id` | integer | Odoo 菜单身份；合成节点可能没有真实 menu ID |
| `name/label/title` | string | 服务端显示名，前端不改写业务名称 |
| `sequence` | integer | 同级排序 |
| `xmlid/xml_id` | string | 稳定来源身份，主要用于诊断 |
| `icon/web_icon` | string/null | 图标表达 |
| `action/meta.action_id` | integer | 目标 window action |
| `meta.model` | string | 目标模型，不作为组件选择器 |
| `meta.view_modes` | string[] | action 支持的视图模式 |
| `meta.domain/context` | mixed | 后端 action 条件，作为 opaque/结构化参数传递 |
| `children` | node[] | 子菜单 |
| `canonical_navigation` | object | 节点状态、路由、父链和 authority 的正式 carrier |

`canonical_navigation` 关键字段：

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `schema_version` | `1.0` | 非此版本应失败关闭 |
| `key/menu_id/action_id/label` | mixed | 必须与外层树节点完全一致 |
| `parent_chain` | array | 必须与实际树路径一致 |
| `route` | string/null | 必须与 route authority 相同 |
| `state` | `enabled\|disabled\|container` | action 节点为 enabled，纯分组为 container |
| `disabled_reason` | string/null | disabled 时必填 |
| `authority` | object | `allowed` 或 `container`，含来源和权威键 |
| `order` | number | canonical 排序值 |

#### 9.1.3 Route authority

`navigation.route_authority` 顶层字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `contract_version/schema_version` | `2.0.0` | 必须严格匹配 |
| `principal_scope` | object | `user_id/company_id/role_code`，必须与当前 session 一致 |
| `primary_actions` | array | 正式主导航动作 |
| `role_home_actions` | array | 角色首页动作 |
| `contextual_actions` | array | 依赖公司/项目/记录上下文的动作 |
| `admin_actions` | array | 管理入口 |
| `denied_actions` | array | 显式拒绝项，用于诊断而非渲染可用入口 |
| `menu_containers` | array | 无 action 的菜单容器 |

每条 authority entry：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `route_kind` | enum | PRIMARY_NAV、ROLE_HOME_ACTION、CONTEXTUAL_ROUTE、ADMIN_ROUTE 等 |
| `menu_id/menu_xmlid` | mixed | 菜单身份 |
| `action_id/action_xmlid` | mixed | 动作身份 |
| `name/model/view_modes/view_id` | mixed | 目标 action 描述 |
| `domain/context` | string | Odoo action 原始语义；前端只传递 |
| `route/scene_key` | string | 正式前端路由/scene |
| `entry_target` | object | 标准化下一页面目标，优先级高于前端拼接 |
| `allowed_operation` | string | 允许的打开操作 |
| `required_capability` | string | 已由后端用于裁剪的能力标识 |
| `context_requirements` | object | 必须存在且匹配的 query/company/record 条件 |
| `source` | string | 权威来源 |

#### 9.1.4 渲染与点击流程

1. `system.init` 成功后，校验 `navigation.integrity.missing_authority_count === 0`。
2. 校验 route authority 的 `principal_scope` 与当前 user/company/role 完全一致。
3. 将 `navigation.nav` 与 route authority 按精确 `menu_id + action_id` 建立 canonical model。
4. `container` 节点只负责展开/折叠；无 action 且无 children 的节点视为契约错误。
5. `disabled` 节点展示 `disabled_reason`，不触发导航。
6. 点击 `enabled` 节点时，从 authority 取得 `route/entry_target/domain/context`。
7. 校验 `context_requirements`，再跳转正式 scene 或 action route。
8. 页面加载失败时保留 trace ID，不回退到猜测 model/URL。

侧边栏 active anchor 的优先级：

1. 当前路由显式 `menu_id`；
2. 页面/scene 契约 `nav_ref.active_menu_id`；
3. `active_scene_key` 在 canonical navigation 中对应的菜单。

同模型导航可以按后端 entry target 继承合法筛选/分组上下文；跨模型导航必须清除来源页面的
业务筛选、分类、分页和 action/menu 状态，只保留目标明确给出的 query。

### 9.2 列表页

#### 9.2.1 初始化链路

```text
菜单 authority / route query
  -> ui.contract.v2(op=action_open)
  -> layoutContract + searchContract + dataContract + status/actionContract
  -> api.data(op=list)
  -> 通用集合渲染器
```

标准步骤：

1. 从 route authority 取得 `action_id/menu_id/view_type/domain/context`。
2. 请求 `ui.contract.v2`，不得先请求业务数据再猜列。
3. 从 `layoutContract.listProfile`、容器树和字段描述建立列、卡片或其他集合 presentation。
4. 从 `searchContract` 建立搜索、筛选、分组、收藏和默认排序。
5. 从 `dataContract.dataMeta.visibleFields` 取得允许读取的字段集合。
6. 合并 action domain、当前合法筛选和记录上下文，调用 `api.data(op=list)`。
7. 用 `statusContract/actionContract` 决定工具栏、行操作和批量操作状态。

#### 9.2.2 列表页状态

| 状态 | 触发条件 | UI 行为 |
| --- | --- | --- |
| `loading_contract` | 页面契约未返回 | 页面骨架；禁止业务操作 |
| `contract_error` | V2 解码失败 | 契约错误页，展示 trace ID |
| `loading_data` | 契约有效、数据查询中 | 保留列结构并显示 loading |
| `ready` | 有记录 | 渲染记录、分页和已授权动作 |
| `empty` | 查询成功且 records 为空 | 显示空状态；创建按钮仍由 action/status 决定 |
| `permission_denied` | 403/状态拒绝 | 权限空状态，不伪装成无数据 |
| `query_error` | 数据查询失败 | 可重试错误；保留当前筛选条件 |

#### 9.2.3 列与行

- 列顺序以契约为基础，用户个人列偏好只能在权威列集合内重排/隐藏；
- 用户列偏好通过 `user.view.preference.get/set` 保存，不得改变共享业务配置；
- `visible_columns/hidden_columns/column_order/column_widths` 都必须过滤掉契约中不存在的字段；
- 单元格类型来自字段 descriptor/component key，不按字段名推断金额、状态或关系；
- 行点击目标来自正式 action/entry target；没有详情 authority 时行不可点击；
- 行操作必须消费对应 action rule 和 button status；批量操作还要验证选中记录范围。

#### 9.2.4 分页与分组

- 普通分页使用 `limit/offset/next_offset`；查询条件变化后 `offset=0`；
- 分组分页使用 `group_offset/group_limit/group_page_offsets`；
- 后续请求必须绑定同一 `query_fingerprint/window_id/window_digest` 语义；
- 切换 `domain/search/order/group_by/context` 任一项都创建新窗口；
- 不把前端当前可见行数当作总数，只有 `need_total=true` 的 `total` 才是总数事实。

### 9.3 筛选页与搜索面板

“筛选页”是列表页面的契约驱动搜索表面，不是独立维护业务查询规则的前端页面。

#### 9.3.1 输入、状态与输出

| 来源 | 输入 | 输出到 `api.data` |
| --- | --- | --- |
| `searchContract.fields` | 用户搜索值 | 结构化 domain / `search_term` |
| `filters` | 预定义过滤器 | domain 片段 |
| `saved_filters` | 用户/共享收藏 | domain + context + order |
| `group_by` | 分组选择 | `group_by` |
| `default_sort/default_order` | 默认排序 | `order` |
| `search_panel` | 分类/层级选择 | 结构化 domain |
| route authority | action domain/context | 基础 domain/context，不可被用户筛选覆盖 |
| `record_context` | 公司/项目/经营方式 | request context 和后端记录范围 |

合并原则：

```text
最终查询 = 后端 action/route 基础约束
         AND 当前记录上下文约束
         AND 用户选择的合法筛选
```

前端可以组合用户筛选，但不能删除或覆盖后端基础 domain、公司范围或记录规则。

#### 9.3.2 URL 状态

建议只把可序列化的展示状态写入 URL，例如：

- `search/q`：搜索词；
- `active_filter/saved_filter`：筛选身份；
- `group_by/group_value`：分组状态；
- `group_offset/group_page`：分页状态；
- `menu_id/action_id`：当前权威入口。

URL 中的字段只是恢复提示。每次恢复都必须重新与当前 `searchContract`、route authority 和
principal scope 校验；不能因为 URL 中存在某个 filter/group 就直接信任。

#### 9.3.3 保存筛选 `search.favorite.set`

```json
{
  "intent": "search.favorite.set",
  "params": {
    "model": "project.project",
    "name": "我的在建项目",
    "domain": [["stage_id", "!=", false]],
    "context": {},
    "order": "name asc",
    "action_id": 120,
    "is_default": false,
    "is_shared": false
  }
}
```

| 参数 | 规则 |
| --- | --- |
| `model/name` | 必填；名称最长 80 字符 |
| `domain` | 必须为数组，服务端写入 Odoo `ir.filters` |
| `context` | 必须为对象 |
| `order` | 当前排序 |
| `action_id` | 将收藏限制在当前 action，避免跨页面污染 |
| `is_default` | 同一 model/user/action 仅保留一个默认项 |
| `is_shared` | 客户端不能自行提升为共享；服务端策略最终裁决 |

返回 `id/name/model/is_shared/is_default/action_id/search_version`。保存成功后重新加载搜索契约或
收藏列表，不在浏览器中构造一份长期平行事实。

### 9.4 详情页

#### 9.4.1 三种模式

| 模式 | 请求 | 数据来源 | 主要动作 |
| --- | --- | --- | --- |
| 创建 | `view_type=form, render_profile=create`，无 record ID | `dataContract.mainData` / `api.data default_get` | create、onchange、取消 |
| 编辑 | `record_id, render_profile=edit` | 记录绑定契约 + 主记录快照 | write、onchange、业务按钮 |
| 只读 | `record_id, render_profile=readonly` | 记录绑定契约 | 导航、审批、附件、chatter 等已授权动作 |

`render_profile` 是请求意图，最终模式以 `statusContract.globalStatus.effectiveRenderProfile`、模型/记录
权限和 widget status 为准。前端不得通过改 URL 强制进入 edit。

#### 9.4.2 初始化

1. 从列表行的正式 entry target 或菜单 authority 取得 model、record/action/menu。
2. 请求记录绑定的 `ui.contract.v2`。
3. 严格解码，并建立 widget/action/status 索引。
4. 使用 `formStructureContract.presentationMode` 选择 task/workspace 通用 presenter。
5. 将 `dataContract.mainData` 作为初始 record snapshot；缺失字段按契约数据源补充读取。
6. 保存 `data.meta.etag/snapshotId/requestId` 作为刷新和诊断身份。

#### 9.4.3 字段交互

| 事件 | 前端动作 | 后端权威 |
| --- | --- | --- |
| focus/blur | 本地输入体验；若 action rule 声明则分发 | action rule |
| change/select | 更新 draft，按 rule 调 `api.onchange` | Odoo onchange/model |
| relation search | 使用 relation entry/data source | relation model ACL/domain |
| x2many add/edit/remove | 本地形成 command draft，应用 line patch | relation contract + onchange |
| upload/download | 调用 file intent | `ir.attachment` 与记录规则 |
| chatter/activity | 调用 chatter/activity intent | mail/thread/activity 权限 |
| submit/save | 先校验状态，再调用 create/write | ORM、ACL、record rule、业务约束 |

字段显示顺序：原生 container occurrence -> form structure slot/group -> widget status。不得把
`fieldRoles` 当作重新排序并删除原生 occurrence 的许可。

#### 9.4.4 Onchange 竞态处理

每次 onchange 建议维护递增 request sequence：

1. 捕获当前 context epoch、record ID、changed fields 和 draft revision；
2. 发送完整 `values` 快照；
3. 响应返回时验证 epoch/record/revision 仍匹配；
4. 只应用最新有效响应；
5. 按 patch -> line patches -> modifiers -> warnings 更新；
6. modifiers 改变 readonly/required 后重新计算本地校验，但不提交数据。

#### 9.4.5 保存与离开

- 创建成功后使用后端返回 ID 重载 edit/readonly 契约，不把 create 契约继续用于新记录；
- 更新成功后按 `refreshMode/effect` 选择局部记录刷新或完整契约刷新；
- 记录 write_date/ETag 冲突时保留用户 draft，提示重新加载与人工合并；
- 有未保存 draft 时，页签切换、菜单跳转和浏览器离开应触发统一 dirty confirm；
- 业务按钮可能隐式改变记录状态，执行成功后必须刷新 record-bound contract。

### 9.5 增删改查（CRUD）交互矩阵

| 操作 | 前置裁决 | Intent | 核心参数 | 成功后 |
| --- | --- | --- | --- | --- |
| 查列表 | route + read ACL + visible fields | `api.data` | `op=list/model/fields/domain/context` | 更新集合数据和分页 |
| 查详情 | detail authority + read ACL | `ui.contract.v2` / `api.data` | model/record/action/menu | 建立记录绑定页面 |
| 新增 | create capability + create profile | `api.data` 或 `api.data.create` | `op=create/model/vals/context` | 用新 ID 重载详情；列表失效 |
| 修改 | edit status + write ACL + record rule | `api.data` 或 `api.data.write` | ids/vals/if_match/context | 刷新记录契约；相关列表失效 |
| 删除 | `deletePolicy` + delete action/status | `api.data.unlink` | model/ids/request/idempotency/context | 关闭详情或移除行并重新计数 |

#### 9.5.1 创建

1. 先加载 create 契约和 defaults；
2. 只提交契约允许、用户实际编辑或后端要求的字段；
3. relation/x2many 使用 Odoo command 语义的受控适配器；
4. create 返回 ID 后清理临时 draft/cache key；
5. 加载新记录的 record-bound 契约，再决定后续按钮和状态。

#### 9.5.2 更新

1. 从当前 draft 与服务器 snapshot 计算待提交字段；
2. 排除 readonly/invisible 且非后端 onchange 产生的非法修改；
3. 携带 `if_match/write_date`；
4. 成功后以服务端重读结果覆盖本地 snapshot；
5. 若状态/权限/结构可能变化，重新加载整个 V2 契约。

#### 9.5.3 删除

1. 读取 `actionContract.deletePolicy` 与删除 action/status；
2. 显示后端确认文案和影响范围；
3. 生成稳定 `request_id/idempotency_key`；
4. 可先 `dry_run=true` 做授权与范围检查；
5. 正式删除成功后使列表、分组计数、详情页和 relation cache 失效；
6. 部分失败时逐项展示 reason code，不能把整批标为成功。

### 9.6 审批交互逻辑

#### 9.6.1 权威分层

| 层 | 权威 | 前端职责 |
| --- | --- | --- |
| 审批运行时 | Odoo/OCA `base_tier_validation`、`tier.review`、业务模型状态与方法 | 展示当前状态和可执行动作 |
| 审批配置 | `sc.approval.policy/sc.approval.step` | 配置管理员编辑；它是友好配置和同步入口 |
| 用户授权 | groups、ACL、record rules、模型 capability helper | 消费 `allowed/authorization_allowed`，不按角色名放权 |
| 页面动作 | V2 action/status 或业务 available-actions contract | 渲染确认、原因输入、按钮层级 |
| 执行 | 语义 execute intent / `execute_button` | 原样传 action identity、记录和幂等信息 |

`sc.workflow.*` 不应成为新的平行审批运行时。新接入优先消费 tier validation 和正式业务模型
动作；审批 policy 只负责配置并同步运行时定义。

#### 9.6.2 通用审批状态流

```text
草稿/被驳回
  -> 提交审批
  -> 待审批（一个或多个 tier review）
  -> 审批通过 -> 已批准/待办结
  -> 驳回 -> 被驳回 -> 修改后重新提交
  -> 业务完成/执行（若模型定义）
```

具体状态值由业务模型拥有，前端不能假定所有模型都叫 `draft/submit/approved/rejected/done`。
前端只显示契约给出的 label、current state、next-state hint 和 reason code。

#### 9.6.3 可用动作载荷

正式业务审批可通过 `actionContract`，也可以有领域 available-actions intent。领域动作行至少应按
以下语义消费：

| 字段 | 说明 |
| --- | --- |
| `key/label` | 动作身份和显示名 |
| `intent/execute_intent/execute_params` | 正式执行入口与基础参数 |
| `allowed` | 业务前提和授权共同通过 |
| `business_available` | 当前状态、模型方法和业务前提通过 |
| `authorization_allowed` | 当前用户授权通过 |
| `entitlement_evaluated` | 后端已完成授权评估，必须为 true |
| `reason_code/blocked_message` | 不可执行原因 |
| `required_params/requires_reason` | 额外输入，例如驳回原因 |
| `idempotency_required` | 是否必须携带幂等键 |
| `actor_matches_required_role` | 当前操作者是否满足能力；仍不是客户端授权来源 |
| `handoff_required/handoff_hint` | 当前用户不能执行时的交接提示 |
| `presentation` | primary/secondary/destructive、确认要求等展示语义 |
| `advisory_warnings` | 非阻断建议；force-block 结果由后端反映到 allowed |

审批按钮显示规则：

```text
visible = 契约声明可见
enabled = allowed === true
       && authorization_allowed === true
       && entitlement_evaluated === true
       && 对应 status.disabled === false
```

缺少任一权威字段时失败关闭。`required_role_key/label/group_xmlid` 用于解释和交接，不用于前端
自行把 `allowed` 改为 true。

#### 9.6.4 审批执行顺序

1. 进入详情页后加载记录绑定契约和最新 available actions。
2. 用户点击动作时再次检查 action/status/allowed；不要使用列表加载时的旧动作快照。
3. 若 `requires_reason=true`，打开原因输入对话框并校验非空。
4. 若 `presentation.requires_confirmation=true`，显示确认文案、目标记录和可能警告。
5. 生成 `request_id/idempotency_key`，调用契约指定 execute intent。
6. 禁用同一动作，防止重复提交；超时后先查状态/幂等结果，不直接重放。
7. 成功后展示 effect/message，重新加载记录契约、审批动作、chatter/activity 和相关列表。
8. 失败时按 reason code 展示业务前提、权限、记录范围或系统错误，保留用户填写的原因。

付款申请是现有领域示例，不是平台硬编码模板：

| 动作 | 示例状态 | 额外要求 | 能力提示 |
| --- | --- | --- | --- |
| submit | draft/rejected | 合同与阻断检查通过 | 财务提交；rejected 时显示“重新提交审批” |
| approve | submit | tier validation 状态允许 | 管理层审批 |
| reject | submit | 必填 `reason` | 管理层驳回 |
| done | approved | validation 已通过；付款类可能要求先生成付款执行 | 财务办结 |

调用形式：

```json
{
  "intent": "payment.request.execute",
  "params": {
    "id": 42,
    "action": "reject",
    "reason": "资料不完整",
    "request_id": "approval-reject-42-...",
    "idempotency_key": "approval-reject-42-..."
  }
}
```

领域 handler 会再次检查记录存在、读写权限、记录范围、业务状态、模型方法和操作能力。前端即使
篡改 action 或角色字段也不能获得权限。

#### 9.6.5 审批配置与业务审批必须分开

- `sc.approval_policy.config.get`：读取某业务模型是否需要审批、模式和运行时同步状态；
- `sc.approval_policy.config.set`：业务配置管理员启停审批；
- `sc.approval_policy.steps.set`：保存步骤、岗位、金额区间和顺序，并同步 tier definitions；
- 配置写入必须由业务配置管理员/平台管理员执行；
- 普通审批人不应看到配置写入口；
- 配置成功后不代表当前记录自动通过或自动迁移状态，记录仍遵循审批运行时。

### 9.7 角色对应渲染

#### 9.7.1 原则

角色决定“后端给当前主体返回什么”，不决定“前端自己推导什么”。渲染输入分四层：

| 层 | 契约 | 影响 |
| --- | --- | --- |
| Shell | `role_surface + navigation` | 默认落点、可见菜单、角色首页 |
| Route | `route_authority.principal_scope` | 当前主体可打开的 action/scene |
| Page | `statusContract + actionContract` | 字段、容器、按钮和记录能力 |
| Domain | available actions/work items | 审批、交接和业务动作 |

#### 9.7.2 `role_surface`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `role_code/primary_role_code` | string | 当前主角色 |
| `role_codes` | string[] | 当前主体的角色集合 |
| `role_label/role_labels` | string/string[] | 后端显示名 |
| `multi_role` | boolean | 是否多角色 |
| `landing_scene_key` | string | 默认 scene |
| `landing_menu_id/landing_menu_xmlid` | mixed | 默认菜单锚点 |
| `landing_path` | string | 默认路径 |
| `scene_candidates` | string[] | 当前角色候选 scene |
| `menu_xmlids` | string[] | 当前角色菜单候选 |

`role_surface_map` 是服务端提供的角色摘要，用于角色切换展示或诊断。不能用它在客户端重建
菜单、字段权限或审批动作。

#### 9.7.3 渲染规则

- App Shell 只渲染 `navigation.nav` 已裁剪的节点；不再按 role code 过滤一次；
- 首页标题、描述、区块和指标来自 workspace/page contract，不建立 `role -> 文案` 字典；
- 同一 model 对不同角色可能返回不同 status/actions/form structure，通用 renderer 只按当前快照渲染；
- 审批按钮依据 action entitlement，不因 `role_code=executive` 就自动出现；
- 多角色用户仍只有一个当前 principal scope；不能把多个角色的 authority 合并放大；
- 缺少角色专属契约时显示通用安全空状态，不补写业务入口。

#### 9.7.4 角色/公司/上下文切换

切换后必须视为新 principal：

1. 使旧请求 context epoch 失效；
2. 清理 navigation、route authority、page contract、数据和 available-actions 缓存；
3. 使用新会话/公司上下文重新调用 `system.init`；
4. 校验新的 `principal_scope`；
5. 按新 `default_route/landing_scene_key` 导航；
6. 当前详情若新主体无权限，关闭页面并显示授权变化，而不是保留旧页面。

### 9.8 端到端页面闭环

```text
system.init
  -> 菜单栏 + principal route authority
  -> 点击菜单
  -> ui.contract.v2(action/model)
  -> 列表：searchContract -> api.data.list
  -> 行 entry target
  -> 详情：record-bound contract
  -> onchange / create / write / unlink / execute
  -> 审批或业务状态变化
  -> 重新加载 contract + data + actions
```

每次跨页面必须携带并核对 `trace_id`、action/menu identity、record context 和 principal scope。
页面闭环的正确完成标准不是“按钮点击成功”，而是后端提交成功后，新契约、新数据、新状态和
相关列表均已收敛到同一记录事实。

## 10. `frontend/apps/web` 当前渲染逻辑

本节不是另起一套设计，而是把 `frontend/apps/web` 当前运行代码如何消费上述契约说明清楚。
接入新页面时应沿用这些公共入口；若页面表现与本节不一致，应先判断是契约缺失、解码失败、
renderer 未注册，还是页面绕过了公共运行时。

### 10.1 渲染分层与代码入口

```text
ui.contract.v2 response
  -> schema.ts：legacy layout 结构归一 + 严格解码
  -> store.ts：按稳定 identity 建索引
  -> 页面语义解析
       列表：ActionView -> collection presentation -> renderer registry
       详情：ContractFormPage -> presenter -> CanonicalFormRenderModel
  -> Vue renderer host / field component
  -> 用户事件
  -> data / onchange / execute_button intent
  -> 刷新数据与契约
```

| 层 | 当前入口 | 责任 | 不承担的责任 |
| --- | --- | --- | --- |
| 契约加载 | `app/contracts/v2/client.ts` | 组装 action/model 参数、声明客户端能力、调用 `ui.contract.v2` | 不渲染、不推断权限 |
| 严格解码 | `app/contracts/v2/schema.ts` | 校验枚举、boolean、必填对象、occurrence authority；错误聚合到具体 path | 不静默修补非法业务事实 |
| 标准化 store | `app/contracts/v2/store.ts` | 建立 widget/action/status/container 索引和值源解析器 | 不把多 occurrence 强行合并 |
| 集合语义 | `app/contracts/actionViewSurfaceContract.ts` | 归一 view mode，解析 table/card/workflow/advanced 语义 | 不直接选择 Vue 组件 |
| 集合 renderer | `app/renderers/actionSurfaceRendererRegistry.ts` | 把 semantic 映射到 renderer、outlet、ready/fallback/unsupported | 不按 model 或菜单名分支 |
| 集合宿主 | `components/action/ActionSurfaceRendererHost.vue` | component outlet 动态挂载；standard outlet 使用默认 slot | 不掩盖 unsupported reason |
| 详情 presenter | `app/presentation/contractFormPresenter.ts` | 合并结构、值、状态、组件和动作，生成内存 ViewModel | 不生成 API payload，不持久化 |
| 字段 registry | `app/presentation/professionalComponentRegistry.ts` | 校验 component key、field type、模式、profile、adapter version | 不猜测未知组件 |
| 详情宿主 | `pages/ContractFormPage.vue`、`contractForm/ContractFormDriverHost.vue` | 维护 runtime value、动作执行、关系字段、保存和刷新 | 不在失败时重新启用旧产品渲染链 |
| 节点渲染 | `contractForm/CanonicalFormNodeRenderer.vue` | 递归渲染可见节点、字段、节点动作与只读事实布局 | 不重新计算授权 |

`CanonicalFormRenderModel` 在类型定义中被明确标注为临时内存 ViewModel。它不是接口返回、
缓存格式或新的版本化协议，不能把它提交给后端，也不能要求后端按这个结构输出。

### 10.2 契约加载、解码与标准化

`loadActionContractV2` 使用 `op=action_open`；`loadModelContractV2` 使用 `op=model`。公共加载器会补入：

- `delivery_profile=full`；
- `client_type=web_pc`；
- `accepted_contract_versions=[2.0.x,2.1.x,2.2.x]`；
- 当前支持的 container、data source、action rule、relation entry、status 和 children-owner 能力；
- route 中合法的 action/menu/view/record/scene/context 与 preview identity。

create profile 且无 record/preview 时，客户端按数据库、token、context epoch 和完整参数建立
30 秒、最多 16 项的内存缓存。命中缓存时会深拷贝 snapshot 并重新创建 store，页面不能依赖
前一次渲染留下的对象引用。编辑、只读记录和 preview 不走这项 create 缓存。

解码顺序为：legacy layout 结构归一，然后分别解码 `pageInfo/layoutContract/statusContract/
actionContract/dataContract/runtimeContract/meta`，再解码可选的 form/search/workflow 合同，最后校验
form occurrence authority。任一 issue 都会抛出 `ContractV2DecodeError`，其中包含 `path + message`；
页面必须显示失败态和 trace ID，不能继续使用部分对象。

store 的关键索引如下：

| 索引 | key | 使用注意 |
| --- | --- | --- |
| `widgetsById` | `widgetId` | widget occurrence 的主索引 |
| `widgetsByFieldCode` | `fieldCode` | 只适合明确单 occurrence 的快捷读取 |
| `widgetsByFieldCodeAll` | `fieldCode` | 同字段多 occurrence 必须读这里 |
| `widgetsByOwnerContainerId` | `ownerContainerId` | 详情节点递归渲染的字段来源 |
| `actionsById` | `actionId` | action plan 查找 |
| `widgetStatusById` | `widgetId` | 字段 occurrence 状态 |
| `buttonStatusById` | `btnId` | 动作状态 |
| `containerStatusById` | `containerId` | 节点可见/禁用状态 |

值源优先级是：能覆盖契约字段的 `dataContract.mainData`，其次是 primary data source；若二者都
没有字段覆盖，再选择非空对象。详情页不得因为某个值为 `false` 就误判“值源为空”；boolean
的 `false` 是有效值。

### 10.3 列表、卡片与高级视图选择

`ActionView` 先汇总契约 view type、action meta view modes 和 snapshot view type，过滤 `form`、
去重并把 `list` 归一为 `tree`。可渲染 mode 只有：`tree/kanban/pivot/graph/calendar/gantt/
activity/dashboard`；未知 mode 返回空值并进入明确失败/空态，而不是随意选组件。

第二步把 mode 转为 collection semantic：

| mode / 契约条件 | semantic | 页面表现 |
| --- | --- | --- |
| `tree`，无正式层级 presentation | `table` | `ListPage` |
| `tree` 且 `collection_presentation.enabled=true`，semantic 为三个正式层级类型之一 | `hierarchy_browser` / `hierarchy_planner` / `hierarchical_worksheet` | 专用 component outlet |
| `kanban` 且 semantic=`workflow_board`、有合法 group_field、`grouped_lanes=true` | `workflow_board` | 分组流程看板 |
| `kanban` 但条件不完整 | `card` | 普通 `KanbanPage` |
| 普通 card 页面附带合法 `group_by` route 参数 | `workflow_board` | 运行时分组看板 |
| `pivot/graph/calendar/gantt/dashboard` | 同名 semantic | 当前使用可读记录降级 |
| `activity` | `activity` | 原生活动 surface |

renderer registry 的当前事实：

| semantic | active renderer | outlet | 状态/意图 |
| --- | --- | --- | --- |
| table/card/workflow_board | `core.standard_collection` | standard | ready，复用 `ActionView` 默认 slot |
| hierarchy_browser | `core.hierarchy_browser` | component | ready |
| hierarchy_planner | `core.hierarchy_planner` | component | ready |
| hierarchical_worksheet | `core.hierarchical_worksheet` | component | ready |
| activity | `core.activity` | standard | ready |
| pivot/graph/calendar/gantt/dashboard | `core.readable_records` | standard | fallback，附 `RENDERER_*_PLANNED` reason |
| 未注册 semantic | `core.unsupported` | component | unsupported，`ACTION_SURFACE_RENDERER_NOT_REGISTERED` |

`ActionSurfaceRendererHost` 会把 requested/active renderer、semantic 和 status 写入 data attribute，
便于自动化测试和现场排障。只有 `outlet=component` 才从 component map 动态挂载；否则渲染
standard slot。fallback 表示“仍可读、可下钻”，不代表伪造出尚未实现的透视/图表交互。

table 还有一条受控 scene collection 桥接：只有只读桥接成功且 driver policy 判定 eligible 时，
才启用 `core.scene_collection`。被定向的场景若 V2 标准化缺失或 adapter 拒绝，会进入
`core.unsupported`；产品路由不会悄悄回到普通表格来掩盖契约错误。

### 10.4 列表数据、筛选和工具栏如何渲染

`ActionView` 的加载前置流程按以下顺序执行：

1. 从 list profile 和契约提取/收敛列；从 kanban/advanced profile 提取专用字段；
2. 根据当前 mode 计算 requested fields，tree 没有契约列时直接阻断；
3. 合并 scene domain、route/用户 filter domain 和 group 条件；
4. 合并 action meta context、route context 和有效请求 context；
5. primary data source 的 `domain_raw/context_raw/domain/context` 只在对应请求值缺失时补入，
   其中结构化 context 按“data source 在前、当前请求在后”合并；
6. 调用 list data intent；成功后再收敛列、记录、聚合、分页和分组窗口。

kanban 契约未提供字段时会记录 warning，并以 list/profile 字段做可读 fallback；tree 缺列则是
阻断错误。这种差异是有意的：卡片可从正式列表字段退化展示，表格没有列定义则无法保证列
顺序、标签和字段权限。

默认 standard outlet 的主要渲染关系：

- `vm.content.kind=list` -> `ListPage`：列顺序/宽度/显隐、分页、排序、选择、批量动作、分组行；
- `vm.content.kind=kanban` -> `KanbanPage`：标题/主次/状态/指标字段与 workflow board 分组；
- `viewMode=activity` -> `ActivityPage`；
- 其他 advanced mode -> 可读记录列表，显示 title/hint、配置摘要和核心记录，并保留下钻能力。

工具栏只呈现契约和运行时 capability 允许的入口：视图切换、搜索、快速筛选、收藏筛选、
排序、分组、自定义筛选/分组和保存收藏。条件变化通过 route state 同步并触发 reload；分页 offset、
group window 和 drilldown identity 必须随查询指纹重置。route preset、standalone chips 和 toolbar
是同一筛选状态的不同 presentation，不能各自维护一份 domain。

新建入口只有 `canCreateRecord` 为真才显示。若正式办理类型多于一个且 route 未给默认类型，先弹
办理类型选择；选定后进入 `/f/<model>/new` 并携带 canonical create query，而不是在列表本地创建行。

### 10.5 详情页 canonical form 渲染链

详情页面的运行链如下：

```text
V2 normalized store + renderProfile + reactive formData
  -> resolveCanonicalFormRenderState
  -> presentContractV2Form
  -> CanonicalFormRenderModel
  -> composeCanonicalFormFloorplan
  -> ContractFormDriverHost
  -> CanonicalFormNodeRenderer（递归）
  -> FormSection / professional field control
```

若存在 decode error，render state 直接返回该错误；store 缺失返回
`NORMALIZED_FORM_CONTRACT_MISSING`；presenter 抛错则返回具体 reason。产品路由的 canonical renderer
始终是唯一渲染 authority，driver/contract 失败留在 canonical host 显示，不重新激活 legacy pipeline。

presenter 生成的模型分为：

| 区域 | 来源/作用 |
| --- | --- |
| `identity` | page/scene/model/view/mode/presentationMode 和源契约 SHA |
| `shell` | 标题、pageVisible、pageAuth、reasonCode |
| `actionBar` | 经授权、去重、primary resolution 后的 header/footer 动作 |
| `zones.primary` | 主业务事实容器 |
| `zones.subordinate` | `projection_only + no_business_fact_authority` 的从属投影容器 |
| `responsive` | adaptMode 和 layout hints |
| `componentTokens` | component registry 的只读快照 |

节点按 `containerTree` 递归。字段必须属于 `ownerContainerId` 对应节点；节点的 visible/disabled/
readonly 会向后代传递。form structure contract 若给出 field role、slot/group、标题、列数和字段标签，
其语义高于 widget/container 上的投影值。相邻重复容器标题会被消除，field 自身的 string/label
只作为控件标签，不重复当 section heading。

`CanonicalFormNodeRenderer` 只渲染 `visible && hasContent` 的节点。hasContent 包括：可见字段、文本、
节点动作、native widget、chatter/activity/attachment 或有内容的子节点。列数限制为 1~3；span 映射
为 1~4 个 grid span。只读页面若节点字段全为 readonly，可使用紧凑的事实布局；纯标点 native text
在该布局中会被过滤。

### 10.6 字段状态合并与组件映射

字段最终状态不是简单覆盖，而是失败关闭的合取：

| 输出 | 当前计算规则摘要 |
| --- | --- |
| `visible` | ancestor visible AND widget status 已解析 AND widgetStatus.visible 非 false AND selectorStatus.visible 非 false |
| `readonly` | readonly profile OR pageAuth 不可编辑 OR ancestor disabled/readonly OR authoritative slot readonly OR field auth 非 edit OR selector readonly OR status 未解析 OR widgetStatus.readonly |
| `required` | widgetStatus.required OR selectorStatus.required |
| `disabled` | ancestor disabled OR selectorStatus.disabled OR status 未解析 OR widgetStatus.disabled |
| `reasonCode` | widget status / selector reason；status 缺失使用 `WIDGET_STATUS_UNRESOLVED` |

page 是否可编辑要求：render profile 不是 `readonly`，且 `globalStatus.pageAuth` 为 `edit` 或 `admin`。
同一 fieldCode 有多个 occurrence 时，公共 field-status 汇总器只在 occurrence 唯一时按 fieldCode 输出；
渲染本身始终按 widgetId/ownerContainerId 处理。

值处理的几个容易踩坑点：

- runtime `formData` 中显式存在字段时优先于 contract value；
- many2one 统一投影为 `{id, displayName, model}`，控件提交 id、展示 displayName；
- 非 boolean 的 `false/null/undefined` 映射为空值，boolean `false` 保留；
- date/datetime 字符串 `"false"` 映射为空；
- monetary 会从配置指定的 currency field 读取当前 runtime/contract currency value。

专业组件必须先通过本地 registry，再通过契约 registry：

1. `componentKey` 必须注册且 readiness 不能是 `fail_closed`；
2. field type、presentation mode（task/workspace）、render profile（create/edit/readonly）必须受支持；
3. required capabilities 必须齐全；
4. `layoutContract.componentRegistry[componentKey]` 必须有 version；
5. 按 client type 选择 adapter，缺失时依次使用契约 fallback / web_pc；仍为空则失败关闭。

当前 renderer 覆盖基础文本、长文本、数字、boolean、selection、日期时间、binary、关系、明细集合、
money/currency/percentage/status/duration/user/company 等。基础字段可进一步映射到
`ProfessionalBaseFieldControl`，many2one/many2many 使用关系控件，one2many 使用明细集合控件，业务值
使用 business value 控件。未知 component key 或 type mismatch 必须显示明确错误，禁止退化成任意 input。

### 10.7 详情动作、审批按钮与执行映射

动作 presentation 同样失败关闭。一个动作要成为可见/可执行按钮，至少满足：

- `actionId` 和 `backendIdentity` 均存在且在当前 action list 中唯一；
- 能唯一解析对应 `buttonStatus`；
- `buttonStatus.visible/disabled` 是明确 boolean；
- `entitlementEvaluated=true`，且 `allowed/enabled/disabled` 均为明确 boolean；
- definition 没有 `visible=false/invisible=true`，当前 profile 在 `visibleProfiles` 中；
- status 没有隐藏；readonly profile 自动隐藏 `form.save`。

最终 `enabled = allowed && action.enabled && !action.disabled && !buttonStatus.disabled`。条件不完整时按钮
不被放权，并携带服务端 reason 或 `ACTION_NOT_ALLOWED`。role code、按钮文字、method 名称和 workflow
状态都不参与前端授权推断。

header/footer 候选动作还会应用 `primaryResolution.demoted`，并按后端 operation identity 去重；winner
优先，否则同 operation 取 `presentationPriority` 更高的 occurrence。最终允许至多一个 visible + enabled
的 primary，多个 primary 直接报 `CANONICAL_FORM_MULTIPLE_PRIMARY_ACTIONS`。

执行时只允许精确映射：

```text
actionId=form.save -> saveRecord
其他 action -> 用 backendIdentity 在现有 contractActions 中找唯一 adapter -> runAction
0 个 adapter -> CANONICAL_FORM_ACTION_EXECUTION_ADAPTER_MISSING
多个 adapter -> CANONICAL_FORM_ACTION_REFERENCE_AMBIGUOUS
identity 缺失 -> CANONICAL_FORM_ACTION_REFERENCE_MISSING
```

切换到 canonical renderer 前，会校验所有“可见且 enabled”的 header、footer、smart-button 和 body node
动作都有唯一执行 adapter；disabled 动作可继续展示服务端原因，不要求执行 adapter。审批提交因此走
与普通业务动作相同的 exact backend identity 链，成功后仍需重新加载 record contract、status、actions
和来源列表，不能仅在本地把审批状态改成下一步。

### 10.8 详情字段交互、onchange、保存与冲突

字段控件发出 change 后，页面先更新 reactive `formData` 并记录 dirty field。仅当契约 action rules
声明该字段需要 server onchange 时，才加入 changed set，并以 300ms debounce 调用 onchange：

```text
field change
  -> dirtyFieldSet
  -> changedFieldSet（仅 server onchange 字段）
  -> api_onchange(values + changed_fields + context)
  -> patch + modifiers_patch + line_patches + warnings
  -> 标准化字段值并原子应用
  -> canonical presenter 基于新 formData 重新计算 render model
```

应用 patch 时设置 `applyingOnchangePatch`，避免服务端补丁再次触发 onchange。补丁只接受契约字段；
many2one 同步 option 与 keyword，x2many 走命令/行状态标准化，readonly 字段按 descriptor 规则处理。
可选 onchange 失败时保留当前用户输入，不把表单清空；warnings 与 line patches 单独展示/处理。

保存只收集可见且可写字段。编辑已有记录时优先提交 dirty fields；create 提交完整必要值；x2many
分别生成 write/onchange 命令。若 runtime contract 启用 record version policy，write 携带当前
`ifMatch`/version token；冲突进入专用 conflict 状态，提示获取最新数据，不做覆盖式自动重试。

页面同时维护未保存离开保护：有 dirty 状态且当前不在 busy 时，route 离开需要确认。保存、动作或
关系记录跳转前应复用统一 guard/ensure-saved 流程，不能让某个专业控件绕开脏数据保护。

### 10.9 角色对应渲染的源码边界

角色影响渲染必须先经后端收敛为 navigation、route authority、global/widget/button/selector status、
action entitlement、entry capability 和业务 workspace 投影。前端 session 中的 role name/code 只能用于
身份展示、诊断或作为受控 preview 参数，不能直接执行：

```ts
if (roleCode === 'manager') showApproveButton(); // 禁止
```

正确的渲染顺序是：

1. `system.init` 决定该主体能看见和打开哪些菜单/route；
2. 页面 V2 contract 决定 pageAuth、字段 occurrence、按钮和 entry capability；
3. presenter/renderer 按明确 status 输出 UI；
4. execute intent 再由服务端对当前主体、公司和记录事实做最终授权。

scene UI driver 的 kit 选择也受 policy 控制。用户偏好仅在 `allowUserOverride` 为真且 kit 位于
`allowedKits` 时加载/保存；preview kit 和个人偏好都不能提升业务权限。角色/公司/context epoch 改变后，
应清除偏好以外的页面契约和数据状态，重新从 `system.init` 收敛。

### 10.10 新 renderer/字段组件的接入规则

新增渲染能力时至少完成以下闭环：

1. 在后端 Schema/handler 定义稳定 semantic 或 component key，不使用 model/menu/中文标题作为 key；
2. 更新 V2 type 与严格 decoder，使非法配置在渲染前失败；
3. 在 renderer 或 professional component registry 注册支持的 mode/profile/type/capability；
4. 为 ready、readable fallback、unsupported/fail-closed 分别定义 reason code 和测试；
5. 复用公共数据、onchange、动作 executor，不在组件内直接拼 raw intent；
6. 测试 occurrence、多角色、readonly、缺 status、adapter 缺失、重复 action identity 和慢请求回写；
7. 用 data attribute/trace ID 保留可观测性，并更新本文与机器目录。

## 11. 推荐前端实现

仓库内已有正式实现，业务页面应复用，不重复封装 raw fetch：

| 能力 | 入口 |
| --- | --- |
| 统一 HTTP | `frontend/apps/web/src/api/client.ts` |
| Intent 信封 | `frontend/apps/web/src/api/intents.ts`、`envelope.ts` |
| 登录/启动状态 | `frontend/apps/web/src/stores/session.ts` |
| V2 加载 | `frontend/apps/web/src/app/contracts/v2/client.ts` |
| V2 严格解码 | `frontend/apps/web/src/app/contracts/v2/schema.ts` |
| V2 标准化索引 | `frontend/apps/web/src/app/contracts/v2/store.ts` |
| 数据 | `frontend/apps/web/src/api/data.ts` |
| Onchange | `frontend/apps/web/src/api/onchange.ts` |
| 按钮 | `frontend/apps/web/src/api/executeButton.ts` |

示例：

```ts
const page = await loadModelContractV2('project.project', {
  actionId: 120,
  menuId: 45,
  viewType: 'form',
  recordId: 42,
  renderProfile: 'edit',
});

const { snapshot, store, traceId } = page;
// 使用 store.widgetsById / widgetStatusById / actionsById；不要手写平行索引。
```

列表：

```ts
const result = await listRecords({
  model: snapshot.pageInfo.model,
  fields: snapshot.dataContract.dataMeta.visibleFields?.fields,
  domain: [],
  limit: 40,
  offset: 0,
  context: snapshot.dataContract.dataMeta.sourceContext?.context,
});
```

## 12. 兼容与禁止事项

### 12.1 主线与兼容面

| 项目 | 现行主线 | 兼容/诊断，不用于新页面 |
| --- | --- | --- |
| 页面 | `ui.contract.v2` | `load_contract` lite preview、旧 `ui.contract` 直接消费 |
| 导航 | `system.init.data.navigation` | 根级 `nav/route_authority/nav_legacy` |
| 参数命名 | snake_case | camelCase 别名 |
| Surface | `user`/governed | `native`、`hud` |
| 页面入口 | model 化 act_window 或正式 scene | `ir.actions.client` 产品页面 |
| 状态 | `statusContract` | 前端解析 modifier 后自行裁决 |

### 12.2 明确禁止

- 前端解析 Odoo XML；
- 按 model、XML ID、菜单中文名、role code 选择业务组件；
- 缺少字段时补写行业 fallback；
- 把字符串 boolean 当 boolean；
- 根据按钮名称直接调用后端 method；
- 把调试 surface 或 `sourceAuthority` 投影当业务事实；
- 对非幂等写操作做无条件自动重试；
- 在 `system.init` 完成前加载普通业务 intent；
- 契约解码失败后静默回退到猜测式页面。

## 13. 前端验收清单

### 启动

- [ ] 登录只保存当前 `session.db` 对应的 token；不同数据库会话隔离。
- [ ] `system.init` 成功前普通 intent 被阻断。
- [ ] 只消费 `navigation.nav/route_authority`。
- [ ] `navigation.integrity.missing_authority_count === 0`，否则失败关闭。

### 页面

- [ ] V2 响应经过正式 decoder，七个核心字段完整。
- [ ] `pageInfo.pageId === layoutContract.pageId`。
- [ ] client type、版本族和 lifecycle 完整性满足客户端能力。
- [ ] 未知顶层字段、非法枚举和错误 boolean 被拒绝。
- [ ] 同字段多个 occurrence 不被按 fieldCode 错误合并。
- [ ] 未注册组件显示明确 unsupported，不进入业务特判。
- [ ] 集合 semantic 经 renderer registry 解析；fallback/unsupported reason 可观测。
- [ ] canonical form presenter 失败时不重新启用 legacy 产品渲染链。
- [ ] 专业字段同时通过本地 registry 与契约 adapter/version 校验。

### 权限与行为

- [ ] 可见/只读/必填/禁用来自 `statusContract`。
- [ ] 按钮同时验证 action rule、button status 和 entitlement。
- [ ] `execute_button` 原样回传 action/backend/source identity 与 action/menu meta。
- [ ] 403/410 不自动走旧页面或旧动作。
- [ ] 菜单节点与精确 `menu_id + action_id` authority 配对，principal scope 与当前会话一致。
- [ ] 审批动作同时满足业务可用、授权裁决、entitlement 和 status，不使用角色提示放权。
- [ ] 角色/公司/记录上下文切换后旧契约和旧请求全部失效。
- [ ] enabled 动作在切换 renderer 前均有唯一 backendIdentity executor adapter。

### 数据

- [ ] 字段集合来自契约，不请求 `*` 作为常态方案。
- [ ] domain/context 来自正式 action/scene 和用户合法输入的结构化组合。
- [ ] 分组查询条件变化时重置窗口 identity/offset。
- [ ] onchange 旧响应在 context epoch 变化后被丢弃。
- [ ] 写入使用并发版本；删除/危险动作使用幂等键和确认策略。
- [ ] create 成功后加载新记录契约；状态动作成功后刷新详情契约与来源列表。
- [ ] 收藏筛选写入 `ir.filters` 对应 intent，个人列偏好不覆盖共享业务配置。

### 可观测性

- [ ] 错误日志包含 intent、HTTP 状态、reason code 和 trace ID，不记录密码/token。
- [ ] 区分 envelope meta 与 page meta。
- [ ] 304 走空体缓存路径。
- [ ] 网络错误、认证错误、契约错误、权限错误使用不同 UI 状态。

## 14. 完整 Intent 目录与扩展接口

本手册聚焦主线页面闭环。文件、消息、协作、偏好、配置和治理接口仍使用同一 intent 信封，
其当前机器目录在：

- `docs/contract/exports/intent_catalog.json`：106 个已发现 intent 的 owner、参数提示、返回键、
  示例和 reason code；
- `docs/contract/exports/scene_catalog.json`：scene identity/access/layout/components/target；
- `docs/contract/snapshots/`：主要 intent 的运行快照。

目录中的 `request_schema_hint` 是从 handler/样例提取的线索，不等同于人工承诺的完整 Schema。
接入扩展 intent 时，必须同时核对 handler、前端调用类型和快照；不能只根据目录自动生成写请求。

## 15. 快速排障

| 现象 | 首查 | 处理 |
| --- | --- | --- |
| 登录成功后任何页面都 409 | `session.initStatus` | 先完成 `system.init` |
| 401 | token、session DB、Authorization | 清会话重新登录；不要跨 DB 复用 token |
| 403 | `error.reason_code/details` | 展示后端裁决，核对角色/记录范围 |
| 410 native contract blocked | delivery policy | 打开正式 `/s/:sceneKey` 路由 |
| V2 decode error | error path + raw trace ID | 视为后端/版本契约不兼容，不静默兜底 |
| 按钮可见但执行被拒 | action ID/backend identity/status/action/menu | 重新加载记录契约，检查是否快照漂移 |
| 切项目后出现旧数据 | context epoch/cache key | 取消旧请求并清理旧上下文缓存 |
| 列表分组重复/跳页 | query fingerprint/window identity | 查询条件变化后重置分组窗口 |
| 304 JSON 解析失败 | HTTP status | 304 不解析 body，使用缓存快照 |
| 菜单可见但无法打开 | canonical carrier、principal scope、menu/action authority | 重新执行 `system.init`，禁止按 model 绕过 |
| 审批按钮错误出现 | available action 与 status/entitlement | 以最新记录契约重算；角色标签不能作为授权 |
| 审批超时后重复执行 | request/idempotency key 与最新记录状态 | 先查询执行结果/记录状态，不生成新键盲重试 |
| 列表显示为 unsupported | renderer data attributes/reasonCode | 核对 semantic 注册和 scene bridge 标准化，不按 model 强制切表格 |
| 详情字段莫名只读 | pageAuth、ancestor/slot/selector/widget status | 按合取顺序检查，status 缺失本身会失败关闭 |
| canonical 详情整页失败 | decode/presenter/action adapter error | 修复契约或唯一执行映射；禁止切回 legacy pipeline |

排障材料至少包含：请求 intent、脱敏 params、HTTP 状态、`X-Trace-Id`、信封
`meta.trace_id`、页面 `data.meta.requestId/snapshotId/etag` 和客户端版本。
