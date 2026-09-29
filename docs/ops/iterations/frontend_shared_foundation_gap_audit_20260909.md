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
| G-F1-10 | 中：J13「清空必填金额→保存草稿必须被拦」与后端契约不一致，且两条必填判定对 0 结论相反 | 定位结论（`j13_zero_amount_localization_20260925.md`）：字段 `payment.request.amount`（Monetary, required，由策略 `finance.payment.apply.pay` 声明，契约 `fieldDescriptor.required=true`/`componentKey=sc.value.money`）。后端**允许 0**：`''`/`False`/`0.0` 三种输入 create 均落库 `0.0`、`state=draft`，只有完全省略字段才 `NotNullViolation`。前端按代码推导：清空（归一为 `false`）与未输入被 `isRequiredFieldEmptyByType`（`saveRecordHelpers.ts:132-137`）判空并应被拦截，显式输入 `0` 被放行并原样提交；**但该推导与既有浏览器记录冲突且未裁决**——`onchange_draft_identity_roundtrip_20260924.md:81-85` 实际观察到清空后草稿保存成功（金额 0.00，旁证真实单据 `PRQ2600326`），故「是否被拦」需实测裁决；而 `isMissingRequiredValue`（`valueUtils.ts:8` `v<=0`）把 0 判为缺失——两条判定互相矛盾，当前仅因该 action 无 scene-ready 契约（`sceneValidationRequiredFields` 为空）而休眠。已排除「`false` 被渲染成 `0.00`」假设（`formSection.mapper.ts:278-280` 对 `false` 先归空）。最小路径：先在能渲染该表单的环境拦截 `api.data` 写入以裁决「清空是否被拦」，再由产品裁定草稿 0 是否合法，随后收敛 `valueUtils.ts` 1 处空值定义并补 0/空/未输入三态非零定向测试；若要求 >0，须在 P1 模型/策略层同时加约束，不得只改前端。浏览器 `not_run`：本地 5176 无监听；18081 可登录（admin/pm1）但 payment.request 入口被 `NAVIGATION_AUTHORITY_DENIED`/`PERMISSION_DENIED` 拒绝，本地无 `sc_frontend_acceptance` 库与 `fixture_role_finance`。**未修改产品代码。【2026-09-27 裁决与根因，详见 `j13_zero_amount_localization_20260925.md` 第 10 节】三态实测（`sc_dev_demo`/`demo_full`/`/f/payment.request/new?action_id=809&menu_id=559`，5176 为 `dist-dev` 已构建产物）：显式 `0` → 载荷 `amount:0`、保存成功、回读 `0.0/draft`；清空 → 载荷 `amount:false`、保存成功、**静默落 `0.00` 草稿**；未触碰 → 载荷无 `amount` 键、后端 `NotNullViolation` → HTTP 500、未创建。三态均**未被前端必填拦截**，故第 3.1 节冲突按浏览器记录裁决，`PRQ2600326` 成因即「清空静默落 0」。根因：保存前必填校验用的 `layoutNodes` 来自 `buildLegacyLayoutNodes`，实参 `order:[]`、`visibleFields:[]`（契约 `dataMeta` 无 `visibleFields`）、`fallbackFieldNames:[]`（契约分组名为 `business_*`，无 `core/advanced`，widget 无 `surfaceRole`），落入 `nativeLayoutUtils.ts:741-744` 兜底 `Object.keys(input.fields).slice(0,16)`——校验字段表退化为契约字段映射前 16 个；前 16 含 `project_id`(9)/`partner_id`(10)/`business_category_id`(11)/`date_request`(12)，不含 `amount`(索引 34)，与「partner 未选被拦且无写请求、amount 三态均发写请求」完全一致；金额仍进载荷来自 `collectWritableValues` 的脏字段回退（`useRecordFormState.ts:151`）。修订后最小路径（P0 通用前端层，未实施）：①校验字段表不得静默 `slice(0,16)`，无清单时按契约节点/`business_*` 分组或原生布局树生成，缺失应显式失败；②`normalizeContractFieldValue` 对清空的 `float/monetary` 不得返回 `false`，应用 `null`/省略，交由 ORM required 裁决；③两条必填判定收敛同源（仅 `null/undefined/''/[]` 为空，数字 `0` 与非布尔 `false` 不算缺失），「金额>0」如需要则为 P1 独立业务约束。【2026-09-27 已修复，`64c326c4`，详见 `j13_zero_amount_localization_20260925.md` 第 11 节】三项最小路径全部实施：①`buildLegacyLayoutNodes` 兜底改为完整契约字段表（不再 `slice(0,16)`，`amount` 索引 34 重新参与校验与写入）；②`normalizeContractFieldValue` 对 integer/float/monetary 的未触碰值返回 `null` 并由新增 `shouldWriteFieldValue` 从载荷省略，显式清空仍走类型化哨兵 `false`、数值 `0` 原样提交，创建态跳过未触碰空值以免覆盖 ORM 默认值；③`isMissingRequiredValue` 成为唯一必填实现（`0` 不再缺失、布尔 `false` 不误伤），`isRequiredFieldEmptyByType` 退化为别名——两条判定不再矛盾。定向 `verify.frontend.j13_required_value_semantics.unit` 83 例并纳入 quick/release 门禁；浏览器（5176/`64c326c4`）：未触碰 → 零写请求 + 「申请金额不能为空」（原 500）、清空 → 零写请求 + 字段级错误、显式 `0` → 载荷 `amount:0` 保存成功、回读 `0.0/draft`、模拟 500 失败保草稿后重试成功（2125）、编辑态不触碰不发写请求且金额保持 `7.50`；专用记录 2124/2125/2126 已清理，`remaining=[]`。本批未新增「金额>0」业务规则。【2026-09-27 收口，`5455ca00`，详见同文第 12 节】上一节点把必填判定收敛为唯一实现，但场景预校验仍**无类型调用**该判定（`sceneValidation.ts` 只按值判断），故「场景要求填写的布尔字段为 `false`」仍会被拦、而按无类型放宽又会漏检空关联——函数合并了、调用方类型没接齐。修复：预检输入增加 `fieldType?` 解析器，生产调用点以契约表单字段表 `formFields` 为唯一类型权威；同时补非必填数值清空闭环。定向由 83 例增至 **110 例**（真实预检入口、类型转发断言、调用点接线守卫、非必填三态、控件清空输出），`vue-tsc` 仍 31 项既有错误未新增。浏览器（正式入口「公司收入」`action_id=806&menu_id=545`，候选 `5455ca00`）：非必填数值 `deducted_tax_amount=3`/`settlement_amount=7` 以数值写入、未触碰的 `deducted_invoice_amount` 不入载荷；清空 `settlement_amount` 时控件输出**空串**、写载荷仅 `{"settlement_amount":false,"note":…}`（未触碰的 `deducted_tax_amount` 不在载荷），权威回读 `settlement_amount=0.0`、`deducted_tax_amount=3.0` 保留、`state=draft`；只改备注时载荷仅 `note`、回读原值不变。**边界**：`monetary`/`float` 对 `false` 哨兵的类型化收敛就是数值 `0.0`，「显式清空」与「从未写入」在存储上不可区分，差异只在写入载荷，不得描述为「数据库空值」。专用记录 257（及首轮 256）已回收，`remaining=[]`。场景所需布尔字段在现有可达入口不存在，故该修复无浏览器场景，仅为真实入口单测+接线守卫。 |
| G-F3-02 / B02 | 高：日记账分录详情整体无法渲染，sc.input.text:json不匹配 | 定位结论（`accounting_json_detail_readonly_20260924.md`）：字段 `account.move.quick_encoding_vals`，ttype `json`、契约只读且原生 `invisible`，值形状为 JSON 对象；首次错误映射在契约生成层 `unified_page_contract_v2_assembler._widget_type_from_field` 对 json 无分支而回退 `input` → `sc.input.text`，前端注册表 `sc.input.text` 仅支持 `['char']`，Resolver 按设计 fail-closed 导致整页不可渲染（Resolver 不是错误点）。正确呈现要求：json 无任何客户端编辑控件，契约声明只读可读展示，对象/数组输出 JSON 文本，`{}`/`[]`/null/false/空串按空值处理，可编辑 json 同样只读，空值与非空值都不得整页失败。最小修改路径：契约层 `json → display`（复用既有 `sc.display.text`，不新增组件键）+ 通用展示层 json 文本化与禁止落入可编辑兜底 + 三类输入的定向测试；解耦 Decoder/Resolver fail-closed。不得隐藏字段、吞异常或把对象字符串化塞入文本框。同类未修：lite 适配器同源回退。复验：列表→详情可打开、JSON 按契约展示、原只读记录仍只读、返回列表保留查询上下文。已实现（契约层 json→display、前端通用 json 文本化与只读分支、三类输入定向测试）并复验通过：定向 7 项/147 项、assembler guard、展示与表单契约单测全绿；浏览器 `/f/account.move/2` 列表→详情整页渲染无错、json 输入数为 0、返回列表保留 `menu_id` 上下文。残留：本数据集无「可见且非空」json 值（可见非空展示由发布模块展示单测＋契约探针承担）；`analytic_distribution` 等原生可编辑 json 一并转为只读展示（旧行为本就 fail-closed）；导航授权拒绝与 lite 适配器回退登记不修；未合入前不宣称主线集成 |
| G-F2-04 / B03 | 中：收款新建返回越过来源收款列表 | 定位结论（`payment_return_navigation_20260924.md`）：根因单点且通用——`ActionView.vue:1647` 用 `router.push` 打开 `/f/<model>/new`，全局 `beforeEach` 守卫为创建表单补注入 `activity_page_id` 时返回了 `replace: true`；`vue-router@4.6.4` 的 `pushWithRedirect` 会把原导航 `replace` 透传给守卫重定向的后续导航（`dist/vue-router.mjs:1311`），用户 `push` 变成 `replaceState`，来源收款列表条目被销毁，表单「返回」(`router.back()`) 落到真实前驱（`/workspace.home`）。修复（通用导航运行时，不写死收款路由）：新增 `resolveCreateFormActivityRedirect()` 注入活动身份但**不带 `replace`**，交回调用方保留导航模式；`executeRecordFormReturn` 增加 `hasInAppHistoryEntry`/`fallbackRoute`/`navigateFallback`，返回 `history` 或 `fallback`，回退目标只取自路由授权声明的入口路由。复验：定向 `make verify.frontend.record_form_return.unit` 11 条通过、`vue-tsc` 错误集与基线一致、`local.dev.frontend` 构建上线；浏览器 5 场景通过（合同页/报表页两种来源均回收款列表、筛选+分页上下文保留、直达 URL 走契约回退、有草稿离页保护），`errors: []`。残留：报表中心投影页 0 行致其对象按钮不可达（入口数据问题，登记不修）；显式创建入口仍 `not_available`（未验收）；many2many 失焦与 `ScAutoComplete.vue` 留后续。未合入前不宣称主线集成 |
| G-F3-03 | 高：开发环境收入/支出结算列表附件 404（`/web/content/231`） | **未复现**：结算列表与详情首屏 `attachment`/`web/content`/`/binary` 请求 0 个、无 4xx/5xx，`sc.settlement.order` 附件关联 0 条。孤立 `/web/content/231`→404 与 `/web/image/231`→200 均不足以判定原问题（200 可能是共享占位图，不能证明返回原文件）。停止推测归类；后续巡检若捕获真实失败，须同时记录页面、实际请求 URL、响应类型、调用来源及附件身份 |
| G-F3-04 | 高：直接访问 `/f/project.task/new` 显示「服务暂时不可用」（后端 5xx） | 定位结论：`UiContractV2Handler` 组装 `project.task` 表单契约时抛 `ValueError`，由通用错误面 `resolveProductErrorState` 的 `status>=500` 分支呈现为「服务暂时不可用」（`productErrorState.ts:44`）。两层独立缺陷：①原生投影 `layout` 含 33 个字段节点，而 `fieldDescriptors` 缺少 `recurrence_id`、`sc_state`、`task_properties`、`repeat_*`、`rating_*`、`personal_stage_type_id`、`allow_task_dependencies` 共 13 个 → `_assemble_native_form_projection.validate_occurrences` 抛 `field descriptor identity mismatch`（`unified_page_contract_v2_assembler.py:1219-1235`）；②已发布低代码契约 `ui.business.config.contract` id 49 `project_task_form_structure_generated_v1`（模块数据 `smart_construction_core/data/view_orchestration_contract_generated_data.xml:259`）只声明 8 项平面 `fields` 编排、无 `composition_mode`，兼容面合成出 `locator=''`、`occurrence_index=0` 的 `name` 节点 → 同一校验抛 `field occurrence identity is incomplete`。因果实测：将契约 49 置 draft/inactive（savepoint 内写入并回滚）只把错误由 `name` 换成 `recurrence_id`，故**仅退役该契约不足以修复**。非权限、非数据问题。最小路径：①让原生投影 layout 与 `fieldDescriptors` 按同一规则收敛（或在装配前剪除无描述符节点），不得静默丢弃 `sc_state` 等 P1 业务字段；②按既有 U-C4 G13/G15/G16（`res.users`）先例处理该生成契约；③补 create/edit 装配的非零定向测试。影响全部原生表单装配，需 P0 决策。本轮仅定位、未改代码；注意 `project.task` 的标签验收走 `project.project` 表单，未覆盖本入口 |
| G-F3-05 | P0：`mail.notification` 详情整页不渲染，`PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH:sc.input.text:many2one_reference` | 定位结论：只读技术踪迹字段 `mail.notification.sc_source_res_id`（`fields.Many2oneReference`，`model_field="sc_source_model"`，原生 `invisible="1"` 且未声明 widget）。首次错误映射在视图解析层 `view_Parser/base._widget_for_field`：未映射类型走 `mapping.get(ftype, ftype)`，把**字段类型本身当 widget 名**透传 → `nativeWidget="many2one_reference"` → `_canonical_widget_type` 无该分支 → `_widget_type_from_field` 回退 `input` → `_component_key` 得 `sc.input.text`，而 `sc.input.text` 只支持 `["char"]`，Resolver 按设计 fail-closed 拒绝整页（Resolver 不是错误点）。与 G-F3-04 的节点装配 5xx 根因不同，同属字段类型映射缺口。另 `fields_get()` 不发布 `model_field`，目标模型指针只有字段对象持有，必须由契约显式携带，前端不得推导。正确呈现要求：保留声明类型与目标模型指针，绑定只读展示（复用既有 `sc.display.text`，注册为 `["*"]`，与 G-F3-02 的 json 处理同构，**不是放宽 `sc.input.text` 校验**）；有权限时来源名称由既有 `sc_record_name`（char）承载；无权限／来源已删除时不泄露内容、不生成不可访问链接。最小修改路径：①`view_Parser/base._widget_for_field` 对 `many2one_reference`／`reference` 返回未声明，其余未映射类型维持原透传（避免无关渲染漂移）；②`contract_Parser._enrich_view_fields_info` 两处从字段对象补 `model_field`；③`utils/native_field_descriptor` 保留／清理 `model_field`；④`core/unified_page_contract_v2_assembler` 新增 `REFERENCE_FIELD_TYPES`：`_component_key`→`sc.display.text`、`_widget_type_from_field`→`display`、`_canonical_widget_type` 按 json 同规则让声明类型压过 widget 拼写、`componentConfig` 透传 `model_field` 并写 `referenceModelField`；⑤`assemblers/page_assembler._to_fields_map` 透传 `model_field`。复验：定向 `test_unified_page_contract_v2_kanban_action_registry` 10/10、`test_native_view_parser_surfaces` 36/36、`test_unified_page_contract_v2_mobile_compact` 92/92；`verify.unified_page_contract.v2.assembler`／`.runtime` PASS；契约探针 `mail.notification` form＋list、`mail.activity` form 的引用字段均为 `sc.display.text`／`display`／`many2one_reference`／`model_field` 且注册表反查 `bad=[]`；浏览器（候选 5176＋18081、`demo_full`）`/f/mail.notification/<id>` 整页渲染、字段全部只读（`inputs=0`）、「关联单据」显示来源名称 `展厅-市政工程样板段-任务 04`、`console_errors`／`http_5xx` 为空，列表→详情→返回 3 行真实行且返回 URL 与列表一致，390px `overflow=false`；三态 ORM 复验 normal→`act_window(project.task,23)`、deleted→`UserError 关联单据已不存在。`、denied→`AccessError`，夹具清理回读全 0。残留见 G-F3-06／G-F3-07。未合入前不宣称主线集成 |
| G-F3-06 | 中：有权限来源的「打开关联单据」在浏览器被导航授权层拒绝（**已修**） | 根因已收口为 P0 导航入口身份合成缺陷，非用户权限、非业务返回错误 action。修复：`normalize_odoo_action_result` 在业务动作**已声明目标**（显式 `res_id`，或 `target=new`）且未返回 action id 时不再调用 `_resolve_action_id_for_model` 合成模型最小 id；目标身份改由既有 `entry_target.record_entry`（`model`／`record_id`／`entry_intent`／`model_write_authority` 后端事实）承载，前端按无 `action_id` 的记录路由打开。未声明目标时保持原解析（由反向用例锁定）。追加反向用例同时锁定：**显式声明的 action 身份必须与声明的目标模型一致**，不一致时不再作为入口身份（见文末「追加三」）。五类浏览器验收全部通过，见文末「追加二」 |
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

### 2026-09-27 追加二：G-F3-06 修复与 G-F3-07／09／10 正式入口可达性分类

**G-F3-06 修复（P0 `smart_core`，独立于 `48a85a8c` 候选）**：修改 `addons/smart_core/core/navigation_entry_target.py::normalize_odoo_action_result`。原实现仅在 `target=="new"` 且显式 `view_id` 时才放弃合成 action id，其余情况一律调用 `_resolve_action_id_for_model`（`sudo()` 取该模型**最小 id** 的 `act_window`）。`mail.notification.action_sc_open_source` 返回的 `act_window` 声明了 `res_model`＋`res_id`（具体来源记录）但不含 `id`，于是被合成 `project.task` 的最小 id `349`——该 action 无任何菜单绑定，前端 `router.beforeEach` 按可见菜单派生 `routeAuthority` 必然拒绝。修复把「业务动作已声明目标」作为**不合成**的判据（显式 `res_id`，或 `target=="new"`），目标身份改由既有 `entry_target.record_entry` 承载；这复用的正是仓库已有关联记录导航契约（`RecordEntryContract`：`model`／`record_id`／`entry_intent`／后端 `model_write_authority` 事实），未新增第二套授权机制，也未放宽任何鉴权。

定向（非零）：`python3 addons/smart_core/tests/test_navigation_entry_target.py` **14/14**（新增两条：显式记录目标不得猜测菜单 action 且保留 `record_entry`；未声明目标仍解析模型 action 身份，锁定边界）；`scripts/verify/navigation_contract_boundary_guard.py` PASS；`test_execute_button_server_action_boundaries` 17/17；`test_scene_normalizer_entry_target` 1/1。`test_identity_resolver_entry_target` 11 项中 1 项失败（`smart_construction_core.menu_sc_project_initiation` 不在角色面），已用 `git stash` 在**未改动**版本复现，属既有基线失败，非本修复引入。

后端探针（受管 dev 环境，`demo_full`）：`_extract_action` 规范化后 `normalized_has_id=false`、`normalized_has_action_id=false`、`compatibility_refs` 只含 `model`＋`view_modes`、`record_entry={model: project.task, record_id: 140, entry_intent: open, model_write_authority: true}`。

浏览器五类验收（候选 5176／18081、`demo_full`，列表身份 `action_id=860&menu_id=675`）：

1. **可读来源打开成功**：通知 → 更多操作 → 打开关联单据 → 落到 `/f/project.task/140?entry_title=…` 并渲染任务表单（名称 `SC_DEMO_FULL_MY_WORK-1-任务01`、状态 In Progress、可编辑），`access_denied=false`，URL 中**无** `action_id=349`。
2. **不可读来源被拒**：来源为 `ir.actions.server:199` 的通知，点击后**停留通知页**，提示后端裁决 `You are not allowed to access 'Server Action' …`，未跳转、未泄露内容。
3. **已删除来源明确反馈**：来源 `res_id` 悬空的通知，点击后停留通知页，提示产品自身文案 `关联单据已不存在。`（后端探针同时复验 `UserError: 关联单据已不存在。`）。
4. **篡改目标模型／ID 不能越权**：直接构造 `/f/ir.actions.server/199` → `access-denied?reason=PERMISSION_DENIED`；这是后端读取裁决（`PERMISSION_DENIED`），不是绕过路由。该路径在修复前即为无 action 记录路由，本修复**未新增**未鉴权入口。
5. **返回通知详情**：浏览器返回后回到 `/f/mail.notification/<id>?action_id=860&menu_id=675`，操作按钮仍在。

夹具为专用临时对象（消息＋通知），验收后清理并回读：`remaining_notifications=0`、`remaining_messages=0`。`http_5xx=0`；`console_errors` 仅为被拒场景的 400／403 资源响应记录，无前端异常。

### 2026-09-27 追加三：显式 action 身份与目标模型冲突的反向锁定

**范围**：`addons/smart_core/core/navigation_entry_target.py` 的显式 action 身份判据 + 定向用例（本提交**不并入** `48a85a8c` 候选批次，不推送该候选分支）。

**缺口**：上一修复只覆盖「业务动作未声明 action id」的路径。若业务动作**同时**声明了目标模型／记录**和**一个 action id，原实现无条件信任该 id（`explicit_action_id or ...`），于是一个归属**另一个模型**的 action 会成为本入口的路由身份：前端 `actionContract` 会取 `raw_action.id`／`action_id` 作为 `actionId`（`actionContract.ts:309`），把外来 action 带进路由，绕过「以声明目标记录为准」的意图。

**修复**：新增 `_declared_action_conflicts_with_target_model`——仅当负载**声明的** `res_model` 与该 action 自身的 `res_model` 明确不一致时，判定该 id 不可作为本入口身份：丢弃它，改由声明的记录／新建目标承载（`entry_target.record_entry`），并同步从归一化负载移除，使消费者不会再把外来 action 当作路由身份。判定极窄：负载未声明 `res_model` 时不判定（回退到来源模型属派生默认，不是声明）；action 不存在或读取失败时不判定（存在性与可读性仍归既有路由鉴权）。**未新增授权机制、未放宽鉴权**：action 是否可达仍由既有「可见菜单派生 routeAuthority」裁决。

**「action 读不到」的边界（本轮补查）**：action 不存在或读取失败时**不判定冲突**，保留其声明身份（此时无法建立冲突，丢弃或改写等于伪造一个本层不拥有的授权判断）；因此该分支**不产生任何授权结论**——入口中没有 `authorized`／`permission`／`access` 类字段，`record_entry.model_write_authority` 仍是模型级访问事实而非「本 action 可打开」的断言。**最终访问仍由后端／路由鉴权裁决**：不可达或未授权的 action 会在既有 `routeAuthority` 校验处被拒（见本节点浏览器第 2／4 类证据）。

**非零定向**：`python3 addons/smart_core/tests/test_navigation_entry_target.py` **18/18**（新增 4 条：显式 action 与目标模型冲突时不得成为记录入口身份、未声明目标的冲突 action 被丢弃后按声明模型解析、**一致**的显式 action 身份必须保留（正向对照）、**读不到的 action 保留身份且不携带任何授权声明**）；`scripts/verify/navigation_contract_boundary_guard.py` PASS；`test_execute_button_server_action_boundaries` 17/17；`test_scene_normalizer_entry_target` 1/1。

**边界**：`_run_window_action` 等由后端自行读取 action 记录的路径，其 `id` 与 `res_model` 同源，不受影响。本轮为**本地定向通过**；无新增浏览器矩阵（既有五类证据的输入为同一入口路径，冲突分支为纯后端判据），**远端 CI／已合并／已部署／目标环境验收均未发生**。

**G-F3-07／09／10：只做正式入口可达性分类，不扩大修复**（`res_model`→`act_window`→菜单绑定实测）。以下「菜单数 0」**只说明该模型不是直接菜单入口**，它既**不能解释装配期异常**（G-F3-09 的 `ValueError` 发生在契约／表单装配阶段，与是否存在菜单无关），也**不能排除按钮、向导、关联记录或其它可达入口**。因此各行**保持待分类，不关闭**：

- `app.view.variant`：`act_window=0`、菜单 **0** → 无直接菜单入口；其契约探针 `ok=false` 是否构成产品缺口**仍未定性**。
- `ir.model.data`／`privacy.lookup.wizard.line`：各 1 个 `act_window`、菜单 **0** → 无直接菜单入口；按钮／向导可达性未排查。
- `sms.template.preview`（G-F3-09）：1 个 `act_window`、菜单 **0**。装配期 `ValueError: field occurrence identity is incomplete` 与菜单无关，**未定性、未修**；`sms.template` 本身有 `sms.sms_template_menu`（Odoo 基础菜单，不在产品导航策略内）。
- `ir.actions.server`、`mail.mail`（G-F3-10 余项）：各有 1 个菜单绑定，但均为 Odoo 基础/管理菜单（`base.menu_server_action`、`mail.menu_mail_mail`），**非产品正式入口**；`ok=false` 原因仍未查清。
- `project.task`（G-F3-07 关联）：14 个 `act_window`，仅 1 个菜单绑定（`project.menu_project_management_all_tasks`）。`properties`／`personal_stage_type_id` 静态命中仍属「未进入渲染解析」类，**在「可见且非空」条件建立前不做定性，也不扩大 `sc.input.text` 支持类型**。

分类结论：本轮只建立「是否为直接菜单入口」这一项事实；**G-F3-07／09／10 全部保持待分类（未关闭）**。不得据「无菜单」把 `ok=false` 判为无缺口，也不得据此定性为产品缺陷。本批不改这些模型的契约或前端类型校验。

### 2026-09-28 追加四：G-F1-03／G-F1-06 两个通用缺口修复与受影响业务联调

候选（本地提交，未推送／未合并／未部署）：`19b2d290` WEB-FIX-01、`c0b9a62e` WEB-FIX-02，分支 `fix/web-occurrence-identity-and-failure-atomicity`；审计基线 `28266e9b`。完整运行元数据、环境、角色、命令与 29 项检查明细见 `artifacts/frontend-web-fix-20260928/evidence.md` 与同目录 `acceptance-check.json`。

**G-F1-03（P0 occurrence 在事件消费边界丢失）——已修，收口于 `19b2d290`。** 原判定「页面合并同字段可写性导致只读位置可借同名字段写入草稿」成立。修复把发射位置的 occurrence 身份从字段变更事件入口（`useRecordActionPresentation.ts::onTemplateFieldChange`）经 `fieldChange.dispatcher.ts` 一路带到草稿写入，并在控件处打戳；带 key 的编辑只按该位置判定（契约 occurrence 优先、渲染位置次之），无法解析的身份**拒绝**而非回退到同名可写位置；`useRecordFormState.ts` 对延迟关系创建在应用结果时复核记录的 occurrence 身份，位置转只读或切换记录后不再写入新草稿。无 occurrence 身份的既有调用者（原生伴随控件、关系子表控件）与系统默认值／服务端 onchange 回填保留按名判定。

定向证据：`make verify.frontend.contract_field_occurrence_identity.unit` PASS（记录前置反例「只读位置不得经可写兄弟写入」修复前失败、修复后通过）；已加入 `verify.frontend.quick.gate`。**前置失败已于 2026-09-28 独立复现**：在 HEAD 的一次性 git worktree 中把 `resolveFormOccurrenceDecision` 换回旧的「任一同名位置可写即可写」汇总逻辑，该单测即失败于 `the read-only occurrence of amount is blocked`（actual `writable`／expected `blocked`）；恢复发布实现后通过，且该变更未保留。受管验收环境服务的生产构建 `assets/ContractFormPage-6z8lXPy7.js`（sha256 `4ab89eb3…`）含 8 处 `occurrenceKey`，证明修复已进入被验收的候选产物。

**边界（未证明者不得外推）**：受影响页（付款申请 `action_id=775`／`menu_id=545`）实际只渲染 14 个 occurrence 节点／14 个互不重复字段、**同字段多位置数为 0**，因此本轮**没有**可直接复现的只读/可写同字段位置浏览器反例；该反例由上述单测覆盖，浏览器侧记为 `NOT_RUN`，**不得**据此声称「浏览器已验证同字段双位置」。关系选择／清除／异步返回仅在受影响分支复核，未做全部关系组件重构验收。

**G-F1-06（P0 `api.data` 把后端 ValidationError 分类为 500/INTERNAL_ERROR）——已修，收口于 `c0b9a62e`。** 修复在 create/write 边界分类：`AccessError`／`AccessDenied` 保持明确权限拒绝，`MissingError` 为未找到，`ValidationError` 及其他 `UserError` 成为可识别业务失败（复用前端既有 `reason_code`／`error_category`／`suggested_action`／`retryable` 元数据），未预期异常仍是系统错误且信封只带泛化消息（服务端保留诊断），并把每次写尝试包进游标 savepoint，使整个逻辑操作（主记录＋关联写入）在转成业务失败响应前回滚。未新增全局异常框架，也未改 RPC 协议。

定向证据（真实 PostgreSQL，隔离库 `sc_test_wf02_rerun_20260928`，`make ci.full MODULE=smart_core TEST_TAGS=api_data_mutation_failure_atomicity` 的直接调用，退出码 0）：`addons/smart_core/tests/test_api_data_mutation_failure_atomicity_orm.py` **12/12，`0 failed, 0 error(s)`**，覆盖创建/更新 × 校验失败／权限拒绝／未知异常／成功，并以**handler 返回后、测试清理前**的原始 SQL 断言主记录与关联记录均未残留（禁用 savepoint 的前置记录确认部分写入会存活的旧行为）。前端：`make verify.frontend.contract_form_save_failure_recovery.unit` PASS（业务拒绝保留字段与关系草稿、不报成功、不刷新掉草稿、按钮可操作、重试成功、双击只发一次写），已加入 `verify.frontend.quick.gate`。

**WEB-CHECK-01 受影响业务联调（受管验收环境，同一候选）**：环境＝Odoo 17 验收后端 `sc-backend-odoo-acceptance`→`127.0.0.1:18082`、生产模式 vite preview `127.0.0.1:5175`（dist-release）、数据库 `sc_frontend_acceptance`；后端容器 12:49:45 启动、晚于 `handlers/api_data.py` 的 12:34:11 修改且源码直挂 `/mnt/source-addons`，容器内该文件含 `_mutation_savepoint`，故浏览器链路确实经过 WEB-FIX-02 代码。入口＝唯一矩阵行 `menu_sc_user_payment_apply`（菜单 545、action 775、模型 `payment.request`）。角色＝`fixture_role_finance`（业务角色）与 `fixture_role_project_a_member`（受限）。结果 **29/29 检查通过、`http_5xx=0`**：

- 创建：业务拒绝→HTTP 422、`error.code=VALIDATION_ERROR`、`reason_code=USER_ERROR`／`error_category=validation`；停留在 `/new`、保留已输入项目、提示为业务文案而非系统错误；纠正后→200→重定向到新记录。
- 编辑：业务拒绝→422 同一分类；停留原记录；**关系与数值两项输入均保留**；纠正后真实发出 `api.data` `write`→200；刷新回读显示纠正后的金额 30（真实落库，非旧草稿）；再次写回 20→200、回读 20。
- 返回列表渲染正常；窄屏 390×844 下同一拒绝的业务文案可见、已输入值仍在、保存按钮可见可用、无横向溢出；受限角色被拒（`NAVIGATION_AUTHORITY_DENIED`）且无财务数据泄露；控制台错误仅为预期的 422 资源行。

**本轮不得宣布**：89 个入口全部可用、目标部署版本已验收、同字段双位置浏览器反例已过、性能/无障碍/响应式全量通过。联调仅覆盖上述入口的创建/草稿保存/编辑/回读/受限拒绝，未覆盖提交审批链、其他角色、其他金额与合同组合，也未做全入口重跑。

### 2026-09-28 追加五：WEB-UAT-01 付款申请入口职责闭环（唯一矩阵回填）

本轮只推进唯一矩阵行 `menu_sc_user_payment_apply`（付款申请，菜单 545／action 775／模型 `payment.request`），把它做成可复用的业务验收样板；未展开 89 入口，未改产品源码，未改扫描器。候选＝分支 `fix/web-occurrence-identity-and-failure-atomicity`、HEAD `fc84fd24`（工作树干净、无暂存）；**本轮无新增产品提交**（未发现需要修复的直接阻断缺陷）。受管验收环境＝Odoo 17 `sc-backend-odoo-acceptance`→`127.0.0.1:18082`、生产模式 vite preview `127.0.0.1:5175`、隔离库 `sc_frontend_acceptance`。明细证据与命令见 `artifacts/frontend-web-fix-20260928/evidence.md#WEB-UAT-01`。

**职责覆盖（本入口适用职责已逐项验）**

- 直接 API 权限矩阵（真实受限角色会话，非管理员）：以财务创建的 `1803`（公司 8／项目 11）与 `1804`（公司 9／项目 12）为样本，覆盖「有权读/写、有权读无写、无权读、跨公司范围拒绝」。`fixture_role_finance`(uid30) 两记录读/写均 200；`fixture_role_executive`(uid37) 读/写 1803 成功、跨公司 1804 读/写均 403；`fixture_role_finance_user`(uid44)、`fixture_role_project_a_member`(uid31) 对该二记录读/写均 403；`fixture_role_config_admin`(uid34) 1803 可读、1804 为 `PROJECT_SCOPE_DENIED`(403)。拒绝信封为 `PERMISSION_DENIED` 且不含被拒记录的字段，写被拒后回读记录未变化。
- 业务流转（真实状态转换，用正式 action 与 intent）：创建→`draft`；提交（`action_submit`，带契约 authority）→`submit`；财务审批（`payment.request.approve`）→`approved`（`validation_status=validated`）；拒绝（`payment.request.reject` 带原因）→`rejected` 且原因落库；纠正（`write amount`）后再次提交→`submit`，再审批→`approved`；`action_done` 对 `type=pay` 被拒（`BUSINESS_RULE_FAILED`「付款申请必须通过专业付款登记完成实付」）证明**审批≠实付执行**；`create_execution` 返回 `action_result` 指向 `smart_construction_core.action_sc_payment_execution_partner_payment`（`res_model=sc.payment.execution`、`context.default_payment_request_id`）且**不**代建执行记录（仅交接，未入库执行）；取消（`payment.request.mark_reversed`）→终态；进入审批后写业务事实被拒（422，要求取消后重发）。办理待办面＝`payment.request.available_actions` 在 `submit` 态对财务返回 `approve/reject` allowed=true，且工作项投影 `my.work.summary`→`product_workspace.sections` 在该记录待办期间包含 `payment.request:<id>`、审批后移出。
- 列表查询/筛选/分页/详情返回上下文：页面级搜索关键字过滤（`PRQ2600337`→单行）、行内打开详情、点「返回」后列表路由带 `search=` 还原、筛选行仍在、清空后恢复整页；列表现渲染分页器（每页 10），该角色默认域内数据集在单页内，跨页由契约层 `op=list limit/offset` 返回互斥页集验证。
- 关系选择/清除：对同一条记录清空并复原 `settlement_id`，均 200 且回读一致（无部分写入）。
- 附件：`file.upload`→`file.download`（base64 与原文一致）、受限角色下载 403「无下载权限」、`chatter.attachment.delete` 删除后回读 404。
- 明细行：视图 `outflow_line_ids` 为 `create="false"`、`receipt_invoice_line_ids` 为 `create="false" delete="false"`，**按职责而非测试便利**判为不适用（该入口不承诺在此新增/删除明细）。

**边界（不得外推）**：本入口适用职责已具备证据，故 `menu_sc_user_payment_apply` 由 `partial_passed` 回填 **`passed`**；矩阵现为 **87 `not_run` / 1 `partial_passed`（`menu_sc_product_project_edit_v1`）/ 1 `passed`**。仍不宣布：89 入口全部可用、目标部署版本已验收、同字段双位置浏览器反例已过（仍为单测覆盖＋页面 `NOT_RUN`）、性能/无障碍/响应式全量通过。`my.work.summary` 属工作台入口面，本轮只作本入口流转的关联证据，**不**据此把工作台行标通过。数据清理：本轮创建的 `1805..1812` 均经 `payment.request.mark_reversed` 进入终态 `cancel`（无强删），附件已删除，fixture（`1794/1795/1787/1710/32/33/18`）未变。

### 2026-09-28 追加六：WEB-EVIDENCE-02 89 入口既有业务证据只读归集（不回填通过）

只读核对，未改产品源码、未改矩阵、未跑浏览器/测试。方法：以唯一矩阵 89 个 `menu_xmlid` 为键，扫描仓内 `docs/`（4711 个文本文件）与仓外 `artifacts/`（523 个文件命中某个入口 xmlid），沿引用回溯原始报告与成功归档。

**归集结果：本批未发现可把其他入口提升为 `passed` 的业务证据。** 现有产物按证明确力分三类：

