# 新旧前端功能迁移台账

状态定义：`已验证` 表示真实接口和构建已通过；`已对接` 表示已接后端但仍需角色/页面回归；`开发中` 表示只有部分能力；`待迁移` 表示旧端有功能而新端尚无完整实现。

| 旧端入口/能力                       | 新端入口                                                         | 真实后端接口                                                                                                                             | 当前状态 | 待验收或缺口                                                                                                                                                 |
| ----------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 登录、退出、刷新恢复                | `/login`、账户菜单                                               | `login`、`auth.logout`、`system.init`                                                                                                    | 已验证   | 各角色落地页回归                                                                                                                                             |
| 账号激活、密码恢复                  | `/activate-account`、`/password-recovery`                        | `/api/v1/auth/activation/*`、`/api/v1/auth/password-recovery/status`                                                                     | 已对接   | 实际邮件/激活码流程                                                                                                                                          |
| 动态菜单、角色首页、公司/项目上下文 | SideNav、`/dashboard/base`                                       | `system.init`                                                                                                                            | 已对接   | 公司、项目、经营方式切换及页签上下文快照已接入；多角色逐项验证                                                                                               |
| Action 列表                         | 动态菜单 -> `pages/odoo/action`                                  | `ui.contract.v2`、`api.data`                                                                                                             | 已对接   | 逐菜单 XMLID 对照                                                                                                                                            |
| 搜索、筛选、排序、分页、导出        | 动态 Action 列表                                                 | `ui.contract.v2`、`api.data/export_csv`、`search.favorite.set`                                                                           | 已对接   | 已接后端分组窗口、组内分页、汇总、收藏保存/读取；待跨模型回归                                                                                                |
| 列显示偏好、Contract 批量动作       | 动态 Action 列表                                                 | `user.view.preference.*`、`api.data.batch`、`api.data.unlink`、`collaboration.users.search`                                              | 已对接   | 批量按钮由 `surfacePolicies.batch_policy.available_actions` 决定；归档、激活、删除、导出及带真实用户选择的批量指派已接入                                     |
| Tree/Kanban/层级工作表              | 动态 Action 列表、层级运行时                                     | `ui.contract.v2`、`api.data`、`execute_button`                                                                                           | 已对接   | contract 声明 `hierarchy_levels` 时渲染层级导航和 WBS 结构动作；声明 `hierarchical_worksheet` 时渲染多级分组工作表；复杂层级权限/编辑回归待验收              |
| Pivot/Graph/Calendar/Gantt/Activity | 动态 Action 集合视图                                             | `ui.contract.v2`、`api.data`                                                                                                             | 已对接   | 已进入 Action Surface Renderer Registry，仅在后端声明对应语义时显示；Graph 已用真实数据浏览器验证，其余视图仍需不同字段 contract 回归                        |
| 动态详情、创建、编辑、onchange      | `/r/:model/:id`、`/f/:model/:id`、记录抽屉                       | `ui.contract.v2`、`api.data`、`api.onchange`                                                                                             | 已对接   | 独立详情/编辑路由支持分享、刷新和业务查询上下文恢复；已接 modifier/domain patch、并发令牌、离开确认及 7 天本地创建草稿恢复；仍需复杂 AST/span 回归           |
| one2many/many2many 明细             | 记录抽屉                                                         | `api.data.write`、`api.onchange`                                                                                                         | 已对接   | 新/改/删输出 Odoo command；需真实含明细表单回归                                                                                                              |
| 业务按钮、审批动作                  | 记录抽屉                                                         | `execute_button`                                                                                                                         | 已对接   | 按模型验证提交、审批、撤回、拒绝                                                                                                                             |
| 附件、Chatter、活动、关注者         | 记录详情协作页                                                   | `file.*`、`chatter.*`、`collaboration.users.search`、`api.data`                                                                          | 已对接   | 已有附件、消息/备注提醒对象、活动负责人、创建/完成/取消、关注者查询/添加/移除；需写操作角色回归                                                              |
| 记录复制、并发冲突解决              | 记录详情工具栏、冲突对比弹窗                                     | `api.data.create`、`api.data.write`、`ui.contract.v2`                                                                                    | 已对接   | 复制按 contract 权限开放；409 显示服务器/本地字段差异，支持保留本地、加载最新和使用最新 `if_match` 令牌覆盖；需双会话冲突浏览器验收                          |
| 我的工作                            | `/my-work/index`                                                 | `my.work.summary`、`my.work.complete`                                                                                                    | 已对接   | model/action/record 目标路由兜底、批量完成                                                                                                                   |
| 使用分析                            | `/operations/usage`                                              | `usage.report`、`capability.visibility.report`                                                                                           | 已对接   | CSV 导出与筛选参数                                                                                                                                           |
| 场景健康                            | `/operations/scene-health`                                       | `scene.health`、`scene.governance.*`                                                                                                     | 已对接   | 已有治理通道、固定稳定版、回滚和导出契约；需治理角色写操作回归                                                                                               |
| 场景包                              | `/operations/scene-packages`                                     | `scene.package.*`                                                                                                                        | 已对接   | 已有列表、导出、导入前检查、导入和冲突策略；需实际包导入回归                                                                                                 |
| 产品发布操作台                      | `/operations/release-operator`                                   | `release.operator.*`                                                                                                                     | 已对接   | 实际治理角色的操作回归                                                                                                                                       |
| API Key 管理                        | `/governance/api-keys`                                           | `auth.credential.*`                                                                                                                      | 已对接   | 已有创建、撤销和轮换；需治理角色与密钥一次性展示回归                                                                                                         |
| 场景运行时                          | `/s/:sceneKey`、动态 scene 菜单                                  | `system.init`、scene block `data_deps` intent、动作 intent                                                                               | 已对接   | 已按后端 Zone 的顺序、布局和已裁决权限渲染，并支持工具栏、状态栏、主动作、指标、待办、预警、入口、记录/关系表、看板和动态依赖；新增 Scene Block Registry 和明确 reason code；复杂专用 Block 仍需逐场景验收 |
| 诊断工作台                          | `/operations/workbench`、兼容 `/workbench`                       | `system.init`                                                                                                                            | 已对接   | 展示用户、公司/项目、导航、场景、能力、Intent、版本和 Trace；仅治理诊断页，需各角色回归                                                                      |
| 业务配置                            | `/governance/business-config`                                    | `ui.business_config.surface.*`、`change_set.*`、`coverage.*`、`contract.versions`、`snapshot.*`、`sc.approval_policy.*`                  | 已对接   | 变更集、stage 编辑、覆盖率扫描/补全、版本查询、快照导出/比较、审批策略及步骤编辑均已接真实接口；需治理角色写操作回归                                         |
| 菜单配置                            | `/governance/menu-config`                                        | `ui.menu_config.panel.*`、`menu.*`、`audit`、`versions`、`rollback`                                                                      | 已对接   | 完整菜单集、父级调整、拖拽排序、显示名、顺序、可见角色多选、创建/删除/审计/版本/回滚已接真实接口；需多角色对照验收                                           |
| 表单字段配置                        | `/governance/form-field-config`、兼容 `/admin/form-field-config` | `ui.form_field_policy.set`、`ui.form_field_order.set`、`ui.form_field_config.batch_set`、`ui.form_custom_field.create`、`ui.contract.v2` | 已对接   | 基于真实动态菜单表单 contract 管理显隐、顺序、分组、尺寸、列数和租户自定义字段；需治理角色写操作回归                                                         |
| 全局消息/通知                       | 顶部铃铛、`/messages`                                            | `mail.notification`、`global.message.*`                                                                                                  | 已对接   | 真实会话列表、收件箱、发送、已读和通知跳转已接入；需多用户互发与未读同步验收                                                                                 |
| 无权访问、404、异常/trace 诊断      | `pages/result/*`、`/operations/workbench`                        | 标准错误 envelope/`trace_id`                                                                                                             | 已对接   | 诊断工作台和统一错误页均展示并可复制最后请求或路由携带的 Trace ID；需逐错误 envelope 回归                                                                    |
| 业务路由二次权限校验                | 全局路由守卫                                                     | `route.authority.validate`                                                                                                               | 已对接   | 普通菜单使用 `system.init` 权限表；仅 contract 声明公司/项目/记录上下文时执行后端二次校验，避免共享 action 被误判 403；管理员固定页面优先消费后端身份/能力/`admin_actions`；需逐角色回归 |

