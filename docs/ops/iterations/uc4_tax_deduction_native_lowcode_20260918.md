# U-C4 G06 税额与专项抵扣原生结构迁移与低代码兼容

- 批次：`U-C4` 表单结构消费稳定化 · 代表面 `G06 税额与专项抵扣`
- 分支：`feature/uc4-tax-deduction-native-v1`（基于 `origin/main`=`daf9a97875a15343671c00e46fd9c4e639ebeca2`）
- 唯一写入者：本会话执行体；本候选之外的其它工作树本轮未触碰
- 状态：**批次验收完成（本批范围）｜主线集成完成（PR #494，main=`5938d6c620952e9c4c1af9fa6c33dbda14da0374`，squash 同树）｜未部署｜89 入口交付未完成**；
  台账（`form_structure_compatibility_consumers_v1.json`）已按合入后的独立提交扣减 **31 → 29**（§12.12）；
  §12.10.6／§12.11 的「整改中」口径与冻结链作为该阶段的历史记录保留

## 1. 范围与身份

| 项 | 值 |
|---|---|
| 正式入口 | `action 790` 抵扣登记 / menu 538、`action 879` 项目专项抵扣 / menu 701 |
| 旁路入口 | `action 852` 扣款单：无自有菜单、只固定 tree 视图、无自有发布契约，记录回落到同一 primary form；按「非消费者」登记，不计数（§4） |
| 模型 | `sc.tax.deduction.registration`（两入口同模型） |
| 原生表单视图 | 两入口均不固定 `view_id`／`view_ids`，都解析到模型 primary form `view 1654` `view_sc_tax_deduction_registration_form` |
| 台账登记配置 | `tax_deduction_registration_productized_form_v1`(206, action 790)、`project_special_tax_deduction_form_v1`(177, action 879) |
| 模型级配置（本批**未改**） | `sc_tax_deduction_registration_form_sections_v1`(143)、`sc_tax_deduction_registration_p1_form_business_facts_v1`(5)、`sc_tax_deduction_registration_form_structure_generated_v1`(129) |

两入口的 action 级权限本批**未改动**：790＝业务发起/财务只读/财务经办/财务审批（78/94/95/96），
879＝财务经办/财务审批（95/96）。模型 ACL、菜单 groups、action domain／context 全部保持原样。

职责分层（本批实施）：

| 层 | 目标 | 说明 |
|---|---|---|
| Formal Product Layer | P0 平台机制（只消费，不改）+ P1 入口声明 + P4 验证工具 | 结构消费属 P0，入口声明属 P1 |
| Layer Target | `smart_construction_core` 原生视图 + 入口级发布配置 | **不改 `smart_core` 机制代码** |
| Standard vs User-Specific | 行业标准默认 | 税额抵扣与项目专项抵扣属标准业务入口 |
| Why Here | 原生 arch 是结构权威；入口发布只保留标题与自身语义上下文 | |
| Why Not Elsewhere | 不把结构写进共享层 sections，也不删除／改写模型级配置（另有消费者 852） | |
| Blast Radius | `sc.tax.deduction.registration` 的 790／879 两个入口 + 同模型旁路入口 852（不改造，仅验不被误伤） | |

## 2. 实际改动（6 个代码／工具路径 + 3 个记录路径 = 9 个路径）

1. `views/core/tax_deduction_registration_views.xml`（+22/−13）：表单加 **8 个** `data-sc-anchor` 业务章节锚点
   （`deduction_business_direction`／`deduction_project_partner`／`deduction_invoice_info`／`deduction_amount_tax`／
   `deduction_handling`／`deduction_note_attachment`／`contractor_responsibility`／`deduction_source_trace`），
   后两个分别归属条件页 `责任余额` 与 `迁移来源`；按退役配置反推的原生缺失字段全部补回
   （`company_id`、`partner_name`、`deduction_bill_attachment_text`、`message_attachment_count`，
   以及 `迁移来源` 页上的 `legacy_source_model`／`legacy_source_table`／`legacy_record_id`／`legacy_document_state`／
   `source_created_by`／`source_created_at`），并把两个退役入口声明过的只读限制写回 arch
   （`state` 状态条、`source_origin`、`currency_id` 收紧为 `readonly="1"`；
   `business_category_id` 改为 `readonly="deduction_scope == 'project_special' or state == 'legacy_confirmed'"`，
   使共享表单同时满足 879 只读、790 可编辑的两种职责）；
   头部 3 个按钮与章节内载体 `action_view_company_contractor_responsibility_summary` 均保持不变。
   **同时删除原生 arch 自身的重复呈现**：`withholding_amount` 原本在 `抵扣金额与税额` 与 `扣款办理` 两个章节各出现一次
   （同一表单同一上下文重复投影），本批保留在 `抵扣金额与税额`（与退役配置一致），`扣款办理` 内不再重复（§10）。
2. `data/tax_deduction_certificate_form_productization_contract.xml`（+43/−1）：206（action 790）`contract_json` 改为
   `{'view_orchestration': {'context': {...product_release}, 'views': {'form': {'title': '抵扣登记',
   'composition_mode': 'native_semantic_surface'}}}}`，删除 `sections/fields/columns`（配置侧结构副本）。
3. `data/project_special_tax_deduction_contract.xml`（+20/−39）：177（action 879）同样改为 title-only 的
   `native_semantic_surface`，删除 `sections/fields/columns`；**但保留**其语义上下文键
   （`fact_authority`、`deduction_scope_authority: project_special`、`projection_authorities`）——
   该上下文说明本入口解析同一模型的 `project_special` 切片，**不是**第二份结构。
4. `tests/test_tax_deduction_native_lowcode.py`（**新增** 492 行 / 7 测）+ `tests/__init__.py`（+1，注册模块）。
5. `scripts/verify/local_dev_form_lowcode_scope.py`（+26）：在既有受管 runner 内登记只读代表 topic `tax_deduction`
   （`TOPIC_IDENTITIES`／`TOPIC_SAMPLE_FIELDS`／`TOPIC_REPRESENTATIVE`），复用同一环境、身份校验与数据权威，
   **未新建 fixture 或环境**。

回滚路径：206／177 只要 `active=False`（或 `git revert`）即回到迁移前；模型级 143／5／129 未被修改，
`git revert` 本批提交即可整体回退。原生补字段、锚点与只读声明的回滚同样是 `git revert`（纯展示层，无数据迁移）。

### 2.1 文件归属（接管前已有 / 接管后修改 / 仅验证）

| # | 路径 | 归属 | 改动 | 层 |
|---|---|---|---|---|
| 1 | `addons/smart_construction_core/views/core/tax_deduction_registration_views.xml` | 接管前已有 | **接管后修改**（锚点＋补字段＋只读收紧＋去重复呈现） | P1 |
| 2 | `addons/smart_construction_core/data/tax_deduction_certificate_form_productization_contract.xml` | 接管前已有 | **接管后修改**（206 去结构副本） | P1 |
| 3 | `addons/smart_construction_core/data/project_special_tax_deduction_contract.xml` | 接管前已有 | **接管后修改**（177 去结构副本，保留语义上下文） | P1 |
| 4 | `addons/smart_construction_core/tests/test_tax_deduction_native_lowcode.py` | — | **本批新增**（492 行 / 7 测） | P4 |
| 5 | `addons/smart_construction_core/tests/__init__.py` | 接管前已有 | **接管后修改**（注册测试模块） | P4 |
| 6 | `scripts/verify/local_dev_form_lowcode_scope.py` | 接管前已有 | **接管后修改**（注册只读代表 topic） | P4 |
| 7 | `docs/ops/iterations/uc4_tax_deduction_native_lowcode_20260918.md` | — | **本批新增**（本记录） | 记录 |
| 8 | `docs/ops/iterations/form_structure_consumption_stabilization_20260917.md` | 接管前已有 | **接管后修改**（总记录 §8.25） | 记录 |
| 9 | `docs/engineering_convergence/complexity_budget_report.md` | 接管前已有 | **接管后修改**（既有生成入口刷新，非手改摘要） | P4（生成物） |

**仅验证、未修改**（不得计入本批改动）：

- `addons/smart_core/**`：本批**未改**共享机制代码。两入口的 `native_semantic_surface` 是配置层
  （`ui.business.config.contract`）声明，不是机制改动。
- 模型级配置 143／5／129 与旁路入口 852：只读核对，未改、未删、未停用。
- `docs/ops/iterations/form_structure_compatibility_consumers_v1.json`：**实现提交未改**（保持 31），
  扣减在合入后由独立提交落地。
- `scripts/verify/view_orchestration_product_boundary_guard.py`：**未改**（§10 登记其既有失败）。
- `/tmp` 下本轮只读诊断脚本：全部在进程外，不进入提交。

## 3. 机制审查结论（先审查，再决定登记范围）

按 P0／P1 口径逐条核对，结论如下（均为只读实测）：

1. **只消费明确的通用语义**：两入口的 `composition_mode=native_semantic_surface` 是显式声明；
   本批没有按模型名或字段后缀猜测副本。删除的只有 206／177 自身 `contract_json` 内的
   `sections/fields/columns`（同一入口的配置侧结构副本），未触碰同模型的其它配置。
2. **同源但承担独立职责的字段不自动删除**：`project_special` 的语义上下文键（`deduction_scope_authority` 等）
   是两个入口唯一的区分依据，属「确有依据的来源关系」，予以保留。
3. **同一事实允许多场景表达，禁止同上下文重复**：`withholding_amount` 在原生的同一表单内重复出现两次，
   属同一上下文内的无意义重复 → 收敛为一次（§10）。
4. **原生结构权威不能单独证明动作已有承载位置**：本批**未**删除任何动作按钮；
   3 个头部按钮与章节内载体按钮都在 arch 中保留了实际承载位置，并用测试断言
   （`test_native_anchors_wrappers_and_conditional_sections`）证明其仍被契约树承载。
5. **空 header ／ 无标题包装组 ／ 嵌套分隔线**（本批验证重点）：本批给 8 个章节都加了 `name` 与
   `data-sc-anchor`，使「标题 + 稳定键」同时存在；未新增无标题包装组；`迁移来源` 页原本就是一个
   无标题 `<group>`，本批为其补 `name`／`string`／锚点，使其成为有标题的正文分组而不是空壳。

## 4. 分层验证结果（实际执行）