- 覆盖/结构元数据（不可作业务验收）：`docs/frontend_productization/domain-rollout/*` 与仓外 `frontend-professionalization/*_runtime_v1.json`、`product_menu_catalog_runtime_v1.json` 等，只声明入口/模型/呈现覆盖（`coverageStatus=covered`），不含角色、写入事实或权限拒绝。
- 管理员只读页面渲染（不可替代业务验收）：`artifacts/playwright/**` 共 **260** 份 `sc_test_admin` 运行且 `mutationCount=0`，证明页面可达与呈现，不证明查询办理、写入回读或受限拒绝。
- 受限角色只读路由（仅证明角色可达性/拒绝）：`demo_role_pm`/`demo_role_finance` 各 5/3 份、仍 `mutationCount=0`；其中 `playwright/project-permission-matrix`（action 859／menu 679 = 项目信息编辑）显示受限角色被 `NAVIGATION_AUTHORITY_DENIED`，与该行既有 `partial_passed` 一致，**不构成升级**。

据此：**不按模型名或共享组件名批量标绿**；`menu_sc_user_payment_apply` 之外无行升级，矩阵维持 **87 `not_run` / 1 `partial_passed` / 1 `passed`**。旧 `/tmp/frontend-f1-*-20260923` 类证据源已不存在，相关入口保持缺证据结论，不追认。

**下一组候选及剩余职责（按真实入口 ID，组≤3）**

- 组 A 项目台账：`menu_sc_product_project_edit_v1`（项目信息编辑，现 `partial_passed`；欠：按角色的写入/回读、列表筛选分页与详情返回、关系/明细职责）、`menu_sc_project_initiation`（新项目立项）、`menu_sc_product_project_lifecycle_v1`（项目启停管理）。
- 组 B 合同办理：`menu_sc_p1_income_contract`（收入合同）、`menu_sc_p1_expense_contract`（支出合同）、`menu_sc_p1_daily_contract`（日常合同）。

两组各自的缺口均为：直接 API 权限（有权读/写、有读无写、无权读、数据范围拒绝）＋创建/编辑与状态流转的真实回读＋列表查询筛选分页与详情返回上下文＋关系选择清除＋（承诺时）附件上传下载权限。本阶段不运行浏览器、不执行测试、不操作数据。

**不得宣布**：89 入口全部可用、目标部署版本已验收；`phase10-*`/rollout 产物不得被当作业务办理验收。

### 2026-09-28 追加七：WEB-UAT-01A 付款申请定点补证、WEB-UAT-02 项目三入口（唯一矩阵回填）

候选：源码验收候选仍为 `fc84fd24`（`19b2d290` WEB-FIX-01／`c0b9a62e` WEB-FIX-02），本轮仅文档与矩阵回填，HEAD `a2c4003f`，分支 `fix/web-occurrence-identity-and-failure-atomicity`；**本轮未改产品源码**（`git status` 干净）。环境＝Odoo 17 验收后端 `sc-backend-odoo-acceptance`→`127.0.0.1:18082`、生产模式 vite preview `127.0.0.1:5175`（dist-release）、数据库 `sc_frontend_acceptance`。完整运行元数据与原始日志见 `artifacts/frontend-web-fix-20260928/`（`uat01a-raw/`、`uat02-raw/`）与同目录 `evidence.md` 的 `# WEB-UAT-01A`、`# WEB-UAT-02` 两节。

**WEB-UAT-01A 付款申请定点补证（`menu_sc_user_payment_apply`）——页面级证据已补齐，但明细职责存在未修复阻断，状态由 `passed` 改回 `partial_passed`。** 补齐项（均为**页面点击**，非直接 API）：①附件经页面真实上传控件 `setInputFiles`→`file.upload` 200→列表显示→刷新仍可见（附件 1091，65B）→点击下载→`file.download` 200 且产生真实浏览器下载事件，下载字节 sha256 与上传一致（15/15）；②分页经可见「每页 10 条」选择器→点下一页→页码与记录集合变化→打开第二页详情→返回后仍在第二页且行集合与筛选保持（11/11）。明细职责范围按视图与运行时子视图契约核定：`outflow_line_ids` 内联可编辑、自由新增被禁（`create=false`）但存在受控新增路径「从结算单引入」、允许删除；`receipt_invoice_line_ids` 因 `type != 'receive'` 在本入口不渲染；`ledger_line_ids` 只读且不在本入口渲染面。**据此不再把明细整体写为「不适用」。**

**~~未修复阻断~~ → 已关闭（FE-TPL-05A，2026-09-29；见文末）**（原文保留：本入口无法取得「编辑已有明细行后保存」证据）**：多行付款申请（经正常 UI 由结算单引入、`source_line_type` 全部为常量「结算单明细」）在编辑任一明细单元格后保存，前端不发写请求并提示 `outflow_line_ids 存在重复行值：结算单明细`／`主值重复：结算单明细`（证据 `uat01a-raw/uat01a_line_dup_block.txt`）。根因：`frontend/apps/web/src/pages/contractForm/one2manyUtils.ts:521-549` 的 `collectOne2manyDraftValidationFromRows` 以 `one2manyPrimaryColumnFromColumns`（**首个业务列**）作行身份，而本子视图首列为 `source_line_type`，导入处理器 `addons/smart_construction_core/handlers/payment_request_settlement_introduce.py:526` 给每行写同常量，于是两行以上互相判重；对照实验（两行 `source_line_type` 取值不同）同一编辑保存即可成功。属既有行为（文件最后修改于 `de9a230d`/`0b47763`，非 `19b2d290`/`c0b9a62e` 引入）。最小修法（**未实施**）：对已持久化行改以记录 id 作行身份，而非主列标签；因该断言被全局 one2many 校验共用，改动语义面较大，故保留为待批准的阻断 + 修法建议，不在本轮改动。 **→ 已关闭（FE-TPL-05A，2026-09-29）。** 该断言已改为按**行身份**判重（`id:<record>` / `key:<draft key>`），列值只作显示、不承担业务唯一性；修法与本段建议一致，但落在 adapter 自身拥有的不变量上而非新增业务规则。真实页面复验：付款申请草稿从两张结算单引入 2 行（`source_line_type` 同为常量）→ 编辑其一 → 保存 → 刷新回读，被编辑行正确、其他行未串位、无重复创建、来源关联正确，且发出真实写请求；`adopted_form_validation_identity` 46/46、`collection_view_semantics` PASS、`typecheck.strict` exit 0。详见同目录文末《FE-TPL-05A：付款申请主从办理接管》。

**发现二（治理元数据，非产品缺陷）：矩阵 `role_authority` 无法表达 role-surface 暴露层。** `project.project` 三条入口的 Odoo 菜单/动作组绑定实测为：`menu_sc_product_project_edit_v1`（菜单 680/动作 861）＝`group_sc_cap_project_user+group_sc_cap_project_manager`；`menu_sc_project_initiation`（374/708）＝**同一对组**；`menu_sc_product_project_lifecycle_v1`（681/863）＝`group_sc_cap_project_manager`。`fixture_role_pm` 同时持有 manager 与 user 组，但其运行时路由面（`system.init`→`navigation.route_authority`，`primary_actions`）**只含 861，不含 708/863**，故 SPA 对 708/863 返回 `NAVIGATION_AUTHORITY_DENIED`（`router/index.ts` 的 `NAVIGATION_AUTHORITY_DENIED` 分支）；列表路由与建单路由结论一致，非路由形态问题。来源为声明式角色面策略 `addons/smart_construction_core/core_extension_policy_maps.py`→`ROLE_SURFACE_OVERRIDES["pm"].primary_menu_xmlids`：列了 `menu_sc_product_project_edit_v1`，未列另两者。**矩阵 role_authority 单元格只录 Odoo 组链、不含该层**，故对 pm 会预测可进 708/863 而运行时被拒——已在三条入口的 `gap` 单元格如实记录，**未**擅自改写组链为猜测值，交治理方复核。

**WEB-UAT-02 项目三入口（同一测试项目 463 贯穿，非三条无关样本）**

- `menu_sc_product_project_edit_v1`（项目信息编辑）→ **`passed`**：列表关键字筛选→行详情→返回后 `search=` 与筛选行保持；说明（富文本）／项目名称／日期（日历控件选日）／客户关系真实写入并刷新回读；责任矩阵行经页面「添加责任矩阵」新增（角色=项目经理、责任人=Acceptance Fixture PM）保存并回读（DB `project_responsibility` id 1 确认）；清空必填「项目名称」保存＝零写请求＋`项目名称不能为空`，已输入说明与客户草稿保留，纠正后重试成功且刷新后一致；名称与日期改动后已复原。运行：`uat02-raw/uat02a_duties.json` 19/19、`uat02a_name_date.json` 5/5。
- `menu_sc_project_initiation`（新项目立项）→ **`passed`**：页面立项表单→「创建项目」`api.data create` 200→跳转新建记录；后端回读新建项目 `lifecycle_state=draft`（并在启停入口状态栏显示「草稿」）；空名称保存被拒且无 create（`uat02-raw/uat02_entries.json`）。入口按自身声明不提供独立列表，未以「缺列表」记缺口。运行：`uat02-raw/uat02b.json`、`uat02c_transitions.json`。
- `menu_sc_product_project_lifecycle_v1`（项目启停管理）→ **`partial_passed`**：状态栏只读事实；「启动项目」draft→in_progress、「更多操作→暂停项目」in_progress→paused（状态栏「停工」）、「恢复项目」paused→in_progress，均经 `execute_button` 后刷新回读；当前状态不允许的「启动项目」直接调用被 **403**（`ACTION_CONTRACT_AUTHORITY_MISSING`）且状态不变。**未验证**：标记竣工／进入结算／进入保修期／关闭项目（含关闭确认弹窗）——测试项目 463 按计划保留在 `in_progress` 供下一批复用，故本轮不terminalize。运行：`uat02-raw/uat02c_transitions.json` 6/6、`uat02c_life.json`、`uat02c_archive.json`。

**直接业务 API 权限边界（不以导航拒绝代替）**：真实受限会话 `fixture_role_project_a_member`、`fixture_role_finance` 对 463 的 `api.data write` 与 `execute_button(action_sc_pause)` 均 **403 PERMISSION_DENIED**（「用户无权以 write 访问模型 project.project」），463 的 `location` 未被改动；`fixture_role_config_admin` 同路径成功。运行：`uat02-raw/uat02_api_deny.json` 10/10。

**测试数据**：`project.project` 463（`in_progress`，`partner_id=56`，`location=FE-UAT02-LOC-EDIT`，名称/日期已复原，1 条责任矩阵行）与 464（`draft`，为证明立项后草稿态而建）**均保留**、未强删、未强制关闭；`payment.request` 1813（draft，2 条 outflow 行、附件 1091）保留；上一轮已终态化的 1803–1812 未触碰。

**矩阵实际分布**：本轮后 **85 `not_run` / 2 `partial_passed`（`menu_sc_user_payment_apply`、`menu_sc_product_project_lifecycle_v1`）/ 2 `passed`（`menu_sc_product_project_edit_v1`、`menu_sc_project_initiation`）**，分母仍 89。

**不得宣布**：89 入口全部可用、目标部署版本已验收、付款申请明细「编辑已有行后保存」已通过、启停管理其余状态转换已通过、同字段双位置浏览器反例已过（仍为单测覆盖＋页面 `NOT_RUN`）、性能/无障碍/响应式全量通过。`my.work.summary`／工作台面、合同组入口均不因本批关联证据而被标通过。

### 2026-09-28 追加八：定位调整为「契约表达 ↔ 成熟组合」贯通；首批语义沿链核对

**本轮定位调整（治理口径）**：建设对象是**契约的产品表达能力 + 成熟组合的适配与消费**，样板页面是**验证结果**，不是目标本身。不再按「某页面改版」立项，也不单独交付一轮「L2 可替代行数」量化报告。既有 `contracts/`、kit、page-patterns、本缺口记录、唯一入口矩阵继续复用，不新建平行体系。

**判定链（每项能力都必须四段齐备）**：原生事实是否存在 → 契约是否准确表达 → 消费端是否实现 → 是否交给成熟组合执行。缺哪段补哪段；不以继续加 YAML 掩盖消费缺失，也不以继续加 Vue 分支弥补契约缺失。

#### 已交付检查点 `06f14f14`（呈现，已定向验证）

`frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue`（仅此一文件，+52/−4）：

- **身份**：标题改为记录业务身份，删除与之重复的副标题行；入口标签仍由面包屑承载。实测同一记录名称此前在面包屑、活动页签、H1、副标题出现 4 处，现降为面包屑 + 页签 + H1。
- **主动作**：命令栏此前**不存在高强调主操作**——`保存修改` 由契约按普通层级下发，渲染为 `t-button--variant-text t-button--theme-default`（ghost），与 `返回` 同权重，违反 `docs/frontend_productization/frontend_product_design_system_v1.md`「每个任务范围最多一个高强调主动作」。现由唯一保存动作认领主动作（direct 与 canonical 两种形态互斥，内置保存/草稿已认领时不重复）。

验证：`menu_sc_product_project_edit_v1` / `project.project` 463（`fixture_role_pm`，1440×900 与 390×844）——主动作计数 1、H1＝记录名、无重复副标题、窄屏无横向溢出且保存可操作；`uat02a_name_date` 编辑→保存→刷新回读 5/5 无回退（`/tmp/wf_check/fepat01-*.png`、`fepat01_baseline.json`、`fepat01_after.json`）。`typecheck:strict` 通过；`typecheck` 31 项＝历史同集合、本轮零新增且本文件 0 项；`frontend_page_pattern_reference_parity_guard` PASS；`verify.frontend.product_page_header.unit` 69/69、`product_page_pattern.unit` 5/5、`form_header_action_promitives.unit` 8/8（`buttonVariant`/`canonicalButtonVariant` 的 destructive/primary 映射**原样保留**，认领逻辑叠加在其上，未改动门禁所固定的表达式）。

**边界（不得外推）**：该改动位于共享表单命令栏，**所有**契约表单入口的外观随之变化；本轮只验证了上述一个入口，其余入口的呈现证据**未重验**，业务证据按原适用范围保留。`06f14f14` 是**消费端兜底**——契约侧仍未把保存动作表达为主次层级，契约侧表达为待办。

#### 首批语义沿链核对（只读，按「未投影 / 未表达 / 未消费 / 未接成熟能力」分类）

| 语义 | 原生事实 | 契约表达 | 消费端 | 成熟组合 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 页面模式与分组 | `<group>`/`<notebook>` | 已表达（`presentationMode`、容器节点） | 已实现 | 已接（`TaskFormPattern`/`WorkspaceFormPattern`） | **已贯通**；两 pattern 各仅 22/26 行，视觉政策仍落在 `FormSection.vue`(1388 行) 而非契约声明的密度/强调策略 |
| 字段位置与动态条件 | 原生修饰条件 | 已表达（`field.widgetId` + `readonly`/`disabled`） | **已修**（`fieldOccurrenceWritability.ts`，WEB-FIX-01） | 已接 | **已贯通**；页面实测 24/24 字段带 `data-occurrence-index` |
| 主次动作 | 动作与状态 | **未表达**：`form.save` 以普通层级下发，无主次 | 兜底认领（本轮 `06f14f14`） | 已接 | **未表达** → 正解在动作层级/呈现适配器，不在命令栏 |
| 错误归属 | 字段级错误 | **未表达位置身份**：`canonicalFormRenderState.ts` 以 `validationFieldErrors[field.fieldCode]` 取用，`formValidationFocus.ts` 按 `data-validation-target`/`data-field-name` 定位（24 字段中 9 个有 target） | 按字段名回退到首个可见位置 | 未接 | **未表达 + 未接**：同字段多位置的错误归属无法表达，与 occurrence 写入判定形成不对称 |
| 通用校验编排 | — | — | 自研：`saveRecordHelpers.ts` 216 行 + `valueUtils.ts`/`fieldUtils.ts` | **未接**：页面无 `<form>`、`t-form` 计数 0 | **未接成熟能力**；阻塞点是消费端 API 暴露——`ScForm.vue` 为 2 行薄包装且**无 `defineExpose`**，实例方法（`validate`/`validateOnly`/`setValidateMessage`/`clearValidate`）对调用方不可达。已核实本地 `tdesign-vue-next@1.20.5` 含 `rules`、`scrollToFirstError` 与上述实例方法 |

**未发现的断点（不计入缺口）**：`data-product-page-mode="form"` 存在于直接表单路由（`DIV.template-layout-shell`），`focusProductFormValidationError` 的根选择器可用——本轮曾怀疑该路由缺失，实测为探测选择器问题，**不记为缺陷**。

**下一步（本记录为入口）**：按上述分类先做「错误归属的位置身份表达」与「保存动作主次表达」两项契约侧表达，再由 `ScForm` 补齐实例方法暴露、把一个入口的通用校验编排接到 TDesign Form，并以第二个业务入口复用同一组合作为设计正确性的检验信号。付款明细行身份问题（首列当唯一键）保持独立修复，不并入表单迁移。

### 2026-09-28 追加九：CONTRACT-ERR-01 错误业务归属契约与 Web 位置消费贯通

**范围**：只做追加八表格第 4 行「错误归属」。不迁移 ScForm、不改动作主次（第 3 行仍未表达）、不处理付款明细唯一性、不动 R7R9／R5。本记录不新建平行矩阵，89 分母不变。

**契约已表达（终端无关）**：新增 `frontend/apps/web/src/app/businessValidationError.ts`。

- 错误以**业务目标**表达：`target = { model, recordId, fieldCode, row }`；`row = { relationField, recordId, rowKey, cellField }`。`code` 是规则身份（`REQUIRED_VALUE_MISSING`／`ROW_KEY_DUPLICATE`／`BUSINESS_RULE_REJECTED`），`message` 是安全提示。
- **无字段归属的错误是合法形状**：`fieldCode` 为空时拒绝生成字段目标（返回 `null`），调用方保留表单级提示，不编造 target。
- 核心模块不 import Vue／不读 DOM／不引用 TDesign（有源码守卫），不含 DOM selector、组件实例、组件 props、页签编号、像素位置或 Web occurrenceKey。`sourceOccurrenceKey` 只是**本地显示上下文**，不是业务归属、不是授权依据。
- 明细行身份用已有真实 `recordId` 或既有稳定草稿 `rowKey`；缺任一稳定部件即**拒绝**（`normalizeBusinessRowIdentity` 返回 null），不以行号、显示文案或首列值代替。

**真实错误生产已接入（不是只在测试里构造）**：

- 必填：`saveRecordHelpers.collectRequiredFieldValidation` / `validateBeforeSaveRecord` 新增 `model`、`recordId`，产出结构化 target；`SaveRecordValidationResult.fieldErrors` 的类型由 `Record<string, string>` 改为 `Record<string, BusinessFieldError>`。
- 明细：`one2manyUtils.collectOne2manyDraftValidationFromRows` 新增 `model`，行错误携带 `rowKey`／`cellField`；`useOne2manyRuntime` 新增 `model: () => string`，页面传 `model.value`。
- 服务端：`decodeServerFieldErrors` 只接受显式 `details.field_errors[]`；只有文案时保持表单级；**声明了行但身份不完整的条目丢弃，而不是降级成关系字段级**（本轮修正）；绝不从异常文案、字段标签或请求参数猜字段。**产品后端当前不产生 `field_errors`**，该解码器为兼容扩展存在。

**Web 解析已消费**：

- `canonicalFormRenderState.applyCanonicalFormValidation` 按 `errorOwnsField`（model + recordId + fieldCode）匹配，每个 fieldCode **只装饰一个**位置：来源 occurrence（仍可纠正时）→ 首个可纠正 → 首个可见；无可见位置则**不装饰**（不把错误挂到用户看不见的位置）。不再用「任一同名位置可写／排在前面」放行。
- `validationErrorPosition.selectValidationPosition`（无 DOM，可单测）：先来源 occurrence → 首个 `visible && correctable` → 否则 `summary`；**绝不因 DOM 靠前就选只读副本**。
- `formValidationFocus.focusProductFormValidationError`（改为 async，消费入口不变）：解析显示键 → 优先 `[data-validation-target]`，回退 `[data-field-name]`；`data-field-state="readonly"`、`disabled`、`aria-disabled`、`readOnly` 均视为不可纠正；折叠区先展开再定位一次；无可用位置时聚焦 `[data-form-error-summary]`，**不丢错误**。
- **单一错误存储**：`useContractFormPageState.validationFieldErrors`；服务端 422 经 `indexBusinessFieldErrors` 汇入同一存储，不新建第二套独立错误存储。
- `useRecordFormFieldSchemas.resolveErrorText` **删除**原先「用 `field.label` 做 `includes` 匹配」的猜测式实现，改为 `selectFieldErrorsForTarget`；`FormSection.vue` 字段根节点登记 `data-validation-target`。

**本轮修复的实际缺陷（超出「只加字段」）**：

1. `useRecordPageLifecycle` 解构了 `validationFieldErrors`，但 `ContractFormPage.vue` 调用点未传入 → `reload()` 写 `undefined.value` → 项目编辑页整页崩溃（`Cannot set properties of undefined (setting 'value')`），表单契约请求根本不发出。已在页面调用点接线；并在新测试中加**调用点守卫**（该组合签名为 `Record<string, any>`，类型系统拦不住这一类）。同一 URL 实测：HEAD 渲染 24 字段正常 / 中间态 0 字段 + PAGEERROR / 修复后 24 字段正常。
2. `decodeServerFieldErrors` 曾把「声明了行但缺 `row_key`」的拒绝降级成关系字段级错误，等于替后端断言整个明细集合被拒。改为丢弃该条，保留表单级提示。

**已验证控件与反例**：新增 `frontend/apps/web/scripts/contract_error_business_ownership_test.ts` 与 make 目标 `verify.frontend.contract_error_business_ownership.unit`（**90 例**），已并入 `verify.frontend.quick.gate`。覆盖：A 同字段两处（首处只读）错误只落在可纠正位置、只读位不装饰且不参与写入；B 多个可写位有来源用来源、无来源稳定选择、只产出一份业务错误；C 同名子字段跨行靠 `rowKey`／`recordId` 区分、重排后仍命中、新行（`recordId null`）不串位、身份不全即拒绝、行错误不装饰记录级字段；D 无可用位置安全降级为摘要且错误保留、不可解码键不猜位置；E 兼容（`field_errors` 接受并限定范围／仅文案与无字段条目保持表单级／缺 `row_key` 丢弃／切记录与切模型不污染）；F 必填失败 → 结构化归属 → 草稿不被清空 → 保存门拒绝 → 纠正 → 同一门通过；以及同字段多位置与终端无关性（同一业务错误两种位置安排下业务目标不变）、源码守卫（核心模块不依赖渲染框架／DOM／组件库）。

**浏览器验证**（`menu_sc_product_project_edit_v1` / `project.project`，`fixture_role_pm`，真实路径 列表 `/m/680` → 记录）：`/tmp/wf_check/journey3.json` **22 项 check 全部通过、0 失败**。

- 24 字段中 **19 个注册 `data-validation-target`**（追加八记录的 9 个已随 `FormSection.vue` 改动升至 19）；未注册的 5 个（`project_code`／`company_id`／`analytic_account_id`／`source_created_by`／`source_created_at`）实测均为 `data-field-state="readonly"` + `data-field-auth="read"` 的只读展示位——**只读节点不需要输入焦点**，不算缺陷。
- 必填失败（清空 项目名称 → 保存修改）：**未发出任何写请求**（客户端门先拦）；`[data-validation-target="name"]` 是**唯一**被装饰的 `invalid` 位置，`aria-invalid="true"`，字段旁提示与摘要按钮文案同为「项目名称不能为空」；表单未关闭、未标记成功；无关字段与责任字段草稿保留。
- 摘要定位：点击摘要条目后 `document.activeElement` 落在该可纠正位置内的 `INPUT`（`data-field-name="name"`、`data-field-state="invalid"`），**不是只读副本**。
- 窄屏（390×844）：摘要与字段提示仍可见可读、保存可操作、无横向溢出。
- 纠正后字段状态回到 `required`、摘要消失；真实编辑（`location` 置标记）保存 **200 write** → 刷新回读一致 → 测试编辑已还原、记录回到原状；返回列表后行仍渲染。无 5xx、无页面级运行错误。

**同字段双位置反例**：本验收页 24 字段**无重名**，故**仅单测覆盖**，不为凑截图修改正式业务布局（与既定边界一致）。

**仍只支持表单级提示的后端错误**：产品后端目前不产生 `field_errors`。实测付款 422（`code=VALIDATION_ERROR`、`error_category=validation`、`suggested_action=fix_input`、文案「合同项目必须与付款/收款申请项目一致。」）只进 `validationErrors` + 摘要，**不猜字段、不标红**。因此**不得宣布「全部后端错误精准定位」**，也不得宣布「成熟表单组合已接入」。

**共享改动的实际消费范围（不得缩写成「只影响项目页」）**：`FormSection.vue`、`X2ManyRelationRenderer.vue`、`canonicalFormRenderState.ts`、`useRecordFormFieldSchemas.ts`、`ProductFormErrorSummary.vue`、`useRecordActionPresentation.ts` 均为**共享**消费端，所有走契约表单的入口其字段错误展示与定位路径随之改变。本轮**只对项目编辑页做了浏览器验证**，其余入口的呈现与定位证据**未重验**，业务证据按原适用范围保留；89 分母不变，未批量升级任何入口状态，也未改动唯一入口矩阵。

**验证与门禁**：`typecheck:strict` PASS；`typecheck` **31 项 = HEAD 同集合**（归一化行列号后逐行 diff 无差异，零新增）；`verify.frontend.quick.gate` 运行到完成，**只剩 4 项 HEAD 即失败的既有红项**（`scene_component_bridge.guard` 期望字面量 `v-else-if="field.readonly"` 在 HEAD 已不存在、`professional_base_field.unit` 与 `professional_relation_field.unit` 的源码文本守卫、`rendering_detail_state.unit` 的 `internalVendorSelectorGapCount` + `component-professionalization-inventory-v1.json` stale），本轮既未新增失败项也未改动这些守卫；`component-driver-takeover-inventory-v1.json` 因新增两个源文件重新生成（仅 `inputDigest` 一行）。付款 422 回归（`/tmp/wf_check/journey2.mjs`）有 2 项失败，经 **HEAD 对照运行复现同样结果**，确认为脚本预期／数据漂移（草稿等于原值时产品不再发写请求；该记录 `amount` 为空），非本轮回归。

**仍未做（不宣布）**：动作主次语义仍由消费端兜底（追加八第 3 行未变）；ScForm 实例方法暴露与单入口通用校验编排未接（第 5 行未变）；付款明细行唯一性独立未修；未推送、未合并、未部署。

**证据位置**：`/tmp/wf_check/journey3.json`、`journey3-error-desktop.png`、`journey3-error-narrow.png`、`journey3-saved-desktop.png`、`quickgate06.log`；契约与位置解析单测见 `verify.frontend.contract_error_business_ownership.unit`。

### 2026-09-28 追加十：CONTRACT-ACT-01 动作业务意图与 Web 适配

**批次状态：批次验收完成（下述限定范围）。** 起点 `86dc1359ce24abdf345866e8d2c4bf30438c4c80` clean，迭代身份为该 HEAD 加本节关联修改，最终代码状态绑定本节所在提交；仅本地提交，不推送、合并或部署。CONTRACT-ERR-01 仍绑定 `c79809757b25f9af779fc4e20e5d28a4a22f029c`，不重拆历史提交。31 项类型错误已由 `86dc1359` 收口，见同目录 `frontend_full_typecheck_closure_20260928.md`，不是本轮待修基线。

**边界与归属**：P0 `smart_core` / 现有 `@sc/schema` / frontend renderer 负责终端无关动作规范化和通用消费；P1 既有付款动作注册表及 workflow service 只声明自身业务动作意图，平台不猜行业方法；P4 现有 project_profile_write browser 工具增加专属定向模式，工具不承载产品规则。无 P2/P3 变更，不接 ScForm、不改保存函数、授权、状态机、ORM 原子性、付款明细或 R7R9/R5。影响所有消费共享 V2 form action/header 的表单；浏览器范围仅项目编辑入口，不能等同所有入口验收，89 分母及入口等级不变。

**权威链**：

- `unified_page_contract_v2_assembler._append_standard_form_save_action` 按已有 create/write 权限产生 `form.save` / `contract_action:form.save`。明确 `actionSemantics={kind:persistence,purpose:save_draft,executor:record.save,origin:platform_form_action,operation:create|write}`，`target.model/operation` 绑定既有持久化能力；不是 `form.save` 后端方法。默认文案按所有者最新意见统一“保存草稿”，治理文案不覆盖该保存含义，仍保留已有显式 tier 策略。
- P1 付款动作 `_ACTION_SPECS` → `_action_entry` 的既有返回 → financial_workspace_contract → runtime business action projection → actionRuleList，保持原方法、目标及条件；workflow registry 分别声明 submit/approve/reject/cancel_record。未知业务动作仍保留原合法分发绑定。
- `frontend/packages/schema/src/actionSemantics.ts` 定义终端无关语义与共享客户端 back/discard 注册，Header 的既有 emit 消费注册绑定。返回、放弃本地修改不等于业务取消。
- V2 decoder 是单一旧输入兼容入口：仅精确历史 `form.save`＋`contract_action:form.save`，不匹配文案、模型、方法正则；显式无效声明不得回退为旧保存。服务端合并冲突保留 `{conflict:true}`，不最后值覆盖。
- canonical presenter 消费既有状态/权限，Web `contractFormHeaderCanonicalActions` 按编辑任务/decision floorplan 适配强调、顺序、收纳、busy/loading。编辑保存唯一时突出；显式呈现配置继续在 Web 处理，冲突零主操作；拒绝、取消、返回不自动提升。无修改和必填错误不在适配器禁用保存，由既有 saveRecord 决定无写入/校验定位。Header 删除 ID 猜保存的主色兜底，保留标题身份与窄屏成果。
- canonical executor 经规范化的 `record.save` 绑定进入原 `saveRecord`；业务动作继续精确 backend/native identity 分发。不存在第二份动作状态存储。

**验证索引（阶段身份：起点 HEAD＋上述 dirty scope；日志最终归档后补路径）**：

| 层 | 命令/结果 | 状态 |
|---|---|---|
| L0 | preflight、单写者、diff check；sc-local-dev/sc_dev_demo 固定运行环境 | passed |
| L1 | `make ci.local.iteration`（非零静态测试，建议不自动执行）；首次旧推断反例失败，修复后通过 | passed |
| L2 | `make verify.unified_page_contract.v2.runtime verify.unified_page_contract.v2.schema`：20＋93 tests、runtime guard、4 schema examples | passed |
| L2 | `make verify.frontend.contract_header_action.unit`：真实历史 runtime 样本＋Python 真实 assembler → decoder → adapter/executor；语言变化、创建/更新/只读、loading、冲突、未知、两种纯数据呈现 | passed |
| L2 | canonical_form_presenter.unit 177＋10；contract_form_save_failure_recovery.unit 4 组；contract_error_business_ownership.unit 90 | passed |
| L2 | product_page_header.unit：28 数据例、4 entries/15 axes adapter checks、70 guard tests；form_header_action_primitives.unit 9；native_form_action_presentation.unit 16 | passed；仅更新被本轮语义／事件绑定直接影响的旧断言 |
| L1 | 完整与 strict 类型检查、lint | passed：类型 0 错误；lint 0 errors / 40 warnings |
| L2 | 既有 P4 fixture/browser 单测 | passed：43 tests |
| L4 | `make verify.frontend.build` | passed：最终受影响产物重建，20.62s；保留 chunk size 警告 |
| L3/L4 | scoped runtime/browser review | passed：15 checks；精确来源与证据复用边界见下 |
| L5 | 全量 Quick、远端检查、发布 | not_run；本轮只本地，四项已知 Quick 红组不重复运行 |

**运行权限边界**：数据库角色为内部持久 demo 开发租户，非控制库、行业目录或客户生产库；environment=dev，project=sc-local-dev，DB=sc_dev_demo，filter=`^sc_dev_demo$`；filestore=`sc_local_dev_odoo_data:/var/lib/odoo/filestore/sc_dev_demo`，local.dev.ready 核验固定卷。仅 namespace `codex_p4_project_profile_write` / batch `contract-act-01` 的可清理合成项目，不允许真实客户数据。复用既有 env 凭据和 fixture authority；不创建新 runtime/profile/端口/卷。无数据模型升级；后端纯 Python 投影需受管 restart 后回读新语义。

**旧证据保护**：`/home/lidefend/workspace/.codex-evidence/contract-err-01-c7980975-historical/` 保存 journey3 脱敏断言及 runtime save 白名单投影、原文件与归档 SHA256。原 JSON 的 candidate 是 `unknown`，c7980975 来自历史报告，不能伪称原始文件自证；原 JSON 实际 29 checks/0 failures，历史文字为22，保留差异。缺明细行身份时拒绝精确定位且保留表单安全提示的既有90例证据复用，不另开错误重构。四项 Quick 既有红组：scene_component_bridge.guard、professional_base_field.unit、professional_relation_field.unit、rendering_detail_state.unit（详见追加九）；不标记全通过。

**回滚**：仅回退本批本地提交，保留 06f14f14、939a937a、c7980975、86dc1359；P4 fixture 仅按 batch 命名空间受管 cleanup。主线集成、版本发布、产品交付均未完成。

**定向产品复核与证据归档**：唯一运行索引为 `/home/lidefend/workspace/.codex-evidence/contract-act-01/result-index.json`。浏览器原始报告为该目录 `browser-menu-tested/summary.json`，截图 `commands-1440.png`、`commands-390.png`、`readonly-denial.png`。浏览器产品来源为 `cf910a213e0618105752df5a717ccb34f42d0704`，受管前端 5176 → sc-local-dev API 18081；candidate health 核验后端 source mount、SC_SOURCE_REVISION、DB/filter 与同一 SHA。该次 P4 runner 为此 HEAD 加 `browser-tool-stage.diff` 中的菜单选择器修正，完整工具文件摘要见 `browser-tool-stage.sha256`，不是 clean frozen 工具候选。

15 项通过：真实后端保存语义/稳定身份/更新绑定；1440×900 和390×844命令栏（窄屏实际打开更多并验证返回）；无修改零写入；必填错误零写入；错误焦点；相邻草稿保留；保存中同一主操作加载；重复点击只一次请求；网络失败后草稿与后端原值；纠正后重试一次成功且状态不推进；刷新权威回读；保存后无修改零额外写入；只读直接写被拒；只读入口无保存能力。会话为既有普通 `pm1`，只读为 `demo_role_project_read`，非管理员。共2次写尝试＝浏览器拦截失败1次＋后端成功1次，不含额外空写入。未执行真实提交、审批或付款；业务动作并存及拒绝边界由既有生产链/纯集成测试验证。

测试数据只在 `contract-act-01` 专属项目4070及现有fixture载体内。受管cleanup回读 `clean=true`、`deleted=true`；再次inspect确认 `existing_batch=false`、project.id=null、carrier=null。角色未变、无真实业务数据修改。候选前端已受管停止；`public/runtime-config.js` 未修改，仍为空覆盖对象。

**失败与恢复分类**：原推断反例先失败后修复；补 target 曾改变保存backendIdentity，由权威生产身份保留修复；fixture dry-run与后端重启重叠退出137，恢复后重跑；通用 local.dev.health 旧nginx静态根地址返回403，未将它计为通过，替代入口为受管candidate frontend health；一次旧SHA身份不匹配的浏览器启动在登录阶段停止、未写入；两次窄屏工具断言失败（返回实际收在更多、Dropdown未透传测试属性）均保留各自原报告，修正为真实菜单操作后通过。Header旧测试的只读保存/重复收纳断言及两个直接相关源码守卫已同步，未修改四项历史Quick红组。

**末次增量及证据复用**：浏览器后补充了显式审批“需确认”仍保留既有primary的反例，Web适配只调整该显式业务动作分支（不是全局审批优先）；项目编辑保存始终由唯一save分支认领，输入、条件、目标及执行未变。Header仅将非保存动作的描述性metadata从猜测submit改为other，菜单back/discard从相同字面事件改为共享注册常量；默认旧保存文案统一“保存草稿”。相应动作链与Header测试、完整类型/lint、最终构建通过。项目保存函数、校验、身份、错误、权限及后端自浏览器候选未变，15项浏览器结果按此确定影响分析复用；最终提交不伪称重新运行整套浏览器。无权把这一项目页证据外推到其他入口。

“主次动作”缺口在本节范围已贯通：保存草稿有真实生产语义，Web负责呈现，Header不再按保存ID兜底猜主色；不宣称所有原生行业动作均已补全语义。下一阶段仍为ScForm实例接口与单入口校验接入，本批不自动实施。

## 追加十一：四项历史前端 Quick 红项收口与 PR 准备（2026-09-28）

