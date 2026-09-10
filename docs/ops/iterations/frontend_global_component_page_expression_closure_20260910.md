# 全局组件能力与页面表达统一收口

日期：2026-09-10
状态：`development_complete_pr_pending`（独立源码与留存证据复核通过，待 PR）

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

## 配置边界表

| 能力 | 是否可配置 | 允许值 | 权威来源 | 校验层 | 非法或缺失配置处理 |
|---|---|---|---|---|---|
| 主题模式 | 可由用户本地偏好配置 | `light`、`dark`、`system` | `sc_theme` 本地偏好与系统 `prefers-color-scheme` | `theme.ts` 联合浏览器运行证明 | 未知值回落 `system`，不写业务数据 |
| 减少动画 | 不提供业务配置；只消费系统偏好 | `reduce`、`no-preference` | `prefers-reduced-motion` | 应用生命周期测试、浏览器根属性 | 缺失时按 `no-preference`；不从路由或业务契约推导 |
| TDesign 动画投影 | 不提供运行时任意配置 | 普通态显式 include `ripple/expand/fade`；减少态显式 exclude 同集合 | 安装锁定的 TDesign 1.20.5 公开 `ConfigProvider.globalConfig.animation` | 真实 Provider 动态组件测试与严格类型 | 编译/测试失败即阻断；不复制 locale、尺寸等其他官方默认值 |
| 章节身份、顺序与显隐 | 沿用既有契约配置，本专题不新增配置入口 | 仅消费实际可见、稳定章节节点 | `ui.contract`/native view 的既有结构与隐藏规则 | section navigation 非零测试和内容级浏览器证据 | 缺失章节不生成入口；不按模型名、字段名或字段语义猜测，隐藏章节保持隐藏 |
| 字段跨度与列数 | 仅消费已有结构表达，不新增配置入口 | 契约已声明的结构/跨度；共享响应式规则在窄屏收敛为单列 | native form contract 与现有 renderer | canonical presenter、field alignment 边界测量 | 非法结构由既有 normalizer/renderer 安全回落并由守卫暴露；不得逐字段补 margin |
| 共享几何规范 | 不可由业务或低代码任意配置 | 已登记的 page/frame/content/spacing token | design-system token、page pattern 和共享组件 | token/official design inventory、页面结构与边界测试 | 未知 token、视觉 literal 或内部 vendor 选择器作为工程缺口阻断 |
| 明细表列 | 可由现有契约声明 | 契约提供的可见列、标题、顺序与类型 | 关系 subview/contract | detail collection model/guard 与桌面/移动浏览器检查 | 缺失时只使用既有受控回落；不由字段名猜测业务重要性 |

章节/列数配置决定“有什么、按何种契约顺序呈现”；共享几何只决定这些内容在已批准视口中的对齐、收缩和阅读宽度。二者不能互相替代，本批没有创建新配置系统。

## 执行批次

1. A：根级 ConfigProvider、单例主题/减少动画监听、公共出口及隔离传播测试；定向验证后本地提交。
2. B：共享页头内部责任与页面 frame/pattern/body 边界；删除与实际 DOM 脱节的深层补丁；定向验证后本地提交。
3. C：明细与协作区层次、五类组件接管审计及确认的不必要接管；定向验证后本地提交。
4. 联合复核：在一个冻结完整指纹上执行 Quick、严格类型、官方组件守卫、非零定向测试和受管 local.dev 浏览器矩阵；人工审看首屏、中段、底部。

每批若失败，只修所属层并从最早失效门禁恢复；回滚按 C→B→A 逆序，不需要数据库、容器或契约回滚。

## A 批结果

