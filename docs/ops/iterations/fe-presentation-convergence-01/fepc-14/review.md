# FEPC-14：阶段要求只读入口

当前阶段为已授权的 FEPC-14I 最小实现，详见 [implementation.md](implementation.md)。不修改 ACL，不部署、不合并。

以下为 FEPC-14 定位阶段的历史记录；其中“待审批/未实施”描述仅适用于当时，已由 FEPC-14R 方案 A 及后续实施授权取代。

## 匹配截图的真实复现

用户补充截图后，已从真实侧栏“项目中心 → 项目台账”进入，不再使用首轮猜测的概览路由。
台账 action **588**、menu **382**，点击项目 **13**「城南污水处理厂扩建工程（完工阶段）」：
项目编码 `DEMO-PJ-STAGE-DONE`，页面状态“竣工”，页头“编辑 / 尚未修改 / 保存草稿”。
浏览器由列表自然导航至 `/t/demo/f/project.project/13` 并携带原入口查询参数；未绕过路由授权。

点击“查看阶段要求”后，页面出现与用户截图一致的“操作未完成 / 请求未能完成，请返回安全页面”。
完整脱敏请求与摘要：[matched-entry-evidence.json](matched-entry-evidence.json)。
原始浏览器证据：`.runtime/fepc-14/browser-smoke.json`；前后截图：
`.runtime/fepc-14/matched-project-before-click.png`、`.runtime/fepc-14/matched-project-after-click.png`。

## 已证明的失败层

`execute_button` 于 **2026-10-28 16:43:37 UTC** 返回 **HTTP 403**，应用层
`ok=false`、`PERMISSION_DENIED`、`retryable=false`、`suggested_action=request_access`。
错误原文关键部分：

> You are not allowed to create '项目阶段要求' (sc.project.stage.requirement.wizard) records.
> No group currently allows this operation.

调用链：

1. 原生 XML object 按钮 `action_view_stage_requirements`。
2. 前端携带契约动作 ID、backend identity、source widget ID、项目 13、公司 1、action 588、menu 382 请求 `execute_button`。
3. handler 校验动作与记录范围后，调用 `project_core.py:1721` 方法。
4. 方法对 `sc.project.stage.requirement.wizard` 执行 `create`。
5. Odoo 拒绝创建，handler 将 AccessError 返回为 403。

源码 ACL `security/ir.model.access.csv:246` 对该向导仅提供项目阅读组的 read=1、write/create/unlink=0，
与现有按钮必须创建临时向导的实现冲突。本轮请求直接证明 create 被拒绝；无须推测是哪类异常。

**排除本次直接根因**：不是目标 action 解析失败、向导契约解码失败或合法空要求项。
请求在向导创建阶段已被拒绝，尚未获得向导 action 或阶段要求内容。不能据此声称内容/空态路径已通过。

## 泛化错误呈现的原因

`useRecordActionPresentation.ts:183` 的 catch 只传递 errorMessage，没有把该次 ApiError 的 status/reason/trace
交给页面 loadError。`ContractFormPage.vue:67` 的错误面板仍读取 loadError；
`StatusPanel.vue:108` 按 errorCode/reasonCode 匹配服务端错误态，unknown 文案正是截图中的泛化提示。
这是源码支持且与当前 DOM 一致的第二层问题，不是解决后端拒绝的替代修复。
本轮未改公共错误处理，也未通过改变文案伪装按钮成功。

## 实施停止边界与最小方案

用户 FEPC-14 阶段 C 明确要求：涉及单独批准的权限、配置发布或业务规则变更时，停止并提交证据。
因此本轮不直接添加向导 create ACL，不使用 sudo，不切换管理员，不修改项目业务权限或阶段。

后续应先批准一个有界方案：

- 保留现有临时向导职责时，评估只针对该 TransientModel 的创建授权及其项目读取校验、记录归属和可写字段约束；不能只放宽 ACL 后就视为修复完成。
- 若产品要求此入口纯只读，则另行明确复用现有阶段要求读取路径的返回内容和页面职责，不自行替换业务语义。
- 无论采用哪一条，必须再验证阶段匹配、非空/空态、无权限、返回导航；同时检查 default_get 在当前 create 调用下是否真正生成明细，不能把“403 消失”视为完成。

建议优先评估现有向导的最小授权与校验方案，保留当前交互和权限边界；本文件只是待审批方案，不是权限变更许可。

## 已执行验证与未执行项

- 真实菜单 → 台账 → 指定项目 → 按钮，共一次成功定位后的按钮执行；HTTP403 与页面故障一致。
- 未拦截请求，未修改字段或点击保存；一次控制台资源错误对应实际403，详见 JSON。
- 8 项离线证据一致性断言通过（绑定项目、入口、错误、原路由与探针状态），不是产品单元测试。
- 新鲜 runtime-version 回读仍为主线 `1e06bcfde151d7669c29825d88c05bf3cd61b455`、构建
  `03045d0ed5c1359b2e2318be631ac6281bf818c39f272f69bfd62d92ac84c208`、`sc_demo/demo`。
- 未运行修复回归、Quick 或 PR 发布：没有获准且已实施的产品修复；本地审阅稿供权限边界裁定。
- 现有 DATA/CFG/部署草稿保留。F1、FEPC-13 不在范围内；未改业务数据、配置、ACL、产品代码。

批次：根因定位完成、实施阻断；主线：未集成；部署：未执行；用户验收：修复待授权与验证。

---

# 首轮未匹配入口的诊断（历史过程，已被下述匹配复现补齐）

本节仅保留首轮过程。当前结论以下述匹配入口复现为准。

## 基线与范围