**授权与阶段身份**：用户追加“先解决四项历史 Quick 红项，然后开 PR”。起点 `2f8a86b26bedeffbc5ad99b53112675a76463023`、clean，沿用原分支与单写者；不重拆 ERR/ACT 已有提交。现有 Gitee main 基线 `28266e9b31e791e380a4a8fa17591228c6a69a9b`。本节对应起点加本次显式 diff；最终 SHA、完整指纹及 PR 身份在仓外唯一结果索引记录，不把 dirty 运行伪称 frozen。

**归属与边界**：P4 / scripts/verify、scripts/audit 为验证工具及派生清单；P0 / frontend renderer 为 Many2one 公共根类宽度和错误焦点降级。规则属于平台通用消费与验证，不属于 P1 行业语义、P2 客户配置或授权策略。影响所有消费这些通用控件与错误定位的表单，不能写成仅项目页受影响。无数据库、模块生命周期、状态机、业务方法或运行配置变更。L0 身份、L1 静态与 L2 定向先行；L3 数据库升级不适用，L4 构建必需；不重跑 ORM、89 入口浏览器或原项目保存旅程，既有证据按未变执行链复用，控件宽度本轮未另做浏览器视觉复验。

| 历史失败目标 | 根因及修复 | 定向结果 |
|---|---|---|
| `verify.frontend.scene_component_bridge.guard` | 守卫还匹配 form.save ID、旧只读模板；改为检查规范化 record.save 执行绑定、非法语义拒绝及真实只读分支 | passed：6+7 tests，129 checks / 262 collaboration self-check |
| `verify.frontend.professional_base_field.unit` | setter 已传 occurrenceKey，守卫仍匹配旧签名；更新并新增退回 name-only 必须失败的反例 | passed：54 matrix+6 counterexamples，13 tests |
| `verify.frontend.professional_relation_field.unit` | 关系 setter occurrence 权限断言过期；保留身份约束并补退化反例 | passed：18 matrix+13 counterexamples，10+36 tests |
| `verify.frontend.rendering_detail_state.unit` | 清单失效；注释里的 vendor selector 被误当代码；真实 Many2one 内部 class 依赖 | passed：58 tests；三份清单 check；vendor/visual/orphan gaps=0 |

**工具与产品修复**：CSS 注释仅以保持换行的空白剔除；反例仍拦截真实 `.t-*` 后代选择器。Many2one 宽度从 TDesign 内部结构转为自己的根控件类，事件和绑定不变。通过现有 refresh 入口更新四份受影响清单，不加白名单、不删除检查。整条前端 Quick 首次汇总在 component-driver 清单 inputDigest 失效处停止；这是本轮样式依赖遗漏，受管刷新后7例及 required=35/missing=0/bridge_only=0/raw=0 定向通过，再运行汇总。普通 Gitee PR 按最新分工不额外运行完整 `ci.local.quick` 或全量生成报告门禁，不冒称已有该 receipt。

**独立复核修正**：Codex B 线发现已解析行错误在目标单元格未挂载时可能回退到整个集合中的其他输入框。本次最小修复禁止 row/cell 位置降级到 field 容器，保留错误摘要；增加“集合和另一行可聚焦控件存在、目标行不存在”反例，`verify.frontend.contract_error_business_ownership.unit` 为92例通过。未改错误生产或保存函数。缺 row_key 的结构化项仍拒绝精确归属，顶层安全失败提示保留；既有证据不能扩称每条被拒绝的明细 message 均被保留。

**结果索引与发布状态**：仓外 `/home/lidefend/workspace/.codex-evidence/frontend-quick-closure-20260928/result-index.json` 统一记录命令、阶段身份、结果、日志和最终公开范围/独立复核。四项旧红在本节定向范围关闭；整条 Quick 的最终状态见该索引与 PR 验证摘要。原 ACT 项目页15项运行证据继续绑定原运行来源，不重标新候选。唯一矩阵分母89不变，未批量升级入口。主线集成、版本发布、产品交付均不能由本地通过推出；PR 开启后仍需当前源/目标的四项远端必需检查。回滚可独立回退本次修复提交，保留既有 ERR/ACT 与类型收口提交。

### PR #30 首次远端失败修复（2026-09-28）

远端候选 `a230c6f52fde52cfb18bc9c6dcd5e305d4de0f9f` / base `28266e9b31e791e380a4a8fa17591228c6a69a9b`：四个 Check Runs 显示 action_required。只读核对执行器原始 receipt `/var/log/gitee-ci/formal/formal-a_m7ugp2/receipt.json` 后，public_guard 实际113 tests成功，merge_policy required静态项成功，professional_quality_gate 在30tests及前两组检查通过后因复杂度报告过期于step3失败；进入frontend前缺匹配离线缓存导致整体 environment_error，并非四组业务测试均失败。

P4修复：现有 `refresh.generated_reports` 仅改变 complexity_budget_report.md 与 split_plan_queue.md；`ci.generated_reports.guard architecture.complexity_baseline_lock` 全部通过（lock checked=11），不调高阈值、不改扫描范围。原31类型修复改了web package脚本，因此完整manifest身份对应依赖key `60900892a75d40ed130a73917e9438ebc72d6abad4518d6855441f77decb0d2d`，服务器仅有旧key `8a7fcf57479ceb577b8dd8fcb72db8cb41dd70c0c91ebb7053f34bc1d3dc45f9`。沿现有prepare/verify/cache.install入口生成与追加匹配缓存，保持断网、禁用安装脚本、固定工具哈希、旧缓存和服务配置不变。安装/重跑最终结果归入既有仓外result-index，不以计划替代成功。

业务源码及前端Quick输入未变，复用a230c6f5的非零定向、完整前端Quick和既有浏览器证据；不重跑数据库或89入口。此次仅P4报告/缓存恢复及文档，L1 iteration与缓存工具定向验证先行，随后clean精确SHA独立复核、公开扫描与受管推送。远端新候选必须重取结果，旧失败不改写为成功。

### 受管前端执行证据复用（2026-09-28）

所有者批准直接补齐复用工具；P4范围及信任边界详见 [操作说明](gitee_frontend_execution_reuse_20260928.md)。在同一PR继续最小接入现有验证器/SSH发布/worker，保留四必需检查和原链回退。独立复核发现的pnpm可写路径别名、产物父目录symlink、读取前容量限制三项已修，并有真实bwrap与封装反例。当前定向测试与生成检查结果、冻结身份、controller安装和真实消费回执继续归入同一仓外result-index。无业务源码变化、无新凭据/数据库/环境。旧本地verification.json不会追认为新受信回执。

此前6ddf4bda远端运行已真实完成：public113、professional30、frontend145测试，四项成功；生产构建日志15m18s。此结果只绑定6ddf4bda/base28266e9b，不沿用为后续工具提交的远端成功。新工具必须以新候选重新验证并确认verified_local_execution记录。


### 2026-09-28 未合并审计交接恢复

从 `audit/formal-entry-gap-intake@28d2e05e` 恢复三份有独立价值的历史交接件，
未覆盖本文件在 PR #30 中已有的错误、保存草稿、类型及 CI 收口结果。
- G-F3-03 / B04：报表投影恒空的历史定位及待办见
  [原定位](report_center_projection_availability_20260924.md) 与
  [责任层交接](report_projection_capability_handoff_20260924.md)。当前源代码仍保留空投影初始化；
  本轮无数据库复验，不能把历史角色/行数判断标成新主线验收。
- G-F2-05 / B05：关系创建能力的对象级分类见
  [边界记录](relation_create_capability_boundary_20260924.md)。不批量开放创建、不扩权；
  quick create、税率闭环及缺失关系策略保持原未验收/待决定状态。

唯一 89 入口矩阵分母和状态保持不变。其他历史分支分类与本地同步结果见
[本轮记录](local_iteration_sync_20260928.md)。

### FE-TPL-01 官方标准表单首次接管（2026-09-28）

专题分支 `feature/web-official-template-adoption`，从 `main`/`23f11f42` 切出，不再复用已合并的
修复分支。官方参考快照固定为 `Tencent/tdesign-vue-next-starter@aeed57076217f7777158b905f353d73585bad1c4`
（参考基线，不是依赖升级）。本地库身份仍为 `tdesign-vue-next@1.20.5`
（`frontend/packages/ui`，由 component-driver 清单回读）。来源→接管位置的映射写入既有
[Product Page Patterns v1](../../frontend_productization/product-page-patterns-v1.md)，未新建治理体系。

**接管范围与提交**：能力接线 `82ab559d`（`standardFormComposition` 策略、`scFormContract`、
`ScForm`/`ScFormItem` 实例与 props 透传、`contractFormValidationRules`、
`standardFormCompositionRuntime`、81 例单测、make 目标与 quick gate）。真实页面接管 `fb6a778e`
（`FormSection.vue` 落入官方组合并注册通用校验、`buildRequiredFieldErrorPayload` 抽出、
`runAdoptedFormValidation` 接入 `saveRecord()` 前置、`ContractFormPage.vue` 提供 runtime）。
未采纳范围由 `bare` 保持原 DOM，同一页面不会同时运行两套组合。

**试点入口与运行来源**：入口 `menu_sc_product_project_edit_v1`（`/m/680` → `/f/project.project/10`），
角色 `fixture_role_pm`。环境：`sc-backend-odoo-acceptance` `127.0.0.1:18082`、生产模式
vite preview `127.0.0.1:5175`、隔离库 `sc_frontend_acceptance`。前端产物由本次源码重建
（`dist-release/assets/ContractFormPage-BxZsuyWO.js`，源码最后修改 20:19:48 早于构建 20:21:54）。
截图与 journey JSON：`artifacts/frontend-web-fix-20260928/tpl01/`（仓外未跟踪）。

**结构证据**：6 个 section form；`24/24` 行渲染为 `t-form__item`、旧行 `0`；`1440×900` 与
`390×844` 结论一致，窄屏 `scrollWidth === clientWidth === 390`，无横向溢出。

**行为与业务证据**：清空「项目名称」并写入草稿标记后保存被拒——当次 0 次写入、唯一 invalid 字段、
`role="alert"`、`aria-describedby` 指向该控件、摘要「请检查以下内容 / 项目名称不能为空」，
草稿标记保留。纠正后保存 2xx 且错误清零，刷新回读 `name`/`location` 与期望一致，随后 fixture 已还原。

**本轮实测检查**：`vue-tsc --noEmit` 0 error；页面模式/专业组件注册/原语适配/表单画布四个守门脚本 PASS；
`standard_form_composition` 81 例、`contract_error_business_ownership` 92 例、
`contract_field_occurrence_identity`、`contract_form_save_failure_recovery` 通过；
`component_driver_takeover` 清单按新源文件刷新后 PASS（required=35 missing=0 bridge_only=0 raw=0）。

**口径限制（不得夸大）**：
- 只能宣布「官方标准表单接管到 `project.project` 的菜单 680 表单」；列表、详情、应用外壳、
  主从办理组合均未接管，89 入口矩阵分母与状态不变，未批量升级任何行。
- 「官方引擎结果参与保存判定」由 shipped 调用顺序断言、registry 单测与页面结构证据共同支持；
  生产构建不暴露组件实例，未能在浏览器中把「官方引擎拒绝」与「既有 precheck 拒绝」两条同形输出分离。
  两条路径按设计共用 `isRequiredFieldEmptyByType` 与同一错误载荷，本轮未观察到二者结果不一致。
- 本环境 `vue-tsc` 未复现历史 31 项错误，因此不能作为「同基线、零新增」的对照，只能报告本次 0 新增。
- 专题内不推送、不合并、不部署；模板接管通过不等于该入口全部业务职责通过。

### FE-TPL-02 第二业务模型复用（2026-09-28）

同一专题分支，基线 `main`/`23f11f42`，开工前 HEAD `0ca84329`。目标是证明标准表单组合可被第二个业务模型通过
**契约差异**复用，而不是又做一次项目专用改版。

**选型**：沿唯一矩阵选 `menu_sc_p1_daily_contract`（日常合同，action `action_sc_general_contract`，
模型 `sc.general.contract`），入口 `rendering_path` 已声明 `form:form_structure [structural]`，与试点同一条渲染链。
该模型在 ORM 层无业务 x2many（仅 chatter/附件），属普通标量表单。写权限按真实角色判定：
`fixture_role_contract_operator` 与 `fixture_role_project_a_member`/`activity_accounting`/`config_admin` 可写，
`fixture_role_pm` 只读（`check_access_rights(write)=false`），`fixture_role_finance` 无模型访问。
角色公司域为 `FE Company A`（`allowed_company_ids=[8]`），因此可见记录 `GC2600011`(confirmed)/`GC2600010`(signed) 均为只读，
唯一可写的既有草稿 `GC2600012` 属 `FE Company B`，不在该角色数据域内——写路径因此走**新建**表单模式。

**复用证据是结构性的**：采用开关按 **model** 判定（`STANDARD_FORM_COMPOSITION_PILOT_MODELS`），
而真正渲染的两个调用点 `components/template/FormSection.vue` 与 `pages/ContractFormPage.vue`
**都不出现任何模型名**。因此本轮生产代码改动只有「作用域清单 + 其单测」，
既没有复制保存函数、错误摘要，也没有按模型名写主按钮逻辑或第二套字段布局循环。

**运行来源与结果**：`feature/web-official-template-adoption`，前端由本轮源码重建后
`vite preview` 提供（`dist-release`）。角色 `fixture_role_contract_operator`，
`/f/sc.general.contract/new?menu_id=662&action_id=673`。

- 结构：新建表单 `official=4 legacy=0 sections=2`；已有草稿表单 `official=31 legacy=0 sections=10 editable=23`；
  非草稿只读表单 `official=13 legacy=0 editable=0` 且无保存动作；`1440×900` 与 `390×844` 均无横向溢出。
- 校验拒绝：清空「合同名称」后保存被拒——**当次 0 次写入**（合同数 3→3）、摘要「请检查以下内容合同名称不能为空」、
  字段级「合同名称不能为空」、`data-field-state=invalid`、`aria-describedby` 指向该控件、金额草稿保留。
- 办理闭环：纠正后保存草稿 → 记录创建（`GC2600015`，`state=draft`，`amount_total=123456`）→ 页面跳到该记录；
  在既有草稿上改金额 `123456→654321` 保存 → 刷新回读一致；随后删除恢复基线（3→3）。
- 删除需能力角色：业务角色 `unlink` 被拒（「允许对以下组进行此操作：合同中心审批」），清理以
  `fixture_role_config_admin` 执行。**这是权限事实，不是缺陷。**

**同轮收口的 TPL-01 遗留（本轮发现并修复）**：开工核对时 `verify.frontend.quick.gate` 在 TPL-01 的 HEAD 上
**并未通过**——`FormSection.vue` 的两条样式规则直接命中 TDesign 内部类
（`.field-control-row.t-form__item`、`.field-control-row .t-form__controls/.t-form__controls-content`），
被 `internalVendorSelectorGapCount` 记为 1；同时三份生成清单（component-professionalization、visual-projection、
official-design-alignment）在 TPL-01 改源后未刷新。修复：改用项目自有选择器
`.field-control-row[data-semantic-component='ScFormItem']`（该身份本就由 `ScFormItem` 适配器写入，天然只覆盖已接管行），
并移除对 TDesign 内部后代的耦合——不需要的规则就不写，而不是换一种写法继续穿透内部结构。
对照 `1440×900` 下项目编辑页 24 行与合同只读页 13 行的逐行矩形，**几何零差异**；TPL-01 与 TPL-02 的浏览器
旅程在修复后各自 8/8 通过。刷新三份清单后 `verify.frontend.quick.gate` 全绿（本次实测退出码 0）。

**本轮实测检查**：`verify.frontend.typecheck.strict` 0 error；`standard_form_composition` 96 例
（由 81 例扩展，新增第二模型作用域、跨模型不泄漏、调用点不含模型名、作用域只有一处声明）；
`component_driver_takeover`（required=35 missing=0）、`product_page_pattern`、`contract_error_business_ownership`（92 例）PASS；
三份渲染清单 `--check` PASS；`verify.frontend.quick.gate` 整体 PASS。

**口径限制（不得夸大）**：
- 只能宣布「官方标准表单接管到 `project.project`（菜单 680）与 `sc.general.contract`（action 673 的菜单 662/353）」；
  列表、详情、应用外壳、主从办理组合仍未接管，89 入口矩阵分母不变，未按模型批量标绿。
- 第二模型的业务证据只覆盖 `fixture_role_contract_operator` 一个角色、新建与编辑两种表单模式；
  **未运行**提交审批等流转动作、该入口的列表查询/筛选/分页/详情返回上下文、附件上传下载、以及其余角色的权限矩阵。
- 托管矩阵行 `menu_sc_p1_daily_contract` 按真实证据回填为 `partial_passed`，缺口逐项写明；
  同 action 的 `menu_sc_general_contract` **不是**矩阵行，只记录其结构探测结果。
- 矩阵若干行引用的 `artifacts/frontend-web-fix-20260928/evidence.md`、`uat01a-raw/`、`uat02-raw/` 在本轮核对时
  **不存在**（该目录下仅有 `tpl01/`、`tpl02/`）。本轮只如实报告，未重建、未改写引用。
- 专题内不推送、不合并、不部署；模板接管通过不等于该入口全部业务职责通过。

### FE-TPL-02 补证：校验结果接管保存判定 · 跨模型复用确认（2026-09-28 续）

同一专题分支，基线 `main`/`23f11f42`，上一段收口 HEAD `0ca84329`。上一轮只做到“结构接管 +
调用顺序断言”，留了两点白：官方校验的返回值是否**控制**保存、同一组合能否接管第二个真实模型。
本段把这两点补成**运行证据**，不重做结构审计。

**校验责任边界（沿真实链核对，不是按文件名猜）**：
- 已由官方引擎执行（通用规则）：adopted section 内、`displayFields ∩ rules` 命中位置的必填/类型规则，
  经 `ScForm/ScFormItem` → `standardFormCompositionRuntime` → `runAdoptedFormValidation` →
  TDesign `Form.validate()`。
- 未接管能力：非 pilot 模型（`adopted=false`）整页走旧路径；adopted 页面里未渲染、或未声明规则的位置。
- 领域与后端约束：`collectSceneValidationPrecheckErrors`、one2many 行错误、后端 ORM 约束全部保留。
- 旧 precheck 是否重复：**是** —— `validateBeforeSaveRecord` 的必填 precheck 会对同一组通用规则再判一次。
  修复取最小口：官方引擎**真正评估过**的位置（`coveredFieldNames`）从该次 precheck 中排除，
  其余位置保持原判定。没有删除 `saveRecordHelpers`，也没有把“某个 section 已采纳”扩大成
  “所有校验都可跳过”。

**真实引擎运行证据（非替身）**：新增
`frontend/apps/web/scripts/adopted_form_engine_decision_test.ts`（make 目标
`verify.frontend.adopted_form_engine_decision.unit`）。用 Vue `createRenderer` 挂载**真实**
`TDesignForm`/`TDesignFormItem`，不 stub 官方校验、不在生产构建里暴露调试实例：
- 真实必填规则失败 → 官方校验返回非成功 → 错误进入既有统一存储 → **保存调用次数 0**；
- 同一字段纠正 → 官方校验成功 → 既有领域校验与保存链继续 → **保存调用次数 1**；
- 已接管位置不再被旧 precheck 独立否决（共用 `isRequiredFieldEmptyByType` 与同一错误载荷，
  但通用权威只有一处）；
- 校验未完成不得提前保存；结果不可读按失败处理（fail closed），不解释成通过。
- 实测：`PASS cases=67 engine=real-tdesign-vue-next writes=counted`。

**fail-closed 边界修复（最小）**：
- `contractFormValidationRules.failedAdoptedFieldNames` 改为 `string[] | null`：`true`→`[]`，
  对象→键集合，缺失/原始值/数组→`null`（fail closed）。
- `FormSection.validateAdoptedSection`：已采纳且声明了规则却没有引擎实例 → 抛错；结果读到 `null` → 抛错。
- `useRecordFormActions.runAdoptedFormValidation` 返回 `{ ok, coveredFieldNames }` 并区分三种边界：
  **A** 未采纳页面不要求存在官方 runtime，保持既有合法路径；**B** 已采纳、契约声明了必填可写位置
  而覆盖为空 → 阻止保存、保留草稿、给统一反馈，不静默跳过、不伪造字段业务错误；
  **C** 按有效契约确实无待校验规则 → 合法空集合，不误判为故障。
- `saveRecord` 用 `if (!adoptedValidation.ok) return false;`，并把 `coveredFieldNames` 作为
  `excludedRequiredFieldNames` 传给 precheck。

**跨模型复用确认**：第二模型 `sc.general.contract`（日常合同）本段**没有新增任何模型专属分支**——
生产改动只有作用域清单已含该项（`STANDARD_FORM_COMPOSITION_PILOT_MODELS`）与共享运行时修复。
三个实测点：
- **真实应用路由隔离**：项目编辑 →（脏表单「确认离开页面」保护）→ 合同 → 返回项目编辑。
  `project.project` 与 `sc.general.contract` 各渲染 `24`/`13` 行官方行、旧行 `0`；模型、字段集合、
  section 注册、错误、动作身份互不沿用（草稿文本只出现在侧栏面包屑，不进入合同表单面）。
- **第二模型视口**：`1440×900` 与 `390×844` 下 `official=13 legacy=0 labels=13`，
  `scrollWidth === clientWidth`，无横向溢出，未混用新旧普通表单行。
- **项目 HTML 富文本字段最小回归**：经实际编辑面输入普通文本 → 保存 → 刷新回读正文一致
  （存为 `<p>…</p>`，允许编辑器对 HTML 正常规范化）→ 按受管规则还原。

**本轮实测检查**：`verify.frontend.typecheck.strict` 0 error；`standard_form_composition` 114 例、
`adopted_form_engine_decision` 67 例、`contract_form_save_failure_recovery`、
`contract_error_business_ownership` 92 例、`j13_required_value_semantics` 110 例、
`contract_field_occurrence_identity`、`cross_model_action_navigation` 全 PASS；`ci.local.iteration` PASS；
前端产物重建后 TPL02（第二模型旅程）8/8、TPL02B（跨模型隔离 + HTML 字段回归 + 双视口）8/8。

**本轮发现（真实，非 TPL 引入）**：`project.project.name` 是**可翻译字段**（JSONB `{en_US, zh_CN}`）。
上一轮“还原”只写了 `en_US`，`zh_CN` 槽仍留草稿名；zh-CN 页面读到的正是 `zh_CN` 槽，
因此表现为“接口读到陈旧值”，实为**翻译上下文不一致**，不是缓存或代理缺陷。
按 `en_US` + `zh_CN` 双槽还原后两语言一致。记录以免下一轮误判。

**口径限制（不得夸大）**：
- 只宣布「官方标准表单接管 + 校验结果控制保存」到 `project.project`（菜单 680）与
  `sc.general.contract`（action 673 / 菜单 662）；列表、详情、应用外壳、主从办理组合、付款明细、
  合同全流程（R7R9/R5）本段均**未运行**。
- 第二模型只覆盖 `fixture_role_contract_operator`（新建/编辑）与 `fixture_role_pm`（只读边界）；
  未跑提交审批流转、附件、其余角色权限矩阵。
- `vue-tsc --noEmit` 的准确口径是“**该命令在本次环境与候选上通过，0 错误**”；
  不代表历史 31 项已分别修复，也不以历史错误数作默认豁免。
- 89 入口唯一分母不变；托管行按真实证据回填，未因模板复用通过就整体标绿。
- 专题内不推送、不合并、不部署目标环境。

### FE-TPL-02R 异步身份修复与只读探测适配（2026-09-29）

同一专题分支。目标：把 TPL-02 收口到**一个固定候选**上——修复已确认的异步身份缺陷、让既有跨模型探测
跟上 TPL-03 的只读呈现、并用同一份构建补齐双视口证据。**不进入 TPL-04，不验收 TPL-03。**

**已确认缺陷（收口阻断项）**：一次已采纳的保存要 await 官方校验、关系创建往返与写请求。此前调用链只在
await **之后**读取 `model`/`recordId`，因此当页面在等待期间切走（包括切回曾经看过的记录）时，
迟到的校验结果会**给下一个记录标红**、**为从未校验的记录报成功**、甚至**把一个记录的值写到另一个记录**；
其 `finally` 还会清掉更新操作的 loading。复现反例（修复前源码 + 本轮测试）：
`cases=46 failed=17`，其中
`observed stray write: model=sc.general.contract ids=[11] vals={"name":"A draft"}`（记录 10 的值写到记录 11）。

**修复（提交 `f017d42d`，父提交 `bffc4b7e`）**：一次保存在**第一次 await 之前**建立归属，并在**每个真实
副作用之前**复核归属；`finally` 只释放自己持有的忙碌标记。

- 归属身份：`useRecordFormActions.ts:157` 的 `boundSurfaceKey()`（`model` + `recordId|new`）+
  `:158` 的 `surfaceEpoch`（绑定面每次变化自增，`model`/`recordId` 相同也不复用同一会话）+
  `:166` 的 `SaveOperation`（`id`/`epoch`/`model`/`recordId`）。
- 复核点：`:182` `saveOperationOwnsSurface`；校验结果写入错误/摘要之前（`runAdoptedFormValidation` 内，
  即副作用发生处，不是只在外层返回后）；precheck 错误写入前 `:607`；发写请求前 `:651`；写目标记录固定为
  `operation.recordId`（不再读当前页面）；反馈与导航前 `:657/:660/:680/:683/:704`；`finally` 只在
  `busyOwnerOperationId === operation.id` 时释放（`:739`）。
- “校验的数据就是提交的数据”：`:575` 在官方校验前取 `canonicalizeSubmissionValues(collectWritableValues())`
  快照，`:580` 在写之前再比一次；期间草稿被改则保留草稿、结束本次保存并提示重新保存，**不**用旧成功结果放行新值。
- 单飞按面收敛：`saveRecordHelpers.ts:32` 的 `createSingleFlightSave(execute, scopeKey)`，
  调用点 `useRecordFormActions.ts:750` 以 `surfaceEpoch` + `boundSurfaceKey` 为键；更旧的调用不得清掉
  更新调用占用的槽位。

**请求发出前后的边界（如实声明）**：本轮修复的是“**校验等待期间失效、尚未发出写请求**”，失效后旧操作
**零写入**。若真实写请求**已发出**后才切换页面，前端只能丢弃响应、不重绘/不导航/不清理新页面、不自动重试；
`useRecordFormActions.ts:651-655` 的注释即此口径——**不**声称数据库已回滚。未改后端事务来绕开前端身份问题。

**回归覆盖（`adopted_form_validation_identity_test.ts`，46 例，进出写边界计数）**：
A 校验延迟失败→切 B→A 返回（B 不标红、草稿不丢、不发写请求）；B 校验延迟成功→切 B（不得读 B 的数据继续保存）；
A→B→回 A（同 `model`+`recordId` 也不复活旧草稿会话，且覆盖空 `recordId` 新建草稿）；
同一记录较新操作先完成、旧操作后完成（旧结果与 `finally` 都不覆盖新错误/新 loading/新结果）；
校验期间草稿被改（未校验的新值不放行）；正常路径（真失败不写、纠正单次写、服务端拒绝保留草稿可重试）。
测试用可控完成时机的 Promise 门（40 微任务 `drain()`，**无固定 sleep**）；真实 Vue 实例承载**shipped** 的
`useRecordFormActions`/registry/`validateBeforeSaveRecord`，只有写/创建边界被计数。
`adopted_form_engine_decision_test.ts` 增补真实 TDesign 用例（引擎 item 错误实例绑定；记录变更 re-key 后
挂载新树、旧错误文本消失），现 **74 例**，引擎仍为真实 `TDesignForm`/`TDesignFormItem`。

**只读探测适配（探测脚本，非产品改动）**：TPL-02 时代的 TPL02B 探测把“只读详情成立”绑定在**可编辑网格**
`.template-form-section-grid > .field[data-field-name] > .field-control-row` 上；TPL-03 的只读详情改用
`ScDescriptions`（`[data-detail-facts="official-standard-detail"]`），探测因此在 S2 直接失败。适配后探测
**按页面模式分支**：可编辑面仍断言官方网格行（`official>0 legacy=0`）；只读面改为断言**当前记录的业务事实**
（`t-descriptions` 的 标签=值 对，与 ORM 读到的 `contract_name`/`amount_total` 对比），**然后**才断言记录区域
内无可见编辑控件、无保存动作、旧网格行为 0。草稿泄漏判定**限定在记录区域**（`[data-form-model]`），
不整页搜文本——页签里保留草稿标题是正常行为。没有“找不到就跳过”、没有把 FATAL 改 PASS、没有 try/catch 吞断言、
没有硬编码记录值、没有恢复旧 grid 或隐藏假输入。
**口径**：探测脚本历来是**会话本地、未入库**的验收探针（含凭据与环境假设），本轮按既有方式把它保存到
`artifacts/frontend-web-fix-20260928/tpl02r/tools/` 并在此记录其适配，**未新增**入库 harness，也未新增治理体系。

**固定候选与产物绑定（一次构建）**：
- 候选 `f017d42d`（工作树干净），离仓构建到
  `/home/lidefend/workspace/sce-offrepo/artifacts/fe-tpl02b2-20260929/dist`；`index.html`
  sha256 `0163d514…f3488`，入口 `/assets/index-CdKU6vab.js` sha256 `9725be9c…3d4c3`，
  `runtime-config.js` sha256 `0a69250f…d77bbc`（值为 `{}`，无凭据）。入口文件名与上一轮
  （`bffc4b7e` 的 `/assets/index-BtjlhXBV.js`）**不同**，旧 bundle 不能替用。
- 服务：`release_static_server.mjs` pid 2166107 @ `127.0.0.1:5176`，`STATIC_ROOT` 指向上面的构建目录。
  停旧进程前先核对 cmdline/cwd/env（旧 pid 988564 与报告一致），未按陈旧 pid 直接 kill。
  `served-bundle-identity.json` 逐文件经 HTTP 取回并哈希：**100/100 与本地构建逐字节一致**。

**结果（均绑定上述候选与产物）**：
- `adopted_form_validation_identity.unit`：修复前 17/46 失败（反例见上），修复后 **46/46 通过**。
- `adopted_form_engine_decision.unit`：`PASS cases=74 engine=real-tdesign-vue-next writes=counted`。
- `contract_field_occurrence_identity`、`contract_error_business_ownership`（92）、
  `contract_form_save_failure_recovery`：PASS；`verify.frontend.typecheck.strict`：退出码 0。
- 跨模型 + 只读 + 项目富文本（`TPL02B-20260928204024`）：**8/8**。项目入口 `official=24 legacy=0`；
  脏表单保护 → 合同只读详情（`official-standard-detail`，事实 `合同名称=FE-B General Contract`、
  `合同金额=¥985,000.00`，无可见编辑控件、无保存动作，项目草稿文本不出现在记录区域）；返回项目互不串用；
  项目 HTML description 实际编辑→保存→刷新回读→还原；项目双视口 `official=24 legacy=0` 无溢出；
  合同只读双视口事实正确、无溢出；无残留。
- 单模型正向回归（`TPL02-20260928204248`）：**8/8**。必填拒绝**零写入**（3→3）且草稿保留
  （`amount 123456.00`）→ 纠正保存（`id 19`）→ 刷新回读 → `/f/…/11` 只读事实 → 清理 3→3。
- 合同**编辑面**正常/错误态双视口（`TPL02C-20260928204429`）：**2/2**，拒绝写入 0（3→3）。
- 保留为记录：`TPL02B-20260928203759` 首次运行 S5b 失败——原因是**本轮探测自身的缺陷**
  （`saveActions` 存成了数字却按 `.length` 断言），非产品回归；已修并在下一次运行通过。

**数据恢复**：`project.project` 10 的 description 经受管富文本面改后清回，存为 `<p><br></p>`
（空文本等价，编辑器对 HTML 规范化；上一轮同样落在此值），名称不变；`project.project` 11 与
`sc.general.contract` 11 未变；正向回归创建的合同 `id 19` 由其自身清理删除（3→3）。
运行前先确认样本可复用：`project.project` 10、`sc.general.contract` 11 均可读；
已删除的记录 18 **不假定**仍存在。

**收口结论**：异步身份修复通过（修复前 17/46 失败 → 修复后 46/46）、既有跨模型探测完整执行
（`TPL02B-20260928204024` 8/8）、当前候选双视口补证完成（`TPL02C-20260928204429` 2/2 + 项目/合同双视口）
——三条件同时满足，**FE-TPL-02 在当前整合候选 `f017d42d` 上收口**。`cc0eee7b` 历史 bundle 对应关系
仍不可追溯，作为历史限制保留，**不阻塞**本次收口。

**口径限制（不得夸大）**：
- 只宣布 TPL-02 能力在**当前整合候选** `f017d42d` 上的验收结果；`cc0eee7b` 的历史浏览器产物对应关系
  仍不可完整追溯，作为历史限制保留，**不倒填**。
- 探测脚本虽经过新详情页，**不**代表 TPL-03 整体通过；本轮未运行 89 入口全量、未跑发布门禁、
  未调整业务矩阵状态；不推送、不合并、不部署。

### FE-TPL-03 官方列表与只读详情接管（2026-09-28/29）

同一专题分支，基线 `main`/`23f11f42`，开工 HEAD `0ca84329`（本轮提交后 `dfd2f324` + 本轮实现提交）。
目标：把 TPL-01/TPL-02 的同一套采纳机制扩展到**标准查询列表**与**标准只读详情**，且**不新增第二套页面实现**。

**结论先行——本轮的“配置级采纳 vs 暴露的共享能力缺口”**：

- 列表侧：**仅配置级采纳**。生产改动是新增纯策略模块
  `app/presentation/standardListComposition.ts`（显式试点清单 + `{composition, adopted, reason}`）、
  官方容器 `components/product-list/ProductListSurface.vue`、`pages/ListPage.vue` 的组装与两个 `data-*` 标识，
  以及 `ProductListHeader.vue` 搜索框的官方图标槽。**未触碰**列、记录、动作或权限。
- 详情侧：**同一处共享复用**，不是按模型的特例。改动落在既有 `components/template/FormSection.vue`
  内新增只读事实分支（`ScDescriptions`=`t-descriptions`），对**所有**已采纳只读页生效；
  `pages/ContractFormPage.vue` 只新增 runtime 创建与两个 `data-*` 标识。
- **没有新增任何模型专属校验、保存或错误逻辑**，因此跨模型复用成立：采纳由 `model` 决定，
  渲染调用点**不出现任何模型名**，错误仍进既有统一存储，保存仍走既有链。

**两处共享修复（非模型专属）**：

1. 官方容器原来用 `:deep(.t-card__body)` 去掉卡片内边距，被
   `official-design-alignment-inventory` 记为 `legacy_override_gap`（对厂商内部的后代选择器耦合）。
   改为使用项目自有 `ScCard appearance="table"`——零内边距由外观本身承载，**不写后代选择器**。
2. `FormSection.vue` 需要按视口把只读事实收敛为单列，但
   `frontend_professional_component_registry_guard` 禁止该组件触碰全局对象（已被守卫锁定的
   fail-closed 谓词所在对象）。新增 `composables/useNarrowViewport.ts` 承载 `matchMedia`，
   组件只消费其响应式结果——能力补齐在共享 composable，而不是在组件里开一个局部后门。

**真实组件集成证据（沿用 TPL-02 的 `createRenderer` 宿主，不 stub 官方引擎、不在生产构建暴露实例）**：
`frontend/apps/web/scripts/standard_collection_composition_test.ts`（make 目标
`verify.frontend.standard_collection_composition.unit`，**64 例**，并已接入 `verify.frontend.quick.gate`）：
策略纯函数真值表与幂等、两个试点模型复用同一组合、非试点保持旧组合、
无关输入不触发采纳、调用点不含模型名、shipped 源码确实渲染采纳标识。

**真实页面旅程证据（绑定本轮实际 `HEAD` 与实际 `dist-release` bundle）**：
`artifacts/frontend-web-fix-20260928/tpl03/`——
- `tpl03-journey-results.json`：**30/30**。采纳的合同列表 `/m/662`（`official-standard-list`，卡片含查询行 +
  表格 + 分页 + 选择 + 列设置，`1440×900` 与 `390×844` 横向溢出 0）、采纳的合同只读详情 `/r/sc.general.contract/11`
  （`official-standard-detail`，7 个 section 全部以 `t-descriptions` 呈现、共 13 项、旧网格 `0`、关系入口保留、
  双视口无溢出）、采纳的项目列表 `/m/680`；对照项 `/a/713?menu_id=414` 旧列表、`/r/res.partner/1` 旧详情
  （`outside-pilot-scope`）、`/f/sc.general.contract/10` 与 `/f/sc.general.contract/new`
  （`not-a-readonly-profile`，网格与输入框原样保留）。
- `tpl03-switch-results.json`：**7/7**。采纳列表 → 采纳详情 → 旧详情 → 旧列表 → 回采纳详情 → 回采纳列表，
  每步 `detailFacts`/官方卡片/`grids` 归零，无状态跨模型残留，全程横向溢出 0。

