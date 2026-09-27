# Batch-1 项目资料办理面交付记录

## 2026-09-23 F0 → F1 当前批次（本节优先于历史验收结论）

目标：自定义前端成为正式业务入口；89 个正式入口均有去向，按职责取得真实操作及权限证据。
基线 `61b8d7121b28d1e1f9126e7c03ab01bce57cee62`；分支
`feature/frontend-business-entry-closure`；当前产品运行候选为 clean `babce9d963b00e501f6889a003447483434eba39`；原名称/权限子范围证据来自`9b3d65d2`，客户交互证据来源及影响分析见当前结果索引。后续仅台账更新不改变运行证据输入。尚未完成 PR 最终冻结与远端验证。

- 唯一入口矩阵：[frontend_business_entry_acceptance_v1.csv](../../product/frontend_business_entry_acceptance_v1.csv)。复用锁定菜单策略的 89 个稳定 XML ID，关联旧覆盖数据，不重新扫描全仓。旧数字 action/menu ID 不作为当前环境权威。
- 唯一缺口清单：[frontend_shared_foundation_gap_audit_20260909.md](frontend_shared_foundation_gap_audit_20260909.md) 的 F0/F1 当前节；本文件为唯一当前批次记录。历史归档不重写为本轮通过。
- F0 去向：86 项本轮验收（项目资料 F1，其余 F3）；3 项会计入口因旧覆盖表缺少同身份行，明确阻塞 G-F0-02。零无归属、零未经确认排除。旧表额外的 WBS 和旧业务映射不扩大本轮范围。
- 角色列保留后端菜单链与 action group 权威，不能当作登录角色或最终写权限；实际账号、company、ACL、record rule 随每项旅程绑定。`ready/structural/readable_fallback` 仅为历史实现描述，所有业务验收状态起始 `not_run`。
- F1 范围：项目资料进入、查询、名称/日期/说明/责任明细编辑、保存、刷新回读、错误定位、权限拒绝及失败草稿恢复。未保存草稿跨刷新持久化不在承诺范围；保存不推进项目生命周期。

所有权：F0 证据登记与环境恢复属 P4；项目标准规则属 P1 `smart_construction_core`；通用执行属 P0 `frontend/apps/web`。沿 Decoder → Store → Resolver → Runtime → Registry；规则由后端裁决，前端不补业务语义。当前只修真实反例暴露的项目名称校验：P0 编辑提交按契约 required 校验实际提交字段；P1 `project_core.write` 在副作用前拒绝显式空名称。不改 schema、权限、数据库结构或默认路由，不加入前端模型名判断；无须模块升级，受管重启加载 Python。F2 竞态/occurrence 与 F4 美化后置。

本轮文件边界：P0 `saveRecordHelpers.ts`、`valueUtils.ts` 与已有 `create_record_user_journey_test.ts`；P1 `models/core/project_core.py` 与已注册 `test_project_state_transition_validation.py`；P4 既有项目写入 browser `.mjs/.sh`、fixture `.py`、对应单元测试，以及本文、缺口清单、89 项矩阵。风险：共享编辑校验影响所有契约表单；通过非零 required 类型/局部更新反例和项目实测控制影响。回滚按 P0/P1/P4 提交分别回退，测试对象按命名空间清理。

发布阻碍的最小追加范围：P4 `scripts/ops/gitee_formal_pr.py`、`make/codex.mk`、`scripts/verify/test_gitee_formal_pr.py`。现有创建器固定旧CI分支，当前业务候选无法使用；仅将branch/title/body文件参数传入同一身份、ledger和回读链，新专题ledger按分支摘要隔离，旧专题ledger继续沿用。属交付工具而非P0-P3业务规则，不改远端服务、检查、权限、合并或部署。新增文案经环境变量作为shell字面量传递；独立审查发现的直接拼接风险已修，并用实际Make wrapper反例覆盖。该范围不依赖/改变frontend、handler、fixture或runtime，因此携带`9b3d65d2`产品证据，无须重复业务写入。

环境：复用 `local.dev` / `sc-local-dev` / `sc_dev_demo` / `^sc_dev_demo$` / 18081，候选静态前端 5176；数据库角色为隔离持久开发租户，非客户生产、非控制库、非行业目录。filestore 为 `sc_local_dev_odoo_data`，数据库和 Redis 卷沿用 `sc_local_dev_*`。凭据只来自受管 `.env.dev`，不复制、不轮换。测试对象仅 `codex_p4_project_profile_write` 命名空间的 `frontend-f1-20260923`；不重置数据、不创建用户。

### 当前结果索引

2026-09-23用户补充巡检后调整：`fd6fb975076c81ba4d6d61db3b773b9b604e3354`已完成独立复核和推送预演，未推送/未创建PR。新证据暴露F1客户交互阻断，暂停发布和最终收口；继续同分支/同台账迭代，不继承该候选的整体可发布结论。已通过的名称校验与权限结果仍保留原身份，后续按共享依赖影响选择复验。

接续顺序：①F1客户完整任务，先分离查询/选中/明确创建，补输入后blur/ESC/取消不修改、明确选中/创建、查询失败恢复与有效保存；同时修下拉遮挡和焦点自动重开。②紧接处理B02日记账JSON详情阻断，归属F3提前解除入口阻塞，不能以文本控件吞JSON。③F2处理B03通用返回与既有竞态/occurrence，补两种来源路径及取消/离页反例。三个主题顺序执行，不并行美化；新增缺口统一登记G-F1-07/08/09、G-F3-02、G-F2-04。

