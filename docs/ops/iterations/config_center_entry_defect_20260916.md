# 配置中心业务对象、配置生命周期与操作体验完善

## 本批六包缺口表（持续更新）

当前结论：六包集中产品复核通过，独立复核的两项整改已关闭，正在完成最终集成门禁；未集成、未部署。最终冻结身份和receipt见外部收口索引。

| 工作包 | 已通过、复用 | 本批修复（已实施） | 明确不支持 |
| --- | --- | --- | --- |
| 业务对象目录 | 正式配置入口承接、排除工作台自身 | 使用正式导航权限目录、入口身份与所属模块 | 技术对象设计 |
| 作用域一致性 | 稳定 action/view 节点 | 宿主菜单和目标菜单分离，拒绝冲突，切换/刷新/返回一致 | 任意跨对象套用草稿 |
| 来源与状态 | 实际契约来源、当前公司可见统计及258组成 | 未选对象不显示检查比例，配置检查不称交付 | 记录状态代替页面验收 |
| 编辑能力 | 标签、同区域排序、分组、显隐及安全反例 | 真实能力说明与反馈 | 自定义字段、跨区域拖拽 |
| 生命周期 | 既有发布回滚与预览无写入 | 离开保护、撤销清空、继续编辑、过期/冲突恢复 | 业务数据回滚 |
| 统一交互 | Sc设计器、390px预览 | 目录与状态/失败反馈、集中桌面窄屏观察 | 全系统改版 |

边界：P0 smart_core 配置目录/作用域及通用前端消费；P3受管测试配置；P4既有观察器。标准平台机制，不增加P1行业或P2客户规则。影响配置中心与普通表单设置；验证正式666/862、另一模型和技术/无权反例。L0=48151d07+上述批次dirty；L1 iteration、L2相关单测先行；仅handler变化无需schema升级，L3受管restart/health，L4只验证变化旅程，L5待集中复核收敛。原章节保留历史证据，不作为本批六包全部通过结论。

## 身份与范围

分支 `fix/config-center-entry-routing`，基于冻结 U-C3 `48151d07b61c6f42bc74008c6c5762334e8fb5a3`，本记录为开发态 dirty。U-C3 原分支、一次成功 Quick、独立复核及15份已验证外部归档不修改，尚未推送PR。台账保持主线44、本地42。

Formal Product Layer=P0；Layer Target=授权后的配置工作台路由承接；Module=通用前端router/actionRoutePolicy。配置产品入口属于平台路由机制，不是P1证照/制度业务规则或P2偏好。复用既有工作台与后端声明，禁止用JSON白名单放宽掩盖入口错误。P4仅扩展既有受管低代码观察器：menu431/action737精确身份、只读浏览器模式、配置/业务指纹回读；不新增环境或凭据。

## 实际失效层

用户在5176观察JSON组件错误。受管5174（sc-local-dev/sc_dev_demo）对照确认：menu431的XML ID是`smart_construction_core.menu_sc_business_config_workbench`，名称“表单配置”；action737为`action_sc_business_config_workbench`，模型`ui.business.config.contract`，context已声明`sc_web_route=/admin/business-config`及root menu。

- `/m/431`正确进入专用工作台。
- `/a/737?menu_id=431`却进入通用列表；实际点击“新建”进入`/f/ui.business.config.contract/new?menu_id=431&activity_page_id=…`，出现`PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH:sc.input.text:json`。
- 手工打开带action737/menu431的通用new也可复现；专用工作台可正常打开。

具体字段：`source_authority_json`、`contract_json`。原生descriptor为type/widget=json；`unified_page_contract_v2_assembler._canonical_widget_type`不识别json，回退`_widget_type_from_field`的input，再由`_component_key`映射为sc.input.text。最终契约已含错配，前端类型校验正确拒绝。普通JSON记录编辑不属于该正式入口用途，本次不实现通用JSON编辑、不改映射白名单或取消校验。