迁移规则：Starter 示例页只能作为视觉基座，不能作为生产入口或模拟业务结果。每个动态菜单的列表、详情、按钮、权限和数据范围，必须与旧端使用同账号、公司、项目和记录进行对照验收后才能标记“等价通过”。

## 最近验证记录

- `2026-08-20`：`pnpm run build:type` 与 `pnpm run build` 通过。
- `2026-08-20`：使用 `role_project_manager` 调用真实后端，登录、`system.init`、`collaboration.users.search`、施工日志 `ui.contract.v2`、`api.data`、`chatter.timeline` 和退出均通过；该账号返回 22 个可见 action。
- `2026-08-20`：施工日志真实表单 contract 包含 6 个分区、19 个字段，`header/group/field` 结构已纳入通用解析。
- `2026-08-20`：新增通用层级运行时，真实 WBS contract 返回 2 个层级和 6 个结构动作，工程量清单 contract 返回 `sheet_groups` 和 4 个导航分组；业务/菜单治理面板真实只读接口通过。
- `2026-08-21`：接口能力注册表覆盖 63 个静态 intent；5 个路由/权限/详情上下文/renderer registry 单测通过，`pnpm run build:type` 通过。
- `2026-08-21`：真实项目数据列表、Graph 视图、消息中心和 `/r/sc.general.contract/2?action_id=685&menu_id=660` 独立详情已完成浏览器冒烟；本轮新增 Zone、冲突处理及其余高级视图仍需继续浏览器验收。
- `2026-08-21`：仅对 contract 声明公司、选中项目或记录上下文的动态路由调用 `route.authority.validate`；普通共享 action 菜单不再被误判 403。
- `2026-08-21`：活动页签持久化公司、项目和经营方式快照，切回页签时恢复对应后端上下文；首页页签按上下文原位更新，避免同路径重复首页。
- `2026-08-21`：动态组件注册表收窄为 Action 与 Scene 两个正式运行时，Starter 示例页面不再因全目录 glob 被打入生产构建或成为潜在动态入口。
- `2026-08-21`：修正动态场景菜单的组件标识，统一按页面注册表根路径解析，避免 Scene 菜单错误进入 500 页面。
- `2026-08-21`：诊断工作台接入 `meta.intent_catalog`，展示后端当前账号目录、前端注册表交集和未登记数量；接口覆盖不再只依赖静态源码扫描。
- `2026-08-21`：分组列表在后端未返回 `grouped_rows` 但返回普通记录时按当前页记录回退分组，并从字段元数据补齐中文分组名称，避免“共 N 条但分组为空”。
- `2026-08-21`：集合视图严格按后端 contract 声明开放：`tree/list`、`card/cards`、`kanban` 及高级分析视图分别映射对应运行时；仅在 contract 未声明任何可识别集合视图时保底显示列表。

