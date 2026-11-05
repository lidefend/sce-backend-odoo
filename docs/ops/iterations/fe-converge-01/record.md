# FE-CONVERGE-01 前端公共表现与交互整体收敛（持续批次记录）

## 0. 身份与边界

- 基线 main：`54bed83383ee2e03773141430bdd6d50ca4f932b`
- 候选分支：`codex/fe-converge-01-presentation`（受管 worktree `sce-backend-odoo-fe-converge-01`）
- 后端运行时：Odoo 17（`smart_core` + `smart_construction_core` 契约驱动）
- 前端运行时：`@sc/web`（Vue 3.5.6 + Vite 5.4 + Pinia），内部 UI 库 `@sc/ui`
  - `tdesign-vue-next 1.20.5`、`tdesign-icons-vue-next 0.4.9`、`echarts 6.1.0`
- Formal Product Layer：P0（平台通用前端运行时与共享组件）
- Layer Target：`frontend`（AppShell / design-system / product-shell / product-list / product-record / page blocks / renderers）
- 模块：`frontend`
- 边界：只改表现与交互，不修改任何后端契约、字段、权限、动作、状态语义；不新增按模型/菜单/角色/状态文本的前端判断。

## 1. FE-00 固定基线与体验样本

### 1.1 基线事实

| 项 | 值 |
| --- | --- |
| main SHA | `54bed83383ee2e03773141430bdd6d50ca4f932b` |
| 前端应用 | `@sc/web`（`frontend/apps/web`） |
| 内部 UI 库 | `@sc/ui`（`frontend/packages/ui`，导出 bridge/collection/form/icons/primitives） |
| TDesign | `tdesign-vue-next 1.20.5` + `tdesign-icons-vue-next 0.4.9` |
| 后端 | Odoo 17（契约驱动，`ui.contract.v2`） |

### 1.2 三角色样本

- 项目经理（PM）：项目台账、合同办理、付款申请主视角（`pm1` 类业务账号）。
- 财务：付款申请、支付执行、结算相关（财务 fixture 账号）。
- 配置管理员：菜单配置、字段管理、发布工作台（`fixture_role_config_admin` / `business_config_admin`）。

说明：FE-00 为静态盘点，未连接数据库；三角色真实页面打开在批次产品复核阶段用
`local.dev.*`（project `sc-local-dev`、database `sc_dev_demo`、端口 18081）或既有 daily
服务器回读确认，不在此批次虚构截图。页面与角色/状态对应关系以后端导航契约为准。

### 1.3 Renderer 现状盘点（`actionSurfaceRendererRegistry.ts`）

| semantic | activeRendererKey | status | 说明 |
| --- | --- | --- | --- |
| table | core.standard_collection | ready | 列表 |
| card | core.standard_collection | ready | 卡片 |
| workflow_board | core.standard_collection | ready | 流程看板 |
| hierarchy_browser | core.hierarchy_browser | ready | 层级浏览（component outlet） |
| hierarchy_planner | core.hierarchy_planner | ready | 层级规划（component outlet） |
| hierarchical_worksheet | core.hierarchical_worksheet | ready | 层级工作表（component outlet） |
| pivot | core.pivot | ready | 透视 |
| graph | core.graph | ready | 图表 |
| activity | core.activity | ready | 活动 |
| calendar | core.readable_records | fallback | `RENDERER_CALENDAR_PLANNED` 降级为可读记录 |
| gantt | core.readable_records | fallback | `RENDERER_GANTT_PLANNED` 降级为可读记录 |
| dashboard | core.readable_records | fallback | `RENDERER_DASHBOARD_PLANNED` 降级为可读记录 |

未知语义统一进入 `core.unsupported`（`ACTION_SURFACE_RENDERER_NOT_REGISTERED`）。
FE-08 必须如实保留 `calendar/gantt/dashboard` 的降级视图，不伪装成完整功能。

### 1.4 公共组件清单（收敛主战场）

- 设计令牌与主题：`styles/tokens/*.css`（primitive/semantic/component/pattern/profile/tdesign-bridge）、
  `styles/design-system.css`、`styles/product-patterns.css`、`styles/theme.ts`、`styles/tdesignGlobalConfig.ts`。
