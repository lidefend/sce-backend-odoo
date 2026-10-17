# 路由入口契约字段分层 v1

日期：2026-10-17
正式产品层：P0
架构层：契约消费边界
运行归属：`smart_core`
状态：**分层与迁移口径已定义；字段裁剪与 `entry_key` 协议未实施**

## 1. 边界

前端只回答“怎么到达、怎么渲染、怎么交互”，后端只回答“这是什么业务、能不能做、能看哪些数据”。

| 内容 | 前端拿到 | 后端保留 |
| --- | --- | --- |
| 路由 | 稳定入口标识、页面地址、记录标识 | 入口到模型/action/view/处理器的解析 |
| 菜单可见性 | 裁定后的可见入口集合 | 用户组、菜单规则、发布版本与授权计算过程 |
| 页面与按钮权限 | 明确的可用/只读/隐藏/拒绝及原因码 | ACL、记录规则、业务状态判断、最终执行授权 |
| 查询条件 | 契约声明的筛选项与用户输入值 | 租户/公司/权限域、基础业务域与合成规则 |
| 关联字段选择 | 字段标识、选择器契约、可选操作 | 目标模型解析、关联约束、候选数据过滤 |
| 诊断 | 用户可理解的错误与追踪编号 | 规则、原始 domain、模型映射、裁定轨迹 |

两条必须同时成立的结论：

1. **减少暴露有价值**，但它只减少传输与认知负担。
2. **隐藏不等于安全**。模型名不可见不构成授权；每个请求仍由后端重新校验会话、公司、ACL、记录规则与业务状态。

“前端完全不知道后端实现”的可检验口径是：

> 前端不解析、不校验语法、不据其分支、不展示某个字段的后端含义。

满足该口径的值可以继续作为**不透明标识**透传并回传（例如 `action_id`）；一旦前端需要理解它代表什么业务对象、能查哪些数据、对应哪个视图，它就已经是产品语义输入，必须改为契约声明或后端裁定，不能靠“看起来是 ID”继续留在客户端。

## 2. 字段分类

四类含义固定：

- **启动必需**：`system.init` 完成前，外壳、导航与路由准入就要用到。
- **页面必需**：只在进入该入口、加载该页面契约时需要。
- **仅后端**：前端不得解释；命中即为“声明了但无人消费”或越界，需收口或移出客户端契约。
- **仅诊断**：只在受控诊断入口按需读取，不得进入普通启动响应。

### 2.1 `navigation.route_authority` 外壳

| 字段 | 前端当前消费 | 分类 | 结论 |
| --- | --- | --- | --- |
| `contract_version` / `schema_version` | 版本校验（`normalizeRouteAuthorityContract`） | 启动必需 | 保留；不匹配应报契约缺口，不得静默降级 |
| `principal_scope.{user_id,company_id,role_code}` | 主体绑定校验（`routeAuthorityForPrincipal`） | 启动必需 | 保留；是“这份裁定属于谁”的显式声明 |
| `source` | 仅规范化，无消费 | 仅诊断 | 可移出客户端契约 |
| 六个 bucket（`primary_actions`/`role_home_actions`/`contextual_actions`/`admin_actions`/`denied_actions`/`menu_containers`） | 路由准入与导航模型（`canonicalNavigation.ts`、`router/index.ts`） | 启动必需 | 保留；bucket 名即裁定语义，不得由前端合并或推导 |

### 2.2 `route_authority` 条目

| 字段 | 前端当前消费 | 分类 | 结论 |
| --- | --- | --- | --- |
| `action_xmlid`、`menu_xmlid` | 准入身份（`normalizeEntry` 要求 action 与 menu 绑定） | 启动必需 | 作为稳定标识保留；不得用于推断业务可见性 |
| `route_kind` | bucket 归属校验 | 启动必需 | 保留 |
| `action_id`、`menu_id` | 准入与路由匹配 | 启动必需 | 作为不透明标识保留 |
| `route` | 导航断言与容器路由 | 启动必需 | 保留 |
| `name`、`action_name` | 标题展示 | 启动必需 | 保留 |
| `allowed_operation` | `actionRoutePolicy` 判定 read/write | 启动必需 | 保留；这是显式裁定值，不是前端推导 |
| `context_requirements` | `routeAuthorityContextAllowed` | 启动必需 | 保留；显式声明所需 query 键 |
| `scene_key`、`entry_target` | 声明式目标入口 | 启动必需 | 保留 |
| `model` | `session.setActionMeta`、`actionRoutePolicy` | **页面必需（过渡）** | 今天仍承载数据调用，**不能只删字段**；见 §4.1 |
| `view_modes`、`view_id` | 复制进 action meta | **页面必需（过渡）** | 同上：应逐步改为后端按入口解析视图 |
| `domain`、`context` | **无消费者**（仅规范化保留） | **仅后端** | 已声明却无人消费，需收口；前端不得据此拼查询 |
| `required_capability` | **无消费者** | 仅诊断 | 移出客户端契约或改为显式裁定字段 |
| `source` | **无消费者** | 仅诊断 | 移出客户端契约 |

### 2.3 `nav[]` 节点

