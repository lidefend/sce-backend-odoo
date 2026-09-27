# 共享前端基础完整性审查

日期：2026-09-09
状态：实施中；不是发布验收结论
基线 HEAD：`d4b66a8eca180bc640bad31285bb80021381251c`

## 1. 范围与所有权

- Formal Product Layer：P0 平台通用前端表达与交互；P4 仅承载验证和报告。
- Layer Target：现有 design-system、canonical form renderer、relation/detail collection runtime、overlay lifecycle、collection/navigation patterns。
- Standard vs User-Specific：跨模型通用机制，不含行业字段语义、客户偏好或管理员配置。
- Why Here：缺口发生在已有契约到真实控件、错误目标、明细列和响应式表达的消费链。
- Why Not Elsewhere：不需要新建后端字段、业务规则或模型特例；契约未提供的分支失败关闭并登记依赖。
- Blast Radius：所有 ContractForm 关系字段与 one2many 明细；通过付款样板、一个可编辑表单样本和共享门禁证明收敛。

## 2. 基础能力缺口与优先级

| 优先级 | 可见问题 | 已有契约/状态依据 | 现有共享实现断点 | 最小修改归属 | 验收 |
| --- | --- | --- | --- | --- | --- |
| P0 | 同名、短标签或隐藏副本可导致错误误标和焦点偏移 | layout field code、required 结果、`data-field-name` | canonical 按错误文案包含标签匹配；错误摘要只携带字符串 | `canonicalFormRenderState`、表单校验状态、`ScErrorSummary`、可见控件定位 | 字段 code 精确投影；展开所在分区；不聚焦响应式隐藏节点；无结构化目标时聚焦摘要 |
| P0 | many2one 外层显示错误，真实 input 没有等价 ARIA 关联 | field required/invalid/describedBy | `ScRelationField` 没有消费现有 native projection 机制 | `ScRelationField` | 真实 input 具有 `aria-required/invalid/describedby`，辅助技术可读取错误 |
| P0 | 明细列标题丢失；手机表格拥挤且字段意义难辨识 | subview column label/type/required/readonly、row state | 桌面列没有显式 title；窄屏仍依赖宽表格 | 同一 `X2ManyRelationRenderer` | 桌面列名完整；320/390 按行展示同一数据与操作 authority；无业务字段特例 |
| P0 | 明细校验只到行级，控件无精确描述 | column required + row key + field code | `rowErrors` 不能建立 control/error id 关联 | one2many validation + relation adapter | 单元格错误不误标同名列；桌面/手机共享同一错误数据 |
| P1 | 契约允许明细行编辑时，many2one 列被前端类型策略一律只读 | 必须同时满足 subview `inline_edit=true`、列非只读、子模型 field contract `relation_entry.can_read=true` | 子模型描述加载函数已存在但未被调用；顶层关系缓存键无法表示“行×列” | 现有 relation runtime + relation adapter + `ScSelect` 搜索转发 | 缺任一 authority 均只读；行/父表 domain 生效；关键词查询不截断；失败不伪装空结果；不提交写入 |
| P1 | 明细桌面/手机控件标记重复，后续容易产生行为偏差 | 两种布局共享同一 row/column/authority/error | 两套 template 重复选择、输入和错误绑定 | 抽取明细单元格编辑器，不新建数据链 | 两种布局使用同一组件与事件，字段值和错误一致 |
| 已有基线 | drawer/dialog 边界、Escape 关闭与焦点恢复 | overlay lifecycle + token | 前序 C1/A2 已收口 | 本轮不重写，仅回归 | 320/390 浮层自身边界与关闭后焦点 |
| 已有基线 | 列表查询、分页、返回恢复；页面身份和外壳 | action/list route query + page identity | 前序 A1/B2/C1 已收口 | 本轮不重写，仅回归 | 付款集合和层级样本往返不回归 |

## 3. 实施顺序

1. 先完成字段错误身份、真实控件 ARIA 和可见焦点闭环。
2. 再完成明细列标题、单元格错误和窄屏表达，同时去除桌面/手机控件逻辑重复。
3. many2one 明细只在三重 authority 完整时启用，查询复用现有 relation runtime；契约缺失或加载失败保持只读。
4. 通过 Quick 和定向门禁后，在受管 local.dev 执行只读/未提交浏览器验收；付款为主样板，其他页面只证明共享机制。

