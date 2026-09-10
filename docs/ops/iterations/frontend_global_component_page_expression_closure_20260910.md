# 全局组件能力与页面表达统一收口

日期：2026-09-10
状态：`verification_pending`（本地实现与联合验证完成，等待独立复核）

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

## B 批结果

- 核对实际 DOM 后确认 `ContractFormPage.css` 中 `.template-page-header-main/-status/-actions` 等选择器没有对应节点；全部删除，并用 guard 禁止页面重新通过 `:deep(.template-page-header…)` 修补共享页头内部。
- task/workspace 页头的吸顶、背景、边界、阴影、内部排列与无状态动作归 `ProductPageHeader`；模板页头不再额外制造底部 margin。合同状态、HUD 和 intake 文案留在 `ContractFormProductHeader` 自身 scoped style。
- `ContractFormPage` 明确消费 `.sc-product-workspace-stack`。页面框架继续负责 gutter，content-layout pattern 继续负责既有阅读宽度决策，正文 `.form-grid` 统一消费 `--sc-product-panel-gap`；没有改变上一批字段槽位或控件尺寸。
- 定向门禁：product page header 28 cases、product page pattern 12 cases、3 个 header adapter guard 及严格类型全部通过；浏览器吸顶/首中底复核留在最终冻结候选统一执行。

## C 批结果

- 明细集合统一暴露 heading、title、count、summary、actions 和 desktop-table/mobile-cards/empty 内容身份；查看态与录入态继续共用同一标题/数量层次，桌面表格边界仍只服务横向比较，移动端继续使用有标题卡片。
- 协作区根从“额外 muted 卡片”改为正文同级章节：只保留有分隔用途的顶部边界与章节标题。动作区不再另套无用途背景/边框；上传拖放区和逐条时间线仍保留有交互/记录分隔用途的边界。加载更多布局移出内联 style。
- 未改变附件归属：关系明细的“单据附件”和协作区的“协作附件”继续分别存在并保留原语义说明。
- 组件接管 inventory 新增五类受影响能力的结构化评估，并绑定 TDesign `1.20.5` 与完整生产源摘要：

| 组件 | 官方公开能力 | 当前接管结论 | 理由与验证 |
|---|---|---|---|
| Dialog | visible、esc/overlay close、scroll-through、destroy | 保留共享生命周期接管 | 嵌套关闭、busy、焦点栈和深度滚动锁必须单一归口；overlay unit + 受影响浏览器旅程 |
| Drawer | visible、esc/overlay close、scroll-through、destroy、size | 保留共享生命周期接管 | 与 Dialog 共用嵌套 exact-once/focus/scroll 权威；overlay unit + 嵌套浏览器旅程 |
| Select | value/options/filter/loading/empty/search/popup | 保留 ARIA 与请求竞态接管 | 原生控件语义需投影，旧响应失效属于关系消费者而非官方组件；primitive/relation/browser 验证 |
| DatePicker | value/disabled/readonly/time/change | 无行为接管 | 官方组件拥有弹层与键盘，适配层仅归一契约值和共享宽度；类型/守卫/表单旅程 |
| Table | data/columns/row/size/loading/scroll/width/attributes | 保留横向浏览接管 | 1.20.5 无公开 scroll-region element/ref 可提供边界状态、焦点语义与步进滚动；inventory + 表格边界/键盘验证 |

- 定向门禁：明细模型/守卫 31 项、协作模型/守卫 73 项、接管 inventory 6 项、overlay lifecycle 10 项及严格类型全部通过。没有修改契约、权限、动作、隐藏章节或业务数据。

## 联合静态复核

- A/B/C 本地提交分别为 `c752482e`、`39f075b5`、`2ac68f66`；三批产品实现边界保持独立。
- `verify.frontend.quick.gate` 全量通过，包含严格类型、production build、官方组件守卫和本专题 16 项非零隔离组件测试；该隔离测试已接入 Quick、PR unit 与 release unit。
- 主题运行时守卫共 12 项断言，覆盖两类系统 media query、幂等注册、显式主题优先及成对释放。守卫读取无框架依赖的主题运行时；Vue 响应式 ConfigProvider 配置由独立模块消费，避免验证脚本伪造框架运行时。
- 页头/表单守卫已跟随责任迁移：吸顶不透明表面检查 `ProductPageHeader`，并明确禁止页面 CSS 重新深穿共享页头；未重新调整字段几何。
- 三份组件/表达 inventory 已按当前生产源摘要刷新，官方组件内部选择器、literal、未知 token 与 orphan 缺口均为 0。
- 此处静态结论本身不替代下述受管 local.dev 页面矩阵、人工首屏/中段/底部复核与最终完整指纹，也不替代独立复核。

