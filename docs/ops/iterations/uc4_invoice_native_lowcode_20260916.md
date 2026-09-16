# U-C4 发票多分类默认结构迁移与低代码兼容（G02）

## 边界与承接

基线 `3323fb49e41e6bf0851acfde0d3e9df2dafafd8f`（#486 主线集成），分支 `feature/uc4-invoice-native-lowcode`，前置提交 `3f318072`（U-C3 台账尾项 44→42 关闭）。本批为台账剩余 42 项中的 G02 组（4 项），按既有分组继续推进，不重跑 UC1/UC2/UC3 证据矩阵。

Formal Product Layer=P1；Layer Target=发票四入口原生默认结构与旧结构覆盖退役；Module=`smart_construction_core`。不新增业务规则、不扩权限、不改金额计算；P3 合法低代码配置仍由既有编译器合成。

## 范围确认（有限范围确认表）

### 正式范围（action / menu / model / view 及共用关系）

| 正式入口 | action | menu | 语义 | 组 |
|---|---|---|---|---|
| 进项发票 | `action_sc_invoice_input`（785） | 532 | domain direction=input | finance_read |
| 销项开票申请 | `action_sc_invoice_application_user`（786） | 534 | invoice.output.application | 4 组 |
| 销项开票登记 | `action_sc_invoice_registration_user`（787） | 535 | invoice.output.registration | 同上 |
| 预缴税款登记 | `action_sc_invoice_prepaid_tax_user`（788） | 536 | invoice.prepaid_tax，default_direction=prepaid | 同上 |

四入口共用 `sc.invoice.registration` 与 form view 1651（`view_sc_invoice_registration_form`）。旁路共享同模型同表单但不入台账、不扣减：`action_sc_invoice_input_report_user`（进项税额上报）、`action_sc_invoice_registration`（发票总台账），二者无 action 级配置。红冲 `action_sc_output_invoice_adjustment` 为独立模型 `sc.output.invoice.ledger`，不受本批影响。

### 当前依赖（仍在实际生效的旧结构覆盖）

1. 4 条 action 级配置（priority 700，entry_semantic_surface，9 sections + 全字段排序）：`invoice_input_productized_form_v1` / `invoice_output_application_productized_form_v1` / `invoice_output_registration_productized_form_v1` / `invoice_prepaid_tax_productized_form_v1`。
2. 模型级 `sc_invoice_registration_form_sections_v1`（priority 20，仅 8 个章节标题，模型全域）。
3. P1 事实 `sc_invoice_registration_p1_form_business_facts_v1`（priority 88，4 章节标题 + 全 readonly display 字段，模型全域）。
4. 实施中发现的第 7 条（台账 G02 legacyConfigurations 原登记遗漏）：模型级生成镜像 `sc_invoice_registration_form_structure_generated`（priority 116，noupdate 起源，内容仅重复字段排序），随本批按 U-C3 精确 ORM 退役 function 定式一并退役。

编排器合并语义（`view_orchestrator.py` + `form_structure_authority.py` 源码核实）：entry_semantic_surface 下正文树=原生解析树+稀疏策略注解，章节投影（section_titles/field_groups/configured_sections）由 `resolve_form_structure_governance` 输出供前端任务态分章；native_semantic_surface 下结构权威归原生视图（configured_sections/section_titles 清零、稀疏语义策略保留）。**非作用域化（模型级）结构配置与 native 共存不报错**，降级为 `LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW` 诊断；仅 action/view 级 scoped 结构配置与 native 共存才触发硬错误。据此本批处置：四 action 配置转 native；两条共享配置按台账 G02 legacyConfigurations 一并退役（旁路两 action 无独立配置层，退役后转消费重构后原生表单）。

### 迁移目标（正文与导航消费同一最终结构）

