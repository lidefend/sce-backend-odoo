# 系统页面体系完善：工作区、配置与异常体验收口

日期：2026-09-09

状态：三个本地批次已收口，产品候选通过；正式发布状态仍为 `verification_pending`

迭代原始基线：`3d3975b3d45c1462677df0abcbb5708e4b53e0b1`

冻结产品候选：`de1c04cd6191acafada58746cddcedf7416676fa`

## 1. 交付结论与边界

本阶段以页面体系而非单个缺陷作为交付单位，完成工作区连续交互、配置工作台状态表达、异常恢复以及跨页面类型的响应式与主题验收。付款申请样板保持冻结，仅作为共享组件回归面；没有扩展审批、支付或其他业务能力。

- Formal Product Layer：P0 承担通用页面 renderer、状态表达、共享浮层和响应式行为；P4 承担受管验证器、测试载体、生成清单和本报告。
- Layer Target：Web `HierarchicalWorksheet`、`ScDrawer`、`ScErrorState`、`BusinessConfigSurfaceView` 及其既有子组件；`smart_core` 仅调整一个平台通用失败文案。没有新增 renderer 主链、UI kit 或 token authority。
- Standard vs User-Specific：平台通用页面机制。收入合同、付款申请和配置目录仅作为现有真实样板，不承载新的 P1 行业默认、P2 客户偏好或 P3 管理员配置。
- Why Here：缺口发生在既有契约和页面输入进入通用页面后的选择一致性、状态投影、恢复动作、浮层边界和布局消费。
- Why Not Elsewhere：不在前端拆标题、猜币种或业务状态；不修改业务模型、工作流、原生视图或运行时配置；不以 P4 脚本承载产品行为。
- Blast Radius：层级工作区、配置工作台、共享 drawer/error state，以及浏览器矩阵涉及的首页、工作列表、标准集合、只读详情和异常页。定向单元门禁、完整 frontend Quick 和只读真实页面矩阵共同证明约束。

本阶段没有创建、编辑、保存、审批、支付、删除、发布配置或写入业务数据；没有创建数据库、端口、volume、profile 或 fixture。复用注册的 `local.dev`：project `sc-local-dev`、database `sc_dev_demo`、候选前端 `127.0.0.1:5176`、API proxy `127.0.0.1:18081`。

## 2. 页面类型与共享规范映射

| 页面类型 | 真实样板 | 页面身份/内容/操作与反馈归属 | 保留差异 |
| --- | --- | --- | --- |
| 首页 | `/`，`WorkspaceHome` | AppShell 提供系统外壳；页面自身以 ProductPageHeader、DashboardPattern 和共享状态组件组织任务摘要 | 保留概览和快捷入口，不模拟标准集合工具条 |
| 工作列表 | `/my-work`，`MyWorkApprovalWorkspace` | ProductPageHeader + ScDisclosure/ScMoney；记录身份、状态、关键事实和主动作属于事项卡 | 保留任务型紧凑卡片与辅助事实展开 |
| 标准集合 | 付款列表 action 809 | ActionView/ListPage + ProductListHeader + ScMobileRecordCard；查询、排序、分页和移动事实展开属于集合模式 | 桌面表格和移动卡片是同一集合的适配，不强制同一排版 |
| 只读详情 | 付款记录 15 `SHOW-PR-04` | ContractFormRoute/DriverHost + floorplan + ScErrorState；摘要、当前任务、动作和错误由既有契约语义驱动 | 保留 task/workspace floorplan，不把表单改成列表布局 |
| 层级工作区 | 收入合同 action 609，46 条 | HierarchicalWorksheet + ScDrawer + ScTable；范围、查询、选择、详情、separator 和返回恢复属于同一工作区状态 | 桌面三分区和移动范围抽屉是合理的载体差异 |
| 配置工作台 | `/admin/business-config`，60 个当前目录对象 | BusinessConfigSurfaceView/CoverageWorkspace/ChangeSetPanel + ScEmptyState/ScErrorState；对象、草稿、发布和请求状态分别投影 | 保留管理员所需高密度详情，但 1088 以下改为顺序阅读 |
| 异常页 | `/access-denied`、真实未知路由 | AccessDeniedView/NotFoundView + ScErrorState；原因和唯一安全返回动作属于异常模式 | 异常页无需伪装 ProductPageHeader，但保留唯一 H1 与系统外壳 |

