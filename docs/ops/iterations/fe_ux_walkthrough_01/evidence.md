# FE-UX-WALKTHROUGH-01 用户问题证据库

所有问题服务版本：`96c860d0fb041c556b687afaad6dc689528785e5`；daily `/t/demo`，`sc_demo`。浏览器观察时间记录为 UTC，换算北京时间 +8 小时。

分类 P1–P7 是用户任务卡的体验分类；优先级 P0–P2 是影响等级；责任层 P0–P4 是仓库架构归属，三者不可混用。

原始证据：[页面/请求观察 JSON](../../../../.runtime/fe-ux-walkthrough-01/observations.json)、[结构化问题索引](../../../../.runtime/fe-ux-walkthrough-01/issues.json)、[会话结束记录](../../../../.runtime/fe-ux-walkthrough-01/session-summary.json)。每张截图的 URL、角色、时间、文字及请求事件可由同名 key 在 JSON 中找到。

## UX-01 · 项目经理首页风险详情进入失败页

**系统 / demo 归因：系统功能表现已证实；触发根因待定位。** 风险入口产生 500 是运行链路失败；不能据此排除某条 demo 风险数据触发异常。

**整改分流与核实：** 取得 action 673 的服务端异常与同角色运行契约，核对风险引用有效性；若为失效样本，修复 demo 来源，同时明确系统失效引用反馈。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P0 / P5 业务反馈 / P7 稳定性 |
| 角色 | demo_role_pm（pm） |
| 用户目标 | 跟进首页提示的“进度严重滞后风险升级”。 |
| 入口 | `/s/workspace.home`，详细目标见原始 URL |
| 实际表现 | 首页风险卡可见“看详情”，最终进入风险提醒工作台加载失败页；ui.contract.v2 action_open 周期观察到 HTTP 500。并非仅有短暂加载态。 |
| 预期表现 | 有权限时打开对应风险/获准风险工作台，保留对象上下文；无权限或入口未发布时，在入口处给出准确原因，不提供失败的办理承诺。 |
| 复现步骤 | 登录 → 首页“风险处置 · 进度严重滞后风险升级” → 看详情 → 等待场景加载完成。 |
| 证据 | [pm-01-home](../../../../.runtime/fe-ux-walkthrough-01/pm-01-home.png)、[pm-07-risk-ready](../../../../.runtime/fe-ux-walkthrough-01/pm-07-risk-ready.png) |
| 影响与范围 | 该风险跟进路径阻断。仅对 PM 实测成立；其他角色的同名卡不外推为同一结果。 |
| 初步责任 | 待定位：P1 风险入口/场景声明与 P0 场景、action_open 契约组装；非 CSS 结论。 |
| 替代操作 | 返回安全页面已可用，但本轮未找到同一风险的有效替代办理入口。 |
| 建议方向 | 定位 action 673 的服务端失败与入口发布/权限绑定，再使首页风险指向权威目标。 |
| 验证方式 | 同账号同风险完成卡片→目标对象→返回；无 500，目标可识别，失败原因可理解。 |
| 证据限度 | 行为已证实；未取得服务端异常栈，不断言具体后端根因。 |

## UX-02 · 项目摘要“查看合同”与授权导航脱节

**系统 / demo 归因：系统入口与权限契约一致性；非已证实 demo 数据错误。** 可见项目按钮指向导航不接受的目标；尚未证明当前用户应获该合同权限。

