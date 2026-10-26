# 产品使用缺口完善迭代（2026-10-26）

状态：执行中。以完整走查17组功能问题为输入，先恢复阻断业务办理的表单/入口，再收口呈现和权限声明一致性。
唯一结果索引 `.agent/runs/PRODUCT-USER-GAP-CLOSEOUT-20261026/run.json`；不重开已完成走查任务。

起点 e0bd7d35b2d8ffcb1d4bbed1b841b98ba424a274，包含已冻结审计记录；当时观测的主线/日常部署
bdef29e11ed83db03ef18ec3ecbb6a71bb6d8963。沿用同一工作树，另建fix分支，不新建运行环境。

Formal Product Layer：诊断区分P0通用契约机制/消费和P1原生业务声明；未确定根因前不修改产品。
Layer Target / Module：smart_core通用接入、smart_construction_core标准原生视图与业务元数据；
前端只允许通用消费修复，P4仅承载诊断和验证。无客户定制或运行配置补丁。
Why Here：标准产品缺口回到事实所有者，避免以种子补数或前端模型特判掩盖。
Blast Radius：按捕获契约与实际根因推导精确受影响入口，局部测试和回归后再进入集成。

验收：每个修复均需声明→消费→实际行为证据；保留权限拒绝、数据完整性和缺契约停机机制。
回退：按层级独立提交/受保护revert；如涉及受管升级，另绑定原环境恢复点，不假设代码revert恢复数据。
首批产品声明已修改，尚未集成或部署，用户交付仍未通过。Demo重建留在后续数据任务。

## 接管增量：真实日记账草稿与子行值缺失语义（2026-10-26）

P4提交d9c2be503扩展已有workspace草稿探针与Make包装器，固定account.move菜单175，
从system.init取得入口，复用现有账号、sc-local-dev/sc_dev_demo、namespace ns_000000000002
及候选前端。保存/create/write/unlink/业务动作继续被拦截。探针等待本次新建根联动与
新增line_ids命令的实际HTTP/ok响应，要求行数精确+1；passed只代表草稿传输。
L1、语法及11项请求策略单测通过，独立复核无S0-S2。未添加新的环境、凭据或fixture。

首次真实候选d9c2be503：受管up/build/health与静态资源身份均通过，demo_full在菜单175
新增日记账项目，0→1行、2次HTTP200/ok、blocked0/errors0。根联动返回journal_id=3、
currency_id=6（CNY）。新子行却把未取得默认值的currency_id/company_id/tax_ids等字段全部
发送为''，服务端仅返回tax_lock_date_message=false、没有line patch。截图已查看。
证据journal-browser.log及journal-draft-browser/d9c2be50398e22a871ede098cb205f968b213b28/report.json。

P0提交112f80f40修复one2manyUtils通用请求构造：新行onchange使用default/edit/server-patch
登记的字段集合，排除展示占位值及id:false；显式false/0/空字符串、只读默认值继续传递，
虚拟行key不变，写入时readonly/force_save规则不变。新增反例在旧代码实际失败，保留
child-presence-before.log；child-presence-checks.log中的L1、默认值55项及新增断言/既有
子表边界、关系生命周期及7项守卫、严格类型检查通过；child-presence-dirty.log通过。
独立复核无S0-S2，生成差异仅源码行数/摘要更新。

复验候选112f80f408a31d412340c834dbc7317187c6e4a9：健康、资源index-CpmASzhI.js身份
与草稿流程通过；新行请求已为[0, virtual_key, {}]，0→1行，blocked0/errors0；服务端仍仅
返回tax_lock_date_message=false，无line patch。因此本修复仅关闭“占位空值污染原生请求”，
不证明子行币种初始化成功。证据journal-presence-browser.log与
journal-draft-browser/112f80f408a31d412340c834dbc7317187c6e4a9/report.json；受管up/build
日志使用journal-presence-runtime/up前缀。原始文件均在本批.runtime目录，不随Git克隆。

下一步：在原有api.onchange/default_get协议内补齐独立子行初始化，绑定当前授权父视图的
关系字段、comodel、inverse、父草稿与context，保留字段/记录权限及虚拟身份；先用真实ORM
验证原生行为，再接入新增行的等待/过期响应保护。禁止以父币种特判或仅移除校验补偿。
根初始化await/空changed_fields与真实保存覆盖也仍待闭合。

运行服务保留在112f80f40；后续记录提交只改变文档，不伪造运行SHA。无模块升级、demo重建、
持久业务写入、主线集成或远端日常部署。FG15未关闭；尚未验证保存、落库回读、精确清理或
角色拒绝，也未通过点击保存证明前一轮原生必填覆盖修复在真实页面生效。

## 接管增量：原生位置与保存校验覆盖一致（2026-10-26）

起点d9d2e2f9f，P0通用前端契约消费。历史走查原件journal-form-failure.json显示auto_post
存在多个原生位置：位置readonly修饰符与模型descriptor.required/readonly并非相同事实。
FormSection依据原生位置生成规则，保存链却用扁平layoutNodes计算必填覆盖期望，可能把
只读位置算成缺失校验。这解释了前轮以“已有默认值”绕开检查的错误方向；不据历史快照
断言当前真实页面已通过。

useRecordFormFieldSchemas复用实际渲染的nativeLayoutNodeToFieldNode投影，按可见原生树
收集可编辑必填字段，再经presentation/page接入保存检查。隐藏祖先不遍历，重复业务字段
去重，关系字段不下钻子视图；无原生树返回null，沿用原有非原生校验。判断不读取字段当前值，
可编辑必填位置没有注册时仍阻断。独立复核发现可见字段映射null会误算为空集合，已修复为
显式ContractGapError，同时保留字段合法不可见分支。

证据：native-required-l1.log、native-required-l2.log、native-required-l2-reviewed.log、
native-required-guards.log位于本批runtime目录。L1通过；既有原生位置套件及新增7项边界
通过；实际保存调用链91项、真实表单引擎74项、严格类型检查通过；契约依据15项守卫通过。
独立复核最终无剩余S0-S2（仅此差异范围）。生成报告更新由既有提交钩子处理。

尚未做真实日记账浏览器保存/落库回读/清理；子行带父草稿的原生初始化及根初始化等待问题
仍开放，FG15不关闭。未切换服务、部署、重建数据或集成主线，无数据库写入；回退按本次独立
提交revert。下一步先验证当前原生位置修复的真实页面，再按请求/响应定位子行初始化缺口。

## 接管增量：恢复保存校验覆盖保护（2026-10-26）

用户确认上一执行者已暂停，当前执行者接管同一工作树。实际接管HEAD为
`4a996cfb4aa83fed3ecbfeffdc7fe2499e25a8fd`；下方49c/b976交接身份是历史记录，
不可再作为当前源码或运行候选事实。接管时唯一未提交文件为useRecordRelationshipFields.ts。
此前提交遗漏6个run.scope路径使agent.run.resume返回reconcile；已核对纳入原批次，恢复入口通过。
这仅修复范围记录，不代表此前新增代码已验收。

P0 / 通用前端保存编排 / useRecordFormActions：d76706577把已有值的必填字段排除出校验
覆盖期望集合，使缺失组件注册的adopted表单能绕过覆盖检查。恢复按契约必填位置计算，
不以当前值替代组件实际验证。独立复核确认该回归。未提交的“父币种填子币种”补丁已移除，
该文件恢复接管HEAD内容；没有将会计业务推断放入通用前端。

真实保存调用链反例：必填name有默认值，移除section注册，断言保存拒绝、写入次数为0、
显式返回校验未完成。修复前3/87失败且写入边界被调用1次，修复后87/87通过。
证据均在原runtime目录：takeover-validation-before.log（保留失败）、takeover-l1.log、
takeover-l2.log。L1通过；adopted engine 74、create defaults 55及既有子表边界断言、
关系生命周期测试与7项守卫、strict typecheck均通过。模拟网络写入边界不等于数据库保存验收。

当前FG15仍开放：子行只default_get后通知父关系变更，没有独立的原生子行初始化及父草稿
inverse绑定；须先捕获真实新增行请求/响应，核对字段spec、父关联和context，再实现通用机制。
根创建初始化仍使用默认字段作为changed_fields并fire-and-forget，空默认表单未覆盖；
adopted组件注册缺口须在注册/契约所有者修复，不能再次降低覆盖检查。历史记录中的“最后一个
保存阻断”不是完整结论。下一步沿此范围诊断，保存、回读、精确清理及角色拒绝尚未验收。

本增量未修改运行环境、未部署、未集成主线、未重建demo；没有持久业务写入。回退使用独立
提交revert，不能把恢复校验绕过作为缺口解决方案。原始测试日志留本机，不改变批次active状态。

## 执行工作区交接（2026-10-26，接手先读）

交接状态：本轮执行已收口并停止新增任务，批次仍active，等待下一执行者接手；不是批次验收
完成、主线集成完成或产品交付完成。不得另建平行结果台账或将该批次标为completed。

### 工作区与身份

- 唯一执行仓库：`/home/lidefend/workspace/sce-backend-odoo-entry-validation`。
- 分支：`fix/demo-product-completion-20261026`；交接记录前HEAD：
  `49c38622c7b73a89b82bac360b7c4e6a42f9c58b`。交接文档提交后的最新HEAD用`git rev-parse HEAD`读取。
- 交接前工作区干净，所有产品与探针改动已提交；没有待提交补丁、运行中的测试或待接续exec会话。
  独立复核代理已结束，无并行写者。保留正在运行的验收服务，不关闭容器或删除工作树。
- 唯一任务索引：`.agent/runs/PRODUCT-USER-GAP-CLOSEOUT-20261026/run.json`；所有任务文件
  范围以其scope为准。目标文件`.agent/goals/PRODUCT-USER-GAP-CLOSEOUT-20261026.yaml`保持active。
- 基线锚点PR735/main `5b58d6a1b2ac759c2f1c1cac26e820236fd74f9f`仅覆盖既定manifest/ORM范围。
  批次起点e0bd7d35与历史日常部署bdef29e11不是当前候选；交接未查询新的远端状态，不据旧记录
  推断当前远端HEAD、CI或合并资格。此次未推送/开PR/合并，也无最终发布冻结、Quick或外部归档回执。

### 运行服务与证据身份

- 已登记环境：project=`sc-local-dev`，DB=`sc_dev_demo`，dbfilter=`^sc_dev_demo$`，
  namespace=`ns_000000000002`，入口`http://127.0.0.1:18081/t/demo`；候选前端5176。
  沿用sc_local_dev_*卷及规范凭据；不得新建或手拼环境、凭据、fixture。
- 最后通过健康/浏览器验证的服务候选：
  `b976394010599e9a2e9cb7675809fb4de0de1d7e`。交接只读PID记录仍指向该候选（进程身份以受管工具回读为准）。
- 交接已逐项比较Git对象，确认服务候选与49c38622c的`addons/smart_core`、
  `addons/smart_construction_core`、`frontend/apps/web`、现有浏览器探针和`make/dev.mk`一致；
  差异为记录文档。不要因文档HEAD变化重跑无关产品测试，也不要伪造服务SHA为文档SHA。
- `local.dev.candidate.frontend.health`强制当前clean HEAD、pid候选及后端source stamp一致。
  因此不能把历史服务SHA当当前HEAD直接重跑该入口。下一实际候选完成并提交后，按受管
  down/up/build/health顺序刷新；不要改PID文件或放宽检查来绕过身份差异。
- 第28轮刷新了本地验收服务，无模块升级、demo重建或业务记录写入，不等同远端日常服务器发布。

### 已完成能力和证据边界

- 内核增量11–21：原生表达式严格求值、Python语义跨端一致、context/parent与关系身份、
  草稿生命周期及受权限检查的create关系快照；具体覆盖与失败修复保留在各增量记录中。
- 增量22–27：虚拟行ID；显式onchange错误；授权视图fields_spec与单次原生调用；many2one
  对象到既有传输格式的适配；LINK行数据回放且不覆盖dirty值；force_save；显式子表表单
  数据字段与显示列分离，并继承祖先readonly/invisible、验证全部条件后再合并。
- 关键代码：`addons/smart_core/core/native_onchange_spec.py`、`handlers/api_onchange.py`；
  前端`pages/contractForm/{one2manyUtils,one2manyOnchange,useOne2manyRuntime,useRecordRelationshipFields,useRecordFormState}.ts`
  及`app/x2manyCommands.ts`。修改前按run.scope和提交diff确认完整依赖，不仅依赖该摘要。
- 最终P0定向证据：`twentyseventh-l1-final.log`、`twentyseventh-l2-strict.log`，包括编译器8、
  跨端3739、parser41、实际子表runtime/读取入口、关系生命周期、严格类型与契约守卫。
  独立复核发现的祖先约束及短路问题已修复关闭。
- 真实ORM：`twentyfourth-orm-reviewed.log`为普通会计真实handler的关系清空、非空选择、
  已有记录联动不落库；`twentyfifth-orm.log`为原生LINK数据与持久关系不变；各实际1项通过。
  第26/27轮无后端产品变化，未新增ORM运行，不将旧ORM扩大为新前端保存证明。
- 真实浏览器：`twentyeighth-browser-namespace.log`及
  `native-child-browser/b976394010599e9a2e9cb7675809fb4de0de1d7e/report.json`。
  demo_full/uid40/company1，客户入口`/a/891?menu_id=603`：一次本次输入对应的根字段联动
  HTTP200/ok=true，child_ids从0→1行、5个输入，错误/拦截均0，截图已核对。
- 浏览器**没有验证子行字段联动、保存、落库回读或清理**。探针继续拒绝业务写入。
  P4复核指出的误报及响应关联问题已修复；最终namespace修正由执行者复跑确认，尚无最终
  交付级完整指纹独立复核或发布资格结论。

所有日志/截图原件位于`.runtime/product-user-gap-closeout-20261026/`，为本机忽略目录，
Git克隆不会携带。换机器时需按现有归档规则转交并验证，不得只交Git而声称证据齐备。
原始17组功能问题和23组demo缺口台账仍在本目录的system_function_gaps/demo_data_gaps文档。
累计16组仅局部修复；FG15、完整业务闭环与demo重建仍未闭合，不提高总体通过率。

### 接手后的确切步骤

1. 在上述仓库读AGENTS.md、.agent/context.yaml及协作协议，核对root/branch/HEAD/status，
   执行`make agent.run.resume`。复用当前run与工作树，先确认没有其他写者。
2. 继续run.next_exact_step：复用现有受管浏览器/fixture及write lease机制，增加固定客户父子
   测试记录的保存、权威回读和精确清理。先定义目标公司/角色、唯一记录标识、创建结果ID、
   失败时保留证据与清理策略；禁止按宽泛名称清理既有demo数据。
3. 扩展前检查已有`local.dev.project_profile_write_*`及其他fixture/browser包装器的治理方式；
   只复用工具机制，不把项目fixture冒充客户fixture。现有`verify.local.dev.native_child.draft`
   仅为草稿前置，不能直接放开其全局写拦截器来跑保存。
4. 新P4改动先声明scope、执行L1及非零受影响测试/独立复核；提交clean候选后再更新已登记
   服务。入口是`make local.dev.up SC_SOURCE_REVISION=<candidate>`、
   `make local.dev.candidate.frontend.down/up/health CANDIDATE_GIT_HEAD=<candidate> CONFIRM_LOCAL_DEV_CANDIDATE_FRONTEND=SERVE_FROZEN_LOCAL_DEV_CANDIDATE`
   （down/up/health分别调用），以及草稿探针同一候选参数。当前探针固定res.partner/child_ids，
   无需重跑全部菜单或重建demo；保存入口尚待实现，不能称已可直接运行。
5. 真实保存验证通过后再扩普通业务角色与受影响原生页面。隐式子视图、字段context/order、
   空changed_fields初始化、富会计告警等剩余能力分别诊断，严格维持声明→消费→行为证据。
   只通过受保护PR流程集成；未具备当前源/目标CI结果前不宣称主线集成。