共享规则是“外壳确定定位、页面类型确定结构、状态组件确定反馈、契约确定业务事实”。页面 scoped style 只承担该类型布局；颜色、尺寸和控件继续消费既有 token/theme bridge。

## 3. 三个完整批次

### 批次 1：工作区与共享交互收口

层级工作区已完成范围选择、查询、有效结果选中、详情、打开记录和返回恢复的连续链路。结果为 0 时清除旧选中、旧金额和记录入口；恢复结果后建立合理选中。桌面 separator 支持鼠标和键盘并具备 ARIA 边界；移动端通过范围按钮和 drawer 保留完整层级能力。

共享 drawer 从 320px 下实际 `380px`、左边界 `-84px`，收敛为 portal panel `0..320`、surface `16..304`；390px 同样在边界内。首次打开、Escape 关闭与焦点恢复、重开和打开态 320↔390 切换均通过，断言检查浮层自身及标题、关闭按钮、树节点，不再只检查根文档 overflow。

完整 C1 证据分别记录于：

- `docs/ops/iterations/frontend_hierarchical_workspace_c1_20260909.md`
- `docs/ops/iterations/frontend_hierarchical_workspace_c1_drawer_closure_20260909.md`

### 批次 2：配置与异常体系完善

配置工作台按“选择对象 → 理解当前配置 → 查看变更 → 理解交付状态”重新划分状态归属：

- 未选择对象时显示明确的“选择一个业务页面”，不再显示虚假的“正在配置 当前页面”。
- 当前真实数据库 changeset 为空时，标题、徽标、说明和动作统一表达“当前没有未发布修改”，不再同时出现“有未发布修改”。
- presentation model 明确区分 loading、empty、draft、failed、published 以及 publishing；请求失败优先于缓存内容，失败不会被空态掩盖。
- 页面目录查询 `60 → 0 → 60`，零结果提供清除筛选，恢复后可以选择真实对象且展示范围与选中对象一致。
- 真实读取请求被受控返回 503 时，页面显示读取失败和“重试读取”；一次重试恢复到真实空 changeset。该证据走真实页面请求链，不以模拟异常路由代替。
- 403 与未知路由分别说明原因，并通过唯一安全动作返回首页。

响应式修正覆盖组件自身边界：320/390 下已选对象概览、元数据、配置类型入口和异常恢复动作纵向展开，主入口 44px；1088 下配置三列转为顺序堆叠，避免根文档无 overflow 但中间窄列自我裁切；1440 保留高效三列布局。规则位于既有 scoped 样式和 ScErrorState 内，没有覆盖 TDesign 内部私有 selector。

### 批次 3：全系统一致性验收

同一产品候选运行两组完整矩阵：1088 桌面 + 390 移动明色，以及 1440 桌面 + 320 移动暗色。每组覆盖首页、工作列表、付款集合、付款详情、层级工作区、配置工作台、403 和 404；每个真实页面均等待加载完成态后取证。

付款冻结样板在四个视口/主题组合继续显示记录 15 的 `¥50.00`，集合与详情无共享回归。层级工作区完整 C1 旅程、配置选择/查询旅程和异常安全返回均在最终 SHA 下通过。两组矩阵及补充失败恢复运行全部 `mutationCount=0`、`errors=[]`、`failures=[]`。

## 4. 验收矩阵

| 页面/状态 | 1440 暗色 | 1088 明色 | 390 明色 | 320 暗色 | 关键链路结果 |
| --- | --- | --- | --- | --- | --- |
| 首页加载完成 | PASS | PASS | PASS | PASS | 唯一 H1、统一页头、overflow 0 |
| 我的工作加载完成 | PASS | PASS | PASS | PASS | 紧凑事项保持；共享页面身份无回归 |
| 付款集合 | PASS | PASS | PASS | PASS | 记录 15 金额 `¥50.00`；冻结样板回归通过 |
| 付款只读详情 | PASS | PASS | PASS | PASS | 同一记录与金额；未执行业务动作 |
| 收入合同层级工作区 | PASS | PASS | PASS | PASS | 范围→0 条→恢复→记录 15→返回状态/滚动恢复；drawer/键盘通过 |
| 配置未选择/空 changeset | PASS | PASS | PASS | PASS | 选择起点明确；60→0→60；状态口径一致 |
| 配置读取失败/恢复 | PASS（受控 503） | — | 390 布局回归 PASS | — | 真实请求失败可见，一次重试恢复；未写配置 |
| 403 / 404 | PASS | PASS | PASS | PASS | 原因可读、唯一安全返回有效、移动动作 44px |
| 页面与浮层边界 | PASS | PASS | PASS | PASS | 根 overflow 0；配置子容器及 drawer portal 自身均有边界断言 |

