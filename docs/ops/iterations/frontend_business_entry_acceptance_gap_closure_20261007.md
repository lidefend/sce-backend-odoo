# 89 正式办理前端入口验收缺口收口（2026-10-07）

## 批次边界

- Formal Product Layer：P1（施工行业标准产品入口面）+ P4（验收记录）。
- Layer Target：`smart_construction_core` 项目中心/合同中心入口面；`docs/product/frontend_business_entry_acceptance_v1.csv` 验收矩阵。
- 环境：既有受管日常开发服务器 `http://1.95.85.92:18081`（`ENV=dev`，`sc_demo`），通过 `config/frontend/acceptance_environments_v1.json` 的 `profiles.daily` 解析；所有者已授权对类生产数据做功能性修改。
- 不做：放宽任何断言/ACL/字段权限/负例；改动日常 profile 的 `allowed_operations`；绕过产品面直写容器或 ORM；引入新的全局测试框架；在未获所有者决议前改动全局 one2many 行身份语义。

## 基线

- 分支 `fix/frontend-business-entry-acceptance-closure-20261007`，基线 `main` @ `1c5368a7ecae72946e8183a8a84c2a1f99a89485`（PR #600 合并后）。

## 观察记录

（随执行追加，引用原始日志与产物路径，不复制并行台账。）

## 批次 F3 收口：项目启停管理入口闭环（2026-10-07）

### 结论

`docs/product/frontend_business_entry_acceptance_v1.csv` 第 8 行
`smart_construction_core.menu_sc_product_project_lifecycle_v1`（项目启停管理）由
`partial_passed` 更新为 `passed`。真实产品入口全链走通：
draft →（提交立项）draft →（启动项目）in_progress →（标记竣工）done →（进入结算）closing →
（进入保修期）warranty →（关闭项目）closed，每步均刷新回读，`problems=[]`、`console_errors=[]`。

### 复用的受管环境（未新建环境/库/端口/凭据）

- 日常开发服务器 `http://1.95.85.92:18081`，served revision `6c8e07f7...`，database `sc_demo`，
  environment `dev`；经 `config/frontend/acceptance_environments_v1.json profiles.daily` 解析。
- 登录 `fixture_role_config_admin`（uid216，FE Company A=21；发布导航含 970/1178）。
- 夹具口令仍为固定 `123456`，仅作用于既有隔离 fixture（`smart_construction_acceptance_fixture`），
  未改动其它环境或通用登录默认。

### 四类根因处理结果

1. **发件人根因（draft→in_progress 提交被整事务回滚）**：daily 无 `mail.default.from`/`res.company.email`，
   且内部账号无邮箱 → `mail.thread._message_compute_author` 抛
   `UserError('无法发送消息，请配置发件人的电子邮件地址。')`。经受管入口
   `make daily.runtime.mail_sender.prepare`（`scripts/ops/daily_runtime_mail_sender_prepare.py`，单测 10 项）修复，
   报告 `.runtime/final-acceptance/daily-deployed/mail-sender-prepare.json`，`users_still_without_email=0`。
   该入口只补既有内部账号缺失地址，不覆盖已有地址。
2. **关闭/保修被拒 = 合法业务前置守卫（非缺陷）**：`project_core.py` 的
   `_guard_project_close_by_settlement` / `_guard_project_close_by_payment` 在存在未完结结算/付款时阻断闭态；
   本次验收使用无结算/付款事实的专用载体，未放宽任何守卫、ACL 或字段权限。
3. **关闭确认弹窗**：`IntentConfirmationDialog.vue` 声明确认按钮文案为 `确认${actionLabel}`
   （`data-dialog-purpose="intent-confirmation"`）。探针改为在该对话框内按 `^确认` 前缀消费，
   废弃固定标签白名单；run2 记录到真实弹窗文本「确认关闭项目…关闭后不可恢复…」。
4. **并列发现（不阻断本入口验收，待裁决）**：发布导航授权对
   `group_sc_role_project_manager`（`fixture_role_pm` uid214）过滤掉本菜单 970/action 1178，
   而菜单/动作声明的 `group_sc_cap_project_manager` 对该角色 ORM `has_group=True` 成立 →
   菜单层 group 授权与发布导航授权口径不一致。本行验收以发布导航含该入口的
   `group_sc_role_business_admin`（`fixture_role_config_admin` uid216）完成。