B01首轮修复（迭代身份`fd6fb975`加19路径dirty）：普通输入/blur/无候选Enter及fallback change不登记创建；只有显式创建产生独立pending意图，真实reload/discard清除，收藏保存不取消。响应式pending投影统一参与hasChanges、字段计数及离页保护。搜索弹窗错误不呈现空态或允许确认旧行，列加载/行查询均有取消代次。复用ScPopover解决祖先层叠，保留焦点恢复并抑制自动重新展开。后端通用搜索不自动纳入原生搜索视图的非存储虚拟过滤器（显式投影/扩展仍保留）；受管日志`/tmp/frontend-f1-relation-diagnostic-20260923.log`确认旧请求由phone_mobile_search短词校验抛UserError。无业务模型特例、无schema/数据库升级。

本轮定向结果：实际关系状态9反例、dirty/离页5反例及原required10/旅程6检查点通过；关系生命周期原12例+搜索失败/乱序/关闭3例+列延迟取消重开1例通过（`/tmp/frontend-f1-relation-state-l2-20260923.log`）。后端38例中新增测试首次缺fake env，补测试依赖后该1例通过，原37例复用（`/tmp/frontend-f1-relation-search-l2-20260923.log`、`/tmp/frontend-f1-relation-search-l2-r2-20260923.log`）。关系呈现/生命周期门禁通过；新增明确清除按钮后同步现有guard期望。受管runner33例通过。首次关系旅程脚本变量重名构建失败已改块级作用域，结果见`/tmp/frontend-f1-relation-intent-l2-r2-20260923.log`。独立复核发现的fallback提交、草稿对象误作代次、失败确认旧行和延迟列污染均已修复；实测仍not_run，准备新候选载体。P4仅在既有runner增加专用对象RELATION_ONLY互斥模式并回读partner_id，不触碰用户管理员会话或草稿。

B01受管复验绑定`ae69871e0cb619d9eab579acee08b7f747ed71b4`，专用批次`frontend-f1-rel-20260923`、项目3928：查询AB后失焦，草稿未修改且写请求为0；随后再次展开失败，整次结果为failed（`/tmp/frontend-f1-relation-browser-20260923/summary.json`），不继承单测通过为验收通过。只读诊断初次聚焦浮层存在，再聚焦aria-expanded=true但浮层DOM缺失（`/tmp/frontend-f1-relation-refocus-diagnostic-20260923/summary.json`）；依赖源码确认关闭动画onAfterLeave在destroyOnClose下卸载容器。恢复变更限定P0 ScPopover可配置挂载策略，默认保持原值，many2one快速关闭/重开保留浮层容器；内容仍由isOpen控制。风险为所有关系选择消费者，不改业务/契约/数据，最早验证L1+关系L2，随后仅复验受影响客户旅程。诊断脚本临时采集已移除；用户管理员草稿未操作。

B01第二次复验候选`7f85e700daad441641760d86bd636e28b9c05de4`：L1迭代、关系L2和独立代码复核通过；受管carrier health通过（首次漏confirmation参数被拒，补齐参数后通过，未绕过门禁）。`/tmp/frontend-f1-relation-browser-r2-20260923/summary.json`确认query/blur零写入、重开与选项无遮挡、短词搜索HTTP200、取消焦点恢复且不重开均通过；390px分支因可见性/溢出/ESC组合断言失败，整次仍failed，待局部诊断。上述结果不覆盖明确选中/创建/保存及查询错误恢复，不关闭B01。数据库专用对象3928仍保留以便连续复验，未修改用户项目4或管理员草稿。

窄屏诊断进一步收敛：初次窄屏进入的只读对照scrollWidth=390；完整桌面搜索取消→390px序列在等待布局条件后仍超时，不能归因测量过早。`/tmp/frontend-f1-relation-overflow-diagnostic-r2-20260923/summary.json`记录scrollWidth=542，可见元素没有对应542px边界；关系输入内部AutoComplete无候选内容但会创建visibility:hidden浮层，沿本地依赖源码确认popupProps可覆盖内部visible。P0仅在ProfessionalMany2oneFieldControl关闭该重复候选层，继续由现有外层ScPopover承接真实关系选项，不改变其他AutoComplete消费者。P4增加窄屏几何条件等待及失败尺寸采集；首次尺寸采集误放预检位置未取得失败尺寸，修到catch后才使用证据。待新载体复验；全部中间失败仍保留，不用静态通过替代业务通过。

`74f5de1e`受管复验三场景passed（`/tmp/frontend-f1-relation-browser-r4-20260923/summary.json`）：query/blur不修改、搜索取消与无遮挡、桌面取消后390px重开/ESC；零业务写请求，权威facts不变。独立复核接受修复边界，最终以本次实测消除窄屏疑点。不能因此关闭明确选择、保存及失败恢复。

接续P4限定既有runner `.mjs/.sh` 和其unit文件追加互斥`RELATION_WRITE_ONLY`，使用同专用项目3928、同数据库/公司/filestore及同受管凭据；只从契约返回的可选关系中明确选中既有记录，不创建客户。阻断一次该项目write验证保留客户草稿，再重试保存、权威回读与刷新比对全部项目/责任事实；对象沿原batch cleanup。此为验收工具层，非业务规则，权限/对象门禁不变。L1与35条runner单测passed，产品源码仍74f5de1e，P4工具dirty三路径；原三场景证据不受新分支影响，不重跑其矩阵。