证据：

- `artifacts/playwright/frontend-system-pages-matrix-light-1088-390/summary.json`
- `artifacts/playwright/frontend-system-pages-matrix-dark-1440-320/summary.json`
- `artifacts/playwright/frontend-system-pages-final-failure-recovery-light-390/summary.json`

上述 artifact 目录同时包含对应页面截图。浏览器证据只绑定 `sc_test_admin` / system administrator 当前会话。

## 5. 代码与门禁证据

冻结候选完整工作树指纹为 `469bbe662245b7610e15398b4cf6c01d1473668ebc5e0e225a9cf41febd91e48`；scope manifest `8c9b1099ec609d073daa2b8ae2600da98b918c4c797a833abe45a5f59a97f058`；7333 paths。指纹 baseline 为本轮前端整体迭代原始基线，候选工作树干净。

最终候选已通过：

- `make verify.frontend.quick.gate`：PASS；strict typecheck、5168 modules build、共享组件/状态/主题/生成清单门禁均完成。构建仅保留既有 large chunk warning。
- `make verify.business_config.unit`：PASS；所有组均为非零用例，包括 change-set presentation 7 cases、schema 6 tests、field params 64 tests、menu audit 48 tests。
- `make verify.frontend.hierarchical_worksheet.unit`：PASS；interaction 15 cases、domain assertions 及后端用例通过。
- `make verify.frontend.overlay_lifecycle.unit`：PASS；9 tests，canonical=3、consumers=3、formal gaps=0。
- `make verify.frontend.page_identity`：PASS；23 + 12 assertions，identity guard writers=1、integrations=6。
- `make verify.frontend.theme_profile.unit`：PASS；runtime assertions=9、profiles=3。

配置测试 harness 的变更只让已有受管非零测试在缺少 lxml 的隔离环境中使用 stdlib XML stub，并补齐现有 mock lifecycle API；没有改变产品运行时契约。平台失败文案调整保留原错误码和动作执行行为。

## 6. 候选提交与回滚

本阶段增量提交按责任边界保留：

- P0 产品：`377ce708`、`213711d3`、`96d54078`、`2baad868`、`9115908d`。
- P4 测试与载体：`7c7d8cab`、`1b4ead47`、`5aa43ba2`、`d02db6b3`、`fcd2568b`、`bc7e6156`。
- P4 生成清单：`a2c0d4a4`、`de1c04cd`。
- 批次 1 的工作区及 drawer 提交保留在对应 C1 报告中，可独立回退。

产品变化可按上述 P0 提交边界回退；验证器和清单可按 P4 边界回退。没有把 P0/P4 拆成相互争用的 worktree 或运行环境。

## 7. 剩余问题及退出判断

页面体系阶段已达到本地退出条件：样板完整可用，共享规则一致，且具备进入下一阶段的稳定候选。以下不阻塞本地页面体系收口，但不得被混称为已验收：

- 正式 `verify.frontend.release.local`、独立审查、`make pr.push`、PR、合并和发布均未执行，发布状态保持 `verification_pending`。
- 当前真实数据库只证明 empty changeset；draft/published/failed/publishing 的表达由 7-case presentation 单元测试覆盖，没有执行真实配置草稿、发布或回滚。
- 受控 503 证明真实前端请求失败与恢复链，但不等于外部生产故障演练。
- 仅 system administrator 角色；其他角色、认证旅程、独立移动端、fallback calendar/gantt/dashboard 和配置业务写操作不在本阶段。
- 构建大 chunk 警告没有性能定量证据，不在本阶段扩展为性能重构。

因此，本阶段结论为：**页面体系本地产品候选完成，可作为下一阶段依赖；正式发布仍待独立审查与 release gate。**