### 载具与身份（受管解析，不硬编码 1813/1843）

- 载体 `smart_construction_acceptance_fixture.fe_project_lifecycle`（`FE Project Lifecycle`，code `FE-LC`）：
  走完闭态后可重置（终态 `closed` 不可回退，故在无业务事实引用时 `unlink()` 重建；有引用则 fail-closed）。
  入口 `make daily.runtime.lifecycle_fixture.prepare`（`scripts/ops/daily_runtime_lifecycle_fixture_prepare.py`，
  单测 17 项；运行工作树夹具源码经受管 `odoo.shell.exec` 送入，不改远端 checkout）。
- 身份解析 `scripts/verify/frontend_delivery_hardening_runtime_ids.py`（契约绑定 record/company/声明起点态，
  要求唯一匹配）→ `artifacts/backend/acceptance_record_identity.json#lifecycle_project`
  （record 2021 / company 21 / menu 970 / action 1178 / 起点 draft+draft）。

### 探针改动

`scripts/verify/frontend_business_entry_lifecycle_browser.mjs` 改为契约驱动：消费运行时
`ui.contract.v2` 的 `workflowContract.availableActions / rawState / stateField` 与
`dataContract.mainData`；动作方法与标签一律取自契约（不再硬编码 `WALK`/`DECLARED_*`）；
写前 fail-closed 绑定 `system.init` 会话公司、载体起点 `draft/draft` 与公司；
逐态校验契约可用动作与声明 `state_actions` 一致（含 `action_domains.activate` 域门：draft 时不得出现 activate）。

### 复现入口

```
make daily.runtime.lifecycle_fixture.prepare \
  CONFIRM_DAILY_RUNTIME_LIFECYCLE_FIXTURE=DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE \
  SC_ACCEPTANCE_FIXTURE_PASSWORD=123456 \
  DAILY_RUNTIME_EXPECTED_SHA=6c8e07f70c1ce0d501f9f5b56911d74f9321a721

make verify.frontend.business_entry.lifecycle.browser \
  ACCEPTANCE_TARGET_SHA=6c8e07f70c1ce0d501f9f5b56911d74f9321a721 \
  ACCEPTANCE_LOGIN=fixture_role_config_admin ACCEPTANCE_PASSWORD=123456 \
  ACCEPTANCE_RECORD_RESOLUTION=artifacts/backend/acceptance_record_identity.json \
  SC_ENTRY_WRITE_CONFIRM=DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE \
  DB_NAME=sc_demo ACCEPTANCE_BASE_URL=http://1.95.85.92:18081 \
  SC_ACCEPTANCE_OUTPUT_DIR=artifacts/frontend-business-entry-lifecycle/daily-6c8e07f7-r2
```

原始证据：`artifacts/frontend-business-entry-lifecycle/daily-6c8e07f7-r2/summary.json`（正式，受管 run 记录）、
`artifacts/frontend-business-entry-lifecycle/dryrun/summary.json`（只读干跑）、
`artifacts/frontend-business-entry-lifecycle/run1/summary.json`（close 确认弹窗修复前，保留）。

## 工作区卫生（批次收口前）

- 收口前发现 `frontend/apps/web/src/views/SceneView.vue` 存在一处**未记录、未声明**的工作区改动
  （`resolveScene()` 的 `stillOwnsSceneRoute` keep-alive 路由归属守卫）。该文件属于 P0 前端渲染机制，
  本 run 的 goal 已声明 `no_p0_platform_mechanism_change_without_observed_defect`，本批次也没有对应的失败观察，
  故不纳入本批次提交：改动已回退，补丁留存于未跟踪证据区
  `.runtime/reverted/sceneview-keepalive-ownership-20261007.patch`。若后续出现真实观察到的缺陷，
  在独立批次中重新评估，不在本批次夹带。