GitHub main、本地 main、origin/main 与当前 HEAD 均为
`1e06bcfde151d7669c29825d88c05bf3cd61b455`。当前工作分支为
`audit/data-01-demo-facts`；已有 DATA、CFG、部署和阶段复盘审阅稿保留，排除在本任务修改范围之外。
本轮只新增诊断记录和任务元数据，尚未创建产品实施分支。

当前运行时 API 在 2026-10-28 16:29:34 UTC 返回同一源码 SHA，构建指纹为
`03045d0ed5c1359b2e2318be631ac6281bf818c39f272f69bfd62d92ac84c208`，
数据库 `sc_demo`，环境 `demo`。数据库 UUID 未在本轮重新查询，不借用历史 UUID 冒充当前核验。
真实登录后 `system.init` 返回用户 41、公司 1、角色 `business_full`。

P4 诊断复用现有 Playwright 启动器、日常安全登录机制和受管凭据；没有新建环境、凭据文件或验收车道。
产品故障归属须以实际失败请求确定，不能先在 P0/P1 或权限层实施补偿。

## 当前运行事实

证据见 [diagnostic-evidence.json](diagnostic-evidence.json)。时间均为 UTC。

- 用户未提供本次截图的具体项目或 URL。限定读取当前账号可见的一个在建项目，取得项目 4「成本资金项目」、`lifecycle_state=in_progress`。这是对照样本，不能声称是截图项目。
- 普通 `/r/project.project/4` 表单契约与相关数据请求成功，但未找到“查看阶段要求”按钮；等待该按钮超时属于入口不匹配，不是业务按钮失败。
- 按源码 XMLID 请求 `ui.contract.v2/action_open`，当前响应解析项目概览为 action 649、view 1775；契约包含可见且允许的 `action_view_stage_requirements` 动作。
- 进入带上述 action/view 的项目路由，浏览器实际转到 `/t/demo/access-denied`，显示“无权访问”。没有发送 `execute_button`，也未进入临时向导。
- 浏览器未被探针拦截任何请求，无控制台或网络错误。导航拒绝和用户截图中的“操作未完成”不是同一个已证明的失败，不能混淆。

## 源码事实与未确认线索

| 环节 | 源码位置 | 事实与边界 |
| --- | --- | --- |
| 按钮声明 | `addons/smart_construction_core/views/core/project_overview_views.xml:57` | 原生概览视图中的 object 动作；草稿阶段隐藏 |
| 前端调用 | `frontend/apps/web/src/pages/contractForm/useRecordActionPresentation.ts:145` | 依契约动作身份发送 execute_button，成功后处理导航 |
| 服务端执行 | `addons/smart_core/handlers/execute_button.py:315` | 校验当前契约动作、模型权限和记录范围后调用方法；不允许跳过 |
| 业务方法 | `addons/smart_construction_core/models/core/project_core.py:1721` | 创建阶段要求 TransientModel，返回对应 form 动作；不修改项目阶段 |
| 向导及数据 | `addons/smart_construction_core/models/support/project_stage_requirements.py:42` | default_get 按当前项目阶段筛选 active 要求项；是否在该 create 调用下实际生成明细尚未实测 |
| ACL 线索 | `addons/smart_construction_core/security/ir.model.access.csv:246` | project_read 对向导为 read=1/create=0；源码搜索未找到另一条向导 ACL。与 create 方法存在冲突线索，但不是本次点击的已证明错误 |
| 导航拒绝 | `frontend/apps/web/src/router/index.ts:368` | action 路由需当前授权声明，拒绝时不进入表单。未绕过或伪造授权 |
| 泛化错误页 | `frontend/apps/web/src/pages/contractForm/useRecordActionPresentation.ts:183`、`frontend/apps/web/src/components/StatusPanel.vue:105`、`addons/smart_core/core/error_state_contract.py:22` | 动作 catch 设置错误状态；StatusPanel 根据状态/原因匹配服务端错误态，unknown 文案为截图所述文字。未捕获截图失败请求，不能据此认定 ACL 或具体异常 |

既有原生阶段摘要组件调用 `sc_get_stage_requirements`，与创建向导是不同路径；仅追踪了源码，未把它声称为已实测成功的同入口对照。

## 最小后续步骤

取得截图的详情 URL，或项目名称/编码及进入路径后，复用同账号准确复现一次点击，记录请求和应用层错误。
若确认向导 create 权限拒绝，按用户任务阶段 C 的要求提交权限/入口职责决策，不直接添加 ACL 或 sudo。
若实际故障在其他层，则只修复被证据证明的层。

现阶段没有足够依据提出可实施的代码差异。不能通过直接调用被路由拒绝的入口制造浏览器成功，也不应仅把错误文案改成另一种提示。

## 验证与限制

- 实际执行：`python3 .runtime/fepc-14/run-smoke.py`，复用既有登录及 Playwright lane。
- 探针首次把 fetch 的 `Response.status` 属性误作函数，已纠正，失败记录保留；后续两个等待目标选择器超时均保留，未算作产品回归。
- 当前成功证据：运行时身份、登录、普通表单加载、概览契约解析；当前阻断证据：概览路由拒绝。
- 未执行：按钮业务方法、阶段要求内容/空态/权限回归、修复后浏览器验收、Quick、PR 发布。没有产品改动，不用单元测试替代缺失的点击证据。
- 未修改业务数据、项目阶段、ACL、配置或数据库；没有部署、初始化、升级、fixture 或重建。
- FEPC-13 与 F1 保持原有未解决状态，未纳入本轮。

批次：定位未完成；主线：未集成；部署：未执行；用户验收：待精确入口复现。