## 冻结候选联合浏览器复核

- 冻结候选：`07758bd72c11e41157b3125b4d314ba7874c606b`；完整指纹 `64220630eaa650bc0f39b04686a310306de892c85976bf8c4d3b3377bf7f972c`，7365 paths；`artifacts/fingerprints/global_component_expression_candidate_07758bd7.json`。
- 受管载体：`local.dev.candidate.frontend.*`，项目 `sc-local-dev`、数据库 `sc_dev_demo`、API `18081`、候选前端 `5176`；候选服务已停止。
- 明色 1440/390：`artifacts/playwright/global-component-expression-final-pass-light-1440-390-07758bd7/summary.json`。
- 暗色 1088/320：`artifacts/playwright/global-component-expression-final-pass-dark-1088-320-07758bd7/summary.json`。
- 两份最终摘要均为 `pass=true`、`mutationCount=0`、errors/failures empty；每份含桌面/移动各 9 个路由样本，合计 36 个样本：主页、我的工作、付款只读、付款编辑、合同只读、合同新建、材料新建、材料集合和合同层级工作区。
- 五类表单在四种宽度均通过正文/导航/字段/控件/允许滚动区边界检查。原收入合同新建每个视口仍测得 24 个 eligible 控件，frame failure、row baseline failure 和强制跨组 grid spread 均为 0；付款只读 row baseline failure 为 0。没有裁切、隐藏字段或缩字号。
- 所有已生成的章节入口均完成名称、稳定目标身份、内容类型、当前态、完整可见和吸顶无遮挡校验。材料临时明细在桌面表格与移动卡片中完成必填聚焦后删除，浏览器请求计数保持 0 次业务 mutation。
- 我的工作真实 Input/Select/Card/结构按钮在鼠标和键盘路径均通过，清除后恢复原记录数，单次触发为 1；首页 Alert 每个视口记录 `retryRequestCount=1`。ConfigProvider 普通、异步和 Teleport 传播及局部覆盖由 16 项隔离组件测试证明。
- 主题在 36 个业务页面样本中分别解析为 light/dark。登录和嵌入页面共享同一个 `App.vue` Provider/主题根，不依赖业务壳挂载；系统主题、减少动画及监听幂等/释放由 12 项运行时断言证明。这里是根结构与隔离运行时证据，不冒充登录/嵌入业务旅程验收。
- overlay lifecycle 10 项定向测试覆盖嵌套关闭、busy、焦点栈、深度滚动锁与单次触发；关系请求旧响应失效继续由既有 professional relation lifecycle 非零门禁负责。本专题未改变这些业务保护。
- 人工抽查最终截图的首屏、中段和底部：吸顶页头保持不透明且未覆盖标题/字段/动作；320px 控件与章节栏完整；明细横向滚动仅发生在已声明的表格区域；协作区保留的章节、关注者交互、附件拖放和逐条记录边界均有明确用途。

### 诊断与未覆盖项

- 一次集合附加搜索旅程因当前材料集合没有脚本要求的唯一查询栏而停止；最终矩阵只验证该页面实际存在的加载、toolbar、navigation、移动卡片和布局能力，不将该搜索旅程计为通过。
- 一次层级工作区“无匹配搜索”诊断没有进入脚本预期的零行状态；最终矩阵保留其页面加载、主题、320px 明确横向表格浏览及主要操作覆盖，不声明该既有搜索旅程通过。
- 材料“搜索更多”弹层在当前数据下正常打开且无残留，但返回 0 个可选结果，因此没有把“选中已有结果”计为本候选通过；最终通过摘要不包含这一数据前提断言。
- 未运行多角色、真实写入、acceptance、升级兼容、发布或 PR/CI；独立复核尚未执行。以上诊断未引发契约、数据、业务流程或门禁降级。

## 本地结论

共享表达规则、官方能力接管记录、代表页面一致性和字段对齐基线均已落到冻结候选并完成本地联合验证。A/B/C 产品提交与最终 P4 验证提交可以保留；本专题进入独立复核准备状态，不再追加零散美化。只有独立复核通过后，才能整理并授权 PR 交付，当前不宣称已合并、已发布或整个系统交互已验收。
