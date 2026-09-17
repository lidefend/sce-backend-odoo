# U-C4 G04 实付与公司支出原生结构迁移与低代码兼容

- 批次：`U-C4` 表单结构消费稳定化 · 代表面 `G04 实付与公司支出`
- 分支：`feature/uc4-payment-execution-native-v1`（基于 `origin/main`=`1cf2a151cb6ac19fe45d2050b875f9b39163ad05`）
- 唯一写入者：本会话执行体；除本候选外的 3 个历史保留工作树本轮未触碰（`git worktree list` 当前 4 个，含本候选）
- 状态：**批次验收待冻结门禁｜未集成｜未部署｜89 入口交付未完成**；台账（`form_structure_compatibility_consumers_v1.json`）保持 **36**，扣减留待合入后核对

## 1. 范围与身份

| 项 | 值 |
|---|---|
| 正式入口 | `action 837` 实付登记 / menu 339（财务中心）、`action 808` 公司财务支出 / menu 547 |
| 旁路入口 | `action 811` 往来单位付款 / menu 561：`view_ids=[(tree,2057),(form,1647)]`，表单同样是 **1647** |
| 模型 | `sc.payment.execution` |
| 原生根表单 | `view 1647` = `smart_construction_core.view_sc_payment_execution_form`（原 arch 无继承视图） |
| 台账登记配置 | `sc_payment_execution_form_sections_v1`(144)、`sc_payment_execution_p1_form_business_facts_v1`(6)、`payment_execution_productized_form_v2`(208)、`payment_execution_actual_outflow_productized_form_v1`(241)、`payment_execution_company_finance_expense_productized_form_v1`(242)、`payment_execution_partner_payment_productized_form_v1`(243) |
| 实施中发现 | `payment_execution_form_structure_generated_v1`(100) 已是 `active=False`，无需再退役 |

样本：8 条 `sc.payment.execution`（本轮只读核对：id 1/154 为 `confirmed`，91/92/93 为 `draft`，155/156/157 为 `paid`）。

职责分层（本批实施）：

| 层 | 目标 | 说明 |
|---|---|---|
| Formal Product Layer | P0 平台机制 + P1 声明 | 结构消费属 P0；入口声明属 P1 |
| Layer Target | `smart_construction_core` 原生视图 + 发布配置退役 | 不改 `smart_core` 机制代码 |
| Standard vs User-Specific | 行业标准默认 | 实付登记属标准业务入口 |
| Why Here | 原生 arch 是结构权威；发布配置只保留入口标题与稀疏注解 | |
| Why Not Elsewhere | 不把结构写进共享层 sections（那正是本批要退役的重复投影） | |
| Blast Radius | `sc.payment.execution` 的 837/808/811 三个入口 + 6 个既有配置记录；列表/API/字段存储不动 | 由 L1/L2/L3/L4 分别证明 |

## 2. 实际改动

1. `views/core/payment_execution_views.xml`：9 个业务组加 `name` + `data-sc-anchor`（`payment_main`/`payment_basis`/`payment_amount`/`payment_note`/`receipt_account`/`payment_account`/`payment_attachment`/`payment_responsibility`/`payment_source_trace`）；
   - 删除「办理类型」组内重复的 `<field name="state" readonly="1"/>`（`state` 原在 header statusbar 与组内各出现一次），statusbar 成为唯一状态呈现；
   - `来源与系统追溯` 补回退役 P1 层声明、原生未承载的独立审计事实 `creator_name`/`created_time`（`readonly="1"`）；
   - **保留** 3 个无标题包装 `group`（仅排布列，非业务章节，未加 anchor、未加标题）。