**整改分流与核实：** 核对 action 677 的发布绑定、实际合同授权与项目过滤；已有授权修正路由绑定，无授权则纠正按钮投影，不通过扩大权限解决。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P0 / P1 信息架构 / P6 数据与权限 |
| 角色 | demo_role_pm（pm） |
| 用户目标 | 在当前项目下核对摘要中显示的 4 份合同。 |
| 入口 | `/a/588?menu_id=382&search=%E4%B8%9C%E7%8E%AF%E8%B7%AF&order=sequence+asc,+name+asc,+id+asc`，详细目标见原始 URL |
| 实际表现 | 项目 1 的“查看合同”返回 action 677，最终进入 access-denied，reason=NAVIGATION_AUTHORITY_DENIED。菜单“日常合同”可打开 action 756，但它是 sc.general.contract 的 3 条公司合同，不是当前项目 construction.contract 的同一集合。 |
| 预期表现 | 摘要数字与点击目标一致；授权可达时保留当前项目范围，否则按钮说明不可用原因。 |
| 复现步骤 | 首页常用入口→项目台账→搜索东环路→打开项目→查看合同。随后返回安全页→日常合同，验证替代路径。 |
| 证据 | [pm-09-search](../../../../.runtime/fe-ux-walkthrough-01/pm-09-search.png)、[pm-11-project-ready](../../../../.runtime/fe-ux-walkthrough-01/pm-11-project-ready.png)、[pm-13-related-contract-read-action](../../../../.runtime/fe-ux-walkthrough-01/pm-13-related-contract-read-action.png)、[pm-14-contract-menu-alternative](../../../../.runtime/fe-ux-walkthrough-01/pm-14-contract-menu-alternative.png) |
| 影响与范围 | 项目→关联业务的连续工作被打断。拒绝机制本身不等于权限故障或越权；问题是页面暴露的操作与允许入口不一致。 |
| 初步责任 | P1 原生 project_overview_views.xml / contract_views.xml 入口，联查 P0 动作结果到导航权威的绑定。禁止前端豁免导航守卫或扩大角色权限。 |
| 替代操作 | 可另查一般合同，但不能当作当前项目合同的有效替代。 |
| 建议方向 | 统一项目摘要的合同对象类型、项目域、发布入口与用户权限；保持拒绝负例。 |
| 验证方式 | 同一项目合同数/列表范围可核对，返回项目保持身份；未授权角色依然拒绝，按钮不再误导。 |
| 证据限度 | 真实只读 act_window 导航证实。pm-12 是观察会话拦截造成的失败，已排除；有效证据为 pm-13。 |

## UX-03 · 管理层付款快捷入口长时间无终态

**系统 / demo 归因：待定位：系统场景/运行环境；无证据归咎 demo 数据。** 管理层付款入口持续加载至少 45 秒；单次观察不足以分离网络、后端耗时与前端未收敛。

**整改分流与核实：** 按该次请求时间关联服务端日志与场景生命周期；确认请求是否完成、失败是否被消费，再确定系统修复或环境整改。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P0 待定位 / P7 性能与稳定性 / P5 业务反馈 |
| 角色 | demo_role_executive（executive） |
| 用户目标 | 由首页进入付款申请审批，了解待关注的资金事项。 |
| 入口 | `/s/workspace.home`，详细目标见原始 URL |
| 实际表现 | 点击“付款申请 / 查看全部付款申请”进入 /s/finance.payment_requests，显式等待 45 秒后仍为“正在加载场景...”。未得到列表、权限说明或可重试错误态。 |
| 预期表现 | 在明确响应预算内给出内容或可恢复终态；如果该角色不具备该入口，首页应说明而不是无限等待。 |
| 复现步骤 | 登录 → 首页常用入口付款申请 → 等待；对照项目卡→项目详情能正常打开。 |
| 证据 | [exec-01-home](../../../../.runtime/fe-ux-walkthrough-01/exec-01-home.png)、[exec-03-project-ready](../../../../.runtime/fe-ux-walkthrough-01/exec-03-project-ready.png)、[exec-08-payment-shortcut](../../../../.runtime/fe-ux-walkthrough-01/exec-08-payment-shortcut.png)、[exec-10-payment-observed](../../../../.runtime/fe-ux-walkthrough-01/exec-10-payment-observed.png) |
| 影响与范围 | 这次审批入口访问不能完成。单次观察，不推定所有用户、所有场景都慢。 |
| 初步责任 | P0 场景启动/请求生命周期，联查 P1 场景发布与该角色表面；还须排除环境请求慢。 |
| 替代操作 | 本角色项目卡详情可用；本轮未验证同一审批集合的替代入口。 |
| 建议方向 | 沿真实请求与场景解析定位；加载必须可结束、可解释、可恢复，不以延长超时掩盖。 |
| 验证方式 | 同角色快捷入口在约定预算内产生正确终态；验证拒绝/慢请求负例，不能永远 loading。 |
| 证据限度 | 45 秒无终态为事实；根因未定。exec-payment-timing.json 是整个该浏览器上下文的资源记录，最大约 59.9 秒，不可冒称该场景的单接口耗时或 p95。 |

## UX-04 · 资金流水难以识别，来源回看语义与返回体验不清

**系统 / demo 归因：混合，必须拆开归因。** 17 条流水均叫“新建”是已见数据质量现象，历史种子或生成逻辑均可能；列表缺少关键识别字段、收款显示付款语义、返回 busy 是系统呈现/交互现象。