### 回退与执行纪律

本轮无需恢复业务数据；浏览器草稿未保存，ORM夹具由既有事务回滚。若后续保存测试失败，
按所登记的准确记录ID执行恢复/清理；代码回退不能代替数据库恢复。保留本批所有失败日志，
仅在代码/工具/环境依赖明确变化后重跑。候选源码回退通过受管分支或受保护revert，不reset/强推
共享历史。继续单写者、最早失败层优先、受影响证据复用，不另起工作树或平行环境。

## 首批：两个办理工作台的提示声明

P1 / smart_construction_core：班组借扣款、往来款工作台的原生 processing_advisory
绑定各自精确 view/locator，并审核声明草稿计算依赖。复用 P0 已有反馈机制，不改提示文案、
业务动作、权限或前端校验。原生产声明范围由退款单入口明确扩展为三个工作台；
其余六种办理提示仍保持未声明，不把扩大范围等同全部修复。

验证：反馈机制60项单元测试通过；两个工作台及原退款回归11项ORM通过；
补充逐字段变化后3项工作台ORM通过。首轮新测试因默认sudo上下文被拒绝，修正为普通
项目/财务测试用户后通过，保留首次失败日志。独立开发复核未发现S0-S2问题，要求实际页面验证。

P4：追加现有 local.dev 的两工作台浏览器观察入口，复用既有凭据、数据库和候选前端。
仅输入草稿说明，拦截保存/业务动作；验证提示刷新，保留桌面和移动截图。此处尚未执行。
质量验收、劳务、日记账的捕获异常同属 legacy alert 无显式消费者；复杂依赖/原生静态告警
尚待分别补齐，不能用工作台修复冒充这些入口完成。功能缺口 FG06/FG07 待页面证据后再关闭。

实际页面验证增量：首个候选的班组工作台已能加载，但 note 未声明空默认值，前端按缺输入拒绝提示求值。P1 补充两个工作台 note 和往来款 partner_id 的显式 default=False，保留缺失与空值区别；不修改前端 presence 判断。新增 default_get 依赖完整性 ORM 回归。
验证工具修正：5176 预览代理未支持命名空间，改用既有 nginx 18081/t/demo；入口身份已验证指向 sc_dev_demo，静态挂载为当前工作树 dist-dev。首次登录失败和提示缺失记录保留。

## 首批本地验证结果

候选 `342c8b8c67d0f747438fbdd932434dfb095c9d4d`：两个工作台真实菜单进入正常；
初始提示显示，输入办理说明后等待服务端 evaluate ready，说明建议消失；往来单位未填的建议仍保留。
2个入口、桌面/移动各2张截图，未拦截请求、无页面脚本异常、未保存或派发正式业务。
证据：`.runtime/product-user-gap-closeout-20261026/workspace-browser/342c8b8c67d0f747438fbdd932434dfb095c9d4d/report.json`。
已人工检查代表性桌面及移动截图；此范围不代表全部移动适配或业务流程验收。

反馈基础单测60项通过；新增工作台ORM最终4项通过（orm-05），原退款9项回归通过
（orm-02、orm-04中原退款部分）。L1通过（iteration-04）；独立开发复核通过。
新增固定入口 `make verify.local.dev.workspace.feedback.orm` 和 `make verify.local.dev.workspace.feedback`，
原始失败/中间观察保留；最终浏览器断言已排除pending隐藏造成的提前通过。

状态：首批入口/提示局部修复完成；FG06/07正式业务派发与台账回读仍待验收，其他15组未修复。
尚无本次Quick、远端CI、受保护合并或日常部署，不能宣布主线集成或产品交付。
本地开发环境留在上述候选，未重建Demo；文档增量不使未变更的代码页面证据失效。
下一步：按真实依赖类型补齐质量、劳务、机械、分包和薪资表单提示声明，保留缺契约停机；
日记账及审批策略的静态原生告警另行处理。后续再收口语义、移动和权限入口一致性。

## 第二批：机械、分包、薪资发放新建页

P0补充显式 char 与 many2many_presence 反馈输入类型；关系只传布尔存在性，
原生计算使用NewId临时关联，不读取附件内容或持久化。前端支持规范ID数组和单条完整
SET快照（原生default_get空默认值为`[(6,0,[])]`），不猜测局部LINK/多条操作。
P1在三个模型声明精确原生view/locator、compute依赖和空默认值，业务动作/金额/权限不改。
新类型须与对应消费端一起发布；旧消费者不识别新类型会拒绝，不能单独部署声明。

范围：FG11机械成本、FG12分包成本、FG14薪资发放；质量、劳务、薪资核算及静态原生告警
仍未修复。启用清单由3个工作台明确扩至6个模型，未全局放开其他提示。
P4复用原草稿浏览器工具，新增固定cost三入口选择，不保存、不派发正式动作、不上传附件。

验证：`make verify.local.dev.cost.feedback.orm`18项通过，覆盖既有退款/工作台回归、
新表单原生绑定、完整默认值、附件存在性及无附件读取/业务写入、非法输入和越权拒绝；
分包单侧日期缺失单独断言。首次新增测试假设错误已修正，日志保留。
协议及前端测试、严格类型检查、契约边界守卫通过；独立开发复核通过。
实际页面观察尚待执行，不以ORM通过推定用户新建路径完成。

### 第二批实际结果及边界

- 产品提交：P0 `8778ea4e01ac152c26f5442b00f1b5f6e3c8a738`；P1 `174c0a7140dc25846670b90734aedfa22ca1a55a`。最终观察工具候选 `d2aa8cc09e90dd42d195be60cf1585a8b59d1b49`，期间产品代码未变。
- 机械：174候选 cost-browser/report.json 中仅机械case通过；整轮因未切换分包页签失败，不能引用其整轮为PASS。
- 分包/发放：d2候选 cost-browser/report.json 两项通过；按原生页签定位到管理要求/发放说明，等待服务端evaluate ready后核对建议变化，附件缺失建议仍保留。
- 既有工作台：8d1b63a1候选 workspace-browser/report.json 两项回归通过。所有路径均在 `.runtime/product-user-gap-closeout-20261026/`，精确影响与保留依据见 `cost-probe-impact.json`。
- 定向完整ORM18项通过；前端协议、类型检查和契约边界守卫通过。已查看三种代表性桌面/移动截图；独立批次复核通过。

首次页面工具失败分别为未切换业务页签、错误假设标准tab角色；改为组件现有data-section-tab后通过。
这不改变产品行为。页签标准角色缺失作为后续可访问性观察保留，未在本批扩大修复范围。
自动提交钩子的派生变更已审阅：复杂度拆分队列仅更新行数，组件接管清单仅更新输入摘要；
纳入同一run scope，不借生成报告更改产品边界。

目前两批共5个模型的新建入口/草稿提示局部修复已验证，其他12组走查问题仍未修复；
5个已修复入口的保存、附件上传、正式动作和台账回读仍未由这些草稿测试证明。
主线尚未集成，日常服务器仍是原基线，Demo未重建；本地保留d2候选。
下一步继续质量验收、劳务成本和薪资核算的选择/数值依赖，再处理日记账、审批策略静态告警。

## 第三批：质量、劳务和薪资核算条件提示

P0新增selection（以原生选项校验并绑定摘要）与number_nonzero（仅布尔存在性）。
后者只允许经审核的真假判断，不能用于正负、金额大小或有效期间校验；真实数值不进入反馈请求。
P1声明质量验收、劳务用工、薪资单据原生绑定及完整默认值，薪资compute补齐人员/人员姓名依赖，
移除未读取的费率依赖。显式启用清单由6扩至9，未声明的工人提示仍保持拒绝。
新类型须前后端协同发布，不支持旧消费端单独接收新声明。

P4复用既有草稿观察器，固定质量、劳务、薪资核算695、社保公积706、工资薪酬673五入口。
每个薪资入口按菜单身份区分，分别选择工资/公积金业务类型，只编辑草稿，不保存/办理。

开发验证：25项ORM全部通过（third-orm-02.log），含7项条件反馈与前两批18项回归。
首次选择选项变化测试错误地只修改field.selection，未影响Odoo翻译后的运行时选项；
改为模拟原生选项解析器，明确断言旧etag被拒绝，保留首次失败日志。
协议/前端投影测试、严格类型、契约边界、L1通过；开发独立复核无确认S0-S2。
此时页面观察尚未执行，不宣称本批用户入口通过。沿用原数据库，不重建Demo、不升级模块。

第三批页面暴露的后续根因：65db6f6d39a3e3f04fad5bdefd578fe791ae90bb 的首轮观察中，
质量/劳务/薪资核算695通过；706选择公积金后，服务端提示正确但公积金条件区域仍隐藏，
缴存单位无法填写，整轮失败，673未执行。原始report保留，不改检查字段绕过缺口。
P0 followup只让结构容器在精确NATIVE_MODIFIER_INVISIBLE、disabled=false、完整声明依赖时
消费当前草稿条件；字段auth、静态visible=false、权限/未知原因与缺失依赖保持原约束。
真实store/layout测试覆盖切换双向显隐、渲染树更新及五类拒绝；严格类型/契约边界通过。
新fixture首次缺少显式列数、随后空组被正常剪枝，补齐实际字段后通过，未削弱产品守卫。

e9候选复查仍在706失败：旧layout桥单测通过不等于正式canonical消费已修复。
进一步定位到contractFormPresenter的独立容器状态合并；现将窄判定提为共享函数，
两条消费路径一致。补充实际canonical presenter→native bridge切换与六类拒绝断言，
canonical完整定向套件、旧layout套件、严格类型、契约边界及L1通过，独立差量复核通过。
第三次前的候选身份门禁曾因后端revision未同步拒绝，已通过受管local.dev.up对齐，
未绕过门禁。所有失败日志保留；等待新候选实际页面结果。

### 第三批最终本地结果

候选 `b144fac690270caebf0c40fa191d0c993d8f6544` 的五入口整轮通过：
质量686、劳务689、薪资核算695、社保公积706、工资薪酬673。
输入前提示可见，输入后等待服务端evaluate ready，再断言对应建议消失、其他建议保留；
706选择公积金后条件字段区域显示，缴存单位可填写。15条反馈响应，0脚本异常、0被拦截请求。
桌面/手机共10张截图；已核对代表性质量/劳务及最终706桌面、手机图。
证据：`.runtime/product-user-gap-closeout-20261026/conditioned-browser/b144fac690270caebf0c40fa191d0c993d8f6544/report.json`。

最终测试：25项ORM通过（新7＋既有18）；协议/输入投影、完整canonical presenter套件、
真实store/layout响应测试、严格类型、契约边界及L1通过；独立开发复核通过。
最终容器改动仅前端，不使上述未变更后端ORM失效；因修改canonical消费而重跑五入口，
未复跑131菜单矩阵。原65db/e9页面失败和候选身份门禁失败全部保留，不覆盖为成功。

代码提交：P0输入25d7d1866，P1声明f1e5ef7e3，P4观察65db6f6d3；
旧桥容器e9e21f6f2＋正式canonical共享消费b144fac69，回退按后依赖先撤销并协同前后端发布。
新增类型不能单独部署给旧消费者。后续仅文档提交不改变上述运行候选和页面证据。

边界：本轮是FG04/10/13入口与草稿交互的局部修复，薪资类型由测试主动选择，
不证明入口默认类型、所有业务分支、保存/核算/审批/发放或台账回读通过。
累计8组已有局部入口修复，另9组原始功能问题未修复；23组Demo数据缺口未重建。
主线仍为bdef29e11，尚无本轮Quick、远端CI、受保护合并或日常部署。
下一步处理FG15日记账、FG16审批策略静态原生提示，再收口FG17新建能力与入口一致性；
正式业务链及Demo数据验收仍单列，不提前宣布产品交付。

## 第四批：审批规则新建说明

FG16的原生单条静态说明改为P1显式interaction办理提示，保留原文与付款申请条件。
采用现有selection草稿反馈、精确view/locator、完整空默认值；不修改规则发布、
付款审批create/write/unlink禁止直写、审批步骤或权限。
FG15日记账诊断确认是多种混合字段/链接/动作的会计告警，不能当普通提示统一放行；
本批先收口独立可验证的FG16，日记账仍未修复。

P4复用既有local.dev环境、草稿观察器，固定menu424的普通项目/付款两个case；
请求须匹配target_model及evaluate ready，核对说明显隐与名称可填写，禁止保存/派发。
29项ORM通过（新增4＋既有25），源XML在测试事务内加载并回滚。
首次测试夹具撞既有公司/业务模型唯一约束；随后未登记测试数据空间被权限拒绝，
改为复用已有租户测试空间注册器和测试受众组后通过，未削弱权限或以sudo执行被测动作。
L1、语法/diff检查、开发独立复核通过。P0/前端产品代码未变，复用此前严格类型和契约检查。

本批视图变更需要升级：先通过local.dev.snapshot保存原数据库/附件，再用
local.dev.upgrade MODULE=smart_construction_core；升级后验证既有环境权威和精确候选。
恢复需要原快照及本批前代码e984cd72a，不能仅代码revert假定数据库视图已回退。
尚未执行升级与页面检查，不宣称审批规则前台可用或规则发布闭环完成。

### 第四批最终本地结果

候选 `7e1c96e2561cfbb2859a6885f54dba119509c06c`（P1提交969b40ce3）：
menu424新建页普通项目与付款两个场景均通过，说明内容/显隐正确，名称可填写；
4张桌面/手机截图，0脚本异常、0被拦截请求，未保存或派发动作。
证据：`.runtime/product-user-gap-closeout-20261026/approval-browser/7e1c96e2561cfbb2859a6885f54dba119509c06c/report.json`，
已核图付款桌面及普通项目手机。场景key/target在报告中区分，不把同菜单两个场景说成两个入口。

受管数据库/附件快照 `artifacts/local-dev/snapshots/20261025T223016Z` 已分别校验SHA256，
readback在fourth-backup-readback.json。首次升级被fast模式门禁拒绝，按实际XML变更补充
CODEX_NEED_UPGRADE=1、CODEX_MODULES=smart_construction_core后升级成功；未关闭门禁。
fourth-upgrade-02.log记录模块加载和环境权威通过，demo入口保持sc_dev_demo/ns_000000000002。
没有重建Demo。升级恢复须结合该快照与本批前e984cd72a代码，不能只revert视图源码。

29项ORM通过，L1/语法检查及开发独立复核通过；P0/前端产品代码未变，复用先前类型/契约检查，
既有页面证据仍归属各自原候选，不因本次模块升级宣布所有页面重新验收。
本批仅FG16入口和草稿交互局部通过；规则保存/生效/步骤顺序及付款参数发布仍未验收。
累计9组原始问题已有局部入口修复，另外8组未修复；23组Demo缺口未重建。
FG15混合会计告警仍需独立声明及消费方案，FG17能力入口一致性仍待处理。
本次没有Quick、远端CI、受保护合并或日常部署；主线仍bdef29e11。


## 第五批：首页可理解性与手机配置标题

P1提交030a115ca把风险卡正文中的状态键改为原生字段selection标签，沿用当前语言；
查询权限、机器优先级、记录ID和跳转目标不变，缺少标签显式拒绝。
P0提交b3deb58fc把首页能力区文案改为“工作入口”，空态说明可从菜单办理或联系管理员；
未增加授权能力，保留加载、错误和空态分支。配置上下文仅在480px以下改为单列，
标题和动作各占整行；未更改全局集合页头或桌面规则。

3项定向ORM通过：原始记录目标、三种活跃状态标签/优先级、未声明标签拒绝。
页面头75项守卫测试、28个模型用例、4个适配入口及真实组件挂载34项检查通过；
样式守卫、严格类型、契约边界（open_defects=0）、L1及开发独立复核通过。
最初P4几何探针和既有vendor选择器被守卫拒绝，改为公开布局状态/精确选项文案；
未修改守卫或抬高基线。失败日志fifth-frontend.log、fifth-frontend-02.log保留，
成功日志fifth-frontend-03.log、fifth-observer-final.log；没有借用失败为通过。

