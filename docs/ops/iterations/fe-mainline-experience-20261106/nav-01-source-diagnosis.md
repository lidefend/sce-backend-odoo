# NAV-01 第一阶段源码诊断（侧边栏导航体系收敛）

基线：origin/main = fdd039b42。结论：可见导航当前消费了错误的“域分类”结构，规范化菜单模型和官方 TDesign 菜单组件均已存在但未接入。

## 1. 三套导航事实

- menuTree / navigationModel：来自 system.init.navigation.nav，经 createCanonicalNavigationModel(menuTree, routeAuthority) 解码。真实 menu→submenu→item 层级，每个节点已解析 route 与 authority。当前不参与可见渲染，仅辅助查找。
- scenarioSurface：来自 system.init.navigation.scenario_surface，经 parseScenarioSurface。业务域/场景分类（centers→scenarios→entries）。当前被 ProductScenarioNavigation 渲染，是可见导航。
- 官方 TDesign 菜单链：MenuTree → TDesignMenu → CanonicalNavigationMenuNode → TDesignSubmenu/MenuItem。统一菜单交互与视觉（data-semantic-driver="tdesign-menu"、data-navigation-node="canonical"）。当前孤立，未被 AppShell 消费。

## 2. 关键结论

- CanonicalNavigationNode 已绑定路由与授权：route（来自 routeAuthority/container/declared）、authority（allowed/container + source/key）、state（enabled/disabled/container）、disabledReason、parentChain、icon、order。
- 选中无需再走场景快照 createScenarioSelectionSnapshot，可直接用 node.route + node.authority。
- session.menuExpandedKeys 已存在（规范化菜单展开态），但缺 toggleMenuExpanded / ensureMenuExpanded 两个方法。
- 搜索当前走 searchScenarioSurface（场景专用）；需改为按规范节点 label/menu 身份过滤，不依赖 scenarioSurface。

## 3. 新旧对账要点

- 同一批业务入口在 navigationModel 与 scenarioSurface 中同时存在；navigationModel 按真实菜单层级，scenarioSurface 按业务域/场景重新分组。
- 可见入口数应以 navigationModel（去重 menu/action 身份）为对账基准；不得通过菜单数量减少掩盖入口缺失。

## 4. 第一阶段接入方案（AppShell）

1. AppShell 由渲染 ProductScenarioNavigation 改为渲染 MenuTree，nodes = navigationModel.nodes。
2. 保留：activeMenuId（选中）、session.menuExpandedKeys（展开）、sidebarCompact（折叠）、query（搜索）、移动端抽屉与键盘能力。
3. 新增/替换：handleCanonicalSelect(node) 用 node.route + node.authority 走 routeAuthorityContextAllowed 后路由；session.toggleMenuExpanded(key) / session.ensureMenuExpanded(keys)；规范化搜索按节点 label/menu 身份过滤并保留父链，searchActive 时全展开。
4. 不删 ProductScenarioNavigation，不删 scenarioSurface，不改后端契约与授权。

## 5. 阶段验收映射

- 数据来源/菜单层级/菜单身份/授权：由 navigationModel + routeAuthority 保证。
- 选中/展开：activeMenuId + menuExpandedKeys。
- 搜索：规范节点过滤，不依赖场景导航组件。
- 视觉体系：MenuTree/CanonicalNavigationMenuNode 真正被消费。
- 旧实现：ProductScenarioNavigation 保留但不再作为数据权威。

## 6. C/D 运行态验收（PM / 隔离环境）

- 搜索过滤：输入“项目台账”后 canonical 节点从 30 → 4（系统菜单→项目中心→项目台账→项目台账），父链保留。
- 叶子路由：点击叶子后导航到 /a/590?menu_id=382。
- 展开：系统菜单默认折叠，点击后项目中心可见。
- 响应式：390px 无横向溢出（scrollWidth=clientWidth=390）。
- 新旧对账（PM）：canonical 叶子 19 条、scenario 入口 19 条，scenario-only 与 canonical-only 均为空，19/19 全部一致，无入口丢失。