**整改分流与核实：** 先追踪现有流水来源与编号生成入参，不创建样本；比对原生视图→运行契约→列偏好→页面，核对收付款语义与返回生命周期。编号若仅存量错误归 demo 修复，若生成遗漏归模型修复；本轮不证明金额账实错误。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P1 / P3 列表体验 / P5 业务反馈 / P7 稳定性 |
| 角色 | demo_full（business_full） |
| 用户目标 | 识别一笔收入流水，核对来源、金额与业务完成状态，再返回台账。 |
| 入口 | `/a/775?product_domain=%E8%B4%A2%E5%8A%A1%E4%B8%AD%E5%BF%83&entry_intent=handling&disposition_policy=keep_list_form&integration_target=sc.treasury.ledger+%E8%B5%84%E9%87%91%E5%8F%B0%E8%B4%A6&entry_target_policy=keep_list_form&business_entry_contract_version=business_entry_disposition.v1&menu_id=367&action_id=775`，详细目标见原始 URL |
| 实际表现 | 台账共 17 条，流水号均为“新建”；当前可见列没有项目、方向、往来单位和申请单号，主要显示内部来源记录 ID。详情能找到来源 PRQ2600088，165 万金额和项目相符；来源为收款/已完成，却同时显示付款执行尚未生成、已付款 0、未付款 165 万。返回台账详情后“正在处理…”及禁用返回持续出现在 11:07:31–11:07:52 UTC 的观察中；活动页签最终可回列表。 |
| 预期表现 | 列表可按业务身份区分流水；收入与支出状态使用适用的语义，不能让“未付款”冒充收款未完成；只读回看后返回可用且保留上下文。 |
| 复现步骤 | 搜索菜单“资金”→资金台账→第一条“新建”（ledger/17）→打开申请（payment.request/91）→返回→观察按钮状态→切换资金台账活动页签。 |
| 证据 | [full-09-funds-ledger](../../../../.runtime/fe-ux-walkthrough-01/full-09-funds-ledger.png)、[full-10-ledger-detail](../../../../.runtime/fe-ux-walkthrough-01/full-10-ledger-detail.png)、[full-12-ledger-source-ready](../../../../.runtime/fe-ux-walkthrough-01/full-12-ledger-source-ready.png)、[full-13-return-observed](../../../../.runtime/fe-ux-walkthrough-01/full-13-return-observed.png)、[full-16-final-state](../../../../.runtime/fe-ux-walkthrough-01/full-16-final-state.png)、[full-18-tab-return-outcome](../../../../.runtime/fe-ux-walkthrough-01/full-18-tab-return-outcome.png) |
| 影响与范围 | 高频核账需要逐条进入详情；收/付款术语混用降低判断把握。本轮未证明实际账务金额错误。影响范围仅证实该全功能账号。 |
| 初步责任 | P1 treasury_ledger 编号/事实展示与 payment.request 收支语义，P0 契约投影、列表消费及返回状态；历史数据修复若需要归 P4，另行精确设计。 |
| 替代操作 | 逐条详情读取项目/申请单号，打开来源核对；活动页签最终能回列表。没有改列偏好或写流水。 |
| 建议方向 | 围绕“一笔流水核对”闭环，先查编号产生及契约可见列，再核对来源页语义与返回状态。 |
| 验证方式 | 真实流水号可区分；列表可识别项目、方向、对象和来源；收/支各一笔金额与状态闭合；来源往返不滞留 busy。 |
| 证据限度 | 显示与返回现象已证实；编号成因、字段隐藏层及慢返回原因待定位。列设置的 accessible name 为“列设置，已启用17列，共17列”，与最终可见表头还需对照契约，不能直接归因于用户隐藏列。 |

## UX-05 · 工作台缺少按角色的下一步引导，并暴露技术文案

**系统 / demo 归因：系统体验为主；待办数量属于数据条件。** 空待办可能真实；空状态缺少下一入口、原始状态英文和“首屏能力”技术说明是呈现问题。

