# U-C4 G05 报销、扣款、备用金原生结构迁移与低代码兼容

- 批次：`U-C4` 表单结构消费稳定化 · 代表面 `G05 报销、扣款、备用金`
- 分支：`feature/uc4-expense-claim-native-v1`（基于 `origin/main`=`8e8c1ce9d4d0fbe63b141cf75475030282f9f9d9`）
- 唯一写入者：本会话执行体；本候选之外的其它工作树本轮未触碰
- 状态：**批次验收中（未冻结）｜未集成｜未部署｜89 入口交付未完成**；台账（`form_structure_compatibility_consumers_v1.json`）保持 **34**，扣减留待合入后核对

## 1. 范围与身份

| 项 | 值 |
|---|---|
| 正式入口 | `action 792` 报销申请 / menu 578、`action 798` 扣款登记 / menu 563、`action 793` 备用金 / menu 575 |
| 旁路入口 | menu 543（费用与保证金）→ 同一 `action 792`，按台账「非消费者」登记，不计数 |
| 模型 | `sc.expense.claim`（三入口同模型） |
| 原生表单视图 | 792 → `view 1633` `view_sc_expense_claim_form`；798、793 → `view 1632` `view_sc_expense_claim_deduction_registration_form` |
| 台账登记配置 | `expense_claim_reimbursement_request_productized_form_v1`(217)、`expense_claim_deduction_bill_productized_form_v1`(222)、`sc_expense_claim_form_structure_generated_v1`(72) |
| 本批新增登记 | `expense_claim_advance_fund_productized_form_v1`（备用金入口级发布，见 §5） |

三类入口的 action 级权限本批**未改动**：792＝业务发起/财务只读/财务经办/财务审批，798＝前述＋项目审批/项目经办，
793＝财务只读（唯一 action 级组）。模型 ACL、菜单 groups、action domain／context 全部保持原样。

职责分层（本批实施）：

| 层 | 目标 | 说明 |
|---|---|---|
| Formal Product Layer | P0 平台机制 + P1 入口声明 + P4 验证工具 | 结构消费属 P0，入口声明属 P1 |
| Layer Target | `smart_construction_core` 原生视图 + 入口级发布配置 | 不改 `smart_core` 机制代码 |
| Standard vs User-Specific | 行业标准默认 | 报销/扣款/备用金属标准业务入口 |
| Why Here | 原生 arch 是结构权威；入口发布只保留标题 | |
| Why Not Elsewhere | 不把结构写进共享层 sections，也不删除模型级配置（另有消费者） | |
| Blast Radius | `sc.expense.claim` 的 792/798/793 三个入口 + 同模型另外 15 份入口级契约（不改造，仅验不被误伤） | |

## 2. 实际改动

1. `views/core/expense_claim_views.xml`（77+/26-）：两个共享表单加 10／9 个 `data-sc-anchor` 业务章节锚点；
  按退役配置反推的原生缺失字段全部补回（1633 补 9 个，1632 补 24 个），无任何配置声明字段仍缺失；
  头部 6 个按钮保持不变，`action_view_company_contractor_responsibility_summary` 保持为章节内载体（非 header）。
   **第三轮回环新增 3 行改动**（见 §11）：`paid_amount`／`payment_state` 由条件只读收紧为 `readonly="1"`，
   `company_name_text` 补 `readonly="1"`。
2. `data/expense_claim_form_productization_contract.xml`（85 变更行）：
   - 217（报销申请）、222（扣款登记）`contract_json` 改为 `{'title': …, 'composition_mode': 'native_semantic_surface'}`，
     删除 `sections/fields/columns`（配置侧结构副本）；其余 14 份入口级契约未改。
   - **新增** `business_config_contract_expense_claim_advance_fund_productized_form_v1`（action 793，`title=备用金`，
     `native_semantic_surface`，无 sections/fields/columns）。模型级 `sc_expense_claim_form_structure_generated_v1`(72)
     **保留原样**（`active=True`、`action_id` 为空），继续服务其其它消费者。
3. `tests/test_expense_claim_native_lowcode.py`（新增 604 行 / 9 测）+ `tests/__init__.py` 注册。
   独立复核指出的可移植性缺陷已修：三入口与兄弟入口的视图改用 xmlid（`view_sc_expense_claim_form` /
   `view_sc_expense_claim_deduction_registration_form`）寻址，不再硬编码库内 id 1633／1632——副本库或
   clean/tenant 库里同一视图的 id 不同，硬编码会让本测试在那些库上失败。
4. `frontend/apps/web/scripts/native_section_navigation_test.ts`（161+/1-）：共享机制用例（空容器不吞按钮/关系/投放目标、
   父级仅剩隐藏子节点不产生导航项、正文与导航同源）。
5. `frontend/apps/web/scripts/formal_form_representative_journey.mjs`（+20）、`formal_form_lowcode_loop.mjs`（+8）、
   `scripts/verify/local_dev_form_lowcode_scope.py`（35+/1-）：代表面「未覆盖」显式登记（见 §6）。