- 设计系统组件：`components/design-system/*`（68 个 `Sc*` 组件 + `tdesignPrimitiveBridge`、
  `primitiveAdapter`、`nativeControlProjection`、`pageWidth`、`scFormContract` 等）。
- 全局外壳：`layouts/AppShell.vue` + `layouts/AppShell.css`；`components/product-shell/*`
  （ProductAppShell、ProductScenarioNavigation、ProductSideNavigation、NavigationBreadcrumb、
  ProductMobileNavigationDrawer、ActivityPageTabs、WorkspaceContextIndicator、ProductIdentity 等）。
- 页面标题/操作区：`components/product-page-header/ProductPageHeader.vue`。
- 列表：`components/product-list/*`（ProductListSurface、ProductListHeader、CollectionRowCell、
  CollectionPaginationFooter、CollectionKanbanLane、CollectionBatchActionBar、CollectionGroupingToolbar、
  CollectionFilterChip、ListSurfaceHeader 等 20+）。
- 表单/详情：`components/product-record/*`、`components/page/*`（PageRenderer/ZoneRenderer/BlockRenderer/blocks）、
  `pages/ContractFormPage.vue`、`pages/ListPage.vue`。
- 呈现策略：`app/presentation/*`（contractFormPresenter、professionalComponentRegistry、
  standardListComposition/standardFormComposition/standardPageType/standardShellComposition、productPageHeaderAdapters 等）。

### 1.5 公共组件消费者盘点（静态，`frontend/apps/web/src`）

- 76 个源文件消费 design-system / product-shell / product-list / product-record /
  product-page-header / product-page-patterns / page 组件。
- `AppShell.vue` 是共享外壳的直接宿主：消费 ProductScenarioNavigation、ProductAppShell、
  ProductMobileNavigationDrawer、NavigationBreadcrumb、WorkspaceContextIndicator、ProductIdentity、
  ActivityPageTabs、ProductShellContentFooter、ProductShellSidebarFooter、ScButton。
- 由此，对共享外壳与设计令牌的任何统一，都会覆盖所有中心页面，而不是逐页重写。

### 1.6 按渲染类型选择的体验样本

| 类型 | 样本入口 | 对应公共组件/Runtime |
| --- | --- | --- |
| 普通列表与详情 | 项目台账（`action_sc_project_list` → 项目概览表单） | standard_collection + 详情 form + ProductPageHeader |
| 复杂合同表单 | 合同办理（收入/支出/日常合同） | ContractFormPage + contractFormPresenter + design-system 表单 |
| 主从明细与业务按钮 | 付款申请（`payment.request`） | x2many + 业务动作 + ProductFormErrorSummary |
| 状态与执行反馈 | 支付执行（`sc.payment.execution`） | 状态/动作反馈 + 加载/成功/冲突 |
| 配置工作区 | 菜单配置（MenuConfigView）、字段管理 | BusinessConfigSurfaceView / 配置相关组件 |
| 特殊表现 | 看板（KanbanPage）、分析（AnalysisPage）、层级（hierarchy_*）各一例 | kanban/chart/hierarchy renderer + 降级视图 |

## 2. 验证状态（持续更新）

| 层 | 命令 | 状态 | 说明 |
| --- | --- | --- | --- |
| L0 | worktree preflight | 通过 | 工作树已创建，branch/SHA 已核对 |
| L1 | `make ci.local.iteration` | 通过 | 静态迭代门禁（dirty 态 L1 only） |
| L1 | `verify.frontend.lint.src` | 通过 | 0 error，1 个既有 warning（StatusPanel.vue 格式，与本次无关） |
| L1 | `verify.frontend.shared_surface_semantic_boundary.guard` | 通过 | 58 文件扫描 |
| L1 | `verify.frontend.action_surface_renderer.architecture.guard` | 通过 | 渲染注册表边界 |
| L2 | `verify.frontend.style_system.guard` | 通过 | hardcoded_color_refs_max=0 |
| L2 | `verify.frontend.theme_profile.unit` | 通过 | 12 断言，3 主题档案一致 |
| L2 | `verify.frontend.navigation_shell.unit` | 通过 | 21 tests + 6 组件守卫 |
| L2 | `verify.frontend.product_page_header.unit` | 通过 | 75 tests，页头入口契约 |
| L2 | `verify.frontend.typecheck.strict` | 通过 | vue-tsc 双档，无类型错误 |
| L2 | `verify.frontend.build` | 通过 | 经 `ENV_FILE` 复用主仓库 `.env.dev` 生产构建成功（28s） |
| L3 | `local.dev.candidate.frontend.up/down` | 通过 | 候选前端在 5176 起停正常（绑定当前 SHA） |
| L3 | `local.dev.candidate.frontend.visual-smoke` | 未执行 | 后端 source mount 非本工作树（见运行时争用） |