2. `data/payment_execution_actual_outflow_form_productization_contract.xml`：整体重写（211→93 行），241/242/243 三个入口声明改为 `{'title': …, 'composition_mode': 'native_semantic_surface'}`，删除 `sections/fields/columns`，保留 id/action_id/priority。
3. `data/payment_request_form_productization_contract.xml`：208 改为 `native_semantic_surface`，**保留 `semantic_anchors`**（4 组角色注解），删除 `sections/fields/columns`。
4. `data/view_orchestration_form_section_contract_data.xml`：144 置 `active=False` ＋注释（`contract_json` 未改，可回读/回滚）。
5. `data/p1_daily_business_form_orchestration_contract_data.xml`：6 置 `active=False` ＋注释。
6. `tests/test_payment_execution_native_lowcode.py`（新增 336 行 / 7 测，`@tagged("post_install","-at_install","uc4_native_lowcode")`）+ `tests/__init__.py` 注册。
7. `scripts/verify/local_dev_form_lowcode_scope.py`：新增只读代表路由 `payment_execution`（3 个身份：837/menu339、808/menu547、811/menu561，视图均为 1647），登记 `TOPIC_SAMPLE_FIELDS["payment_execution"]=["state","source_kind","payment_family"]` 与 `TOPIC_REPRESENTATIVE={"section_navigation":True,"record_surface":True}`；复用既有环境与身份校验，不新建 fixture/环境。

回滚路径：144/6 只置 `active=False`，`contract_json` 原样保留 → 回播置回 `active=True` 即恢复；208/241/242/243 的 `sections/fields/columns` 未行内保留，回滚方式为 **`git revert` 对应提交**（`b4bf7df0`/`1116c1ad`）。

## 3. 机制审查结论（先审查，再决定登记范围）

| 规则 | 结论 |
|---|---|
| P0 只消费明确的通用语义，不按模型名/字段后缀猜副本 | 未新增任何按模型名/后缀推断的副本；`*_display` 全部按显式消费者处理（见下） |
| P1 声明确有依据的来源关系；同源但承担独立职责的字段不自动删除 | 退役 P1 层(6) 共 27 条声明，其中 4 条原生已承载（`kingdee_document_no`/`receipt_account_name`/`payment_account_no`/`note`），**23 条原生未承载**。23 条构成为（本轮只读核对模型元数据，非推断）：**10 个 `payment_execution_*_display`（`store=False` 非存储展示投影，唯一消费者即被退役的配置 6）** + **6 个 `partner_payment_*_display`/`company_finance_note_display`（`store=True` 计算显示，另有列表消费者）** + **6 个 `store=True` 计算快照**（`company_finance_push_result`/`partner_payment_project_name`/`partner_payment_actual_payee_unit`/`partner_payment_source_text`/`partner_payment_voucher_no`/`partner_payment_writer`） + **1 个独立审计事实 `created_time`（`store=True`、无 compute）**。三类均不因退役而删除字段：展示/快照保留其列表与 API 职责，只补正文一次、不入正文第二次；`created_time` 已补入 `payment_source_trace`。**另一独立审计事实 `creator_name`（`store=True`、无 compute）不在层 6 的 27 条声明内，是本批新增补入的原生载体**（依据：层 6 声明的投影 `payment_execution_source_created_by_display` 的 canonical 事实链 `…_display` ← `partner_payment_source_created_by` ← `creator_name`），不能表述为「退役 P1 层声明」 |
| 展示副本协议 | `sc.payment.execution` **未继承** `sc.formal.display.copy.sources`，`FORMAL_DISPLAY_COPY_SOURCES` 中也没有该模型条目 → **不登记副本**（与 G03 同题），不猜测、不新建协议 |
| 同一事实允许在列表/正文/审计各有表达 | 附件原件（`attachment_ids`，正文「附件」章节）与附件文本摘要（808 列表 `company_finance_attachment_text`、811 列表 `partner_payment_attachment_text`）分别服务不同场景：摘要只在**对应入口的列表列**出现，正文只由原件承载，不重复 |
| 列表消费者不得因退役而断供 | `company_finance_*_display` 仍在 `views/support/user_confirmed_formal_list_views.xml`、`user_confirmed_formal_list_alignment_views.xml`；`partner_payment_*_display` 仍在 `user_confirmed_formal_list_views.xml` 与 tree 2057；tree 2065 用 `company_finance_*` 快照。退役的 `payment_execution_*_display`（`store=False`）**唯一消费者就是被退役的配置 6**，故不入正文、也不删字段 |
| 原生结构权威不能单独证明动作已有承载位置 | «查看责任余额» 按钮保留原 `invisible="not company_contractor_responsibility_summary_id"`，header 5 按钮与各自 `invisible`/`groups` 条件逐条保留；本批未改任何可见条件 |