回滚路径：217/222 与新增的 793 契约只要 `active=False`（或 `git revert`）即回到迁移前；
模型级 72 未被修改，`git revert` 本批提交即可整体回退。原生补字段与锚点的回滚同样是 `git revert`（纯展示层，无数据迁移）。

### 2.1 文件归属（接管前已有 / 接管后修改 / 仅验证）

| # | 路径 | 归属 | 改动 | 层 |
|---|---|---|---|---|
| 1 | `addons/smart_construction_core/views/core/expense_claim_views.xml` | 接管前已有 | **接管后修改**（锚点＋补字段） | P1 |
| 2 | `addons/smart_construction_core/data/expense_claim_form_productization_contract.xml` | 接管前已有 | **接管后修改**（217/222 去结构 + 新增 793 入口声明） | P1 |
| 3 | `addons/smart_construction_core/tests/test_expense_claim_native_lowcode.py` | — | **本批新增**（604 行 / 9 测） | P4 |
| 4 | `addons/smart_construction_core/tests/__init__.py` | 接管前已有 | **接管后修改**（注册测试模块） | P4 |
| 5 | `frontend/apps/web/scripts/native_section_navigation_test.ts` | 接管前已有 | **接管后修改**（机制用例） | P0（机制由测试锁定，未改 `smart_core` 源码） |
| 6 | `frontend/apps/web/scripts/formal_form_representative_journey.mjs` | 接管前已有 | **接管后修改**（未覆盖登记） | P4 |
| 7 | `frontend/apps/web/scripts/formal_form_lowcode_loop.mjs` | 接管前已有 | **接管后修改**（未覆盖/BLOCKED 打印） | P4 |
| 8 | `scripts/verify/local_dev_form_lowcode_scope.py` | 接管前已有 | **接管后修改**（topic＋样本可用性事实） | P4 |
| 9 | `docs/ops/iterations/uc4_expense_claim_native_lowcode_20260918.md` | — | **本批新增**（本记录） | 记录 |
| 10 | `docs/ops/iterations/form_structure_consumption_stabilization_20260917.md` | 接管前已有 | **接管后修改**（总记录 §8.23） | 记录 |
| 11 | `docs/engineering_convergence/complexity_budget_report.md` | 接管前已有 | **接管后修改**（既有生成入口刷新，4382→4383，非手改摘要） | P4（生成物） |

合计 **11 个路径**（与候选提交 `git show --stat` 一致）；恢复前 baseline（`8e8c1ce9`）上不存在本批私有文件。

**仅验证、未修改**（不得计入本批改动）：

- `addons/smart_core/**`：本批**未改**共享机制代码；793 的入口声明是配置层（`ui.business.config.contract`）声明，不是机制改动。
- `docs/ops/iterations/form_structure_compatibility_consumers_v1.json`：**未改**（保持 34）。
- 临时只读诊断脚本（`frontend/apps/web/g05_*.local.mjs`，6 个）：已全部删除，不进入提交。
- 未消费草稿：163/190/192/194/233/267/274/276 等历史草稿本轮**未读改写**、未删除。

## 3. 机制审查结论（先审查，再决定登记范围）

| 规则 | 结论 |
|---|---|
| P0 只消费明确的通用语义 | 未新增任何按模型名或字段后缀推断的副本；`*_display` 均按显式消费者处理 |
| P1 声明确有依据的来源关系 | 217/222 去结构依据是原生 arch 已承载全部声明事实（逐字段核对）；793 新增入口声明依据是「同模型同视图的另外两个入口均以入口级声明消费同一原生树」 |
| 同源但承担独立职责的字段不自动删除 | 模型级 72 未被删除（另有消费者）；`sourceSectionTitles` 等既有行为仅登记不改造 |
| 同一事实在列表/正文/审计各有表达 | 原生补字段只在正文一次；列表列不动 |
| 原生结构权威不能单独证明动作已有承载位置 | 793 一度「原生权威成立但页面空」——本批结论是**结构消费缺失**，不是动作缺承载：action 可达、壳与操作行正常渲染（见 §5） |
| 禁止同一上下文无意义重复 | L4 `findings.duplicated=[]`（三入口），`empty_containers=[]`、`decorated/titled_layout_groups=[]` |

## 4. 分层验证结果（实际执行）