| 层 | 入口 | 身份 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | HEAD `daf9a978` + dirty（6 路径） | **PASS**：16 tests OK；`changedPathCount=6`、`change_state=dirty coverage=L1_only receipt=none`（L1 不入交付证据） |
| L2（后端，本批） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestTaxDeductionNativeLowcode'` | 同上 | **PASS**：`0 failed, 0 error(s) of 7 tests`（独立复核的 nit 已闭合后重跑：790 可编辑事实改为断言解析后策略 `readonly=false` / `auth=edit`） |
| L2（后端，相邻） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestProjectSpecialTaxDeduction'` | 同上 | **PASS**：`0 failed, 0 error(s) of 2 tests`（独立复核指出原「沿用回执」未留存对应回执，故本提交前实跑一次取回执） |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` | 运行身份 `project=sc-local-dev db=sc_dev_demo` | **PASS**：78 modules loaded（90.6s / 58295 queries）＋ `local.dev.ready` PASS ＋ `local.dev.demo.authority` PASS（`finance_xmlid=present finance_membership=authoritative company_currency=CNY sale_tax_9=present`） |
| L4（只读代表面） | `make local.dev.form_lowcode.browser FORM_LOWCODE_TOPIC=tax_deduction FORM_LOWCODE_REPRESENTATIVE=1` | 同上 | **PASS**：`ok=true restored=true`，3 条 create/record 路由，findings 全空，吸顶不重叠；1 项登记事实未覆盖（§6）。证据：`artifacts/lowcode-form-loop/browser/representative-report-tax_deduction.json` |

stage identity 口径：本批按「日迭代＝HEAD ＋ 显式 dirty 范围」记录；冻结候选身份的取值不写入本记录文件
（写入会改变候选自身的 commit hash），只在冻结步骤生成的产物与外部归档中出现（§11）。

L2 覆盖的 7 个用例：入口契约只花一份原生结构、legacy 结构不得在原生权威入口上二次投影、
声明事实恰好渲染一次（且隐藏必须是消费层可见性而不是静默移除）、补回事实是真实字段而非同名副本、
补回事实保持声明过的只读行为、锚点/包装组/条件章节/载体按钮、模型级配置继续服务旁路入口 852。

**失败归因（已完成，不重跑）**：`TestUserFeedbackBusinessViews` 在 `sc_dev_demo` 上 28/72 失败。
为区分「本批引入」与「基线已有」，在基线态（把本批 3 个产品文件 `git checkout` 回 `daf9a978` 并重新 upgrade）复跑，
得到**完全相同**的 28 项失败集合（`diff` 为空），故判定为**预先存在、与本批无关**（成因为测试数据漂移：
`发票合同类型必须与发票业务类型一致`／`必须关联已归属公司的有效项目`／`currency_id` 可见性等）。
归因后已从备份恢复本批文件并再次 upgrade PASS。

## 5. L4 归因：790 记录态导航少了「扣款办理」——空值合法隐藏，不是丢失

**观察**：790 `record`（只读呈现）路由的导航目标是 7 个：业务方向／项目与往来单位／发票信息／抵扣金额与税额／
**办理说明与附件**／协作记录／历史审计；同一入口的 `create` 路由是 7 个但含**扣款办理**、不含历史审计。
即 `扣款办理` 在只读呈现下不产生导航项。

**归因链（每步实测）**：

1. 只读路由渲染字段 26 个，create 路由 30 个，差集恰为
   `{attachment_ids, deduction_bill_attachment_text, deduction_reason, deduction_unit_name}`；
   `扣款办理` 分组的两个字段（`deduction_unit_name`、`deduction_reason`）都在差集内 → 该分组无可渲染内容，
   按 P0「父级仅剩隐藏子节点不产生导航项」不再产生导航项。
2. 只读 `sc_dev_demo` 探针读受管样本 `sc.tax.deduction.registration` id=1（`S70-TAX-001`，`state=deducted`，
   `source_origin=manual`）：`deduction_unit_name=False`、`deduction_reason=False`、`attachment_ids`（0 条）、
   `deduction_bill_attachment_text=''`，而 `note='S70 进项税抵扣登记样例'`、`message_attachment_count=0`。
3. 因此 `扣款办理` 的消失由**样本本身取值为空**驱动，`办理说明与附件` 因 `note` 有值而保留导航项。
   报告同时给出 `collapsed_sections=[]`／`collapsed_sections_unresolved=[]`，即没有任何章节被折叠且无法解析。

**结论**：属 P1「字段合法隐藏」，不是修剪误删、不是定位器错误、不是加载失败。
可写面（create）已证明该分组的锚点与字段仍被契约树承载；只读面的缺席不登记为缺陷。
（`责任余额`／`迁移来源` 两个条件页在本批受管样本上同样按条件隐藏，其锚点与条件由 L2 用例在契约层锁定：
`test_native_anchors_wrappers_and_conditional_sections` 断言两页各自的 `invisible` 条件与「页签归属」链路。）

## 6. P4 工具与「未覆盖」事实

只读代表路由 `tax_deduction`（2 身份）登记在 `scripts/verify/local_dev_form_lowcode_scope.py`，
复用既有受管 runner、环境与身份校验（**未另建 fixture 或环境**），并对每条登记事实给出显式的
`representative_uncovered` 记录，使「已登记但当前跑不了」的事实可见而不是静默消失：

| 入口 | 登记事实 | 状态 | 原因 |
|---|---|---|---|
| 879 | `record_surface` | `empty_action_domain` | `domain_rows=0`、`business_row_count=1`：受管身份在该入口 domain 下没有可读样本，故只读重放无从进行；如实登记为未覆盖，**未**缩短或跳过 |

## 7. 代表面结果（L4 明细）

报告：`artifacts/lowcode-form-loop/browser/representative-report-tax_deduction.json`（`candidate=daf9a97875a1…`，`dirty=true`）。
`recovery_state={"draft_tokens_held":0,"rollback_tokens_pending":0,"released":true}`、`cleanup_guard={"decision":"proceed","foreign":[]}`、
`browser_errors=[]`、`transport_recoveries=[]`；runner 明确输出 `business fingerprints unchanged`，全程只读，
未保存／发布／回滚／清理任何草稿，受保护草稿 163/190/192/194/233/267/274/276 未被触碰。
其中草稿编号口径为 `ui.business.config.change.set`（低代码变更集）上的 id；同一编号在
`ui.business.config.contract.version` 上是另一批对象，两者不可混用。

只读呈现层另有一处已登记的呈现事实（不影响功能）：790 `record` 呈现下 `business_category_id` 的
`widgetStatus` 报 `readonly=true`、`reasonCode=NATIVE_MODIFIER_UNRESOLVED`——条件表达式
（`deduction_scope == 'project_special' …`）在只读**呈现**模式不求值，故按「无法解析即只读」保守呈现；
可写面（create）解析为 `readonly=false` / `auth=edit`，即合法编辑入口未丢失。

| 入口 | 路由 | 字段 | 章节 | 导航 resolved+visible | findings |
|---|---|---|---|---|---|
| 790 | create | 30 | 7 | 7/7 | `duplicated=[] empty_containers=[] decorated_layout_groups=[] titled_layout_groups=[]` |
| 790 | record（只读） | 26 | 7 | 7/7 | 同上（§5 归因） |
| 879 | create | 30 | 7 | 7/7 | 同上 |

吸顶布局（1088×900）：操作行 `175–205`、导航 `218–257`，相邻分离 **13px**，正文目标 `269` 起；章节跳转后三者互不遮挡。

## 8. 回滚与数据边界

- 本批写入的对象只有两类：`ui.business.config.contract` 206／177（入口发布）与原生 `ir.ui.view` 1654 的 arch；
  两者的回滚均为 `active=False` 或 `git revert`，无数据迁移、无 ACL／groups／domain 改动。
- 受管样本与测试草稿：本批 L4 为**只读**，`recovery_state.released=true`、`draft_tokens_held=0`，
  未创建、未消费、未清理任何草稿；非本轮所有的草稿一律保留。
- 未执行：`sync_demo`、fixture reset、发布快照、历史数据修复、无关模块 upgrade、容器停启、Docker 网络调整、
  历史工作树清理。受管开发服务仅在加载本批后端变更时按既有 Make 入口重启并核验运行身份。

## 9. 状态与下一步

- 本批范围：入口 790／879 的原生结构消费收敛 + 入口声明退役 + P4 只读代表面与测试。
- 台账 `form_structure_compatibility_consumers_v1.json` 保持 **31**；本批在台账内**正好 2 条**
  （index 21 = action 790／menu 538／view 1654、index 22 = 879／menu 701／view 1654），
  合入后按 G03/G04/G05 先例退役这两条并新增 `uc4G06PublishedAudit`，`count`／`localVerifiedCount`／
  `mainlineRemainingCount` 同步 **31 → 29**，`nextBatch.selectedGroup` 前进到下一组。
- 未推送、未建 PR、未合并、未部署；冻结候选身份的取值不写在本文件，见 §11 与外部归档。

第 5 轮结束时状态（**已被 §12 取代，不得再作为当前结论引用**）：
当时记为「批次验收完成（本批范围，冻结链见 §11）｜未集成｜未部署｜89 入口交付未完成｜台账 31」；
随后用户复核未通过并进入 §12 整改，当前状态以 §12.8 末行为准（**整改中**，不是验收通过）。

## 10. 本批登记的产品与机制发现（不隐藏）

| 发现 | 层次 | 处置 |
|---|---|---|
| 原生 1654 在同一表单把 `withholding_amount` 呈现两次（`抵扣金额与税额` + `扣款办理`） | P1 产品结构 | **本批已修**：保留在 `抵扣金额与税额`，`扣款办理` 不再重复；L2 用 `SINGLE_PRESENTATION_FACTS` 断言「同一表单内一次呈现」 |
| `smart_core/app_config_engine/services/view_Parser/base.py:102` 用 `not xml_content` 判断入参，而该函数同时接受 lxml Element（第 104 行 `else xml_content`）；lxml 对 Element 的真值语义已废弃（相邻调用点 `contract_Parser.py:109`、`parsers Tree Form.py:698` 都以 Element 传入） | P0 机制 | **登记不改**（改 `smart_core` 超出本批边界）。当前不可观测：真实 form arch 必有子节点，故不会退化为 `{}`；仅对**无子节点**的元素会静默返回 `{}` 并抛 `FutureWarning`。属潜在健壮性缺口，需 P0 单独决定 |
| 本批新增测试首版用 `arch_fields.get(name) or {}` 读 lxml 元素，触发同一条 `FutureWarning`，且对无子节点的字段会读错可见性 | P4 本批引入 | **本批已修**：改为显式 `is not None`，并把断言提升为行为断言（声明事实恰好呈现一次 + 隐藏必须是消费层可见性而非静默移除） |
| `scripts/verify/view_orchestration_product_boundary_guard.py` 的 `ALLOWED_COMPOSITION_MODES` 不含 `native_semantic_surface`，且只在「form 带 `fields`」时才要求允许模式 —— 缺一条「`native_semantic_surface` 必须无 `sections/fields/columns`」的正向校验 | P0/P4 共享守卫 | **登记不改**。该守卫实跑 `FAIL`（exit 2），5 条错误全部指向本批**未改**的契约（`tender_bid` P1 事实、`payment_request` P1 事实、`policy_document_form_v1`、`tender_bid_registration_productized_form_v1`、`tender_bid_registration_form_structure_v1`）；守卫文件与这 5 个输入都不在本批 9 个路径内，故**预先存在、非本批引入**。本批两条退役契约因已删 `fields` 而通过该守卫。该守卫未纳入 `ci.local.quick.run` 与 `pr.push`，不影响本候选的 Quick。是否补正向校验属 P0/P4 单独决定 |