## 3. 阻断与缺口

- FE-02 已登记（待后续批次收口）：
  - `--sc-shell-navigation-item-height`（44）与 `--sc-shell-page-gutter`（24）声明但尚无消费者；
    属于设计令牌卫生问题（非契约缺口），需在 FE-01 外壳收敛时接线到导航项与页面沟槽，或显式退役。
  - `AppShell.css` 1177 行，含旧壳（1–940）与“2026 workspace refresh”（943–1177）两段，需在 FE-01 确认
    是否仍有双重实现残留，避免 FE-09 清理时误删仍在生效的旧规则。

### 运行时视觉复核被共享后端争用阻塞（environment_defect，非产品缺陷）

- 事实：候选前端构建与服务均可从本工作树经受管入口完成（`verify.frontend.build` 经
  `ENV_FILE` 复用主仓库 `.env.dev` 通过；`local.dev.candidate.frontend.up/down` 在 5176 起停正常）。
- 真正阻塞：`local.dev.candidate.frontend.visual-smoke` 的 `_backend_identity` 要求 local.dev 后端
  `/mnt/source-addons` 挂载点与 `SC_SOURCE_REVISION` 等于本工作树 `addons` 与 HEAD；当前该后端
  实际绑定 `sce-backend-odoo-mainline-deploy`（HEAD `fe719728b`）。
- 处置：不重建共享 local.dev 后端（会打断当前所有者 `mainline-deploy` 的运行时，属串行共享资源争用）。
  视觉复核待该共享后端释放或明确授权切换绑定后再执行；期间视觉改动继续走静态守卫+单测。

## 3.1 前端机制缺口登记（FE-01/02 深入结论）

### 导航项高度无法直接接线（P0 桥接缺口，非产品契约缺口）

- 事实：`--sc-shell-navigation-item-height: 44` 已在 `pattern.css` 声明，但侧边栏菜单项实际高度
  由 TDesign `.t-default-menu .t-menu__item` 的 `height: var(--td-comp-size-l)`（40px）驱动；
  TDesign 主题桥 `frontend/packages/ui/src/kits/tdesign/theme.css` 只映射 brand/radius/component-stroke，
  没有菜单项高度映射点。
- 尝试：在 `MenuTree.vue` 作用域内覆写 `--td-comp-size-l` → 被 `verify.frontend.style_system.guard`
  正确拦截（“TDesign theme variable outside bridge” + “new global CSS variable outside Token v1”），已撤销。
- 结论：`--td-comp-size-l` 是共享尺寸令牌，全局覆写会波及按钮/输入等其它控件；正确处置是
  在 P0 TDesign 主题桥新增菜单项高度映射点，或显式退役 `--sc-shell-navigation-item-height` 并接受 40px。
  这不是前端 CSS 补丁能安全闭合的，需桥接层决策。

### 页头已收敛，无平行实现（FE-03 结论）

- `ProductPageHeader` 是唯一页头实现；`ScPageHeader`（design-system）与 `PageHeader`（page）都是
  薄适配器，统一固定 `presentationMode='collection'`；入口轴由
  `app/presentation/productPageHeaderAdapters.ts` 的 `PRODUCT_PAGE_HEADER_ENTRIES` 受管登记，
  并有 `verify.frontend.product_page_header.unit` 守卫。FE-03 无重复页头问题。

### 列表工具栏高度已收敛（FE-02 第一批）