| 层 | 入口 | stage identity（HEAD ＋ dirty 范围） | 结果（含日志／证据路径） |
|---|---|---|---|
| L1 | `make ci.local.iteration` | `b2b12365` ＋ dirty `{views/core/expense_claim_views.xml, tests/test_expense_claim_native_lowcode.py}`（第三轮） | **PASS**：16 tests OK；`change_state=dirty coverage=L1_only receipt=none`（L1 不入交付证据） |
| L1/L2（前端机制） | `make verify.frontend.native_section_navigation.unit` | 同上（第三轮补跑） | **PASS**：`authority=7 next_action=3 content_identity=11 active_tracking=7 structure_consumption=7` |
| L2（前端类型） | `make verify.frontend.typecheck.strict` | 同上（第三轮补跑，因第二轮改过 `native_section_navigation_test.ts`，其输入已变） | **PASS**（`vue-tsc --noEmit -p tsconfig.strict.json` 无输出、退出 0） |
| L2（后端） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestExpenseClaimNativeLowcode'` | 同上（第三轮） | **PASS**：`0 failed, 0 error(s) of 9 tests` |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` | 同上（第三轮）；运行身份 `project=sc-local-dev db=sc_dev_demo` | **PASS**：78 modules loaded（58254 queries）＋ `local.dev.demo.authority` PASS（`finance_xmlid=present finance_membership=authoritative company_currency=CNY sale_tax_9=present`） |
| L4 | `make local.dev.form_lowcode.browser FORM_LOWCODE_TOPIC=expense_claim FORM_LOWCODE_REPRESENTATIVE=1` | 同上（第三轮重跑：原生 arch 已变，页面证据按依赖作废后重取） | **PASS**：三入口 create 通过，**3 项**登记事实未覆盖（§6 表 3 行）。证据：`artifacts/lowcode-form-loop/browser/representative-report-expense_claim.json`（sha256 `c04bc2c1769524f894277d9786611695f0362c9a344bffb62898dbacafa5573c`）＋ 三张 `representative-expense_claim-{792,798,793}-create.png` |

stage identity 口径：本批仍处**批次验收中（未冻结）**，按「日迭代＝HEAD＋显式 dirty 范围」记录，不写 full fingerprint、不称 frozen；
交付阶段的干净 HEAD ＋ 完整指纹在冻结步骤单独生成（§9）。第一轮（`ba3f5da7` ＋ 首轮全量 dirty）的 L1／L2 前端／L2 类型回执
已被第二轮的 TS 测试改动与第三轮的 arch 改动取代，不再引用。

L2 覆盖的 9 个用例：入口契约单一原生结构、legacy 章节被抑制且登记 `compatibility_dependencies`、
兄弟契约保持自身结构、声明事实恰好渲染一次、readonly 规则、锚点/包装组/条件章节、o2m 明细独立承载、
页签归属、scoped preview→publish→rollback（业务指纹不变）。

## 5. L4 归因：793 备用金曾渲染空结构（根因＋修复＋验证）

**观察（修复前，只读复现）**：`.native-form-tree[data-state="empty"]`、`fields=0`、`nav=0`、`containers=0`，
而同一页面的表单壳、操作行（新建/尚未修改/返回/保存草稿/提交审批/更多操作）、协作日志均正常渲染。
同一会话内 792（36 字段）与 798（29 字段）READY，793 稳定 NOT_READY（重试 2 次一致）。

**归因链（每步均为实测，非推断）**：

1. 后端 `api.data` 对 793 返回 `layoutContract.containerTree` **79 节点**（header 1、button 7、field 57、sheet 1、
   group 10、notebook 1、page 2）→ 结构数据并非缺失。
2. 同一响应里 `formStructureContract.sourceAuthority.governance_source.formStructureAuthority`
   **792/798 = `native_authority`，793 = 空字符串** → 793 没有入口级发布，解析落到模型级
   `sc_expense_claim_form_structure_generated_v1`(72，`layoutPolicy=native_authority`，带 5 slots／29 fieldRoles)。
3. 前端 `contractFormPresenter.ts` 的 `structureAuthority: structure?.layoutPolicy === 'container_tree_authority' ? 'containerTree' : 'compatibility'`
   → 793 走 **compatibility 平面**；该平面在 create 模式经 `createReadyNode` 修剪「可见且只读且无值」的字段，
   793 又在只读能力入口上 → 整个正文被修剪为空，只剩壳。

**修复（P1 入口声明，本批范围内）**：为 action 793 新增入口级发布 `expense_claim_advance_fund_productized_form_v1`
（`备用金`、`native_semantic_surface`），与同模型的 792/798 一致；模型级 72 保持不动。

**修复后实测**：793 编译契约 = `native_authority` / `container_tree_authority` / `slots=0` / `fieldRoles=0` /
`title=备用金` / 树 79 节点；浏览器 create 路由 **35 字段、8 章节、8/8 导航 resolved+visible、无吸顶重叠**
（`actions 175–205` vs `nav 218–257`）。792/798 结果不变。

**未顺手改的相邻机制（候选，未登记为缺陷）**：compatibility 平面在 create 模式下可能把整个 primary zone 修剪空，
且不产生 fail-closed 状态或提示；本批只按受影响入口修复声明，未改共享修剪规则（影响面覆盖全部 compatibility 入口，
超出本批边界）。

## 6. P4 工具与「未覆盖」事实

只读代表路由 `expense_claim`（3 身份）登记在 `scripts/verify/local_dev_form_lowcode_scope.py`，
复用既有受管环境与身份校验，未新建 fixture 或环境。

本批新增的最小诊断能力（P4）：

1. scope 探测为每个身份输出 `sample_state`（`available` / `record_rule_denied` / `empty_action_domain`，
   含 `domain_rows`、`readable_samples`）与 `business_row_count`；
