# U-C4 G03 收款与公司收入原生结构迁移与低代码兼容

- 批次：`U-C4` 表单结构消费稳定化 · 代表面 `G03 收款与公司收入`
- 分支：`feature/uc4-receipt-income-native-v1`（基于 `origin/main`=`1dbf63f5dd8513b71aede67c875e51b7a95e8626`）
- 唯一写入者：本会话执行体；4 个历史保留工作树本轮未触碰
- 状态：**批次验收待冻结门禁｜未集成｜未部署｜89 入口交付未完成**；台账（`form_structure_compatibility_consumers_v1.json`）保持 **38**，扣减留待合入后核对

## 1. 范围与身份

| 项 | 值 |
|---|---|
| 正式入口 | `action 637`（收款收入 / menu 545 公司收入，财务中心）、`action 806`（收入 / menu 907） |
| 旁路入口 | `action 807`（工程进度款收入登记 / menu 908）：`view_ids=[(tree,2059),(form,1644)]`，表单同样是 **1644** |
| 模型 | `sc.receipt.income` |
| 原生根表单 | `view 1644` = `smart_construction_core.view_sc_receipt_income_form`（`sc.receipt.income.form`） |
| 台账登记配置 | `sc_receipt_income_form_sections_v1`(149)、`sc_receipt_income_p1_form_business_facts_v1`(8)、`receipt_income_productized_form_v1`(196)、`receipt_income_project_productized_form_v1`(197) |
| 实施中发现 | `sc_receipt_income_form_structure_generated_v1`(109，模型级生成镜像)、`receipt_income_engineering_progress_productized_form_v1`(198，旁路 807 的产品化声明) |

样本：全库仅 1 条（`id=1 S70-RI-001`，`state=confirmed`，`source_origin=manual`，`business_category_id.code=finance.receipt.income.project`，`treasury_ledger_id/legacy_*` 全空，无草稿样本）。

职责分层（本批实施）：

| 层 | 目标 | 说明 |
|---|---|---|
| Formal Product Layer | P0 平台机制 + P1 声明 | 结构消费属 P0；入口声明属 P1 |
| Layer Target | `smart_construction_core` 原生视图 + 发布配置退役 | 不改 `smart_core` 机制代码 |
| Standard vs User-Specific | 行业标准默认 | 收款登记属标准业务入口 |
| Why Here | 原生 arch 是结构权威；发布配置只保留入口标题与稀疏注解 | |
| Why Not Elsewhere | 不把结构写进共享层 sections（那正是本批要退役的重复投影） | |
| Blast Radius | `sc.receipt.income` 的 637/806/807 三个入口 + 4 个既有配置记录；列表/API/字段存储不动 | 由 L1/L2/L3/L4 分别证明 |

## 2. 实际改动

1. `views/core/receipt_income_views.xml`：重建原生 1644
   - 8 个业务组加 `name` + `data-sc-anchor`（`data-sc-anchor` 是业务章节唯一 opt-in，仅 `group` 且需 anchor+label）；
   - 组标题与退役配置对齐（`业务方向`→`办理主信息`、`项目与往来单位`→`项目与合同`、`收款信息`→`收款事项`、`收款金额/抵扣与结算`→`金额与抵扣`、`办理说明`→`说明与附件`）；
   - 恢复配置声明过、原生未承载的 15 个事实（`legacy_project_name/company_id/legacy_company_name/legacy_partner_name/legacy_contract_no/legacy_receipt_type/legacy_receipt_subtype/legacy_source_model/legacy_source_table/legacy_record_id/legacy_document_state/legacy_document_state_label/legacy_note/reject_reason` + `creator_name/created_time/active` 收敛入「来源追溯」）；
   - `receiving_account` 按配置归入「收款账户」；「台账」页只留 `treasury_ledger_id`（三处 `creator_name/created_time/active` 重复收敛为两处，其中一处随页条件合法隐藏）；
   - 保留：header 5 按钮及其 `invisible`/`groups`、notebook 2 页条件、页内 `action_view_company_contractor_responsibility_summary`、`name` 静态 `readonly="1"`、`can_review`/`company_contractor_responsibility_summary_id` 的 `invisible="1"`。
2. `data/receipt_income_form_productization_contract.xml`：3 个入口声明改为 `{'title': …, 'composition_mode': 'native_semantic_surface'}`（不再带 `sections/fields/columns`）；文件尾以 `<function … write>` 精确退役模型级生成镜像 109（沿用 U-C3/U-C4 G02 形态）。
3. `data/view_orchestration_form_section_contract_data.xml`、`data/p1_daily_business_form_orchestration_contract_data.xml`：149、8 置 `active=False` 并加注释（`contract_json` 未改，可回读原声明）。
4. `tests/test_receipt_income_native_lowcode.py`（新增 6 测）+ `tests/__init__.py` 注册。
5. `scripts/verify/local_dev_form_lowcode_scope.py`：新增只读代表路由 topic `receipt_income`（3 个身份，复用既有环境/身份校验，不新建 fixture/环境），并登记 `section_navigation` + `record_surface`。
6. `frontend/apps/web/scripts/formal_form_representative_journey.mjs`：每条路由增加 `field_names`（实际提升为节点的字段名，只读、有界、无密钥），用于把「章节是否出现」变成可归因事实。