- 夹具口令仍为既有固定值 `123456`，本批次 diff **未改动任何口令或认证默认**（`git diff` 无 password/认证相关行）。
  口令只经由 `SC_ACCEPTANCE_FIXTURE_PASSWORD` 作用于既有隔离 fixture（`smart_construction_acceptance_fixture`），
  未改变其它环境或通用登录默认。

## 收口验证矩阵（L1/L2，冻结前）

阶段身份：迭代期 = HEAD + dirty scope；冻结后 = 精确 HEAD `425bd830f9dc7eeb969875ca6c0d48e10dea825d`。
本地 receipt 按框架设计对 `environment.kind=runtime` 恒为 advisory `stale`
（`runtime evidence requires authoritative environment readback`），不是门禁；门禁是远端必需检查。

| 层 | 入口 | 结果 | 非零计数 | 说明 |
| --- | --- | --- | --- | --- |
| L1 | `make ci.local.iteration` | PASS | 16 | `change_state=dirty scope=unclassified_by_design coverage=L1_only`；含 `verify.baseline.iteration.execution.policy` |
| L2 | `make verify.daily.runtime.mail_sender.prepare` | PASS | 10 | 发件人受管入口行为单测 |
| L2 | `make verify.daily.runtime.lifecycle_fixture.prepare` | PASS | 17 | 生命周期夹具受管入口行为单测 |
| L2 | `make verify.frontend.delivery_hardening.guard` | PASS | — | 静态守卫 `error_states=12 title_writers=1 async_epoch=enabled` |
| L2 | `py_compile` + `node --check` | PASS | — | `frontend_productization_fixture.py`、`frontend_delivery_hardening_runtime_ids.py`、`frontend_business_entry_lifecycle_browser.mjs` |
| L4 | `make verify.frontend.business_entry.lifecycle.browser` | PASS（重跑） | 6 | 探针选择器加固后重跑；见「F3 复验」 |

未跑层的显式理由：

- L3（受管模块升级 / 运行时冒烟）：本批次未改产品运行时代码；日常服务器仍由
  `make pr.push` 之外的既有主线承载，发布不触发产品部署，故不适用于本轮候选。
- L5（独立复核 / 生成报告 / 完整发布门禁 / 精确头发布）：待本次冻结后由远端必需检查与独立复核执行。

`make ci.delivery.freeze.prepare` PASS（生成报告 `docs/engineering_convergence/` 已刷新并一并提交）。

## 批次 F3 复验：探针选择器去 vendor 耦合（2026-10-07）

### 触发

精确头 `64b3cf6f5f7600f3adbb168ecd67762e76e13ae2` 的远端 `professional_quality_gate` 在
`verify.frontend.playwright_vendor_coupling.guard` 失败：新探针
`scripts/verify/frontend_business_entry_lifecycle_browser.mjs` 有 4 处 vendor 内部选择器
（`.t-message--error`/`.t-alert--error`、`.t-dialog--default … .t-dialog__body`、
`.t-dialog:visible`、`.t-dropdown__item:visible`）。该守卫基线只允许收缩，不允许抬高基线通过。

### 修复（只改探针，不改产品面）

| 用途 | 原（vendor 内部） | 现（声明语义 / 业务事实） |
| --- | --- | --- |
| 错误态文本 | `.t-message--error, .t-alert--error` | `[data-semantic-status="error"], .status-panel.error` |
| 确认弹窗文本 | `.t-dialog--default … .t-dialog__body` | `[data-dialog-purpose="intent-confirmation"], [role="dialog"]` |
| 确认弹窗范围 | `[role="dialog"]:visible, .t-dialog:visible` | `[role="dialog"]:visible` |
| 溢出菜单项 | `.t-dropdown__item:visible` | 按契约标签精确文本定位 `li`（`escapeRegExp` 转义） |

溢出项经核为 TDesign `<li class="t-dropdown__item">`，**无 `role` 属性**，因此不能用角色定位；
改为消费契约声明的动作标签（业务事实），不使用任何 vendor 类名。

### 因断言输入变化而重跑（旧证据作废）

探针是断言的输入，故先前的 `daily-6c8e07f7` 证据不再复用：