2. 代表面 journey 对「已登记但无法运行」的事实生成 `representative_uncovered` 记录（不再静默少一条路线）；
3. loop 打印 `UNCOVERED` / `BLOCKED` 行，使覆盖率缺口在运行输出中可见。

**本批实测未覆盖事实**（`representative-report-expense_claim.json`）：

| 入口 | 事实 | 状态 | domain_rows | 可读业务行 |
|---|---|---|---|---|
| 792 | `record_surface` | `record_rule_denied` | 1 | 0 |
| 798 | `record_surface` | `empty_action_domain` | 0 | 0 |
| 793 | `record_surface` | `empty_action_domain` | 0 | 0 |

含义：793/798 域内无数据（数据事实）；792 域内有 1 条记录但受管身份读不到（**记录规则事实**）。
因此本主题「业务指纹前后一致」这条护栏在当前身份下是以 **0 行可读业务数据**计算的，护栏强度有限，
不能表述为「已证明业务数据未被改动」；本批改动本身只读，不存在业务写入路径。

792 的记录规则事实指向批外候选 `sc.expense.claim` 的 ir.rule 组交并被合并为 `&`（非扣款组用户读域归零）。
该机制面**不属本批**，本批只登记、不修改（候选问题，未登记为缺陷）。

## 7. 代表面结果（L4 明细）

| 入口 | 路由 | 字段 | 章节 | `findings` | 导航 | 吸顶（1088） |
|---|---|---|---|---|---|---|
| 792 报销申请 | create | 36 | 8 | 全空 | 8/8 resolved+visible | `actions 175–205` / `nav 218–257` 分离 |
| 798 扣款登记 | create | 29 | 8 | 全空 | 8/8 resolved+visible | 分离（同上） |
| 793 备用金 | create | 35 | 8 | 全空 | 8/8 resolved+visible | 分离（同上） |

`browser_errors=[]`、`representative_blocked=[]`、`cleanup_guard.decision=proceed`、`recovery_state.released=true`、`restored=true`。
吸顶分离在 1088 与 390 两个视口均为 **13px**（1088：`actions 175–205` / `nav 218–257`；390：`actions 251–281` / `nav 294–347`），
每个章节跳转后的 `target.top` 都大于 `nav.bottom`（无重叠）。

**传输口径（第三轮实况，不得改写成零错误）**：本轮 **观察到 1 次传输中断**——
`transport_recoveries=[{stage: post_navigation_mount, classification: environment_transport, aborted_module_requests: 4,
recovery_attempt: renavigate_once, recovered: true}]`，4 个被中断的请求全部是 Vite dev 模块
（`/src/components/professional-fields/*.vue`），错误 `net::ERR_NETWORK_CHANGED`；同一记录也出现在
`diagnostics.failed_requests`（4 条）。按既有口径：这是 **Vite dev 模块传输中断**，不是接口故障，
也不是「已恢复」的判据——恰好 recover 成功只说明本次重导航后页面可用，不证明网络故障已消失。
同一运行内 `diagnostics.intents` 的 5 条 `ui.contract.v2` 全部 `status=200, ok=true`（1327–3078ms），
说明被中断的不是契约请求本身。

### 7.1 798=29 与 793=35 字段差的归因（同视图 1632、同 create profile）

两入口消费同一原生表单视图、同一 create 渲染档，字段数却不同，必须给出依据而不是留一个数字。实测结论：
**差在字段策略层，不在结构消费层**。

1. **结构层完全一致**：`ui.contract` 编译后 798 与 793 的 `layoutContract.containerTree` 各含 **57 个 field 节点**，
   节点级 diff（`modifiers`／`attributes`／`occurrenceIndex`）在这些字段上逐项相同；`formStructureContract` 除
   `navigation.title` 与 `sourceAuthority.governance_source.businessConfigContracts`（222↔528 入口声明）外无实质差异。
   即两入口的结构权威、结构来源、容器树一致。
2. **策略层有差**：`statusContract.widgetStatus` 中 798 有 **27** 个 widget `visible=false`，793 有 **14** 个
   （第三轮用只读探针重算并已存档口径，见下「可复现性」）；只在 798 被置为不可见／`auth=none` 的恰好 **13** 个：
   `company_contractor_{responsibility_state,arrival_unprocessed_amount,arrival_over_processed_amount,self_funding_balance,responsibility_notice}`、
   `reject_reason`、`creator_name`、`created_time`、
   `legacy_{source_model,source_table,record_id,document_no,document_state}`。
3. **成因是入口业务类别**：798 的 action context 声明 `default_business_category_code=finance.deduction.bill`
   且 `allowed_business_category_codes=['finance.deduction.bill']`，该类别 `form_policy_json` 额外提供
   `dataContract.dataMeta.fieldGroups`（仅 798 有，793 为 `null`）与 **4 条** category-sourced `REQUIRED` 规则
   （`business_category_id`／`project_id`／`partner_id`／`deduction_line_ids`，source=`sc.business.category.form_policy_json`），
   使 798 的 `runtimeContract.validationRules` 为 **10** 条；793 无业务类别，全部 7 条都回落通用
   `visible_form_required_marker` 策略。**规则条数差是 3 不是 4**：`project_id` 在 798 由类别规则承担、
   在 793 由通用标记规则承担，属**同一字段换来源**而非新增规则（早前「7＋4＝10」的算术写法有误，此处更正）。
