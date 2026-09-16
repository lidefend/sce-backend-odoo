# UC2 主线集成关闭与 U-C3 结构分组启动

状态：**UC2 主线集成完成，不等同于产品交付完成。** PR #482 已 squash 合入 `main@e802f7239bf005482a352caa64eb9da0e78a085a`。入库、出库批次验收完成，保留既有未覆盖项；本轮未报告部署，版本发布不登记完成；89 个入口的整体用户交付验收仍未完成。主线剩余兼容消费者 **44**，本地已验证剩余 **44**。

台账将原 `publishedCount=46` 改为 `mainlineRemainingCount=44`（显示名“主线剩余”），不保留含混的发布数别名。仓库执行代码未引用旧字段；历史 UC1 审计字段与原始证据保持原义，不据此宣称部署。已核对原审查候选 `25cb3cd106ead9dd09b3f2b68ed152fbd413da0f` 与合入提交的 addons/frontend/scripts 内容一致，546/547 原生结构退役产物已合入，44 项原条目未增删。

## 候选与边界

- 基线：`main@28b7695dc9f1cebbbe9bd5d715e951c6dec8a4da`。
- 产品与取证候选：`f1dbaa9950263f735b0619a08b545f8f199f5982`；完整指纹 `f9780e4b60fb625cdaa8b73a8cdb7a5217dd1069a989b64d4c5721e7290304da`。
- 分支／唯一写入工作树：`feature/uc2-material-native-v1` / `sce-backend-odoo-material-handling-v1-uc2-material-native-v1`。两个无关历史工作树未操作。
- P0：原生 statusbar 在新建态保留节点身份但不显示状态，避免同一状态回落到正文；章节导航显露 notebook 目标、定位并同步高亮。
- P1：`smart_construction_core` 材料入库／出库原生视图与分类契约。
- P4：受管只读浏览器矩阵、退库路径解析、证据和台账。
- 业务边界：库存、计价、保存、审批、状态方法、ACL 与 record rule 均未修改；供应商退货不在本批。

## 实际入口与覆盖

| 范围 | 正式身份与原生来源 | 已覆盖 | 结果／未覆盖 |
|---|---|---|---|
| 入库 | menu 494 / action 546 / `material.inbound` / view 1428 | `S80-MIN-001` received 查看、空白新建；桌面 1440×960、移动 390×844 | 通过；无合法 draft，未做编辑 |
| 出库 | menu 495 / action 547 / `material.outbound` / view 1431 | `S80-MOUT-001` issued 查看、空白新建；桌面、移动 | 通过；无合法 draft，未做编辑 |
| 退库（批外调查） | 内部 XML 定义 action 548 / `material.return` / 共用 view 1431 | 正式菜单、角色路由、action 547 分类、供应商退货边界 | **不在正式 89 项基线；无正式可达用户路径，另立业务能力专题；未把直接 action URL 当成验收路径** |

没有为补齐查看或编辑态创建、保存或修改业务数据。最终 8 个材料组合及非材料反例捕获到的业务写请求为 0，运行前后业务指纹一致。

## 唯一结构与兼容退出

action 546 与 547 的实际契约均满足：

- `layoutPolicy=container_tree_authority`；
- `formStructureAuthority=native_authority`；
- `compatibilityDependencies=[]`；
- action 546 解析到 view 1428，action 547 解析到 view 1431；
- 入库旧基础章节、生成字段顺序、P1 业务事实排序和 action 产品化结构按精确 XMLID 停用；
- 出库旧生成结构与 action 产品化结构按精确 XMLID 停用；
- 分类模板只保留 required、readonly、visible 等字段语义，不再提供章节结构。

因此入库、出库两个技术消费者已从剩余数组移除；合入后主线剩余 `46→44`，本地剩余 44。退库不重复计数，供应商退货不纳入本批。

## 信息组织、导航与交互