真实只读观察复用sc-local-dev/sc_dev_demo/18081，无保存、动作派发、升级或数据重建。
候选b606eef05324de68c32556c446e38af92a919608下四角色首页全部通过：
demo_full和demo_role_pm真实风险样本显示“已升级/已认领”，finance/project_read
沿用各自可见的项目风险提醒；三个普通角色实际为空态，显示新说明。共6张普通角色截图，
报告各记录原账号、state、文本，0脚本异常、0被拦截请求。
第一次配置截图仍在读取页面目录，因此补充等待“选择业务页面”可见且可用，
只复跑受影响的demo_full观察，不重复三个普通角色。
最终候选3894dda3586abc3167a364d4ac487d7dc3a0575f下管理员首页、390/1440配置标题
三用例通过，4张截图；人工核图确认标题可读、动作不遮挡、手机按钮在下方、桌面横排。
配置验收仅覆盖标题及页面选择按钮就绪；其他能力异步加载、选择业务页面后的配置/发布
不在本批验收范围，不能称整个配置工作台已经完整验收。

证据目录`.runtime/product-user-gap-closeout-20261026/usability-browser/`：
四角色首次报告归b606eef05324de68c32556c446e38af92a919608，最终管理员报告归
3894dda3586abc3167a364d4ac487d7dc3a0575f。两候选间仅P4等待条件和运行记录改变，
产品、数据权威、账号及普通角色断言未变，故保留三个普通角色原始证据及先前L2。
最终文档提交不改变产品与浏览器输入。当前本地运行版本为3894dda35，回退本批可按
P4→P0→P1撤销；本批无数据库结构/视图变更，不需本批新增数据库恢复。

FG01/02/03本地已验证上述修复范围；不据此证明所有语言、所有角色、风险处置闭环、
无授权账号或配置发布完成。累计12组已有局部修复（其中本批3组为体验问题），
另外5组FG05/08/09/15/17未修复；已有9组业务入口仍需完整业务链验收。
23组Demo数据缺口仍未重建。FG15确认13处混合告警，含字段、嵌套链接/动作与不同条件，
不得以scalar提示替代全部内容或绕过原生提示守卫；仍需独立完整声明及消费方案。
下一步优先诊断FG17入口能力一致性，并继续FG15及其余业务链。
未执行Quick、远端CI、受保护合并、日常部署；主线仍bdef29e11，不能宣称整体基线或交付完成。


## 第六批：新建入口与目标权限一致性

FG17定位为P0声明传递/投影问题：原生列表解析已产出capabilities，
app.view.config的tree API导出却丢失该字段；v2集合页又把模型ACL直接作为创建能力，
未合并原生form/tree禁建声明与入口create/no_create限制。
P0提交205881c30原样导出tree capabilities，并在集合创建裁决中取权限与声明的交集。
保留其他操作权、现有表单拒绝、模型ACL和记录规则；无前端模型特判，无P1业务权限放宽。
更新assembled cache版本/pin；源缓存已有addon内容指纹，防止沿用旧源声明。

L1通过；132项投影测试、23项运行协议测试及assembler/runtime守卫通过。
原生ORM为1个测试、4个分支：允许、form禁建、tree禁建、action context禁建，最终全通过。
测试走原生view/action→parser→app.view.config→assembler，事务回滚，不留新夹具。
先前ORM暴露head.view_type来源、tree capabilities导出两个问题，均修复后定向重跑；
独立复核发现的_field_rows附带变更已撤销。原始失败sixth-orm.log、sixth-orm-02.log、
sixth-orm-diagnostic.log保留，最终结果为sixth-orm-final.log，未放宽断言。
投影最终日志sixth-projection-final.log；P4守卫7项通过，开发独立复核无阻断发现。

P4提交39ab0318e65741c09f7fb497cdfb8a2fa77ffb8b复用固定local.dev观察器，
以demo_full/company1仅检查三个受影响入口：
- menu176日记账项目：集合create=false，无可执行新建；直接新建契约仍以FORM_CREATE_NOT_ALLOWED拒绝。
- menu703税务报表：集合create=false，无可执行新建；入口只读限制在新建契约中保持拒绝。
- menu702税务申报：集合create=true，新建按钮可用，点击后表单出现申报期字段，create=true。

真实浏览器三用例通过，4张桌面截图，0脚本异常、0被拦截请求；核图税报无新建、税务申报表单正常。
本地候选为39ab0318e65741c09f7fb497cdfb8a2fa77ffb8b，证据在
`.runtime/product-user-gap-closeout-20261026/create-authority-browser/39ab0318e65741c09f7fb497cdfb8a2fa77ffb8b/report.json`，
命令`make verify.local.dev.create_authority`，环境身份门禁与候选健康检查通过。
无保存、派发、导入或直接业务写接口测试；不据此证明业务保存、申报闭环或所有角色权限验收。
手工访问被禁止的新建地址仍沿用既有诊断页；本批修复列表误导入口，没有声称诊断页工程文案已优化。
税报截图同时确认与FG08同类的技术字段/枚举展示问题，登记为同类受影响页面，仍未修复。

本批无XML/数据库结构变更，不需升级/重建；仅重启并构建既有本地候选。
P0回退205881c30应与缓存身份一起回退，P4观察器单独回退；没有本批业务数据恢复需求。
前端产品输入未改，沿用第五批类型/样式/契约守卫，真实浏览器验证当前消费者。
最终文档变化不使上述证据失效。累计13组有局部修复，FG05/08/09/15四组仍未修复；
FG17本轮只完成上述入口一致性范围，其他业务链/角色/直写权限仍须后续验收。
23组Demo数据缺口未重建。下一步处理FG09证书列表声明和FG08通用报表标签，FG15混合告警继续独立收口。
没有Quick、远端CI、受保护合并或日常部署，主线仍bdef29e11，整体交付基线未重新宣布成立。


## 第七批：证书列表真实信息呈现

P1提交dfdf41622为证书动作声明专用原生tree并显式绑定tree/form：证照名称、编号、
持有人、有效期置于首列，保留状态、登记编号、项目及发证信息。priority90避免抢占
同模型默认视图；既有共享form/search、证书domain/default_fact_type、groups和ACL不变。
修复归属行业入口声明，不向前端增加模型特判，也未补造Demo证书数据。

2项定向ORM通过：真实v2契约包含证书字段且排除资料/制度专用字段，制度入口保持自己的列；
共享借阅/资料表单、分类和ACL既有断言保持通过。测试在事务中导入XML并回滚。
L1、观察器守卫7项、语法/diff与开发独立复核通过；P0/前端产品代码未改，复用上批类型/样式/契约检查。
日志seventh-orm.log、seventh-l1-final.log、seventh-observer-final-02.log。

XML需要升级，先由local.dev.snapshot生成
`artifacts/local-dev/snapshots/20261025T225820Z`数据库与filestore备份；已读取文件并核对
manifest SHA256，见seventh-backup-readback.json。备份对应升级前DB、代码2ad75738f，
当时工作区有已声明XML修改，不能把快照说成含新视图。随后执行
`make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core`，
模块加载、demo入口sc_dev_demo/ns_000000000002及环境权威校验均通过，无Demo重建。
恢复本批须结合原快照与升级前代码；仅revert XML不能保证数据库action/view绑定恢复。

P4只读观察绑定menu356、708和当前用户可读真实记录，不执行保存/派发/关注/留言/删除。
初次276bf275897d4335c0e53fbf94348e4fd95c64b8中证书桌面/手机/详情四字段匹配，
制度708列隔离通过（真实0条），但详情时间线读取被观察器拦截，整体报告failed。
第二次5acfcc1b1375581856918de1a002bff3c5b860ca时间线HTTP200/ok通过，其后关注者读取
又被拦截，报告仍failed。检查实际loadTimeline→loadFollowers调用链及两个只读handler后，
将两种读取限定为certificate模式、固定模型和从本次列表提取的记录ID，并等待两者HTTP200/ok；
其他写请求仍禁止。两个失败报告全部保留，不改记为整轮通过。

最终候选d095e061a9efdd6ed81e36f748cc28ac1e6a1bff只重跑受影响menu356：
已有安全生产许可证的名称、编号、持有人、有效期四项在1440/390列表及只读详情逐项匹配；
两项协作读取均HTTP200/ok=true，0脚本异常、0被拦截请求，3张截图。
人工核图：手机卡片直接显示四项完整信息；桌面已有对应列，长编号/单位沿用现有截断样式，
详情显示完整值。不是“全部桌面文本无截断”的验收。
制度708复用276候选中的独立列断言与截图，允许空列表，不把Demo空数据误判为字段修复失败。
三候选之间仅P4读取白名单/等待条件及记录改变，产品、XML、数据库和708断言未变；
不因候选身份变化复跑不受影响页面。最终文档不使上述证据失效。
证据根`.runtime/product-user-gap-closeout-20261026/certificate-browser/`，各报告归各自完整SHA。

本批完成FG09上述信息展示范围，未证明搜索筛选、多角色权限、证书新建/办理/到期提醒全链。
累计14组原始问题有局部修复；FG05薪酬混合列表、FG08透视标签、FG15混合会计告警三组仍未修复。
23组Demo数据缺口仍未重建，制度空数据仍保留在数据缺口中。
本地运行d095e061a；未执行Quick、远端CI、受保护合并或日常服务器部署，主线仍bdef29e11。
下一步处理FG08通用透视字段与selection标签，继续保留FG05/FG15及业务链验收边界。


## 第八批：FG08报表原生标签与枚举（2026-10-26）

本批仅在既有entry-validation分支迭代。P0解析器从当前用户原生字段元数据投影label、fieldType、selection，
显式XML标签优先；通用前端消费声明，缺失元数据或未知枚举进入错误态，不显示原始码兜底。
分组使用原始值/关系ID，因此同名项目与同名枚举标签不会合并。后续将透视列省略关闭，长名称换行。
未加入行业模型翻译表，未修改P1业务数据或XML。产品提交dd54fed46、fe3cdbb56。
契约缓存版本随语义提升，输入摘要与守卫同步；hook生成的复杂度行数和前端inventory摘要已复核。

L1初次因新增路径仅记于observations、未进入run.scope而失败，归为证据范围登记缺陷；
补齐精确路径后eighth-l1-scoped.log通过，后续换行eighth-wrap-l1.log通过。原失败保留。
定向验证：37个原生解析测试、132个投影测试、23个运行时测试；前端renderer/collection和9个coverage测试；
严格类型、契约依据15绑定、样式与观察器7项守卫均通过。真实ORM
`TestProductReports.test_analysis_contract_projects_native_labels_and_selection`一项测试覆盖两个原生action的pivot/graph四分支，0失败/错误。
日志为eighth-frontend.log、eighth-projection.log、eighth-orm.log、eighth-wrap-checks.log。
P0/P4开发独立复核均无阻断。无需XML升级或Demo重建，沿用sc-local-dev/sc_dev_demo/ns_000000000002。

首个浏览器候选bdfb1bd144972fcb393533d07dadb81dd62d55e5的703pivot/704pivot/704graph，
1440/390六个观察均通过，零错误/拦截。但人工核图仍见长标题截断，因此不把其透视截图当最终可读性证据。
唯一产品增补为AnalysisPage透视列关闭ellipsis；按影响分析只重跑703/704的pivot两个页面和两个viewport。
最终候选 **40805e49f9fb463ce132435a374a1e04ffdac1a4** 两case通过，4张截图，0错误/拦截；
税务1条1组，劳务3条3组，全部中文标签和每个已加载度量与API记录逐项相同。
劳务分包登记/结算各280000，用工人数24、工时192保持一致。税务当前草稿的各金额均为0，未伪造数据。
手工核图确认桌面长标题完整，项目/单位/日期换行；手机长值换行，仍沿用横向表格浏览，未宣称全部列同屏。
图表DOM/消费算法未改变，复用bdf候选704graph的分组/首度量证据；原报告身份不改写。
证据：`.runtime/product-user-gap-closeout-20261026/analysis-browser/<上述各SHA>/report.json`及截图。

FG08仍为局部修复：未完善金额格式，月interval仍未消费，客户端按已加载记录求和而非证明全量聚合；
图表仍仅渲染首度量，真实样本首度量全0不能表达分包登记/结算金额。当前样本loadedRecords=reportedTotal，
这不能代替任意分页/筛选/完整业务账对账验收；这些限制已回填功能台账。23组Demo数据缺口未重建。
累计15组原始问题有局部修复，FG05混合薪酬列表、FG15富会计告警尚未修复，各组完整业务链仍待验收。
本地运行40805e49f；未执行Quick、远端CI、合并或日常部署，主线/日常仍bdef29e11。
本批回退只需受管恢复73af2acd7前后端，保留第七批已升级数据库，无本批业务数据或XML迁移回退。
下一步修FG05，继续保留FG08剩余能力与FG15。最终文档提交不使上述产品证据失效。


## 第九批：FG05混合薪酬列表（2026-10-26）

P1为工资薪酬673声明专用原生tree，priority90且显式action绑定；不修改原domain/context/权限。
模型增加非存储只读payroll_display_period/amount：工资取年度月份与net_salary，补助/奖金取occurrence_date与amount；
缺失期间保留空，不生成零年月。字段help明确金额不是已付款，原核算/发放/源值保持。
不在前端判断业务类型，不向Demo补假工资年月。产品提交60f98a123，后续列序修正870a36bd2。

L1通过。ninth-orm.log记录3个实际测试、0失败/错误，覆盖三类金额/期间、依赖变化/类型切换、
非存储只读、原值不覆盖，以及673与695/706原生契约隔离、既有domain/菜单。
P4在既有只读观察器添加固定673/695/706；从当前列表ID经同用户api.data read回读源字段，
与computed及列表逐条比较，再核对桌面/手机的类型/期间/格式金额，未扩大写权限。
观察器7项守卫通过，P1/P4独立复核无阻断。前端产品代码未变，复用第八批type/style/basis结果。

升级前local.dev.snapshot生成`artifacts/local-dev/snapshots/20261025T233220Z`，DB和filestore可读，
manifest SHA256核对通过（ninth-backup-readback.json）。快照为df7eaa452阶段已安装旧视图，
工作区当时有声明内修改，不能说快照含新视图。两次local.dev.upgrade均通过模块/环境/入口权威校验，
沿用sc-local-dev/sc_dev_demo/ns_000000000002。本批回退须prebatch df7eaa452代码加此快照，不能只revert XML。
两次升级之间仅调整视图顺序，无业务写；初始快照仍是整批回退锚点。无Demo重建。

第一候选a9c049a7f87429bbbd263f3af3cbf2815efdc50a的源值和桌面通过，手机卡片前三项为金额/类型/人员，
期间落入折叠区，观察器正确失败。未执行695/706，不把该报告记为整轮通过。
P1将专用tree期间/金额移到人员之前，沿用通用移动卡片；测试新增前四列顺序断言。
仅重跑受影响原生collection ORM（ninth-mobile-orm.log，1项0失败/错误），复用未改的计算/domain测试。
新列序需再次升级，ninth-mobile-upgrade.log通过；原失败报告保留。

最终本地候选 **870a36bd26e12dac7c0073b4a63c73e2804bfc1d**：673的两条现有记录逐字段回读，
奖金BONUS-BF26000011金额3500、发生日期2025-05-20；工资金额16200、期间2025-05，币种均CNY。
1440/390两种页面逐记录类型、日期、金额均匹配，无“实发工资/年度/月”工资专用列误导。
人工核图确认奖金手机卡片直接显示¥3,500.00、奖金及2025-05-20；桌面两条均正确。
工资卡片需纵向滚动，DOM断言通过，不把首屏截图说成全部记录同屏。
695返回1条，706为空，均未混入新字段；这只是相邻入口隔离，不是其全功能验收。
3cases、4截图、0脚本错误、0被拦截请求；证据payroll-browser/870a36bd26e12dac7c0073b4a63c73e2804bfc1d/。