| 字段 | 前端当前消费 | 分类 | 结论 |
| --- | --- | --- | --- |
| `key`、`label`、`children` | 渲染树 | 启动必需 | 保留 |
| `menu_id`、`menu_xmlid`、`xmlid` | 路由与准入匹配 | 启动必需 | 保留（不透明标识） |
| `action_id`、`route` | 跳转 | 启动必需 | 保留 |
| `model`、`view_modes` | action meta 合并 | 页面必需（过渡） | 随 §4.1 一起迁移 |
| `sequence` | 排序 | 启动必需 | 保留；顺序由后端声明 |
| `meta.groups_xmlids` | 仅透传合并，无可见性判定 | **仅后端** | 用户组属于授权实现；无消费证据时应移出导航响应 |

### 2.4 `user` 身份块

| 字段 | 前端当前消费 | 分类 | 结论 |
| --- | --- | --- | --- |
| `id`、`name`、`lang`、`tz` | 会话与展示 | 启动必需 | 保留 |
| `company_id`、`allowed_company_ids`、`company` | 公司范围 | 启动必需 | 保留；是裁定结果，不是规则 |
| `is_platform_admin` | 管理面入口 | 启动必需 | 保留；仍须后端逐请求校验 |
| `groups_xmlids` | 无可见性判定 | **仅后端** | 用户组是 ACL 实现；除非有登记的产品消费场景，应移出客户端契约。当前已改为稳定排序，见 §5 |

## 3. 契约缺口规则

前端拿到必须消费的字段时，缺失或非法只有一种正确结果：停机并报告缺口。

- 唯一原语：`frontend/apps/web/src/app/contract/contractGap.ts` 的 `contractGapError`，携带 `missing` 路径与 `requiredDeclarationLayer`。
- 禁止：默认值、夹取、按模型名特判、静默丢条目、推断缺失的权限或状态。
- 已有落地：`session.ts` 在缺失/错配 `route_authority` 时把 `initStatus` 置 `error` 并中止启动（fail-closed）。
- 仍然存在的缺口：`normalizeRouteAuthorityContract` 对不合法条目执行 `filter(Boolean)` 静默丢弃，且外壳不匹配时只返回 `null`。拒绝是安全的，但**不报告**会把后端契约缺陷伪装成“本来就没有这个入口”。

下一批应收口为：拒绝 + 显式缺口（bucket、下标、字段路径），并在台账登记该判断站点。

## 4. 迁移顺序（兼容优先）

本迁移已登记为独立计划任务 `.agent/goals/ROUTE-ENTRY-CONTRACT-MIGRATION.yaml`（`status: planned`），
按专题处理；在它启动前，本文件只定义边界与顺序，不授权任何前端协议改造。

### 4.1 先建入口级数据协议，再谈删除 `model`

今天前端确实需要知道模型，因为调用面是模型级的：

- `frontend/apps/web/src/api/data.ts` 的 `listRecords`/`listRecordsRaw` 必填 `model`；
- `router/index.ts` 把 `routeAuthority.model` 写入 action meta；
- `frontend/apps/web/src/services/actionRoutePolicy.ts` 读 `authority.model`；
- 公开 URL 直接带模型名：`/f/:model/:id`、`/r/:model/:id`。

因此“前端不知道后端模型”不是响应裁剪问题，而是**协议迁移**问题。顺序必须为：

1. **P0-1 入口级读写**：列表/读取/写入支持 `entry_key`（或入口 ID）由后端解析模型，前端不再提交 `model`。
2. **P0-2 地址不透明化**：公开地址改为入口令牌 + 记录标识，旧地址保留跳转兼容。
3. **P0-3 裁定显式化**：页面、按钮、查询、关联选择器统一返回可用/只读/隐藏/拒绝及原因码。
4. **P0-4 字段收口**：把 §2 中“仅后端/仅诊断”字段从客户端契约移出，并升版本。
5. **P0-5 移除过渡依赖**：删除 `router`/`actionRoutePolicy` 对 `model` 的分支，`model` 最多保留为不透明技术标识。

在 P0-1、P0-2 完成前删除 `model`/`view_modes` 只会把“知道模型”变成“猜模型”，比现状更差。

### 4.2 启动与页面拆分

`system.init` 只生成：身份与公司、可见入口集合、默认入口、路由裁定、启动必需声明与契约版本。页面结构、筛选项、关联选择器在进入入口时解析。拆分必须由后端契约声明，前端不得自行省略字段。

## 5. 与本轮改动的交点

- **请求内菜单事实复用**让同一请求的可见/授权事实各导出一次；它不改变裁定语义，只减少重复扫描（见迭代记录 R15）。
- **`groups_xmlids` 稳定排序**：该字段原按 Python `set` 顺序输出，同一身份在不同进程产生不同字节；排序后启动响应可逐字节比较，缓存与等价性证据才有确定基准。排序不改变集合语义，也不把 ACL 暴露给前端当判定依据。

## 6. 目标调用形态（未实施）

```text
system.init → 身份、导航入口、默认入口、契约版本
用户进入 entry_key → 后端解析入口并校验权限 → 当前页面契约
用户提交筛选/动作 → 后端重新校验并执行
```

列表请求的声明式表达（目标态）：

```json
{"entry_key": "payment.requests", "filters": {"status": "pending"}, "page": {"cursor": "..."}}
```

前端不携带公司隔离域与权限域，也不能通过修改请求绕开；未声明的筛选或动作由后端明确拒绝。

## 7. 本文件不声称

- 未实现 `entry_key` 协议、未删除任何字段、未更改 URL 方案。
- 不构成安全论证：隐藏字段不替代逐请求授权。
- 不改变批次状态：未冻结、未 `ci.local.quick`、未推送、未部署。
