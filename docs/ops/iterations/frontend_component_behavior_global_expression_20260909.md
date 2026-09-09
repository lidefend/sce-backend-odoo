# 共享组件行为确认与全局表达收口（2026-09-09）

## 批次信息

- 当前批次：共享组件行为确认 → 全局视觉一致性收口。
- 唯一目标：证明本轮受影响的官方组件能力在真实页面中正确工作，并在不改变业务语义的前提下统一全局页面表达。
- Formal Product Layer：P0 平台通用前端运行时；P4 仅承载验证与证据。
- Layer Target：frontend shared primitives、shell、通用页面 surface/theme，以及既有 local.dev candidate browser evidence。
- Module：frontend。
- Standard vs User-Specific：平台通用交互、可访问性、响应式和视觉层级，不是施工行业规则、客户偏好或管理员运行时配置。
- Why Here：Input、Select、Card、Alert、Button 的行为投影与页面外壳/工作表面属于通用前端渲染责任。
- Why Not Elsewhere：不修改 Odoo 模型、原生视图、契约、scene 编排、P1/P2/P3 数据或运维修复；不按付款模型、菜单或角色写前端特判。
- Blast Radius：首页、我的工作、付款列表/详情、收入合同代表工作区，以及这些页面共享的组件、外壳、页头、工作表面和主题规则。

## 范围

- 允许修改：`frontend/apps/web/src/components/design-system`、`frontend/apps/web/src/components/product-shell`、`frontend/apps/web/src/layouts`、`frontend/apps/web/src/styles`、共享页面模式及现有 `scripts/verify/local_dev_candidate_visual_smoke.mjs` 的增量断言。
- 允许产物：同视口 before/after 截图、交互摘要、完整候选指纹、验证日志和本迭代记录。
- 复用环境：`local.dev.*`，Compose project `sc-local-dev`，database `sc_dev_demo`，backend port `18081`，candidate frontend port `5176`。

## 不做

- 不修改 contract/schema、public intent、启动链、default_route、权限、业务状态或数据规则。
- 不保存表单、不执行业务动作、不 reset fixture、不升级模块、不进入 release/acceptance 环境。
- 不创建 Compose project、database、port、volume、credential、runtime profile、fixture 体系或测试入口。
- 不以材料入库开启业务专题，不做全业务流程回归，不把工程清单归零等同于视觉或交互验收。
- 不执行 push、PR、ready、merge 或发布。

## Step A：受影响组件真实行为确认

### 操作

1. 在既有 local.dev candidate browser 入口中选择真实、只读页面载体：
   - Input：导航或列表搜索的输入、清除、焦点与错误关联；
   - Select：我的工作排序或通用列表筛选的鼠标选择、键盘选择与单次变化；
   - Card：正文 class 与操作插槽在真实卡片中的可见结构；
   - Alert：真实错误恢复表面的 description、operation slot、焦点恢复与单次重试；
   - structured Button：正式页面验证首页快捷入口/我的工作指标的鼠标与键盘触发、焦点与单次触发；正式页面没有可控 loading 状态，因此 disabled/loading 通过既有组件浏览器机制向真实 `ScButton` 传入响应式 props 验证，并与正式页面结论分列。
2. 记录 light/dark、1440×960/390×844 下的无溢出与焦点可见性。
3. 若暴露产品缺陷，仅修改对应 P0 共享组件；若只是验证脚本误判，仅修改 P4 断言，不改变产品语义。

### 完成判据

- 搜索清除、鼠标/键盘选择、错误反馈、操作插槽、disabled/loading、焦点及 exactly-once 均有非零断言并通过。
- 受测路径业务 mutation 为 0，console/page/network failures 为空。
- 明暗主题和窄屏无退化。
- 未通过前不进入 Step B。

### 回滚

- P4 行为断言与 P0 产品修复分开提交；任一层可按独立提交回退。
- 若现有正式页面无法承载必要状态，停止并登记缺口；不向产品代码注入测试专用路由或数据。

## Step B：全局视觉一致性收口

### 操作

1. 在 Step A 通过的冻结候选上，以首页、我的工作、付款列表/详情、收入合同工作区生成同视口 before 对照。
2. 先冻结共享规则：外壳留白、页头层级、工作表面、内容密度、边框数量、主次动作、长内容和主要操作可达性。
3. 仅在共享组件、主题与通用页面模式集中实现，避免业务页面散落补丁。
4. 生成同视口 after 对照，验证 light/dark 与窄屏。