FG05此批完成现有工资/奖金列表展示范围，未完成三类型真实数据覆盖与完整办理链：补助当前无样本，
缺口已另记demo_data_gaps，不将ORM等同Demo页面证明。未验证缺失草稿期间视觉、多币种、计算列排序/筛选/汇总、
新建保存/付款/多角色。原始23组Demo缺口未重建，新增本地补助覆盖观察不改原始计数。
累计16组原始功能问题局部修复；FG15日记账新建尚未修复，FG08分析语义及各业务闭环仍待完成。
未执行Quick、远端CI、合并或日常部署；主线/日常bdef29e11保持。本地运行870a36bd2，最终文档不使产品证据失效。
下一步处理FG15原生会计新建页，保留凭证约束；后续统一业务链验收与Demo重建。


## 第十批：平台内核原生表达能力覆盖研究（2026-10-26）

用户将FG15修复提升为平台内核能力覆盖研究，本批据此调整范围：先区分原生声明的语义、
解析保真、契约承载、前端消费、交互闭环与证据，再决定通用能力补齐顺序。
研究身份7052f80c0e13af03ac0ad9332e7241c3e14455de加本批明确parser/test差量；
复用单一run与原始走查，不建立平行覆盖台账。此为源码/代表样本审计，不是所有Odoo语法、
全部安装视图或90入口重新执行的覆盖率报告，不能给出全平台百分比。

### 结论与证据口径

平台已有原生视图复用骨架，但尚不能宣称原生表达语义完整覆盖。
“组件已注册”“表单structural”“数据可读”“浏览器可打开”“业务交互等价”是不同证据等级。
源码：`scripts/verify/frontend_project_domain_rollout.py::classify_surface`对form直接返回structural；
`docs/frontend_productization/domain-rollout/accounting-center-coverage-v1.md`的PASS仅覆盖3个foundation
入口（account.journal、account.analytic.account、account.analytic.distribution.model），不含175/account.move。
原PASS保留其原范围，不据此称审计伪造；问题在于不能把局部结构报告提升成系统语义交付结论。

原始175契约快照提取出13处混合告警、4个#outstanding链接，原文/条件/节点结构均保留在
`tenth-native-expression-inventory.json`（含原始artifact摘要，明确历史证据身份）。
该入口原生widget还包括account-tax-totals-field、payment、section_and_note_one2many、
res_partner_many2one、many2one_avatar_user、email、statusbar；这里只列需求，不把名称出现当已支持或已缺失。
当前普通accounting_user真实ORM额外证明本批解析修正，不能代替整个表单可运行。

### 分层能力表

“局部支持”表示已有机制及限定证据，不等于所有组合正确；“待证明”表示还不能下完整支持或缺陷结论。

| 原生能力 | 当前判定 | 断点/已知边界 | 主要声明与消费依据 | 补齐验收 |
| --- | --- | --- | --- | --- |
| form/group/notebook/field、重复字段occurrence | 局部支持 | 主结构、字段控件已有；inline分支曾丢身份/条件，本批修正 | native tree/form parser、contractFormPresenter、NativeFormTreeRenderer | 合并继承后的真实arch→每个occurrence→DOM/状态一一对应；重复字段互不串值 |
| invisible/readonly/required复合条件 | 有机制，但有确认语义缺口 | 生产端可丢未知子表达式；客户端未知返回false、空数组真值存在差异 | utils/native_modifier.py、app/modifierEngine.ts | 完整编译或显式拒绝；同输入跨端差分；缺失依赖不得当False |
| parent/context及字段间比较 | 部分支持/上下文待证明 | value_field有支持；点路径被当平面key时需要明确上下文绑定；函数调用无完整语义 | native_modifier.py、resolveDeclaredModifierFieldValue、relationDescriptor | 根/子记录/上下文分别声明命名空间、可读依赖、生命周期；禁止任意执行Python/JS |
| 标量提示与草稿建议 | 有显式限定协议 | sc.feedback.message仅标量源、受限条件/证明；不是富内容容器 | node_component_validation.py、native_advisory.py、nodeComponentPresentation.ts | 保留既有拒绝边界，不扩大到任意混排节点 |
| 富提示：文字+字段+按钮+嵌套条件 | 未有完整承载/消费 | 13处会计告警不能平铺为字符串；现在明确failclosed | component.yaml、nativeTextPresentation.ts、NativeFormTreeRenderer | 独立声明式region能力，绑定原生来源/用途/条件，按原顺序消费children；后代独立授权 |
| 片段导航及条件目标 | 静态锚点有限支持 | 现有anchor要求唯一、恒定可见目标；#outstanding指向会计内容，不能直接放行href | sc.navigation.anchor、node_component_validation.py、navigateToDeclaredNode | 精确目标occurrence、目标可见性、tab展开/定位；隐藏/缺失/恶意目标显式拒绝 |
| object/action/stat按钮 | 通用链存在、组合待验 | 权限/安全/record要求已有；正文label此前丢失，本批仅补纯静态正文 | parser::_button_to_action、actionRuleAuthority、execute_button | 原method/context/confirm/权限不变；禁用与撤权、返回动作、实际结果回读 |
| x2many编辑与onchange | 通用能力存在，不能推出会计等价 | 普通关系表、虚拟行/命令路径不证明section/note/account行语义 | onchangeNormalization、useRecordFormState、专业关系/明细组件 | 真实子视图章节/备注行、虚拟ID、onchange往返、行ACL、保存命令及会计平衡 |
| 字段专用widget | 按组件局部支持，其余待证明 | 原生widget到类型控件可能降级；读取数值不能证明payment/tax totals交互 | semantic_resolver、semantic.yaml、component.yaml | 每个widget声明语义、依赖、动作、降级策略；不能用通用输入框冒充完整原生能力 |
| 独立widget节点 | 有限实现 | NativeFormTreeRenderer独立widget分支显式处理web_ribbon；其他需逐项查承载/消费，不能泛称ready | NativeFormTreeRenderer.vue | 注册每个消费分支或明确unsupported，不静默忽略 |
| tree/search/kanban | 局部支持 | 列/筛选/分组及卡片投影已有；不等于完整QWeb或任意修饰组合 | native解析器、actionSurfaceRendererRegistry、ListPage | native列序/字段/作用域与筛选分页结果；模板指令需有限协议，不执行任意QWeb/JS |
| pivot/graph | 可呈现，原生分析语义未齐 | FG08已修标签；按加载记录分组、未消费月interval，graph仅首度量 | actionViewAnalysisContract、AnalysisPage | 服务端全范围聚合、日期桶、多个measure及聚合算子/图型完整消费 |
| calendar/gantt/dashboard | 当前为可读回退 | registry明确core.readable_records/fallback；不是时间布局/拖拽/依赖支持 | actionSurfaceRendererRegistry、view_type_render_coverage_guard | 独立验证原生布局与交互；回退结果不得计入等价支持 |
| 权限、状态与配置扩展 | 有机制，必须贯穿上述每项 | 节点可见不等于业务授权；富容器不能豁免后代，配置不能修改来源证明 | backend node验证、字段/动作status、最终handler复核 | 多角色/公司/撤权/readonly/create/edit与最终执行端一致，未知能力拒绝 |

### 已复现的内核语义问题

只读函数诊断（不是受管验收gate，也不证明当前页面已发生越权）：

1. `state == 'draft' or context.get('show_warning')`经native_modifier编译只剩state分支。
   state=posted、context.show_warning=True时原意为True，丢失分支后的AST结果为False。
   这是“部分理解却输出合法AST”，比明确unsupported更危险。
2. 单独的context.get表达式以raw string残留；consumer给False。未知kind给False，外层not可变成True。
   未知不应被当成已求值的业务布尔值，必须回传明确缺口。
3. field_truthy的空关系集合[]由JavaScript Boolean得到True，而原生Python空集合为False。
   这会影响诸如duplicated_ref_ids的条件；仍需实际字段编码与服务端路径差分验证影响面。
4. parent.state可进入AST，但平面key resolver对嵌套parent对象不解析路径。
   这是上下文绑定必须明确的证据，不断言所有子表路径都已出现故障。

原始输出：tenth-modifier-producer-diagnostic.json、tenth-modifier-consumer-diagnostic.json。
后续需将这些例子转为受管回归，覆盖and/or/not组合、未知子表达式、空关系、False/None/0、
缺失字段、value_field、parent/context依赖及draft/onchange之后的状态。后端业务ACL仍是最终边界，
本研究不把这些呈现语义诊断扩大为已证实的数据越权。

### 内核实现与协作顺序

1. **先保证表达式完整性。** 明确受支持AST集合与版本；一棵表达式必须整体编译成功，不能过滤未知分支。
   原生truth/comparison及关系编码需跨端一致；不支持的函数/上下文路径采用有限受管映射或明确unsupported。
2. **再承载富内容。** 增加独立的声明式富提示组件，P0拥有协议/验证/通用渲染，P1只绑定真实原生视图、
   locator/occurrence、用途和条件。文本、字段、按钮、子条件保持顺序与身份；无v-html、无模型特判、无CSS自动放行。
3. **导航和专用控件单独成能力。** 条件锚点需要目标/生命周期协议；会计支付、税额和行编辑各自证明，
   不因同页使用就全部塞进提示组件，也不能用删节点来恢复页面。
4. **用原生样本做垂直闭环。** 先普通用户日记账create/readonly/edit及告警双向切换，再科目/行onchange、
   不平衡拒绝、合法保存、过账及回读；角色/公司/撤权分开验证。页面加载成功只关闭加载阻断。
5. **扩展覆盖分母。** 从实际发布入口和权限合并后的arch采集表达实例，以模型/action/view/occurrence/
   角色/公司/模式/配置版本为身份；对每项记录解析、契约、消费、交互、证据级别。
   复用现有run/registry/Make/证据复用机制，P4报告不能另创产品规则；缺项、降级、未知和未测分列，不能统称PASS。

上述为本次研究形成的实施顺序；当前没有自动全库采样或新覆盖门禁落地，不能将研究表本身当机器验收证明。

### 本批已完成的有限修正与验证

P0通用inline节点补native_locator/occurrence_index及compiled modifiers，保留文本/children顺序；
按钮无string/title时，只允许纯文本和无属性的span/b/strong/i/em/small提取静态label。
字段/widget/条件/QWeb/hidden/style/class后代均不被扁平化；有显式string/title仍优先，未执行HTML。
这两个修正为后续富提示保真提供基础，没有注册新富组件、没有放宽scalar反馈或legacy alert守卫。

L1通过。首轮parser测试1/39失败：测试XML wrapper在iter中重新包装根节点，原实现按对象identity排除根不可靠；
改为标准迭代的descendants[1:]后通过。独立复核提出hidden/style/class可能影响正文可见性，
进一步限定无属性格式节点并补拒绝样例；最终39项parser测试通过，投影132项+runtime23项通过。
真实普通accounting_user的1项ORM读取实际account.view_move_form，验证auto_post_until嵌套span条件、
4个#outstanding链接身份/文本、2个action_activate_currency按钮的原生label/method保留；0失败/错误。
日志tenth-parser-reviewed.log、tenth-orm-reviewed.log、tenth-projection.log；失败日志保留。
最终静态正文限制变更后39项parser＋1项ORM重跑；132项投影＋23项runtime输入未变且不导入该parser，复用原通过结果。
最终L1见tenth-l1-final.log；独立代码与研究文档复核通过。

FG15依然未关闭，富组件尚未实现，因此本批不重跑已知会失败的页面、不声称日记账能新建。
无模块升级、会计保存/过账、Demo重建、Quick、远端CI、主线合并或日常部署。
本地受管候选仍870a36bd2；本批仅源码/定向ORM阶段，主线/日常仍bdef29e11。
累计仍16组原始功能问题局部修复、23组原始Demo缺口未重建；平台研究不会把数量刷成全绿。


## 第十一批：原生条件编译完整性与跨端真假语义（2026-10-26）

本批承接内核覆盖研究，P0归属`smart_core`条件编译/装配和通用前端消费者；P4仅扩展现有
`verify.frontend.collection_view_semantics.unit`测试入口，不新增环境或业务默认值。
阶段身份为`b48aab84631787302af9ae5a4cbe316af8c1ec8d`加本批声明dirty范围，非冻结交付。

### 已实现

- Python布尔表达式遇到未知分支、动态比较字面或非法语法，整条输出`unsupported`，保留原文，
  不再过滤分支；domain不完整、未知token/operator同样整体拒绝。支持prefix嵌套与隐式AND，
  补齐有符号数字比较字面、数字0、属性路径标识。属性路径标识不代表父记录传输已实现。
- 编译器把静态常量折叠为布尔值，保持原有`static.value`布尔协议；前后端拒绝字符串static。
- 前端原生AST求值器对不支持表达式、非法结构/operator和缺失字段依赖抛`ContractGapError`；
  所有布尔分支先求值，再归约，避免短路掩盖契约缺陷。可选modifier未声明仍代表没有该约束。
- 空数组/空对象的真假采用原生Python口径；后端保留未知为None，不能经NOT或已知分支变成
  已确定的真/假。动作适配器的既有依赖预检仍可提前拒绝，不宣称每条消费路径都抛错。
- 装配缓存版本升为`ui-contract-v2-native-modifier-totality-v1`并重新绑定输入摘要。

### 验证与失败保留

日志均在`.runtime/product-user-gap-closeout-20261026/`，原始失败不覆盖：

- `eleventh-l1.log`：首次diff空白失败；去掉空白后L1通过，见`eleventh-l1-operands.log`。
- `eleventh-l2-reviewed.log`与最终`eleventh-frontend-complete.log`：7项编译器测试、61项跨端检查（Python固定表达式/真实后端求值器/
  前端求值器，包括嵌套domain、空集合、未知分支、缺依赖和静态常量）、39项原生解析器测试、
  canonical presenter现有断言及装配23/运行时132项全部通过。
- 保留`eleventh-l2.log`、`eleventh-l2-followup.log`、`eleventh-l2-final.log`、
  `eleventh-presenter.log`、`eleventh-projection.log`：发现旧fixture未声明blocked、缺依赖负例
  仍断言静默隐藏、以及初版错误放宽static协议。补显式输入/异常断言并修复static类型；
  权限拒绝、正常显隐和动作适配器预检断言保留，没有删除失败或降低门禁。
- `eleventh-frontend-complete.log`：contract basis与strict typecheck通过。
- `eleventh-orm-complete.log`：现有`local.dev.test`入口，在注册`sc-local-dev/sc_dev_demo`内以普通会计
  用户的真实原生日记账视图执行指定回滚管理ORM用例，1项通过，0失败/0错误。
  只证明inline契约回归，不证明浏览器或会计办理完成。
- 独立只读复核最终差量通过，无确认S0–S2；严格求值可能暴露旧契约缺口，仍属发布风险。

### 尚未完成与下一步

这批证明限定表达式样本的一致性，不是完整Python/Odoo表达式等价。比较类型转换、关系ID编码、
like语义、context.get/parent依赖传输仍未完整对齐；未知能力当前显式拒绝，不能计作能力实现。
下一步先补上下文/父记录的有限声明与依赖运输、比较语义及真实契约消费错误态验证，
然后补富提示/条件导航与会计专用组件，再验收FG15完整业务链。

未切换本地服务候选（仍为870a36bd2），未升级模块、重建Demo、推送、集成或部署；
主线/日常开发服务器仍为bdef29e11。FG15未关闭，累计仍为16组局部修复。
本批是内核源码验证完成，运行影响及批次产品验收待完成；不宣称稳定交付基线或全部能力覆盖。
P0源码提交`3ac785fd0`、`809710549`；生成报告仅行数及前端输入摘要更新，已检查。
最后补拒绝函数调用派生空字段与复合AST空字符串操作数；受影响解析器/前端重跑通过。
ORM最终日志对应未再变化的后端源码；末次前端补丁不影响该ORM输入。
回退本批源码恢复b48aab846；没有本批业务数据变更需要回退。