- 入库现有记录由页头唯一承接“已入库”：状态区 1、状态标签 1、正文状态字段 0。新建页状态区 0、正文状态字段 0，由页面的新建／未修改元信息表达当前模式。
- 入库 `document_status`、`quantity_summary`、`tax_included_amount` 的可见实例均为 0；`total_qty` 与 `amount_total` 各 1。明细继续保留逐行数量、单价、金额与原生合计，未改计算规则。
- 入库正文页签为“入库明细／说明与附件／来源追溯”；出库为“材料明细／说明与附件／来源追溯”。章节导航与 notebook 来自同一原生树。
- 从“来源追溯”点击顶部明细章节后，目标由不可见 0 变为可见 1，正确激活明细页签并定位关系锚点；活动导航为 `aria-current=location`。
- 新建态明细保留原生添加能力；已入库、已出库记录的明细为只读。新建备注探针跨三个页签保持，未触发保存。
- 入库保留提交、确认入库、退回草稿、取消、带入验收明细；出库保留提交、确认出库、退回草稿、取消和调拨关联动作。按钮继续由原方法、状态和权限控制。
- P0 非材料反例为人员档案：章节目标可见且唯一高亮，证明通用修复未绑定材料语义。

## 退库路径调查（UC2 范围外）

退库不属于 action 546、547 的本批正式范围，且当前不能宣称可用，依据如下：

1. 正式 89 项产品导航基线不含退库菜单。
2. `menu_sc_material_return` 的父菜单停用，管理员菜单搜索无“退库”。
3. 角色 route authority 列表为空。
4. action 547 的正式业务分类不包含 `material.return`；模型虽有 return 类型定义，但没有把普通出库入口变成正式退库入口的权威路由。
5. action 548 的 XML 定义或直接 URL 不能替代用户可达路径。
6. action 554“材料退货”对应 `sc.material.supplier.return`，属于供应商退货，明确排除。

后续另立业务能力专题：以可追溯原出库记录为起点，先核实来源关联、可退数量、库存方向和权限，再确定正式入口。该专题不直接放开出库分类，不复活旧菜单。执行者未擅自新增菜单，退库调查结论不阻断 UC2 正式范围冻结。

## 结果索引

| 层 | 入口／命令 | 状态 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | passed | 16 tests；最终 P0/P1 变更的静态与架构入口通过 |
| L1/P4 | XML parse、`node --check`、`python3 -m unittest scripts.verify.test_frontend_material_domain_rollout` | passed | 5 tests；浏览器断言按唯一状态区域取证 |
| L2/P0 | `make verify.frontend.professional_workflow.unit` | passed | 10 模型例、5 Python guards |
| L2/P0 | `make verify.frontend.canonical_form_presenter.unit` | passed | 170 cases；新建 statusbar 保留归属且不显示业务状态 |
| L2/P1 | `TestUserFeedbackBusinessViews.test_material_inbound_form_uses_handling_identity_and_business_first_line_order` | passed | 1 个精确方法，非零；0 failed/error |
| L2/P1 | 出库原生契约与无正式退库角色路径的精确方法 | passed | 既有候选结果复用；相关产品输入未变 |
| L3 | `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make local.dev.upgrade MODULE=smart_construction_core` | passed | `sc-local-dev` / `sc_dev_demo`；demo authority passed；未执行 `sync_demo` |
| L4 | 最终材料矩阵与非材料反例 | passed | 8 个材料组合、1 个非材料反例、25 张截图、0 写请求、0 浏览器错误 |

中间候选曾因两类取证问题失败：一是把新建 statusbar 节点身份清空，导致“草稿”回落正文；二是 Playwright 把组合徽标当作单一文本节点，`exact` 定位不到实际存在的“已入库”。前者由 P0 通用归属修复，后者由 P4 按唯一业务状态区域逐行取证；失败未被改写为通过。

`local.dev.sync_demo` 未执行。既有“期望 280000、实际 0”的结算演示数据问题继续单列，未修改金额或演示事实。action 777 保持原未通过状态。