## 4. 外部依赖与失败关闭

- 子模型 field contract 若缺少 relation model、`relation_entry` 或读权限，关联列保持只读并显示通用可理解原因；不根据列标题猜选项。
- 后端若只返回非结构化错误文案，前端保留并聚焦错误摘要，不猜字段身份。
- 行级 domain 中未被契约解析器支持的表达式登记为契约依赖，不在前端执行任意表达式。
- 本轮不包含业务保存、审批、支付、fixture、数据迁移或 release gate。
# 2026-09-23 F0/F1 当前缺口（历史审计保留于下文）

本节为本轮唯一缺口索引，配合 `business_entry_surface_normalization_batch_1_20260913.md`
当前结果索引和 `docs/product/frontend_business_entry_acceptance_v1.csv` 使用。旧静态覆盖不证明业务验收。

| ID | 缺口与责任 | 状态/验收要求 |
| --- | --- | --- |
| G-F0-01 | P4 运行容器仍挂载已清理专题，前端 403、代码版本未知 | 已通过原 local.dev 入口恢复挂载和精确版本；health 通过；不涉及新环境或数据库重建 |
| G-F0-02 | 会计日记账分录、日记账项目、科目表在正式 89 范围内，但旧覆盖表没有同菜单身份 | 阻塞；F3 会计批次读取当前角色、action、contract，补查询/写入职责与实测。禁止自动排除 |
| G-F1-01 | 项目资料历史证据缺少无权角色浏览器及直接调用拒绝；当前源码较旧证据发生变化 | 本轮必验：真实授权操作、保存回读、只读字段/不可用动作/直接调用拒绝、字段/表单/服务端错误及失败恢复；未取得证据不得关闭 |
| G-F1-02 | P0 onchange 旧回包覆盖新草稿/新记录 | 独立复核 REQUEST_CHANGES：`useRecordFormState.ts` 的 set→timer→API→回写完整链无序号/草稿保护，`useRecordPageLifecycle.ts` 换记录只清 timer；需补乱序、下一次请求前新输入、记录切换三类反例 |
| G-F1-03 | P0 occurrence 在事件消费边界丢失 | 渲染策略已有 occurrence；`formSection.types.ts` 只有 key，`useRecordActionPresentation.ts` 按 name 分发，页面合并同字段可写性；需携带 index 并按事件来源位置核验。未认定为后端越权 |
| G-F1-04 | P4 旧 runner 依赖关系控件 placeholder，未实际选择责任人 | 已关闭此定位缺口；改用可访问标签并保留真实选择断言，`/tmp/frontend-f1-browser-r2-20260923/summary.json` 真实责任明细保存/恢复通过 |
| G-F1-05 | P0编辑跳过required校验、P1接受显式空项目名 | 已关闭此数据完整性缺口；`9b3d65d2` 六场景通过，`/tmp/frontend-f1-fixed-counterexamples-20260923/summary.json`；必填错误零请求、后端拒绝无部分写、合法保存刷新一致；不代表全部F1验收 |
| G-F1-06 | P0 api.data 把后端ValidationError分类为500/INTERNAL_ERROR | 真实拒绝已证明，业务校验分类仍不正确；下一F1修复在通用handler，不把项目文案判断加入前端。表单/服务端失败后页面草稿恢复尚需实测 |
| G-F1-07 / B01 | 高：客户查询文字经失焦隐式修改关系草稿，保存可能由查询词触发创建 | 完整链已确认：ProfessionalMany2oneFieldControl.blurField → commitMany2oneInline 自动匹配/清ID/markDirty；resolvePendingInlineRelationCreates仅凭关键词和契约允许判待创建。P0分离查询词、选中ID、明确创建意图；输入、blur、Escape、取消都不得改变ID/dirty或触发创建；明确选择/清除/创建单独验证。`74f5de1e`已实测查询/失焦零修改；客户选择写入旧初测撤回；`babce9d9`严格复验两场景通过，所点ID独立绑定，仅partner_id提交，失败草稿可编辑且权威不变，重试一次成功，刷新UI与事实一致。pm1契约不提供创建；其他获准创建消费者仍待实际创建验收，不能据此声称全关系写入通过 |
| G-F1-08 / B01 | 高：客户搜索更多内部错误与空态并存，名称列重复 | 原始管理员报告及截图已复现；受管logs定位原生phone_mobile_search少于3字符UserError被包装500。P0后端按搜索契约处理搜索字段与校验分类；前端error/loading/empty互斥、禁止失败冒充无匹配；不新增项目或客户模型特例。短词AB搜索HTTP200及取消已在`74f5de1e`通过；错误/空态互斥及旧行禁止确认有定向测试，查询失败后的浏览器恢复、名称重复列的契约来源仍待收口 |
| G-F1-09 / B01 | 客户下拉被项目名称输入遮挡；取消弹窗后下拉自动重开 | P0现有关系控件/浮层生命周期；仅修影响选项可操作性的层叠与焦点恢复。复验桌面和390px、鼠标/键盘、取消/ESC后的关系值及dirty不变；`74f5de1e`已实测桌面不遮挡、取消恢复焦点不展开、桌面转390px重开无溢出、ESC关闭且权威不变；页面离开清理及完整键盘选择归F2继续验证。不得以取消焦点恢复方式破坏无障碍 |
| G-F1-10 | 中：J13「清空必填金额→保存草稿必须被拦」与后端契约不一致，且两条必填判定对 0 结论相反 | 定位结论（`j13_zero_amount_localization_20260925.md`）：字段 `payment.request.amount`（Monetary, required，由策略 `finance.payment.apply.pay` 声明，契约 `fieldDescriptor.required=true`/`componentKey=sc.value.money`）。后端**允许 0**：`''`/`False`/`0.0` 三种输入 create 均落库 `0.0`、`state=draft`，只有完全省略字段才 `NotNullViolation`。前端按代码推导：清空（归一为 `false`）与未输入被 `isRequiredFieldEmptyByType`（`saveRecordHelpers.ts:132-137`）判空并应被拦截，显式输入 `0` 被放行并原样提交；**但该推导与既有浏览器记录冲突且未裁决**——`onchange_draft_identity_roundtrip_20260924.md:81-85` 实际观察到清空后草稿保存成功（金额 0.00，旁证真实单据 `PRQ2600326`），故「是否被拦」需实测裁决；而 `isMissingRequiredValue`（`valueUtils.ts:8` `v<=0`）把 0 判为缺失——两条判定互相矛盾，当前仅因该 action 无 scene-ready 契约（`sceneValidationRequiredFields` 为空）而休眠。已排除「`false` 被渲染成 `0.00`」假设（`formSection.mapper.ts:278-280` 对 `false` 先归空）。最小路径：先在能渲染该表单的环境拦截 `api.data` 写入以裁决「清空是否被拦」，再由产品裁定草稿 0 是否合法，随后收敛 `valueUtils.ts` 1 处空值定义并补 0/空/未输入三态非零定向测试；若要求 >0，须在 P1 模型/策略层同时加约束，不得只改前端。浏览器 `not_run`：本地 5176 无监听；18081 可登录（admin/pm1）但 payment.request 入口被 `NAVIGATION_AUTHORITY_DENIED`/`PERMISSION_DENIED` 拒绝，本地无 `sc_frontend_acceptance` 库与 `fixture_role_finance`。**未修改产品代码** |
| G-F3-02 / B02 | 高：日记账分录详情整体无法渲染，sc.input.text:json不匹配 | 定位结论（`accounting_json_detail_readonly_20260924.md`）：字段 `account.move.quick_encoding_vals`，ttype `json`、契约只读且原生 `invisible`，值形状为 JSON 对象；首次错误映射在契约生成层 `unified_page_contract_v2_assembler._widget_type_from_field` 对 json 无分支而回退 `input` → `sc.input.text`，前端注册表 `sc.input.text` 仅支持 `['char']`，Resolver 按设计 fail-closed 导致整页不可渲染（Resolver 不是错误点）。正确呈现要求：json 无任何客户端编辑控件，契约声明只读可读展示，对象/数组输出 JSON 文本，`{}`/`[]`/null/false/空串按空值处理，可编辑 json 同样只读，空值与非空值都不得整页失败。最小修改路径：契约层 `json → display`（复用既有 `sc.display.text`，不新增组件键）+ 通用展示层 json 文本化与禁止落入可编辑兜底 + 三类输入的定向测试；解耦 Decoder/Resolver fail-closed。不得隐藏字段、吞异常或把对象字符串化塞入文本框。同类未修：lite 适配器同源回退。复验：列表→详情可打开、JSON 按契约展示、原只读记录仍只读、返回列表保留查询上下文。已实现（契约层 json→display、前端通用 json 文本化与只读分支、三类输入定向测试）并复验通过：定向 7 项/147 项、assembler guard、展示与表单契约单测全绿；浏览器 `/f/account.move/2` 列表→详情整页渲染无错、json 输入数为 0、返回列表保留 `menu_id` 上下文。残留：本数据集无「可见且非空」json 值（可见非空展示由发布模块展示单测＋契约探针承担）；`analytic_distribution` 等原生可编辑 json 一并转为只读展示（旧行为本就 fail-closed）；导航授权拒绝与 lite 适配器回退登记不修；未合入前不宣称主线集成 |
| G-F2-04 / B03 | 中：收款新建返回越过来源收款列表 | 定位结论（`payment_return_navigation_20260924.md`）：根因单点且通用——`ActionView.vue:1647` 用 `router.push` 打开 `/f/<model>/new`，全局 `beforeEach` 守卫为创建表单补注入 `activity_page_id` 时返回了 `replace: true`；`vue-router@4.6.4` 的 `pushWithRedirect` 会把原导航 `replace` 透传给守卫重定向的后续导航（`dist/vue-router.mjs:1311`），用户 `push` 变成 `replaceState`，来源收款列表条目被销毁，表单「返回」(`router.back()`) 落到真实前驱（`/workspace.home`）。修复（通用导航运行时，不写死收款路由）：新增 `resolveCreateFormActivityRedirect()` 注入活动身份但**不带 `replace`**，交回调用方保留导航模式；`executeRecordFormReturn` 增加 `hasInAppHistoryEntry`/`fallbackRoute`/`navigateFallback`，返回 `history` 或 `fallback`，回退目标只取自路由授权声明的入口路由。复验：定向 `make verify.frontend.record_form_return.unit` 11 条通过、`vue-tsc` 错误集与基线一致、`local.dev.frontend` 构建上线；浏览器 5 场景通过（合同页/报表页两种来源均回收款列表、筛选+分页上下文保留、直达 URL 走契约回退、有草稿离页保护），`errors: []`。残留：报表中心投影页 0 行致其对象按钮不可达（入口数据问题，登记不修）；显式创建入口仍 `not_available`（未验收）；many2many 失焦与 `ScAutoComplete.vue` 留后续。未合入前不宣称主线集成 |
| G-F3-03 | 高：开发环境收入/支出结算列表附件 404（`/web/content/231`） | **未复现**：结算列表与详情首屏 `attachment`/`web/content`/`/binary` 请求 0 个、无 4xx/5xx，`sc.settlement.order` 附件关联 0 条。孤立 `/web/content/231`→404 与 `/web/image/231`→200 均不足以判定原问题（200 可能是共享占位图，不能证明返回原文件）。停止推测归类；后续巡检若捕获真实失败，须同时记录页面、实际请求 URL、响应类型、调用来源及附件身份 |
| G-F3-04 | 高：直接访问 `/f/project.task/new` 显示「服务暂时不可用」（后端 5xx） | 定位结论：`UiContractV2Handler` 组装 `project.task` 表单契约时抛 `ValueError`，由通用错误面 `resolveProductErrorState` 的 `status>=500` 分支呈现为「服务暂时不可用」（`productErrorState.ts:44`）。两层独立缺陷：①原生投影 `layout` 含 33 个字段节点，而 `fieldDescriptors` 缺少 `recurrence_id`、`sc_state`、`task_properties`、`repeat_*`、`rating_*`、`personal_stage_type_id`、`allow_task_dependencies` 共 13 个 → `_assemble_native_form_projection.validate_occurrences` 抛 `field descriptor identity mismatch`（`unified_page_contract_v2_assembler.py:1219-1235`）；②已发布低代码契约 `ui.business.config.contract` id 49 `project_task_form_structure_generated_v1`（模块数据 `smart_construction_core/data/view_orchestration_contract_generated_data.xml:259`）只声明 8 项平面 `fields` 编排、无 `composition_mode`，兼容面合成出 `locator=''`、`occurrence_index=0` 的 `name` 节点 → 同一校验抛 `field occurrence identity is incomplete`。因果实测：将契约 49 置 draft/inactive（savepoint 内写入并回滚）只把错误由 `name` 换成 `recurrence_id`，故**仅退役该契约不足以修复**。非权限、非数据问题。最小路径：①让原生投影 layout 与 `fieldDescriptors` 按同一规则收敛（或在装配前剪除无描述符节点），不得静默丢弃 `sc_state` 等 P1 业务字段；②按既有 U-C4 G13/G15/G16（`res.users`）先例处理该生成契约；③补 create/edit 装配的非零定向测试。影响全部原生表单装配，需 P0 决策。本轮仅定位、未改代码；注意 `project.task` 的标签验收走 `project.project` 表单，未覆盖本入口 |
| G-F3-05 | P0：`mail.notification` 详情整页不渲染，`PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH:sc.input.text:many2one_reference` | 定位结论：只读技术踪迹字段 `mail.notification.sc_source_res_id`（`fields.Many2oneReference`，`model_field="sc_source_model"`，原生 `invisible="1"` 且未声明 widget）。首次错误映射在视图解析层 `view_Parser/base._widget_for_field`：未映射类型走 `mapping.get(ftype, ftype)`，把**字段类型本身当 widget 名**透传 → `nativeWidget="many2one_reference"` → `_canonical_widget_type` 无该分支 → `_widget_type_from_field` 回退 `input` → `_component_key` 得 `sc.input.text`，而 `sc.input.text` 只支持 `["char"]`，Resolver 按设计 fail-closed 拒绝整页（Resolver 不是错误点）。与 G-F3-04 的节点装配 5xx 根因不同，同属字段类型映射缺口。另 `fields_get()` 不发布 `model_field`，目标模型指针只有字段对象持有，必须由契约显式携带，前端不得推导。正确呈现要求：保留声明类型与目标模型指针，绑定只读展示（复用既有 `sc.display.text`，注册为 `["*"]`，与 G-F3-02 的 json 处理同构，**不是放宽 `sc.input.text` 校验**）；有权限时来源名称由既有 `sc_record_name`（char）承载；无权限／来源已删除时不泄露内容、不生成不可访问链接。最小修改路径：①`view_Parser/base._widget_for_field` 对 `many2one_reference`／`reference` 返回未声明，其余未映射类型维持原透传（避免无关渲染漂移）；②`contract_Parser._enrich_view_fields_info` 两处从字段对象补 `model_field`；③`utils/native_field_descriptor` 保留／清理 `model_field`；④`core/unified_page_contract_v2_assembler` 新增 `REFERENCE_FIELD_TYPES`：`_component_key`→`sc.display.text`、`_widget_type_from_field`→`display`、`_canonical_widget_type` 按 json 同规则让声明类型压过 widget 拼写、`componentConfig` 透传 `model_field` 并写 `referenceModelField`；⑤`assemblers/page_assembler._to_fields_map` 透传 `model_field`。复验：定向 `test_unified_page_contract_v2_kanban_action_registry` 10/10、`test_native_view_parser_surfaces` 36/36、`test_unified_page_contract_v2_mobile_compact` 92/92；`verify.unified_page_contract.v2.assembler`／`.runtime` PASS；契约探针 `mail.notification` form＋list、`mail.activity` form 的引用字段均为 `sc.display.text`／`display`／`many2one_reference`／`model_field` 且注册表反查 `bad=[]`；浏览器（候选 5176＋18081、`demo_full`）`/f/mail.notification/<id>` 整页渲染、字段全部只读（`inputs=0`）、「关联单据」显示来源名称 `展厅-市政工程样板段-任务 04`、`console_errors`／`http_5xx` 为空，列表→详情→返回 3 行真实行且返回 URL 与列表一致，390px `overflow=false`；三态 ORM 复验 normal→`act_window(project.task,23)`、deleted→`UserError 关联单据已不存在。`、denied→`AccessError`，夹具清理回读全 0。残留见 G-F3-06／G-F3-07。未合入前不宣称主线集成 |
| G-F3-06 | 中：有权限来源的「打开关联单据」在浏览器被导航授权层拒绝 | 独立缺陷，与 G-F3-05 根因无关。`action_sc_open_source` 对可读来源已返回 `act_window`（`res_model="project.task"`、`res_id=23`，ORM `check_access_rights`／`check_access_rule` 通过），但浏览器落到 `NAVIGATION_AUTHORITY_DENIED`（跳转 `/access-denied?from=/f/project.task/23&action_id=349`），未显示来源内容。疑似导航运行时对「对象自带 act_window 的跨路由目标」缺少授权声明或契约回退，属 P0 导航授权层。本轮仅登记，不修；不得用动作域或前端兜底绕过授权层 |
| G-F3-07 | 未裁决：`properties` 等类型疑似同类字段类型映射问题（静态扫描命中，浏览器未证伪） | 静态扫描（契约探针＋注册表镜像）显示 `project.task.task_properties` 为 `fieldType="properties"`、`componentKey="sc.input.text"`、`invisible=false`、`modifiers=null`，而 `sc.input.text` 只支持 `["char"]`，形态与 G-F3-05 同类；但浏览器 `/f/project.task/new`、`/f/project.task/23` 实测无 mismatch、无 5xx、`console_errors` 为空，新建表单实际只渲染 5 个字段（任务名称／当前阶段／执行人／截止日期／优先级），该节点未进入渲染解析。**两种观测冲突未裁决**，不得据静态扫描断言线上缺陷，也不得据此扩大 `sc.input.text` 支持类型。同批静态命中 `personal_stage_type_id`（`many2one`→`sc.display.status`）、`credit_limit`（`float`→`sc.value.money`）亦属「未触达即不报错」类。需在「可见且非空」条件下单独验证后再定性 |
| G-PUB-01 | P4 `gitee.ci.pr.create` 硬编码旧分支及旧PR正文 | 最小参数化修复及11定向测试通过，待独立复核与实际PR回读；保留精确SHA、受保护main和创建回读，不扩大CI建设 |
| G-F3-01 | 其余已映射正式入口只有历史结构/覆盖信息 | 保留本轮 F3 归属，逐域覆盖列表与表单；写入口具备成功/失败/拒绝/恢复，按实际职责转为只读或明确降级，不能以 ready 关闭 |