## 11. 身份与冻结口径

本记录按「日迭代 ＝ HEAD ＋ 显式 dirty 范围」书写。按阶段证据规则，**冻结值不写入本文件**：本文件在冻结
候选内，写入冻结取值会改变候选自身的 commit hash，故冻结候选身份的取值只出现在冻结步骤生成的产物与外部
归档（`identity.json`／`worktree-fingerprint.json`／`review.json`）中。

| 阶段 | 身份 | 取值方式 |
|---|---|---|
| 迭代期（§1–§8 书写时） | `HEAD=5b10410663c9c5ceac7678aaaff66379000e2226`（tree `5fb43ba0e2cc9b9c0aa99b70b773aeff2e18985f`） | 实现提交完成后的身份；L1（`changedPathCount=6`）／L2（7 用例）／L3（78 modules）／L4（只读代表面）即在此身份上执行 |
| L2 收口（§4 口径：L2 在 dirty 收口后重跑） | 同上 ＋ dirty `{tests/test_tax_deduction_native_lowcode.py}` | L2 回执与其输入（新增测试文件）一致 |
| 独立复核 | 同上 ＋ dirty `{tests/…, docs/…×2}` | 结论 **APPROVE**，无 blocker／major；3 项 minor 与 5 项 nit 见总记录 §8.25 与本文件 §10 |
| 复核修正提交 | `4402b4aa91192852010f246a66cc339b68e85c91`（tree `781f81f18b88f50037f3cec03ff437d9256f36e5`） | 只含上述 3 个路径（1 个 P4 验证测试 + 2 份记录），`git diff --name-only` 可核；**不改产品运行路径**（测试文件属 P4 验证范围） |
| 记录口径提交 → 冻结 | 由冻结步骤前的最后一次记录提交产生 | `make ci.delivery.freeze.prepare` → `python3 scripts/contract/complete_worktree_fingerprint.py --baseline daf9a97875a15343671c00e46fd9c4e639ebeca2` → `make ci.local.quick`（exact-head，一次）→ 独立复核绑定同一指纹与回执 |
| 冻结候选复核 | 绑定冻结指纹 ＋ exact-head Quick 回执 | 结论与回执随归档 `review.json` 记录（本文件不含该取值） |

**复用与被取代的口径**：L1／L2／L2 相邻／L3／L4 的输入是本批 9 个路径内的产品与工具文件，复核修正提交只动
2 份记录与 1 个新增测试文件——按「文档变更不作废页面证据、测试工具变更只作废依赖该变更的执行」的规则，
L3／L4 页面证据不因此重跑，L2 已按上表在 dirty 收口后重跑取回执；冻结身份在最后一次记录提交上重走一次
（完整指纹 ＋ exact-head Quick ＋ 复核绑定同一指纹）。

**L4 报告身份的口径**：报告内 `candidate=daf9a97875a15343671c00e46fd9c4e639ebeca2`（**基线 head**）＋
`dirty=true` —— runner 记录的是「基线 head ＋ 存在未提交改动」，既不是本批实现 head，**也不是**冻结候选的
证明；冻结候选身份只认「干净 HEAD ＋ 完整指纹 ＋ exact-head Quick 回执」三件套，报告与截图在归档中作为
该次运行的页面证据与其它角色文件一同绑定同一 `candidateHead`。

### 11.1 冻结候选独立复核（只读）

| 项 | 值 |
|---|---|
| 复核候选 | `08cf715159bdb10265affb9aee2bb7db8ed9ff7b`（tree `9f57d4c5…`，干净工作树） |
| 绑定身份 | 完整指纹 digest `f9f529fb923f3e592b9804d0c2112c8f969bda01bf9e88038890589d0a7536b0`（7511 路径）＋ exact-head Quick 回执 sha256 `203ae4f4ddb284d783c7e6c3c5d918349ecfdbe3e55189a4d71369be630a489d` |
| 结论 | **APPROVE**；0 blocker、0 major、4 minor、3 nit（**全部为记录口径，无产品行为项**） |
| 独立复现 | `HEAD`／`HEAD^{tree}`／branch／空 `git status --porcelain`；重算指纹 digest 与路径数**完全一致**；Quick 回执 `head`／`tree`／sha256 一致；delta 恰为声明的 9 路径、无未声明路径；`addons/smart_core/**` 未改、无 ACL／groups／ir.rule／domain 改动、台账仍 31 |
| 独立核对 | 退役声明过的 39（790）／28（879）个事实在 arch 中全部存在、只读限制全部还原、`withholding_amount` 全表单仅 1 次；写／恢复边界成立（`cleanup_guard=proceed`、`foreign=[]`、`released=true`、`draft_tokens_held=0`、无发布／回滚），受保护 change set 163/190/192/194/233/267/274/276 写日期仍为 2026-09-17、当日无新建 change set |

复核提出的 7 项（4 minor + 3 nit）**全部为记录口径**，已在本次记录口径提交闭合：
① 本文件头部状态行与 §9 不一致 → 统一为「批次验收完成（本批范围，冻结链见 §11）」；
② §11 原把 L4 报告的 `candidate` 写成实现 head → 更正为实测值「基线 `daf9a978` ＋ `dirty=true`」；
③ 复核候选「clean 工作树 ＋ digest `f54cf06e…`」与「＋dirty」两处口径并存 → 明确 `f54cf06e…` 绑定**已被取代**的
候选 `5b104106` 的干净工作树，在当前冻结候选上不可复现（指纹按定义绑定某一具体树状态，属预期）；
④ 总记录 §8.25 相邻用例仍写「沿用既有回执」→ 更正为实跑 `0 failed, 0 error(s) of 2 tests`；
⑤ 新增测试行数「486」→ 实测 **492**；
⑥ 关于 `readonly` 条件守卫的 nit：`assertTrue(modifiers.readonly)` 确实也接受无条件 `readonly="1"`，但该情形会被
同批 `test_recovered_facts_keep_their_declared_readonly_behaviour` 的 `policy.readonly is False`（790 创建面）
拦下 → 行为仍被锁定；不改代码，仅记录该推理；
⑦ 「无产品运行路径改动」表述不精确 → 更正为「3 个路径中 1 个为 P4 验证测试、2 份记录，不改产品运行路径」。

复核另记 1 项 `inconclusive`：**本轮之前**（候选 `5b104106`）那轮复核的结论与其指纹 digest 无法从 tracked
证据验证 —— 该轮只在记录文字中留痕、未归档；本轮回执随本文档同批产物 `review.json` 外部归档。

本次记录口径提交为 docs-only，产品与测试行为未变，故上表结论继续适用；冻结身份在本提交上重走一次
（完整指纹 ＋ exact-head Quick 一次），其取值仍只写入冻结产物与外部归档。

### 11.2 冻结身份被定时 CI 处置提交取代（2026-09-18，后记）

本轮 G06 冻结候选 `fad9a110`（tree `…`／完整指纹 `e4e6efb5…`／Quick 回执／外部归档回执）在**产出时点有效**，
其归档与回执**未被改写**。但其后按用户指令「定时 ci 有失败先处理了」新增了 CI 门禁修复提交（见总记录 §8.26），
故 `fad9a110` **不再是最终交付候选**；其冻结链（完整指纹 ＋ exact-head Quick ＋ 独立复核）需在**新的最终提交**
上重走一次，第二次取值同样只写入冻结产物与外部归档，不写入记录文件（写入会改变候选自身 commit hash）。
本批记录中的「冻结候选」表述一律以总记录 §8.26.7 的状态为准。

## 12. G06 整改回环 R1（2026-09-18 12:04）：L4 `invoice_date` 归因与测量口径修复

身份：HEAD `7b792729f67c17be8d8e5e483df8b027b65d752d` ＋ 未提交 dirty 范围（**阶段身份，非冻结身份；未冻结**）。
本节只追加，不改写 §1–§11 的既有结论；§11.2 关于冻结候选被 CI 处置提交取代的结论继续有效。

### 12.1 接管范围与唯一写入者

本轮回环开始时工作树已带未提交改动（上一轮执行器所写），本轮在其上**继续**推进，不覆盖、不重做。
工作树/分支的唯一写入者是本执行器；`git worktree list` 的另外 3 条为**登记但非活跃**的历史工作树
（`…-contract-work-reading-efficiency-v1`、`…-material-handling-v1`、`…-material-handling-v1-uc2-material-native-v1`），
本轮**未进入、未修改、未清理**，不参与本批预算判定。

