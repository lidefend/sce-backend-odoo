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
| G-F3-02 / B02 | 高：日记账分录详情整体无法渲染，sc.input.text:json不匹配 | 定位结论（`accounting_json_detail_readonly_20260924.md`）：字段 `account.move.quick_encoding_vals`，ttype `json`、契约只读且原生 `invisible`，值形状为 JSON 对象；首次错误映射在契约生成层 `unified_page_contract_v2_assembler._widget_type_from_field` 对 json 无分支而回退 `input` → `sc.input.text`，前端注册表 `sc.input.text` 仅支持 `['char']`，Resolver 按设计 fail-closed 导致整页不可渲染（Resolver 不是错误点）。正确呈现要求：json 无任何客户端编辑控件，契约声明只读可读展示，对象/数组输出 JSON 文本，`{}`/`[]`/null/false/空串按空值处理，可编辑 json 同样只读，空值与非空值都不得整页失败。最小修改路径：契约层 `json → display`（复用既有 `sc.display.text`，不新增组件键）+ 通用展示层 json 文本化与禁止落入可编辑兜底 + 三类输入的定向测试；解耦 Decoder/Resolver fail-closed。不得隐藏字段、吞异常或把对象字符串化塞入文本框。同类未修：lite 适配器同源回退。复验：列表→详情可打开、JSON 按契约展示、原只读记录仍只读、返回列表保留查询上下文。已实现（契约层 json→display、前端通用 json 文本化与只读分支、三类输入定向测试）并复验通过：定向 7 项/147 项、assembler guard、展示与表单契约单测全绿；浏览器 `/f/account.move/2` 列表→详情整页渲染无错、json 输入数为 0、返回列表保留 `menu_id` 上下文。残留：本数据集无「可见且非空」json 值（可见非空展示由发布模块展示单测＋契约探针承担）；`analytic_distribution` 等原生可编辑 json 一并转为只读展示（旧行为本就 fail-closed）；导航授权拒绝与 lite 适配器回退登记不修；未合入前不宣称主线集成 |
| G-F2-04 / B03 | 中：收款新建返回越过来源收款列表 | 定位结论（`payment_return_navigation_20260924.md`）：根因单点且通用——`ActionView.vue:1647` 用 `router.push` 打开 `/f/<model>/new`，全局 `beforeEach` 守卫为创建表单补注入 `activity_page_id` 时返回了 `replace: true`；`vue-router@4.6.4` 的 `pushWithRedirect` 会把原导航 `replace` 透传给守卫重定向的后续导航（`dist/vue-router.mjs:1311`），用户 `push` 变成 `replaceState`，来源收款列表条目被销毁，表单「返回」(`router.back()`) 落到真实前驱（`/workspace.home`）。修复（通用导航运行时，不写死收款路由）：新增 `resolveCreateFormActivityRedirect()` 注入活动身份但**不带 `replace`**，交回调用方保留导航模式；`executeRecordFormReturn` 增加 `hasInAppHistoryEntry`/`fallbackRoute`/`navigateFallback`，返回 `history` 或 `fallback`，回退目标只取自路由授权声明的入口路由。复验：定向 `make verify.frontend.record_form_return.unit` 11 条通过、`vue-tsc` 错误集与基线一致、`local.dev.frontend` 构建上线；浏览器 5 场景通过（合同页/报表页两种来源均回收款列表、筛选+分页上下文保留、直达 URL 走契约回退、有草稿离页保护），`errors: []`。残留：报表中心投影页 0 行致其对象按钮不可达（入口数据问题，登记不修）；显式创建入口仍 `not_available`（未验收）；many2many 失焦与 `ScAutoComplete.vue` 留后续。未合入前不宣称主线集成 |
| G-F3-03 | 高：开发环境收入/支出结算列表附件 404（`/web/content/231`） | **未复现**：结算列表与详情首屏 `attachment`/`web/content`/`/binary` 请求 0 个、无 4xx/5xx，`sc.settlement.order` 附件关联 0 条。孤立 `/web/content/231`→404 与 `/web/image/231`→200 均不足以判定原问题（200 可能是共享占位图，不能证明返回原文件）。停止推测归类；后续巡检若捕获真实失败，须同时记录页面、实际请求 URL、响应类型、调用来源及附件身份 |
| G-PUB-01 | P4 `gitee.ci.pr.create` 硬编码旧分支及旧PR正文 | 最小参数化修复及11定向测试通过，待独立复核与实际PR回读；保留精确SHA、受保护main和创建回读，不扩大CI建设 |
| G-F3-01 | 其余已映射正式入口只有历史结构/覆盖信息 | 保留本轮 F3 归属，逐域覆盖列表与表单；写入口具备成功/失败/拒绝/恢复，按实际职责转为只读或明确降级，不能以 ready 关闭 |

新增巡检唯一来源：`artifacts/frontend-business-entry-browser-audit-20260923/browser-audit.md`（现有外部归档），产品载体`9b3d65d2`；管理员会话、代表入口、390px观察，未保存业务数据。它不替代业务角色、拒绝角色、89项全量或真实写入验收。用户当前草稿保持，不保存、不放弃、不刷新该会话；修复复验使用独立受管测试会话和专用对象。