**本轮实测检查**：`verify.frontend.typecheck.strict` 0 error（口径：**该命令在本次环境与候选上通过、0 错误**，
不代表历史 31 项已分别修复）；`standard_collection_composition` 64 例、`standard_form_composition` 114 例、
`adopted_form_engine_decision` 67 例、`rendering_detail_state`、`page_pattern_reference_parity`、
`product_page_pattern`、`primitive_adapter`、`collection_action_toolbar`、`canonical_form_presenter`（177 例）、
`contract_render_profile`、`native_form_structure_responsibility`、`mobile_viewport`、
`professional_component_registry`、`professional_detail_collection`、`detail_form_productization.guard` 全 PASS；
`ci.local.iteration` PASS（L1）；`ci.generated_reports.guard` PASS、`architecture.complexity_baseline_lock` PASS（checked=11）。

**已知前置失败（非本轮引入，基线 HEAD 即存在，未修复）**：
`verify.product.page_structure`（基线 `PageHeader.vue` 即无 `sc-product-page-header`）与
`verify.frontend.style_system.guard`（`ScRelationField.vue` 新 z-index、`ContractFormPage.vue` > 1900 行等）。
本轮未据其推翻成果，也不将其计入本轮新增。

**口径限制（不得夸大）**：
- 只宣布「官方列表 + 只读详情组合接管到 `project.project`、`sc.general.contract`（列表）与
  `sc.general.contract`（只读详情）」；**未运行** 列表/详情之外的接管、应用外壳（TPL-04）、主从办理组合（TPL-05）、
  付款明细、合同全流程（R7R9/R5）。
- 官方详情页的 `t-steps` 时间线**未采纳**：本仓已有更丰富的审计/协作时间线，替换会丢业务能力而非改表达。
- 89 入口唯一分母不变；本轮只验证标准组合复用，**未**因模板复用通过就把任何业务职责标为 passed。
- 专题内不推送、不合并、不部署目标环境。

### FE-TPL-03 列表/只读详情证据再绑定到当前整合候选（2026-09-29）

同一专题分支。**不是**新一轮 TPL-03 验收、不新增页面实现、不调整业务矩阵。目的：把已实现的
列表/只读详情采纳证据，从“浏览器产物已被覆盖、无法追溯对应关系的 `bffc4b7e` 历史 bundle”
改为绑定在**当前整合候选**上的一次可追溯运行。历史记录
`artifacts/frontend-web-fix-20260928/tpl03/` **保持原样、不回填**。

**输入**：源码候选 `f017d42d`（即 TPL-02R 修复提交；其上的 `9fd6a4b6` 仅动 `docs/`），离仓构建
`/home/lidefend/workspace/sce-offrepo/artifacts/fe-tpl02b2-20260929/dist`（`index.html`
sha256 `0163d514…f3488`，入口 `/assets/index-CdKU6vab.js` sha256 `9725be9c…3d4c3`），由
`release_static_server.mjs` pid 2166107 @ `127.0.0.1:5176` 服务（`04:42:40` 起），100/100 文件经
HTTP 取回校验逐字节一致。

**结果**（均绑定上述候选/产物，运行于 `06:32–06:33`，`loadedScripts` 含被服务的入口
`/assets/index-CdKU6vab.js`）：

- `artifacts/frontend-web-fix-20260928/tpl03r/tpl03-journey-results.json`：**30/30**。采纳合同列表
  `/m/662`（`official-standard-list`，1 官方卡片，分页/选择/列设置齐备）、采纳合同只读详情
  `/r/sc.general.contract/11`（`official-standard-detail`，`facts/readonlySections/descriptions=7`、
  `items=13`、`legacyGrids=0`、`relationEntries=4`）、采纳项目列表 `/m/680`，均 `1440×900`/`390×844`
  无横向溢出；旧列表 `/a/713?menu_id=414`、旧详情 `/r/res.partner/1` 保持 `legacy-*-surface`；
  编辑/新建表单保持旧网格（`not-a-readonly-profile`）。
- `.../tpl03r/tpl03-switch-results.json`：**7/7**。采纳列表→采纳详情→旧详情→旧列表→回采纳详情→
  回采纳列表，每步 `facts`/官方卡片/`grids` 归零，全程横向溢出 0。
- 响应式（加载时）：`detail-contract-1440.png` 事实 2 列/行，`detail-contract-390.png` 1 列/行，
  由 `composables/useNarrowViewport.ts`（`matchMedia` + `change` 监听）驱动。

**边界（不得夸大）**：

- switch 的“旧详情”一步落在 `/r/res.partner/1`，该页在本验收环境为**既有**的“记录详情 · 加载失败”
  （`invalid contract v2 snapshot: …editable auth conflicts with readonly occurrence status`），
  与 `bffc4b7e` 历史运行**完全一致** → 既有/环境问题，**非本候选引入**。该步因此只证明“采纳组合未
  泄漏到旧详情面”，不是在可正常渲染的旧详情页上取得。补充参照：`/r/project.project/10` 在
  `fixture_role_pm` 下渲染为 `legacy-detail-surface` 且旧网格 `legacyGrids=4`
  （`tpl03r/legacy-detail-r_project.project_10-pm.png`）；在 `operator` 角色下为 `无权访问`
  （预期读权限边界，非采纳副作用）。
- “跨断点拖拽 resize（不重载）”本轮**未**在浏览器验证，仅有代码层 `matchMedia` 响应式救济。
- 本轮**不**代表 TPL-03 整体通过：未运行应用外壳（TPL-04）、主从办理（TPL-05）、付款明细、合同全流程
  （R7R9/R5）；89 入口唯一分母不变；未调整业务矩阵状态；不推送、不合并、不部署目标环境。

### FE-TPL-03 验收结论（2026-09-29）

对已实现的列表/只读详情接管（代码提交 `308a85a6`）在**当前整合候选** `f017d42d` 上做验收。
逐项判定如下，每项给出实现位置与原始证据；**未**下放新的列表/详情开发任务，**未**进入 TPL-04。

| # | 验收项 | 判定 | 实现位置 / 原始证据 |
|---|---|---|---|
| 1 | 采纳由显式策略驱动，不由外观、名称或角色推断 | PASS | `standardListComposition.ts:40`（`STANDARD_LIST_COMPOSITION_PILOT_MODELS`）、`:45` `resolveStandardListComposition`；`standardDetailComposition.ts:43/:47`；策略为纯函数（无 Vue/DOM/TDesign）。调用点只传 `model`（+只读面的 `renderProfile`）：`ListPage.vue:526`、`ContractFormPage.vue:1199`。 |
| 2 | 同一组合被复用，不是第二套页面实现 | PASS | 列表只有 `ProductListSurface.vue` 一个官方容器（两个试点列表共用）；只读事实只有 `FormSection.vue` 内**一个** `ScDescriptions` 分支（`:26-58`，由 `:488` `adoptedDetailFactLayout` 守卫），对所有已采纳只读页生效；决策由页面 provide（`standardDetailCompositionRuntime.ts`），section 只消费。**未复制**表单渲染循环、保存链、错误存储或工具栏主次逻辑。 |
| 3 | 非采纳面保持旧组合，无双重容器/半转换 | PASS | `ProductListSurface.vue:12` 未采纳时 `v-else` 直通插槽；`FormSection.vue:488-496` 需同时满足 adopted+`preferReadonlyFacts`+`allFieldsReadonly`+非选择/非配置编辑+有字段。证据：旧列表 `/a/713?menu_id=414`、旧详情 `/r/res.partner/1` 保持 `legacy-*-surface`，编辑 `/f/sc.general.contract/10` 与新建 `/f/…/new` 保持旧网格。 |
| 4 | 采纳列表真实渲染（官方容器/卡片/分页/选择/列设置，双视口） | PASS | `tpl03r/tpl03-journey-results.json`：`/m/662`、`/m/680` = `official-standard-list`，`card=1 queryRow=1 table=1`、`pagination=2 selection=5 columnSettings=7`，`1440×900`/`390×844` 溢出 0。 |
| 5 | 采纳只读详情真实渲染（逐项 label/value、关系入口保留、无编辑能力，双视口） | PASS | 同上：`/r/sc.general.contract/11` = `official-standard-detail`，`facts/readonlySections/descriptions=7`、`items=13`、`legacyGrids=0`、`relationEntries=4`；`detail-contract-1440.png`（2 列/行）与 `detail-contract-390.png`（1 列/行）。 |
| 6 | 跨模型与 section 生命周期隔离 | PASS | `tpl03r/tpl03-switch-results.json`：采纳列表→采纳详情→旧详情→旧列表→回采纳详情→回采纳列表，每步 `facts`/官方卡片/`grids` 归零，溢出 0。 |
| 7 | 响应式：加载时与**不重载 resize** 均视口正确 | PASS | `tpl03r/logs/resize-no-reload.log`：`/r/sc.general.contract/11` 首行单元格数 `1440→4`（2 列）、`setViewportSize(390)` 不重载 `→2`（1 列）、回到 `1440→4`；断点 640（500→1 列、700→2 列），由 `useNarrowViewport.ts` 的 `matchMedia` + `change` 监听驱动。上一轮登记的该风险已关闭。 |
| 8 | 源码—产物—证据绑定同一候选 | PASS | 候选 `f017d42d`；离仓构建 `fe-tpl02b2-20260929/dist`（`index.html` sha256 `0163d514…`，入口 `index-CdKU6vab.js` sha256 `9725be9c…`）；`release_static_server.mjs` pid 2166107 @ `:5176`，100/100 文件 HTTP 逐字节一致；旅程 JSON 的 `loadedScripts` 含该入口。 |
| 9 | 派生的生成清单与当前源码一致 | **FAIL → 已修复** | 验收初查 `verify.frontend.component_driver_takeover.unit` 报 `stale`（committed 生成于 `dfd2f324`，早于 `308a85a6`/`f017d42d` 的源码改动，`source_files=702`）。用仓库自带生成器刷新（提交 `3f3a48fe`）：无 schema/词汇变化，仅派生计数与摘要变化；`ScDescriptions` 首次获得生产消费者，一个适配器 `adapter_unconsumed → adapter_present`（present 32→33、unconsumed 3→2）。现 `PASS required=35 missing=0 bridge_only=0 raw=0`。**这是本轮验收发现的唯一确认缺陷**，按最小方式修复，未改产品行为。 |
| 10 | 相关 L2 单元/结构门禁 | PASS | `logs/tpl03-gates-run.log`：`standard_collection_composition` `cases=64`、`mobile_viewport` PASS、`product_page_pattern` `cases=12`+guard `patterns=4`、`professional_component_registry` `cases=137`、`page_pattern_reference_parity` `surfaces=15`、`rendering_detail_state`（58 tests，含三份 inventory `--check`）PASS、`native_form_structure_responsibility` `cases=10`；日志中 `[frontend_official_design_alignment_inventory] FAIL incomplete=…` 是生成器**负向测试**（`test_generate_frontend_official_design_alignment_inventory.py:54`）的预期输出，该目标退出码 0。 |

**验收结论**：列表与只读详情接管**在当前整合候选上验收通过**（第 9 项为过程缺陷、已按仓库机制修复）。
`TPL-03` 的“官方列表 + 只读详情”范围就此收口。

**边界（不得夸大）**：

- switch 的旧详情一步落在既有加载失败的 `/r/res.partner/1`（见上一节），只证明“采纳组合未泄漏”；
  可正常渲染的旧详情参照为 `fixture_role_pm` 下的 `/r/project.project/10`。
- 只宣布已采纳范围（列表 `project.project` + `sc.general.contract`；只读详情 `sc.general.contract`）；
  未运行应用外壳（TPL-04）、主从办理（TPL-05）、付款明细与合同全流程（R7R9/R5）。
- 89 入口唯一分母不变，未调整业务矩阵状态；不推送、不合并、不部署目标环境。

### FE-TPL-04 官方应用外壳采纳验收（2026-09-29）

同一专题分支 `feature/web-official-template-adoption`。把应用外壳的**采纳范围**从内联的
route-meta 比较，提升为显式、按 layout 限定的呈现策略，并把外壳样式层从组件本地别名块收敛到
权威令牌。**纯呈现改动**：不删除任何外壳能力、不新增业务语义。候选
`b2fa65b6be864c271d8859a743cb49ab34fa2783`（工作树 clean），本轮提交：
`1bf2d783`（采纳实现）与 `b2fa65b6`（仅派生清单刷新）。逐项判定如下，每项给出实现位置与原始证据。

| # | 验收项 | 判定 | 实现位置 / 原始证据 |
|---|---|---|---|
| 1 | 采纳由显式策略驱动，不由外观、名称或角色推断 | PASS | `frontend/apps/web/src/app/presentation/standardShellComposition.ts:46`（`STANDARD_SHELL_COMPOSITION_LAYOUTS`）、`:50` `resolveStandardShellComposition`；纯函数（无 Vue/DOM/TDesign/model/menu/action/role 输入）。调用点只传 `route.meta.layout` 与内嵌弹窗标记：`App.vue:50-53`。 |
| 2 | 外壳门与对外发布的采纳身份同源，不会漂移 | PASS | `frontend/apps/web/src/App.vue:5-7`：`v-if="shellComposition.adopted"` 与 `:data-shell-composition`/`:data-shell-composition-reason` 都取自同一次 `resolveStandardShellComposition` 决策。 |
| 3 | 未采纳路由与内嵌关系弹窗保持旧呈现，无双重外壳/半转换 | PASS | `standardShellComposition.ts:55-57`（非采纳 layout → `legacy-shell-surface`/`not-a-shell-layout`）、`:58-60`（内嵌关系弹窗 → `legacy-shell-surface`/`embedded-relation-dialog`）；此处直接渲染页面组件。 |
| 4 | 官方组合在真实页面被采纳（双视口） | PASS | `artifacts/frontend-web-fix-20260928/tpl04b/shell-parity-results.json` 的 `after-5178-b2fa65b6` 运行：`1440×900` 与 `390×844` 均为 `official-standard-shell`/`shell-layout-adopted`，`compositionMarkerCount=1`，`layoutDriver=tdesign`；参照构建 `f017d42d` 无标记（`null`）。 |
| 5 | 采纳前后呈现值等价，无视觉回归 | PASS | 同上：`diffs = []` —— 15 项实测计算值在**两个构建、两个视口**完全一致（`shell.color` `rgb(46,49,51)`、`topbar.minHeight` `52px`/`0px`、`sidebar.width` `232px`、分隔线 `rgb(226,232,240)`、触控目标 `44px` …）。 |
| 6 | 组件本地别名收敛到权威令牌且取值不变 | PASS | `frontend/apps/web/src/layouts/AppShell.css:7`（`--sc-semantic-text-primary`）、`:54/:235/:263/:369`（`--sc-semantic-border-default`）、`:455`（`--sc-semantic-surface-panel`）、`:555`（`--sc-semantic-text-secondary`）、`:976-979/:1143-1144`（`--sc-touch-target-min`）；6 个本地别名实测由 hex 变为空串（已移除，非遮蔽）。`--sc-semantic-text-primary` 与旧 `--ink` 解析值完全相同。 |
| 7 | 外壳能力无回退 | PASS | 同上 JSON：桌面折叠 `hidden false→true→false` 且侧栏随之存在/消失；390px 打开抽屉 `{sidebar: true, role: "dialog", backdrop: true}`；two 构建均 `consoleErrors: []`，均无横向溢出。 |
| 8 | 参考一致性门禁与结构门禁扩展 | PASS | `scripts/verify/frontend_page_pattern_reference_parity_guard.py` 新增 4 条 AppShell.css 要求 + `App.vue` 条目（`surfaces` 15→16）；`test_frontend_page_pattern_reference_parity_guard.py` 新增 2 条负向测试（共 15 tests OK）。 |
| 9 | 派生清单与当前源码一致 | PASS | `b2fa65b6` 用仓库自带生成器刷新 4 份派生清单：仅摘要变化，无计数/状态/词汇变化（`component-professionalization` `surfaces=169 gaps=0`、`official-design-alignment` `internalVendorSelectorGapCount=0`）。 |
| 10 | 相关 L2 单元/结构门禁 | PASS | `artifacts/frontend-web-fix-20260928/tpl04b/logs/tpl04b-gates-run.log`：`standard_shell_composition` `cases=69 layouts=1`、`page_pattern_reference_parity` `surfaces=16`、`navigation_shell` 19 tests/`components=5`、`rendering_detail_state` 58 tests（含 `shell_density_contracts=2` 与三份 inventory `--check`）、`component_driver_takeover` `required=35 missing=0`、`product_page_pattern` `cases=12`/`patterns=4`；全部 `exit=0`。 |
| 11 | 相关类型检查 | PASS | `.../tpl04b/logs/tpl04b-typecheck.log`：`make verify.frontend.typecheck.strict` 运行 `vue-tsc --noEmit` 与 `tsc.strict` 两份配置，`exit=0`、0 错误。 |
| 12 | 源码—产物—证据绑定同一候选 | PASS | 候选 `b2fa65b6`；离仓构建 `.../fe-tpl04b-20260929/dist`（`index.html` sha256 `74f58f11…9eac`，入口 `/assets/index-Dnkap0aw.js` sha256 `b3b16f06…06bb`），`release_static_server.mjs` pid 3174598 @ `:5178`；`served-bundle-identity.json` HTTP 取回 **100/100** 文件逐字节一致（`mismatches: 0`）；探针 `loadedScripts` 含该入口。 |

**验收结论**：应用外壳的官方组合采纳**在当前候选上验收通过**，且采纳前后外壳呈现值完全等价。
`TPL-04` 的“官方应用外壳”范围就此收口；不据此宣布 TPL-05 或整个前端模板接管通过。

**边界（不得夸大）**：

- 本轮的浏览器证据是**只读角色 `fixture_role_pm` 对外壳的观测**，不是业务旅程：该角色可见外壳但无业务顶栏，
  `rail.borderRightColor`/`footer.borderTopColor` 仅在 `1440×900` 测得（窄屏下栏隐藏）；未触发任何保存链或权限边界。
- `verify.frontend.style_system.guard`（`scripts/audit/design_token_system.py`）仍报**既有**问题：
  `ScRelationField.vue` 的新 z-index 未登记，以及 `ContractFormPage.vue`（1932>1900）、
  `useRecordActionPresentation.ts`（505>500）、`useRecordFormActions.ts`（804>619）超长。
  **非本轮引入**，属范围外，未在本轮处理。
- 未运行 89 入口矩阵、全站浏览器验收与发布门禁；89 入口唯一分母不变；未调整业务矩阵状态；
  **未**进入 TPL-05；不推送、不合并、不部署目标环境；参照服务（`:5176`）及其构建目录保持原样。

### FE-TPL-04 scope A 官方外壳对齐验收（2026-09-29）

范围：把 `artifacts/frontend-web-fix-20260928/shell-official-comparison/COMPARISON.md`
§三 列出的 4 项“可对齐且不损失产品能力”的不一致，改为消费官方 TDesign 组合。
本轮只做呈现与组合对齐；不新增业务语义、不删除外壳能力。

| # | 验收项 | 判定 | 实现位置 / 原始证据 |
|---|---|---|---|
| 1 | 高度由令牌权威驱动、与官方 `t-header` 带同值 | PASS | `frontend/packages/design-tokens/tokens/component.json`：`shell.topbar_height` 48→56、`shell.sidebar_collapsed_width` 56→64（dist 令牌已重建，`verify_tokens.py` PASS）；`frontend/apps/web/src/styles/tokens/pattern.css:44-46` 的 `--sc-shell-topbar-height` / `--sc-shell-sidebar-collapsed-width` 成为真实消费者。实测解析值 `tokenXxxl=56px`、`shellTokenValue=56px`。 |
| 2 | 页头回到官方 `t-header` 带（非本地高度覆盖） | PASS | `frontend/apps/web/src/layouts/AppShell.css:456-457`（`.topbar` `min-height: var(--sc-shell-topbar-height)`，桌面块内 `height` 同值）；`AppShell.vue:193`（`ScHeader` → `t-header`）。实测 `header.height` 52px → **56px**（1440×900），窄屏 `minHeight` 0px → 56px。 |
| 3 | 面包屑使用官方 `t-breadcrumb`，无本地仿制与并存旧行 | PASS | `frontend/apps/web/src/components/product-shell/NavigationBreadcrumb.vue`：渲染 `TDesignBreadcrumb :max-item-width="'150'"` + `TDesignBreadcrumbItem`，scoped CSS 仅保留槽位（本地字号/分隔符规则已删除）。实测 `crumbs.present` false → true、`itemCount` 0→1、`legacyCrumbNodes` 两侧均为 0（旧 `.crumb` 未与新组件并存）。 |
| 4 | 侧栏折叠回到官方 64px 紧凑栏，入口在侧栏底部 | PASS | `MenuTree.vue`（`t-menu :collapsed`）、`ProductSideNavigation.vue`（`:collapsed`）、`ProductShellSidebarFooter.vue`（`sidebar-compact-toggle`，`aria-controls="primary-sidebar"`）、`AppShell.css:1160-1180`（紧凑栏块）。实测 `shell--sidebar-hidden` → `shell--sidebar-compact`；`sider.box.w` → **64**、`flexBasis` `64px`、`menuCollapsed true`；`bottomCollapseControl` false → **true**、`topbarTogglePresent` true → **false**、`aria-expanded` `true→false→true`。 |
| 5 | 内容列挂载真实 `t-footer` 并采用官方页脚几何 | PASS | 新增 `frontend/apps/web/src/components/design-system/ScFooter.vue`（`TDesignFooter` 原语）与 `product-shell/ProductShellContentFooter.vue`；`AppShell.vue:379` 挂载于内容列；`AppShell.css:435-447` 采用官方 `*-footer-layout` 语义（零内边距 + 一个 24px 偏移）与居中说明文字。实测 `content.footerPresent` false → true、`footerTag` → `FOOTER`、`footerPadding` → **0px**、`footerInsideContent true`。 |
| 6 | 未采纳面与产品扩展不回退 | PASS | 移动抽屉 `{sidebar: true, role: "dialog", backdrop: true}`（390×844）；工作空间/公司/记录范围面板、活动页签、导航搜索、退出登录均保留（`AppShell.vue`、`ProductShellSidebarFooter.vue`）。两构建两视口 `consoleErrors: []`、无横向溢出。 |
| 7 | 源码—产物—证据绑定同一候选，且构建可复现 | PASS | 候选 `fed15486`/`c3e29246`/`ed14d7bd`；离仓构建 `.../fe-tpl04d-20260929/dist`（`index.html` sha256 `b61b92de…7577`，入口 `/assets/index-DJ44umQ0.js` sha256 `174d4e35…3547`），`release_static_server.mjs` pid 4007259 @ `:5180`；`served-bundle-identity.json` HTTP 取回 **100/100** 文件逐字节一致（`mismatches: 0`）；同源码二次构建逐字节一致（100/100 文件、`contentDiffCount: 0`）。探针记录的入口与 `index.html` 一致。 |
| 8 | 派生清单与当前源码一致 | PASS | `ed14d7bd` 用仓库自带生成器刷新 4 份清单：`component-driver-takeover` `required=35 missing=0 bridge_only=0 raw=0`（`breadcrumb` 首次获得 `bridgeExports`+适配源）、`rendering-detail` `surfaces=169 gaps=0`、`official-design-alignment` `internalVendorSelectorGapCount=0`/`visualLiteralGapCount=0`、`visual-projection` 新增 3 个源。两个 refresh 目标均为幂等（重复运行文件字节不变）。 |
| 9 | 相关 L2 单元/结构门禁 | PASS | `standard_shell_composition` `cases=71 layouts=1`、`navigation_shell` 19 tests/`components=5`、`page_pattern_reference_parity` `surfaces=16`、`rendering_detail_state` 58 tests（`surfaces=95`、`shell_density_contracts=2`、三份 inventory `--check` PASS）、`component_driver_takeover` `required=35 missing=0`、`product_page_pattern` `patterns=4`、`delivery_hardening.guard` PASS（`async_epoch=enabled axe=4.10.2`）；全部 `exit=0`。日志中 `[frontend_official_design_alignment_inventory] FAIL incomplete={'internalVendorSelectorGapCount': 1}` 是生成器**负向测试**的预期输出，该目标退出码 0、正式检查输出 `internalVendorSelectorGapCount=0`。 |
| 10 | 相关类型检查 | PASS | `make verify.frontend.typecheck.strict`：`vue-tsc --noEmit` 与 `tsconfig.strict.json` 两份配置，`exit=0`、0 错误（在本轮最后一次源码改动之后重跑）。 |

**验收结论**：COMPARISON.md §三 的 4 项“纯呈现/交互不一致”**在本轮候选上已完成官方组合对齐并实测通过**；
对齐后内容列页脚几何、面包屑组件、侧栏紧凑栏与页头高度均与官方模板取值一致。
本结论不覆盖下方“仍未对齐”项，也不据此宣布 TPL-05 或整个前端模板接管通过。

**对齐后仍未对齐（本轮未改动，不得当作已一致）**：

- **页脚位置**：我方是内容列内的页脚带（贴列底部），官方把 `t-footer` 放在内容列的滚动容器内，
  内容短时官方页脚紧跟内容。改动会牵动全站单一滚动属主（`.shell-content-surface` → `.router-host`），
  本轮只对齐官方 `*-footer-layout` 的几何与文字处理，未迁移滚动属主。
- **面包屑位置**：我方在页头工具条内渲染 `t-breadcrumb`，官方把 `<l-breadcrumb>` 置于 `t-content` 首行。
  本轮只完成组件采纳，未迁移位置。
- **移动端无官方基准**：官方模板 `src/style/layout.less:36-41` 对内容列强制 `min-width: 760px`，
  不存在 390px 官方呈现；我方窄屏页头为两行产品组合，实测 78px，只保证不低于官方 56px 下限。
- **官方一侧为源码级比对**：未运行官方模板本体，未做像素级截图对比。

**边界（不得夸大）**：

- 浏览器证据是**只读角色 `fixture_role_pm` 对外壳的观测**，不是业务旅程：未触发保存链、权限边界或合同业务办理；
  截图只证明可见呈现，不证明写入与回读。
- `verify.frontend.style_system.guard`（`scripts/audit/design_token_system.py`）仍报**既有**问题：
  `ScRelationField.vue` 的新 z-index 未登记，以及 `ContractFormPage.vue`（1932>1900）、
  `useRecordActionPresentation.ts`（505>500）、`useRecordFormActions.ts`（804>619）超长。
  **非本轮引入**，属范围外，未在本轮处理。
- 未运行 89 入口矩阵、全站浏览器验收与发布门禁；89 入口唯一分母不变；未调整业务矩阵状态；
  **未**进入 TPL-05；不推送、不合并、不部署目标环境；参照服务（`:5176`/`:5178`/`:5179`）
  及其构建目录保持原样，历史失败记录未被覆盖。

### FE-TPL-04 scope B 内容区布局收口验收（2026-09-29）

范围：按所有者决策只处理两项内容层级——面包屑迁入内容区首行，页脚迁入**现有**主内容滚动区域，
随内容自然滚动。不为复制官方 DOM 更换全站滚动属主；移动端继续使用我方窄屏适配，
**不**照搬官方 `min-width: 760px`，也不把“移动端无官方样板”记为欠账。
本节关闭 scope A 记录中“面包屑位置”“页脚位置”两条仍未对齐项；组件采纳（scope A）结论不回退。

| # | 验收项 | 判定 | 实现位置 / 原始证据 |
|---|---|---|---|
| 1 | 面包屑在内容区首行，且只有一份 | PASS | `frontend/apps/web/src/layouts/AppShell.vue:196-201`（页头标题行只剩 `h1`，面包屑与 `:minimal`/`:compact` 传参一并移除）；`:334-336` 新增 `content-breadcrumb-row`，位于 `ScContent` 内、`StatusPanel`/`main.router-host` 之前；`AppShell.css:454-458`（`flex:0 0 auto` + `padding: var(--sc-space-xs) var(--sc-page-padding) 0`，与页面栅格同槽位）；死规则 `.topbar--single-heading .topbar-breadcrumb` 已删除（保留 `.eyebrow` 半边）。实测 `inTopbar:false` / `inContentArea:true` / `inContentRow:true` / `insideRouter:false`，行内边距桌面 24px、窄屏 12px，`itemCount=3`，导航来源、路由身份与权限均未改（沿用同一 `displayBreadcrumb` 与 `NavigationBreadcrumb`/`t-breadcrumb`）。 |
| 2 | 页脚进入现有单一滚动属主，随内容滚动 | PASS | `AppShell.vue:365-368`：`ProductShellContentFooter` 由 `ScLayout` 列内兄弟节点移入 `<main class="router-host">` 末尾、`<slot />` 之后；`AppShell.css:441-452` 沿用官方 `*-footer-layout` 几何；`AppShell.css:559-576`：`.router-host` 改 `display:flex; flex-direction:column; flex:1 1 auto`（仍是唯一 `overflow-y:auto`），新增 `.router-host > * { flex-shrink:0 }`；`styles/product-patterns.css:45-55`：`.router-host > :is(.sc-page-frame,.sc-product-page-frame)` 由 `min-height:100%` 改 `flex:1 0 auto`。实测页脚 `insideRouter:true`、`position:static`；长页 `scrollDelta=44`（改动前同为 44）、长详情 `scrollDelta=760`（改动前同为 760）、短页 `scrollDelta=0` 无幻影滚动；每页纵向属主恒为 `router-host` 单一个。**未**新增第二个滚动容器、未改路由滚动恢复、未改表头固定偏移。 |
| 3 | 桌面长/短页与窄屏可用 | PASS | `scopeB-layout-results.json`（stamp `20260929032437`，只读角色 `fixture_role_pm`）**15/15 PASS**：长页/长详情页脚紧跟内容无重叠、短页无空白占位与额外滚动、390×844 无横向溢出且抽屉 `role=dialog` 可用、两视口 `consoleErrors: []`。 |
| 4 | 一条既有页面往返与错误定位 | PASS | `scopeB-write-results.json`（stamp `20260929032225`，`fixture_role_contract_operator`）**9/9 PASS**：列表→详情(11)→编辑(10)→返回，列表查询上下文保持、每步单属主+内容区面包屑；必填拒绝时错误定位到真实控件（`controlBelowHeader`、`controlInViewport` 均 true）且**零写请求**，草稿放弃后记录回读不变；`consoleErrors: []`。 |
| 5 | 相关 L1/L2 与构建 | PASS | `verify.frontend.workspace_content_alignment.guard`（`entries=31`）、`standard_list_scroll_contract.guard`（`vertical_owner=router-host`）、`standard_shell_composition.unit`（`cases=71`）、`navigation_shell.unit`、`product_page_pattern.unit`、`rendering_detail_state.unit`、`component_driver_takeover.unit`（`required=35 missing=0`）、`page_pattern_reference_parity.unit`（`surfaces=16`）、`verify.frontend.typecheck.strict` 全部 `exit=0`（`AppShell.vue` 1597 行，上限 1600）；单次构建见下。 |

**候选与产物**：被测产品源 `fb5934b7`（薄派生 HEAD `69da338f` 仅刷新清单），工作树干净；
离仓单次构建 `…/fe-tpl04e-20260929/dist`，`index.html` sha256 `a1d049b9…10ea`、
入口 `/assets/index-CGFvSmxS.js` sha256 `11da9347…5dbfd`、`runtime-config.js` 值 `{}` 无凭据；
`release_static_server.mjs` pid 60945 @ `:5180` 服务该目录，HTTP 取回的 `index.html` 与入口块
与构建产物**逐字节哈希相同**，探针记录的加载入口即该入口块。历史产物与失败记录未被覆盖；
`:5176`/`:5178`/`:5179` 三个旧预览进程本轮未清理。

**本轮内的测试维护（非产品缺陷）**：首次写入探针使用 `sc.general.contract` **12**，
该记录属 `FE Project C`/`FE Company B`（id 9），不在这两个角色的范围（`FE Company A`/id 8），
`PROJECT_SCOPE_DENIED → /access-denied` 是既有的项目范围契约按设计生效，不是布局回归；
探针改用范围内的 **11（详情）** 与 **10（编辑）**。`/f/…/11` 对已确认记录呈现只读详情，
故可编辑表单步骤必须使用记录 10；详情(11)→编辑(10) 返回时回到打开它的详情条目即为正确历史语义。

**仍未对齐 / 保留的差异（不得当作已一致）**：

- `/`（角色首页）本身无面包屑轨迹（导航态面包屑 0 项），故 `v-if` 守卫下不渲染该行——与本轮之前一致。
- 移动端为**我方窄屏组合**（两行页头实测 78px），非官方呈现；官方一侧仍为源码级比对，未运行官方模板本体。
- `verify.frontend.style_system.guard` 仍报**既有** 4 项（`ScRelationField.vue` 未登记 z-index、
  `ContractFormPage.vue` 1932>1900、`useRecordActionPresentation.ts` 505>500、`useRecordFormActions.ts` 804>619），非本轮引入、未处理。
- 历史 `cc0eee7b` 产物被覆盖的缺口继续登记为历史限制，不倒填、不追溯。

**边界（不得夸大）**：页脚与面包屑是**按我方适配**迁移到官方位置，不写成“与官方完全一致”；
未运行 89 入口矩阵、全站浏览器验收与发布门禁（本轮差异无关）；89 入口唯一分母不变；
未调整业务矩阵状态；**未**进入 TPL-05，也不据此宣布 TPL-03 通过；不推送、不合并、不部署目标环境。
本轮未创建/修改/删除任何业务数据：写入探针拒绝后放弃编辑，`sc.general.contract` 记录 10
前后逐字段一致、记录总数 3 不变。

### FE-TPL-03 列表与详情定向验收（2026-09-29）

范围：确认**已实现**的官方列表与只读详情不仅完成结构替换，而且正确消费真实服务端查询、
记录身份与业务动作。不重新开发列表/详情，不继续外壳对齐，不处理四项 `style_system` 欠账，
不进入 TPL-05。已完成的 TPL-04B 外壳结论直接复用，不重复采集几何。

**候选与运行来源（复用，未重建）**：被测 HEAD `9e240dc4`（薄派生提交，产品源 `fb5934b7`，
两者间无产品源码差异），工作树干净；沿用已固定的 `:5180`（`scripts/release/release_static_server.mjs`
pid **60945**，`STATIC_ROOT=…/sce-offrepo/artifacts/fe-tpl04e-20260929/dist`，经 `/proc/60945/environ` 核实），
`index.html` sha256 `a1d049b9…10ea`；后端 `127.0.0.1:18082`、库 `sc_frontend_acceptance`；
写入角色 `fixture_role_contract_operator`。产品源未变，故不重建、不新增端口、不重跑 HTTP 全文件比对。
权威运行记录：`artifacts/frontend-web-fix-20260928/tpl03closeout/tpl03-closeout-results.json`
（stamp `20260929035002`），探针 `tools/tpl03_closeout_probe.mjs`，日志 `logs/tpl03-closeout-probe.log`。

| # | 验收项 | 判定 | 实现位置 / 原始证据 |
|---|---|---|---|
| 1 | 官方列表承担呈现与通用交互，真实服务端查询/身份/授权仍由原链路控制 | PASS | 采纳为**前端**切换：`frontend/apps/web/src/app/presentation/standardListComposition.ts`（`STANDARD_LIST_COMPOSITION_PILOT_MODELS=['project.project','sc.general.contract']`，标记 `data-list-composition="official-standard-list"` / `reason=pilot-model-adopted`）。探针绑定真实 `POST /api/v1/intent` `op:list` 请求+响应，非仅 DOM。 |
| 2 | 查询发往服务端并改变结果集 | PASS | 搜索 `GC2600011` 携带 **`params.search_term`**，服务端 `total 2→1`、`共 1 条 1`；非前端数组过滤。清除后恢复 `total=2`。 |
| 3 | 排序由服务端语义控制 | PASS | 点击列头 `contract_name` 发送 `order:"contract_name asc"`（基线 `contract_date desc, id desc`），行序随之变化；无第二套本地排序。 |
| 4 | 分页为真实请求 | PASS（含 1 项证据缺口） | 每页选项 `10/20/50 条/页`；选择 10 发送真实 `limit:10 offset:0`。**真实下一页**在受管数据上不可达（最小页长 10 仍只 1 页，最大在职集合仅 2/4 行），记为 `kind: evidence_gap` 并附实测数字，不写成通过。 |
| 5 | 无结果与恢复；接口失败不伪装成“没有数据” | PASS | 不命中查询得 `共 0 条` + `.list-empty-surface`（“没有符合当前条件的记录…”）、`alerts: []`；清除后恢复 `total=2`。 |
| 6 | 只读详情事实与模式正确 | PASS | `/r/sc.general.contract/10` = `official-standard-detail`，0 可编辑控件、0 保存动作；事实 `FE-A General Contract`/`GHT2600010`/`FE Project A` 与记录一致。`/r/…/11` = `FE-B General Contract`/`GHT2600011`/`FE Project B`，0 编辑/0 保存/0 旧 grid 行。`/f/…/10` 才是同记录可编辑面（23 可编辑、`保存草稿`）。 |
| 7 | 同记录往返不串位 | PASS | 列表 10 → 详情 10 → 编辑 10 → 返回：详情与“从编辑返回”均为 `/r/…/10`；回到列表 `/a/673…order=contract_name+asc…` 且 **保留 `search=GC2600010`**，行回读 `GC2600010`/`GHT2600010`/`FE Project A`。 |
| 8 | 代表视口可用 | PASS | 390×844 列表与详情：无横向溢出、纵向属主恒为 `router-host` 单一个、详情仍只读；`consoleErrors: []`。 |