客户选择写入初测仅为诊断（`/tmp/frontend-f1-customer-write-20260923/summary.json`，产品74f5de1e、P4三路径dirty）：pm1明确选择契约候选6390，模拟首次项目write网络失败后客户草稿可编辑且权威facts不变；同载荷重试仅一次业务成功，刷新与后端全facts一致，生命周期draft及责任33/34不变。未创建或修改客户6390，只改专用项目3928关联。前述三场景为有效实测，本次两场景因下述验收工具缺口撤回passed结论，尚不覆盖查询失败页面恢复、重复名称列、创建权限消费者及F2离页/竞态。只读角色直接write403原9b3证据可携带：本次后端改动仅查询domain构造、不改write权限/路由；这不是新候选全量权限验收。

独立复核撤回客户写入初测的验收资格：旧fixture的write_scope漏partner_id，候选ID又取自提交载荷而非所点候选，全变更监听在选择后启动，刷新缺UI值断言。该次仅登记诊断，项目3928/责任33/34已cleanup且inspect确认existing_batch=false（`/tmp/frontend-f1-rel-cleanup-20260923.log`、`/tmp/frontend-f1-rel-after-cleanup-20260923.log`）。本次明确的P4授权扩展在原fixture.write_scope登记partner_id，runner在浏览器前强制该字段范围；P0选项仅增加data-record-id供绑定真实候选，无行为变化。选择前监听全部api变更并阻断非目标单字段写入，期望ID取自候选，验证isEditable和刷新UI标签。失败注入仅拦本项目预期partner_id写入；成功只允许一次。同域非零定向36测试及关系L2通过，准备新精确载体重新验证写入；原只读3场景源代码行为未变可携带。

`0e0935a1`严格写入复验failed（`/tmp/frontend-f1-customer-write-scoped-20260923/summary.json`）：只选择客户但请求含`tag_ids:[[6,0,[]]]`，超出本次单字段范围，路由已按预期阻断。旧report误以整体验证布尔填backend_unchanged，已改为独立权威比较，不能把该false当落库证据。归属P0 buildSaveRecordPayload：多选关系无论与原值是否一致均序列化命令，可能由控件初始化触发dirty。最小修复按现有comparableFieldValue跳过未变化many2many，保留显式清空、变更及one2many命令；不按visible过滤，不改写契约，不扩大fixture范围。新增空值/同集合不同顺序/明确清空/新增四反例，随后复验同项目3929，无须重置fixture。

最终客户写入局部复验：`babce9d9`两场景passed（`/tmp/frontend-f1-customer-write-scoped-r2-20260923/summary.json`），真实pm1/user7/company1在专用项目3929选择既有客户6390。所点候选ID独立绑定；全程仅两次预期partner_id请求，第一次模拟网络失败后权威不变、草稿可编辑，第二次业务成功；刷新UI客户标签与候选一致，权威项目/责任35/36事实一致，生命周期仍draft。此次成功可携带74f5de1e三项无写入交互证据：后续P0仅DOM身份属性及保存载荷省略等值many2many，不影响查询/浮层/取消输入。原错误运行仍failed/diagnostic，不回填为pass。L1、4个多选关系载荷反例及原9+5+10+6项目检查、36个runner测试passed；独立复核确认最小修复后允许该精确候选实测。

本次精确受管命令：`PM_LOGIN=pm1 READ_LOGIN=demo_role_project_read PROJECT_ID=3929 P4_PROJECT_PROFILE_BATCH=frontend-f1-rel-20260923 RELATION_WRITE_ONLY=1 ARTIFACT_DIR=/tmp/frontend-f1-customer-write-scoped-r2-20260923 make local.dev.project_profile_write_browser PRODUCT_CANDIDATE_SHA=babce9d963b00e501f6889a003447483434eba39 FRONTEND_URL=http://127.0.0.1:5176`；工具与产品均为该clean HEAD，环境身份见`/tmp/frontend-f1-payload-identity-20260923.log`。独立复核回读summary、两次载荷和facts后确认局部证据有效。已通过原fixture入口cleanup3929/责任35/36，再inspect确认existing_batch=false；日志`/tmp/frontend-f1-customer-scoped-cleanup-20260923.log`、`/tmp/frontend-f1-customer-scoped-after-cleanup-20260923.log`。用户项目4、管理员会话和保留草稿未操作。当前F1仍partial，创建/明确清除/查询错误恢复/完整键盘及F2反例继续开放；未推送PR、未远端CI、未合入、未目标环境部署或整体验收。

边界：客户状态和浮层为P0现有ProfessionalMany2oneFieldControl/useRecordFormState/useRelationRuntime及RelationSearchDialog；查询/错误分类为P0 smart_core通用handler，后端拥有搜索/错误语义，前端只执行。会计JSON先核验类型契约来源再决定Resolver/Registry或后端修复；导航沿现有Runtime，不写客户/会计/收款特例。风险覆盖所有many2one消费者，L1语法/静态→L2关系字段/生命周期非零定向测试→受管客户真实旅程；原F1名称/权限证据只在相关输入未变时携带。广泛浏览器矩阵、完整Quick和远端发布在已知前层阻断消除前不运行。

基线运行结果绑定 `61b8d712`；修复后运行结果绑定 `9b3d65d2`，定向测试绑定提交前相同源码及明确 dirty 范围。后续仅文档变化不使产品测试失效。L0/L1/L2 是本地迭代证据，不代表部署或远端 CI。