1. 载体经 `make daily.runtime.lifecycle_fixture.prepare` 重建 → record **2021**（company 21，起点 draft+draft）。
2. 身份经受管 `odoo.shell.exec` 重新解析 → `artifacts/backend/acceptance_record_identity.json#lifecycle_project`。
3. 全链重跑 → `artifacts/frontend-business-entry-lifecycle/daily-6c8e07f7-r2/summary.json`：
   `ok=true`、`problems=[]`、`console_errors=[]`；`submit→draft, activate→in_progress, complete→done,
   advance_closing→closing, advance_warranty→warranty, close→closed`；
   `via=overflow` 命中 5 次（activate/complete/advance_closing/advance_warranty/close）；
   关闭弹窗真实文案「确认关闭项目 关闭后不可恢复，确定继续吗？」被捕获。

该次重跑同时证明了被动过的四条选择器在真实产品面上确实被消费，而非仅静态存在。

### 过程教训（已纳入后续 L2 选择）

本地 `make ci.local.quick` 不覆盖 `verify.frontend.playwright_vendor_coupling.guard`，
本次漏检因此在远端才暴露。凡改动 `scripts/verify/**` 下的浏览器探针，
必须把 `make verify.frontend.playwright_vendor_coupling.guard` 纳入本轮 L2 定向测试。

## 批次 F4（裁决 B）：发布导航面刻意窄化改为显式声明 + 守卫（2026-10-07）

### 触发与裁决

F3 的「并列发现」事实链：菜单 970 `menu_sc_product_project_lifecycle_v1`（及 376
`menu_sc_project_initiation`）声明持组 `group_sc_cap_project_manager`，`fixture_role_pm`
（uid214）对该组 `has_group=True`，菜单层 ACL 放行；但发布导航面由
`ROLE_SURFACE_OVERRIDES["pm"].primary_menu_xmlids`（24 项白名单）驱动，这两项不在其中，
发布面拒绝。两侧口径不同不是偶然，而是**产品刻意窄化**。

所有者裁决 **B**：登记为显式声明，**不算缺陷、不放宽验收断言、不擅自补菜单**，并加守卫锁住
「角色能力组可达但未注册交付面」的分歧。

### 责任层与边界

- Formal Product Layer：P1（施工行业标准产品的角色发布面声明）。
- Layer Target：`config/frontend/role_surface_exposure_declarations_v1.json`（新增声明）、
  `scripts/verify/role_surface_exposure_declaration_guard.py`（新增守卫）。
- 不改：`ROLE_SURFACE_OVERRIDES` 白名单、`config/frontend/authoritative_navigation.json`、
  任何 ACL / record rule / 字段权限 / 验收断言 / 前端渲染 / 契约 schema。

### 声明的语义（口径可复算）

- 能力可达 = 角色**身份组闭包**（`implied_ids` 传递闭包）∩ 入口逐层声明组与 `action_groups`。
  入口声明来自 `docs/product/frontend_business_entry_acceptance_v1.csv` 的 `role_authority`
  （`all_restricted_layers_must_match_one_group`）。
- 身份组取**受管夹具身份**（`addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py`），
  无夹具身份的角色回落到其角色组并显式记录证据来源（`identity_evidence`）。
- 发布面 = `ROLE_SURFACE_OVERRIDES[role]` 的 `primary_menu_xmlids ∪ role_home_menu_xmlids − denied_menu_xmlids`。
- 交付模式：`declared_whitelist`（白名单交付）/ `capability_discover`（可达即交付）/
  `denied`（`deny_all_navigation`，一律不交付）。

### 结果（登记表实际内容，非人工估计）

| 角色 | 交付模式 | 能力可达 | 交付 | 窄化声明 |
| --- | --- | ---: | ---: | ---: |
| restricted | denied | 19 | 0 | 19 |
| project_member | declared_whitelist | 33 | 5 | 29 |
| business_full | capability_discover | 83 | 可达即交付 | 0 |
| business_config_admin | capability_discover | 83 | 可达即交付 | 0 |
| owner | declared_whitelist | 24 | 2 | 22 |
| pm | declared_whitelist | 38 | 3 | 35 |
| finance | declared_whitelist | 47 | 15 | 32 |
| executive | declared_whitelist | 48 | 0 | 48 |
| cost | declared_whitelist | 24 | 4 | 22 |

