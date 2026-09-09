# 前端页面体验 Phase A：A1+A2 外壳样板

日期：2026-09-09  
状态：开发候选验证通过；正式发布门禁待既有样式系统阻断清理  
基线：`3d3975b3d45c1462677df0abcbb5708e4b53e0b1`  
产品提交：`8cdbcd7c005e6a28170800b8d76c6f190b57ab04`

## 1. 交付结论

本批完成 A1 页面身份与外壳统一，以及 A2 页面表达基准的首个样板：首页与“我的工作”的根路由、场景别名现在由显式页面元数据决定相同的最小顶栏和标题归属；两个页面共同消费既有 `ProductPageHeader`、`DashboardPattern` 与共享面板，不再由路由名称或页面内重复标题决定外壳。

首页任务、概览、常用入口调整为主任务区加右侧辅助区；局部卡片改用分隔与轻背景，减少连续装饰边框。付款列表与付款详情只作为共享基准的对照面，本批未改动其字段、动作或业务语义。

## 2. 架构边界

- Formal Product Layer：P0 平台内核产品；验证脚本和本记录属于 P4。
- Layer Target：Web router、AppShell、页面身份运行时、既有 page pattern 和共享展示组件。
- Standard vs User-Specific：平台通用页面身份与展示机制，不是建设行业事实、客户偏好或管理员运行配置。
- Why Here：等价路由的外壳、页头和空间语言必须由通用前端机制统一。
- Why Not Elsewhere：不应在 P1/P2 契约中编码布局，也不应以 P3 配置或业务字段猜测修复页面一致性。
- Blast Radius：首页、我的工作及其场景别名；付款列表/详情契约、权限、状态动作、数据和 fixture 不变。

## 3. 变更范围

- 路由元数据显式声明 `shellDensity: minimal` 与 `pageHeadingOwner: content`，AppShell 只消费页面身份，不再硬编码首页名称。
- HomeView、MyWorkView 统一使用共享页头与仪表盘 pattern；“我的工作”刷新动作归入页面页头。
- MyWorkApprovalWorkspace 移除重复标题面板，保留加载、错误、空态、筛选、事项动作和刷新事件。
- WorkspaceHome 收敛桌面网格与嵌套表面；移动端仍按单列自然重排。
- 守卫增加根路由/场景别名元数据、共享页头、pattern 和 dashboard 页面模式断言。
- 候选视觉脚本增加等价路由组的顶栏高度、内容起点和 minimal 模式比较。

未修改后端模块、契约 schema、权限、付款动作、数据库、fixture、Compose/profile、端口或凭据。没有新增 UI kit、token authority 或 renderer 主链。

## 4. 验证证据

产品提交 `8cdbcd7c` 的完整工作树指纹为 `5a7c4af3b22e415a210e0af86b6f1becd86b070c15ce44d6020e605b6c2836bc`，共 7322 路径。候选使用既有 `local.dev`：数据库 `sc_dev_demo`，只读账号 `sc_test_admin`，浏览器写请求计数为 0。

已通过的注册入口包括：

- `make codex.preflight`
- `make verify.frontend.dev.incremental ...`
- `make verify.frontend.page_identity`
- `make verify.frontend.product_page_header.unit`
- `make verify.frontend.page_pattern_reference_parity.unit`
- `make verify.frontend.shared_surface_semantic_boundary.guard`
- `make verify.frontend.theme_profile.unit`
- `make verify.frontend.mobile_viewport.unit`
- `make verify.frontend.product_page_pattern.unit`
- `make verify.frontend.state_dashboard.unit`
- `make verify.frontend.lint`（0 error，32 个既有 warning）
- `make verify.frontend.typecheck.strict`
- `make verify.frontend.diff_check`
- 前端候选 build

受控 local.dev 候选视觉检查覆盖 `/`、`/s/workspace.home`、`/my-work`、`/s/my_work.workspace`，结果 `pass=true`、`mutationCount=0`、`errors=[]`、`failures=[]`。四个入口在 1440px 与 390px 均只有一个可见 H1、一个 ProductPageHeader、`dashboard` 展示模式且根文档横向溢出为 0。

| 等价组 | 1440px 顶栏/内容起点 | 390px 顶栏/内容起点 |
| --- | --- | --- |
| `/` 与 `/s/workspace.home` | 52 / 52 px | 86 / 86 px |
| `/my-work` 与 `/s/my_work.workspace` | 52 / 101 px | 86 / 135 px |

“我的工作”额外的 49px 来自两个别名共同拥有的活动页签层，不是别名漂移。截图人工复核确认共享页头、表面层级和移动单列重排；截图捕获时业务内容处于加载态，因此本证据不声称 B1 的三条事项密度、真实错误恢复或付款业务动作已验收。

证据入口：`artifacts/playwright/local-dev-candidate-visual-smoke/summary.json`，以及同目录的 `desktop|mobile-home|my-work-{root,scene}.png`。该路径由仓库既有 artifact 链接承载，不作为产品源码提交。

## 5. 门禁与风险

`make verify.frontend.style_system.guard` 仍被基线已有的三个无关项阻断：

- `ActionSurfaceToolbar.vue` 在 Token v1 authority 之外声明全局 CSS 变量。
- `ScTable.vue` 混用 Unicode glyph 与 SVG 图标体系。
- `useRecordFormActions.ts` 为 622 行，超过 619 行 ratchet。

三项均存在于初始 HEAD，本批未扩大这些违规。按门禁 fail-closed，当前结论只能是本地开发候选验证通过，不能称为 `verify.frontend.release.local`、全系统验收或发布就绪。后续应以独立、明确授权的阻断清理批次处理，不能混入 A1+A2 视觉交付来稀释责任。

## 6. 回滚与下一批

产品改动集中在提交 `8cdbcd7c`；回滚该提交即可恢复原外壳判定和页面组合，报告提交 `606f49a7` 可独立保留。回滚不会涉及数据库或 fixture。

下一批进入阶段 B 的 B1+B2：以同一付款申请记录贯穿首页、我的工作和付款列表，优先收敛事项身份、关键事实、查询恢复及返回状态。若缺少结构化身份或金额权威输入，应登记 P1 契约依赖；禁止在前端拆解拼接标题或猜测币种、精度。动作执行链仍不在未授权范围内。