## 3. 机制审查结论（先审查，再决定登记范围）

| 规则 | 结论 |
|---|---|
| P0 只消费明确通用语义，不按模型名/字段后缀猜副本 | 未新增任何按后缀/模型名推断的分支；共享层仍只读 `_display_copy_source_fields` 协议 |
| P1 声明确有依据的来源关系 | **本批不登记 `sc.receipt.income` 的展示副本**：`receipt_income_attachment_text_display` 的 compute 在无附件时回退到 `_receipt_income_attachment_ref_value()`（双来源派生），且 `sc.receipt.income` **未**继承 `sc.formal.display.copy.sources` 协议（`payment.request`/`sc.material.inbound` 才继承）。登记会既无依据又不会被消费（`_display_copy_field_names` 返回 `set()`），因此改为**保留其配置/列表/API 职责、由退役重复投影来保证正文单一呈现**，并以测试固定该结论 |
| 同一事实允许在不同场景各有表达 | 附件摘要仍在列表列（`receipt_income_views.xml:65`、`user_confirmed_formal_list_views.xml:350`）与 API；正文只由 `attachment_ids` 承载 |
| 原生结构权威不能单独证明动作已有承载位置 | 逐条核对：header 5 按钮 + notebook 1 按钮均保留原可见条件/组限；`name` 转原生权威后手工指定编号入口关闭，**登记为本轮观察项**（未在无业务决策的情况下改条件只读） |

## 4. 验证矩阵

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS（16 tests + 全部守卫；`change_state=dirty coverage=L1_only`；8 路径未映射→按规则改跑选定 L2） |
| L2 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestReceiptIncomeNativeLowcode'` | **6 tests / 0 failed / 0 error**（`l2-receipt-income.log`） |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` + `local.dev.verify_authority` | PASS（78 modules，`demo.authority` PASS，`l3-upgrade.log`） |
| L4 | `FORM_LOWCODE_TOPIC=receipt_income FORM_LOWCODE_REPRESENTATIVE=1 make local.dev.form_lowcode.browser` | EXIT=0，`ok=true`、`restored=true`、`browser_errors=[]`、业务指纹未变（`run-receipt_income-r3.log`；报告 `artifacts/lowcode-form-loop/browser/representative-report-receipt_income.json`） |

L4 三次运行均为**输入变更驱动**（非无变化重跑）：r1＝首次只读（仅 create 路由，暴露 806 通过、637/807 拒绝访问）；r2＝在既有 runner 内登记 `record_surface` 后复跑（记录路由纳入，暴露「来源追溯」在只读样本上不出现在导航）；r3＝在既有 runner 内补 `field_names` 只读证据后复跑（把章节差异变成可归因字段清单，即上表最终结果）。
日志：`artifacts/uc4-representative/run-receipt_income.log`、`-r2.log`、`-r3.log`。

L2 日志处置（透明记录）：首轮运行在断言全部通过的同时，日志中出现一次被捕获并记录的异常（frame 链：`contract()`→`ui_contract_v2.handle`→`PageAssembler`→`app_view_config._generate_from_fields_view_get`→`contract_Parser._get_and_parse_view`→`base._lossless_parse_xml`）。为留存 L2 日志并复核该记录的可复现性，**同输入复跑一次**：`0 failed / 0 error(s) of 6 tests`，且该异常**未复现**（`l2-receipt-income.log` 全文无 `Traceback`/`ERROR`）。安装后（L3）的只读契约复验（3 入口）同样无该记录，最终契约均为 `native_authority`。归因未闭合 → 登记为观察项（非阻断），不以重跑掩盖，也不据此改产品。

L2 断言（行为，非实现字符串）：入口声明为 `native_semantic_surface` 且无 `sections/fields`；149/8/109 均 `active=False`；三入口 `formStructureAuthority=native_authority`、`configuredSections=[]`、`compatibilityDependencies=[]`、最终树 55 字段且**无重复节点**；14 个恢复事实各 1 次；历史/来源字段 `readonly`、`legacy_receipt_type/subtype` 保持可编辑；章节归属（`receiving_account`→收款账户、`reject_reason`→说明与附件、`legacy_source_model/active`→来源追溯）；空 header 组不带 `invisible`；附件摘要不入正文且仍在列表；展示副本结论（未继承协议/未登记）；807 的 `view_ids[(form,1644)]` 与 domain 不变；作用域低代码 **预览→发布→回滚**（`reject_reason` 隐藏→发布后仍隐藏→回滚后恢复可见，且同表单另一入口契约逐项不变，业务记录 `write_date/state` 不变）。