- 入口全集 89 行：86 行可由当前契约解析，3 行（`account.menu_action_move_journal_line_form` /
  `menu_action_account_moves_all` / `menu_action_account_form`）`role_authority` 仍为
  「待从当前契约核对」→ 登记在 `authority_pending_entries`，**显式保留为缺口**，不静默丢弃。
- `capability_reachable_by_no_role` = 3：`menu_sc_product_data_permission_v1` /
  `menu_sc_product_numbering_rule_v1` / `menu_sc_product_system_parameter_v1`
  （仅存在、无任何业务角色交付）。
- `delivered_without_declared_capability`（反方向分歧，同样登记）：
  `project_member` 1 项（875 班组借/扣款登记工作台）、`cost` 2 项
  （`menu_sc_p1_daily_contract`、`menu_sc_certificate_registration`，需业务发起能力）。
- `system_admin` 列在 `excluded_roles`：`base.group_system` 属 Odoo 核心模块、不在本仓库源码内，
  无法静态求闭包，显式排除并记录理由。

### 守卫行为（fail-closed，锁定消费与行为）

`scripts/verify/role_surface_exposure_declaration_guard.py` 静态重算上述集合并要求与登记表**完全相等**；
以下任一项漂移即失败：登记表缺角色、`delivery_mode` 与策略标志不符、身份组不可解析、
窄化声明多一项/少一项、反向分歧未登记、`no_role` 集合变化、待解析入口变化、
新入口进入验收全集而未登记。单测 `scripts/verify/test_role_surface_exposure_declaration_guard.py`
（10 项：9 项负例 + 1 项仓库现状断言）。

负例实证（临时抽掉 `pm` 一条窄化声明 → 守卫 exit=2）：

```
- pm: capability_reachable_not_delivered drift undeclared=['smart_construction_core.menu_sc_workbench_my_todo_fact'] stale=[]
```

### 挂载

| 层 | 入口 | 结果 | 非零计数 |
| --- | --- | --- | --- |
| L1/L2 | `make verify.frontend.role_surface_exposure_declaration.guard` | PASS | 10 |
| L2 | `make verify.frontend.release_navigation_policy.guard`（现依赖上一项） | PASS | 10 + 5 |
| L2 | `make verify.guard.registry` | PASS | 1389 scripts |
| L2 | `make ci.generated_reports.guard` | PASS | 1467 assets |
| L2 | `make verify.contract.structure_lock` | PASS | 14 domains |

- `verify.frontend.release_navigation_policy.guard` 是 `frontend_static_release_audit.py` 的必需检查项，
  因此新守卫自动进入 `frontend_release_gate`；同时把新目标追加进
  `ci.professional.backend.shard-verify` 依赖串，使其在远端 shard-verify 直接覆盖
  （教训：本地 `ci.local.quick` 不覆盖该层）。
- 生成物刷新：新增 2 个 `scripts/verify/**` 资产 → `make refresh.generated_reports` 更新
  `docs/engineering_convergence/test_inventory.csv|_summary.md`（1465→1467）与
  `complexity_budget_report.md`（扫描文件 4600→4602）；`contract_structure_fingerprint.json` 未变。

### 未放宽的证明

- 未改任何 ACL / 菜单持组 / `authoritative_navigation.json` / 验收断言；`frontend_release_navigation_policy_guard`
  在 `roles=4 released_leaf_identities=84` 下仍 PASS。
- 声明文件不产生任何运行态可见性变化，只是把既有刻意窄化写成可复算、可失败的契约。
- 守卫不把「选择器字符串/像素值文本出现」当作正确性证明：它比较的是集合等式与声明模式。

## 批次 F4 收口：付款申请入口明细行身份（2026-10-07）

### 结论

`docs/product/frontend_business_entry_acceptance_v1.csv` 第 47 行
`smart_construction_core.menu_sc_user_payment_apply`（付款申请）由 `partial_passed` 更新为
`passed`：该行 `gap` 原记录的「多行付款申请编辑已有明细行后保存被判为重复行、不发写请求」
在 daily 修订 `6c8e07f7` 上**已不可复现**，并由受管探针从产品面与持久化结果证明。

