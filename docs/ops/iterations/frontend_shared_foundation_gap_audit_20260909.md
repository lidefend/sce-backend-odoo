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
- `Module`：`smart_core`、`smart_construction_core`、`sce_customer_<tenant_key>_legacy`（属主侧）。
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
- P2 属主侧提交：`sce-customer-<tenant_key>-odoo` `bfbc736`（`fix/native-form-preference-upgrade`），
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
- 跨仓 P2 注册（`sce-customer-<tenant_key>-odoo` `bfbc736`，`sc.partner.import.review`）本次未跨仓运行验证；
  新语义下同内容重复注册仍是幂等 `True`，不影响其现有调用形态。

### 状态

本段**批次验收完成**。四项 followup 全部关闭；未推送、未合并、未部署目标环境。

## 原生按钮 occurrence 覆盖收口：把未声明的 workflow 按钮显式登记（2026-09-29，FE-CONTRACT-NATIVEBTN-01）

上一段 `FE-CONTRACT-VOCAB-01` 登记了一项未闭合：「约 80 处未声明的原生按钮 occurrence 仍需按
『权威侧缺失 / 原生未登记』逐类定性」。本段把这条口径固定到可复算的范围内并闭合它，
不重开该批结论，不猜测任何业务语义。

### 1. 口径收敛：80 → 25 是收紧，不是问题消失

重枚举口径（可复算）：

- 扫 `addons/**/views/**/*.xml` 中 `model="ir.ui.view"` 记录里 `type="object"` 的 `<button>`；
- 按钮所属 `model` 必须**已有 workflow profile**（`workflow_contract_service.PROFILE_BY_MODEL`，共 **40** 个）；
- 按钮 `name` 必须**未被任何 profile 声明**（所有 `method_by_action` 取值合并收集，共 **29** 个）。

第三条是故意保守的：跨 profile 合并收集只会**少报**（一个模型声明了某方法，会顺带遮蔽另一个模型上同名按钮），
它不会凭空造出一个缺口。按模型精确判定需要执行各 profile builder，超出静态守卫的职责，不做。

结果：未声明 occurrence **25 处**，去重 **24 条 `(model, method)`**，覆盖 **16 个模型**、**17 个去重方法名**。
方法与模型的差来自两处一对多：`action_generate_lines_from_budget` 出现在 3 个模型、
`action_view_company_contractor_responsibility_summary` 出现在 6 个模型。

与旧登记的「约 80 处」相比，这是**口径收敛**：旧口径没有限定到被接管模型，也没有扣除跨 profile 已声明的同名方法。
每个被移除的 occurrence 都落在「不是被接管模型」或「方法已有声明」两类之一。

### 2. 登记分类（`config/contract/native_view_undeclared_actions.v1.json`，24 条）

| class | 条数 | 含义 |
|---|---|---|
| `navigation` | 11 | 打开关联记录／视图，不改变状态 |
| `document_helper` | 9 | 生成／加载／创建业务内容，不改变状态 |
| `state_transition_undeclared` | **4** | 真实改变记录状态，且没有任何 profile 声明承担它 |

前两类是「原生未登记」：它们不写状态，缺的只是显式登记，不是权威侧缺口。
第三类是「权威侧缺失」，逐条经过实现确认。

### 3. 四条 `state_transition_undeclared` 逐条定性

| model | method | 实测状态变化 | 定性 |
|---|---|---|---|
| `payment.request` | `action_set_approved` | `approve → approved`，`with_context(allow_transition=True, payment_soft_gate=True)`，两侧有 `_assert_finance_approve_access` | 该模型另有 `action_approve` 承担 `approve`，此第二条批准入口尚无声明 |
| `sc.general.contract` | `action_signed` | `draft/confirmed → signed` | profile 声明了 `signed` phase，却没有把任何动作投影进该 phase，签署在被接管页不可达 |
| `sc.payment.execution` | `action_reverse_payment` | `paid → ` 冲销，有 `_assert_finance_cancel_access` 且 `raise_guard("PAYMENT_EXECUTION_REVERSAL_INVALID_STATE")`，**未**用 `allow_transition` 绕过 | 无 profile 动作覆盖冲销 |
| `sc.project.document` | `action_reset_to_draft` | `state='draft'` 重置 | 该模型未声明 `reopen` 类动作 |

四条**都不擅自补 purpose**。是否要为原生转移补一条声明，是业务权威的判断，不是守卫或适配器能自行发明的。
本段只把它们从「静默消失」变成「显式登记」，让缺口可见。

### 4. 守卫机制与 fail-closed 四类（`scripts/verify/native_view_workflow_action_coverage_guard.py`）

守卫只做「显式登记 + 双向往返」，不提议任何含义。四类检查全部 fail-closed：

1. 接管模型上的原生 object 按钮既未被声明、也不在登记表 → **FAIL**（新缺口无法静默进入）；
2. 登记条目已不再对应任何原生按钮 → **FAIL**（stale，登记不能留存过期的缺口）；
3. 登记条目对应的方法现在已被 profile 声明 → **FAIL**（登记不得比它记录的缺口活得更久）；
4. 条目缺 `reason` 或 `class` 不在 `{state_transition_undeclared, navigation, document_helper}` → **FAIL**。

### 5. 与 `workflow_action_semantics_completeness_guard` 的口径关系

两个守卫口径起点相同（「原生呈现 vs 契约声明」），方向互补，不是重复：

- `completeness_guard` 从**声明侧**出发：profile 声明了某 `(kind, executor, purpose)` 组合，端上是否有真实消费者；
- 本守卫从**原生呈现侧**出发：原生视图里真实存在一个 object 按钮，契约侧是否有任何声明承担它。

一个抓「声明了没人用」，一个抓「存在了没人声明」。合起来才是双向闭合。

### 6. 修正一条旧说法

旧登记里写着「`construction.contract` 的 `activate/complete` 只读详情面不渲染 header 动作，属前端
presentation 可达性缺口」。本轮实测确认：`construction.contract` 的 profile **有** `state_actions`
（`draft: submit/cancel`、`confirmed: activate/complete/cancel`、`running: complete/cancel`、`cancel: reopen`），
且 `activate → action_set_running`、`complete → action_close` 均已声明；原生 `contract_views.xml` 里这两个
object 按钮也真实存在。因此它们**不在**本守卫的未声明集合内，此前若把它读成契约缺口是不准确的。

它是「已声明，端上是否渲染」的 presentation 面，本段不改变该登记、也不以本守卫覆盖它。

### 7. 接入现有门禁（不新建治理体系）

- 新 target `verify.native_view.workflow_action_coverage`：`py_compile` + 守卫 + 8 个单测；
- 登记进 `verify.unified_page_contract.v2` 与 `verify.unified_page_contract.v2.professional_backend` 两个聚合
  （与 `verify.unified_page_contract.v2.action` 相邻，同族）；
- 同步登记进 `scripts/verify/unified_page_contract_v2_guard_inventory.py` 的 `OFFLINE_TARGETS`，
  否则该 inventory guard 会报聚合依赖漂移；
- `scripts/verify/guard_registry_audit.py` 因脚本已被 make 引用，不再是 orphan，无需 registry.yaml 条目。

### 8. 负例实测（全部按预期 FAIL）

| 人造偏差 | 期望 | 实测 |
|---|---|---|
| baseline 原样 | PASS | PASS `registered=24 document_helper=9 navigation=11 state_transition_undeclared=4` |
| 删掉一条登记条目 | FAIL | FAIL（`no native form view uses it anymore` 之外的未登记缺口被报出） |
| 登记一条幽灵条目（原生不存在） | stale FAIL | FAIL |
| 登记一条已被 profile 声明的方法 | stale FAIL | FAIL |
| 条目去掉 `reason` | FAIL | FAIL |
| 条目 `class` 改成非法值 | FAIL | FAIL |

### 9. 验证结果

| 命令 | 结果 |
|---|---|
| `make verify.native_view.workflow_action_coverage` | PASS（守卫 + 8 tests OK） |
| `python3 scripts/verify/guard_registry_audit.py` | AUDIT PASS `1346 scripts (1222 referenced, 124/124 orphans acknowledged, 1 retired)` |
| `make verify.unified_page_contract.v2`（含前端构建） | **exit=0** |
| `make verify.unified_page_contract.v2.professional_backend` | **exit=0**（inventory PASS、web_architecture PASS debt_lock findings=0 等） |
| `make ci.local.iteration` | PASS `change_state=dirty scope=unclassified_by_design coverage=L1_only` |

未运行 `verify.workflow_contract.backend` 整条：其 `audit.workflow_state.inventory` 前置会污染历史
`sc_demo` 基线，属既有环境限制（见上一段说明），与本次改动无关。

### 10. 七问

- **Formal Product Layer**：守卫与登记表属 **P4 ops/verify 工具**（`scripts/verify`、`config/contract` 的显式登记）；
  被扫描的契约声明属 **P0 平台机制**（`smart_core` 动作语义词汇表）+ **P1 行业标准**（`smart_construction_core`
  的 workflow profile）。不引入任何新的业务层语义。
- **Layer Target**：`scripts/verify/native_view_workflow_action_coverage_guard.py`、
  `scripts/verify/test_native_view_workflow_action_coverage_guard.py`、
  `config/contract/native_view_undeclared_actions.v1.json`、`make/ci.mk`、
  `scripts/verify/unified_page_contract_v2_guard_inventory.py`。
- **Module**：`scripts/verify`（守卫/测试）+ 仓库级 `make` 门禁；被扫描对象是 `smart_construction_core` 的
  workflow profile 与各模块原生视图。
- **Standard vs User-Specific**：平台机制层——「原生呈现 vs 契约声明」的覆盖口径对每个部署一致，非客户偏好。
- **Why Here**：登记表落在 `config/contract/`，与其它契约侧登记同址；守卫落在 `scripts/verify`，与
  `workflow_action_semantics_completeness_guard` 同址；接入现有 v2 聚合，不新增体系。
- **Why Not Elsewhere**：不改 `workflow_contract_service.py` 去补 purpose——那会由守卫发明业务语义；
  不改前端渲染去隐藏按钮——那是让缺口更不可见；不新增独立门禁平台——现有 v2 聚合已覆盖同族口径。
- **Blast Radius**：新增一个只读静态守卫 + 一张登记表 + 两处聚合依赖登记。不改业务模型、不改契约投影、
  不改前端渲染、不改权限。受影响面仅为 `verify.unified_page_contract.v2*` 门禁，已验证 `exit=0`。

### 状态

本段**批次验收完成**。未推送、未合并、未部署目标环境；业务矩阵状态不变。
四条 `state_transition_undeclared` 保持为**权威侧待决**，不是本轮阻断项，也不因本段自动消项。

## 契约接管模型集口径修正：把 helper 生成的 profile 纳入扫描（2026-09-29，FE-CONTRACT-NATIVEBTN-02）

上一段 `FE-CONTRACT-NATIVEBTN-01` 的守卫用正则从源码文本里抓「被接管模型」，
结果只认内联字面量，漏掉了通过 helper 调用生成的 profile。本段修掉这个口径，
并把它暴露的缺口补齐。

### 1. 根因：正则只看得见一半注册表

上一段 `adopted_models()` 的匹配式是
`"\n        \"<model>\": \{\n            \"state_field\""` —— 它要求 model 键**紧跟**一个内联的
`state_field`。而 `PROFILE_BY_MODEL` 里还有另一类条目：

```python
**_simple_approval_profiles(("sc.equipment.plan", "sc.labor.plan", ...)),
**_close_issue_profiles(("sc.quality.issue", "sc.safety.issue")),
**_submit_confirm_profiles((...)), **_in_progress_done_profiles((...)), **_confirm_done_profiles((...)),
```

这些 helper 每个都返回**完整的 profile**（含 `state_field` / `state_phase` /
`state_actions` / `method_by_action`），但它们在源码里不是内联字面量，正则抓不到。

实测口径差：

| 口径 | 被接管模型 |
|---|---|
| 上一段正则（内联字面量） | 40 |
| 静态求值 `PROFILE_BY_MODEL`（含 helper 展开） | **65** |

被漏掉的 25 个模型：`sc.dashboard.cockpit.fact`、`sc.document.admin.document`、
`sc.equipment.plan/request/settlement/usage`、`sc.fund.account.operation`、
`sc.hr.payroll.document`、`sc.labor.plan/request/settlement/usage`、
`sc.material.purchase.request`、`sc.material.rental.plan`、`sc.material.settlement`、
`sc.office.admin.document`、`sc.plan`、`sc.quality.issue`、`sc.safety.disclosure/issue/plan`、
`sc.subcontract.plan/request/settlement`、`sc.workbench.item`。

### 2. 影响：7 条未声明原生按钮从未被检查

把这 25 个模型纳入扫描后，原「24 条登记」之外多出 7 条未声明按钮：

| model | method | class | 实测行为 |
|---|---|---|---|
| `sc.material.purchase.request` | `action_create_rfq` | `document_helper` | `create` `sc.material.rfq`，不改自身状态 |
| `sc.material.purchase.request` | `action_create_purchase_order` | `document_helper` | `create` `purchase.order`，不改自身状态 |
| `sc.material.purchase.request` | `action_view_rfqs` | `navigation` | 返回 `ir.actions.act_window` |
| `sc.material.purchase.request` | `action_view_purchase_orders` | `navigation` | 返回 `ir.actions.act_window` |
| `sc.material.settlement` | `action_create_remaining_payment_request` | `document_helper` | `create` `payment.request`，自身状态不变 |
| `sc.material.settlement` | `action_open_payment_request` | `navigation` | 返回 `ir.actions.act_window` |
| `sc.plan` | `action_start` | **`state_transition_undeclared`** | `write({"state": "in_progress"})`，`confirmed → in_progress` |

登记表因此从 24 条 / 25 occurrence / 16 模型变为 **31 条 / 32 occurrence / 19 模型**
（`navigation` 11→14、`document_helper` 9→12、`state_transition_undeclared` 4→5）。

### 3. `sc.plan.action_start` 同时是一条相位可达性缺口

`sc.plan` 的 profile（经 `_confirm_done_profiles` 生成）声明了
`state_phase = {draft, confirmed, in_progress, done, cancel, cancelled, legacy_confirmed}`，
但 `state_actions` 的 `confirmed` 只有 `["complete", "reopen", "cancel"]` ——
**没有任何声明动作能进入 `in_progress`**。原生视图里 `action_start` 正是那个入口
（`invisible="state != 'confirmed'"`，`string="开始执行"`）。

这与 `sc.general.contract.action_signed` 是同一类问题：**phase 声明了，进入它的动作没有声明**。
本段仍按既定口径处理——登记、定性，不擅自补 purpose。

### 4. 验收体系为什么没发现

上一段的 8 个单测全部只做一件事：**验证守卫与它自己的登记表自洽**
（登记一致、移除条目 FAIL、幽灵条目 stale、缺 reason FAIL……）。
它们没有一条独立断言 **「守卫扫描的模型集 == 契约实际注册的模型集」**。
于是「正则少抓 25 个模型」和「登记表也少 24 条」可以同时成立，两边互相印证，测试全绿。

这正是「静默补齐」的镜像：不是前端补了业务语义，而是**验收工具静默缩小了自己的作用域**。

### 5. 修复：用静态求值替代模式匹配，并把范围断言钉进单测

新增 `scripts/verify/workflow_contract_profile_loader.py`：

- 用 AST 求值 `PROFILE_BY_MODEL` 表达式，支持内联字面量、helper 调用、`**` 展开、`_()` 标记；
- 只接受字面量表达式的白名单；遇到不支持的结构（推导式、模块属性、条件表达式……）
  **抛 `ProfileSourceError` 而不是返回部分结果** —— 消费者永远不该静默扫一个子集；
- 空注册表、非 dict 的 profile 条目同样拒绝。

`native_view_workflow_action_coverage_guard.py` 的 `adopted_models()` /
`declared_methods()` 改为调用该 loader；读不到注册表时守卫以 exit 1 fail-closed。

补的单测：

- `test_workflow_contract_profile_loader.py`（8 tests）：真实注册表读全、helper 生成的
  `sc.plan` 在内、helper 绑定的方法计入声明集、`**` 展开、以及四类 fail-closed
  （不支持的表达式 / 缺注册表 / 空注册表 / 非 profile 条目）；
- `test_native_view_workflow_action_coverage_guard.py` 新增 2 tests（共 10）：
  `test_helper_built_profiles_are_scanned_too` 断言几个 helper 生成的模型确实在扫描集里；
  `test_a_helper_built_model_transition_must_be_registered` 断言移除 `action_start`
  登记后守卫会 FAIL。

### 6. 七问

- **Formal Product Layer**：P4 ops/verify 工具（`scripts/verify`、`config/contract` 登记）。
  不引入业务语义。
- **Layer Target**：`scripts/verify/workflow_contract_profile_loader.py`、
  `scripts/verify/native_view_workflow_action_coverage_guard.py`、
  `scripts/verify/test_workflow_contract_profile_loader.py`、
  `scripts/verify/test_native_view_workflow_action_coverage_guard.py`、
  `config/contract/native_view_undeclared_actions.v1.json`、`make/ci.mk`、
  `scripts/verify/unified_page_contract_v2_guard_inventory.py`。
- **Module**：`scripts/verify` + 仓库级 `make` 门禁；被扫描对象仍是 `smart_construction_core`
  的 workflow profile 与各模块原生视图。
- **Standard vs User-Specific**：平台机制层——「契约声明 vs 原生呈现」的覆盖口径对每个部署一致。
- **Why Here**：loader 与守卫同址；登记表与其它契约侧登记同址；仍挂在既有 v2 聚合下。
- **Why Not Elsewhere**：不改 `workflow_contract_service.py` 去补 purpose（那是发明业务语义，
  仍由业务权威决定）；不改前端渲染去隐藏按钮；不为了迁就旧正则而恢复内联写法。
- **Blast Radius**：新增一个只读静态模块与两个单测；登记表 31 条；两处聚合依赖不变。
  不改业务模型、契约投影、前端渲染、权限。受影响面仅为 `verify.unified_page_contract.v2*`，已验证 exit=0。

### 7. 验证结果

| 命令 | 结果 |
|---|---|
| `make verify.native_view.workflow_action_coverage` | PASS（`registered=31 document_helper=12 navigation=14 state_transition_undeclared=5`；8 + 10 tests OK） |
| 口径反证：回填旧正则模型集 | `models=40 undeclared=24 has_action_start=False`；求值口径 `models=65 undeclared=31 has_action_start=True` |
| `python3 scripts/verify/guard_registry_audit.py` | AUDIT PASS `1348 scripts (1224 referenced, 124/124 orphans acknowledged, 1 retired)` |
| `make ci.generated_reports.guard` | PASS（test inventory 1416 entries 等全部 current） |
| `make verify.unified_page_contract.v2`（含前端构建） | **exit=0** |
| `make verify.unified_page_contract.v2.professional_backend` | **exit=0** |
| `make ci.local.iteration` | PASS `change_state=dirty` |

### 8. 剩余（显式登记，不在本段）

- **phase 覆盖完备性**尚未守卫：`state_phase` 是否覆盖该模型 `state` selection 的全部取值。
  已验证 34/40 内联模型可直接 AST 解析、其余 6 个经 `ScStateMachine.selection(...)`；
  当前已知一处真实缺口：`sc.general.contract` 的 `legacy_confirmed` 未在 `state_phase` 中声明
  （同类模型如 `sc.expense.claim`、`sc.payment.execution` 都声明了该相位）。这是**投影缺口**，
  应改契约投影；本段不顺手改，避免把两个口径混在一笔里。
- **phase 可达性**：`sc.plan.in_progress`、`sc.general.contract.signed` 已通过
  `state_transition_undeclared` 登记显式化；是否补声明由业务权威决定。

### 状态

本段**批次验收完成**。未推送、未合并、未部署目标环境；业务矩阵状态不变。

## 相位覆盖完备性守卫：把 `state_phase` 的取值集双向钉死（2026-09-29，FE-CONTRACT-PHASECOV-01）

上一段 `FE-CONTRACT-NATIVEBTN-02` 第 8 节登记了「`state_phase` 是否覆盖该模型 `state`
selection 的全部取值」尚未守卫，并明确本轮不顺手改。本段收口这一项：补掉登记里那处真实缺口，
并把覆盖口径做成静态守卫。

### 1. 先确认 `state_phase` 是真实运行语义，不是装饰

`state_phase` 在前端源码里没有任何字面引用，容易被读成「只为展示的映射表」。实际消费链在
`addons/smart_construction_core/models/support/workflow_contract_service.py`：

```python
business_phase = profile["state_phase"].get(raw_state, raw_state or "unknown")   # 第 976 行
```

`business_phase` 随后驱动三处判定并发布到端上：

| 派生结果 | 位置 | 未映射时的行为 |
|---|---|---|
| `editability` | `_editability()`（第 1028 行） | 用 raw token 去比 `field_editable_phases` / `TERMINAL_PHASES` / `editable_phases` |
| `approvalPhase` | `_approval_phase()`（第 1012 行） | 只对 `approved/done/legacy_confirmed` 等已知相位生效 |
| `statusbar` / `businessPhase` | `_statusbar_projection()`（第 991 行） | 把 raw token 当相位发布，并落 `STATUSBAR_EXTRA_LABELS` 兜底标签 |

所以缺一条映射不是「显示少了几个字」：**一个真实业务相位会走兜底分支**，而兜底恰好返回相同字符串时
一切看起来都对——这正是这类缺口能长期存活的原因。

### 2. 状态集的权威来源：源码静态解析，不是生成报告

`docs/audit/workflow_state_inventory_sc_demo.md` 是运行时快照，但它对
`construction.contract.expense/income` 只能渲染成 `<callable>`（这两个模型经
`_inherits` 委派到 `construction.contract`），对静态解析不到的模型无法给结论。用它当守卫权威，
等于把「静默跳过」写进守卫本身。

改用源码静态解析，解析不到就 FAIL：

| 形态 | 解析方式 |
|---|---|
| `state = fields.Selection([...])` | 字面量表求值（含 `_()` 包裹） |
| `ScStateMachine.selection(ScStateMachine.X)` | 解析 `state_machine.py` 的 `X_STATES`（5 个：`CONTRACT`/`PAYMENT_REQUEST`/`SETTLEMENT`/`SETTLEMENT_ORDER`/`PROJECT`） |
| `_inherits = {"construction.contract": ...}` | 跟随委派基类 |
| `_inherit = ["sc.business.fact.mixin", ...]` | 跟随 mixin |

解析结果是**并集**：只可能多报（可见的 FAIL），不可能少报（静默 PASS）。

对 63 个快照可枚举的模型做交叉校验：**静态解析结果与运行时快照 63/63 完全一致**，0 处差异 ——
证明解析器没有少解析，也没有把 mixin 使用者的取值并进被复用模型。

### 3. 实测缺口与修复

| model | 缺口 | 定性 |
|---|---|---|
| `sc.general.contract` | `legacy_confirmed` 未在 `state_phase` | **投影缺口**，P1 行业标准层 |

`sc.general.contract` 的 selection 是 `draft/confirmed/signed/legacy_confirmed/cancel`；
`legacy_confirmed` 在模型里是真实状态（`general_contract.py:23-30`），又被
`TERMINAL_PHASES`、`_approval_phase()`、`STATUSBAR_EXTRA_LABELS` 三处按相位名识别，
但 profile 忘了声明它。同型模型（`sc.expense.claim`、`sc.payment.execution`、
`sc.invoice.registration`、`sc.settlement.adjustment`）都声明了该相位。

修复是 `state_phase` 补一行 `"legacy_confirmed": "legacy_confirmed"`。

**诚实说明**：本例兜底返回值与映射值同为 `legacy_confirmed`，所以今天的
`businessPhase` / `editability` / `approvalPhase` 用户可见结果**没有变化**。这是**潜在**缺口
（下一个加入 selection 的取值就不会这么幸运），不是已发生的用户故障。按「缺口必须显现」登记并修复，
不按「已经出事了」夸大。

### 4. 反向口径：死条目必须有登记，不能静默存在

同一个查找键方向还有反向问题：profile 声明了 `Selection` 永远产生不了的 key。
扫描实测 **12 个模型**有这种情况，全部来自共享 helper 模板的防御性别名：

| 来源模板 | 模型 | 死条目 |
|---|---|---|
| `_simple_approval_profiles` | `sc.equipment.plan/request`、`sc.labor.plan/request`、`sc.material.purchase.request`、`sc.material.rental.plan`、`sc.safety.disclosure/plan`、`sc.subcontract.plan/request` | `phase:submit`、`phase:rejected`、`actions:submit`、`actions:rejected` |
| `_confirm_done_profiles` | `sc.fund.account.operation` | `phase:cancel`、`phase:in_progress`、`phase:legacy_confirmed`、`actions:cancel`、`actions:in_progress` |
| `_confirm_done_profiles` | `sc.plan` | `phase:cancelled`、`phase:legacy_confirmed`、`actions:cancelled` |

模板按 `payment.request` 的取值集写成（那里真有 `submit`），不是每个成员模型都有。
运行期无害（查找键是记录的真实 raw state），但**profile 与模型在互相矛盾**。

本段不改这 12 个 profile（那是对 12 个模型做配置编辑，不在授权范围），改为登记进
`config/contract/workflow_state_phase_dead_entries.v1.json`，键集精确匹配、必须带 reason、
登记表过期同样 FAIL。

### 5. 守卫与 fail-closed

`scripts/verify/workflow_state_phase_coverage_guard.py`：

- 覆盖缺口 → FAIL（无可豁免通道：补映射或改模型，二选一）；
- 未登记死条目 → FAIL；登记表 stale / 键集不符 / 缺 reason → FAIL；
- 某模型 selection 解析不到 → FAIL 并单独报该模型（**不跳过**）；
- profile 注册表读不全（复用 `workflow_contract_profile_loader`）→ FAIL；
- 扫描数不等于 profile 数 → FAIL（防止守卫自身缩小作用域）。

复用 `workflow_contract_profile_loader`，不再写第二套注册表读取。

### 6. 负例实测（真实仓库，全部按预期 FAIL）

| 人造偏差 | 期望 | 实测 |
|---|---|---|
| 移除 `sc.general.contract` 的 `legacy_confirmed` 映射 | FAIL | FAIL `raw state ['legacy_confirmed'] is absent from state_phase` |
| 删掉 `sc.plan` 死条目登记 | FAIL | FAIL `sc.plan: ['actions:cancelled', 'phase:cancelled', 'phase:legacy_confirmed'] ... register it` |
| 登记一个没有死条目的模型 | stale FAIL | FAIL `registered ... but none were found` |
| 死条目去掉 reason | FAIL | FAIL `registered without a reason` |
| 后端断言：移除映射后跑真实 Odoo 检验 | FAIL | FAIL `AssertionError: None != 'legacy_confirmed'` |

### 7. 验收体系为什么之前没发现

上一段的 8+10 个单测只验证「守卫与它自己的登记表自洽」。相位覆盖这一类**根本没有断言**，
所以 `state_phase` 缺一条 key、以及 12 个模型的死条目可以长期存在而全套门禁全绿。
与上一段同一病根：**工具没有声明自己的作用域**。本段把作用域断言直接钉进守卫
（`scanned != len(profiles)` 即 FAIL），并把它挂进既有 v2 聚合。

### 8. 七问

- **Formal Product Layer**：被修的 `state_phase` 属 **P1 行业标准产品**
  （`smart_construction_core` 的 workflow profile 与状态机，每个标准部署一致继承）；
  守卫与登记表属 **P4 ops/verify 工具**。
- **Layer Target**：`addons/smart_construction_core/models/support/workflow_contract_service.py`、
  `scripts/verify/workflow_state_phase_coverage_guard.py`、
  `scripts/verify/test_workflow_state_phase_coverage_guard.py`、
  `config/contract/workflow_state_phase_dead_entries.v1.json`、
  `addons/smart_construction_core/tests/test_workflow_contract_backend.py`、`make/ci.mk`、
  `scripts/verify/unified_page_contract_v2_guard_inventory.py`。
- **Module**：`smart_construction_core`（契约投影 + 后端断言）；`scripts/verify`（守卫/测试）。
- **Standard vs User-Specific**：标准——`state_phase` 是行业标准的生命周期投影，
  不是客户偏好，不进 `smart_construction_custom`，也不进低代码运行时。
- **Why Here**：相位投影与状态机同在 `smart_construction_core`；覆盖口径与 loader 同址；
  登记表与其它契约侧登记同址；仍挂在既有 `verify.unified_page_contract.v2*` 聚合下。
- **Why Not Elsewhere**：不改前端去兜底相位猜测（那正是要禁止的「前端发明业务语义」）；
  不把 12 个 profile 顺手改掉（配置编辑超出本轮授权，改为登记）；不新建治理文档或门禁平台。
- **Blast Radius**：1 行 profile 声明 + 1 个静态守卫 + 1 张登记表 + 1 条后端断言；
  不改业务模型、不改状态机、不改前端渲染、不改权限。
  受影响面为 `verify.unified_page_contract.v2`、`.professional_backend` 及其新 target。

### 9. 验证结果

| 命令 | 结果 |
|---|---|
| `make verify.workflow_state_phase_coverage` | PASS `models=65 covered=65 dead_registered=12`；16 tests OK |
| `make verify.native_view.workflow_action_coverage` | PASS（相邻守卫未受影响，10 tests OK） |
| 后端单方法（`TEST_TAGS=/smart_construction_core:TestWorkflowContractBackend.test_general_contract_legacy_confirmed_phase_is_declared`，DB `sc_dev_demo`） | PASS `0 failed, 0 error(s) of 1 tests` |
| `python3 scripts/verify/workflow_inventory_profile_method_guard.py` | PASS |
| `python3 scripts/verify/workflow_contract_custom_coverage_guard.py` | PASS |
| `python3 scripts/verify/workflow_action_semantics_completeness_guard.py` | PASS `profiles=65` |
| `make verify.unified_page_contract.v2.guard_inventory` | PASS |
| `make verify.unified_page_contract.v2.professional_backend` | PASS |
| `make verify.unified_page_contract.v2`（含前端构建） | **exit=0** |
| `make refresh.generated_reports` + `make ci.generated_reports.guard` | PASS（test inventory 1418 entries） |
| `make architecture.complexity_baseline_lock` | PASS `checked=11` |
| `python3 scripts/verify/guard_registry_audit.py` | AUDIT PASS `1350 scripts (1226 referenced, 124/124 orphans acknowledged, 1 retired)` |
| `make ci.local.iteration` | PASS `change_state=dirty coverage=L1_only` |

未运行 `verify.workflow_contract.backend` 整条：其 `audit.workflow_state.inventory` 前置会用注册库
覆盖历史 `sc_demo` 基线，属既有环境限制（见 `FE-CONTRACT-NATIVEBTN-01` 说明），与本段改动无关。
本段以「守卫 + 单测 + 一条真实 Odoo 断言」覆盖同一口径，不重复整条门禁。

### 10. 剩余（显式登记，不在本段）

- 12 个模型的死条目仍留在 profile 里（已登记，未删）。删除是对 12 个业务模型做配置编辑，
  应与相位语义复核一起做，不在本轮授权范围。
- `state_transition_undeclared` 五条（`payment.request.action_set_approved`、
  `sc.general.contract.action_signed`、`sc.payment.execution.action_reverse_payment`、
  `sc.plan.action_start`、`sc.project.document.action_reset_to_draft`）仍为**权威侧待决**，
  不因本段消项。
- `style_system.guard` 文件长度四项欠账独立保留，本段未触及。

### 状态

本段**批次验收完成**。未推送、未合并、未部署目标环境；业务矩阵状态不变。

---

## FE-CONTRACT-DEADPHASE-01：共享审批模板的不可达相位收口

起点 HEAD `119e1ea50`（干净）。本段只删除**没有成员能取到的相位/动作**，并让对应原生按钮在模型真正接受的状态出现。
不新增业务动作、不改状态机语义、不重写模板体系。

### 1. 七问

- **Formal Product Layer**：P1 建筑行业标准产品（`sc.*` 计划/申请族的共享审批语义）。
- **Layer Target**：`smart_construction_core`，`models/support/workflow_contract_service.py`
  的 `_simple_approval_profiles()` 模板 + 五个原生 form 的 `action_reset_draft` 可见性。
- **Module**：`smart_construction_core`。
- **Standard vs User-Specific**：行业标准。10 个成员的 `state` Selection 都是
  `draft/submitted/approved/cancel`，这是产品标准，不是客户偏好；因此修正落在标准模块而不是
  `smart_construction_custom` 或低代码运行时。
- **Why Here**：模板与原生视图同属该族标准定义处，删除残留与修正按钮可见性都在此层闭环。
- **Why Not Elsewhere**：不放前端（前端只消费契约，不能替契约删状态）、不放低代码配置
  （不是运行期偏好）、不放 ops 脚本（不是一次性修复）。
- **Blast Radius**：10 个模型的 `describe_record` 相位表与 form 头部按钮；由
  `verify.workflow_state_phase_coverage`（65/65）与新增后端用例共同证明收敛。

### 2. 真实缺陷

`_simple_approval_profiles` 是 10 个计划/申请模型共用的模板，长期带着一组**成员取不到的键**：

- `state_phase` 里的 `submit` / `rejected`：10 个成员无一含这两个 Selection 值，也无一继承
  `tier.validation`（`validation_status` 不可能为 `rejected`）；`_approval_phase()` 的 `under_review`
  分支要求 `raw_state in ("submit","approve")`，`submitted` 不命中。**纯复制残留，删除零行为变化。**
- `state_actions` 把 `reopen` 挂在 `submitted` / `submit` 上：`action_reset_draft` 在 8/10 成员上
  仅接受 `cancel`，于是页面渲染出**只可能抛 UserError 的按钮**，而模型真正接受的 `cancel`
  反而没有任何回退入口。

同一缺陷在原生侧重复出现：8 个 form 的 `退回草稿` 按钮写成
`invisible="state != 'submitted'"`，与模型接受的状态正好相反。

本段同时把 `config/contract/workflow_state_phase_dead_entries.v1.json` 的登记条目从 **12 条降到 2 条**
（仅剩 `sc.fund.account.operation`、`sc.plan`）——登记集重新变得有信息量。

### 3. 负例（先证明测试真的会失败）

| 负例 | 结果 |
|---|---|
| A：把旧模板（含 `submit`/`rejected`）还原回去 | **FAIL 如预期**：`['approved','cancel','draft','rejected','submit','submitted'] != [...]` |
| B：对 `HEAD` 的旧 XML 施加新的 arch 断言 | 5 个 form **FAIL 如预期**（`state != 'submitted'`） |

新增用例 `test_the_shared_approval_family_declares_only_reachable_states` 从 helper 自身读模板，
按 `state_actions`/`state_phase` 全等**自动派生** 10 个成员名单——编辑手工映射无法收窄检查范围。
它同时断言：模板相位键恰为四值、每个成员 `reopen` 只在 `cancel`、`method_by_action["reopen"]`
指向 `action_reset_draft`、`fields_get(['state'])` 的 Selection 键一致，以及**从 `ir.ui.view` 读回**
的每个 form 里 `action_reset_draft` 按钮的 `invisible` ⊆ `{"state != 'cancel'"}`（无按钮的 form 跳过：
契约可以领先原生头，但不得提供模型拒绝的控件）。

### 4. 验证

| 命令 | 结果 |
|---|---|
| `make verify.workflow_state_phase_coverage` | PASS `models=65 covered=65 dead_registered=2`；16 tests OK |
| 后端单方法（新用例，DB `sc_dev_demo`） | PASS `0 failed, 0 error(s) of 1 tests` |
| 后端单方法（`test_general_contract_legacy_confirmed_phase_is_declared`） | PASS `0 failed, 0 error(s) of 1 tests` |
| `TestWorkflowContractBackend` 全类 | 30 tests，7 errors — **与 `HEAD` 基线完全一致**（stash 对拍：HEAD 亦 7 errors / 29 tests），属既有环境缺陷，非本批引入 |
| `python3 scripts/verify/workflow_inventory_profile_method_guard.py` | PASS `profile_methods=29 inventory_methods=41` |
| `python3 scripts/verify/workflow_contract_custom_coverage_guard.py` | PASS |
| `python3 scripts/verify/workflow_action_semantics_completeness_guard.py` | PASS `profiles=65` |
| `make verify.native_view.workflow_action_coverage` | PASS `registered=31` |
| `addons/smart_core/tests/test_workflow_contract_profile_registry.py` | PASS 9 tests |
| `make refresh.generated_reports` + `make ci.generated_reports.guard` | PASS（全部 current） |
| `make verify.unified_page_contract.v2.professional_backend` | PASS（含 `verify.workflow_state_phase_coverage`） |
| `make ci.local.iteration` | PASS `change_state=dirty coverage=L1_only` |
| `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core MODULE=smart_construction_core make mod.upgrade` | 成功（78 modules，registry 重新加载 view 后 arch 断言拿到真实结果） |

未运行 `verify.workflow_contract.backend` 整条：其 `audit.workflow_state.inventory` 前置会用注册库
覆盖历史 `sc_demo` 基线（既有环境限制，见 `FE-CONTRACT-NATIVEBTN-01`），与本段无关。本段以
「守卫 + 单测 + 一条真实 Odoo arch 断言」覆盖同一口径。

### 5. 剩余（显式登记，不在本段）

- `sc.safety.disclosure` / `sc.safety.plan` 的原生 form header **完全没有** workflow 按钮（契约有、arch 无）：
  按「契约可以领先 arch，但不得提供模型拒绝的控件」本段不扩大处理。
- `sc.fund.account.operation`、`sc.plan` 两条死条目仍登记在册（权威侧待复核）。
- `state_transition_undeclared` 五条仍为权威侧待决，不因本段消项。
- `style_system.guard` 文件长度四项欠账独立保留；本段 `workflow_contract_service.py` 由 1488 → 1490 行，
  仍在既有 warning 档，未跨过 split-plan 阈值。

### 状态

本段**批次验收完成**。未推送、未合并、未部署目标环境；业务矩阵状态不变。

---

## FE-CONTRACT-WORKFLOW-AUTHORITY-01：工作流可用性收敛为单一权威

起点 HEAD `6cabe3067`（干净）。本段只删除**没有消费方**的重复门禁与死接线，并给被删的 fail-open 默认留下回归钉子。
不改业务动作、不改状态机、不改原生视图。

### 1. 七问

- **Formal Product Layer**：P0 平台内核产品（统一页面契约 v2 的通用消费行为）。
- **Layer Target**：`frontend/apps/web` 的 `app/contracts/v2/workflowActionAvailability.ts`（权威）与
  `pages/contractForm/workflowContract.ts`（页面适配）、`pages/ContractFormPage.vue`（组装）。
- **Module**：前端 Web 渲染层，不涉及 Odoo 模块。
- **Standard vs User-Specific**：平台机制。动作可用性判定不是客户偏好，也不是低代码可配置项。
- **Why Here**：契约已经声明动作与按钮状态，前端只需要**一处**把它换算成"能不能点"；重复的第二处必然漂移。
- **Why Not Elsewhere**：不放后端（后端已给出 `enabled`/`disabled`/`entitlementEvaluated` 事实），
  不放低代码（不是呈现偏好），不放原生视图（按钮可见性由 arch modifier 表达）。
- **Blast Radius**：仅合同表单的动作可用性判定路径；由 present 单测（177 例）＋严格类型检查＋一次前端构建证明收敛。

### 2. 真实缺陷：两处门禁，其中一处还默认放行

合同表单的动作可用性实际由 `contractFormPresenter.ts` 单点判定：读 `resolveWorkflowActionAvailability`，
`error` 与 `managed && !enabled` 都产出 `enabled: false`（fail-closed，已有活体断言）。

同时，页面侧长期带着第二个实现：

| 死符号 | 位置 | 问题 |
|---|---|---|
| `applyWorkflowAvailability` | `pages/contractForm/workflowContract.ts` | presenter 同一判定的第二份拷贝；页面把它当依赖传入，消费方从未解构使用 |
| `shouldShowWorkflowAction` | 同上 | 已知转移 + `availableActions` 存在但**不是数组**时直接 `return true` —— 读不懂的载体照样渲染出工作流控件 |
| `isWorkflowTransitionMethod` / `workflowActionMethodAliases` / `workflowActionRowForMethod` | 页面导入 | 仅再导出，页面未使用 |
| `normalizeWorkflowActionRows` / `normalizeWorkflowPhaseStatusbar` / `normalizeNativeFormStatusbar` / `resolveStatusbarSelectionValue` | 页面导入 | 前两者**只被测试引用**（测试保留，页面接线删除）；后两者由 `useRecordFormLayout` 直接导入，页面导入是纯冗余 |

也就是说：**"未知判为允许"的默认值真实存在于代码里，只是恰好没有消费者。** 一旦有人按名字去调用它，
按钮就会出现；而这条路径从来不在验收视野内，因为页面上看不到差异。

### 3. 负例（先证明回归抓得住）

`/tmp/deleted_helper_negative.ts`（一次性，未入库）逐字复制被删助手，对同一输入做对拍：

| 输入 | 被删助手 | 现权威 |
|---|---|---|
| `{ availableActions: 'unreadable' }` + `action_submit` | `true`（渲染按钮，**fail-open**） | `kind: 'error'`（不可用，fail-closed） |
| `{ availableActions: 'unreadable' }` + 未登记方法 | `true` | `kind: 'unmanaged'`（不扩大权威范围） |

`[deleted_helper_negative] PASS: the removed helper failed open, the authority reports an error`

新入库回归：`canonical_form_presenter_test.ts` 用 `resolveWorkflowActionAvailability` 直接断言上述两种输入，
并保留原有 7 条语义（非布尔 `enabled`、畸形 `target`、合法禁用行、孤立畸形行不误伤、非工作流动作不越界、
同标签不同身份合法、已声明转移无行时 fail-closed）。

### 4. 修正既有记录的一处口径

`form_structure_consumption_stabilization_20260917.md:4284/4425/4877` 把 `shouldShowWorkflowAction=true`
记为 `reactivate` 降级的"后果/批次 C 探针实测值"。**该助手的真实消费方为零**，实测的是函数返回值，
不是渲染出来的页面；当时真正的拦截来自交付状态契约的 `enabled` + 原生 modifier + 后端拒绝。
结论方向（fail-closed 成立）不变，但"页面会渲染出该按钮"的表述应视为**函数级代理指标**。
本段删除该助手后，该口径不再有歧义。

### 5. 验证

| 命令 | 结果 |
|---|---|
| `make verify.frontend.canonical_form_presenter.unit` | PASS `cases=177`（含新增 fail-closed 回归） |
| 负例对拍（一次性脚本） | PASS：被删助手 = fail-open，现权威 = error |
| `make verify.frontend.adopted_form_validation_identity.unit` | PASS `cases=46 failed=0 host=real-vue-instance` |
| `make verify.frontend.contract_form_save_failure_recovery.unit` | PASS（edit-retry / single-flight / create-retry / permission-denial） |
| `make verify.frontend.contract_error_business_ownership.unit` | PASS `92 cases` |
| `make verify.frontend.standard_form_composition.unit` | PASS `93 cases` |
| `make verify.frontend.contract_field_occurrence_identity.unit` | PASS |
| `make verify.frontend.lint.src` | PASS `0 errors`（57 warning 为既有 vue 属性换行风格项） |
| `make verify.frontend.typecheck.strict` | PASS（`vue-tsc --noEmit` 两套配置） |
| `make verify.frontend.no_new_any_guard` | PASS `files_checked=703 total_any=25` |
| `make verify.frontend.build` | PASS（`ContractFormPage-*.js` 948.98 kB） |
| `python3 -m unittest scripts.verify.test_product_view_capability_ledger` | PASS 22 tests（该测试文件同时是能力台账交互证据源，已确认守卫引用的符号未被触及） |
| `make ci.local.iteration` | PASS `change_state=dirty coverage=L1_only` |

### 6. 剩余（显式登记，不在本段）

- `normalizeWorkflowActionRows`、`normalizeWorkflowPhaseStatusbar` 目前**只被测试引用**。二者语义 fail-closed，
  暂不删除；若后续仍无消费方，与对应测试一并清理。
- 合同表单仍有 `standardFormComposition.ts`（官方组合）与 `legacy-form-section` 两条渲染器：
  后者是**契约未声明为 record-form 时的 fail-closed 兜底**，不是遗漏。真正要补的是
  "哪些在册入口的契约没有声明 `pageInfo`"，属契约投影侧，不在本段。
- `style_system.guard` 文件长度四项欠账独立保留，本段未触及。

### 状态

本段**批次验收完成**。未推送、未合并、未部署目标环境；业务矩阵状态不变。

## FE-CONTRACT-PAGE-INFO-01（已更正）：装配器的视图类型边界与平台既有约定对齐

> **更正声明（2026-09-29，本段自查后重写）**：本段初次提交把该问题写成"现网产品缺陷，
> 导致前端退回旧渲染器、并静默丢弃看板行动作"。**该结论不成立，现予撤回。**
> 决定性证据：拼接串确实由 `page_assembler` 产生，但在到达任何消费者之前，
> 已被平台既有规范化函数处理（见 §2）。因此**没有任何现网页面因此被误分类**，
> 本段代码是**边界防御性收口 + 补齐缺失的枚举守卫**，不是缺陷修复。
> 下面的分类、证据与剩余项均按此更正；机制描述与判定链条保持可复核。

起点 HEAD `56150df42`（干净）。本段只改 `_assemble_ui_contract` 的视图类型解析，
让装配器在**收到视图列表**时按平台既有约定解析出唯一活动视图，再进入闭合枚举。

### 1. 七问

- **Formal Product Layer**：P0 平台内核产品（`ui.contract.v2` 装配属平台机制）。
- **Layer Target**：`smart_core`，`addons/smart_core/core/unified_page_contract_v2_assembler.py`
  的 `_assemble_ui_contract()` 视图类型解析。
- **Module**：`smart_core`。
- **Standard vs User-Specific**：平台标准。视图列表 → 单一页面身份的映射与行业/客户无关。
- **Why Here**：`pageInfo` 是 page 级契约，schema 已把 `viewType`/`layoutType` 定为闭合枚举，
  归一化职责应落在写出该字段的边界函数上。
- **Why Not Elsewhere**：不改 `page_assembler`（发布 `head.view_type` 列表是它作为 action 级
  source 的既有语义，且已被下游规范化消费）；不放松 schema（枚举是权威）；不改前端
  （`standardPageType.ts` 对未枚举/冲突输入判 `specialized` 是**正确的 fail-closed**）。
- **Blast Radius**：仅 `ui.contract` 装配的 `pageInfo.viewType/layoutType` 与其派生的 `pageId`、
  看板行动作注册表查找键。输入为单值 token 时行为不变（由既有 105 例 + 新增 1 例共同证明）。

### 2. 机制判定链（本段更正的核心）

拼接串的产生与消除：

1. `app_config_engine/services/assemblers/page_assembler.py:621` 发布
   `head["view_type"] = ",".join(view_types)`。**这是真实存在的列表形态。**
2. `core/native_view_contract_projection.py:44-45` 的 `resolve_primary_view_type` 取
   **首项**：`head_view_type.split(",")[0].strip()`。注释也明确"请求的视图列表 → 活动视图"。
3. `handlers/ui_contract.py:_finalize_projected_contract` → `inject_primary_view_projection`
   （`native_view_contract_projection.py:94-97`）把 `data["view_type"]` 与
   **`head["view_type"]` 双双重写为该单一 token**。
4. `handlers/ui_contract_v2.py:602` 解析 `view_type`：
   `params.view_type or ui_data.view_type or ui_meta.view_type or "form"`；
   第 744-745 行把它写回 `source_contract["view_type"]`，即装配器读到的那个键。

**活体实测（只读，`127.0.0.1:8070`）**：`op=action_open`（**不传 `view_type`**）：

| 入口 | 声明 `view_mode` | legacy `ui.contract` 的 `head.view_type` | legacy 顶层 `view_type` |
|---|---|---|---|
| `product.packaging`（action 185） | `tree,form` | `tree` | `tree` |
| `tier.review`（action 579） | `tree,form` | `tree` | `tree` |

即：**第 3 步已经把列表收敛成单值**，装配器收到的不是拼接串。本段因此不是现网缺陷修复。

### 3. 本段代码与它现在承担的作用

装配器是对外可调用的公共入口（`assemble_unified_page_contract_v2(source, ...)`），
其 `source.view_type` 是调用方给出的契约字段。原本该入口对"列表形态输入"不做归一化，
一旦有调用方按 `page_assembler` 的既有形态传入 `"tree,form"`，就会写出 schema 枚举之外
的 token，并被前端判为 `specialized → legacy-form-section`。
本段按平台**已有**约定（首项）在此边界补齐归一化，使两条约定一致，而不是新增第三套规则：

```python
raw_view_type = _text(source.get("view_type") or ui.get("view_type"), "form").split(",")[0].strip()
view_type = "tree" if raw_view_type == "list" else (raw_view_type or "form")
```

- `list → tree` 归一只影响 `pageId` 与内部视图查找键（`_view_field_names` 本就对两者互相回退），
  输出仍由第 823 行既有改写给出 `viewType="list"`，**不改变单值输入的任何对外结果**。
- **不动**"缺失 → `form`"的现状（属另一类缺口，登记在 §6）。

修复后实测（单元级，输入 → 输出）：

| 输入 `view_type` | `viewType` | `layoutType` | `pageId` |
|---|---|---|---|
| 缺失 | `form` | `form` | `x.document.form` |
| `tree,form` | `list` | `table` | `x.document.tree` |
| `form,tree` | `form` | `form` | `x.document.form` |
| `kanban,tree,form` | `kanban` | `kanban` | `x.document.kanban` |
| `tree` / `list` | `list` | `table` | `x.document.tree` |

`pageId` 在 `list`/`tree` 两种拼法下统一为 `x.document.tree`（同一页面责任一个身份）；
这是本段唯一的对外身份变化，活体可达入口的 `pageInfo` 值未变（§5.1）。

### 4. 回撤此前两处不成立的表述

- 撤回"**前端因此退回 `legacy-form-section`**"：前端只在拿到未枚举/互相冲突的 token 时
  才这么做，而第 3 步已保证它拿到的是单值 token。
- 撤回"**`project.project` 看板行动作被静默丢弃**"：`_append_registered_kanban_row_action`
  收到的是装配器内的 `view_type`，其来源即 §2 第 3-4 步的单一 token；
  修复前实取值为 `kanban`，注册键 `("project.project","kanban")` 命中。
  （一次性探针中我直接调用装配器并传入 `"kanban,tree,form"`，那是**合成输入**，
  被我误当作现网路径，属本次自查发现的方法错误。）

### 5. 验证

| 命令 | 结果 |
|---|---|
| `python3 addons/smart_core/tests/test_unified_page_contract_v2_mobile_compact.py` | PASS 106 tests（新增"枚举守卫"+"与 `resolve_primary_view_type` 约定一致性"两例） |
| `make verify.unified_page_contract.v2.schema` | PASS `examples=4` + 3 tests |
| `make verify.unified_page_contract.v2.assembler` | PASS `sources=4`（映射快照未漂移） |
| `make verify.unified_page_contract.v2.runtime` | PASS `score=6`（含 106 例） |
| `make verify.unified_page_contract.v2.action / .data / .status / .client` | PASS `actions=7` / `dataSources=2` / `widgets=4 buttons=2` / `clients=3` |
| `make verify.unified_page_contract.v2.intent` | PASS（`ui.contract.v2` 仍是唯一终态入口） |
| `make verify.unified_page_contract.v2.web_consumer` | PASS（5 tests + 双守卫） |
| `make verify.unified_page_contract.v2.guard_inventory` | PASS |
| `make verify.frontend.canonical_form_presenter.unit` | PASS `cases=177` |
| `make verify.frontend.product_page_pattern.unit` | PASS `patterns=4` |
| `make verify.frontend.page_pattern_reference_parity.unit` | PASS `surfaces=16` |
| `make verify.frontend.typecheck.strict` | PASS（两套 `vue-tsc --noEmit`） |
| `make ci.local.iteration` | PASS `change_state=clean coverage=L1_only` |
| `make verify.unified_page_contract.v2.regression_audit.host` | **not_run（环境）**：需 `127.0.0.1` + `DB=sc_demo` 活体实例，当前返回 HTTP 500，未进入装配逻辑 |

### 5.1 活体可达入口的页面类型（只读核对）

`sc-local-dev-odoo-1` 的 `addons_path` 含 `/mnt/source-addons`，即本仓库 `addons/` 的 bind mount。

| 入口 | `view_mode` | `pageInfo.viewType` | `pageInfo.layoutType` |
|---|---|---|---|
| `product.packaging`（185） | `tree,form` | `list` | `table` |
| `tier.review`（579） | `tree,form` | `list` | `table` |

**环境限制（如实登记，非产品缺口）**：`admin` 账号对 `sc.general.contract`（687）、
`payment.request`（688）无读权限，`ui.contract.v2` 返回 500
（日志：`You are not allowed to access … records`）。业务角色登录在本库也不可用：
`res_users.password` 用 pbkdf2-sha512 校验 `sc_test_admin` + `SC_DEMO_USER_PASSWORD` = **False**，
而同一方法校验 `admin` + `ADMIN_PASSWD` = **True**（方法有效）。
恢复该口令属 P4 数据动作，需单独授权；中文业务入口的逐条运行时取证待其恢复后进行。

### 6. 剩余（显式登记，不在本段）

- **缺失 `view_type` 仍默认 `form`**：缺口应显现而非猜测。让缺失走既有诊断/显式类型属另一类缺口，
  本段不扩张。
- `page_assembler` 发布 action 级视图列表、`resolve_primary_view_type` 负责收敛，是**既有正确分工**；
  本段只让装配器边界与后者一致。
- 前端 `standardPageType.ts` 的 `specialized` 兜底与 "冲突即 specialized" 规则**保留**：
  它是契约未声明可渲染页面类型时的 fail-closed 答案。
- 本地 `sc_dev_demo` 的 demo 业务角色口令与 `SC_DEMO_USER_PASSWORD` 不一致（见 5.1）。
- `style_system.guard` 文件长度四项欠账独立保留，本段未触及。

### 7. 验收机制补强（本次偏差的直接成因）

本次偏差不是"看漏了一个页面"，而是**方法错误**：我用手写 dict 调用装配器，
把合成输入的结果当成现网路径的证据，因此把"边界健壮性"写成了"现网缺陷"。
对应的验收缺口是：**没有任何回归钉住"消费前已收敛为单值 token"这一不变式**，
所以这类错判只能靠事后人工复核发现。

补强（本段新增，已入库）：

| 回归 | 钉住的不变式 | 负例验证 |
|---|---|---|
| `test_legacy_finalizer_publishes_one_active_view_for_the_consumer` | `inject_primary_view_projection` 必须把 `head.view_type` 与顶层 `view_type` 双双重写为单一 token；消费方（含 `_assemble_ui_contract`）**永远看不到列表** | 临时移除该双重重写 → 本回归 `FAILED (failures=3)`（`'form,tree' != 'form'`）；恢复后 `Ran 107 tests ... OK` |
| `test_assembler_active_view_resolution_agrees_with_the_native_view_finalizer` | 装配器边界归一化必须与平台既有 `resolve_primary_view_type` 同一约定（取首项） | 约定漂移即失败（对 `tree,form` / `form,tree` / `kanban,tree,form` / `tree,form,pivot,graph` / `tree` / `list` / `form` / 缺失 逐一断言） |
| `test_joined_view_type_cannot_publish_a_token_the_schema_does_not_enumerate` | 装配器输出必须落在 schema 枚举内，且 `layoutContract.layoutType == pageInfo.layoutType` | 见 §4 |

效果：如果将来有人移掉规范化，或让两条约定分叉，**本地定向回归先失败**，
不会再以"某个页面变成 specialized"这种远端表现才被发现。

### 状态

本段**批次验收完成（含自查更正）**。未推送、未合并、未部署目标环境；业务矩阵状态不变。

## FE-TPL-07 续：只读记录页的官方详情事实不可达（2026-09-30，已修复）

分支 `feature/web-official-template-adoption`；修复前候选 HEAD `35d1f4d13`；修复后候选 `25b31e714`。
本段是 `## FE-TPL-07`（2026-09-29）同一职责范围的续段，不新建专题、不改业务矩阵。

### 1. 七问

- Formal Product Layer：P0 平台通用前端表达（页面类型 → 组合采纳的消费边界）。
- Layer Target：`app/presentation/standardDetailComposition.ts`、`components/template/FormSection.vue`；
  只读探针 `frontend/apps/web/scripts/standard_page_type_browser.mjs`。
- Standard vs User-Specific：跨模型通用机制，不含行业字段语义、客户偏好或管理员配置。
- Why Here：「页面级采纳」与「section 是否有资格作为事实呈现」是两个判断，此前被折成一个恒假的合取。
- Why Not Elsewhere：不涉及后端字段、事务或权限；也不需要每个页面各自决定，边界属于呈现组合层。
- Blast Radius：所有 `preferReadonlyFacts` 的只读记录页（合同、付款、项目等）；可编辑表单页不受影响。

### 2. 真实缺陷（先有运行证据，再改代码）

修复前候选 `35d1f4d13` 在 5180 生产模式实测 `/r/payment.request/1813`（受管角色 `fixture_role_finance`）：

| 观察 | 值 |
|---|---|
| `data-detail-composition` / `-reason` | `official-standard-detail` / `contract-readonly-record-view`（页面级采纳为**真**） |
| `[data-detail-facts="official-standard-detail"]` | **0** |
| `[data-semantic-component="ScDescriptions"]` | **0**；旧网格 `.template-form-section-grid` **10** 行 |
| 10 个 section 的 `data-detail-section-reason` | 全部 `outside-standard-detail` |

缺陷表达式（`FormSection.vue`）：`standardDetailComposition.adopted && standardFormComposition.adopted`。
两者在 `20781fe2d` 之后同源于 `standardPageType.ts` 对同一页面的**单一**分类——`record-form`
或 `record-detail`，互斥——因此该合取恒假，**官方只读详情在任何页面都不可能被渲染**。

引入与可见窗口（已用 git 核实，不依赖推断）：

- `308a85a60` 引入该合取：当时 form 采纳来自**模型试点表**、detail 采纳来自「试点模型 + readonly profile」，
  两者可同时为真，`sc.general.contract` 只读页的 facts 可见（与本文件 TPL-03 记录的 record 11 `facts=7` 一致）。
- `7f7392584` 把该合取搬进 `resolveStandardDetailSection`，同时加入 section 字段资格
  （含专用控件的 section 不得降级为纯文本）。
- `20781fe2d` 让两个采纳项都由**同一** `StandardPageTypeDecision` 推导 → 合取变为恒假。
  **本文件此前记录的只读详情事实结论（`fc0afcb32` 及更早候选、含 `tpl07-1790669324381` 的
  「付款非零 facts」）都不属于包含 `20781fe2d` 的候选，不能沿用。**

### 3. 修复

新增 `resolveStandardDetailFactLayout(decision, section)`：页面级采纳**只取** detail 决策，section 资格
（设计模式、非只读、空 section、关系/附件集合、专用控件、未知类型）保持独立。`ScForm :bare` 仍跟随
form 组合，因此只读页用官方事实呈现，但**不**借用可编辑表单的容器与规则；可编辑记录表单因页面级
detail 采纳为假而继续走控件。`standardFormComposition.ts` 的注释同步更正（不再声称非采纳 section
没有 facts 布局）。未改任何业务规则：字段、取值与读权限仍来自有效契约与后端。

### 4. 负例（先证明回归真的抓得住）

临时把合取写回 `FormSection.vue` → `verify.frontend.standard_collection_composition.unit`
**FAIL**（源码守卫 `actual: true, expected: false`）；恢复后 **PASS cases=113**（原 102）。
新增行为断言以 `StandardPageTypeDecision` 为输入、以 section 渲染结论为输出：
契约声明的 readonly record 采纳 facts；可编辑记录表单 / 集合页 / 无 page 决策 / 编辑 section /
设计器 / 关系集合分别落在 `outside-standard-detail` / `editable-section` / `configuration-editor` /
`relation-collection-extension`。此前只有「采纳策略纯函数」和「源码里有某个守卫」两类断言，
**页面级采纳能否在 section 看见**从无覆盖——这是本缺陷得以存活的直接原因。

### 5. 探测适配（不降低断言）

`form()` 的就绪条件原先恒为 `[data-form-composition="official-standard-form"][data-state="ok"]`；
在只读页这要求一个契约不可能同时声明的模式，只读步骤只能**超时**，于是失败表现为「超时」而不是
「事实缺失」。改为按契约声明的模式等待，并把只读断言**加强**为：只读模式已发布、
可编辑表单组合**未**挂载、官方事实非零、关系/附件集合留在 facts 布局之外。不恢复旧 DOM 迎合探针。

另补一条：**「引擎未挂载」不等于「记录没有被呈现为可编辑」**——只读记录仍可能被可编辑 section 框住而无需挂载官方引擎。
因此只读步骤改为直接断言 section 自身状态（`[data-detail-section-reason][data-state="editable"]` 计数为 0），
不再用组合身份代理记录的可编辑性。

### 6. 验证（同一候选 `25b31e714`，一次构建）

- L1：`make ci.local.iteration` PASS（dirty 阶段，`coverage=L1_only`）；`git diff --check` 干净。
- L2：`standard_collection_composition` 113、`standard_form_composition` 97、
  `adopted_form_engine_decision` 74（真实 TDesign 引擎）、`adopted_form_validation_identity` 46/46、
  `product_page_pattern` 4 patterns、`page_pattern_reference_parity` 16 surfaces、
  `canonical_form_presenter` 177 + 10、`collection_action_toolbar`、`primitive_adapter` 46、
  `navigation_shell`、`standard_preview` 6、`verify.frontend.typecheck.strict`（vue-tsc ×2）全部 PASS。
- L4：`make frontend.standard.preview.build` + `.up`；`verify.frontend.standard_page_type.browser`
  三个 scope 全 PASS（`default` 32/32、`TPL07_SCOPE=detail` 19/19、`TPL07_SCOPE=additional` 3/3），
  `forbiddenWrites=[]`、`pageErrors=[]`：
  - `/r/payment.request/1813`：facts=2；section = 2×`standard-readonly-facts` + 2×`relation-collection-extension`
    + 6×`dedicated-control-extension`；事实值回读 `FE-A Counterparty` / `FE Acceptance Bank A` / `FE-ACCEPTANCE-A-001`。
  - `/r/sc.general.contract/11`：6×`standard-readonly-facts` + 1×`dedicated-control-extension`。
  - 可编辑 `/f/payment.request/1813` **未受影响**：facts=0、8×`outside-standard-detail`、6 editable + 2 readonly
    section、`official-standard-form`。
  - 真实第二页（offset 10 → ids `[1803,1795,1794,1787,1710,33]`）与返回同集、组合原因、窄屏 containment 均通过。
- 只读能力边界定向核对（`/r/payment.request/1813`、`/r/sc.general.contract/11`）：10 / 7 个 section 全部
  `data-state="readonly"`；页面内唯一的可输入控件是外壳菜单搜索与集合/关系搜索（`inFacts=false`）；
  无记录字段可编辑、无保存/提交草稿动作。页面上出现的 `提交审批` 是契约声明的**业务动作**（action bar，
  草稿态可用），`删除` 只属于 chatter 消息（`native-chatter-message-delete`）与附件
  （`native-attachment-delete`），不是记录或明细行的写入能力——业务只读与业务动作属不同层，不得混为一谈。
- 「6 facts + 1 dedicated-control」**不是静默降级**：含专用控件的 section 按 `resolveStandardDetailSection`
  的既有资格判定保留专用控件，而不是被压成纯文本；这是 `7f7392584` 起有意为之的 fail-closed 规则，
  先前「7 个 section 全部进入 descriptions」的观察早于该资格判定。

提交（本地，未推送）：`841b2e9f8 fix(web): render a readonly record's facts through the detail composition`、
`25b31e714 test(web): wait for the mode the contract declared, not an assumed one`、
`108fa3f60 test(web): assert the readonly record has no editable section, not just no engine`。
产物 `sce-offrepo/artifacts/config05-20260929`（`build-identity.json`：`base_sha=25b31e714…`、`dirty_scope=""`、
`entry=/assets/index-CNrigT9d.js`、`entry_sha256=4d80190b…`）；旧候选按既有约定改名保留为
`config05-20260929-prev-35d1f4d13`（不是覆盖）。5180 监听 `pid=802966`，`STATIC_ROOT` 指向该 dist，
端口 5180、proxy `http://127.0.0.1:18082` 与后端 `sc-backend-odoo-acceptance` 一致。

### 7. 两处口径更正（回撤此前不成立的表述）

- `legacy-detail-surface`（见 `### FE-TPL-03 列表/只读详情证据再绑定到当前整合候选`）与
  `legacy-list-surface`（见 `### FE-TPL-05A`）：这两个 token 名为「未采纳」的回退渲染器，但本项目
  只发布**一个**列表面和**一个**只读记录面，不存在第二渲染器。把它们写成渲染器身份是把「未采纳」
  误报成实现事实。列表侧在 `20781fe2d` 收敛为单值，详情侧在 `eb479cedb` 收敛为单值；
  相应表述更正为：**回退的答案是「未采纳」，不是另一个渲染器。**
- 只读详情事实结论的有效窗口：`fc0afcb32` 及更早候选成立，`20781fe2d` 之后失效，
  本候选 `25b31e714` 重新取得（不是回填历史报告）。

### 8. 验收体系为什么之前没发现

1. **页面级采纳与 section 渲染之间没有回归**。既有断言只覆盖「采纳规则纯函数」和「源码守卫」，
   缺少「页面级采纳在 section 可见」的链路断言；补强见 §4，断言以「决策 → 渲染结论」为口。
2. **探测把假设写进了就绪条件**。`form()` 恒等可编辑组合，使只读步骤在任何业务断言之前超时，
   失败形态从「事实缺失」变成「定位超时」，掩盖了缺陷本相。
3. **上游输入变化后没有重跑受影响的旅程**。`20781fe2d` 改的是「页面类型推导」这一上游输入，
   但只读详情旅程未随该提交重跑，失效的通过结论被继续引用（连同 r2 的 facts 证据）。
   由此固定一条规则：**页面类型/组合采纳这类上游输入变化，必须重跑受影响的只读与可编辑旅程，
   不得沿用旧证据。** 本段即按该规则重跑，并保留旧报告不重标通过。

### 9. 剩余（显式登记，不在本段）

- `sc.safety.disclosure` / `sc.safety.plan` 原生 form header 无 workflow 按钮（契约有、arch 无）。
- 缺失 `view_type` 仍默认 `form`（显式化属另一类缺口）。
- 五条 `state_transition_undeclared`（权威侧待决，见 `### FE-CONTRACT-NATIVEBTN-01`）。
- `style_system.guard` 四项文件长度欠账（本段未触及）。
- 只读页仍发布 `data-form-composition="legacy-form-section"`：该页的 form 组合确实未采纳
  （section 以 bare 呈现、无引擎规则），与 `data-detail-composition` 采纳并存是设计结果，不是矛盾。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## FE-TPL-07 三续：验收门禁抓到后端未定义名缺陷，并修正只读事实计数口径（2026-09-30）

分支 `feature/web-official-template-adoption`；本段起点 HEAD `41b765559`（工作树仅一份派生清单待提交）；
收口 HEAD `1c95d4a74`。延续 `## FE-TPL-07 续` 的同一职责范围，不新建专题、不改业务矩阵、不进入下一批。

### 1. 七问（本段的后端修复）

- Formal Product Layer：P1 建筑行业标准产品。
- Layer Target：`addons/smart_construction_core/handlers/payment_request_available_actions.py`。
- Module：`smart_construction_core`。
- Standard vs User-Specific：行业标准产品的动作面；不含客户偏好，不含管理员配置。
- Why Here：角色码与授权组的关系由行业能力注册表 `capability_registry.role_code_for_group` 单点拥有，
  `8890d5f0f2` 已把该关系收敛到那里；本 handler 只是消费方，缺的是**导入**，不是规则。
- Why Not Elsewhere：不在前端补一份角色→按钮映射（那是把授权语义复制到端侧）；不在 `smart_core`
  平台内核新增行业能力表；也不改后端事务绕过前端问题。
- Blast Radius：`payment.request.available_actions` 意图，以及复用其 `_action_entry` 的
  `payment_request_work_item_service`（财务「我的工作」的工作项投影）。

### 2. 失败定性：不是探测失配，是真实产品缺陷

`verify.frontend.standard_bootstrap.browser` 在本段起点为 FAIL：

```
locator.waitFor: Timeout 15000ms exceeded — waiting for locator('[data-workspace-composition="official-dashboard-workspace"]')
```

按「先定性、不草率下结论」的要求逐层核对：

1. 源码字面值确认：`ProductWorkspaceSurface.vue` 根节点确为
   `data-workspace-composition="official-dashboard-workspace"`（**探针期望值没有过期**，可排除上一种
   「旧选择器失效」的假设；这一点必须亲自读文件，不能凭 `rg` 的显示下结论）。
2. 目标复现：`/s/workspace.home` 正常渲染该标记（`markerCount=1`）；失败发生在 `/my-work`。
3. `/my-work` 的状态是 `data-my-work-renderer="product-workspace" data-state="error"`，页面文本为
   「操作未完成 / 当前无法读取工作事项，请检查网络后重试。」——`MyWorkApprovalWorkspace` 因此根本没有
   挂载，探针等待的标记自然不存在。
4. 请求级证据：`POST /api/v1/intent` 的 `my.work.summary` 对 `fixture_role_finance` 返回 **HTTP 500
   INTERNAL_ERROR**（`trace_id=b024072b-146d-4a5a-a5dd-bdb7ea693064`）。
5. 后端堆栈（容器内 `odoo.log`）：

```
File ".../smart_construction_core/services/payment_request_work_item_service.py", line 264, in _todo
    actions = self._allowed_actions(record)
File ".../smart_construction_core/handlers/payment_request_available_actions.py", line 344, in _action_entry
    "required_role_key": role_code_for_group(required_group_xmlid),
NameError: name 'role_code_for_group' is not defined
```

**根因**：`8890d5f0f2`（`fix(workflow): derive the role code and own only the industry projection`，2026-09-29 21:37）
把每条动作的硬编码 `required_role_key`（`"finance"` / `"executive"`）改为由授权组派生，但**没有导入**
`role_code_for_group`。该符号只在 `handlers/payment_request_available_actions.py:344` 被使用，文件内
无定义、无导入。

**回归窗口（git 坐实，不靠推断）**：

| 候选 | 时间 | `role_code_for_group` 使用 | `verify.frontend.standard_bootstrap.browser` |
|---|---|---|---|
| `376e5a064592` | 2026-09-29 17:30 | 该文件无 | PASS（`bootstrap-inventory-1790674371809`） |
| `8890d5f0f2` | 2026-09-29 21:37 | 引入第 344 行 | — |
| `25b31e714a4e` | 2026-09-30 00:14 | 仍在 | FAIL（`bootstrap-inventory-1790702186688`，仅走到 `-home-*.png`，未产出 `-work-*.png`） |

通过报告与本段失败报告的差异恰好落在 `/my-work` 这一步：前者有 `fixture_role_finance-work-1440.png` /
`-work-390.png`，后者只有 `-home-1440.png` / `-home-390.png`。

### 3. 修复（最小，且先有负例）

`addons/smart_construction_core/handlers/payment_request_available_actions.py` 增补导入：

```python
from odoo.addons.smart_construction_core.services.capability_registry import (
    role_code_for_group,
)
```

角色码值不变（`group_sc_cap_finance_user` → `finance`、`group_sc_role_executive` → `executive`），
既有断言无需改动；改的是「名字有没有被绑定」，不是业务规则。

负例先行 / 修复后对照（同一门禁，`make local.dev.test MODULE=smart_construction_core`）：

| 阶段 | 命令标签 | 结果 |
|---|---|---|
| 修复前 | `TEST_TAGS='payment_request_available_actions_backend'` | **`0 failed, 4 error(s) of 6 tests`**，4 条均为同一 `NameError` |
| 修复后 | 同上 | **`0 failed, 0 error(s) of 6 tests`** |

同层兄弟测试一并收口：`payment_request_available_actions_backend,payment_request_action_surface_backend,
workflow_contract_backend` 合并运行得出 `0 failed, 7 error(s) of 42 tests`。这 7 条**与本修复无关且为既有失败**
（同门禁在无本改动的纯净工作树上复跑得到完全相同的 7 条）：

- 5 条测试夹具自身违反领域约束：`expense_claim` / `self_funding_registration` 抛
  「必须关联已归属公司的有效项目」、`receipt_income` 抛「收款归集关系不存在或当前用户无权访问」。
- 1 条 `payment.request.write` 被状态守卫拒绝：`[SC_GUARD:P0_PAYMENT_STATE_BYPASS_BLOCKED]`。

### 4. 验收后端身份必须随代码刷新（不然门禁会正确拒绝）

`addons/` 是 bind mount，容器跑的是**当前工作树**，但容器在启动时记录了 `SC_SOURCE_REVISION`；
前端门禁会校验 `git diff <该修订> -- addons` 为空。因此改完后端后**必须**走受管入口刷新身份：

- 刷新前：容器 `SC_SOURCE_REVISION=eb479cedb60ab7c63bf37c775a32d919d00237f7`。
- `make backend.acceptance.replace-stale` → `PASS backend=sc-backend-odoo-acceptance revision=1c95d4a7457f9f63d07073f1a52a7eb0efc1c3ca`。
- `git diff eb479cedb6 1c95d4a74 -- addons` = 仅本文件 `3 insertions(+)`，确认后端修订区间内**没有**其他代码漂移。
- 副作用：**所有依赖该后端容器的浏览器证据都随之失效**，必须复跑（见 §5），不得沿用旧容器实例的结论。

### 5. 复跑后的门禁结果（当前候选 + 当前后端）

| 层 | 入口 | 结果 |
|---|---|---|
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='payment_request_available_actions_backend,payment_request_action_surface_backend'` | PASS（付款两项；工作流契约那 7 条为既有失败，见 §3） |
| L4 | `verify.frontend.standard_bootstrap.browser` | **PASS `roles=3`**（`fixture_role_finance` / `fixture_role_contract_operator` / `fixture_role_config_admin` 三个角色均到达 `/s/workspace.home` 与 `/my-work`） |
| L4 | `verify.frontend.standard_page_type.browser`（`default` / `detail` / `additional`） | PASS **32 / 19 / 3**；`forbiddenWrites=[]`、`pageErrors=[]` |
| L4 | `verify.frontend.standard_config_field.browser` | PASS `checks=12` |
| L4 | `verify.frontend.standard_public_auth.browser` | PASS `checks=18` |
| L4 | `verify.frontend.standard_menu_config.browser` | PASS `checks=46` |

### 6. 跨模型只读详情复核（当前候选 + 当前后端，全部 `data-state=ok` 后取值）

| 目标 | 角色 | facts | section 数 | section 归属 | 可编辑 section |
|---|---|---|---|---|---|
| `/r/payment.request/1813` | `fixture_role_finance` | 34 | 51 | 34 facts + 16 dedicated-control + 1 relation-collection | **0** |
| `/r/sc.general.contract/11` | `fixture_role_contract_operator` | 6 | 7 | 6 facts + 1 dedicated-control | **0** |
| `/r/sc.general.contract/10` | `fixture_role_contract_operator` | 6 | 7 | 6 facts + 1 dedicated-control | **0** |
| `/r/project.project/10` | `fixture_role_finance` | 4 | 5 | 4 facts + 1 relation-collection | **0** |
| `/r/project.project/10` | `fixture_role_pm` | 2 | 4 | 2 facts + 2 relation-collection | **0** |
| `/f/payment.request/1813`（可编辑） | `fixture_role_finance` | 0 | 44 | 44 `outside-standard-detail` | 17 |

`pageErrors=0`。结论不变且更强：**只读详情按 `contract-readonly-record-view` 采纳，跨模型无特例；
可编辑记录表单不被 facts 布局侵占。**

**口径更正（本段发现，回撤 §6 的计数）**：上一段的 `facts=2、10 section` 是**加载过程中**的快照。
固定延时（1500ms）在冷启动后端上会取到 `data-state=loading` 的中间态（本段先复现过 `facts=0、
sectionCount=0`）。本段改为轮询到 `data-state=ok` 再取值，稳定得到上表数字；同一脚本在修复前
后端上也返回过 `2 / 10`，说明那是**测量口径**差异而非契约差异。由此固定规则：**只读事实/分区计数
必须在页面声明加载结束后读取，不得用固定 sleep 取数**——这与「等待绑定明确状态、不用固定延时掩盖
渲染未完成」是同一条规则。

### 7. 同族缺陷登记（同类未定义名，本段**不修**）

同一类「名字被使用但从未绑定」的缺陷在仓库另有 5 处。它们不是本次失败的原因，也不在本段范围内，
但必须显式登记，因为它们证明**这类缺陷没有静态防线**：

| 位置 | 未绑定名 | 现状与影响 |
|---|---|---|
| `addons/smart_core/handlers/login.py:429` | `request` | 文件未导入 `odoo.http.request`。位于 `try` 中，`NameError` 被 `except Exception` 吞掉 → Cookie session 永不登出，只有一条 debug 日志。**静默降级。** |
| `addons/smart_core/handlers/load_contract.py:463` | `_logger` | 全文件仅此一处，无 `logging` 导入。位于 `except` 内的日志语句 → 一旦 `fields_get(missing)` 失败，会在处理异常时再抛 `NameError`。 |
| `addons/smart_construction_core/controllers/pack_controller.py:190` | `Usage` | `Usage` 从未赋值（对照 `platform_ops_controller.py:89` 的 `Usage = env.get("sc.usage.counter")`）。pack 安装成功后会 `NameError`。 |
| `addons/smart_construction_core/models/support/scene_orchestration.py:694` | `Usage` | 同上；场景发布成功后会 `NameError`。**后续低代码发布闭环（WEB-LC-01 方向）若要经过此路径，需先修。** |
| `addons/smart_core/handlers/system_init.py:1325` | `acceptance_root_group_label` | 死代码：`_append_user_data_acceptance_nav_group` 自 `401bcb3bd` 起**无任何调用点**，其函数体引用了另一个函数的局部变量。当前不可达，属潜伏缺陷。 |

本段的处理是**登记 + 保留真实状态**，不是顺手全仓清理。建议单列一批（后端 P0/P1，需走
`sc_smoke` 后端 lane 与验收后端身份刷新）。

### 8. 验收体系为什么这次是靠浏览器门禁才发现的

1. **后端单测 lane 没有随该后端提交运行。** `8890d5f0f2` 改的是 Python，但当日只跑了前端门禁；
   `sc_smoke`（`make local.dev.test MODULE=smart_construction_core TEST_TAGS=sc_smoke…`）本可**直接**
   抓住它——本段修复前的负例正是这条 lane 报的 `4 error(s) of 6 tests`。
2. **没有未定义名的静态检查。** 仓库无 `flake8` / `ruff` 配置，`ci.local.iteration` 只做 L1 静态
   （`git diff --check`、增量计划、可信扫描范围），不解析 Python 名字绑定。用一个 30 行的
   `symtable` 扫描即可在本段复现该类缺陷（`addons/**/*.py` 1255 个文件 → 7 个疑似命中，经人工分类
   得到上表 5 处真缺陷；本段触及的模块扫描结果为 0）。
3. **前端门禁反而成了唯一防线**，因为「财务角色能不能读我的工作」是跨模型浏览器旅程里的一条断言。
   这说明跨模型旅程本身有价值，但**不能让它承担后端静态缺陷的兜底**。

由此固定两条规则：

- **改动 `addons/` 后必须至少跑一次受影响模块的非零后端测试**（按 `sc_smoke`/`sc_gate` 标签选择，
  不是全量），再进入浏览器层。
- **浏览器层失败必须先定位到「契约/后端/前端/探针」哪一层**，本段即是「先怀疑探针失配、实测为后端
  500」的反例；没有 §2 的第 1~5 步逐层证据，就会把产品缺陷误修成选择器适配。

### 9. 本段提交

- `bd898fb35 fix(payment): import the role-code helper the action entry calls`（产品修复）
- `1c95d4a74 chore(docs): refresh the component-driver takeover inventory digest`（派生清单跟随源码刷新；
  该刷新在修复前即为既有失败，`required=35 missing=0 bridge_only=0 raw=0`）

运行来源：源码 HEAD `1c95d4a74`；前端产物仍为 `sce-offrepo/artifacts/config05-20260929/dist`
（`base_sha=25b31e714…`、`entry=/assets/index-CNrigT9d.js`、`entry_sha256=4d80190b…`）——
本段 `frontend/` 无源码变化，`identity` 校验通过，故**不重建、不新增端口**；5180 仍为 `pid=802966`。
验收后端已从 `eb479cedb6` 刷新到 `1c95d4a74`。

### 10. 剩余（显式登记，不在本段）

- §7 的 5 处同族未定义名缺陷（含 1 处会影响场景发布路径）。
- `workflow_contract_backend` 的 7 条既有失败（测试夹具/状态守卫，与 Mock 或数据基线相关，未在本段定性）。
- 上一段已登记项继续有效：`sc.safety.disclosure` / `sc.safety.plan` 原生 header 无 workflow 按钮；
  缺失 `view_type` 仍默认 `form`；五条 `state_transition_undeclared`；`style_system.guard` 四项文件长度欠账。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## FE-CONTRACT-UNDEFINED-NAME（续）：名字未绑定族收口 + `env.get` 真值陷阱清理（2026-09-30）

### 1. 七问

| 项 | 结论 |
|---|---|
| `Formal Product Layer` | P0 平台内核（`smart_core`）+ P1 行业标准（`smart_construction_core`），运维/校验脚本属 P4 |
| `Layer Target` | 写动作审计落库、用量计数、能力可见性报告、登录登出、契约加载器、场景发布、工作流状态盘点；`make/ci.mk` 的 L1 入口 |
| `Module` | `smart_core`、`smart_construction_core`、`scripts/`、`make/` |
| `Standard vs User-Specific` | 平台机制缺陷（名字绑定、`env.get` 语义、审计/计数/去重落库），不含任何行业或客户偏好 |
| `Why Here` | 缺陷就在这些模块的调用链上；`env.get` 真值判断是 Odoo 平台语义误用，必须由平台内核与行业标准模块承担 |
| `Why Not Elsewhere` | 不在前端兜底（前端无法感知后端未落审计）、不改后端事务、不新建治理文档、不做全仓重构或顺手拆文件 |
| `Blast Radius` | 审计落库恢复写入、用量计数恢复累加、能力报告恢复返回真实 payload；受影响写动作的幂等/去重响应字段口径须重新核对（见 §5） |

### 2. 上一段 §7 登记的同族缺陷：已全部修复

| 位置 | 未绑定名 | 修复方式 | 运行期影响 |
|---|---|---|---|
| `smart_core/handlers/login.py` | `request` | 补 `from odoo.http import request` | logout 分支不再静默 `NameError`（此前被 `except` 吞掉 → Cookie session 永不登出） |
| `smart_core/handlers/load_contract.py` | `_logger` | 补 `import logging` + `_logger` | 异常分支不再在处理异常时二次抛 `NameError` |
| `smart_core/handlers/system_init.py:1325` | `acceptance_root_group_label` | 改为形参传入 | 函数体恢复自洽；**仍无调用点**，性质仍是"潜伏死代码" |
| `smart_construction_core/controllers/pack_controller.py` | `Usage` | 补 `Usage = env.get("sc.usage.counter")` | pack 安装成功后不再 `NameError` |
| `smart_construction_core/models/support/scene_orchestration.py` | `Usage` | 同上 | 场景发布成功后不再 `NameError`；新增运行时回归（§7） |
| `smart_construction_core/models/support/sc_data_validator.py` | `_` | `from odoo import _, api, fields, models` | 校验器取用翻译函数不再 `NameError` |
| `smart_core/tests/test_contract_governance_project_form.py` | `visible_fields` | `out.get("visible_fields") or []` | 断言读取真实字段；`NameError` 变为真实断言结果（§8） |
| `scripts/verify/{ops_batch_smoke,subscription_smoke}.py` | `_load_env_value_from_file` | 改用已 import 的 `load_env_value_from_file` | DB 名回退路径恢复 |
| `scripts/verify/product_hardening_schema_guard.py` | `EXPECTED_INTENTS` | 改用 `REQUIRED_INTENTS | OPTIONAL_INTENTS` | 校验失败信息恢复，不再二次 `NameError` |

### 3. 本段真正的产品缺陷：`env.get("<model>")` 真值判断恒假

Odoo `Environment.get(model)`：

- 模型**存在** → 返回**空 recordset**，`bool()` 为 `False`；
- 模型**不存在** → 返回 `None`，同样 `False`。

所以 `if env.get("sc.audit.log"):` 与 `if not env.get(...):` **永远走假分支**，而作者本意是"模型是否可用"。
这不是代码风格问题，是**静默禁用功能**。仓库里已有正确对照（团队早已踩坑，附中文注释）：
`addons/smart_core/utils/idempotency.py` 的 `if Audit is None: ...`。

按 `is None` 修正、从而**恢复**的能力：

| 位置 | 此前被静默禁用的能力 |
|---|---|
| `smart_core/handlers/api_data_write.py` | `api.data.write` 幂等审计**从不落库** |
| `smart_core/handlers/api_data_unlink.py` | `api.data.unlink` 幂等审计**从不落库** |
| `smart_core/handlers/api_data_batch.py` | `api.data.batch` 幂等审计**从不落库**（连带"重放窗口"永远判不出来） |
| `smart_construction_core/handlers/my_work_complete.py`（两处） | 批量完成审计不落库；`todo_remaining` 恒为 0 |
| `smart_construction_core/handlers/payment_request_approval.py` | 付款审批审计不落库 |
| `smart_construction_core/handlers/capability_visibility_report.py` | 能力可见性报告**恒返回空 payload** |
| `smart_construction_core/controllers/pack_controller.py` | `packs_installed` 从不累加 |
| `smart_construction_core/models/support/scene_orchestration.py` | `scenes_published` 从不累加 |
| `smart_core/controllers/platform_ops_controller.py`（3 处） | 权益/用量/订阅查询恒走空分支 |
| `scripts/audit/workflow_state_inventory.py`（2 处） | tier / business-category 统计恒为 0 |
| 7 处测试 `if not self.env.get(...): skipTest(...)` | **测试长期被静默跳过**（见 §6） |

### 4. 静态门禁：`scripts/verify/python_name_binding_guard.py`

新增两族静态检查（`symtable` 语义，不需要运行环境）：

1. **名字被读但从未绑定**（`F821` 语义）→ 运行期 `NameError`；
2. **`env.get("<model>")` 结果参与真值判断**（含 `if/while/三元/assert/assertTrue/assertFalse/变量间接`）。

豁免按"显式命名单条、无通配目录"实现：builtins/dunder、`import *` 与 `globals()`（跳过并计数）、
行内 `# noqa`（含既有 `# noqa: F821` 拼法）、`scripts/` 下的 `env`/`odoo`（`odoo shell < script.py` 注入；
`addons/` 不豁免）。

- 正例：**2844 文件 / 0 违反**（59 个动态绑定模块显式计数跳过）。
- 负例（先证明抓得住）：把本段修复逐个回退后，门禁精确报出 **4 个名字缺陷 + 8 个 `env.get` 真值缺陷**。
- 自测 `scripts/verify/test_python_name_binding_guard.py`：**19 用例全通过**。
- 接入：`make verify.python_name_binding`，并作为 `make test.unit` 依赖。

### 5. 三处"测试 vs 产品语义"冲突：按规则冲突流程核清权威依据

激活被静默跳过的测试后暴露 3 处失败。**不由测试或页面自行选一方**，先找已发布契约：

- `contracts/domain/write-idempotency.yaml`：
  `replay_window_expired` = "信息性标记（记录权威路径下 replay 不受窗口限制——键即逻辑操作，永久可重放；
  窗口仅保留信封可观测语义）。审计投影回退路径仍按窗口截断。"
  `fallback` = "`sc.idempotency.record` 缺席时回退既有审计投影路径（`resolve_idempotency_decision` 窗口语义不变）。"
- `smart_core/utils/idempotency.py` G7 段注释同义；`write_idempotency_source_authority_contract()` 输出
  `replay_policy=permanent_for_key`、`window_semantics=informational_only`。
- `smart_core/tests/test_write_idempotency_claim.py::test_done_beyond_window_still_replays_with_expired_flag` 已固化该语义。

结论：**测试假设陈旧，不是产品缺陷。** 三条断言写于 `401bcb3bd`（审计通道时代），G7 `7e622c35a`
迁移到记录去重权威后未同步，又因静默跳过而无人发现。修正断言，**不触碰产品语义**：

| 测试 | 陈旧假设 | 修正后的断言 |
|---|---|---|
| `test_my_work_backend.test_batch_idempotent_replay_returns_same_contract` | 重放证据来自审计行（`replay_from_audit_id > 0`） | 记录通道证据 `replay_from_record_id > 0` |
| `test_my_work_backend.test_batch_idempotent_window_expired_no_replay` → 更名 `test_batch_replay_is_permanent_regardless_of_window` | 「window=0 即过期，故不重放」 | window=0 表示"无窗口限制"→ **仍然重放**且信息标记为假；把记录 `created_at` 拨到窗口外 → **仍然重放**且信息标记为真 + `REPLAY_WINDOW_EXPIRED` |
| `test_api_data_batch_contract_backend.test_replay_window_expired_is_exposed_in_contract` | 用 window=0 制造过期 | 该通道是**审计投影回退路径**（窗口语义保留）：把审计 `ts` 拨到窗口外，确定性地得到"不重放 + 标注过期" |

**测量教训（固化）**：`window = 0 ⇒ 过期` 这个直觉在**两个通道上都不成立**——记录通道是"永久重放"，
审计通道是"秒级精度，同一秒内仍算窗口内"。窗口类断言必须**显式构造时间差**，不能靠把窗口置 0。

### 6. 验收体系为什么长期没发现（本段真正的机制缺口）

1. **`skip` 被当成"通过"。** 7 处 `if not self.env.get("sc.audit.log"): self.skipTest(...)` 因真值陷阱
   **永久跳过**：报告里是 `skip`，CI 只看 "0 failed" 就放行。改为 `is None` 后这些用例**首次真正执行**，
   并立刻暴露 3 处语义漂移（§5）。
2. **没有名字绑定静态检查。** `scripts/ci/python_syntax_check.py` 只建 AST、不做绑定解析；仓库无
   `flake8`/`ruff` 配置。本段新增门禁补上这一层。
3. **大量测试文件未接入任何 lane。** `addons/smart_core/tests/` 160 个测试文件中 **117 个无 `@tagged`**，
   默认标签是 `at_install`，而仓库所有 lane 都用显式自定义标签（`sc_smoke`/`sc_gate`/业务标签）或
   `post_install` 标签；`at_install` 只在"该模块正在安装/升级"时执行，而迭代 lane 传 `-d` 不带 `-u`，
   因此这些文件**平时根本不跑**——与已登记的"121 个未接入测试文件"是同一件事。

新增固定规则：

- 判"测试通过"必须同时看 **test count 非零** 与 **skip 数**；`skip` 不得等价于 `pass`。
- 新增/修正静态门禁必须**先给负例**（回退修复能精确报出），再给正例。
- 测试与产品语义冲突时，先找**已发布契约/权威常量**；找不到权威依据才升级为产品缺陷，
  **不允许改产品去迎合测试**。

### 7. 定向验证（分层结果）

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make verify.python_name_binding` | PASS（2844 文件 0 违反；自测 19 用例 OK） |
| L1 | `make test.unit` | PASS（含 `verify.python_name_binding` 前置） |
| L1 | `make verify.guard.registry` | PASS（`AUDIT PASS: 1352 scripts`） |
| L1 | `make ci.local.iteration` | PASS `coverage=L1_only`；`frontend/` 无源码变化 → 不选前端 L2 |
| L2 | `local.dev.test MODULE=smart_construction_core TEST_TAGS='api_data_batch_backend,my_work_backend,capability_contract_backend'` | **PASS 46 tests, 0 failed**（修复前 3 failed） |
| L2 | `local.dev.test MODULE=smart_construction_core TEST_TAGS='scene_publish_usage_backend'` | **PASS 1 test, 0 failed**（新增回归：发布后 `scenes_published` 真实累加） |
| L4 | `verify.frontend.standard_page_type.browser`（`default` / `detail` / `additional`） | PASS **32 / 19 / 3**；`forbiddenWrites=[]`、`errors=[]` |
| L4 | `verify.frontend.standard_bootstrap.browser` | PASS `roles=3` |

L4 全部绑定的验收后端为 `d66182a91`（`make backend.acceptance.replace-stale` 刷新所得）。
`frontend/` 本段无源码变化 → 5180 复用既有产物（`pid=802966`），**未重建、未新增端口**。

### 8. 既有失败对照实验（证明与本段无关）

`smart_core` 整模块跑出 `2 failed, 11 errors of 408`。用 `git stash`（含未跟踪文件）把本段**全部**改动移出后
重跑，失败身份**完全一致**：

- `TestOdooNativeAlignmentBoundaries.test_explicit_form_view_preserves_mixed_text_and_field_order`
  （`'电话' != 'Phone'`，DB 本地化漂移）；
- `TestUmP1OwnershipVisibilityContractOrm.test_real_registry_preserves_record_rule_topology_and_explicit_gaps`
  （记录规则域文本与注册表现状漂移）；
- `TestUmP2ReceiptRelationAggregationOrm` ×4（`could not serialize access due to concurrent update`，DB 并发）；
- `TestUmP1{Payment,CostLedger}Visibility...` / `TestUmP2PaymentRelation...` / `TestUmP3...` 的 `setUpClass`
  （**测试夹具绑定了会漂移的演示数据/能力状态**，如"付款申请必须处于已批准状态"、
  `TPV1_SIGNED_MAINTENANCE_CAPABILITY_REQUIRED`）。

另单独对照 `tenant_extension`：`0 failed, 1 error of 0 tests`（`setUpClass` 能力门禁），同样与本段无关。

**结论：13 条全部是既有失败或环境数据漂移；本段未新增失败、未扩大失败面。**

`test_contract_governance_project_form.py` 独立执行对照（`odoo shell` 直接跑该文件）：

- 修复前 `7 failures + 2 errors / 21`；
- 修复后 `8 failures + 1 error / 21`。

非通过总数不变（9 → 9）：本段把 1 个 `NameError` 变成真实断言失败，**未引入回归**。该文件 9 条非通过为
**既有**，且属"未接入 lane 的测试文件"，本段只登记不修。

### 9. 提交

- `90e1c456f fix(backend): restore writes disabled by unbound names and env.get truthiness`
- `e493a441f test(guard): detect unbound names and env.get truthiness statically`
- `d66182a91 chore(docs): refresh generated reports for the name-binding guard`

### 10. 剩余（显式登记，不在本段）

- §6.3 的 117 个无 `@tagged` 测试文件（与已登记的"121 个未接入测试文件"合并计账）；
- `test_contract_governance_project_form.py` 的 9 条既有非通过；
- `smart_core` 整模块 13 条既有失败（含 6 条夹具/数据漂移类）；
- `system_init.py:_append_user_data_acceptance_nav_group` 仍无调用点（死代码，本段只恢复自洽）；
- `make verify.docs.product_boundary` 既有失败：`modules documented but not present under addons: smart_construction_demo`。
  已核对：`addons/smart_construction_demo` 在 `7a963bbb7` 与本段 HEAD **均不存在**，且引用它的文档
  （`docs/demo/*`、`docs/planning/.../G7_LAUNCH_SCOPING.md` 等）本段**未触碰** → 与本段无关。
  `verify.docs.inventory` / `docs.links` / `docs.temp_guard` / `docs.contract_sync` 均 PASS；
  `verify.docs.all` 只因 product_boundary 这一项中断。
- 上一段已登记项继续有效：`workflow_contract_backend` 7 条既有失败、`sc.safety.disclosure` /
  `sc.safety.plan` 原生 header 无 workflow 按钮、缺失 `view_type` 仍默认 `form`、五条
  `state_transition_undeclared`、`style_system.guard` 四项文件长度欠账。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。


## FE-CONTRACT-TAKEOVER-RULE-01：把接管清单"对外声明"的完成规则变成"实际被求值"（2026-09-30）

分支 `feature/web-official-template-adoption`；本段起点 HEAD `e3412b370`（工作树干净）。
延续前端接管专题的验收体系收口，不新建专题、不改业务矩阵、不进入下一批业务接管。

### 1. 七问

- **Formal Product Layer**：P4 ops/verify 工具（`scripts/audit` 的接管清单生成器与其单测、派生清单），
  以及被清单描述的前端渲染面（P1 行业标准产品的前端呈现层）。不新增业务语义。
- **Layer Target**：`scripts/audit/generate_frontend_component_driver_takeover_inventory.py`、
  `scripts/audit/test_generate_frontend_component_driver_takeover_inventory.py`、
  `docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json`
  及三件指纹绑定派生清单。
- **Module**：无 Odoo 模块改动；不改 `smart_core` / `smart_construction_core` / 前端产品源码。
- **Standard vs User-Specific**：属平台级验收约定（每条正式产品线共用同一清单契约），非客户或行业特例。
- **Why Here**：完成规则由该清单自己发布，因此只能由该清单自己的 `--check` 求值；放在别处就会出现
  "第二份口径"，正是本段要消除的东西。
- **Why Not Elsewhere**：不改前端产品源码——`ScSteps` / `ScAutoComplete` 的必需性判定是**契约层**结论，
  不能用"删掉适配器"或"随便找一处塞进去"来消灭条目。
- **Blast Radius**：仅接管清单的必需驱动集（35 → 33）与其 `--check` 行为；前端渲染、契约、权限、
  后端事务、数据库、业务矩阵均不变。

### 2. 真实缺陷（先有运行证据，再改代码）

本段起点的门禁是**绿**的：

```
$ make verify.frontend.component_driver_takeover.unit
[component_driver_takeover_inventory] PASS required=35 missing=0 bridge_only=0 raw=0
```

但同一份清单在 JSON 里对外发布了一条完成规则：

```
missing=0, bridge_only=0, adapter_unconsumed=0, unassessedRequiredTakeovers=0,
directLibraryImportBypasses=0, unassessedRawBehaviorSurfaces=0
```

实测这份清单**违反**其中两项：

- `adapter_unconsumed` 实际为 **2**——`ScAutoComplete`、`ScSteps` 的适配器存在、`productionConsumerCount=0`；
- `unassessedRequiredTakeovers` 在 `summary` 里是**硬编码常量 `0`**，从未由行数据推导，因此不可被证伪。

也就是说：**清单对外声明了一条完成规则，而门禁只验证"JSON 是否与生成器一致"，规则本身从未被计算。**
只要 JSON 与生成器同步，规则被违反也照样报绿。这与上一段 `env.get` 真值判断同属一类：
**口径比事实松，缺口被静默。**

对照：同一目录下的 `generate_frontend_official_design_alignment_inventory.py` 的 `--check` **确实**对真实报告
逐项求值（`unknownProjectTokenOverrideCount` 等四项非 0 即 `FAIL incomplete=...`）。
正确模式就在隔壁，接管清单缺的正是这一步。

### 3. 负例（先证明回归真的抓得住）

**端到端负例**（把 `steps` 加回 `REQUIRED_DRIVERS`，再重新生成——即 JSON 与生成器**一致且最新**）：

```
$ python3 scripts/audit/generate_frontend_component_driver_takeover_inventory.py --check
[component_driver_takeover_inventory] FAIL completion rule
 - adapter_unconsumed=1 (a required official adapter has no production consumer)
 - unassessedRequiredTakeovers=1 (a required driver is not fully adopted and carries no capability assessment)
exit=1
```

"最新但违规"必然失败——这正是旧门禁放行的那种状态。负例执行后已恢复。

**入册单测负例**：`test_required_driver_without_consumer_fails_the_completion_rule`、
`test_unassessed_takeover_is_derived_from_rows_not_hardcoded`；
另有 `test_published_completion_rule_is_evaluated_and_clean` 正向锁定当前仓库为零违反。

### 4. 修复

1. `--check` 新增 `completion_rule_failures(report)`：对 `completionRule` 声明的**每一项**求值
   （summary 的四个计数 + 两个列表），非 0 / 非空即 `FAIL completion rule` 并逐项打印。
2. 成功行补齐它此前漏印的两项：`adapter_unconsumed=`、`unassessedRequiredTakeovers=`。
3. `unassessedRequiredTakeovers` 改为**由行数据推导**：必需驱动中"未完全采纳且没有能力评估归属"的条数。
4. 按第 5 节的契约依据，把 `steps` / `auto-complete` 从 `REQUIRED_DRIVERS` 移入
   `NOT_REQUIRED_DECISIONS`（必需驱动集 35 → 33）。

### 5. 两项 `adapter_unconsumed`：按"契约是否声明该语义"裁决，不是把红改绿

| driver | 裁决 | 依据（已发布契约 / 仓库自身权威） |
|---|---|---|
| `auto-complete` | `not_required` | Contract V2 **没有**"自由文本 + 建议"字段类型。关系输入是官方可过滤组合框（`ProfessionalRelationFieldControl` → `ScRelationField` → `TDesignSelect filterable`）；其余字段类型全部落入取值确定的 value 控件（`professionalComponentRegistry.ts` 的 `REGISTRATIONS` 字段类型集：`char/text/html/integer/float/monetary/selection/boolean/date/datetime/binary/many2one/many2many/one2many/action`）。独立 AutoComplete 必须**自造**一个契约未声明的建议源。 |
| `steps` | `not_required` | Contract V2 把工作流状态声明为**选择（selection）**，不是有序流程；仓库自己的守卫 `scripts/verify/frontend_professional_workflow_guard.py` 明确禁止状态区出现 `<ScSteps` 或 `native-statusbar-track`——原文即 "selection status must not imply ordered workflow topology"；审批策略是**可编辑配置列表**，不是记录流程。 |

并留下"没有遗漏面"的证据：全仓检索无任何自造步骤指示器（只有可编辑审批表
`BusinessConfigApprovalPanel.vue` 与一处上下文条 `contract-form-design-strip`，后者是三列信息条而非序列），
也没有任何页面的自由文本建议控件；因此不存在"应改用官方 Steps/AutoComplete 却用了自造实现"的遗漏面。

**适配器本身保留**：bridge 与适配器仍在 `primitives.ts` / `tdesignPrimitiveBridge.ts` / `primitiveAdapter.ts`，
仍受 `frontend_primitive_adapter_guard.py`、`frontend_rendering_detail_state_guard.py` 约束；
变的只是"当前正式产品的**必需驱动集**"。若将来产品声明了有序流程面或建议输入面，
该条必须从 `NOT_REQUIRED_DECISIONS` 退回 `REQUIRED_DRIVERS`，而不是让页面自造实现。

### 6. 验收体系为什么长期没发现（本段真正的机制缺口）

1. **成功行漏印关键项**。门禁 PASS 行只打印 `required/missing/bridge_only/raw`，
   恰好漏掉 `adapter_unconsumed` 与 `unassessedRequiredTakeovers`——报绿的信息量小于它宣称的范围。
2. **断言了规则的文本，没断言规则本身**。既有单测
   `test_completion_rule_cannot_hide_unassessed_raw_behavior` 只断言 `completionRule` 字符串里**包含**
   `adapter_unconsumed=0`，从未断言这个等式**成立**。
3. **常量冒充推导值**。`unassessedRequiredTakeovers` 以字面量 0 写进 summary，使它天然不可被证伪。

固化规则（本段起适用）：**凡清单/报告对外发布的 `completionRule`，其每一项都必须在同一 `--check` 内被求值，
且成功行必须逐项打印实际值；字符串包含关系不作为通过依据。**

**同类缺口的全仓收敛核对（本段已执行）**：

- 生成器侧：`rg completionRule scripts/` 只有两处发布者——
  `generate_frontend_official_design_alignment_inventory.py`（其 `--check` **本就**对真实报告求值，正确模式）
  与 `generate_frontend_component_driver_takeover_inventory.py`（本段修好）。两者现已全部强制求值。
- 报告侧：扫描 `docs/**/*.json` 中 `completionRule` 含 `=0` 字样的报告，命中**恰为上述两件**。
- 单测侧：其余 `assertIn(..., rules)` 命中都是记录规则 XML 的**内容**断言（如 `tenant_product_payload_boundary_guard`、
  `tax_certificate_formal_contract`），不是"规则文本通过即视为规则成立"，不属同类缺陷。

即：这一类"发布规则但不计算规则"的缺口在本段之后**全仓为零**，并有本节判据可供后续复查。

### 7. 顺带收口：两件陈旧派生清单（既有，先取基线证明与本段无关）

`make verify.frontend.rendering_detail_state.unit` 在本段起点即为**红**：

```
[frontend_rendering_detail_inventory] FAIL stale=.../component-professionalization-inventory-v1.json
```

**归属判定**：把本段三处改动 `git stash`（含生成物）后复跑，失败身份**完全一致** → 与本段无关。
根因：`26ed7116e refactor(web): render the configuration overview with the official table` 新增 P3 面
`BusinessConfigOverviewTable.vue`，但未按注册目标刷新指纹绑定生成物。

按既有恢复动作 `make refresh.frontend.rendering_detail.inventory` 刷新 3 件。
逐件核对差异，**无内容漂移**：

- `component-professionalization`：`inputDigest`/`sourceIdentity` 变化 + **1 条真实新增 P3 surface**
  （`surfaces` 171→172、`summary.p3_out_of_scope` 18→19），即那个新文件本身；
- `visual-projection`：`currentInputDigest` 变化 + `currentSourceCount` 225→226、`changedSourceCount` 207→208，
  以及跟随的逐源 digest；
- `official-design-alignment`：`inputDigest` 变化 + `section-tab` 一项消费方清单跟随真实源码。

复跑 `make verify.frontend.rendering_detail_state.unit` **PASS**
（59 测 OK；`rendering_detail_inventory PASS surfaces=172 gaps=0`、`visual_projection PASS`、
`official_design_alignment PASS summary={... internalVendorSelectorGapCount: 0 ...}`）。
（输出里那行 `[frontend_official_design_alignment_inventory] FAIL incomplete={'internalVendorSelectorGapCount': 1}`
是单测 `test_check_fails_closed_when_completion_rule_has_gaps` 的**预期负例输出**，不是失败。）

### 8. 验证（分层结果）

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS `change_state=dirty scope=unclassified_by_design coverage=L1_only` |
| L1 | `make verify.guard.registry` | PASS `AUDIT PASS: 1352 scripts` |
| L1 | `make ci.generated_reports.guard` | PASS（含 `tracked generated reports are current`） |
| L1 | `make test.unit` | PASS（Python 语法 1170 文件、名字绑定 2844 文件 0 违反） |
| L2 | `make verify.frontend.component_driver_takeover.unit` | **PASS 10 tests**（原 7）；`PASS required=33 missing=0 bridge_only=0 adapter_unconsumed=0 unassessedRequiredTakeovers=0 raw=0` |
| L2 | `make verify.frontend.rendering_detail_state.unit` | **PASS 59 tests** + 3 件清单 `--check` 全 PASS（起点为红，见 §7） |
| L2 | `make verify.frontend.primitive_adapter.unit` | PASS `components=46 eventCases=11` |

未运行 L4 浏览器旅程：本段**未改前端产品源码**，页面呈现、交互与请求路径均未变化，
按分层规则不触发受影响浏览器复验（`frontend/` 无源码变动 → 5180 复用既有产物，未重建、未新增端口）。

### 9. 提交

- `fix(guard): evaluate the published component takeover completion rule`（生成器 + 单测 + 清单）
- `chore(web): refresh the stale rendering-detail inventories`（3 件派生清单，§7）

### 10. 剩余（显式登记，不在本段）

- 本段**新登记**：`frontend_primitive_adapter_guard.py` 的 `PRIMITIVES` 与
  `primitive_adapter_contract_test.ts` 仍把 `ScSteps` / `ScAutoComplete` 列为**必须存在且合规**的适配器。
  这是有意的：适配器保留，只是"当前正式产品必需驱动"集不含它们；两处清单口径不矛盾，但需在文档中并存说明。
- 承接上一段全部登记项：`state_transition_undeclared` 五条（权威侧待决）、
  `sc.safety.disclosure` / `sc.safety.plan` 原生 header 无 workflow 按钮、缺失 `view_type` 仍默认 `form`、
  `workflow_contract_backend` 7 条既有失败、`style_system.guard` 四项文件长度欠账、
  117 个无 `@tagged` 而未接入 lane 的 `smart_core` 测试文件、
  `test_contract_governance_project_form.py` 9 条既有非通过、`smart_core` 整模块 13 条既有失败
  （含 6 条夹具/数据漂移类）、`verify.docs.product_boundary` 既有失败（`smart_construction_demo`）、
  `playwright_vendor_coupling` 探针层既有债务（vendor 内部类 22 文件 / 几何断言 11 文件）。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

---

## 段 28｜低代码管理面的原生行为面盲区（P3 契约外观边界，2026-09-30）

### 1. 边界七问

| 项 | 结论 |
|---|---|
| **Formal Product Layer** | P0（`smart_core` 契约结构与守卫）＋ P4（前端呈现适配），不新增业务层 |
| **Layer Target** | `scripts/audit/generate_frontend_component_driver_takeover_inventory.py`；`frontend/apps/web/src/views/SceneHealthView.vue`、`ScenePackagesView.vue`、`views/businessConfigSurface/BusinessConfigChangeSetPanel.vue` |
| **Module** | `smart_core`（契约/守卫）；`frontend/apps/web`（消费） |
| **Standard vs User-Specific** | 平台标准：**"原生行为元素只能存在于设计系统适配层"** 是通用呈现规则，不属任何行业或客户语义 |
| **Why Here** | 只有这里同时掌握"契约声明的分区角色"和"页面实际渲染的元素"；判定必须发生在能同时看到两者的守卫里，页面自身不能自证 |
| **Why Not Elsewhere** | 不放后端：后端不渲染 DOM，无法判断页面是否用原生元素；不新增治理文档：既有接管清单本就是该规则的发布者；不改契约 `tag`：`tag` 是**布局角色**（呈现策略），不是组件指定，且已被 `frontend_page_contract_boundary_guard.py` 固定 |
| **Blast Radius** | 接管清单评估范围由「非 P3 且非设计系统」扩到「全部产品前端，除设计系统适配层」；3 个 P3 页面改为官方组件；4 件派生清单刷新。菜单/模型/后端/请求载荷零变化 |

### 2. 已确认缺口：发布规则却在**评估范围上留洞**

前一段修掉了"发布 `completionRule` 但从不求值"。本段在同类检查里发现第二层：

```python
if not is_p3(source) and "/components/design-system/" not in source and source not in {
    "frontend/apps/web/src/components/MenuTree.vue",
    "frontend/apps/web/src/components/product-shell/CanonicalNavigationMenuNode.vue",
}:
    ... 收集 rawBehaviourSurfaces ...
```

`not is_p3(source)` 把**整个低代码管理面（P3）**排除在原生行为扫描之外。
于是规则文本写着 `unassessedRawBehaviorSurfaces=0`，实际生产面上仍有原生行为在渲染。
`scope` 字段自称 `repository P0/P1 frontend production sources`，与实现共同把缺口包装成"范围之外"。

**让缺口显现**（只计算、不落盘，改动生成器后第一次求值）：

```
raw surfaces:
  views/SceneHealthView.vue                        ['details', 'window.confirm']
  views/ScenePackagesView.vue                      ['window.confirm']
  views/businessConfigSurface/BusinessConfigChangeSetPanel.vue  ['details']
completion failures:
  unassessedRawBehaviorSurfaces=3 (...)
```

三项全部落在 P3。这正是"契约缺口必须显现"的反面教材：**看板绿，页面红**。

### 3. 裁定：`tag="details"` 不是契约越界

对 `page_contracts_builder.py` / `workspace_home_contract_builder.py` 的 `sections[].tag` 逐值统计：
`section`×68、`header`×8、`div`×5、`details`×4。裁定如下，**本段不重命名 tag 词表**：

- `tag` 表达的是**布局角色**（结构语义），属"受管呈现策略"，不是组件指定，也不声明授权、状态迁移、业务唯一性或计算公式；
- 词表取 HTML5 **语义元素名**（`header`/`section`/`div`/`details`），四者同级，不是把某个 TDesign 组件写进契约；
- 因此契约给角色，**前端负责选择实现组件**：`header`/`section`/`div` → 原生语义容器；`details` → **官方 `ScDisclosure`**（TDesign Collapse），不再是原生 `<details>`；
- 守卫只把**带行为语义**的原生元素（`button|input|select|textarea|table|dialog|details` 与 `window.confirm/alert/prompt`）计为缺口；纯布局容器（`header`/`section`/`div`）允许原生。这条口径写进本段并由此守卫执行；
- 重命名 `details` 会牵动 `SectionTag` 联合类型、`sectionLayout.ts`、`pageContract.ts` 与 4 处消费点，且 `page_contract_boundary_guard` 已把 `"tag": "details", "open": True` 固定为必需契约文本——**无收益、有回归面**，不在本段。

`window.confirm` 则无争议：仓库其余全部位置都走受管确认权威 `IntentConfirmationDialog`（`ScDialog` + 嵌套遮罩焦点/滚动恢复），这两处是**唯一的例外**。

### 4. 修复

产品侧（`fc38e62f6`）：

- `SceneHealthView`：3 处原生 `<details>/<summary>` → `<ScDisclosure :title="..." :open=... :style=...>`，保留 `pageSectionTagIs(..., 'details')` 角色守卫与 `pageSectionOpenDefault` 默认展开；作用域样式 `details`/`summary` 选择器改为 `.health-details`（不再样式化原生元素）；
- `SceneHealthView`（rollback）、`ScenePackagesView`（import）：`window.confirm` → `await ref.confirm({actionLabel, message})`，**确认放在 `busy = true` 之前**，取消不再闪现 loading，也不再需要 `busy=false` 回滚写；
- `BusinessConfigChangeSetPanel`：`.high-risk-boundary` 原生 `<details>` → `<ScDisclosure>`。

守卫侧（`0cd4d0a03`）：

- 去掉 `not is_p3(source)` 与两个**惰性**名称排除（`MenuTree.vue`、`CanonicalNavigationMenuNode.vue` 实测无任何原生行为，排除只留未来盲点）；**设计系统适配层排除保留**，因为在适配层实现 primitive 正是它的职责；
- `scope` 更正为 `repository P0-P4 frontend production sources except the design-system adapter layer`；
- 失败信息由"只有一个计数"改为**逐源可定位**：`unassessedRawBehaviorSurfaces=3 (... SceneHealthView.vue(details+window.confirm), ...)`；
- 新增 `productLayer` 字段，失败时能直接判断是 P3 还是主产品面。

### 5. 负例（先证明门禁会红）

`0cd4d0a03` 之前先用**未修复的真实源码**求值，得到 §2 的三项失败（非构造样本）。
另有入册单测三条（`scripts/audit/test_generate_frontend_component_driver_takeover_inventory.py`，10 → 13 测）：

- `test_raw_behavior_surface_inside_p3_administration_is_evaluated`：把含 `<details>` 的临时文件放进 P3 前缀目录，必须被计入且 `productLayer=P3`；**若有人把 `not is_p3(source)` 加回去，这条立即失败**；
- `test_native_confirmation_api_is_a_raw_behavior_surface`：`window.confirm` 必须被计入（覆盖非 P3 通用路径）；
- `test_design_system_adapter_layer_may_own_native_elements`：设计系统层内的 `<button>` 必须**不**计为缺口（正向对照，防止守卫扩大化）。

### 6. 验证（分层结果）

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS `change_state=dirty scope=unclassified_by_design coverage=L1_only` |
| L1 | `make verify.guard.registry` | PASS `AUDIT PASS: 1352 scripts` |
| L1 | `make ci.generated_reports.guard` | PASS |
| L2 | `make verify.frontend.component_driver_takeover.unit` | **PASS 13 tests**（原 10）；`PASS required=33 missing=0 bridge_only=0 adapter_unconsumed=0 unassessedRequiredTakeovers=0 raw=0` |
| L2 | `make verify.frontend.rendering_detail_state.unit` | **PASS 59 tests** + 3 件清单 `--check` 全 PASS（`rendering_detail_inventory surfaces=172 gaps=0`、`visual_projection PASS`、`official_design_alignment PASS internalVendorSelectorGapCount=0`） |
| L2 | `make verify.frontend.primitive_adapter.unit` | PASS `components=46 eventCases=11` |
| L2 | `make verify.frontend.typecheck.strict` | PASS（`vue-tsc --noEmit` 两套配置） |
| L2 | `verify.frontend.state_dashboard.unit` / `scene_component_bridge.unit` / `scene_component_bridge.guard` / `global_component_capability.unit` | 全 PASS（`blocks=9 formal_gaps=0`、`checks=129`、`tests=31`） |
| L2 | 6 条契约消费/边界守卫（`page_contract_boundary`、`orchestration_consumption`、`product.contract_consumption`、`scene_governance_consumption`、`section_tag_coverage`、`section_style_coverage`） | 全 PASS（`checked_pages=17 checked_sections=85`） |

L4（受管 5180，一次构建、一次定向检查）：

- `make frontend.standard.preview.build` 单次构建 22.73s，产物替换 `sce-offrepo/artifacts/config05-20260929/dist`
  （旧候选另存 `config05-20260929-prev-8feb2ee0d`，未覆盖）。`build-identity.json`：
  `base_sha=640a97eb7`、`dirty_scope=""`、`entry=/assets/index-Clm_Nfe3.js`、`entry_sha256=fc1ee8d0…`。
  5180 监听进程仍为 `pid=802966`（`STATIC_ROOT` 指向同一路径，故**无需重启、未新增端口**），
  HTTP 回读 `index`/`entry` 的 SHA-256 与身份文件逐一相符。
- 定向探针 `artifacts/frontend-web-fix-20260928/p3-official-components/`：以受管角色
  `fixture_role_config_admin` 登录，1440×950 与 390×844 两个视口。

| 检查 | 结果 |
|---|---|
| `/admin/business-config` `.high-risk-boundary` | `data-semantic-component=ScDisclosure`、`data-disclosure-trigger` 标签为「独立高风险操作」、可展开收起、正文完整；页面 `details/summary` 计数 **0** |
| 两视口横向溢出 | 1440 与 390 均 `scrollWidth-clientWidth <= 1` |
| 写请求 | 仅 `login`；**零业务写**（`ui.business_config.*` 均为读/扫描） |
| `window.confirm` | 全程未触发原生对话框（`page.on('dialog')` 零命中） |

`ScDisclosure` 本身的渲染由同一次运行中的项目列表行（4 个实例）与上述 boundary（1 个实例）共同证明。

### 7. 未取得的证据（明确登记，不扩大权限凑证据）

`/admin/scene-health` 与 `/admin/scene-packages` 的路由守卫要求 `session.user.is_platform_admin === true`
（`router/index.ts` `adminOnly`），而受管验收环境**没有 platform-admin 夹具账号**
（`config/frontend/acceptance_environments_v1.json` 的 `role_bindings` 只有 finance / project_member /
project_manager / owner / contract_operator / config_admin）。实际访问被重定向到 `/s/projects.list`。

**不为此扩大角色或权限**：这是既有的授权边界，不是本段缺陷。因此这两个页面的页面级浏览器证据
**本轮未取得**，其改动依据为：同一官方组件在本次运行中的 5 个实例、两套 `vue-tsc` 类型检查、
以及 6 条契约消费/边界守卫。按分层规则记为 `not_run`，不写成通过。

### 8. 提交

- `fc38e62f6 fix(web): render administration disclosure and confirmation with official components`
- `0cd4d0a03 fix(guard): evaluate raw behaviour surfaces in administration sources`
- `640a97eb7 chore(web): refresh the derived inventories for the administration takeover`
- 本段记录（文档）

### 9. 剩余（显式登记，不在本段）

- 承接上一段全部登记项（`state_transition_undeclared` 五条、`workflow_contract_backend` 7 条既有失败、
  `style_system.guard` 四项文件长度欠账、117 个未接入 lane 的 `smart_core` 测试文件、
  `test_contract_governance_project_form.py` 9 条、`smart_core` 整模块 13 条、
  `verify.docs.product_boundary`、`playwright_vendor_coupling` 探针层债务），本段未触碰。
- 本段**新登记（非阻断）**：`MenuTree.vue` / `CanonicalNavigationMenuNode.vue` 的名称排除已删除，
  两文件当前无任何原生行为；若将来需要豁免，必须给出与设计系统同级的理由，不能只写文件名。
- 本段**新登记（非阻断）**：`/admin/*` 管理面在受管验收环境无 platform-admin 夹具，
  这三条管理路由的页面级回归目前只能靠组件级＋契约级证据；需要页面级证据时应单独申请夹具授权，
  不得用放宽 `adminOnly` 解决。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

---

## 段 29｜"范围排除"的同类盲区复查：层级无关的策略边界不得被层级延迟吞掉（2026-09-30）

### 1. 边界七问

| 项 | 结论 |
|---|---|
| **Formal Product Layer** | P0（`smart_core` 共享契约/守卫的判定范围）＋ P4（`scripts/audit`、`scripts/verify` 的前端守卫与其单测、派生清单） |
| **Layer Target** | `scripts/audit/generate_frontend_rendering_detail_inventory.py`；`scripts/verify/frontend_primitive_adapter_guard.py` 及两份单测 |
| **Module** | `smart_core`（守卫与清单归属）；不触及 `frontend/apps/web` 与 `frontend/packages/ui` 任何源码 |
| **Standard vs User-Specific** | 平台标准：**"层级无关的策略边界（原生控件、原生行为）必须对全产品层生效，层级延迟只能延后所有权声明，不能吞掉策略边界"** —— 与行业/客户语义无关 |
| **Why Here** | 只有生成器与守卫里能同时看到"对外声明的作用域"和"实际被求值的集合"；单测是唯一能把两者锁成不变量的地方 |
| **Why Not Elsewhere** | 不放后端：后端不渲染 DOM；不放页面：页面不能自证；不删 `is_p3` 整体：会把 19 个 P3 所有权欠账一次性变成阻断，属扩大范围；不改业务矩阵：矩阵只随已证明职责升级 |
| **Blast Radius** | 清单 `completionPolicy` 增加 `nativeControlScope`、新增 `p3OwnershipDeferred` 登记块、P3 面 `reason` 文本更新；判定顺序改变但**今日输出零差异**（P3 内原生控件命中 0）。菜单/模型/契约/请求载荷零变化 |

### 2. 为什么上一轮验收体系没发现这个偏差（根因）

段 28 修掉的是"**发布 `completionRule` 但从不求值**"。那是一次性缺陷，修完就没了。本段复查发现更根本的一层：

> **守卫的"对外口径"（`scope` / `completionPolicy` / 错误文本）与"实际被求值的集合"是两处彼此独立的声明，没有任何机器把二者绑在一起。**
> 因此任意一个提前 `return` / `continue` 都能悄悄缩窄求值集合，而对外口径不变，看板依旧全绿。

具体到三个失效环节：

1. **判定顺序无约束**：`is_p3` 提前 `return` 写在原生控件检查之前，读代码时两行都"正确"，只有把两者**组合**起来看才知道策略规则被吞掉。
2. **`--check` 只证明确定性，不证明覆盖**：清单的 `--check` 只比对"生成结果与磁盘是否一致"，不做"声明范围 ⊇ 求值范围"的语义比对。生成器与清单一致地"少检查一块"，`--check` 恒绿。
3. **单测只锁样例，不锁作用域**：既有单测断言的是具体正例/负例（某文件必须是 `gap`、某文件必须是 `governed_primitive`），没有一条断言"某条策略规则的作用域必须覆盖它声明的层级"。

**本轮的补齐方式**（对应上面三条）：

- (1) 把层级无关的策略边界移到**任何层级延迟之前**，并在原位留注释说明顺序是规则的一部分；
- (2) 让口具有可校验的形状：`completionPolicy.nativeControlScope` 显式写出覆盖层，`p3OwnershipDeferred` 让"延后"本身变成**被计数、被登记**的数据，而不是一句字符串；
- (3) 新增断言"作用域不变量"的负例测试，并**先证明旧行为会红**。

### 3. 复查方法（D = 声明范围 − 求值范围）

对 `scripts/audit/generate_frontend_*.py`（5 件）与 `scripts/verify/frontend_*guard*.py`／`*audit*.py`
逐一检查"是否存在按 P3／路径前缀的排除"，并与该文件**对外声明的范围**对照：

| 文件 | 是否有范围排除 | 对外声明的作用域 | 一致？ |
|---|---|---|---|
| `generate_frontend_component_driver_takeover_inventory.py` | 曾有 `is_p3`（段 28 已修） | `repository P0-P4 frontend production sources except the design-system adapter layer` | ✅ |
| `generate_frontend_rendering_detail_inventory.py` | `is_p3` 提前 return，**吞掉原生控件规则** | `scope` = 全部正式产品前端；`completionPolicy.nativeControlRequiresExplicitCompositeOwnership` 无限定层 | ❌ **本段修复** |
| `generate_frontend_visual_projection_inventory.py` | `consumer_primitive_visual_chrome` 排除 P3 | `scope` = `repository formal P0/P1 frontend source projection` | ✅ 声明的本来就是 P0/P1 |
| `verify/frontend_primitive_adapter_guard.py` | 原生控件规则全仓；呈现 chrome 规则排除 P3 | 文件内**无声明**，且是裸 `continue` | ⚠️ **本段改为具名声明** |
| `generate_frontend_official_design_alignment_inventory.py` | `excludedScopes` 显式含 `P3 low-code designer styling` | 已声明 | ✅ |
| `generate_frontend_professionalization_baseline.py` | `EXCLUDED_SCOPES` 已声明，无 P3 跳过 | 已声明 | ✅ |
| 其余前端守卫（约 30 处 `continue`） | 按文件后缀／diff 行过滤 | 与作用域无关 | ✅ |

结论：与 P3 有关的排除共 4 处 —— 1 处已在段 28 修复、**1 处本段修复**、1 处声明本就一致、1 处本段改为具名声明。不存在需要继续扩张的第二个同类盲区。

### 4. 已确认缺口 A：`rendering-detail` 清单的原生控件边界被 P3 延迟吞掉

```python
def classify(source, text):
    if "/components/design-system/" in source:
        return "governed_primitive", ...
    if is_p3(source):                       # ← 提前 return，吞掉下面全部规则
        return "p3_out_of_scope", "... handled by a separate P3 batch"
    if source in DELIBERATE_NATIVE_COMPOSITES: ...
    raw_controls = [...]                     # ← 层级无关的策略边界，反而在延迟之后
    if raw_controls:
        return "gap", f"formal P0/P1 surface bypasses governed adapters: ..."
```

两处不一致同时存在：

- `completionPolicy.nativeControlRequiresExplicitCompositeOwnership = True` 写的是**无限定层**的规则，
  实现上 P3 却被静默豁免；
- `reason` 声称 `handled by a separate P3 batch`，但**没有任何被登记的 P3 批次** —— 这正是"缺口必须显现"的反面。

### 5. 已确认缺口 B：原生适配守卫的 P3 呈现豁免是裸 `continue`

```python
if RAW_INTERACTIVE_CONTROL.search(source_text):        # 全仓规则，正确地在前面
    errors.append(...)
...
if relative in p3_files or relative.startswith(p3_prefixes):
    continue                                            # ← 裸 continue，无具名理由
```

豁免本身**是可辩护的**（`official-design-alignment` 已把 `P3 low-code designer styling` 声明为范围外），
但豁免在**使用点**上没有声明，读者只能靠推断；一旦有人把这一行上移，全仓的原生控件规则会被一起吞掉。

### 6. 修复

**A（`generate_frontend_rendering_detail_inventory.py`）**

- 与层级无关的原生控件边界移到 `is_p3` 延迟**之前**；
- `reason` 按实际层命名：`formal P3 surface bypasses governed adapters: …` / `formal P0/P1 …`；
- 新增 `layer_of(source)`，`formalProductLayer` 由 `"P3" if status == "p3_out_of_scope" else "P0"`
  改为 `"P3" if is_p3(source) else "P0"` —— P3 面即使在 `gap` 状态下也**不会**被错标成 P0；
- `completionPolicy` 新增 `nativeControlScope = "every formal-product surface (P0-P4) except the design-system adapter layer"`；
- 新增 `p3OwnershipDeferred`：把"延后"变成显式、被计数的登记块
  （`deferred/register/reason/surfaceCount/surfaces`，当前 `surfaceCount=19`）。

**B（`frontend_primitive_adapter_guard.py`）**

- 新增具名常量 `P3_CONSUMER_CHROME_EXEMPTION`（写明基准与理由）与函数
  `consumer_chrome_exempt(relative, p3_files, p3_prefixes)`；使用点改为调用该函数，
  并在常量注释中固定"原生控件/对话框语义规则必须先于该豁免运行"。

**不动的东西**：`DELIBERATE_NATIVE_COMPOSITES` 的优先级、`STATE_PATTERNS`、
`STATUS_VALUES` 词表、前端任何 `.vue` / `.ts`、业务矩阵、`.agent`。

### 7. 负例（先证明会红，再声称修复）

| 负例 | 变异 | 期望 | 实测 |
|---|---|---|---|
| `test_p3_surface_cannot_bypass_the_repo_wide_native_control_boundary` | 把 `is_p3` 延迟**移回**原生控件检查之前 | 必须红 | 变异后 `classify(P3, '<button>')` 返回 `p3_out_of_scope` → **断言失败，盲区复现** |
| `test_p3_administration_consumer_chrome_is_a_declared_exemption` | 让 `consumer_chrome_exempt` 恒返回 `None`（撤销豁免） | 必须红 | 报出 `consumer primitive visual chrome must move to an adapter appearance: …LegacyPanel.vue` → **断言失败** |
| `test_p3_administration_surface_cannot_bypass_native_control_boundary` | 把 P3 豁免上移到原生控件检查之前 | 必须红 | 变异后 P3 面的 `<input>` 不再报错 → **盲区复现** |

新增不变量断言（正向锁）：`p3OwnershipDeferred.surfaceCount == len(p3_out_of_scope 面)`、
`nativeControlScope` 同时含 `P0-P4` 与 `design-system adapter layer`、`layer_of` 分层正确。

### 8. 验证（分层结果）

改动只落在 `scripts/audit`、`scripts/verify` 与 `docs/` 派生清单，**未触及 `frontend/` 源码**，
因此 L4 浏览器层与 `verify.frontend.typecheck.strict` 不因本段失效，不重跑（沿用段 28 同一候选）。

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS `coverage=L1_only next=risk_selected_non_zero_L2_targets_required` |
| L1 | `make verify.guard.registry` | PASS `AUDIT PASS: 1352 scripts` |
| L1 | `make ci.generated_reports.guard` | PASS（含 `tracked generated reports are current`） |
| L2 | `make verify.frontend.rendering_detail_state.unit` | **PASS 64 tests**（原 59，+5）；`rendering_detail_inventory PASS surfaces=172 gaps=0`、`visual_projection PASS`、`official_design_alignment PASS internalVendorSelectorGapCount=0`、`rendering_detail_state_guard PASS surfaces=97` |
| L2 | `make verify.frontend.primitive_adapter.unit` | **PASS 33 tests**（原 31，+2）；`components=46 eventCases=11`、`frontend_primitive_adapter_guard PASS components=46` |
| L2 | `make verify.frontend.component_driver_takeover.unit` | PASS 13 tests；`required=33 missing=0 raw=0`（同类规则未回退） |

派生清单刷新：`make refresh.frontend.rendering_detail.inventory` 后仅
`component-professionalization-inventory-v1.json` 变化（49+/21−：`sourceIdentity`/`generatorDigest`、
19 条 P3 `reason`、`completionPolicy.nativeControlScope`、新键 `p3OwnershipDeferred`）；
`visual-projection-inventory-v1.json` 与 `official-design-alignment-inventory-v1.json` **逐字节不变**，
证明改动未外溢到相邻清单。

### 9. 显式登记（不在本段范围）

- **P3 状态原语所有权欠账（非阻断，独立台账）**：`p3OwnershipDeferred.surfaceCount = 19`
  （P3 共 20 个 `.vue`，1 个无相关词汇不入清单）；其中 **17 个有状态词汇但无
  `ScLoading`/`ScEmptyState`/`ScErrorState` 原语**。这是真实的 P3 欠账，需单独的 P3 所有权批次建立声明；
  **不通过删掉 `is_p3` 让 19 个 `gap` 一次性冒出并阻断 P0/P1 收口**。
- `scale` 延后口径：P3 面判定为 `p3_out_of_scope` 时 `reason` 指向 `p3OwnershipDeferred`，
  未来 P3 批次应把该块改为 `deferred: false` 并补齐所有权声明。
- 承接段 28 全部登记项（含 `/admin/*` 无 platform-admin 夹具的页面级证据缺口、
  `MenuTree.vue`/`CanonicalNavigationMenuNode.vue` 名称豁免移除后需同等理由才能恢复），本段未触碰。

### 10. 提交

- `fix(guard): evaluate the layer-independent native control boundary before the P3 deferral`
- `chore(web): refresh the derived inventory for the layer-independent native control policy`
- 本段记录（文档）

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

---

## 段 30｜求值集合 ≠ 渲染面：外置模板与状态原语词表（2026-09-30）

段 29 的复查结论是"P3 只残留所有权欠账，无第二处同类盲区"。本段在同一批生成器/守卫上继续追问
"求值集合是否等于被声明的面"，又发现两处，其中一处会浮现**真实的 P0 所有权缺口**。

### 1. 边界七问

| 项 | 结论 |
|---|---|
| **Formal Product Layer** | P0（`smart_core` 共享守卫的求值集合与所有权登记）＋ P4（`scripts/audit`、`scripts/verify`） |
| **Layer Target** | `scripts/audit/generate_frontend_rendering_detail_inventory.py`、`scripts/verify/frontend_primitive_adapter_guard.py`、`docs/frontend_productization/rendering-detail/rendering-surface-ownership-v1.json` |
| **Module** | `smart_core`（守卫与所有权归属）；未改 `frontend/apps/web` 任何源码 |
| **Standard vs User-Specific** | 平台标准：**"被求值的源必须等于该组件真实渲染面"**、**"状态原语词表必须与治理该原语的守卫一致"** —— 与行业/客户语义无关 |
| **Why Here** | 只有守卫/清单能同时看到"声明的源集合"与"实际扫描的文件集合"；只有所有权登记能表达"这个面由谁负责" |
| **Why Not Elsewhere** | 不放页面：页面不能自证被扫描到；不改后端；不放宽门禁阈值；不改业务矩阵 |
| **Blast Radius** | 新增 2 个外置模板进入 `input_digest`；状态原语词表 +`ScInlineState`；`ObjectTaskPage.vue` 进入既有 P0 完成批次与所有权登记。菜单/模型/契约/请求载荷零变化；`frontend/` 源码零变化 |

### 2. 同类根因的第三次显形

段 28 修的是"发布规则但不求值"，段 29 修的是"层级延迟吞掉层级无关边界"。本段发现第三种形式：

> **求值集合被"文件边界"和"词汇表"两处静默裁剪，而对外声明的面（组件 / 状态原语）并没有变小。**

### 3. 缺口 A：外置 `<template src>` 不在求值集合

仓库有 2 个正式产品组件把模板放在外部文件：

```
frontend/apps/web/src/views/MenuConfigView.vue            -> views/menuConfig/template.html (27,674 B)
frontend/apps/web/src/views/BusinessConfigSurfaceView.vue -> views/businessConfigSurface/template.html (16,996 B)
```

而两处扫描都只看 `.vue` 本身：

- `frontend_primitive_adapter_guard.py`：`frontend_root.rglob("*.vue"/"*.ts"/"*.js"/"*.mjs")` —— `.html` 模板**不在扫描集合内**；
- `generate_frontend_rendering_detail_inventory.py`：`text = path.read_text()` —— 只读 `.vue`，外置模板内容**不参与任何判定**。

后果是**双向**的：

1. **漏报**：外置模板里的原生 `<button>`／`<input>` 完全不被 `RAW_INTERACTIVE_CONTROL` 看见；
   而该模板正是这些组件真正的渲染面。这是一个可以长期潜伏的守卫空洞。
2. **误判**：`MenuConfigView` 的状态呈现全靠外置模板里的 `<ScInlineState>`（4 处），
   但清单只看到 `.vue`，于是把它的 `governedStatePrimitives` 记为"空"。

今日两处外置模板恰好没有原生控件（实测 `<button|<input|<select|<textarea>` 命中 **0**），
所以这是**结构性空洞**而非既发缺陷——但"今天没踩到"不能作为保留空洞的理由。

### 4. 缺口 B：状态原语词表漏 `ScInlineState`，浮现真实 P0 所有权缺口

清单的 `GOVERNED_STATE_PRIMITIVES = (ScLoading, ScEmptyState, ScErrorState)`，
但仓库**另有** `frontend_inline_state_guard` 明确治理 3 个原语：
`ScInlineState` / `ScEmptyState` / `ScErrorState`（该守卫逐项断言其 TDesign 驱动、语义身份与无障碍属性）。

**清单的词表与治理该原语的守卫不一致**：`ScInlineState` 明明受治理，却不被清单识别为"状态原语已接管"。
由于清单的纳入条件之一是 `governed_primitives` 非空，只用 `ScInlineState` 呈现状态的面
会**整体从清单里消失**——不是判为缺口，而是**根本不出现**。

补齐词表后立即浮现 **1 个真实的 P0 所有权缺口**：

```
frontend/apps/web/src/pages/contractForm/ObjectTaskPage.vue
  status=gap  reason=relevant state or native interaction has no explicit professionalization ownership declaration
```

该组件是 `ContractFormDriverHost` 渲染的"当前任务"页（`ObjectTaskPage`，含 1 处 `ScInlineState`、
多个 `ScCard`），并且**已被另外 5 个守卫治理**：

- `frontend_professional_audit_guard.py`
- `frontend_form_canvas_wide_grid_guard.py`
- `frontend_page_pattern_reference_parity_guard.py`
- `frontend_product_page_pattern_guard.py`
- `frontend_scene_component_bridge_guard.py`

也就是说：它并不缺专业实现，**缺的是在本清单的所有权登记**——长期不可见，因为词表根本没把它纳入。
这正是"静默缺口"最危险的一种形态：不是判错，而是**看不到**。

**没有通过放宽阈值或删除词表来消除它**：按既有机制把它登记进 `p0-inline-full-state-completion-v1`
批次，并给出机器可校验的绑定（`ScInlineState` + `state="info"` + `density="compact"` ≥1），
同时在 `rendering-surface-ownership-v1.json` 声明该源归属同一 P0 所有者。

### 5. 修复

**A（外置模板进入求值集合）**

- 新增 `EXTERNAL_TEMPLATE_SRC` 与 `external_template_paths()` / `resolve_source_text()`
  （清单）、`external_template_text()` / `component_source_text()`（守卫）；
- 解析失败**失败关闭**（`ValueError` / `FileNotFoundError`），不允许"文件找不到就只判 `.vue`"；
- 清单把外置模板并入 `input_digest`，`scope` 明确写为
  `… including external <template src> files`，并在 `p3OwnershipDeferred.externalTemplateCount` 计数。

**B（词表对齐 + 登记真实缺口）**

- `GOVERNED_STATE_PRIMITIVES` 增加 `ScInlineState`，并注明与 `frontend_inline_state_guard` 对齐；
- `BATCH_BINDINGS["p0-inline-full-state-completion-v1"]` 增加
  `ObjectTaskPage.vue: {"scinlinestate": {"states": {"info"}, "attrs": {"density": "compact"}, "minimum": 1}}`；
- `rendering-surface-ownership-v1.json` 的同一 P0 所有者 `sources` 增加 `ObjectTaskPage.vue`
  （`ownership_binding_failures()` 要求批次的每个绑定源都有正式所有者，缺失即失败关闭）。

### 6. 负例（先证明会红）

| 负例 | 变异 | 实测 |
|---|---|---|
| `test_external_component_template_cannot_hide_a_native_control` | 让 `component_source_text` 退化为纯读 `.vue` | 外置模板里的 `<button>` 逃过守卫 → **断言失败** |
| `test_external_template_joins_the_evaluated_source` | 取消 `resolve_source_text` 的模板拼接 | 组合文本不再含 `<ScInlineState` → **断言失败** |
| `test_object_task_page_binding_fails_closed_when_state_changes` | 把 `state="info"` 改成 `state="empty"` | 绑定失配 → `classify()` 返回 `gap` → **断言失败** |
| （登记前实测） | 只补词表、不登记所有权 | `gap=1`、`nextBatch` 非空 → 缺口确实显现，未被吞掉 |

### 7. 验证（分层结果）

改动只落在 `scripts/`（audit/verify）与 `docs/` 派生清单，**`frontend/` 源码零变化**，
因此 L4 浏览器层与 `verify.frontend.typecheck.strict` 不因本段失效，不重跑（沿用同一 5180 候选）。

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS `coverage=L1_only` |
| L1 | `make verify.guard.registry` | PASS `1352 scripts` |
| L1 | `make ci.generated_reports.guard` | PASS |
| L2 | `make verify.frontend.rendering_detail_state.unit` | **PASS 70 tests**（段 29 后 64，+6）；`rendering_detail_inventory PASS surfaces=173 gaps=0`、`rendering_detail_state_guard PASS surfaces=98`、`visual_projection PASS`、`official_design_alignment PASS internalVendorSelectorGapCount=0` |
| L2 | `make verify.frontend.primitive_adapter.unit` | **PASS 34 tests**（+1）；`components=46 eventCases=11` |

### 8. 对段 29 数字的更正（附录义，不回改历史记录）

- `p3OwnershipDeferred.surfaceCount`：**19**（不变）；
- "有状态词汇但无状态原语"的 P3 面：段 29 记为 **17**，本段词表对齐后实际为 **16**
  （`MenuConfigView`、`BusinessConfigSurfaceView` 已确证使用受治理状态原语）；
- 清单总面数：172 → **173**（`ObjectTaskPage.vue` 由不可见变为可见并有归属）；
- `governed_composite`：112 → **113**。

### 9. 显式登记（不在本段范围）

- **未解析外置模板的相邻扫描**：`generate_frontend_visual_projection_inventory.py` 的
  `consumer_primitive_visual_chrome` / `direct_root_visual_overrides` 仍只读 `.vue`。
  这两个规则面向组件自身的 `<style>` 块与容器 class，外置模板不含样式块；
  且它已把 P3 排除在外（段 29 已定性为"声明的就是 P0/P1"）。
  记录为**已知不等价**：若将来把外置模板用于非 P3 组件且在该模板内挂容器 class，需一并解析。
- 承接段 28/29 全部登记项，本段未触碰。

### 10. 提交

- `fix(guard): evaluate external component templates and align the governed state vocabulary`
- `chore(web): refresh the derived inventory for the external-template and vocabulary alignment`
- 本段记录（文档）

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## 段 31｜P3 状态带所有权：把手写状态标记换回受治理原语，并让转换可被机器复核（2026-09-30）

### 1. 本段目标与边界

P3（低代码设计器／管理台）状态的**所有权延迟**在段 29/30 已显式化，但一直只是"欠账计数"：
登记表说这些面"有状态词汇、没有专业化所有权声明"，却没有任何东西记录**哪一面已经真的把状态带交给了设计系统**。
本段做两件事：

1. 把 P3 面上**语义最容易出错、风险最低**的手写状态标记，真正换成受治理状态原语；
2. 给这批转换加一份**失败关闭**的登记（`p3OwnershipDeferred.stateBandOwned`），
   让"已转成受治理原语"这件事可被机器验证，且删除原语／改掉字面状态就会立刻回退为延迟。

**不做**：不放开 P3 的 `p3_out_of_scope` 不变量（`test_p3_surfaces_do_not_masquerade_as_p0_completion`
仍要求 P3 面保持延迟状态），不重构低代码设计器，不动后端契约，不动其他守卫欠账。

### 2. 产品渲染收口（4 面 / 5 处）

| 文件 | 原来（手写） | 现在（受治理原语） | 判定依据 |
|---|---|---|---|
| `views/businessConfigSurface/BusinessConfigVersionPanel.vue` | `<div class="empty-state">{{ emptyText }}</div>` | `<ScEmptyState :title="emptyText" … />` | 真正的空结果带 |
| `views/businessConfigSurface/BusinessConfigStartPanel.vue` | `<div class="workbench-status-empty">状态读取中</div>` | `<ScInlineState state="loading" label="状态读取中" />` | **类名说"空"、文案说"读取中"**，语义错位；同一组件的 `deliveryReadinessStatusText` 也把该条件判为"读取中"，故按 loading 呈现是行为保持 |
| `views/businessConfigSurface/BusinessConfigCoverageWorkspace.vue` | 同上 | 同上 | 同上 |
| `views/ReleaseOperatorView.vue` | 两处 `<p class="release-operator__empty">{{ … }}</p>` | 两处 `<ScEmptyState :title="…" … />` | 真正的空结果带 |

配套清理（避免死样式）：
`style.css` 的 `.empty-state` 改为 `.version-panel-empty`（保留原纵向节奏），删除已无消费者的 `.workbench-status-empty`。

### 3. 失败关闭的转换登记

`generate_frontend_rendering_detail_inventory.py` 新增：

- `P3_STATE_BAND_OWNERSHIP`：`source -> ("Primitive:state", …)`，只登记**实际渲染**的原语/状态对；
- `rendered_state_bands(text)`：从**解析后的源**（含外置模板）取
  `ScLoading:loading` / `ScEmptyState:empty` / `ScErrorState:error` 与 `<ScInlineState state="…">` 的字面状态；
- `p3_state_band_ownership_failures(deferred_sources)`：四条失败关闭检查——
  声明源必须是 P3 面、必须仍在延迟登记表内、文件必须存在、**每一条声明必须真的被渲染**；
- `build_inventory()` 在求值完 `surfaces` 后调用该检查，**失败即 `ValueError` 抛出**（不是打印告警）。

报告新增 `p3OwnershipDeferred.stateBandOwned` / `stateBandOwnedCount` / `stateBandOwnershipRule`。
`p3OwnershipDeferred.surfaces`（source 列表）保持不变，既有断言与外部消费不受影响。

当前登记：

```
stateBandOwnedCount = 4
ReleaseOperatorView.vue                -> ScEmptyState:empty
BusinessConfigCoverageWorkspace.vue    -> ScEmptyState:empty, ScInlineState:loading
BusinessConfigStartPanel.vue           -> ScInlineState:loading
BusinessConfigVersionPanel.vue         -> ScEmptyState:empty
```

`p3OwnershipDeferred.surfaceCount` 仍为 **19**（不变量未放开），其中 **4** 面已进入"状态带已受治"登记，
剩余 **15** 面仍为纯延迟。

### 4. 负例（先证明会红，再证明会绿）

| 负例 | 变异 | 实测 |
|---|---|---|
| `test_p3_state_band_ownership_fails_closed_when_a_claim_stops_rendering` | 把 `BusinessConfigVersionPanel` 的 `<ScEmptyState` 换成裸 `<div>` | 断言失败（`ScEmptyState:empty` 未被渲染） |
| （端到端实测） | 给 `BusinessConfigVersionPanel` 追加一条 `ScInlineState:loading` 声明 | `build_inventory()` 抛 `ValueError: … declared P3 state band is not rendered …` |
| `test_p3_state_band_ownership_rejects_a_non_p3_declaration` | 把未渲染的 `SceneHealthView.vue` 登记进来 | 断言失败 |
| `test_p3_state_band_ownership_claims_are_rendered` | 登记表与报告字段／延迟登记表一致性 | 通过 |

### 5. 验证（分层结果）

**声明**：改动路径 = `frontend/apps/web/src/views/**`（4 个 Vue + 1 个 CSS）+ `scripts/audit/**`（生成器与单测）+ `docs/**` 派生清单。
影响层：L1 静态/生成物、L2 前端定向单测；风险类：呈现与守卫登记（非持久化、非授权）。
最早必需层 L2；跳过项及理由见下。

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS `coverage=L1_only` |
| L1 | `make verify.guard.registry` | PASS `1352 scripts` |
| L1 | `make ci.generated_reports.guard` | PASS（其中 `complexity_budget_report` 因本段文件尺寸变化先过期，已按提示重新生成） |
| L1 | `python3 scripts/verify/docs_inventory.py` + `make verify.docs.links` | PASS |
| L2 | `make verify.frontend.rendering_detail_state.unit` | **PASS 73 tests**（段 30 后 70，+3）；`rendering_detail_inventory PASS surfaces=173 gaps=0`、`rendering_detail_state_guard PASS surfaces=98`、`visual_projection PASS`、`official_design_alignment PASS internalVendorSelectorGapCount=0` |
| L2 | `scripts/audit/test_generate_frontend_rendering_detail_inventory` | **PASS 37 tests** |
| L2 | `make verify.frontend.primitive_adapter.unit` | PASS 34 tests；`components=46 eventCases=11` |
| L2 | `make verify.frontend.component_driver_takeover.unit` | PASS 13 tests；`required=33 missing=0 raw=0`（清单已刷新：alert 54→56、empty 24→27、loading 50→52） |
| L2 | `make verify.business_config.guard_inventory` / `.product_guard` / `.publish_boundary_guard` | PASS（`design_system_usages=130`、`raw_controls=0`） |
| L2 | `verify.frontend.official_icon.unit` / `.global_component_capability.unit` / `.low_code_field_create_dialog.unit` / `.page_pattern_reference_parity.unit` / `.product_page_pattern.unit` | PASS |
| L2 | `make verify.frontend.typecheck.strict` | PASS |
| L4 | 5180 新候选双视口定向观察 | 见第 6 节 |

**跳过项与理由**：不重跑 89 入口、全站发布验收、后端模块升级与夹具重置——本段未改后端模型、权限或数据契约。

### 6. 候选、运行身份与浏览器观察

- 旧产物保留：`config05-20260929` → `config05-20260929-prev-640a97eb7`（base_sha `640a97eb7…`，未覆盖）。
- 新候选（最终冻结）：`config05-20260929/dist`，`base_sha=013770d18…`（本段 4 笔提交后的干净 HEAD），
  `dirty_scope=""`，`entry=/assets/index-C53ItXQV.js`。
  过程序：先在 `e01137026` + dirty 树上构建一次用于观察，提交后在干净 HEAD 上重建；
  两次构建的入口与 `entry_sha256` **逐字节一致**（`d8faca02…`），因此前面的观察证据对冻结候选同样成立。
  另保留 dirty 构建为 `config05-20260929-prev-e01137026`（未覆盖）。
- 5180 监听进程在操作前后均为 `pid=802966`（`scripts/release/release_static_server.mjs`，
  `STATIC_ROOT=…/config05-20260929/dist`，`STATIC_PORT=5180`，`API_PROXY_TARGET=http://127.0.0.1:18082`）；
  静态服务按请求读盘且 `index.html` 为 `no-cache`，同路径替换产物即对新内容生效，**未新增常驻端口**。
- 身份自校验：`SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY=operation_entry_v1 DB_NAME=sc_frontend_acceptance COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01 python3 scripts/dev/frontend_standard_preview.py identity` → PASS。
- 实际服务入口：`/assets/index-C53ItXQV.js`，已用 HTTP 回读核对与 `build-identity.json` 一致，
  且回读字节的 sha256 等于 `entry_sha256`。

定向浏览器观察（受管角色 `fixture_role_config_admin`，`sc_frontend_acceptance`，全程零写入；
下表为**对冻结候选复采**的结果，两个视口均为 `scan-row=60`）：

| 检查 | 1440×900 | 390×844 |
|---|---|---|
| `/admin/business-config` 可达 | 是（`scan-row=60`） | 是 |
| 手写状态标记 `.workbench-status-empty` | **0** | **0** |
| 遗留 `.empty-state` | **0** | **0** |
| 受治理 `[data-semantic-component="ScEmptyState"]` | **1** | **1** |
| 页面级横向溢出 `scrollWidth/clientWidth` | 1440/1440 | 390/390 |
| console error | 0 | 0 |

`/admin/release-operator` 为 `adminOnly`，受管环境**无 platform-admin 夹具** → 记录为
`not_run`（不放宽 `adminOnly`、不换管理员证明业务可用）。该面的源码级证据来自失败关闭登记。

**未覆盖（如实记录，不当作通过）**：版本记录面板的"空结果带"未在浏览器里被驱动出来
（本次运行中三列工作台的版本触发入口未激活），因此
`release-operator` 与版本面板空态目前只有**源码级失败关闭登记**，没有页面级截图证明。

**环境差异（非本段引入）**：带 `model=construction.contract&action_id=1002` 的工作台入口在
`sc_frontend_acceptance` 返回"动作 1002 不存在"——该样本属于 demo 库，本段改用无动作参数入口，
未修改任何业务数据。

### 7. 对段 30 数字的补充（附录义，不回改历史记录）

- `p3OwnershipDeferred.surfaceCount`：**19**（不变）；
- 其中 `stateBandOwnedCount`：**4**；剩余纯延迟：**15**；
- `governed_composite`：**113**（不变，P3 面未跨状态）；
- 清单总面数：**173**（不变）；
- `component-driver-takeover` 消费者计数：alert 54→**56**、empty 24→**27**、loading 50→**52**。

### 8. 显式登记（不在本段范围）

- `views/businessConfigSurface/template.html` 仍有 2 处手写状态带
  （`<div class="status error">`、`<section class="loading-state">`）。
  转换需要在 `BusinessConfigSurfaceView.vue` 增加一行 import，而该文件**正好卡在
  `low_code_workbench_product_guard` 的 600 行路由装配上限**（当前 600 行）。
  **有意保留**：先拆装配职责再转换，不在本段用"删一行凑数"的方式绕过上限。
- `BusinessConfigApprovalPanel.vue` 的 `approval-step-empty` 是带内联动作的虚线框布局，
  换原语会改变对齐方式，登记为后续面。
- `MenuConfigView` 的 `menu-selected-panel--empty` 是"未选菜单"引导面板（含标题与说明），
  不是瞬时状态带，登记为布局面而非状态带。
- 承接段 28–30 全部登记项：`generate_frontend_visual_projection_inventory.py` 的
  `consumer_primitive_visual_chrome` / `direct_root_visual_overrides` 仍只读 `.vue`（已知不等价）；
  `/admin/scene-health`、`/admin/scene-packages` 无 platform-admin 夹具；
  `style_system.guard` 四项文件长度欠账；`state_transition_undeclared` 五条等。
  本段未触碰，未新增越界。

### 9. 提交

- `refactor(web): render P3 administration state bands through governed primitives`
- `fix(guard): fail closed on P3 state-band ownership claims`
- 派生清单与段记录

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## 段 32｜设计器与专用树的状态带收口：把剩余 P3 手写状态标记换回受治理原语，并扩表失败关闭（2026-09-30）

### 1. 本段目标与边界

段 31 把 P3 面上"语义最容易出错、风险最低"的 4 面状态带换成了受治理原语，并在
`p3OwnershipDeferred.stateBandOwned` 建立失败关闭登记；但在段 31 §8 显式登记里，
设计器、专用菜单树、审批面板三面被登记为"后续面"，工作台壳的两处状态带被
`low_code_workbench_product_guard` 的 **600 行路由装配上限**挡住。

本段承接这批登记，只做三件事：

1. 把这三面 + 工作台壳（含外置模板）的**手写状态带**真正换成受治理状态原语；
2. 把这 4 个新来源加进**失败关闭**登记（`P3_STATE_BAND_OWNERSHIP` 4 → 8），
   让"已转成受治理原语"这件事继续可被机器验证——删原语、改字面状态立刻回退为延迟；
3. 维护因退役类名而失配的探针（`configuration_center_batch_journey.mjs`），
   **保留等待意图，不降断言**。

**不做**：不放开 P3 的 `p3_out_of_scope` 不变量（`test_p3_surfaces_do_not_masquerade_as_p0_completion`
仍要求 P3 面保持延迟状态）；不重构设计器；不动后端契约；**不拆**
`BusinessConfigSurfaceView.vue` 的装配职责（见 §9）；不动四项 `style_system` 欠账。

### 2. 边界七问

| 项 | 结论 |
|---|---|
| `Formal Product Layer` | P3 —— 低代码配置产品（设计器／管理台呈现面） |
| `Layer Target` | 前端渲染层：`frontend/apps/web/src`（设计系统原语消费），非平台机制、非行业默认 |
| `Module` | `frontend/apps/web`（Vue 呈现）+ `scripts/audit`（失败关闭登记与单测） |
| `Standard vs User-Specific` | 平台机制级：状态**呈现**统一走受治理原语；与业务默认、客户偏好、管理员配置无关 |
| `Why Here` | 状态带是**呈现**，归端侧设计系统；P3 面仍是 P3，本段只换承载原语，不改低代码语义与权限 |
| `Why Not Elsewhere` | 不落后端契约（契约不表达外观）；不落 `smart_core`/`smart_construction_core`（非业务语义）；不落模板派生配置（非客户偏好） |
| `Blast Radius` | 仅 `businessConfigSurface`、`menuConfig`、`contractForm` 设计器面与管理台壳的**瞬时状态带 DOM**；不动查询域、记录身份、授权、动作绑定。验证：既有 L1/L2 定向单测 + 失败关闭登记 + 一次浏览器观察 |

### 3. 产品渲染收口（5 面 / 8 处）

| 文件 | 原来（手写） | 现在（受治理原语） | 判定依据 |
|---|---|---|---|
| `pages/contractForm/CurrentFormFieldSettingsPanel.vue` | `<p class="contract-form-field-search-empty">没有匹配字段</p>` | `<ScEmptyState density="compact" :heading-level="5" title="没有匹配字段" />` | 真正的空结果带 |
| 同上 | `<div class="contract-field-selection-empty">…`（含标题与说明） | `<ScEmptyState class="contract-field-selection-empty" density="compact" :heading-level="5" … />` | 空态引导，按 empty 语义；保留类名作外层框架 |
| 同上 | `<p class="contract-form-operation-log-empty">暂无操作记录</p>` | `<ScEmptyState density="compact" :heading-level="6" title="暂无操作记录" />` | 真正的空结果带 |
| `views/MenuConfigView.vue` + `views/menuConfig/template.html` | `<section class="menu-selected-panel menu-primary-panel menu-selected-panel--empty">…<h2>全部菜单</h2><p>…</p></section>` | `<ScEmptyState class="menu-empty-panel menu-primary-panel" :heading-level="2" title="全部菜单" … />` | "未选菜单"引导面板，empty 语义 |
| `views/businessConfigSurface/BusinessConfigApprovalPanel.vue` | `<div class="approval-step-empty">…<ScButton>…</div>` | `<ScEmptyState class="approval-step-empty" density="compact" :heading-level="4" …><template #actions><ScButton … /></template></ScEmptyState>` | 空结果带 + 带内联主操作；动作经 `#actions` 槽保持同一业务意图 |
| `views/BusinessConfigSurfaceView.vue` + `views/businessConfigSurface/template.html` | `<div v-else-if="error" class="status error">{{ error }}</div>` | `<ScInlineState v-else-if="error" state="error" :label="error" />` | 瞬时错误带 |
| 同上 | `<div v-else-if="message.text" class="status ok">…</div>` | `<ScInlineState v-else-if="message.text" state="success">…</ScInlineState>` | 瞬时成功带 |
| 同上 | `<section v-if="loading" class="loading-state">正在读取配置能力...</section>` | `<ScInlineState v-if="loading" state="loading" label="正在读取配置能力..." />` | 瞬时加载带 |

配套清理（避免死样式）：
- `CurrentFormFieldSettingsPanel.css`：删孤儿 `.contract-form-field-search-empty`、`.contract-form-operation-log-empty`；
  把 `.contract-field-selection-empty` 从与 `.contract-field-selection-card` 的群组选择器拆出，独立保留边框/内边距/背景。
- `menuConfig/table.css`：删 `.menu-selected-panel--empty` 及其 h2/p 规则；`.menu-empty-panel` 进面板边框群组 + `padding: 14px` 框架规则（注释说明只接管框架）。
- `businessConfigSurface/style.css`：删孤儿 `.status.ok`、`.status small`、`.loading-state`；`.status`/`.loading-state` 从 margin 群组移除。
- `BusinessConfigSurfaceView.vue`：新增一行 `import ScInlineState`，同时删除经核实**确属未用**的 `type BusinessConfigRemediationAction`
  （唯一被削的阴影导入，**不是"删行凑数"**——该类型在文件内无任何引用；文件仍**恰好 600 行**）。

### 4. 失败关闭的转换登记扩展

`scripts/audit/generate_frontend_rendering_detail_inventory.py` 的 `P3_STATE_BAND_OWNERSHIP` 由 4 项扩到 **8 项**：

```
CurrentFormFieldSettingsPanel.vue            -> ScEmptyState:empty
MenuConfigView.vue                           -> ScEmptyState:empty
BusinessConfigApprovalPanel.vue              -> ScEmptyState:empty
BusinessConfigSurfaceView.vue                -> ScErrorState:error, ScInlineState:error,
                                                ScInlineState:loading, ScInlineState:success
```

检查逻辑沿用段 31：声明源必须是 P3 面、必须仍在延迟登记表内、文件必须存在、
**每一条声明必须真的被渲染**（从解析后的源含外置模板取字面状态），
`build_inventory()` 失败即 `ValueError` 抛出（不是打印告警）。

### 5. 负例（先证明会红）

| 负例 | 变异 | 实测 |
|---|---|---|
| `test_p3_designer_and_tree_bands_are_owned_by_governed_primitives` | 显式断言退役类名（`.contract-field-selection-empty`、`menu-selected-panel--empty`、`.approval-step-empty` 的旧 div、`.status ok`、`.loading-state`）**不再渲染**，且对应原语已在位 | 通过 |
| `test_p3_state_band_ownership_fails_closed_on_a_dropped_designer_band` | 把设计器某一 `<ScEmptyState` 换成裸 `<div>` | 断言失败（声明未被渲染 → 登记回退为延迟） |
| `test_p3_state_band_ownership_fails_closed_on_a_changed_inline_state` | 改工作台壳 `<ScInlineState state="…">` 的字面状态 | 断言失败 |

单测模块：`python3 -m unittest scripts.audit.test_generate_frontend_rendering_detail_inventory` → **40 tests OK**（段 31 为 37）。

### 6. 验证（分层结果）

**声明**：改动路径 = `frontend/apps/web/src/**`（5 个 Vue/HTML + 3 个 CSS + 1 个探针），
`scripts/audit/**`（生成器与单测），`docs/**` 派生清单。
影响层：L1 静态/生成物、L2 前端定向单测；风险类：呈现与守卫登记（非持久化、非授权、非契约）。
最早必需层 L2；L3/L4 跳过项及理由见 §7。

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS `change_state=clean coverage=L1_only receipt=none` |
| L1 | `make verify.guard.registry` | PASS `1352 scripts` |
| L1 | `make ci.generated_reports.guard` | PASS（`complexity_budget_report` 随本段 `MenuConfigView.vue` 行为刷新，已在校验前重生成） |
| L1 | `python3 -m unittest scripts.audit.test_generate_frontend_rendering_detail_inventory` | PASS `40 tests OK` |
| L2 | `make verify.frontend.rendering_detail_state.unit` | PASS `76 tests OK`；`rendering_detail_inventory PASS surfaces=173 gaps=0` |
| L2 | `make verify.frontend.component_driver_takeover.unit` | PASS `13 tests OK`；`required=33 missing=0` |
| L2 | `make verify.frontend.typecheck.strict` | PASS（先修过 `heading-level="5"` 类型错误 → `:heading-level="5"`） |
| L2 | `make verify.business_config.guard_inventory / .product_guard / .publish_boundary_guard` | 全 PASS |
| L2 | `make verify.frontend.primitive_adapter.unit / navigation_shell.unit / form_designer_actions.unit / low_code_field_create_dialog.unit / page_pattern_reference_parity.unit` | 34 / 19 / cases=6 / 6 / 15 全 PASS |
| L2 | `bash scripts/verify/menu_config_tree_editor_behavior_guard.sh` | PASS |

**L3 跳过**：未改后端模型、权限、数据契约 → 不做模块升级与夹具重置。
**L4**：一次定向浏览器观察（见 §7），非完整发布门禁。

### 7. 候选、运行身份与浏览器观察

- 旧产物保留：`config05-20260929` → `config05-20260929-prev-6cd68a909`（base_sha `013770d18…`，**未覆盖**）。
- 新候选：`config05-20260929/dist`，`base_sha=3da37f767…`（本段 3 笔提交后的干净 HEAD），
  `dirty_scope=""`，`entry=/assets/index-XdKv-Cj_.js`，
  `entry_sha256=425f40ee523e8c52d3dad3056ad5087a86091ca1b5b1fc048fd7fc5a2a45e03c`，
  `index_sha256=d421f8da30e382985336f3ba1f334769280cce3d4d8fba81b7e6392237cf9970`。
  构建命令：`SC_ACCEPTANCE_RUNTIME_PROFILE=local DB_NAME=sc_frontend_acceptance COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01 make frontend.standard.preview.build`
  （构建前须先移走旧目录，否则 `REUSED unchanged build`）。
- 5180 监听进程在操作前后均**未变**：`pid=802966`，`node scripts/release/release_static_server.mjs`，
  `STATIC_ROOT=…/config05-20260929/dist`，`STATIC_PORT=5180`，`API_PROXY_TARGET=http://127.0.0.1:18082`。
  静态服务按请求读盘 → 同路径替换产物即对新内容生效，**未新增常驻端口**。
- 身份自校验：HTTP 回读 `index.html` 与入口 JS，`index_sha256` / `entry_sha256` 与 `build-identity.json` **逐字节一致**。
- 受管后端容器 `sc-backend-odoo-acceptance`（healthy，`127.0.0.1:18082→8069`，db `sc_frontend_acceptance`），
  受管角色 `fixture_role_config_admin`，凭据仅取 `SC_ACCEPTANCE_FIXTURE_PASSWORD`。**全程零写入**。
- 证据目录：`sce-offrepo/artifacts/seg32-p3-designer-tree/`（`observation.json`、`designer-probe2.json`、
  `approval-probe2.json`、`approval-mobile.json` 及截图）。

定向浏览器观察（两个视口，受管角色，全程零写入）：

| 检查 | `/admin/business-config` 1440×900 | 同 390×844 | `/admin/menu-config` 1440×900 | 同 390×844 |
|---|---|---|---|---|
| 可达（`scan-row`） | 是（60） | 是 | 是 | 是 |
| 手写状态标记 `.status.ok/.status.error/.loading-state` | 0 | 0 | 0 | 0 |
| 退役类名 `.workbench-status-empty` / `.empty-state` | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 专用树 `.menu-selected-panel--empty` → `.menu-empty-panel` | — | — | **0 → 1** | **0 → 1** |
| 受治理 `[data-semantic-component="ScEmptyState"]` | 1（"选择一个业务页面…"） | 1 | 1（"全部菜单…"） | 1 |
| `ScInlineState state="loading"` | 采集到（"正在读取配置能力..."） | 采集到 | 采集到 | 采集到 |
| 页面级横向溢出 `scrollWidth/clientWidth` | 1440/1440 | 390/390 | 1440/1440 | 390/390 |
| console error | 0 | 0 | 0 | 0 |

审批空态：由工作台"付款申请（`payment.request`，`action_id=775`）→ 配置审批规则"驱动出来，
断言 `approvalEmpty=1`、DOM `data-semantic-component="ScEmptyState"`、
文本"当前没有审批步骤 启用审批后可添加办理节点。启用并添加步骤"；1440 与 390 均无横向溢出，console error 0。

**未覆盖（如实记录，不当作通过）**：设计器面 `CurrentFormFieldSettingsPanel`（本段改造的三处之一）
在本次运行中**未被渲染**——该路由 `/f/payment.request/new?…&config_mode=business_config_lowcode`
当前由 `data-bound-form-designer[data-ready=true]` 接管（`boundDesigner=1 boundReady=1`），
因此设计器面登记为 **`not_run`**；其证据来自源码级失败关闭登记（§4/§5），
**未放宽任何条件去凑出页面级证据**。该次设计器探针另记录到一次 `404` console error（资源未找到），
本段未改动相关链路，如实登记、不作归因。

`/admin/release-operator`、`/admin/scene-health`、`/admin/scene-packages` 为 `adminOnly`，
受管环境**无 platform-admin 夹具** → 保持 `not_run`（不放宽 `adminOnly`、不换管理员证明业务可用）。

### 8. 对段 31 数字的补充（附录义，不回改历史记录）

- `p3OwnershipDeferred.surfaceCount`：**19**（不变量未放开）；
- 其中 `stateBandOwnedCount`：**4 → 8**；剩余纯延迟：**15 → 11**；
- `governed_composite`：**113**（不变）；`governed_primitive`：**41**（不变）；
- 清单总面数：**173**（不变），`gap=0`；
- `component-driver-takeover` 消费者计数：empty **27 → 31**（+4），alert **56**（不变），loading **52**（不变）。

### 9. 显式登记（不在本段范围）

- `views/BusinessConfigSurfaceView.vue` 的**路由装配 600 行上限**仍需后续按职责拆分。
  本段只删除了一个经核实确未使用的类型导入（`BusinessConfigRemediationAction`），
  **没有**用"删一行凑数"的方式绕过上限，也没有把装配职责搬进 `AppShell`。
- `views/businessConfigSurface/BusinessConfigCoverageWorkspace.vue` 的 `page-config-selection-empty`：
  已被 `ScEmptyState` 包在 `ScCard v-else` 框架内，属**布局框架**而非状态带 → 登记为后续面。
- `views/businessConfigSurface/BusinessConfigStartPanel.vue` 的 `config-status--empty` 是**徽标修饰符**（非状态带）→ 登记。
- 承接段 28–31 全部登记项：`generate_frontend_visual_projection_inventory.py` 的
  `consumer_primitive_visual_chrome` / `direct_root_visual_overrides` 仍只读 `.vue`（已知不等价）；
  `/admin/scene-health`、`/admin/scene-packages` 无 platform-admin 夹具；
  `style_system.guard` 四项文件长度欠账；`state_transition_undeclared` 五条等。
  本段未触碰，未新增越界。

### 10. 提交

- `refactor(web): render the remaining P3 designer and tree state bands through governed primitives`
- `fix(guard): extend the fail-closed P3 state-band register to the designer and tree`
- `chore(web): refresh the derived inventories for the designer and tree state bands`
- 段记录（本文件）

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## 段 33｜把工作台的路由装配从视图里拆出来：解除 600 行上限对后续收口的阻塞（2026-09-30）

### 1. 本段目标与边界

段 32 §9 显式登记了 `views/BusinessConfigSurfaceView.vue` **恰好卡在
`low_code_workbench_product_guard` 的 600 行路由装配上限**（600 行，`>600` 即失败），
并明确"先拆装配职责再转换，不用删行凑数"。本段执行这次拆分。

**只拆装配，不改行为**：URL→业务范围、`business_config` 页契约门控、真实页面运行目标
这三块内聚职责移出视图，落到该目录既有的 composable 形态里（同目录已有 15 个 `use*`）。
视图保留编排与绑定，**不新增第二个业务数据源、不改任何契约消费逻辑、不动后端**。

### 2. 边界七问

| 项 | 结论 |
|---|---|
| `Formal Product Layer` | P3 —— 低代码配置产品（管理台工作台的装配层） |
| `Layer Target` | 前端呈现层：`frontend/apps/web/src/views/businessConfigSurface`（路由装配编排） |
| `Module` | `frontend/apps/web`（Vue 呈现 + composable 拆分） |
| `Standard vs User-Specific` | 平台机制级：装配边界属于端侧实现组织，与行业默认、客户偏好、管理员配置无关 |
| `Why Here` | 该目录已经是 `business_config` 工作台的装配归属地；拆出的三块都是它的装配职责 |
| `Why Not Elsewhere` | 不落后端契约（契约不表达装配）；不落 `smart_core`（非平台机制语义）；不进 `AppShell`（路由装配不属于外壳，且外壳已有自己的上限约束） |
| `Blast Radius` | 仅 `BusinessConfigSurfaceView.vue` 与其同目录 3 个新 `.ts`；**对外暴露的 setup 绑定名全部保持不变**，因此模板、子组件 props、守卫 token 都不受影响。验证：类型检查 + 该目录全部守卫 + 派生清单复核 + 一次受管浏览器冒烟 |

### 3. 产品改动

新增（均在同目录，沿用既有 `useX(options)` 形态）：

| 新文件 | 承接的职责 |
|---|---|
| `useBusinessConfigSurfaceScopeParams.ts` | URL query → 业务范围：`numericQuery`、`entryModel`、`scopeModel/scopeActionId/scopeViewId/scopeRoleKey/selectedPageLabel`、`rootMenuXmlid`、四个 `shouldOpen*` 意图位，以及派生的 `currentModel/scopeAction/scopeView/scopeRole/currentModelIsRuntimeConfig` |
| `useBusinessConfigSurfacePageContract.ts` | `business_config` 页契约：`sectionEnabled/sectionStyle/sectionTagIs`、`pageSectionsReady`、`pageSectionContractValid`、`pageSectionsFingerprint`、`pageGlobalActions` 与 `executeGlobalPageAction` |
| `useBusinessConfigSurfaceRuntimeRoute.ts` | 真实页面运行目标：`runtimeRouteTarget`、`runtimeRouteHref`（扫描行无 runtime route 时回落到 scope action，**不会指向操作者没有选择的页面**） |

视图侧只保留解构调用与编排：`BusinessConfigSurfaceView.vue` **600 → 554 行**。

同时删掉 4 个因移出而**确实不再使用**的导入
（`usePageContract`、`executePageContractAction`、`findActionMeta`、
`BUSINESS_CONFIG_ROUTE_FLAGS`/`isBusinessConfigRuntimeModel`）。
这不是"删行凑数"：四个符号在视图内已无任何引用，`BUSINESS_CONFIG_INTENTS` 保留（仍在用）。

`executeGlobalPageAction` 现在通过 `refresh: () => loadSurface()` 取得刷新回调。
该闭包在 setup 期只被创建、不被调用，因此不产生 `const` 暂时性死区问题；
运行时已由浏览器冒烟确认（见 §5）。

### 4. 守卫为何不需要扩展

段 31/32 的失败关闭登记解决的是"**声明把状态带交给设计系统、实际却没渲染**"。
本段没有新增任何状态带声明，也没有新增可被伪造的语义声明——拆分是同一份代码的物理搬迁，
因此**没有新建台账项**。守卫继续以原有方式失败关闭：

- `low_code_workbench_product_guard`：视图行数 600 → **554**（回到上限内），
  设计系统用量、contract 声明名、`section-display-label` 绑定等 29 条断言全部保持；
- `low_code_publish_boundary_guard`：新 `.ts` 落在既有扫描根内，
  仍禁止 `publishBusinessConfigChangeSet` 越权导入与编辑器内 `publish:true`
  （扫描文件 39，AST 节点 44258，errors 空）。

### 5. 验证（分层结果）

**声明**：改动路径 = `frontend/apps/web/src/views/**`（1 个 Vue + 3 个新 `.ts`），
`docs/**` 派生清单。影响层：L1 静态/生成物、L2 前端定向单测与守卫；风险类：
纯重构（非持久化、非授权、非契约语义）。最早必需层 L2；L3/L4 见下。

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS `coverage=L1_only` |
| L1 | `make verify.guard.registry` | PASS `1352 scripts` |
| L1 | `make ci.generated_reports.guard` | PASS（刷新后） |
| L2 | `make verify.frontend.typecheck.strict` | PASS（`vue-tsc --noEmit` + strict 工程） |
| L2 | `eslint src/views/BusinessConfigSurfaceView.vue` + 3 个新文件 | PASS（0 问题） |
| L2 | `make verify.business_config.product_guard / .publish_boundary_guard / .guard_inventory` | 全 PASS |
| L2 | `make verify.business_config.unit` | PASS（9 组，多套用例全绿） |
| L2 | `make verify.frontend.page_contract.key_consistency.guard / .orchestration_consumption.guard` | PASS（keys=18 / source_files=707；orchestration PASS） |
| L2 | `make verify.frontend.navigation_shell.unit / primitive_adapter.unit / page_pattern_reference_parity.unit / low_code_field_create_dialog.unit` | 19/34/15/6 全 PASS |
| L2 | `make verify.frontend.rendering_detail_state.unit / component_driver_takeover.unit` | PASS（`surfaces=173 gaps=0`；`required=33 missing=0`） |
| L4 | 受管角色浏览器冒烟（见 §6） | PASS |

**L3 跳过**：未改后端模型、权限、数据契约、迁移 → 不做模块升级与夹具重置。

派生清单按既有方式刷新（未新增归档工具）：
`make refresh.frontend.rendering_detail.inventory`、
`make refresh.frontend.component_driver_takeover.inventory`、
`python3 scripts/ci/generate_complexity_budget_report.py --write`。

### 6. 候选、运行身份与浏览器冒烟

- 旧产物归档保留（**未覆盖**）：`config05-20260929` → `config05-20260929-prev-3da37f767`
  （其 `base_sha` 即 `3da37f767…`，即段 32 的候选）。
- 新候选：`config05-20260929/dist`，`base_sha=e25a8e6ae…`（本段 2 笔提交后的干净 HEAD），
  `dirty_scope=""`，`entry=/assets/index-jJZSUKRZ.js`，
  `entry_sha256=c8a76a6e4512be2556f96547363604188b6e68c97a3471fbfe114ebd1119b296`，
  `index_sha256=6cbe3902ef0367f5f35f0d286e3f63c49fb6c4b0ef3a5c184cdc6ff2b2599ca8`。
  构建命令：`SC_ACCEPTANCE_RUNTIME_PROFILE=local DB_NAME=sc_frontend_acceptance COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01 make frontend.standard.preview.build`
  （单次构建；构建前先移走旧目录，否则会 `REUSED unchanged build`）。
- 5180 监听进程**未变**：`pid=802966`，`node scripts/release/release_static_server.mjs`，
  `STATIC_ROOT=…/config05-20260929/dist`，`STATIC_PORT=5180`。按请求读盘 → 替换产物即生效，
  **未新增常驻端口，未重启服务**。
- 身份自校验：HTTP 回读 `index.html` 与入口 JS，`index_sha256`/`entry_sha256` 与
  `build-identity.json` **逐字节一致**。
- 受管后端容器 `sc-backend-odoo-acceptance`（healthy，`127.0.0.1:18082→8069`，
  db `sc_frontend_acceptance`），受管角色 `fixture_role_config_admin`。**全程零写入**。
- 证据目录：`sce-offrepo/artifacts/seg33-route-assembly/`（`route-assembly-smoke.json` + 2 张截图）。

冒烟结果（同一受管角色，两视口，POST 写请求计数 **0**）：

| 检查 | 工作台（无范围参数）1440×900 | 工作台（`model=payment.request&action_id=775`）1440×900 | 同 390×844 |
|---|---|---|---|
| `data-page-sections-ready`（页契约门控） | `true` | `true` | `true` |
| `data-contract-sections`（指纹绑定） | `[true,{},{},{},{}]` | 同 | 同 |
| `data-runtime-route`（抽离后的运行目标） | `''`（未选范围） | **`/a/775`** | `/a/775` |
| 业务页面目录 `.scan-row` | 60 | 60 | 60 |
| 页头契约动作按钮 | 2 | 2 | 2 |
| 页面级横向溢出 | 无（1440/1440） | 无 | 无（390/390） |
| console error | 0 | 0 | 0 |
| POST 写请求 | — | 0 | 0 |

### 7. 本段发现并登记的既有失败（非本段引入，独立记账）

| 失败项 | 定性 | 证据 |
|---|---|---|
| `verify.frontend.config_workbench_navigation_boundary.guard` FAIL | **既有守卫/验收脚本漂移** | 守卫要求 `product_navigation_boundary_acceptance.mjs` 含 `product_configuration_entry_count === 1` 等 3 个 token；该脚本**在 HEAD 提交内也不含**（`git show HEAD:…` 计数为 0），两文件本段均未修改。漂移起点指向 `2ef14ff65 Merge PR #372`：该合并把验收脚本改成 TDesign 选择器（`:scope > .t-submenu__title` 等）后，守卫期望的旧 token 从未补回 |
| `verify.business_config.coverage` FAIL | **独立的数据覆盖状态** | 失败信息为 `低代码业务配置覆盖验收未通过：system_root, user:admin, user:wutao`；`scripts/verify/business_config_coverage_gate.py` **不含任何前端引用**，本段前端改动不可能影响它 |

两项都**未修复、未放宽、未改写成通过**，按既有规则独立保留（不扩大本段范围）。

### 8. 显式登记（不在本段范围）

- 承接段 28–32 全部登记项：`BusinessConfigCoverageWorkspace` 的
  `page-config-selection-empty`（布局框架）、`BusinessConfigStartPanel` 的
  `config-status--empty`（徽标修饰符）、`/admin/release-operator` 与
  `scene-health`/`scene-packages` 无 platform-admin 夹具、`style_system.guard` 四项文件长度欠账、
  `state_transition_undeclared` 五条、`generate_frontend_visual_projection_inventory.py` 的
  `consumer_primitive_visual_chrome` / `direct_root_visual_overrides` 仍只读 `.vue`。
- 本段**未新增**任何越界，也未新增守卫欠账。

### 9. 提交

- `refactor(web): extract the workbench route assembly out of its view`
- `chore(web): refresh the derived inventories after the route assembly split`
- 段记录（本文件）

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## 段 34｜导航边界守卫漂移：把断言重新绑到真实配置入口，并修掉被它挡住的缓存场景视图越权派发（2026-09-30）

段 33 登记的 `verify.frontend.config_workbench_navigation_boundary.guard` FAIL，本段定向收口。
裁决：**升级验收脚本把断言重新绑到当前真实入口；不改守卫、不降断言、不恢复旧 DOM 迎合测试。**

### 1. 漂移定性

守卫 `scripts/verify/frontend_config_workbench_navigation_boundary_guard.py` 对验收脚本
`frontend/apps/web/scripts/product_navigation_boundary_acceptance.mjs` 要求 3 个 token：

- `product_configuration_entry_count === 1`
- `legacy_configuration_entry_count === 0`
- `getByRole("heading", { name: "菜单配置", exact: true })`（语义：配置入口必须**真实可达**）

`2ef14ff65 Merge PR #372` 把验收脚本改成 TDesign 内部选择器（`.t-submenu__title` 等）后，
3 个 token 全部消失，守卫从此长期红。守卫本身要表达的业务边界（唯一「产品配置」入口、
拒绝旧「配置中心」、配置入口真实可达）**没有被推翻**，只是验收脚本的定位方式与入口事实
同时失效，所以按「保留断言含义、替换定位方式」处理。

### 2. 本段实测的真实入口（不再假设历史菜单分支）

- 导航树当前发布 `产品配置`（唯一）→ `表单配置`(menu 417/action 720)、`流程审批配置`(711)、`字段管理`(732)。
- **没有** `低代码系统配置`/`菜单配置` 节点；`legacy_configuration_entry_count = 0`。
  菜单 `smart_construction_core.menu_ui_menu_config_policy_business_config` 处于 `active=False`，
  故「产品配置 → 菜单配置」这条旧分支已不发布，验收不得再靠它证明可达。
- 真实可达路径：`产品配置 → 表单配置` → `/admin/business-config`（工作台）
  → `选择业务页面` → 选择一条业务页面（本次 `account.account` / action 302）
  → 工作台发布 `导航入口` 任务卡 → `配置菜单` → `/admin/menu-config` → `H1 菜单配置`。
- 该路径为只读：`选择` 与 `配置菜单` 只产生
  `ui.business_config.surface.get` / `coverage.scan` / `change_set.open`，**无 create/write/unlink/execute_button/upload**。

### 3. 被这条路径挡住的真实产品缺陷（根因修复）

修复前，沿上述真实用户路径点击 `表单配置` 后，页面会发出
`POST /api/v1/intent {"intent":"handling", ...}` → `404 INTENT_NOT_FOUND: Unknown intent: handling`，
并在浏览器留下 console error。

根因（非猜测，逐层查实）：

1. `表单配置` 的菜单/动作入口带业务契约字段 `entry_intent=handling`
   （`addons/smart_construction_core/models/support/product_policy_sync.py` 的 `entry_intent_label='办理'`），
   落地 URL 为 `/admin/business-config?…&entry_intent=handling&…`。
2. `App.vue` 用 `<KeepAlive :max="6">` 缓存业务视图；被缓存的 `SceneView` 的 watcher
   仍随**全局 route 变化**继续触发。
3. `SceneView.vue` 用 `route.query.entry_intent` 直接当**场景入口意图**派发
   （`sceneContractEntryIntent`），于是把「业务办理处置值」当成「场景意图」发出去。

`entry_intent` 是**两个契约共用的一列参数**：业务入口契约用 `handling/query/analysis/config/master_data/source_fact`，
而打开场景的行动作（如 `_PROJECT_DASHBOARD_ROW_ACTION`）用它携带 `project.dashboard.enter`
这类**已声明场景意图**。所以判定依据只能是「谁拥有这条路由」，**不能是取值形状**（不做字符串启发式猜测业务语义）。

修复（最小、契约正确）：

- 新增 `frontend/apps/web/src/app/sceneEntryContract.ts`：`ownsSceneRoute()` + `resolveSceneContractEntryIntent()`
  （非 `scene` 路由一律返回空意图；`scene` 路由继续接受查询里的已声明场景意图，否则回落到场景契约自声明表）。
- `SceneView.resolveScene()` 首行先校验路由归属；`SceneView.vue` 不再各自持有意图映射表。
- **未**通过禁止导航、全屏刷新、清空草稿或改后端来绕开。

### 4. 验收体系为什么没发现这个偏差（缺口与补齐）

| 缺口 | 为什么漏 | 本段补齐 |
|---|---|---|
| 只读页/工作台入口漂移 | 守卫只校验验收脚本**是否含 token**，不校验该断言是否仍指向**真实可达**路径；token 缺失时长期红也无人跟进 | 验收脚本改为走真实入口（选择业务页面 → 配置菜单），守卫 token 原样保留 |
| 缓存视图越权派发无确定性验证 | 没有场景路由归属的单元测试；浏览器验收也从不从场景页进入业务配置页 | 新增 `verify.frontend.scene_entry_contract.unit`（40 例），覆盖 `handling/query/analysis/config/master_data/source_fact` 在非归属路由上**必须为空** |
| 改动 `SceneView.vue` 只会落到通用兜底 | `scripts/verify/frontend_dev_incremental.py` 的 RULES 无 `SceneView.vue` 规则 → 只推荐 `verify.frontend.typecheck.strict` | 新增规则：`/views/SceneView.vue`、`/app/sceneEntryContract.ts` → `verify.frontend.scene_entry_contract.unit` + `verify.frontend.navigation_shell.unit`，并加对应单测 |
| 只读详情呈现结构 | 已有 `data-navigation-toggle="submenu"` 第一方语义锚点替代已消失的 `.t-submenu__title`/`aria-expanded` | 沿用段 33 已落地的锚点，不再依赖 TDesign 内部类名 |

### 5. 分层验证（L0→L5）

| 层 | 命令 | 结果 |
|---|---|---|
| L0 | `git diff --check` / 工作树与 HEAD 身份 | PASS |
| L1 | `make ci.local.iteration` | PASS（`change_state=dirty coverage=L1_only`） |
| L1 | `make verify.guard.registry` | PASS（1352 scripts / 124 孤儿已登记） |
| L1 | `make ci.generated_reports.guard` | PASS（含 complexity / split-plan 派生刷新） |
| L2 | `make verify.frontend.scene_entry_contract.unit`（新增） | PASS `cases=40` |
| L2 | `make verify.frontend.navigation_shell.unit` | PASS（含新增前置依赖） |
| L2 | `python3 -m unittest scripts.verify.test_frontend_dev_incremental` | PASS 12 |
| L2 | `make verify.frontend.config_workbench_navigation_boundary.guard` | **PASS**（段 33 的 FAIL 关闭） |
| L2 | `make verify.frontend.typecheck.strict` | PASS |
| L2 | `make verify.frontend.lint.src` | PASS（0 error / 57 既有 warning） |
| L2 | 三份派生清单 `--check` | PASS |
| L4 | `make verify.product.navigation_boundary`（受管角色 + 5180 真实候选） | **PASS**（desktop + mobile，`errors=[]`、`mutations=0`） |

**L3 跳过**：未改后端模型、权限、数据、契约投影或迁移 → 不做模块升级与夹具重置。

### 6. 候选、运行身份与环境

- 旧产物保留（**未覆盖**，按序归档）：
  `config05-20260929-prev-221b5ba5b`（07:48 构建）、
  `config05-20260929-prev-221b5ba5b-navdrift`（验收脚本重绑版）、
  `config05-20260929-prev-221b5ba5b-sceneown-v1`（仅含第一次场景修复版）。
- 新候选：`config05-20260929/dist`，`base_sha=221b5ba5b…`，`dirty_scope` 见
  `config05-20260929/build-identity.json`，`entry=/assets/index-D-WZIX_H.js`，
  `entry_sha256=7ee7724b0b344fc38f8a2dcad1ac8e31c89314e1a666fa8933a42317374a41d3`，
  `index_sha256=18127f6813ec84740d01ad505dba6984aa37fdd6184aa16e4ac02536d378fb53`，
  `diff_sha256=28027a581ee8df80046346e3162b072184952fff2e60301784acdbb048fac91b`。
  构建命令：`SC_ACCEPTANCE_RUNTIME_PROFILE=local DB_NAME=sc_frontend_acceptance COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01 make frontend.standard.preview.build`
  （单次构建；构建前先移走旧目录，否则 `REUSED unchanged build`）。
  **未二次构建、未做全文件 HTTP 比对。**
- 5180 监听进程**未变、未重启、未新增端口**：`pid=802966`，
  `node scripts/release/release_static_server.mjs`，`STATIC_ROOT=…/config05-20260929/dist`，
  `STATIC_PORT=5180`，`API_PROXY_TARGET=http://127.0.0.1:18082`。按请求读盘 → 替换产物即生效。
- 身份自校验：HTTP 回读 `index.html` 与新入口 JS，`index_sha256`/`entry_sha256` 与
  `build-identity.json` **逐字节一致**。
- 受管后端容器 `sc-backend-odoo-acceptance`（healthy，`127.0.0.1:18082→8069`，
  db `sc_frontend_acceptance`），受管角色 `fixture_role_config_admin`。
  **本轮全部浏览器操作 mutations=0，零业务写入、零数据恢复动作。**

### 7. 验收结果（`make verify.product.navigation_boundary`，5180 真实候选）

| 项 | 1440×900 desktop | 390×844 mobile |
|---|---|---|
| 旅程 | 项目中心深链→刷新→折叠持久→前进后退→产品配置→表单配置→选业务页面→配置菜单→`H1 菜单配置` | Drawer `role=dialog`/`aria-modal`、Esc 关闭并归还焦点、横向溢出 0 |
| `errors`（console/pageerror/≥400 API） | 0 | 0 |
| `mutations` | 0 | 0 |
| 绑定身份 | menu 680 / action 861；配置对象 `account.account` / action 302 | — |
| 守卫 token 事实 | `product_configuration_entry_count=1`、`legacy_configuration_entry_count=0`、`menuConfigurationHeadingText=菜单配置` | — |

### 8. 提交

- `fix(web): keep the cached scene runtime inside the route it owns`（产品代码 + 反例单测）
- `chore(verify): rebind the navigation boundary acceptance to the published config entry`（验收脚本 + 派生清单 + 复杂度/分片派生 + 增量映射规则）

### 9. 显式登记（**不在本段范围，继续独立记账**）

- `verify.business_config.coverage` FAIL（`低代码业务配置覆盖未通过：system_root, user:admin, user:wutao`）——
  数据覆盖状态，脚本无前端引用，本段未触及。
- `BusinessConfigCoverageWorkspace` 的 `page-config-selection-empty`、`BusinessConfigStartPanel` 的
  `config-status--empty`、`/admin/release-operator`、`scene-health`/`scene-packages` 无 platform-admin 夹具。
- `style_system.guard` 四项文件长度欠账（本段未放宽阈值、未压行数消红）；
  `SceneView.vue` 行数保持 1708（**未增长**）。
- `state_transition_undeclared` 五条；`generate_frontend_visual_projection_inventory.py` 仍只读 `.vue`。
- 工作台「选择业务页面」目录加载约 13–15 s 才出现（既有性能观感问题，本段只作等待条件，未改实现）。

### 10. 补记｜页面契约覆盖守卫的扫描范围与段 33 抽取结果失配（同段收口）

段 33 把 `BusinessConfigSurfaceView.vue` 的页面契约消费抽到同名伴随目录
`frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigSurfacePageContract.ts`
（其中调用 `usePageContract('business_config')`）。四个页面契约守卫长期红，本段查实根因并定向收口。

**根因（非猜测）**：四个守卫的 `_find_page_consumers()` / `usePageContract(` 扫描只覆盖
`views/*.vue` + `pages/*.vue`。抽取后 `usePageContract(` 落在 `views/businessConfigSurface/*.ts`，
不在扫描集合内 → 该页从消费者集合消失，覆盖断言随之报缺。

**五问边界**：`Formal Product Layer` = P0 平台内核产品（验证/Gate 工具层，非业务层）；
`Layer Target` = `scripts/verify/frontend_page_contract_*`；`Module` = 验证脚本；
`Standard vs User-Specific` = 平台机制；`Why Here` = 断言集合的**取值来源**就是扫描范围，范围错口径就错；
`Why Not Elsewhere` = 不能改 `usePageContract(` 的调用位置去迎合守卫，也不能给该页加豁免；
`Blast Radius` = 仅四个守卫的候选文件集合，产品代码、契约、渲染路径零改动。

**修复（放宽的是断言的"广度"而非"强度"）**：

- 三个 section 覆盖守卫（`sections_coverage` / `section_tag_coverage` / `section_style_coverage`）：
  `candidates` 扩展为 `views/*.vue`、`views/*/*.vue`、`views/*/*.ts`、`pages/**` 同形集合，
  注释写明「视图可把抽出的部件放在同名伴随目录，仍属同一页面契约消费范围」。
- `frontend_page_contract_boundary_guard.py`：新增
  `view_module_scopes = {"BusinessConfigSurfaceView.vue": "businessConfigSurface"}`，
  并对伴随目录做 `usePageContract(` 兜底检查（目录不存在也报错），不把检查放宽到无关模块。

**反例验伪（证明检查真在求值，不是阈值放宽）**：把
`useBusinessConfigSurfacePageContract.ts` 里的 `usePageContract('business_config')` 改成
`usePageContractNeutralized(...)` 后，四项守卫**全部 FAIL**；`git restore` 复原后四项 **PASS**。

**分层验证**：L0 `git status` 干净；L1 `make verify.guard.registry` PASS、`make ci.generated_reports.guard` PASS；
L2 四项守卫 + `verify.frontend.page_contract.key_consistency.guard` **全部 PASS**
（`checked_pages=17, checked_sections=85`；`keys=18, source_files=708`）。
产品布局未变 → 产物与 5180 候选**无需重建**（`base_sha` 仍为 `221b5ba5b…`）。

**提交**：`fix(guard): let the page-contract coverage guards see extracted companion modules`

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## 段 35｜尺寸门禁越限收口：把受限文件里的职责拆出去，并补上增量路由缺口（2026-09-30）

### 1. 本轮触发与真实起点

- 起点 HEAD `3e46b5649`（段 34 收口），工作树干净，分支 `feature/web-official-template-adoption`。
- 实测当前强制门禁，`verify.frontend.style_system.guard` **FAIL**，其余通过：
  - `frontend/apps/web/src/views/ActionView.vue exceeds 3800 lines: 3803`
  - `record runtime exceeds 619 lines: frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts=621`
  - `verify.frontend.no_new_any_guard` PASS（709 文件 / 25 any / 11 余额）。

### 2. 越限溯源（按实际 git 历史核对，未按行号猜改）

| 文件 | 越限前 | 越限提交 | 越限后 | 阈值 |
|---|---|---|---|---|
| `views/ActionView.vue` | `20781fe2d` = 3795 | `95137138d` *refactor(web): execute the declared batch intent instead of naming actions* | **3803** | 3800 |
| `pages/contractForm/useRecordFormActions.ts` | `97f5ff0fe` = 612 | `20781fe2d` *feat(web): derive the page type from the contract, not from a business model* | **621** | 619 |

两条都是**业务驱动的真实重构**（声明式批量意图、由契约派生页面类型）把文件推过棘轮，
不是无意义代码增长；因此本轮只拆职责，不放宽阈值、不压行数消红。

### 3. 验收体系为什么没发现（用户明确要求先补缺口）

`scripts/verify/frontend_dev_incremental.py` 的 `RULES` **从不指向** `verify.frontend.style_system.guard`：
`views/ActionView.vue` 与 `pages/contractForm/*.ts` 只落到兜底 `verify.frontend.typecheck.strict`。
于是日常增量迭代对这两个文件**只做类型检查**，尺寸棘轮只有在有人手工全量跑守卫时才暴露——
这正是它们能连续越限的直接原因。尺寸规则的唯一执行点在人工路径上，不在迭代路径上。

### 4. 修复 A｜批量选择行为退出 `ActionView.vue`（3803 → 3672）

- 新增 `frontend/apps/web/src/app/action_runtime/useActionViewSelectionActionRuntime.ts`（225 行）：
  承载 `selectionActions`、`handleSelectionAction`、`runBatchPolicyAction`，并导出 `ActionBatchPolicy`。
- `ActionView.vue` 只保留组合，删除本地 `ActionBatchPolicy` 及
  `actionViewBatchRuntime` / `actionViewBatchActionFlowRuntime` / `actionViewSelectionExportRuntime` 导入。
- **行为等价搬运**：同一份声明式批量策略、同一批 execution intents、同一守卫与确认决策、
  同一 `unlinkActionViewRecord` / `batchUpdateActionViewRecords` 调用与同一 `finally` 清理。

### 5. 修复 B｜设计器导航退出保存属主（621 → 599）

- 新增 `frontend/apps/web/src/pages/contractForm/useRecordFormDesignerNavigation.ts`（117 行）：
  `lowCodeApplyBaseParams` / `lowCodeReturnQuery` / `previewLowCodeConfiguredPage` /
  `previewCurrentFormConfiguration` / `returnToBusinessConfigDesigner`。
- `useRecordFormActions.ts` 在已组合设计器动作处组合该导航，**函数体逐行等价**：
  同一路由标志、同一「有草稿先保存再预览」判断、同一业务配置设计器返回路径。

### 6. 修复 C｜把尺寸门禁接回增量路由，并给路由本身加自检

- `frontend_dev_incremental.py` 新增两条 `Rule`：
  `layouts/AppShell.vue` / `pages/ListPage.vue` / `pages/ContractFormPage.vue` /
  `pages/ContractFormRoute.vue` / `views/ActionView.vue` → `verify.frontend.style_system.guard`；
  `pages/contractForm/` + `components/template/` **追加**该守卫（既有目标一个不减）。
- 新增单测 `test_size_ratcheted_files_route_to_the_size_guard`：直接读取守卫的
  `SIZE_LIMITS` 与 `RECORD_RUNTIME_SIZE_LIMITS`，断言**每条**受限路径都被路由到尺寸门禁。
  这样扩展棘轮而漏扩路由会立刻失败，而不是再次静默兜底。
- 实测增量入口对这两个文件已经调用尺寸门禁：
  `make verify.frontend.dev.incremental FRONTEND_DEV_CHANGED_PATHS="…/ActionView.vue …/useRecordFormActions.ts"`
  → `frontend_style_system_guard PASS` + `[frontend.dev.incremental] PASSED returncode=0`。

### 7. 守卫探测位置维护（保留断言含义，未放宽）

`scripts/verify/list_batch_action_closure_guard.py` 三条断言原扫描 `ActionView.vue`，行为抽出后失效。
处理原则同段 34：**跟随行为到新属主，并保留「视图确实消费该属主」的反向断言**。

- 新增 `selection_action_runtime` 读取抽出的运行时；
- `ActionView` 必须组合 `useActionViewSelectionActionRuntime(` 且仍传 `contractActions: contractActionButtons`；
- `resolveSelectionActions(` + `execution_intents`、`unlinkActionViewRecord`、`batchUpdateActionViewRecords`
  三条在生产该行为的模块内断言。

### 8. 反例验伪（证明检查真在求值）

- 把 `ActionView.vue` 中的 `useActionViewSelectionActionRuntime(` 改名 →
  `verify.list_batch_action.closure_guard` **FAIL**；复原 → **PASS**。
- 删掉新增的尺寸路由 → `test_size_ratcheted_files_route_to_the_size_guard` **FAILED (failures=5)**；
  复原 → **OK (13 tests)**。

### 9. 分层验证结果

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make verify.frontend.style_system.guard` | **PASS**（`hardcoded_color_refs_max=0`，两条尺寸越限关闭） |
| L1 | `make verify.frontend.no_new_any_guard` | PASS |
| L1 | `make ci.local.iteration` | PASS（`coverage=L1_only`） |
| L1 | `make verify.guard.registry` | PASS（1352 scripts / 124 orphans） |
| L1 | `py_compile` + `python3 -m unittest scripts.verify.test_frontend_dev_incremental` | OK（**13 tests**） |
| L2 | `make verify.list_batch_action.closure_guard` | PASS |
| L2 | `make verify.frontend.standard_collection_composition.unit` | PASS（`cases=113`） |
| L2 | `make verify.frontend.form_designer_actions.unit` | PASS（`cases=6`） |
| L2 | `make verify.frontend.contract_form_save_failure_recovery.unit` | PASS（edit-retry / single-flight / create-retry / permission-denial） |
| L2 | `make verify.frontend.adopted_form_validation_identity.unit` | PASS（`cases=46 failed=0 engine=shipped-save-chain host=real-vue-instance`） |
| L2 | `make verify.frontend.record_form_return.unit` | PASS（`cases=13`） |
| L2 | `make verify.frontend.typecheck.strict` | PASS（抽离前后各一次） |
| L4 | `make verify.frontend.standard_preview.unit` | OK（6 tests） |
| L4 | `make verify.frontend.standard_page_type.browser`（5180 真实候选） | **passed assertions=32**，`errors=[]`、`forbiddenWrites=[]` |
| — | `make ci.generated_reports.guard` | PASS（先刷新复杂度/分片派生，再复检） |

说明：`scripts/verify/test_frontend_dev_incremental.py` 在托管环境**无 pytest**，
按仓库既有入口用 `python3 -m unittest` 运行（与 `make verify.frontend.dev.incremental.unit` 一致）。

### 10. 候选、运行身份与产物归档

- 旧产物保留（**未覆盖**，按序归档）：
  `config05-20260929-prev-221b5ba5b-sizesplit-v1`（本轮起点候选，
  `entry=/assets/index-D-WZIX_H.js`，`entry_sha256=7ee7724b…`，`index_sha256=18127f68…`）。
- 新候选：`config05-20260929/dist`，`base_sha=3e46b5649…`，
  `entry=/assets/index-DShCtG8D.js`，
  `entry_sha256=cc73042cdab8684bedc572cba22d7d73943e041ccb1c370c318b886ee7c5b891`，
  `index_sha256=4c236bf058f4b866449dda73f7b9d49230195e6e4c7d374c21eb332c00380555`，
  `diff_sha256=483c0f4e1cd4d23eab5a188f510f524cfaf578f5d18837e44d3ab625ea62d0f1`。
  **单次构建**：`SC_ACCEPTANCE_RUNTIME_PROFILE=local DB_NAME=sc_frontend_acceptance COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01 make frontend.standard.preview.build`
  （构建前先归档旧目录，否则入口按设计拒绝：`preview build inputs changed`）。
- 5180 监听进程**未变、未重启、未新增端口**：`pid=802966`，
  `node scripts/release/release_static_server.mjs`，`STATIC_ROOT=…/config05-20260929/dist`，
  `STATIC_PORT=5180`，`API_PROXY_TARGET=http://127.0.0.1:18082`；`preview.up` 返回
  `REUSED current 5180 listener`（按请求读盘，替换产物即生效）。
- 浏览器断言已绑定当前候选：报告内 `build.entry_sha256` 与上文 `entry_sha256` 一致。
- **未二次构建、未做全文件 HTTP 比对、未新增常驻端口**；本轮浏览器操作 `mutations=0`。

### 11. 提交

- `refactor(web): move the list batch-selection behaviour out of ActionView`（新运行时 + 视图 + 探测位置维护）
- `refactor(web): move the designer navigation out of the save owner`（新运行时 + 保存属主 + 复杂度/分片/三份渲染清单派生刷新）
- `fix(verify): route size-ratcheted frontend files to the size guard`（增量路由 + 路由自检单测）

### 12. 显式登记（**不在本段范围，继续独立记账**）

- `verify.business_config.coverage` FAIL（`system_root, user:admin, user:wutao`）——数据覆盖状态，脚本无前端引用。
- `BusinessConfigCoverageWorkspace` 的 `page-config-selection-empty`、`BusinessConfigStartPanel` 的
  `config-status--empty`、`/admin/release-operator`、`scene-health`/`scene-packages` 无 platform-admin 夹具。
- `style_system.guard` 四项欠账中**尺寸两项本段关闭**，其余（z-index 等）保留；
  `state_transition_undeclared` 五条保留。**未放宽阈值、未改退出码。**
- `verify.unified_page_contract.v2` 的 `payment.request` 表达缺口
  （`done`/`payment_execution`、workflow `activate/complete/reopen/reactivate`）仍待 P1 权威补声明，**不得猜测补齐**。
- 工作台「选择业务页面」目录约 13–15 s 才出现（既有性能观感问题）。
- 本段未触及 `.agent/`、未触碰业务矩阵；`AppShell.vue` 未新增业务职责。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。
未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

## 段 36｜前端门禁聚合由红转绿：两条守卫的真实缺陷（探针与源码布局耦合、探针与 diff 形状耦合）（2026-09-30）

### 1. 本轮触发

段 35 收口后，在 clean HEAD 上第一次跑完整**前端门禁聚合** `verify.frontend.quick.gate`
（45 个子目标），得到 **一条真实 FAIL**：`verify.frontend.professional_base_field.unit`。
继续扫权威门禁面，又得到第二条真实 FAIL：`verify.frontend.delivery_hardening.guard`。
两条都不是产品行为缺陷，而是**探针自身的判定方式与源码形式耦合**——正是段 34/35 反复处理的同一类漂移。

### 2. 修复 A｜`professional_base_field` 守卫：断言绑定到语句，而不是源码布局

**现象**：clean HEAD 上 `[frontend_professional_base_field_guard] FAIL base field handler does not fail closed`，
指向 `useRecordFormState.ts` 的 `queryMany2oneInline`。

**根因（查实，非猜测）**：`030a189b9 fix(web): keep the exact typed text in the relation search input`
把该 handler 改成多行、并在声明前加了一段注释（**行为未变，仍然 fail-closed**）。
守卫把「非可写即返回」写成**整行字面量**，于是换行/注释一变即失配——
报告的是一个**仍然 fail-closed 的 handler**“没有 fail-closed”。同文件另外三个 handler 仍是一行，故未触发。

**修复（保留断言含义，替换定位方式）**：新增 `_compact()`，**先去注释（行/块）再去空白**，两侧同时规范化。
于是绑定变成「声明签名后面**紧跟** fail-closed 守卫，且它仍是函数体的第一条语句」：

- 换行重排 + 无关注释 → 不再误报；
- 守卫被注释掉 → 注释被剥离后消失 → **仍然 FAIL**；
- 守卫被移到别的语句之后 → 前缀不再紧邻 → **仍然 FAIL**。

**新增回归（`test_frontend_professional_base_field_guard.py` 13 → 16 项）**：
`test_rewrapped_handler_still_passes`（重排+内联注释仍通过）、
`test_rewrapped_handler_without_the_guard_fails`、`test_rewrapped_handler_that_does_not_open_with_the_guard_fails`。

**真实源码反例验伪**：临时删除真实 `useRecordFormState.ts` 里那一句守卫 → 守卫 **FAIL**；
原样恢复 → **PASS**；`git diff` 对该产品文件为空（确认原样恢复、产品零改动）。

### 3. 修复 B｜`delivery_hardening` 守卫：按基线修订判定“新增”，而不是按 diff 形状

**现象**：clean HEAD 上 `[frontend_delivery_hardening_guard] FAIL new model-specific CSS`。

**根因（查实）**：该规则在 `git diff --unified=0 origin/main -- frontend/apps/web/src` 的**新增行**里
匹配 `\.(?:project|contract|settlement|payment)[-_][\w-]+\s*\{`。
而 `CurrentFormFieldSettingsPanel.css` 里原有一条**共享选择器规则**：

```css
-.contract-field-selection-card,
-.contract-field-selection-empty {
+.contract-field-selection-card {
```

共享选择器列表被拆开后，git 把**保留下来的那个选择器**重新输出为一条新增行。
于是 `.contract-field-selection-card` 这个**在 `origin/main` 早已存在**的选择器被当成新增模型专用 CSS。
换言之：**零新增模型专用样式，却报了一条新增违规**——判定绑定到了 diff 形状，而不是“是否是新产品语义”。

**修复（保留断言含义，替换定位方式）**：新增 `MODEL_SPECIFIC_SELECTOR_RE` 与
`_base_frontend_source(path)`（按路径缓存 `git show origin/main:<path>`）。
新增行里命中的选择器，只有在**基线修订中不存在**时才计为违规；比较带边界
（`re.escape(selector) + r"(?![\w-])"`，避免长名满足短名）。
真正新增的模型专用选择器依旧 FAIL，并且报出精确路径与选择器。

**反例验伪**：临时向 `CurrentFormFieldSettingsPanel.css` 追加
`.payment-brand-new-banner { … }` → 守卫 **FAIL**
`… : .payment-brand-new-banner`；移除后 → **PASS**；产品文件 `git diff` 为空。

**回归**：`test_frontend_delivery_hardening_guard.py` 新增 `NewModelSpecificCssTest`，
锁定“按基线判定新增”的实现（含 `git show origin/main:{path}` 与边界检查），并断言
“只看新增行的旧字典键”不再存在，防止退回 diff 形状判定。

> 说明：该守卫的基线引用是 `origin/main`。本轮先执行了一次 `git fetch origin main`，
> 使远端跟踪引用与实际 `origin/main` 一致，比较才有意义（只更新 remote-tracking ref，
> 未改工作树、分支、也未推送）。

### 4. 本轮实测的门禁现状（HEAD，全部为真实运行）

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS（`change_state=clean`、`coverage=L1_only`） |
| L1 | `make ci.generated_reports.guard` | PASS（复杂度/分片/remote plan/fingerprint 全部 current） |
| L2 | `make verify.frontend.quick.gate`（45 子目标） | **由 FAIL 转 PASS（exit=0）** |
| L2 | `make verify.frontend.pr.unit` | PASS |
| L2 | `make verify.frontend.release.unit` | PASS |
| L2 | `make verify.frontend.delivery_hardening.guard` | **由 FAIL 转 PASS** `/ PASS error_states=12 title_writers=1 async_epoch=enabled axe=4.10.2` |
| L2 | `make verify.frontend.professional_base_field.unit` | **由 FAIL 转 PASS**（13 → **16 tests**） |
| L2 | `make verify.frontend.style_system.guard` / `no_new_any_guard` / `typecheck.strict` | PASS |
| L2 | `make verify.frontend.lint.src` | PASS（**0 error / 57 warning**，exit 0） |
| L2 | `make verify.frontend.release_navigation_policy.guard`、`page_width_contract.guard`、`page_identity` | PASS |

### 5. 本轮新登记的欠账（**不靠放宽消红**）

- **`verify.frontend.industry_agnostic.guard`：FAIL，`files=747 findings=127`。**
  这是**收敛型门禁**：脚本自身声明 `FRONTEND_INDUSTRY_AGNOSTIC_ENFORCE=1`
  “intended for the release gate after convergence”，报告 `policy.target=zero`、
  `policy.baseline_approval=forbidden`。它**未接入任何聚合目标，也不在
  `.github/workflows/frontend_release_gate.yml` 的任何 lane**里。
  逐类计数：`industry_text_anywhere` 37、`industry_behavior_identifier` 36、
  `business_field_inference` 32、`industry_literal` 12、`industry_model_or_xmlid` 5、
  `industry_regex_inference` 3、`industry_asset` 2；
  集中在 `components/professional-fields/PaymentSettlementIntroduceDialog.vue`(31)、
  `api/overviewRichTextPatch.ts`(13)、`components/page/blocks/BlockChartDataset.vue`(11) 等。
  **本轮只登记准确数字，不展开全仓行业语义清理，也不允许靠删基线/放宽判定消红。**
- `verify.frontend.all_list_visual.audit` 需要 `E2E_PASSWORD`（浏览器凭据）→ 本轮 **not_run**（前置缺失，非门禁失败）。

### 6. 验收体系为什么没及时发现（本轮的直接教训）

这两条守卫有一条共同特征：**它们不在这条专题日常会跑的路径上**。
`quick.gate` 直到本段才第一次在前端专题里运行；`professional_base_field` 的失配自
`030a189b9`（09-29）起潜伏，期间所有前端批次都不会碰到它。
段 35 已把「尺寸棘轮」接回增量路由；本段暴露的是同一类问题在**聚合层**的版本：
**单一入口的守卫失配不会被任何日常路径发现，只有聚合门禁才会暴露。**
因此本段的两条修复各自的回归都随提交保存，且 `quick.gate` 可以作为后续批次的一条低成本聚合检查。

### 7. 边界七问

`Formal Product Layer` = P0 平台内核（验证/Gate 工具层）；`Layer Target` =
`scripts/verify/frontend_professional_base_field_guard.py`、`scripts/verify/frontend_delivery_hardening_guard.py`
及其单测；`Module` = 验证脚本；`Standard vs User-Specific` = 平台机制；
`Why Here` = 两条断言都在声称“某行为必须成立”，而它们实际判定的是源码**形式**；
`Why Not Elsewhere` = **不**改产品去迎合探针（本段产品源码零改动）、**不**放宽阈值、
**不**给 `industry_agnostic` 加豁免；`Blast Radius` = 仅两个守卫脚本与其单测。

### 8. 候选与运行身份

本段**无产品源码改动**（仅 `scripts/verify/*`）→ 按既有证据失效规则，
段 35 的 5180 候选继续有效，**不重建、不重启、不新增端口**：
`base_sha=3e46b5649…`、`entry=/assets/index-DShCtG8D.js`、`entry_sha256=cc73042c…`、
`index_sha256=4c236bf0…`；监听仍为 `pid=802966`。

### 9. 提交

- `fix(verify): bind the base-field fail-closed assertion to statements, not layout`
- `fix(verify): decide new model-specific CSS against the base revision`

### 10. 显式登记（**不在本段范围，继续独立记账**）

- 段 35 全部登记项不变（`verify.business_config.coverage` 数据覆盖、
  platform-admin 夹具缺口、`state_transition_undeclared` 五条、
  `payment.request` 契约表达缺口需 P1 权威补声明、工作台目录 13–15 s 观感）。
- 新增：`industry_agnostic.guard` 127 项（见 §5）；`all_list_visual.audit` 凭据前置缺失。
- 未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。


## 段 37｜把「从结算单引入」弹窗的行业词汇收回 P1 契约，并让前端在契约缺口处失败关闭（2026-09-30）

### 1. 本轮触发

`verify.frontend.industry_agnostic.guard`（收敛门禁，`policy.target=zero`）报告里，
`components/professional-fields/PaymentSettlementIntroduceDialog.vue` 是**单一最大命中点（31/127）**。
逐条看下去，这不是「行业词汇恰好出现在通用组件里」，而是更严重的形态：
**弹窗自带一整套行业文案与载荷键名，因此即使有效契约什么都不声明，它仍然能凭本地硬编码
拼出一个看起来可用的办理流程——契约缺口被永久隐藏。** 这正是本专题要消掉的形态。

### 2. 权威归属（先定边界，再改代码）

| 事项 | 权威 | 本轮处理 |
|---|---|---|
| 弹窗标题/描述/占位/列头/状态/历史/模式/按钮文案 | P1 施工行业标准（`smart_construction_core`） | 由既有 normalizer 经 `componentConfig` 声明 |
| 载荷键名（`payment_request_id`/`settlement_id`/…） | 后端真实参数名，同样属 P1 契约面 | 由契约声明，前端只按声明取值 |
| 如何呈现、何时启用入口、缺口如何显现 | 端侧适配 | 前端负责，且必须 fail-closed |

这**不是新发明**：同一组件家族早已用 `introduceLabel` / `optionalDetails` / `amountBinding` /
`actionRefs` 驱动前端，并有既有测试断言。本段只是把「引入弹窗」这一块补进同一模式。

### 3. 改动

**A. P1 契约声明**（`addons/smart_construction_core/core_extension_contract_normalizers.py`）
在既有 `introduceLabel` / `actionRefs` 之外新增 `introduceDialog` 块（36 个叶子键：
文案、列头、状态、历史、模式、提示、`payloadFields` 七个真实参数名）。
`actionRefs` 三个动作身份保持不变（`payment.request.settlement.search` / `.preview` /
`payment.request.add.settlement.lines`）。

**B. 前端消费 + 失败关闭**
- 新增 `paymentSettlementIntroduceDialogModel.ts`：`SETTLEMENT_INTRODUCE_REQUIRED_PATHS`（44 条），
  `resolveSettlementIntroduceContract()` 逐路径解析；**空白值也算缺口**；**无任何默认值**；
  `requireSettlementIntroduceContract()` 为调用方提供失败关闭入口。
- `PaymentSettlementDetailCollectionControl.vue`：契约就绪才渲染入口按钮并挂载弹窗；
  不就绪则**不渲染入口、不挂载弹窗**，只渲染禁用按钮 + 缺口提示（点名缺失路径）。
- `PaymentSettlementIntroduceDialog.vue`：全部模板文案、三个 intent 身份、七个载荷键改为
  `contract.*`；删除 `requiredActionRef` 猜测函数与 `contract_id` 字段。
  弹窗内 `付款|结算|合同|明细|名称|状态|取消|搜索|引入` 命中数 = **0**。

**C. 守卫与反例**
- `frontend_professional_detail_collection_guard.py`：AST 解析 normalizer 声明的叶子路径，
  与前端 `REQUIRED_*` 数组**两侧比对**（`unrequired=` / `undeclared=` 分别报），
  并禁止弹窗内出现载荷键/动作猜测/行业词。单测 43 → **44 项**。
- 新增 `payment_settlement_introduce_dialog_contract_test.ts`（**67 例**）：
  逐条 44 个必需路径单独删除/置空都必须失败关闭并点名。

**D. 派生清单**（生成器权威输出，非放宽阈值）
`generate_frontend_rendering_detail_inventory.py` 的期望条目由字面 `data-dialog-purpose`
改为契约绑定的 `:data-dialog-purpose="contract.purpose"`；三份清单 digest 按实际源码刷新。

**E. 浏览器定向断言**（复用既有 `standard_page_type_browser.mjs`，不新建 harness）
从**有效契约响应**里取出声明词汇，再断言页面渲染的就是声明值：
入口标签 == `introduceLabel`、弹窗标题 == `introduceDialog.title`、
确认按钮 == `introduceDialog.confirmLabel`、页面上无 `data-contract-semantic-gap`。

**F. 后端组件测试**：`test_core_extension_v2_finalize.py` 补 `introduceDialog` 全量断言
（purpose/title/cancel/confirm/recordRequiredMessage/`columnLabels` 全字典/`payloadFields` 全字典/键全集），
声明被截短时后端套件先失败。

### 4. 本轮踩到的真实缺陷（前端类型层，值得记录）

实现完成后 `vue-tsc` 报 3 处 `TS2339: Property 'missing' does not exist`。
根因**不是**写法错误，而是本仓库 `frontend/apps/web/tsconfig.json` 是 `"strict": false`
（`strictNullChecks` 关闭），**布尔判别式无法窄化联合类型**（已用最小复现确认：
同一段代码 `--strict` 通过、非严格模式报错）。
处理方式：模型与消费点改用 `in` 检查选择变体（`'missing' in resolved` / `'contract' in …`），
**没有降低契约、没有引入 `any`、也没有把断言改成字符串**。

### 5. 定向验证

| 层 | 命令/入口 | 结果 |
|---|---|---|
| L1 | `scripts/verify/frontend_industry_agnostic_audit.py` | **127 → 97 findings**（files 748） |
| L1 | `ci.local.iteration` | PASS（dirty / L1_only / 524 changed paths） |
| L1 | `pnpm -C frontend/apps/web typecheck` | PASS（修复 `in` 检查后 0 error） |
| L2 | `verify.frontend.professional_detail_collection.unit` | PASS（守卫 44 + 弹窗契约 67） |
| L2 | `verify.frontend.rendering_detail_state.unit` | PASS（76 项；其中一行 `FAIL incomplete=` 是 fail-closed 反例测试的预期输出） |
| L2 | `collection_action_toolbar / primitive_adapter / product_page_pattern / professional_component_registry / style_system.guard` | PASS |
| 活契约 | `/api/v1/intent`（`ui.contract.v2`, `payment.request` form, `fixture_role_finance` uid 30） | 变更前 `introduceDialog` **不存在**；重建容器后 **存在**，36 键，`payloadFields` 与声明一致 |
| L4 | `verify.frontend.standard_page_type.browser` | **passed assertions=38**（原 32，本轮 +6） |

浏览器本轮新增断言全部通过：契约已发布到页面、入口标签 == 声明值、无缺口标记、
弹窗标题 == 声明值、确认按钮 == 声明值；`errors=[]`、`forbiddenWrites=[]`。
证据：`artifacts/frontend-web-fix-20260928/tpl07-1790739384227/`（含 `payment-introduce-dialog.png`）。

### 6. 缺口处理规则（本轮落地形态）

**契约缺失 → 入口禁用 + 弹窗不挂载 + 点名缺失路径；已确认安全的读取不受影响。**
即「禁止未知语义被默认为允许」，而不是遇到一个缺口就停掉整页。

### 7. 候选与运行身份

- 源码：`15351d632`（本段三笔代码提交之后）+ 本轮记录提交。
- 后端：受管容器按新修订重建（`make backend.acceptance.up`），
  `SC_SOURCE_REVISION` 与实际 `addons` 一致——**这是构建预览的前置**：
  `standard-page-build` 会拒绝 `git diff` 与容器记录修订不一致的候选。
- 5180：新产物 `entry=/assets/index-BlsrCAPY.js`、`entry_sha256=db3b259f…`、
  `index_sha256=ab5602d9…`；监听仍为 `pid=802966`（同路径替换产物，服务按请求读盘，
  无需重启）；旧产物按序归档为 `config05-20260929-prev-introduce-contract`。
  HTTP 回读确认服务端 entry 与 `build-identity.json` 完全一致。

### 8. 边界七问

`Formal Product Layer` = P1 施工行业标准（契约声明）+ 端侧契约消费；
`Layer Target` = `smart_construction_core` 的 `core_extension_contract_normalizers.py` 与
`components/professional-fields/*` 的引入弹窗/集合控制；
`Module` = `smart_construction_core` + `frontend/apps/web`；
`Standard vs User-Specific` = 行业标准（任何标准施工部署都应继承同一引入词汇）；
`Why Here` = 词汇与载荷键名是**业务语义**，只能由有效契约声明；
`Why Not Elsewhere` = **不**在前端按模型名/列名/按钮文案重建（本轮删除的正是这条路径）、
**不**把契约缺口的判断放进页面、**不**用默认值兜底；
`Blast Radius` = 付款申请表单的「从结算单引入」入口与弹窗、其守卫与派生清单；
读取链路、其他模型与其他弹窗不受影响。

### 9. 提交

- `fix(web): consume the declared introduce-dialog contract instead of guessing`
- `feat(construction): declare the settlement introduce vocabulary in the contract`
- `fix(verify): bind the introduce-dialog gap to the declared contract vocabulary`
- 记录与派生清单随本段单独提交。

### 10. 显式登记（**不在本段范围**）

- `industry_agnostic.guard` **127 → 97**：剩余集中在 `overviewRichTextPatch`(13+9)、
  `BlockChartDataset.vue`(11)、`SceneContractBlockGridView.vue`(9)、`productPageHeaderAdapters.ts`(8)、
  `boqImportPreview`(7+6)、`chartFetch.ts`(5) 等；仍不靠删基线/放宽判定消红。
- 该弹窗残留 1 条**假阳性**（`settlement.contract_name` 被 `sc.(project|contract|…)` 正则命中）
  与集合组件键 `sc.payment.settlement_detail_collection` 1 条，均在既有登记内。
- 段 35/36 全部登记项不变（`verify.business_config.coverage`、platform-admin 夹具缺口、
  `state_transition_undeclared`、`payment.request` 契约表达缺口、`render_semantic_ready_guard` 滞后、
  `all_list_visual.audit` 凭据前置、工作台目录 13–15 s 观感）。
- 未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 38｜把「动作语义完备性」守卫扩到第三条真实权威：财务工作区的对象方法动作不再能静默存在（2026-09-30）

### 1. 本轮触发

上一步顺着段 28 登记的「`payment.request` 的 `done`/`payment_execution` 表达缺口」复核。
**活契约实测先推翻了这个旧登记**（见 §2）：八类业务动作的语义全部已声明，缺口并不存在。
但同一轮复核暴露了真正的问题——**它本来就不该只靠人工核对活契约才能发现**：

`scripts/verify/workflow_action_semantics_completeness_guard.py` 此前只读两条权威
（`workflow_contract_service.py` 的 `PROFILE_BY_MODEL`/`ACTIONS`、`payment_request_available_actions.py`
的 `_ACTION_SPECS`），**完全没有覆盖第三条真实权威** `services/financial_workspace_contract.py`。
该文件里 `view_payment_execution`（L731-775）以对象方法 `action_view_payment_execution` 执行，
**没有任何语义声明**，守卫却看不见它。

这就是本专题反复出现的形态：**不是「某个词写错了」，而是「一条真实执行路径从未进入验收射程」。**
缺的不是再核对一遍活契约，而是**让这类动作一旦新增就必须被分类，否则门禁失败**。

### 2. 活契约实测（先证伪旧登记，再定位真实缺口）

`/api/v1/intent`（`ui.contract.v2`，`model=payment.request`，`view_type=form`，`record_id=1813`，
`fixture_role_finance` uid 30）返回 **11 个动作**，业务动作语义**全部已声明**：

| 动作 key | method | `action_semantics` |
|---|---|---|
| `payment_submit` | `action_submit` | `business/submit/contract.action` |
| `payment_approve`（3 变体） | `action_approve*` | `business/approve/contract.action` |
| `payment_reject`（2 变体） | `action_reject*` | `business/reject/contract.action` |
| `payment_done` | `action_done` | `business/complete/contract.action` |
| `payment_execution` | `action_create_payment_execution` | `business/start_execution/contract.action` |
| `cancel` | `action_cancel` | `business/cancel_record/contract.action` |
| `save_draft` | `data.write` | 平台持久化例外（`PLATFORM_PERSISTENCE_KEYS`），正确 |

即段 28 登记的「`payment.request` 的 `done`/`payment_execution` 表达缺口」**实际已闭合**；
`action_semantics_vocabulary.py` 已含 `start_execution`/`complete`/`reopen`，
`workflow_contract_service.py` L876-888 八个动作全部映射。**旧登记在本段更正，不再挂账**（见 §9）。

顺带确认前端执行链**没有**按方法名猜意图：`canonicalFormActionExecutor.ts` 的
`resolveCanonicalFormActionExecution()` 明确按 `backendIdentity` 精确匹配（不按标签/方法/模型/角色/状态推断），
`actionExecutionPlan.ts` 按显式 `intent`/`kind`/`methodName` 分派。**前端这一侧是干净的，缺口在验收体系。**

### 3. 权威归属

| 事项 | 权威 | 本轮处理 |
|---|---|---|
| 一个可被 Web 执行的动作属于什么业务目的 | 已发布的动作语义词汇表 + 各契约权威的显式声明 | 守卫扩到第三条权威 |
| 财务工作区的动作列表如何组装 | `financial_workspace_contract.py`（P1 行业标准） | 静态读取其字面声明 |
| 导航类动作（读取关联记录、不做状态迁移） | 显式登记表 + 理由 + 硬化条件 | 新增 `NAVIGATION_METHOD_ACTIONS` |
| 方法名/文案能否决定业务意图 | **不能** | 守卫以「是否声明语义」判定，不看方法名 |

### 4. 改动（仅验证体系，产品源码零改动）

**A. `scripts/verify/workflow_action_semantics_completeness_guard.py`**
- 新增 `FINANCIAL_WORKSPACE` 常量与 `--financial-workspace` 参数。
- 新增 `NAVIGATION_METHOD_ACTIONS`：带理由的导航豁免登记表（当前仅 `view_payment_execution`）。
- 新增 `financial_workspace_action_declarations(path)`：AST 扫 `actions.append({...})` 与 `return [ {...} ]`，
  用既有 `eval_node` 静态求值。**必须用 `eval_node` 才能读到嵌套 `action_semantics`**
  （最初只读 `ast.Constant` 导致误报——这一段本身也是「校验器必须先能被反例打穿」的证明）。
  `binds_method` 表示「存在 `method` 键（即使值不可解析）」；`propagates_semantics` 表示该 dict 用
  `**(action_semantics=...)` 从 workflow registry 行传播语义（由既有 `validate()` 覆盖，跳过）。
- 新增 `validate_navigation_exception(key, item)`（硬化）：豁免**不得**用于 `required_params` 非空、
  `requires_reason` 为真、或 `action_safety.classification ∈ {danger, destructive}` 的动作。
- 新增 `validate_financial_workspace_actions(...)`：绑定方法的动作必须
  (a) 声明已发布 purpose 且落在已发布 (kind, purpose, executor) 三元组内，或
  (b) 在导航登记表内并通过硬化检查；另检「登记 key 必须仍被声明」「登记项必须有理由」；
  declarations 为空 → 报 vacuous 失败（**零读取等于失败，不是通过**）。

**B. 单测 `scripts/verify/test_workflow_action_semantics_completeness_guard.py`：4 → 15 项**
新增 `FinancialWorkspaceActionClassificationTest` 11 项：已声明通过、无 purpose 失败、词汇表外 purpose 失败、
未发布三元组失败、registry 传播不重判、导航豁免覆盖通过、豁免 key 消失失败、豁免无理由失败、
**豁免用于带输入动作失败**、**豁免用于破坏性动作失败**、空读取 vacuous 失败。

### 5. 验证（L0→L5，风险类：验收体系正确性）

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `python3 scripts/verify/workflow_action_semantics_completeness_guard.py` | **PASS**：`profiles=65 reachable_actions=9 payment_specs=4 workspace_actions=3 role_gates=4 verdict_covers=4 roles=11 vocabulary=10` |
| L1 | `PYTHONPATH=scripts/verify python3 -m unittest test_workflow_action_semantics_completeness_guard` | **Ran 15 tests, OK** |
| L1 | `make verify.native_view.workflow_action_coverage` | **PASS**（单测 8 + 10 项；`registered=31 navigation=14 state_transition_undeclared=5`） |
| L1 | `make verify.workflow_state_phase_coverage` | **PASS**（16 项） |
| L1 | `make ci.local.iteration` | **PASS**（`coverage=L1_only`，`change_state=dirty`） |

**真实源码反例验伪**（对 `financial_workspace_contract.py` 本身，非构造输入）：

1. 临时删除 `payment_execution` 的 `action_semantics` 行 → 守卫 **exit 1**，点名
   `financial workspace action 'payment_execution' binds method 'action_create_payment_execution'
   without a declared action purpose and is not a registered navigation action ['view_payment_execution']`。
2. 临时注入 `{"key":"some_new_object_action","method":"action_some_new_thing"}` → **exit 1**，点名该 key。
3. 两次恢复后 `git diff --stat` 均为空 → 守卫 **exit 0**。**产品文件零改动得到证明。**

### 5b. 接线收口：让守卫真的会被自动运行

写完 §4 后核查守卫是否进入任何自动门禁，发现同一形态的第二处实例：

`workflow_action_semantics_completeness_guard` 只挂在 `verify.workflow_contract.backend` 下，
而该目标仅被 `verify.workflow_contract` 引用，**后者不被任何 CI lane 引用**
（`grep -rn "verify.workflow_contract\b" make/ .github/workflows/` 只命中定义自身）。
即：**守卫此前只在我手动运行时生效，从不进入自动门禁**——正是本段主题：
「一条真实路径从未进入验收射程」，只不过这次是守卫自己。

**收口**（只改 `make/ci.mk`，产品代码零改动）：

- 新增轻量目标 `verify.workflow_action_semantics.guard`（`py_compile` + 守卫 + 15 项单测），
  **不依赖容器**与 `audit.workflow_state.inventory`。
- 接入 `verify.unified_page_contract.v2` 与 `verify.unified_page_contract.v2.professional_backend`
  （两者已有 `verify.native_view.workflow_action_coverage`、`verify.workflow_state_phase_coverage`）。
- `verify.workflow_contract.backend` 改为依赖该新目标并移除重复调用，保持**单一接线权威**。

**验证**：

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make verify.workflow_action_semantics.guard` | **PASS**（守卫 + 15 项单测） |
| L1 | `make -n verify.unified_page_contract.v2` | 命中该守卫 **3** 次调用（py_compile/守卫/单测） |
| L1 | `make -n ci.local.quick.run` | 同样命中 **3** 次 → **Quick/交付 lane 会执行它** |
| L1 | `make ci.local.iteration` | **PASS** |

### 6. 缺口处理规则（本段落地形态）

**一条可被 Web 执行的对象方法动作，要么声明已发布语义，要么以带理由的导航豁免登记并满足硬化条件；
两者都不满足时门禁失败。** 新动作不能靠「没被扫描到」而静默存在。

### 7. 候选与运行身份

- 源码：`4da430d50`（本段第一笔）+ 接线提交（`make/ci.mk`）。
- 本轮**未改 `addons`**，容器 `sc-backend-odoo-acceptance` 仍绑 `SC_SOURCE_REVISION=15351d632…`
  （`SC_SOURCE_FINGERPRINT=4a3c77c5…`），无需重建。
- 本轮**未构建前端**；5180 仍为段 37 产物（`pid=802966`，`127.0.0.1:5180` 监听），
  入口 `entry=/assets/index-BlsrCAPY.js`；后端 `127.0.0.1:18082` 正常监听。

### 8. 边界七问

`Formal Product Layer` = P0 平台内核（动作语义词汇表/守卫）+ P1 行业标准（财务工作区契约）；
`Layer Target` = `scripts/verify` 的验收守卫与单测，不触碰 `smart_core`/`smart_construction_core` 产品代码；
`Module` = 验收体系（`scripts/verify`）；
`Standard vs User-Specific` = 平台机制（动作语义的完备性校验规则）；
`Why Here` = 「哪些执行路径必须被分类」是**验收体系的职责**，不是某个业务模块的；
`Why Not Elsewhere` = **不**在产品契约里补声明来让门禁变绿（那会掩盖路径）、
**不**在前端按方法名猜意图（前端已按 `backendIdentity` 精确匹配）、
**不**放宽守卫判定或加无理由豁免；
`Blast Radius` = `workflow_action_semantics_completeness_guard.py` 及其单测；
其他契约权威、其他模型、前端渲染与业务办理不受影响。

### 9. 显式登记（**不在本段范围**）

- **更正**：段 28 登记的「`payment.request` 的 `done`/`payment_execution` 表达缺口」经活契约实测**已闭合**
  （`complete`/`start_execution` 均有声明与三元组），本段从挂账中移除。
- 段 32/35/36/37 全部登记项不变：`industry_agnostic.guard` 127→97（收敛门禁，未接入聚合目标）、
  弹窗 1 条 `sc.*` 正则假阳性 + 集合组件键 1 条、`style_system.guard` z-index、
  `state_transition_undeclared` 五条、`render_semantic_ready_guard` 滞后、
  `verify.business_config.coverage` FAIL（数据覆盖）、platform-admin 夹具缺口、
  `verify.frontend.all_list_visual.audit` 需 `E2E_PASSWORD`、工作台目录 13–15 s 观感。
- 新增观察（**未处理，仅记录**）：未跟踪的前端文件必须先 `git add` 才能被
  `frontend_standard_preview.py` 的 `inputs()` 计入构建身份，而 `git add` 又会让暂存内容进入
  `git diff` 计算 → **构建身份可能被暂存内容污染**。规避方式：构建前保持工作树干净。是否属缺陷待后续判定。
- 未推送、未合并、未部署目标环境；业务矩阵状态不变；`.agent` 未改。

### 10. 提交

- `fix(verify): prove the financial workspace action authority is classified`（守卫 + 15 项单测）
- `fix(ci): run the workflow action semantics guard from the contract lanes`（`make/ci.mk` 接线）
- 本段记录随这两笔提交保存。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 39｜整体收口：把离线必需门禁从红恢复为绿（2026-09-30）

### 1. 本轮触发

段 38 把守卫接进了 `verify.unified_page_contract.v2`，但当时没有跑该聚合本身。
本轮按「整体收口」要求，从聚合门禁而不是单点守卫出发，逐个确认必需检查的真实状态。
结果：**发现三处真实红灯，全部修绿**，其中一处自 2026-09-29 起就已存在。

### 2. 收口一：接线未同步清单，契约主 lane 被我弄红

`make verify.unified_page_contract.v2` 第一次运行即失败：

```
[unified_page_contract_v2_guard_inventory] FAIL
- verify.unified_page_contract.v2 aggregate dependencies drifted; extra=['verify.workflow_action_semantics.guard'] missing=[]
```

**原因**：该聚合有自己的权威清单 `OFFLINE_TARGETS`，`unified_page_contract_v2_guard_inventory.py`
会比对聚合依赖集合与清单是否一致。段 38 只改了 `make/ci.mk`，没有同步清单。

**修复**：把 `verify.workflow_action_semantics.guard` 及其两个脚本加入 `OFFLINE_TARGETS`
（同步权威清单，**不是**放宽判定）。提交 `498cd38b8`。

**顺带的结论**：这个清单守卫正是「接线完整性」的既有权威，它拦住了段 38 的疏漏。
段 38 §5b 关于「守卫不被任何 lane 调用」的发现仍然成立——清单检查的是聚合依赖一致性，
不检查守卫是否真的进入了某个 lane。

### 3. 收口二：离线聚合门禁自 2026-09-29 起为红（记录里的客户品牌引用）

`make ci.professional.backend.shard-verify` 失败：

```
[tenant_product_payload_boundary_guard] FAIL
- rule=customer_identity_or_brand_reference path=docs/ops/iterations/frontend_shared_foundation_gap_audit_20260909.md
FIXED_CUSTOMER_IDENTIFIERS=1
```

**原因**：更早的段落记录里直接写入了 P2 属主侧的真实客户品牌模块名与仓库名
（`sce_customer_<tenant_key>_legacy`、`sce-customer-<tenant_key>-odoo`）。
这些字符串由 `21df11b45`（2026-09-29 记录提交）引入；
守卫的 `CUSTOMER_IDENTITY_TOKENS` 从 `401bcb3bd`（clean product baseline）起就包含该品牌 token，
**因此该必需门禁自那笔记录提交起一直是红的，只是没有以这种聚合形态跑过。**

**修复**：把三处引用改写为仓库既有占位形式
（`sce_customer_<tenant_key>_legacy`、`sce-customer-<tenant_key>-odoo`），
**不改守卫、不加豁免**。被记录的事实（哪一层拥有该模块、注册哪个动作、哪个提交）完整保留。
提交 `c9135c13d`。

**判定**：这是「文档里固化了客户身份」，属真实违约，不是假阳性；
用占位符修正是它本就应有的形态。

### 4. 收口三：复杂度生成报告过期

`make ci.professional.backend.shard-reports` 失败：

```
[ERROR] complexity report is stale. Run: python3 scripts/ci/generate_complexity_budget_report.py --write
```

**原因**：段 38 把 `workflow_action_semantics_completeness_guard.py` 扩到 819 行，
进入报告的尺寸分档；扫描数 4504→4505、超预警阈值文件 98→99。

**修复**：经权威生成器 `generate_complexity_budget_report.py --write` 重新生成
（**不手工编辑报告**）。提交 `818d7c7fe`。

### 5. 整体验证矩阵（本轮实测）

| 门禁 | 结果 |
|---|---|
| `make verify.unified_page_contract.v2`（含一次前端构建） | **PASS** |
| `make ci.professional.backend.shard-verify` | **PASS** |
| `make ci.professional.backend.shard-reports` | **PASS**（8 份生成报告 current；`complexity_baseline_lock checked=11`） |
| `make ci.professional.backend.shard-tests` | **PASS**（name-binding 2844 文件、Python 语法 1170 文件、Node 语法 364 文件、E2E 预检） |
| `make verify.repository.clean_history` | **PASS** |
| `make verify.product.release.version` | **PASS** |
| `make verify.tenant.product_payload_boundary` | **PASS**（`FIXED_CUSTOMER_IDENTIFIERS=0`） |
| `make verify.frontend.typecheck.strict` | **PASS** |
| `make verify.frontend.lint.src` | **PASS**（0 errors，57 warnings） |
| `make verify.guard.registry` | **PASS**（1352 scripts，1228 referenced，124 orphans acknowledged） |
| `make verify.contract.structure_lock` / `architecture.complexity_baseline_lock` | **PASS**（domains=14；checked=11） |
| `make ci.local.iteration` | **PASS** |

即 `ci.professional.backend` 的三个 shard 合起来已全绿，`public_guard` 与
`merge_policy_gate` 的本地对应目标也全绿。

### 6. 未在本轮范围

- `verify.frontend.industry_agnostic.guard` 仍为 **FAIL（97 条）**，`policy.target=zero`，
  **未接入任何聚合/CI lane**，本轮不接入、不处理。按规则实测的真实分布（按文件）：

  | 文件 | 条数 | 规则 |
  |---|---|---|
  | `views/SceneContractBlockGridView.vue` | 6+3 | `business_field_inference` / `industry_behavior_identifier` |
  | `api/overviewRichTextPatch.ts` | 6+4+3 | `industry_behavior_identifier` / `business_field_inference` / `industry_text_anywhere` |
  | `components/page/blocks/BlockChartDataset.vue` | 6+5 | 同上两类 |
  | `app/presentation/boqImportPreview.ts` | 5+2 | `business_field_inference` / 行业文案 |
  | `app/presentation/productPageHeaderAdapters.ts` | 4+4 | `industry_literal` / `industry_text_anywhere` |
  | 其余 12 个文件 | 各 1–5 | 混合 |

  **判定口径（不臆断）**：`api/*` 的多为后端契约参数名/路径绑定（`project_id`、`contract_id`、
  `boq*`），属「消费契约」形态；`views/*`、`components/page/blocks/*` 与
  `app/presentation/*` 需要逐条判定是「消费契约」还是「按字段名/行业词推断行为」——
  后者才是真正需要消掉的越界。**这需要一次专项（审计器语义细化 + 前端改造），本轮不做。**
- `verify.business_config.coverage` 仍 FAIL，原因是验收数据库缺少 `system_root`/`user:admin`/`user:wutao`
  三个身份的数据覆盖，属**环境数据**问题，非代码缺陷。
- `verify.frontend.all_list_visual.audit` 需 `E2E_PASSWORD`，not_run。
- 段 38 §9 的其余登记项不变。

### 7. 边界七问

`Formal Product Layer` = 验收与交付门禁（跨 P0/P1 的仓库治理层）；
`Layer Target` = `make/ci.mk`、`scripts/verify/*`、生成报告与活记录；
`Module` = 验收体系（非产品代码）；
`Standard vs User-Specific` = 平台机制；
`Why Here` = 三处红灯都是「验收/交付体系自身的状态不对」，不属于任何业务模块；
`Why Not Elsewhere` = **不**放宽守卫、**不**加豁免、**不**手工编辑生成报告、
**不**把客户品牌留在记录里换取门禁变绿；
`Blast Radius` = 契约 lane 接线清单、活记录文档、复杂度报告；
产品代码零改动，业务渲染与办理不受影响。

### 8. 提交

- `fix(verify): register the action semantics guard in the contract lane inventory`
- `fix(docs): replace the customer brand reference in the iteration log with the tenant placeholder`
- `chore(reports): refresh the complexity budget report after the guard change`
- 本段记录随第三笔提交保存。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 40｜把「列表状态色调」从平台内核收回声明方：内核不再替业务决定哪个状态算成功（2026-09-30）

### 1. 本轮触发与分支主目标的关系

分支主目标：**前端所有渲染与交互由有效契约驱动，并回到组件官方模板组合逻辑**。
前面几段处理的是「前端自行推断业务语义」，本轮顺着同一条往前查了一层权威：
**平台内核自己也在替业务层发明语义。**

`addons/smart_core/utils/contract_governance_list_surface.py` 里硬编码了一份
业务状态 → 色调映射（`draft / in_progress / paused / done / closing / warranty / closed`），
并且**对所有带 `status_field` 的列表档案无条件生效**。
结果是：内核替 P1/P2 决定了「哪个业务状态算成功、哪个算警告」，
而这本来只能由拥有该模型的层声明。契约没有表达的东西被内核补齐了，缺口因此被永久隐藏。

### 2. 问题定位

- 映射写死在内核（`contract_governance_list_surface.py`），与具体模型无关却对全部档案生效；
- 前端消费方 `collectionStatusPresentation.ts` 在无 `tone_by_value` 时回退 `neutral`，
  本身是**正确的**（不猜），但内核总是给出映射，回退分支实际永不触发；
- 部分档案的状态值（如 `payment.request` 的 `submit/approve/rejected/cancel`）根本不在映射内，
  于是「已声明状态」和「未声明状态」被同一份内核默认值混在一起，**缺口不可见**。

判定：这是**内核越界发明业务语义**，属分支主目标要清的口子。

### 3. 修复：权威搬回声明方（行为保持的搬迁，非扩权）

内核侧：

- 只保留**投影**职责。新增 `STATUS_TONE_VOCABULARY =
  frozenset({neutral, info, success, warning, danger})` 与
  `normalize_status_tone_by_value(raw)`；
- **无声明 → 完全不写 `tone_by_value`**，由前端按其既有规则回退 `neutral`；
- `contract_governance.py`（facade）与 `contract_governance_registry.py` 只透传/整形，
  不再发明任何语义。

声明侧（P1，`addons/smart_construction_core/core_extension.py`）：

| 档案 | 声明内容 | 值来源 |
|---|---|---|
| `project.project.list` | 全量 7 值（`draft/in_progress/paused/done/closing/warranty/closed`） | `ScStateMachine.PROJECT_STATES` |
| `payment.request.list` | `{draft: neutral, done: success}` | `PAYMENT_REQUEST_STATES` |
| `project.material.plan.list` | `{draft: neutral, done: success}` | 模型 `state` 选择项 |
| `project.task.list` | `{draft: neutral, in_progress: info, done: success}` | 模型 `sc_state` 选择项 |
| `tax_deduction_registration.list` | **仍不声明** | 旧映射唯一重叠值 `draft` 原本即 neutral，无行为变化 |

**关键判定：这是行为保持的搬迁。**
`payment.request` 的 `submit/approve/rejected/cancel` 在旧内核映射里本来就没有条目
（只覆盖 `draft/done`），搬迁后**同样没有**，仍渲染中性——**没有借机扩权**。
这些状态该用什么色调属 P1 产品决策，已登记为**显式产品缺口**（缺口必须显现）。

### 4. 顺带修复：段 39 记录正文自己把客户品牌写回，聚合门禁自那笔提交起为红

写本段记录时复跑 `scripts/verify/tenant_product_payload_boundary_guard.py`，发现它在 HEAD
（`26c32476f`）**本身就是红的**：

```
[tenant_product_payload_boundary_guard] FAIL
- rule=customer_identity_or_brand_reference path=docs/ops/iterations/frontend_shared_foundation_gap_audit_20260909.md
FIXED_CUSTOMER_IDENTIFIERS=1
```

`git log -S` 定位：命中由 **`382d37e35`（段 39 的「离线门禁恢复」记录提交）** 引入。
段 39 在「原因」段落里为说明问题，把被判红的真实客户品牌模块名与仓库名**照着写了一遍**，
于是 `c9135c13d` 的修正只覆盖了更早的三处，**记录自身又新增了第四处**，
守卫从 `382d37e35` 起一直为红——这与段 39「聚合 PASS」的结论并不矛盾，
因为那段结论是在更早的 `c9135c13d` 时刻取得的。

**这暴露的是验收体系缺口，不是本段的副作用**：
记录文本是在**之后那一笔记录提交**里才写下的，
而那笔提交**没有复跑被它自己改变的文件所参与的守卫**。
「记录/文档提交同样要复跑该文档参与的门禁」此前不是硬规则，本段起按此执行。

**修复**：把该处改写为仓库既有占位形式
（`sce_customer_<tenant_key>_legacy`、`sce-customer-<tenant_key>-odoo`），
**不改守卫、不加豁免、不删已记录事实**。复跑后 `FIXED_CUSTOMER_IDENTIFIERS=0`、PASS。

### 5. 守卫：`scripts/verify/contract_governance_list_surface_split_guard.py`

挂在 `ci.local.quick.run`（`make/ci.mk:919`），双向 fail-closed，均已用注入实验证明有牙齿：

1. **内核不得出现任何业务状态字面量**（`draft`…`closed`）。
   注入 `_LEGACY_TONE_SEED = {"draft": …}` 即 FAIL；
2. **声明方 profile 必须拥有映射**。删掉 P1 声明即 FAIL
   （`project.project.list must own its status tone map; the kernel no longer supplies one`）；
3. **泛化到所有声明档案**：色调必须落在已发布词表内、键非空、逐字投影；
4. **`STATUS_VALUE_SOURCES`**：每个声明档案必须登记其状态值来源；
   守卫用 AST 读取 `ScStateMachine` 状态表或模型 `fields.Selection` 首元素，
   声明了模型不存在的值即 FAIL（注入 `"nope": "danger"` 报
   `declares values the model does not define`）。
   **新增声明档案必须同步补 `STATUS_VALUE_SOURCES`，否则 FAIL。**

### 6. 实测（按 L0→L5 分层；零测试即失败）

- **L1（静态/守卫，离线）**：`contract_governance_list_surface_split_guard` PASS；
  `_responsibility_map_guard`、`_registry_split_guard`、`_determinism_guard`、`_coverage` PASS；
  `construction_core_extension_{intent_handlers,hook_facts,capability_rows,project_layout}_split_guard` PASS；
  `navigation_contract_boundary_guard` PASS；`owner_industry_isolation_probe` PASS；
  `make ci.local.iteration` PASS；`tenant_product_payload_boundary_guard` 由红转 PASS
  （`FIXED_CUSTOMER_IDENTIFIERS=0`，见 §4）。
  四个派生清单 `--check` 全部 CHECK-OK
  （`rendering_detail` PASS surfaces=173 gaps=0；`component_driver_takeover` required=33 missing=0；
  `visual_projection` PASS；`official_design_alignment` PASS）。
- **L2（后端单测，受管容器内）**：
  `odoo.addons.smart_core.tests.test_contract_governance_record_context_registry`
  → **Ran 21 tests OK（0F/0E）**，含新增
  `test_standard_list_profile_keeps_the_declared_status_tone_map`；
  `test_contract_governance_kanban_profile_registry`、
  `test_contract_governance_task_form_profile_registry`、
  `scripts/verify/test_formal_list_configuration_baseline.py` 均 PASS。
  L2 前端 16 项 collection/list 目标（`verify.frontend.collection_*.unit`、
  `standard_collection_composition.unit`、`page_pattern_reference_parity.unit`、
  `product_page_pattern.unit`、`scene_entry_contract.unit`、`primitive_adapter.unit`、
  `professional_detail_collection.unit`）全 PASS。
- **L3（受管运行时）**：容器 `sc-backend-odoo-acceptance`，库 `sc_frontend_acceptance`，
  `127.0.0.1:18082`，`SC_SOURCE_REVISION=26c32476ff60a21fbc009a108b82bad4d189a448`（==HEAD），
  `/web/login` HTTP 200。运行时探针结论：4 个声明档案的每个键都解析到模型真实状态；
  `project.project` 列表契约投影出 `cell_role=status` + 完整 `tone_by_value`；
  `payment.request` 契约投影 `cell_role=status` 且**无** `tone_by_value`；
  `tax_deduction_registration.list` 记为 undeclared。

### 7. 判定

内核不再替业务决定语义，声明方成为唯一权威，缺口以「无声明 → 中性」的形式可见。
前端未被改动，仍是纯呈现 + 中性回退，符合「缺语义不得猜测补齐」。

### 8. 本段登记项（未处理，仅记录）

- `payment.request` 的 `submit/approve/rejected/cancel` 色调**未声明**，
  属 P1 产品决策，需业务确认后补声明（不代拟）。
- `verify.frontend.industry_agnostic.guard` 仍 FAIL（97 条，`policy.target=zero`，
  未接入任何聚合 lane）——需专项（审计器语义细化 + 前端改造）。
- `verify.business_config.coverage` FAIL（验收库缺 `system_root`/`user:admin`/`user:wutao`，
  环境数据）；`verify.frontend.all_list_visual.audit` 需 `E2E_PASSWORD`（not_run）。
- `state_transition_undeclared` 5 条仍在 `config/contract/native_view_undeclared_actions.v1.json`。
- `style_system.guard` z-index 与四项文件长度欠账不变。
- **P1 `core_extension.py` 行数预算守卫此前即红**（改动前 1830 已超 1787/1809/1820），
  本段新增 P1 声明后为 1842。**已确认非本段引入**，属预存量技术债；
  本段已把声明压到最小行数（净增 2 行/档案）。
- `test_contract_governance_project_form.py` 在容器内仍 8F+1E（既有登记的非通过，
  失败信息与色调无关）。

### 9. 边界七问

`Formal Product Layer` = P0 平台内核（搬运方）+ P1 建筑行业标准（声明方）；
`Layer Target` = `smart_core/utils/contract_governance_list_surface.py`（投影）、
`smart_construction_core/core_extension.py`（声明）、验收守卫；
`Module` = `smart_core` / `smart_construction_core`；
`Standard vs User-Specific` = 平台机制（投影）+ 行业标准默认（状态色调默认）；
`Why Here` = 投影是内核机制，色调是行业模型的业务默认，二者必须分层；
`Why Not Elsewhere` = **不**把业务状态留在内核、**不**把投影逻辑下放到 P1、
**不**让前端从中文标签猜色调、**不**靠降低词表或加豁免消红；
`Blast Radius` = 列表契约 `tone_by_value` 投影路径、4 个声明档案、契约守卫与单测。
未声明档案的契约投影由「内核默认映射」变为「无映射」，前端回退中性，行为不变。

### 10. 提交

- `fix(contract): own the list status tone in the declaring profile`（内核搬迁 + P1 声明 + 守卫 + 单测）
- `fix(contract): declare the remaining list status tones in the owning profiles`（其余档案补声明 + 守卫泛化）
- `fix(verify): require declared tones to name real model states`（守卫新增状态值来源校验）
- `docs(web): record segment 40 and reclaim the brand reference the boundary guard caught`
  （活记录段 40；段 39 记录正文的客户品牌回写修正，守卫由红恢复为绿；
  `page-pattern-reference-contract-gaps-v1.md` 与 `...-detail-ledger-v1.json`
  仅 `collection.semantic-tones` 一条改述）。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 41｜主线契约 lane 在 HEAD 整体核验，并给行业语义审计加「角色」维度让缺口可见（2026-09-30）

### 1. 本轮触发

分支主目标：**前端所有渲染与交互由契约驱动，并使用组件官方模板组合逻辑**。
段 40 收口了「列表状态色调」的权威归属；本轮回到主目标本体，做两件事：

1. 在 HEAD 上**完整核验主目标的契约 lane**（不再逐入口试点证明）；
2. 处理行业语义审计「把**消费契约**与**发明语义**压成同一个数字」的**验收体系缺口**。

### 2. 主目标契约 lane 在 HEAD 的整体核验

- `make verify.unified_page_contract.v2.professional_backend` **PASS**，包含
  `unified_page_contract_v2_guard_inventory`、`_schema`、`_assembler`、`_status`、`_action`、
  `native_view.workflow_action_coverage`、`workflow_state_phase_coverage`、
  `workflow_action_semantics_completeness_guard`、`_data`、`_runtime`、`_client`、`_intent`、
  `_web_consumer`、`_web_architecture`、`_stable_projection`；
  单测 16 / 15 / 20 / 107 / 5 例全部 OK。
- `make verify.unified_page_contract.v2.frontend_static` **PASS**
  （`verify.frontend.typecheck.strict` + `verify.frontend.build`，21.29 s）。
- 派生清单 `--check` 全绿：`frontend_rendering_detail_inventory` PASS surfaces=173 gaps=0；
  `component_driver_takeover_inventory` required=33 missing=0 bridge_only=0 adapter_unconsumed=0；
  `visual_projection_inventory` PASS；`official_design_alignment_inventory` PASS。
- 组件专业化清单 173 个表面 **gap=0**（governed_composite 113 / governed_primitive 41 / p3_out_of_scope 19）。
- 列表组合唯一：`standardListComposition.ts` 只有 `official-standard-list` 一个取值，
  `legacy-list-surface` 已不存在。

**结论：主目标的「契约驱动渲染 + 官方组合」在 HEAD 的结构与静态层没有缺口。**

### 3. 缺口：行业语义审计把「消费契约」与「发明语义」压成一个数字

`scripts/verify/frontend_industry_agnostic_audit.py` 是纯文本正则审计，`policy.target=zero`，
当前 97 条命中，**未接入任何 lane**。它无法区分三类完全不同的东西：

| 类别 | 例子 | 是否越界 |
|---|---|---|
| 注释/文档里的行业词 | `// 入参与后端 handler 对齐：project_id` | 否 |
| 传输参数名、属性名、登记键 | `project_id: params.projectId`、`'sc.payment.settlement_detail_collection'` | 否（**消费契约**必然出现） |
| 在比较/三元/过滤里用行业名选行为 | `key === 'project.management' ? '项目驾驶舱'` | **是** |

三者被合并成一个 97：既不能据以收口，也不能据此判定达标。这是**验收体系缺口**，
不是产品缺陷——它让「缺口不可见」。

### 4. 改动：新增「角色」维度，不改判定、不改计数

- `Finding` 增加 `role`，取值 `documentation | string_literal | code_identifier | code_conditional`。
  由 `lexical_role(text, start, matched)` 按**词法位置**判定：从行首走到命中点，
  跟踪 `//` 行注释、`/* */` 与 `<!-- -->` 块注释、引号字面量与转义（引号内出现未闭合的
  `'` 不会吞掉后续代码）；命中点仍落在代码区、且该行含比较/三元/`.filter(` 等分支标记时，
  记为 `code_conditional`，否则记为 `code_identifier`。
- **保持历史口径**：仍是「每规则每行一条」，去重键与旧实现一致。
  实测 `finding_count` 与各规则计数与改动前**逐一致**：97；28 / 2 / 36 / 5 / 3 / 2 / 21。
- **不改 `policy.target`，不改 ENFORCE 语义**：`FRONTEND_INDUSTRY_AGNOSTIC_ENFORCE=1` 下仍 rc=1。
  本段不是消红，而是让报告第一次可以用于收口判定。
- 报告新增 `role_counts`；14 例自测固定在
  `scripts/verify/test_frontend_industry_agnostic_audit.py`，
  入口 `make verify.frontend.industry_agnostic.audit.unit`，
  并成为 `verify.frontend.industry_agnostic.guard` 的依赖；
  脚本按 `active` 登记进 `scripts/verify/registry.yaml`，
  `make verify.guard.registry` **PASS**（1353 scripts / 1229 referenced / 124 orphans acknowledged / 1 retired）。

### 5. 角色分布与逐条判定

97 条角色分布：`documentation` 21、`string_literal` 17、`code_identifier` 48、`code_conditional` 11。

`code_conditional` 11 条已**逐条查看**（分布在 4 个文件）：

- `api/boqImportPreview.ts:100`、`views/SceneContractBlockGridView.vue:153,161`：
  按 `id > 0` 决定是否把**声明参数**放进请求载荷（传输整形）；
- `app/presentation/boqImportPreview.ts:141`：类型保护式强制转换；
- `components/page/blocks/BlockBoqImportPreview.vue:73`、`BlockChartDataset.vue:90,108`：
  判断**上下文是否存在**，然后在契约声明的
  `empty_message` / `empty_message_no_context` 两个键中择一。

**未发现「按行业名字发明业务规则」**：择一的对象是契约已声明的键集，文案本身来自块契约。

`code_identifier` 48 与 `string_literal` 17：按首次抽查为传输参数名/属性名/登记键（消费契约形态），
**未逐条复核**，本段不作结论。

**因此本段不宣布审计清零、不调整 `policy.target`、不动 ENFORCE。**
把目标从「零行业词」改为「零发明语义」并据此重写规则，属独立专项，
必须建立在本段的角色数据之上，**不得借收口顺手放宽**。

### 6. 另一个确认的陈旧规则（登记，不在本段改）

`industry_asset` 的 2 条命中是**按文件名**拦截：
`components/role-home/WorkspaceHome.vue`、`composables/shared-surface/useWorkspaceHome.ts`。
两者**仍在使用**（`views/HomeView.vue` 引用），且**按通用 `workspace_home` 契约渲染**
（`data-role-home-renderer="workspace-contract"`，任务/摘要/入口全部来自契约），
不是行业专用页面；原 11 个被拦文件中 9 个已删除。
按路径而非按行为判定与「消费与发明分离」的原则相反，登记为专项内处理项。

### 7. 边界七问

`Formal Product Layer` = 验收与交付门禁（跨 P0/P1 的仓库治理层）；
`Layer Target` = `scripts/verify/frontend_industry_agnostic_audit.py`、
`scripts/verify/test_frontend_industry_agnostic_audit.py`、`scripts/verify/registry.yaml`、`make/frontend.mk`；
`Module` = 验收体系（非产品代码）；
`Standard vs User-Specific` = 平台机制；
`Why Here` = 审计无法区分「消费」与「发明」，是审计自身能力的缺口，不属于任何业务模块；
`Why Not Elsewhere` = **不**改前端去迎合审计、**不**放宽阈值、**不**删命中、
**不**把 `target` 从 `zero` 换一个数字、**不**把 97 拆成「可忽略」；
`Blast Radius` = 审计报告结构（只增字段）、新增自测与登记项。
**产品源码与前端的渲染/交互零改动**，因此本轮无渲染影响面。

### 8. 提交

- `feat(verify): classify industry-agnostic findings by lexical role`
  （角色分类 + 14 例自测 + make 入口 + registry 登记 + 报告重导出）
- 本段记录随该提交保存。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 42｜把「reference 明细账」自带的完成规则做成机检：缺口必须有主、有出口（2026-09-30）

### 1. 本轮触发

段 41 把行业语义审计的角色维度补齐后，回头核查主目标依赖的第二本账：
`docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json`。
它自己声明了完成规则：

> `No needs_work item may remain when this PR is declared visually complete. Contract gaps require an authoritative owner, evidence, and follow-up target.`

但**没有任何门禁读它**。21 条 `contract_gap` 里多数只有一段描述性文字，没有
`owner`，也没有明确的关闭出口。这正是本轮要消除的验收体系缺口：
规则写在文件里，却由人工记得执行，等于没有边界。

### 2. 改动：新增 ledger 守卫（fail-closed，只加校验）

- 新增 `scripts/verify/page_pattern_reference_ledger_guard.py`，执行 ledger **自带的**
  `completionRule`，不引入第二套判定：
  - `needs_work` 不得残留（声明为 complete 的账本里出现即 FAIL）；
  - 每条 `contract_gap` 必须同时具备 `authority`、`owner`（`^(P[0-4]\b|evidence\b)` 正则，
    即 P0–P4 分层或 evidence）、`followUp`（≥12 字符，必须是可关闭的具体目标）；
  - 校验 `status` 词表、`surface` 白名单、`key` 唯一；
  - 非对象条目、缺 `completionRule`、`details` 非非空数组均 FAIL。
- 新增 13 例自测 `scripts/verify/test_page_pattern_reference_ledger_guard.py`，
  含 9 类反例：无 owner、伪造 owner（`P9`）、无 followUp、无 authority、
  残留 needs_work、未知 status、重复 key、未知 surface、缺 completionRule、非对象条目。
- **有牙齿验证**：补 `owner` 之前运行守卫 → FAIL 46 条；就地补全后 → PASS，
  证明它拦的是真实缺口而不是空跑。
- 接线：`make/frontend.mk` 的 `verify.frontend.page_pattern_reference_parity.unit`
  追加两行（自测 + 守卫）；两脚本以 `active` 登记进 `scripts/verify/registry.yaml`。

### 3. 缺口归属就地补全（只加字段，不改判定、不消红）

给全部 21 条 `contract_gap` 就地补 `owner` / `followUp`（紧凑行内注入，`details` 仍为 67 条）：

- `P0 smart_core`：`login.*`（4）、`shell.*`（2）、`collection.favorite`、
  `collection.settings-export`、`collection.record-action`、`detail.*`（9）；
- `P1 smart_construction_core`：`collection.semantic-tones`、`task.field-grid`、
  `task.slot-coverage`；
- `evidence`：`responsive.reference-mobile`（缺认证态 390px 参考截图，由证据补齐，非产品缺陷）。

**没有把任何 `contract_gap` 改成 `aligned`，没有删条目，没有放宽词表。**
`docs/frontend_productization/rendering-detail/page-pattern-reference-contract-gaps-v1.md`
新增 `## Ownership enforcement` 节，说明该配对是强制而非建议。

### 4. 边界七问

`Formal Product Layer` = 验收与交付门禁（跨 P0/P1 的仓库治理层）；
`Layer Target` = `scripts/verify/page_pattern_reference_ledger_guard.py`、
`scripts/verify/test_page_pattern_reference_ledger_guard.py`、`scripts/verify/registry.yaml`、
`make/frontend.mk`、reference 明细账与其 contract-gaps 说明；
`Module` = 验收体系（非产品代码）；
`Standard vs User-Specific` = 平台机制；
`Why Here` = 「缺口必须有主有出口」是账本自带的完成规则，理应由读该账本的门禁执行，
不属于任何业务模块；
`Why Not Elsewhere` = **不**把 `contract_gap` 降级为 `aligned`、**不**删条目、
**不**靠人工记忆维持、**不**把守卫降级为「提示」；
`Blast Radius` = ledger JSON 只增 `owner`/`followUp` 字段、新增守卫与自测、make 接线、
registry 登记、guard_registry 重导出。
**产品源码与前端渲染/交互零改动**，本轮无渲染影响面。

### 5. 验证

- `python3 scripts/verify/page_pattern_reference_ledger_guard.py` → `PASS entries=67 owned_gaps=21`（rc=0）；
- `python3 scripts/verify/test_page_pattern_reference_ledger_guard.py` → 13 tests OK（rc=0）；
- `make verify.guard.registry` → `AUDIT PASS: 1355 scripts (1231 referenced, 124/124 orphans acknowledged, 1 retired)`；
- `make verify.frontend.page_pattern_reference_parity.unit` → parity 15 tests OK + surfaces=16；
  ledger 13 tests OK + `PASS entries=67 owned_gaps=21`（三步都在同一入口内跑通，验证接线）；
- `python3 scripts/verify/tenant_product_payload_boundary_guard.py` → PASS
  `FIXED_CUSTOMER_IDENTIFIERS=0`（文档改动复查）；
- `make ci.local.iteration` → PASS `scope=unclassified_by_design coverage=L1_only`
  `next=risk_selected_non_zero_L2_targets_required`。

### 6. 提交

- `feat(verify): enforce the reference ledger completion rule`
  （守卫 + 13 例自测 + make 接线 + registry 登记 + ledger 归属补全 + contract-gaps 说明 + guard_registry 重导出）
- 本段记录随该提交保存。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 43｜色调回归前端呈现层：契约不再承载颜色，并把「文件行数」从阻断降为优化方向提示（2026-09-30）

### 1. 本段要解决的问题

段 40 已经认定「内核不能替业务决定哪个状态算成功」，但当时的修正方向是**让声明方在
profile 里声明 `tone_by_value`**。这在边界上是错的：`tone_by_value` 是颜色（呈现），
不是业务含义。于是本段把它彻底移出契约，并把方向掉转过来——
**契约只给权威状态值与原生标签，颜色由前端呈现层唯一决定。**

同时在执行中发现第二类「机械」问题：守卫把**文件行数**当作阻断点，且同一个文件被十几个
守卫各自用不同的历史快照盯着（`core_extension.py` 同时挂着 1787/1809/1820/1830/1858/
2065/2120/2243/3145/3763/4180/4241 十二个上限）。按本段确认的口径：
**行数是代码优化方向的提示依据，不是功能迭代的阻断点。**

### 2. 改了什么

**(A) 色调退出契约（后端）**

- `addons/smart_core/utils/contract_governance_list_surface.py`：删除 `STATUS_TONE_VOCABULARY`
  与 `normalize_status_tone_by_value()`；`govern_standard_list_for_user` 去掉
  `status_tone_by_value` 参数。状态列只写 `schema["cell_role"]="status"`。模块内不再出现
  任何业务状态值字面量（`"draft"`/`"in_progress"`/`"closed"` …）。
- `addons/smart_core/utils/contract_governance.py`：去掉调用点/签名/转发三处 `status_tone_by_value`。
- `addons/smart_core/utils/contract_governance_registry.py`：profile 形状不再归一化 `tone_by_value`。
- `addons/smart_construction_core/core_extension.py`：4 个 profile
  （`project.project.list` / `project.task.list` / `payment.request.list` /
  `project.material.plan.list`）删除 `tone_by_value` 声明（1842 → 1830 行）。

**(B) 前端承接色调，且只有一份权威**

- 新增 `frontend/apps/web/src/app/presentation/collectionStatusPresentation.ts`：
  `STATUS_TONE_POLICY` 以**权威状态值**为键（不是中文显示标签），覆盖共享生命周期与通用
  进度/风险值，未声明 → `neutral`；导出 `resolveStatusTone(value)` 与
  `resolveCollectionStatusPresentation({value, selection})`。
- 消费方改为单一入口，删除各自的 `toneByValue`：
  `pages/listPage/listCellPresentation.ts`、`utils/semantic.ts`（`statusTone()` 转发）、
  `pages/ListPage.vue`、`pages/KanbanPage.vue`、`views/ActionView.vue`、
  `app/action_runtime/useActionViewCollectionMetricRuntime.ts`、
  `app/action_runtime/useActionViewContractShapeRuntime.ts`。
- 色调依据是**我们自己的每日前端参考快照**（`审批中` = TDesign warning-1 `#FFF1E9`，
  故 `approve → warning`），不是从契约反推。

**(C) 行数锁定统一并降级为非阻断**

- 新增 `scripts/verify/line_budgets.py`：**唯一权威**的行数登记表（17 个受监控文件），
  规则只有一条 `guidance budget = 登记基线 + 统一余量(60)`；未登记文件 fail closed。
- 36 个守卫改为向该登记表取预算；`action_view_responsibility_map_guard`、
  `ui_contract_v2_responsibility_map_guard`、`low_code_workbench_product_guard`、
  `frontend_style_system_guard` 的内联阈值一并收口。
- **超预算不再 FAIL**：改为打印 `[size-advisory] <file> is N lines, M over the ...guidance
  budget; consider splitting before the next structural change`，退出码不变。
  守卫真正的阻断断言（模块归属、split token、禁止依赖）全部保留。
- 新增元守卫 `scripts/verify/file_line_budget_uniform_guard.py`：禁止守卫再次写死数值预算、
  禁止再出现 `line budget exceeded` 这类阻断措辞、校验登记表完整性；已接入 `make/ci.mk`。

**(D) 顺带维护的两处**（均为既有红，非本段引入）

- `action_view_responsibility_map_guard.py`：`runBatchPolicyAction` 已由该视图迁到
  `frontend/apps/web/src/app/action_runtime/useActionViewSelectionActionRuntime.ts`，
  守卫改为断言**新归属模块**持有该职责，并禁止视图内再本地实现（保留原业务断言）。
- `docs/verify/frontend_native_list_alignment_batch_20260430.md`：为其中的
  `tone_by_value` 条款加「已被取代」说明，避免它继续被读成现行规格。

### 3. 未被本段更改的同名落点（已分类登记）

| 落点 | 定性 | 处置 |
| --- | --- | --- |
| `addons/smart_construction_core/services/scene_block_schema.py`（`metric_card(...tone=)`） | **场景呈现载荷**（P1 编排输出），词表已限定 `{success,warning,danger,info,neutral}`，不含业务状态枚举 | 属呈现载体，**不是业务契约越界**，不改 |
| `addons/smart_construction_core/services/insight/project_insight_service.py`（`tone: gentle/ready/ok_to_continue`） | hero 的**语气标记**，与「颜色」只是同名 | 命名债，登记不改 |
| `addons/smart_construction_core/services/project_next_actions_builder.py`（`tone: info/neutral`） | 同上，场景/首页呈现载荷 | 登记不改 |

判断依据：业务契约不得承载呈现，但**编排/首页呈现载荷本身**就是呈现载体的数据格式；
本段要清除的是「业务状态值 → 颜色」被写进业务契约，这三处不属于该路径。

### 4. 边界七问

`Formal Product Layer` = P0 平台内核（契约投影与呈现边界）+ 验收体系（行数口径）；
`Layer Target` = `smart_core.utils.contract_governance*`、`smart_construction_core.core_extension`
声明档案、`frontend/apps/web` 呈现层、`scripts/verify/*`；
`Module` = 契约内核 / 前端呈现 / 验收工具，三类各自归属；
`Standard vs User-Specific` = 平台机制；
`Why Here` = 「什么算业务含义、什么算呈现」是内核与呈现层的通用边界，不属于任何行业或客户；
`Why Not Elsewhere` = **不**把颜色词表留在契约里（内核越界）、**不**在前端按中文标签猜状态
（呈现越界）、**不**靠放宽/忽略守卫消红（把机械约束伪装成通过）；
`Blast Radius` = 列表契约状态列投影、4 个行业 profile、7 个前端消费点、36 个守卫的预算来源、
ci.local.quick 新增一条元守卫；**产品业务规则、校验、动作、权限零改动**。

### 5. 验证（分层）

- L0 身份：开工 HEAD `afdffcd4d` + 显式 dirty scope；收口提交 `0a6cd0a98`（提交后工作区干净，
  `git status --short` 空）；
- L2（本段直接受影响面）：
  - 40 个受影响的 `*_guard.py` 全 PASS（`ran=40 fails=0`）；
  - `python3 -m unittest scripts.verify.test_frontend_dev_incremental` → 13 tests OK
    （`SIZE_LIMITS` / `RECORD_RUNTIME_SIZE_LIMITS` 形状与路由断言保持有效）；
  - `make verify.frontend.collection_status_presentation.unit` → `PASS cases=15`；
  - `make verify.frontend.page_pattern_reference_parity.unit` → parity 15 tests OK +
    ledger 13 tests OK + `PASS entries=67 owned_gaps=20`；
  - `make verify.frontend.typecheck.strict` → `vue-tsc` 两遍均过；
  - 容器内 `test_contract_governance_record_context_registry` → `RAN=21 FAIL=0 ERR=0`；
- **反向注入**（证明新守卫有效，不是空转）：
  - 往守卫写死 `MAX_GOVERNANCE_LINES = 9999` → `file_line_budget_uniform_guard` FAIL；
  - 往守卫塞回 `"line budget exceeded"` → 同上 FAIL；恢复后 PASS；
- 提交后干净态复跑：`make ci.local.iteration` → `PASS change_state=clean coverage=L1_only`；
  41 个受影响守卫 `ran=41 fails=0`；`make verify.guard.registry` → `AUDIT PASS: 1357 scripts
  (1233 referenced, 124/124 orphans acknowledged, 1 retired)`；`make verify.frontend.build`
  → `✓ built in 21.46s`（唯一一次构建；后续未做同源码二次构建或逐文件比对）。
- 未执行：浏览器旅程、全量 Quick（按规则 `ci.local.quick` 只在最终冻结 HEAD 跑一次）、
  100 文件 HTTP 比对。理由：本段无产品渲染逻辑变更，只有呈现层颜色取值来源与验收工具，
  派生产物按既有方式保留。
- 已知与本段无关的既有红：`scripts/verify/frontend_product_design_system_metrics.py` 因克隆
  缺少基线 ref `86f9b29eb…`（`fatal: not a tree object`）无法运行——该脚本只输出指标、
  不设门禁，非本段引入，未扩大处理。

### 6. 提交

- 单笔本地提交：`fix(contract): return the list status tone to the frontend presentation layer and make line budgets advisory`
  （契约去色 + 前端单一色调权威 + 边界守卫双向检查 + `.mjs` 自测接线 + ledger 归属 +
  `line_budgets.py` + 36 个守卫预算收口 + 元守卫 + ci.mk 接线 + 两处文档加注 + 本段记录）。
- **为什么合成一笔**：色调守卫（`contract_governance_list_surface_split_guard.py`）同时承载
  边界断言与预算取数；拆成两笔会让任一笔处于「守卫引用了尚不存在的登记表」或
  「守卫仍写死预算」的临时不一致状态。按职责拆提交不以制造中间坏状态为代价，
  故本段按实际依赖合并提交，不做机械拆分。

### 状态

本段**批次验收完成**（上述范围）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 44｜主线移植（GitHub 恢复）与协作流程接入（2026-09-30）

### 1. 触发与目标

`origin`（GitHub `lidefend/sce-backend-odoo`）恢复可用，`origin/main` 前进到 `fff226d7b`
（PR #524）。本段目标：把本专题分支移植到最新主线继续迭代，并接入主线新增的
**统一执行器续接入口**（`.agent/active-runs.json` + `make agent.run.resume`）以提高迭代效率。
不改变产品行为，不推送、不合并、不部署。

### 2. 移植方式与结果

- 移植前：`HEAD=33c3b553f`，`origin/main=fff226d7b`，本地 `main=23f11f426`（落后 8 个提交）；
- 方式：**merge，不用 rebase**（不改写已交付历史）：`git fetch origin` 后
  `git merge origin/main` → **合并提交 `dc460758c`**；合并前 `23f11f426` 正是本分支直接基点，
  8 个主线提交干净并入，无历史重建；
- 合并后：领先 `origin/main` 196 / 落后 0；工作区干净。

主线新增能力（本分支自此遵循）：

- `AGENTS.md` → **Unified Executor Resume Entry (2026-09-30)**：首次变更前经
  `.agent/active-runs.json` 解析当前分支并跑 `make agent.run.resume`；新任务须先注册
  一个 goal 与 `.agent/runs/<goal-id>/run.json`（此元数据 bootstrap 允许在 resume 通过前完成）；
  续接复用当前 run 与证据索引，只 reconcile 变更过的输入/依赖/环境，**不重复全仓盘点**；
- `make/codex.mk` 新增 `agent.run.resume` / `agent.run.begin` / `agent.run.record` /
  `verify.agent.resume.unit` / `verify.trusted_scan.unit` / `verify.ci.orm_selection.unit`；
- `make ci.local.iteration` 现在先跑 `scripts/ops/agent_run_context.py`，status 非 `resolved`
  即整条入口失败（`outside_scope` 非空也算）；新增
  `config/ci/risk_tiering_v1.json`、`scripts/ci/trusted_scan_scope.py`（增量扫描复用）；
- `ci.local.quick.run` 新增 `python3 -m unittest scripts.verify.test_construction_create_default_hooks`。

**冲突解法（已提交，勿回退）**：`make/ci.mk` 保留双方条目
（`file_line_budget_uniform_guard.py` 与 `test_construction_create_default_hooks`）；
5 个生成型收敛报告取主线版（随后由重生成覆盖为合并后真实值）。

`core_extension.py` 行数算术自洽：base 1807 → 本分支 1830（-23 色调移除，含压缩空行）
→ 主线 1784（+23 create-default 代码）→ **合并 1807**；双方改动位于不同区域，语义无丢失，
`py_compile` 通过。

### 3. 本段实际交付

1. **注册本分支运行记录**（主线新流程要求）：
   - `.agent/goals/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION.yaml`（七问边界 + 约束 + 下一步）；
   - `.agent/runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/run.json`（baseline = 合并提交 `dc460758c`，
     scope 8 条有界目录，3 个离线 check 及显式 inputs）；
   - `.agent/active-runs.json` 增加本分支映射（**不动** 主线自己的 `fix/agent-resume-mainline` 条目）；
   - `make agent.run.resume` → `status=resolved`、`outside_scope=[]`。
2. **重生成漂移的生成型报告**（合并提交导致基线漂移，主线 gate 因此会红）：
   - `make refresh.generated_reports`：`test_inventory.{csv,summary.md}`（1400→1427 资产）、
     `complexity_budget_report.md`、`split_plan_queue.md`（55→57 文件）、
     `e2e_journey_matrix.md`、`module_dependency_map.md`、`github_remote_execution_plan.*`、
     `contracts/generated/contract_structure_fingerprint.json`（内容未变）；
   - `make refresh.contract_form_split_evidence`：`ContractFormPage.vue` 证据行
     1918（主线值）→ **1894（合并后真实值）**，与 `scripts/verify/line_budgets.py`
     登记基线一致；
   - `make refresh.frontend.component_driver_takeover.inventory`：
     `inputDigest` 随合并后前端源码更新（`rendering-surface-ownership` 等源 SHA 同步）。

### 4. 验证（分层，按简化口径）

- L0 身份：开工 `HEAD=dc460758c` 干净；本段提交后工作区干净；
- L1 `make ci.local.iteration` → `PASS change_state=clean coverage=L1_only receipt=none`，
  且 `agent_run_context` 输出 `status=resolved`；
- L1 `make ci.generated_evidence.preflight` → `PASS all content-bound generated evidence is current`
  （含 `tracked generated reports are current`、`split plan queue is current`、
  `contract structure fingerprint is current`、component-driver takeover `required=33 missing=0`、
  `contract_form_split_evidence PASS lines=1894`）；
- L2（**run 内声明并已记账**，`.runtime/agent-runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/*.log`）：
  - `verify.agent.resume.unit` → `Ran 30 tests OK`（`source_head=f0894221b`，status=reusable）；
  - `verify.frontend.collection_status_presentation.unit` → `PASS cases=15`；
  - `verify.frontend.page_pattern_reference_parity.unit` → 15 + 13 tests OK、
    `PASS surfaces=16`、`PASS entries=67 owned_gaps=20`；
- L2 主线新增单测：`verify.ci.orm_selection.unit` OK（14 tests）、
  `verify.trusted_scan.unit` OK（10 tests）、
  `python3 -m unittest scripts.verify.test_construction_create_default_hooks` → `Ran 4 tests OK`；
- L2 段 43 受影响面复跑：`contract_governance_*_split_guard` /
  `construction_core_extension_*_split_guard` / `*_responsibility_map_guard` /
  `file_line_budget_uniform_guard` 共 **`ran=37 fails=0`**
  （行数登记 `registered_files=17 headroom=60 consumers=36 blocking_line_checks=0`）；
- L2 `make verify.frontend.typecheck.strict` → `vue-tsc` 两遍均过；
- L4 一次构建：`make verify.frontend.build` → `✓ built in 21.06s`（唯一一次，无二次构建比对）；
- 未执行（按规则显式跳过）：浏览器旅程（本段无产品渲染/交互变更）、`ci.local.quick`
  （只在最终干净冻结 HEAD 跑一次）、100 文件 HTTP 比对、89 入口、全站发布验收。

### 5. 继承缺口（非本段引入，登记不改）

- `make verify.guard.registry` → `AUDIT FAIL`：`test_construction_create_default_hooks.py` 与
  `test_frontend_v2_policy_projection_guard.py` **未被 registry.yaml 承认**。
  证据：两个脚本在 `origin/main` 已存在，且 `origin/main:scripts/verify/registry.yaml` 同样
  没有这两个条目 → **主线自身即红**，非本分支引入；
  远端必需检查走 `ci.professional.backend.shard-*`，不含 `verify.guard.registry`，
  故不阻断本轮；合并前统一门禁批次再处理（可用 `make guard.registry.seed` 记账）。
- 段 43 已登记的其余欠账（`industry_agnostic.guard` 97 条、`state_transition_undeclared` 5 条、
  z-index 项、`p4_p0_03` 之外的旧产物缺口等）状态不变，本段未扩大处理。

### 6. 提交

- `c230cdb5d` `chore(agent): register the web official template adoption run for mainline resume entry`
- `aa0c9f615` `chore(convergence): refresh generated reports after the mainline port`
- `f0894221b` `chore(agent): include the rendering-detail inventory in the run scope`
- 本段记录（本节）单独一笔随记录文件提交。

### 状态

本段**批次验收完成**（移植 + 协作流程接入 + 生成型证据一致）｜主线未集成｜目标环境未部署｜
整体用户交付未验收。**段 44 曾把下一步写成「FE-TPL-06A → WEB-LC-01」，那是照抄一份过期交接摘要，
与仓库事实不符：这两批在 2026-09-29 已完成并收口（`bb14bff52`、`196bbcd38` 等均为当前 HEAD 的祖先）。
真实下一步见段 45。**
## 段 45｜移植后的候选复位：前端门禁转绿、验收后端重绑、5180 当前候选与 38 项定向浏览器证据（2026-09-30）

### 1. 本段要解决的问题

段 44 完成了主线移植与协作流程接入，但没有检查移植对**前端派生产物**和**运行候选**的影响。
本段把移植后的候选重新恢复到可用、可看、可复核的状态，并纠正段 44 对下一步的误述。

**事实纠正（先说清楚，避免继续误传）**：`FE-TPL-06A`（付款申请标准列表首例）、`WEB-LC-01`（标准列表
配置闭环）、`FE-TPL-07`（按页面类型默认接管、删除三个模型白名单）、`WEB-LC-01B` 均已在
2026-09-29 完成并写进本记录；`bb14bff52`、`196bbcd38`、`9e240dc46`、`fb5934b77`、`d92ebf9c9`
等提交都是当前 HEAD 的祖先（`git merge-base --is-ancestor` 已核）。因此不存在"再去接一次付款列表"
的待办；`standardListComposition.ts` 现在只剩一条 `official-standard-list`，`legacy-list-surface` 已不存在。

### 2. 改了什么

**(A) 前端渲染明细清单过期 → 按既有入口重生成**

`make verify.frontend.quick.gate` 在移植后为红，根因是两条受源码摘要绑定的生成型清单过期：

- `docs/frontend_productization/rendering-detail/component-professionalization-inventory-v1.json`
- `docs/frontend_productization/rendering-detail/visual-projection-inventory-v1.json`

`make refresh.frontend.rendering_detail.inventory` 后 **diff 只有 `sourceIdentity` / `inputDigest` /
逐文件 `digest`，无语义条目增删**（`ListPage.vue` / `ActionView.vue` / `KanbanPage.vue` 因移植而变摘要）。
`official-design-alignment-inventory` 内容不变（`internalVendorSelectorGapCount=0` 保持）。

> 说明：`verify.frontend.rendering_detail_state.unit` 的 unittest 阶段会**故意**打印一行
> `[frontend_official_design_alignment_inventory] FAIL incomplete={'internalVendorSelectorGapCount': 1}`
> 作为反向用例，随后 `--check` 才是真判定（`PASS ...GapCount': 0`）。不要把这行当成红。

**(B) 验收后端容器重绑到当前修订**

容器仍绑定旧修订 `SC_SOURCE_REVISION=26c32476f`，`addons` 与 HEAD 有差异（段 40–43 的契约改动 +
主线 create-default 代码），浏览器候选入口会以 `exit 2` 拒绝。按既有治理入口
`make backend.acceptance.up SC_ACCEPTANCE_RUNTIME_PROFILE=local` 重绑 →
`SC_SOURCE_REVISION=626bac24430731b695f100a5922065e820c85c12`（= 当时 HEAD），容器 healthy。

**(C) 5180 当前候选重建，不新增常驻端口**

`make frontend.standard.preview.build SC_ACCEPTANCE_RUNTIME_PROFILE=local`：
旧候选目录 `config05-20260929` 先以 **`config05-20260929-prev-15351d632`** 保留（不覆盖历史），
再重建到同一路径。新 `build-identity.json`：

- `base_sha = 626bac24430731b695f100a5922065e820c85c12`，`dirty_scope` 空
- 入口 `/assets/index-DTvz9KvJ.js`，`entry_sha256 = a50ea83c…`，`index_sha256 = f05d4244…`

`make frontend.standard.preview.up` → `REUSED current 5180 listener`（pid 802966 未变，`STATIC_ROOT`
指向新产物，代理 `http://127.0.0.1:18082`）。

**(D) 两处受治理文档与已发布决策对齐（不再自相矛盾）**

本段复查时发现两处文档会**把人引回已经废止的做法**，就地修正，不新建治理文档：

1. `docs/frontend_productization/rendering-detail/page-pattern-reference-contract-gaps-v1.md`：
   把 "Collection semantic tones" 从 **P0 contract gaps** 里移出，改为新的
   **"Closed boundary decisions (no longer gaps)"** 段落，写明：状态徽标颜色是呈现决策、
   由前端呈现层唯一拥有，任何契约层和 profile 都不得声明状态→色调映射，
   前端只按**权威状态值**解析（`collectionStatusPresentation.ts`），
   并由 `contract_governance_list_surface_split_guard.py` 双向钉死。
   保留该条是为了防止旧措辞被重新引入——它不是生产侧缺口。
2. `docs/frontend_productization/product-page-patterns-v1.md`：
   - "Adoption switch" 里"解析一个模型、拥有 pilot scope 清单"的描述改为
     **按页面职责解析、不读模型名、不持有 scope 清单**（TPL-07 删除了
     `STANDARD_FORM_COMPOSITION_PILOT_MODELS` 及列表/详情同名机制），
     唯一输入是 `standardPageType.ts`；
   - "Adopted scope" 小节标注为 **historical / superseded**；
   - 采纳表里 "Master-detail handling page … not adopted yet (planned TPL-05)" 更正为
     **已由共享记录表单组合（TPL-05A）+ 页面职责选择（TPL-07）采纳**；
   - 原"付款表单仍是 `legacy-form-section`"的段落标注 **superseded**，并注明当前候选的浏览器
     断言（`payment-master-detail: official form engine mounted`）已经推翻该结论。

### 3. 定向验证

- **L4 浏览器（当前候选）**：`TPL07_SCOPE` 默认全量，
  `make verify.frontend.standard_page_type.browser SC_ACCEPTANCE_RUNTIME_PROFILE=local`
  → `passed assertions=38`，报告
  `artifacts/frontend-web-fix-20260928/tpl07-1790755616473/report.json`，
  `forbiddenWrites=[]`、`errors=[]`、`calls=6`。关键断言：
  付款列表 `standard type` / `one container`、**服务端下一页**（`ids=[1803,1795,1794,1787,1710,33]`）、
  打开记录身份与点击行一致（`openedRecordKey=1803`）、返回上下文与页码集合保持、
  主从页 `official form engine mounted` + 扩展保留、引入契约已发布且无缺口渲染、
  只读页 `readonly mode published`。截图：`payment-list.png`、`payment-master-detail.png`、
  `payment-readonly.png`、`payment-readonly-narrow.png`（390px）等 9 张。
- **L2 采纳单测（移植后的合并树）**：
  - `verify.frontend.standard_form_composition.unit`、`verify.frontend.adopted_form_engine_decision.unit` PASS；
  - `verify.frontend.standard_collection_composition.unit` → `PASS cases=113 scope=page-types`
    （模型白名单删除后，用例由"模型试点"改为"页面职责"）；
  - `verify.frontend.standard_shell_composition.unit` → `PASS cases=71 layouts=1`；
  - `verify.frontend.adopted_form_validation_identity.unit` → `cases=46 failed=0
    engine=shipped-save-chain host=real-vue-instance`，且打印
    `no cross-identity leak observed`；**这是异步身份保护的现成关闭依据**（实现与反例都在真实保存链上），
    按既定口径补记即可，不再重复实现或重开排查；
  - `verify.frontend.standard_preview.unit` → 6 tests OK。
- **L1**：`make ci.local.iteration` PASS（见段 44 记录，本段未改动其输入）。
- 未执行：全量 Quick、发布门禁、89 入口、目标环境验证——本段是本地候选复位，不是发布。

### 4. 剩余缺口（不得夸大，也不得据本段消项）

- **前端已到契约边界**：`page-pattern-reference-detail-ledger-v1.json` 现为
  `entries=67 aligned=46 contract_gap=20 not_applicable=1`，无 `needs_work`。三条列表项
  （`collection.favorite` / `collection.settings-export` / `collection.record-action`）与认证、壳、
  上下文抽屉等其余缺口，`followUp` 都写明是**产品/契约决策**（"按模型决定是否声明显式行动作"、
  "为支持导出的动作声明导出能力"），不是前端可自行消项；按既定边界不猜测补齐。
- 两处受治理文档的过期口径**已在本段 (D) 收口**（色调边界、已删除的模型白名单、
  "付款表单仍未接管"的事实错误）；两条 `PILOT_MODELS` 残留字样只出现在"已被删除/历史"的说明句中。
- 390×844 官方参考截图证据缺口、主线继承的 `verify.guard.registry` 两条 orphan 记账、
  四项 `style_system` 欠账状态均不变。

### 5. 提交

- `626bac244` `chore(convergence): refresh the render-detail inventories after the mainline port`
- `docs(frontend): align the governed reference docs with the shipped tone and page-type decisions`
  （两处文档对齐 + 本段记录）

### 状态

本段**批次验收完成**（候选复位 + 定向补验）｜主线未集成｜目标环境未部署｜整体用户交付未验收。


## 段 46｜主线现状复核 + 守卫登记审计的根因修复：`python3 -m unittest scripts.verify.<mod>` 不再被误判为孤儿（2026-09-30）

### 1. 主线复核（本轮起点）

- GitHub 恢复后实际核对：`origin` = `https://github.com/lidefend/sce-backend-odoo.git`，
  `origin/main` = `fff226d7be72878ea6861cfab2ce13d990cee806`（2026-09-30 15:32，`Merge PR #524`），
  与 `git ls-remote origin main` 一致；`git merge-base HEAD origin/main` = `fff226d7b`，
  即**主线最新提交已在 `dc460758c` 并入本分支，无新增待移植内容**（领先 202 / 落后 0）。
- `gitee-mirror/main` = `23f11f426` 为另一条发布镜像线，`git rev-list --left-right --count
  gitee-mirror/main...HEAD` = `0 210`，已完全包含于本分支；本轮不改动其方向。
- 主线新增协作流程已可用并被本轮实际使用：`make agent.run.resume`（本节）、
  `agent.run.begin AGENT_CHECK=<id>`、`agent.run.record ...`、`verify.agent.resume.unit`。

### 2. 未决项的实际根因（不是"缺登记"，是审计漏识别）

移植后 `make verify.guard.registry` 报两条孤儿：
`test_construction_create_default_hooks.py`、`test_frontend_v2_policy_projection_guard.py`。

复核结论（推翻"只是登记没同步"的判断）：

- 两条脚本**都已被 make 引用**——`make/ci.mk:951`、`make/ci.mk:1099`
  （`python3 -m unittest scripts.verify.test_construction_create_default_hooks`）与
  `make/ci.mk:417`（`python3 -m unittest scripts.verify.test_frontend_v2_policy_projection_guard`）。
- 漏识别根因：`scripts/verify/guard_registry_audit.py` 的引用索引只认两种形态——
  `.py` 文件名字符串（`SCRIPT_REFERENCE_RE`）与 `import/from` 语句（`IMPORT_REFERENCE_RE`）。
  `-m unittest scripts.verify.<module>` 这种**点号模块调用**两种都不匹配，于是真实被测脚本被判孤儿。
- 影响面不止两条：把点号形态纳入识别后，**37 条历史 orphan 登记**（`test_gitee_*`、`test_local_dev_*`、
  `test_frontend_standard_preview.py` 等）实际都被引用，属长期误登记。逐条核对命中来源确为真实引用
  （`make/codex.mk`、`make/ci.mk`、`scripts/verify/test_native_view_capability_taxonomy.py` 等）。

判定：这是**门禁的真实性缺陷**，不是"红项需要消红"。按"门禁检查真实边界、不用放宽阈值或改退出码"的原则，
修审计而不是补假登记。

### 3. 修复内容

- `scripts/verify/guard_registry_audit.py`：
  - 新增 `MODULE_INVOCATION_REFERENCE_RE = \bscripts\.verify\.([A-Za-z_][A-Za-z0-9_]*)\b`；
  - `build_reference_index()` 增加 `module_hits`（返回三元组），`resolve_external_hits()` 接受并合并该索引
    （新增参数带默认值，调用方兼容）；`_reference_patterns()` 增加点号模块形态的正则；
  - 模块文档串同步说明"文件名 / import / `scripts.verify.<module>` 模块调用"三种静态引用形态。
- `scripts/verify/test_guard_registry_audit.py`：既有两例随三元组签名更新，并新增
  `test_resolve_external_hits_matches_module_invocation`（命中 `make/dev.mk`，不命中 `scripts.verify.unrelated`）。
- `scripts/verify/registry.yaml`：`make guard.registry.seed` 丢弃 37 条失效登记，**129 → 92 条**；
  结构化比对确认"仅删除这 37 条，无新增、无字段改动"（`removed=37 added=0 changed=0`）。
- `docs/audit/guard_registry/guard_registry.json`：按既有 `make guard.registry.export` 重生成，
  counts `active 1231 / orphan 124 / retired 1` → `active 1273 / orphan 87 / retired 1`，脚本 1355 → 1360。
- `.agent/runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/run.json`：scope 增加 `docs/audit/guard_registry/`。

### 4. 验证

- **L2（定向，非零）**：`python3 -m unittest scripts.verify.test_guard_registry_audit` → 3 tests OK。
- **L2（审计本体）**：`make verify.guard.registry` →
  `AUDIT PASS: 1360 scripts (1273 referenced, 87/87 orphans acknowledged, 1 retired)`。
- **L1**：`make ci.local.iteration` PASS（`status=resolved`，`outside_scope=[]`）。
  期间观察到主线新流程的实际约束：派生导出件落在 scope 外时 run 状态为 `reconcile`、
  L1 退出码 2（fail closed）；把派生目录正确定位进 scope 后恢复 `resolved`——**这是流程在起作用，
  不是被绕过**。
- 未执行：全量 Quick、发布门禁、89 入口、浏览器旅程（本段只动审计脚本与登记，不影响产品面）。

### 5. 提交

- `fix(guard): recognize module-invocation references in the guard registry audit`
  （审计脚本 + 单测 + registry.yaml + 派生导出件 + run scope）
- `docs(iteration): record 段 46`（本段）

### 6. 剩余缺口与下一步

- 前端采纳仍在**契约边界**：`page-pattern-reference-detail-ledger-v1.json` =
  `entries=67 aligned=46 contract_gap=20 not_applicable=1`。其中 **17 条归 P0 `smart_core`、2 条归 P1
  `smart_construction_core`**，都是"原生事实已有、契约未投影/未声明能力"的**投影缺口**，
  按用户口径"契约不满足就先完善契约"应转为主线工作项：行详情动作、导出能力、收藏归属与可变性、
  复制/删除能力与禁用原因、区块条目计数、上下文抽屉呈现授权等。
- 四项 `style_system` 欠账、合并前门禁批次、390×844 官方参考截图证据缺口不变。

### 状态

本段**批次验收完成**（审计修复 + 登记复位）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 47｜契约侧投影缺口收口（一）：`collection.favorite` 的收藏能力改为按 `ir.filters` 权威判定，不再硬编码 `True`（2026-09-30）

### 1. 主线与运行上下文

- `origin/main`（GitHub 已恢复）经 `git fetch origin main` 复核 = `fff226d7be72878ea6861cfab2ce13d990cee806`
  （`Merge PR #524`），与 `git ls-remote` 一致；`merge-base HEAD origin/main` = `fff226d7b`，
  `git rev-list --left-right --count origin/main...HEAD` = `0 204` → **主线已是本分支祖先，无待移植内容**。
- 主线新协作流程本轮**实际使用**：`make agent.run.resume` 已按 `.agent/active-runs.json` 直接解析
  （`resume=30 / status_presentation=15` reusable；`page_pattern_parity` 因本段 ledger 变更判 `stale`），
  `make agent.run.begin/record` 用于候选取证，`change_state` 与 `outside_scope` 作为 fail-closed 约束。

### 2. 缺口定位（先核对"原生事实是否已有、契约是否只是没投影"）

选中 `collection.favorite`（P0 `smart_core`）。原缺口描述"payload 未一致投影收藏归属与可变性"经查**准确**：

- `addons/smart_core/app_config_engine/models/app_search_config.py` 的
  `_build_custom_search_contract()` 把 `favorites.save_enabled` **无条件写成 `True`**——
  这是模型级 `search_def` 缓存里的**非权威常量**，对任何用户/权限都返回同一结果；
  行内也没有 `owned_by_current_user / writable / deletable`。
- 属**投影缺口**（原生事实在 `ir.filters` ACL + record rule + `check_access_rights` 里已有），
  按用户口径"契约不满足就先完善契约"应由契约侧补投影，而不是让前端猜。

### 3. 修复内容（P0 `smart_core`，唯一权威来源 = Odoo 17 `ir.filters`）

`addons/smart_core/app_config_engine/models/app_search_config.py`：

1. `_build_custom_search_contract()` 静态块：**移除硬编码 `save_enabled: True`**，只声明用户无关的静态语义
   + 保守默认（`owner_scope: "current_user"`、`shared_enabled: False`、`save_enabled: False`），
   避免把用户相关能力写进 model 级 `search_def` 缓存。
2. `get_search_contract()` 先构造 `contract`，再 `return self._project_saved_search_capability(contract, self.model)`。
3. 新增 `_saved_search_save_capability(model_name)`：按 Odoo 17 权威规则判定——
   `base.group_user` 内部用户、目标模型 `check_access_rights("read", raise_exception=False)`、
   `ir.filters.check_access_rights("create", raise_exception=False)`；共享收藏由既有
   `core/search_favorite_policy` 固定 `False`；任何异常 → 保守 `False`（fail closed）。
   `disabled_reason` ∈ {`SAVED_SEARCH_AUTHORITY_UNAVAILABLE`, `SAVED_SEARCH_REQUIRES_INTERNAL_USER`,
   `SAVED_SEARCH_MODEL_UNAVAILABLE`, `SAVED_SEARCH_MODEL_READ_DENIED`, `SAVED_SEARCH_CREATE_DENIED`}，成功为空串。
4. 新增 `_project_saved_filter_mutation_rows(rows, uid)`：用
   `env["ir.filters"].browse(ids)._filter_access_rules("write"/"unlink").ids` **实算**行级可变性，
   归属用 `ir.filters.user_id` 业务身份字段比对 `uid`，判定不了保守 `False`；
   注入 `owned_by_current_user / writable / deletable`。
5. 新增 `_project_saved_search_capability(contract, model_name)` 完成投影（保留静态 `label`/`intent`）。

### 4. 反例与验证（L2 定向，非零）

新增 `addons/smart_core/tests/test_saved_search_capability_projection.py`（**9 tests OK**），
关键是"同一 model 级缓存下不同用户/权限必须得到不同 `save_enabled`"——**常量实现无法同时满足**：

- 内部用户判定；模型 read 拒绝；缺 authority fail-closed；
- 静态保守默认 vs 运行时投影；私收藏行不外泄（仅本人 + 共享）；跨用户行能力拒绝；
- `_filter_access_rules` 异常 fail-closed。

`make/frontend.mk` 新增 `verify.frontend.saved_search_capability.unit`，并纳入 `verify.frontend.quick.gate` prereq。

既有回归同步复核（全绿）：

- `make verify.frontend.saved_search_capability.unit` → 9 tests OK
- `make verify.frontend.page_pattern_reference_parity.unit` → 15 tests OK；`ledger PASS entries=67 owned_gaps=20`
- `make verify.frontend.search_groupby_savedfilters.guard` → PASS
- `python3 addons/smart_core/tests/test_search_favorite_handler_boundaries.py` → 8 tests OK
- `python3 addons/smart_core/tests/test_contract_projection_json_boundaries.py` → 4 tests OK

**真实环境能力判定链只读探针**（`docker exec -i sc-backend-odoo-acceptance ... odoo shell -d sc_frontend_acceptance`）：
`uid=1 internal=True`、`ir_filters_create=True`、`config_found=False`（该库尚无 `app.search.config` 记录）、
`portal_has_users=False`。→ 链路可用，但 `cap=False` 差异场景现场不可观察（无 portal 用户、无配置记录），
已用行为级单测覆盖并**如实记录为环境限制**。

### 5. 文档

`docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json`：
`collection.favorite` 条目更新为**准确剩余状态**（仍 `contract_gap`）——
`authority` 改为 saved search contract（runtime capability from `ir.filters` record rules plus the
`search.favorite.set` write-proxy gate）；`gap` 改为"契约已投影 save 能力与行归属/可变性，
但采纳的 collection surface 尚未渲染该动作，能力暂无消费者"；`followUp` 改为
"在采纳的 list 工具栏搜索菜单暴露该能力并给浏览器证据，或记录差异为 accepted"。
（该文件为 67 行单行 JSON 数组格式，精确替换按整行字符串进行。）

### 6. 提交

- `fix(contract): project saved-search capability from ir.filters authority instead of a constant`
- `docs(iteration): record 段 47`（本段）

### 7. 剩余缺口与下一步

- 前端采纳契约边界现状：`entries=67 aligned=46 contract_gap=20 not_applicable=1`；
  **17 条归 P0 `smart_core`、2 条归 P1 `smart_construction_core`**，均为投影缺口，按序收口：
  行详情动作（`collection.record-action` 需要**通用规则**，不得按模型名硬编码）、
  导出能力（`collection.settings-export`，先核对是行级/工具栏声明缺口还是前端消费缺陷）、
  复制/删除能力与禁用原因（`detail.action-state`）、区块条目计数（`detail.section-heading`）、
  上下文抽屉呈现授权、`detail.primary-tabs`/`secondary-tabs`。
- 保留不并入：四项 `style_system` 欠账、`industry_agnostic.guard` 97 条、
  `state_transition_undeclared` 5 条、390×844 官方参考截图证据缺口、合并前门禁批次。

### 状态

本段**批次验收完成**（契约投影修复 + 定向回归）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 48｜契约侧投影缺口收口（二）：被拒绝的记录操作必须声明「是哪一层拒绝的」，不再让终端自己编理由（2026-09-30）

### 1. 主线与运行上下文

- `git fetch origin main` 复核 = `fff226d7be72878ea6861cfab2ce13d990cee806`（`Merge PR #524`）；
  `merge-base HEAD origin/main` = `fff226d7b`，`git rev-list --left-right --count origin/main...HEAD` = `0 206`
  → **主线仍是本分支祖先，本段无待移植内容**（与段 47 结论一致，主线移植已完成）。
- 主线协作流程本段继续实跑：`make agent.run.begin/record` 记录 `record_denied_reason`(25)、
  `contract_record_action_state`(19)、`page_pattern_parity`(28)；`make agent.run.resume` → `status=resolved`、
  `outside_scope=[]`。
  **本段新增改动路径越出原 scope**（`addons/smart_core/`、`addons/smart_construction_core/`），
  已按 fail-closed 语义先把两路径补进 `.agent/runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/run.json` 的 `scope`，
  再进入实现；否则 `ci.local.iteration` 会判 `reconcile`（退出码 2）。

### 2. 缺口定位（先核对"原生事实是否已有、契约是否只是没投影"）

选中 ledger 条目 `detail.action-state`（`edit/copy/delete reflect explicit capability and disabled reason`）。
原缺口描述"Copy/delete and disabled-reason authority are not consistently present in the current record contract"
经查**部分准确、部分需要修正**：

- **能力本身已投影**：详情契约 `statusContract.globalStatus.effectiveRecordCapabilities`
  在传 `record_id` 时可用（早期探针漏传 `record_id` 导致误读为全 `false`，已修正）。
- **真正的缺口**：任何被拒绝的记录操作**只有一个布尔值，没有权威原因**。
  `statusContract.globalStatus` 原有
  `modelRights/recordRights/viewCapabilities/entryCapabilities/effectiveRecordCapabilities/effectiveRenderProfile`，
  **没有 `recordDeniedReasons`**；终端只能拿 `false` 去猜"是没权限、还是记录不允许、还是状态不允许"——
  这正是"缺少必要业务语义时前端会猜着补"的典型入口。
- **第二个缺口（P1 侧）**：`actionContract.deletePolicy` 已表达**模型级**状态门
  （`policy_kind: state_limited_business_document`、`state_field`、`allowed_states`、
  `reason_code: DRAFT_BUSINESS_DOCUMENT_DELETE_ALLOWED`），但**没有"当前记录状态不允许删除"的拒绝原因**；
  且 `frontend/apps/web/src/pages/ContractFormPage.vue` 的删除权**只读 `rights.unlink`，完全忽略该状态门**——
  `state=signed/confirmed` 的合同在页面上仍被当作"可删除"（属**消费缺陷**）。

### 3. 修复内容（按层落位，前端只做消费）

**P0 `smart_core`——投影"是哪一层拒绝的"（只读事实，不解析异常文本）**

`addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`：

1. 新增 denial 词表常量：`MODEL_ACCESS_DENIED / RECORD_RULE_DENIED / RECORD_NOT_FOUND / RECORD_AUTHORITY_UNRESOLVED`。
2. 新增 `_model_access_allows(env, model, op)`（`check_access_rights(..., raise_exception=False)`）与
   `_record_rule_allows(env, model, record_id, op)`（`browse(id)._filter_access_rules(op)`）——
   **只看 Odoo 自身的判定结果，不看异常文本**。
3. 新增 `_record_rule_denied_reasons(...)`：对每个被拒操作判定 ACL 层 / record-rule 层；
   记录不存在 → `RECORD_NOT_FOUND`；两层都放行但权限仍为假 → `RECORD_AUTHORITY_UNRESOLVED`（不猜）；
   `duplicate` 视为 read+create 并按同一口径归因。
4. 新增 `_record_capability_block(env, model, record_id)` → `{rights, record_id, denied_reason}`，
   两处权限根（原 `:550` 附近与 `:3994` 附近）改为经它产出，保持 `record_id` 既有语义。
5. `addons/smart_core/core/unified_page_contract_v2_assembler.py`：把
   `source.permissions.record.denied_reason` 投影为
   `statusContract.globalStatus.recordDeniedReasons`（**非空才写**，空则不materialize 成空对象）。

**P1 `smart_construction_core`——状态门的拒绝原因由业务声明**

6. `addons/smart_core/utils/delete_policy.py`：新增 `DELETE_POLICY_STATE_DENIED`；
   `_normalize_policy` 透传 `denied_reason_code / denied_message`，并**强制**"声明了
   `allowed_states`/`blocked_states` 却没声明 `denied_reason_code` 的策略自动补
   `DELETE_POLICY_STATE_DENIED`"——状态门带原因成为不可省略的契约形状（没有状态门的策略**不补**，不发明）。
7. `addons/smart_construction_core/core_extension_policy_maps.py`：`_state_unlink_policy` 增加
   `denied_reason_code: BUSINESS_DOCUMENT_STATE_NOT_DELETABLE` 与业务化 `denied_message`
   （"该{业务对象}已形成业务事实，仅未提交状态可删除。"）。

**前端（P0 契约消费，不重造规则）**

8. `frontend/apps/web/src/app/contracts/v2/types.ts` + `schema.ts`：`ContractV2GlobalStatus` 增
   `recordDeniedReasons`，在 `rejectUnknownKeys` 白名单与 `optionalRecord` 解码中登记——
   **仍是 fail-closed**（数组/未声明键照样报错）。
9. `frontend/apps/web/src/app/contracts/v2/store.ts`：`resolveContractV2GlobalStatus` 透传
   `recordDeniedReasons`；新增 `resolveContractV2RecordActionStates(store)`，把
   `effectiveRecordCapabilities` 与 `actionContract.deletePolicy` 的状态门**做与运算**，
   每个操作给出 `{operation, allowed, reasonCode}`；**契约没声明的原因保持空串，绝不编造**。
10. `frontend/apps/web/src/pages/ContractFormPage.vue`：`rights.unlink` 改由
    `resolveContractV2RecordActionStates` 的 `unlink.allowed` 决定，因此**尊重 deletePolicy 声明的状态门**；
    未声明 record 能力时保持全 `false`（fail closed）。

### 4. 反例与验证（L2 定向，非零；读写分离）

**行为级反例（后端，新增 `addons/smart_core/tests/test_record_denied_reason_projection.py`，15 tests OK）**

- ACL 层拒绝 → `MODEL_ACCESS_DENIED`；record rule 拒绝 → `RECORD_RULE_DENIED`；
  记录不存在 → `RECORD_NOT_FOUND`；两层放行却仍为假 → `RECORD_AUTHORITY_UNRESOLVED`。
- **关键反例（常量实现必失败）**：`acl_rights == unresolved_rights`（同一 operation、同一 `False`），
  但归因**必须不同** → 证明原因来自"实际观测到的权威层"，不是常量。
- `duplicate` 跟随 read 权威（ACL 与 record-rule 两种）；`create` **永不**被报成记录级拒绝；
  ACL 权威不可用 → fail closed 到 `MODEL_ACCESS_DENIED`；`record_id ∈ {None,0,"abc",""}` → 不产原因。
- **真实调用链**：直接调 `_assemble_ui_contract` 断言 `recordDeniedReasons` 进入已发布契约、
  允许的记录与无 record 块的契约**都不出现该键**。

**行为级反例（删除策略，新增 `addons/smart_core/tests/test_delete_policy_denied_reason.py`，10 tests OK）**

- 声明状态门未声明原因 → 自动补 `DELETE_POLICY_STATE_DENIED`；
  显式原因保留；无状态门 → **不产生** `denied_reason_code`；空白声明值不当作原因。
- 端到端：P1 策略表经 `resolve_unlink_policy` 后 `payment.request` 得到
  `BUSINESS_DOCUMENT_STATE_NOT_DELETABLE` + 含"付款申请"的业务文案；**未登记模型仍只给模型级
  `DELETE_POLICY_DENIED`，不发明状态原因**。

**行为级反例（前端消费，新增 `scripts/verify/frontend_contract_record_action_state.test.mjs`，19 cases PASS）**

- 解码：`recordDeniedReasons` 保留；未声明键与数组形态**照样 fail closed**；缺省不 materialize。
- 投影：无原因时 `allowed:false` 且 `reasonCode:''`（**不猜**）；有原因时原样透出；
  状态门 `state=approved` → 用声明的 `denied_reason_code`；`state=draft` → 允许；
  `mainData` 没有该状态字段 → **不当作被阻止**；状态门**不外溢**到其他操作；
  策略整体禁止用 `reason_code`；状态门无声明原因 → 拒绝但原因为空；
  `store=null` → 五项全拒且原因为空；已允许操作上出现的陈旧原因不翻转结论。
- 接线：`ContractFormPage.vue` 必须 import 该 resolver，且 `unlink` 必须取自解析结果。

**真实运行环境只读探针**（`sc-backend-odoo-acceptance` → `sc_frontend_acceptance`，日志
`.runtime/agent-runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/logs/record_denied_reason_runtime_probe.log`）：

- P1→P0 链路：`resolve_unlink_policy(env,'sc.general.contract')` →
  `denied_reason_code=BUSINESS_DOCUMENT_STATE_NOT_DELETABLE`、
  `denied_message="该综合合同已形成业务事实，仅未提交状态可删除。"`。
- 归因可区分（同模型不同用户）：`uid=31`（项目成员）→
  `{'read':'RECORD_RULE_DENIED','write':'RECORD_RULE_DENIED','duplicate':'RECORD_RULE_DENIED'}`；
  `uid=1/30/33/37` → `{}`（无拒绝）→ **不是常量**。
- 契约链：`sc.general.contract` 记录 11（`state=confirmed`）经 `UiContractV2Handler` →
  `statusContract.globalStatus.recordDeniedReasons` 为 `uid=31` 时真实发布；
  `effectiveRecordCapabilities` 与 `actionContract.deletePolicy` 的
  `policy_kind/state_field/allowed_states/denied_reason_code` 同时到端。
- **本修复的可观察行为变化**：`uid=1` 对记录 10（`signed`）/11（`confirmed`）的
  `effectiveRecordCapabilities.unlink` 仍为 `true`（ACL 层事实），但删除策略声明的状态门只允许
  `cancel/cancelled/draft` → 页面解析出的删除态由"可删除"变为
  `allowed=false, reasonCode=BUSINESS_DOCUMENT_STATE_NOT_DELETABLE`；记录 12（`draft`）仍可删除。

**受影响的既有门禁（全绿，未新增失败）**

- `make ci.local.iteration` → `PASS change_state=dirty coverage=L1_only`（5 个已登记检查全 reusable）。
- `make verify.frontend.typecheck.strict` → PASS；`make verify.unified_page_contract.v2.frontend_static`（typecheck + 一次构建）→ PASS。
- `verify.unified_page_contract.v2.{schema,guard_inventory,assembler,status,action,data,runtime,client,intent,web_consumer,web_architecture,stable_projection}` → 全 PASS。
- `verify.frontend.style_system.guard` → **PASS**（`hardcoded_color_refs_max=0`）；
  `verify.frontend.delivery_hardening.guard`、`verify.frontend.search_groupby_savedfilters.guard`、
  `verify.contract.operation_gateway.guard`、`verify.list_batch_action.closure_guard` → PASS。
- `make verify.frontend.page_pattern_reference_parity.unit` → 15 + 13 tests OK；
  `[page_pattern_reference_ledger_guard] PASS entries=67 owned_gaps=20`。

**守卫按设计拦住本段新增面（真 fail closed，未放宽门禁）**

`verify.unified_page_contract.v2.stable_projection` 先报
`frontend_v2_policy_projection_guard` FAIL：`store.ts` 新读入的 6 个 snake_case 契约键
（`allowed_states/denied_reason_code/policy_kind/reason_code/state_field/state_limited_business_document`）
不在白名单。处理方式不是放宽，而是**把白名单绑定到真实生产者**：新增
`ALLOWED_STRICT_STORE_DELETE_POLICY_TOKENS` + `DELETE_POLICY_PRODUCERS`，
逐个断言这些键必须由 `smart_core.utils.delete_policy` 或
`smart_construction_core.core_extension_policy_maps` **真实声明**，并补负例单测
（`test_delete_policy_token_must_have_a_backend_producer`）→ 4 tests OK，白名单无法漂移成"发明的别名"。

**已存在且与本段无关的失败（如实登记，不顺手修）**

`make verify.user_delete_data.closure_guard` FAIL 三条：
"ActionView batch delete must preflight with dryRun" / "…must still execute real unlink after preflight" /
"ActionView batch policy must fall back to surface policy when list_profile has no executable actions"。
证据：该守卫读取的 `ActionView.vue` / `ListPage.vue` / `api/data.ts` /
`actionViewBatchActionFlowRuntime.ts` / `useActionViewContractShapeRuntime.ts` /
`ui_contract_v2_projection.py` **在本段 diff 中为空**，`ActionView.vue` 当前也确实不含 `dryRun: true`
→ 属**先前既有**的守卫期望漂移，独立保留。

### 5. 文档

`docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json`
（67 行单行 JSON 数组，精确替换按整行字符串）：

`detail.action-state` 条目 `authority` 改为"`statusContract.globalStatus.effectiveRecordCapabilities`
+ 指明拒绝层的 `recordDeniedReasons` + `actionContract.deletePolicy` 状态门及其 `denied_reason_code`"；
`gap` 改为**准确剩余状态**——契约侧（能力 + 拒绝层 + 状态门 + 业务拒绝原因）与
表单页删除权消费均已到位，**仍缺的是只读详情面把声明的禁用原因呈现给操作者、以及
`duplicate` 能力在该面的可用入口**；`followUp` 相应改为
"在采纳的 readonly-detail 面渲染声明的禁用原因并在契约声明 `duplicate` 时提供复制入口，
或把该 reference 差异记录为 accepted"。状态仍为 `contract_gap`（未宣称超前）。

### 6. 提交

- `fix(contract): declare the authority that denied a record operation`
- `docs(iteration): record 段 48`（本段）

### 7. 剩余缺口与下一步

- 前端采纳契约边界现状不变：`entries=67 aligned=46 contract_gap=20 not_applicable=1`
  （**17 条 P0 `smart_core`、2 条 P1 `smart_construction_core`**）。本段关闭其中
  `detail.action-state` 的**契约侧**部分，剩余为只读详情面的呈现消费。
- 仍待收口的 P0 投影缺口（按序）：`collection.record-action`（行详情动作需要**通用规则**，
  不得按模型名硬编码；付款列表实测已含 `action.open_form`，需据实判断剩余是行级/工具栏声明还是消费）、
  `collection.settings-export`（`batch_policy.available_actions` 已含 `export`，同上）、
  `detail.section-heading`（区块条目计数）、上下文抽屉呈现授权一族
  （`detail.container/header/primary-tabs/secondary-tabs/description-grid/loading-skeleton`）、
  `login.*`、`shell.global-search`、`shell.footer-version`。
- 事实更正：段 47 曾把"四项 `style_system` 欠账"列为待独立处理，本段实测
  `make verify.frontend.style_system.guard` **PASS**（该项已不再失败）；`industry_agnostic.guard` 97 条、
  `state_transition_undeclared` 5 条、390×844 官方参考截图证据缺口仍独立保留。
- `user_delete_data.closure_guard` 的 3 条既有失败（见 §4）独立保留，作为合并前清理批次的输入。

### 状态

本段**批次验收完成**（契约投影修复 + 定向回归 + 真实环境只读证据）｜主线未集成｜目标环境未部署｜整体用户交付未验收。

## 段 49｜把"能静默失效的守卫"修回来：批量删除预检门的定位漂移、按序列重绑与自证伪（2026-09-30）

### 1. 主线与运行上下文

- 分支 `feature/web-official-template-adoption`，开工 HEAD `6cf886bcb`、工作区 clean。
- 主线移植**已完成且无需再动**：`origin/main = fff226d7b`（`Merge PR #524`，2026-09-30 15:32 +0800）
  已是本分支祖先（`git rev-list --left-right --count origin/main...HEAD` = `0 208`），
  且含本轮要复用的协作流程提交 `81788ca9a`（统一 agent resume 与增量证据复用）、
  `8b44ce536`（跨登记工作树复用已校验的主线扫描）、`b6ea04f0d`（按运行影响选择 ORM 校验）。
- 协作流程按主线新规范消费：`make agent.run.resume` 直接解析本分支唯一 run（不再全量扫描 goals）；
  检查按 `make agent.run.begin` → 执行 → `make agent.run.record` 留回执。
- Formal Product Layer：P0（平台内核的**验收工具**与通用前端消费契约）/ P4（执行与证据机制）。
  Layer Target：`scripts/verify` 的删除数据闭包守卫、对应 Make 入口、`.agent/runs` 检查声明。
  Module：`scripts/verify`、`make`、`.agent`。Standard vs User-Specific：通用工程机制，不含行业或客户语义。
  Why Here：守卫定位方式与自证伪属于平台工程机制。Why Not Elsewhere：不向产品契约、前端呈现或数据库加入规则。
  Blast Radius：一个前端写路径守卫的**可证伪性**；不改任何前端/后端产品行为、不放宽门禁、不写数据库。

### 2. 先定性：这是产品缺陷还是守卫漂移？

段 48 §4 把 `make verify.user_delete_data.closure_guard` 的 3 条失败记为"先前既有的守卫期望漂移"独立保留。
本段按要求"对照实际专题基线判断，不凭'当前 HEAD 也会失败'就认定无关"，沿真实调用链核对**行为**：

| 守卫断言 | 当前代码事实 | 定性 |
| --- | --- | --- |
| `ActionView.vue` 必须含 `dryRun: true` | 该调用已迁至 `app/action_runtime/useActionViewSelectionActionRuntime.ts` | **定位漂移** |
| `ActionView.vue` 必须含 `const result = await unlinkActionViewRecord` | 同上 | **定位漂移** |
| `ActionView.vue` 必须含 `resolveUnifiedPageContractV2SurfacePolicies(actionContract.value)` | 页面现持**归一化 store**，调用 `resolveContractV2SurfacePolicies`；语义相同，解析入口不同 | **符号漂移** |

行为链核对（`useActionViewSelectionActionRuntime.ts`）：`resolveBatchActionGuardDecision` 前置校验
→ 删除二次确认 → `resolveBatchDeleteExecutionSeed` 产出**两个不同**幂等键
（`delete.dry_run` 与 `delete`）→ `await unlinkActionViewRecord({ dryRun: true, idempotencyKey: seed.dryRunIdempotencyKey })`
→ `const result = await unlinkActionViewRecord({ idempotencyKey: seed.idempotencyKey })`，两者同一 `try`，
`catch` 内**不再发出**真实删除。后端 `api_data_unlink.py` 在 `dry_run` 下仍执行
`_check_record_delete_policy` + `check_access_rights("unlink")` + `check_access_rule("unlink")`，仅跳过 `recs.unlink()`。

结论：**产品行为正确、预检确实在闸住真实写入**；失败的只是守卫的定位方式。
但更严重的问题在定性之外——**该门禁已经停止证明任何东西**：
它盯着的文件里不再有这些调用点，因此"预检被删掉"与"代码被搬迁"在守卫看来完全一样。
这正是"验收体系为什么没有发现偏差"的同一类缺口，必须补。

### 3. 修复：按序列重绑，并让守卫自证伪

`scripts/verify/user_delete_data_closure_guard.py::_probe_frontend_delete_flow`：

- 改为读**拥有该流程的模块** `useActionViewSelectionActionRuntime.ts`，断言从"某文件里有某个字符串"
  升级为**业务序列**：
  1. `dryRun: true` 预检必须存在；
  2. 真实 `const result = await unlinkActionViewRecord` 必须存在；
  3. **预检必须排在真实写入之前**（`preflight_at < destructive_at`）；
  4. 两次调用必须使用**不同**幂等键（`seed.dryRunIdempotencyKey` vs `seed.idempotencyKey`）；
  5. 预检与真实写入之间**不得**出现 `catch`/`finally`（否则失败可能被吞掉后继续写）；
  6. `ActionView.vue` 必须**委派**给 `useActionViewSelectionActionRuntime` 且**不得**出现
     `await unlinkActionViewRecord`（禁止页面长出第二条删除路径）。
- 契约面策略回退改为**顺序断言**：`list_profile.batch_policy` 优先、`SurfacePolicies(actionContract.value)`
  兜底，且 `list_profile_at < surface_policy_at`；同时保留"空 `available_actions` 视为未声明可执行动作"。
- `_probe_frontend_delete_flow(errors, read=_read)` 增加可注入 reader，使守卫可被无容器自证伪。

新增 `scripts/verify/test_user_delete_data_closure_guard.py`（8 项）：
对**真实出厂源码**断言守卫成立（绑定测试），再用受控源码逐一证明守卫仍可被证伪——
删预检、删真实写入、**颠倒顺序**、预检后插 `catch`、两次调用共用幂等键、去掉契约面策略回退、
页面新增第二条删除路径，七种都必须被拒。
新入口 `make verify.user_delete_data.closure_guard.self_test`（`make/dev_test.mk`）。

登记：`docs/audit/guard_registry/guard_registry.json` 按既有生成方式
（`make guard.registry.export`）刷新，`make verify.guard.registry` → **AUDIT PASS: 1361 scripts
（1274 referenced, 87/87 orphans acknowledged, 1 retired）**。
同次导出顺带收敛了此前未重导的登记行数（`frontend_v2_policy_projection_guard.py` 795→827 等），
属生成物追平，非本次改动范围扩大。

### 4. 定向验证

L0：分支/HEAD/工作区已记录，开工 clean。L1：`make ci.local.iteration` PASS（scope=dirty，L1-only）。
L2（非零，逐项留原始日志于 `.runtime/agent-runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/`）：

| 目标 | 结果 | 计数 |
| --- | --- | --- |
| `verify.user_delete_data.closure_guard` | PASS | —（守卫本体） |
| `verify.user_delete_data.closure_guard.self_test` | PASS | 8 |
| `verify.guard.registry` | PASS | 1（AUDIT PASS，1361 scripts） |
| `verify.frontend.style_system.guard` | PASS | `hardcoded_color_refs_max=0` |

`make agent.run.resume`：7 项检查全部 `reusable`（`resume` 30 / `status_presentation` 15 /
`page_pattern_parity` 28 / `record_denied_reason` 25 / `contract_record_action_state` 19 /
`user_delete_guard` 8 / `guard_registry` 1），`blockers=[]`。
L3/L4：本次只改守卫/工具/生成登记，未改前端或后端产品代码、未改运行环境
→ 数据库、浏览器与服务目录**不适用**，不重跑构建与业务旅程（按影响分析，非跳过真实失败）。
L5：未推送、未合并，远端门禁不在本段范围。

### 5. 边界与剩余

- **不改产品代码**去迎合旧选择器：前端与后端删除链一行未动；修的是守卫的定位方式与可证伪性。
- 段 48 §4 的"独立保留"到此**关闭**：三条失败经定性为守卫漂移并已修复，不再是合并前清理批次的输入。
- 真正独立保留的项不变：`industry_agnostic.guard` 97 条、`state_transition_undeclared` 5 条、
  390×844 官方参考截图证据缺口、`style_system` 历史记账（本段实测已 PASS）。
- 契约 ledger 现状不变：`entries=67 aligned=46 contract_gap=20 not_applicable=1`；
  下一步仍按段 48 §7 的顺序收口 P0 投影缺口。

### 提交

- `fix(guard): bind the batch-delete preflight gate to the module that owns the flow`（守卫 + 自检 + Make + 登记）

### 状态

本段**批次验收完成**（守卫修复 + 自证伪回归）｜主线已并入（`fff226d7b` 为祖先，无待移植提交）｜
目标环境未部署｜整体用户交付未验收。

## 段 50｜行激活身份回到契约声明的行位：`targetScope` 不再冒充行级动作，并把"守卫只验字面量"这个缺口一起补上（2026-09-30）

### 0. 主线移植状态（本段开工前先确认，不重复劳动）

- `origin/main = fff226d7b`（Merge PR #524）**已是本分支祖先**：
  `git rev-list --left-right --count origin/main...HEAD` = `0 210`。
  `git fetch` 后未出现新主线提交 → **无需移植、无需再动**。
- 主线协作流程优化已在祖先链上并被本段直接消费：`81788ca9a`（统一 agent resume + 增量证据复用）、
  `8b44ce536`（跨登记工作树复用主线扫描）、`b6ea04f0d`（按运行影响选择 ORM 校验）。
  本段按 `make agent.run.begin` → 执行 → `make agent.run.record` 留回执，未再全量扫 goals。
- 开工 HEAD `ec268dee0`，工作区干净。

### 1. 本段目标与边界

段 48 §7 定的顺序是"先 `collection.record-action`、再 `collection.settings-export`"。
本段的目标不是"再实现一个行级动作"，而是把这条**契约缺口按真实事实核清并收口**：

| 对象 | 本段结论 | 依据 |
| --- | --- | --- |
| `collection.record-action` | 台账原文**已过期**；同时发现一个真实前端身份缺陷 | 受管环境 120 个列表契约实测 |
| `collection.settings-export` | 台账原文**已过期**（能力已声明且已被消费） | 三个入口契约实测 + 前端消费链 |

边界：不改业务动作、不改后端投影、不改外壳；只修"前端用错身份信号"这一处消费缺陷，
并把因此失灵的守卫换回**能真的验到东西**的检查。

七问：`Formal Product Layer = P0 platform kernel product`｜`Layer Target = frontend renderer /
action runtime + smart_core contract V2 action contract`｜`Module = smart_core`（契约侧只读）+
`frontend/apps/web`｜`Standard vs User-Specific = platform mechanism`（行位声明是契约通用能力，
不属于某个模型/客户）｜`Why Here = 行位身份由契约的 sourceWidgetId 声明，消费方就是导航运行时`｜
`Why Not Elsewhere = 不改后端投影去迎合前端、不在页面按模型名补规则`｜
`Blast Radius = 列表行点击的目标解析 + 一个前端守卫 + 两条台账文字`。

### 2. 用真实契约核清两条台账（推翻过期表述）

只读探针 `odoo shell -d sc_frontend_acceptance`（`UiContractV2Handler`，`record_id` 非必需）：

**行级动作声明（`actionRuleList`）** —— 三个采样入口：

| action_id | 模型 | 行级动作 | 行位 | 表头/根动作 |
| --- | --- | --- | --- | --- |
| 675 | `payment.request` | `action.open_form`（`view_type=form`） | `page.row` | 10 条 `page.header` |
| 673 | `sc.general.contract` | `action.open_form`（`view_type=form`） | `page.row` | 5 条 `page.header` |
| 348 | `project.project` | `action.action_view_tasks.2` | `page.row` | 15 条 `page.header`/`page.root` |

扩样到 **60 个真实列表契约**：**60/60 都声明了 `page.row` 行级动作**，且
**60/60 的行级动作都带非空 `label`**。故台账原文
"Some current collections only declare row activation and do not provide an explicit labelled detail action"
**不成立**（`action.open_form` 本身即"带标签的详情动作声明"，`target.view_type="form"`）。

**导出能力** —— 三个入口均声明（`layoutContract.listProfile.batch_policy` 与
`actionContract.surfacePolicies.batch_policy` 双处）：

```
batch_policy.available_actions            = ["export"]
batch_policy.execution_intents.export     = "api.data"
batch_policy.execution_operations.export  = "export_csv"
```

前端确有消费：`useActionViewSelectionActionRuntime` 的 `resolveSelectionActions(...)` 从
`available_actions` + `execution_intents` 映射执行器，`action === 'export'` 分支调用
`executeActionViewSelectionExport`。故 `collection.settings-export` 的
"the current action does not declare export capability" **不成立**。

### 3. 顺带定位到的真实产品缺陷：行级身份用错信号

`useActionViewNavigationRuntime.ts::resolveRowOpenAction()` 原判定为三者取或：

```ts
triggerType === 'row_click'  ||  sourceWidgetId === 'page.row'  ||  targetScope === 'page'
```

两个分支都站不住：

1. `triggerType === 'row_click'` **永不可能成立**：后端 `normalize_trigger_type`
   （`core/unified_page_contract_v2_action.py:75`）把 `row_click` 归一为 `click`，前端
   `decodeTriggerType` 也只接受闭合词表 → 解码后的契约里不存在该字面量。
2. `targetScope === 'page'` **过宽**：后端 `normalize_target_scope`（同文件 `:92`）的文档明确写
   "Native action placement values such as header, toolbar, smart and row are presentation facts.
   They must never leak into the closed V2 target-scope vocabulary"，而表头动作的实际
   `target_scope` 默认值就是"row"→被归一成 `page`。于是**表头动作也满足该分支**，
   而 `actionRuleList` 里表头动作排在行级动作**之前**（`_append_ui_contract_actions` 早于
   `_append_actions(..., source_widget_id="page.row")`）→ `.find()` 会先命中表头动作。

本源可追：`c0a6e9e2c` 把该分支从 `'row'` 改成 `'page'`（因为归一化把它变成了 `page`），
从此行级判定就失去意义。

**实际影响面（据实说明，不夸大）**：对 120 个列表契约做"命中位置是否携带可用跳转目标"的
模拟统计 → **120/120 命中位置都不可跳转**（表头动作 `target` 基本为 `{}`），随后走既有兜底
`buildActionViewRowClickTarget`，**因此当前没有可见的用户故障**。但身份规则是错的：
一旦某个表头动作携带 `route`/`entry_target`/`record_entry`，行点击就会跳到表头动作的目标。
属于**latent 缺陷 + 可复现反例**，不是"看起来能用就不用修"。

### 4. 修复

**产品代码（唯一改动点）**：`frontend/apps/web/src/app/action_runtime/useActionViewNavigationRuntime.ts`

- 新增 `ROW_PLACEMENT_WIDGET_ID = 'page.row'` 与 `isRowPlacementAction(action)`，
  行级判定**只认契约声明的行位** `sourceWidgetId === 'page.row'`；
- 删除 `targetScope === 'page'` 兜底与已失效的 `row_click` 字面量；
- 保留原结构（无行级声明时返回 `undefined`，由既有兜底路径处理，不按模型名猜）；
- 注释写明"为什么不能用 `targetScope`/`row_click` 推断行位"及其后端依据。

**验收体系缺口（本段重点）**：`scripts/verify/web_unified_page_contract_v2_guard.py` 原来只断言
`"resolveContractV2ActionRules" in nav_source or "row_click" in nav_source` —— 它**只验字面量是否出现**，
所以"把行位判定删掉、换成 targetScope"这种退化它根本看不见（`row_click` 在旧实现里一直存在，
在正确实现里反而消失）。这属于与段 49 同类的"守卫在盯不存在的证据"。

改为 `check_row_activation_identity(nav_source, errors)`：

1. 必须消费 `resolveContractV2ActionRules`（仍来自 v2 列表契约）；
2. 必须存在行位声明 `sourceWidgetId` + `page.row`；
3. **不得出现 `targetScope`**（禁止再用 target scope 推断行位）；
4. **不得出现 `row_click`**（不得回头检已退役触发器）；
5. 判定前先 `strip_js_comments()` 剥离注释 —— 否则我自己写的说明注释会让守卫假阳/假阴，
   正对应"不要把说明文字当作越界证据"。

新增 `scripts/verify/test_web_unified_page_contract_v2_guard_row_identity.py`（**6 项**）：
出厂源码必须通过，再加受控变异逐一证明守卫仍可被证伪 —— 用 `targetScope` 推断行位、
把常量退回 `row_click`、去掉行位比较、不消费 v2 动作规则、以及**只用注释写规则**，五种都必须被拒。

新增前端行为级定向测试
`frontend/apps/web/scripts/collection_row_action_identity_test.ts`（**6 项**，真实执行生产函数）：
- `isRowPlacementAction` 对 `page.header` / `page.row` / `null` / 空白的判定；
- **缺陷反例**：表头动作带 `route:/f/other.model/999` 且排在行级动作之前时，行点击**不得**
  继承表头目标，必须落到被点击记录（修复前实测会跳到 `/f/other.model/999`）；
- 行级动作自己声明的 `route` 仍被尊重并做行值物化（`menu_id`/`action_id` 保持）；
- 只有表头动作时**不得**解析出行级动作（fail-closed）；
- `viewType` 非集合视图时不解析行级动作。

入口：`make verify.frontend.collection_row_action_identity.unit`（`make/frontend.mk`），
并纳入 `.PHONY`、`verify.frontend.quick.gate`、`verify.frontend.pr.unit`、`verify.frontend.release.unit`；
守卫自检纳入 `make/ci.mk` 的 `verify.unified_page_contract.v2.web_consumer` 与
`verify.workflow_contract.frontend`。

### 5. 台账按事实更新（不是"为过守卫"删条目）

- `page-pattern-reference-detail-ledger-v1.json`：
  `collection.settings-export` 与 `collection.record-action` 由 `contract_gap` 改为 `aligned`，
  并各带 `resolution` 说明关闭依据与实测口径；`owned_gaps 20 → 18`（守卫 PASS entries=67）。
- `page-pattern-reference-contract-gaps-v1.md`：把两条已关闭结论移入
  "Closed boundary decisions (no longer gaps)"（沿用该文件既有先例），
  并把仍在开放的部分（copy/delete 的 disabled reason、view-switch/settings 的 capability-bound 规则）
  收窄保留，不趁机重开新缺口。

### 6. 定向验证

L0：`origin/main` 关系已核（`0 210`），HEAD `ec268dee0`，开工 clean。
L1：`make ci.local.iteration` PASS（`change_state=dirty`，L1-only，`scopeSource=.agent/runs/.../run.json`；
未分类路径按设计不阻断）。
L2（非零，逐项原始日志在 `.runtime/agent-runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/`）：

| 检查 | 结果 | 计数 |
| --- | --- | --- |
| `resume`（`verify.agent.resume.unit`） | PASS | 30 |
| `row_action_identity`（新） | PASS | 6 |
| `page_pattern_parity` | PASS | 28（15+13） |
| `record_denied_reason` | PASS | 25（10+15） |
| `contract_record_action_state` | PASS | 19 |
| `guard_registry` | PASS | 1（AUDIT PASS: 1362 scripts / 1275 referenced / 87/87 orphans / 1 retired） |
| `status_presentation`（复用） | reusable | 15 |
| `user_delete_guard`（复用） | reusable | 8 |

另跑：`make verify.frontend.typecheck.strict` PASS；
`make verify.frontend.style_system.guard` PASS（`hardcoded_color_refs_max=0`）；
`make verify.unified_page_contract.v2.web_consumer` PASS；
`make verify.workflow_contract.frontend` PASS（含 `verify.frontend.build` 一次最终构建）。

`make agent.run.resume`：**8/8 reusable，`blockers=[]`，`outside_scope=[]`**。
`make guard.registry.export` 已刷新登记（新增脚本计入 `active`）。
L3/L4：本段未改后端业务代码、未改运行环境、未改数据库 → 模块升级/夹具/数据库**不适用**；
浏览器旅程不在本段目标内（行点击目标解析已由行为级单测 + 真实契约探针覆盖），按影响分析记录而非跳过真实失败。
L5：未推送、未合并、未部署。

### 7. 剩余

- 台账剩余缺口不变：`entries=67 aligned=48 contract_gap=18 not_applicable=1`
  （17 条 P0、1 条 evidence 归属等），下一步仍按段 48 §7 顺序，优先
  `detail.section-heading`、上下文抽屉呈现授权一族，以及 `detail.action-state` 的
  copy/delete disabled-reason 呈现。
- 真正独立保留项不变：`industry_agnostic.guard`、`state_transition_undeclared`、
  390×844 官方参考截图证据缺口、合并前必要门禁批次。
- 本段未触碰 `style_system.guard` 四项历史记账（实测仍 PASS）。

### 提交

- `fix(web): resolve row activation from the declared row placement`（产品修复 + 定向单测 + 守卫与自检 + Make + 登记导出）
- `docs(iteration): record 段 50`（台账、缺口文档、专题记录、run.json）

### 状态

本段**批次验收完成**（行位身份修复 + 守卫可证伪 + 台账据实更新）｜主线已并入
（`fff226d7b` 为祖先，无待移植提交；`0 210`）｜目标环境未部署｜整体用户交付未验收。


## 52. 官方模板共享样式收口（2026-09-30，进行中）

- 起点：`510a37d5f784b36f1e1ad4d7d02dbd1331f673f5`，接管时 clean；以下实施阶段显式 dirty，不作冻结候选。
- P0 / frontend tokens and shared presentation；平台通用样式，不属于 P1 行业、P2 客户或 P3 配置规则；不修改业务契约。P4 仅在现有验收工具确需补充定向探针时介入。
- 裁决：外壳标题 18px/600/26px；Inter 优先为产品有意差异；兼容别名集中修复并登记退出条件，中心调用采用规范语义名。
- 顺序：断链 token → 外壳/弹层标题 → 共享页面族 → 既有台账按实际证据更新。ProductPageHeader 的等价官方 24/600/32 保持不变。
- 验证从 L1 静态开始，L2 token 非零测试及相关呈现守卫，稳定后受管 5180 候选和双视口；复用 18082 验收库及原 fixture 权威，不新增数据。L3 ORM/模块升级跳过（无后端或数据库变化）；全业务矩阵、Quick、远端与目标部署跳过（本轮仅本地呈现批次）。
- 旧 run 基线 dc460758 的合同检查回执保留，样式阶段基线更新为 510a37d5f；未变合同输入不重跑。旧 next-step 已被本次明确授权替代。

### 52.1 断链修复实施

- semantic/component 兼容族集中补齐，每族附最后消费者退出条件；额外发现并修复 8 个 pre-v1 旧名，作用域 scene 变量不冒充全局缺失。浅/深 disabled 使用既有调色板引用，生成四份 dist。
- placeholder 桥接 secondary → muted；对应 primitive guard 的旧 marker 同步纠正。NativeFormTreeRenderer 原有直接厂商 token 引用违反桥接边界，改用等价共享角色，官方字体定义仍只在 theme.css 消费。
- L1 `make ci.local.iteration` passed；token build/verify passed；token 构建单测 5/5；style_system.guard、contract_consumer_intrusion.guard、typecheck.strict passed。日志 `/tmp/tpl52-iteration.log`、`/tmp/tpl52-tokens.log`、`/tmp/tpl52-static.log`。
- primitive adapter 初次失败原因为守卫锁定旧 placeholder 映射，修复后 11 个事件案例及 34 个 Python 测试通过；最终回执待共享样式稳定后登记。首次 begin 的任意命令/依赖目录符号链接均被工具拒绝，已改用注册 Make target 和源码依赖范围，未绕过检查。
- 运行时断链检查与下一批标题双视口共用一次候选构建；本节为代码提交，浏览器验收仍 pending，不提前宣称批次通过。

### 52.2 标题梯队与真实双视口

- 外壳及 compact/mobile 标题规则统一 title-large；ScDialog/ScDrawer 标题统一 title-medium，副标题 body-small；caption/xs 兼容别名完成。ProductPageHeader 保持守卫锁定值。
- 定向检查：primitive adapter 11 事件 + 34 单测，ProductPageHeader 70 单测及适配器契约、style_system 均 passed。`agent.run.begin/record` primitive_adapter 已登记 45 非零案例，日志 `artifacts/frontend-web-fix-20260928/tpl52/headings.log`。
- 单次受管构建 21.85s，复用 5180 监听，入口 `/assets/index--AkVL68O.js`；候选 base `66d4386bc` + 显式样式 dirty 范围。原 510a37 候选保留 `sce-offrepo/artifacts/config05-20260929-prev-510a37d5f-tpl52`。
- 既有浏览器工具增加 `TPL07_SCOPE=style`，真实 login/system.init + 有效合同读取，1440×900、390×844 付款列表/表单/详情/引入弹层，无业务写入，58/58 passed。报告 `artifacts/frontend-web-fix-20260928/tpl07-1790764766851/report.json`。全局兼容 token 链在实际 CSS 中全部解析，placeholder=muted，弹层标题 16/600/24；两视口无整页横向溢出。
- 第一次探针错误地要求普通列表出现外壳 headline（该页依法由内容区标题负责，外壳不渲染）；已修正探针为实际内容标题 24/600/32，另测 title-large 角色 18/600/26。仅探针变化，复用同一构建，未重建。失败报告 `tpl07-1790764734192/report.json` 保留。
- 图像复核覆盖窄屏弹层及列表；官方只读基线仍为 aeed5707，已有官方双视口原图复用，不新增演示业务数据。抽屉标题与弹层共享改动，但上下文抽屉的业务契约缺口未因此关闭。

### 52.3 页面族：外壳

- 导航/上下文/标签/账户等文字采用官方 body-small/body-medium、mark 与 title-medium 共享角色；品牌图形和关闭图标尺寸保留为几何用途。补充 mark/headline 桥接角色供后续共享族消费。
- navigation_shell 单测 19 个及组件契约通过，style_system passed（`tpl52/shell.log`）；一次构建 22.27s。
- `TPL07_SCOPE=style TPL52_FAMILY=shell` 两视口 18/18 passed，报告 `artifacts/frontend-web-fix-20260928/tpl07-1790764883387/report.json`。未重跑付款业务办理；沿用前批 modal/合同结果。

### 52.4 页面族：列表共享部件

- 行/移动记录/分组/汇总/看板/分页的文字统一消费官方梯队；收藏星形等图标几何以及隐藏选择器 font-size:0 保持。列标题 14/600/22，移动记录身份 16/600/24。
- standard_collection_composition 113 案例 + style_system passed；一次构建。定向双视口 28/28 passed，报告 `artifacts/frontend-web-fix-20260928/tpl07-1790765049108/report.json`。
- 首次探针依赖当前契约未采用的 status-badge 单元格类型而超时；改为当前实际列标题和移动身份，复用构建，失败报告 `tpl07-1790764971580/report.json` 保留。不据此宣称未展示的看板/分组数据已做业务验收。
- 所有者再次明确：本轮完整目标是全系统契约驱动的官方渲染/交互，样式修复只是基础批次；后续仍按既有页面类型核对唯一组合及旧职责退出，不能以字号修复代替整体接管。

### 52.5 页面族：详情、表单、任务共享渲染与弹层正文

- FormSection / NativeFormTreeRenderer / ContractFormPage 共享文字角色统一：区块 title-medium、记录 headline-small、正文 body-medium、辅助 body-small；readonly value 不再使用 550 字重。任务 monetary 强调保留，字体采用 title-large。记录标题输入桥接采用 headline-small。
- 付款引入领域扩展保留全部业务输入/输出与动作，只更新呈现字体；同时纠正 ListPage 父级覆盖，防止共享部件对齐后再次被父级字号覆盖。
- L2：standard_form_composition 97、product_page_pattern 12+5、page_pattern_reference_parity 15+13；style_system passed。日志 `artifacts/frontend-web-fix-20260928/tpl52/record-families.log`。无 TS/模板/业务逻辑变化，严格类型结果沿用 52.1 的同源脚本与类型输入。
- 单次合并候选构建 21.65s，同一候选检查受影响列表、现有表单、只读详情、引入弹层；双视口 91/91 passed，包含浅/深两种 token 解析及禁用态。报告 `artifacts/frontend-web-fix-20260928/tpl07-1790765202063/report.json`。任务专用独立旅程未在本轮重跑，不把共享事实渲染证据扩大为全部任务业务验收。
- 视觉复核发现过渡动画让弹层截图仍呈半透明，探针改为禁用截图动画并等待列表加载结束；同一构建只补弹层两视口 30/30，稳定截图 `artifacts/frontend-web-fix-20260928/tpl07-1790765261313/dialog-390.png` 等。之前 91 项的合同/数据/字体输入未变，继续复用。无额外构建。

### 52.6 样式基础批次收口与总体目标边界

- 官方参考台账明确 aeed5707 为权威、旧日快照为历史；不再混用两个实现的视觉义务。390px 官方原图已存在，旧 missing-evidence 条目改为不适用像素对齐（保留产品窄屏可用性责任），其余 16 项能力缺口未擅自关闭。
- 最终 primitive_adapter 回执 45、page_pattern_parity 回执 28 均 passed；日志与 begin/record 在 `artifacts/frontend-web-fix-20260928/tpl52/`。前一类型检查、未变业务合同回执复用；未运行 ORM、模块升级、Quick 或全旅程。
- 加载候选：构建基线 `825a3795c6aac8ffc7f45e9034123d29075c6e80` 加构建回执所列样式 dirty 输入，代码已收进 `c0623fb18`；入口 `/assets/index-DzCJIgmD.js`，entry SHA256 `e60ddb0ccfe637175da3f46d41eb11890390c1457de7c948a84277607e51cd74`。浏览器已核对实际 HTTP entry。之后仅文档/记录变更，不重建或伪装 clean 构建。
- 样式基础批次验收完成；总体官方页面/交互接管继续。主线未集成、目标环境未部署、整体用户交付未验收。所有提交仅本地。
- 下一步复用本 run 与台账，处理仍由旧共享实现承担的呈现/交互职责；已确认的候选、角色、数据和原始报告均复用，不重新执行菜单/环境全量盘点。

## 53. 全系统渲染与交互体系闭环（2026-09-30，进行中）

所有者明确：本轮不仅完成样式，应完整建立契约驱动的官方渲染和交互体系，包含已确认业务职责所缺的契约；contract_gap 不是永久豁免。

- 复用现有 67 条台账、16 项剩余职责及其 owner/followUp，不另建覆盖表、不重新全仓/菜单盘点。
- 前端共性呈现、组合及模态生命周期由 P0 frontend 拥有；缺失的通用能力投影由 P0 smart_core，行业标准结构由 P1 smart_construction_core；不把视觉义务塞进业务契约，也不让模板演示创造新的业务要求。
- 已确认移动导航仍用 ScAside + 手写遮罩/位移 + 独立生命周期，拟复用 ScDrawer 官方驱动并退出对应旧职责；同时继续已有 collection.favorite、detail.action-state 等声明能力的消费/生产闭环。
- 后端未修改前不运行 ORM；一旦实际修改契约生产者，只运行受影响的非零契约测试及必要受管运行时检查，按层推进。无新环境、凭据或 fixture；不推送、合并或部署目标环境。

### 53.1 移动导航官方 Drawer 接管

- P0 / shared shell overlay：ProductMobileNavigationDrawer 在移动端只消费 ScDrawer，桌面只消费 ScAside。ScDrawer 增加通用 placement 和 navigation appearance；官方驱动统一负责遮罩、位移动画，既有共享生命周期负责焦点/滚动锁。菜单和上下文内容继续是同一契约消费者。
- 旧职责退出：删除导航自己的 backdrop 节点、位移动画样式和 useModalLifecycle 实例；不保留双路径或第二份开关状态。旧 guard 从锁定导航自管生命周期修正为要求共享 ScDrawer，并加入拒绝私有遮罩/生命周期回流的负例。
- L1/L2：navigation_shell 全链 40+12+42+19 个案例，primitive adapter 11+34；overlay lifecycle 12（新增两类负例），delivery_hardening、style_system、typecheck.strict 全部 passed。日志 `tpl52/navigation-takeover.log`、`tpl52/navigation-lifecycle.log`（同一批次证据目录继续复用，不再复制原始日志）。
- 单次构建 21.11s，base `904b3fa65` + 明确导航 dirty 范围；5180 原 listener 复用，之前 c062 样式候选保留。
- `TPL07_SCOPE=navigation` 真实 finance login/system.init →付款列表，1440/390 两视口 16/16 passed：一个官方导航模态、无私有遮罩、授权菜单保留、Tab 焦点在模态内、Escape 还原 opener、路由保持、滚动锁释放、官方遮罩可关闭、回桌面唯一导航。无业务写入。报告 `artifacts/frontend-web-fix-20260928/tpl07-1790765698870/report.json`，窄屏截图已实际复核。
- 后端/数据库未变，ORM 不运行。下一项复用段47/48生产者修复证据，核对 collection.favorite 与 detail.action-state 的实际共享消费者。


### 53.2 收藏能力按有效契约消费

- P0 / frontend generic collection consumer，平台共享行为；不在 P1/P2/P3 或模型白名单定义权限。复用段47已有生产者，影响 ActionView 的共享搜索菜单，未改后端，L3 ORM/升级不适用。
- 修复缺省 `save_enabled !== false` 放行、缺失 intent 自动补写、无条件展示共享选项三个消费偏差。现在只接受显式 true 及现有适配器支持的 search.favorite.set；共享必须单独明确授权，提交时再次限制。声明拒绝时保留禁用入口及原因，未声明不制造权限。
- L1 intrusion guard、strict typecheck passed；L2 collection_action_toolbar 16 纯逻辑 + 11 守卫测试 passed，begin/record 回执27。日志 `artifacts/frontend-web-fix-20260928/tpl52/favorite-static.log`。既有生产者输入未变，复用原证据，无 ORM。
- 一次构建21.31s，base d1da61c0f + 上述 dirty 范围，5180 原 listener 复用。真实 finance login/system.init/ui.contract，1440/390 收藏入口、显式不共享、表单可用、取消、Escape、无横向溢出19/19 passed：`artifacts/frontend-web-fix-20260928/tpl07-1790766225490/report.json`。
- 首次17项报告 `tpl07-1790766188416/report.json` 已通过；图像复核发现窄屏截图未展示保存操作，探针增加滚动到操作并核对其进入视口，仅补验相同受影响收藏范围，复用构建。不是产品失败或第二次构建。
- collection.favorite 台账仅关闭“声明控制项已呈现”的职责；没有点击保存，不宣称写入/刷新/失败恢复已验收。下一步继续这些交互及 detail.action-state；整体目标进行中，主线未集成、目标未部署、整体用户验收未完成。


### 53.3 收藏异步结果与失败恢复（进行中）

- P0 / shared collection interaction；沿用 ui.contract 的已有权限和写入口，schema/store 不新增业务语义。提交从无返回值事件改为可等待的共享回调；等待期间禁止重复保存和修改输入，失败保留名称/默认选项，成功后收起输入并反馈；已写入但刷新失败独立提示，不误报写入失败。路由/合同切换后不覆盖新页面合同。
- L1 `ci.local.iteration` passed；L2 collection toolbar 19+11 passed、strict typecheck passed，回执30。首次类型检查发现两处禁用收藏的工具栏缺少新增接口，已补齐并定向复验，原失败日志保留 `favorite-feedback-static.log`，最终 `favorite-feedback-static-fixed.log`。
- 单次构建21.21s，base 7f8c38288 + 收藏交互 dirty 范围。后续只改浏览器探针/恢复工具，未重复构建。
- P4 探针缺陷：原 `**/api/v1/intent` 未匹配带 `?db=` 的实际请求。首次失败注入 `tpl07-1790766458924/report.json` 未拦截保存，不计通过；只读回读 `tpl07-1790766553758/report.json` 确认误建 ir.filters 7（finance 30/payment.request/action775/非默认）。工具匹配修为 `intent*`，并阻断 search.favorite.set 及独立 create/write/unlink intent；不得继续把旧 guard 的零记录当作写入未发生的充分证据。
- 最小 P4 恢复沿用 acceptance profile/preflight/容器与 filestore 校验，专用 Make 入口锁定该记录全部身份。首次因 HTTP create_date 去掉微秒而 fail closed，诊断确认 ORM 精度后绑定完整时间 2026-09-30 11:07:45.676133；没有放宽匹配条件。恢复工具9项测试通过，精确删除并提交后回读 remaining=0，日志 `tpl52/favorite-recovery-restored.log`。不重置 fixture、不升级模块、不运行无关 ORM 测试。该脚本只用于本次对象恢复，不是通用删除入口。

- 修正拦截后第二次探针已截获请求，但等待态的可访问名称包含“处理中”，精确“保存”定位超时（`tpl07-1790766654026/report.json`）；只修正定位，复用同一构建。最终受控网络失败29/29 passed：`tpl07-1790766709771/report.json`，两个视口均验证 pending 防重复、输入保留、恢复重试、共享不越权、取消与焦点。失败注入不经过后端写入；不冒充真实成功写入旅程。随后取消已完成请求的探针超时计时器，消除多余等待，语法检查通过。
- 恢复工具提交后的 ORM 回读 remaining=0；独立 HTTP 回读 `tpl07-1790766734559/report.json` 却仍返回 id=7 一条记录，同候选菜单截图也仍呈现该收藏。数据库直接回读与 HTTP 读路径矛盾，需要诊断缓存或读写载体一致性；不能宣称 HTTP 恢复确认完成。该发现是下一项真实闭环阻断，不能把本节宣布为收藏完整验收。
- 下一步 P0 契约生产者：沿 ui_contract_v2 缓存命中路径确认 saved_filters 的用户/action 运行事实何时重投影；修复后定向契约测试及必要受管装载，不通过前端过滤不存在记录或强制刷新兜底。后端真正变化时才执行相关层验证。


### 53.4 收藏运行事实缓存边界与恢复纠正

- 纠正53.3的初步归因：后续 HTTP 记录是新建 id=8（11:11:30.981759），不是已清理 id=7。此前只看数量导致误判，不能据此声称 api.data 缓存故障。id=8 来自等待态探针超时退出阶段；工具现在先中止全部悬挂拦截请求，再关闭浏览器，防止退出时请求继续。
- P4 精确恢复 id=8，完整身份与 fixture 用户绑定，9项工具测试通过，提交后 ORM remaining=0。修正后的失败恢复29项 passed，报告 `tpl07-1790766965631/report.json`；随后 HTTP 查询 records=[]，但搜索菜单仍显示该收藏，报告 `tpl07-1790766975287/report.json`。此时才获得真正的“HTTP事实已删除、合同菜单仍旧”的分层证据。
- P0 / smart_core / 搜索运行事实投影：缓存是页面结构权威，不能缓存用户收藏事实。沿现有 app.search.config 生产者补 refresh_saved_search_runtime，在统一 runtime seal 前重投影 searchContract 的 saved_filters 和收藏能力；冷源、缓存源和 assembled cache 都经过同一边界，显式传 action_id；不重写过滤器/分组/配置结构，不新增业务契约字段，不替前端造权限。scene_contract 维持原职责，不人为接入模型收藏。
- L1 ci.local.iteration、Python语法通过；L2 saved_search_capability 13项通过，涵盖删除后空集合、action scope、用户隔离、权限变化、查询失败不交付旧结果、先刷新再封装。登记 begin/record13。生命周期守卫发现既有 nested_form_relation.json 哈希漂移，确认文件在起点HEAD未变；只按现有语义内容重算 contractSha256，不修改示例语义或降低守卫。
- 模块加载评估：没有字段、XML、注册或 manifest 变化，无需 -u。纯 Python 代码需通过既有 backend.acceptance.up 重载；复用原验收库、卷与端口，不做安装/fixture/全量ORM回归。前端构建输入未变，继续使用53.3候选；受影响实际合同/菜单验证待重载后完成。

- 生命周期首次报告同时存在 definition/schema 哈希和 validation/示例哈希两项漂移；首次修复只处理了报告末尾的示例错误，遗漏 definition，未达到完整通过。3de6778a2 的后端重载已发生，但没有在该失败状态继续浏览器验收。现已按原 schema 文件实际字节 SHA256 同步 runtime 常量与四份示例，不改 schema 或示例业务内容；完整守卫最终8/8维度、p0Count=0，5+10单测通过，日志 `tpl52/favorite-runtime-lifecycle-final.log`。后续只因这次运行常量变化再次受管重载，不重建前端。

- 受管后端最终加载8128f14b5，18082健康；5180仍复用53.3构建，没有第二次前端构建。修复后只读恢复7/7 passed (`tpl07-1790767270036/report.json`)；增加同一页面重新加载并检查缓存命中交付，9/9 passed (`tpl07-1790767317777/report.json`)：HTTP精确查询空集合、首次和缓存命中菜单都无测试收藏，实际 projection_cache hot/persisted 由报告保留。恢复阻断关闭。
- 本节验证了缓存后运行事实投影及测试对象恢复；不把失败注入或误建对象当成经过设计的收藏成功/刷新业务闭环。整体目标继续，仍需完成相应成功路径及详情动作状态。官方基线再次确认 detail/base 与 detail/advanced 是 Card+Descriptions 的独立页面，后续不得把旧日快照的右侧抽屉义务误当官方模板必须具备的业务契约。


### 53.5 只读详情的声明限制反馈与官方参考收敛

- P0 / frontend shared readonly header；沿既有 schema→store 的 recordActionStates 只解释明确拒绝，不改变权限/状态判定。通用 reason code 映射用户提示，未知原因只给中性说明；不因 capability boolean 生成执行动作。复用 ScInlineState 的官方 TDesign Alert，旧“有拒绝原因但不显示”职责退出，无新私有提示系统。
- L2 contract_record_action_state 26/26、strict typecheck通过，begin/record26；前后端生产者未变，复用53.4生产者结果，L3不运行。一次受管构建21.85s，base533519b47 + 本节前端 dirty 范围，5180复用，原收藏候选保留。
- 第一次实际样本1813是草稿，验证允许态不捏造限制（15/15报告 `tpl07-1790767535920/report.json`）。进一步按该契约声明的 state_field/allowed_states，在同一project/company和finance授权范围中只读选取现有记录1710 approved；双视口29/29通过 `tpl07-1790767599788/report.json`。实际显示“不可删除：当前业务状态不允许删除”，同一官方 Alert 驱动，窄屏可读且无整页横向溢出；无业务写入。截图已复核。
- 官方 pinned aeed5707 的 detail/base 与 detail/advanced 源码是 standalone Card/Descriptions，并非日快照右侧抽屉。既有 FormSection/standardDetailCompositionRuntime 与段52实际详情证据已覆盖容器、共享页头、事实网格；对应3条改aligned。强制两级tab与抽屉loading几何是旧参考义务，3条改not_applicable；不豁免契约声明的 notebook/关系/协作/加载与返回职责，不为历史截图新造drawer契约。
- 原67条台账保留，9项待处理；detail.action-state只关闭声明拒绝反馈，复制动作是否属于确认职责及执行契约仍待解决，不因 duplicate=true 前端补一个按钮。page_pattern_reference_parity 28测试通过，原样式/页型/返回链证据不重跑；无推送、合并、目标部署或整体交付声明。


### 53.6 公开登录契约复用与共享页脚版本消费

- P0 / schema→session→shared shell：system.init_payload_builder 已调用 runtime_product_identity，版本由部署配置/产品VERSION产生；补齐 AppInitResponse 已有字段的类型声明，session productVersion getter 映射既有 initMeta，侧栏页脚显示真实版本。展开桌面及移动导航显示，折叠栏保留操作空间；无来源时不造版本，不暴露源码SHA。没有后端/schema-wire语义或数据库变化，L3/ORM不运行。
- L1 ci.local.iteration passed；L2 navigation_shell 40+12+42+19 =113，strict typecheck passed（`tpl52/shell-version-static.log`）。单次构建22.43s，base4d32e3f3a + 明确本节前端dirty范围，复用5180。浏览器真实public auth→login→system.init→付款列表→移动导航23/23 passed，报告 `tpl07-1790767915401/report.json`；版本值匹配实际system.init，移动页脚可见且不溢出。截图已复核，未写业务数据。
- 公开契约现有 build_public_auth_page_contracts 声明激活/恢复目标，LoginView 已消费，并非台账所写“未声明”。本次核对实际登录标题和入口，复用早前public-auth18项（模拟激活无账号写入），不重复账号业务验收。
- 按所有者“不复制官方演示业务”边界，纠正历史义务：官方 Header.vue 无fullscreen；Login.vue 的remember checkbox未绑定持久化；Search.vue 仅管理focus/text，未实现全局结果查询。不能为这些演示或旧参考控件新增凭据保留、三方登录或跨模型搜索。对应项记not_applicable，保留将来明确功能需契约先行的边界；没有删去已确认的登录、激活/恢复、授权菜单检索职责。
- 67条台账结构不变，剩余3项：复制记录执行职责、任务字段几何、任务事实slot覆盖。复制权限bool不等于动作声明；后两项继续定位P1有效视图/结构生产者。另保留计划中的收藏成功/刷新/恢复闭环，不能用失败注入替代。总体仍进行中，主线/部署/整体用户验收均未完成。


### 53.7 任务页实际权威与响应式布局核对

- 候选 aedbd1f95 + P4 `standard_page_type_browser.mjs` dirty；产品源码/后端/构建输入未变，复用53.6候选与5180。L1 node syntax、ci.local.iteration通过；L2 native_form_structure_responsibility 11/11（tpl52/task-authority-static.log）。不运行ORM、升级、构建或fixture写入。
- 新增既有探针的task-authority只读范围。首次报告tpl07-1790768213033为validation_tool_defect：关系附件响应覆盖单一recordAuthority。按模型保留观察结果后13/13通过（tpl07-1790768237871）；进一步补充实际字段坐标而非容器CSS猜测，15/15通过（tpl07-1790768273395，tpl52/task-authority-geometry.log）。所有请求只读，无业务写入；同一启动链及既有finance/1813身份。
- 实际action775/view2145使用container_tree_authority、native_authority、slots=[]，契约组cols=2与显式cols=1并存。项目/往来单位实际桌面同排双列，390窄屏同列上下排列；无整页横向溢出。桌面截图已复核。task.field-grid关闭，不能再为旧“单列”记录重写P1。
- task.slot-coverage仍未关闭，但纠正为必要业务事实覆盖核对：原生字段树、语义锚点、条件字段及关系/页签是当前权威，不能恢复旧slot路径。67条保留，剩余2项（事实职责覆盖、复制执行职责）；另有收藏成功/刷新/恢复闭环及总体完成审计待执行，不宣称整体完成。


### 53.8 复用P1字段职责矩阵核对任务事实

- 候选5c47cf263 + P4既有browser探针dirty；P0/P1产品输入未变，复用53.7的11项native structure定向结果及53.6构建，不运行ORM/模块升级/重构建。读既有config/p1_payment_request_field_completeness_v1.json作为41项edit/create_edit职责来源，不新增覆盖矩阵。
- 原生view_payment_request_pay_form已明确移除payment_flow_label重复摘要，name/state由页头承载，legal_next_action_display与payment_blocking_reason_display由动作/反馈承载。历史slot不足记录不能作为恢复重复正文的依据。41项矩阵声明检查使用原生字段节点、语义锚点与页头数据；显式记录payment_flow_label的P1退役依据，不能把该摘要当新业务输入。
- 首次探针使用旧dataMeta.fields位置，报告tpl07-1790768422213为validation_tool_defect，并非41项业务字段全部缺失；修复当前V2投影采集后23/23通过（tpl07-1790768458153/report.json，tpl52/task-facts-browser-fixed.log）。已证明4项always required输入可见、附件输入可见、追溯区可展开、双视口几何保留，41项职责无未解释的声明缺失；无业务写入。
- task.slot-coverage继续保留：上述声明完整与代表字段可见不能直接证明每项条件字段/追溯页签事实均可消费。下一步只补条件字段与追溯页签的实际交互证据，复用TPL05A49项业务闭环，不重做办理；复制职责与收藏成功/刷新/恢复仍待收口。整体目标保持active。


### 53.9 条件事实及追溯页签闭环，参考台账收敛

- P4探针；候选2c1c9ca6e + browser script dirty，无产品/后端变化。复用53.7 L2 11项与53.6静态候选，node syntax和diff通过；无ORM、构建或业务写入。
- 现有finance1813同时有合同/结算依据，按原P1矩阵核对适用事实。首轮tpl07-1790768539759在付款记录tab定位超时；追加有界DOM/screenshot诊断tpl07-1790768605198证明页签存在，官方Tabs没有role=tab。分类validation_tool_defect，改用可见标签，无产品改动。最终tpl07-1790768656354/report.json（tpl52/task-conditional-final.log）43/43通过：合同/结算条件字段、付款记录关系、历史金额只读与声明空文本、切回结算事实、双视口布局。诊断截图已复核。
- task.slot-coverage关闭：41项既有P1职责及当前原生投影、代表/条件事实/关系切换证据共同证明本条呈现责任；条件性权限/审批等业务闭环仍引用原TPL05A49结果，不宣称本次重跑或自动升级业务矩阵。
- detail.action-state关闭剩余范围判断：duplicate是权限交集，不是动作；实际actionRuleList没有copy，既有P1职责矩阵与pinned官方detail均不要求copy。禁止仅据boolean新增端侧执行，未来明确业务要求需正式执行契约。既有编辑/删除拒绝反馈沿用53.5。
- 67条参考台账无开放项不等于整体目标完成。下一项是收藏成功保存→有效契约刷新→恢复原配置闭环，之后核对原整体计划、必要门禁与现有证据；不推送/合并/目标部署。


### 53.10 收藏删除/管理登记为产品缺口（所有者纠正）

- 在af7620ea3上准备收藏成功验证时发现产品只有保存，没有删除/管理入口。原拟添加P4精确恢复工具，已进行纯测试14项；所有者明确指出应登记产品缺口。该判断采纳：不能用恢复工具替代产品删除职责或宣称闭环完成。
- 本轮临时工具、Make接线和浏览器写入分支全部撤回，未提交；没有调用prepare/restore，没有执行收藏保存、删除或其他数据库写入。纯工具日志仅为已撤回方案的历史记录，不计产品验收证据。
- 既有67条台账中collection.favorite重开为P0 contract_gap；P0 smart_core拥有权限/执行及投影，通用前端仅消费明确能力与动作，不按角色或过滤器名称猜权限。下一步补齐删除执行、私有收藏所有权/ACL边界、共享菜单入口及成功/失败反馈，再通过产品入口验证保存→刷新→删除→刷新。维持单一主路径，不另建收藏管理页面。
- 53.9的67条无开放项仅代表当时已确认范围，现已被本次产品缺口裁决修正；整体目标一直未宣布完成。其他67条的既有通过证据不失效。


### 53.11 收藏删除的P0执行与契约投影

- 候选913d71a99 + smart_core收藏handler/投影/定向测试、make/frontend.mk dirty。Formal Product Layer=P0，Layer Target=通用收藏权限与执行；不涉及行业/客户规则，不在前端推导归属。沿既有handler模块自动发现增加search.favorite.delete，无模型字段/XML变更，不需要模块升级；待共享消费完成后受管重载及运行态验证。
- 删除显式绑定id/model/action_id，内部用户、目标模型read、ir.filters read/unlink ACL和记录规则均由后端检查；查询强制user_id=当前用户，拒绝共享与他人私有收藏，全程无sudo。响应明确deleted结果，重复/不存在对象不伪报删除成功。
- saved_filters逐项增加delete_action（intent/label/enabled/disabled_reason/params）；可删除要求当前所有者、模型read及过滤器read/unlink ACL/record-rule。沿53.4每次有效契约刷新投影，不从缓存继承旧权限。无create权限不影响已获授权的删除。
- L1 ci.local.iteration及py_compile通过；L2现有saved_search_capability入口扩展执行handler边界测试，16+13=29项通过（tpl52/favorite-delete-backend-final.log），agent.run.begin/record29。覆盖共享/他人/错模型/错action、ACL/rule拒绝、非法身份类型、不能提权、删除不要求create等。纯测试不是运行态ORM证明。
- collection.favorite保持contract_gap：尚待共享菜单消费删除动作、确认/反馈/失败恢复，以及真实保存→刷新→删除→刷新闭环。当前未重载后端、未构建、未执行配置写入，不宣称产品缺口关闭。其余页面证据不受本次后端范围影响。


### 53.12 收藏删除共享消费与反馈

- P0 generic frontend contract consumption；候选0c9915e43 + shared search runtime/VM/toolbar/ActionView与定向测试dirty。没有模型/角色专属分支：只接受显式enabled=true、已知search.favorite.delete及严格id/model/action_id参数。修复中间ChipVM适配丢弃删除动作的缺口，同一共享菜单供现有列表/看板宿主使用。
- 收藏项使用独立删除按钮与现有ScDialog官方弹窗，清晰说明仅删除收藏不删除业务记录；确认期间阻止重复提交和关闭。执行前从当前契约按记录id重取授权动作，不用显示名称推导执行；页面上下文变化不把旧结果写入新页面。
- 删除失败保留确认面与可重试反馈；删除成功后刷新有效契约和列表，当前选中收藏同步清除。删除成功但刷新失败明确告知无需再次删除，关闭删除确认，不以刷新失败重发删除请求。
- L1 ci.local.iteration passed；L2 collection_action_toolbar 31+11=42通过（tpl52/favorite-delete-ui-receipt-tests.log，begin/record42），包含严格动作参数、VM动作透传、删除失败/刷新失败区分；strict typecheck、style_system.guard、contract_consumer_intrusion.guard通过（tpl52/favorite-delete-consumer-types.log）。中途类型检查期间仅helper/adapter收紧，最终再跑stable typecheck，使用最终日志。无ORM/构建/数据库写入。
- 下一步受管重载后端至本批代码、稳定后一次构建，复用5180完成真实收藏保存→刷新→取消删除确认→确认删除→刷新回读，补失败与窄屏定向检查。collection.favorite仍为开放产品缺口，静态通过不能代替真实闭环。


### 53.13 收藏闭环实测暴露并修复请求身份冲突

- 候选faffa6cd6已受管backend.acceptance.up重载，原静态候选保留，构建22.20s并复用5180。真实私有收藏保存生成ir.filters id9（finance uid30、payment.request/action775、非默认、名称FE-TPL53-私有收藏闭环），服务端回读一致。新删除入口、双视口确认/取消及注入失败保留记录已通过。
- 实际删除失败报告tpl07-1790769469765/report.json：INTENT_NOT_FOUND“记录[9]不存在”。P0 product_defect：请求model=payment.request与通用id=9触发路由前置业务记录检查，错误地把收藏ID当付款记录ID。不能修改/绕过通用权限保护；修正为明确filter_id，由收藏handler按ir.filters归属/ACL/record-rule执行。响应id仍是删除结果身份。
- 生产者/consumer/handler及定向反例同步改filter_id；29项后端、42项前端及strict typecheck通过（tpl52/favorite-filter-identity-fix.log）。浏览器新增精确续验模式，只接受原报告所见id9及完整私有对象身份，不重建收藏；恢复只走产品删除入口。
- 此处提交是修复候选，真实删除/恢复待新代码受管重载及构建后续验。既有id9仍须恢复，不能把失败或工具清理计作闭环完成。第二次构建属于已定位产品缺陷后的必要重验，不是无变化重建。


### 53.14 收藏真实产品闭环完成

- 0d2c6190a修复候选受管重载后端，必要重建21.79s，旧静态候选保留，5180复用同一产物。首次失败中的成功保存/回读不失效：仅续验精确私有收藏id9，tpl07-1790769636566/report.json（tpl52/favorite-lifecycle-resumed.log）25项通过。产品确认删除成功、api.data回读空集、有效契约刷新与再次reload均无旧收藏；未调用P4恢复工具。390确认截图已复核。
- 为补“删除当前选中的收藏”的独立状态责任，通过相同产品入口保存私有非默认配置id10；应用后URL与菜单/条件标签均已选中。首次tpl07-1790769721849为validation_tool_defect：探针假定只有一个aria-pressed控件，实际两个选中控件均正确。修复为断言所有匹配控件均选中，不改产品、不重建；绑定原报告精确id10续验，tpl07-1790769758359/report.json（tpl52/favorite-active-delete-resumed.log）24项通过。删除后saved_filter路由清除、服务器空集、reload无残留。
- 允许的写入只有fixture finance本人、payment.request/action775指定名称私有收藏的保存/删除；一次失败通过受控abort注入，记录未被删除且可重试。付款业务记录与共享配置未修改，未创建业务fixture。临时收藏9和10均由产品正常删除。
- collection.favorite重新关闭，67条参考台账0开放项。29后端/42前端纯测试和strict types沿53.13修复证据复用；本节只改验收工具与记录，未变产品输入不再编译/构建。下一步执行总体完成核验，检查页面类型、旧路径退出、配置闭环及强制门禁，不能用台账0缺口代替总体完成。


### 53.15 总体收口发现既有状态动作产品缺口，先补日常合同签署声明

- 起点e1325df02 clean；前一回复仅状态确认，本节恢复实际产品推进。复用段45中TPL06A/LC01/TPL07/LC01B已完成事实，不重接付款列表、不重跑49项办理。段51注册表已PASS，段52已有官方390参考；run中旧注册表失败与goal中16项缺口数字已纠正，历史通过不是当前全量门禁通过。
- 完成审计发现native_view_undeclared_actions仍登记5条真实状态变更。它们是P1产品投影缺口，不能长期“权威侧待决”后退出总体范围。既有67条中的detail.action-state重开（1个聚合产品缺口），保留53.5拒绝反馈和53.9复制范围裁决的有效证据；不另建覆盖表。
- Formal Product Layer=P1；Layer Target=workflow contract profile；Module=smart_construction_core；Standard vs User-Specific=行业标准。原生general_contract_views.xml已声明合同经理签署按钮、draft/confirmed来源状态，general_contract.action_signed已执行业务锚点校验并从draft走action_confirm；审批未完成时不签署。这里补生产者方法声明，不在P0发明行业规则、不在P2/P3写运行偏好、不在前端猜方法/权限。Blast Radius仅sc.general.contract现有签署动作及其声明覆盖测试。
- 复用现有complete业务动作语义，明确label=已签署、method=action_signed，在draft/confirmed声明；完成的是该业务操作，不把signed重命名为done。原生动作身份/组授权、execute_button重新加载有效actionRule并检查allowed/enabled/entitlement的执行链保持。未改模型方法、原生视图、schema词汇或前端。去除已经声明的唯一登记项，其余4项仍登记；这不是运行态验收关闭。
- L1首次ci.local.iteration失败为run范围未登记config/contract路径；明确登记本次已有契约清单路径后重跑PASS（general-sign-iteration-final.log）。未用全量Quick排错。L2 native_view.workflow_action_coverage 8+17=25通过（general-sign-coverage-final.log；begin/record25），真实运行生产_available_actions与action_signed函数，覆盖合法来源、终态拒绝、审批未完成不签署、必要业务锚点、reviewer动作不可冒领。workflow_action_semantics.guard 15项通过（general-sign-contract.log）；page_pattern_reference_parity 28通过，67条/1开放项（general-sign-ledger.log）。台账随后仅恢复原紧凑格式，JSON语义逐值相等，不重跑相同断言。
- 上述函数级测试不等于ORM权限或真实页面执行证明。L3受管后端重载、L4现有角色有效契约/实际动作定向验收仍待执行；无字段/XML/manifest变更，不需要模块升级，前端构建输入不变，不重建5180。当前未写业务数据库，未创建fixture。下一步补运行态身份/授权证据，再处理付款审批、付款冲销、计划启动、文档回草稿四条。行业无关审计97词法命中亦保留，需按现有分类证据处理，不能假称97业务缺陷或直接豁免。
- 状态：本节实现及纯测试完成，产品缺口verification_pending；整体目标active。主线未集成、目标未部署、整体用户验收未完成。回滚为本节P1声明与覆盖登记的同批回退，不涉及数据恢复。


### 53.16 同族补齐计划启动与文档回草稿

- d88ae3e41 clean起步，沿53.15 P1/workflow contract范围。核对原业务方法和原生按钮后，为sc.plan声明confirmed→action_start（activate/start_execution），为sc.project.document的review/done/cancel声明action_reset_to_draft（reopen）。未改P0词汇、业务方法或端侧规则。
- 计划不再继承与模型前置条件冲突的通用完成/回草稿状态：完成仅in_progress，回草稿仅cancel；不向sc.fund.account.operation推广计划专属动作。原生计划视图仍有confirmed显示完成、非draft显示重置的旧宽条件，当前有效workflow声明不再赋予这些无效操作语义；原生视图一致性及运行态效果仍待定向收口，不能据单测宣布完整关闭。
- L1 ci.local.iteration PASS。L2 native coverage 8+21=29通过（native-state-contract.log，begin/record29）；同一次命令的state_phase guard发现sc.plan旧dead-state登记已失效，分类为随产品修复而过期的证据登记。移除该精确条目后phase16、semantics15通过（native-state-phases-final.log）。无全量ORM、fixture写入、前端重建。后端运行态重载仍待执行。
- 已知登记内未声明状态动作5→3（含53.15签署则剩2）：付款action_set_approved、付款执行action_reverse_payment；签署/计划/文档的运行态验收未闭合，67条中的detail.action-state继续开放。源码同时发现native coverage把各模型方法名汇成全局集合，存在同名方法跨模型误覆盖的验证工具缺陷；目前计数只代表已登记集合，不证明全系统仅余2个缺口。下一步必须按(model,method)验证，补可证伪测试，不能以全局方法存在消项。
- 本批P1声明及纯测试完成，整体继续active；不推送、合并或目标部署。


### 53.17 所有者裁决：审批由状态机和用户配置统一驱动

- 所有者明确要求：配置审批则走审批，未配置审批则提交自动通过，统一由状态机控制。此裁决调整53.15/53.16后续顺序：不再逐个给旧批准按钮补平行声明；先收敛既有业务执行，再同步有效契约和原生入口。签署、计划启动、付款冲销等审批之外的业务转换仍保留各自状态/权限/数据前置条件，不把自动审批扩大为自动签署或自动付款。
- 已定位权威：sc.approval.policy.is_approval_required(model, company)以及next_state_after_submit已经存在；费用action_submit、结算action_submit已按该权威分流。payment.request.action_submit却固定写submit并request_validation，action_approval_decision还把“validation_status=no且无review”当人工通过，形成不一致的第二套判断。此为P1执行缺陷，不是前端模板职责。
- 修复要求：公司范围内的有效用户审批策略决定提交走向；启用审批但没有可匹配规则必须报配置错误，不能视同未配置。已在审批中的单据不得仅因当前策略改变或review集合为空被自动批准；需明确在途配置/审批实例权威。多级审批只在最后完成时推进一次，拒绝/重提/重复调用有稳定结果；审计记录区分提交自动通过与人工审批通过，不能伪造审批人或把no改成validated充当审批事实。
- 统一入口应复用既有状态转换与审批策略机制，不新建工作流引擎；旧action_approve/action_set_approved与回调只能委托同一转换裁决，不能各自实现放行规则。前端消费最终状态/可执行动作，不判断是否配置审批。原生按钮与共享官方动作栏使用同一合法动作集合。
- 本节为裁决与直接实现定位，未修改付款执行代码、未运行数据库写入、不宣称统一完成。下一批从付款提交/审批回调/写入守卫/执行handler一起做最小闭环，定向覆盖无审批、配置单级/多级、规则缺失、错误审批人、在途配置变化和重复回调；使用现有环境与配置恢复机制。模型绑定覆盖守卫缺陷继续登记，不因调整优先级消失。


### 53.18 付款审批执行收敛到状态机与公司审批配置

- c4cfd498a clean起步。Formal Product Layer=P1，Layer Target=payment request transitions/approval policy consumption，Module=smart_construction_core；P4仅补同层函数执行回归。行业执行规则放P1，不在P0通用前端/模板、P2客户规则或P3临时配置中复制。Blast Radius为付款提交、批准回调、批准兼容入口、后续结清状态校验及其动作投影/原生按钮；非付款业务方法未改。
- 提交的原有权限、对象/公司范围、依据/金额/资金门禁、锁与审计保留。提交后由既有公司sc.approval.policy判定：无需审批经私有提交身份推进approved，不伪写validation_status、不制造review；已配置则调用原生request_validation，缺匹配规则抛错。同一重提先用既有restart_validation重置上次审批尝试。未新建工作流引擎或数据字段。
- action_approve/action_set_approved只委托action_approval_decision；等待/待处理要求真实review和当前can_review，已有完整validated链统一调用_complete_payment_approval。回调也调用同一完成逻辑；未完成多级不推进，重复回调不重复审计。无review不再成为人工放行条件，在途判断不读取后续变更的策略。自动路径是不可伪造的本地对象token，不接受布尔回调标记；原先tier_validation_callback=True绕过完成检查的逻辑退出。
- write接入已有ScStateMachine.assert_transition，状态机补齐已经真实存在的submit→approved、rejected→submit以及受付款冲销执行保护的done→approved。approved/done是已经取得批准的业务事实，后续办理不再要求虚构审批记录；现金结清/来源/角色门禁仍先于done状态变更。未把自动批准扩展成自动付款。
- 原生表单移除validate_tier/action_approve/action_set_approved三条重复批准入口，只保留action_approval_decision，保留财务经理组、当前审批人和待审批状态条件。available_actions绑定同一方法，拒绝无review批准，校验当前审批人，提交状态提示调用既有next_state_after_submit；待处理多级不承诺最终approved。删除已经退出原生面的action_set_approved登记，不给旧按钮新增平行语义。
- L1 ci.local.iteration PASS（approval-unification-iteration-final.log）；L2新增verify.payment.approval_state_machine.unit稳定22项，执行真实生产方法与状态机，含原生/动作描述绑定、无配置自动通过、有配置等待、规则缺失、错误审批人、部分审批、完整审批、重复回调、旧入口统一、金额校验、伪造token/布尔回调拒绝和审批后配置变化。原native coverage 29与semantics15同次通过，日志approval-unification-stable.log；begin/record22。新脚本Make与registry登记、guard.registry.export同步。函数级测试不证明ORM事务回滚/真实权限/模块升级效果。
- 本批改XML，L3必须通过既有acceptance.module.upgrade针对smart_construction_core升级；当前尚未升级/重载，没有执行任何业务数据库写入。前端输入未变，5180继续复用原产物，不需构建。L4真实配置切换/多级链/返回反馈仍待同一受管环境验证。既有TPL05A49项只作未变范围基线，本次审批变化不能继承其审批结果。
- 已知未完：拒绝/重提的完整ORM链、审批策略配置变化的运行验证、费用/结算旧批准入口一致性，以及native coverage全局方法名误覆盖缺陷。登记中仍余付款冲销1项不代表全系统只剩1项；模型绑定的只读比较已发现5个隐藏方法（付款action_approve/validate_tier本批退役，另外sc.contract.event.action_reject、sc.expense.claim.action_approve、sc.settlement.order.action_approve仍需按所有者统一规则处置）。签署/计划/文档运行验证仍保留，不宣称完整收口。
- 当前为实现与纯测试完成，批次产品验收verification_pending，整体active；本地提交，不推送、合并或目标部署。


### 53.19 审批范围明确为所有业务单据；付款驳回先退出直改状态路径

- 所有者补充强制范围：审批统一逻辑覆盖所有业务单据，付款仅首个修复点，不是最终架构。后续必须复用现有状态机、sc.approval.policy和base_tier_validation的共同机制，不能逐模型复制付款私有审批编排；业务单据各自合法状态、权限、输入校验和审批后执行职责仍由行业/用户契约拥有。配置审批走真实链，无配置提交自动通过，已启用而无规则不放行。
- 本节已完成P1付款驳回执行修复：payment.request.reject改调action_approval_reject，验证财务权限、当前can_review、实际reviewer及当前sequence；先写review意见，交给原生_rejected_tier记录真实驳回，再由action_on_tier_rejected推进业务状态。回调没有rejected审批事实时不推进，重复回调不重复审计。原生reject_tier仍走相同审批运行时及事实回调，未增加第二套审批引擎。
- 定向回归verify.payment.approval_state_machine.unit稳定28项、workflow_action_semantics.guard15项通过（approval-rejection-stable.log，begin/record28），L1 ci.local.iteration通过（approval-rejection-iteration.log）。覆盖错误审批人/错误步骤、缺意见、伪造回调、真实意见先于状态推进及专用intent方法绑定。HTTP dispatcher已按失败结果显式rollback，未为猜测另改事务框架。函数测试不等于ORM/数据库恢复验证。
- 精确读取现有权威清单发现：sc.approval.policy.BUSINESS_MODEL_SELECTION仅17类，_tier_sync_supported仅15类，而workflowContract已有65个profile。它们职责并非等价，不能简单相减或把17类当用户确认的全范围。配置可用范围、审批运行时接入和状态动作投影需要按既有业务职责清单逐项关联；未接入但属于必要业务单据的部分登记产品缺口，不静默采用“不能配置，所以无审批”。不建立平行模型白名单来定义业务规则。
- 下一步优先共同机制与必要业务单据覆盖，统一提交/通过/拒绝/重提/回调/动作投影，并消除旧并行路径；复用既有workflow/审批配置清单和67条台账。先前付款已通过的函数结果只证明付款范围，不能外推全系统。native coverage按全局方法名误覆盖的问题继续保留，必须绑定model+method再作为全范围证据。
- 当前未执行模块升级、运行配置写入或业务写入，受管验收仍待。目标由所有者明确为全系统审批一致性，整体接管保持active；不推送、合并、部署。


### 53.20 覆盖守卫按模型绑定，显式保留全单据审批缺口

- 3f48ef47c clean起步，上一轮已提交53.19。Formal Product Layer=P4，Layer Target=原生动作覆盖验证，Module=scripts/verify；P1仅更新既有缺口登记，不改变业务语义。将declared_methods从全局方法集合改为(model, method)，复用既有profile loader。新增同名方法跨模型反例，验证另一模型声明不能覆盖本模型按钮，也不能错误判定本模型缺口登记已过期。
- 修正首次运行准确暴露sc.contract.event.action_reject、sc.expense.claim.action_approve、sc.settlement.order.action_approve三条此前隐藏路径；读取对应真实方法确认都是状态变更，在原native_view_undeclared_actions登记P1产品缺口。已登记状态动作1→4，不是新增业务缺陷，也不是批准旧路径永久保留。67条台账detail.action-state继续开放，范围仍是所有业务单据。
- L1 make ci.local.iteration PASS（model-bound-coverage-iteration.log）；L2 make verify.native_view.workflow_action_coverage 8+22=30项通过（model-bound-coverage-tests.log），begin/record30。覆盖守卫通过只证明缺口被完整登记于本工具已采用模型范围，不能证明审批全系统接入。付款28项输入未变，复用既有证据。
- L3/L4未运行：本批仅验证工具/登记，未改产品或数据库，无需模块升级、重建或浏览器矩阵。之前审批XML升级和真实业务验收仍待，不因本节工具通过而关闭。下一步将付款私有提交编排收敛到共享审批机制，推广必要单据并逐项退出登记中的旧并行入口；不复制模型专属审批引擎。


### 53.21 提交审批分流收敛为共享策略服务

- 755453829 clean起步。Formal Product Layer=P1，Layer Target=sc.approval.policy私有提交编排，Module=smart_construction_core；行业单据共享执行责任，不放入前端、P2配置或P4脚本。复用现有审批策略及base_tier_validation，不新增引擎、模型、字段或审批事实。各单据仍负责入口权限、业务校验、状态机转换和审计。
- 新增_start_submission_review(record)，按单据公司读取配置：未配置返回自动通过分支；已配置调用原生request_validation，匹配为空抛配置错误。已有waiting/pending实例禁止重建或自动通过；终结实例经原生restart_validation重置后必须确实清空，否则失败。调用为私有服务，不能由RPC直接发起，提交前置条件由调用单据验证。
- 付款、费用、结算三条提交路径已实际消费共同机制，删除各自重复的配置/创建review逻辑。费用和结算统一先进入原有submit状态，再由服务决定保持审批中或转各自approved/approve；保留原有业务校验、结算锁和数据验证、费用审计，不伪造validated。付款原有自动批准私有token与金额/状态守卫继续生效。
- L1 ci.local.iteration PASS（shared-approval-route-iteration.log）。L2 verify.payment.approval_state_machine.unit稳定33项（shared-approval-route-tests.log，begin/record33）：执行实际共享服务，跨模型配置分流、在途配置改变不绕过、原生重置失败拒绝；执行真实费用/结算action_submit，核对业务校验、锁/数据验证、原状态名与审计。新增测试后只重跑受影响目标，不重复其他页面证据。
- 这是共同机制首次落地，不是全单据完成：其他单据提交消费者、费用/结算旧批准和回调的在途实例权威仍须继续统一，原四项状态动作缺口未关闭。未执行ORM事务/真实多级配置验收，不能把函数测试等同运行验收。此前付款XML仍需受管模块升级，稳定批次统一进行；前端产物不变、不重建、不推送/合并/目标部署。


### 53.22 费用/结算旧批准入口退出配置重判放行

- 785094a7f clean起步，P1 smart_construction_core审批执行；共享策略服务新增私有_approve_submission_review，只读取真实review、当前审批状态及can_review，委托原生validate_tier并保留评论向导返回值。无实例/驳回/非当前审批人拒绝，不再以当前策略关闭为在途放行依据。
- 费用与结算action_approve委托共同决定，再由原审批完成回调执行业务转换。保留费用业务准备检查、财务权限和审计，结算角色、锁、合同/采购严格校验及数据验证。结算草稿不能直接批准；无审批应走已统一的提交路径。费用批准回调要求真实review，费用驳回回调要求rejected事实；终态重复批准回调不重复审计或业务转换。多级审批未完成保持submit。
- L1 make ci.local.iteration PASS（shared-approval-decision-iteration.log）；L2 verify.payment.approval_state_machine.unit 38项PASS（shared-approval-decision-tests.log，begin/record38）。新增真实共享方法与费用/结算生产方法执行回归，覆盖配置变更不读取、缺实例/错误审批人、评论向导返回、重复完成、部分审批与草稿批准拒绝。函数测试不证明ORM事务或真实审批人权限链。
- 原生按钮/契约投影尚未统一，四项状态动作登记保持开放；付款已有实例保护，但批准决定尚有局部编排，后续同样消费共享服务。其他业务单据仍须接入，不将两类旧入口修复外推为全系统完成。未重建前端、未写数据库、未运行无关ORM；受管升级和多级审批运行闭环仍待稳定批次执行。


### 53.23 费用/结算原生重复批准按钮退出

- 3973fc041 clean起步。P1 smart_construction_core原生视图与现有workflow契约一致性；费用两个表单、结算一个表单移除action_approve重复按钮。既有契约和原生validate_tier/reject_tier均保留，当前审批人及waiting/pending约束保留；action_done作为审批之后的业务办理仍保留。后台兼容action_approve已在53.22委托真实审批实例，本节不删除兼容方法。
- 原登记的费用/结算action_approve因按钮退出而移除，原生状态动作登记4→2（合同履约事件驳回、付款执行冲销）。这是旧呈现职责退出，不是通过给按钮随意补语义来消项；全单据审批接入与运行态验收未完成，detail.action-state继续开放。
- L1 ci.local.iteration PASS；L2 native_view.workflow_action_coverage 8+23=31通过，新增解析真实XML和profile的回归，确认三个表单审批方法一致、无重复批准且业务完成动作保留。日志approval-native-exit-iteration.log/approval-native-exit-tests.log，begin/record31。编辑脚本首次正则无匹配、断言在写入前退出，修正后才产生本批变更；最终L1绑定修改后作用域。
- 未改业务方法，53.22的38项结果输入不变复用。XML需要smart_construction_core受管模块升级，尚未执行；前端无需重建，不跑无关ORM。源代码退出不等于已加载运行候选退出，待稳定后统一升级及定向页面验证。


### 53.24 财务单据族成组接入共享提交分流

- 4e8ffeebe clean起步，P1 smart_construction_core：收款收入、付款执行、发票、融资借款、自筹办理、资金对账、结算调整七类action_confirm共同消费sc.approval.policy._start_submission_review。删除七份_request_document_approval及各提交入口重复的公司/策略分支，保留原权限、业务锚点/来源校验、审计、confirmed状态和批准后的独立业务执行。
- 原七份实现的rejected分支只restart_validation而未重新request_validation；共享路径重置后确认清空并建立真实新链。审批等待期间即使关闭配置也不能直接确认；无配置直接confirmed，不制造review/validated。七类原有draft承载审批中状态保持，以真实review区分，不重建状态框架。
- L1 ci.local.iteration PASS（finance-family-submit-iteration.log）；L2 verify.payment.approval_state_machine.unit 39项PASS（finance-family-submit-tests.log，begin/record39）。新增参数化执行七个真实action_confirm，每个覆盖无配置、有配置、驳回重提，并检查有配置后的在途关闭拒绝。首次测试失败为测试替身缺payment_execution._assert_finance_handling_access；补该协作者并断言它先执行，生产权限代码未改，失败日志finance-family-submit-tests-initial.log保留。
- 该族尚未整体关闭：完成/付款/入账入口仍读取当前配置，部分批准回调还需真实实例事实约束，继续列为P1产品工作。下一步统一这些执行边界后再扩展其余业务单据；不能用提交路径测试代替整个生命周期。未写数据库、未重建前端；受管升级与真实多级审批/恢复验收仍待。


### 53.25 财务单据按既有批准事实执行，回调不再自行放行

- 891859fb4 clean起步；P1 smart_construction_core审批结果消费。新增共享_assert_submission_approved：后续业务办理要求已确认业务状态，已有review必须validated；未创建review的自动批准仍有效，不受后来配置启用影响。六个后续入口（收款、付款、发票登记、融资完成、自筹完成、资金对账）改消费该门禁，不再重新读取当前策略。资金来源、角色、金额、合同及账务同步逻辑保留。结算调整确认本身即该单据的审批结果，不新增执行步骤。
- 七类批准/驳回回调均要求真实review及对应validated/rejected结果；中间层审批或伪造直接回调不推进、不产生审计。批准仍只从draft推进confirmed，重复批准不重复推进。驳回原生事实与意见逻辑保持；未宣称重复驳回审计全局幂等已验证。
- 收款、自筹、融资、对账四类workflow profile退出draft complete，原生完成按钮同步仅confirmed；不让前端猜是否需要审批，也不把审批通过自动变成付款/入账。用户须先提交，无配置时提交自动确认，再执行业务办理。
- L1 ci.local.iteration PASS（finance-outcome-iteration.log）；L2付款/共享审批41、native coverage8+24=32、semantics15全部PASS（finance-outcome-tests.log，begin/record41）。测试执行七类真实回调，含缺review、pending及真实终结；共享门禁覆盖草稿拒绝、自动批准后启用配置仍可办理、在途关闭仍拒绝；生产动作投影及真实XML验证四类草稿无完成动作。首次测试替身缺发票业务锚点协作者，补齐后重跑受影响目标，产品校验未删除。
- 这是源码与函数级验证，尚无真实ORM交易/多级审批恢复证据。XML增加四处变更，需与前批统一受管模块升级；必要定向ORM须验证真实权限、事务与旧调用方对“先提交”的适应，不以既有TPL05A49项替代。仍有其他单据族接入、付款批准局部编排、合同履约事件及付款冲销投影等缺口；总体目标保持active，无推送/合并/目标部署。


### 53.26 合同族提交/审批回调收敛

- 48d6c25ad clean起步；P1 smart_construction_core的一般合同与项目合同。action_confirm共同使用已有共享提交服务，删除两份申请审批助手及项目合同局部配置判断助手；保留一般合同业务锚点、项目合同状态消息与原confirmed业务状态。不调整签署或执行语义。
- 已有真实validated链可完成其回调；其他提交走共享分流，无配置自动确认、配置审批建立真实链、驳回重提重建。两类回调要求实际review与对应结果，仅从draft推进，终态重复回调无副作用，不重读策略、不再次发起审批。一般合同原回调循环结束后无条件action_confirm会让部分审批重新进入提交路径，本节删除该递归编排。
- L1 ci.local.iteration PASS（contract-approval-iteration.log）。L2共享审批42、native coverage8+24=32通过（contract-approval-tests.log，begin/record42），执行两类真实提交与回调，覆盖有/无配置、重提、部分审批后配置关闭、完整回调和缺review反例；既有签署回归随native目标通过。无ORM/数据库写入，无前端重建。
- 采购button_confirm仍按可变配置过滤执行集合，物资计划仍固定申请审批并有直接批准路径，已读取直接方法明确后续责任；不是重新全仓盘点。合同后续执行入口前置条件、其余单据族与付款局部审批编排仍须收敛；两项原生状态动作缺口、受管模块升级和真实业务验收继续保留。总体active，不推送/合并/目标部署。


### 53.27 采购确认集合按真实审批结果形成

- 85e1bff94 clean起步；P1 smart_construction_core.purchase_extend。button_confirm复用_start_submission_review，新提交无配置或已有review且validated才进入to_confirm；不再第二次读取当前策略来过滤集合。保留项目暂停/关闭校验、原生super采购确认及已有成本台账调用。删除重复_requires_purchase_approval/_request_purchase_validation。
- 审批中关闭配置无法确认；驳回重提建立新链；批准/驳回回调都要求真实review结果。非draft/sent重复确认不触发原生确认或台账，也不误提示“已提交审批”。该状态分流不替代原生采购数量、供应商、权限、双重验证及账务规则。
- L1 ci.local.iteration PASS（purchase-approval-iteration.log），L2 verify.payment.approval_state_machine.unit 43项PASS（purchase-approval-tests.log，begin/record43）。新增真实button_confirm执行，隔离原生父类与台账协作者，覆盖无配置、有配置、驳回重提、validated、在途关闭及重复确认；这不证明真实原生采购/成本台账ORM行为，相关集成验收仍必要。
- 不重建前端、不写验收业务数据；物资计划固定审批/直接批准、其余单据类型、付款局部编排和合同执行前置条件继续待收敛，两项原生动作产品缺口未关闭。后续仍需受管模块升级和真实配置/业务闭环，不把函数测试外推为总体完成。


### 53.28 物资计划提交/批准/驳回接入共享机制

- 36fa7a954 clean起步；P1 smart_construction_core物资计划生命周期。提交保留发起权限、业务锚点、单位归一、编号、提交人/时间及审计，改用共享配置分流。无配置直接approved，approved_by=False，不伪造人工批准人或validated；自动结果使用material_plan_approved审计且action_submit来源。
- action_approve委托已有共享真实审批决定，action_reject委托新增共享_reject_submission_review；有显式意见时核对真实reviewer/sequence后写意见并走原生_rejected_tier，无意见保留原生驳回向导。旧动作不再直接写批准/驳回状态。回调要求review及对应validated/rejected，只有submit可推进，部分/重复回调不再触发错误状态变更。保留物资经理限制、待办清理及审计；原生驳回回调从真实review取意见。
- L1 ci.local.iteration通过（material-approval-iteration.log）；最终补回两处原有待办清理后定向生产方法编译及45项测试通过（material-approval-tests.log，begin/record45），未变架构/路径规则沿用L1结论。测试覆盖真实物资提交/批准与回调、自动批准人为空、部分审批、完整/重复批准、缺事实驳回，以及共享驳回的实际审批人、意见与向导返回。真实ORM权限/事务/多级运行仍待，函数协作者不能替代该验收。
- 未改前端/XML、不重建、不写业务数据。尚待付款局部批准/驳回也复用共享服务、出库和其他未接入业务单据范围、合同执行前置条件、两项原生动作缺口及受管升级/真实业务验收。总体active，不推送/合并/目标部署。


### 53.29 付款批准/驳回消费共享决定服务

- b20352338 clean起步，P1 smart_construction_core付款适配。action_approval_decision改调共享_approve_submission_review；action_approval_reject删除本地review筛选/写意见/原生驳回编排，改调共享_reject_submission_review。财务权限、金额一致性、余额/提示、驳回必填原因、付款完成状态守卫保留，不把领域规则移入共享服务。
- 共享当前审批人/步骤权限失败使用AccessError，缺实例或不合法审批状态仍为业务错误；付款既有错误审批人拒绝语义未降级。原生意见向导action完整返回，尚未提交意见时付款保持submit。
- L1 ci.local.iteration PASS（payment-shared-decisions-iteration.log），L2 verify.payment.approval_state_machine.unit最终46项PASS（payment-shared-decisions-tests.log，begin/record46），既有付款真实方法回归现在经过共同服务；新增付款原生向导返回及不提前状态变更反例。无模型字段/XML变化，不重建前端，运行态重载与前批XML升级统一待执行。
- 此处完成已接入付款消费者的重复编排退出；不等于所有业务单据已覆盖。下一步材料出库、既有配置/运行支持缺口及合同执行边界仍按原产品范围收敛；两条原生状态动作登记和真实ORM/浏览器审批闭环保持未完成。


### 53.30 材料出库审批与实际出库分离

- 1b62c67f4 clean起步；P1 smart_construction_core材料出库生命周期。原action_issue仅对loss读取配置，批准回调直接_complete_issue写库存/成本；不符合提交统一分流及审批不代替业务执行。新增approved（已批准）状态，submitted明确审批中；提交对issue/return/transfer/loss共同调用共享服务，无配置直接approved、有配置等待真实review。启用审批却规则只覆盖部分类型仍按共享服务报缺规则，不静默放行其他类型。
- 审批回调要求真实review结果，通过仅submitted→approved，驳回submitted→draft并记录原因/审计；删除loss专属配置/申请编排。实际action_issue要求approved且共享批准事实门禁通过，再调用原_complete_issue。项目成本、退回数量锁、调拨入库、库存执行逻辑未改，审批不执行它们。主单与明细修改/删除锁加入approved，取消可从approved进入cancel。
- workflow profile和原生页面同步新增approved，只在approved暴露确认出库；新增真实can_review/validation_status批准驳回按钮。顺带修正直接相关旧不一致：reset模型只接受cancel，契约/原生旧submitted重置入口改为cancel；不改重置业务方法。
- L1 ci.local.iteration PASS（outbound-approval-iteration.log）；L2共享审批47、native32、semantics15通过（outbound-approval-tests.log，begin/record47），state_phase16通过（outbound-phase-tests.log，65模型状态覆盖）。新增执行四类出库真实提交/回调/出库入口，确认有/无配置均不会在审批阶段触发_complete_issue，未批准拒绝执行、批准后仅显式办理才调用。库存/台账协作者隔离，真实ORM业务验收仍待。
- 新增selection值和XML必须受管模块升级；不自动将既有submitted数据认作approved。既有无审批实例submitted记录需要在验收/迁移时逐项处理，现有受控cancel→draft→重新提交可用，不偷偷批量改历史数据。已在审批中的真实validated回调可完成批准；已issued事实不改。未执行数据库写入或前端重建。
- 配置选择17类/运行支持15类不等于全业务单据完成；后续继续既有职责范围内必要接入、合同执行边界、两项原生动作缺口与受管升级/真实验证。总体active，不推送/合并/目标部署。


### 53.31 项目合同执行入口与既有批准契约对齐

- 665245103 clean起步。P1 smart_construction_core项目合同生命周期及三张原生合同表单。workflow已仅confirmed声明activate，但action_set_running及原生按钮仍接受draft。本批执行入口改用共享_assert_submission_approved(confirmed)，关闭入口在原confirmed/running状态限制和明细检查外，同样要求既有实例通过。不读取当前配置推翻自动批准，不允许草稿直接执行。
- 三张原生合同表单开始执行按钮改为confirmed条件，保留合同经理组。有效契约既有状态职责不变；原始models、收入合同、支出合同投影均验证只有confirmed提供action_set_running。保留原运行/关闭状态消息和无明细不能关闭的业务校验。
- L1 ci.local.iteration PASS（contract-execution-iteration.log），L2共享审批48、native8+25=33通过（contract-execution-tests.log，begin/record48）。执行真实开始/关闭方法，覆盖草稿包括有validated实例也拒绝、自动批准后配置变化可执行、pending拒绝、完整review通过，以及关闭明细检查；解析实际XML核对三张表单与三类profile动作。
- XML仍待统一受管升级，真实权限/运行尚未验证；无数据库写入、无前端重建。后续需要对既有审批支持清单之外的必要业务单据确认有效契约接入，处理两项原生动作产品缺口，并运行已积累改动的受管升级/定向ORM和真实业务闭环。总体目标继续active，不据这81项窄测试宣称全系统完成。


### 53.32 累计审批改动受管升级与付款只读页面验证

- 4b8c4397e clean候选。P4执行既有受管入口验证P1累计模型/XML，不新建环境。目标角色=内部隔离验收租户，tenant/environment=sc_frontend_acceptance/local；非平台控制库、非行业目录、非客户生产库，既有fixture允许，客户生产数据不进入本次操作。preflight确认project=sc-fe-r2-p1-01、dbfilter=^sc_frontend_acceptance$，db/redis/filestore分别sc_fe_r2_p1_01_db/redis/odoo。日志approval-runtime-preflight.log。
- L3 make acceptance.module.upgrade SC_ACCEPTANCE_RUNTIME_PROFILE=local MODULE=smart_construction_core CODEX_MODE=gate CODEX_NEED_UPGRADE=1成功，真实registry加载66.793秒并正常退出（approval-module-upgrade.log）。升级初始日志目录不可创建后回退stdout，完整日志已留存；不是模块加载失败。受管入口重建其登记redis容器，未更换数据库或卷。
- make backend.acceptance.up受管识别旧SC_SOURCE_REVISION后替换旧后端，重新加载4b8c4397e2a0de6b24749f2a1826e8c7bc13629f；source fingerprint=12831d00b85a6886cb51fd23ae21641362e6f5d724e2f067eb20532664d0dfb6。backend.acceptance.health PASS，端口18082；日志approval-backend-up.log/approval-backend-health.log。此为本地验收更新，不是目标环境部署或主线集成。
- L4复用原5180静态产物，TPL07_SCOPE=detail-state make verify.frontend.standard_page_type.browser SC_ACCEPTANCE_RUNTIME_PROFILE=local，29项PASS（approval-detail-state-browser.log；tpl07-1790772544286/report.json）。既有finance角色读取付款1710 approved，双视口官方详情状态限制反馈通过，errors=[]、forbiddenWrites=[]，无业务写入。build.base_sha仍0d2c6190a6df7dcbd90f5f1dad23a18fea3fdfff，entry=/assets/index-BEqhG955.js，entry_sha256=4d954cbf38b86a8ab8e4c9cf383229dd7f70908b09743c7802f0dd32c1084aa5；端侧输入不变所以不构建。
- 该29项只证明共享页面消费已加载契约，不证明审批办理闭环。现有business_config_approval_runtime_smoke允许validation_status=no，finance_document_tier_runtime_smoke通过SQL/_set_validated伪造结果，均不能直接用于本次真实审批验收；后续应在现有工具上修正真实review执行及配置恢复，不新增fixture权威。未运行这些不适用工具，不以旧证据冒充新规则通过。
- 已完成本候选L3升级与所述只读页面验证；全单据覆盖、两项原生产品动作、审批开关/多级链/异常回滚和真实业务办理等仍未完成，总体active。无推送、合并或目标环境部署。


### 53.33 既有审批smoke改为真实review并完成受管运行

- 9bf7c6e9b clean起步；P4验证工具，业务产品输入沿4b8c4397e加载版本不变。复用business_config_approval_runtime_smoke与现有verify.business_config.approval_runtime：显式SC_ACCEPTANCE_RUNTIME_PROFILE=local时经现有operation_entry→standard-approval-runtime，复用preflight和backend代码身份检查后在受管后端执行。其他原入口保留，未组装新环境/凭据/fixture体系。
- smoke不再接受no审批状态：启用配置必须有真实review且waiting/pending；修改为无需审批后，待办实例不能通过回调放行；遍历真实reviewer_ids，以with_user用户身份和can_review选择当前审批人调用validate_tier，要求每次真实review状态推进，最多32步。完成后业务approved且全部review approved；另验证无配置提交approved、无review且validation_status=no。不写SQL或validated字段，不强制调用审批完成回调冒充审批成功。
- 保留原工具事务内创建项目/客商/费用及附件方案，不新增持久fixture；finally回滚，invalidate缓存后回读原策略字段/步骤身份一致，并核对临时项目/客商/费用不存在。PASS仅在恢复核对后输出。目标仍sc_frontend_acceptance内部隔离验收租户、精确filter与既有filestore，沿53.32身份；无付款/入账操作。
- L1 ci.local.iteration通过（real-review-smoke-iteration.log），工具py_compile/bash语法通过；L2既有standard_preview.unit9通过（real-review-wrapper-tests.log）。首次真实运行失败：原项目helper未设置company_id，现行费用创建校验拒绝；ROLLBACK=VERIFIED，归因P4旧测试数据契约漂移（real-review-runtime-project-failure.log）。补项目company_id=_env().company.id，未改产品校验；脚本编译后受管定向重跑。
- make verify.business_config.approval_runtime SC_ACCEPTANCE_RUNTIME_PROFILE=local真实运行5项PASS、ROLLBACK=VERIFIED（real-review-runtime.log）。这是费用单代表审批运行证据；不能外推全单据、多级指定顺序、错误审批人、缺规则、驳回重提、浏览器操作或付款/库存事务均已完成。未重载未变后端、未升级第二次、未构建前端。
- 下一步沿同一工具补必要异常/多级和恢复断言，同时继续全单据有效契约缺口及两项原生动作收口。批次局部验证通过，总体active，无推送/合并/目标部署。


### 53.34 真实缺规则拒绝与驳回重提闭环

- b65d1c839 clean起步，P4仅扩展同一business_config_approval_runtime_smoke。沿53.33受管验收身份，backend4b8c4397e及前端输入不变，不重载/升级/构建。L1 ci.local.iteration通过（approval-exceptions-iteration.log），脚本编译通过；受管封装输入未变，9项封装证据复用，不重跑无关测试。
- 临时将已有有效步骤金额下限置高于测试费用，配置仍启用。提交在保存点内失败，错误为缺匹配规则，回读仍draft且无review；随后恢复原步骤金额条件。不是删除规则或绕过产品验证。
- 真实当前审批人经共享驳回服务与原生_rejected_tier执行，业务回draft，驳回原因保留，sc.audit.log的expense_claim_rejected恰好1条。原生tier.validation在submit→draft时删除本次review，validation_status回no；首次断言错误要求rejected持久存在而失败，回滚仍VERIFIED（approval-exceptions-native-reset-failure.log）。核对原生_allow_to_remove_reviews后修正工具断言，未为测试修改产品。
- 重提创建新的真实review IDs，与旧ID不相交，再由真实审批人validate_tier完成approved/validated。保存原策略和步骤active/sequence/group/amount/tier_definition身份，最终rollback后回读完全一致，临时项目/客商/费用不存在。
- make verify.business_config.approval_runtime SC_ACCEPTANCE_RUNTIME_PROFILE=local最终8项PASS、ROLLBACK=VERIFIED（approval-exceptions-runtime.log）。其中原5项随着同一配置事务复验，新3项是缺规则保存点回滚、驳回原因/审计及新链重提。仍仅费用代表路径，不代表指定多级顺序/越权/所有业务模型及前端办理均通过。总体active；两项原生动作缺口、全单据必要能力及剩余真实业务验收继续推进，无远端或目标部署。


### 53.35 多级运行发现停用步骤未撤销定义，修复共同同步

- 7819842e7 clean起步，P4原smoke增加两级linear与现有fixture非审批人拒绝场景，事务结束核对原策略/步骤恢复。首次配置创建遗漏必填approval_scope_key，补既有组到岗位映射（approval-linear-scope-failure.log），未改约束。第二次发现实际生成3条review；定向诊断确认两条新linear步骤之外仍有旧“财务中心审核”active定义，approve_sequence=False（approval-linear-runtime.log）。所有失败均ROLLBACK=VERIFIED。
- 归因P1产品缺陷：sc.approval.policy.sync_tier_definitions默认active_test隐藏停用step，无法把旧tier.definition.active同步为False，也无法更新其模式。修复为在既有同步流程使用active_test=False遍历完整步骤；不扩大模型范围、不删除审批实例、不新增引擎。新增执行实际同步方法的回归：停用步骤必须向旧定义写active=False。
- L1 ci.local.iteration PASS（approval-inactive-sync-iteration.log）；L2共享审批49项PASS（approval-inactive-sync-tests.log）。当前提交是待运行复验候选，需受管重载后端后再次运行同一多级场景；无字段/XML变化，不需再次模块升级或前端构建。总体目标保持active，不能把定位或纯测试当作多级运行已通过。


### 53.36 停用定义修复运行通过，两步与非审批人拒绝验证

- 4880989f8候选经backend.acceptance.up受管重载成功（approval-inactive-backend-up.log），无模块再次升级、无前端构建。原失败完整日志保留approval-linear-stale-definition-failure.log；未改配置绕过旧定义缺陷。
- 同一受管verify.business_config.approval_runtime最终12项PASS、ROLLBACK=VERIFIED（approval-linear-runtime.log）。新证据为正好两条linear review、既有非审批fixture角色被AccessError拒绝且无review推进、一次validate_tier仅完成一级且业务仍submit、第二次完成后才approved。原8项随同一事务仍通过，策略/步骤含approval_scope_key回读恢复、临时单据不存在。
- 覆盖边界：两个步骤复用同一合资格审批组，证明分次推进而非两个不同人的岗位流转；非审批人拒绝可能发生于对象访问或审批能力层，不宣称覆盖所有权限层。尚未断言配置sequence10先于20的精确方向；此前诊断显示原生review排序与配置序号需要进一步核对，不能把本12项当作配置顺序完全一致。下一步补绑定definition/step的顺序断言，再处理必要全单据与两条原生业务动作缺口。总体active，未推送/合并/目标部署。


### 53.37 全单据共同审批适配修正配置步骤顺序

- dbcb0545f clean起步，沿用所有业务单据统一审批决策；已有17类配置/15类运行支持不是范围上限。P1 smart_construction_core共同审批适配，P4既有rollback smoke补definition绑定断言；非用户专属规则，不在前端或测试工具实现审批语义。
- 新断言在现有受管sc_frontend_acceptance/local环境实证失败：实际definition顺序[4983,4982]，配置10→20对应[4982,4983]；ROLLBACK=VERIFIED（approval-order-runtime-failure.log）。OCA request_validation固定sequence desc，而配置按sequence,id升序。共同适配改用配置排序位置的负值作为原生优先级，保证零值、负值和并列序号也保持配置顺序；不修改OCA，不重排在途review实例。
- L1 ci.local.iteration PASS（approval-order-iteration.log）；L2 verify.payment.approval_state_machine.unit 50项PASS（approval-order-tests.log，begin/record50）。新增执行真实_tier_definition_vals的方法测试，按原生降序恢复配置顺序。方法改动无需模块升级，提交后受管重载及真实顺序复验待执行；前端输入未变，不构建/不跑浏览器矩阵。
- 既有持久tier.definition需通过原配置同步机制重新投影才应用新顺序；本轮不擅自批量改租户配置。在途实例不迁移。全单据缺失接入、不同审批人流转及两项原生业务动作仍为产品缺口；总体active。


### 53.38 配置顺序修复真实运行通过

- 7c3667740 clean候选经backend.acceptance.up受管重载，沿用sc_frontend_acceptance/local既有身份（approval-order-backend-up.log）。未再次升级模块、构建前端或运行无关ORM。
- verify.business_config.approval_runtime 12项PASS、ROLLBACK=VERIFIED（approval-order-runtime.log）：配置10→20对应definition与实际review.sequence升序完全一致；首次真实validate_tier批准的definition明确是第10步，业务仍submit；最后一步才approved。启用、关闭、在途配置变化、缺规则、驳回重提、非审批人拒绝同事务仍通过，原策略/步骤回读一致、临时单据清理已核对。
- 本批配置顺序缺陷定向验收完成；复用同一组审批人，不声称不同岗位链或全业务单据已验收。持久旧定义重新同步、支持清单外必要单据、两项原生业务动作仍按既有产品缺口推进。总体active；主线未集成、目标未部署、全产品用户验收未完成。


### 53.39 付款执行状态动作与既有领域契约对齐

- 34c4777b8 clean起步；P1 smart_construction_core工作流契约投影，非客户配置、非前端推断。只读取既有两项登记缺口及直接模型/原生视图/领域契约。payment-execution.yaml已声明paid独立reverse_payment→cancel，而profile仍给paid错误action_cancel、给draft提前action_paid。本批按权威领域边界修正：draft提交/取消，confirmed付款/取消，paid独立撤销付款；新增reverse_payment动作键绑定既有action_reverse_payment，标签撤销付款。
- purpose沿既有cancel_record表示目标取消事实，但key/method明确区分付款前取消与已付款冲销；不改台账、冲销原因、财务授权或cancellation_kind。登记中错误paid→reversed说明随已解决条目退出；实际状态是cancel/payment_reversed。合同履约事件尚缺共享审批接入，继续为产品缺口，不通过直接补action_reject投影掩盖。
- L1 make ci.local.iteration PASS（payment-reversal-contract-iteration.log）。L2 native coverage 8+26=34（payment-reversal-contract-tests.log，begin/record34），workflow_action_semantics15（payment-reversal-semantics-tests.log），payment approval50（payment-reversal-approval-tests.log）全部PASS。新增实际_available_actions执行覆盖六种状态及target/label/purpose，与原生财务组、付款/冲销状态条件核对。注册27项=12helper+14navigation+1state gap。
- 方法常量变化无字段/XML变化，无需模块升级或前端构建；后端受管重载及有效契约/浏览器冲销入口仍待验证，不以离线测试宣称资金冲销业务验收通过。不重新执行费用审批12项（输入无依赖变化）。仍需全单据必要接入、持久审批定义同步及相关实际业务验证。总体active，未推送、合并、目标部署。


### 53.40 合同履约事件接入共同审批，原生未声明状态动作归零

- 747d380ef clean起步。P1 smart_construction_core合同履约事件；现有直接状态批准/驳回且无配置支持属于已确认全单据产品缺口。新增tier.validation继承、project公司相关字段、驳回原因；审批配置选择、同步支持、OCA可选模型、金额影响条件及既有回调XML共同接入。复用已登记finance_document_tier_actions.xml，未新建模块或审批引擎。
- action_submit保留日期/合同项目校验，在submitted调用共同_start_submission_review；无配置批准但不完成事件。兼容action_approve/action_reject委托共同实际review决策；通过/驳回回调要求submitted及真实review最终结果，驳回保留意见；完成要求原approved条件与共同批准事实门禁。原生按钮改validate_tier/reject_tier并受can_review/validation_status约束，驳回后可重提。profile同步审批动作、重提，去掉模型不允许的approved取消；原生取消同样限draft/submitted/rejected。
- L1 ci.local.iteration PASS（contract-event-approval-iteration.log）。L2审批51、native8+27=35、semantics15 PASS（contract-event-approval-tests.log）。新增实际方法测试覆盖有/无配置分流、共同审批委托、伪造/中间回调拒绝、真实通过与独立完成、业务anchor失败；新增实际契约当前审批人/重提/完成动作与原生入口一致性测试。补登记新直接输入后旧begin回执被正确拒绝，按新输入重新begin并执行51项后record（contract-event-approval-final-*）；不冒用旧身份。
- 最后补原生驳回原因字段显示，XML解析通过，无业务方法再改。登记剩余合同事件直接action_reject按钮已退出，native registry=26（12helper+14navigation），state_transition_undeclared=0只表示当前登记缺口已编码，不能证明全单据覆盖或运行正确。detail.action-state继续open。
- 新字段/继承/selection/XML需受管模块升级与后端重载；本提交尚未执行，必须先完成再做真实事件审批/拒绝/重提验证。同批付款冲销有效契约仍需运行核对。前端不变，不构建；不以纯测试宣称全系统接管或审批验收完成。总体active，无推送、合并或目标部署。


### 53.41 合同履约事件受管升级与真实审批通过

- b985a026b候选，P4运行验证P1新增模型能力；既有内部隔离验收tenant/database=sc_frontend_acceptance，profile=local，project=sc-fe-r2-p1-01，精确filter=^sc_frontend_acceptance$及sc_fe_r2_p1_01_db/redis/odoo卷复用。acceptance.module.upgrade MODULE=smart_construction_core CODEX_MODE=gate CODEX_NEED_UPGRADE=1成功，registry66.151秒（contract-event-module-upgrade.log）；backend.acceptance.up受管重载完成（contract-event-backend-up.log）。前端输入不变，无构建。
- P4在原business_config_approval_runtime_smoke同一回滚事务增加合同事件5项，不新增环境/fixture权威。不覆盖已有事件策略：精确公司/全局范围内如已有策略（含停用）即拒绝。先验证不存在配置时submit→approved且无review、不自动done；再事务内创建策略/步骤，复用已有审批组，真实request_validation及with_user审批人validate_tier→approved，显式action_done后才done。
- 新事件真实审批人经共同拒绝服务→原生驳回→业务rejected，原因一致；重提新review IDs与旧链不相交，真实批准到approved。临时事件/策略和原项目/客商/费用统一登记，finally rollback后均不存在；原费用策略/步骤完整回读一致。
- L1 ci.local.iteration PASS、py_compile通过（contract-event-runtime-iteration.log）。受管verify.business_config.approval_runtime最终17项PASS、ROLLBACK=VERIFIED（contract-event-runtime.log）：既有费用12项及新增事件5项。这是本次新增tier/config/callback真实运行检查，不是全模块ORM扫描；封装未变，复用原9项wrapper证据。最后仅修改脚本说明为实际两类覆盖，不失效执行证据。
- 本轮证明合同事件所述模型审批链，但尚未验证合同事件的最终ui.contract/浏览器办理、不同审批岗位以及全部业务单据；付款冲销有效契约/真实执行仍待。登记state gap归零不代表全系统交付，detail.action-state继续open。主线未集成、目标未部署、用户整体验收未完成，总体active。


### 53.42 已付款官方详情动作验证，合同事件缺可用页面记录

- 45ec5095f clean起步，P4在既有standard_page_type_browser新增approval-actions只读范围；复用受管入口/5180产物/fixture登录，api.data只查询现有记录，不创建业务数据、不执行资金冲销。受限TPL07_APPROVAL_MODEL仅允许合同事件或付款执行，用于独立未覆盖面的检查，未知模型拒绝。L1 ci.local.iteration PASS（approval-actions-browser-iteration.log），新增分支node --check通过；后续模型选择增量语法通过。
- 首次合同操作员fixture_role_contract_operator查询sc.contract.event成功但当前公司8作用域内records=[]，断言失败（approval-actions-browser.log；tpl07-1790773719865/report.json），errors=[]、forbiddenWrites=[]。这是当前授权范围缺可用浏览器验收记录，不证明全库为空，也不是已通过。未换高权限角色绕过、未造额外fixture；合同事件UI验收保持pending。
- 独立执行TPL07_SCOPE=approval-actions TPL07_APPROVAL_MODEL=sc.payment.execution受管browser，finance在原授权范围读取现有paid记录186，16项PASS（payment-reversal-browser.log；tpl07-1790773738989/report.json）。有效ui.contract模型/state一致，actionRuleList中的action_reverse_payment为原生object动作、label撤销付款、actionSemantics=business/cancel_record/contract.action；页面该按钮恰好1，取消/已付款按钮0。官方readonly详情单一路径且有非零facts，1440/390无溢出，截图在同一目录，errors=[]、forbiddenWrites=[]。
- 复用原静态build身份和已加载b985a026b后端（后续仅工具/记录变化），未构建/升级/重载。该16项证明冲销入口呈现及有效契约，不证明真实资金冲销成功；不点击按钮制造资金副作用。工具捕获的actionSafety仍标safe，后续需核对既有资金动作确认规则归属，不能从本次只读页面通过推出执行安全已验收。
- 总体active：合同事件页面数据前提、资金冲销实际办理、不同审批人/必要全单据覆盖等继续；登记归零不关闭detail.action-state。未推送、合并或目标部署。


### 53.43 付款冲销由原生契约声明执行前确认

- 02722f3d1 clean起步，P1原生payment_execution视图；P4定向验证。追踪既有parser→actionSafety→contractActionConfirmationPrompt→共享IntentConfirmationDialog，确认能力已存在，缺的是冲销原生按钮confirm声明。原生补后果说明：冲销对应台账并将已完成付款申请退回已批准，不给前端增加模型判断或词法猜测。
- L1 ci.local.iteration PASS（payment-reversal-confirm-iteration.log），L2 native8+28=36 PASS（payment-reversal-confirm-tests.log，begin/record36）。新增执行实际parser安全投影方法，读取真实XML并断言danger/requires_confirm/准确文案。浏览器定向分支增加有效契约确认断言、点击打开后取消，沿既有拦截禁止业务写入；node --check通过。
- 本候选XML需受管升级后验证页面，未以静态测试宣称确认框已运行通过。前端源码/产物未改，无需构建。全单据审批及合同事件页面数据前提等原缺口保留；总体active，无远端/目标部署。


### 53.44 付款冲销确认框真实页面验证通过

- 20f359069经受管acceptance.module.upgrade及backend.acceptance.up成功，日志payment-reversal-confirm-upgrade.log/payment-reversal-confirm-backend.log；沿用sc_frontend_acceptance/local、精确过滤与原卷，无新环境。既有5180静态产物不变。
- TPL07_SCOPE=approval-actions TPL07_APPROVAL_MODEL=sc.payment.execution受管browser19项PASS（payment-reversal-confirm-browser.log；tpl07-1790773977925/report.json）。finance既有paid186有效契约requires_confirm=true/classification=danger，点击撤销付款打开共享确认弹层，后果文案与契约一致，点击取消后关闭且forbiddenWrites=[]，errors=[]。原双视口/单一官方详情/入口状态检查继续通过。未执行实际台账冲销，未改付款数据。
- 该声明与共享消费闭环完成，合同事件页面无授权范围数据的前提仍未变化，不重试；全部业务单据审批覆盖与真实资金事务未由本次通过推定。下一步沿已登记必要业务缺口继续收敛，包括sc.plan原生状态条件旧不一致及现有配置支持之外的单据；不重新全仓审计。总体active，主线/目标部署/整体验收未完成。


### 53.45 计划原生按钮与状态机/契约对齐

- d97d8bc45 clean起步，P1 sc.plan原生视图。复用53.16登记缺口，只核对plan_management.py、原生视图及既有workflow profile。模型完成仅in_progress、重置仅cancel、取消仅draft/confirmed/in_progress；原生此前分别额外允许confirmed、所有非draft、所有非done/cancel。按模型现有规则修正三个invisible表达式，profile已正确不再修改。
- L1 ci.local.iteration PASS（plan-state-iteration.log）；L2 native8+29=37 PASS（plan-state-tests.log，begin/record37）。新增测试执行模型五个实际动作，隔离日期/业务anchor协作者，逐draft/confirmed/in_progress/done/cancel/unknown比较可执行方法、实际XML可见集合和实际_available_actions输出一致。测试不是按标签或方法名称推导许可。新增相关模型/视图及前轮parser实际依赖至原native_action_coverage输入登记。
- 本批只修正呈现状态边界；sc.plan尚无tier继承/审批配置支持，仍直接确认，按所有业务单据统一规则这是必要产品缺口，不计作自动审批已接入。下一步在同一产品批次补既有共同审批适配后统一受管升级与真实验证，不为本次三个视图属性单独升级/浏览器矩阵。既有付款19项及审批17项不因本次无依赖变更重跑。
- XML待受管升级，不能宣称已加载；前端产物不变。总体active，主线未集成、目标未部署、整体验收未完成。


### 53.46 计划单接入共享审批配置与运行机制

- 222b47903 clean起步；P1 smart_construction_core的sc.plan业务能力，遵循所有业务单据统一审批要求。复用tier.validation与sc.approval.policy，新增配置选择/同步支持/OCA模型名单和既有回调XML；公司字段沿用原模型，不新增公司权威。新增reject_reason保存驳回意见。非客户特例，不由前端或工具决定审批分流。
- action_confirm保留draft和日期/节点前置校验，调用共同_start_submission_review；配置审批则保持draft由原生validation_status表达审批进度，未配置则confirmed。真实review validated回调检查计划条件后confirmed，伪造/中间结果不推进；真实rejected回调保存原因，重提依共同服务重置旧链。开始/完成继续独立执行，在既有状态/日期/节点校验之外加入共同批准事实门禁。
- 原生视图添加can_review/validation_status与validate_tier/reject_tier，审批中不重复显示确认；profile声明同一审批动作。上一轮完成/取消/重置条件继续保持。兼容原draft/confirmed/in_progress/done/cancel状态，没有新状态或自动迁移已有业务记录。
- L1 ci.local.iteration PASS（plan-approval-iteration.log）；L2审批52、native8+29=37、semantics15 PASS（plan-approval-tests.log，begin/record52）。新增执行实际确认/回调/开始/完成方法，验证配置分流、伪造/中间结果拒绝、通过不自动开始、独立开始/完成及节点完成校验仍调用；视图状态测试使用无配置协作者继续校对原动作状态边界。新增模型/视图输入注册于原审批检查。
- 新字段/tier继承/selection/XML需统一受管升级，53.45视图亦随本批加载。下一步扩展同一rollback smoke验证计划有/无配置、真实审批/驳回重提及独立开始/完成，再做相关有效契约消费；本次尚无真实ORM通过证据。前端输入不变，无构建；总体active，未推送、合并或目标部署。


### 53.47 计划单共享审批真实运行通过

- 478215ca4候选，P4复用既有受管acceptance.module.upgrade与backend.acceptance.up验证P1累计53.45/46字段/原生视图/回调。sc_frontend_acceptance/local内部隔离验收租户、sc-fe-r2-p1-01、精确filter及原db/redis/filestore卷不变。升级registry68.600秒成功（plan-approval-upgrade.log），后端重载成功（plan-approval-backend.log）；前端未构建。
- 原rollback smoke扩展计划5项，创建记录和策略全部在原事务登记，若公司/全局已有计划策略（含停用）则拒绝覆盖。无配置确认到confirmed、无review、无实际开始日期；配置下draft且真实review pending/waiting，action_start在savepoint明确拒绝，无开始日期。实际审批人validate_tier通过后仅confirmed，显式action_start才in_progress并写actual_start，显式action_done才done并写actual_finish。
- 真实审批人经共同拒绝服务驳回，draft保留原因；重提review IDs与旧链不相交，原生批准后confirmed且原因清空。finally rollback回读原费用策略/步骤一致，所有临时计划/事件/策略/项目/客商/费用不存在。没有直接写审批结果，没有新环境或持久fixture。
- L1 ci.local.iteration/py_compile PASS（plan-approval-runtime-iteration.log）。受管verify.business_config.approval_runtime22项PASS、ROLLBACK=VERIFIED（plan-approval-runtime.log），其中费用12+事件5沿同一事务验证、计划新增5。封装不变，原wrapper9证据复用；不以22项代表全部业务单据或浏览器完成。
- 计划有效契约/浏览器、不同审批岗位、实际金融冲销与总体必要单据覆盖继续待验。沿已有profile顺序定向核对下一项sc.construction.diary：模型仅mail继承、直接action_confirm/action_done，profile draft仍包含complete，未接共享审批，是既有正式单据的后续产品缺口；本轮未改日志模型，不新建盘点表。总体active，无远端/目标部署。


### 53.48 施工日志共享审批接入，关闭草稿直接完成

- 75834d4a1 clean起步，P1 smart_construction_core施工日志正式业务能力。原模型无tier继承、配置无支持且draft可直接done，属于全单据统一审批缺口。新增tier继承、项目公司相关字段、驳回原因，配置选择/同步支持/OCA模型列表及原回调XML纳入sc.construction.diary。沿既有机制，不新建审批引擎或前端业务分流。
- 确认保留日期、标题、日志类型、非负人数及至少一项内容检查；调用共同_start_submission_review，配置审批保持draft等原生review结果，无配置校验后confirmed。通过回调只接受真实validated且重新校验内容；驳回保留真实意见，重提复用共同重置。完成仅confirmed且共同批准事实校验通过，保留内容校验，不由审批自动完成。
- 原生增加真实审核按钮及can_review/validation_status，profile同一审批动作，draft移除complete；完成仅confirmed。原生取消此前误显示于done，按模型原draft/confirmed范围对齐，legacy取消拒绝业务规则未改。已有legacy_confirmed状态/历史数据未迁移。
- L1 ci.local.iteration PASS（diary-approval-iteration.log）。L2审批53、native8+30=38、semantics15 PASS（diary-approval-tests.log，begin/record53）。实际方法测试验证无/有配置、草稿/审批中不能完成、伪造/部分回调不推进、真实通过后独立完成、内容不满足拒绝；实际投影与原生完成/取消/审核人条件一致。新模型/视图加入既有输入登记。
- 字段/继承/XML仍需受管升级、真实日志审批/拒绝重提验证，尚未执行。本次不重建前端、不重跑无关浏览器；不能以纯测试宣称全系统完成。总体active，未推送、合并、目标部署。


### 53.49 施工日志真实审批闭环验证通过

- cbd60bd63候选经既有acceptance.module.upgrade与backend.acceptance.up受管升级/重载成功（diary-approval-upgrade.log/diary-approval-backend.log）。继续复用内部隔离sc_frontend_acceptance/local、sc-fe-r2-p1-01、精确dbfilter及原卷；前端产物不变，不构建。
- P4原rollback smoke将计划的共同确认/审批/拒绝/重提检查复用于施工日志，模型限定为sc.plan/sc.construction.diary，只在创建字段与独立执行动作上区分。先拒绝覆盖该公司/全局任何既有策略，再创建事务内策略及业务记录，均进入原created恢复清单；不增加持久fixture权威。
- 新日志5项真实通过：无配置confirmed无review且不done；配置审批draft+真实review，savepoint内action_done明确拒绝；实际审批人validate_tier完成后confirmed，显式action_done才done；真实驳回保留意见；重提新review IDs与旧链不交集，通过后清空旧原因。没有SQL伪造审批结果或强制回调冒充审批。
- L1 ci.local.iteration和py_compile PASS（diary-runtime-iteration.log）。受管verify.business_config.approval_runtime27项PASS、ROLLBACK=VERIFIED（diary-approval-runtime.log），包括费用12、事件5、计划5、日志5；计划与日志共享工具改变，因此同事务复验相关链。原策略/步骤回读一致，临时项目/客商/单据/策略不存在。受管封装不变，原9项证据复用。
- 这证明所述模型审批循环，不证明项目经理角色端到端权限、最终页面契约及整个业务单据集合完成。下一步将计划/日志加入现有只读页面验收范围核对有效契约消费，按现有授权角色查已有记录；合同事件公司8无记录前提不变不重试。总体active，未推送、合并或目标部署。


### 53.50 计划/日志页面定向检查发现实际消费阻断

- b7d554d45 clean起步，P4扩展既有approval-actions浏览器范围，仅fixture_role_pm的sc.plan/sc.construction.diary；原backend cbd60bd63及5180产物不变。L1 ci.local.iteration PASS（plan-diary-browser-iteration.log），新增分支node --check通过。无写入/新数据/新环境。
- 两类现有记录查询均ok=true、公司8授权范围records=[]：plan-browser.log对应tpl07-1790774584870/report.json，diary-browser.log对应tpl07-1790774597249/report.json。不能称全库无数据，不改权限换角色取证，详情验收pending。
- 单独新增TPL07_APPROVAL_VIEW=create明确打开未保存新建表单，不是自动回退或替代详情验收。计划首次timeout（plan-create-browser.log；tpl07-1790774631462/report.json），已收到sc.plan/create且create=true有效契约，不能据presentationMode=workspace就认作工具等待错误。追加有界失败现场捕获（当前页正文/语义surface/截图），只重跑受影响计划并独立检查日志。
- 计划诊断失败（plan-create-diagnostic.log；tpl07-1790774686651/report.json）：实际data-form-composition=official-standard-form但data-state=error，页面“网络连接异常”；契约已到达，需继续定位后续失败请求。日志失败（diary-create-browser.log；tpl07-1790774692654/report.json）：明确invalid contract v2 snapshot，layoutContract.containerTree若干children仍含不允许的field_info，页面拒绝契约；该处属于P0有效契约/规范投影缺口，不放宽前端schema。两者errors=[]，但页面错误不能以JS无异常算通过。
- 当前已知早层阻断，不继续广泛浏览器/发布门禁。直接源码定位现有assembler _normalize_native_layout_nodes已有field_info→fieldInfo归一化，而_native_field_node仍deepcopy输入；尚未证明真实泄漏路径，未盲改或重复全仓扫描。下一步捕获该ui.contract的精确布局投影链并修正产生层，及计划失败请求；修复后只重验受影响页面。既有27项ORM只证明审批模型，不覆盖这些页面阻断。总体active，未推送/合并/目标部署。


### 53.51 新建页双故障分层定位，计划通过，日志重复后处理仍阻断

- fef872276起步。P4查原失败report发现计划forbiddenWrites实际含api.data/default_get；53.50“无写入”应解读未发生业务写入，不能描述为未拦截请求。api_data将default_get明确定义为读操作，工具白名单补此op，其他写入继续拦截。计划新建双视口12项PASS（plan-create-defaults.log；tpl07-1790774808335/report.json），无需产品修复；记录详情无数据仍pending，不混记。
- 现有失败诊断补当前ui.contract完整响应（仅approval-actions本地受限验收），日志再次捕获tpl07-1790774814944/report.json，确认不是P0归一化缺失：P1 core_extension_contract_normalizers.normalize_construction_diary_form在规范化之后为所有字段重复添加field_info。修复该行保留fieldInfo并移除旧别名，关系/必填/组件信息保留。L1 ci.local.iteration PASS（diary-alias-iteration.log），native8+31=39 PASS（diary-alias-tests.log，begin/record39），实际后处理方法回归覆盖别名不泄漏与信息保留。
- 338d5253f受管backend.acceptance.up重载（diary-alias-backend.log），无模型字段/XML变更不升级/构建。日志复验仍失败（diary-create-fixed.log；tpl07-1790774968894/report.json），field_info已不再报错，但runtimeContract.containerTree/widgetStatus/governancePatches及meta.governance_patches不允许，formStructureContract.slots引用name等字段未投影。证明同一重复行业后处理还有结构性冲突，不能据39单测称页面完成。
- 下一步核对并退役日志的重复布局重组/兼容投影路径，让原生视图及有效配置保有完整字段/结构；不继续逐个放宽schema或增加别名。计划误阻断关闭，日志页面阻断保持open，早层失败禁止广泛浏览器/发布门禁。审批27项只证明业务模型，不能替代此处消费。总体active，无远端/目标部署。


### 53.52 施工日志重复布局退出，官方新建表单通过

- c62e25241 clean起步。P1核对原生施工日志视图已完整承载主信息、期间经办、现场、正文、附件及驳回原因；标准合成契约已有对应formStructure。旧normalize_construction_diary_form按固定清单重建布局、向runtime/meta投兼容属性并裁掉字段，与权威合成冲突。删除core_extension最终调用和包装、删除105行独立重组实现；不再为这条路径逐项补别名，不改schema。
- 原拆分守卫从强制保留旧函数/compat治理字段改为禁止已退役路径复活，其他normalizer检查保留。测试执行实际最终处理函数，隔离工作流/无关财务协作者，确认注入审批动作后layout、formStructure、runtime/meta以及配置扩展字段保持原样，输入不被修改。新增直接生产依赖到原native检查输入，按最终输入begin/record39。
- L1 ci.local.iteration PASS（diary-native-exit-iteration.log）；native8+31=39 PASS（diary-native-exit-final-tests.log），normalizers_split_guard PASS（diary-native-exit-guard.log）。30ca72d76经受管backend.acceptance.up重载（diary-native-exit-backend.log），无模型/XML变化，不升级、不构建前端。
- 既有受管approval-actions diary/create浏览器12项PASS（diary-native-create-browser.log；tpl07-1790775130070/report.json）。PM公司8未保存新建页有效契约/官方ScForm、无未知字段渲染、无未保存审批/完成入口、1440/390无溢出，errors=[]、forbiddenWrites=[]。回读有效布局31字段节点，name/reject_reason/report_period_start/report_period_end/attachment_ids/header_description均保留。53.50/51日志新建页面阻断实质关闭；此前计划create12证据输入不变复用。
- 仍不等于已有记录办理验收：计划/日志/合同事件公司8无现有记录的详情前提未变化，真实审批27项只覆盖事务模型。下一步继续原工作流职责中的必要单据覆盖与配置/权限/页面组合缺口；总目标active，detail.action-state整体不升级。未推送、合并或目标部署。


### 53.53 抵扣登记执行边界与原生/契约对齐

- 69e1d4648 clean起步，P1税款抵扣登记，沿现有workflow下一个未接共享审批的正式单据定向核对，不扫描全仓。模型action_deduct、原生按钮及profile均允许draft直接deducted。先关闭该明确绕过确认边界：模型仅confirmed允许，profile draft移除complete，原生已抵扣仅confirmed。原生取消从原“非cancel/legacy”收紧到模型原draft/confirmed，防止deducted错误出现取消。
- 财务权限、默认抵扣日期/金额、_check_deduct_ready、公司承包人责任校验、_write_finance_authority、审计顺序保留；未改终态token保护、财务身份或历史规则。未新增自动抵扣。
- L1 ci.local.iteration PASS（tax-execution-state-iteration.log）；native8+32=40 PASS（tax-execution-state-tests.log，begin/record40）。执行实际action_deduct，覆盖五状态，只有confirmed走finance→ready→responsibility→authority→audit，其余在资金动作前拒绝；隔离余额协作者，不宣称真实台账通过。同一测试核对实际profile与原生条件。
- sc.tax.deduction.registration仍未tier/config接入，是后续必要产品缺口，不把confirmed状态条件当作审批接入完成。直接发现审批金额前提：deduction_amount/deduction_tax_amount在action_deduct才从发票金额默认补值；共享审批接入需先明确/复用金额准备职责，不能拿未补出的0作为金额阈值事实或静默忽略配置条件。下一步继续该直接适配。
- 模型/XML待受管升级，与后续完整审批适配合并运行验收；不为本次窄条件单独构建/升级/浏览器矩阵。已有日志新建12和审批27证据无依赖改变继续复用。总体active，未推送、合并、目标部署。


### 53.54 抵扣登记接入统一审批配置与真实审批链

- a8e36c9b7 clean起步。沿用所有业务单据统一审批目标，支持名单不作为范围上限。P1 smart_construction_core负责税务单据校验与动作；复用既有sc.approval.policy/OCA机制，P3用户配置决定是否审批；前端不增加业务分支。P4只扩展既有事务回滚验收脚本，不新增环境或fixture权威。
- 税务登记增加tier.validation、驳回原因、真实审批回调、配置可选模型/同步支持/服务端动作；原生及workflow统一validate_tier/reject_tier，等待时不重复提交。金额阈值绑定deduction_amount；沿用原有发票金额默认准备，但前移至提交前，先校验财务身份、发票、税额上限及责任余额，再启动审批。无配置只confirmed；有配置保持draft等待真实review；启用无匹配规则沿用共享fail-closed。
- 审批完成仅确认登记并保留确认审计；驳回保留原因及新审计事件。抵扣执行校验共享审批事实后才走原财务权限、日期、责任余额、私有财务token及审计。认证抵扣日期仍在实际执行时默认，不在提交时伪造；已审批金额不在执行时重新补值。历史状态与既有财务身份保护不变。
- L1 ci.local.iteration PASS（tax-approval-iteration.log）；相关生产方法隔离协作者回归55 PASS（tax-approval-tests.log，begin/record55），native8+32=40 PASS（tax-native-tests.log，begin/record40），workflow语义15 PASS（tax-workflow-tests.log）。测试覆盖默认金额在策略调用前就绪、显式金额不覆盖、无配置/配置/未完成回调边界与财务执行顺序；不把隔离测试当真实ORM验收。
- 既有runtime脚本增加7项税务事务检查：无配置、金额阈值、等待禁止抵扣、真实审批不抵扣、驳回审计、重提新链、启用无匹配拒绝。脚本语法通过，待运行。受管preflight已确认local/sc-fe-r2-p1-01/sc_frontend_acceptance、精确dbfilter及既有三卷；内部验收租户库，沿用既有全事务rollback和配置回读。
- 下一步提交后受管升级模块/重载，再执行34项集中审批运行验证。新增字段/XML需要升级；前端未改，不构建、不重跑未受影响日志/计划新建浏览器。实际抵扣财务写入和税务浏览器仍未覆盖；总体active，未推送、合并或目标部署。

- 运行回读：0a85b8168已通过受管acceptance.module.upgrade、backend.acceptance.up与health；原审批运行脚本34项PASS，其中税务7项全部PASS。实际tier review证明金额默认值在阈值匹配前就绪，真实审批仅confirmed未抵扣，驳回原因/审计和重提新链成立，启用但金额无匹配拒绝。末尾ROLLBACK=VERIFIED，原配置/步骤回读一致、临时对象不存在。日志tax-approval-{upgrade,backend,health,runtime}.log（同tpl52目录）。
- 状态：本批代码及真实模型审批链验证通过，税务浏览器与实际财务抵扣仍未验收，不称全部业务接管完成；主线未集成、目标环境未部署、用户整体验收未完成。继续既有职责中剩余project.project/project.task配置与运行支持差距及其他必要单据，支持名单只记录覆盖进度。


### 53.55 统一审批状态字段及任务执行真实回读

- 02ee7299a clean起步，上一轮有实际税务接入/运行证据，归类progress。仅核对剩余项目/任务直接实现，未全仓盘点。P1 shared approval及project execution service负责状态消费，行业模型仍是业务权威；不向前端/P3配置写入硬编码状态语义。
- 发现共享_assert_submission_approved固定record.state，不适用于task.sc_state/project.lifecycle_state。改为使用现有OCA tier声明的_state_field，兼容缺省state；审批实例仍须validated，不重新查询当前策略。生产方法测试覆盖两种字段与相矛盾state值、无审批/真实通过/等待/驳回，防止借另一状态字段放行。
- task执行服务准备后原来直接假设ready、启动后假设in_progress；恢复/完成不论真实状态返回True。改为回读sc_state，只在真实目标状态才成功，并使用既有失败码。测试执行三个实际服务方法，覆盖正常推进与方法返回但未推进；待审批式draft停留不会继续调用start，不虚报恢复/完成。
- L1 ci.local.iteration PASS（approval-state-field-iteration.log），后续直接服务变更py_compile及diff check通过；L2原审批注册目标57项PASS并begin/record57（approval-state-field-tests.log/receipt.log）。未改变视图/schema/前端，不构建或升级。当前运行仍0a85b8168，已有34项是该来源运行证据，不冒称本候选运行证明；税务等现有模型_state_field=state，逻辑分支等价，未受task service影响，不为安心重跑其旅程。
- 项目/任务完整审批仍未完成：task_extend.action_prepare_task直接draft->ready；project_core.action_sc_submit直接draft->in_progress，write还集中校验生命周期权限与迁移。下一步任务tier配置/回调与执行服务等待响应共同接入；项目必须分开立项审批与实际启动，不能让统一审批自动启动项目。中央workflow未含这两模型，后续沿直接契约生产者/处理器适配，不复制渲染。
- 总目标active；本次是必要共享前提与执行错误修复，不称全部单据接管。主线/目标部署/用户整体验收均未完成；无推送或合并。


### 53.56 项目任务接入共享审批与显式执行边界

- 7e5c5dce7 clean起步。P1 task_extend、共享审批适配、原生view/workflow及现有任务执行服务；P4只扩展已有事务回滚检查。任务使用OCA _state_field=sc_state，draft->ready、cancelled；提交先沿用原readiness阻断/缺失检查，无配置ready、有配置等待真实review。通过回调重新校验就绪后ready，驳回保留原因及审计，重提沿用共享重建review。开始/完成消费已完成审批事实，原取消权限/直接状态写保护保留。
- 原BUSINESS_MODEL_SELECTION已有project.task，补齐tier支持、回调与原生可选模型；金额条件使用现有BOQ汇总boq_amount_total。原生任务表单增加提交/真实审批/启动/完成，workflow新增同一sc_state配置，无前端模型分支；审批不自动启动任务。
- 直接服务发现执行推进处于原子savepoint，返回未完成会回滚新review。因此执行服务不隐式在该事务提交审批，先调用模型_execution_approval_block：待提交配置审批返回EXECUTION_TASK_APPROVAL_REQUIRED，真实在审返回EXECUTION_TASK_APPROVAL_PENDING；保持执行失败回滚边界，单独的提交动作承载审批事务。前端等待提示/跳转尚待页面验收，不宣称工作区闭环。
- L1 iteration PASS（task-approval-iteration.log），P4扩展语法通过；审批58 PASS（task-approval-tests.log，begin/record58），native8+33=41 PASS（task-native-tests.log，最终inputs重绑begin/record41），workflow15 PASS/66 profiles（task-workflow-tests.log）。新增契约测试五状态及can_review真权限；生产方法隔离测试证明无配置/配置/回调只ready，未启动。
- 既有rollback runtime工具新增task5项，整体预期39：无配置就绪、等待禁止启动、真实批准后显式启动、驳回原因、重提新链。待受管模块升级/重载后运行；不是已验收结果。无需前端构建；不新建环境或fixture，不做整体验收矩阵。项目project.project审批与启动拆分仍待完成，整体目标active。

- 运行回读：fef68d390受管preflight/模块升级/后端重载/health通过，身份仍local/sc-fe-r2-p1-01/sc_frontend_acceptance、精确dbfilter及既有三卷。approval_runtime39 PASS，新增任务5项全部通过；真实review校验draft等待、通过仅ready、显式start才in_progress，驳回/重提新链保留正确状态与原因。最终ROLLBACK=VERIFIED，原审批配置/步骤回读一致、临时对象不存在。日志task-approval-{preflight,upgrade,backend,health,runtime}.log。
- 阶段状态：任务模型/配置审批链验证通过，页面与工作区审批提示尚未验收；本轮未构建前端、未推送/合并/目标部署，整体验收未完成。下一步继续任务契约/页面及可操作等待提示，再推进项目立项审批与启动拆分。


### 53.57 任务官方新建页验收与记录办理前提

- 5227e572f clean起步，上轮任务配置/真实review39属于progress。P4扩展既有standard_page_type_browser approval-actions支持project.task，使用PM角色、sc_state字段读取，不新建脚本/环境/fixture；不改变产品模型、前端运行代码或权限。沿用已有受管5180候选与fef68d390后端，未构建/升级/重载。
- L1 iteration及node --check通过（task-page-iteration.log）；原preview wrapper9通过，登记到本run既有checks机制standard_preview_tool并begin/record9（task-page-wrapper-tests.log、task-page-tool-receipt.log）。该测试证明工具包装，不替代浏览器结果。
- PM任务create12 PASS（task-create-browser.log；tpl07-1790776268742/report.json）：login/system.init后有效契约project.task、官方共享表单、未保存无审批通过/驳回/完成、1440/390无页溢出；errors=[]、forbiddenWrites=[]，截图沿用报告目录。表单包含后端原生审批动作声明，由现有创建态消费控制显示。
- 任务详情前置查询api.data fields=[id,sc_state]返回ok=true、records=[]（task-detail-browser.log；tpl07-1790776285320/report.json）。不是页面渲染失败，已有记录办理未运行；不反复重查、不扩权、不造数据，把数据前提保留为缺口。
- 执行等待提示尚未闭环：当前project_execution_advance._blocked_response建议仍是刷新next-actions；仅加原因码不能算可操作UI完成。定向查询未发现前端直接按project.execution.advance/suggested_action_payload命名消费，后续必须沿共享动作结果链核实实际契约形状，不能凭空添加无人消费的字段/导航。此项与项目审批/启动拆分继续保留。
- 总目标active；本轮完成任务新建共享消费证据，不自动升级detail.action-state台账整行。主线未集成、目标未部署、用户整体未验收；既有模型39运行证据依赖不变复用。


### 53.58 共享场景动作拒绝将业务阻断报告为成功

- 8c3ee0cec clean起步，上轮task/create12构成新增有效证据。沿直接消费链定位：普通原生按钮经execute_button/intent envelope处理失败；场景mutation经sceneMutationRuntime→intentRequestRaw只检查envelope.ok。project执行阻断明确返回ok=true,data.result=blocked，原场景调用者在await返回后固定显示操作完成，可能误报业务结果。
- P0通用前端消费修正：共享sceneMutationRuntime只识别生产者明确result=blocked，抛出后端message或通用未完成提示，让现有表单/列表异常反馈承接，不依赖模型/按钮名/状态猜测。请求参数模板、trace和未声明业务结果的兼容响应保持。P1 project_execution_response_builder为审批待提交/审批中提供中文办理提示，保留task_id及原状态，不把失败当成已启动；不改审批或回滚逻辑。
- L1 iteration PASS（scene-outcome-iteration.log）；实际共享执行器4例PASS：blocked自带文案、blocked无文案、显式success、原无result响应；原create_record_user_journey同时PASS（scene-outcome-tests.log，begin/record4仅计新增场景例）。P1响应生产方法测试加入审批目标，总59 PASS（scene-outcome-backend-tests.log，begin/record59）。verify.frontend.typecheck.strict双配置PASS（scene-outcome-typecheck.log）。
- 已确认这是共享结果消费修复，不把未消费的legacy原因码文本当UI完成。当前无授权任务记录，真实执行阻断浏览器旅程仍待验证；这次单元测试不伪装真实请求。下一步一次构建/复用5180并后端重载，定向复核官方任务create；不重跑未变审批39，不升级模块（无字段/XML变化）。项目立项审批/启动拆分及全部台账仍active。

- 候选更新事实：b06c8a2f7首次frontend.standard.preview.build在addons相对已加载后端不一致处退出（scene-outcome-build.log），未进入编译。受管backend.acceptance.up已重载b06c8a2f7（scene-outcome-backend-load.log）。因这一前置恢复后再运行build，进入frontend_standard_preview.py发现旧receipt存在且inputs改变，identity()拒绝（scene-outcome-build-loaded.log）；同样未调用编译。两次不同前置失败均保留，未重复编译。
- P4确定性缺口：现有build分支只有旧产物复用/首次构建，缺少源码变化后的安全候选更新。5180仍服务0d2c6190a旧前端，不能声称本轮前端修复已加载。下一步在既有工具内补齐保留上一dist/receipt、暂存构建、成功切换及失败恢复，沿用同端口/代理/环境身份；不直接删receipt解除锁。当前前端产品复核待候选更新，整体仍active，主线/部署/整体验收无升级。


### 53.59 既有预览工具支持安全更新候选

- 13a3ec8ac clean起步，上一轮共享动作修复及前置失败定位属于progress。本轮P4精确范围scripts/dev/frontend_standard_preview.py及既有测试/记录；不新环境、端口、数据库、凭据或fixture。复用固定OUTPUT/DIST/5180/18082及既有Make入口。
- build先核对旧回执与产物：输入不变复用，旧产物损坏拒绝；源码改变时在同一artifact目录的临时候选目录构建，编译期间旧dist不变。构建前后输入一致才生成新回执；切换前再次核对旧候选，保留旧dist及原回执到previous-*目录，再提升新候选并验证identity。提升或验证异常恢复旧dist/receipt并回读验证，处理KeyboardInterrupt等BaseException；进程强杀恢复不在单元测试覆盖中，旧产物保留可供恢复，不宣称零停机原子部署。
- 既有入口增加文件锁串行build/up/identity，原监听进程归属、STATIC_ROOT、端口/代理检查及不明候选拒绝保持。没有删除回执绕过输入校验，也没有两次编译。静态入口首次因run缺少精确工具路径reconcile退出（preview-refresh-iteration.log），补登记本批已授权P4路径后PASS（preview-refresh-iteration-scoped.log）；不扩大整个scripts/dev权限范围。
- 既有preview测试从9增至16：未变不编译、变化只编译一次且旧产物保留、编译失败保持旧候选、编译中源码漂移拒绝、旧产物损坏拒绝、回执提升失败恢复、切换后身份失败恢复。最终L1之后begin/record16 PASS（preview-refresh-tests.log/receipt.log），首次L1前的测试仅诊断，不替代最后回执。
- 下一步提交后实际一次构建/复用5180，再绑定加载entry复核任务create。后端仍b06c8a2f7，本轮未改addons，不重载/升级。审批39与模型证据输入无变化继续复用；前端共享结果修复仍待候选加载，不宣称真实阻断任务旅程已完成。

- 实际候选更新已完成：fed2dfcc234565d8e48a644e38cff702c5c56c7b仅编译一次，23.45s（preview-refresh-build.log），旧候选保留于既有OUTPUT/previous-avuxmhgu（dist及原build-identity.json）。受管up复用5180监听进程，新首页HTTP hash与回执一致（preview-refresh-observed.json）；entry=/assets/index-C9RBIxc0.js，entry_sha256=3c9d155557f1dcb45d85a45be8dd0db457025fb23ed190c17efd1c434fa25fc4，index_sha256=8bf961230df3aa181e8963a125b630e69d99d1bac3c72b35999e02b6f5df9a3e。不做全文件HTTP比对。
- 新候选PM任务create12 PASS（preview-refresh-task-browser.log，tpl07-1790776830481/report.json），官方共享表单和双视口加载正常。53.58共享阻断消费代码已实际进入当前前端；真实审批中任务操作UI仍无现有授权记录，不能用create12代替该旅程。无字段/XML改动，不升级；审批39输入不变复用，不重复ORM。
- 53.58预览工具阻断关闭。本轮P4批次验证通过；总体目标未完成、主线未集成、目标环境未部署、用户整体验收未完成。下一步继续project.project审批/启动分离及原67台账的生产者/消费者/旧职责退出缺口，不再停留在预览更新。


### 53.60 项目立项审批与生命周期启动分离

- cdb10b1e1 clean起步，复用已加载前端fed2dfcc2。P1项目立项是独立审批事实，不把批准等同在建。新增同模块project_initiation_approval模型扩展，复用tier.validation/_state_field=sc_approval_state；原project_core.action_sc_submit实现移出并改为提交审批，原启动/提示行为由action_sc_start承接，没有两份提交编排。
- 提交保留原项目角色门禁，校验草稿/名称/公司，无配置仅立项approved，有配置等待真实review。通过回调重验前提仅approved；驳回保留原因和消息，重提沿共享restart新链。立项状态只能私有对象token写入，create不能伪造approved，bool/string上下文不能绕过。实际启动调用原集中生命周期权限/状态机；集中_validate_lifecycle_transition拦住draft->in_progress及draft->paused绕行，历史在建/暂停项目原生命周期继续，不生成历史审批。
- 原生通用项目表单/总览/启停管理拆分提交与启动并声明真实审批按钮；项目信息编辑仍只承担提交，不吸收生命周期操作，增加审批事实字段。总览提交不再把资料完备度当硬门槛，与既有advisory模型边界一致。配置增加project.project tier支持和回调注册。项目审批金额尚无确认业务权威，不猜合同额/预算额：共享适配遇无amount映射且配置金额条件时明确ValidationError，普通无金额规则可用；该必要配置能力保留产品缺口。
- L1 iteration PASS（project-approval-iteration.log）；审批63 PASS（project-approval-tests.log，begin/record63），包括无配置/配置/真实回调与显式启动、集中绕行拦截、私有状态写保护、无金额权威禁止忽略条件。已有native8+33=41回归PASS（project-native-tests.log），仅覆盖现有profile集合，不声称项目中央profile完整。当前项目仍须核对原生到有效契约的状态/动作消费，不以模型通过代替页面。
- P4既有回滚脚本新增项目6项（总45），所有新项目/策略加入原created清理回读；语法通过，待运行。下一步提交、受管模块升级与后端重载，再运行45。新字段/XML需升级；前端未改不构建，不重跑任务/付款全旅程。整体active，未推送/合并/目标部署。

- 运行回读：4a3e08ffa受管acceptance.module.upgrade、backend.acceptance.up/health均通过（project-approval-{upgrade,backend,health}.log）。集中真实审批45项PASS，新增项目6项全部通过：直接写批准/直接draft启动及暂停绕行拒绝，无配置仅批准未启动，真实在审不启动，真实review通过后显式start，驳回原因与重提新链。ROLLBACK=VERIFIED，原策略/步骤回读一致、临时项目/单据/策略不存在（project-approval-runtime.log）。
- 阶段：模型与配置执行链验证成立，项目有效动作/状态契约和页面仍待核对；未将native41外推到未加入中央profile的project.project。金额条件权威缺口登记到原contract-gaps文档，保留detail.action-state未完成。前端候选fed2dfcc2未变；不构建、不推送、不合并、不部署目标环境。总体active。


### 53.61 项目进入统一动作契约与生命周期语义

- ed723870b clean起步。P4 probe扩展project.project/lifecycle_state及独立sc_approval_state读取，PM现有授权项目10（draft/draft）只读详情18 PASS（project-detail-browser.log；tpl07-1790777366552/report.json，errors/forbiddenWrites为空）。回读原生提交/审批/启动存在但actionSemantics缺失，18项只证明原生呈现与未批准不启动，不能据此宣称办理完成。
- P1将project.project加入既有workflow profile，生命周期为主状态、审批事实保持独立；声明提交/审批/启动/暂停/恢复/竣工/结算/保修/关闭真实方法和状态范围。用既有Odoo filtered_domain承接profile.action_domains，提交与启动根据sc_approval_state及真实validation_status筛选，不新增前端模型分支。历史活跃/后续阶段元数据保持field_editable_phases范围；草稿审批阶段继续标准工作流只读约束。
- P0只增加通用pause_execution、advance_phase、close_record词汇，恢复使用已有start_execution；项目结算/保修等行业名称与方法只在P1。同步权威词汇、schema与TS消费投影，不把暂停当取消、阶段推进当最终完成。既有native登记表增记项目12个导航和2个BOQ辅助方法，不将它们伪装状态迁移、不建平行覆盖表；项目状态方法均由profile声明。
- L1首次精确TS消费文件未登记导致reconcile（project-contract-iteration.log），补入既有scope后PASS（project-contract-iteration-scoped.log）；早期诊断不充当最终回执。L2 native8+34=42 PASS并begin/record42（project-contract-native-tests.log），语义15 PASS/67 profiles/13词汇（project-contract-semantics-tests.log）；实际表单header链及新增3合法/3非法配对PASS（project-contract-header-tests-final.log），严格双tsconfig PASS（project-contract-typecheck.log）。一次误用不存在的header测试目标未执行测试，改用既有verify.frontend.contract_header_action.unit，日志分开保留。
- Probe增加edit只读观察模式与四动作语义断言；下一步提交/后端重载/一次新前端候选构建，仍查同一现有项目，不执行业务写入、不造fixture。无字段/XML变更，无模块升级；既有45真实审批输入不变复用。整体仍active，项目金额权威及跨状态用户办理未覆盖保留。


### 53.62 完整动作声明与当前可用性分离（进行中）

候选 51f470eb9 + 本段 dirty。53.61 浏览器报告 `artifacts/frontend-web-fix-20260928/tpl07-1790777792498/report.json` 超时：有效契约 viewCapabilities.write=false / effectiveRenderProfile=readonly，页面实际采用 official-standard-detail，测试误等 official-standard-form。四个原生动作均存在，只有当前可用 submit 具有 actionSemantics；start/approve/reject 缺失。

P1 smart_construction_core workflow.contract.service 的完整动作目录通过既有 workflowContract.actions 输出，仅声明方法与含义，不携带 enabled/target；availableActions 保持当前状态、审批人与证据约束。P0 既有投影无需业务特例。范围为该生产器与两项现有纯测试；不改权限、状态机、原生视图或前端业务逻辑。L0 已确认当前分支、工作区原本 clean；L1 iteration → L2 native coverage 与有效契约投影纯测试 → L3 后端重载 → L4 复用现有构建核对只读入口。没有模型/XML变化，不升级模块；没有前端源变化，不重建；既有45项审批运行时输入不变，复用，不跑无关 ORM。

L1 `action-catalog-iteration.log` PASS；L2 `action-catalog-native.log` 8+35=43 PASS，begin/record43 回执 `action-catalog-receipt.log`。投影首次新增用例缺必填 origin 导致1错误（产品正确拒绝不完整声明）；纠正测试输入后 `action-catalog-projection-fixed.log` 20+108=128 PASS，runtime guard score6。未改变生产投影校验；首次失败日志保留。待后端重载与实际契约核对。

实际运行完成：后端 `e14519cb1` 受管重载成功；5180 复用 `51f470eb9` 的 `/assets/index-C5E0xYhV.js`，SHA256 `86ff6b206abb70d2e56716f2ce6b1bc7df0aabc6f8b7b495bdc328d1d3b56b18`，前端构建输入无变动、未重建。PM/公司8/project10 的官方只读详情浏览器22项 PASS，报告 `artifacts/frontend-web-fix-20260928/tpl07-1790778081937/report.json`：submit/start/approve/reject 均有正确语义，未审批无启动，审批事实与生命周期分离，双视口、errors=[]、forbiddenWrites=[]。这是只读入口与契约验收，不证明信息编辑入口或真实提交操作已验收。

后续已定位共享消费者 `workflowActionAvailability.ts` 仍使用方法名别名和固定 knownKeys；应以完整声明目录识别受管动作，退出名称推导，不能因 unavailableActions 不含动作就漏掉新声明的暂停/阶段推进等动作约束。本段未改变该消费者，不声称全系统收口；67条/所有业务单据目标继续，金额权威与数据不足旅程仍保留原缺口。无推送、合并、目标环境部署。


### 53.63 共享动作消费退出名称推导（进行中）

候选1c6a76b18 + dirty；P0 frontend/apps/web 共享 workflowActionAvailability 消费 workflowContract.actions/availableActions，不添加业务规则。删除固定 knownKeys 与方法别名表；方法身份优先精确匹配，声明但缺可用项禁用，冲突/损坏契约报错。无目录的旧契约仍仅精确消费显式可用项，不再猜测未知方法含义。L1 iteration → L2 canonical presenter 非零回归与严格类型 → L4 单次构建、既有项目记录浏览器。后端源、模型与45项审批执行输入未变，跳过ORM/模块升级；后端运行身份仅在受管入口要求时重绑。目标为退出共享旧推导，不以单页通过宣称67条已完成。

L1 `catalog-consumer-iteration.log` PASS；L2 `catalog-consumer-tests-final.log` 原有177+10与新增10项 PASS（含真实 presenter 禁用未知命名但已声明的不可用动作），回执绑定新增10项 `catalog-consumer-receipt-final.log`；`catalog-consumer-typecheck.log` 严格双配置类型检查 PASS。只读检查既有所有 profile 的 method_by_action 无重复方法；未修改映射。最后新增仅测试用例，生产输入未变，复用已通过类型结果。等待构建与定向浏览器。

构建7915f3bb9一次24.37s完成。首次项目浏览器 `tpl07-1790778275644/report.json` 11断言处失败：P4最后响应观测被 project.responsibility 子契约覆盖，主响应project.project/id10已存在；页面无错误。修复既有审批检查脚本按本次导航的model+id选择契约，保留首次失败报告。仅工具变动，不失效生产构建或已通过前端类型/纯测试；node语法检查后重跑定向页面。

最终运行：前端7915f3bb9，entry `/assets/index-DHbyXOXT.js`，SHA256 `88b2bf54f30cca97c91fac0942c83b883079245460594ac380f02f4b0c14e865`；原候选保留 previous-5rbtrx0q。后端源e14519cb1未改，工具接受相关addon输入不变。修正probe的L1 `catalog-consumer-probe-iteration.log` PASS；项目 `tpl07-1790778322370/report.json` 22 PASS，付款执行 `tpl07-1790778337439/report.json` 19 PASS，双视口/errors=[]/forbiddenWrites=[]。确认取消不派发写入；未执行财务撤销，不增加fixture。同步既有detail.action-state后续说明及缺口文档，不升级整行状态。批次定向验证完成，原总体目标仍active；无主线集成/目标部署/完整交付声明。


### 53.64 项目信息编辑入口定向验收（进行中）

候选a8a5ccc4c + P4 probe dirty；复用53.63全部产品测试/构建。原生独立编辑菜单/action/view职责为资料保存+提交立项，不含审批/启动。验收扩展按当前PM system.init.route_authority查正式menu XMLID取得菜单与动作ID，携带真实入口上下文打开现有project10；无业务写入、无fixture。L1 iteration与node语法检查后运行单次定向浏览器；产品输入无变化，不运行ORM/类型检查/重建。

首次入口检查4项处失败：新增probe误读旧顶层route_authority；当前system.init正式路径为data.navigation.route_authority（system_init.py生产器明确移除顶层carrier）。按正式路径纠正，仅P4输入变化；首份报告tpl07-1790778448035保留，不记产品失败。

最终报告 `artifacts/frontend-web-fix-20260928/tpl07-1790778468464/report.json` 16 PASS，errors=[]、forbiddenWrites=[]。当前PM初始化route authority正式菜单680/action861，project10，独立入口effectiveRenderProfile=edit、write=true、create=false、unlink=false。动作契约只有平台save_draft/write与P1 submit；无启动/审批动作注入。双视口官方表单正常。源与构建沿用7915f3bb9/backend e14519cb1，无新构建、模块升级或ORM。该结果关闭入口职责/官方渲染验证，不是实际保存、提交和审批办理验收。原始失败仅新增probe旧字段路径错误，已纠正，不放宽契约。


### 53.65 物资链统一审批前的状态契约纠偏（进行中）

候选e5405a983+dirty。P1 smart_construction_core.workflow.contract.service：按既有模型权威纠正材料验收/入库 reset与cancel可用源状态；不放在前端/P3，不改模型授权与执行，不新增状态框架。验收取消仅draft/submitted，重置cancel/rejected；入库重置仅cancel。原契约错将提交态发布reset、遗漏cancel态reset，并允许rejected验收cancel。四项新回归从模型实际状态guard提取权威，再执行共享投影逐状态比较，包含unknown。L1 iteration→L2现有native coverage；未改数据库结构/XML，跳过升级和无关ORM，运行时验证尚待完成。

下一项已定位的必要P1缺口：材料验收、入库均未继承tier.validation，也未进入sc.approval.policy支持；action_submit直接变submitted。入库实际action_receive改变received，出库调拨_sync_transfer_inbound_after_issue会sudo生成→提交→接收并强制received，否则回滚整个出库。统一审批不能只改按钮或静默跳过入库审批，必须处理该关联链与审批/实际执行分离。保留产品缺口，不将现有支持列表当全业务范围。

L1 material-state-iteration.log PASS；L2 material-state-tests.log 8+39=47 PASS，begin/record47 material-state-receipt.log。本段仅源代码/纯投影完成，运行时候选未加载此改动，保持verification_pending；下一步补入库审批时合并一次受管升级/加载，不为两处profile改动重复构建和跑页面。此前前端7915f3bb9、后端e14519cb1的页面结果仍仅证明此前声明范围。


### 53.66 材料入库统一审批与调拨关联链（进行中）

P1 smart_construction_core：复用sc.approval.policy/OCA tier，无配置submitted→approved、有配置真实review，审批回调只到approved；独立action_receive要求approved和有效审批事实。新增company关联、拒绝原因、approved状态与私有写令牌；配置金额绑定既有amount_total。原生动作/中心profile同源；现有submitted无审批事实可再次提交，不能自动回填审批。调拨自动生成入库在configured pending时保留关联，不再强制received回滚；无review且自动通过保留既有显式调拨执行中的自动接收。审批回调不执行接收。

涉及模型/schema/XML，必须先L1+审批/native L2，再受管升级及真实审批/调拨检查，之后才页面验收。当前尚未升级，无运行时完成声明。旧前端构建未变可复用；此次backend/配置/领域输入改变，需要定向新增入库回归，非无关ORM。不新建环境fixture。

源码L1 inbound-approval-iteration.log PASS，审批纯测试66（含新增入库/写令牌/调拨3项）inbound-approval-tests.log PASS；native8+39=47 inbound-native-tests.log PASS，两个begin/record非零回执已登记；2份XML解析PASS。当前verification_pending：未升级模块、未实际跑入库审批/驳回重提/调拨，不宣称批次验收完成。下一步扩展现有rollback审批smoke，审查新增状态保护与原有直接状态写入的兼容后再升级；复用旧前端构建，无需重建。


### 53.67 入库统一审批受管运行验证（进行中）

P4扩展既有business_config_approval_runtime_smoke.py，使用同一rollback事务、已有仓库和材料，新增8项：禁止外部状态写、无配置审批与独立接收、有金额配置真实review/禁止早接收、配置变动不绕过进行中review、真实审批后显式接收、驳回重提、调拨关联入库保留审批与回调不接收、无配置调拨保持既有自动接收。调拨项调用既有内部关联生成链，不能当完整出库办理验收。全部临时单据/政策加入原恢复检查；不建立新fixture或环境。

数据库角色平台内部验收租户，local profile/sc-fe-r2-p1-01，sc_frontend_acceptance，精确filter及sc_fe_r2_p1_01固定卷沿用已登记预检；非客户生产/控制库。此次P1新字段/state/XML需要smart_construction_core受管升级；先L1、复用未变66/47定向输入结果（唯一变化为P4 smoke及文档），随后一次升级、后端重绑与实际53项。当前仅脚本编译通过，未开始数据库写入。

受管升级61facd29b成功（Registry72.023s），后端重载成功。全量现有45检查通过且rollback verified，新增入库因不存在非服务材料前置失败。P4现有入口增加SC_APPROVAL_RUNTIME_SCOPE=all|inbound白名单（默认all），复用身份预检，不新增环境；inbound只运行8项，不再重复45。已有仓库有效，最小消耗材料仅在同一rollback事务临时建立，product/template均纳入消失回读，无fixture基线或持久测试数据。

入库前5项实际通过后，驳回重提触发OCA旧tier记录状态写锁；报告inbound-only-material-runtime.log，rollback verified。P1修复只在私有token保护的提交方法内skip_validation_check跨过旧锁，shared router随后重建review，外部状态写仍拒绝。新增重提纯回归，L1 inbound-resubmit-iteration.log PASS；67审批tests PASS及非零回执。仅Python改动，无第二次模块升级/前端构建，待后端重载后仅8项重验。

实际结果：后端f5e771c03，inbound-only-runtime-fixed.log 8/8 PASS；ROLLBACK VERIFIED确认原配置/步骤恢复，临时入库/出库/项目/材料及product.template均不存在。此前inbound-approval-runtime.log中原有45项成功有效，后续修复只影响入库动作，P4只新增scope/临时材料协作者，按输入独立性复用45不重跑。新增8项全部真实Odoo执行；调拨仅关联生成与接收链，仍不等于完整出库角色旅程。未重建前端。入库有效页面与角色办理仍pending，材料验收等全单据范围继续开放。


### 53.68 入库官方页面消费（进行中）

P4仅扩展现有standard_page_type_browser审批范围支持sc.material.inbound。PM既有角色包含cap_material_manager，沿用公司/项目授权；先不保存创建表单，再查询已有记录做只读契约/状态观察，没有记录明确pending。沿用前端7915f3bb9、后端f5e771c03；无产品源改动，不重建/升级/重跑8项ORM。L1 iteration、node语法→本次受影响页面观察。

结果：inbound-page-iteration.log L1 PASS；创建报告tpl07-1790779258521/report.json 13 PASS，官方表单、未保存无审批/确认入库、双视口、errors=[]、forbiddenWrites=[]。既有记录报告tpl07-1790779275827/report.json查询ok=true/records=[]，2项处停止；这是授权数据前置不足，不是记录页通过。不扩权、不新增fixture、不重试相同查询。实际记录UI审批/确认入库继续pending；后端8项及创建13项保持各自证据范围。
