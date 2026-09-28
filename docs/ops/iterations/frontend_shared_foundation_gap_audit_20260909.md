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

**未修复阻断（本入口无法取得「编辑已有明细行后保存」证据）**：多行付款申请（经正常 UI 由结算单引入、`source_line_type` 全部为常量「结算单明细」）在编辑任一明细单元格后保存，前端不发写请求并提示 `outflow_line_ids 存在重复行值：结算单明细`／`主值重复：结算单明细`（证据 `uat01a-raw/uat01a_line_dup_block.txt`）。根因：`frontend/apps/web/src/pages/contractForm/one2manyUtils.ts:521-549` 的 `collectOne2manyDraftValidationFromRows` 以 `one2manyPrimaryColumnFromColumns`（**首个业务列**）作行身份，而本子视图首列为 `source_line_type`，导入处理器 `addons/smart_construction_core/handlers/payment_request_settlement_introduce.py:526` 给每行写同常量，于是两行以上互相判重；对照实验（两行 `source_line_type` 取值不同）同一编辑保存即可成功。属既有行为（文件最后修改于 `de9a230d`/`0b47763`，非 `19b2d290`/`c0b9a62e` 引入）。最小修法（**未实施**）：对已持久化行改以记录 id 作行身份，而非主列标签；因该断言被全局 one2many 校验共用，改动语义面较大，故保留为待批准的阻断 + 修法建议，不在本轮改动。

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