| G-F3-08 | 中：`project.task` 经 `api.data` 创建时被平台伪造直接状态写入（已修） | `smart_core` 的 `api.data` create 路径 `merge_orm_create_defaults` 把 `default_get` 解析出的**全部模型默认值**物化进 `vals`；对 `project.task` 注入 13 个字段（含 `sc_state='draft'`），触发模型守卫 `task_extend._ensure_no_direct_state_write` → `TASK_GUARD_DIRECT_STATE_WRITE` → 整页 HTTP 500。因果实测：同 `vals` 直连 ORM `create` 成功、经该函数合并后失败，唯一差异是 `sc_state`；浏览器真实 create 载荷 `{"name","stage_id":false,"date_deadline":false,"priority":"0"}` **不含** `sc_state`，故**不是**契约 `ct_req=true`／前端提交所致。修复：平台新增通用钩子 `smart_core_create_default_skip_fields`，`merge_orm_create_defaults(..., skip_fields=...)` 不对声明字段物化默认值（客户端显式传值仍透传并受模型守卫约束）；`smart_construction_core` 声明 `project.task: ("sc_state",)`。定向：`test_api_data_execution_policy` 8/8、`test_api_data_sudo_scope_order_boundaries` 5/5、`test_api_data_list_param_boundaries` 38/38 |
| G-F3-09 | 低：`sms.template.preview` 表单装配 `ValueError: field occurrence identity is incomplete` | 与 G-F3-04 同族的 occurrence 身份错误，本轮仅探针命中、未定性、未修 |
| G-F3-10 | 待查：`ir.actions.server`／`ir.model.data`／`privacy.lookup.wizard.line`／`app.view.variant`／`mail.mail` 契约探针 `ok=false` | 探针环境已确认为 sudo `su_env`，故 `ok=false` 非 G-F3-05 那类探针构造问题；原因（无菜单入口／投影拒绝／真实缺陷）未查清，不得据此定性为产品缺陷 |
新增巡检唯一来源：`artifacts/frontend-business-entry-browser-audit-20260923/browser-audit.md`（现有外部归档），产品载体`9b3d65d2`；管理员会话、代表入口、390px观察，未保存业务数据。它不替代业务角色、拒绝角色、89项全量或真实写入验收。用户当前草稿保持，不保存、不放弃、不刷新该会话；修复复验使用独立受管测试会话和专用对象。