## 浏览器证据与现场

- 证据摘要：`tmp/uc2/material-batch-f1dbaa99/browser-batch-review/summary.json`。
- 截图：同目录 25 张，摘要记录逐文件 SHA-256。
- 身份：HEAD `f1dbaa9950263f735b0619a08b545f8f199f5982`，完整指纹 `f9780e4b60fb625cdaa8b73a8cdb7a5217dd1069a989b64d4c5721e7290304da`。
- 滚动事实：桌面表单顶部 `formTop=101`、标题 `headingTop=133`；移动 `formTop=135`、标题 `headingTop=155`；实际滚动所有权为 `.router-host`，顶部截图时 `scrollTop=0`。
- 受管现场：`http://127.0.0.1:5176`。提交本记录后的仅文档候选可承接上述浏览器证据，因为产品、脚本、数据库、账号和运行配置输入未变；运行服务仍须绑定最终完整 HEAD。

原始浏览器证据保持不变。既有外部归档位于 `/home/lidefend/workspace/.codex-evidence/workspace-archives/20260916/uc2-material-native/25cb3cd106ead9dd09b3f2b68ed152fbd413da0f/`，引用 `archive-receipt.json`、`archive-verification.json`、`merge-receipt.json`；33 个文件与25张图的可读/哈希验证结论复用。Quick receipt 绑定原冻结候选，独立复核与四项 required checks 已通过；这些不是新规划候选的验证结果。本轮不重跑、不重建归档、不清理工作树、不重绑5176现场。

## UC2 四层状态与独立问题

| 层次 | 状态 |
|---|---|
| 批次验收 | 546/547 已完成；无合法既有草稿编辑样本，未新增保存及权限运行矩阵覆盖 |
| 主线集成 | PR #482 / e802f7239bf005482a352caa64eb9da0e78a085a 已完成 |
| 版本发布 | 本轮未报告部署，不登记完成 |
| 用户交付 | 正式89入口整体交付验收未完成 |

退库无正式可用能力，另立来源关联、可退数量、库存方向、权限评估专题；不直接放开出库分类，不复活旧菜单。action777保持原未通过；结算demo期望280000/实际0原因未定。三者不混入UC2完成结论。

## 剩余44项：按结构关系分组

仅使用既有 `form_structure_compatibility_consumers_v1.json.entries`，保留每项历史sourceHead与证据状态；未重新扫描89入口或数据库。以下view数字是原台账的运行ID，后续实施使用XMLID并重新核对所选组的实际契约。分类是排程依据，不证明旧路径已退出；sections为空也不能直接扣减。

共同旧路径为台账的 `legacy structure slots → frontend compatibility floorplan`。各组精确旧配置名已写入台账 `nextBatch.groups[].legacyConfigurations`。标为“机制族”的组不表示共用一张原生表单，实施仍按列出的子组隔离条件与权限。