## 尚未宣称等价通过的范围

- 21 个角色的菜单、数据范围、创建、编辑、审批和禁止动作尚未形成完整自动化矩阵。
- 复杂 modifier AST、嵌套动态 domain、不同模型的 x2many 和双会话 409 冲突仍需真实数据覆盖。
- Pivot、Calendar、Gantt、Activity 需要分别使用后端明确声明且字段结构匹配的 contract 验收。
- 表单设计器已有拖拽、分组、Notebook 和实时预览，但嵌套布局与完整发布生命周期仍需治理角色逐项验收。

## 本轮对照升级记录

- 旧端管理员入口通过 `user.is_platform_admin`、能力目录和 `route_authority.admin_actions` 判定；新端已同步该优先级，固定 XMLID 仅作兼容兜底。
- 旧端场景区块先经 `pageBlockRegistry` 解析；新端已新增 `sceneBlockRegistry.ts`，未知 Block 不再静默按普通内容推断，统一输出 reason code。
- 旧端高级视图通过 renderer registry 返回 `requestedRendererKey/activeRendererKey/status/reasonCode`；新端高级视图已根据 Contract renderer、data source 和结构化配置做 ready/fallback 诊断。
- 旧端业务配置边界中的 7 个正式 Intent 已补入新端统一 SDK 和能力登记检查，避免“台账登记但客户端没有调用方法”。
- `dataContract.tableRows` 同时支持内嵌数组和 `api.data` 数据源映射；成本计划真实 Contract 返回空对象映射时已按旧端语义正常进入列表加载，不再误报 `CONTRACT_SHAPE_INVALID`。