- `--sc-product-list-toolbar-height` 由 46px 收敛到 `var(--sc-pattern-collection-toolbar-height)`（52px），
  消除 `HierarchyBrowser/HierarchyPlanner` 同一组件内 46/52 两套高度。

### FE-04 列表与搜索静态结论

- 搜索/筛选控件高度已一致：桌面 36px（`--sc-component-input-form-height: 36px`），
  移动端 44px 触控目标；`MyWorkApprovalWorkspace` 与 `ProductListHeader` 同口径。
- 金额/日期对齐已收敛：`.column-layout-money { text-align: right; min-width: 128px }`、
  `.column-layout-date { min-width: 108px; color: secondary }`；长文本统一
  `text-overflow: ellipsis + white-space: nowrap`。
- 已具备横向滚动与 sticky 表头/选择列；缺口：无横向滚动可发现性样式（无 scrollbar 宽度/常显/淡出指示）。
  该项是视觉改动，按选项 2 延后到后端释放后经 visual-smoke 复核。

### FE-02 令牌卫生收尾结论

- 剩余硬编码字面量均为文档化 legacy 或规范值：`--sc-pattern-task-form-*`（注释声明不持有 primitive）、
  `--sc-touch-target-min: 44px`（触控目标规范值）、`--sc-product-line-body: 22px`、密度变体 42/46px。
  不再强改；`--sc-shell-page-gutter`（24px）与 `--sc-shell-navigation-item-height`（44px）为未消费别名，
  前者被响应式 `--sc-page-padding` 取代、后者受桥接缺口阻塞（见 §3.1）。

## 4. 下一步精确动作

1. 对导航项高度桥接缺口做归属决策：P0 桥接层新增菜单项高度映射点，或退役 44px 令牌（需所有者/架构确认）。
2. 继续 FE-02：逐项排查 `pattern.css` 中剩余硬编码值与未消费别名。
3. FE-01：核实 AppShell.css 两段式外壳是否有双重实现，统一侧边栏/顶部栏/标签页/面包屑/内容区/移动端抽屉。
4. 视觉改动统一经 `local.dev`（nginx 18081 / odoo 8070 已就绪）做真实页面复核后再提交。

## 5. FE-R1/R2/R3 首轮实看（2026-11-05 续）

### 运行环境身份

| 项 | 值 |
| --- | --- |
| 前端候选 | `2018be046`（本工作树，FE-CONVERGE-01） |
| 后端 | `fe719728b`（local.dev 共享后端，绑定 mainline-deploy；addons 与前端同源，仅 P4 脚本差 1 提交） |
| 数据库 | `sc_dev_demo`（命名空间 `/t/demo`） |
| 角色 | `sc_test_admin`（系统管理员） |
| 访问路径 | 候选前端 5176 → local.dev nginx 18081（受管入口 `local.dev.candidate.frontend.up`） |

### FE-R1 结论（导航高度）

- 真实消费链：AppShell → ProductScenarioNavigation → ProductSideNavigation → MenuTree →
  TDesignMenu → CanonicalNavigationMenuNode（TDesignMenuItem/Submenu）。
- 计算后高度：`.t-default-menu .t-menu__item { height: var(--td-comp-size-l) }`，`--td-comp-size-l=--td-size-11=36px`。
- `--sc-shell-navigation-item-height`(44px) 无消费者，且被 `standard_shell_composition_test.ts` 显式登记为
  **reserved**（声明但不消费、测试强制保持）。真实消费者无尺寸不一致。
- 裁定落点：**不新增主题桥、不退役、不制造消费者**；此前的“P0 桥接缺口”分类撤销，改为“保留令牌，无产品缺陷”。

### FE-R3 实看结果（DOM 实测 + 截图，截图供人工复核）

- 外壳正常：侧栏 `232px`、顶栏 `56px`，与 `--sc-shell-sidebar-width`/`--sc-shell-topbar-height` 一致。
- `/`、`/my-work`、`/admin/menu-config` 均加载，`overflowX=0`，无控制台业务错误（仅 2 个 404 资源）。
- **真实发现（后端事实/数据缺口）**：侧栏导航空态显示
  “场景导航配置不可用，请在配置中心维护业务场景后重试，业务入口保持关闭”。
  `sc_dev_demo` 当前无可用场景导航配置，导致无法经导航进入项目台账/合同/付款/支付执行等业务页。
  该空态本身是合法的配置缺失提示，不是前端缺陷；但据此无法完成 FE-R3 业务页实看。