### 根因（先证伪，再定性）

原阻断描述的「首个业务列作行身份」实现，已在 PR #525 被身份式判定取代
（`frontend/apps/web/src/pages/contractForm/one2manyUtils.ts` 的 `one2manyRowCollectionIdentity`
与 `collectOne2manyDraftValidationFromRows`）；`git merge-base --is-ancestor 2d164a1f 6c8e07f7`
成立，即 daily 已含该修复。导入处理器写入的常量列（`来源类型=结算单明细`）不再承担行身份。
因此本批次**不改任何校验语义**，只把「原阻断是否仍存在」用产品面证据定性。

### 并列根因（本轮真正的阻断）：受管记录身份漂移

首次重跑探针时报「the record form did not expose the declared detail collection」。
定位：`artifacts/backend/acceptance_record_identity.json` 是上一轮**人工拼装**的裸 payload
（顶层直挂 `payment_request`，无 `schema/targets` 信封），其中 `record_id=36166`；
而 2026-10-07 08:38 的夹具重建（`make daily.runtime.lifecycle_fixture.prepare`）已把该行重建为
`36168`。**身份漂移 → 路由指向不存在的记录 → 明细集合不存在**，与产品缺陷无关。

同时暴露契约不一致：仓库里两个受管写入器（`make verify.dev.acceptance.record_identity.resolve`、
`make daily.dev.acceptance_contract.resolve`）写的是规范信封 `{schema,producer,expected_sha,targets}`，
而两个浏览器消费端读的是顶层裸键。

### 处理（体系化，不放宽）

1. **新增受管入口** `make daily.runtime.record_identity.resolve`
   （`scripts/ops/daily_runtime_record_identity_resolve.py`，单测 26 项）：复用既有注册环境
   （ssh `sc-root` + 远程受管 `make odoo.shell.exec`），把**工作树**的既有解析器
   `scripts/verify/frontend_delivery_hardening_runtime_ids.py` 送入远程执行，写规范信封，
   fail-closed：远端 HEAD ≠ 声明 SHA、served revision/database 不一致、payload 缺失或目标缺键时
   拒绝写入（**不覆盖既有工件**）。不新建环境/库/端口/凭据。
2. **消费端口径统一**：两个浏览器探针改为读规范信封 `body.targets.<key>`，
   并在 `targets` 缺失时 fail-closed（不再接受裸 payload）。
3. **身份重新解析**：`payment_request.record_id=36168`、`lifecycle_project.record_id=2022`，
   与夹具重建后的实际值一致；`producer`/`expected_sha` 绑 `6c8e07f7`。

### 复现入口

```
make daily.runtime.record_identity.resolve \
  CONFIRM_DAILY_RUNTIME_RECORD_IDENTITY=RESOLVE_DAILY_SC_DEMO_RECORD_IDENTITY \
  DAILY_RUNTIME_EXPECTED_SHA=6c8e07f70c1ce0d501f9f5b56911d74f9321a721 \
  DAILY_RUNTIME_DATABASE=sc_demo \
  ACCEPTANCE_RECORD_RESOLUTION=artifacts/backend/acceptance_record_identity.json

make verify.frontend.business_entry.payment_request.browser \
  ACCEPTANCE_TARGET_SHA=6c8e07f70c1ce0d501f9f5b56911d74f9321a721 \
  ACCEPTANCE_BASE_URL=http://1.95.85.92:18081 DB_NAME=sc_demo \
  ACCEPTANCE_LOGIN=fixture_role_finance ACCEPTANCE_PASSWORD=123456 \
  ACCEPTANCE_RECORD_RESOLUTION=artifacts/backend/acceptance_record_identity.json \
  SC_ENTRY_WRITE_CONFIRM=DRIVE_DAILY_SC_DEMO_PAYMENT_REQUEST_ONE2MANY \
  SC_ACCEPTANCE_OUTPUT_DIR=artifacts/frontend-business-entry-payment-request/daily-6c8e07f7
```

### 证据（受管探针，绑定声明消费与持久化结果）

`artifacts/frontend-business-entry-payment-request/daily-6c8e07f7/report.json`（`ok=true`、`problems=[]`）：