### 2026-09-27 追加：G-F3-04 写入闭环、G-F3-05 影响边界、G-F3-06 定位（修正前轮两处结论）

**G-F3-04 真实写入闭环（补齐）**：`/f/project.task/new` 在受管环境（前端 5176／后端 18081，`demo_full`）完成「合法必填 → 保存 → 刷新回读 → 清理」——保存成功并重定向 `/f/project.task/195`，刷新后任务名称一致，`console_errors=0`、`http_5xx=0`；夹具回收后回读 `remaining_count=0`、id 195 不存在。字段权限**未因复用 occurrence 丢失**（真实路径 `su_env` 为 sudo）：form `create` 7 字段／5 可写、`edit` 37 字段／18 可写，`drift_readonly=0`、`drift_required=0`；`demo_full`／`wutao`／`demo_role_pm`／`demo_role_project_read` 四角色均 `ok=True`。写入 500 的真实根因与契约装配无关，见新增行 `G-F3-08`。

**修正一（探针构造，非产品缺陷）**：前轮登记「`demo_role_pm`／`demo_role_project_read` 的 `project.task` form `ok=false`，底层 `AccessError: ir.model`，栈指向 `page_assembler._resolve_page_title`」**不成立**。该结果由探针显式传入**非 sudo** 的 `su_env` 造成；真实请求路径 `BaseIntentHandler` 在 `su_env=None` 时构造 `SUPERUSER_ID` 环境（`addons/smart_core/core/base_handler.py:74`）。以正确环境复验两角色均 `ok=True`。此修正不外推到其他模型。