- 截图目录：`artifacts/fe-converge-01/observe/*.png`、`measure.json`（DOM 实测）。

### 遗留缺口（如实登记，不绕过）

- 业务样本页实看受 `sc_dev_demo` 场景导航配置缺失阻塞；需后端/数据侧补齐场景配置，或经
  `/a/<action_id>` 直连（需从后端取 action id，尚未取得）。
- 前端无产品缺陷需要修复；FE-R4 暂无可修项（已实看页面无溢出/溢出/错误）。

### FE-R3 续：项目台账列表页实看（DOM 实测）

- 经菜单路由 `/m/382`（项目台账，action 590）成功打开：标题“项目台账”，真实数据渲染
  （如“东汽数字化产线改造工程 / DEMO-PJ-206”）。
- 列表头高 **52px**，与 FE-02 收敛后的 `--sc-pattern-collection-toolbar-height` 一致（修复已生效）。
- `overflowX=0`（1440px 无横向溢出）；金额列 `.column-layout-money` 右对齐（约 40 列）；
  另有 4 个命中 `.column-layout-money` 的元素 `align:left`，待复核是否为表头/日期列分类差异。
- 直接 `/a/590` 被拒绝：`access-denied reason=NAVIGATION_AUTHORITY_DENIED`——直接动作访问
  需导航授权，属正确权限边界（场景授权/入口由后端任务负责），非前端缺陷。
- 无控制台业务错误。

### FE-R4 修复：统一列表工具栏主操作按钮高度

- 实看发现：付款申请“新建/批量导入”按钮 30px，而收入合同页头“新建”36px；同一 `size=small`
  主操作在两处高度不一致（同 class `t-size-s sc-btn sc-btn-primary`）。
- 根因：页头集合动作在 `theme.css:538` 有 `min-height: var(--sc-component-input-form-height)`（36px），
  列表工具栏 `ProductListHeader` 的 leading 动作区无此规则，回落 TDesign small 30px。
- 修复：`ProductListHeader.vue` 集合布局 leading 按钮消费同一
  `min-height: var(--sc-component-input-form-height); height: auto`，桌面统一 36px；
  移动端既有 44px 触控目标规则保持。
- 验证（DOM 实测）：付款申请“新建”30px → 36px（与收入合同一致）；移动端 44px 保持；
  `overflowX=0`。`style_system.guard`、`lint.src` 通过。
- 受益页面：付款申请、收入合同、项目台账及所有经 `ProductListHeader` 渲染的列表。

### FE-R3 续：字段管理 / 合同表单 / 支付执行

- 字段管理（`/m/445` → action 820）：标题“表单字段配置”，`overflowX=0`，显示 `ScEmptyState`
  （demo 库无字段策略数据，空态合法，非前端缺陷）。
- 收入合同列表行 `tr.record-row[data-record-id]` 存在但点击未打开表单（仍在 list 态）——待查
  是否为行点击交互或记录打开授权问题，不在本轮前端绕过。
- 支付执行：`menu_sc_payment_execution` 未出现在可访问菜单集（与场景导航数据缺口同源），无法经菜单到达。

### FE-R3 续：合同表单详情实看

- 收入合同列表为 Odoo 风格 tree（`td > .tree-cell`，行双击打开），双击后进入
  `/f/construction.contract.income/6`，标题“CONIN2600006”，`formMode=form`，`overflowX=0`。
- 表单有“合同审批岗”动作按钮（36px）。
- 待登记（FE-08 交互一致性）：收入合同用 tree 双击打开，付款申请用主单元格单击打开
  （`CollectionRowCell` primary 链接）——两种列表打开交互并存，需确认是否由契约视图类型决定，
  避免前端强行统一破坏 Odoo tree 语义。

### FE-08 打开交互来源核对（代码位置）