## 5. 代表面浏览器结果（只读）

| 入口 | 路由 | 结果 |
|---|---|---|
| 806 收入 | create | **passed**：章节导航 8 项（7 业务章节 + 协作记录）全部 resolve 且可见；吸顶不重叠（1088：操作行 175–205 / 导航 218–257 / 目标 269+；390：281 / 294–347 / 359+，18 组测量 0 重叠）；`duplicated=[]`、`empty_containers=[]`；渲染节点 29 |
| 806 收入 | record（样本 id=1） | **passed**（readonly 形态）：导航 7 项全部 resolve 可见；吸顶同样 0 重叠；渲染节点 22；`责任余额` 页可见（样本有责任余额摘要）、`台账` 页合法隐藏（无台账） |
| 637 公司收入 | create | **拒绝访问**：`NAVIGATION_AUTHORITY_DENIED`（交付导航权威不含该入口的治理身份），非结构结果 |
| 807 工程进度款收入登记 | create | **拒绝访问**：同上；且该入口 domain 无样本，查看路由未执行（**未覆盖**） |

传输证据（单独记录，不判为产品缺陷，也不声称零错误）：本轮代表面报告 `diagnostics.failed_requests=0`、`console` 仅 1 条 Vue Router `history.state` 警告；上一轮同 topic 运行曾记录 Vite 资源 `net::ERR_NETWORK_CHANGED`。

**观察项（不登记为缺陷）**：契约层 3 入口均为 55 字段且无重复；前端把其中一部分提升为渲染节点（create 29 / record 22）。`state/legacy_document_state/legacy_document_state_label` 不出现可由 `nativeLayoutUtils.CREATE_WORKFLOW_STATE_FIELD_NAMES`（创建面工作流状态字段）解释；其余差异与空值 readonly 字段的呈现策略一致，**但本会话未对逐字段做完整归因**，登记为观察项 + 后续最小诊断（字段名证据已随报告留存）。本批未改动任何前端渲染代码，该差异不是本批引入。

**观察项（被捕获异常）**：见 §4 L2 日志处置。同输入复跑与安装后复验均未复现；不登记为缺陷，不以超时/断言放宽处理。

## 6. 剩余缺口

1. 637 / 807 的浏览器结构结果：交付导航权威对治理身份拒绝访问；需要具备财务/业务发起能力的受管身份才能补测（新建身份属独立 P4 授权，本批不做）。
2. 807 查看路由：progress 域内 0 样本，未覆盖。
3. 前端「契约字段 → 渲染节点」逐字段归因（见观察项）。
4. `name` 由原生权威承载后手工编号入口关闭：登记为观察项，待业务决策。

## 7. 未执行项（保持未执行）

`local.dev.sync_demo`、`local.dev.snapshot`、fixture reset、历史数据修复、无关模块 upgrade、发布快照、历史容器停启、Docker 网络调整、工作树清理、复核草稿清理。
非本轮草稿（163/190/192/194/233/267/274/276）全部保留未消费；本批写入仅限 `sc.receipt.income` 的视图/配置退役与新增文件。

## 8. 主线集成与台账扣减（合入后记录）

- 冻结候选：head `558626214f57f03e3bc3eb25e1acd9caa40b0d63`、tree `175da4c07dad0524bd13aaa4466202518953ba56`，
  完整指纹 `9b1bae26…2808cb`（7505 路径），`make ci.local.quick` 在该 head 上 PASS
  （receipt `.git/codex/evidence/ci.local.quick/558626214f57f03e3bc3eb25e1acd9caa40b0d63.json`）。
- 独立复核：同 head/base 只读复核，结论 APPROVE，无 S0/S1/S2 阻断项；残留风险与 5 条跟进项见
  `.codex-evidence/workspace-archives/20260918/uc4-g03-receipt-income-native/558626214f57f03e3bc3eb25e1acd9caa40b0d63/` 的 `review.md`。
- 归档：`make workspace.evidence.archive`（manifest `tmp/g03-evidence/archive-manifest.json`）共 5 个文件
  （summary / identity / review / 2 张代表面截图），回执 `status=verified`，逐文件哈希与源文件一致、JSON 可读。
- 远端门禁：PR #488，exact head 上 `frontend_release_gate`、`merge_policy_gate`、`public_guard`、`professional_quality_gate`
  全部 success；`make pr.merge.prep` PASS；`make pr.merge`（squash，`--match-head-commit`）合入。
  合入后 main = `654edf0ff09fe394080bfa2545a5061dcafdbecd`。
- 台账扣减：**38 → 36**（退役 action 637/806 与视图 1644），新增 `uc4G03PublishedAudit`；
  旁路 action 807 不计数、如实登记在 `bypassConsumers`；`nextBatch.selectedGroup` 前进到 **G04**（实付与公司支出 837/808）。

状态：**批次验收完成（本批范围）｜主线集成完成（PR #488）｜未部署｜89 入口用户验收未完成**。