| 阶段 | 观察 | 断言 |
| --- | --- | --- |
| after_introduce | 从 2 个声明结算单各引入 1 行，共 2 行；10 列含「本次申请」；全部行的首列值相同（常量前置条件成立） | 行数=2；列含声明列；首列常量 |
| save(编辑行) | 「本次申请」200→150；无重复行提示；`data-validation-visible=false`；`待提交：无变更`；`api.data(payment.request)` HTTP 200 | 不得出现重复行/校验阻断；必须发写请求且成功 |
| readback_after_save | 重新加载后该单元格 = 150，行数=2 | 持久化值等于声明值 |
| restored | 产品面删行 + 复位申请金额 20.00 | `row_count=0`、`amount=20.00`（声明空态） |

补充：解析体口径对齐后，生命周期探针的**只读干跑**（不重跑对象 3 的产品验收）
`.runtime/business-entry-lifecycle/dryrun-canonical` `ok=true`，证明 `targets.<key>` 读取路径可用。

### 环境与夹具身份

- served revision/database：`6c8e07f7…` / `sc_demo`（与解析体 `expected_sha` 一致）。
- 载体由**声明 xmlid** 绑定：`smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a`，
  探针按 xmlid 校验解析体，不硬编码数字 id。
- 写入仅限该声明载具（引入/编辑/删行/复位金额），结束态回到声明空态；未改 ACL、字段权限、发布导航或断言。
- 夹具口令仍为既有固定值 `123456`，只作用于既有隔离 fixture，未改其它环境或通用登录默认。

## 批次 F3 收口：日常合同入口闭环（2026-10-07）

### 结论

`docs/product/frontend_business_entry_acceptance_v1.csv` 第 38 行
`smart_construction_core.menu_sc_p1_daily_contract`（日常合同，`sc.general.contract`，menu 907 / action 669）
由 `partial_passed` 更新为 `passed`。声明阶梯经真实产品入口走通：
draft →（submit / `action_confirm`）confirmed →（complete / `action_signed`）signed，终态零动作；
列表查询/筛选/分页与详情返回上下文、授权边界均已核实并回读，`problems=[]`、`console_errors=[]`。

### 根因修复（P1 契约投影缺陷，提交 `f7b7c2ee`）

`addons/smart_construction_core/models/support/workflow_contract_service.py` 的 `sc.general.contract`
profile 原先声明 `"signed": ["cancel"]`，但 `general_contract.py` 的 `action_cancel` 只接受 `draft/confirmed`，
且 `test_p0_state_closure.test_general_contract_blocks_invalid_anchor_or_terminal_cancel` 锁定该终态拒绝 →
投影发布了唯一结果只会抛 `UserError` 的按钮。修复为 `"signed": []`（附注释）。
未改 `action_cancel`、未放宽断言/ACL/字段权限、无模型特判。新增
`test_general_contract_signed_declares_no_transition`（直接以 `state="signed"` 建记录，断言
`availableActions==[]` 且 `action_cancel` 抛 `UserError`）。本地 A/B：旧代码 FAIL、修复后 PASS
（`.runtime/final-acceptance/business-entry-general-contract/local-l2-{with-fix,baseline}.log`）。

### daily 部署（受管入口）

`make daily.runtime.candidate.bundle_sync` → `make daily.runtime.source_revision.align`，日常开发服务器现服务
`f7b7c2ee` / `sc_demo`（`.runtime/final-acceptance/daily-deployed/{candidate-bundle-sync,source-revision-align}.json`）。

### 载体与身份（受管解析，不硬编码 1722/1723）

- 新增可重置载体 `smart_construction_acceptance_fixture.fe_general_contract_carrier`
  （`FE General Contract Carrier`，company A=21；非 draft 且被业务行引用时 fail-closed 拒绝 unlink）。
- `make daily.runtime.record_identity.resolve` → `artifacts/backend/acceptance_record_identity.json#general_contract_carrier`
  （xmlid 校验 + 唯一匹配 + 声明起点 `state=draft` 绑定；验收时 record 1722，复位重建后 1723）。

### 探针