### 完成判据

- 首页、我的工作、付款列表/详情和代表工作区使用一致的外壳、页头、表面与动作层级。
- 重复框层减少，主次操作清晰；长内容不遮挡，主要操作在 390px 可访问。
- before/after 使用相同 viewport、theme、route 和真实数据身份。
- 无 contract、route、权限或业务 mutation 差异；浏览器 errors/failures 为空。

### 回滚

- 共享视觉改动保持独立 P0 提交，可整体回退而不影响 Step A 的行为证据。
- 若改善要求新增业务语义、页面特判或后端契约，停止本批并另行立项。

## 验证顺序

1. 完整候选 fingerprint 与范围 manifest。
2. 最早相关 static/guard 与非零 targeted tests。
3. `verify.frontend.primitive_adapter.unit`、相关 shell/page/theme guards、strict typecheck。
4. `verify.frontend.quick.gate`。
5. 冻结 clean candidate 后，通过 `local.dev.candidate.frontend.*` 运行只读浏览器交互与同视口矩阵。
6. 文档和生成报告核对。

## 停机条件

- 工作树出现非本批变更或候选身份漂移。
- 需要跨出 frontend/P4 evidence 范围，或改变契约、启动链、路由、权限、业务数据。
- 任一已知 static/backend/identity/normalized-contract gate 失败。
- targeted test 收集为 0、真实页面交互失败或运行环境身份不可信。

## 当前状态

- Baseline/起始 HEAD：`314a0ac2ccdbc4793455a323620cfc988dd4e7b2`。
- 启动链：不变。
- contract/schema：不变。
- default_route：不变。
- public intent：不变。
- 产品候选 HEAD：`df3227c38e908b883ed45553e9511b03b59a3348`。
- 最终证据候选 HEAD：`c755e5515b9f876565080f4c0ced1c87d5f12cf0`（产品代码仍冻结在 `df3227c38e908b883ed45553e9511b03b59a3348`）。
- 状态：前端表达阶段的本地验收与证据已冻结；发布资格仍为 `verification_pending`。

## Step A 结果：官方组件行为

- Input：我的工作真实搜索输入获得焦点，4 张工作卡筛到空态后通过公开清除能力恢复为 4 张，输入值为空。
- Select：真实 `ScSelect` 通过鼠标从“最近更新”切到“金额从低到高”，再通过键盘切回其他选项；焦点保留，选项数量非零。
- Card：4 张真实工作卡均通过公开 `bodyClassName` 投影正文 class；付款只读详情没有 Card actions slot，因此未将不存在的插槽当作通过条件。
- Alert：受控只读失败显示官方 Alert driver、description 和 1 个 operation；在激活前安装 `my.work.summary` 请求监听，重试按钮先获得焦点，键盘触发后页面恢复且请求精确为 1 次。恢复成功与 exactly-once 使用同一轮证据，不再由“等待一个成功响应”推断。
- 结构化按钮（正式页面）：真实工作指标按钮的鼠标、Enter 各只触发 1 次并更新 `aria-pressed`，焦点保持正确；这里不再声称覆盖 disabled/loading。
- `ScButton` disabled/loading（组件浏览器测试）：父组件响应式状态通过真实 `ScButton` props 依次设置 disabled、loading 和恢复态；目标 DOM 由组件投影出 `disabled`、`aria-disabled`、`aria-busy`、`data-loading` 及 loading label，两个阻断态点击计数均不增加，恢复后仅增加 1。验证脚本禁止直接给被测 DOM 写这些属性。证据由 `make verify.frontend.overlay_lifecycle.browser` 生成，明确属于组件测试，不冒充正式页面验收。
- 表单错误：材料入库只作为组件样本；空项目触发错误摘要并把焦点移到 `project_id`，未保存数据。
- light/dark × 1440×960/390×844 全部通过；两份摘要的 `mutationCount=0`，`errors=[]`，`failures=[]`：
  - `artifacts/playwright/frontend-official-component-behavior-light-df3227c3/summary.json`
  - `artifacts/playwright/frontend-official-component-behavior-dark-df3227c3/summary.json`