## 第十二批：原生 Python 比较的类型与集合语义（2026-10-26）

阶段身份：`c79e4adc7ae9e4f8fd5be6cca5f17c9c946be215`加本批声明dirty范围。
P0归属`smart_core`编译器/求值器与通用前端消费者；P4仅现有测试、缓存输入锁和结果记录。
检查发现旧比较器字符串化两端且把数组取首项，不能代表Python表达式；
上下文/父记录与关系RPC编码需要声明载体，不在前端猜测后直接放行。

### 实现范围

- 原生Python表达式的比较叶显式声明`semantics: python`。两端按声明分派；没有该标记的
  legacy/domain节点保持原有行为，未知标记后端未知、前端`ContractGapError`。
- 新纯函数比较器保留JSON类型和完整序列，支持等于/不等于、数值/字符串/列表顺序、
  字符串/列表/字典键成员判断；布尔与数值等价遵循Python，数字字符串不转为数字。
  字符串排序按Unicode码点。非法类型比较不制造False结论。
- 支持范围为Unicode标量字符串、有限且绝对值不超过2^53−1的数值、布尔/null和递归JSON
  列表/字符串键对象。孤立surrogate、超范围数值、非有限值明确拒绝。
- Tuple只在成员判断的右侧作为容器规范化；无法保留tuple/list差别的比较和嵌套tuple显式拒绝。
- 缓存版本为`ui-contract-v2-native-python-comparison-v1`；新后端比较器纳入装配缓存摘要。