**整改分流与核实：** 保留真实零值，消费权威可用入口提供下一步；不通过造待办掩盖空状态设计。管理层概览层级随真实任务验证。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P1 / P1 信息架构 / P5 业务反馈 |
| 角色 | PM、项目成员、管理层；技术文案亦见财务 |
| 用户目标 | 登录后知道现在该做什么；无待办时仍能开始工作。 |
| 入口 | `/my-work`，详细目标见原始 URL |
| 实际表现 | PM/成员我的工作明确为空，但仅有刷新/查找/排序，无去项目或计划的下一步。管理层首页主体仍是零待办和混合对象卡，经营概况需进入项目并滚动到关联业务页签。多角色显示“当前账号没有声明登录首屏能力区块”；风险状态有 escalated/claimed。 |
| 预期表现 | 空态说明范围并提供该角色已授权的下一步；经营角色优先看经营关注项；业务状态使用用户可理解的名称。 |
| 复现步骤 | 各角色登录→查看全部；管理层打开项目→经营概况；阅读首页底部及风险卡。 |
| 证据 | [pm-03-my-work-ready](../../../../.runtime/fe-ux-walkthrough-01/pm-03-my-work-ready.png)、[member-02-my-work](../../../../.runtime/fe-ux-walkthrough-01/member-02-my-work.png)、[exec-01-home](../../../../.runtime/fe-ux-walkthrough-01/exec-01-home.png)、[exec-04-operating-overview](../../../../.runtime/fe-ux-walkthrough-01/exec-04-operating-overview.png)、[finance-01-home](../../../../.runtime/fe-ux-walkthrough-01/finance-01-home.png) |
| 影响与范围 | 多个高频入口需要用户自己知道菜单词汇。空待办本身不构成缺陷，不要求造待办。 |
| 初步责任 | P1 角色工作入口与业务状态标签声明；P0 workspace/home 契约消费与通用空态。无证据支持直接重做 CSS 或新建组件体系。 |
| 替代操作 | 菜单搜索可定位项目台账/计划管理；项目详情经营页签可读。 |
| 建议方向 | 基于已有角色表面提供少量明确下一步，清除技术性的能力空声明文案，保留现有搜索和返回机制。 |
| 验证方式 | PM/成员空态能用一次明确操作进入获准项目/计划；管理层能解释经营信息入口；状态不露枚举代码。 |
| 证据限度 | 当前页面事实。此前财务接口“0待办”已被本轮浏览器 27 待办纠正，不再作问题依据。 |

## UX-06 · 退款工作台的前置步骤需要靠试操作理解

**系统 / demo 归因：系统流程说明/契约消费；暂无 demo 缺陷证据。** 选定现有项目后入口按条件出现，项目查找成功；主要障碍是上下文保存与正式退款两阶段关系不清。

**整改分流与核实：** 对比原生占位说明和运行字段契约，定位说明在声明、投影还是消费处丢失；业务保存与正式退款结果仍未覆盖。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P1 / P4 表单体验 / P5 业务反馈 |
| 角色 | demo_role_finance（finance） |
| 用户目标 | 选择退款类型并知道需要先准备、保存哪些信息。 |
| 入口 | `/f/sc.company.project.refund.workspace/new?menu_id=700&action_id=946&product_domain=%E8%B4%A2%E5%8A%A1%E4%B8%AD%E5%BF%83&entry_intent=handling&disposition_policy=keep_list_form&integration_target=sc.company.project.refund.workspace+%E5%85%AC%E5%8F%B8%26%E9%A1%B9%E7%9B%AE%E9%80%80%E6%AC%BE&entry_target_policy=keep_list_form&business_entry_contract_version=business_entry_disposition.v1&activity_page_id=ap_mvmah1ec_6wr4lg`，详细目标见原始 URL |
| 实际表现 | 菜单直接进入新建上下文，初始只见“记录办理上下文”，无退款类型按钮。搜索并选择项目后才显示扣款/投标保证金/合同保证金退回与关联台账，未保存时为禁用。初始正文没有说明“选项目→记录上下文→正式退款单”。原生 XML note 占位说明提到金额/账户在正式单填写，页面只显示通用“请输入办理说明”。 |
| 预期表现 | 清楚区分准备上下文与发起退款，说明为什么下一步不可用，并消费已声明的业务说明。 |
| 复现步骤 | 菜单搜索退款→公司&项目退款→搜索项目东环→选择→查看动作和未保存标识→返回→确认离开。 |
| 证据 | [finance-04-refund-ready](../../../../.runtime/fe-ux-walkthrough-01/finance-04-refund-ready.png)、[finance-07-project-search](../../../../.runtime/fe-ux-walkthrough-01/finance-07-project-search.png)、[finance-08-refund-context-selected](../../../../.runtime/fe-ux-walkthrough-01/finance-08-refund-context-selected.png)、[finance-09-refund-leave](../../../../.runtime/fe-ux-walkthrough-01/finance-09-refund-leave.png) |
| 影响与范围 | 财务初次使用需要试探。未保存状态及离开确认是已验证的优点；不宣称退款业务链不可完成。 |
| 初步责任 | P1 原生 company_project_refund_workspace_views.xml 与工作台语义；P0 字段占位、动作原因、反馈契约消费。 |
| 替代操作 | 选择项目后可发现下一阶段动作；本轮未保存上下文，正式退款未执行。 |
| 建议方向 | 先补齐/正确消费前置说明和禁用原因，不加新的退款弹窗或业务绕路。 |
| 验证方式 | 无需试填即可理解办理步骤；选项目后说明与动作同步；已修改与放弃确认保持有效。 |
| 证据限度 | 只观察未保存内存态，已确认丢弃；创建、保存、退款结果不在已通过范围内。 |