首次路径分歧：MenuView/openAction已有配置工作台承接，router授权后的直接action/record路由未统一调用，ActionViewShell仅特殊处理菜单配置，列表新建继续通用form。以上router/service/ActionView/assembler文件在main225a56bf到U-C3冻结48151d07之间无差异，结合5174复现可确认非U-C3引入的回归。5176运行SHA未独立取证，不冒称两个服务相同候选；不操作其历史环境。

## 最小修复与验证

把既有配置action判定与路由解析提取为无运行副作用的`actionRoutePolicy`，原action_service保持导出兼容。router在既有route authority及上下文检查完成后应用相同规则，menu/action/raw new/record进入专用工作台。保留后端作用域及root menu；记录页activity身份不带进工作台。模型不匹配、无权、无authority及工作台自身不重定向；业务表单内嵌设置保持原路径。

L0：基线HEAD与明确dirty范围；L1 `make ci.local.iteration`通过；L2 `make verify.nav.pro01r.route_authority.unit verify.frontend.typecheck.strict`通过，新增10项配置路由反例及原授权测试。后端业务/配置机制、数据与权限无改动，不升级模块、不reset、不运行新的Quick。浏览器只通过既有`local.dev.form_lowcode.browser`，结果见`artifacts/config-center-entry/`。

原始四路径诊断：`browser/original-four-routes.json`；真实列表点击新建：`browser/before-fix-new-click.json`；具体契约：`browser/configuration-form-contract.json`。诊断脚本成功仅指观察完成，类型错配仍记产品失败；不能把工具退出0称为页面通过。修复后结果另由entry-report.product_status声明。

早期入口修复阶段不发布配置、不保存配置草稿、不修改业务数据；后续整组六包受管写入范围见文末。该阶段为定向修复/产品复核准备，不借用U-C3 Quick冒称本修复已冻结或主线集成。


## 定向结果

- 原四路径与产品行为见`browser/routes-passed-observer-rejected.json`，修正观察器后的续验见`fixed-browser-resume2.log`；早期`entry-report.json`曾被统计观察覆盖，不再把它作为原四路径报告。四条路径（menu431、action737、raw new、专用工作台）均进入专用工作台；返回到`/s/workspace.home`；证照新建“更多操作→表单设置”仍进入内嵌设计器，未被入口修复截走。
- 初次修复观察的所有页面行为已通过，最后观察器误把`change_set.open`列为禁止项而失败，原报告保留在`routes-passed-observer-rejected.json`。代码显示该调用为工作台建立/恢复owner作用域的未发布会话，并非发布；不更改产品行为，补充配置记录及全部本人草稿write_date/state的前后回读，允许会话恢复。补验一致，包括草稿133/134未变；不宣称早先诊断全程数据库绝对零写入，工作台可能自动建立空会话。没有stage/publish/rollback/save请求，没有业务保存。
- 扩展scope首次因datetime无法JSON序列化在浏览器前停止；添加显式序列化后仅续验受影响的scope与会话检查，原失败日志保留。路由产品及类型检查输入未变，原四路径结果承接，不重跑业务配置旅程。
- 最终日志：`fixed-browser-resume2.log`、`final-static.log`、`targeted.log`；截图：`browser/entry-0.png`与`browser/business-form-settings.png`，其他原四路径截图保留。此阶段不生成交付指纹/Quick，不借用U-C3冻结身份称本修复已验收。