| # | 路径 | 来源 | 本轮处理 | 层 |
|---|---|---|---|---|
| 1 | `addons/smart_construction_core/data/p1_daily_business_form_orchestration_contract_data.xml` | 接管前已有 ＋ **接管后续改**（本轮唯一内容即 `active=True → False`＋退役注释） | id=5 退役 | P1 |
| 2 | `addons/smart_construction_core/tests/test_tax_deduction_native_lowcode.py` | 接管前已有 ＋ **接管后续改** | 退休层事实保全与创建面可填性测试 | P4 |
| 3 | `addons/smart_construction_core/data/tax_deduction_certificate_form_productization_contract.xml` | 接管前已有 ＋ **接管后续改** | id=5 退役的声明侧注释 | P1 |
| 4 | `scripts/verify/local_dev_form_lowcode_scope.py` | 接管前已有 ＋ **接管后续改** | `required_fillable` 判据注释 | P4 |
| 5 | `frontend/apps/web/scripts/formal_form_representative_journey.mjs` | 接管前已有 ＋ **接管后续改** | 失败诊断＋章节导航三相测量（接管前）／**本轮：picker 触发器的可填口径＋可达性断言** | P4 |
| 6 | `addons/smart_core/core/lowcode_presentable_fields.py`（新文件） | 接管前新增 | 未改 | P0 |
| 7 | `addons/smart_core/core/view_orchestrator.py` | 接管前已有 | 未改 | P0 |
| 8 | `addons/smart_core/handlers/form_field_configuration.py` | 接管前已有 | 未改 | P0 |
| 9 | `addons/smart_construction_core/models/core/formal_config_contract_fields.py` | 接管前已有 | 未改 | P0 |
| 10 | `addons/smart_construction_core/views/core/tax_deduction_registration_views.xml` | 接管前已有 | 未改 | P1 |
| 11 | `addons/smart_construction_core/tests/test_form_structure_consumption.py` | 接管前已有 | 未改 | P4 |
| 12 | `frontend/apps/web/src/components/template/FormSection.vue` | 接管前已有 | 未改 | P0 |
| 13 | `frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue` | 接管前已有 | 未改 | P0 |
| 14 | `frontend/apps/web/src/pages/ListPage.vue` | 接管前已有 | 未改 | P0 |
| 15 | `frontend/apps/web/src/views/ActionView.vue` | 接管前已有 ＋ **后在提交 `d14020bb` 由本批修改**（口径见 §12.11） | 列表内建新建入口不再重复声明 | P0 |
| 16 | `frontend/apps/web/src/app/presentation/collectionEmptyStatePresentation.ts`（新文件） | 接管前新增 | 未改 | P0 |
| 17 | `frontend/apps/web/scripts/collection_view_semantics_test.ts` | 接管前已有 | 未改 | P4 |
| 18 | 本文件 ＋ 总记录 §8.27 | **接管后修改** | 本节与总记录 | 记录 |

**仅验证、未修改**：模型级配置 143／5／129、旁路入口 852、受保护草稿
163／190／192／194／233／267／274／276；`/tmp` 与 `tmp/g06-remediation/**` 下的只读诊断脚本全部在进程外，不进入提交。

同文件内混有两个来源的改动，按内容区分（不按文件粒度声称）：
`tax_deduction_certificate_form_productization_contract.xml` 的附件副本取舍注释、
`test_tax_deduction_native_lowcode.py` 的既有用例调整、`local_dev_form_lowcode_scope.py` 的 topic 注册与
`formal_form_representative_journey.mjs` 的失败诊断＋章节导航三相测量属**接管前已有**；
id=5 退役声明与其事实保全测试、picker 可填口径与可达性断言属**接管后修改**。

### 12.2 L4 失败归因：`invoice_date` 是**测量口径**缺陷，不是渲染失败、不是定位失败

上一轮 L4 唯一剩余红灯为 790 创建面 `invoice_date`（判据：交付策略要求必填且可编辑，却量不到可编辑控件）。
本轮先用两个有界只读实验把它归到唯一一类，再改工具，**未延长超时、未放宽断言**：

| 假设 | 实验 | 观察 | 判定 |
|---|---|---|---|
| 渲染失败（控件未生成／被 disabled／被 readonly 门控） | 790 创建面 `[data-field-name="invoice_date"]` 的 DOM 转储 | 存在 `<input class="t-input__inner" type="text" readonly>`，`disabled=false`，宿主 `[data-semantic-component="ScDateField"][data-semantic-driver="tdesign-date-picker"]`；节点带 `data-field-state="required"`、`data-field-auth="edit"`、可见标签「开票日期 *」 | **不成立** |
| 定位失败（节点不在树里／不可见） | 同上 ＋ 契约只读探针 `probe_invoice_date.py` | 节点在 `containerTree` 唯一出现于 `/sheet.native.1/deduction_invoice_info`，`node.readonly=False`、`policy={visible:true,readonly:false,required:true,auth:'edit'}`；DOM 中 `rendered=true` | **不成立** |
| 测量口径（触发器内层 input 依设计 `readonly`，被 `:not([readonly])` 计成 0） | 点击触发器 ＋ 选区 | 点击后日期面板出现（2 个 popup），点选单元格后输入框值变为 `2026-08-31`，`field--empty` 类消失 | **成立** |

同页 `document_date`、`deduction_confirm_date` 与 `invoice_date` 同形（均为 `picker=1 / editable=0`），
只因不在必填集合内才未触发断言——这佐证归因是**口径**而非某个字段的偶发渲染。

### 12.3 实际修复（P4 验证工具层，一层）

`frontend/apps/web/scripts/formal_form_representative_journey.mjs`：

1. 新增 `PICKER_CONTROL = '[data-semantic-driver$="-picker"]:not(.t-is-disabled) input:not([disabled])'`，
   与既有 `EDITABLE_CONTROL` 并列，作为「交付面的第二种可填形态」；只有触发器宿主未禁用且 input 未 `disabled` 才计数。
2. 快照把两个选择器**作为参数**传入 `page.evaluate`（消除浏览器内重复的字面量），每字段同时产出 `editable` 与 `picker`；
   `record()` 对两者各取 `Math.max`。
3. `assertRequiredFactsAreFillable` 以 `fillable = editable + picker` 判定矛盾，并在观测里分别保留 `editable`／`picker`／`fillable`，
   使「为什么算可填」可归因；返回仅靠 picker 计数的字段名。
4. 新增 `assertPickerTriggersAreReachable`：对上述字段断言触发器存在、可见并**能取得焦点**，
   使放宽后的口径不能成为隐藏/惰性控件的普遍豁免。
5. `assertReadonlyValues` 同步**收紧**：只读事实必须既无原生可编辑控件、也无可用的 picker 触发器（`editable === 0 && picker === 0`）。