## UX-07 · 演示叙事与当前对象状态不够自洽

**系统 / demo 归因：demo 数据叙事与覆盖为主；不认定系统状态计算错误。** 名称“在建”与草稿状态、历史计划日期和 OdooBot 责任人均为实际字段；历史记录本身可合法。

**整改分流与核实：** 核对 seed/导入来源及样本用途，选择连贯角色案例，区分历史/当前；修正样本来源与重放规则，不靠前端改状态、不批量平移日期。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P1 / P6 数据与权限（数据侧） / P5 业务反馈 |
| 角色 | PM、项目成员、全功能；管理层亦读取历史项目 |
| 用户目标 | 根据项目名称、计划和责任人判断当前业务进展及谁负责。 |
| 入口 | `/a/588?menu_id=382`，详细目标见原始 URL |
| 实际表现 | 东环路项目名称注明“在建阶段”，列表和详情状态均为草稿；计划 1 的日期为 2025-04、实际开始为 2026-10-22，节点逾期 554 天，责任人为 OdooBot；采购申请同样为 2025 年业务日期、OdooBot 申请人。历史可以合法存在，但这些样本没有清楚区分历史展示与当前角色任务。 |
| 预期表现 | 演示案例明确历史/当前定位；阶段命名与权威状态不相互暗示矛盾，责任人能解释业务归属。 |
| 复现步骤 | PM 搜索东环路→查看项目状态；成员进入计划管理→计划1；全功能进入采购申请1。 |
| 证据 | [pm-08-project-list](../../../../.runtime/fe-ux-walkthrough-01/pm-08-project-list.png)、[pm-11-project-ready](../../../../.runtime/fe-ux-walkthrough-01/pm-11-project-ready.png)、[member-04-task-list](../../../../.runtime/fe-ux-walkthrough-01/member-04-task-list.png)、[member-06-plan-ready](../../../../.runtime/fe-ux-walkthrough-01/member-06-plan-ready.png)、[full-04-procurement-list](../../../../.runtime/fe-ux-walkthrough-01/full-04-procurement-list.png) |
| 影响与范围 | 用户难判断自己的下一步及指标是否代表现在；不等同于计算错误或权限漏洞。 |
| 初步责任 | Demo 数据载体/叙事规则与 P1 状态展示。一次性存量修复属 P4，需有来源与重放规则；本轮不直接改状态/日期。 |
| 替代操作 | 以结构化状态为准，结合审计记录；不能把历史样本假作当前待办。 |
| 建议方向 | 选定少量连贯演示案例，明确历史轨道和责任人；不要批量改日期制造新鲜感。 |
| 验证方式 | 主案例名称、状态、日期、责任及关联单据能讲清同一条业务故事。 |
| 证据限度 | 字段显示事实已证实；没有证明历史数据非法，也未验证全部 demo 数据。 |

## UX-08 · 查看页面的非关键限制信息抢占业务重点

**系统 / demo 归因：系统信息层级；非 demo 数据问题。** 未尝试删除即突出不可删除等限制，是通用详情展示顺序问题。

**整改分流与核实：** 随对应业务专题核对限制契约与展示优先级，保留真实限制；无需改业务数据。