契约层实测（安装后只读重放 `ui_contract_v2` `op=model`、`render_profile=create`）：三入口 `formStructureAuthority=native_authority`、`configuredSections=[]`、`compatibilityDependencies=[]`、`formPresentationMode=task`、`resolvedViewId=1647`，导航标题分别为「实付登记」「公司财务支出」「往来单位付款」；最终树**形状一致**——各 **67 个容器节点 / 46 个字段节点**、字段集合相同、无重复（含 header statusbar 的 `state` 一次），`fieldSemanticRoles` 各 14 项且三入口相同（位于 `formStructureContract.sourceAuthority.governance_source.fieldSemanticRoles`）。**但三入口 `layoutContract.containerTree` 并非逐字节相同**（上一版记录的该断言不成立，本次实测更正）：按节点键（`containerId`/`name`+`type`）匹配并比较**节点自身属性**（不含 `children` 传播）的口径，837↔808 有 48 个节点不同、808↔811 有 2 个、837↔811 有 48 个（= 38 个字段级属性节点 + 10 个组 `widgetList` 差异节点；808↔811 为 1+1）；若按位置逐条比较并把子节点差异传播到父容器则为 52/4/52。差异全部落在字段级属性与组 `widgetList`（`fieldInfo`/`componentConfig`/`required` 档位，如 `business_category_id`/`payment_request_id`/`partner_id`/`paid_amount`/`receipt_account_*`/`payment_account_*` 在 837 create 为 `required=false`、在 808/811 create 为 `required=true`），与结构形状无关，属各入口 action context 与业务分类策略。可复算证据：`artifacts/uc4-representative/g04-contract-tree-diff/`（只读重放脚本 + 原始输出 + 口径说明，本轮新增留档，便于第三方按同口径复算）。`sourceAuthority.governance_source.businessConfigContracts` 分别解析为 837=[208,241]、808=[208,242]、811=[208,243]。

