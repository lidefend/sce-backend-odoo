# U-C4 G06 税额与专项抵扣原生结构迁移与低代码兼容

- 批次：`U-C4` 表单结构消费稳定化 · 代表面 `G06 税额与专项抵扣`
- 分支：`feature/uc4-tax-deduction-native-v1`（基于 `origin/main`=`daf9a97875a15343671c00e46fd9c4e639ebeca2`）
- 唯一写入者：本会话执行体；本候选之外的其它工作树本轮未触碰
- 状态：**批次验收中（未冻结）｜未集成｜未部署｜89 入口交付未完成**；台账（`form_structure_compatibility_consumers_v1.json`）保持 **31**，
  扣减（**31 → 29**）按 G03/G04/G05 先例留待合入后由独立提交落地（§9）

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
4. `tests/test_tax_deduction_native_lowcode.py`（**新增** 486 行 / 7 测）+ `tests/__init__.py`（+1，注册模块）。
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
| 4 | `addons/smart_construction_core/tests/test_tax_deduction_native_lowcode.py` | — | **本批新增**（486 行 / 7 测） | P4 |
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

stage identity 口径：本批仍处**批次验收中（未冻结）**，按「日迭代＝HEAD ＋ 显式 dirty 范围」记录，不写 full fingerprint、不称 frozen；
交付阶段的干净 HEAD ＋ 完整指纹在冻结步骤单独生成（§9）。

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
- 未冻结、未跑交付 Quick、未推送、未建 PR、未部署。

状态：**批次验收中（未冻结）｜未集成｜未部署｜89 入口交付未完成｜台账 31**。

## 10. 本批登记的产品与机制发现（不隐藏）

| 发现 | 层次 | 处置 |
|---|---|---|
| 原生 1654 在同一表单把 `withholding_amount` 呈现两次（`抵扣金额与税额` + `扣款办理`） | P1 产品结构 | **本批已修**：保留在 `抵扣金额与税额`，`扣款办理` 不再重复；L2 用 `SINGLE_PRESENTATION_FACTS` 断言「同一表单内一次呈现」 |
| `smart_core/app_config_engine/services/view_Parser/base.py:102` 用 `not xml_content` 判断入参，而该函数同时接受 lxml Element（第 104 行 `else xml_content`）；lxml 对 Element 的真值语义已废弃（相邻调用点 `contract_Parser.py:109`、`parsers Tree Form.py:698` 都以 Element 传入） | P0 机制 | **登记不改**（改 `smart_core` 超出本批边界）。当前不可观测：真实 form arch 必有子节点，故不会退化为 `{}`；仅对**无子节点**的元素会静默返回 `{}` 并抛 `FutureWarning`。属潜在健壮性缺口，需 P0 单独决定 |
| 本批新增测试首版用 `arch_fields.get(name) or {}` 读 lxml 元素，触发同一条 `FutureWarning`，且对无子节点的字段会读错可见性 | P4 本批引入 | **本批已修**：改为显式 `is not None`，并把断言提升为行为断言（声明事实恰好呈现一次 + 隐藏必须是消费层可见性而非静默移除） |
| `scripts/verify/view_orchestration_product_boundary_guard.py` 的 `ALLOWED_COMPOSITION_MODES` 不含 `native_semantic_surface`，且只在「form 带 `fields`」时才要求允许模式 —— 缺一条「`native_semantic_surface` 必须无 `sections/fields/columns`」的正向校验 | P0/P4 共享守卫 | **登记不改**。该守卫实跑 `FAIL`（exit 2），5 条错误全部指向本批**未改**的契约（`tender_bid` P1 事实、`payment_request` P1 事实、`policy_document_form_v1`、`tender_bid_registration_productized_form_v1`、`tender_bid_registration_form_structure_v1`）；守卫文件与这 5 个输入都不在本批 9 个路径内，故**预先存在、非本批引入**。本批两条退役契约因已删 `fields` 而通过该守卫。该守卫未纳入 `ci.local.quick.run` 与 `pr.push`，不影响本候选的 Quick。是否补正向校验属 P0/P4 单独决定 |