`scripts/verify/business_entry_general_contract_browser.mjs`（契约驱动：消费运行时 `ui.contract.v2` 的
`workflowContract.availableActions / rawState / stateField` 与 `dataContract.mainData`，方法名取自契约）。

### 证据

`artifacts/frontend-business-entry-general-contract/daily-f7b7c2ee/summary.json`（`ok=true`、`problems=[]`、`console_errors=[]`）：

| 阶段 | 观察 | 断言 |
| --- | --- | --- |
| initial | rawState=draft, mainData.state=draft, company=21, editability=editable | 起点等于声明 `draft`，会话公司等于声明公司 |
| list_query | 搜索 `FE-GC-CARRIER` 命中 1 行 | 唯一匹配 |
| paging | mode=paged，共 3 条（1 页） | 分页面按声明渲染，未越界 |
| detail_return | 返回后搜索词恢复 `FE-GC-CARRIER`、行数恢复 1 | 详情返回恢复同一过滤上下文 |
| submit | 声明动作 `submit`→`action_confirm`；draft→confirmed；后续 offered=[complete,cancel] | rawState/mainData 等于声明后继 `confirmed` |
| complete | 声明动作 `complete`→`action_signed`；confirmed→signed；后续 offered=[] | rawState/mainData 等于声明后继 `signed` |
| terminal | signed：`declared_actions=[]`、`offered=[]` | 终态零动作（`cancel` 不再出现） |
| authority_negative | `fixture_role_finance` → `/access-denied?reason=NAVIGATION_AUTHORITY_DENIED`，渲染 0 行 | 无声明组角色不得进入本入口 |

干跑（只读、不写入）`artifacts/frontend-business-entry-general-contract/daily-f7b7c2ee-dryrun/summary.json` 同样 `ok=true`。

### 运行时契约事实（非缺陷，记录以对齐口径）

FE Company A(21) 无 `sc.general.contract` 生效审批策略（daily 的 `general_contract_approval` 为
`company_id=1` 且 `mode=none / required=False`），故本入口声明机器在验收公司下不存在审批档位，
`submit` 直达 `confirmed`；探针以运行时契约声明为准，未引入或伪造审批事实。

### 残留（不在本行收口口径内）

页面级附件上传/下载旅程、超出既有两个角色（`fixture_role_config_admin` / `fixture_role_finance`）
的完整权限矩阵，由后续批次按同一矩阵口径补足。

### 复现入口

```
make daily.runtime.lifecycle_fixture.prepare \
  CONFIRM_DAILY_RUNTIME_LIFECYCLE_FIXTURE=DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE \
  SC_ACCEPTANCE_FIXTURE_PASSWORD=123456 \
  DAILY_RUNTIME_EXPECTED_SHA=f7b7c2eefbbb1ffbfd2ac304108c28166419c9ef DAILY_RUNTIME_DATABASE=sc_demo

make daily.runtime.record_identity.resolve \
  CONFIRM_DAILY_RUNTIME_RECORD_IDENTITY=RESOLVE_DAILY_SC_DEMO_RECORD_IDENTITY \
  DAILY_RUNTIME_EXPECTED_SHA=f7b7c2eefbbb1ffbfd2ac304108c28166419c9ef DAILY_RUNTIME_DATABASE=sc_demo \
  ACCEPTANCE_RECORD_RESOLUTION=artifacts/backend/acceptance_record_identity.json

make verify.frontend.business_entry.general_contract.browser \
  ACCEPTANCE_TARGET_SHA=f7b7c2eefbbb1ffbfd2ac304108c28166419c9ef \
  ACCEPTANCE_BASE_URL=http://1.95.85.92:18081 DB_NAME=sc_demo \
  ACCEPTANCE_LOGIN=fixture_role_config_admin ACCEPTANCE_PASSWORD=123456 \
  ACCEPTANCE_RECORD_RESOLUTION=artifacts/backend/acceptance_record_identity.json \
  SC_ENTRY_WRITE_CONFIRM=DRIVE_DAILY_SC_DEMO_GENERAL_CONTRACT \
  SC_ACCEPTANCE_OUTPUT_DIR=artifacts/frontend-business-entry-general-contract/daily-f7b7c2ee
```