4. **与 DOM 计数对齐**：浏览器 `[data-field-name]` 包装数为 792=36／798=29／793=35；798 比 793 少的 **6 个**正好是
   上述 13 个里的 `company_contractor_*`×5 ＋ `reject_reason`。其余 7 个（`creator_name`、`created_time`、
   `legacy_*`×5）在 **798 与 793 的 DOM 中都不出现**（两入口一致），因此不参与该差值。

**可复现性（第三轮补齐）**：本节第 2／3 条的数字可由只读探针复算，命令与取值路径如下，不再依赖未存档的观察：
`env["ui.business.category"]` → 798 解析到 `finance.deduction.bill`、793 解析到无类别；
`statusContract.widgetStatus[].visible` 计数 → 27／14；`widgetStatus[].auth in (None,'none')` → 26／3；
`runtimeContract.validationRules` 的 `source` 分布 → 798 = `{sc.business.category.form_policy_json: 4, visible_form_required_marker: 6}`、
793 = `{visible_form_required_marker: 7}`；`dataContract.dataMeta.fieldGroups` → 798 为 dict、793 为 `null`。
第 1 条的「57 个 field 节点」与第 4 条的 DOM 差集在本轮 L4 报告
（`representative-report-expense_claim.json` 的 `stages.representative[].routes[].field_names`）中可直接复算：
`793 − 798 = {company_contractor_*×5, reject_reason}`（6 项）、`798 − 793 = ∅`。
**仍未存档、不作为依据**：早前写过的「58／57 节点级 diff 明细」「13 个不可见字段的逐字段来源」没有独立存档文件，
本节只保留可由上述取值路径复算的部分。

含义：798=29 与 793=35 的差**不是**结构被吞或被修剪，而是同一结构在不同入口业务类别下的字段策略结果。
本批不改业务类别 `form_policy_json`；若后续要求 798 呈现 `company_contractor_*`，责任层是业务类别策略，不是原生 arch。
**口径限制**：本节只证明「编译树里每个声明事实仍存在且只出现一次」与「策略层的可见性/可编辑性差异」，
**没有**证明 798 的这 13 个字段在**真实浏览器中**逐个不可见（本轮 L4 只按 `[data-field-name]` 包装计数与
`sections`/`navigation` 断言，未做 13 项的逐字段可见性断言）。

## 8. 回滚与数据边界

- 产品回滚：`git revert` 本批提交（纯展示层与配置声明，无模型字段、无数据迁移、无 ACL 变化）。
- 配置回滚：217/222 与新增 793 契约可单独置 `active=False`；模型级 72 未动。
- 数据边界：本轮未执行 `sync_demo`、fixture reset、发布快照、历史数据修复或模块升级（`smart_construction_core`
  的升级仅为本批数据文件生效所需）；未停启历史容器、未改 Docker 网络、未清理历史工作树、未消费任何非本轮草稿。

## 9. 状态与下一步

状态：**冻结链已走完（干净 HEAD ＋ 完整指纹 ＋ exact-head Quick ＋ 独立复核 APPROVE）｜未集成｜未部署｜89 入口交付未完成｜台账 34（扣减待合入后核对）**。

已按顺序执行完：记录第三轮回环（§11）→ 独立复核发现 `readonly` 放宽回归 → 修复 → 提交 → `ci.delivery.freeze.prepare`
→ 冻结干净 HEAD 与完整指纹（§12）→ 一次 exact-head Quick → 第三轮独立复核（§11.5，APPROVE）→
复核提出的 4 项**记录措辞**问题在归档前修完（§11.5，仅 `docs/`）→ 新 head 重走冻结链 → 外部归档与 PR 正文 →
合入后按 G03/G04 先例做扣减（34 → 32，退役 792/798/793 与视图 1632/1633，旁路 menu 543 登记 `bypassConsumers` 不计数，
`nextBatch.selectedGroup=G06`）。

本批不扩：约六组副本候选继续留台账；G06（税额与专项抵扣 790/879，视图 1654）另行准备，不在本批实施。

## 10. 独立复核闭环与本轮记录修正

第二轮之前的独立复核（只读）结论 **APPROVE**；无写路径、无授权绕过、无丢失业务事实、无 scope creep
（`addons/smart_core/**` 零改动、台账零改动）。复核提出的问题与本轮处置：

