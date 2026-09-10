# 全局组件能力与页面表达统一收口

日期：2026-09-10
状态：`active`

## 基线与边界

- 冻结起点：`fe22402edad0c8d72445f07e5af61e5ce67b2884`；分支 `feature/form-page-structure-professionalization-v1`；工作区干净。
- 完整基线指纹：`9efb3b6bf6e5b13ca56715f61a8d9341ae93c5df141d40465ee77bd6ad8fb69e`，7361 paths；文件 `artifacts/fingerprints/global_component_expression_baseline_fe22402e.json`。
- 上一批字段对齐结论保持 `verification_pending`。本专题复用其 24 个控件、跨组列线和付款只读行基线证据，但不把本地验证冒充独立复核。
- Formal Product Layer：P0 通用前端机制；P4 只承载守卫、隔离测试和浏览器证据。
- Layer Target：应用根配置、共享页面组合、design-system adapter 与通用 form/detail/collaboration renderer。
- Why Here：配置传播、主题生命周期、共享页头、阅读宽度和组件交互保护属于通用前端责任。
- Why Not Elsewhere：不改后端契约、schema、权限、动作、金额口径、隐藏章节、行业/客户默认、低代码运行时配置或数据库。
- Blast Radius：登录/业务/嵌入路由根、共享页头、表单正文、明细/协作区，以及 Dialog、Drawer、Select、DatePicker、Table 适配器。
- 启动链与契约：不改变 login、system.init、ui.contract、默认路由或 schema 消费，只在既有 Vue 根和共享表达层接入。

## 表达归属表

| 层级 | 现有责任组件 | 统一控制面 |
|---|---|---|
| 外壳 | `App.vue`、`AppShell.vue`、`.sc-page-frame/.sc-product-page-frame` | 路由根、页面画布与外边距；`--sc-page-padding`、`--sc-workspace-frame-max` |
| 页头 | `ProductPageHeader.vue`，模板 `PageHeader.vue` 与 `ContractFormProductHeader.vue` 只做语义/动作适配 | 页头内部排列、尺寸、状态与动作间距；`--sc-space-*`、`--sc-product-panel-radius` 和语义色 token |
| 正文 | 既有 page patterns 与 `ContractFormPage.css` 的正文根 | pattern 控制阅读宽度，正文控制章节间距；`--sc-content-*-max`、`--sc-product-workspace-stack-gap`、`--sc-product-panel-gap` |
| 字段 | native form renderer、`ProfessionalBaseFieldControl` 及专业字段适配器 | 字段槽位、标签/控件基线、公开控件根；沿用冻结候选的 field grid 与 control token，不再调整已达标几何 |
| 明细 | `X2ManyRelationRenderer.vue`、`ProfessionalDetailCollectionControl.vue` | 集合标题、数量、动作、桌面比较表与移动卡片；共享章节间距、边界和表格 token |
| 协作区 | `NativeCollaborationPanel.vue` 及现有子组件 | 协作标题、附件/日志/审计分区和必要边界；共享章节/表面 token，不另建样式体系 |

## 官方能力对照表（TDesign Vue Next 1.20.5）

| 能力 | 采用方式 | 原因与验证 |
|---|---|---|
| locale、`classPrefix`、控件默认尺寸 | 官方默认值 | 不复制官方默认配置；隔离测试确认根 provider 未臆造全局尺寸或 locale 覆盖 |
| 动画 include/exclude | 根级 `ConfigProvider.globalConfig.animation` 公开 API | 仅用于系统“减少动画”偏好；普通、懒加载和弹层组件验证注入传播，局部显式配置仍优先 |
| Dialog/Drawer 关闭、焦点与滚动生命周期 | 自行接管，底层组件仍走公开 props/events | 现有嵌套弹层、busy、dismissible 和焦点恢复保护需要统一生命周期；验证嵌套关闭、焦点/滚动恢复和单次触发 |
| Select 搜索与清除 | 公开 API + 适配层请求去重/旧响应保护 | 官方组件不拥有业务请求竞态；验证清除、旧响应失效和一次操作一次请求 |
| DatePicker 值与范围 | 公开 API 适配 | 保留契约值格式和局部显式 props；隔离测试验证局部配置不被全局覆盖 |
| Table 渲染与横向比较 | 公开 API；必要的滚动边界由适配层接管 | 明细表需在窄屏保留受控横向比较，不能用裁切隐藏；登记具体 DOM 依赖并用边界/滚动测试证明必要性 |
| 页面布局、字段对齐、自定义组件层次 | 项目共享组件与 token 自行负责 | ConfigProvider 不负责项目布局；用结构测试、边界测量和同视口截图验证，不归因于官方全局配置 |

## 执行批次

1. A：根级 ConfigProvider、单例主题/减少动画监听、公共出口及隔离传播测试；定向验证后本地提交。
2. B：共享页头内部责任与页面 frame/pattern/body 边界；删除与实际 DOM 脱节的深层补丁；定向验证后本地提交。
3. C：明细与协作区层次、五类组件接管审计及确认的不必要接管；定向验证后本地提交。
4. 联合复核：在一个冻结完整指纹上执行 Quick、严格类型、官方组件守卫、非零定向测试和受管 local.dev 浏览器矩阵；人工审看首屏、中段、底部。

每批若失败，只修所属层并从最早失效门禁恢复；回滚按 C→B→A 逆序，不需要数据库、容器或契约回滚。

## A 批结果

- `App.vue` 以 TDesign 1.20.5 公开 `ConfigProvider.globalConfig` 包住完整路由树，登录、业务壳和嵌入关系页面拥有同一配置祖先；公共出口只新增 ConfigProvider 及其公开类型。
- 全局配置在普通偏好下为空，继续继承官方 locale、`classPrefix`、尺寸和动画默认；仅当系统要求减少动画时通过公开 API 排除 `ripple`、`expand`、`fade`。
- 系统深浅色与减少动画监听由 `bootTheme()` 在应用生命周期幂等注册，`AppShell` 不再随业务壳挂载/卸载注册主题监听。根节点同时记录解析主题和减少动画状态，已有 CSS reduced-motion floor 保持有效。
- 隔离测试共 16 项断言：单例注册/释放、系统主题响应、减少动画响应，以及普通、异步、Teleport 弹层和嵌套局部配置的传播/覆盖全部通过。
- 定向门禁：`verify.frontend.global_component_capability.unit`、严格类型、production build、primitive adapter、rendering detail 与 official design alignment 均通过；未运行浏览器全矩阵或写业务数据。