| 组 | 入口清单（action） | 视图/继承与旧路径 | 必须保留；代表场景；风险 |
|---|---|---|---|
| G01 资料证照（首组，2） | 证书管理666、制度文件862 | 同model/view1703；根 `view_sc_document_admin_document_form`，源XML无inherit_id；两项action产品化覆盖 | fact_type条件、有效期、附件、来源、办理动作；两入口新建/查看，跨页签及权限否定例；中风险 |
| G02 发票（4） | 进项785、开票申请786、销项787、预缴788 | 同view1651；共享form_sections + P1业务事实 + 各action产品化覆盖 | 发票/税额/明细/红冲/来源和分类权限；每入口契约，进销项明细与预缴条件代表；高风险 |
| G03 收入（2） | 收款登记637、公司收入806 | 同view1644；共享sections/P1事实 + 两种产品化覆盖 | 合同、账户、抵扣与责任余额、明细；项目/公司各一例及公司边界；高风险 |
| G04 支出（2） | 实付837、公司支出808 | 同view1647；共享sections/P1事实/实付v2 + action覆盖 | 来源申请、付款账户、凭证、状态动作；申请驱动实付/公司费用两类；高风险 |
| G05 费用（3） | 报销792、公司项目扣款798、备用金793 | 同model，view1633/1632为两个根表单；扣款与备用金共view；生成覆盖和action覆盖 | 报销、扣款、备用金条件与责任余额、来源、账户；两根表单各一例及同view分类反例；高风险 |
| G06 抵扣（2） | 税额抵扣790、项目专项抵扣879 | 同view1654；共享sections/P1事实 + action覆盖 | 认证、税额、发票/预缴来源和明细；两个分类各核契约及条件；高风险 |
| G07 薪资（4） | 核算清单873、社保公积884、工资薪酬858；发放874 | 前三共view1697，发放为伴随view1700，不冒充同view；生成与action覆盖 | 人员/期间/薪资社保字段、发放记录、敏感权限；核算/社保条件+发放关联，不改算法；高风险 |
| G08 上下文工作台（3） | 班组借扣875、往来款877、公司项目退款878 | 独立view1932/1933/1934；同“办理上下文/说明”配置形状，非同model | 路由上下文、业务去向、帮助、各自操作权限；每入口上下文与动作核对；高风险 |
| G09 用量履约（3） | 劳务871、机械570、分包575 | view1461/1476/1491；劳务advisory继承劳务原生表单；共sections/P1事实机制，机械/分包另有action覆盖 | 用量/工期/合同清单/计价只读事实及来源；劳务继承帮助、机械数量、分包明细代表；高风险 |
| G10 工程过程（5） | 安全682、质量867；日志729；工程资料597、进度527 | view1741/1550/1893/1560/1389；处理表单、安全质量子组；日志三层覆盖；资料进度生成路径子组 | 责任/整改/验收结果、日志内容附件、进度数量；按三个子组取代表，状态和来源逐入口核对；中风险 |
| G11 轻表单/管理配置（6） | 消息860、岗位883、资产885；审批727、系统参数887、编码888 | 各自view1910/2070/1908/1887/2072/2074；无共享根，entry或generated机制族 | 消息只读/已读语义、岗位职责、资产归属；配置权限、审批条件、编号格式；前3中风险、后3高风险，分开验收 |
| G12 项目立项（1） | 724 | view1503项目专用创建；另有project.edit_project及多层继承，不能整model停用；project_project_form_structure_v1 | 创建身份、参建关系、合同工期、必填和来源；立项新建+非立项表单反例；高风险 |
| G13 日常合同/结算（2） | 合同687、结算876 | view1757/1764；结算共用UC1根，仍有daily_contract_settlement action覆盖 | 合同分类、结算来源/明细/动作；日常合同与结算各一例，UC1结算结构不退化；高风险 |
| G14 汇总与保证金（4） | 成本归集523、盈亏522、资金汇总646；保证金778 | 独立view1379/1377/1669/1540；均generated路径，汇总只读与保证金办理分子组 | 只读聚合口径、钻取来源；保证金合同与状态动作；汇总一例/保证金一例，禁止改计算；高风险 |
| G15 税务申报（1） | 880 | 独立view1659，tax_filing_form_v1 | 申报期间、税额测算、来源治理和权限；只读测算+合法新建代表；高风险 |

同一resolved view只说明共用候选。发票、薪资等根表单的有效继承组合还需实施时按所选组核对，未从历史ID推断运行继承已验证。劳务advisory继承和项目继承扇出来自本次有限源码核查。以上15组共44项，无重复、无漏项；不把额外状态消费者886重复计入。

## U-C3 首组执行范围

选择 G01：666证书管理与862制度文件，同一model、同一原生form，同一说明/附件页签、状态动作与来源字段，可一次迁移共享结构，并分别保留fact_type条件。无需新增库存、金额或业务计算规则。相比财税/薪资大组，跨模型关系较少；权限差异明确，风险可通过既有授权正反例控制。