**修正二（引用类型能力边界，勿过度声明）**：G-F3-05 只完成「引用类型 → 只读展示映射」。`reference`／`many2one_reference` 影响边界盘点（`ir.model.fields`，共 21 字段／19 模型）：唯一 `required=True` 的 `rating.rating.res_id` 为 `compute`+`store` 且**无任何视图声明**，不可编辑，故**不存在「必填引用无法填写」的消费者**；可编辑非只读消费者（`ir.ui.menu.action`、`ir.model.data.res_id`、`mail.message.res_id`、`mail.followers.res_id`、`mail.activity.res_id`、`mail.mail.res_id`、`mail.template.preview.resource_ref`、`ir.actions.server.resource_ref`、`sms.template.preview.resource_ref`）`required` 均为 False。契约探针中这些引用字段一律 `sc.display.text`／`display`／`many2one_reference`，无一处落回 `sc.input.text`。**前端当前没有 `referenceModelField` 消费代码**，因此元数据透传 ≠ 通用引用名称解析／跳转已完成；通知页「关联单据」显示的来源名称来自既有 `sc_record_name`（`char`，`related="mail_message_id.record_name"`），**不是**引用字段自身的解析结果。

**G-F3-06 定位结论（原行「疑似」到此收口，不改导航权限）**：`action_sc_open_source` 返回的 `act_window` 字典**不含 `id`**（`mail_notification_product.py:53-79`）；`smart_core` 的 `normalize_odoo_action_result` 在缺少显式 id 时调用 `_resolve_action_id_for_model`，以 `sudo()` 取该模型**最小 id** 的 `act_window`——`project.task` 命中 `349 = project.act_project_project_2_project_task_all`（`navigation_entry_target.py:231-236、351-359`）。前端 `router.beforeEach` 对 `record`／`model-form` 路由在 `actionId>0` 时要求该 id 出现在**由可见菜单派生**的 `routeAuthority`（`menu_service.build_route_authority` 逐 `menu_xmlid` 取 `export_visible_menu_facts`），而 **349 没有任何菜单绑定**（实测 `project.task` 的 18 个 `act_window` 全部 `menus=[]`），故必然被判定未授权 → `NAVIGATION_AUTHORITY_DENIED`。结论：**不是用户权限问题，也不是业务上返回了错误 action**，而是导航入口身份合成缺陷（P0 `smart_core`）——后端把一个用户从未被授权、也不可达的 action 身份写入 `entry_target`，前端鉴权层如实拒绝。修复方向（下轮，最小化且不放宽鉴权）：`_resolve_action_id_for_model` 只能返回当前用户经可见菜单可达的 action；无可达 action 时不得伪造 action 身份（保持 0，让前端走纯记录路由），并需实测定稿前端在无 `action_id` 时的记录路由行为。

**本轮状态口径**：通知详情本地渲染通过；任务表单本地打开与本地保存回读通过；来源跳转（G-F3-06）未修；任务创建的目标环境复验未做；J13 与 `properties`（G-F3-07）不混入本批。