- view 1651 原生重构为四方向条件分组的唯一结构源：显式分组加 `data-sc-anchor` 锚点；补齐配置呈现而原生缺失的字段（`company_id`、`note_display`、`invoice_attachment_text`、`legacy_source_model/legacy_source_table/legacy_record_id/legacy_document_state`、`legacy_partner_id/legacy_partner_name`、`source_created_by/source_created_at`、`applicant_name`、`expected_receipt_date`、`prepaid_tax_date`、`tax_certificate_no` 等，以四配置字段并集为准）；header 按钮、statusbar、notebook（红冲关联/迁移来源）保留。
- 4 条 action 配置转 `native_semantic_surface`：仅保留 title 与 action 作用域稀疏只读策略（U-C3 制度文件 `policy_document_form_v1` 先例），sections/字段排序退役。
- 2 条共享配置（模型级 sections + P1 事实）`active=False` 退役；两数据文件均为 noupdate="0"，原地编辑记录即可随受管升级生效。生成镜像为 noupdate 起源，走精确 ORM 退役 function（invoice_input_form_productization_contract.xml 尾部）。

### 保留能力

- 字段：四配置字段并集全部保留呈现；readonly 语义按各配置既有策略迁入稀疏策略或原生 attrs；金额字段 compute 语义（amount 权威链）不动。
- 动作：提交审批/审批通过/审批驳回/已登记/取消按钮与状态条原样。
- 权限：四 action 组绑定与模型 ACL 不改；不新增组、不放宽 domain。
- 合法低代码：native 模式下「表单设置→预览→发布→回滚」配置闭环继续可用（node_patches 编译器路径不受影响）。
- 旁路入口：两旁路 action 打开不报错、不出现已退役章节标题，转原生结构正常呈现。

### 验收安排

- 新建样本：785 进项新建（桌面）与 788 预缴新建（窄屏）各一，验证章节导航、锚点、条件分组方向正确。
- 查看/编辑样本：复用 `sc_dev_demo` 既有发票记录（direction 各向至少一条；无可读样本的方向明确记未覆盖，不造业务数据）。
- 配置闭环：任一入口跑「表单设置→预览→发布→业务页刷新→回滚」。
- 入口隔离反例：785 前后发布操作不改变 787 有效结构；旁路 action（发票总台账）打开无错且无已退役章节。
- 证据承接：按已合入影响范围验证规则，不重复完整验证；L1/L2/L3 分层推进，整组浏览器复核后再冻结。

## 执行记录

### 首轮实施（2026-09-16）

改动（全部在 `smart_construction_core`）：

- `views/core/invoice_registration_views.xml`：form view 1651 重构——9 个具名锚点组（invoice_main / invoice_project / invoice_tax_details / invoice_prepaid_tax / invoice_amount / invoice_output_business / invoice_handling / invoice_notes / invoice_source_trace），补齐缺失字段（company_id、legacy_partner_name、note_display、invoice_attachment_text、legacy_source_model/table/record_id/document_state、legacy_partner_id、source_created_by/at），header 按钮与 statusbar、红冲关联/迁移来源 notebook 原样保留。
- `data/invoice_input_form_productization_contract.xml`：785 配置转 `native_semantic_surface`（仅 title+mode）；文件尾部新增精确 ORM 退役 function（生成镜像 `sc_invoice_registration_form_structure_generated` → active=False）。
- `data/invoice_output_tax_form_productization_contract.xml`：786/787/788 三条配置同构转 `native_semantic_surface`。
- `data/view_orchestration_form_section_contract_data.xml`、`data/p1_daily_business_form_orchestration_contract_data.xml`：两条共享配置 `active=False` 退役（noupdate="0" 原地编辑）。
- `tests/test_invoice_native_lowcode.py`（新增，三测）：①四入口结构退役与字段并集保留断言；②原生表单锚点/按钮完整性 + 两旁路 action 反例（无已退役章节标题、native workspace 态）；③作用域低代码预览→发布→回滚闭环与另一入口隔离、业务指纹不变。
- `data/view_orchestration_contract_generated_data.xml` 未改动（noupdate 起源，退役走 function，U-C3 定式）。

实施中发现：台账 G02 legacyConfigurations 原登记 6 条遗漏了生成镜像（priority 116，noupdate，内容仅重复字段排序），已补登为第 7 条（`sc_invoice_registration_form_structure_generated_v1`），evidenceStatus 更新为 grouped_from_ledger_plus_implementation_discovery_generated_mirror。

