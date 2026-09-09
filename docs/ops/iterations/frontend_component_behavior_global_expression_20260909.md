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
   - structured Button：首页快捷入口/我的工作指标的鼠标与键盘触发、焦点、disabled/loading 原生阻断与单次触发。
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
- 状态：active，先执行 Step A。
