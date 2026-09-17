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

1. `views/core/expense_claim_views.xml`（75+/24-）：两个共享表单加 10／9 个 `data-sc-anchor` 业务章节锚点；
   按退役配置反推的原生缺失字段全部补回（1633 补 9 个，1632 补 24 个），无任何配置声明字段仍缺失；
   头部 6 个按钮保持不变，`action_view_company_contractor_responsibility_summary` 保持为章节内载体（非 header）。
2. `data/expense_claim_form_productization_contract.xml`（85 变更行）：
   - 217（报销申请）、222（扣款登记）`contract_json` 改为 `{'title': …, 'composition_mode': 'native_semantic_surface'}`，
     删除 `sections/fields/columns`（配置侧结构副本）；其余 14 份入口级契约未改。
   - **新增** `business_config_contract_expense_claim_advance_fund_productized_form_v1`（action 793，`title=备用金`，
     `native_semantic_surface`，无 sections/fields/columns）。模型级 `sc_expense_claim_form_structure_generated_v1`(72)
     **保留原样**（`active=True`、`action_id` 为空），继续服务其其它消费者。
3. `tests/test_expense_claim_native_lowcode.py`（新增 578 行 / 9 测）+ `tests/__init__.py` 注册。
4. `frontend/apps/web/scripts/native_section_navigation_test.ts`（162+/1-）：共享机制用例（空容器不吞按钮/关系/投放目标、
   父级仅剩隐藏子节点不产生导航项、正文与导航同源）。
5. `frontend/apps/web/scripts/formal_form_representative_journey.mjs`（+20）、`formal_form_lowcode_loop.mjs`（+8）、
   `scripts/verify/local_dev_form_lowcode_scope.py`（36 变更行）：代表面「未覆盖」显式登记（见 §6）。

回滚路径：217/222 与新增的 793 契约只要 `active=False`（或 `git revert`）即回到迁移前；
模型级 72 未被修改，`git revert` 本批提交即可整体回退。原生补字段与锚点的回滚同样是 `git revert`（纯展示层，无数据迁移）。

### 2.1 文件归属（接管前已有 / 接管后修改 / 仅验证）

| # | 路径 | 归属 | 改动 | 层 |
|---|---|---|---|---|
| 1 | `addons/smart_construction_core/views/core/expense_claim_views.xml` | 接管前已有 | **接管后修改**（锚点＋补字段） | P1 |
| 2 | `addons/smart_construction_core/data/expense_claim_form_productization_contract.xml` | 接管前已有 | **接管后修改**（217/222 去结构 + 新增 793 入口声明） | P1 |
| 3 | `addons/smart_construction_core/tests/test_expense_claim_native_lowcode.py` | — | **本批新增**（578 行 / 9 测） | P4 |
| 4 | `addons/smart_construction_core/tests/__init__.py` | 接管前已有 | **接管后修改**（注册测试模块） | P4 |
| 5 | `frontend/apps/web/scripts/native_section_navigation_test.ts` | 接管前已有 | **接管后修改**（机制用例） | P0 |
| 6 | `frontend/apps/web/scripts/formal_form_representative_journey.mjs` | 接管前已有 | **接管后修改**（未覆盖登记） | P4 |
| 7 | `frontend/apps/web/scripts/formal_form_lowcode_loop.mjs` | 接管前已有 | **接管后修改**（未覆盖/BLOCKED 打印） | P4 |
| 8 | `scripts/verify/local_dev_form_lowcode_scope.py` | 接管前已有 | **接管后修改**（topic＋样本可用性事实） | P4 |
| 9 | `docs/ops/iterations/uc4_expense_claim_native_lowcode_20260918.md` | — | **本批新增**（本记录） | 记录 |
| 10 | `docs/ops/iterations/form_structure_consumption_stabilization_20260917.md` | 接管前已有 | **接管后修改**（总记录 §8.23） | 记录 |

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

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | **PASS**：16 tests OK；`change_state=dirty coverage=L1_only receipt=none` |
| L1/L2（前端机制） | `make verify.frontend.native_section_navigation.unit` | **PASS**：`authority=7 next_action=3 content_identity=11 active_tracking=7 structure_consumption=7` |
| L2（前端类型） | `make verify.frontend.typecheck.strict` | **PASS**（`vue-tsc --noEmit -p tsconfig.strict.json` 无输出即通过） |
| L2（后端） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestExpenseClaimNativeLowcode'` | **PASS**：`0 failed, 0 error(s) of 9 tests` |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` | **PASS**：78 modules loaded ＋ `local.dev.demo.authority` PASS |
| L4 | `make local.dev.form_lowcode.browser FORM_LOWCODE_TOPIC=expense_claim FORM_LOWCODE_REPRESENTATIVE=1` | **PASS**：三入口 create 通过，1 项登记事实未覆盖（§6） |

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

`failed_requests=0`、`browser_errors=[]`、`transport_recoveries=[]`、`cleanup_guard.decision=proceed`、`restored=true`。
本次运行 **没有**传输中断，但按既有口径这只是「本次运行未观察到中断」，不构成「网络已恢复正常」的判据；
`ERR_NETWORK_CHANGED` 仍按 Vite dev 模块传输中断记录（既非接口故障，也不得改写成零错误）。

## 8. 回滚与数据边界

- 产品回滚：`git revert` 本批提交（纯展示层与配置声明，无模型字段、无数据迁移、无 ACL 变化）。
- 配置回滚：217/222 与新增 793 契约可单独置 `active=False`；模型级 72 未动。
- 数据边界：本轮未执行 `sync_demo`、fixture reset、发布快照、历史数据修复或模块升级（`smart_construction_core`
  的升级仅为本批数据文件生效所需）；未停启历史容器、未改 Docker 网络、未清理历史工作树、未消费任何非本轮草稿。

## 9. 状态与下一步

状态：**批次验收中（未冻结）｜未集成｜未部署｜89 入口交付未完成｜台账 34（扣减待合入后核对）**。

下一步（按既有顺序）：生成证据准备与预检 → 冻结干净 HEAD 与完整指纹 → 一次 exact-head Quick →
独立复核 → 外部归档与 PR 正文 → 合入后按 G03/G04 先例做扣减（34 → 32，退役 792/798/793 与视图 1632/1633，
旁路 menu 543 登记 `bypassConsumers` 不计数，`nextBatch.selectedGroup=G06`）。

本批不扩：约六组副本候选继续留台账；G06（税额与专项抵扣 790/879，视图 1654）另行准备，不在本批实施。