分层验证：

- L1 `make ci.local.iteration`：16 项测试 + 全部守卫 PASS（增量计划 9 路径未映射，按规则选定非零 L2 目标）。
- L2 `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestInvoiceNativeLowcode'`：首轮 2 失败（①生成镜像未退役触发 `legacy_configuration_structure_suppression`——正是遗漏的第 7 条；②测试自身子串断言把原生组标题「发票金额与税额」误判为已退役章节「发票金额」），修复后 0 failed / 0 error。
- L3 `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1`：ready + demo.authority PASS；`local.dev.restart` + `local.dev.health` PASS（profile=persistent, dbfilter 校验通过）。
- 运行态冒烟（odoo shell，sc_dev_demo 实库）：7 条旧结构职责退役后契约状态正确（4 条 action 配置 active+native+无 sections；sections_v1(150)/P1(9)/生成镜像(81) 均 active=False）；四正式入口（785/786/787/788）governance=`native_authority`/`task`/compat=[]/configuredSections=0，9 个锚点组全部在 containerTree；两旁路（789 进项税额上报、639 发票总台账）`native_authority`/`workspace`/compat=[]/无已退役章节，同一原生树正常承载。冒烟过程中确认 admin 账号不在发票模型四个能力组（既有权限边界，非本批回归）。

### 源码复核回应（用户复核 720bfb15 后，同日）

用户复核结论：实施方向正确、可继续，但"全绿"证明范围偏窄，冻结前三缺口须集中补齐。本轮修齐（仅测试强化，无产品修改，未重复升级）：

1. **权威断言去兜底**：旁路测试原先在 `formStructureAuthority` 缺失时默认成功值——已改为键必须存在（`assertIn`）+ 明确断言实际模式（旁路=`native_authority`/`workspace`；正式入口=`native_authority`/`task`）。键名经 ui_contract_v2.py `formal_governance_source` 映射表核实（snake→camel 精确键）。
2. **字段有效规则断言**：新增 `test_shared_form_effective_field_rules`——关键字段断言单一 occurrence、归属组（tax_type/prepaid_tax_date/tax_certificate_no→invoice_prepaid_tax；applicant_name/expected_receipt_date→invoice_output_business）、条件组 invisible 表达式原文（预缴/销项两组）、无条件组不得携带 invisible、readonly 约束保留（company_id/note_display/legacy_*/source_created_*）、可编辑字段未被静默置只读。
3. **低代码断言补齐**：预览态与发布态分别断言 `note_display` 在最终树上 modifiers.invisible 生效（非仅补丁在途）；回滚后显式断言恢复可见；基线前置断言可见。
4. **tax_type 进项显隐核查（原有规则判定，非迁移回归）**：机制对照测试 `test_tax_type_input_visibility_is_preexisting_native_rule`——事务内重建 legacy 复合态（native 785 配置停用 + 三条共享层激活 + 旧 entry 配置机制等价副本，其 tax_type 声明与旧配置一致：section 成员 + 无语义键字段行），断言 legacy 态 `formStructureAuthority=entry_semantic_surface` 且 configuredSections 非空（重建确实走旧路径）后比对：**tax_type 节点 modifiers/attributes 与迁移后完全一致，预缴组 invisible 表达式逐字一致**；辅以 git diff（b80b2cde→HEAD）证明预缴组表达式未被本批改动。结论：旧进项配置将 tax_type 列入「进项税务信息」section，但正文树自始将其置于仅预缴方向可见的组，entry 配置投影从未翻转原生隐藏——**进项方向 tax_type 隐藏为原有产品歧义（配置声明与原生显隐矛盾），维持原状不擅改**；若产品决定进项需要 tax_type，属业务规则取舍，另行批次决策。

措辞修正：本批准确表述为「七条旧结构职责退役」（4 条 action 配置转换为 native 稀疏契约 + 3 条共享层停用），非"七条配置全部停用"。低代码三测覆盖预览/发布/回滚后端链路与入口隔离，UI 操作闭环留待 L4 浏览器复核。