- `App.vue` 以 TDesign 1.20.5 公开 `ConfigProvider.globalConfig` 包住完整路由树，登录、业务壳和嵌入关系页面拥有同一配置祖先；公共出口只新增 ConfigProvider 及其公开类型。
- 全局配置不复制 locale、`classPrefix` 或控件尺寸。动画只声明经 1.20.5 审计的 `ripple`、`expand`、`fade`：减少态显式排除，普通态显式恢复。真实 Provider 动态测试证明，挂载后从减少态改为空对象不能可靠清除既有嵌套排除值，因此普通态的显式恢复是必要兼容边界，不是全量复制官方默认配置。
- 系统深浅色与减少动画监听由应用根运行时幂等拥有：`main.ts` 负责启动及 HMR dispose，`App.vue` 的 mounted/unmount 生命周期负责正常挂载释放；路由组件不注册或释放。根节点同时记录解析主题和减少动画状态，已有 CSS reduced-motion floor 保持有效。
- 隔离测试升级为 31 项断言：通过生产公共出口挂载真实 ConfigProvider 与 TDesign Tag；普通、异步、Teleport 消费者完成普通→减少→普通动态更新，嵌套局部配置保持；路由子树切换不重复注册，应用卸载实际释放，重新挂载只恢复一次并同步当前系统偏好。
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
- `verify.frontend.quick.gate` 在补证候选上全量通过，包含严格类型、production build、官方组件守卫和本专题 31 项非零真实 Provider 组件测试；该隔离测试已接入 Quick、PR unit 与 release unit。
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
- 我的工作真实 Input/Select/Card/结构按钮在鼠标和键盘路径均通过，清除后恢复原记录数，单次触发为 1；首页 Alert 每个视口记录 `retryRequestCount=1`。原候选的 16 项初始传播测试已由补证候选的 31 项真实 Provider 动态测试取代。
- 主题在原 36 个业务页面样本中分别解析为 light/dark。补证候选又在登录页与无 `AppShell` 的嵌入表单实际记录 `system→dark/reduce`，嵌入页挂载后完成 dark/reduce→light/no-preference→dark/reduce；因此登录、业务壳和嵌入路由都已取得运行证据。
- overlay lifecycle 10 项定向测试覆盖嵌套关闭、busy、焦点栈、深度滚动锁与单次触发；关系请求旧响应失效继续由既有 professional relation lifecycle 非零门禁负责。本专题未改变这些业务保护。
- 人工抽查最终截图的首屏、中段和底部：吸顶页头保持不透明且未覆盖标题/字段/动作；320px 控件与章节栏完整；明细横向滚动仅发生在已声明的表格区域；协作区保留的章节、关注者交互、附件拖放和逐条记录边界均有明确用途。

### 补证候选与三项诊断归因

- 最终补证候选：`c442f731adb6cd23e3adc77811c1c895f137a5fe`；完整指纹 `93bca159a932f41910a5eb3525a4c781b91a684d85af1362269605a4263571dd`，7366 paths；`artifacts/fingerprints/global_component_capability_exit_candidate_c442f731.json`。
- 定向浏览器摘要：`artifacts/playwright/global-capability-exit-system-1088-320-c442f731/summary.json`；1088/320、系统主题、桌面/移动各 4 个样本，`pass=true`、`mutationCount=0`、errors/failures empty。候选服务已停止。
- 材料关系弹层：触发“搜索更多”后实际请求为 `intent=api.data`、`op=list`、`model=project.project`、空搜索词、limit 80，权威 domain 为 `[(id, =, -1)]`；响应 HTTP 200、0 records、无 error。界面同步显示空态、选择按钮禁用。分类为**数据前提不足/权威 domain 排除全部记录**，归属既有契约/数据前提，不是弹层请求或渲染故障；本专题不改 domain、契约或数据。
- 材料集合查询栏：页面实际具有一个可见搜索输入，旧脚本把两个可能的语义容器合并后要求容器唯一，错误地把容器身份歧义归为控件缺失。脚本改为先锁定唯一可见 `input[type=search]`，再反查最近语义 owner。桌面/移动均完成 1 record→无匹配空态→清除→1 record，URL 搜索参数同步恢复。分类为**P4 脚本选择器假设**，页面能力存在，无产品修改。
- 合同层级搜索：生产实现对当前已加载 `visibleRows` 做客户端过滤，不发搜索请求。旧脚本用全局 document 选择器等待零行，可能命中页面其他表格；改为绑定当前 `HierarchicalWorksheet` 根。桌面/移动均完成 46 records→项目范围 1 record→无匹配 0 records/无打开动作→清除恢复 1 record，并保留选中记录。分类为**P4 等待作用域错误**，不是数据、过滤或渲染问题。
- 首次补证运行在页面请求前因把 `emulateMedia` 调在 BrowserContext 而停止；改用当前 Playwright 支持的 Page API 后重新冻结并通过。该历史失败不计入候选通过证据。
- 未运行多角色、真实写入、acceptance、升级兼容、发布或 PR/CI。以上诊断未引发契约、数据、业务流程或门禁降级。

### 独立复核结论

- 复核方式：只读核对源码差异、目标记录、阶段报告以及绑定 `c442f731…` 的既有浏览器摘要；没有重新启动候选或重跑测试。
- 结论：真实公开 ConfigProvider 动态恢复、应用卸载/重新挂载/HMR 释放、登录与嵌入页主题证据、三项查询诊断归因均与实现一致；此前四项补证问题关闭。
- 范围限定：这是开发阶段的表达收口和已有证据独立复核，不是全系统业务验收、merge-ready 或 release-ready 结论。
- 未覆盖：多角色、真实保存/审批、非空权威材料关系数据集选择、acceptance、升级兼容、PR exact-head CI 与发布验收。

## 本地结论

共享表达规则、官方能力接管记录、代表页面一致性、字段对齐基线、动态 Provider 传播、生命周期释放和三项诊断归因均已完成本地验证并通过独立源码/留存证据复核。开发阶段表单表达收口完成，下一状态为待 PR；不再追加页面美化。当前仍不宣称 merge-ready、release-ready、已发布或全系统业务交互已验收。
