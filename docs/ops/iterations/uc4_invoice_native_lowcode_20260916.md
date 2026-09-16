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

编排器合并语义（`view_orchestrator.py` + `form_structure_authority.py` 源码核实）：entry_semantic_surface 下正文树=原生解析树+稀疏策略注解，章节投影（section_titles/field_groups/configured_sections）由 `resolve_form_structure_governance` 输出供前端任务态分章；native_semantic_surface 下结构权威归原生视图（configured_sections/section_titles 清零、稀疏语义策略保留）。**非作用域化（模型级）结构配置与 native 共存不报错**，降级为 `LEGACY_STRUCTURE_SUPPRESSED_BY_NATIVE_VIEW` 诊断；仅 action/view 级 scoped 结构配置与 native 共存才触发硬错误。据此本批处置：四 action 配置转 native；两条共享配置按台账 G02 legacyConfigurations 一并退役（旁路两 action 无独立配置层，退役后转消费重构后原生表单）。

### 迁移目标（正文与导航消费同一最终结构）

- view 1651 原生重构为四方向条件分组的唯一结构源：显式分组加 `data-sc-anchor` 锚点；补齐配置呈现而原生缺失的字段（`company_id`、`note_display`、`invoice_attachment_text`、`legacy_source_model/legacy_source_table/legacy_record_id/legacy_document_state`、`legacy_partner_id/legacy_partner_name`、`source_created_by/source_created_at`、`applicant_name`、`expected_receipt_date`、`prepaid_tax_date`、`tax_certificate_no` 等，以四配置字段并集为准）；header 按钮、statusbar、notebook（红冲关联/迁移来源）保留。
- 4 条 action 配置转 `native_semantic_surface`：仅保留 title 与 action 作用域稀疏只读策略（U-C3 制度文件 `policy_document_form_v1` 先例），sections/字段排序退役。
- 2 条共享配置（模型级 sections + P1 事实）`active=False` 退役；两数据文件均为 noupdate="0"，原地编辑记录即可随受管升级生效。

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

（实施中——首轮实施结果、分层验证与证据后续追加于本节。）

## 状态

本批范围确认完成，首轮实施进行中｜本批未集成｜未部署｜89入口交付未完成。主线剩余 42 不变。