## 4. 验证矩阵

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS（16 tests + 全部守卫；`change_state=dirty coverage=L1_only`；8 路径未映射→按规则改跑选定 L2） |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestPaymentExecutionNativeLowcode'` | **7 tests / 0 failed / 0 error**（`l2-payment-execution.log`） |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` + `local.dev.verify_authority` | PASS（78 modules；`demo.authority` PASS；`l3-upgrade.log`） |
| L4 | `FORM_LOWCODE_TOPIC=payment_execution FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | EXIT=0，`ok=true`、`restored=true`、`browser_errors=[]`、`cleanup_guard=proceed`、`recovery_state.released=true`、业务指纹未变（`run-payment_execution.log`；报告 `artifacts/lowcode-form-loop/browser/representative-report-payment_execution.json`） |

L2 首轮失败与处置（透明记录，两次缺陷均在**测试自身**，非产品缺陷；输入已变更，非无变化重跑）：
1. 用 `reversal_reason` 作「隐藏→发布→回滚」对象失败——该字段原生 `invisible="state not in ('paid','cancel')"` 本就成立，断言前提错误 → 改用原生无 `invisible` 的 `planned_amount`；
2. `TypeError: unhashable type: 'dict'`（对 dict 取 set）→ 改为按契约名遍历，并断言 `formStructureContract.navigation.title` 等于各入口标题。
复跑：`0 failed, 0 error(s) of 7 tests`。

L2 行为断言（非实现字符串）：三入口声明为 `native_semantic_surface` 且无 `sections/fields`；144/6 均 `active=False`；三入口 `native_authority`、`configuredSections=[]`、无重复节点；`state` 单次出现；`creator_name/created_time` 在 `payment_source_trace` 且 `readonly`；空标题包装组不带 anchor/标题；3 个入口的 action/domain/view_ids 不变；作用域低代码 **预览→发布→回滚**（`planned_amount` 隐藏→发布后仍隐藏→回滚后恢复可见，且同表单另一入口契约逐项不变、业务记录 `write_date/state` 不变）。

## 5. 代表面浏览器结果（只读）

| 入口 | 路由 | 结果 |
|---|---|---|
| 837 实付登记 | create | **passed**：9 个章节入口全部 resolve 且可见（含 `公司-承包人资金责任`）；`duplicated=[]`、`empty_containers=[]`、无标题包装组不带标题/分隔线；渲染节点 32；吸顶 1088/390 各 10 组测量，操作行↔导航↔正文 **0 重叠** |
| 837 实付登记 | record（样本 id=1，readonly） | **passed**：导航栏渲染 8 个按钮（含 1 个横向滚动控件），其中 7 个 `data-section-target` **章节入口全部 resolve 且可见**；相比 create 少 `付款账户` 与 `公司-承包人资金责任` 两个章节入口；渲染节点 17；吸顶 18 组测量 0 重叠。契约层只读重放（`render_profile=readonly`、`record_id=1`）中该两组在 `statusContract.containerStatus` 仍为 `visible=true`、其字段 `invisible=false` → 差异位于渲染层，本批未归因，记为观察项（既非隐藏策略，也非定位失败） |
| 808 公司财务支出 | create | **passed**：8 个章节入口全部 resolve 可见；渲染节点 27；吸顶 18 组测量 0 重叠 |
| 811 往来单位付款 | create | **拒绝访问**：`NAVIGATION_AUTHORITY_DENIED`（交付导航权威不含该入口的治理身份），非结构结果 |

「808 create 少 5 个事实、少 1 个章节」的归因（**不是**修剪误删）：

1. **事实（浏览器 DOM，本轮实测）**：808 create 渲染 27 个字段，比 837 create 的 32 个**少且仅少** 5 个 `company_contractor_*`（`…_responsibility_state`/`…_arrival_unprocessed_amount`/`…_arrival_over_processed_amount`/`…_self_funding_balance`/`…_responsibility_notice`），随之为空的 `公司-承包人资金责任` 章节不再出现；**导航与正文一致、无孤儿入口、无空容器**。
2. **声明层（只读核对）**：`sc.business.category`（P1 行业标准产品数据）20 `finance.payment.execution.company` 与 16 `finance.payment.execution.partner` 的 `form_policy_json` 对这 5 个字段（以及 `payment_family`/`source_kind`/`push_result`/`kingdee_document_no`/`active`）声明 `visible_profiles=["readonly"]`，并对它们声明 `readonly_profiles` 覆盖全部档位。
3. **入口差异（只读核对）**：action 837 的 context 不带业务分类默认值；808 带 `default_business_category_code=finance.payment.execution.company`，811 带 `…partner`。
4. **结构层（只读重放）**：三入口解析同一原生视图 1647，容器形状与字段集合一致、无重复（见 §3）→ 该差异**不来自**本轮退役配置，也**不来自**结构消费层。
5. **未复现部分（如实记录）**：本次经 `op=model` 重放**未复现** create 档位对这 5 个字段的 `visible=false`（容器节点 `invisible=false`；`statusContract.containerStatus` 中对应组 `payment_responsibility` 为 `visible=true`——该标志位于 `statusContract.containerStatus` 的 `{containerId, visible, disabled, reasonCode}` 行，不在树节点本身）；该可见性在入口/应用配置装配路径生效。本批只登记声明层证据与浏览器实测结果，**不把契约层 `visible=false` 记为已复现结论**。
6. 该章节的«查看责任余额»按钮在无责任余额时本就合法隐藏（`invisible="not company_contractor_responsibility_summary_id"`，本批未改任何可见条件）。

传输证据（单独记录，不判为产品缺陷，也不声称零错误）：本报告 `diagnostics.failed_requests` 含 40 条 `net::ERR_NETWORK_CHANGED`（Vite 模块请求，`stage=post_navigation_mount`，`classification=environment_transport`，`renavigate_once` 后 `recovered=true`）；`console` 仅 1 条 Vue Router `history.state` 警告与若干 Vue 属性继承/组件解析警告。以上不计入结构结论。

## 6. 剩余缺口

1. 811（往来单位付款）的浏览器结构结果：交付导航权威对治理身份拒绝访问；需具备相应授权角色的受管身份才能补测（新建身份属独立 P4 授权，本批不做）。契约层已证明其表单与 837/808 同源（同一原生视图 1647，容器形状一致：67 节点 / 46 字段、无重复）。
2. 808/811 create 档位的业务分类可见性策略（`visible_profiles=["readonly"]`）是 P1 数据声明；本批只做归因与记录，**未修改**该策略（改与不改属业务决策，不在本批范围）。
3. 前端「契约字段 → 渲染节点」逐字段归因（G03 同题，仍为观察项）。
4. 传输中断（`ERR_NETWORK_CHANGED`）为环境事件；本轮已由 runner 的 `renavigate_once` 恢复并记录，未据此改写任何产品结论。
5. 837 record（readonly）导航比 create 少 `付款账户` 与 `公司-承包人资金责任` 两个章节入口；契约层该两组仍 `visible=true`，差异位于渲染层，本批只记录未归因（§5）。
6. 808/811 create 档位对 5 个 `company_contractor_*` 事实的隐藏，本批已核对声明层（业务分类 `form_policy_json`）与入口差异，但未通过 `op=model` 复现契约层 `visible=false`（§5）。

## 7. 未执行项（保持未执行）

`local.dev.sync_demo`、`local.dev.snapshot`、fixture reset、历史数据修复、无关模块 upgrade、发布快照、历史容器停启、Docker 网络调整、工作树清理、复核草稿清理、`make pr.push`（本批收口阶段另行决定）。
非本轮草稿（163/190/192/194/233/267/274/276）全部保留未消费；本批写入仅限 `sc.payment.execution` 的视图/配置退役与新增文件。

## 8. 主线集成与台账扣减（合入后记录）

- 冻结候选：head `3c4346bf28b93490ba117ae0a26f917e609d59cc`、tree `709b601ca05b213e819db5dbe8b99684de7680cd`；
  完整 tracked+untracked 指纹 `dfc169622c4bd443d49912a7dd05f9d41ac303c97409e712e909cc1c386b04e5`（7507 路径，`artifacts/fingerprints/uc4-g04-frozen.json`）；
  `make ci.local.quick` 回执 `.git/codex/evidence/ci.local.quick/3c4346bf28b93490ba117ae0a26f917e609d59cc.json`（日志 `artifacts/uc4-representative/quick-g04-r2.log`）；
  `make ci.delivery.freeze.prepare` PASS（冻结前生成证据无未提交改动）。
  身份沿革：上一身份 `0e88d252…`（Quick PASS）被纯文档更正提交 `3c4346bf` 取代；产品代码未变，页面证据按规则沿用不受影响。
- 记录更正（本次）：独立复核 REQUEST_CHANGES 仅涉及 4 处记录陈述（工作树计数、"逐字节相同"断言、23 字段构成、837 record 章节数），
  已按只读重放结果更正并撤回不成立断言，另补记回滚路径；未改产品代码。
- 台账扣减：**36 → 34**（退役 action 837/808 与视图 1647）；旁路 action 811 不计数、如实登记在 `bypassConsumers`；`nextBatch.selectedGroup` 前进到 **G05**（报销/扣款/备用金 792/798/793，视图 1632/1633）。
- 台账（`docs/ops/iterations/form_structure_compatibility_consumers_v1.json`）现状说明：**合入前仍为迁移前快照**——837/808 条目仍写着
  `layoutPolicy=business_config_sections`、`formStructureAuthority=entry_semantic_surface` 并列出 144/241/242/243 等旧配置
  （该快照绑定更早的 head）。合入提交须一并落实：条目重新快照为 `native_authority` + 退役配置、`count` 由 36 扣减为 34、
  旁路 811 登记进 `bypassConsumers`、新增 `uc4G04PublishedAudit`、`nextBatch.selectedGroup=G05`、`sourceMainlineHead` 更新为合入后主线 head。
  在扣减落地前，本记录的 36 应理解为**尚未扣减的台账值**，不得当作本轮已生效计数。