2026-09-25 目标环境结果与三个定位任务（本节点**仅文档变更，不改产品代码**；分支 `audit/j13-zero-amount-localization-main`，起点为实时 main `28e4ddffd0f55758382019249249d2f0689d04f7`，PR !20 已合入）。目标环境标签闭环由所有者实测通过：开发服务器 `28e4ddff`、用户 `wutao`——新建标签后立即可搜索、保存前后数据库与刷新回读一致、阶段选择器 7 个候选、专用任务/项目/标签清理后回读均为 0。该闭环在 `project.project` 表单上完成，**不等于 `project.task` 新建入口通过**。①受影响阶段模型（任务1，完成）：`project.task.type` 无 `company_id`、无公司记录规则；公司域修复后域内可见 14（修复前 0）、sudo 14；个人阶段规则仍生效（`pm1` 可见/可读，`sc_project_viewer` 不可见）；删除向导无 `ir.rule`、唯一 ACL 为项目/管理员，三个角色 read/create/write/unlink 全 denied。证据 `artifacts/ci/handoff-20260925/target-acceptance-827fad4b/tag-create-visibility/local-postfix-stage-model-boundary-probe.txt`。②J13 零金额分歧（任务3，定位完成）：登记 `G-F1-10`，独立文档 `j13_zero_amount_localization_20260925.md`——`payment.request.amount` 后端允许 0 草稿（create 落库 0.0/draft），前端按代码推导清空应被必填拦截而显式 `0` 放行，但该推导与既有浏览器记录冲突（`onchange_draft_identity_roundtrip_20260924.md:81-85` 观察到清空后草稿保存成功、旁证 `PRQ2600326`），**冲突未裁决**；`isMissingRequiredValue` 与 `isRequiredFieldEmptyByType` 对 0 结论相反（此条独立成立）；「金额必须大于 0」只是办理前置条件提示；浏览器为 `not_run`，实测阻断原因为 5176 无监听、18081 可登录但 payment.request 入口返回 `NAVIGATION_AUTHORITY_DENIED`/`PERMISSION_DENIED`、本地缺 `sc_frontend_acceptance` 与 `fixture_role_finance`。未改产品代码。③新发现并定位 `G-F3-04`：`/f/project.task/new` 返回「服务暂时不可用」，为契约装配 5xx——原生投影 `fieldDescriptors` 缺 13 个 layout 字段，且模块数据 `view_orchestration_contract_generated_data.xml:259` 的平面 `fields` 编排合成出 `locator=''`、`occurrence_index=0` 的 `name` 节点；把该契约置 draft（savepoint 回滚）只把错误由 `name` 换成 `recurrence_id`，故仅退役契约不足以修复；影响全部原生表单装配，交 P0 决策。④部署后最小验收（任务2）：创建→再次搜索→保存→刷新回读→清理已由上述目标环境结果覆盖，**只读拒绝一项仍为未覆盖**，待目标环境补做（复用 P4 夹具入口，不新建环境）。本轮定向验证：`make ci.local.iteration` passed（16 tests，L1）；无 L2/L3/L4/L5 变更输入。下一项：①裁决「清空金额是否被拦」（在能渲染该表单的环境拦截 `api.data` 写入、观察是否发出写请求），②产品裁定草稿 0 是否合法（J13），③`G-F3-04` 的装配层归属决策。本轮未推送、未建 PR、未部署。

2026-09-25 many2many 合并后复验（PR !20 已合入 main；分支 `audit/j13-zero-amount-localization-main` HEAD `8b557213`，产品代码 = 实时 main `28e4ddff`，差异仅 `docs/ops/iterations`）。因 !20 改动共享字典公司域（`project_context.py`），关系查询输入已变化，故在受管环境重跑该套件：`M2M_ONLY=1 PROJECT_ID=4067 PM_LOGIN=pm1 READ_LOGIN=demo_role_project_read P4_PROJECT_PROFILE_BATCH=m2m-readonly-20260925 make local.dev.project_profile_write_browser` → **23/23 PASS**，`summary.json` sha256 `300cc93e…`（本次新证据，不替代历史 19/19 与 23/23）。此前登记为**未覆盖**的只读拒绝本轮通过：`m2m_readonly_principal_cannot_modify`——只读账号（`demo_role_project_read` user 37，`acl_write=false`）直接 `api.data.write` 得 HTTP 403 `PERMISSION_DENIED`，权威 `tag_ids` 保持 `[34,36]`；同账号表单路由落 `/access-denied?reason=NAVIGATION_AUTHORITY_DENIED`，拒绝文案可见、`tag_ids` 内可编辑控件数 0。夹具回收：project 4067、carrier 4068、tags 34/35/36、UI 新建标记标签 37、责任 61/62 全删，`clean=true`；inspect 回读 `existing_batch=false`、`project=null`、`tags=[]`、`responsibilities=[]`。候选前端已 `local.dev.candidate.frontend.down`（pidfile 移除、5176 关闭）。**分层**：本项为本地候选证据（产品代码等于已合 main），**不是目标环境证据**；目标环境 `28e4ddff` 的只读拒绝仍待部署车道补做。证据（仓外）`artifacts/ci/handoff-20260925/target-acceptance-827fad4b/m2m-readonly-20260925/`。