- 正式action：`action_sc_certificate_registration` / `action_sc_product_policy_document_v1`。保留前者certificate_registration与后者policy_document的domain/default；政策列表使用 `view_sc_policy_document_tree`，不误换成通用列表。
- 原生来源：`addons/smart_construction_core/views/core/document_admin_document_views.xml` 的 `view_sc_document_admin_document_form`。只迁移必要章节、字段顺序、来源追溯和说明/附件布局。原生当前“历史来源”组为空，旧配置含四个legacy来源字段，实施必须补齐，不能停配置后丢失来源。证照配置中的project_id及制度名称label/分类readonly同样逐项保留。
- 退出目标：`business_config_contract_document_admin_certificate_productized_form_v1`、`business_config_contract_policy_document_form_v1` 的sections、结构字段sequence/group_title与entry_semantic_surface重组；保留fact_authority、fact_type_authority、标题/帮助和字段语义。模型级 `business_config_contract_sc_document_admin_document_form_structure_generated` 是需核查的潜在重叠路径，不能仅因本台账未命中便全局关闭。
- 同model的公司存档、借阅不扩为新增正式入口；若调整共享根或模型级覆盖影响它们，补有限结构反例以避免退化，不复活菜单、不计入本批扣减。
- 权限：证照action允许business_initiator/business_config_admin；制度action仅business_config_admin。模型ACL允许发起人读写创建而非删除，配置管理员拥有删除权限；保留action与模型两层约束、公司/记录规则和附件可见性。密级字段不是新增授权机制，本批不得自行设计密级权限。
- 原有提交、完成、取消、重置草稿及日期一致性规则保持不变；不通过直接调用动作完成浏览器取证。

代表验收：两个正式菜单各查实际契约，新建+可用现有记录；桌面以证照新建/制度查看、移动以制度新建/证照查看覆盖共用布局与不同条件。核对隐藏组不能导航、页签切换保留未保存说明、附件与来源可读；分别检验发起人证照权限和制度入口不可达。已有合法草稿才补编辑，无样本就记录，零保存现场不冒充保存能力验收。两入口都需最终无结构覆盖/无兼容依赖和浏览器证据后才能从44扣减，预计最多44→42；当前保持44。

按整组连续实施与定向验证 → 一次集中浏览器复核 → 冻结并走PR主线集成门禁。普通缺陷在批次内修复；新增业务规则、权限扩张、库存/金额口径变化才升级讨论。

## 本轮执行与承接

- 分支：`feature/uc3-native-structure-grouping`，基线 `e802f7239bf005482a352caa64eb9da0e78a085a`；主工作目录承接UC3文档准备，UC2 linked worktree与5176现场原样保留，两个历史工作树未动。
- Formal Product Layer=P4；Layer Target=兼容消费者台账与批次排程；Module=docs/ops/iterations；Standard vs User-Specific=工程记录。Why Here=主线集成状态与规划不属于业务模型；Why Not Elsewhere=不改P0机制、P1规则或P2/P3偏好；Blast Radius=本台账及本记录。
- 后续实施归P1 `smart_construction_core` 原生视图和精确配置退役，已有P0通用机制复用；本轮未实施U-C3产品改动。
- L0：起始完整指纹 `db4d78613db67a3ddd895b70937e5ab080fa9f411bd68e4ba1a6affb9f038230`。L1：`make ci.local.iteration` 通过（16 tests，仅静态门禁、不产生候选receipt）；JSON解析、44项分组集合一致性、UC2合入内容比对、文档diff检查均通过。本轮低风险文档变更，L2/L3/L4不运行（未变产品、脚本和运行输入），L5/Quick不运行（用户明确要求，尚非冻结集成候选）。UC2历史通过结果只证明原候选，不冒称本分支新门禁。
- 回滚范围仅本台账与记录改动；原证据和运行态均未变。下一步直接按G01整组实施，复用已登记local.dev及模块测试入口，不新增环境、fixture或治理专题。