**本轮内的测试维护（探针缺陷，非产品缺陷）**：

- 列表搜索词是 `params.search_term`（非 `search`）；run1 读错键导致 `L2` 假失败。提交按钮文案为 `搜索`，
  清除为 `清除`。
- 事实标签映射：`合同编号`→`contract_no`（`GHT…`，非 `name` 的 `GC…`）、`合同名称`→`contract_name`、
  `关联项目`→`project_id[1]`；run1 误用 `name` 断言 `合同编号`，导致 `R2`/`D1` 假失败。
- 从编辑表单返回需沿打开它的详情条目回退；`R4` 改为循环 pop 历史直至 `/a/673` 再断言 `search=GC2600010` 保留。
  上述修正只改探针定位/取值方式，**未降低断言、未吞失败、未改产品迎合探针**。

**范围与边界（不得夸大）**：

- 记录 11 为**独立只读核验**，不是同记录闭环；`/r/11` 与 `/r/10` 是同一只读机制，可编辑步骤必须使用记录 10，
  **禁止**把“详情 11 → 编辑 10”写成同记录办理闭环。
- 记录 12 的 `PROJECT_SCOPE_DENIED` 是项目范围契约**按设计生效**（记录 12 ∈ `FE Company B`/id 9，
  角色范围 `FE Company A`/id 8）；保留为正常权限拒绝，未改角色或业务域来消除它。
- 分页下一页为**证据缺口**，已附实测数字，不静默转成通过。
- `verify.frontend.style_system.guard` 四项欠账（`ScRelationField.vue` 未登记 z-index、
  `ContractFormPage.vue` 1932>1900、`useRecordActionPresentation.ts` 505>500、`useRecordFormActions.ts` 804>619）
  仍保持**真实 FAIL**，放入独立合并前清理批次；未放宽阈值/忽略文件/压缩行数/改退出码；`AppShell.vue` 1597/1600，
  未在其中新增业务职责。
- 已确认的**异步身份漏洞**保持其既有阻断状态，不因本轮布局/列表验收自动消项，本轮也未重新开启排查。
- 历史 `cc0eee7b` 产物缺口继续登记为历史限制，不倒填、不追溯。
- **TPL-03 结论：PASS（含 1 项受管数据不可达的分页证据缺口）**，限于上述已核验的列表职责、只读详情、
  同记录往返与代表视口；不代表 89 入口矩阵或所有路由/所有模型均已验收。业务矩阵状态不因模板验收升级；
  未重跑 89 入口、全站发布验收与发布门禁；**未**进入 TPL-05；不推送、不合并、不部署目标环境。
- 本轮未创建/修改/删除任何业务数据（未执行保存）；`sc.general.contract` 记录总数保持 3。

### FE-TPL-03 收口后的两个真实缺陷修复（2026-09-29）

用户在实际页面上报两个问题，均为**产品缺陷**，已定位根因、修复并定向复验；不重开 TPL-03 全量验收。

**候选与运行来源**：修复提交 `1087d708`（IME）、`fd581cb9`（表单体快捷筛选）之上 HEAD 为 `fd581cb9`，
工作树干净。同批次构建一次：`scripts/dev/frontend_static_build.sh` →
`sce-offrepo/artifacts/fe-tpl03fix-20260929/dist`，`index.html` sha256
`cee31a23e6b353dce8524cb6885170e0d3d6a024f9c31456d7f934e8eec3354f`，入口 `/assets/index-jnbV95D6.js`。
旧 `:5180`（pid 60945，服务 `fe-tpl04e-20260929/dist`）经核实后停止，同一端口改由新进程
（pid **608525**，`STATIC_ROOT=…/fe-tpl03fix-20260929/dist`）服务；`/api/`、`/web/` 仍代理到 `:18082`。
历史产物 `fe-tpl04e-20260929/dist` 与历史 `tpl03closeout/tpl03-closeout-results.json`（stamp `20260929035002`）
**保留未覆盖**，不因新运行倒填。

| 缺陷 | 根因 | 修复位置 | 复验证据 |
|---|---|---|---|
| 列表搜索框中文（IME）输入丢失 | `ScInput.vue` 未声明/透传 `compositionstart|end`；TDesign 走自身 `(value, context)` 签名且此处 `value` 陈旧，调用方读 `event.target.value` 得到 `""`，每次合成上屏清空草稿 | `frontend/apps/web/src/components/design-system/ScInput.vue`（透传真实 `CompositionEvent`）；`pages/ListPage.vue`、`views/ActionView.vue`（容错读取 `target.value` / `{e:{target}}` / 字符串，无法解析则**保留**草稿） | `tools/tpl03_search_ime_probe.mjs` 真实 CDP 合成：`commit-合同 → value="合同"`、`SEARCH_REQ {"search":"合同"}`（修复前 `value=""`、`search: undefined`） |
| 「快捷筛选」（列表查询预设）泄漏到表单体 | `formActionPlaceholderGate` 仅对 `useNativeFormTree || nativeAuthority` 关闭预设；已采纳的 `sc.general.contract` / `project.project` 表单体两者皆否，故泄漏 | `pages/contractForm/formActionPlaceholderGate.ts` 新增 `officialFormComposition`（仅关闭 `suppressSearchFilters`；流转/体动作仍只看结构归属）；`pages/ContractFormPage.vue` 传入 `standardFormComposition.adopted` | `hasQF:false`、`hasQuickFilterChips:false`、表单字段与页签在位、`CONSOLE_ERRORS []`；截图 `tpl03closeout/fix-1440-form10.png` |

**回归与门禁**：`make verify.frontend.native_form_structure_responsibility.unit` → `PASS cases=10`（新增
`officialFormComposition` 两例）；`make verify.frontend.typecheck.strict` → exit 0。修复后在**新候选**上重采
TPL-03 探针：`artifacts/frontend-web-fix-20260928/tpl03fix-20260929/`（stamp `20260929045101`），
**16 PASS / 1 GAP**（分页下一页仍为受管数据不可达的证据缺口）、`consoleErrors: []`；列表查询/排序/清除、
详情 10/11 只读、同记录往返、390×844 全部无回退。旧 `tpl03closeout` 结果保持不变，两次运行分别注明候选。
本轮未创建/修改/删除业务数据（未执行保存），记录总数保持 3。

**边界（不得夸大）**：历史 `cc0eee7b` 产物缺口与异步身份漏洞的既有阻断状态**均未因此消项**；
四项 `style_system.guard` 欠账仍为真实 FAIL、独立记账；不重跑 89 入口/全站发布门禁；
不修改业务矩阵；不推送、不合并、不部署；**未**进入 TPL-05。

### BOUNDARY-01：契约边界硬化与验收缺口闭合（2026-09-29）

本节**取代**上文"FE-TPL-03 收口后的两个真实缺陷修复"中对"快捷筛选"修复方式的描述：
当时先落地的 `officialFormComposition` 开关（判断"是否官方组合"再关掉预设块）**只是补丁**——它把
"表单正文不该承载列表查询面"这条业务职责边界交给了一个渲染承载标志。现改为按职责边界直接删除该职责，
并补上代码依赖与门禁级执行。原有提交与复验记录保留，不倒填、不改写。

**权威运行标识（本批权威证据）**

- 候选源码：本轮提交（见下 `fix(web)` 三笔）；`artifacts/` 为 gitignored，证据不入库。
- 产物：`sce-offrepo/artifacts/fe-tpl03boundary-20260929/dist`，`index.html` sha256
  `092486e77ac4535a050def56094d03ce5683d82d29eb303e12ec7acf3e389a16`，入口 `/assets/index-BMkF2JIf.js`。
- 服务：`127.0.0.1:5180`（pid 796716，`scripts/release/release_static_server.mjs`，`STATIC_ROOT` 指向上述产物，
  `/api/`、`/web/` 代理 `:18082`）。停旧进程前已核对 PID、命令行与 `STATIC_ROOT`；旧
  `fe-tpl03fix-20260929/dist`（`index.html` sha256 `4fd1050f…b5612`）与 `fe-tpl04e/tpl04b/tpl04c` 产物**均未覆盖**。
- 运行记录：`artifacts/frontend-web-fix-20260928/tpl03boundary-20260929/`（stamp `20260929052308`，
  **19 PASS / 1 GAP / 0 deviation / consoleErrors []**）；同目录 `run1-prenavrule/`（stamp `20260929051816`）
  保留为导航标签修复前的同候选运行，不倒填。
- 库与角色：`sc_frontend_acceptance`，`fixture_role_contract_operator`。本轮**未执行任何保存**，
  记录总数保持 3（`GC2600010/11`、记录 18 已删除），无数据创建或删除，无需恢复动作。

**根本原因（产品）**

| 缺陷 | 根本原因 | 修复 |
|---|---|---|
| "快捷筛选"（列表查询预设）出现在表单正文 | 表单页自行消费记录列表搜索契约并渲染查询块；提前落地的修复只把它与"是否官方组合"绑定 | 直接删除该职责：`ContractFormPage.vue` 不再 import/消费列表搜索契约，`ContractFormActionBlocks.vue` 删除查询块与相关 props，`useFormNavigationActionsRuntime`/`contractFormMetaLine` 同步清理 |
| 列表搜索框中文（IME）丢失 | `ScInput` 未按共享适配器约定透传组合事件，调用方又读不到 TDesign 的取值路径 | `ScInput` 复用共享 `resolvePrimitiveNativeEvent`；`primitive_adapter_contract_test.ts` 扩到 6 个事件用例并断言真实 `CompositionEvent` 取值 |
| 记录表单分区标题全部塌缩为占位名 | `NativeFormTreeRenderer.semanticSectionTitle()` 用**前端硬编码的语义角色→中文业务标签表**兜底；且"空角色 == 空继承角色"的抑制条件把有契约标题的首个分区也一起吃掉 | 分区标题改为契约解析：统一走 `resolveNativeSectionHeading()`（原生锚点 → 契约 `string/label` → 契约 `semanticTitle`），删除该硬编码表；`nativeSectionNavigation.SECTION_LABELS` 同源治理 |
| 列表/详情承接方式变化后边界失效 | 判断入口是"是否原生树"而不是"是否业务职责" | `formActionPlaceholderGate.ts` 引入 `FormActionPlaceholderBodyKind` 穷尽表（`Record<Union,…>`：新增承载种类不补分类即编译失败），只有结构自有正文才可关闭动作入口 |

**验收体系为什么没有发现（缺口分析与闭合）**

| 缺口 | 为什么漏掉 | 闭合方式 |
|---|---|---|
| 只有正向断言 | 探针只检查"该有的存在"（标签、值、条数、请求），从不检查"不该有的不存在"，泄漏的列表查询面因此不可见 | 新增**否定断言** `F1-form-body-hosts-no-record-list-query-presets`（`[data-form-body-action-block="search-filters"]` 计数为 0 且正文无"快捷筛选"） |
| 只到字段层，没到分区层 | 只断言字段标签与取值，分区层级从未被观察；渲染器内的兜底在生产里生效而单测喂的是合成节点，一直绿 | 新增 `F2-form-section-heads-are-contract-authored-titles`：每个渲染出的标题必须等于其容器自己的契约标题、不得是 `默认分组 N` 包装名、不得画在 layout 包装上；并由 `resolveNativeSectionHeading` 的纯函数用例覆盖（`role alone → 无标题`） |
| 用 `fill()` 测输入 | Playwright `fill()` 直接赋值、**不触发 `compositionend`**，IME 缺陷在任何既有探针下都复现不了 | 新增 `L2b` 走真实 CDP `Input.imeSetComposition` + `Input.insertText`，断言上屏值 `合同` 进入搜索请求 |
| 守卫把违规机制钉成标准 | `render_semantic_ready_guard` 原先把 `showSearchFilters` 计算属性列为 **required** token——等于要求违规存在；旧探针又依赖 `.template-form-section-grid > .field-control-row` 这类易变 DOM | 改为 forbidden-token 块（`resolveContractV2SearchContract`/`showSearchFilters`/`快捷筛选`）并新增 `form_body_excludes_list_query_contract` 摘要；新增入侵守卫规则阻止渲染层/导航层发明业务标签（并在修复前源码上验证守卫会真的失败，确保非空断言） |
| 采纳范围按 model 配置，影响面按入口数被低估 | 采纳策略命中整个模型，只验一个入口会低估影响面 | 记录影响面口径：边界按**职责**而非入口数量执行；共享实现以代表模型验证，语义有差异才补验 |

**执行方式**：`make verify.frontend.native_form_structure_responsibility.unit` → `PASS cases=11`；
`make verify.frontend.native_section_navigation.unit` → PASS；`make verify.frontend.primitive_adapter.unit` → PASS components=46；
`make verify.frontend.canonical_form_presenter.unit` → PASS cases=177；`make verify.frontend.standard_form_composition.unit` → PASS cases=114；
`make verify.frontend.form_header_action_primitives.unit` → PASS；`make verify.frontend.typecheck.strict` → exit 0；
`frontend_contract_consumer_intrusion_guard.py` → PASS files_scanned=8。

**已登记未处理（明确不在本批）**

- `render_semantic_ready_guard.py` 仍有一条**既有、与本批无关**的失败：
  `contract_governance missing token: data["render_profile"] = _resolve_render_profile(data)`。
  已核实该文件（`addons/smart_core/utils/contract_governance.py`）本轮未改动，且该字面量在 HEAD 上已不存在——
  属于守卫期望滞后于后端重构，独立记账，不并入本批。
- `verify.frontend.no_new_any_guard`、`make verify.list.surface.clean` 两项仍为既有失败，需在干净 HEAD 上复核后
  另批处理，不归属本次改动。
- 四项 `style_system.guard` 欠账与异步身份漏洞的既有阻断状态**均未消项**。
- 仍未治理的旧推断（登记，不扩面）：`X2ManyRelationRenderer` 等处的 `Record<string,string>` 业务字典、
  `formConfigHelpers` 的原生标签缓存。按"触及范围逐步清理"，新代码不得新增。

**边界四类反例的落点**（规范 §14.2 要求的最小反例，落在既有测试入口，不新建框架）

| 反例类别 | 抓什么 | 现有入口与本批结果 |
|---|---|---|
| 删除关键契约语义 → 明确报缺口或停止 | 静默补齐 | `verify.frontend.native_form_structure_responsibility.unit`（`role alone → 无标题`，cases=11）、`verify.frontend.native_section_navigation.unit`（role-only 分区不给导航项）|
| 换标题/标签/列顺序 → 身份与授权不变 | 文案猜测 | `verify.frontend.adopted_form_validation_identity.unit`（cases=46 failed=0，无跨身份泄漏）、`verify.frontend.contract_error_business_ownership.unit`（92 cases passed）|
| 只改契约规则、不改页面 → 消费随规则变化 | 契约不消费 | `verify.frontend.adopted_form_engine_decision.unit`（cases=74，真实 TDesign 引擎 + 计数写入）、`verify.frontend.standard_form_composition.unit`（cases=114）|
| 只改模板/布局、不改契约 → 输入语义与结果不变 | 模板越权 | `verify.frontend.standard_collection_composition.unit`（cases=64）、`verify.frontend.standard_shell_composition.unit`（cases=71）、`verify.frontend.cross_model_action_navigation.unit` |

`F2` 之所以比"结构计数"更强：它把**渲染出来的分区标题**与**该容器自己的契约标题**逐一比对；
旧的全绿测试只喂合成节点，渲染层兜底在生产里生效也照样通过。

**边界（不得夸大）**：本批是**契约边界硬化 + 验收缺口闭合**，不等于 89 入口矩阵或所有模型已验收；
不重跑 89 入口与全站发布门禁；不修改业务矩阵状态；不推送、不合并、不部署；**未**进入 TPL-05。

### FE-TPL-05A：付款申请主从办理接管（2026-09-29）

**A｜异步保存旧阻断——关闭。** 旧漏洞（校验等待期间切换记录/草稿，旧异步结果污染新上下文）的实现
已在真实保存链上：`frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts` 的
`surfaceEpoch` / `SaveOperation` / `saveOperationOwnsSurface`。本轮不重复修复，只补关闭依据：
`make verify.frontend.adopted_form_validation_identity.unit` → `cases=46 failed=0`、
`no cross-identity leak observed`（真实 Vue 实例 + 真实保存链），覆盖 A 校验晚失败、A 校验晚成功读 B、
A→B→A 同身份重入、旧 `finally` 不清理新操作、校验期间草稿被改等反例。

**B/C｜master/detail 由有效契约驱动。** 入口 `menu_sc_user_payment_apply`（menu 545 / action 775 /
`payment.request`），角色 `fixture_role_finance`，DB `sc_frontend_acceptance`。主单沿用官方表单与规则适配；
明细 `outflow_line_ids` 的契约 `subview.policies={can_create:false, can_unlink:true, inline_edit:true}`：
自由新增被禁，受控路径为 `从结算单引入`（`actionRefs.introduce=payment.request.add.settlement.lines`）。

本轮修复两个**真实缺陷**（独立提交）：

| 缺陷 | 根因 | 修复 |
|---|---|---|
| 明细行「主值重复」误判、保存被拦且零写请求 | `one2manyUtils.collectOne2manyDraftValidationFromRows` 以**首个业务列**（此处 `source_line_type`，导入处理器写同常量「结算单明细」）作行身份，两行以上互相判重 | 改按**行身份**判重（`one2manyRowCollectionIdentity`：`id:N` / `key:K`）；列值只作显示，业务唯一性只能来自契约或存储模型；消息改为 `存在重复明细行：…` |
| 关系字段搜索吞掉空格 | `ProfessionalMany2oneFieldControl.vue` 把 `.trim()` 后的 keyword 作为**受控** `:query-value` 回填输入框，`FE Project` 尾随空格逐字符被删 → `FEProject`，请求亦发规范化键 | 拆成「输入文本（原样回填）」`resolveProfessionalMany2oneSearchInput` 与「请求键（trim）」`resolveProfessionalMany2oneQueryKey`；`useRecordFormState.queryMany2oneInline` 分别存储 |

**主从办理链（真实页面，一次性 49/49 PASS，0 FAIL）**：
`artifacts/frontend-web-fix-20260928/tpl05a-20260929/chain-masterdetail-20260929064307.json`

- 主单草稿：真实关系选择（项目/往来单位/业务分类）→ 金额直填 → 保存 → RPC 回读 `state=draft`。
- 受控引入：两张结算单各引 1 行 → 2 行；无自由新增控件；主单金额由明细合计重绑（300）。
- 编辑一行 → 保存 → 刷新回读：被编辑行正确、其他行未串位、无重复创建、`settlement_line_id` 来源关联正确、
  来源结算单头未变、`applied_amount` 随引入变化（结算行 15→200、14→40）。
- 删除一行 → 保存 → 刷新回读：行消失、`applied_amount` 复原（14→0）。
- 拒绝与恢复：导入对话框把超额申请 clamp 到可申请余额（`9999 → 100`）；同一规则由后端
  `payment.request.add.settlement.lines` 强制（`AMOUNT_EXCEEDS_REMAINING`，且**全量校验后才创建 = 零写入**）；
  主单必填被清空 → 保存被拦（`writesDuring:0`）、明细草稿保留 → 纠正后保存并回读成功。
- 附件：页面文件控件上传 → 刷新可见（`ir.attachment`）→ 下载字节 sha256 与上传一致。
- 受限操作：已批准申请为只读——无 `从结算单引入`、无 `保存草稿`、无可编辑明细输入。
- 窄屏 390×844：无整页横向溢出、单一纵向滚动属主、主操作与明细（移动卡片式）可用。

**唯一控制台报错是正确行为**：`/api/v1/intent` 返回 409 `RECORD_VERSION_CONFLICT`（phase `F-attachment`：
附件上传后立即保存，乐观并发守卫拒绝过期写入），附件已持久化、记录收敛，记为
`Z1b-conflict-recovered-without-loss` PASS；未捕获 JS 异常 0。

**D｜真实下一页，不造数据。** 复用本批受管样本，在已有真实数据的付款申请列表 `/m/545` 完成：
`nextpage-20260929065605.json`，6/6 PASS——每页 10（真实请求 `{limit:10, offset:10}`）→ 下一页 →
第 2 页为**不同记录集合** → 打开该页记录（URL 携带 `list_offset=10`）→ 返回后仍第 2 页、记录集合与请求
`{limit:10, offset:10}` 保持。**未创建任何记录。** 已接管试点列表 `sc.general.contract` / `project.project`
在验收角色下受管可见记录仅 3 / 2 行，最小页长 10 仍单页；该缺口在试点列表上仍受**受管数据量**限制，
记录为限制（不作产品缺陷，也不为它造 7–9 条业务数据）。

**范围必须读准**：`payment.request` **不在** `STANDARD_LIST_COMPOSITION_PILOT_MODELS`
（`frontend/apps/web/src/app/presentation/standardListComposition.ts`）内，该列表当前仍由
`legacy-list-surface` 承载；因此上面这次真实翻页证明的是**共享列表分页/返回上下文链路**，
**不等于官方列表组合的分页已取证**。官方组合的真实下一页仍受试点列表受管数据量限制（单页），
保持 `NEEDS_EVIDENCE`；是否把 `payment.request` 纳入试点（并随之重新构建、对官方组合复验）
留作后续批次决定，本轮不动源码、不重建候选。

**双视口证据**：`tpl05a-masterdetail-desktop.png`、`tpl05a-masterdetail-narrow.png`（含 `-detail.png`
元素截图：申请金额页签、明细 2 条、移动卡片明细）。

**候选与运行来源**：HEAD `196bbcd3` + 两笔缺陷修复提交；`artifacts/` gitignored。产物
`sce-offrepo/artifacts/tpl05a-20260929/dist`（入口 `/assets/index-BwDHt7Yf.js`，磁盘 sha256 == 服务端
`cfddd84c…`）；`:5180` pid `1009190`（`STATIC_ROOT=…/tpl05a-20260929/dist`，代理 `:18082`），
`:5176/:5178/:5179` 未变动。全部改动源码 mtime 早于构建时间，无漂移，故未重复构建。

**回归**：`adopted_form_validation_identity` 46/46、`collection_view_semantics` PASS、
`professional_relation_field` PASS、`typecheck.strict` exit 0。

**数据恢复**：本轮新建的付款申请草稿经 `unlink` 删除（无孤儿 `payment.request.line`）；结算行
`applied_amount` 全部回到 0；既有草稿 1813 未变（`amount=33`、行 `[1,2]`）。删除=新草稿、恢复=结算行
applied、保留=1813 与结算单 13/14/15，分别记录。

**边界（不得夸大）**：四项 `style_system.guard` 欠账与 `render_semantic_ready_guard.py`、
`verify.list.surface.clean`、`no_new_any_guard` 仍独立记账，未处理；业务矩阵未升级整行（只关闭上述
一条既有未修复阻断的记录）；未重跑 89 入口/全站发布门禁；不推送、不合并、不部署；下一批为 WEB-LC-01。

---

## FE-TPL-06A：标准列表推广首例——付款申请（2026-09-29）

**目标**：让付款申请列表采用已实现的官方标准列表组合，与已完成的付款表单/主从办理形成一致体验，
并在同一稳定候选上完成官方组合的真实下一页验证。只本地提交；不推送、不合并、不部署。

### 接管了什么

| 项 | 变化 |
|---|---|
| 列表组合 | `payment.request` 加入 `STANDARD_LIST_COMPOSITION_PILOT_MODELS`（`standardListComposition.ts`），列表改由官方容器 `ProductListSurface`（`t-card.list-card-container` 形态，`bordered=false`，零 body padding 来自 primitive 的 `table` appearance）承载查询行与表格 |
| 呈现路径 | 同一次运行只有一条列表呈现路径：`data-list-composition="official-standard-list"`、`data-list-composition-reason="pilot-model-adopted"`、`data-list-card-container="official"` 包裹表格，列表 surface 仍不出现任何模型名 |
| 查询/排序/分页 | 仍走原链路：服务端 `api.data` 查询域、服务端 `order`、服务端 `limit/offset`，未新增第二份查询状态，也未在服务端分页之外叠加本地分页 |

**旧路径退出**：付款列表不再以 `legacy-list-surface`（无官方容器）承载该范围的 DOM 与交互。
未接管的普通列表仍按原实现渲染（明确登记，不是静默回退）。

### 顺带修掉的共享适配缺口（本轮发现的真实缺陷）

**排序点击被静默忽略**：付款列表“申请付款金额”列在契约里声明 `sort_field: "amount"`
（`request_amount_display` → `amount`），表头据此提供排序；但请求侧的排序白名单
（`collectContractOrderFields`）只收集字段码与 primary/search 候选，**没有收集契约声明的
`sort_field`**，于是 `amount asc` 被静默丢弃、请求继续沿用 `id desc`。用户看到排序已应用（URL 带
`order=amount+asc`），服务端顺序却没变——属于「契约已表达、前端未消费」的静默空操作，不是明确拒绝。

- 修法：白名单同样收集每个 widget 声明的 `sort_field`，使表头可供排序的字段与请求放行字段
  读**同一份契约声明**；反方向仍是 fail-closed（未声明的字段、非标识符、未知方向一律丢弃）。
- 反例测试：`frontend/apps/web/scripts/list_order_field_contract_test.ts`
  （`make verify.frontend.list_order_field_contract.unit`，14 cases）。**去掉修复即失败**，修复后通过。

### 定向验证（同一候选，一次运行）

`artifacts/frontend-web-fix-20260928/tpl05a-20260929/tpl06a-list-after-*.json`（**17/17 PASS，0 FAIL**）：

- A 接管：官方组合身份 + 官方容器包裹表格 + 列表 surface 唯一（1 条）。
- B 查询：输入 `PRQ` → 真实请求带 `search_term`（域仍含 `business_category_id.code` 业务域）
  且 16→12 行；清除后恢复 16 行。
- C 排序：点“申请付款金额” → 真实请求 `order: "amount asc"`，首行金额 0.00/5.00/10.00/12.00
  实际升序（修复前同一操作被静默丢弃）。
- D 真实翻页：每页 10（真实 `{limit:10, offset:10, order:"amount asc"}`）→ 第 2 页为不同记录集合
  → 打开该页记录（URL 携带 `list_offset=10`）→ 返回后仍第 2 页、记录集合一致。
- E 窄屏 390×844：官方组合与官方容器仍在；无整页横向溢出（表格未被迫横滚）；单一纵向滚动属主
  （`MAIN.router-host`）；分页/页脚可用；未捕获 JS 异常 0。

**旧路径基线**：`tpl06a-list-before-*.json`（改造前的同一旅程）记录旧状态：
`data-list-composition="legacy-list-surface"`、无官方容器，且 C1/C2 复现上面的静默排序缺陷。
旧结果保留，不覆盖。

**回归**：`standard_collection_composition`（65 cases，含新增的 `payment.request` 用例）、
`list_order_field_contract`（14）、`collection_view_semantics`、`product_page_pattern`、
`page_pattern_reference_parity`、`collection_action_toolbar`、`adopted_form_validation_identity`
（46/46）、`verify.frontend.typecheck.strict`（exit 0）全部通过；`make ci.local.iteration` PASS。

### 候选与运行来源

- 源码：HEAD `8adfff9e`（`27098f36` 排序契约修复 → `8adfff9e` 付款列表接管）。
- 产物：`sce-offrepo/artifacts/tpl06a-20260929/dist`，入口 `/assets/index-D84RQvtG.js`
  （sha256 `57ad4572…`）；构建时间 15:25 晚于最新源码 mtime（15:23），无漂移，只构建一次。
- 运行：`:5180` pid `1532369`（`STATIC_ROOT=…/tpl06a-20260929/dist`，代理 `:18082`），
  替换上一候选的 `tpl05a-20260929` 服务（未新增端口、未删除旧产物）；`:5176/5178/5179` 未动。

### 剩余缺口（不得夸大）

- **官方组合的分页只在本入口取证**；试点列表 `project.project` / `sc.general.contract` 在验收角色下
  受管可见记录 3/2 行，最小页长 10 仍单页——该缺口保持**受管数据量**限制，未造数据。
- **付款表单仍非官方表单组合**：`payment.request` 不在 `STANDARD_FORM_COMPOSITION_PILOT_MODELS`，
  表单侧仍 `legacy-form-section`。同一业务流程目前是“官方列表 + 旧表单组合”，已登记为有意的范围不一致，
  不写成“全流程已接管”。
- 排序白名单的其余宽松处（例如无 `sort_field` 声明的显示列仍会被当作可排序字段发出请求）保持原状，
  未在本轮扩大处理范围。
- 四项 `style_system.guard` 欠账、`render_semantic_ready_guard.py`、`verify.list.surface.clean`、
  `no_new_any_guard` 仍独立记账；业务矩阵未升级整行；未重跑 89 入口/全站发布门禁。

## WEB-LC-01：标准列表配置闭环（2026-09-29，窄范围批次验收完成）

以下准备阶段记录保留；最终续跑结果与限制见本节末尾，不将历史阻断视为当前状态。

续跑基线 `e877afcc18cd7b5d2556e8053a64c4f93bda3e1b`，分支
`feature/web-official-template-adoption`，开始时工作区干净。本增量只准备定向工具，
**尚未取得真实配置发布、生效、恢复的浏览器结果**，不进入页面类型下一批推广。

- Formal Product Layer / Layer Target / Module：P4，既有低代码变更集浏览器验收入口、
  `frontend_acceptance_runtime.sh` 与 `make/runtime_ops.mk`。配置本身属于 P3 的临时验收配置；
  不沉淀客户偏好，不修改 P0/P1 产品实现或业务事实。Why Here：绑定既有环境并验证现有 API；
  Why Not Elsewhere：验证脚本不得成为配置或页面呈现的产品权威。
- 范围：付款申请 menu 545 / action 775 / `payment.request` 普通列表，当前公司下
  `fixture_role_config_admin` / `business_config_admin`，只改变 `name` 列标签，
  经既有 change-set stage/validate/publish/rollback 完成闭环。旧配置不覆盖；独立临时 target key
  和 token 在发布前保存，回滚停用本次新增配置，保留平台审计历史。权限及有效契约仍由后端决定。
- 身份：内部隔离验收租户（非生产客户库、非控制库、非行业目录），local acceptance profile，
  project `sc-fe-r2-p1-01`，DB `sc_frontend_acceptance`，filter `^sc_frontend_acceptance$`，
  filestore `sc_fe_r2_p1_01_odoo:/var/lib/odoo/filestore/sc_frontend_acceptance`；
  不新建 fixture、账号、凭据、数据库、端口或卷。既有 fixture 只读复用，禁止业务 create/write/unlink。
- 后端证据复用：容器 source `23f11f426880585ca307544545c9bf9c01245b42`；
  原 clean source fingerprint 与当前 `addons` 输入相同，经入口确定性核对，不改写旧回执。
  前端复用 TPL-06A 的 5180 产物；核对现有 listener/proxy、入口摘要及源码差异，
  不重新构建、不全文件 HTTP 比对。测试脚本变化不影响已有产品产物。

### 本批结果索引

| 层 | 命令/观察 | 结果 | 归因/下一步 |
|---|---|---|---|
| L0 | preflight、`git diff 23f11f4 HEAD -- addons`、既有 5180 listener | passed；clean 起点，后端产品输入无差异 | 后续 dirty scope 仅 P4 工具及本记录 |
| L1 | `make ci.local.iteration` | passed；策略测试 16，L1 only，无交付回执 | 工具变更不扩大产品回归 |
| L1 | `node --check frontend/apps/web/scripts/standard_list_lowcode_loop.mjs`、`bash -n`、`git diff --check` | passed | 定向工具可解析 |
| L2 | `make verify.business_config.standard_list_loop.unit` | passed，7 tests | 发布不确定先回读；冲突不强制覆盖；未尝试发布的失败草稿清理；在途发布即使读到旧 ready 也不得 discard |
| L3 前提 | `make acceptance.runtime.preflight`；定向入口 resource/source 核验 | passed | profile、精确 DB/filter/卷、后端输入可复用 |
| L3/L4 | `make verify.business_config.standard_list_loop` | failed，凭据前置拒绝；浏览器及配置写入 not_run | environment prerequisite：缺少既有 `SC_ACCEPTANCE_FIXTURE_PASSWORD`，未重试、未重置 fixture |
| L5 | Quick、发布、远端 CI、合并、部署 | not_run | 本地迭代范围；闭环未完成，禁止生成交付结论 |

定向工具默认只读，显式 `WEB_LC_APPLY=1` 才执行已授权临时配置写入。凭据从既有私有权威注入，
不得写进仓库或报告。报告位于既有 `artifacts/frontend-web-fix-20260928/web-lc-01-<run>/report.json`
（目录 0700、报告 0600；包含精确恢复 token，禁止公开上传）。请求失败先回读同一变更集状态，
已发布走同一幂等回滚请求，仅未尝试发布的本次草稿可放弃；发出发布请求后即使读到旧 ready，
也不能据此推断事务未提交。未知状态/冲突/恢复失败均保留恢复身份并报告，不推测性 discard。
验证有效契约标签、真实表头、服务端查询和返回记录摘要，恢复后与基线比较；不以配置存储成功代替页面验证。

独立 B 线复核发现“发布失联但读到旧 ready 时 discard”的恢复竞态；工具已增加
持久化 `publish_attempted` 标记并拒绝此类推测性清理，新增第 7 项失败注入测试通过。
本次 L2 仅 7 项工具测试，不计作真实页面用例；产品源码未变，沿用上一批产物和页面证据，
这些证据不代替本批尚未执行的配置闭环。

下一步：既有验收凭据就绪后先运行默认只读入口，再用 `WEB_LC_APPLY=1` 运行同一入口；
只有真实生效、恢复回读及独立复核通过后才能记为批次验收完成。
回滚代码：撤回本 P4 增量；运行时恢复：仅本次变更集 token 的平台 rollback/discard，
不得删除其他草稿或直接改配置表。批次未完成｜主线未集成｜目标环境未部署｜用户交付未验收。

### 凭据补齐后续跑与收口

用户提供既有 `/tmp/wf_check_fixture.env` 权威来源后，以环境变量注入口令；不记录口令、不建凭据文件、
不重置 fixture。执行基线 `e41e25e1b7c71ddb24885859385db5da7b814daa` 加本批工具 dirty scope；
产品源码和 TPL-06A 产物不变，继续使用 5180 → 18082。修改仅限工具的配置作用域、
业务事实比较和截图留存，原 L1 的产品/环境输入不变；修订后非零 L2 8 项全部通过。

| 原始证据（均在 `artifacts/frontend-web-fix-20260928/`） | 结果与归因 |
|---|---|
| `web-lc-01-d3f6c76d-44e9-44d7-b93a-b979fc64b0cd/report.json` | 默认只读 passed；真实 fixture_role_config_admin 登录及 system.init/contract 启动链、官方列表身份通过，无配置写入 |
| `web-lc-01-1534cbcc-d95e-4630-b6ca-5b3d383ba3bc/report.json` | failed / rolled_back；P4 工具误把登录角色当成目标 role_key，普通列表配置未被选择；有效契约标签恢复回读通过 |
| `web-lc-01-ab7da385-ded3-418a-8202-72d570b4b2da/report.json` | failed / rolled_back；标签已在契约与页面生效，但 P4 比较了整个显示投影摘要，不能据此判定业务事实变化；恢复通过 |
| `web-lc-01-93fc22b0-578f-460c-9d2f-03a27b387c17/report.json` | **passed / rolled_back，10/10 具名断言**，另有记录 ID、固定业务字段、查询上下文和恢复深比较全部通过；浏览器异常 0 |

修复依据：现有 `ViewOrchestrator.compose` 的普通列表路径未传角色限定，配置工作台的角色范围
也不同于登录身份。定向工具改为公司 8 / action 775 的普通列表覆盖，`role_key=''`，仍由配置管理员
认证并由平台执行配置权限；不扩展业务授权。第二处修复将显示响应与业务事实分开：同一业务域、
公司/allowed_company_ids、排序和分页下，前后返回 **20 条相同有序 ID**；额外通过真实 `api.data`
固定读取 `id/name/amount/state/write_date`，摘要一致，任何缺失字段、空集、非法/重复 ID 均失败。

最终运行命令：从既有私有环境加载口令后执行
`WEB_LC_APPLY=1 make verify.business_config.standard_list_loop`。
每次失败均先完成恢复，再依据具体工具输入修复重跑；未重试相同失败。无业务写入、无模块升级、
无新构建或服务替换。三张截图位于最终证据目录的 `before.png`、`published.png`、`restored.png`；
发布时编号表头为本次唯一标记，恢复后为“单据编号”。恢复后契约标签与原基线深比较一致，
页面表头、查询上下文、有序记录 ID、固定业务字段摘要也与原基线一致。