### 12.4 分层验证结果（实际执行）

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | **PASS** 16 tests OK；`changedPathCount=29`、`change_state=dirty coverage=L1_only receipt=none` |
| L2（前端映射面） | `verify.frontend.canonical_form_presenter.unit`（170 cases）／`page_pattern_reference_parity.unit`（surfaces=15）／`primitive_adapter.unit`（46 组件／9 事件用例，31 tests OK）／`product_page_pattern.unit`（12 cases，5 tests OK） | 4/4 **PASS**，均非零 |
| L2（共享结构机制） | `verify.frontend.native_form_structure_responsibility.unit` | **PASS** `cases=10`（空 header／无标题包装组／隐藏子节点／非空页签与明细／嵌套分隔线／正文与导航一致） |
| L2（后端结构消费） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestFormStructureConsumption'` | **PASS** `0 failed, 0 error(s) of 6 tests` |
| L2（本主题用例） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestTaxDeductionNativeLowcode'` | **PASS** `0 failed, 0 error(s) of 10 tests`（含 id=5 退役后的事实保全与创建面可填性） |
| L2（列表空态能力） | `verify.frontend.collection_view_semantics.unit` | **PASS**（`collection-view-semantics` ＋ 34 tests ＋ guard，非零） |
| L4（本主题） | `FORM_LOWCODE_TOPIC=tax_deduction FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | **PASS** exit 0；`ok=true restored=true browser_errors=[] transport_recoveries=[]`；`cleanup_guard=decision:proceed foreign=[]`；`recovery_state={draft_tokens_held:0, rollback_tokens_pending:0, released:true}`；`business fingerprints unchanged` |
| L4（受影响只读面 · contract） | `FORM_LOWCODE_TOPIC=contract …` | **PASS** exit 0（`readonly_values` 主题，验证收紧后的只读守卫无回归） |
| L4（受影响只读面 · settlement） | `FORM_LOWCODE_TOPIC=settlement …` | **PASS** exit 0（同上） |

未执行：L3 模块升级**本轮未重跑**——本轮只改了前端验证工具（`.mjs`）与文档，
未触及 `addons/**` 与运行时代码，前一轮 `0 failed, 0 error(s) of 10 tests` 与 78 模块升级结果按其输入未变而沿用。
未跑 Quick、未推送、未冻结。

### 12.5 代表面结果（本轮实测，绑定本阶段身份）

| 入口 | 路由 | 结果 |
|---|---|---|
| 790（抵扣登记） | create | **PASS** 28 字段／7 章节；必填事实 8 项，可编辑项全部 `fillable=1`；`invoice_date` 记为 `editable=0 picker=1 fillable=1` |
| 790 | record | **PASS** 只读呈现（`presentation_mode=readonly`）；`attachment_ids` 按 `readonlyFactIsPresentable` 规则省略（见 12.6 候选②） |
| 879（项目专项抵扣） | create | **PASS** 28 字段／7 章节；`deduction_confirm_date` 由 picker 计数并通过可达性断言 |
| 879 | list | **PASS** `collection_state=empty`、`create_entry_available=true`，空态文案为「当前还没有数据 可以先新建一条业务记录…」，**不再出现「没有新建权限」** |
| 879 | record | **未覆盖**：`empty_action_domain`（`domain_rows=0`、`business_row_count=1`），无同类可读样本，保持未执行 |

#### 12.5.1 章节导航／吸顶坐标（按阶段重测，同一稳定态内取三个矩形）

**口径纠正**：早先并列出现的 `nav 347–400` 与 `nav.bottom 347` 分属**不同阶段**
（前者是未激活的静止态、后者是激活后的吸顶态），并列书写会被误读成互相矛盾；
下表按阶段分行，每行的三个矩形都在**同一稳定态**内同时测量。

| 入口 | 视口 | 阶段（稳定态） | 操作行 actions | 章节导航 nav | 目标 target.top | 判定 |
|---|---|---|---|---|---|---|
| 790 create | 1088×900 | 静止（未激活） | `191–221` | `263–302` | — | 操作行 → 导航 → 正文顺序成立，分离 42px |
| 790 create | 1088×900 | 激活后（吸顶） | `175–205` | `218–257` | 首项 `269`／末项 `576` | `target.top ≥ nav.bottom`，互不遮挡 |
| 790 create | 390×844 | 静止（未激活） | `263–293` | `347–400` | — | 正文自 `400` 起，顺序成立 |
| 790 create | 390×844 | 激活末项后（吸顶） | `251–281` | `294–347` | `464` | 目标落在导航下方 |
| 790 create | 390×844 | 再激活首项（反向回跳） | `251–281` | `294–347` | `359` | 反向回跳同样把目标送进吸顶带下方 |
| 790 create | 390×844 | 手动滚动后激活中项 | `251–281` | `294–347` | `359` | 从非导航产生的静止位激活仍成立 |
| 879 create | 1088×900 | 静止（未激活） | `191–221` | `263–302` | — | 与 790 同形 |
| 879 create | 1088×900 | 激活后（吸顶） | `175–205` | `218–257` | 首项 `269`／末项 `576` | 同 790 |
| 879 create | 390×844 | 静止（未激活） | `263–293` | `347–400` | — | 同 790 |
| 879 create | 390×844 | 激活后（吸顶） | `251–281` | `294–347` | 首项 `359`／末项 `464` | 首尾双向通过 |

导航元素是 `[data-form-section-navigation]`（`FormSectionNavigation.vue`，**不是** `form-section-nav-shell`：
后者属 `ContractFormNativeCanvas.vue` 的设计器画布，790／879 创建面不渲染它）。
790／879 创建面均渲染 **7 个** `[data-section-target]`（`业务方向／项目与往来单位／发票信息／抵扣金额与税额／
扣款办理／办理说明与附件／协作记录`）；390 视口横向轨道 `scrollWidth 566 / clientWidth 237`，
末项激活后 `scrollLeft 329`、点回首项回 `0`；两个入口 `scrollWidth - innerWidth = 0`，无根页面横向溢出。
证据：`tmp/g06-remediation/probe-closure.out`（只读）。

截图同时显示 `单据附件`（随当前单据保存）与 `协作附件`（随沟通与协作记录上传）各自独立成组，
正文内不再出现 `Attachment Count`，也无重复的「附件 —」。

### 12.6 本轮登记（候选，不登记为缺陷、不批量改字段）

- **候选①（P0 呈现口径，跨主题）｜本批已关闭**：可编辑日期事实的控件是 TDesign 日期选择器，其触发器内层 `input` 依设计带 `readonly`。
  任何只统计「非 readonly 原生输入」的测量都会把它计成 0。本轮在代表面判据内闭合；
  同类选择器还出现在 `formal_form_invoice_journey.mjs`（仅用于只读事实要求 0 与 `note` 要求 >0，
  经核对**不产生**日期必填的假阳性）、`local_dev_project_profile_write_browser.mjs`（用于交互填充，非断言）、
  `frontend_scene_component_driver_readonly_browser.mjs`（只读驱动要求 0，严格口径正确）。
  三者**本轮均未修改**；若后续新增「必填日期」断言，须复用本口径。
  关闭依据是**行为证据而非控件类型**：日期触发器可打开、可在面板中点选（§12.5 前的日期测量项），
  因此「可填写」成立，本项不再作为缺口。
- **候选②（P0 呈现口径）**：只读呈现下空值的 `many2many`（790 记录态 `attachment_ids`）被
  `readonlyFactIsPresentable` 省略，而 `FormSection.vue` 已具备 `field--readonly-empty-relation` 渲染支撑，
  两层对「空只读关系集合是否保留入口」的判断不一致。归因规则已随 L4 报告记录（`readonly_fact_omitted`），
  本轮**只登记不改**：是否要求空只读关系集合保留入口属产品判断，且影响所有主题，超出本批代表面。
- **候选③（P1 字段职责，已给结论）**：`partner_name`（历史往来单位）与 `partner_id`（往来单位）是**独立存储事实**，
  不因文本相同而删除（已实测：`partner_name` 为独立 `char` 字段，记录态有值渲染）。
  创建面上它是 `visible=true / readonly=true / auth=read` 且值为空，渲染为 `field--empty` 的只读事实（显示「-」），
  因为**可写呈现**（`preferReadonlyFacts=false`）保留只读事实、**只读呈现**才应用空值省略规则。
  与用户「新建页空历史字段应评估退出主办理区」一致，属**呈现取舍**而非策略消费错误，本轮**只登记不改**；
  `creator_name`／`created_time`／`source_created_by`／`source_created_at` 已由交付策略 `visible=false` 合法隐藏（实测未渲染），无需处理。

- **候选④（P1 声明层，**本批已收口**）**：790／879 的 action context 声明了
  `default_business_category_code`（`tax.deduction.registration` / `tax.deduction.project_special`），
  但创建面 `business_category_id`（业务分类，**必填**）抵达时为空。
  **首次偏差已定位在 P1 声明层**：`tax_deduction_registration.default_get` 未像同类入口
  （`settlement_order.py`、`payment_request.py`、`expense_claim.py`）那样把 action context 的
  `default_business_category_code` 解析成 `business_category_id`；保存侧
  `create() → _resolve_business_category_id()` 本来就正确。**修复见 §12.8**，本项不再是缺口。
- **候选⑤（P1 派生事实，保存前生成条件已明确）**：`deduction_flow_label`（办理事项）是
  `store=False` 计算字段，创建面 `readonly=true`，保存前渲染为「-」。
  **生成条件**（`_compute_deduction_flow_label`，按优先级）：`deduction_scope == 'project_special'` → `项目专项抵扣`；
  `is_transfer_out` → `进项税额转出`；`withholding_amount` → `扣款抵扣`；
  `deduction_tax_amount` 或 `deduction_amount` → `进项税额抵扣`；否则 `抵扣登记`。
  **首次偏差**：`default_get`（创建面水合入口）不返回该非存储计算字段——同一组默认值经 `new()` 已算出
  `抵扣登记`／`项目专项抵扣`（只读探针 `probe_flow_label.py`）。
  **前端未拼造**：创建面渲染的是契约里的空值「-」，符合「尚未产生」语义，未做客户端推导。
  **本轮不加默认值**：该字段取决于用户尚未录入的金额（`进项税额抵扣`／`扣款抵扣`），
  若在创建时静态水合一个值，录入金额后没有 onchange 会停留在陈旧值，比「-」更误导；
  若产品要求保存前即显示，须由后端默认值/onchange 提供，前端不得拼造。

### 12.7 未执行项（保持未执行）

- 未冻结、未跑 `make ci.local.quick`、未推送、未建 PR、未合并、未部署；未启动 G07。
- 未重跑全部代表面主题，只补本轮受影响面（tax_deduction ＋ `readonly_values` 的 contract／settlement）。
- 未 `sync_demo`／fixture reset／发布快照／无关 upgrade；未停启历史容器、未调整 Docker 网络、未清理历史工作树。
- 未触碰受保护草稿 163／190／192／194／233／267／274／276；879 记录态仍未覆盖。
- 台账保持 **31**；约 6 组副本候选继续留台账，不扩大登记范围。
- 未执行真实保存／上传／确认／发布与状态流转；**未持久化业务或配置写入**，未消费既有草稿。
  （口径纠正：日期点选是未保存的表单交互，不是「未做任何写操作」。）

第 7 轮结束时状态（**已被 §12.8 取代**）：G06 整改中｜未集成｜未部署｜89 入口用户验收未完成。

---

## 12.8 第 8 轮接管：入口分类与默认值收口、共享修复边界、空值表达结论（2026-09-18）

### 12.8.1 身份与写入归属（唯一写入者 = 本轮执行器）

- HEAD `7b792729f67c17be8d8e5e483df8b027b65d752d`（已推送）；分支 `feature/uc4-tax-deduction-native-v1`；
  工作树 **dirty**：`M` 18 ＋ `??` 2（合并后计入单一指纹时须整体声明，**本轮未冻结**）。
- 归属三分（禁止把三种口径混为一句「只写了批次记录」）：

| 归属 | 文件 |
|---|---|
| **接管前已有**（本批前几轮写入，本轮未改） | 15 个 `M`：两份本批记录、`p1_daily_business_form_orchestration_contract_data.xml`、`tax_deduction_certificate_form_productization_contract.xml`、`formal_config_contract_fields.py`、`tax_deduction_registration_views.xml`、`view_orchestrator.py`、`form_field_configuration.py`、`collection_view_semantics_test.ts`、`formal_form_representative_journey.mjs`、`ProfessionalBaseFieldControl.vue`、`FormSection.vue`、`ListPage.vue`、`ActionView.vue`、`local_dev_form_lowcode_scope.py`；＋`??` 2：`lowcode_presentable_fields.py`、`collectionEmptyStatePresentation.ts` |
| **接管后修改**（本轮唯一写入） | `tax_deduction_registration.py`（P1 声明，11 行）、`test_tax_deduction_native_lowcode.py`（＋5 例）、`test_form_structure_consumption.py`（＋2 例，含同类入口与无默认分类反例）；另：本记录 §12.5／§12.6／§12.7／§12.8 与 `form_structure_consumption_stabilization_20260917.md` §8.28 |
| **仅验证**（未写入） | 790／879 创建与查看、879 列表、章节导航、日期控件、候选分类、`tmp/g06-remediation/**` 只读探针 |

### 12.8.2 首次偏差与根因（两个）

1. **P1 声明缺失（产品根因）**：`tax_deduction_registration.default_get` 未把 action context 的
   `default_business_category_code` 解析成 `business_category_id`，而同类入口
   （`settlement_order.py:1129-1132`、`payment_request.py:1958`、`expense_claim.py:633`）都已解析；
   保存侧 `create() → _resolve_business_category_id()` 本就正确。→ 创建面显示空必填项，保存后却带值，
   两次观察都自洽，唯一断点是**声明层**。
2. **运行期装载陈旧（环境根因）**：受管容器 `sc-local-dev-odoo-1` 以 `/usr/bin/odoo -c …` 运行（无 `--dev=reload`），
   启动时间早于模块改动，故修复前 HTTP 契约缺 `business_category_id` 而直接 handler 却返回 50——
   说明**执行的是旧模块代码**。`make local.dev.restart`（compose `up -d --force-recreate odoo`，
   `addons` 挂载到 `/mnt/source-addons`）后即正常；**未执行** `local.dev.upgrade`（无必要）。

### 12.8.3 实际改动（P1 声明层，不写特判、不铺开）

- `default_get` 中 `return res` 前补：若字段清单含 `business_category_id` 且尚未水合，
  则用 `create()` 同一个权威 `_resolve_business_category_id(res)` 解析，解析不到就不猜。
- **未改 P0**：`view_orchestrator.py`／`form_field_configuration.py`／编译器与共享水合层本轮无新增写入
  （它们的 dirty 属接管前已有）。**未写抵扣模型特判**，**未在其他入口铺开**。
- 测试补在共享机制用例集与主题用例集：同类入口（结算单收／支两个 action ＋ 抵扣登记两个 action，共 4 个 action／2 个模型）
  必须同样把声明送到创建面；声明了但数据里不存在的 code **不得被替代**（无默认分类反例）。

### 12.8.4 分层验证结果（实际执行）

| 层 | 入口 | 结果 | 证据 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | **PASS** `change_state=dirty coverage=L1_only receipt=none`（`changedPathCount=30`） | 本轮改文档后重跑：`tmp/g06-remediation/l1-iteration-r2.log` |
| L2（本主题） | `make local.dev.test MODULE=smart_construction_core TEST_TAGS="uc4_native_lowcode"` | **PASS** `0 failed, 0 error(s) of 45 tests` | `tmp/g06-remediation/l2-entry-category-4.log` |
| L2（共享结构消费） | 同上 `TEST_TAGS="/smart_construction_core:TestFormStructureConsumption"` | **PASS** `0 failed, 0 error(s) of 8 tests`（接管前为 6，本轮＋2） | `l2-form-structure-consumption-after.log` |
| 只读探针（后端） | `odoo_shell_exec` `probe_flow_label.py`／`probe_save_validation.py`／`probe_partner_name_origin.py` | **PASS**，见 §12.8.5／§12.8.6 | `probe-flow-label.out` 等 |
| 运行期 | `make local.dev.restart` | 容器二进制与启动时间已刷新、`health=healthy`、`db=sc_dev_demo` | — |

失败分类：`l2-entry-category-3.log` 的 1 failed 是**测试自身入参类型错误**（browse record 传给了只接受字符串的辅助函数），
修正后复跑通过；**不是**产品缺陷，也未通过放宽断言取得通过。

### 12.8.5 代表面结果（本轮实测，绑定本阶段身份）

| 入口／路由 | 结果 |
|---|---|
| 790 create @1440 | **PASS** 28 字段／7 章节、`dupes=[]`；`业务分类 抵扣登记`（`field--widget-select`，`*必填`）、`抵扣范围 普通税额抵扣`、`扣款事由 抵扣登记`（标签持续可见，placeholder「请输入扣款事由」） |
| 879 create @1440 | **PASS** 28 字段／7 章节、`dupes=[]`；`业务分类 项目专项抵扣`、`抵扣范围 项目专项抵扣`、`扣款事由 项目专项抵扣`；该入口分类字段按视图声明为只读（`deduction_scope == 'project_special'`），用户无法越界选择 |
| 790 record/1 @1440 | **PASS** 只读呈现（无保存按钮）；`业务分类 抵扣登记`、`办理事项 进项税额抵扣`；25 字段节点、`dupes=[]`；无 `Attachment Count` |
| 879 list（受管路由 `/a/879?menu_id=701`） | **PASS** `collection_state=empty`；空态文案「当前还没有数据 可以先新建一条业务记录，开始录入和办理。」；`create_entry_available=true`；**不再出现「没有新建权限」** |
| 879 record | **未覆盖**（`empty_action_domain`：`domain_rows=0`）；不为补证据制造数据 |

**分类选择（三层证明「不能静默保存到入口范围外的分类」）**：

1. **候选范围**：790 打开候选时发出 `sc.business.category` 的 `list`，域为
   `[["code","in",["tax.deduction.registration"]],["target_model","=","sc.tax.deduction.registration"]]`，
   `count=1`、`codes=["tax.deduction.registration"]`；「搜索更多」弹窗仅 1 行「抵扣登记」。
2. **入口政策**：879 的业务分类字段是只读的单值（`项目专项抵扣`），无候选可选。
3. **保存校验**：在 790 context 下提交越界分类 → `ValidationError: 项目专项抵扣业务分类只能用于项目专项抵扣范围。`，**未创建**；
   同 context 提交本入口分类 → 创建成功（`flow_label=进项税额抵扣`、`state=draft`），
   证明守卫是**入口范围内的定向拒绝**而非一刀切；两次均 `env.cr.rollback()`，
   持久化记录数 `1 → 1`，**零持久化**。

### 12.8.6 空值表达：核对结论（本批不改代码）

1. **历史往来单位保留独立事实**：`partner_name` 是独立 `char` 存储事实，**不按重复文本删除**。
   它并非只服务历史导入：由入口 context `default_partner_name` 水合
   （`tax_deduction_registration.py:311-313`；来源入口如 `finance_business_fact`、`ar_ap_project_summary`、
   `finance_project_counterparty_position`、`company_contractor_responsibility_context_mixin`），
   且只读探针显示记录 1（`source_origin=manual`，**非 legacy**）就带真实值
   `德阳某某钢材贸易有限公司（示例）`。因此**不能**照搬进项发票的
   `invisible="source_origin != 'legacy'"`——那会在 manual 记录上隐藏真实事实。
   790／879 创建面为空只是这两个入口没有 context 往来单位；按评估结论**保留**，
   与「不得让重复文本冒充可删除」一致。
2. **空附件关系与组件空态职责**：可见性由 `readonlyFactIsPresentable`
   （`!readonly || one2many || !empty || hasAction`）在**呈现形态**上决定，
   组件侧 `FormSection.vue::isReadonlyEmptyRelation`（one2many 看行数、其余关系看已选/已关联）负责已保留关系的空态渲染。
   实测：创建面（可写呈现）保留附件集合并给出上传区；记录态（只读呈现）`attachment_ids` 为空时被省略，
   只有一处 `单据附件`，无 `Attachment Count`、无「附件 —」重复。
   结论：两层职责不矛盾（一层定可见性、一层定已保留关系的渲染），
   唯一未定项仍是 `one2many` 与 `many2many` 的取舍差异——**留候选②，本批不扩大**。
3. **办理事项保存前生成条件**：见候选⑤，首次偏差是 `default_get` 不返回该非存储计算字段，
   前端未拼造；本轮**不加静态默认值**（会因录入金额后无 onchange 而陈旧），改为记录明确条件。

### 12.8.7 口径纠正（本记录同步生效）

- 日期测量以「**可打开、可选择**」为可填写证据（行为证据，不看控件类型）；候选①据此**关闭**。
- `nav 347–400` 与 `nav.bottom 347` 属**不同阶段**（静止态 vs 吸顶态），已按阶段重列为 §12.5.1 的同一稳定态坐标。
- 「未做任何写操作」→「**未持久化业务或配置写入**」；日期点选属未保存的表单交互。
- 879 列表空态在**受管路由** `/a/<action_id>` 上复核通过；此前 `/f/<model>?action_id=…` 的形状不是列表路由，不构成反证。
- 879 记录态继续明确记为**未覆盖**；其余代表面只因本轮改动受影响才补跑。

### 12.8.8 未执行项（保持未执行）

- 未冻结、未跑 `make ci.local.quick`、未推送、未建 PR、未合并、未部署；未启动 G07。
- 未重跑全部代表面矩阵；合同／结算既有证据按输入未变而**复用**（本轮未改其依赖）。
- 未 `sync_demo`／fixture reset／发布快照／无关 upgrade；未停启历史容器、未调整 Docker 网络、未清理历史工作树。
- 未触碰受保护草稿 163／190／192／194／233／267／274／276。
- 台账保持 **31**；约 6 组副本候选继续留台账，不扩大登记范围。

状态：**入口分类与默认值已收口（P1，本批内）｜整改中｜台账 31｜未集成｜未部署｜89 入口交付未完成**。

## 12.9 第 10 轮：窄屏导航与办理事项收口（R5）

### 12.9.1 身份、归属与唯一写入者

| 项 | 事实 |
|---|---|
| HEAD | `7b792729f67c17be8d8e5e483df8b027b65d752d`（未变，未提交、未推送） |
| 分支 | `feature/uc4-tax-deduction-native-v1` |
| dirty | 21 个已跟踪路径 ＋ 2 个未跟踪新增；本轮**只新增 1 个文件的写入**（见下） |
| 唯一写入者 | 本会话执行体。`git worktree list` 中另外 3 条为**登记但非活跃**的历史保留工作树，本轮未触碰，**不等于活跃工作树**，也不作预算违规判定 |

归属分区（区分「接管前已有／接管后修改／仅验证」）：

- **接管前已有（本轮未新增写入）**：`addons/smart_core/core/view_orchestrator.py`、`addons/smart_core/handlers/form_field_configuration.py`、
  `addons/smart_construction_core/models/core/formal_config_contract_fields.py`、两份 P1 契约 data、
  `frontend/apps/web/src/pages/contractForm/FormSectionNavigation.vue`、`.../nativeSectionNavigation.ts`、
  `.../components/template/FormSection.vue`、`.../professional-fields/ProfessionalBaseFieldControl.vue`、
  `.../pages/ListPage.vue`、`.../views/ActionView.vue`、`scripts/verify/local_dev_form_lowcode_scope.py`、
  `.../scripts/native_section_navigation_test.ts`、`.../scripts/collection_view_semantics_test.ts`、
  `addons/smart_core/core/lowcode_presentable_fields.py`（新增未跟踪）。
- **接管后修改（本轮唯一写入）**：`frontend/apps/web/scripts/formal_form_representative_journey.mjs`（§12.9.3，P4 验证工具）。
- **仅验证**：上列全部；本轮**未改动**任何后端产品代码、视图声明或前端渲染代码，因此 §12.8 的 L1／L2／契约证据按输入未变**复用**。
- 未触碰受保护草稿 163／190／192／194／233／267／274／276；**未持久化业务或配置写入**。
  只读回读（`ui.business.config.change.set`，本轮结束）：8 条全部存在且 `write_date` 均为 2026-09-17（**早于本轮全部运行**）；163／194 `discarded`、190／192／274 `superseded`、**233／267／276 仍为 `ready`**，即未发布、未回滚、未删除、内容未变。另：全表 `max(id)=276`、`create_date=2026-09-17 14:47`（总量 68 条），即本轮两项 L4 运行**没有新建任何草稿行**。

### 12.9.2 上轮整改项 → 处理结论 → 证据

| 上轮整改项 | 处理结论 | 对应证据（同一稳定态） |
|---|---|---|
| **879 的 390 窄屏回跳失效**：从「办理说明与附件」点「业务方向」后停在下部，目标标题在视口上方，高亮仍是「扣款办理」 | **已修复并受管复验通过**。首项位于横向可视区外时，「点击前的自动横滚」与「正文定位」不再互相干扰：按下期间不自动滑动轨道，释放仍投递给被按下的条目 | 受管 runner `assertSectionNavigationPressStability`（879 create，390×844）：`last_then_first` → `active=业务方向`、`target_top=359 ≥ nav.bottom=347`、`trackScrollLeft 329→0`；`last_entry_in_view`／`first_then_last` → `active=协作记录`、`target_top=464`、`trackScrollLeft 0→329`；`pressed_after_body_scroll`（手动滚动后再跳）同 `业务方向`359 |
| **办理事项口径**：保存前没有已返回的计算值时隐藏该辅助只读项；后端返回有效值后再显示；不新增静态默认值、不为该项扩展 onchange、不做前端模型特判 | **已收口，落在 P1 模型 compute 属主层 + 既有通用可见性消费**（本条**取代** §12.8.7 中「改为记录明确条件」的临时口径） | 同一次 L4 的落盘字段清单：`879 create`＝27 个字段、含 `deduction_reason`、**不含 `deduction_flow_label`**；`790 create` 同形；`790 record`＝25 个字段、**含 `deduction_flow_label`**（反例对：新建无值即隐藏／已有记录有值即显示）。记录态取值见 §12.5／§12.6 既有探针（`办理事项＝进项税额抵扣`） |

同一稳定态坐标（390×844；来源＝本轮受管 runner 落盘 `observations`，非探针估算）：

| 面／阶段 | 操作行 `product-page-header__actions` | 导航 `[data-form-section-navigation]` | 目标 `targetRect.top` | 重叠 |
|---|---|---|---|---|
| 879 create 静止顶态 | `251–281` | `294–347` | 359（业务方向） | 否（gap 13） |
| 879 create 首项跳转后 | `251–281` | `294–347` | 359 | 否 |
| 879 create 末项跳转后 | `251–281` | `294–347` | 464（协作记录） | 否 |
| 790 record 跳转后 | `279–309` | `322–375` | 387（业务方向） | 否 |
| 1088×900 879 create 跳转后 | `175–205` | `218–257` | 269 | 否（gap 13） |

> `nav 347–400`（静止态）与 `nav.bottom 347`（吸顶态）属**两个阶段**；上表按阶段分读，同一行内三个矩形取自同一稳定态。

### 12.9.3 首次 L4 失败：归因、结论与修复（P4 验证工具，不动产品）

- **首次失败**：`FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` → **exit 2**。
  失败行 `390x844:pressed_while_body_scrolled:协作记录`，`status=wrong_section`、`delivered_active=办理信息`、
  按下期间 `track.scroll_left=341` **未变**；落盘 `artifacts/uc4-invoice-lowcode/browser/representative-report-invoice.json`（`failure_class=product_or_locator`）。
- **首次偏差**：runner 的 `bodyScroll()` 在按住条目的同时先 `page.mouse.move()` 到滚轮位置再 `mouse.wheel()`。
  这在浏览器语义下已是**拖拽**：释放点离开了该条目，click 不派发、激活被取消；而高亮按设计继续跟随正文（`协作记录 → 办理信息`）。
- **归因实验**（`tmp/g06-remediation/probe_nav_step6_attribution.mjs`，只读；两变体各回放步骤 1–5 后进入第 6 步）：
  - 变体 A（runner 手势：按住 → 移动指针 → 滚动）：`duringPress.active=办理信息`、条目几何不变（left 244／top 298）、`track.scroll_left=341` 不变、
    释放后 `active=办理信息` —— **没有任何相邻条目被误激活**。
  - 变体 B（真实按住：`mouse.wheel` 不移动指针）：`duringPress.active=办理信息`、条目几何不变、`track.scroll_left=341` 不变、
    `pointerup`／`click` **均命中 `协作记录`**，释放后 `active=协作记录`、目标 `top=464 ≥ nav.bottom 347`。
  - **结论**：产品行为正确（自动跟随不改动轨道、不误投递）；失败来自**探针手势**，既不是导航缺陷，也不是产品回归。
- **修复（仅验证工具）**：第 6 步改为「滚动不移指针」的真实按住手势，并补反例 6b：同一按住但释放点**故意离开**条目时，必须**什么都不激活**
  （`release_off_entry_activates_nothing`）。6b 自带结论（通过记 `control`，失败记 `activation_survived_a_cancelled_press`／`control_not_armed`），
  既不进失败清单也不计入「已投递章节」——**不以放宽断言换通过**。
- **第二次失败的自身错误**：6b 的「已武装」判据最初对**条目自身坐标**做命中测试（必然命中），已改为对**释放点坐标**做命中测试；
  该次运行该行已记录 `delivered_active=协作记录 === active_when_held`，即控制项行为本身已正确，仅判据错误。
- 重跑依据：**输入已变**（手势与判据改正），非无变化重试。

### 12.9.4 分层验证与代表面 L4 结果（本轮实际执行）

- **L1（本轮重跑）**：`make ci.local.iteration` → **PASS** `change_state=dirty coverage=L1_only receipt=none`（`tmp/g06-remediation/l1-iteration-r10.log`）。
  > 日志中的 `changedPathCount=33` 是**相对基线参考快照**的集合（含本分支既有提交的改动面），与 `git status --short` 的 23 条 dirty（21 已跟踪＋2 未跟踪）**口径不同**，两者不矛盾。
- 说明（措辞）：theme `invoice` 的收尾日志复用 `designerOnly` 分支文案（`PASS formal designer journey`），但本轮 `FORM_LOWCODE_REPRESENTATIVE=1` 走的是**代表面**分支（不打开、不暂存、不发布任何 change set）；结论以 `report.ok && report.restored` 与 `cleanup_guard.decision=proceed`／`foreign=[]`／`recovery=[]` 为准。
- **L2（前端非零，本轮执行）**：`make verify.frontend.native_section_navigation.unit` → **PASS**（`authority=7 next_action=3 content_identity=11 active_tracking=11 structure_consumption=7`，`tmp/g06-remediation/l2-nav-unit-r10.log`）；`make verify.frontend.product_page_pattern.unit` → **PASS**（`5 tests`，`l2-page-pattern-r10.log`）。
- **L2／契约**：本轮未改后端产品代码与视图声明，按输入未变**复用** §12.8 的 L2（`TEST_TAGS="uc4_native_lowcode"` 46 tests、`TestTaxDeductionNativeLowcode` 16 tests）与既有契约落盘证据。

| 主题 | 入口 | 结果 | 说明 |
|---|---|---|---|
| invoice | `FORM_LOWCODE_TOPIC=invoice FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | **PASS** exit 0 | 785／787／786／788 create 全绿；789 与 639 `blocked / NAVIGATION_AUTHORITY_DENIED`（按登记事实记录，既不记为产品缺陷也不记为通过）；`ok=true`、`restored=true` |
| tax_deduction | 同上 `FORM_LOWCODE_TOPIC=tax_deduction` | **PASS** exit 0 | 790 create＋record、879 create 全绿；879 record `UNCOVERED / empty_action_domain`，继续记为**未覆盖**（不为补证据造数据） |

两主题均 `business fingerprints unchanged`（运行前后业务指纹一致）。

### 12.9.5 未执行项（保持未执行）

- 未冻结、未跑 `make ci.local.quick`、未推送、未建 PR、未合并、未部署；未启动 G07。
- 未重跑全矩阵：合同／结算／材料／客户／付款等代表面输入未变，按既有证据**复用**。
- 未 `sync_demo`／fixture reset／发布快照／无关 upgrade；未停启历史容器、未调整 Docker 网络、未清理历史工作树。
- 台账保持 **31**；约 6 组副本候选继续留台账，不扩大登记范围。

状态：**窄屏导航与办理事项已收口并受管复验通过｜整改中｜台账 31｜未集成｜未部署｜89 入口交付未完成**。

## 12.10 第 11 轮：三条导航路径分离复验（正常用户／键盘／自动显露）

本轮**只做有界诊断**，不改办理事项（其口径已于 §12.9 收口），不重跑全矩阵。唯一写入者仍是本会话执行体；
本轮新增写入路径仍只有 `frontend/apps/web/scripts/formal_form_representative_journey.mjs`（P4 验证工具）。

### 12.10.1 复核反馈与结论

复核指出：879／390×844 下「点『办理说明与附件』→ 通过按钮定位点击屏外『业务方向』」失败
（高亮停在别处、首标题 −1516.5px、导航底边 347px），而「先用左箭头显露再点击」通过；
且第一组**没有按住／拖拽／滚轮**，故不能用 §12.9.3 的「拖拽取消 click」归因关闭。

结论（有实测支撑）：**三条路径必须分开判定，且失败只出现在「坐标先于显露」这一类自动化时序上，不是导航缺陷**。
按 §12.9 的既有机制（按下期不自滑 + 正文跟随），产品侧无回归；受管 runner 现已把三条路径**分别登记、分别断言**。

### 12.10.2 三条路径的独立结论（390×844）

| 路径 | 操作 | 结果 | 关键事实 |
|---|---|---|---|
| **正常用户路径** | 点末项 → 用「向前浏览表单章节」显露 → 在显露后的位置真实按下 | **PASS** | §12.9 的 6 个稳定态场景全绿：`last_then_first` → `active=业务方向`、`target_top=359 ≥ nav.bottom=347`、`trackScrollLeft 329→0` |
| **键盘路径** | 聚焦已发布浏览控件 → `Tab`（1 次）→ 屏外首项获得焦点 → `Enter` | **PASS** | `focused_entry=业务方向`、`tabs_to_focus=1`、`delivered_active=业务方向`、`target_top=359`（790 record：387 ≥ 375） |
| **自动显露路径** | 用自动化自身 `scrollIntoViewIfNeeded` 把屏外条目显露后，在**显露之后重新取点**按下 | **PASS** | 按下前条目 `visible_width ≤ 0`（隐藏点 `x=20`／invoice `x=26`，轨道左边界 `69`）；显露后 `left=69`；投递 `业务方向`、`target_top=359`。785／786／787／788 create 同样通过（`办理主信息`、375 ≥ 375） |

三条路径的断言分别落在 `step=first_entry_in_view／pressed_after_body_scroll／last_then_first／first_then_last／
pressed_while_body_scrolled`、`keyboard_activation`、`auto_reveal_press`，**不再合并成一个「导航全绿」**。

### 12.10.3 失败模式的定位证据（区分滚动竞争与投递）

| 实验 | 入口 | 观察 |
|---|---|---|
| 自动显露（正确时序）延迟矩阵 | `probe_nav_autoreveal_race_r6.mjs`：首点后有界延迟 0／60／120／250／500／900ms，再 `locator.click()` | **6/6 PASS**。每次 `pointerdown／pointerup／click` 的 target 与命中点均为 `业务方向`，之后正文滚到该章节（`ownerScrollTop 2125→57`），高亮 `业务方向`、首标题 359 |
| 正常用户与键盘路径对照 | `probe_nav_autoreveal_r6.mjs` | **PASS**：箭头显露后真实按下 = 业务方向／359；键盘 24 次 Tab 到首项后 Enter = 业务方向／359 |
| **坐标先于显露**（负向对照） | `probe_nav_stale_coords_r6.mjs`：隐藏时取点（`press_x=−229`）→ 显露 → 按**旧坐标**派发 | **FAIL（自动化侧）**：实际派发点 `(191,366)`，`pointerdown／up／click` 的 target 全部是 `办理说明与附件`（**另一个条目**），正文未移动（首标题 −1709），稳定高亮 `办理说明与附件`。显露后重新取点（`press_x=100`）则 **PASS** |

- 负向对照复现的正是复核报告的症状类别（**点击落在非目标条目、正文不动、首标题远在视口上方**），
  且事件证据显示产品把按下**正确投递给了指针下的那个条目**——即「投递异常」发生在自动化的取点时序，而非产品事件错投。
- 同时，6 号场景按下期间的 `track.scroll_left` 始终不变（341），说明**不存在按下期轨道自滑**的滚动竞争；
  正文跟随仍按设计更新高亮（`协作记录 → 办理信息`）。
- runner 现将该风险作为**可复核事实**落盘：`hidden_point`、`under_hidden_point`、`stale_point_after_reveal`；
  断言只在「显露后重新取点」的前提下判定投递，避免用放宽断言换通过。

### 12.10.4 本轮实际运行的 L4（仅受影响主题）

| 主题 | 结果 | 证据 |
|---|---|---|
| tax_deduction | **PASS** exit 0（`l4-tax_deduction-r10.log`） | 790 create／790 record／879 create 的 `auto_reveal_press` 与 `keyboard_activation` 全为 `pressed`；879 record 仍 `UNCOVERED/empty_action_domain` |
| invoice | **PASS** exit 0（`l4-invoice-r10.log`） | 785／786／787／788 create 的同上两场景全 `pressed`；789／639 `blocked/NAVIGATION_AUTHORITY_DENIED` |

两主题均 `business fingerprints unchanged`。**未重跑未受影响主题**：`section_navigation_press` 行仅存在于上述两主题的报告，
其余主题报告不含该断言结果，故本轮 runner 改动对其无失效影响。

### 12.10.5 办理事项的当前呈现证据（未改动，仅补图）

`artifacts/lowcode-form-loop/browser/representative-tax_deduction-790-record.png`（本轮 L4 生成）：
已有记录 S70-TAX-001 的「业务方向」区**显示「办理事项 = 进项税额抵扣」**，与 `登记单号／业务分类／抵扣范围` 同列；
新建面同批字段清单仍**不含** `deduction_flow_label`（§12.9.2）。即「新建无值即隐藏／记录有值即显示」两侧证据齐备。

### 12.10.6 未执行项与状态

未冻结、未跑 Quick、未推送、未建 PR、未部署、未启动 G07；未重跑全矩阵；未改办理事项；
未 `sync_demo`／fixture reset／无关 upgrade；未停启历史容器、未改 Docker 网络、未清理历史工作树；
受保护草稿 163／190／192／194／233／267／274／276 未触碰（全表 `max(id)=276`，本轮无新建草稿行）；
**未持久化业务或配置写入**。台账保持 **31**。

状态：**三条导航路径已分离复验（正常用户／键盘／自动显露均通过；失败仅复现于「坐标先于显露」的自动化时序）｜整改中｜台账 31｜未集成｜未部署**。

## 12.11 第 12 轮（R12）：独立复核 REQUEST_CHANGES 的整改（2026-09-18）

本轮只做复核整改，不扩展代表面、不改产品行为。共享机制结论、分层验证与未执行项同总记录 §8.31，此处只记本册专属事实。

### 12.11.1 Major：退役的模型级契约作用于**本模型所有渲染面**，不止「三个入口」

复核结论：**REQUEST_CHANGES**，无 blocker；1 major ＋ 9 minor ＋ 4 nit；四项重点判定（分类约束／只读与空值呈现／共享机制／测试未削弱）**通过**。

Major 属实并已闭合。`sc_tax_deduction_registration_p1_form_business_facts_v1` 四字段（`action_id`／`view_id`／`role_key`／`company_id`）全空，
故它覆盖**该模型全部渲染面**；第 4 个消费者是 `sc.tax.filing.action_open_deductions()`
（正式菜单「税务申报」`menu_sc_product_tax_filing_v1` → 该 action → 申报期抵扣来源），其返回的 action dict 无 `id`、无视图固定，记录页也不带 `action_id`／`view_id`，因此该面**无 action 与 view 作用域**。

实测（`ui.contract` v2，无作用域请求，绑定 view 1654）：

| 项 | 实测值 |
|---|---|
| `resolvedActionId`／`resolvedViewId` | `0` ／ `1654`（`view_sc_tax_deduction_registration_form`，与 790／879 同一正文） |
| `formStructureAuthority`／`formPresentationMode` | `entry_semantic_surface` ／ `task` |
| `businessConfigContracts` | 含模型级 `sc_tax_deduction_registration_form_sections_v1`，**不含**退役体 |
| `sectionTitles` | 9 个模型级旧标题，**不含**退役体的「单据识别／业务对象／金额与办理／附件与来源」 |
| 退役体未渲染的 5 个事实 | 均为 `compute+store+readonly` 投影，保留各自场景（扣款单列表／业务层 display-copy 源），**一条未丢** |

**关键判据**：退役体自身声明 `composition_mode=entry_semantic_surface`，与该面解析结果同一个 mode，因此**退役不可能改变任何模型级面的 authority**
（790／879 的 `native_authority` 来自它们各自的 action 级 `native_semantic_surface` 声明）。原先「三个入口」的写法是**范围低报**，不是 authority 变更。

**剩余观察（不登记缺陷、不扩本批）**：852 与派生面仍按模型级兜底渲染 `task` 模式 ＋ 9 个旧章节标题；
这是本批之前既有的呈现（退役后该面标题 13→9，方向为收敛），本批只声明范围、未整改其任务模式，且未做浏览器复核，故留台账观察。

### 12.11.2 本轮实际改动（P1 声明 ＋ P4 验证工具）

| 路径 | 层 | 改动 |
|---|---|---|
| `data/p1_daily_business_form_orchestration_contract_data.xml` | P1 业务声明 | 退役注释改为真实作用域（**本模型所有渲染面**），并写明各面 authority 来源（790／879＝entry 级 native；852／派生面＝模型级 entry floor） |
| `tests/test_tax_deduction_native_lowcode.py` | P4 验证工具 | 新增派生面用例：无 `id`／`view_mode=tree,form`／`context={'create': False}` 溯源；正式可达性（菜单→action→form 按钮）；无作用域请求解析结果；退役体不在 applied；退役标题不再并入；模型级兜底声明的字段仍在该面渲染；`_assert_declared_facts_survive` 通过 |

验证：`make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestFormStructureConsumption,/smart_construction_core:TestTaxDeductionNativeLowcode'`
→ **PASS** `0 failed, 0 error(s) of 25 tests`（`tmp/freeze-r12/l2-sc-core-structure-consumption.log`）。
两次定向失败均为**断言期望／读取口径错误**（非产品缺陷），已按事实改写；未放宽任何既有断言、未做无变化重试（见总记录 §8.31.3）。

### 12.11.3 交付前口径修正（复核 minor）

| # | 发现 | 处置 |
|---|---|---|
| 1 | 本册头部「批次验收完成」与末段「整改中」冲突 | 头部已标注被 §12.10.6／§12.11 **取代**，冻结链以末段为准 |
| 2 | `ActionView.vue` 已由本批 `d14020bb` 修改，归属表却记「未改」 | §12.9.1／§8.30.1 的「本轮未改」时间边界限于第 10／11 轮；**本批 P0 产品改动包含 `ActionView.vue`**（提交 `d14020bb`：列表内建新建入口不再重复声明）。§12.1 归属表第 15 行已同步更正 |
| 4 | 证据摘要 `scope manifest` 值写错 | 以完整指纹产物 `scope_manifest_sha256` 为准重生成（新冻结身份） |
| 7 | `ListPage.vue` 的 `showFallbackCreate` 成为无消费者分支 | 保留并登记为 P0 卫生项（删共享分支需自身受影响面验证，不在本批扩面） |
| 9 | 852 列表域引用不存在的 `finance.tax.deduction` | 本批外观察项，登记待办 |
| nit 3 | `tax_deduction_registration.py` `init()` 裸 SQL 回填 | 本批外待办，登记 |

### 12.11.4 未执行项与状态

未推送、未建 PR、未部署、未启动 G07；未重跑全矩阵；未改办理事项；未重做迁移；
未 `sync_demo`／fixture reset／发布快照／无关 upgrade；未停启历史容器、未改 Docker 网络、未清理历史工作树；
受保护草稿 163／190／192／194／233／267／274／276 未触碰；**未持久化业务或配置写入**；
879 记录态仍**未覆盖**（`empty_action_domain`，不为补证据造数据）；台账保持 **31**。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #494，squash 同树）｜未部署｜89 入口交付未完成｜台账 29**。

## 12.12 G06 主线集成与台账 31 → 29（2026-09-18）

§12.11.4 的「未推送、未建 PR、未合并」与「台账 31」已闭合。冻结候选
`dea896d229c17628d4f770f06da21dfbe28eff6d`（tree `f709bccacff913fcd26aeac0b245337a4ae046d2`，
7514 路径完整指纹，exact-head `ci.local.quick` PASS）经 **PR #494** 合入 main
`5938d6c620952e9c4c1af9fa6c33dbda14da0374`（squash）；`origin/main^{tree}` 与候选 tree 逐字节一致。
该 head 上远端必检项全部 success：`frontend_release_gate`／`merge_policy_gate`／`public_guard`／
`professional_quality_gate`／`release_candidate_gate`／`python310_runtime_compatibility`／`professional_authorization`。
本 PR 承载范围是**全 33 路径／18 提交**（P0 机制消费、共享前端、P1 声明与原生结构、P4 工具、生成证据、记录），
不是单一「抵扣表单迁移」；正文含 852 三项区分与全部保留边界。

台账 31 → 29：退役本册两个正式入口 790／879 的条目（视图 1654，`uc4G06PublishedAudit`）。
852 与派生面按「非额外消费者」登记进该审计块的 `bypassConsumers`（`counted=false`）；
`nextBatch` 前进到 G07。`879` 记录态仍登记**未覆盖**（`empty_action_domain`，不造数据）。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #494，squash 同树）｜未部署｜89 入口交付未完成｜台账 29**。