2026-09-27 `many2one_reference` 契约映射修复（本节点**产品代码 + 文档**；分支 `audit/j13-zero-amount-localization-main`，起点 HEAD `b896cc8d`，未推送／未建 PR／未部署）。浏览器确认 `mail.notification` 详情整页不渲染，错误 `PROFESSIONAL_COMPONENT_FIELD_TYPE_MISMATCH:sc.input.text:many2one_reference`，定位为只读技术踪迹字段 `sc_source_res_id`（`fields.Many2oneReference`，`model_field="sc_source_model"`）：视图解析层把字段类型当 widget 名透传，契约最终绑定只支持 `char` 的 `sc.input.text`。修复：`many2one_reference`／`reference` 不再冒充 widget 名，并在契约层显式绑定只读展示 `sc.display.text`（与 `json` 既有处理同构，**不放宽 `sc.input.text` 校验**），同时携带声明类型与目标模型指针（`model_field`／`referenceModelField`）。复验：定向 `test_unified_page_contract_v2_kanban_action_registry` 10/10、`test_native_view_parser_surfaces` 36/36、`test_unified_page_contract_v2_mobile_compact` 92/92；`verify.unified_page_contract.v2.assembler`／`.runtime` PASS；`ci.local.iteration` PASS（L1）。浏览器（候选 5176＋18081、`demo_full`）：`/f/mail.notification/318` 整页渲染、字段全部只读、「关联单据」显示来源名称、`console_errors`／`http_5xx` 为空；列表→详情→返回 3 行真实行、返回 URL 与列表一致；三态 ORM 复验 normal→`act_window`、deleted→`UserError 关联单据已不存在。`、denied→`AccessError`；夹具（`mail.notification`／`mail.message`／`res.partner.category`）清理回读全 0。顺带复核 G-F3-04：`/f/project.task/new` 现已正常呈现（任务名称必填／当前阶段／执行人／截止日期／优先级，无 5xx、无 mismatch、`console_errors` 为空），`/f/project.task/23` 同；证据推翻此前「`project.task` form 仍失配」的静态推断。新登记 G-F3-05（本缺口）、G-F3-06（有权限来源的「打开关联单据」在浏览器被导航授权层拒绝，独立缺陷）、G-F3-07（`properties` 静态命中与浏览器观测冲突，未裁决）。分层：**本地候选通过；远端 CI／已合并／已部署／目标环境验收均未发生**。
2026-09-27 `project.task` 写入闭环与引用类型边界（本节点**产品代码 + 文档**；分支 `audit/j13-zero-amount-localization-main`，上一节点 HEAD `cbf2b354`）。①G-F3-04 收口（任务2）：上一节点只证明 `/f/project.task/new` **能打开**；本轮补完真实写入闭环——受管环境（前端 5176／后端 18081，`demo_full`）「合法必填 → 保存 → 刷新回读 → 清理」全通过：保存成功并重定向 `/f/project.task/195`，刷新后任务名称一致，`console_errors=0`、`http_5xx=0`；夹具回收后回读 `remaining_count=0`、id 195 不存在。真实 500 根因与契约装配无关，登记为 **G-F3-08**：`smart_core` `api.data` create 的 `merge_orm_create_defaults` 把 `default_get` 的**全部模型默认值**物化进 `vals`，给 `project.task` 注入 13 字段（含 `sc_state='draft'`），触发模型守卫 `_ensure_no_direct_state_write` → `TASK_GUARD_DIRECT_STATE_WRITE` → 500。因果实测：同 `vals` 直连 ORM `create` 成功、经该函数合并后失败，唯一差异为 `sc_state`；浏览器真实 create 载荷 `{"name","stage_id":false,"date_deadline":false,"priority":"0"}` **不含** `sc_state` → **不是**契约 `ct_req=true`／前端提交所致（纠正此前推断）。修复：平台新增通用钩子 `smart_core_create_default_skip_fields`，`merge_orm_create_defaults(..., skip_fields=...)` 不对声明字段物化默认值（客户端显式传值仍透传并受模型守卫约束）；`smart_construction_core` 声明 `project.task: ("sc_state",)`。非零定向：`test_api_data_execution_policy` 8/8、`test_api_data_sudo_scope_order_boundaries` 5/5、`test_api_data_list_param_boundaries` 38/38。字段权限未因复用 occurrence 丢失（真实路径 sudo `su_env`）：form `create` 7 字段／5 可写、`edit` 37 字段／18 可写，`drift_readonly=0`、`drift_required=0`；`demo_full`／`wutao`／`demo_role_pm`／`demo_role_project_read` 四角色 `ok=True`。②G-F3-05 影响边界（任务1，完成）：`reference`／`many2one_reference` 共 21 字段／19 模型，唯一 `required=True` 的 `rating.rating.res_id` 为 `compute`+`store` 且无视图声明（不可编辑）→ **不存在「必填引用无法填写」消费者**；可编辑非只读消费者的 `required` 全为 False；契约探针中引用字段一律 `sc.display.text`／`display`，无一处回落 `sc.input.text`。**前端无 `referenceModelField` 消费代码**，故元数据透传 ≠ 通用引用名称解析／跳转已完成；通知页「关联单据」名称来自 `sc_record_name`（`char`，`related`），非引用字段自身解析。③修正上一节点两处结论：其一，「`demo_role_pm`／`demo_role_project_read` 的 `project.task` form `ok=false`（`ir.model` AccessError）」系**探针传入非 sudo `su_env`** 造成，真实路径 `BaseIntentHandler` 在 `su_env=None` 时构造 `SUPERUSER_ID` 环境（`base_handler.py:74`），正确环境复验两角色 `ok=True`；其二，`project.task` 能打开**不是**「原缺陷被证伪」，而是 `b896cc8d` 的已有代码修复，被证伪的是「缺 13 个 descriptor」的诊断（此前用错误探针用户误测）。④G-F3-06 定位完成（任务4，不改导航权限）：`action_sc_open_source` 返回的 `act_window` **无 `id`**；`normalize_odoo_action_result` 用 `_resolve_action_id_for_model` 以 `sudo()` 取该模型**最小 id** 的 `act_window` → `project.task` 命中 `349 = project.act_project_project_2_project_task_all`；前端 `router.beforeEach` 对 `record`／`model-form` 路由在 `actionId>0` 时要求该 id 出现在**由可见菜单派生**的 `routeAuthority`，而 349 **无任何菜单绑定**（`project.task` 的 18 个 `act_window` 实测 `menus=[]`）→ 必然 `NAVIGATION_AUTHORITY_DENIED`。结论：非用户权限问题、也非业务返回了错误 action，而是 P0 `smart_core` 导航入口身份合成的缺陷（写入了用户从未被授权的 action 身份）。修复方向（下轮）：`_resolve_action_id_for_model` 只返回当前用户经可见菜单可达的 action；无可达 action 时不伪造身份（保持 0），并实测定稿前端在无 `action_id` 时的记录路由行为。⑤新登记 G-F3-09（`sms.template.preview` 装配 `ValueError: field occurrence identity is incomplete`，G-F3-04 同族，未定性）、G-F3-10（`ir.actions.server`／`ir.model.data`／`privacy.lookup.wizard.line`／`app.view.variant`／`mail.mail` 契约探针 `ok=false`，原因未查，不得据此定性为产品缺陷）。分层：**本地候选通过；远端 CI／已合并／已部署／目标环境验收均未发生**。下一项：G-F3-06 最小修复 + `G-F3-07` 可见非空条件下的 `properties` 裁决。