| 项目 | 记录 |
| --- | --- |
| 优先级 / 类型 | P2 / P2 页面布局 / P5 业务反馈 |
| 角色 | 项目成员、全功能，管理层详情亦有重复信息层 |
| 用户目标 | 快速读懂计划或已确认采购、资金来源。 |
| 入口 | `/r/sc.plan/1?menu_id=521&action_id=738&product_domain=%E9%A1%B9%E7%9B%AE%E4%B8%AD%E5%BF%83&entry_intent=handling&disposition_policy=keep_list_form&integration_target=sc.plan+%E8%AE%A1%E5%88%92%E7%AE%A1%E7%90%86&entry_target_policy=keep_list_form&business_entry_contract_version=business_entry_disposition.v1`，详细目标见原始 URL |
| 实际表现 | 未尝试删除时，计划/采购/流水详情顶部先显示“不可删除”；多处重复标题、金额标签及技术追溯字段占据阅读空间。 |
| 预期表现 | 当前状态、责任与合法下一步优先，限制原因在用户需要时可发现；技术追溯信息放到合适层级。 |
| 复现步骤 | 打开计划1、采购申请1、台账17，观察首屏。 |
| 证据 | [member-06-plan-ready](../../../../.runtime/fe-ux-walkthrough-01/member-06-plan-ready.png)、[full-05-procurement-detail](../../../../.runtime/fe-ux-walkthrough-01/full-05-procurement-detail.png)、[full-10-ledger-detail](../../../../.runtime/fe-ux-walkthrough-01/full-10-ledger-detail.png) |
| 影响与范围 | 降低扫描效率，尚未单独阻断查询；不值得拆成多个样式修补任务。 |
| 初步责任 | 先核对 P1 原生视图与 P0 契约/通用页面反馈组合；不预设 CSS 为责任层。 |
| 替代操作 | 继续阅读下方业务字段，核心查询仍可完成。 |
| 建议方向 | 随所属旅程专题一起调整信息层级，保留真实操作限制。 |
| 验证方式 | 状态和下一步可在首屏辨识，限制仍可获取，不隐藏必要业务错误。 |
| 证据限度 | 截图观察，属于体验判断而非功能错误。 |

## 证据排除规则

- `pm-02`、`pm-04`、`pm-05-risk-settled`、`exec-02`、`finance-03`、`finance-12` 等仅为过渡态；结论采用后续 ready/settled 观察。
- `pm-12-related-contracts` 是观察会话阻止 execute_button 的结果，不能算产品错误。核对原生按钮为只读 act_window 后，pm-13 才取得实际导航拒绝。
- tooltip、活动页签、列设置的定位器超时不作为产品故障。列设置实际 accessible name 带已启用列数；没有修改工具去“修复”产品，也未把无弹窗观察定为缺陷。
- 付款详情加载期观察到一次 api.onchange HTTP 422，但随后页面成功；无错误体和业务影响证据，不计入阻断清单。台账返回期 HTTP 400 与 busy 同现，仅为待定位线索，不断言因果。
- 不把单次耗时当作稳定性能指标，不把日期久远直接判为业务非法；不把 UI 显示按钮当作后端授权通过。
- 未点击提交、审批、完成、生成询价单、保存、删除、确认付款。退款仅修改浏览器未保存状态，已通过确认离开丢弃；没有创建 team-loan-deduction 样本。

## 责任追踪参考（只读源码，不是完成诊断）

- P1 风险状态文本：`addons/smart_construction_core/core_extension_system_init_rows.py` 的 `build_risk_action_rows`；P0 风险入口归一：`addons/smart_core/core/workspace_home_contract_builder.py` 的 `_normalize_risk_action_row`。
- 项目合同入口：`addons/smart_construction_core/views/core/project_overview_views.xml` 的“查看合同”，指向 `contract_views.xml` 的 `action_construction_contract_my`。前端拒绝位置：`frontend/apps/web/src/router/index.ts` 的 `NAVIGATION_AUTHORITY_DENIED`。
- 首页消费：`frontend/apps/web/src/components/role-home/WorkspaceHome.vue`、`frontend/apps/web/src/composables/shared-surface/useWorkspaceHome.ts`。
- 退款前置说明：`addons/smart_construction_core/views/support/company_project_refund_workspace_views.xml`；对应模型 `models/support/company_project_refund_workspace.py`。
- 台账身份与来源：`addons/smart_construction_core/models/projection/treasury_ledger.py` 的 `create` / `action_open_payment_request`，视图 `views/projection/treasury_ledger_views.xml`。编号 `create` 对缺少 name 的路径值得定向核对，但未取得存量记录的创建入参，不把它写成已证实根因。
- 已核对上述产品目录从服务 SHA 至本地 HEAD 无源码差异。部署源版本一致仍不替代实际运行时契约/已安装 XML 的逐段核对。