定向 L2 复跑：`TestInvoiceNativeLowcode` 5 测 0 failed / 0 error（含两轮修复：walk 元组化、无产品代码改动）。

未覆盖（后续阶段）：浏览器层 L4 复核（四入口新建/查看样本、窄屏、配置闭环 UI、隔离反例的浏览器证据）、整组冻结与 Quick、L5 集成门禁。台账扣减（42→38）须待主线合入后按发布核对流程执行。

### 整组浏览器复核（L4，同日）

命令：`FORM_LOWCODE_TOPIC=invoice make local.dev.form_lowcode.browser`（env：`BASE_URL=http://127.0.0.1:5174`、`E2E_LOGIN=sc_test_admin`、`E2E_PASSWORD=$SC_DEMO_USER_PASSWORD`、`DB_NAME=sc_dev_demo`）；结果 `EXIT=0`，报告 `artifacts/uc4-invoice-lowcode/browser/designer-report.json`（`ok=true`、`restored=true`、`browser_errors=0`）。整组一次跑通：发票六入口旅程 + 设计器「表单设置→预览→发布→业务页刷新→回滚」闭环。

**四正式入口（785 进项 / 786 销项申请 / 787 销项登记 / 788 预缴）**：契约层断言六面全过（authority 键必须存在、mode 精确、compat/configuredSections 为空、resolvedActionId/viewId 匹配、9 锚点组在 containerTree、条件组 invisible 原文、readonly/required 修饰符）；浏览器层 785/786/787/788 新建页桌面 1440 + 窄屏 390（`scrollWidth <= innerWidth+1`）全过、章节导航齐、退役章节零泄漏、必填与只读标记落地到渲染控件（readonly 字段无可编辑控件，`note` 可编辑）。记录页样本：785、787（含 legacy 迁移页）通过；**786、788 记 `not_run_no_sample`**——sc_dev_demo 中无该两方向可读记录，按纪律不造业务数据。

**两大根因判定（均为既有产品设计，非本批迁移回归）**：

1. **入口级字段面差异＝业务分类 form_policy_json 的 create profile 裁剪**。action context 的 `default_business_category_code`（786/787/788/789 有绑定，785/639 无）→ `sc.business.category.form_policy_json` 的 field_policies 按 render_profile 求值 → `apply_field_policies_to_v2_status`（ui_contract_v2_projection.py）在 widgetStatus 置 `visible:false, auth:'none'`。advanced 组字段 vis_prof 无 create（创建页被裁）、creator_name/created_time/legacy_* 仅 readonly profile、required 集来自 required_fields_json。与迁移前台账字段面口径（785=81 / 787=72）一一对应。已把该机制固化为显式守卫：`CATEGORY_BINDING` / `CREATE_HIDDEN_ADVANCED` / `CREATE_REQUIRED` / `CREATE_READONLY` 表 + `assertCreateSurfaceStatus`（策略隐藏字段必须 visible:false/auth:'none'，绑分类入口的 required 必填、identity 字段 readonly，未绑入口 name 保持可见）。787 创建页销项组整组折叠即由此产生（组内四字段全被裁），断言据此改为组级条件守卫。

2. **记录页条件组隐藏＝readonly 空值投影 + 空组折叠**。`canonicalNativeFormBridge` 在 readonly 模式对每字段执行 `readonlyFactIsPresentable`（formSection.mapper.ts：`!readonly || one2many || 有值 || 有动作`），空值且无动作的字段被裁、组随之折叠。样本 #2 的销项组四字段（push_result / kingdee_document_no / expected_receipt_date / applicant_name）DB 值全空，故整组隐藏；契约三面（layoutContract 树 / statusContract widgetStatus / 前端 canonical 投影）逐面排查确认契约层字段全可见、隐藏发生在前端投影。样本断言据此改为**方向性守卫**：显示 ⇒ 条件成立（反之不成立），`tax_type` 同规则。同源问题：迁移页 `legacy_source_table`/`legacy_record_id` 为分类 readonly-profile 字段而记录页解析 edit profile 契约，断言改锚有值且不受限的 `legacy_partner_name`（报告记录 `legacy_fact`）。