2026-09-27 G-F3-06 导航入口身份修复（本节点**产品代码 + 测试 + 文档**；起点 HEAD `48a85a8c`＝已发布候选，本修复**不并入**该候选批次）。根因：`smart_core` `normalize_odoo_action_result` 仅在 `target=="new"` 且显式 `view_id` 时放弃合成 action id，其余一律 `_resolve_action_id_for_model`（`sudo()` 取模型最小 id）；`mail.notification.action_sc_open_source` 返回的 `act_window` 声明了 `res_model`＋`res_id` 但无 `id`，被合成 `project.task` 最小 id `349`，该 action 无菜单绑定 → 前端按可见菜单派生 `routeAuthority` 必然 `NAVIGATION_AUTHORITY_DENIED`。修复：把判据改为「业务动作已声明目标（显式 `res_id`，或 `target=="new"`）即不合成」，目标身份复用仓库既有 `entry_target.record_entry` 关联记录导航契约（`model`／`record_id`／`entry_intent`／后端 `model_write_authority` 事实），未新增授权机制、未放宽鉴权；未声明目标时保留原解析并用新增反例锁定。定向：`test_navigation_entry_target` 14/14（含 2 条新增）、`navigation_contract_boundary_guard` PASS、`test_execute_button_server_action_boundaries` 17/17、`test_scene_normalizer_entry_target` 1/1；`test_identity_resolver_entry_target` 的 1 项失败经 `git stash` 在未改动版本复现，属既有基线失败。浏览器五类（5176／18081、`demo_full`、列表身份 `action_id=860&menu_id=675`）：可读来源打开成功落 `/f/project.task/140` 且渲染任务表单、URL 无 `action_id=349`；不可读来源（`ir.actions.server:199`）停留通知页并显示后端拒绝文案；悬空来源停留通知页显示产品文案 `关联单据已不存在。`；篡改 `/f/ir.actions.server/199` → `access-denied?reason=PERMISSION_DENIED`（后端裁决）；返回回到通知详情且按钮仍在。夹具（消息＋通知）清理回读 `remaining_notifications=0`、`remaining_messages=0`；`http_5xx=0`。同时完成 G-F3-07／09／10 正式入口可达性分类（`app.view.variant`／`ir.model.data`／`privacy.lookup.wizard.line`／`sms.template.preview` 菜单数为 0，`ir.actions.server`／`mail.mail` 仅有 Odoo 基础／管理菜单）——只分类、不修；**「菜单数为 0」只说明不是直接菜单入口，不能解释装配期异常（G-F3-09），也不能排除按钮／向导／关联入口，故 G-F3-07／09／10 保持待分类、不关闭**。追加反向锁定（同一节点，独立提交）：显式声明的 action 身份必须与声明的目标模型一致，冲突时不再作为入口身份（详见缺口清单「追加三」）；定向 `test_navigation_entry_target` 17/17（新增 3 条含正向对照）、`navigation_contract_boundary_guard` PASS、`test_execute_button_server_action_boundaries` 17/17、`test_scene_normalizer_entry_target` 1/1，未重跑浏览器矩阵。分层：**本地候选通过；远端 CI／已合并／已部署／目标环境验收均未发生**。下一项：G-F3-07「可见且非空」条件定性；J13 独立保留。