- 列表主表面：`ListPage.vue` → `ScTable`（design-system），`ScTable.vue:30` 绑定
  `@row-dblclick="emit('rowDblclick', $event)"` —— 行打开默认是**双击**。
- `CollectionRowCell.vue:19` 主单元格用 `@click.stop="$emit('open-record')"` —— **单击**打开。
  `ListPage.vue:1719` 的 `collectionCell` 对文本列用 `CollectionRowCell`，`onOpenRecord: () => handleRow(row)`。
- 结论：**打开方式来自 Renderer 默认行为，契约不声明 open method**。契约只声明视图类型
  （收入合同/付款申请均为 `tree,form`）与列结构；单击/双击是 ScTable（双击）与
  CollectionRowCell（单击）各自的渲染器默认。收入合同首列为原生 tree 名称单元格（`tr.record-row > td > .tree-cell`，
  双击打开，已实测），付款申请行结构本轮未干净复核（列表页出现“确认操作”弹层干扰），后续补验。
- 处置：**本轮不改动打开行为**，不把差异归因于 Odoo tree 语义；如需统一需先在契约/呈现层
  明确打开语义，再决定渲染器默认。

### 支付执行实看（FE-R3 状态与执行反馈样本）

- 入口：`menu_sc_payment_execution` = ir.ui.menu 339，action 908（“实付登记”，`sc.payment.execution`）。
- 列表（`/m/339`）：标题“实付登记”，6 条记录，`overflowX=0`，无空态/错误。
- 详情（双击进入 `/f/sc.payment.execution/189`）：标题“PE2600180”，状态“已付款”，`overflowX=0`，
  有“办理类型/办理说明”按钮（30px small）与“确认操作”。
- 直连 `/a/908` 被 `NAVIGATION_AUTHORITY_DENIED` 正确拒绝（权限边界正常）。
- 导航可达性：侧栏场景导航仍因后端模块升级缺口失败，但**菜单直连 `/m/339` 可达**——
  前端直连证明页面表现通过，导航缺口仍单独登记，不混为一谈。

### 后端子代理只读诊断（支付执行入口缺失层）

- 根因：`smart_construction_core` 模块未升级（DB installed 17.0.0.174 vs 源码 17.0.0.175），
  缺 `ir.ui.menu.sc_scenario_exempt` 列 → `scenario_surface_projection.py` 抛 UndefinedColumn →
  整个场景导航投影失败 → 前端显示“场景导航配置不可用”。
- 四层：发布 ✅、场景关联 ✅、**原始 ACL 配置 ✅（菜单/动作/模型 ACL 无缺口）**、
  模块升级 ❌（缺列）。支付执行未被权限或场景删除。
- 独立复核边界澄清：demo_role_finance 的菜单/动作/模型 ACL 原始配置确实无缺口；但
  **最终路由授权结果尚未证实**——菜单 ORM 读取先被缺列阻断，授权求值未走到。因此
  “本地无有效快照”不能直接等同于“开发环境必然拒绝”；须在补列（模块升级）后核实
  实际发布库的解析结果，才能下“授权通过/拒绝”的最终结论。
- 最小修复：对 sc_dev_demo 走受管入口升级 `smart_construction_core`（174→175）补列；
  属模块升级交付，非权限扩大或场景豁免。
- 后端身份已漂移：source mount `sce-backend-odoo-mainline-deploy`，分支 `release/be01-daily-c819daff`，
  HEAD `c819daff`（此前记录 `fe719728b` 已失效）。

### 后端前置完成 + 前端验证（2026-11-06）

- 后端已完成：sc_dev_demo 升级对齐 `7998f673c`（缺失字段已加载），发布快照 12，公司 1 的
  payment.capital 由未启用→启用，场景关联保留；demo_role_finance 非 sudo 路由校验通过，
  动作范围内 6 条记录；财务组/菜单动作组/ACL 未改，豁免仍 False。交接证据见
  `sce-backend-odoo/.runtime/payment-entry-frontend-handoff.json`。
- 前端验证（demo_role_finance / 公司 1 / 候选前端 5176）：
  - 场景导航已恢复——侧栏显示“财务主管 / 财务中心”，不再“场景导航配置不可用”。
  - 支付执行 `/m/339` 与 `/a/908?menu_id=339` 均“实付登记”、6 条记录、表格渲染、`overflowX=0`、无错误。