| 复核项 | 处置 | 状态 |
|---|---|---|
| 测试硬编码视图 id 1633／1632，在 id 不同的库会失败（major） | 改用 xmlid 寻址（§2 第 3 条） | **已修** |
| 总记录 §8.23 记「dirty 范围 8 个路径」与实际 11 文件不符 | 更正为 11 个路径并附候选身份 | **已修** |
| §2.1 归属表漏 `complexity_budget_report.md`（生成物） | 补为第 11 行，注明既有生成入口刷新 | **已修** |
| §4 L4 行「1 项登记事实未覆盖」与 §6 表 3 行不符 | 更正为 3 项 | **已修** |
| 「P0 共享结构消费机制」易读成改了 P0 源码 | §2.1 第 5 行标注「机制由测试锁定，未改 `smart_core` 源码」 | **已修** |
| 798=29 与 793=35 字段差无依据 | 补 §7.1 归因（结构层一致、差在业务类别字段策略层） | **已修** |
| `views/core/expense_claim_views.xml:333-335` 包装 `<group>` 缩进错位 | 纯 cosmetic、不影响 XML 语义与渲染；本批**不改**，避免为此作废 L3／L4 页面证据，留待下次触碰该文件时一并整理 | 已知未改 |

证据失效判定（第二轮）：变更仅 `tests/test_expense_claim_native_lowcode.py`（P4 测试）与两份记录（`docs/`）；
`addons/**` 下唯一改动落在 `tests/`，无产品运行路径改动（`git diff --name-only` 可核），
故 L1 重跑、L2 后端定向重跑；当时 L2 前端／L3／L4 页面证据的输入未变，按不变输入沿用（该沿用已被第三轮取代，见 §11）。

## 11. 第三轮回环：独立复核发现并修复 `readonly` 放宽回归

### 11.1 现象与首次偏差

第二轮提交 `b2b12365` 的独立只读复核结论 **REQUEST_CHANGES**，其中一条为**真实回归**（major）：

> 792 入口（`action_sc_expense_claim_reimbursement_request`，视图 1633）的 `company_name_text`、`paid_amount`、
> `payment_state`，从「退役配置声明只读」变成了契约层 `auth=edit`。

**首次偏差定位**：退役前 217 的配置体对这三个字段声明 `readonly`；本批把 217 改为 `native_semantic_surface`
并删除 `sections/fields`（配置侧结构副本）后，原生 arch 是唯一剩余载体，而 1633 上
`paid_amount`／`payment_state` 只是**条件**只读（`state in ['done','legacy_confirmed','cancel']`）、
`company_name_text` 连条件都没有。因此 create 档（`state='draft'` 缺省）下三字段全部落到 `auth=edit`。
对照 1632（扣款共享视图）的同族字段**已是** `readonly="1"`——但该声明由本批 recovery 步骤 `ba3f5da7`
补字段时新增：基线 `8e8c1ce9` 的 1632 完全没有 `company_name_text`／`paid_amount`／`payment_state` 声明
（`git show 8e8c1ce9:…/expense_claim_views.xml` 的命中只在树视图与 1633）。即**本批只对齐了 1632、漏了对齐 1633**，
两个共享视图的声明因此不一致；而本批只核对了「字段是否存在」，未核对「声明是否活到策略层」。
这是本批的方法缺口，不是环境问题，也不是基线遗留缺陷。

**归因链（每步实测）**：

1. 只读探针对 792 逐字段矩阵：`LOSS = [company_name_text, paid_amount, payment_state]`，其余 16 项无丢失。
2. 从基线 `8e8c1ce9` 的 `expense_claim_form_productization_contract.xml` 用 `ast.literal_eval` 解出 217 的
   `contract_json`：49 个字段中 19 个 `readonly: True`，包含这三项；222 为 53 字段中 26 项。
3. 原生 arch 对照：基线 1633 三字段如上（条件只读／无声明）；1632 的同族 `readonly="1"` 是本批 `ba3f5da7` 新增（基线无）。
4. 合并方向证据：`addons/smart_core/core/view_orchestrator.py:1103` `_apply_field_display_policy`——
   policy `readonly: True` **强制**节点只读，`readonly: False` 仅在原生无限制时生效；`:975` 归一化 `readonly`。
   因此「把声明写回原生 arch」既不与 217/222 冲突，也不与其它入口的既有意图冲突：实测扫描 18 份
   `sc.expense.claim` 表单契约，其中 **14 份入口契约全部声明这三项 `readonly: True`**（`not_readonly_true=[]`），
   1632 亦为 `readonly="1"`，且全库 runtime 配置无任何 `node_patches`／`field_policy` 涉及这三项。
   **边界**：对**无入口声明**、经模型级 72 解析的入口未逐入口实测（批外且无契约，受管 runner 内无法验证）；
   该部分结论依据上述声明一致性与「`readonly` 不移除动作入口」推导，不声称已实测。

### 11.2 修改层与改动

责任层：**P1 行业标准默认**（`smart_construction_core` 原生视图），不是 P0 机制、不是运行时配置。
`views/core/expense_claim_views.xml` 共 3 行：

- `paid_amount`：`readonly="state in ['done','legacy_confirmed','cancel']"` → `readonly="1"`
- `payment_state`：同上 → `readonly="1"`
- `company_name_text`：补 `readonly="1"`