| 层 | 命令/证据 | 结果 | 归因和下一步 |
| --- | --- | --- | --- |
| L0 | preflight + worktree/HEAD | passed：起始 clean，唯一工作树 | 从 main 精确基线建立专题分支 |
| L1 | `make ci.local.iteration` | passed：16 tests | 推荐器按旧 origin/main 提示 86 个历史路径；本轮不采纳为扩大范围的依据 |
| L2 | `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture` | passed：29 tests | 验收工具原有安全边界 |
| L2 | `make verify.frontend.create_record_user_journey.unit verify.frontend.canonical_form_presenter.unit` | passed：6 旅程检查点；170+10 呈现用例 | `/tmp/frontend-f1-l2-20260923.log`；不替代真实写入 |
| L0 环境 | `make local.dev.ready local.dev.health` | 首次 failed：HTTP 403 | environment_defect：运行容器仍挂载已退役的旧专题目录 |
| L0 恢复 | `make local.dev.up`；`SC_SOURCE_REVISION=<基线完整 SHA> make local.dev.up` | passed | 复用原 project/库/卷，重新挂载当前代码；补齐运行态版本声明，无模块升级 |
| L0 恢复核验 | `make local.dev.health` | passed | `/tmp/frontend-f0-health-20260923.log` |
| L3 载体 | `CANDIDATE_GIT_HEAD=<基线 SHA> CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND=SERVE_FROZEN_LOCAL_DEV_CANDIDATE make local.dev.candidate.frontend.up` | passed | `/tmp/frontend-f1-carrier-20260923.log`，只构建当前业务验收载体 |
| L0 精确运行身份 | 同上身份参数 `make local.dev.candidate.frontend.health` | passed（首次因版本未声明拒绝，恢复事实见上） | `/tmp/frontend-f1-identity-recovered-20260923.log`；后端源码/版本/库/filestore 同候选 |
| L3 对象准备 | `make local.dev.project_profile_write_fixture P4_PROJECT_PROFILE_MODE=prepare P4_PROJECT_PROFILE_BATCH=frontend-f1-20260923 P4_PROJECT_PROFILE_CONFIRM=PREPARE` | passed | 项目 3919、公司 1、责任明细 26/27；pm1 写 ACL/规则允许；只读账号 ACL 拒绝。`/tmp/frontend-f1-prepare-20260923.log` |
| 批次业务复核 | `local.dev.project_profile_write_browser`，项目 3919 | passed（保存/恢复子范围） | `/tmp/frontend-f1-browser-r2-20260923/summary.json`：网络失败草稿保留、真实重试、完整明细回读与刷新一致；生命周期未变 |
| 清理 | 同批次 `cleanup` → `inspect` | passed | `/tmp/frontend-f1-cleanup-20260923.log`、`/tmp/frontend-f1-after-cleanup-20260923.log`；项目3919及责任明细27/28已清理，批次不存在 |
| 权限子范围 | `PERMISSION_ONLY=1 … local.dev.project_profile_write_browser`，项目3920 | passed | `/tmp/frontend-f1-permission-r2-20260923/summary.json`：user37/company1，实际 role_code=project_member；直接同值 write 403/PERMISSION_DENIED、权威事实不变；精确目标转入NAVIGATION_AUTHORITY_DENIED拒绝页 |
| F0 安装版本 | fixture inspect | passed | `/tmp/frontend-f0-installed-version-20260923.log`：smart_core 17.0.1.1.12、smart_construction_core 17.0.0.168，state=installed，与源码一致 |
| F1 字段反例 | 项目3920清空名称并保存 | failed：product_defect | `/tmp/frontend-f1-counterexamples-20260923/summary.json`：系统编号只读通过；name空字符串却写入成功，触发P0/P1修复。该专用对象已cleanup，见`/tmp/frontend-f1-auth-cleanup-20260923.log` |
| L2 P0 修复 | `make verify.frontend.create_record_user_journey.unit` | passed | 编辑空文本/隐藏已提交字段/关系必填/未修改历史空字段，独立审查又补required boolean=false合法反例；`/tmp/frontend-f1-required-l2-boolean-20260923.log`，10新增用例+原6检查点 |
| L2 P1 修复 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=<3个完整方法>` | passed（3方法合计） | 首次前缀选择0 tests判失败；精确选择3方法中批量拒绝通过，2方法因Html规范化断言失败；只改测试比较规范化前值，重跑2方法通过。原始日志`/tmp/frontend-f1-name-l2-exact-20260923.log`、`/tmp/frontend-f1-name-l2-html-20260923.log`，不掩盖失败 |
| L2 P4 | `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture` | passed：31 tests | 增加专用对象权限反例模式的越界拒绝测试；原有范围/身份门禁保持 |
| L0/L3 修复后身份 | 同受管入口重启后端与候选前端并 health | passed | `/tmp/frontend-f1-fixed-identity-20260923.log`，源码/载体均 `9b3d65d2`，复用原库与卷 |
| F1 修复后 | `PERMISSION_ONLY=1 … local.dev.project_profile_write_browser`，项目3927 | passed：6场景 | `/tmp/frontend-f1-fixed-counterexamples-20260923/summary.json`：编号只读；必填错误零写请求且草稿可编辑；直接API空名称拒绝且同请求description不落库；改正保存及刷新一致；只读角色直接write403和精确拒绝页。业务校验仍为500/INTERNAL_ERROR，另记G-F1-06 |
| 清理 | `frontend-f1-fixed-20260923` cleanup → inspect | passed | `/tmp/frontend-f1-fixed-cleanup-20260923.log`、`/tmp/frontend-f1-fixed-after-cleanup-20260923.log`；项目3927及责任明细31/32清理，existing_batch=false |
| L2 P4发布 | `make verify.gitee.formal_pr.unit` | passed：11 tests | `/tmp/frontend-f1-pr-publication-l2-literal-20260923.log`；含新专题准确创建/回读、无效元数据拒绝、实际Make字面量传递与保留的不确定写入防重复边界 |
| L5 | 独立复核 / 远端 CI / 合并 | 产品局部、P4追加及15路径公开范围复核passed；CI/合并 not_run | 产品summary SHA256 `4cd9af17796bb0df80adebea19dbd569f23b80f8282ffb8aeacffcb0f21e1c92`；仅允许F1首个局部补丁进入集成，不代表全F1通过 |

高风险写入前已确认对象命名空间、库与公司及原始明细；收尾必须用同批次 `cleanup` 检查引用、清理并 `inspect` 回读。开发实测不升级为目标环境部署验收。

独立复核：已确认P0布尔false不能视空并补反例，P4按钮计数必须绑定精确拒绝页（已修），5个form-only入口不虚构列表职责（已修）。项目原生视图来源可承接；较历史候选变化的decoder/presenter/页头/关系/导航只保留历史观察，不冒称当前验证。新字段校验仅影响保存前置；已有网络错误处理/明细序列化未改，正向原证据保留来源，修复后补实际保存与刷新。

当前状态：F0 范围去向已登记、受管版本核验完成；F1 名称校验、失败草稿恢复、成功回读及权限拒绝子范围已实测，F1全部验收未完成｜未合入｜未部署｜用户验收未完成。剩余F1包括表单级/服务端错误的页面恢复，以及隐藏伴随字段、附件载荷；重复/取消/离页和occurrence反例在F2收敛后回验本任务。初步排期以工作量而非组件数估算：F1补齐上述反例并关闭错误分类；F2至少2个独立机制修复（竞态、occurrence），各需定向反例与项目回归；F3按89项职责逐域排期，3项会计入口先解除身份阻塞，目前不承诺整体完成日期。

[English](business_entry_surface_normalization_batch_1_20260913.en.md)

## 1. 本轮变更

- 目标：关闭项目资料办理面的正式入口、真实保存和网络失败恢复链。
- P1：项目资料字段、日期范围、说明、责任明细及资料保存/生命周期动作边界。
- P0：共享保存错误把浏览器原始 `Failed to fetch` 本地化为可操作的网络错误提示，不含项目模型特例。
- P4：受管 `local.dev` 专用数据生命周期、正式菜单旅程、单次写请求阻断、失败/重试分段报告、实际控件快照和主记录/责任明细权威回读。
- 未完成：浏览器无权角色拒绝反例因既有凭据不可用保留为未覆盖；Batch-2 未启动。

## 2. 影响范围

- 模块：`smart_construction_core`、共享 contract-form 前端、`scripts/verify`、`make/dev.mk`。
- 启动链：仅修复项目经理既有授权菜单的运行时投影，不改变认证或公司上下文。
- contract/schema：不新增 schema，不绕过契约；沿用 `ui.contract.v2` 与 `api.data op=write`。
- 路由：正式菜单使用 `menu 681/action 861`；不把手拼路径作为授权入口。
- 数据：仅操作 `sc-local-dev/sc_dev_demo` 中受管专用批次，未使用项目 2/8 写入。

## 3. 风险与边界

- P0：网络错误文案为共享前端行为；定向测试约束其不泄露原始浏览器错误。
- P1：资料保存不推进生命周期；本次回读保持 `draft`。
- P4：runner 的正常保存和失败恢复期望已分离；恢复 PASS 要求失败前后实际控件值及明细操作一致、主记录及责任明细内容未变、错误元素真实可见；两次浏览器尝试中仅一次到达后端并成功。
- 未覆盖：无权角色浏览器反例。既有后端权限证据继续复用，但不替代该浏览器缺口。

## 4. 验证

- `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture`：PASS，13 项。
- `create_record_user_journey_test.ts` 经仓库现有 esbuild 入口执行：PASS。
- 受管失败恢复：PASS。首次请求被阻断；错误摘要元素真实可见并单独截图；失败前后名称、双日期、说明和责任明细控件快照一致，明细保持新增/修改/删除三类操作；主记录全部涉及字段及责任明细角色、人员、备注均与初始化事实一致。同会话重试业务成功，权威回读与刷新全量一致。
- 预收口 `make ci.local.quick`：在生成报告门禁前的守卫均通过，随后因新增测试导致 test inventory 陈旧而按预期失败；已使用 `make refresh.generated_reports` 对齐。最终 exact-head Quick 由冻结候选的受管 receipt 和独立评审包记录，不在本文预声明结果。

## 5. 产物

- 浏览器摘要：`/tmp/p4-recovery-evidence-0913/summary.json`。
- 可见错误元素截图：`/tmp/p4-recovery-evidence-0913/failure-feedback-visible.png`。
- 失败态整页截图：`/tmp/p4-recovery-evidence-0913/failure-before-retry.png`。
- 成功刷新截图：`/tmp/p4-recovery-evidence-0913/recovery-after-refresh.png`。
- 摘要 SHA-256：`e27df862a76c680f5be2b1016b6ba0ed2888fb4889520bd1760556cd4e91a0ce`。

## 6. 数据处置与回滚

- 批次：`recovery-evidence-0913`；项目 374。
- 清理：PASS，项目与责任明细 `[24,25]` 已由受管入口删除，`clean=true`；后续 inspect 确认批次不存在。
- 回滚：按提交边界反向回退 P4 runner、P0 错误本地化和 P1 入口/页面提交；无需业务数据库回滚。

## 7. 下一步

- Batch-1 已归档。PR #465 最终 HEAD 为
  `73842d9248867599a54f9ce4647381b2ab59ea28`，其后于初始交付候选增加三项审查修正：
  共享字段/P4 runner 缺口关闭、组件接管清单刷新、登录角色与业务角色判定分离。
- 最终 PR HEAD 的 `frontend_release_gate`、`merge_policy_gate`、
  `professional_quality_gate`、`public_guard` 与 `release_candidate_gate` 均为
  `SUCCESS`。GitHub 没有人工 review 记录；独立代码复核与 CI 证据不得表述为
  GitHub 人工批准。
- squash 合并提交为
  `dbf1e171281bd920c39099be7085718c892b10f4`；最终 PR HEAD 与合并提交的 tree
  均为 `2f52649c86587c94e9dfbc1e318538eca41741e2`，产品内容一致。
- Batch-2 另行实施；不再重跑 Batch-1 浏览器保存链。