- 结论：前端独立直连验证通过；后端/前端 SHA 不同（前端 `8b840a07d`，后端 `7998f673c`），
  受管 `list_surface_structure` 回执的 same-HEAD 约束仍存在（`_adapter_list_surface` 要求
  `expectedSha == head`），记为后续工程优化，不在本轮改门禁。

### FE-R5 降级视图表达（已实现，待真实页面复核）

- 事实：calendar/gantt/dashboard 渲染器为 `fallback → core.readable_records`（standard outlet）；
  `ActionSurfaceRendererHost` 此前只在 data 属性暴露 `status/reasonCode`，用户看不到降级说明。
- 实现：`ActionSurfaceRendererHost.vue` 在 `status === 'fallback'` 时显示简洁提示
  “该视图暂以列表形式展示”，不渲染 `RENDERER_*_PLANNED` 等实现标识；样式用 info 态令牌。
- 验证：typecheck.strict、lint.src、style_system.guard、action_surface_renderer_registry.unit、
  action_surface_renderer.architecture.guard 全部通过。
- 限制：demo 可访问面未发现默认 calendar/gantt/dashboard 入口（默认视图均为 tree/kanban），
  降级提示的真实页面展示待找到含这些视图类型的入口后复核。

## 6. 治理修复后的候选同步（2026-11-06）

- 注册审计修复 PR #816 已合入 `1d0f2fe5a760`；生成报告同步修复 PR #817 已合入 `17adbaf774370`，两者均经过独立审查和当前 SHA 的远端必需检查。
- 原候选 `1d0d1d6285e4` 保留恢复 bundle；既有备份引用 `fe-converge-01-backup-20261106` 仍指向 `c589f9dea194`。旧回执、截图及记录的 46 个文件已复制并逐项哈希核对，清单见本 run 的 `governance_sync.archive_manifest`。
- 第一次普通同步因生成报告冲突拒绝并恢复原 HEAD。修复后通过 `workspace.branch.sync-main REGENERATE_GENERATED_EVIDENCE=1` 同步到上述精确主线，原生成器重建 complexity 报告，生成证据 preflight 和原提交 hooks 通过，得到 `8852eeb6a472`。
- 当前只有两个责任提交，使用受管短分支重建路径；没有伪造提交数满足 extended，也没有跳过 hooks 或修改旧回执。
- 前述验证结果均为历史阶段记录，不能当作同步后候选的通过证明。此次所有者明确要求当前 HEAD Quick；冻结新候选后执行，随后重取受管契约及列表浏览器回执。最终结果由同一 run 引用原始回执，不为写入事后结果重复变更冻结 HEAD。
- 本批仍只改善公共表现；实际支付、撤销及审批业务闭环不在本批验收范围。

### 独立审查收口

- `bae4dec0b1e5` 的独立审查发现历史 `scripts/dev/fe_converge_observe.mjs` 自带默认凭据及任意目标配置，不能作为正式交付工具。该脚本无正式验收消费者，已从发布候选移除；原文件保存在上述归档和原责任分支恢复 bundle 中，不删除历史截图或观察结论。
- 该候选的 Quick 因审查修正主动停止，不能记为通过。新候选继续使用既有受管契约、列表验收及凭据解析入口，不新建观察或授权体系。

### 主线测试覆盖登记补齐

- `3783bfffa199` 的完整 Quick 在 `verify.test.coverage.registry` 失败，原因是主线两个 ORM 自定义标签尚未登记；没有签发回执。干净主线复现后，由独立治理 PR #818 修复并通过独立审查、19 项审计测试及当前远端必需检查，合并至 `f64de1f87c8c`。
- 两类原已通过 `sc_gate` 进入默认模块套件；本次仅登记并回归验证真实链路，未新增重复 ORM 车道，未将自定义标签虚称为独立门禁。
- 已受管同步前端至该主线并执行原生成器/preflight，得到 `97ff41cdd519`；无生成文件冲突，无产物内容变化。更新本索引后冻结最终候选，重新取得明确要求的 Quick，再进行受管页面验收。