现场：[表单配置正式入口](http://127.0.0.1:5174/m/431)；[旧新建路径（应承接工作台）](http://127.0.0.1:5174/f/ui.business.config.contract/new?menu_id=431&action_id=737)。当前HEAD仍48151d07，加独立未提交入口修复；等待集中产品复核，不混入U-C3三提交。主线未集成、未部署、89入口交付未完成。


## 对象选择与统计语义收口

本节与入口修复同批，不改U-C3冻结分支。P0归属：`business_config_surface`只读汇总、工作台对象选择和最终契约来源呈现；不改底层渲染/配置编译/发布/ACL。采用`odoo-module-change`约束；没有模型/schema数据库变化或data XML更新，不需模块升级。运行更新只执行`local.dev.restart`，目标为既有平台内部开发演示租户sc-local-dev/sc_dev_demo，精确filter `^sc_dev_demo$`，filestore `sc_local_dev_odoo_data`，非生产/控制/目录库，不reset、不执行sync_demo。首次health为starting，`local.dev.ps`证明恢复healthy后health通过，才进行浏览器检查。

### 三个口径

1. 当前页面从正式`ui.contract.v2`最终契约的来源清单读取实际配置ID与版本，逐项呈现，不取最大版本、不以全库计数兜底。无覆盖时显示默认配置；无来源或读取失败明确未核验；旧字段策略覆盖缺少版本时明确诊断。表单明确标注新建态，不冒称所有记录状态已验证。总览只补充来源分类，不用于推断本页应用。个人偏好保存数量单列，不从保存状态推断页面应用。
2. 配置总览使用普通ORM读取（移除summary/export的sudo），保留ACL/record rule，显式限制当前公司及共享配置，包含active=False；已停用优先于原published状态。产品默认、企业配置（含共享偏好投影）、本人个人偏好和来源待确认分列。分类沿用后端既有配置类别并结合记录来源；不引入新来源权威。个人偏好无发布生命周期，单列已保存。配置记录draft与设计器change set分开说明。
3. 工作台入口自身不自动成为待设计对象；coverage以显式参数排除配置运行模型，技术盘点原默认行为不改。业务action直达仍可按已授权菜单元数据恢复对象；选择列表与hydrate同样拒绝配置模型。个人设置和业务模型不受影响。

### 258只读组成（未删除记录）

`configuration-inventory.json`和CSV逐行保留ID、名称、XML来源、公司/角色/action/view、状态与版本；不是只保存数量。数据库共273条配置记录：258启用已发布、15停用、0记录草稿。258条均带smart_construction_core XML ID、company=False共享、无角色限定：152模型级、106 action级，其中6条还限定view；248 form、5 tree、3 search、2 list。153条声明product_release来源，105条无source声明；其中104条名称标记generated，为旧生成默认，需要后续按消费者/作用域核查，不能仅因名称或数量删除。

停用的12条产品配置ID：12、27、31、65、90、91、100、122、135、152、259、263。停用的3条受管验收配置ID：393（材料闭环脚本）、398（入库546正式设计器）、404（证照666正式设计器）；均为先前回滚/退役后状态，本轮未更改。另有本人个人偏好2条，独立模型，不计入273或258。盘点原始权限为经授权只读运维盘点；产品UI汇总另走当前用户ORM权限，二者职责分开。

### 验证与原始证据

`verify.business_config.unit`通过，包含20项surface定向测试及6项页面来源显示反例；授权与路由10项沿用前节。新增反例包括禁止sudo、另一公司排除、inactive与published区分、本人偏好只统计本人且不标published、配置模型不进业务选择、不同配置版本不取max、缺少来源不能用258兜底、旧字段策略不能冒称默认。严格前端类型检查通过；L1 iteration通过。

既有目标先暴露两个P4测试缺陷：发布AST守卫仍查runtime_verified，基线实际已用published_content_verified；schema测试桩未提供既有模型import的AccessError。仅修复这两处测试输入，保持ready/published/ok和发布内容核验要求，不改发布实现、不跳过门禁。随后目标完整通过。库存/金额/权限/业务计算未改。

浏览器`summary-behavior-report.json`：ok/restored=true，零浏览器错误；工作台自身未选中/不在业务目录。实际选择证照显示“表单新建态：使用默认配置；产品默认 #191 · v2”，制度显示“产品默认 #178 · v2”；未出现258作为当前页版本。`summary-report.json`补总览表格可读性，未重跑配置发布旅程。前后配置记录、本人草稿及业务指纹一致；无stage/publish/rollback/save请求。零覆盖、多配置不同版本及旧策略情况采用纯函数反例；没有为验收创建新配置或业务样本。后续仅清空无目标入口残留view参数，已有浏览器请求该参数均为空，行为证据按输入未变承接。

主要日志：`semantics-static.log`、`semantics-final-targeted.log`、`semantics-final-typecheck.log`、`semantics-health-recovered.log`、`semantics-browser.log`、`semantics-visual.log`。截图`overview-unselected.png`、`overview-191.png`、`overview-178.png`。盘点首次数据量超过环境变量长度限制，现有包装改用stdin做身份校验，配置盘点限定scope-only，不另建工具或环境。

状态：本地实施与定向自验完成，待本批集中产品复核；未冻结/未跑本修复Quick、未主线集成、未部署。主线44、本地42保持；U-C3的48151d07候选、Quick及15份归档独立保留。

截图补正：总览表格采用既有设计变量增加间距与分隔线；证照画面通过滚动所有实际容器到0后取证，旧中段画面不称首屏。仅补此显示观察，没有重跑发布回滚。


## 整组收口结果索引（2026-09-16）

候选仍为 `fix/config-center-entry-routing@48151d07b61c6f42bc74008c6c5762334e8fb5a3 + 本批 dirty`。新增修改属于P0的业务对象目录、scope/draft消费、绑定设计器生命周期及预览失败恢复；P4为既有受管观察器和相应测试。原生默认、编译器安全校验、业务权限、库存和金额规则未改。普通目录复用 `system.init.navigation.nav` 最终产品/角色/发布裁决，不读退役顶层nav，不把缺失目录降级成全库扫描；旧技术审计接口的显式扫描能力保留。

| 包 | 实施与当前自验 | 证据及限制 |
| --- | --- | --- |
| 1 目录 | 已改为正式授权入口目录；后端排除配置载体；显示模块路径和action身份，可按模块/入口搜索 | 当前账号86个可配置正式入口；89基线不是本批重新盘点结果。配置中心自身、底层配置记录不能成为设计目标；正式产品定义的管理页面仍按权限保留 |
| 2 作用域 | menu为工作台宿主，进入业务页用目录签发的目标menu，独立config_host_menu_id供返回；相同对象重复选择不清草稿；禁止操作处理中切换 | 666/862/546选择、刷新及546设计器返回通过；模型/公司/角色/技术目标冲突拒绝。高级面板身份只读，不允许改参数时复用旧编辑器内容 |
| 3 来源状态 | 当前页只读最终契约来源；总览按权限和公司；目录配置记录匹配不冒称页面生效；无对象不显示检查比例 | 258组成、默认191/178版本证据沿用；当前公司/角色统计一致；未保存修改与已保存待发布草稿分开 |
| 4 能力 | 现有字段标签、显隐、同区域排序、单区域新增分组；摘要沿用稳定节点补丁；不放宽业务约束 | 原编译器51项及授权拒绝证据按未变输入复用；设计器明确自定义字段/跨区域移动不支持 |
| 5 生命周期 | 按owner/company/role/model/action恢复草稿；未命中不创建；保存后恢复、再编辑、撤销回基线、离开提示；失败保留本地编辑 | 受管数据库定向1项通过（含目标与另一owner隔离）；保存/恢复/预览/发布/刷新契约/再编辑/回滚/撤销与窄屏离开已通过；原始证据及分段承接见下 |
| 6 交互反馈 | Sc组件；不可用/失效预览提供返回设计器；失效草稿可读取当前配置重新开始；只读身份、未应用字段提示、窄屏布局 | 桌面及390px预览可读；失效预览拒绝后实际返回设计器通过；窄屏编辑与离开通过，预览无写入机制证据复用 |

结果入口：L1 `make ci.local.iteration`（batch-static.log）；L2 `make verify.business_config.unit`（batch-draft-scope-tests.log，surface新增目录/模型冲突/空目录不扩域及canonical载体反例），`make verify.nav.pro01r.route_authority.unit`（batch-routing.log，增加宿主/目标返回2例）、`make verify.frontend.bound_form_configuration.unit`与strict typecheck（batch-designer-tests.log/batch-typecheck.log）。受管ORM `make local.dev.test MODULE=smart_core TEST_TAGS=/smart_core:TestBusinessConfigChangeSet.test_resume_draft_is_target_scoped_and_missing_does_not_create`：实际1项、0错误；不以Odoo包含setup的3条统计冒充3项用例。没有模块schema/data变化，L3只restart/health，不upgrade/reset/sync_demo。

浏览器同属 `local.dev.form_lowcode.browser`，只读目录/冲突阶段和受管配置生命周期分段留在同一结果索引；不另建测试环境。完整目录/身份检查见 `browser/batch-directory-passed.json`，其中终止原因是观察器使用了错误字段标签，发生在发布前；其已完成目录/作用域部分承接，不能把整份失败报告称为完整通过。`browser/batch-material-scope-report.json`证实等待目标作用域响应后，入库刷新、进入设计器和返回通过。第一次目录缺失属P0读取了退役载体；随后根菜单重复过滤属P0范围叠加；刷新观察先明确等待作用域加载完成；后续`batch-network-failure.json`实际捕获Chromium ERR_NETWORK_CHANGED及Vite动态模块拉取失败，归environment_defect。保存草稿/离开提示已执行，未发布；测试草稿撤销与回读通过。续验前必须验证具体失败模块HTTP200且内容非空，不延长超时或掩盖失败。原失败报告保留。

配置写入限定已有受管证照配置404和新建“受管配置中心闭环”草稿。包装在前后校验：其他配置记录指纹不变；原有草稿write_date/state不变；新增草稿必须discarded/superseded；新增回滚审计必须指向本轮草稿且内容/最终契约回读为真；404的内容、active、状态、优先级、scope回到基线。版本号/审计新增正常保留，不伪称数据库零写入。业务指纹涵盖证照/制度与入库。没有真实用户偏好修改或业务保存。

未覆盖和边界：自定义字段、跨区域编排、审批引擎重构不在本批；其他角色/公司的正向业务全旅程没有本批样本，复用权限机制证据并补参数隔离拒绝；不重跑UC1/UC2矩阵。U-C3制度查看、合法业务草稿编辑、多角色未覆盖仍独立保留；action777、退库和结算demo问题不混入本批结论。主线44、本地42不变。

冻结/Quick/独立复核/最终外部归档/PR尚未执行，浏览器自验已收齐，等待用户集中复核收敛。U-C3的冻结SHA、Quick与外部归档不借给本批；现场5174保留，历史5176与历史工作树未操作。

### 生命周期续验归因与影响承接

- `batch-observer-popup-failure.json`：观察器直接新建tab，未按真实“打开配置预览”链接继承sessionStorage会话；P4修正为点击现有rel=opener链接，不修改登录机制。
- `batch-preview-recovery-failure.json`：预览、发布、最终契约一致和另一入口隔离均已执行通过，清理回滚及业务指纹回读通过；失效预览恢复提示失败。后端确实只接受ready草稿令牌；前端通用403跳转抢先离开页面，预览专用恢复提示未能展示。P0仅对预览403保留原错误状态及返回设计器入口，未把403转成功，也未放宽任何业务权限。
- 最后续验需重新建立短暂published状态才能检验“再次编辑”，使用同一受管配置404，结束回滚；不是重跑目录、编译器或UC1/UC2矩阵。其他产品输入不变，目录证据直接承接。新增前端生命周期反馈及空对象loading复位影响L1/L2及对应浏览器步骤，不失效后端目录/草稿ORM测试。
- L1 `make ci.local.iteration`、L2 `make verify.frontend.typecheck.strict` 通过；`make verify.frontend.create_default_hydration.unit verify.frontend.readonly_main_data_coverage.unit` 为28+14项通过。日志 `batch-preview-feedback-{static,typecheck,targeted}.log`。观察器syntax检查通过。

- `batch-network-recurrence.json`保留第二次浏览器网络变化的资源列表；未发布，草稿已撤销、基线回读通过。观察器只在明确ERR_NETWORK_CHANGED且逐个失败资源恢复HTTP200/非空后允许一次只读reload，不重试任何stage/publish写入；再次失败仍整体失败。公司query在同页导航中的变化现在明确拒绝，并提示使用全局公司选择。L1及strict typecheck/路由用例再次针对该实际修改通过（`batch-scope-final-{static,targeted}.log`）。

- `batch-lifecycle-passed-narrow-pending.json`：保存、刷新恢复、预览、UI发布、预览/发布最终契约一致、制度隔离、失效预览拒绝并实际返回设计器、再次编辑、回滚回读、另一个草稿UI撤销与清空均已完成。最后窄屏返回观察器未使用“更多”及可见菜单项，整份报告仍保留ok=false，不冒称完整通过。仅观察器改为真实窄屏菜单路径；随后窄屏只进行本地未保存编辑和放弃离开，不再发布或新建配置。`batch-narrow-observer-failure.json`保留可见性选择错误，非产品字段能力缺陷。

### 本次集中交回

最终索引 `artifacts/config-center-entry/browser/batch-report.json`：`ok=true`、`restored=true`，引用已完成的目录阶段和生命周期原始结果；最后仅补窄屏观察，未重复发布。命令为 `FORM_LOWCODE_TOPIC=document FORM_LOWCODE_CONFIG_ENTRY=1 FORM_LOWCODE_CONFIG_BATCH=1 FORM_LOWCODE_CONFIG_BATCH_NARROW_ONLY=1 make local.dev.form_lowcode.browser`，日志 `batch-narrow-final.log`。桌面生命周期日志 `batch-lifecycle-completion.log` 的最终失败仅是窄屏观察器选择错误，保留原失败状态，通过结果由本索引逐项承接，不改写原报告。

分别记录：
- 配置发布：本轮受管测试曾发布成功，发布内容回读通过，随后回滚；当前404内容/启停/作用域恢复原基线。
- 最终契约：预览与发布结果的有效结构、字段策略、动作一致；862不受666覆盖影响；回滚恢复默认。
- 浏览器：正式目录、目标选择/刷新/返回、设计器保存和恢复、预览、发布反馈、再编辑、撤销、失效预览实际返回，以及390px编辑/摘要/更多返回/放弃未保存修改通过。原发布刷新页面旅程按未改变的合成机制复用，不把本次契约回读单独称为完整业务验收。
- 前后权威回读：证照/制度/入库业务指纹不变；原有草稿未改；无真实个人偏好修改；其他配置记录不变。

截图 `browser/batch-preview-narrow.png` 为390×844完整视口；`browser/batch-designer-narrow.png` 为滚动到设计器操作区域的完整视口，不命名或宣称首屏；改动摘要通过可见文本断言。旧目录截图和来源统计截图继续复用。原浏览器网络错误单列环境问题，最后窄屏观察无浏览器错误，不将此扩写为所有历史运行零错误。

复核现场：http://127.0.0.1:5174/m/431 。选证照666、制度862或入库546进入相应表单设置；既有草稿133保留，不要求修改它。本批受管测试草稿已撤销/回滚，不留下待发布测试改动。分支仍 `fix/config-center-entry-routing`，HEAD `48151d07b61c6f42bc74008c6c5762334e8fb5a3` 加本批未提交修改，不冒称冻结候选。

提交边界预案：P0配置目录/来源/作用域/生命周期与其定向测试为产品提交；P4既有观察器、诊断和本记录为验证提交；U-C3已有三提交保持独立依赖。待集中产品复核后再整理提交、生成预检、冻结、Quick、独立复核、归档与PR；本轮均未执行。

状态：**批次自验完成、待集中产品复核｜本批尚未主线集成｜未部署｜89入口交付未完成**。台账主线44、本地42不变。

## 集中产品复核通过与冻结授权

2026-09-16 用户集中复核通过：正式目录和身份可辨认；未选对象无就绪率；全局记录数量与当前页配置分开；证照恢复原草稿，制度不串草稿；目标菜单与宿主返回分离；390px设置、摘要及操作区可读可达。用户未重复发布、回滚或修改业务数据，这些结论引用既有批次证据。桌面视口已恢复，5174现场保留。

本批进入冻结收口：先提交P0产品与P4验证范围，再通过既有freeze.prepare刷新生成证据并预检，审阅后形成最终clean HEAD；一次最终Quick与同候选独立代码复核；摘要、身份、关键截图和复核结果通过受管入口外部归档。最终HEAD/Tree/Quick receipt及归档receipt写入已有未跟踪证据区，避免提交后再改正文导致身份循环。

依赖：main@225a56bf之后的U-C3三个提交aff0cc36→70973007→48151d07为本分支祖先，已冻结证据独立保留。本批不重写这三个提交；远端集成按U-C3先、本批后的顺序准备，尚不执行推送或创建远端PR。若U-C3先squash合并导致基线变化，须通过受管入口承接并依影响重新验证，不能沿用旧exact-head receipt。

本轮只变提交身份、本文和受管生成报告；产品文件内容与用户复核候选一致时，目录、生命周期、授权和浏览器结果直接承接。完整承接记录含源dirty指纹、冻结指纹及逐文件内容比较，位于现有config-center-entry证据区。未覆盖项、主线44/本地42、未部署和89入口未整体交付结论不变。

### 独立复核整改（同批，不扩大范围）

首个冻结候选c3bc87349b6d93fa3cbf9f6ea1132048323ab666的独立复核发现两项：S1统一草稿在validate等待期间可切对象，旧响应覆盖并继续发布；S2未应用字段/分组输入仍可预览或发布旧草稿。前者用源码Node VM和延迟Promise实际复现；后者由按钮及handler路径确认。立即取消该候选Quick（exit130，无通过receipt），未归档为通过、未推送。

修复只涉及既有P0草稿事务和设计器输入门禁：操作开始同步busy；捕获epoch及model/action/company/role，每次异步响应检查身份后才写入本地状态或继续发布；同步scope watch使旧请求失效。按钮与handler均拒绝未应用标签/显隐/分组输入。P4在已有verify.business_config.unit增加9项真实Vue响应式+延迟Promise反例，涵盖校验→发布、校验、预览、暂存、回滚、撤销的迟到响应，角色/公司切换，以及不切换时正常发布。既有发布ready/published/ok/内容回读守卫保持不变。

9项反例和完整相关unit入口、strict typecheck、L1通过；只补390px未应用输入门禁及离开操作，无配置发布/业务写入。对应日志review-fix-{static,targeted,typecheck,browser}.log。旧浏览器/发布回滚证据保留；变化只失效草稿异步状态及输入按钮部分，不重跑整套旅程。新的最终候选需要新Quick和变化范围独立复核，取消运行不计通过或复用。

最终门禁补正：7bb16858候选Quick在frontend lint发现一个未使用解构变量replaceWorkbenchQuerySilently，门禁失败且没有receipt。仅删除该无用途绑定，不改变函数调用或页面行为。先单独运行verify.frontend.lint.src，通过后再刷新生成证据、冻结并运行新候选Quick；浏览器、延迟反例及独立复核的其余范围按无行为变化承接。此失败不是环境原因，也不称为Quick通过。