测试同批加固（P4）：`DECLARED_READONLY_CLAIM_FACTS` 补入这三项，并新增 `widget_status()` 读取器，
使断言从「编译后的 arch 字符串」升级为「**渲染器实际消费的策略层**」：
每个声明只读事实在 `statusContract.widgetStatus` 中的 `readonly` 必须为真。

### 11.3 验证

| 项 | 结果 |
|---|---|
| L1 `make ci.local.iteration` | PASS（16 tests） |
| L2 后端定向 | PASS：`0 failed, 0 error(s) of 9 tests`（含新断言） |
| L3 `local.dev.upgrade` | PASS：78 modules ＋ demo authority |
| 只读探针（从 DB 实际 arch 解析） | **792 `LOSS=[]`、`HARD_NONREADONLY=[]`**；三字段 `ctl_ro=true`（`company_name_text`：`model_ro=false / arch_ro="1" / ctl_ro=true`） |
| L4 代表面重跑 | PASS（§7 表；页面证据按依赖作废后重取，报告 sha256 `c04bc2c1…`） |

**793 的 `state` 不再计入本项**：探针显示 793 的 `state` 为 `auth=edit`，但 793 从未声明过该事实
（基线无入口契约），且 `state` 在 1632 由 `widget="statusbar"` 承载、前端 `normalizeNativeFormStatusbar`
另有 `fieldReadonly || profile=readonly || !rights.write` 门控，**create 档 `recordId` 为空时状态条 `visible=false`**。
因此它不是「声明丢失」，而是下述候选缺口。

### 11.4 登记为候选缺口（未在本批修改）：无声明入口的状态条可写

**事实**（第三轮只读实测，17 个 `sc.expense.claim` 表单入口全扫）：

- 792/798 的 `state` 只读来自**业务类别** `form_policy_json`
  （`readonly_profiles: [create, edit, readonly]`），不是原生 arch；
- 全部 14 份入口契约与 25 份类别策略**一致**声明 `state` 只读，没有任何来源声明它可编辑；
- 结果：**793 是 17 个入口中唯一 `state` 为 `auth=edit` 的入口**（`readonly=false`），
  另有 6 个无任何入口声明的入口（794／815／839／840／841／842）同型。

**为什么不在本批修**（三条都可核）：

1. **不是本批回归**：基线 793 没有入口契约，只用模型级 72 时 `state` 同样是 `readonly=false`；
   内存内剔除 528 的对照实验（`_effective_view_orchestration_contracts` 过滤）得到同一 `state` 行。
2. **可用载体只有共享原生 arch，而 1632 是模型默认表单视图**
   （`sc.expense.claim.get_view(view_type='form')` → 1632），加 `readonly="1"` 会同时收紧上述 6 个**批外**入口。
   这 6 个入口不在本批登记面内，其状态流转的合法入口尚未核验，直接收紧会违反
   「确认合法动作不会因门控而失去入口」。
3. **入口级最小修复在当前机制下不被允许**：`form_configuration_compiler.is_configured_surface` 只接受
   `tenant_lowcode_configuration` / `user_preference_projection`；793 的 528 是 `source=…product_release`，
   若在其中加 `node_patches` 会命中 `CONFIG_SOURCE_NOT_AUTHORIZED`（前缀还会命中
   `CONFIG_TARGET_BINDING_REQUIRED`）。要在此层修复需改 P0 机制，超出本批边界。

**影响面（如实登记，不夸大为越权）**：模型层未在 `write()` 中拦截状态跳转，ACL 才是写边界；
`finance_read` 对 `sc.expense.claim` 只读，但 `finance_user`／`finance_manager` **implies** `finance_read`
因而可达 793 且具备 create/write——他们打开**既有**备用金记录时状态条可交互。
也就是说这是**入口间 UX 一致性缺口**与**工作流绕过面**，不是权限绕过。
**推荐修复方向（留待下一批/机制层决定）**：在 P0 策略层为「无业务类别的入口」提供显式的 workflow-state 只读承载，
而不是逐入口改共享 arch。

### 11.5 第三轮独立复核（候选 `78f7cd17`）与随之完成的记录修正

只读独立复核（禁写、禁远端、未跑 Quick、仅只读读取既有回执）结论 **APPROVE**：无 S0／S1。
复核方独立复算的关键事实与本记录一致：工作树 clean（仅 `ahead 3`）、`git diff --stat 8e8c1ce9..78f7cd17` 为 11 文件、
`addons/smart_core/**` 零改动、`78f7cd17` 仅 4 文件且无夹带、指纹 digest／7509 路径内存复算一致、台账 34、
`transport_recoveries` 恰 1 条、36／29／35 与 8 章节／8-8 导航／13px 吸顶可复算；并实测**修复后 792 三字段
`(readonly=true, auth="read")`**、相邻可编辑事实未被收紧、14 份入口契约无相反声明、动作入口无损失。

复核提出 4 项 **S2 记录措辞**问题（均非阻断，不涉及代码），已在归档前修正：