**旁路与入口隔离（不临时加组、不绕权限）**：

- **789 进项税额上报 = 入口隔离（正向覆盖）**。以 `system.init` route_authority 重放取证：sc_test_admin（`role_code=system_admin`）route_authority 仅含 785/786/787/788（`DISCOVERED_PRIMARY_NAV`），无 789 授权 → 直连 `/a/789?menu_id=537` 被 `NAVIGATION_AUTHORITY_DENIED` 送 access-denied（报告记 `denied_for_account`，断言为「必须被隔离」而非跳过）。既有 finance 角色账号（`demo_role_finance`，亦验证 `demo_finance`/`fin1`/`fin_mgr`）持有 789 的 `CONTEXTUAL_ROUTE`（source `finance.invoice_input_report_contextual_route`），直连成功——按「使用已有授权账号」原则以该账号完成 789 的完整 DOM 断言（列表页 + 新建页 + 字段面 + 退役章节 + 窄屏），报告记 `account=demo_role_finance`、`route_kind=CONTEXTUAL_ROUTE`、`status=passed`。
- **639 发票总台账 = 退役导航入口**。菜单 340 的父菜单 323「发票台账」(`menu_sc_invoice_management_group`) 被 `views/menu_product_finance_wave1.xml`（P1 财务中心 wave one）显式停用（active=False），子树对所有主体不可见，任何账号都不持有 `/a/639` 路由授权（已逐一探测 system_admin/finance/owner/business_full/pm/restricted 六个角色面均 denied）。处理方式：断言该入口**必须保持被拒**（反例守卫），DOM 记 `not_run_no_access` 并写明原因；契约层（workspace 权威 + create-profile 字段面）仍全量断言通过。
- 排除的误诊：四正式入口与 789/639 的 Odoo action/menu 组要求完全一致（均含「SC 能力 - 业务发起」），且 786/787/788 对无该组的账号仍可达——说明前端路由授权不读 Odoo 组，而读 role surface 声明；「账号缺组」不是 639/789 不可达的原因。

**设计器闭环**：同一轮跑通「正式 action → 设计器（字段改名/上移/新建分组/隐藏只读备注）→ 预览 → 发布 → 业务页刷新 → 回滚」。`source_patches` 三条稳定 target 全部落地（`/form[1]/sheet[1]/group[2]/field[4]` 等），发布态 `published_content_verified=true`、`runtime_verified=true`，发布前后主入口契约与预览契约一致、另一入口（787）契约与基线逐字一致（入口隔离），回滚后恢复到基线且业务页不再出现配置标签。修正了本分支新增的 invoice 视觉顺序断言：原式 `y0<y1<y2` 前提有误，实际渲染为「受管发票号码」独占一行、未动的「发票代码/发票类型」保持默认两列同排——改为断言「被移动字段在上 + 未动字段共享列」（`visual_order: invoice_no_y=325 < invoice_code_y=461 == invoice_type_y=461, untouched_columns=shared`），同时把 outside 页锚点从 787 创建页被策略裁掉的「销项业务信息」改为常驻可编辑 `note`。

**未覆盖（明确登记）**：786/788 记录页（无合法样本）；639 全部 DOM 路由（退役入口）；sc_test_admin/`admin` 本身不在发票模型四个能力组（既有权限边界，非本批回归）。

## 状态

本批首轮实施 + 源码复核断言强化 + 整组浏览器复核（L4）已完成自验：L1/L2/L3 与运行态冒烟通过，L4 六入口旅程 + 设计器发布回滚闭环 `EXIT=0`（报告 `ok=true`、`restored=true`、`browser_errors=0`）。遗留未覆盖已逐条登记。**下一步待用户决策**：整组结果交回后再冻结、Quick、独立复核，不自动连续放行。本批未集成｜未部署｜89 入口交付未完成；主线剩余 42 不变。