独立 B 线复核已读取最终及两次失败报告、核对当前工具代码，结论为窄范围内未发现阻断。
**范围限制**：这是现有配置 API → 有效契约 → 官方列表消费 → 回滚闭环；不是配置工作台 UI
编辑操作验收，不是角色定向列表配置、全角色权限或全部低代码能力验收。发布期间有效投影还出现
selection 标签与未呈现字段数量差异，不能声称“整个契约结构不变”或“所有必要能力均已验证”。
该范围差异留给后续页面类型推广的能力核对，不用静默回退或修改规则掩盖。

下一批按既有 `product-page-patterns-v1.md` 推进页面职责/能力分组采纳与旧路径退出；
不再新增模型专属列表。本批窄范围验收完成｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## FE-TPL-07：按页面类型默认接管（2026-09-29，本地批次收口）

基线 `fc0afcb32cd7864f4495f5c60322ac7d26193391`，既有专题分支与工作树，开始 clean。
P0 / frontend renderer / 标准呈现采纳机制：平台通用页面职责决定组合，不承载施工、客户或角色业务规则。
P4 仅补既有 acceptance 入口的固定 5180 预览生命周期及只读定向探针。既有 local profile、
sc-fe-r2-p1-01 / sc_frontend_acceptance / 精确过滤器与固定卷、fixture 权威和 18082 后端全部复用。
不改 P1/P2/P3 数据或配置，不升级模块；当前候选身份为上述 HEAD 加显式 dirty scope，不称 frozen。

边界与实施：三个 standard composition selector 改收页面职责，删除模型白名单；
ListPage 有数据/空态共用 ProductListSurface，旧透传 DOM 分支退出；ContractFormPage 的主表、
主从办理共用既有官方表单引擎和一次保存校验。只读详情增加 section 能力判断：集合、附件、
专用 renderer、未知类型及设计模式保留原控件并记录 reason，不能降为文字或计作 descriptions 接管。
影响普通列表和通用记录页；专用工作表/层级规划/看板不因名称相似自动接管。

先决诊断：独立 B 线确认 WEB-LC 列减少为 P4 输入语义问题：`tree.columns=[name]` 在 V2
是完整列权威（`ui_contract_v2.py:2961`），并非单字段 patch。可选隐藏列当时确实退出配置候选，
原探针已回滚恢复。因此不扩大旧“标签闭环”结论；不改后端既有完整替换规则。
无运行时配置变化的页面类型推广与该输入独立，可以继续；今后标签安全性须完整列能力比较。

验证顺序：L0 身份 → L1 iteration/语法 → L2 采纳策略、真实官方引擎、异步身份、集合/动作及严格类型
→ 一次定向构建与 L4 代表页。L3 模块升级/fixture reset 不适用（产品后端和数据未改）；
L5 Quick/发布/远端 CI 不运行（本地迭代）。L1 iteration 已通过；L2 当前通过：form 94、collection 69、
真实引擎 74、异步保存身份 46；集合语义 18+36、动作 6+11、页面模式 12+5、模板对齐 15；
strict typecheck 通过。P4 固定预览身份测试 5 通过。保留原始终端输出及 `/tmp/tpl07-iteration.log`，
后续只重验被实际修订影响的结果。

本批登记的增量 Make 入口：`frontend.standard.preview.build`、`frontend.standard.preview.up`、
`verify.frontend.standard_page_type.browser`、`verify.frontend.standard_preview.unit`。
仅复用已授权 5180 → 18082；构建至既有仓外证据根下 `tpl07-20260929/dist`，保存 build-identity.json，
绑定源 HEAD/dirty frontend 输入及入口摘要；源码未变重用产物。替换预览前核验唯一 PID、所属用户、
static-server 命令、旧 tpl06a/current tpl07 目录、端口和 proxy；未知 listener 拒绝停止。
旧产物保留，新启动失败尝试恢复旧目录。5175/5176/5178/5179 与数据库生命周期均不触及。

代表页结果在下表统一收口；回滚为本批 P0 提交及保留的先前预览产物。
全部入口与目标环境交付不在本批证据范围。

TPL07 代表页审查修订：原生 readonly slot 是通用格式化呈现，不能整体列为专用能力。
仅透传该 slot 至 descriptions 普通值分支，保留关系/HTML/办理动作优先级和集合、附件等排除；
付款详情旧截图未证明 facts 接管，修订使该结果失效，需定向补验。为保留首轮产物与证据，
修订候选构建登记为 `tpl07-20260929-r2/dist`，仅替换已验证的 `tpl07-20260929/dist` listener。
这是一次具体缺陷修复所需重建，不重跑列表、编辑或全旅程；首次付款/合同列表与客户空态证据沿用。

### TPL07 统一结果索引与证据复用

原始报告均在 `artifacts/frontend-web-fix-20260928/`，失败报告不重标通过：

| 原始报告 | 结果与本批使用范围 |
|---|---|
| `tpl07-1790668835237/report.json` | 探针 failed，锁定数据库构建只有两个可编辑登录输入，第三输入定位超时；尚未进入产品断言 |
| `tpl07-1790668884648/report.json` | 20 项通过后探针因客户菜单被误认为 link 而 failed；沿用付款真实第二页/返回同集、主从引擎与明细、合同列表结果；旧详情结果由 r2 代替 |
| `tpl07-1790669007131/report.json` | 修正为真实菜单搜索，additional 分支 passed 3 项；非旧试点 res.partner 客户空列表采用官方卡片，无业务写入 |
| `tpl07-1790669293555/report.json` | r2 详情探针 failed：7 项已过，公司字段所在 mixed section 是专用控件扩展，探针错误要求其进入 descriptions；未改产品，只修正该定位断言 |
| `tpl07-1790669324381/report.json` | **r2 detail passed 15 项**；付款非零 facts 与非零明细、明细扩展隔离、原公司值、窄屏；合同非零 facts；异常与业务写入均 0 |

r2 事实文本回读包括既有往来单位户名、开户行、账号及匹配提示，slot 格式与取值保留。
付款事实/专用混合 section 保留整节扩展，未把 page marker 当作整页 descriptions 完成。
原列表、编辑、空态测试所依赖的代码与 backend/profile/fixture 输入未变；r2 仅修改 readonly
事实普通值插槽及能力判断，故明确沿用首轮相应检查，不宣称整个 failed 报告通过。

L1：`make ci.local.iteration` passed，`/tmp/tpl07-iteration.log`；后续只读插槽小修未改变
该静态策略输入。L2 修订后 `make verify.frontend.standard_collection_composition.unit
verify.frontend.standard_preview.unit verify.frontend.typecheck.strict` passed（69 + 5，strict typecheck），
日志 `/tmp/tpl07-detail-check.log`；其他前述非零 L2 输入未变，沿用本批原结果。
L4：`make frontend.standard.preview.build` 初次产物与 r2 保留，日志 `/tmp/tpl07-build.log`、
`/tmp/tpl07-r2-build.log`；`make frontend.standard.preview.up` r2 成功，
`TPL07_SCOPE=detail make verify.frontend.standard_page_type.browser` passed，
日志 `/tmp/tpl07-detail-browser-r2.log`。5180 当前入口 `/assets/index-R2g4OV5o.js`，
SHA256 `fabee65071492ce6409578f74758de5625e34861c5fe148251f3a0152540f444`，
源基线仍为 `fc0afcb32cd7864f4495f5c60322ac7d26193391` 加本批 frontend dirty scope；
后续仅提交不会改变相对该基线的构建输入摘要。build-identity.json 为真实构建身份，不伪写新 SHA。

B 线独立复核当前同一范围：未见新增保存授权/双引擎/集合吞控件阻断，已核验 live listener
绑定与非零能力断言。代码退出范围：标准列表旧透传容器及三个模型白名单删除；详情普通事实
使用官方组合，集合/附件/专用控件仍由同一契约扩展承担，设计编辑及专用页面仍明确除外。
本批未验证全部 89 入口、全部写入或每种专用能力；未升级业务矩阵整行。

既有 style_system 4 项、render_semantic_ready 旧期望、no_new_any/list.surface.clean 待收口项继续
保留在此结果索引，禁止据本批结果宣称发布门禁全部通过。低代码完整列能力比较进入下一批；
无本批数据库配置或业务写入，无推送/合并/目标部署。
**批次验收完成（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。**

## WEB-LC-01B：完整列能力保留（2026-09-29，进行中）

基线 `bc630039` clean。P4 / 既有配置验收工具，修正临时测试配置输入和预发布检查；
不更改 P0 full-list 替换语义，不把测试标签固化为 P1/P2 默认。复用同一受管库与 fixture，
数据库角色/卷/过滤器沿用 TPL07；配置写入串行，仅拥有本批 token，可权威回读及 rollback/discard。
先只读采集完整 normalized baseline，再新增预发布全能力比较与非零失败注入测试；
未知语义差异必须在 publish 之前关闭，不以成功回滚证明发布安全。
初始诊断阶段禁用 APPLY，随后改为完整预发布比较决定是否允许 publish；只读入口复用 TPL07 真实构建身份。
L1 节点语法、L2 定向工具测试 → L4 只读基线；后续配置候选预览受上述检查阻挡。
产品源码不变，不构建；不升级模块/fixture，不重复已过业务旅程。

### LC01B 定向执行结果（保留真实阻断）

P4 改为完整 profile 列全集+独立非零 sequence，只为 name 写 label；不写 visible，避免
`false` 删除字段、`true` 强制展开。完整 table widgets 顺序必须与 profile 一致，拒绝空集、
重复、隐藏/事实列不覆盖，不取并集掩盖权威冲突。比较完整 page/layout/status/action/data/runtime/search
及 meta 的版本/authority/trim，只规范明确的请求ID/摘要和顶层 name table widget、descriptor、
listProfile.column_labels.name 标签；嵌套同名字段不豁免。

L1 `make ci.local.iteration` passed（`/tmp/lc01b-iteration.log`）；L2
`make verify.business_config.standard_list_loop.unit` **13 tests passed**（`/tmp/lc01b-unit-final.log`），
新增完整列/顺序/隐藏映射/权限与未知结构漂移/嵌套同标签拒绝测试。节点语法与 diff check passed。
B 线复核预览 token 的 owner/company/database/action/menu/view/role 绑定及完整投影比较，没有发现
阻断本次受管草稿验证的缺陷；采纳其建议收窄标签豁免范围。所有配置操作均串行。

| 原始证据（既有 artifacts/frontend-web-fix-20260928 下） | 结果 |
|---|---|
| `web-lc-01-ba094467-4d94-483c-be03-ba1f37ecfab6/report.json` | readonly_passed / not_needed；3项，无配置写入；baseline-contract.json 留存完整基线 |
| `web-lc-01-69db0ba3-0ab1-4046-8c5d-0da45a8f9379/report.json` | **failed / discarded**；到预览6项通过，完整能力比较拒绝后续 publish；没有 publish_attempted，完整有效契约回读与基线一致 |

命令分别为 `make verify.business_config.standard_list_loop` 与
`WEB_LC_APPLY=1 make verify.business_config.standard_list_loop`，既有私有 env 注入口令。
后者日志 `/tmp/lc01b-preview.log`；失败后没有原样重跑，未发布到有效配置，未修改业务记录。
新证据绑定 `bc630039` 加本批 P4 dirty scope，前端仍为 TPL07-r2，未重建/重启后端。

**实际阻断**：完整22列、13隐藏列已保留，但草稿令
`preference_policy.allow_visibility/allow_order` 从 false→true，locked_columns 从22列→空；
还注入 nativeWidget/cell_role/tone_by_value 与 column_policy，部分 selection 从tuple变object。
其中显隐/顺序权限及锁定列变化具有行为意义，不能统一当作“正常投影”豁免。
责任定位为 P0 `ui_contract_v2.py::_enforce_business_list_config_projection` 的强制 preference
覆盖及业务列表投影对 schema 的补写；需独立收口完整配置与标签修改的语义边界，不能在 P4
放宽断言或前端绕过。当前工具已具备发布前阻断与恢复保护，但 **LC01B 业务验收未完成**。
既有 TPL07 页面类型批次结果不受影响，普通列表/表单默认接管保持；后续最早有效步骤为
P0 定向语义修复/契约测试，禁止直接重复浏览器或宣称总接管完成。

本批工具修正完成，配置完整能力闭环 blocked｜主线未集成｜目标环境未部署｜整体用户交付未验收。

B 线进一步定位：P1 `smart_construction_core/core_extension.py:1342` 见权威列表配置即提前返回，
跳过正式 action-bound 原生 schema 及其 :1467 的锁策略；P0 `ui_contract_v2.py:3174` 与 :364
又两次强制开启列偏好。`view_orchestrator.py:801` 不消费 tree.preference_policy/columns_schema，
因此补 payload 不能解决。下一机制批次须保留 P0 全量列集选择语义，同时让 P1 标准 schema/锁策略
先形成稳定基线，配置只覆盖显式职责；先后端定向测试，后受管预览，不再试错式发布。

## WEB-LC-02：配置与正式列表基线交接（2026-09-29，进行中）

基线 c8ad8d66 clean，沿用已有分支/工作树/验收资源。本批唯一目标：全量配置列集仍权威，
未声明改变的正式原生列语义和个人偏好锁不因配置存在而退出。P0 smart_core 最终投影负责保留
已有策略；P1 smart_construction_core 正式列表既有 hook 提供 action-bound 原生基线，再调用
现有 ViewOrchestrator 应用显式覆盖并按权威列集精准裁剪。施工金额/锁策略仍在 P1；P4与前端
不实现语义。影响已登记正式 list action + 权威配置路径，无配置正式列表和非正式列表应保持。
不新增 public intent/字段/schema、不修改模型/权限/fixture；仅 Python handler/hook 修复，
运行时需重启清除进程缓存，不需数据库 -u 或数据迁移。P0/P1 提交分开，回滚按相反依赖顺序。
L0身份→L1语法/iteration→L2非零P0/P1定向测试→受管后端重启→既有草稿预览。
前置未通过不得运行浏览器；前端产物未变不重建。发布/主线/目标交付均未执行。

LC02 开发验证：L1 iteration passed `/tmp/lc02-iteration.log`；L2
`make verify.business_config.formal_list.unit` passed **111 P0 + 51 composer + 5 P1 hook tests**，
`/tmp/lc02-unit-r2.log`。P1 测试执行真实 shipped hook 与真实 composer，ORM仅作有界替身；
完整 Odoo TransactionCase suite 未运行，不把纯测试冒称数据库集成。Python语法/diff check passed。
首次P1测试暴露 visible:true 未传为optional-show，已由P0列策略就地修复；未声明显隐仍继承native。
B线发现个人顺序在锁前进入fact_columns，已将direct配置个人偏好处理推迟至最终约束之后。
合法非native扩展schema（sort/value/readonly/required/selection）保留及显式覆盖均有非零测试。

本次运行库判定：TARGET_DATABASE_ROLE=isolated_acceptance_tenant；TARGET_TENANT_ID=sc_frontend_acceptance；
TARGET_ENVIRONMENT_ID=sc-fe-r2-p1-01/local；非platform-control/industry-catalog，隔离模拟客户租户；
不允许真实客户业务数据，允许既有fixture。精确dbfilter `^sc_frontend_acceptance$`，filestore为
受管 `sc_fe_r2_p1_01_odoo` 卷内该库目录；每次入口重新验证身份，不新建/复制/reset库或卷。
受管后端仅重启Python，不做模块升级；前端5180/TPL07-r2原产物复用。运行态验证pending。

LC02 首次运行：P0 `41737a8a`、P1 `e37cd160`、测试 `7be3cce8`；工作树clean后
`make backend.acceptance.up` 成功替换旧revision后端（`/tmp/lc02-backend-up.log`），库/卷未改。
`WEB_LC_APPLY=1 make verify.business_config.standard_list_loop`：
`web-lc-01-06b41f95-ec23-4ed3-97f2-759c09ab35dd/report.json` failed/discarded，无publish_attempted，
恢复全契约一致。此前229叶节点差异消除，剩余仅listProfile的精确strict配置来源column_policy及
sourceAuthority.source_key。原所有显隐/顺序/锁/schema/selection/映射/actions/data/runtime等深比较一致。
后续必须证明来源标记允许差异边界；不能丢弃任意policy、sourceAuthority或profile再比较。

### LC02 真实闭环收口

来源差异审计：column_policy在后端确有strict列投影意义，不能称作任意无行为元数据。
本次仅draft/published允许精确 `{mode: strict, reason: business_list_config_contract_authoritative,
owner_layer: ui.business.config.contract.view_orchestration}` 三键对象及对应source_key，
验证后规范为相同基线以比较所有有效能力；未知值/额外键拒绝。
baseline/restored必须无该policy、source_key为list_profile，配置来源残留即恢复失败。
P4失败注入测试新增阶段隔离、额外键/其他mode/错误来源拒绝，
`make verify.business_config.standard_list_loop.unit` **14 tests passed**（`/tmp/lc02-tool-unit.log`）。
未改变P0/P1后端代码，未重启第二次、未新建前端构建。

最终命令 `WEB_LC_APPLY=1 make verify.business_config.standard_list_loop`，日志
`/tmp/lc02-loop-final.log`；原始报告：
`artifacts/frontend-web-fix-20260928/web-lc-01-bb8af700-b57b-4832-8a65-458a5b1f0810/report.json`。
**passed / rolled_back，13具名断言通过**；此外草稿、正式发布、恢复有效契约严格比较均通过。
原22列、13隐藏列、显隐/顺序禁用和锁定集合、widget/selection/金额映射、actions/status/
query/domain/context/权限及runtime能力保留；发布期间仅目标标签与精确配置来源发生预期变化。
20条有序ID、固定id/name/amount/state/write_date摘要、实际查询上下文相同，browser errors=0。
回滚后完整能力/原生来源以及可见表头、请求、记录集与原基线一致；所有配置已恢复，无业务写入。
`before.png`、`published.png`、`restored.png`保存在同一原始目录；保留首次failed/discarded证据。

真实后端绑定 clean `7be3cce84ba10a05e5e0240bc176a62cfd6b4a62`，最终工具运行身份为该HEAD+
本批P4工具dirty scope；前端为已验证TPL07-r2，原build receipt不改写。后续工具/文档提交不改变
本次产品输入，不需为换SHA重跑。风险回滚：P1后P0逆序撤回相关提交，受管backend重启；无schema/
数据迁移。先前LC01B的行为漂移阻断已由本批关闭，但历史失败报告不改写为passed。

范围：配置API→有效契约→官方标准列表→完整回滚已验证；不是配置工作台UI全旅程、全部模型/
全部角色配置能力或全89入口验收。TPL07标准页面默认接管不变；原style_system等强制门禁仍待
各自收口，不能据本批宣称总体官方接管/发布/交付全部完成。
**批次验收完成｜主线未集成｜目标环境未部署｜整体用户交付未验收。**

LC02 最终B线已核对同一候选报告及阶段化来源比较：范围内无剩余阻断，正常和异常恢复均不豁免配置来源残留。

## WEB-GATE-01：强制门禁检查点校正（2026-09-29，进行中）

基线 ebd069bf clean；P4 / scripts.verify / 门禁有效性。目标仅修正已迁移契约消费者后的
两个失效字面检查，并验证破坏真实链路仍失败。产品层无改动：列表现消费canonical V2 store，
表单render-profile需经能力约束；守卫不得要求已退役API或旧的直接赋值。
不删除检查、不增加白名单/阈值、不更新any或尺寸基线。L0身份→L1 iteration/语法→L2守卫
失败注入与真实门禁。无产品输入变化，跳过构建、运行态/数据库/浏览器，沿用已有LC02/TPL07证据。
clean HEAD下首次复核 no_new_any：19文件超基线（`/tmp/web-gate-any-baseline.log`），包含注释误计及
真实新增any，后续必须分别修正计数与类型；当前不改该门禁、不宣称通过。

WEB-GATE-01收口：`make ci.local.iteration` passed（`/tmp/web-gate-01-iteration.log`）；
`make verify.page_contract_gate_wiring.unit verify.list.surface.clean verify.render.semantic.ready`
全部passed（`/tmp/web-gate-01-results.log`），6项测试，生成的既有两份报告同步。
B线复核无放宽：AST检查请求→能力→只读fallback及委托，列表检查真实canonical调用并拒绝旧resolver。
行为测试仅证明编排（能力函数替身），不冒称权限计算运行态验收。产品及构建/数据库输入未变，
沿用TPL07/LC02原证据。本批两项门禁已关闭；no_new_any及style_system仍待收口。
批次验收完成（两项守卫）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

后续类型诊断（只读，不计通过）：用现有TypeScript AST只统计script内AnyKeyword，原19项中
实际超过现有数值基线的为6个文件：one2manyColumnOptionsRuntime、useRecordCollaborationPresentation、
useBusinessConfigPublishLifecycle、useBusinessConfigRemediationLifecycle、useBusinessConfigScopeLifecycle、
useBusinessConfigWorkbenchBootstrap。其余报告主要来自注释/禁用注释的词法误计。
此诊断未改guard或baseline，不能替代no_new_any门禁。下一步需为6个真实依赖边界补明确类型，
再处理词法计数对注释的误判；禁止把Record<string, any>机械替成不安全断言或提高基线。

## WEB-TYPE-01：真实类型依赖与扫描语义（2026-09-29）

基线 b43572ec clean。P0/frontend renderer：只补6个边界的精确依赖类型，复用API/事件/组合返回类型，
不改变业务处理与授权；P4扫描只计算显式类型语法，不把注释/字符串中的词当作类型。
不提高基线额度，不增加unknown索引签名/断言来替代类型。范围为上述6文件、必要显式调用传参、
扫描工具及负例测试。L1 iteration/语法→L2严格类型与影响范围非零测试；若运行时代码未变，
以擦除类型后的等价性复用页面证据，不为纯类型变更构建/写配置。风险回滚本批提交即可。

WEB-TYPE-01复核修正：B线发现旧regex额度包含注释，不能直接当作AST额度使用。
以原baseline提交 ea0170d2652188083146c5423ed9dcbb20a170d7 的源码重算，逐文件取
min(原额度, 原源码AST计数)，同一baseline总额度55→36；记录metric/source_commit。
没有从当前源码刷新额度；第6项扫描测试逐项验证来源和收紧值，并覆盖“历史只有注释、
当前新增真实any必须超限”。首次负例路径误写pages而非app，修正测试路径后6/6通过。
收紧后揭示useRecordRelationships布局回调还有一处真实any，已接入既有LayoutNode类型；
父级历史Record<string, any>仍保留，不宣称完全无any。B线复核原额度阻断已关闭。

结果索引（候选 b43572ec + 本节P0/P4 dirty范围）：
- L1 `make ci.local.iteration` passed，`/tmp/web-type01-iteration-final.log`。
- L2 `make verify.frontend.explicit_any.unit` passed 6/6，`/tmp/web-type01-any-final.log`；
  同日志随后旧候选guard发现关系回调超限，是实际失败，已由上述类型修复解决。
- L2 `make verify.frontend.no_new_any_guard verify.frontend.typed_dependencies.unit verify.frontend.typecheck.strict`
  全部passed，`/tmp/web-type01-types-final2.log`；guard检查698文件、显式any25、剩余历史额度11；
  依赖类型负例6项。首次类型负例执行器因/tmp配置不能定位node/vite类型而失败，
  已改为复用仓库已安装的绝对类型路径，未改变产品类型检查规则。
- L2 `make verify.frontend.native_collaboration_presentation.unit verify.frontend.professional_detail_collection.unit`
  passed，`/tmp/web-type01-behavior.log`：协作呈现断言、集合matrix=6/domain=7、Python 10+37测试。
- 7个修改TS文件类型擦除后与源HEAD逐字节一致，`/tmp/web-type01-runtime-equivalence.json`；
  Vue调用只删除被调函数从未读取的replaceWorkbenchQuerySilently参数。
  最后关系布局类型修正重新核验7文件等价，行为测试可沿用。
- L3/L4不运行：无服务端/数据库变更，前端执行逻辑未变，不重复构建或浏览器旅程。
  5180仍为TPL07-r2原构建，保留其原receipt身份；不冒称已加载当前源码版本。
  TPL07/LC02页面证据按上述输入影响分析沿用。L5未进入，无推送/合并/部署。

剩余强制门禁：style_system既有4项（关系选择z-index、表单与两处action文件尺寸），
后续按所属呈现职责处理，不增加尺寸阈值。本批不升级89入口业务矩阵或整体交付状态。

WEB-TYPE-01批次验收完成（类型边界与同口径no-new-any）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## WEB-STYLE-01：共享表单职责与样式门禁（2026-09-29）

基线 cb06a004 clean。Formal Product Layer=P0；Layer Target=frontend generic form renderer；
Module=frontend/apps/web。平台通用呈现职责，不属于P1业务/P2偏好/P3配置内容/P4业务补丁。
目标：配置字段交互退出保存处理器；原生动作状态映射归入既有动作适配器；页面返回接线归入既有导航运行时；
关系选择局部层级使用受管令牌。范围仅对应文件、直接类型/测试/令牌，不改变契约、权限、保存epoch、
数据身份、字段顺序、回退策略。不增加尺寸基线。L0身份→L1 iteration/style→L2严格类型、
保存身份/失败恢复、字段事件和返回导航相关回归；先验证代码再决定必要页面复核。无数据库写入。

实现收口：14个配置选择/显隐/拖放交互移到useRecordFormDesignerActions，明确36项依赖，
原保存owner612行。动作状态映射复用contractActionPresentation，避免牵动字段分发链；
页面返回接线进入useCreatedRecordNavigationRuntime，仍先确认未保存内容再读取实时路由/权威。
清理Page中11个已无消费者的类型导入。关系弹层底部操作令牌计算值保持1。
P0职责退出：原保存owner不再实现设计交互，Page不再重复返回接线；无第二状态或业务执行链。
尺寸/颜色/类型基线均未提高。

验证索引（cb06a004 + 上述P0实现及P4测试dirty范围）：
- L1 `make ci.local.iteration` passed，`/tmp/web-style01-iteration-final.log`。
- L1/L2 `make verify.frontend.style_system.guard verify.frontend.no_new_any_guard verify.frontend.typecheck.strict`
  passed，`/tmp/web-style01-final-static.log`；样式/token PASS，699文件显式any仍25，严格类型PASS。
  第一次style检查Page1901行失败；移除真实未使用的类型导入后通过，未提高1900限制。
- L2 `make verify.frontend.form_designer_actions.unit` passed6项，`/tmp/web-style01-designer.log`。
- L2 保存失败恢复首次failed（`/tmp/web-style01-behavior.log`）：旧harness未接已默认启用的
  官方校验入口，写次数为0。P4修正为真实createStandardFormValidationRegistry的合法无必填空集；
  未更改产品保存判定。`make verify.frontend.contract_form_save_failure_recovery.unit verify.frontend.record_form_return.unit`
  passed，`/tmp/web-style01-recovery.log`：4种失败恢复场景及13项返回测试（含确认拒绝和实时权威）。
- L2 独立受影响回归 `/tmp/web-style01-independent.log`：adopted_form_validation_identity46、
  adopted_form_engine_decision74、contract_error_business_ownership92、canonical_form_presenter177+10、
  professional_relation_field18+17及Python10+36全部passed；对应入口均为`make verify.frontend.<name>.unit`。
  同日志的旧12项return结果被上述13项替代，不重复计数。
- 确定性影响复核 `/tmp/web-style01-equivalence.json`：14函数正文、保存核心/返回对象、save epoch
  保护逐字一致。B线独立AST比较同样通过，无阻断。返回接线和动作映射有直接定向回归，token值同1。
  L3跳过：无后端/DB/配置变化。L4复用TPL07/LC02原页面观察，不重新构建/浏览器全程；
  当前源码不同于5180的TPL07-r2原构建，运行预览身份仍按原receipt，不冒称本批已加载。
  L5未进入：仍是本地迭代，无推送/合并/目标环境部署。

- L2 `make verify.frontend.standard_form_composition.unit verify.frontend.standard_collection_composition.unit verify.frontend.native_form_action_presentation.unit`
  passed94/69/16，`/tmp/web-style01-compositions.log`。普通页面职责仍选择同一标准组合，旧路径未重启。
WEB-STYLE-01批次验收完成｜主线未集成｜目标环境未部署｜整体用户交付未验收。
已知list/render/no-new-any/style阻断已逐项关闭，不等同未运行的完整发布门禁通过。
下一阶段：统一候选的必要集成门禁与受管预览复核；专用页面例外继续按page-patterns登记，
不把专用层级/工作表强塞普通列表，不以模板接管比例替代正式89入口的业务交付验收。

## WEB-BOOT-01：由真实初始化契约驱动接管盘点（2026-09-29，进行中）

基线 ef346859 clean。用户明确扩大到登录→system.init→授权导航→页面类型的系统盘点与补齐。
P4只读观察复用验收库sc_frontend_acceptance、既有profile/fixture角色/5180→18082及构建receipt；
先观察已登记旧预览，不将source不一致的观察算当前候选验收。不创建环境/数据，不写业务或配置。
P0修复范围由实际契约与源码判定：登录呈现与初始化后共享页面，保留认证、权限、默认路由真源。
L0身份→L1/P4探针及非零单测→真实启动链观察→P0缺口修复→定向L2→一次稳定候选构建/复核。

WEB-BOOT-01真实来源：`bootstrap-inventory-1790671776437/report.json`首次取得三角色登录/system.init，
finance/contract_operator落`/s/workspace.home`；config_admin落projects.list，和role_surface.landing_path一致。
导航叶15/3/86，去重87，不把它替换正式89业务矩阵。旧登录form=1、officialForms=0；外壳均official。
按授权导航扩大后的`bootstrap-inventory-1790672013759/report.json`观察104个角色×菜单入口：
91个official-standard-list、6个official-standard-form标记、6个collection专用候选、1个配置工作台。
该文件是旧TPL07-r2诊断，不是当前候选验收：偏好读取、6次创建默认值读取和1次配置surface读取曾被
只读允许表拒绝，所致错误不归产品；usage.track也被阻止。菜单335/663的实际listProfile明确
hierarchical_worksheet/sheet_groups，454明确kanban；不是普通列表的旧实现遗漏。
完整观察已落盘，但外层Make最终failed：执行中的shell入口被本轮编辑，恢复读取时语法位置失效；
当前`bash -n`通过。保留观察原件、不把此命令记为passed，后续只定向复核工具限制和受影响页面。

P4探针修正轨迹：最初response事件读取body遭浏览器缓存逐出（failed），改route.fetch持有实际响应；
随后精确路径未匹配带query的API导致init缺失（failed），改匹配API路径并解析实际pathname。
独立复核指出写intent黑名单不足，旧全扫主动中止；采用明确read allowlist，未知请求fail-closed，
6项负例包含配置stage/discard/validate、非intentAPI和写操作拒绝。读取默认值、个人偏好、配置surface
分别核对后端handler后登记；候选启动另明确允许既有usage.track访问计数，业务/配置写仍不允许。
observed-identity仅允许原构建观察，仍验证登记listener/代理和产物摘要；candidate入口保持源码匹配检查。

P0落位：LoginView采用官方Login.vue的Form/FormItem/Input提交组合；Home/MyWork采用共享
ProductWorkspaceSurface的summary/query/main/actions/secondary卡片区域。参考仍为固定Starter快照，
未引入示例统计、模拟数据或角色推导。原业务适配/办理动作及登录→init→权威路由未改；旧Home私有
panel/header及MyWork外层编排退出。B线确认槽职责保留，发现的残留CSS逗号已修复为按钮flex:none。
相关guard以共享槽接线代替旧section类名，8项正反例；ScPanel检查迁到仍真实消费它的ApiKey页；
两个旧home guard对display_role的子串误判改词边界，真实role/role_code推导仍拒绝。

验证日志索引：
- L1 iteration最终基于r3记录`/tmp/web-boot01-iteration-r3.log`；早期iteration因已清理的空白失败保留。
- L2 strict typecheck/auth credential/auth surface：`/tmp/web-boot01-auth-feedback.log`passed。
- L2 workspace接线8例、home职责/编排/my-work/shared semantic/style/no-any：
  `/tmp/web-boot01-workspace2.log`的旧误判failed由`/tmp/web-boot01-remaining-guards.log`和
  `/tmp/web-boot01-tool-final.log`的passed替代；700源码文件显式any仍25，无额度增加。
- L2状态/事项呈现、活动页键盘/身份/保留、page-pattern12+5、真实表单引擎74：
  `/tmp/web-boot01-behavior.log`passed。P4预览6例及允许表6例、布局8例有各自日志。
- L4首次boot01产物在必填语义复核前未启用，保留；r2启用后空凭据真实检查failed：引擎阻断但
  错误信息未显示。`bootstrap-inventory-1790672596362`与`1790672664978`保留failure，后者DOM确认
  novalidate/required均有效，错误显示开关缺失。修复仅Login明确showErrorMessage=true，未更改共享
  wrapper默认和业务表单摘要策略；因此有依据构建r3，而非重复同一失败。构建日志
  `/tmp/web-boot01-build.log`、`/tmp/web-boot01-build-r2.log`、`/tmp/web-boot01-build-r3.log`分别保留。

- r3构建与L1/预览6项已passed，P0提交`b3d918bf`，加载entry `index-CWMKjz2r.js`，
  SHA256 `8cdd39c1fce3521e5e943da0885ece5973a6ede6189203d3d544f19fee169cc5`。
  `/tmp/web-boot01-up-r3.log`确认5180切换成功，后续仅P4/docs变动，不重建。
- r3首跑探针在关闭时出现route.fetch context disposed，未形成终态；保留
  `bootstrap-inventory-1790672966925`为未完成，不算passed。P4补异常脱敏与收尾等待；
  r3b到合同角色后无有界定位等待，主动中止，`bootstrap-inventory-1790673027623`亦非passed。
  已有财务桌面/390截图显示共享工作台可用，但不替代整轮结果。后续P4明确15秒定位/30秒导航
  超时、阶段日志、收尾前落盘，继续定位而非宣称产品通过。无业务写入、无新增构建。

- r3c `bootstrap-inventory-1790673173453`明确failed：合同角色普通列表容器已出现，
  但ui.contract.v2尚未完成时即断言。P4补networkidle后验证真实契约、route.fetch 15秒上限，
  防止异步请求无限拖住收尾；不修改产品契约消费。r3c终态已落盘，收尾进程中止。
  后续定向候选日志`/tmp/web-boot01-browser-r3d.log`；不得混用旧failed为成功证据。

### WEB-BOOT-01收口（本地批次）

- L4 r3d `bootstrap-inventory-1790673243161/report.json`保留整体failed，原因仅管理员
  `ui.business_config.coverage.scan`被只读探针拒绝。财务/合同分角色终态均零页面/请求错误、
  零拦截；登录官方必填提示→真实init→权威落地→标准列表→Home/MyWork双宽检查通过。
  各自本次列表菜单334/414均有唯一新增成功V2响应，终态复核与独立B线确认可复用。
- P4核对`BusinessConfigCoverageScanHandler`为查询投影后精确放行；bootstrap修复写仍拒绝。
  B线发现的收尾竞态一并修正：先等待回调，再断言errors；异常route主动abort；列表响应绑定
  本次导航新增契约和menu_id。工具策略6例passed `/tmp/web-boot01-policy-final.log`。
- 仅管理员受影响补验 `make verify.frontend.standard_bootstrap.browser`，环境
  `BOOTSTRAP_ROLES=fixture_role_config_admin`，`/tmp/web-boot01-browser-admin-final.log` passed，
  `bootstrap-inventory-1790673383007/report.json`：1角色登录/初始化/权威落地、当前列表326、
  Home/MyWork × 1440/390、10个定向导航；零未登记请求、零页面/请求异常。
  10页落盘另核对零alerts/item.error，所有专用renderer为ready。417重定向到真实
  `/admin/business-config`；其coverage扫描可能超过4秒观察窗口，未据此声称配置写流程已验收。
- 此次13个角色×定向页面与旧104入口观察分开：6个创建页官方表单；335/663层级工作表，
  454流程看板，702/703透视表；417专用P3工作台。它们有明确类型和职责，没有作为普通列表
  静默回退。授权导航仍为87去重入口，不升级正式89行业务矩阵。
- L1最终 `make ci.local.iteration` passed `/tmp/web-boot01-iteration-tools-final.log`；
  共享接线8例/布局guard及策略6例passed `/tmp/web-boot01-final-tools.log`（策略最终以上一日志为准）。
  类型、真实表单引擎、状态/事项/返回行为及预览6项复用上文成功结果，产品输入未再变。
  B线最终只读复核无代码阻断。P4/docs变化不改变r3产品输入，不重新构建。
- 当前预览5180为b3d918bf产品候选；本地后续工具/文档提交不改变产物。无业务/配置写入，
  无推送/合并/目标环境部署。登录会话和既有usage.track访问计数为已声明启动副作用。