| 项 | 修正 |
|---|---|
| §11.1 原写「1632 同族字段**本就是** `readonly="1"`」与基线不符 | 更正为「本批 `ba3f5da7` 补字段时新增，基线 1632 无这三项声明」——如实登记为**本批只对齐了 1632、漏了对齐 1633**（§11.1 归因链第 3 步同步更正） |
| §11.1 归因链第 4 条「对其它 1633 消费者不产生收紧」是无条件表述 | 限定为 14 份入口契约（实测 `not_readonly_true=[]`）与 1632 消费者，并显式标注**无入口声明的入口未逐入口实测** |
| 总记录三处历史状态行仍写「台账 42」，易与现行 34 混淆 | 改为「台账 42（当时）」，与 §8.20／§8.22 的 42→38→36→34 扣减链一致 |
| 总记录「独立复核结论 APPROVE」未标注适用候选 | 标注为候选 `ba3f5da7`，与 §8.23.1 记录的 `b2b12365` REQUEST_CHANGES 区分 |

修正只触碰两份 `docs/` 记录，无产品运行路径改动（`git diff --name-only` 可核）；按阶段证据规则，
文档变更不作废页面证据，故 L3 升级与 L4 页面证据不因此重跑，但冻结身份按规则在新 head 上重走一次
（完整指纹 ＋ exact-head Quick ＋ 独立复核绑定同一指纹）。

## 12. 身份与冻结口径

本记录按「日迭代＝HEAD＋显式 dirty 范围」书写，**不声称 frozen**；冻结值不写入本文件（写入本文件会改变候选自身的
commit hash），只出现在冻结步骤生成的产物与外部归档中。

| 阶段 | 身份 | 取值方式 |
|---|---|---|
| 迭代期（§1–§10 书写时） | `HEAD=b2b1236595701afa9e7e274c3d0c417658aafac7` ＋ dirty `{views/core/expense_claim_views.xml, tests/test_expense_claim_native_lowcode.py}` | 第二轮结束时的身份；§11 的 3 行 arch 改动即此 dirty（L4 报告 `dirty=true` 即此状态） |
| 第一轮提交 | `ba3f5da7ad54f68cb59d5553166f1d9eab6f1598`（tree `7380ca2915e20ecb4f0317d96dd6988a16123f81`） | 已被第二轮取代 |
| 第二轮提交 | `b2b1236595701afa9e7e274c3d0c417658aafac7`（tree `70d23ed16e5aa62d4d585c3b66300867fb85a550`） | Quick 回执 `.git/codex/evidence/ci.local.quick/b2b1236595701afa9e7e274c3d0c417658aafac7.json`（PASS）；**已被第三轮取代** |
| 第三轮提交 | `78f7cd17d573a720edc5093f457d758864b03b8f`（tree `6497b2c212398712cc6891c30576fe03fe71e5d4`） | Quick 回执 `.git/codex/evidence/ci.local.quick/78f7cd17d573a720edc5093f457d758864b03b8f.json`（PASS）；第三轮独立复核 APPROVE（§11.5）；**已被本轮记录修正提交取代** |
| 记录修正提交 → 冻结 | 由本次提交产生；冻结值只出现在外部归档 `identity.json` / `worktree-fingerprint.json` | `python3 scripts/contract/complete_worktree_fingerprint.py --baseline 8e8c1ce9d4d0fbe63b141cf75475030282f9f9d9` ＋ `make ci.local.quick`（exact-head，一次）＋ 独立复核绑定同一指纹 |

**L4 报告的自身身份口径**：`representative-report-expense_claim.json` 顶部 `candidate` / `dirty` 记录的是**产生该报告时的
运行身份**（本轮为 `b2b12365` ＋ `dirty=true`），它是「按当时 HEAD＋dirty 运行」的事实记录，**不是**冻结候选的证明。
冻结候选身份只认「干净 HEAD ＋ 完整指纹 ＋ exact-head Quick 回执」三件套；报告与截图在归档中作为该次运行的页面证据，
与其它角色文件一同绑定同一 `candidateHead`。

## 13. 第三轮复核提出、按边界未处置项（不隐藏）

| 项 | 处置 |
|---|---|
| 793 及 6 个无声明入口的 `state` 可写（§11.4） | 登记为候选缺口；修它需要 P0 机制或收紧模型默认表单视图，两者都超本批边界 |
| `sc.expense.claim` ir.rule 组交并被合并为 `&`，非扣款组读域归零（§6） | 批外机制面，只登记不改 |
| `views/core/expense_claim_views.xml` 包装 `<group>` 缩进错位（§10） | 纯排版，本批不改，避免作废 L3／L4 页面证据 |
| compatibility 平面 create 档可把整个 primary zone 修剪空且无 fail-closed（§5） | 影响全部 compatibility 入口，超本批边界，登记不改 |
| G04 遗留：808／811 的 5 个 `company_contractor_*` 合法隐藏未在契约层复现 | 属 G04 批次边界，本批不合并处理 |
| 837 record 渲染层少 2 个章节入口；「契约字段→渲染节点」逐字段归因 | 未覆盖项，随 G06 准备一并处理 |