### 最终证明修正

- 组件 props 证据：`make verify.frontend.overlay_lifecycle.browser` PASS，共 10 项非零场景；`structuredButtonProps.initialStructuredActivations=1`，disabled/loading 两态均保持为 1，恢复后为 2。
- 正式页面 exactly-once 证据：
  - `artifacts/playwright/frontend-final-component-behavior-light-1440-390-c755e551/summary.json`
  - `artifacts/playwright/frontend-final-component-behavior-dark-1088-320-c755e551/summary.json`
- 两轮均为 `pass=true`、`mutationCount=0`、`errors=[]`、`failures=[]`；桌面和移动的 Alert 均记录 `operationCount=1`、`retryRequestCount=1`、焦点正确并恢复成功。

## Step B 结果：全局表达

- `ScPanel` 新增通用 `workspace` tone；“我的工作”取消外层套卡，筛选区改为次级工作带，记录卡继续作为主要表面。
- 首页桌面端改为“待办 + 状态”首行、完整宽度入口区次行；常用入口为双列，最近访问保持独立区域，修复右侧窄长入口列和左侧无效空白。
- `ProductPageHeader` 的 task/workspace 表达统一为透明背景和单一下边界；通用 ContractForm 命令栏同步消费该层级，桌面和窄屏均移除页头卡 + 主体卡的重复框层。
- 首页、我的工作、付款列表、付款详情、收入合同工作区在 light/dark × 1440×960/390×844 共 20 个页面样本均无根横向溢出；标题、状态、返回/更多/主要操作可见可达。
- 两份最终摘要均 `pass=true`、`mutationCount=0`、`errors=[]`、`failures=[]`：
  - `artifacts/playwright/frontend-global-expression-after-light-df3227c3/summary.json`
  - `artifacts/playwright/frontend-global-expression-after-dark-df3227c3/summary.json`
- 同视口 before 基线保留在 `frontend-global-expression-before-{light,dark}-af9df37b`，after 保留在 `frontend-global-expression-after-{light,dark}-df3227c3`。

### 最终视觉复核与冻结

- 最终证据候选在 light 1440/390 与 dark 1088/320 下覆盖首页、我的工作、付款列表、付款详情、收入合同层级工作区，共 20 个 route/viewport 样本。
- 自动结果全部 `pass=true`、根横向溢出为 0、浮层残留通过、页头操作通过、可见操作数量非零，且 `mutationCount=0`、`errors=[]`、`failures=[]`。
- 对 20 张候选截图完成人工复核：标题、正文、状态、主要操作、滚动与窄屏横向访问未发现阻断；没有因留白或个人审美继续修改产品。
- 冻结证据：
  - `artifacts/playwright/frontend-final-expression-light-1440-390-c755e551/summary.json`
  - `artifacts/playwright/frontend-final-expression-dark-1088-320-c755e551/summary.json`

## 门禁与结论边界

- `make verify.frontend.quick.gate`：PASS；严格类型、构建、组件适配、页面身份、表单页头、工作台、主题及生成库存均通过。
- 最终 P4 修正的受影响门禁：`python3 -m unittest scripts.verify.test_local_dev_candidate_frontend`（9 tests）、`make verify.frontend.overlay_lifecycle.unit`（10 tests）、`make verify.frontend.primitive_adapter.unit`（27 Python tests，另含 46 个 JS component scenarios）及 `make verify.frontend.overlay_lifecycle.browser`（10 browser scenarios）均 PASS；没有以零测试命令满足门禁。
- 官方设计库存保持四项零缺口：内部 vendor selector、视觉字面量、未知项目 token、孤立 appearance variant 均为 0。
- 本批结论是“官方组件能力在本轮影响面正确使用，且代表页面的全局表达已改善”。它不是全业务流程、全角色、业务写入、release 或生产环境验收完成。
- 契约依赖仍为既有 `login → system.init → ui.contract` 消费链；本轮没有改变 schema、public intent、启动链或 default route。disabled/loading 结论来自真实组件 props 的浏览器测试，Alert exactly-once 来自正式页面的请求计数，两者不互相替代。
- 未升级模块、未 reset fixture、未保存业务数据，未执行 push、PR、merge 或 release。