WEB-BOOT-01批次验收完成（上述分角色有效证据组合），主线未集成、目标环境未部署、整体用户交付未验收。
已补登录和共享工作台呈现缺口，普通列表/表单/详情沿用TPL07标准路径。公共激活/找回挑战流程、
专用设计器/配置编辑器仍是明确保留范围，未冒称整个前端所有特殊页面已完成官方接管。

提交后预览复核：误直接调用identity被既有Make入口保护拒绝（无变更、非验收）；
随后使用`make frontend.standard.preview.up` passed，日志`/tmp/web-boot01-final-preview-reuse.log`
确认REUSED current 5180 listener，不重建、不重启。

## WEB-AUTH-02：公共激活表单接管（进行中）

基线91278229 clean；P0 frontend renderer / AccountActivationView。两处原生form迁已有
ScForm/ScFormItem，官方成功校验事件接原start/finish；保留原required/minlength语义（官方规则承接，novalidate避免双引擎）、
禁用/清理/上下文链。仅呈现所有权，非P1行业规则或P3配置变动。PasswordRecovery仅说明和返回，
不为接管伪造恢复写流程。范围不含专用设计器。L1 iteration→L2类型/auth/真实表单引擎及
受影响接线检查；无后端或DB写，L3升级跳过。L4仅在稳定候选按受管入口检验受影响页面，
不重复87导航或三角色矩阵。L5发布不进入；沿用单写者/B线只读复核。

WEB-AUTH-02当前结果：P0提交e58b9969；L1 iteration passed `/tmp/web-auth02-iteration-final.log`。
L2严格类型passed `/tmp/web-auth02-type-final.log`；auth surface/credential及表单引擎74例passed
`/tmp/web-auth02-focused.log`；本批实际官方引擎+源码规则/提交接线12行为例passed
`/tmp/web-auth02-engine.log`。start/finish/unmount逐字等价 `/tmp/web-auth02-equivalence.json`。
P4预览6例passed `/tmp/web-auth02-preview.log`。唯一构建22.47秒 `/tmp/web-auth02-build.log`，
受管up passed `/tmp/web-auth02-up.log`，5180加载auth02候选，旧boot01-r3保留可回退。

L4 `make verify.frontend.standard_public_auth.browser` **failed**：
`public-auth-1790673764790/report.json`，13项UI检查已通过，包括激活两阶段、短密码阻断、
模拟服务拒绝清空、双宽无溢出、成功后移除secret及恢复说明；最终返回登录超时。
所有API被拦截，零真实账号写；零pageerror/未登记请求。B线建议的短密码等待已限定到对应
ScFormItem的错误消息（不命中常驻说明）。不把模拟成功称真实激活验收。

新发现P0公共契约引导缺口：冷启动session.pageContracts={}，仅登录后的system.init填充；
AccountActivation/PasswordRecovery却依赖usePageContract中的open_login target。后端
`action_target_schema.resolve_action_target`正式定义了/login，但匿名阶段未投影到前端；
按钮因此无动作。不是本次表单替换造成，也不能以前端硬编码目标掩盖契约缺失。
本批保持verification_pending，不进入发布收口，不把已有13项改写为整轮passed。
下一最早步骤为P0公共页面匿名契约的生产/消费边界修复（仅公开页面、不得暴露授权导航/角色），
再对返回链定向补验；不重做74/12不受影响用例、87入口盘点或激活真实写入。

## WEB-AUTH-03：匿名公共契约引导（进行中）
基线c2a852c7 clean。P0 smart_core公共页面投影/前端session消费，修复匿名返回链；
既有builder/action target为唯一权威，只公开三页，不接收调用者profile/context，不开放system.init。
GET /api/v1/auth/page-contracts → {ok,data:{schema_version:1.0.0,pages}}；pages沿用PageContract。
无schema/model/data改变，不需-u；测试后只以backend.acceptance.up更新受管后端代码。
原sc-fe-r2-p1-01/sc_frontend_acceptance/18082/5180/filestore不变，不改fixture或账号。
P4复用public-auth探针，公共契约GET改用真实响应；激活写响应继续模拟。L1→非零backend/frontend
定向L2→clean后端身份/受管重启→单次构建/定向匿名浏览器；远端/发布未进入。

WEB-AUTH-03验证索引：
- 初始backend public投影测试failed，发现原page_orchestration_data_provider未登记激活/恢复open_login，
  落到refresh；在该唯一provider补齐，builder中的共享target继续决定目的地。非前端fallback。
- L1 `make ci.local.iteration` passed `/tmp/web-auth03-iteration-ready.log`及后续
  `/tmp/web-auth03-iteration-zones.log`；L2严格类型/auth surface passed `/tmp/web-auth03-ready.log`。
  `make verify.frontend.public_auth_bootstrap.unit`最终7后端+8前端并发/失败/缺失动作例passed
  `/tmp/web-auth03-zones-final.log`。P4 public GET允许表7例/预览6例passed
  `/tmp/web-auth03-focused-final.log`。新增API仍拒绝POST及其它匿名写。
- P0 82664f30、P4 376e5a06后clean；受管`backend.acceptance.up`与health通过，
  `/tmp/web-auth03-backend-up.log`、`/tmp/web-auth03-backend-health.log`。旧容器源码身份不符按
  既有入口替换；相同库/profile/端口/filestore，不升级模块、不写fixture或账号。
- 前端auth03一次构建21.96秒 `/tmp/web-auth03-build.log`，up通过。真实匿名公共契约GET和
  真实恢复status、首次公共GET模拟503→重试、模拟激活两阶段→两条返回login16项passed：
  `public-auth-1790674299932/report.json`，不冒称真实密码写闭环。
- 随后P0补canonical zones/data_sources安全投影（3aa76af6）：原consumer不读旧sections，
  不能只给actions后继续布局fallback。保留区块身份/priority/tag/enabled/open和数据源身份字段，
  去掉role/visibility/context；7后端例含结构等价。后端受管再次up，未重建前端；16项定向复核
  passed `public-auth-1790674367302/report.json`、`/tmp/web-auth03-browser-final.log`，绑定新后端。
- 真实finance启动回归 `BOOTSTRAP_ROLES=fixture_role_finance make verify.frontend.standard_bootstrap.browser`
  passed `/tmp/web-auth03-login-final.log`，`bootstrap-inventory-1790674371809/report.json`：
  登录/真实init/权威落地/334列表契约、335工作表、698/699表单、Home/MyWork双宽，零错误/拦截。
- 截图复核发现最后字段错误提示挤压提交按钮：行为16项通过不等于视觉通过。6ea88c6a仅把两处
  裸submit纳入ScFormItem，保留既有grid/gap布局；12项引擎及类型passed
  `/tmp/web-auth03-spacing-tests.log`、L1 `/tmp/web-auth03-spacing-iteration.log`。B线确认行为未变，
  finance证据输入不受影响可复用；P4新增两宽度错误底部<=按钮顶部断言。由实际视觉缺陷触发
  r2修正构建，原auth03保留；不称无依据重复构建。

WEB-AUTH-03最终结果：r2构建21.83秒 `/tmp/web-auth03-build-r2.log`，受管up
`/tmp/web-auth03-up-r2.log`，18/18公共页面检查passed `/tmp/web-auth03-browser-r2.log`及
`public-auth-1790674497445/report.json`（含新增双宽反馈间距）；390截图复核无重叠。
前端产物base `6ea88c6ab978b027d96589e3fd1aed031bf3cdad`，entry `index-B23jnz4I.js`，
SHA256 `4da0248faec09b715ca92902d030ac65afc32f991cb1b1eab265ec8d192c0655`；后端3aa76af6
及相同addons输入。P4/docs后续提交不改变产品输入，不重跑finance。
公共契约实际响应随报告保存，版本1.0.0，三页动作来自后端；失败重试通过。激活请求全被模拟，
未真实激活/重置账号；恢复status和公共契约真实读取。B线最终复核无代码阻断。
WEB-AUTH-02返回链阻断由WEB-AUTH-03关闭，两批范围内批次验收完成；主线未集成、目标环境未部署、
整体用户交付未验收。5180保留r2候选，旧auth02/auth03产物可回退。专用设计器/配置编辑器仍需按
已登记页面职责推进，未自动升级正式89入口业务矩阵或宣称整体官方接管完成。

## WEB-CONFIG-01：专用编辑器通用输入收口（进行中）
基线aae185d9 clean。P0 frontend renderer共享LowCodeFieldChipEditor与直接style；
覆盖列表列、搜索筛选/分组、透视/图表字段配置七种消费。P3目录、添加/排序/删除草稿与发布
逻辑不变。修复ScInput旧value接线并接入ScForm/Item；退出原生form提交及重画input边框的CSS。
普通列表组合不承接树/画布专用编排。不修改账号、业务或配置数据，不推送/合并/部署。
L1 iteration→非零组件输入/表单及既有配置行为L2→受影响呈现验证；L3跳过无后端变化。


WEB-CONFIG-01结果（批次验收完成）：
- P0提交46196f195ccb474aa16f3652942a0f47c3b859d5；P4仅扩展既有Make、受管验收包装和探针，
  无新环境/端口/凭据权威。页面类型范围在既有page-patterns同步。P0为通用契约控件消费，
  非行业/客户规则；P3业务逻辑不迁入前端。未改后端，L3跳过；L5发布流程本批未进入。
- L1 `make ci.local.iteration` passed `/tmp/web-config01-iteration-final.log`。
  L2 `make verify.frontend.field_configuration_component.unit` 14项passed，严格类型检查及
  `make verify.business_config.unit` passed，见 `/tmp/web-config01-tests-final.log`；包含配置草稿、
  发布边界及后端配置回归。14项为真实SFC/官方组件SSR及提交接线，不冒称浏览器输入事件测试。
- P4组件工具初次失败为compiler导入、server-renderer解析、mjs扩展及SSR空value属性假设，
  分别修正工具后重试，日志 `/tmp/web-config01-tests.log` 与r2/r3/r4；不是产品运行失败。
  允许表8项、预览工具6项passed `/tmp/web-config01-tools.log`；只放行严格resume_only=true且
  非fresh的草稿读取及两项audit，创建/保存/发布仍拦截。
- `make verify.frontend.lint.src` passed（0 errors、56 warnings） `/tmp/web-config01-lint.log`；
  `make verify.frontend.style_system.guard` passed `/tmp/web-config01-style.log`。
- 唯一构建20.15秒 `/tmp/web-config01-build.log`，受管up `/tmp/web-config01-up.log`。
  5180加载config01-20260929；base为46196f19加明确P4/docs dirty scope，非冻结交付身份。
  entry index-CmcaSee3.js，SHA256 7ccc3986dc000491645129165b375aa8ae6500099ddf3fa7c4c1bf1badfcc753；
  后端继续3aa76af6及不变addons，sc-fe-r2-p1-01/sc_frontend_acceptance/18082不变。
- `make verify.frontend.standard_config_field.browser` 初次failed：登录页数据库框缺席时探针
  等待isEnabled超时，修正count检查。第二次10项passed（config-field-1790675036110），
  截图取景落在覆盖列表，补scroll/表单边界及局部截图后定向重验，非产品修改或重复构建。
  最终12/12 passed `/tmp/web-config01-browser-final.log`，原始结果
  `artifacts/frontend-web-fix-20260928/config-field-1790675091316/report.json`。
  真实config_admin登录→system.init→配置工作台，输入/清空、Enter/按钮提交、搜索、排序恢复、
  1440/390无溢出通过，零页面错误及未登记请求；390局部截图复核通过。
  id可能已存在，结果只证明提交/清空链，不宣称新增配置字段成功。
- 草稿读取权威返回created=false，无配置保存/发布；局部未保存状态随浏览器关闭丢弃。
  不宣称后端零写（登录session和usage.track仍允许）。B线只读复核无阻断，明确七种组件消费
  不等于七条浏览器旅程。既有AUTH/BOOT业务输入未变，证据复用，不重跑87入口盘点。
- 后续P4/docs提交不改构建产品输入，沿用上述产物与页面证据。旧auth03-r2产物保留可回退。
  批次验收完成；主线未集成、目标环境未部署、整体用户交付未验收。剩余菜单配置树/编辑控件
  及专用设计器继续按页面职责收口；不自动升级正式89入口矩阵。


## WEB-CONFIG-02：菜单配置页头与文本输入接管（进行中）
基线5962350b clean；P0 frontend renderer，Module MenuConfigView/menuConfig模板与直接样式。
通用呈现机制由P0负责，非P1行业规则、P2偏好或P3配置语义；后端、schema、store不变。
复用ScPageHeader/ScInput，覆盖新增、单条、批量及树搜索文本输入；旧header/input自绘职责退出。
树、数字/选择/复选控件、发布/版本逻辑继续明确保留，不冒称完整专用编辑器接管。
风险为受控输入和响应式布局，L0身份→L1 iteration→L2严格类型/primitive/header/配置回归，
再决定受影响L4；L3无后端改动跳过，L5远端发布不进入。沿用既有受管验收环境。

WEB-CONFIG-02新增阻断：L1、L2通过后e5eee791构建一次21.83秒，真实panel.get返回空runtime.tree，
页面正确拒绝旧树回退。两次探针0项超时，第二次仅补定位阶段/失败截图，见menu-config-1790675429611。
受管只读诊断固定uid34/验收库，SET TRANSACTION READ ONLY并finally rollback，确认
异常delivery_navigation_empty。相同actor仅替换为正式IdentityResolver得到非空树，
`/tmp/web-config02-nav-canonical.log`；不是权限放宽或业务数据修复。

## WEB-CONFIG-03：菜单配置复用正式身份投影（进行中）
P0 smart_core handler，现有IdentityResolver/扩展identity profile为唯一角色曝光权威。
停止前端改动，仅把菜单handler三字段自造role_surface替换为正式解析结果，保留平台/配置管理员
能力标志；DeliveryEngine与权限过滤不动。无模型/schema/注册/data变化，不需-u，仅受管后端重启。
单独P0提交及非零菜单单测，L1→L2→clean后端身份→L3 up/health→复用CONFIG02产物定向L4。
不新增环境或凭据、不修改配置/账号，不重跑无关付款旅程。

WEB-CONFIG-02/03合并结果索引（页面最终补验中）：
- CONFIG02 L1 iteration passed `/tmp/web-config02-iteration-final.log`；L2严格类型、primitive
  11事件例、页头28模型例及adapter/guard、配置回归passed `/tmp/web-config02-tests.log`。
  style guard passed `/tmp/web-config02-style.log`；lint 0 errors/56 warnings `/tmp/web-config02-lint.log`。
  允许表9例及预览6例passed `/tmp/web-config02-policy.log`、`/tmp/web-config02-preview.log`。
- CONFIG03 P0 ba6478f2；L1 `/tmp/web-config03-iteration.log` passed；
  `make verify.business_config.unit` passed `/tmp/web-config03-tests.log`，菜单专项49例含新增
  多角色、曝光/拒绝透传断言。无模型变更跳过-u；不触及P1规则或数据库数据。
- P4 14e9db7c形成clean后端候选，`make backend.acceptance.up`及health passed
  `/tmp/web-config03-backend-up.log`、`/tmp/web-config03-health.log`，原容器旧源码身份被受管替换。
  相同project/库/端口/volume。前端复用唯一config02产物base e5eee791，entry index-DznGOp-O.js，
  SHA256 8a52fe645d3339e54fcddf6d788f3679ef0e33ed9b1b736a864735d1a97fc0e2。
- 后端修复后浏览器通过前三项搜索/文本检查，随后因三个同名批量按钮strict定位失败，
  `menu-config-1790675688914/report.json`。截图确认树/单条编辑已恢复。P4仅将定位限定到既有
  菜单摘要面板，产品与产物不变后重试；不把此前失败改写为通过。
- B线当前修复无阻断：不放宽DeliveryEngine过滤，不提升平台权限。当前安装identity profile与
  startup override provider使用同一ROLE_SURFACE_OVERRIDES；未承诺未来多provider场景等价。


WEB-CONFIG-02/03最终结果：12/12 passed `/tmp/web-config03-browser-final.log`，原始报告
`artifacts/frontend-web-fix-20260928/menu-config-1790675716958/report.json`；errors/blocked均空。
真实config_admin登录/init→菜单panel→搜索/清空→中文名称→单条与批量同步/清空/恢复→
新增草稿名称及空值禁用→1440/390无水平溢出。390截图复核文本输入与编辑区可用。
本地草稿恢复并关闭浏览器，无菜单保存/创建/发布/回滚请求，登录session及usage遥测除外。
CONFIG02空树阻断由CONFIG03关闭，两批范围内批次验收完成。最终定位器修改只影响P4浏览器选择，
node语法/diff检查及对应真实12项已重验；产品L1/L2及构建输入未变复用，文档不使页面证据失效。
旧config01产物保留；5180继续config02，后端14e9db7c。后续文档/探针提交无addons变化。
主线未集成、目标环境未部署、整体用户交付未验收。后续仍需专用配置页数字/选择/复选、
反馈与树/设计器通用交互接管；不把103个可配置菜单节点当作正式89入口业务通过数。


## WEB-CONFIG-04：菜单配置通用选择控件接管（进行中）
基线6bd1c8eb clean；P0 frontend renderer MenuConfigView/menuConfig template与直接CSS。
ScSelect/NumberInput/Checkbox/Radio替代原生控件，选项/草稿/语义继续现有P3权威，非P1/P2规则。
DOM event改值协议；ID显式Number，数字清空仍0，复选boolean；旧input边框退出，树及批量表格保留。
L0→L1 iteration→L2严格类型/primitive/配置回归→一次构建及受管菜单定向L4；无后端改动跳过L3，
L5远端发布未进入。复用14e9db7c后端/sc_frontend_acceptance/5180，不保存配置或新建环境。
首次编辑脚本匹配无span标签失败，文件未写入；修正标签转换后继续，非产品验证失败。


WEB-CONFIG-04验证索引：
- P0 cfc9e6b0，L1 `/tmp/web-config04-iteration-fixed.log`及final passed；编辑器转换产生空白尾空格，
  diff检查发现后清理，初始iteration不作通过依据。严格类型、primitive 11事件例及配置回归
  passed `/tmp/web-config04-tests.log`；style/预览6例/lint通过 `/tmp/web-config04-quality.log`
  （lint仍0 errors/56 warnings）。共享单测不替代实际浏览器交互。
- B线指出新增复选框会被.create-form label布局覆盖，已在初次构建前排除.sc-checkbox；
  同时详情区排除对应根label，原生标签嵌套退出。无改变已验证业务回调。
- 首次构建21.79秒 `/tmp/web-config04-build.log`，受管up；浏览器14项通过后下拉option角色
  定位超时，原始 `menu-config-1790676000863/report.json`。截图证实选项可见；P4改为
  可见.t-popup范围内的用户文案定位，避免全页同名当前值。数字窄列加减按钮挤压数值为真实
  视觉缺陷，f80cbffd仅采用官方theme=normal，非重建控件或修改值语义。
- r2 L1 `/tmp/web-config04-r2-iteration.log` passed；严格类型及primitive回归passed
  `/tmp/web-config04-r2-tests.log`。仅主题变化，之前配置业务回归输入不变复用。
  r2修正构建20.47秒 `/tmp/web-config04-build-r2.log`，受管up `/tmp/web-config04-up-r2.log`。
- 版本handler可能由allow_bootstrap/allowBootstrap/bootstrap触发初始化；探针只读白名单拒绝
  三别名真值，10例passed `/tmp/web-config04-policy-final.log`。版本响应必须HTTP成功、ok=true、
  versions数组及bootstrapped=false，失败不冒称空数据；0/1版本显式标明相应覆盖限制。
  不执行保存/创建/回滚；登录session及usage遥测仍允许。最终浏览器补验进行中。


WEB-CONFIG-04 r2页面结果：24/24 passed `/tmp/web-config04-browser-final.log`，
`artifacts/frontend-web-fix-20260928/menu-config-1790676155504/report.json`。数字输入/清空/恢复、
单条-批量显示同步、角色文字切换恢复、父级0选项、两宽弹层边界及页面无溢出均通过。
versions真实读取成功、bootstrapped=false、现有0版本，版本单选运行交互明确未覆盖；无新增fixture。
截图处在关闭动画中，P4增加等待可见弹层隐藏后取景；仅采集工具改变，未重建产品。
前端base f80cbffd63051180944fd691335f0d557047a2ad加明确P4/docs dirty scope，非冻结身份；
entry index-Bax7D-I5.js，SHA256 80ca1ab6a1339e377c1c0e3aad45c732b8cbf545b9b1803e7d09bb9fb5c3d8d6。
后端14e9db7c/addons不变，既有profile/库/端口/volume不变。B线值协议与样式修正无阻断，
P4版本响应严格校验及可见popup范围已采纳。之前无关AUTH/BOOT/付款证据复用。

最终采集24/24 passed `/tmp/web-config04-browser-capture.log`及
`artifacts/frontend-web-fix-20260928/menu-config-1790676189351/report.json`；390截图复核正常，
零页面错误/未登记请求。就本批控件读写草稿范围批次验收完成，版本单选无数据的运行覆盖限制保留。
未保存/发布/创建/回滚菜单，浏览器关闭丢弃未保存状态；主线未集成、目标环境未部署、整体用户
交付未验收。后续仅P4/docs提交不改变产品/后端输入，复用本次证据。旧config04/config02产物保留。


## WEB-CONFIG-05：菜单配置反馈组合接管（进行中）
基线588b6881 clean。P0 frontend renderer共享ScInlineState增加官方success主题；菜单页错误、成功、
加载及版本说明改用共享状态。旧状态边框/背景/加载样式退出。错误优先、提示来源、刷新方法不变。
非P1行业规则/P2偏好/P3配置语义，无新接口、schema、store或后端。L0→L1→L2类型/状态/组件→
单次构建/受管定向L4；L3无后端改动跳过、L5远端未进入。仅P4扩展原探针模拟读失败和会话提示，
不称真实保存，不新增fixture，环境及后端14e9db7c不变。

状态缺口同批修复：loadPanel已有保存提示时不清旧error，成功刷新仍可能显示失败。
只在完整面板装载成功后清error，异常路径继续保留错误，不改变保存提示或丢弃草稿规则。
P4受控拦截首次panel读取为失败，校验loading/错误优先/既有刷新恢复/成功提示；模拟会话提示
在当前浏览器内生成，未调用真实保存。后续panel和版本查询仍真实读取。

L2 rendering_detail_state发现5项失败，停止构建。归因3个旧绑定：ActionBlocks锁3按钮、MyWork
锁ScPanel、WorkspaceHome锁div，均在已完成官方组合后过时。P4原inventory就地改为工作区
精确导入+状态/忙碌绑定、两类动作各自循环/disabled/执行绑定，新增破坏绑定反向测试；
不是降低按钮数或放宽未知组件。design_alignment打印的gap1来自负例，当前独立inventory为0。


WEB-CONFIG-05门禁收敛：inventory完整复核另有App公共状态与ProductListSurface两处未登记，
与三个旧绑定共同形成5个source gap。已在既有ownership登记，检查真实组件/条件/动作/slot；
没有新建平行覆盖表。P4消费绑定规则增加精确composition导入路径和同节点attribute_groups，
7处反向破坏测试覆盖拒绝错误导入、忙碌状态丢失、动作禁用丢失、重试/卡片职责丢失。
- L1 `/tmp/web-config05-ready-iteration.log` passed；严格类型、state_dashboard先前通过
  `/tmp/web-config05-tests.log`。rendering59测试/状态guard通过后旧生成清单stale，原始结果
  `/tmp/web-config05-tests-final.log`；使用 `make refresh.frontend.rendering_detail.inventory` 后，
  `make verify.frontend.rendering_detail_state.unit verify.frontend.primitive_adapter.unit` 全通过
  `/tmp/web-config05-tests-ready.log`，含59测试、11输入事件及31 primitive guard测试、生成一致性。
  负例中故意输出的design_alignment FAIL不代表当前清单失败，最终--check通过。
- style/预览6例/lint passed `/tmp/web-config05-quality.log`，lint 0 errors/56 warnings。
  后续P4规则不改变产品lint输入。B线复核无放宽门禁；工作区内部实现不变，沿用既有组合验证，
  不把静态消费绑定59测试称运行页面验收。产品P0 dfc7a615，无后端变化。


WEB-CONFIG-05最终结果：本批范围批次验收完成。
- 单次构建21.11秒 `/tmp/web-config05-build.log`，受管up `/tmp/web-config05-up.log`；5180加载
  config05-20260929，base dfc7a6152672556d198041ca78ed23e7c5cb466e加明确P4/docs dirty scope，
  非冻结交付身份。entry index-9ng9XRoC.js，SHA256
  6faee2e922755100ca36701931237e9be6a647b5dc59825888e61dbbce24f204。
- `make verify.frontend.standard_menu_config.browser` 33/33 passed `/tmp/web-config05-browser.log`；
  原始 `artifacts/frontend-web-fix-20260928/menu-config-1790676629976/report.json`，errors/blocked空。
  首次panel读取及已保存文案明确模拟；loading aria-busy、error alert优先于success、既有刷新真实
  读取恢复后error隐藏及success status保留、双宽反馈边界均通过。390错误红色/成功绿色截图复核。
  后续文本/数字/选择草稿及弹层检查沿用同一旅程，未执行真实保存/创建/发布/回滚。
- 版本真实读取仍0历史版本，单选运行交互保持uncovered；无fixture新增。浏览器关闭即丢弃模拟
  会话提示和局部草稿。后端14e9db7c及addons输入未变，原profile/库/端口/volume复用。
- 最终P4/docs提交不改已验产品与环境输入，继续复用本次页面证据及原始记录。旧config04-r2保留。
  主线未集成、目标环境未部署、整体用户交付未验收；零静态状态gap不等于89入口业务完成。
  菜单通用输入/反馈已接管，专用树/批量编排及设计器后续按必要职责收口，不再另造通用状态实现。


## MENU-TREE-01：菜单专用树接管与探针层 vendor 耦合硬化（2026-09-29，本地批次）

### 层级、范围与身份

- `Formal Product Layer`：P0 平台内核产品（原语导出/桥接）+ P4 运维交付工具（验证脚本与门禁）。
- `Layer Target`：`frontend/packages/ui` 原语导出、`frontend/apps/web` 菜单配置视图、
  `scripts/verify` 探针门禁、`scripts/verify/baselines` 基线。
- `Module`：`frontend/packages/ui/src/primitives.ts`、`frontend/apps/web/src/views/menuConfig/*`、
  `frontend/apps/web/src/views/MenuConfigView.vue`、`scripts/verify/playwright_vendor_coupling_guard.py`。
- `Reason`：菜单树是首个“页面类型”接管；通用交互必须回到官方组合，探针不得继续锁死私有 DOM。
- `Why Not Elsewhere`：不新增业务功能、不重构模板体系、不改后端事务，也不把业务语义放进前端。
- 本地提交（未推送/未合并/未部署目标环境）：`fc04b09c3`（树接管）→ `a114ffe0f`（拖拽契约守卫）
  → `b2ad32f33`（派生清单刷新）→ `c5f08314b`（节点展开语义标识）→ `d3bc7b45d`（探针断言官方交互契约）
  → `3c1d4e70a`（按可见文案定位选项）→ `1d155b257`（探针层 vendor 耦合门禁与基线）。

### 本次提交的权威边界回答

- 业务语义来源：菜单身份、层级、可删除性仍来自菜单配置契约的运行时投影；前端只决定呈现与交互。
- 前端自主范围：节点标签插槽、`data-menu-id`/`data-menu-expandable`/`data-menu-expanded` 语义标识、
  展开集合跟随编辑器折叠状态、拖拽可落点判定 `canDropTree`。
- 未做静默补齐：删除的私有键盘微步重排不再由前端另造；父级移动与顺序重排仍走显式编辑器输入。

### 定向验证

- L1 `make ci.local.iteration` passed `/tmp/menu-tree-11-iteration.log`。
- L2 定向：`verify.menu_config_tree_editor.behavior`（`/tmp/menu-tree-12-tree-guard.log`）、
  `verify.frontend.primitive_adapter.unit`、`verify.frontend.component_driver_takeover.unit`、
  `verify.frontend.rendering_detail_state.unit`、`verify.frontend.navigation_shell.unit`
  （`/tmp/menu-tree-12-l2.log`、`/tmp/menu-tree-12-l2b.log`）；产品源码改动使
  `component-driver-takeover-inventory-v1.json` stale，用既有生成器刷新后通过。
- 类型检查 `scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck` passed
  `/tmp/menu-tree-12-typecheck.log`；`make ci.generated_reports.guard` passed
  `/tmp/menu-tree-12-generated.log`。
- 受管浏览器：`make verify.frontend.standard_menu_config.browser` 46/46 passed，
  errors/blocked 空，uncovered 仅“版本单选：现有数据无历史版本，不新增fixture”。
  原始 `artifacts/frontend-web-fix-20260928/menu-config-1790679481731/report.json`
  （`/tmp/menu-tree-16-browser.log`）。新增断言：面板只由官方树渲染（旧 `.config-tree-list`/
  `.branch-marker` 计数为 0）、每节点恰有一个官方展开交互槽、展开/收起跟随折叠集合、
  按菜单身份而非列表位置驱动业务面板。

### 全局硬化：探针层 vendor 耦合门禁

根因：只接管产品渲染不够。探针若用 vendor 内部类名、过渡状态类或像素几何断言，仍能报绿，
于是验收体系跟随标记而不跟随业务事实，官方组件一变就掩盖真实回退。

- `scripts/verify/playwright_vendor_coupling_guard.py`，扫描 `frontend/apps/web/scripts` 与
  `scripts/verify`：
  - 零容忍：过渡/动画状态类（`--enter-active`、`v-enter` 等）、
    `querySelector`/`querySelectorAll` 内使用 Playwright 专属选择器语法（`:visible`、`:has-text(`、`:text=`）。
  - 只减不增：非 `Sc` 根下的 vendor 内部类选择器（复用产品侧 official-design 规则口径）、
    `getBoundingClientRect().width/height` 内联几何断言。
- 基线 `scripts/verify/baselines/playwright_vendor_coupling.json` 登记既有债务
  （vendor 23 文件/109 处，几何 11 文件/33 处），只允许减少；**本轮不清偿既有债务**。
- 规则自身带反例：`scripts/verify/test_playwright_vendor_coupling_guard.py` 证明四类规则非空跑；
  规则定义文件与反例文件按精确路径排除，不用目录或通配符。
- 挂载：`verify.frontend.playwright_vendor_coupling.guard`，并接入 `verify.frontend.quick.gate`
  与 `ci.professional.backend.shard-verify`，使远端必需检查覆盖该规则。
- 顺带合规：`standard_menu_config_browser.mjs` 的移动选项定位由 `.t-popup:visible` 改为可见文案，
  使 vendor 内部类选择器由 109 降至 107（其余 22 文件为已登记既有债务）。

### 候选与运行来源

- 单次构建 `make frontend.standard.preview.build` `/tmp/menu-tree-13-build.log`，
  `base_sha=d3bc7b45df98adc5cfd368ba0fba9b71a5be734f`、`dirty_scope` 为空，
  `index_sha256=a593c0411ce8e12629a6d3bf094130130c8ee2ddf0970e710feecf95811eeb3a`、
  `entry=/assets/index-CaZN7DlL.js`。
- 复用受管 5180 预览（pid 2669621，`config05-20260929/dist`，Odoo
  `sc-backend-odoo-acceptance` / `sc_frontend_acceptance` / `SC_SOURCE_REVISION=14e9db7c`），
  HTTP 回读 index 与 entry 哈希一致。旧冻结产物与历史 identity 存档保留。

### 剩余阻断与非阻断

- 非阻断（既有，独立记账，本轮不动）：`verify.guard.registry` 报
  `test_frontend_standard_preview.py`、`test_workspace_composition_wiring.py` 为未登记孤儿；
  两者全仓零引用且不在本批 diff 中，本批改动经 diff 证明为纯增量，未移除任何引用。
- 非阻断：探针层 vendor 内部类选择器既有债务 22 文件/107 处、几何断言 11 文件/33 处仍未清偿。
- 非阻断：菜单历史版本单选项因无数据仍 uncovered；未新增 fixture。
- 未执行：真实保存/发布/回滚，89 入口矩阵，发布门禁，设计器与批量编排职责。
- 状态边界：本批**批次验收完成**；主线未集成、目标环境未部署、整体用户交付未验收。

## OFFICIAL-RENDER-ALIGN-01：契约边界硬化与工作台官方呈现收口（2026-09-29，本地批次）

### 层级、范围与身份

- `Formal Product Layer`：P0 平台内核产品（契约边界与端侧消费）+ P4 运维交付工具（验证脚本与门禁）。
- `Layer Target`：`smart_core` 契约投影载荷、`frontend/apps/web` 配置工作台视图、`scripts/verify` 边界门禁。
- `Module`：`addons/smart_core/handlers/business_config_surface.py`、
  `frontend/apps/web/src/views/businessConfigSurface/*`、`frontend/apps/web/src/views/BusinessConfigSurfaceView.vue`、
  `scripts/verify/backend_contract_boundary_guard.py`、`scripts/verify/low_code_workbench_product_guard.py`。
- `Reason`：工作台此前保留了一份与契约并行的业务名称词表，契约边界此前只有文字、没有可执行约束。
- `Why Not Elsewhere`：不新增业务功能、不重构模板体系、不改后端事务、不把业务语义放进前端。
- 本地提交（未推送/未合并/未部署目标环境）：`26ed7116e`（配置总览走官方表格）→ `10622e54f`（菜单批量维护与配置页签走官方原语）
  → `612dca581`（配置工作台名称由契约声明）→ `a6c949c7a`（契约/外观职责边界首次可执行）
  → `41a3853d3`（受管布局通道显式合法）→ `66202b629`（终端投影合法、语义分叉禁止）。

### 本次边界回答（四问）

- 本次涉及什么业务语义：配置分区与边界码的**人类可读名称**，以及契约可以表达/不可以表达什么。
- 权威来源与契约路径：名称由 `ui.business_config.surface.get` 的 `data.sections[].label` /
  `data.boundary_labels` / `data.source_category_labels` 声明；布局语义走 `unified_page_contract_v2.layoutContract`
  与 `view_orchestration.views.form`；终端差异走 `unified_page_contract_v2_client.py` 的按终端投影。
- 前端只决定了什么：组件选择与组合、章节/按钮/帮助文案、可访问性、瞬时交互状态。
- 必要语义缺失时会怎样：`test_business_config_surface.py` 要求契约必须为它发出的每个分区、每个边界码和每个来源类别声明名称；
  工作台不得保留第二份词表。

### 关键纠正：三条边界一次说清（原先的写法是错的）

最初把边界写成“契约不表达外观”，随后又写成“契约必须终端无关”。第二条**与仓库既有实现冲突**，
已改正，不倒填、不保留错误口径：

| 边界 | 正确口径 | 执行位置 |
|---|---|---|
| 外观 | 契约不表达原始视觉值、DOM/CSS 通道、设计系统内部取值、客户端可访问性属性 | `backend_contract_boundary_guard.CONTRACT_APPEARANCE_PATTERNS` |
| 布局 | **布局是合法的一层契约**：`layoutContract`／`layoutType`／`layoutHints`／`view_orchestration.views.form` 表达顺序、分组、显隐、列集合与受管尺寸档位 | `MANAGED_LAYOUT_CHANNEL_KEYS` + 自检（外观规则永不误伤布局） |
| 终端 | **投影可终端化，语义不可分叉**：一份语义契约驱动 `web_pc`／`wx_mini`／`harmony_h5`，允许不同详细程度；终端身份只有一个受管入口 `pageInfo.clientType`，少投必须记账 | `TERMINAL_PROJECTION_CHANNEL_KEYS` + 自检；语义一致性由既有 `find_client_semantic_drift` 与 `make verify.unified_page_contract.v2.client` 执行，本批不重造 |

裁剪记账的既有权威是 `unified_page_contract_v2_client.py` 的 `omitted = original - delivered`，
门禁同时断言 `mobile_compact` 必须报出 `omitted.widgets`；因此“未投递”不会被写成“不存在／不适用／无权”。

### 验收体系为什么没有发现（本批缺口与闭合）

| 缺口 | 为什么漏掉 | 闭合方式 |
|---|---|---|
| 契约边界只有文字 | 没有门禁时，前端可以保留一份与契约并行的业务名称词表，页面照样“看起来可用” | `low_code_workbench_product_guard` 新增：工作台不得重新声明契约已声明的名称，不得再绑定页面自有的章节标题；`*.html` 边车模板一并扫描；两条新规则各带反例自检 |
| 反向边界没有约束 | 只有“前端不得发明业务语义”，没有“契约不得携带外观” | `backend_contract_boundary_guard` 新增外观规则并覆盖 8 个契约写入者；反例测试证明非空跑 |
| 新规则可能误伤既有契约层 | 规则只按“看起来像外观”写，会连带把布局契约和终端投影判为违规 | 两个通道登记为合法并由自检保证永不误伤；`layoutContract`、`spanClass`、`field_size`、`clientType`、`deliveryProfile`、`omitted` 等逐一断言 |
| 工作台名称可被前端覆盖 | 契约已声明 `sections[].label`，但页面曾用自有词表覆盖（`表单配置`／`列表`／`搜索配置`） | 删除 `sectionDisplayLabel` 与 `BUSINESS_FIELD_LABEL_OVERRIDES`；`BusinessConfigSurfaceView.vue` 改为只消费契约名称 |