[Odoo 17视图规范](https://www.odoo.com/documentation/17.0/developer/reference/user_interface/view_architecture.html)
说明原生表达式有字段、context及parent等求值环境，关系值具有原生表达形态。
本批仅关闭有限JSON值比较语义，未把数据库read/display关系值当作原生表达值完整支持。

### 证据和修复

原始日志均位于`.runtime/product-user-gap-closeout-20261026/`：

- `twelfth-l1-import-final.log`：`make ci.local.iteration contract.semantic.registry.generate`通过。
- `twelfth-l2-reviewed.log`及包路径修复后的`twelfth-l2-import-final.log`：现有collection/canonical/assembler/runtime Make入口通过。
  7项编译器测试，3,596项跨端检查（其中21×21×8比较矩阵直接以Python固定表达式为oracle），
  39项原生解析器、23项装配、132项运行时测试；新增4项canonical呈现断言证明语义标记穿过
  契约decode，完整列表及类型差异影响readonly，未知语义进入契约缺口错误。
- `twelfth-frontend-guards.log`：contract basis与strict typecheck通过。
- 独立复核发现S2：UTF-16 substring可能匹配孤立surrogate，双方初版接受此输入。
  已在编译literal、后端递归值/对象键、前端码点校验统一拒绝，并加入负例；复核确认修复。
  初版绿色日志`twelfth-l2.log`保留，不当作Unicode边界覆盖证明。
- `twelfth-orm.log`失败为新增测试定位错误：只找invisible，但实际原生`state != 'draft'`
  存在于readonly。根据原始journal契约改为检查全部modifier桶，未删除非零真实条件断言。
- `twelfth-orm-fixed.log`及最终`twelfth-orm-import-final.log`：指定`TestSystemPermissionAccounting.test_native_journal_notice_parser_preserves_inline_contract`
  经`make local.dev.test`在注册`sc-local-dev/sc_dev_demo`回滚管理测试中1项通过，0失败/0错误。
  验证普通会计用户真实继承视图的Python语义标记及draft/posted两种求值结果，保留inline/link/button断言。

- 首次提交钩子的生成器以独立`core`包加载装配器，暴露跨包导入失败。将纯比较器移到
  `core/native_modifier_comparison.py`并使用同包导入；生成器本身不变。同步scope/index/缓存输入后
  生成入口、受影响后端L2与ORM均重跑通过；路径同步前的L0失败保留于`twelfth-l1-import-fixed.log`。
- P0提交`18b70a42b70d952c66ffbc5eb7ea4d0277bda03e`；生成报告仅源码数量/行数及前端输入摘要变化，已检查。

### 状态与后续

源码定向验证通过；未做浏览器产品验收、主线集成、部署或Demo重建。
当前服务仍为870a36bd2，主线/日常开发服务器仍为bdef29e11；FG15未关闭，累计仍为16组局部修复。
关系RPC/display编码没有原生求值绑定，不能因数组比较正确就宣称关系语义完整；
context.get/parent依赖传输、legacy/domain的like等差异、富提示/条件导航和专用会计组件继续未完成。
下一步建立上下文/父记录与字段类型的显式求值绑定，再做真实消费错误态及受影响页面验证。
回退本批源码恢复c79e4adc7；无本批业务数据写入或部署需要回退。


## 第十三批：context.get声明、绑定与求值闭环（2026-10-26）

阶段身份`93642077811e1b6bf5bc19087b7f4b4ec6a675a2`加声明dirty范围。P0归属原生表达编译器、
装配器和通用消费机制；P4仅现有测试入口、缓存输入锁与单一结果记录。
复用已有`dataContract.dataMeta.sourceContext.context`，不新增上下文来源或业务默认值。

### 本批实现的协议

- 支持`context.get(字面字符串键)`及带已支持字面标量/列表默认值的形式；缺省默认值明确为null。
  支持真假、NOT/AND/OR以及与字段/字面值/另一context.get的Python比较。动态键、动态默认值、
  任意函数、context下标访问、复杂方法链不支持，整条表达式显式拒绝。
- 新AST为`value_truthy`/`value_compare`（显式`semantics: python`），操作数为`context_get`、
  `field_value`或`literal`。比较继续复用第十二批限定JSON值域。
- 后端最终字段/容器/动作状态与前端canonical/原生layout桥都从声明上下文构造内部求值键
  `$native.context`。该键不是模型字段或新增wire字段；mainData/草稿同名值不能替代声明上下文。
  空字典是有效上下文，键不存在时才用表达式声明的默认值；整个namespace缺失/非法时保持未知或
  `ContractGapError`，不能靠默认值掩盖缺声明。
- 空source context保留优先级，不再因falsy而落到其他来源；已编译的条件不再被旧字符串context
  处理覆盖成静态布尔值。原有权限、禁用、静态隐藏和策略拒绝保持约束。
- `field_value`进入现有字段依赖补读闭包，context key不被当作数据库字段读取；创建草稿的读取
  和字段访问检查不变，无sudo。前端容器依赖检查同步使用最终绑定map。
- 缓存版本`ui-contract-v2-native-context-binding-v1`，新context求值器及依赖模块纳入缓存输入锁。

### 检查与失败保留

证据根`.runtime/product-user-gap-closeout-20261026/`：

- `thirteenth-l1-shapes.log`：`make ci.local.iteration contract.semantic.registry.generate`通过。
- `thirteenth-l2-shapes.log`：8项编译器测试、3,710项跨端检查、39项原生parser测试；
  canonical新增7项上下文绑定/动作呈现断言，真实layout hook新增4组空/有/无context及伪造输入用例；
  runtime 23项及装配投影133项通过。全部通过现有Make入口，非零收集。
- `thirteenth-guards-shapes.log`：contract basis与strict typecheck通过。
- `thirteenth-hydration.log`：`verify.business_config.formal_list.unit`的149项handler边界、48项缓存、
  62项视图编排及5项基线工具测试通过，另装配guard通过。新增测试验证context比较中的field_value
  正常补读及拒绝read/拒绝field时不补值，context key不进入mainData。
- 独立复核确认layout容器依赖检查漏用绑定context（S2），已统一最终值map并通过真实hook测试。
  初步提出的live覆盖专用resolver问题未复现：该resolver已有保留键保护；复核已纠正此项描述。
- `thirteenth-l2-reviewed.log`保留旧layout fixture期望缺依赖静默隐藏的失败；迁为隔离的显式异常
  负例，其他权限/禁用/静态隐藏断言保留。`thirteenth-l2-fixed.log`保留负例后未恢复合法store造成
  Vue延迟watch报错；恢复fixture后通过，没有在产品代码吞掉异常。
- `thirteenth-orm.log`保留选错原始证据范围的失败：default_move_type条件来自searchContract，
  不在当前form布局。追溯原始路径后选择真实form的default_journal_id与move_type复合条件。
- `thirteenth-orm-shapes.log`：现有`local.dev.test`指定journal parser用例，在注册
  `sc-local-dev/sc_dev_demo`回滚管理ORM中1项通过，0失败/0错误。要求实际普通会计用户原生表单
  非空命中，检查四种context结果及缺namespace未知，保留既有状态/inline/link/button断言。
- 最后收口补三项非法AST负例：两种比较均要求string操作符，field_value拒绝空身份，避免前端类型
  转换与后端结果分歧。受影响L1/L2/typecheck/ORM重新通过；字段补读访问路径未变，复用其通过日志。
- P0源码提交`39619650d583d47344e90de36a083e31cabb43cb`、`12af199373f07f42d15e06218ba6eee9bc8016d6`。
  生成报告仅源码数量/行数及前端输入摘要变化，已检查。
- 最终开发独立复核通过，无剩余确认阻断项；不等于浏览器或发布批准。

### 尚未覆盖与下一步

这批支持主表单canonical/layout上下文求值，不证明所有原生表达式或所有消费者完成支持。
parent记录帧、one2many行的context传输、关系RPC/display编码、搜索/活动等其他消费路径、
富提示/条件导航和会计专用组件仍待覆盖。新AST要求匹配的后端/前端候选一起验证和发布，
未证明其他客户端兼容，也未做浏览器错误态及完整会计保存/过账验收。

没有服务候选切换、主线集成、部署或Demo重建；当前已登记服务候选仍870a36bd2，
主线/日常服务器仍bdef29e11。FG15未关闭，原始功能组仍为16组局部修复。
下一步建立子表行的显式parent/context求值帧及关系类型绑定，再进入受影响用户路径验收。
回退本批源码恢复936420778；本批无业务数据写入或部署需要回退。

## 第十四增量：子表共享上下文与父记录求值

开发候选以`4231e560488b5fedee03da87d4dc3fa5a748181c`加本节源代码/测试范围为身份；
P0通用消费机制，沿用当前工作树、单一run和验证入口，无业务模型特判。

- 删除子表私有AST白名单，统一消费内核表达式；不再把未知声明静默转换为隐藏/只读。
- 页面从契约store快照与实时父表草稿取得父值，复用已声明的sourceContext.context，
  按关系字段叠加已解析对象context。空上下文有效；缺失底层上下文或未解析字符串不补默认值。
- `$native.context`仅取父级绑定帧，子行同名数据不能替换；`parent.*`仅取父值。
  显示、编辑、必填校验和新增行写入过滤共享按字段解析的帧，父草稿变化即时生效。
- 本轮未增加后端依赖补读：已声明快照中的非渲染父字段可消费，缺少父字段仍显式报错。
  子表parent依赖的后端补读闭包仍须专门验证；不声称所有父字段已由服务端声明齐全。

证据在`.runtime/product-user-gap-closeout-20261026/`：L0 diff检查与`fourteenth-l1.log`
轻量迭代通过；`fourteenth-collection-final.log`覆盖编译器8项、跨端3710项、parser39项及
集合运行时断言。`fourteenth-l2-fixed.log`已有默认值55项和新增真实子表hook行为通过，
覆盖字段上下文隔离、行伪造拒绝、父草稿只读切换、必填和新增写命令。
`fourteenth-l2.log`保留测试AST遗漏Python语义标记的失败，修正fixture后通过；
`fourteenth-l2-fixed.log`同时保留页面FieldDescriptor未声明context属性的类型失败，
改用现有关系默认值消费同样的未知对象读取方式，运行时仍由严格绑定器校验。
独立只读复核未发现新增S0–S2阻断。

此轮仅源代码与运行时单元证据，无浏览器或新增ORM验收，无主线集成、部署或demo重建。
FG15仍未关闭，16组局部修复口径不变。后续：按声明字段类型规范关系值、核验子表parent依赖
补读与嵌套作用域，再推进富内容和真实页面验收；既有行写入策略亦需独立核验。

最终`fourteenth-guards.log`：strict typecheck和contract basis enforce均通过。

## 第十五增量：直接子表父字段依赖补读

候选基于`5d6637a98632f1c3626d40daec9a59e48f6f5345`及本节登记修改，P0通用内核声明
依赖闭包，无业务模型特判。第十四轮已统一前端父值来源，本轮补齐服务端直接子表的标量依赖：

- 收集器按原生`subviews`和字段`subview`显式载体区分作用域；直接子表的`parent.x`映射
  为根模型字段`x`，包含field_truthy、field_compare两侧及field_value操作数。
- 子表本地同名字段不再误读根模型；更深层作用域、残留点路径不映射到根模型。未知字段仍
  由模型字段白名单排除，context key不作为字段读取。
- 新建草稿与已有记录复用原补读路径及权限约束，拒绝读取时保持未知，无sudo、默认真值或
  额外数据库写入。关系集合值仍不在本轮标量补读范围。
- 缓存版本更新为`ui-contract-v2-native-parent-dependencies-v1`，装配输入摘要同步绑定。

证据根`.runtime/product-user-gap-closeout-20261026/`：

- `fifteenth-l1.log`保留首次范围守卫失败：上一轮提交钩子生成的split evidence报告未进入
  累计run scope。本轮登记该生成报告后，`fifteenth-l1-fixed.log`轻量迭代通过，未放宽守卫。
- `fifteenth-l2.log`：handler152、缓存48、视图编排62、基线工具5项通过，assembler guard通过。
  新增3项测试覆盖两种载体、新建读取/字段拒绝、子表同名与嵌套排除、已有记录读取拒绝。
- `fifteenth-runtime-unit.log`：runtime23、投影133、编译器8、跨端3710、parser39及集合语义
  回归通过。前端源代码未修改，沿用第十四轮类型检查与契约依据守卫证据。
- 独立只读复核未发现新增S0–S2阻断，并核对parser与assembler的实际载体路径。

这是服务端依赖闭包与合成契约验证，未执行新增ORM或真实页面端到端验收，无模块升级、
主线集成、部署或demo重建。FG15仍未关闭；下一步为按声明类型规范关系值，再验证嵌套父级、
既有行写入策略及真实原生子表页面行为。回滚本轮内核/缓存变更即可撤销该依赖收集行为，
无数据库恢复操作。

## 第十六增量：子表本地关系字段的原生求值类型

候选基于`3f434d0541c19bc99ffcb97e8231d8dff35adc4c`及本节修改，P0通用消费机制。
查核[Odoo17 Record._computeDataContext](https://github.com/odoo/odoo/blob/17.0/addons/web/static/src/model/relational_model/record.js)：
many2one条件使用记录ID，x2many条件使用当前ID列表。原子表Python比较直接收到显示对
`[ID,label]`，导致与ID字面值或同ID不同显示名字段比较不一致。

本轮按子表完整columns声明选择转换，仅在原生Python操作数/字段真假路径使用：

- many2one接受false、正安全整数ID、`[正安全整数ID,字符串显示名]`，返回false或ID。
- one2many/many2many仅接受已保存ID列表，保留顺序及列表比较语义；空列表合法。
- 非法身份、显示对误作ID列表、关系命令数组显式ContractGapError；类型冲突也显式拒绝。
- 共享求值器递归传递Python字段resolver，context与literal不按关系字段转换；旧domain
  比较保持既有路径。显示、编辑、必填校验和新增写入过滤传入相同完整子表列声明。

范围明确限定子表本地已声明类型的字段；没有推断缺失类型，没有修改父/根记录和后端
状态求值器。未保存x2many命令到ID集合、嵌套父级、既有行写入策略和隐藏依赖类型声明仍需
后续收口，不据此宣称关系字段全覆盖。无schema变更、ORM写入、模块升级、demo重建或部署。

本轮证据沿用`.runtime/product-user-gap-closeout-20261026/sixteenth-*`；新增用例包括ID与
显示对等价、同ID不同显示名、两个字段比较、组合表达式、操作数AST、列表顺序、非法身份、
命令拒绝和旧domain保留，以及真实useOne2manyRuntime草稿改选后的只读/必填/提交行为。

验证结果：`sixteenth-l1.log`轻量迭代通过；`sixteenth-l2.log`编译器8、跨端3710、parser39、
集合语义、默认值55及新增关系/hook行为断言、严格类型检查和契约依据守卫全部通过。
独立只读复核无新增S0–S2阻断。未开展真实页面端到端验收，FG15仍未关闭。

## 第十七增量：form根记录与父记录的关系类型权威绑定

开发候选基于`1fb9b1fcaa9ed87ef70c87c67875976f86e2c18f`加本节登记修改。P0统一契约生产
与消费，不新增业务特判。第十六轮的子表本地类型转换扩展到最终form状态与实时父/根记录：

- 最终form hydration从模型字段定义发布`dataContract.dataMeta.nativeModifierFieldTypes`，
  范围为mainData字段和最终条件依赖（含直接子表parent依赖）；类型信息不代替字段值读取，
  原有访问拒绝仍保持未知值。前端decoder验证类型map为非空字符串值。
- 前后端清除业务数据中的`$native.fieldTypes`伪造值，重新从metadata绑定内部namespace；
  前端实时草稿不能覆盖。Python字段真假、比较双方、context复合操作数使用many2one ID与
  持久x2many ID列表语义；context值与字面值不转换，旧domain比较路径保留。
- 前端子表`parent.x`从父级类型表求值，父记录草稿变化继续覆盖快照字段值。后端最终动作/
  布局状态与前端canonical呈现使用同一声明载体。缓存版本同步为
  `ui-contract-v2-native-relation-types-v1`并更新装配输入摘要。

证据根`.runtime/product-user-gap-closeout-20261026/`：`seventeenth-l1.log`轻量迭代通过；
`seventeenth-l2.log`handler153、cache48、orchestrator62、基线工具5、assembler通过，
canonical真实呈现新增3组关系类型及草稿伪造断言通过，strict typecheck与contract basis通过。
`seventeenth-relations-final.log`编译器8、跨端3732（新增22项关系值形态）、parser39、集合
行为、runtime23及投影133通过。新增元数据来源断言确认模型类型覆盖伪造声明；ID/显示对、
无效身份、空集合与关系命令拒绝均有跨端结果。独立只读复核未发现新增S0–S2阻断。

边界：类型元数据当前发布限定form，未声明类型仍兼容透传，不声称所有裸record消费者已
覆盖；未保存x2many命令仍显式拒绝。本轮无新增ORM/浏览器端到端验收、模块升级、主线集成、
部署或demo重建。FG15未关闭，后续优先处理未保存关系集合的原生求值身份，再核验嵌套父级、
既有行写入策略和真实子表页面。回滚本轮源码及缓存版本可撤销行为，无数据库恢复需求。

## 第十八增量：默认新增明细保留与父级集合求值身份

开发候选基于`8d13b273e49a0b1390f3907d3d3e33a6194395c2`，P0子表草稿生命周期。
调查发现初始化仅提取已有ID，后端默认值的`[0,0,values]`行会被丢弃；先修复该前置缺口，
再按实际行状态生成直接子表父级条件的集合身份。

- 初始化接受完整ID数组，或限定的完整命令快照：首条set(6)、link(4)、create(0)。保留
  默认新增行及已声明默认字段，草稿`id`明确为false；已有行明确带持久ID。
- 不支持缺少基线的update/delete/unlink/clear增量命令，重复/非法ID、错序set及非法
  create payload显式ContractGapError。不能据此宣称完整ORM命令协议已支持。
- 初始化成功后才记录可用于求值的行集合；addRow先从原始值初始化，避免直接新增吞掉默认行；
  clearRows清除初始化状态。父级类型声明为one2many时，从已初始化响应式行集合投影持久ID，
  排除removed和isNew；不把草稿key伪装成持久ID。依据Odoo17普通evalContext的withoutVirtualIds
  语义（源码链接见第十六增量），只有新行时该ID集合为空，不能等同业务“没有明细”。
- 显示、编辑、必填校验和新增写入过滤使用同一父值投影；提交仍使用草稿行生成命令，
  求值ID列表不替代实际创建payload。

独立复核发现S2：create payload中的未投影字段会被原草稿构造器静默丢弃。已在初始化入口
拒绝所有未声明payload字段及伪造id，并新增负例；没有擅自放宽未知字段写入。本轮严格拒绝
代替静默丢行，后续须在声明层补足隐藏默认字段。另确认initRows也被onchange调用，缺基线的
增量回放仍是显式未关闭缺口。

证据根`.runtime/product-user-gap-closeout-20261026/`：`eighteenth-l1.log`轻量迭代通过；
`eighteenth-l2.log`保存首次通过结果；复核修复后以`eighteenth-l2-reviewed.log`为最终结果。
新增实际hook用例覆盖默认行显示/提交、已有与新行混合、删除/恢复的父条件变化、编辑拒绝与
放行、清理后再新增保留默认行；集合用例覆盖快照语法、未知字段与非法身份拒绝。

本轮仍未接通根表单/动作的实时集合投影和后端创建关系求值，也未闭合onchange增量回放、
嵌套父级或既有行写入策略。无ORM/浏览器新增验收，无部署、主线集成或demo重建；FG15未关闭。

最终`eighteenth-l2-reviewed.log`：编译器8、跨端3732、parser39、集合语义、默认值55及新增
生命周期断言、严格类型检查、契约依据守卫均通过；独立复核确认S2关闭，无其他新增阻断。

## 第十九增量：基于当前明细草稿的onchange命令回放

候选基于`7139989a0625d5fd5cb8213c4547bc200016007c`，P0明细命令与表单消费，另有P4
既有静态守卫调用标记同步。未新增环境或业务特判。

- 新增纯副本reducer，以明确的当前rows为基线回放0–6命令：创建新行、更新已有持久行、
  删除、解除关联、关联、清空和替换。update保留未改字段及本地未保存行。虚拟ID目标更新、
  未声明payload字段和非法身份仍显式拒绝，不伪造关联或猜测隐藏字段。
- runtime先prepare再commit；表单先准备所有字段的明细命令，准备失败时不改formData、
  rows或响应覆盖层。提交阶段用finally复位applyingOnchangePatch，契约错误通过可见的
  validationErrors反馈；网络失败继续保留草稿。既有响应过期/跨记录防护保持。
- delete2与unlink3在行状态及写命令中分开保留；新增关联生成link4，避免只生成update1而
  丢关联。set保持声明顺序，clear/set清除未保存行并解除不再选中的持久关联。

独立复核暴露并关闭两项S2：

1. set/clear曾将delete2覆盖为unlink3。现保留删除标记，同批delete后link/update或set
   再包含该ID显式拒绝；unlink后link仍可恢复。新增组合序列回归。
2. 真实formstate入口的旧normalization会把非数组关系响应变成空数组。现向prepare传
   原始值，禁止非法响应变成清空集合。通过真实useRecordFormState入口注入测试请求，验证
   字符串/对象/null响应下rows与formData均不变、flag复位、错误可见；正常响应保留本地新行。

证据根`.runtime/product-user-gap-closeout-20261026/`：`nineteenth-l1-final.log`通过；
`nineteenth-l2.log`保留初轮集合/编译器8/跨端3732/parser39及已有回归通过结果；
`nineteenth-l2-reviewed.log`真实runtime新增回放断言、默认值55和dirty semantics实际入口通过，
随后P4守卫因旧direct-call字面标记失败。同步为仍默认triggerOnchange的可注入请求表达式，
无删除断言；`nineteenth-guards-fixed.log`onchange守卫、4项竞态用例、x2many语义守卫、strict
类型检查及contract basis均通过。独立复核确认两项S2关闭，无其他新增阻断。

本轮没有证明任意line_patches异常后的整体事务回滚，原子性证据限定命令准备失败；虚拟ID
目标、隐藏默认字段声明、根表单/动作实时集合投影和后端创建关系求值仍待收口。无新增ORM/
浏览器验收、部署、主线集成或demo重建，FG15未关闭。回滚本轮命令/接线源码即可，无数据库恢复。

## 第二十增量：根表单、动作与子表共享实时集合求值

候选基于`2e22f93bdc82757a3f0402d0563bb110b6b8422d`及本节修改，P0通用前端契约消费。
原子表父条件已有行状态投影，但根表单仍直接读取可能携带ORM命令的formData，导致同一关系
字段在不同消费路径判断不一致。本轮接通同一投影实现：

- `useOne2manyRuntime.projectModifierValues`只从已初始化且声明为one2many的行集合取得
  持久ID；子表parent、canonical容器/动作、原生layout及依赖就绪检查、动作执行适配列表共用。
- canonical新增独立modifierValues输入，仅用于条件求值；显示仍用原始runtimeValues。
  投影不修改formData、原始命令或写入payload。页面以响应式回调引用完成接线，投影只读
  initialized/rows，不回调列解析，避免新增初始化循环。
- 清理行运行时后不复用旧集合身份；缺少已初始化行且原值是未支持命令时仍显式失败。
  新行不伪造持久ID，静态隐藏/只读、权限和disabled/unknown否决保持。

证据`.runtime/product-user-gap-closeout-20261026/twentieth-l1.log`轻量迭代通过；
`twentieth-l2.log`canonical呈现、真实原生layout hook、默认值55及已有回放生命周期断言、
strict typecheck与contract basis均通过。新增组合用例覆盖实际行runtime删除/恢复对根字段
只读及动作可见性的同步变化、新行排除、原始草稿命令保留、写命令仍携带新行、清理后拒绝。
独立只读复核无新增S0–S2阻断，并核对动作适配及依赖就绪接线。

本轮没有后端源码或数据库改动，不重复未受影响的跨端编译器与ORM检查；没有新增浏览器
业务验收、主线集成、部署或demo重建。后端未保存关系快照、虚拟ID目标、隐藏默认字段声明
以及真实页面交付验收仍未闭合，FG15未关闭。下一步处理服务端创建快照的关系求值权威。

## 第二十一增量：服务端创建关系快照的原生求值

开发候选基于`de92fc82fb993c36f29ac3cf8c5aadf7ccfb88ac`。P0服务端声明及通用消费，P1
仅扩展现有会计权限ORM测试。创建mainData中的关系默认值是命令，不能直接当作条件ID列表。

- 对已在mainData出现且被条件引用的one2many/many2many，使用同一sourceContext和原生
  default_get构造Model.new草稿；保留已有create/read/字段检查，并对关联_origin执行read
  权限与记录规则检查，取合法持久ID。拒绝时不发布结果，不制造空集合。
- 发布`dataMeta.nativeModifierRelationSnapshots[field]={sourceValue,persistedIds}`；
  sourceValue规范为JSON命令形状，mainData原命令不替换，每次最终hydration先清旧快照。
- 前后端只有在当前关系值与sourceValue一致时采用该ID列表；对象键顺序无影响，数值1/1.0
  视为同一JSON数值，布尔与数值不同。草稿变化后旧快照不再生效，合法实时ID数组继续直接
  校验，其他命令保持未知/ContractGapError。已有行runtime投影优先反映实时身份。
- `$native.relationSnapshots`为内部保留namespace，业务数据和实时草稿不能伪造；前端
  decoder验证快照结构。context值、字面值、原始显示/写入数据及旧domain比较不改。
- 缓存版本`ui-contract-v2-native-create-relation-snapshots-v1`与装配输入摘要同步。

证据根`.runtime/product-user-gap-closeout-20261026/`：`twentyfirst-l1.log`轻量迭代通过；
`twentyfirst-l2.log`handler154、cache48、视图编排62、工具5、assembler、编译器8、跨端3738、
parser39、canonical新增快照绑定/伪造拒绝断言、strict typecheck和contract basis均通过。
`twentyfirst-runtime-unit.log`runtime23及投影133通过。独立只读复核无新增S0–S2阻断。

本轮边界：缺失关系源字段不自动补值；虚拟ID目标、隐藏默认字段及完整真实页面业务验收仍未
闭合。普通会计用户的新增ORM用例通过既有local.dev.test入口执行，结果另记于本节最终条目；
该用例使用合成契约调用真实原生草稿，不等同完整页面端到端证明。无主线集成、部署、模块升级
或demo重建，FG15未关闭。

最终ORM与修复证据：`twentyfirst-orm.log`、`twentyfirst-orm-diagnostic.log`保留两次失败。
真实default_get返回Command IntEnum操作码（SET/CREATE），严格JSON校验将其拒绝，导致已有
空ID快照仍得到未知条件；诊断定位到原生命令类型，未放宽通用比较器。仅在关系快照形状转换中
将明确IntEnum转为其JSON整数，原始mainData不修改，并新增枚举跨端用例。
`twentyfirst-enum-fixed.log`受影响后端/装配/编译器/parser/runtime投影回归通过，跨端总数3739。
前端产品源码未随枚举修复改变，沿用twentyfirst-l2中的类型检查和canonical证据。
独立复核确认适配未扩大通用值域。

`twentyfirst-orm-fixed.log`：通过现有`local.dev.test`、`sc-local-dev/sc_dev_demo`回滚管理
入口执行普通accounting_user用例，非零1项、0失败/0错误；断言非空原生默认命令、空_origin持久
身份、mainData命令保留与最终False条件。没有模块升级、fixture重建或服务候选切换。

## 第二十二增量：未保存明细的虚拟ID联动定位

候选基于`8ba805dcd3401ccdb5388b2de0d0e315b4d7f68d`，P0子表onchange身份与传输，P1
扩展已有普通会计ORM测试；P4仅同步既有命令类型守卫。
依据[Odoo17 RecordSnapshot.diff](https://github.com/odoo/odoo/blob/17.0/addons/web/models/models.py)，
新行可用NewId.ref返回CREATE/UPDATE/DELETE命令。此前请求把每个新行引用都发成0，不能稳定定位。

- 子表onchange create命令第二项携带稳定row.key，要求非空且唯一；正式write仍生成
  `[0,0,values]`，虚拟ID不作为数据库ID或原生条件持久ID。
- 回应UPDATE以字符串key精确定位新行；已知CREATE引用合并已有行，保留未改字段，不重复造行；
  新CREATE引用建立对应新行，后续同批UPDATE可定位。虚拟DELETE/UNLINK移除草稿，不发数据库
  删除命令。未知更新/删除、持久行key冲突、同批删除后复活和虚拟LINK/SET仍显式拒绝。
- 命令准备失败不修改当前行。两个显示名相同的新行按不同key定位，不按文本或位置猜测。
  本轮只扩展受控one2many inline路径，旧通用sanitizer未获得虚拟ID支持。

证据根`.runtime/product-user-gap-closeout-20261026/`：`twentysecond-l1.log`轻量迭代通过；
`twentysecond-l2.log`默认值55及新增runtime虚拟身份断言、实际formstate请求/响应定位用例、
onchange守卫和4项竞态通过，随后旧x2many守卫仅数字ID类型字面标记失败。P4同步为number|string
协议类型，未删除其他断言；`twentysecond-guards-fixed.log`x2many守卫、明细组件定向回归、
strict typecheck和contract basis通过。独立只读复核无新增S0–S2阻断。

真实ORM使用既有local.dev.test与会计测试类，检查两个同名原生新行的RecordSnapshot差异更新，
结果在本节最终条目记录。这不等于api_onchange handler全链路已贯通；其field_spec声明形状、
隐藏默认字段权威与真实页面验收仍是后续重点。无主线集成、部署、模块升级或demo重建；FG15未关闭。

最终ORM：`twentysecond-orm.log`记录2026-10-26 01:12 UTC在已登记的
`sc-local-dev/sc_dev_demo`执行普通会计用例，实际1项、0失败/0错误。原生快照只返回
指定虚拟ID的UPDATE，另一同名草稿不受影响，持久身份仍为空。使用既有回滚测试入口，
未升级模块、重建demo或切换服务候选；最终仅补证据记录，已通过检查的源码输入未变。

## 第二十三增量：原生联动失败显式返回与过期错误隔离

候选基于`4eae8ae22f18399219b5c4cc6b682a56cae74b9d`，仅P0后端错误边界与前端
错误消费、对应定向测试。原实现捕获原生onchange所有异常后继续手工补算，可能将失败包装为成功。
现分别返回权限403、业务校验400、内部执行500及返回格式500；权限/内部错误采用固定公开提示，
业务UserError保留原生业务信息。失败不进入手工补算、不生成成功data或v2补丁。
已知value/domain/modifiers_patch载体必须为字典，line_patches须为字典列表，warning须为
字典或字典列表；缺省及合法空容器仍兼容。此校验不等于深层字段语义完整校验。

前端实际formstate入口显示当前联动失败并保留草稿；请求序号、记录身份或草稿快照变化时丢弃
过期失败，防止污染当前页面。没有新增保存阻断状态机或自动重试，不宣称业务流程验收完成。

证据位于既有.runtime批次目录：`twentythird-l1.log`初检通过；`twentythird-l2.log`
保留首次失败：测试夹具recordId是只读computed，测试未能真正切换记录；改用ref后重跑。
独立复核S2发现dict包装的非法载体仍可能成功，已在补算前补形状校验和负例，复核确认关闭。
`twentythird-l2-fixed.log`后端10项（含10类非法返回子例）、协议schema、实际formstate
当前失败/记录切换/新草稿/新请求用例、4项联动竞态、严格类型检查及contract basis均通过。
最终轻量静态结果见`twentythird-l1-final.log`。

本轮为错误边界收口，不是fields_spec迁移。成功路径旧手工补算仍保留；下一步须由权威视图声明
建立原生字段规格，补隐藏默认字段并验证真实handler。无ORM算法/模型结构变更，本轮未运行
ORM或浏览器验收，未升级、部署、重建demo或集成主线。FG15仍未关闭。

## 第二十四增量：原生视图字段规格与单次onchange执行

候选基于`c3a9234feb68f1173323b4e67607e24030014fdc`。P0从当前用户get_view表单XML
生成原生fields_spec，替代旧注册方法字段名→字符串映射；依据
[Odoo17 onchange/RecordSnapshot](https://github.com/odoo/odoo/blob/17.0/addons/web/models/models.py)
与[get_view](https://github.com/odoo/odoo/blob/17.0/odoo/addons/base/models/ir_ui_view.py)。
前端传选中view_id，未指定时由原生默认视图选择机制解析。get_view之后只用sudo读取视图
model/type元数据校验归属，字段规格本身使用当前用户处理后的架构，不读取sudo业务记录。

隐藏字段保留；显式子表tree/list/form/kanban按comodel隔离并合并重复字段声明，逐模型与
字段验证read权限。已有记录绑定原始记录并检查read规则；changed字段必须存在于视图及请求
values。原生onchange只执行一次，移除旧手工补算与合并。没有改成自行执行模型方法。

独立复核S2：原生many2one显示对象不兼容既有ID提取/条件消费。修复采用后端公共传输适配，
根字段及x2many的0/1/4命令payload中将对象转为[id,label]，保持虚拟引用且不改输入；非法对象
明确报错。前端实际formstate用例确认非空关系ID及显示名称保留，复核关闭该S2。

证据仍位于既有.runtime批次目录。`twentyfourth-l2.log`保留首次轻量测试缺lxml的失败；
仅需XML遍历，改用标准库ElementTree，不新增环境依赖。`twentyfourth-l1-reviewed.log`通过；
`twentyfourth-l2-reviewed.log`后端14项、schema、实际formstate视图传输与关系值用例、4项
联动竞态、严格类型检查及contract basis通过。静态守卫同步原生规格变量名，断言未减少。

`twentyfourth-orm.log`初次真实清空关系通过，随后适配变更使其不再作为最终证据。
`twentyfourth-orm-reviewed.log`在sc-local-dev/sc_dev_demo通过既有local.dev.test执行，
普通会计身份、真实res.partner原生视图/handler：国家变化清空不匹配省份、省份变化选中非空
国家、已有记录联动不修改持久原值。实际1项、0失败/0错误，测试数据由既有事务回滚。

边界：原生LINK携带行数据仍会被前端拒绝；隐藏子列/默认值的完整声明消费、隐式子视图、
字段context/order、空changed_fields初始化和真实浏览器闭环仍需推进。此处只证明真实handler
与上述普通用户场景，不证明所有原生模型/菜单兼容。无模块升级、demo重建、服务候选切换、
部署或主线集成，FG15未关闭。下步优先收口LINK数据回放及隐藏子列声明消费。

## 第二十五增量：原生LINK行数据的受控回放

候选基于`17dbb342f6c23d694ac45b8a07e67c54d8deb006`。P0子表回放接受原生
`[4,persisted_id,base_data]`：base_data.id若出现必须与命令身份严格一致，其余字段必须有
现有列声明；未声明字段、非法身份/载体、删除后复活及新行key碰撞仍拒绝。原先纯ID LINK
行为保留，不扩虚拟LINK。没有放宽CREATE/UPDATE中伪造id的拒绝规则。

LINK数据仅补读取基线，不标记dirty或新增UPDATE；显式UPDATE另行处理。独立复核发现S2：
无条件hydrate会覆盖dirty字段并生成旧值写回，现按dirtyFields过滤，只补clean字段，保留
本地编辑或较早UPDATE。新增重复LINK、LINK→UPDATE、UPDATE→LINK、本地编辑→LINK回归。
已知行不重复创建。所有变化仍在副本上准备，后续命令错误时不部分提交；真实formstate也验证
根字段与子表共同准备失败时均保持原状。复核确认S2关闭，无新增阻断。

证据根沿用现有.runtime目录：`twentyfifth-l1.log`及`twentyfifth-l1-reviewed.log`通过；
`twentyfifth-l2-reviewed.log`默认值55及新增runtime断言、实际formstate联动、x2many守卫、
严格类型检查、contract basis通过。初始`twentyfifth-l2.log`保留，不能替代修复后的结果。
`twentyfifth-orm.log`在已登记sc-local-dev/sc_dev_demo通过local.dev.test执行普通会计
RecordSnapshot用例，实际1项、0失败/0错误；确认[4,id,{id,name}]返回且持久父子关系不变，
沿用事务回滚，不等同真实浏览器端到端证明。

本轮仍拒绝未声明的隐藏子列；未解决隐式子视图、字段context/order、空changed_fields初始化
或完整页面业务验收。无主线集成、部署、模块升级或demo重建，FG15保持未关闭。

## 第二十六增量：隐藏只读子列force_save声明消费

候选基于`18c0f4add760501c34817607d040e4b7f1615cf2`。检查发现原生tree解析器已保留
隐藏字段及原始occurrence.attributes，本轮不新增隐藏字段授权，也不接受未声明字段；具体缺口
为force_save声明未消费，以及已有行只读dirty字段此前未按原生写策略筛选。
依据[Odoo17 Record._getChanges](https://github.com/odoo/odoo/blob/17.0/addons/web/static/src/model/relational_model/record.js)，
P0消费静态force_save为可选forceSave；未声明保持原形状，非法显式值报契约缺口。write对新行
及已有行均只选可写或明确forceSave的dirty字段，抑制空UPDATE；onchange仍携带只读值。
隐藏、readonly、界面setter拒绝和后端权限不改变，force_save不是模型/字段写权限授权。

声明→消费→行为证据：原生解析器用例断言隐藏/readonly/force_save保留；前端从occurrence
构造列，实际子表runtime验证隐藏默认值写出、已有行服务端更新写出、显式false排除、onchange
保留只读值和手工编辑拒绝。一般form-only或默认值中未声明的子字段仍未接入，不能宣称隐藏
数据范围整体闭合。

`twentysixth-l2.log`保留首轮失败：缺省force_save时添加forceSave:false导致原有精确形状
断言失败，修复为缺省不添加属性，未修改断言。`twentysixth-l2-fixed.log`编译器8、跨端3739、
parser40、默认值55及新增runtime用例、明细组件定向测试/守卫、x2many守卫、严格类型检查与
contract basis均通过。`twentysixth-l1-final.log`记录最终轻量静态结果，独立复核无S0–S2。

本轮只改变前端声明消费和写命令筛选、增加后端解析回归；无后端产品/模型结构变化，未重复
运行ORM，无浏览器保存验收、模块升级、主线集成、部署或demo重建。FG15仍未关闭；下一步
处理inline tree外子字段的声明来源及草稿/写入传递，再验证实际页面保存。

## 第二十七增量：显式子表表单字段的数据链路

候选基于`b132b4e6391a3d202ea52e05fa45fb23b8de527d`。P0从已有子视图form.layout
的直接field声明补充数据字段集合，要求合法类型，保留字段属性、修饰与force_save；只遍历容器
children，不将field内嵌套关系的后代提升到当前行，不从全模型fields自行补字段。与tree重名时
保留tree口径，避免表单声明放宽现有行内字段行为。

列表显示列维持原集合，行内setter只允许该集合；数据字段用于default_get字段选择、已有行
读取/合并、初始化、onchange回放、条件类型、校验及write。表单专用字段的服务端默认/联动值
可按原生readonly/force_save规则写出；它们不会变成额外列表列或行内编辑入口。未声明字段
依旧拒绝。关系字段的选择器可用性不替代表单专用数据字段的声明写策略，后端ACL保持权威。

独立复核S2：初版遗漏祖先readonly/invisible。已携带所有容器约束，使用统一原生求值器处理
静态/动态条件；未编译的动态祖先原文明确拒绝。后续发现OR短路可隐藏非法祖先，修复为先
求值全部声明再合并，静态readonly/required也不跳过动态校验。复核确认两项关闭，无新增阻断。

最终证据：`twentyseventh-l1-final.log`轻量静态通过；`twentyseventh-l2-strict.log`
编译器8、跨端3739、parser41、默认值55及新增子表实际runtime用例、关系生命周期回归、
严格类型检查与contract basis通过。用例证明声明类型与scope、默认/回放/写入、显示集合不变、
禁止未渲染字段手工编辑、祖先条件动态切换和非法祖先显式失败。实际关系读取入口断言请求包含
form-only字段。保留初次通过日志与`twentyseventh-l2-reviewed.log`中的测试夹具失败：误读
validation.length，修正为既有validation.issues.length后重跑，未删除断言。

本轮无后端产品/模型结构变更，未重复ORM；未做浏览器保存验收、模块升级、部署、主线集成
或demo重建。隐式子视图、字段context/order及空changed_fields初始化仍未覆盖，FG15不关闭。
下一步验证受影响真实原生子表页面的新增、联动、保存链路。

## 第二十八增量：真实客户联系人子表草稿前置走查

P4复用既有workspace反馈浏览器入口、凭据和请求拦截器，增加固定res.partner/child_ids场景。
工具提交为96c087df1、6526274d2、ab0434899、b97639401；无P0产品源码改动。
首次独立复核发现空联动数组/固定等待可能误报，改为等待本次name输入、新建身份与changed_fields
对应的实际响应，校验HTTP及ok；新增行要求row-count精确+1，不再仅检查已有输入。保存和业务
dispatch继续被拦截；本入口不具有保存/清理测试记录的执行能力。

通过受管Make入口将本地sc-local-dev/sc_dev_demo与候选前端切至
`b976394010599e9a2e9cb7675809fb4de0de1d7e`，保留既有卷/数据库/凭据，无升级或数据重建。
namespace=ns_000000000002，入口http://127.0.0.1:18081/t/demo；候选前端5176。
健康检查验证后端源码挂载、SHA、dbfilter和filestore，浏览器进一步核对入口资源
`/assets/index-vC_g85dF.js`与候选dist-dev一致。此为本地验收候选更新，不是主线合并或日常
服务器正式发布；后续文档提交不改变已测产品树。

保留首次`twentyeighth-browser.log`及ab0434899报告：探针new URL把/t/demo丢掉，跳回
无namespace登录页，属于P4路由错误，不是产品失败。修复后
`twentyeighth-browser-namespace.log`和
`native-child-browser/b976394010599e9a2e9cb7675809fb4de0de1d7e/report.json`通过。
使用demo_full（uid40/company1），客户入口/a/891?menu_id=603：根字段联动HTTP200/ok=true，
添加联系人后child_ids从0行变1行，出现5个编辑输入，blocked=0/errors=0；before/after/final
截图已查看。静态及请求拦截策略测试见twentyeighth-preflight.log，各次语法检查日志保留。

结论限于真实客户页的一次根字段联动及新增子草稿出现；未验证新增子行字段联动、保存、落库
回读和清理。无业务记录写入，不能作为保存或全用户交付通过证据；FG15不关闭。
下一步通过现有受管fixture/浏览器通道绑定可回读、可清理的父子记录，完成保存验收。

## 第二十九增量：隐式关系子视图的onchange字段解析

P0 smart_core `core/native_onchange_spec.py`：x2many字段没有内联 tree/list/form/kanban
子视图时，原实现只返回空 spec，子行联动字段被静默丢弃。本增量改为经 comodel 默认表单视图
（`get_view(view_type="form")`，沿用当前用户权限）补齐子行字段；显式子视图保持优先，不触发
回退；自引用隐式子视图（如 res.partner.child_ids）用解析栈防无限递归；未知视图字段、读权限
拒绝维持 fail-closed。候选提交 `647075525`。

验证：L0 工作区 clean 身份；L1 `py_compile` 与 `make ci.local.iteration` 通过（L1_only，
无 receipt）；L2 非零边界套件 `test_api_onchange_record_id_boundaries` 19 项全过（14 项既有
+ 5 项新增：隐式解析、显式优先、自引用防递归、未知字段、读拒绝）。未做真实 Odoo 运行时
联动、前端/浏览器、模块升级、部署或主线集成。

结论：补齐“隐式子视图”这一动态语义缺口；字段 context/order、空 changed_fields 初始化、
富会计告警及 FG15 仍未闭合，继续按声明→消费→行为证据逐个增量推进，不提前宣告完整动态语义
或主线集成。

## 第三十增量：onchange 行补丁的关系值归一化

P0 smart_core `handlers/api_onchange.py`：onchange 的 `line_patches[].patch` 携带与顶层
`value` 相同的原生 many2one/x2many 传输对象，此前被原样透传，前端会收到不一致的格式。本增量
按关系 comodel 调用既有 `normalize_native_onchange_values`，统一为公共传输格式；子行关系对象
非法时 fail-closed 返回 `ONCHANGE_RESPONSE_INVALID`，并复用顶层归一化的异常边界。候选提交
`203ecdf8d`。

验证：L0 工作区 clean 身份；L1 `py_compile` 与 `make ci.local.iteration` 通过（L1_only，
无 receipt）；L2 非零边界套件 `test_api_onchange_record_id_boundaries` 21 项全过（19 项既有
+ 2 项新增：公共传输行补丁适配、非法关系拒绝）。未做真实 Odoo 运行时联动、前端/浏览器、
模块升级、部署或主线集成。

结论：补齐 onchange 子行行补丁的关系传输语义；字段 context/order、空 changed_fields
初始化、富会计告警及 FG15 仍未闭合，继续逐项增量。


## 原生子行初始化与动作专用表单身份收口（2026-10-26）

本轮代码候选 `1ab1254aa898b10ff9641f1c91df0cbf0550037e`，本地候选服务保持该版本。
归属 P0：smart_core 从已授权父视图解析子关系、字段和 inverse，携带父草稿调用原生 child onchange 初始化；
前端等待成功后追加行，父草稿、兄弟行或上下文变化时丢弃过期结果。不推断币种、不放宽字段/模型权限。
P4 仅扩展既有草稿探针的结果采集。当前单写者、既有工作树及 registered local.dev 环境复用。

- 原生 ORM 证据：普通会计角色下一项实际测试通过，journal 行遵循公司币种，invoice 行遵循父单币种；
  新草稿不持久化，已有父记录不被初始化修改。最初“journal 必继承父币种”的错误假设失败日志保留。
- 联系人回归揭示专用表单身份丢失。修复链为 PageAssembler `view_ids_by_type.form` → native marker
  `page.formViewId` → canonical source → V2 `sourceContext.formViewId` → 根/子 onchange。
  严格解码拒绝非法 ID，后端仍检查视图模型、类型和访问权限；同步契约 schema 与缓存版本/输入摘要。
- 三个中间候选未修全该链路，浏览器失败记录保留。尤其 source helper 测试不能代替完整 native projection 测试；
  已补 marker 到最终契约、source 到 marker、实际根请求优先于路由 ID 的回归断言。
- 最终联系人浏览器通过：视图1595，初始化HTTP200，0→1行，5个可编辑输入项，错误0/拦截0，截图已核。
- 最终凭证明细浏览器通过：视图790，初始化HTTP200，0→1行，8个输入项，原生返回 `[6,CNY]`，
  币种进入后续父 onchange 的同一虚拟新增行；错误0/拦截0。

验证索引：`.agent/runs/PRODUCT-USER-GAP-CLOSEOUT-20261026/run.json` 的 `native_child_init_closeout`。
原始日志统一位于 `.runtime/product-user-gap-closeout-20261026/`：`child-init-final-checks.log`、
`child-init-final-orm.log`、`form-marker-checks.log`、`form-marker-tests.log`（288项通过）、
`form-identity-frontend.log`（严格类型检查及身份断言）、`form-identity-final-guards2.log`、
`form-marker-contact.log`、`form-marker-journal.log`，两份浏览器报告目录均绑定上述候选 SHA。
独立只读复核无剩余 S0–S2；生成报告变更为受影响代码行数等派生量，已检查。

结论限定为子行初始化和这两个草稿场景通过。子初始化返回非空 warnings/modifiers/line patches 时仍显式拒绝，
并未声称完整消费；FG15 保存、借贷平衡、回读、过账及角色/公司边界仍待后续验收。
本轮未保存业务数据、重建 demo、合并主线或部署日常开发服务器。批次保持 active。
回滚应逆依赖撤销视图身份及子初始化提交，不恢复前端币种推断；证据与失败记录继续保留。

截图附带待核线索：凭证明细科目初始显示“暂无可选内容”，项目等显示“可选内容暂不可用”。本探针未搜索/选择科目，不能据此判断无数据或业务可录入；后续保存验收须先验证关系查询/选择链路，避免将初始化通过扩大为可保存。


## 科目选择诊断与关系域拒绝修复（2026-10-26，未完成办理收口）

代码候选及当前本地服务：`bdeaada403205f428486f1c0f703ba8a421b07ed`。
P4 在既有 journal-draft 探针中新增打开科目→实际 list 查询→点击选项→同虚拟行 onchange 的关联证据，
不允许保存或业务动作。探针自身 capture 限制及桌面/移动同名控件定位问题经独立复核、真实执行修复，失败日志保留。

中间候选 `cca43487e064f553fd23320ea4a7193e89c37d4e` 查到49个科目，选中49“601880 工程收入”，
onchange200；初始空提示并非缺少 demo 科目。但请求 domain=[]，不能据此接受业务筛选语义正确。
追踪发现 P0 `dynamicRelationDomainFromDescriptor` 将不支持的域直接退化为空数组，且其注释错误假定
comodel list 会重建来源字段的域；实际请求没有来源字段权威，不能作此假定。

本轮修复为查询前抛出 ContractGapError；根关系与子表共用此机制。已有明细测试在修改前已失败
（预期拒绝域而实际[]），已保留 `journal-domain-before.log`；现在要求明确异常，并增加真实 inline
query runtime 的零 fetch/list 反例。静态守卫也由名称存在检查改为拒绝路径检查，负例移除 throw 必失败。
这恢复的是拒绝机制，尚未新增复杂表达式求值能力。

验证：`journal-domain-final-tests.log` L1、明细矩阵/域、实际查询零传输、67项结算测试、10项后端测试、
46项守卫及严格类型检查通过；`journal-domain-root-tests.log` 根关系字段与40项守卫通过；独立复核无S0–S2。
`journal-domain-browser.log` **失败**：新行及币种仍通过，点击科目后不再发送丢弃域的查询，科目选择因此被阻断。
不得将此候选称为凭证可办理、保存通过或FG15关闭，也不得恢复无约束查询以获得绿灯。

已有原始契约证据 `caught-exceptions/report.json` responses19 的 account_id.domain 显示：
公司作用域 `company_id and ... or ...`、前缀 `|`、`parent_of`、列表拼接 `+`，再叠加
`deprecated=False` 与 `account_type != off_balance`。这是原生表达能力缺口，不能按会计模型写前端特判。
后续须核对当前权威描述符，补齐声明层原生关系域编译与消费/求值，绑定当前子行、父草稿、上下文，
验证公司和停用/类型过滤后再推进保存、平衡、回读与过账。

单一索引已更新；批次active，未做业务持久化、demo重建、远端集成或日常服务器部署。
回滚本轮拒绝修复会重新出现域丢失风险，不能作为关闭问题的方案；保留受管运行环境与全部失败证据。


## 原生关系域表达式接入及科目筛选恢复（2026-10-26）

产品代码/受管运行候选 `1958136964016db335d445a92e2d21d449bcc0d6`。P0 `smart_core` 编译，
前端仅消费显式数据表达式；P4 扩展既有 journal-draft 实际请求断言。当前工作树无外部执行者写入。

声明：原生字段字符串 domain 经 Python AST 白名单编译为 `fieldDescriptor.domain_expression`：
`version=1/raw/dependencies/tree`；未支持表达式为显式 unsupported。覆盖安全字面量、字段/parent字段、
list/tuple、返回操作数的 and/or、同类型序列拼接。List与Tuple保留类型，不接受Python本应拒绝的混合拼接。
无eval/任意调用/任意属性访问。新增compiler纳入 assembled cache输入，版本及摘要同步。
消费：严格绑定原始domain，校验AST、依赖及最终前缀域；normalized store保留声明。
当前行字段不借同名父字段兜底，显式parent字段按父描述符转换；缺少原始值在归一化为false/[]之前即拒绝。
512节点/32层资源限制登记在contract-basis机制豁免，不承载产品规则，不截断业务集合。

独立复核发现的两项S2（缺值归一化掩盖、parent类型来源）已修复，并补真实query runtime反例。
跨端共享fixture由后端测试核对编译结果，前端验证同一数据协议、raw不一致/非法节点/缺值/数组非法值/混合拼接拒绝。
实际查询测试证明子行公司7不会误用父公司1，显式parent.company_id才使用父描述符；缺少行公司不发第二次查询。

测试通过：`native-domain-final-back.log`135项后端；`native-domain-final-front.log`明细/域实际runtime与反例、
67项结算、10项后端附属及46项守卫、严格类型；`native-domain-semantic-tests.log`真实decode/store保持声明；
`native-domain-final-guards.log`L1/assembler缓存/探针语法/11项请求策略；`native-domain-root-tests.log`根关系及40项守卫。
早期类型检查失败、缓存摘要失败等原始日志保留，不算通过证据。

真实行为：`native-domain-browser.log` PASS，实际account.account查询包含完整域
`['|', ['company_id','=',false], ['company_id','parent_of',[1]], ['deprecated','=',false], ['account_type','!=','off_balance']]`。
返回49条，选择49“601880 工程收入”，ID进入同一虚拟新增行、onchange200；0→1行及币种6继续通过，
错误0/拦截0，截图已核。`native-domain-contact.log`联系人回归PASS，0→1行/5输入项，错误0/拦截0。
两份报告目录分别为 `journal-draft-browser/<candidate>/report.json` 与 `native-child-browser/<candidate>/report.json`，
均位于既有 `.runtime/product-user-gap-closeout-20261026/`；单一run索引已更新。

结论：上一轮科目复杂公司域阻断在该受限表达式范围内关闭；有数据且约束进入查询，不再靠丢域获取候选。
这不代表全部Python表达式已支持；函数调用、context.get、条件表达式/比较等仍显式拒绝，需按实际声明继续扩展。
仅证明demo_full的草稿/查询/选中链，未完成普通角色跨公司矩阵，也未保存、验证借贷平衡、回读或过账。
FG15整体保持开放。未合并主线或部署日常服务器；本地服务保留上述候选，后续记录提交不改变产品行为。
回滚195813696会恢复明确拒绝，不得恢复静默空域。

## 草稿保存实测、两项内核修复与恢复（2026-10-26）

本轮最后产品候选 `c0624c553232883baa8552fa49ca667f14326ef8`，本地服务与前端均绑定该候选。
沿用 sc-local-dev / sc_dev_demo / ns_000000000002 / sc_local_dev_odoo_data；未集成主线、部署日常服务器或重建demo。

- P4 `0167ec4aa` 增加单张唯一标记草稿的 UI 保存、刷新回读、精确清理探针；独立复核收紧 root/row/context/transport 白名单，禁止额外关系写入和禁用校验。策略23项、只读策略11项通过。后续 `f8e113ed9` 仅允许观察到的原生动作上下文精确值，显式日记账受限、默认日记账须回读核验。
- P0 `ea780d72a` 修复原生 notebook 只挂载当前页导致必填校验范围与引擎覆盖不一致。契约可见页保持挂载并绑定各自节点身份，复用原校验器；不删除校验失败保护。真实 TDesign panel/form 引擎87项、保存身份91项、strict、primitive、contract basis和容器守卫通过（journal-notebook-tests.log / journal-notebook-guards.log）。真实保存从“表单校验未能完成”推进到发出create请求，证明该阻断解除。`24af8b842` 的失败后内部状态诊断返回 unavailable，不算证据。
- P0 `c0624c553` 修复子行默认/联动回填 many2one 显示元组直接进入 ORM 外键。服务端 SQL 原始失败为 currency_id ARRAY[6,'CNY']；现在仅 write 按字段声明转换合法ID，保留展示/onchange元组，非法载体显式拒绝，无会计模型特判。新增真实子行runtime回归先复现后通过；create-default55及附加子行回归、strict、basis通过，独立复核无阻断。日志 journal-child-write-before.log / journal-child-write-tests-corrected.log。

**完整保存验收仍失败，FG15保持开放。** c0624c553真实create HTTP200生成草稿13，但刷新
ui.contract.v2返回409 `FEEDBACK_SOURCE_INVALID` / `layoutContract.feedback`，界面误呈“数据已发生变化”。
受管ORM权威回读另证实：界面借贷各100，保存后明细21/22的debit、credit、balance、amount_currency全部0。
不能以创建成功或借贷合计同为0宣布金额语义通过。后续应验证原生子行字段onchange/派生值及写入载体，不能前端硬算会计金额。

HTTP清理也返回403：产品未开放account.move unlink。未为测试放宽产品删除政策。
经独立复核新增P4 `local.dev.journal.recovery`，复用受管shell、写租约、数据库/命名空间身份；
只接受这次完整ref与id13、creator40/demo_full、公司1、日记账3、未过账draft及已核明细21/22。
以原创建用户检查ORM删除权限，不使用sudo；删除前保留金额证据，提交后验证父子不存在。
零金额应收行的reconciled计算值为true，但matched_debit_ids/matched_credit_ids均空，恢复按实际核销关系拒绝保护。
首轮环境绑定与该计算字段误判失败均保留；没有在不匹配时写入。

原始报告 `journal-save-browser/c0624c553232883baa8552fa49ca667f14326ef8/report.json` 保持FAIL与cleanup失败原貌，
恢复证据独立引用 journal-recovery-inspect-lines.log、journal-recovery-cleanup.log、journal-recovery-after.log，
单一run索引记录最终恢复状态。既有测试对象清理不等于HTTP删除/保存闭环通过。
在可复用清理路径和前置核验完善前，禁止再运行新的凭证创建验收。

本次两项阻断是功能/平台内核问题，不是demo缺少科目：有效科目仍有49条。测试草稿不纳入demo基线。
下一步从定向回滚ORM及前端runtime测试开始补齐子行金额联动、保存记录反馈源，再恢复保存回读验收；
过账、普通角色与跨公司矩阵仍未验证。回滚应按逆依赖撤销对应产品提交，保留失败证据，不恢复空域查询或放宽校验。


## 原生子行金额联动与已保存反馈读取（2026-10-26）

候选阶段：`f3812808bdb12b33c968c32d0dbea38eb1f0461b` 加本轮显式未提交范围；单writer、单run。
P0 `smart_core` 与通用前端消费者负责原生语义；P1仅复用会计权限测试载体，不添加会计公式或行业默认值。
沿用 sc-local-dev/sc_dev_demo/ns_000000000002/sc_local_dev_odoo_data，测试事务回滚；未新增持久凭证。

原生子行字段 onchange：传递父记录/原生视图、子字段集合、实际changed_fields和已有子行身份，
从当前用户父表单及子视图推导字段规格，验证已有子行确属该父记录。前端按行请求版本接收服务端派生值，
待返回及失败均阻止保存；立即登记dirty，累计未确认字段，防并发编辑丢失不同字段的联动。
父草稿/页面身份漂移显式阻断；已有行显示元数据不进入业务字段输入。没有前端借贷计算。
真实普通角色 rollback ORM 证实借贷各100经原生child onchange导出balance/amount_currency正负100，
实际保存合计仍为100/100；已有行联动120不隐式落库，错误父记录拒绝。
独立复核发现的scope漂移、已有行id混入、跨字段并发遗漏三项S2已修复并补用例。

已保存反馈：原校验器递归标量依赖，拒绝原生计算字段的关系/点路径/compute_sudo/无_depends。
新增路径从普通用户get_view实际XML证明host、首个内容节点、原始invisible及AST、顶层字段；
关系子视图不授予父字段权限，残留host/祖先/source groups拒绝。仅按当前记录ACL/rule/字段权限读取
提示直接需要的字段，使用原生ORM计算语义；不sudo业务记录，不重写计算方法。
逐plan隔离原生和自定义读取，自定义sc_feedback_usage仍走原严格校验，不能借同名字段绕过。
缓存版本与输入摘要同步。独立复核无已发现S1/S2。

证据均在原 `.runtime/product-user-gap-closeout-20261026/`：
- `native-child-change-backend-reviewed.log` 28项；`native-child-change-front-reviewed2.log` create-default55及实际行runtime、strict/basis通过；`native-child-change-loader-tests.log` 实际传输/显式拒绝及后端28通过。
- `native-child-change-handler-orm.log` 精确1项真实子行onchange/save/ownership回归通过。
- `saved-journal-feedback-before.log` 与 nodes日志保留真实409；`native-feedback-orm.log` 暴露测试请求缺客户端capability，修正测试后 `native-feedback-reviewed-orm.log` 普通会计角色保存记录契约成功，精确1项通过。
- `native-feedback-reviewed-unit.log` 30+154+48项通过，含来源伪造、其他alert内容借用、子视图、groups、跨公司/用户拒绝和混合来源；`native-feedback-final-guards.log` L1及assembler缓存守卫通过。

结论仅为上述两项修复的定向和rollback ORM验证通过，**FG15整体仍开放**。
本地浏览器服务仍是c0624c553，未将测试结果描述为新版本页面验收。
原生子行warning/modifier/line patches当前显式拒绝；完整groups表达能力、过账和角色公司矩阵未验收。
下一步先完善P4可复用的精确清理/preflight，解决HTTP unlink403条件下的自有测试草稿恢复，
再刷新干净候选并重验唯一凭证保存、刷新、金额权威回读、清理和独立不存在证明。禁止直接再创持久草稿。
无模块升级、demo重建、远端发布、主线集成或日常服务器部署；不声明完整基线/产品交付成立。