### 定向验证

- L1 `make ci.local.iteration` → `PASS change_state=clean coverage=L1_only`（`/tmp/align01-iter4.log`）。
- L1/L2 边界守卫：`python3 scripts/verify/backend_contract_boundary_guard.py` → `error_count=0`
  （8 个契约写入者零误报；`appearance=0`、`semantic_fork=0`、两条通道自检为空）；
  `python3 addons/smart_core/tests/test_backend_contract_boundary_guard.py` → `Ran 10 tests OK`。
- L2 工作台：`make verify.business_config.product_guard` → `PASS assertions=29 scanned_files=36`；
  `make verify.business_config.guard_inventory` → `PASS assertions=151`；`make verify.business_config.unit` → OK。
- L2 既有终端权威：`make verify.unified_page_contract.v2.client` → `passed: clients=3`
  （三终端语义签名一致 + `mobile_compact` 必须报 `omitted.widgets`）。
- 受管浏览器（5180，`fixture_role_config_admin`，`sc_frontend_acceptance`）：
  8/8 通过，`consoleErrors []`。断言为“渲染出的页签名 == 契约声明的 `sections[].label`”，
  实测 `["表单字段与布局","列表与搜索","菜单入口","审批规则"]` 完全一致；旧页面自有的
  `表单配置／列表配置／搜索配置` 计数为 0；官方表格与 `[role=tab]` 语义存在；390×844 无整页横向溢出。
  原始结果 `sce-offrepo/artifacts/align01-boundary/report.json`，截图同目录 `shots/`。

### 候选与运行来源

- 后端验收容器 `sc-backend-odoo-acceptance`：`SC_SOURCE_REVISION=66202b629`（`make backend.acceptance.replace-stale` PASS）。
- 前端产物 `sce-offrepo/artifacts/config05-20260929/dist`：`base_sha=a6c949c7a`、`dirty_scope` 为空、
  `index_sha256=e868f1e6490a9c45dcc7d320b34bf7cebf3adb1969fb8bdbf00264250d754935`、`entry=/assets/index-lnyQ5gBG.js`。
  本批后三笔提交只改 `scripts/verify`、`addons/**/tests` 与文档，前端产品源码无变化，因此不重建、不二次比对。
- 5180 运行现场：pid `2669621`，`scripts/release/release_static_server.mjs`，
  `STATIC_ROOT=<config05-20260929/dist>`，`/api/`、`/web/` 代理 `127.0.0.1:18082`（调整前已核对 PID、命令行与目录）。
  5175/5176/5178/5179 旧预览与本批无关，未清理。

### 剩余阻断与非阻断

- 非阻断（既有，独立记账，本轮不动）：`style_system.guard` 四项欠账；`verify.guard.registry` 两个孤儿测试文件；
  探针层 vendor 内部类选择器与内联几何断言的历史债务；菜单配置历史版本单选因无数据仍 uncovered。
- 未执行：真实保存/发布/回滚，89 入口矩阵，全站发布门禁，TPL-05 之后的目标环境交付。
- 状态边界：本批**批次验收完成**；主线未集成、目标环境未部署、整体用户交付未验收。
  本批不把“模板接管通过”写成业务矩阵整行升级。

## 契约动作语义投影：把声明的 purpose 绑到它声明的 occurrence（2026-09-29，FE-CONTRACT-ACTIONSEM-01）

### 问题

`workflowContract.availableActions[].action_semantics` 与 `runtimeContract.businessActions[].action_semantics`
都已声明业务目的，但 `actionContract.actionRuleList` 没把它送到消费位置：**声明存在，语义缺席**，
前端只能靠方法名或按钮文案推断。

修复前实测（`sc_frontend_acceptance`，后端 `66202b629` 运行现场）：

| 记录 | 权威声明 | 交付的 action rule |
|---|---|---|
| `sc.general.contract` 12（draft） | `submit → method action_confirm` | `action_confirm` → `actionSemantics: null` |
| `sc.general.contract` 11/10 | 仅 `cancel → action_cancel` | 三条 native 按钮全部 `actionSemantics: null` |
| `payment.request` 1787 | `approve → validate_tier` | `payment_approve.2/.3` 无语义 |

修复后同一批记录：`contract 12 action_confirm → {"kind":"business","purpose":"submit","executor":"contract.action","origin":"workflow.contract.service"}`；
`payment.request` 新增 `payment_approve.2/.3 → approve`、`action_cancel → cancel_record`；6 个记录合计 `conflicts=0`。

### 分层归属（四问）

- `Formal Product Layer`：P0 平台内核（`smart_core`）。
- `Layer Target`：`unified_page_contract_v2` 投影 + `ui.contract.v2` 动作装配。
- `Module`：`smart_core`。
- `Standard vs User-Specific`：平台机制（已发布词汇表的校验 + 绑定投影）。业务目的本身由 P1 行业模块声明。
- `Why Here`：把“某个方法的业务目的是什么”绑定到消费它的 occurrence，是终端无关的投影机制，任何模型都成立。
- `Why Not Elsewhere`：不在 `smart_construction_core` 写通用绑定（否则行业模块承担平台职责）；
  不在前端按方法名/按钮文案推断（那正是本批修掉的缺陷）；不新增全局状态或并发框架。
- `Blast Radius`：所有 form 契约的 `actionRuleList`。实测 6 个受管记录零冲突，`record.save` 平台语义不被覆盖。

### 实现

- `declared_action_semantics`：按 schema `$defs.actionRule.actionSemantics` 校验声明；越界词汇**丢弃**，
  使动作保持“可见地未声明”，不把未批准的语义当已批准语义投递；`{"conflict": true}` 原样保留。
- `declared_action_meaning`：只比较业务含义（kind/purpose/executor/operation），**不比较 provenance**。
- `project_workflow_action_semantics`：`availableActions[].method` ↔ `button.name`（`button.type` 必须为 `object`）绑定；
  同一方法真正的语义分歧保留 `{"conflict": true}`；平台 `record.save` 语义永不覆盖。
- `_row_declared_action_semantics`：声明随 occurrence 走（policy / row / 其 business action）时同样经词汇表校验后投递。
- `handlers/ui_contract_v2.py` 在 `project_runtime_business_actions` 之后调用。

### 中途发现并修正的假冲突

首版实现按“整份声明”比较，导致 `payment_submit` 变成 `{"conflict": true}`：
`workflow.contract.service` 与 `payment.request.available_actions` 对同一方法声明了**相同目的、不同 origin**。
改为只比较业务含义后恢复为 `purpose: submit`，并保留既有 origin；新增反例
`test_corroborated_purposes_from_two_authorities_are_not_a_conflict` 固定该行为。

### 前端边界硬化（同批，独立提交）

`resolveSelectionActions` 原先硬编码 `['export','archive','activate','delete']`：**由客户端决定有哪些批量动作**。
改为消费契约的 `execution_intents` → 客户端执行器表（按 intent 而非动作名索引）：

- 契约声明的每个动作都保留（隐藏等于前端否决契约）；
- 声明了策略但被策略禁止的 → 可见但禁用；
- 本构建无法解析执行方式的 → 显式报为未解析，不静默丢弃；
- 启用条件仍来自声明的 `delete_mode` / `active_field`。

### 未闭合的缺口（必须显现，不得猜测补齐）

| 缺口 | 定性 | 归属 |
|---|---|---|
| `payment.request` 的 `done/action_done`、`payment_execution/action_create_payment_execution` 无语义声明 | 表达缺口（业务含义存在，契约未表达） | P1 行业模块 + schema 词汇表 |
| workflow registry 的 `activate/complete/reopen/reactivate` 无语义声明 | 同上 | P1 行业模块 + schema 词汇表 |
| 词汇表 `purpose` 无非 `submit/approve/reject/cancel_record` 之外的“完成/开始执行”取值 | 表达缺口 | contract 定义（schema） |

本轮**不猜**这些目的：未声明即保持未声明，前端应显式报缺口而不是按方法名推断。
补齐需要业务权威决定，属下一批，不在本批越权填入。

### 定向验证

- 后端：`addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py` → `Ran 101 tests OK`。
- 契约守卫 5 项：`verify.unified_page_contract.v2.runtime/action/assembler/schema/intent` 全 PASS。
- 实测对照：6 个受管记录（contract 10/11/12、payment 1787/1813）修复前后差异如上，`TOTAL_CONFLICTS 0`。
- 前端：`verify.frontend.typecheck.strict` PASS；`standard_collection_composition.unit`（84→89 cases）、
  `standard_form_composition`（93）、`standard_shell_composition`（71）、`adopted_form_engine_decision`（74，真实 TDesign）、
  `adopted_form_validation_identity`（46）、`contract_form_save_failure_recovery` 全 PASS；`make verify.frontend.build` PASS。
- 既有守卫：`list_batch_action_closure_guard`（按新语义改写断言）PASS；`frontend_contract_consumer_intrusion_guard` PASS；
  `frontend.collection_action_toolbar` / `page_pattern_reference_parity` / `contract_header_action` PASS。
- `make ci.local.iteration` → `PASS coverage=L1_only`。
- 受管浏览器（5180，`sc_frontend_acceptance`）：
  付款列表 `/a/775?menu_id=545` → 呈现 `official-standard-list`（reason `contract-collection-view`），
  选中 2 行后批量动作完整：行内「导出所选」+「更多批量操作」内「导出所选／批量归档／批量激活／批量删除」，
  按钮身份以 `data-action-key="batch:*"` 暴露，`console/pageerror` 为空；
  合同记录 11 → 只读详情 `data-detail-composition-reason=contract-readonly-record-view`；
  付款表单 1815 → 动作身份来自契约（`form.save` / `payment_submit` / `action_cancel`）。
  裸路由 `/a/775` 被 `NAVIGATION_AUTHORITY_DENIED` 拦住，导航授权仍由契约控制（符合预期，非缺陷）。
- 未通过且**与本批无关**：`verify.guard.registry` 仍报既有两个孤儿测试文件（`test_frontend_standard_preview.py`、
  `test_workspace_composition_wiring.py`），与上一批相同，本批未新增。

### 候选与运行来源

- 提交：`dfeecdd3d`（平台契约投影）、`95137138d`（前端批量声明消费 + 守卫/测试维护），HEAD `95137138dc9915d1fec8d9c19549bfb9bd04c154`。
- 前端产物 `sce-offrepo/artifacts/sem01-20260929/dist`：以 `VITE_ODOO_DB=sc_frontend_acceptance VITE_ODOO_DB_LOCKED=1 VITE_APP_ENV=acceptance` 构建一次，
  `entry=/assets/index-qp_wz1lo.js`、`entry_sha256=4bfc4ef6a4802be1e5805e9a4eb0a3aab68e5aa3ccf68c70f07ac49f11787c12`、
  `index_sha256=b5f204d70e0f3971e61740c451d6d5384968e063c0437ff365cd518e4dcc7d64`。
- 5180 运行现场：pid `3612724`，`scripts/release/release_static_server.mjs`，
  `STATIC_ROOT=<sem01-20260929/dist>`，`/api/`、`/web/` 代理 `127.0.0.1:18082`；
  旧候选 `config05-20260929/dist` 保留未覆盖。
- 后端验收容器 `sc-backend-odoo-acceptance`：以**保留容器身份**的方式重启加载工作树源码；
  容器声明的 `SC_SOURCE_REVISION` 仍为 `66202b629`，实际加载的是本批提交的源码（开发态，未冻结）。

### 剩余阻断与非阻断

- 非阻断（既有，独立记账）：`style_system.guard` 四项；`verify.guard.registry` 两个孤儿测试文件；
  探针层 vendor 内部类选择器历史债务；菜单配置历史版本单选无数据。
- 本批未关闭的表达缺口见上表（付款 `done`/`payment_execution`、workflow `activate/complete/reopen/reactivate`），
  按“缺口必须显现”处理，**不视为本批失败**，也不以猜测补齐。
- 状态边界：本批**批次验收完成**；主线未集成、目标环境未部署、整体用户交付未验收。

## 契约词汇表单一权威与后端自证完备性（2026-09-29，FE-CONTRACT-VOCAB-01）

### 问题

声明过的动作语义词汇表 `(kind, purpose, executor)` 在四处各写一份：后端装配器、schema、前端
`actionSemantics.ts`、守卫脚本。于是生产者可以发布 `business + return + client.back` 这种**每个终端都会
丢弃的组合**，四处副本一致地“看起来正常”，缺口被永久隐藏。同一批还暴露了两处同类越界：

- `sc.partner.import.review` 是客户模块拥有的模型，却被 P1 行业模块当成自有 profile 登记，
  `test_profile_methods_resolve_to_existing_model_methods` 在 `sc_dev_demo` 直接红。
- 付款入口与财务工作台对同一字段用了两个词：`finance` 与 `finance_manager`，把角色码写成了第二份声明。

### 分层归属（七问）

- `Formal Product Layer`：P0 平台内核（`smart_core`）为权威；P1（`smart_construction_core`）只声明行业语义；P2（客户模块）只登记自己拥有的模型。
- `Layer Target`：`smart_core.core.action_semantics_vocabulary`、`unified_page_contract_v2_assembler`、`contract_governance` 注册表；`smart_construction_core` 的 workflow 投影服务与能力注册表。
- `Module`：`smart_core`、`smart_construction_core`、`sce_customer_baosheng_legacy`（属主侧）。
- `Standard vs User-Specific`：词汇表与注册机制是平台标准；行业 profile 是行业标准；`sc.partner.import.review` 是客户专属，属 P2。
- `Why Here`：词汇表的单位是 `(kind, executor)` 对而非三个独立集合——独立校验会接受所有终端都丢弃的组合，而生产者确实会发布它。
- `Why Not Elsewhere`：不在前端重述业务子集（那是本次修掉的漂移源）；不在 P1 为不属于本层的模型写 profile；
  不给角色码再加一份字面量；不靠禁止导航/刷新/清空草稿来掩盖身份问题。
- `Blast Radius`：所有 form 契约的 `actionRuleList`、workflow `availableActions`、付款动作的 `required_role_key`。
  实测 `examples=4`、`profiles=65 reachable_actions=9 payment_specs=4 role_gates=4 verdict_covers=4 roles=11 vocabulary=10`。

### 实现

- `addons/smart_core/core/action_semantics_vocabulary.py`（新）：`DECLARATIONS = {kind: {executor: frozenset(purposes)}}`，
  派生 `KINDS/EXECUTORS/PURPOSES/OPERATIONS/BUSINESS_PURPOSES/NON_BUSINESS_PURPOSES` 与 `is_declared(kind, purpose, executor)`。
- `unified_page_contract_v2_assembler.py`：删除本地四个 `DECLARED_ACTION_SEMANTICS_*` 字面量，改为消费权威；
  组合越界即 `return None`，保持“可见地未声明”。
- `frontend/packages/schema/src/actionSemantics.ts`：`DECLARED_BUSINESS_PURPOSES` 改为从 `ACTION_PURPOSES` 过滤派生，不再重述清单。
- `unified_page_contract_v2_schema_guard.py`：四个 enum 对权威比对，禁止装配器再出现本地副本，
  并要求前端业务子集必须是派生表达式；负例 ×3 均按预期 FAIL。
- `contract_governance_registry.py` / `contract_governance.py`：新增 `register_workflow_contract_profile(model, profile, source=)`；
  结构缺键即拒绝注册（缺口不降级为半份投影），读者拿隔离副本。
- `workflow_contract_service.py`：`profile_by_model()` 合并 P1 自有 profile 与外部注册；
  模型或其声明的方法在本 registry 解析不了时**不发布**该动作并留 warning，`describe_record`/`is_model_supported`/`supported_model_names` 统一走合并结果。
- `capability_registry.role_code_for_group()`：角色码从门禁组 xmlid 派生；付款入口与财务工作台删除各自字面量。
- `scripts/verify/workflow_action_semantics_completeness_guard.py`（新，已接入 `verify.workflow_contract.backend`）：
  静态求值 profile/ACTIONS/`_ACTION_ROLE_HINTS`，校验可达动作的 purpose 落在 schema 词汇表内、
  被提供的 payment spec 都有 role gate、role gate 不重述 `required_role_key`、gate 指向真实 `res.groups`，
  以及 `approval_actions` 必须被 `can_review` 消费（否则 Web 会成为唯一决定者）。负例 ×4 均按预期 FAIL。
- `scripts/audit/workflow_state_inventory.py`：`WORKFLOW_METHOD_NAMES` 补 `action_reopen`（注册表已交付该方法，清单缺失使守卫在 HEAD 即红）。

### 定向验证结果

| 命令 | 结果 |
|---|---|
| `make verify.unified_page_contract.v2.schema` | PASS（examples=4） |
| `verify.unified_page_contract.v2.{assembler,runtime,action,intent,client,web_consumer,web_architecture}` | 全部 PASS |
| `python3 addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py` | 104 tests OK（含本批新增的运行时通道配对回归） |
| `python3 addons/smart_core/tests/test_workflow_contract_profile_registry.py` | 4 tests OK（缺键拒绝/空名拒绝/隔离副本） |
| `python3 scripts/verify/workflow_action_semantics_completeness_guard.py` | PASS |
| `python3 scripts/verify/workflow_inventory_profile_method_guard.py` | PASS profile_methods=29 inventory_methods=41 |
| `python3 scripts/verify/workflow_contract_custom_coverage_guard.py` | PASS allowed_standard_uncovered=account.move,purchase.order,stock.picking |
| `TestWorkflowContractBackend`（`sc_dev_demo`，注册 env） | **0 failed**，7 error(s) of 28 tests |
| `make verify.frontend.contract_header_action.unit` | PASS |
| `make verify.frontend.typecheck.strict` | PASS |
| `make verify.frontend.build`（`VITE_ODOO_DB=sc_frontend_acceptance`） | 成功，`dist-dev` |

修复前 `TestWorkflowContractBackend` 为 **2 failed**（`test_profile_methods_resolve_to_existing_model_methods`
报 `sc.partner.import.review not found in registry`），现已归零。

七条 error 全部是**开发库环境数据**类：`费用与扣款单据必须关联已归属公司的有效项目`、
`自筹办理必须关联已归属公司的有效项目`、`收款归集关系不存在或当前用户无权访问`、
`[SC_GUARD:P0_PAYMENT_STATE_BYPASS_BLOCKED] 未完成审批流程`。按“开发阶段关注功能而非环境数据”口径
**不作为本批阻断**，也不以造数掩盖；修复前后的 error 集合逐条一致，未新增。

### 候选与运行来源

- 提交：`e7a523cca`（P0 词汇表权威 + 注册表）、`8890d5f0f`（P1 行业语义与角色派生 + 完备性守卫）、
  `7ec3bbf16`（前端派生）；HEAD 见下方批次记录。
- P2 属主侧提交：`sce-customer-baosheng-odoo` `bfbc736`（`fix/native-form-preference-upgrade`），
  `runtime_registration.py` 注册 `sc.partner.import.review` profile。
- 后端测试现场：`ENV_FILE=.env.dev DB_NAME=sc_dev_demo MODULE=smart_construction_core` 经 `scripts/test/test_safe.sh`。
- 前端产物：`VITE_ODOO_DB=sc_frontend_acceptance VITE_ODOO_DB_LOCKED=1 VITE_APP_ENV=acceptance make verify.frontend.build`，
  输出 `frontend/apps/web/dist-dev`（开发态，未冻结、未替换 5180 服务目录）。

### 剩余阻断与非阻断

- 非阻断：`docs/audit/workflow_state_inventory_sc_demo.md` 仍为历史 `sc_demo` 基线。
  当前注册库 `sc_dev_demo` 生成会得到空清单，`sc_demo` 未装模块，故**本批不重生成**；
  `verify.workflow_contract.backend` 的 `audit.workflow_state.inventory` 前置步骤在具备已装模块的 `sc_demo` 前不要单独跑。
- 非阻断：`style_system.guard` 三项文件长度、探针层 vendor 选择器历史债务（均独立记账，未触碰）。
  `verify.guard.registry` 的两个 false-orphan 已在本批收口，见下方 `FE-GUARD-REGISTRY-01`。
- 未闭合：约 80 处未声明的原生按钮 occurrence 仍需按“权威侧缺失 / 原生未登记”逐类定性；
  `construction.contract` 的 `activate/complete` 只读详情面不渲染 header 动作，属前端 presentation 可达性缺口，非契约缺陷。
- 状态边界：本批**批次验收完成**；未推送、未合并、未部署目标环境，整体用户交付未验收。

### 独立复核与同批修复（2026-09-29）

对本批四个提交（`c4b419878..21df11b45`）与跨仓 `bfbc736` 做了一次**只读独立复核**，
结论 `REQUEST_CHANGES`，无 S0/S1，两条 S2，均在本批内收口：

- **S2-1 运行时业务动作通道绕过权威校验**：`_append_actions` 的复制表把 `action_semantics` 原样搬运，
  该通道（`project_runtime_business_actions`，P1 财务工作台正用）仍可发布“所有终端都会丢弃”的组合，
  与“组合越界即丢弃”的表述不符。修复：该键从复制表移除，改为经 `declared_action_semantics` 投影。
  复核者的原始探针（`business+return+client.back`）现返回 `contract actionRuleList actionSemantics: [None]`，
  合法声明 `business+start_execution+contract.action` 仍原样发布。
- **S2-2 守卫与 schema 只有逐维枚举、无配对校验**：把 `ACTIONS["activate"]` 的 executor 改成 `client.back`
  时，新守卫仍 PASS。修复：schema 的 `actionSemantics` 声明分支新增 `allOf[].oneOf` 配对约束
  （4 个 `(kind, executor)` 对，各自的 purpose 集合）；`unified_page_contract_v2_schema_guard`
  新增“schema 配对 == 权威 `DECLARATIONS`”比对；`workflow_action_semantics_completeness_guard`
  改为用权威 `is_declared` 做配对校验。负例实测：executor 漂移 → FAIL；schema 少一个 pair → FAIL；
  schema 放宽某 pair 的 purpose → FAIL。

**同批收口**：`verify.unified_page_contract.v2.stable_projection` 原为基线即红
（`frontend_v2_policy_projection_guard` 报 `types.ts` 的 `actionSemanticsInvalid` 不在严格白名单内；
三处相关文件在本批 diff 中字节未变，该标识由基线祖先 `22ee5391b` 引入）。
该字段是端侧对“后端发布了越界声明”的拒收标记：`canonicalFormActionExecutor` 与
`contractFormHeaderCanonicalActions` 真实读取它，删掉会把“缺口可见”退化回静默丢弃。
处理方式不是放宽白名单，而是把它登记为 `ContractV2ActionRule` 唯一允许的端侧扩展字段，
并补两条 fail-closed 约束：白名单字段必须被声明的消费者读取，且后端 schema 不得发布它。
负例实测：消费者不再读取 → FAIL；schema 发布该键 → FAIL。收口后
`verify.unified_page_contract.v2`（含前端构建）与 `verify.unified_page_contract.v2.professional_backend`
均 `exit=0`，该红项不再阻塞聚合门禁。

复核者登记的非阻断后续（`POST_MERGE_FOLLOWUP`，本批未处理）：
`register_workflow_contract_profile` 重复注册为静默覆盖；
`method_by_action` 值类型未校验（非字符串会 `TypeError`，被 `core_extension` 的 `try/except` 兜住）；
`schema_guard` 的 `ts_derives_business_list` 只校验派生表达式形状、不比对结果集合；
`completeness_guard` 的 `can_review` 消费判定是存在性代理；
本段落的 v2 定向验证表未列 `stable_projection`（已在上方补登）。

复核者未能独立复核的部分：其运行环境无 `odoo` 模块，故 `TestWorkflowContractBackend`
的 `0 failed / 7 error` 由其未复核；本批在注册环境（`sc_dev_demo`）自行跑过该套件，结论见上文表格。

## 守卫注册表 false-orphan 收口（2026-09-29，FE-GUARD-REGISTRY-01）

### 定性：既有失败，非本批引入

`verify.guard.registry`（属 `ci.professional.backend` 专业质量门禁）在本批开工前即报两条：

```text
✗ orphan script 'test_frontend_standard_preview.py' is not acknowledged in registry.yaml
✗ orphan script 'test_workspace_composition_wiring.py' is not acknowledged in registry.yaml
```

按“是否既有应对照实际专题基线判断”，用不可变对象核对，而不是只跑一遍看它也红：

| 证据 | 结果 |
|---|---|
| 两个脚本是否在本批 diff（`c4b419878..fb51e465b`）内 | 否 |
| 基线 `c4b419878` 是否存在这两个脚本 | 是 |
| 基线 `c4b419878` 的 `registry.yaml` 是否已承认二者 | 否 |
| 基线 `c4b419878` 的引用正则与 HEAD 是否一致 | 一致（`SCRIPT_REFERENCE_RE` / `IMPORT_REFERENCE_RE` 字节相同） |
| 基线 make 是否已以同一形式引用二者 | 是（`make/runtime_ops.mk:150`、`make/frontend.mk:929`） |

⇒ 基线必然 FAIL。属既有失败，与本批契约改动无关。

### 根因：引用检测不覆盖点分模块调用形式

`guard_registry_audit.py` 的引用判定只用两类证据：脚本文件名（含 `.py`/`.sh`）与 Python import 语句。
这两个脚本在 make 中的真实引用形式是

```make
python3 -m unittest scripts.verify.test_frontend_standard_preview
python3 -m unittest scripts.verify.test_workspace_composition_wiring
```

既无 `.py` 后缀，也不是 import，于是被判为 orphan —— **false orphan**，脚本其实有消费者。

### 处理：跟随仓库既有登记惯例

registry.yaml 里**已有同类先例**：`test_frontend_system_state_recovery_guard.py`、
`test_frontend_page_pattern_reference_parity_guard.py`、`test_form_structure_authority_unification.py`、
`test_gitee_ci_acceptance.py` / `_checks` / `_incremental_update` 等条目都是 `status: orphan`，
`reason` 写明 “invoked by make/… through Python unittest module notation; registry static scan does not
recognize that invocation form”。本批按完全相同的体例补两条，保持 registry 文本单行风格：

```yaml
- script: test_frontend_standard_preview.py
  status: orphan
  owner: platform-team
  date: '2026-09-29'
  review_by: '2026-09-30'
  reason: invoked by make/runtime_ops.mk through Python unittest module notation (scripts.verify.test_frontend_standard_preview); registry static scan does not recognize that invocation form
```

```yaml
- script: test_workspace_composition_wiring.py
  status: orphan
  owner: platform-team
  date: '2026-09-29'
  review_by: '2026-09-30'
  reason: invoked by make/frontend.mk through Python unittest module notation (scripts.verify.test_workspace_composition_wiring); registry static scan does not recognize that invocation form
```

`guard_registry_audit.py` 与 `docs/audit/guard_registry/guard_registry.json` 均未改动：前者不必为本批
改判定语义，后者无任何 make/CI 消费者、且在本批之前已落后于 registry 多次变更（`counts` 差 6 active /
2 orphan），不为它引入 117 行无关刷新噪声。

### 为什么不改引用正则

把 `-m unittest/pytest <dotted.module>` 纳入检测会让 **33 个脚本**从 orphan 翻转为 active
（`test_gitee_*.py` 一系、`test_product_*_wave1_guard.py` 一系、`test_local_dev_*.py` 等）。
其中 11 个当前以 `orphan` 登记、10 个未登记，其余已 active。翻转后这些 `orphan` 条目立刻变成
guard 自身定义下的 stale，需一并重写 registry 的三十余条状态。那是一次注册表治理重写，
超出本轮“最小定向修复”范围，因此不动引用正则。

### 顺带发现的 guard 缺陷（登记，不在本批修）

guard 的 docstring 把 `active-dynamic` 指定为这类 false orphan 的承认方式，但实测该分支实现与文档相反：

```python
if entry and entry.get("status") == STATUS_ACTIVE_DYNAMIC and item["status"] != STATUS_ACTIVE:
    failures.append("claims active-dynamic but no static reference exists and it is not orphan-acknowledged")
```

判定要求脚本“静态可见”，而该状态的语义恰是“静态看不见但确有引用”，于是 `active-dynamic`
在任何情况下都不可用（registry 中 0 条使用印证）。这是 guard 自身的实现缺陷，属 P4 ops 工具治理，
**不在本批（契约词汇表）范围**，不引入首例状态语义变化，登记为后续项。

### 定向验证

| 命令 | 结果 |
|---|---|
| `python3 scripts/verify/guard_registry_audit.py` | **PASS** `1342 scripts (1218 referenced, 124/124 orphans acknowledged, 1 retired)`，`exit=0` |
| `python3 -m unittest scripts.verify.test_guard_registry_audit` | 2 tests OK |
| `python3 -m unittest scripts.verify.test_registry_audit_environment` | 18 tests OK |
| `make ci.local.iteration` | PASS `change_state=dirty coverage=L1_only` |

改动前后 `orphan` 承认数由 122 增至 124，与新增两条登记一致；`referenced` 1218 不变，
说明未把任何真实脚本误判成“有引用”。

### 与 style_system.guard 的边界

`verify.frontend.style_system.guard` 实测 3 项，均为文件长度超限：

```text
- frontend/apps/web/src/pages/ContractFormPage.vue exceeds 1900 lines: 1903
- frontend/apps/web/src/views/ActionView.vue exceeds 3800 lines: 3803
- record runtime exceeds 619 lines: frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts=621
```

三文件在本批 diff 中未触及，且基线 `c4b419878` 与 HEAD 行数完全一致（1903/1903、3803/3803、621/621），
未扩大。按既有口径独立保留，不靠放宽阈值、压缩行数或忽略文件消红。
（此前记录中的“四项”含 `ScRelationField.vue` 的 z-index 一项，该标识现已不在仓库中，故本轮实测为 3 项。）

### 候选与运行来源

- 本段收口只动 `scripts/verify/registry.yaml`（+12 行）与本记录。
- 未重跑 89 入口、全站发布验收或四项必需检查的其余部分；未推送、未合并、未部署目标环境。

### 状态

本批**批次验收完成**。`verify.guard.registry` 红项关闭；`style_system.guard` 三项为明确的既有非阻断债务；
guard 自身 `active-dynamic` 分支缺陷已登记，未在本批扩大处理。

## 后端自证完备性：复核登记的 followup 收口（2026-09-29，FE-CONTRACT-SELFPROOF-01）

上一批独立复核在 `FE-CONTRACT-VOCAB-01` 段落登记了四项 `POST_MERGE_FOLLOWUP`。本段逐项收口，
不重开该批已通过的结论，只关闭这四条。

### 1. 重复注册静默覆盖（P0 注册表）

`register_workflow_contract_profile` 对同一 model 的第二次不同声明直接改写 `_WORKFLOW_CONTRACT_PROFILE_REGISTRY`，
于是“哪个 owner 生效”取决于模块导入顺序。

处理：第二次声明不再覆盖。

- 内容与已注册项相同 → 幂等 `True`（允许重复 import / 热加载）；
- 内容不同 → 拒绝 `False`，追加一条 `_WORKFLOW_CONTRACT_PROFILE_CONFLICTS` 记录
  （`model` + `existing_source` + `incoming_source`）并输出 warning；第一个声明保留。

经 `contract_governance` facade 暴露 `workflow_contract_profile_conflicts()`，让冲突可见而不是靠导入顺序解决。
反例测试 `test_a_second_different_profile_for_the_same_model_is_refused` 同时断言“拒绝 + 保留第一份 + 冲突留痕”。

### 2. `method_by_action` 值类型未校验（P0 注册表）

原注册只做 truthy 检查。`{"submit": 123}` 能注册成功，直到 `_profile_is_executable` 调用
`hasattr(model, 123)` 抛 `TypeError`，被 `core_extension` 的 `try/except` 兜住 → **整个 profile 静默消失**。

处理：注册处校验 `method_by_action` 必须是 dict，键必须是去空白后的非空字符串，值必须是字符串或 `None`
（`None` 表示“声明为无方法”）。`_profile_is_executable` 增加同层防御：非字符串名直接判为不可执行，
不再依赖调用方的 `try/except`。

反例测试：非字符串值（`123` / dict / list / `True`）与非字符串键都被拒绝；`None` 值仍被接受。

### 3. `ts_derives_business_list` 只校验派生形状（前端派生守卫）

原实现只匹配 `Object.freeze(\s*ACTION_PURPOSES\.filter(`。把谓词改成
`... && purpose !== 'submit'` 后，形状仍匹配、两个数组字面量仍与权威相等，但派生结果集少一个 purpose。

处理：谓词固定为唯一的受控补集形式
`ACTION_PURPOSES.filter((x) => !(NON_BUSINESS_PURPOSES as readonly string[]).includes(x))`。
配合原本已校验的两个字面量（`ACTION_PURPOSES` / `NON_BUSINESS_PURPOSES` == 权威），结果集由此完全确定。

负例实测：加入额外谓词 → `verify.unified_page_contract.v2.schema` **FAIL**（
`the web business purpose list must be derived from ACTION_PURPOSES and NON_BUSINESS_PURPOSES`），恢复后 PASS。

### 4. `can_review` 消费判定是存在性代理（授权绑定守卫）

原 `references_marker` 只要求 `_available_actions` 函数体内**出现** `"can_review"` 常量，
因此只把 verdict 写进日志、或写成永不成立的分支，都能通过“运行时审批裁决被消费”这条检查。

处理：marker 必须出现在 `if` / `while` / 三元表达式的 **test** 内，且该 test 不能本身是字面常量。
真实实现 `if not bool(getattr(record, "can_review", False)): keys.remove(...)` 仍是合格形态。

负例实测：把两处 `getattr(record, "can_review", ...)` 换成别的名字、只保留一行
`_marker_only = "can_review"` 提及 → guard **FAIL**（
`workflow profiles publish approval actions without consulting the runtime approval verdict`），恢复后 PASS。

### 固化进现有测试

两个守卫此前没有回归测试，本次反例只存在于一次性探针里。新增两个单测文件并接到各自的 make target：

- `scripts/verify/test_unified_page_contract_v2_schema_guard.py`（3 tests）→ 接入 `verify.unified_page_contract.v2.schema`
- `scripts/verify/test_workflow_action_semantics_completeness_guard.py`（4 tests）→ 接入 `verify.workflow_contract.backend`

这样“代理检查”无法悄悄回归。

### 验证结果

| 命令 | 结果 |
|---|---|
| `python3 addons/smart_core/tests/test_workflow_contract_profile_registry.py` | 9 tests OK（新增 5 个反例） |
| `python3 scripts/verify/workflow_action_semantics_completeness_guard.py` | PASS `profiles=65 … verdict_covers=4` |
| `python3 scripts/verify/workflow_inventory_profile_method_guard.py` | PASS `profile_methods=29 inventory_methods=41` |
| `python3 scripts/verify/workflow_contract_custom_coverage_guard.py` | PASS（见下方基线说明） |
| `python3 scripts/verify/contract_governance_registry_split_guard.py` | PASS |
| `make verify.unified_page_contract.v2.schema` / `.assembler` / `.action` | 均 PASS |
| `make verify.unified_page_contract.v2`（含前端构建） | **exit=0** |
| `TestWorkflowContractBackend`（`sc_dev_demo`） | `0 failed, 7 error(s) of 28`，**error 集合与 stash 基线逐条一致**（全为环境数据类） |
| `make ci.local.iteration` | PASS `change_state=dirty` |

后端套件的 7 个 error 用 `git stash` 前后各跑一次逐条比对：改动前后测试名完全一致，
确认非本段引入。

### 踩到并还原的一次基线覆盖

`verify.workflow_contract.backend` 的前置 `audit.workflow_state.inventory` 会以注册库 `sc_dev_demo`
重新生成 `docs/audit/workflow_state_inventory_sc_demo.md`，覆盖这份历史 `sc_demo` 基线；
被覆盖后 `workflow_contract_custom_coverage_guard` 会报 13 个“意外未覆盖模型”。

本次已 `git checkout` 还原该文件，未把覆盖结果带入提交。**该 target 在当前注册库下不能整条直接跑**；
需要时按上面的清单逐条执行，跳过 inventory 前置。这是既有环境限制，非本段改动引入
（`git stash` 后同一 target 同样如此，因为 stash 一并还原了被覆盖的基线文件）。

### 未处理（保持登记）

- `docs/audit/workflow_state_inventory_sc_demo.md` 需在具备已装模块的 `sc_demo` 环境重新生成，本段不重生成。
- 跨仓 P2 注册（`sce-customer-baosheng-odoo` `bfbc736`，`sc.partner.import.review`）本次未跨仓运行验证；
  新语义下同内容重复注册仍是幂等 `True`，不影响其现有调用形态。

### 状态

本段**批次验收完成**。四项 followup 全部关闭；未推送、未合并、未部署目标环境。
