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
| paging | 声明语义面 `mode=paged`、`state=ready`、`region_label=列表分页`、`共 3 条`、`rows=3` | 分页声明与列表数据一致（total ≥ rows）；交互换页不可用并已显式记录（页脚不暴露公共页控件，列表路由不接受 page/page-size 查询） |
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
的完整权限矩阵，以及可交互的换页（当前数据集仅 1 页且页脚无公共页控件），由后续批次按同一矩阵口径补足。

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

---

## 轮次增补：设计系统语义身份契约收口（2026-10-07）

### 根因（本轮实证，纠正上一轮假设）

列表/看板入口的 `ProductListSurface`、`CollectionKanbanRecordCard`、`ProductAppShell` 在真实 DOM 中
根本不可寻址：`ScCard`、`ScButton`、`ScIconButton` 三个原语把 `v-bind="$attrs"`（或
`v-bind="{ ...$attrs, ...semanticPrimitiveIdentity(...) }"`）放在静态身份之前，消费方在消费点声明的
`data-semantic-component` 被原语默认值覆盖，于是消费方身份被“吞掉”。

- 实测：`ProductListSurface` 未渲染（被 `ScCard` 吞）、`CollectionKanbanRecordCard` 被吞（看板卡片计数 0）、
  页面骨架 `ProductAppShell` 被吞。
- 实测反证：`ScCheckbox`/`ScLayout`/`ScFooter`/`ScAside` 不吞（消费方胜出），
  `CollectionSelectionControl` 实际渲染 7 个、`data-selection-scope` 存在。
  因此上一轮“列表选择框定位超时＝身份被吞”的判断不成立，选择框身份一直正常。
- Vue 语义实证（`@vue/runtime-core@3.5.27` / `@vue/compiler-sfc@3.5.27`）：fallthrough `$attrs` 在
  `cloneVNode` → `mergeProps(props, extraProps)` 中后者胜；模板里静态属性写在 `v-bind="attrs"` 之前则静态胜
  （编译器保持属性顺序）。

### 契约裁决

`data-semantic-component` = 该节点的**归属组件**，遵循平台属性约定：消费方在消费点上声明即合法胜出。
因此每个原语必须**恒定发布 `data-semantic-primitive`**（稳定原语标记），否则消费方的合法声明会让原语本身
不可寻址。不新增 `data-primitive-component`（与 `data-primitive-driver` 视觉混淆）。

`ScDialog` 的既有守卫本来即规定“消费方不得用 `data-semantic-component` 覆盖”，现改述为“不得占用归属标记，
请用 `data-dialog-purpose`”。

### 改动

- `primitiveAdapter.ts`：`semanticPrimitiveIdentity` 返回 `{data-semantic-component, data-semantic-primitive,
  data-semantic-layer}` 并写入契约注释。
- 17 个原语的 `{ ...$attrs, ...semanticPrimitiveIdentity(X) }` 翻转为身份优先；37 个原语补
  `data-semantic-primitive`；`ScButton`/`ScIconButton`/`ScDialog`/`ScDrawer` 改为“静态身份在 fallthrough 之前”。
- `ScFormItem` bare 分支只加 `data-semantic-primitive`（加 `data-semantic-component` 会新激活
  `[data-semantic-component='ScFormItem']` 样式，属契约外行为变更）。
- 守卫 `frontend_primitive_adapter_guard.py` 新增两条断言：缺 `data-semantic-primitive`、`$attrs` 在身份默认之前
  均报错；测试 helper 桩同步为真实规范形态。

### 验证（L1/L2，未部署）

| 入口 | 结果 |
| --- | --- |
| `verify.frontend.primitive_adapter.unit` | passed：契约测试 `components=46 eventCases=11`、单测 41/41、守卫 `PASS components=46` |
| `verify.frontend.component_driver_takeover.unit` | passed 13/13（生成清单已按受管入口 `refresh.frontend.component_driver_takeover.inventory` 重算） |
| 受影响消费方单测（kanban card / selection control / overlay lifecycle / product page pattern / collection view semantics / list surface search / row cell / row action identity / action toolbar / aggregate footer / page header / mobile record row / navigation controls / low-code dialog / form header actions / native form action+structure / action view actions / relational actions / state dashboard / navigation shell / professional registry / professional detail collection / global component capability / official icon / native text） | 全部 passed |

### 预先存在、非本轮引入（已有基线对照）

- `verify.frontend.standard_shell_composition.unit`：断言 `AppShell.css` 含
  `width: min(340px, calc(100vw - 44px))`，该文件未修改且 HEAD 与 main(`c3979912`) 均无此串。
- `verify.frontend.standard_collection_composition.unit`：断言 `ListPage.vue` 含
  `<ProductListSurface v-else-if="status === 'empty'">`，该文件未修改且 HEAD 与 main 均无此串。
- `verify.frontend.rendering_detail_state.unit`：三份 rendering-detail 生成清单在 HEAD 已 stale
  （暂存改动后逐项复核），与本轮无关；run 中已有 `rendering_detail_state` 排除裁决。
- 以上三项均不在 CI 必需门（`frontend_release_gate` 走 `pnpm test`/`test:release`）内。
  按规则不在本批次修复。

### 探针补强

- `business_entry_matrix_browser.mjs`：按声明展示形态选择就绪面（table→`ListPage[data-list-status]`，
  kanban→`KanbanPage[data-collection-state]`）；渲染记录数按展示形态读取；单入口失败改为
  per-entry try/catch，绑定到该入口并继续覆盖同批其余入口，不再中断整批。

### 下一步

1. 提交候选。
2. 经受管入口重建/刷新日常运行为态产物并重新声明 served revision。
3. 在日常运行时对刷新后的候选运行 `verify.frontend.business_entry.matrix.browser`，确认
   `ProductListSurface`/`CollectionKanbanRecordCard`/`ProductAppShell` 身份恢复且
   `CollectionSelectionControl` 不变。
4. 按域继续剩余 `not_run` 行。**不标记分支目标完成**。

---

## 89 入口矩阵域级收口（f4279416，2026-10-07）

本轮把矩阵从「表格/看板二元假设」推进到**声明驱动 + 登记表消费**，并把负例授权判定改为
运行态权威能力闭包。全部验证在受管日常运行时进行（`http://1.95.85.92:18081`、ENV=dev、
DB=`sc_demo`、served `f4279416`、受测角色 `fixture_role_config_admin`/公司21）。

### 五类根因与处理

1. **配置工作台入口未识别（原 `unknown-presentation`）**：根因是动作
   `action_sc_business_config_workbench` 用 `context.sc_web_route=/admin/business-config`
   声明了工作台面，而 CSV 仍声明 `tree:table; form:form_structure`（产物声明过期）。
   处理：探针新增声明驱动的 `admin` 适配器，读取页面根 `data-product-page-mode="admin"`
   （就绪属性 `data-page-sections-ready`）；同时把 CSV 该行 `rendering_path` 改为
   `admin:business_config_surface [declared: action context sc_web_route=...]`。非入口特判。
2. **产品配置 3 行 NOT-IN-NAV**：事实为菜单声明 `group_sc_cap_config_admin`，而
   `group_sc_role_business_admin` 闭包仅到 `group_sc_cap_business_config_admin`；
   受管登记表已按「仅存在、无人交付」登记为 `capability_reachable_by_no_role`。
   处理：探针消费登记表判定为 `declared`（带登记原因），**未放宽断言、未改动菜单/ACL**；
   CSV 记 6. 行状态 `declared` 并写明产品侧待裁决。
3. **阻塞清单 3 行 account**：登记表 `authority_pending_entries` 已登记为待解析。
   处理：同样按登记判定 `declared`，不静默丢弃也不放宽。
4. **负例授权泄漏（`fixture_role_finance` 收到 `action_sc_invoice_input`）**：根因是 overlay
   手写的角色能力闭包过期（只列身份组、漏传递闭包）。处理：删除手写闭包，改为读取登录信封
   `principal.role_xmlids`（运行态发布的完整生效组闭包），候选仅当闭包与入口声明组**不相交**
   才作为有效负例；`fixture_role_finance` 因此不再是该入口的负例。overlay 仅保留候选登录清单。
5. **空态权威计数**：对空态入口的 42 个模型在受管 odoo.shell 内以受测角色执行
   `with_user(uid).search_count([])` 与 `sudo().search_count([])`：34 个模型全库 0 行（真实空态），
   8 个模型存在他公司数据（`account.journal`/`hr.department`/`project.cost.ledger`/`sc.expense.claim`/
   `sc.invoice.registration`/`sc.tax.deduction.registration`/`ui.form.field.policy` 全属公司1，
   `project.progress.entry` 1 行无公司），受测公司21 作用域排除，属**作用域边界**而非产品零数据。

### 负例覆盖的结构性事实

16 个入口的声明组含基线能力 `group_sc_cap_project_read`，而被测的 8 个夹具角色闭包**全部**持有该能力，
故在当前角色模型下不存在可断言的负例角色；3 个 account 行 `role_authority` 未声明可否定组。
两类共 19 个入口以显式 observation 记录「负例不可构造」及阻断能力组，**不伪造通过**。

> 已被 2026-10-07 `ce8b77bf` 轮次取代：见文末「负例授权覆盖闭环」。上述「不存在可断言的负例角色」
> 只对**当时**的候选集与判定成立（当时不要求负例角色真的收到发布导航）；补齐平台技术面身份并把
> 「收到 0 条发布导航目标的候选」判为不合格后，19 个入口均已实测断言，`uncovered_entries=0`。

### 验证

| 入口 | 结果 |
| --- | --- |
| `verify.frontend.business_entry.matrix.browser`（全量 80 行） | `ok=true entries=80 problems=0 console_errors=0`；分布 table:ok 11 / table:empty 52 / hierarchical:ready 4 / hierarchical:empty 1 / form:ok 3 / aggregate:ok 1 / aggregate:empty 1 / admin:true 1 / declared 6 |
| 负例授权 | project_a_member 49 + contract_operator 10 + executive 2 = 61 入口已断言 0 泄漏；19 入口不可构造（见上） |
| `make ci.local.iteration` | PASS（L1，推荐 L2） |
| `verify.frontend.role_surface_exposure_declaration.guard` | PASS roles=9 universe=86 pending=3 no_role=3 |
| `verify.frontend.release_navigation_policy.guard` | PASS roles=4 released_leaf_identities=84 |

### 证据落盘

- `artifacts/frontend-business-entry-matrix/daily-f4279416-matrix/summary.json`（权威全量报告）
- 空态权威计数：受管 odoo.shell 批量输出（本轮临时 `/tmp/empty_counts.out`，CSV `evidence` 已内联结论）

### 下一步（未完成）

1. 产品配置 3 行「仅存在无人交付」需产品侧裁决（是否收敛发布面或调整声明组）。
2. 19 个入口的负例覆盖需产品侧确认是否引入受限身份或调整声明组，方可闭环负例断言。
3. 提交候选后按受管入口补 `agent.run.record`；**仍不标记分支目标完成**，走 PR 集成。

## 轮次增补：产品配置入口按「可配置属产品功能」交付（owner decision B，2026-10-07）

### 裁决

产品配置（数据权限 / 系统参数 / 编码规则）是**产品功能**，应由业务配置管理员角色
（`group_sc_role_business_admin` → `group_sc_cap_business_config_admin`）交付，
而不是登记为「仅存在、无人交付」的发布面缺口。

### 事实（运行态实测，非推断）

- 日常运行时（served `f4279416`）`fixture_role_config_admin`（uid216，role `business_config_admin`）
  发布面 86 actions / 108 nodes，「产品配置」下仅 表单配置(1014)/流程审批配置(699)/字段管理(839)。
- 同角色 `wutao`（uid16）发布面 89 actions / 111 nodes，**已包含** 数据权限(1201)/系统参数(1202)/编码规则(1203)
  —— 因其原生持有行业配置能力 `group_sc_cap_config_admin`。即真实产品面已交付，缺失的是**声明角色面**。
- 三个入口的菜单/动作声明组仅 `group_sc_cap_config_admin`，而规范业务配置管理员角色不持有它。

### 责任层与改动（P1 施工行业标准产品入口面）

- `views/menu_product_contract_completion_v1.xml`：三个 action 与 menuitem 的组声明**追加**
  `group_sc_cap_business_config_admin`（保留 `group_sc_cap_config_admin`；后者已 implied 前者，行业能力可达性不变）。
- `security/ir.model.access.csv`：为 `group_sc_cap_business_config_admin` 复刻既有
  `sc.product.system.settings`(1,1,1,1) 与 `ir.sequence`(1,1,0,0) 授权；未改既有规则。
- `core_extension_policy_maps.py`：把三个叶子 xmlid 加入 `business_config_admin.admin_menu_xmlids`，
  使**声明角色面**与真实产品面一致。
- `config/frontend/role_surface_exposure_declarations_v1.json`：`capability_reachable_by_no_role` 清空，理由记 owner decision B。
- `tests/test_data_permission_surface.py`：旧断言（锁定 business_admin 看不到权限菜单）改写为正向交付断言
  （业务/行业管理员均可见三个入口，`project_read` 成员不可见）。

未放宽任何断言/ACL/字段权限/负例，无模型特判；正式 4 业务角色发布面不变（84 leaves）。

### 日常运行时验证（served `aed39bc5` / `sc_demo`，候选提交 `aed39bc5`）

| 项 | 结果 |
| --- | --- |
| `daily.runtime.candidate.bundle_sync` | PASS（bundle `d087a30a`，old `f4279416`） |
| `daily.runtime.source_revision.align` | PASS（served `aed39bc5`） |
| 远端 `make mod.upgrade MODULE=smart_construction_core` | EXIT=0（registry 134.9s） |
| 运行态回读：`fixture_role_config_admin` 发布面 | **86→89**，出现 数据权限(1201)/系统参数(1202)/编码规则(1203) |
| 运行态回读：`wutao` 发布面 | **89（不变）** → 日常导航政策 `min=max=89` 未被击穿 |
| `verify.frontend.business_entry.matrix.browser`（三键定向） | `ok=true entries=3 problems=0 console_errors=0` |
| 负例授权 | `fixture_role_project_a_member`（闭包 12）对三入口 `leaked_entries=[]` |
| `role_surface_exposure_declaration_guard` | PASS `no_role=0`（原 3） |
| `release_navigation_policy_guard` | PASS `roles=4 released_leaf_identities=84`（不变） |
| `ci.local.iteration` | PASS（L1_only，dirty） |

CSV 第 88/89/90 行 `declared` → `passed`（矩阵合计 86 passed + 3 declared）。

### 证据落盘

- `artifacts/frontend-business-entry-matrix/daily-aed39bc5-matrix/summary.json`
- `.runtime/final-acceptance/daily-deployed/candidate-bundle-sync.json`、`source-revision-align.json`

### 下一步（未完成）

1. 剩余唯一 OPEN：19 入口负例覆盖限制（16 声明 `group_sc_cap_project_read` + 3 account 无组），需受限夹具身份或声明组的产品/治理裁决。
2. 待所有者授权分支目标后，跑一次冻结候选 Quick 并发起 Gitee PR；**不标记分支目标完成**。

### 部署身份（最终）

日常运行时服务**本分支 tip**。产品改动在代码提交 `aed39bc5` 上完成部署与验证（bundle `d087a30a`，模块升级
registry 134.9s，上述运行态回读与三键矩阵均在该身份取得）；其后的 delta 仅为 `.agent/` + `docs/` 台账，
`addons/`、`config/`、`scripts/` 运行相关文件集**未变**，故按确定性影响分析复用已取得的运行证据，
不重复跑矩阵。

## 轮次增补：负例授权覆盖闭环（`ce8b77bf`，2026-10-07）

### 结论

原 run 的**唯一 OPEN 项**（19 入口负例覆盖）已彻底收口：19/19 实测断言，`uncovered_entries=0`。
同时修正了上一轮的一处**假通过**。

### 根因（上一轮为何是假通过）

- 上一轮把 `fixture_role_partner_manager` 作为 16 个 project-baseline 入口的负例基线。该身份确实是
  唯一不含 `group_sc_cap_project_read` 的已声明 SC 角色，但**运行态不给它任何发布导航**：登录信封发布
  了 12 个能力组，`system.init.navigation.nav` 为空。
- 探针对候选只判 `!observed.nav`，而 `Boolean([]) === true`，空导航因此混过；随后
  `findReleasedNavigationTarget(observed.nav, action)` 对任意 action 恒为 `null`，
  `leaked_entries=[]` 变成**空洞成立**，并非被检验过的拒绝。
- 结构事实（源码组闭包核验）：发布面角色触发组
  `business_full / owner / executive / project_manager / project_user / finance_manager / finance_user / cost /
  group_sc_cap_business_config_admin` **全部**传递蕴含 `group_sc_cap_project_read`；唯一不蕴含的
  `group_sc_role_partner_manager` 未被映射到任何交付面，因此拿不到导航。

### 修复（不放宽任何断言/ACL/字段权限/负例，无模型特判，未改产品角色与能力组）

1. **探针加固** `scripts/verify/business_entry_matrix_browser.mjs`：负例候选**必须真的收到 ≥1 条发布导航目标**
   （含正 `action_id`+`menu_id` 的节点）才合格；不合格候选记 `authority_negative_candidate` 观察项，
   **不再计作拒绝**；`authority_negative_summary.uncovered_entries > 0` 直接 fail-closed。
   这样「空导航」在结构上不可能再伪造通过。
2. **夹具对齐产品能力** `addons/smart_construction_acceptance_fixture/tools/frontend_productization_fixture.py`：
   新增 `fixture_role_system_admin`（平台技术面，能力闭包 9，**不含** `group_sc_cap_project_read`，
   运行态收到 2 条发布导航目标）——它是**可判别**的负例基线：该主体能正常导航（证明导航链路已投递），
   却收不到 16 个 project-baseline 入口。
   `fixture_role_partner_manager` 保留为**不合格候选回归样本**（证明加固生效）。
3. overlay `scripts/verify/business_entry_matrix_overlay.json` 增加
   `fixture_role_system_admin`；`scripts/verify/frontend_productization_fixture.py` 的 `LOGINS` 同步补登。

### 运行态验证（served `ce8b77bf` / `sc_demo`）

| 项 | 结果 |
| --- | --- |
| `daily.runtime.candidate.bundle_sync` | PASS（old `e57e4990` → source `ce8b77bf`） |
| `daily.runtime.source_revision.align` | PASS（served `ce8b77bf`，restarted，未回滚） |
| 远端 `make daily.dev.acceptance_fixture.ensure` | PASS `db=sc_demo`（含新身份重建） |
| `verify.frontend.business_entry.matrix.browser`（19 键定向） | `ok=true entries=19 problems=0 console_errors=0` |
| `authority_negative_summary` | `checked_entries=19 uncovered_entries=0` |
| 负例 `fixture_role_system_admin`（闭包 9） | `checked_entries=16 leaked_entries=[]`（导航已发布，真实拒绝） |
| 负例 `fixture_role_project_a_member`（闭包 12） | `checked_entries=3 leaked_entries=[]` |
| 不合格候选 | `fixture_role_executive`、`fixture_role_partner_manager` 均记 `released_navigation_targets=0` |
| `role_surface_exposure_declaration.guard` | PASS `roles=9 excluded=1 universe=89 pending=0 narrowed=211 no_role=0` |
| `release_navigation_policy.guard` | PASS `roles=4 released_leaf_identities=84`（正式 4 业务角色发布面不变） |
| `ci.local.iteration` | PASS（dirty，L1_only） |

CSV：3 个 account 行 `declared→passed`、`阻塞→本轮验收`，`role_authority` 记为真实
`account.group_account_invoice / group_account_readonly / group_account_manager` 菜单链；
16 个 project-baseline 行的 evidence 由「负例不可构造」改为实测结论。**矩阵现为 89/89 passed**。

### 证据落盘

- `artifacts/frontend-business-entry-matrix/daily-ce8b77bf-negative-19/summary.json`（19 键定向 + 负例断言）

### 未完成

- 本分支目标**仍未完成**：待所有者授权后，在干净 HEAD 上跑一次冻结候选 `make ci.local.quick` 并开 Gitee PR。
- 运行相关文件集在测量提交 `ce8b77bf` 上完成部署与验证；其后 delta 仅为 `.agent/` + `docs/` 台账，
  按确定性影响分析复用上述运行证据。

## 迭代效率：体系化复用引擎（P4 研发/交付工具，2026-10-07）

### 根因

上一轮把「19 键负例覆盖」的收口退化成了整矩阵重跑。直接原因不是探针慢，而是**没有任何机制
能算出「受影响集合」**：既有增量机制只到 check/target 粒度，声明型批处理（89 入口）没有**键级**
证据绑定，于是每次收口都只能全量重跑。

### 落地（体系化复用，非点对点缓存）

- **单一复用权威**：`scripts/ops/evidence_scope.py`（schema `evidence_scope.units.v1` /
  `evidence_scope.ledger.v1`，台账 `.runtime/evidence-scope/<check>.json`）。它与检查无关、不执行任何
  检查，只做裁决：`affected / reusable / never_recorded / stale / blocked / execution_required`。
  `select` 复用优先：已覆盖单元重跑必须带 `--reverify-reason`，失败单元盲重试同样被拒；
  `record` 三向校验：只能登记真实执行过的单元、`executed_units` 必须与 `results` 一一对应、
  `planned_affected ⊆ executed`——**杜绝虚假覆盖**。
- **单测**：`scripts/ops/test_evidence_scope.py`（25 项）经
  `make verify.frontend.business_entry.evidence_scope.unit` 执行，锁住引擎语义。
- **执行与规划同源**：`scripts/verify/business_entry_matrix_model.mjs` 是唯一纯函数真相源，浏览器探针
  与范围规划器共同 import，消除「执行/规划漂移」。矩阵按 entry 声明为 unit，指纹包含声明行、
  overlay 行为、推导出的拒权候选与模型/探针 revision。
- **构建产物版本是溯源而非有效性键**：仅因重新部署不使集合失效；使单元失效的是声明输入、模型/探针
  断言或受管运行态身份（base url、库、登录、候选顺序）变化。跨部署沿用证据需要记录影响分析。
  该判断经所有者确认，固化为 `.agent/decisions/evidence-reuse-identity.yaml`（`OPS-DECISION-002`，
  owner_approval=confirmed），并显式登记了「纯部署改变页面行为但未触及任何声明输入」这一已接受风险
  与补偿控制（影响分析留痕）。
- **复用优先入口**：`make verify.frontend.business_entry.matrix.incremental`。默认先规划、只跑受影响键、
  再回写台账；`SC_ENTRY_SCOPE_REVERIFY_REASON` 才允许重跑已覆盖键，`SC_ENTRY_SCOPE_FULL=1` +
  `SC_ENTRY_SCOPE_FULL_REASON` 才允许整矩阵重跑。原 `matrix.browser` 保持为执行器。
- **只读诊断复用输入**：`scripts/verify/business_entry_negative_closures.mjs` 支持
  `SC_ENTRY_MATRIX_CLOSURES_FROM` 采用既有观测，避免重复登录 10 个 principal。
- **入口可发现**：`scripts/verify/frontend_dev_incremental.py` 把矩阵/引擎文件映射到引擎单测，
  `ci.local.iteration` 会推荐正确的责任检查。

### 实测（served `ce8b77bf` / `sc_demo`，未重新取证）

| 步骤 | 结果 |
| --- | --- |
| 台账播种（复用 `daily-ce8b77bf-negative-19`、`daily-ce8b77bf-negative-delta2`，以及按其自身记录的候选集复算的 `f4279416` 全量） | `recorded=85/89 {passed:80, declared:5}` |
| `plan`（播种后） | `85 reusable / 4 affected / 0 stale / 0 blocked` |
| `make verify.frontend.business_entry.matrix.incremental` | 只执行 4 键：`ok=true entries=4 problems=0 console_errors=0`，回写台账 |
| 再次运行同一入口 | `89 reusable / 0 affected` → `REUSE-FIRST nothing to execute`（约 1.6s，无浏览器执行） |
| 重跑已覆盖键（无理由） | DENY（拒绝重复取证） |
| `SC_ENTRY_SCOPE_FULL=1`（无理由） | DENY（全量需显式理由） |
| `make verify.frontend.business_entry.matrix.evidence_scope.status` | `{checked:4, declared:5, passed:80}`（89/89，uncovered=0） |
| `make verify.frontend.business_entry.evidence_scope.unit` | `Ran 25 tests OK` |

### 需要所有者知悉（未放宽、未替证）

- 4 个声明归于其他车道的入口（`menu_sc_project_initiation`、`menu_sc_project_project`、
  `menu_sc_user_payment_apply`、`menu_sc_p1_daily_contract`）引用的证据路径在磁盘上已不存在
  （`artifacts/frontend-web-fix-20260928/evidence.md`、`uat02-raw/*`、`tpl02/TPL02-20260928132220-journey.json`）。
  播种器把它们记为 `declared`，并在结果文档写显式 `declaration_drift` 列表，**不静默声称覆盖**；
  这是另一车道的声明漂移，需由其责任层修复或重新指向可读证据。
- 该 4 项之外，矩阵车道自身表面（85 键）零缺口。

### 未完成

- 本分支目标**仍未完成**：待所有者授权后，在干净 HEAD 上跑一次冻结候选 `make ci.local.quick` 并开 Gitee PR。

### 本轮收口补充（2026-10-07 继续）：声明漂移消解 + 证据落点修复

- **声明漂移由本车道直接消解**：4 个漂移声明（连同未漂移的第 5 个声明单元）改为第一手取证。带
  `SC_ENTRY_MATRIX_KEYS` + `SC_ENTRY_SCOPE_REVERIFY_REASON` 运行
  `make verify.frontend.business_entry.matrix.incremental`，只走这 5 键 →
  `ok=true entries=5 problems=0 console_errors=0`；台账状态 `{checked:9, passed:80}`、
  `declared=0`、uncovered=0。未放宽任何断言，未改绑 1813/1843，未新增模型特判。
- **修复证据落点缺陷（根因）**：受管 Make 目标在调用者未设置时也会转发空 `SC_ACCEPTANCE_OUTPUT_DIR`，
  而 `scripts/verify/business_entry_matrix_incremental.py` 用 `os.environ.get(name, default)` 把空串
  当作有效值，`Path('') == '.'`，于是 `summary.json` 被写进**仓库根**（未跟踪、易被误提交）。
  修复为「空/空白视为未设置」，新增 `scripts/verify/test_business_entry_matrix_incremental.py`（5 项
  行为测试）并接入 `verify.frontend.business_entry.evidence_scope.unit`（现 `Ran 30 tests OK`）。
  探针侧本已空安全（使用 `||`），无需改动。
- 修复后带理由复采这 5 键一次，使 `source` 解析到声明目录
  `artifacts/frontend-business-entry-matrix/incremental/summary.json`；仓库根泄漏文件已清理。台账中
  先前 `run.source="summary.json"` 为被取代的历史条目，其单元引用已由新条目覆盖。

### 待所有者裁决（未擅自放宽）

- `scripts/ops/agent_run_context.py:170` 的复用判定要求 `check.kind == 'offline'` **且**
  `run.environment.kind == 'offline'` 才可能返回 `reusable`。本 run 的 `environment.kind = 'runtime'`，
  因此该 run 内**任何**检查（含纯静态单测）在 `agent.run.resume` 中都只能读作 `stale`，结果索引无法
  体现复用。运行时证据需要环境回读是正确的，但静态/单测证据不依赖运行态，按其输入是否变化即可复用。
  这是 fail-closed 门禁的语义，本轮**未擅自修改**；运行时表面的复用由矩阵台账承担（本次 89/89）。

## 轮次增补：往来款登记工作区「办理事项」按钮不渲染（根因 + 双层修复）

### 现象与决定性证据

用户级浏览器（`wutao` / `sc_demo` @ `http://1.95.85.92:18081`，菜单 987 / action 1192
`sc.current.account.workspace`）打开办理工作区时，6 个 header「办理事项」按钮完全不渲染。

用受管探针 `.runtime/diag/ws_decisive.mjs`（记录打开工作区 → 选项目全过程的契约请求/响应 + DOM dump）
取得：

1. **`op=model`（表单实际消费的契约）** 的 `buttonStatus` 停在
   `visible:false / disabled:false / reasonCode:"ACTION_NOT_VISIBLE_IN_STATE"`，而同行
   `entitlementEvaluated:false`（`allowed / enabled / disabled` 均为 `true`）。
2. **选中项目后前端不重新请求契约**：timeline 在 `project_selected` 之后没有新的 `ui.contract.v2` 请求，
   `buttonStatus` 原样保留 → 契约必须在下发时就带正确的 entitlement 事实。
3. **前端 presenter 门**：`explicitAuthority` 要求 `status.visible === true` 且
   `action.entitlementEvaluated === true`。离线复算（`presenter_probe.mjs` + vite `ssrLoadModule`）证明
   只补状态或只补 ee 都仍为空，两者齐备才出按钮。
4. **后端装配缺口**：`hydrate_final_action_modifier_status`
   （`addons/smart_core/core/unified_page_contract_v2_assembler.py`）原先只在 `verdict is False` 分支补记
   `entitlementEvaluated`；`verdict is True/None`（状态隐藏）分支不补，`entitlementEvaluated:false`
   从 `sourceTrace` 直接透传。
5. `action_open`（无 record）是 `ACTION_VISIBILITY_UNRESOLVED`（无 `project_id`）；`op=model` 是
   `ACTION_NOT_VISIBLE_IN_STATE`（`project_id` 为空 → 声明式 `not project_id` 为真）。**两者都是
   「未选项目应隐藏」的正确状态**；缺陷只在 entitlement 事实被漏记，且前端无法用实时值重算。

### 修复（各自责任层；未放宽任何 ACL / 字段权限 / 负例，无模型特判）

- **P0 平台内核投影** `addons/smart_core/core/unified_page_contract_v2_assembler.py`：
  把 `modifier_authoritative`（`native_form_header` + `button.type==object` + `native_locator`）与
  `permission_resolved`（`allowed/enabled/disabled` 均为 bool）提升到 verdict 判定之前；
  `verdict is True or verdict is None` 分支在两者成立时补记 `row["entitlementEvaluated"] = True`，
  随后**仍按原逻辑**设置 `visible:false`（True → `ACTION_NOT_VISIBLE_IN_STATE`；None →
  `ACTION_VISIBILITY_UNRESOLVED` 且 `disabled=True`）。不改 `allowed/enabled/disabled`。
- **P0 前端渲染机制** `frontend/apps/web/src/app/presentation/contractFormPresenter.ts`：
  新增 `STATE_DERIVED_STATUS_REASONS`（仅 `ACTION_NOT_VISIBLE_IN_STATE` /
  `ACTION_VISIBILITY_UNRESOLVED`）与 `resolveStateDerivedStatus`。仅当状态为**状态派生**、且声明 modifier
  引用的字段在实时值中**全部存在**时，才把该状态从「authority 拒绝」降级为「按声明 modifier × 实时值
  重算」；`ACTION_NOT_ALLOWED`、字段 / ACL 策略与合法隐藏照旧阻断（fail-closed）。`explicitAuthority`
  其余判据不变；另加 single-primary 守卫，契约自有 primary 保持主导。

### 本地判别力（回退即失败）

| 层 | 受管目标 | 结果 |
| --- | --- | --- |
| L2 后端 | `make verify.unified_page_contract.v2.runtime` | `Ran 117 tests OK`（含新增 `test_final_modifier_hydration_records_entitlement_for_state_hidden_native_action`；回退修复会 KeyError 失败） |
| L2 前端 | `make verify.frontend.canonical_form_presenter.unit` | 全绿；`state-derived action visibility cases PASS count=5`、`state-derived primary resolution cases PASS count=2`（回退即失败） |
| L1 | `make ci.local.iteration` | PASS |

后端新增用例覆盖三个子场景：状态隐藏的原生 header 按钮补记 ee 且 `allowed/enabled/disabled` 不变；
`project_id=12` 时 `visible=true` 且无 `reasonCode`；非原生行不写 ee。前端新增用例覆盖：基线（无 `project_id`）
不出现；`project_id=12` 出现；依赖缺失 fail-closed；`reasonCode:ACTION_NOT_ALLOWED` 仍阻断；
`entitlementEvaluated:false` 仍阻断；单 primary 解析（`form.save` 保持 primary，业务按钮保持 secondary）。

端到端离线复算：对真实 `op=model` 契约先跑后端 `hydrate_final_action_modifier_status`
（产出 `.runtime/diag/contract_model_ws_hydrated.json`，6 行 ee=True），再以 `VALUES='{"project_id":12}'`
跑 presenter → actionBar 为 `form.save`(primary) +
`borrow_company / repay_company / account_transfer / view_current_account`(secondary)；空 `project_id`
基线不出现。

### 运行台账对齐（本轮）

- run `FE-BUSINESS-ENTRY-ACCEPTANCE-GAP-CLOSURE` 的 `scope` 增补 `addons/smart_core/`（本层改动首次进入该 run），
  新增检查 `contract_v2_final_modifier_entitlement`、`frontend_canonical_form_presenter_state_derived`；
  `make agent.run.resume` 由 `reconcile` 恢复为 `resolved`（`outside_scope=[]`），`make ci.local.iteration` 恢复 PASS。
  仅补齐本轮真实改动范围，未放宽任何门禁。

### 日常运行态下发与真实浏览器复验（served `f1745110` / `sc_demo`）

| 步骤 | 受管入口 | 结果 |
| --- | --- | --- |
| 同步候选 | `make daily.runtime.candidate.bundle_sync` | PASS（old `ce8b77bf` → source `f1745110`，bundle `c705908b`） |
| 声明身份 + 重载 | `make daily.runtime.source_revision.align` | PASS，`restarted=true`、`rolled_back=false`，odoo 容器已重建（addon python 重新装载） |
| 重建前端 | 远端 `ENV=dev ENV_FILE=.env.dev make verify.frontend.build` | RC=0（重建 `frontend/apps/web/dist-dev`；线上 `index.html` 现引用 `assets/index-Ct929tvc.js`） |

**契约回读（运行态 `op=model`，`sc.current.account.workspace`）**：6 行原生 header 行现均为
`entitlementEvaluated:true`、`allowed/enabled/disabled = true/true/false`；`buttonStatus` 对「未选项目」
快照**仍然**如实报告 `visible:false` / `reasonCode:"ACTION_NOT_VISIBLE_IN_STATE"`（状态本身没有被改写）。

**真实浏览器复验**（`.runtime/diag/ws_buttons_final.mjs`，`wutao` @ `http://1.95.85.92:18081`，
证据 `artifacts/frontend-business-entry-workspace-buttons/daily-f1745110/summary.json`）：

| 状态 | action refs | header 文本 | 渲染数 |
| --- | --- | --- | --- |
| 基线（未选项目、未选承包人/往来单位） | `['form.save']` | 返回 保存草稿 | 0/6 |
| 仅选承包人/往来单位 | `['form.save']` | 返回 保存草稿 | 0/6 |
| 选项目 + 承包人/往来单位 | `form.save` + `action.{project_borrow_company, project_repay_company, contractor_borrow_project, contractor_repay_project, account_transfer, view_current_account}` | 返回 保存草稿 项目借公司款 项目还公司款 承包人借项目款 承包人还项目款 账户间调拨 查看往来台账 | **6/6，missing=[]** |

即渲染集合现在**精确跟随声明 modifier**（4 个声明 `invisible="not project_id"`，2 个声明
`invisible="not project_id or not partner_id"`），而不是修复前「任何状态都不渲染」。基线/仅选承包人两项的
隐藏是**契约声明的正确 fail-closed 结果**，未放宽为可见。

### 未完成（下一步）

1. 按原 `next_exact_step`(2) 把 `verify.system_user_experience.business_form_user_perspective` 重定位到
   声明交付入口（消费契约，而非已退役的独立 `借款办理/结算办理/票税办理` 菜单），并把本次「办理事项按钮
   声明消费」断言并入该入口；不放宽断言、不加模型特判、不新增第二套全局测试框架。
2. 收敛 `docs/product/frontend_business_entry_acceptance_v1.csv` 中两行 `partial_passed`（日常合同、付款申请）
   的运行态证据。
3. 出 89 条交付面的一次性用户级验收结论。**分支目标仍未完成。**

---

## 续轮：字段策略声明一致性 + 声明口径收敛到交付面（2026-10-08 续）

### A. `due_date` 消失 = 契约声明投影缺陷（P1 声明体，非放宽断言）

- 责任层：P1 施工行业标准产品（`smart_construction_core` 的 `ui.business.config.contract` 声明体）。
  P0 `smart_core` 字段策略投影的**收紧语义**本轮没有改动，也没有加任何模型特判；同批另加了一道
  「渲染档策略不得新隐藏原生 required 字段」的**结构权威守卫**（见续轮 3 · H，属于通用投影责任修复，
  不是本节的替代解释，也不放宽任何断言）。
- 泄漏链：模型级 `*_p1_form_business_facts_v1` 声明体给出**无条件** `readonly: True` →
  `view_orchestrator._apply_field_display_policy` 只置 true 不回松 → 交付字段节点被压成只读 →
  `statusContract.widgetStatus` 仍按原生 arch 报 `auth=edit`（两个投影互相矛盾）→
  `formSection.mapper.ts::readonlyFactIsPresentable` 丢弃“只读且空值”字段 → 到期日从页面消失。
- 修复：移除 6 个模型级声明体上 **14 个应由用户录入字段**的无条件只读，保留 `sequence`；
  `*_display` 镜像事实的只读策略仍由这些声明体承载，**声明体不退役**。

| 模型 | 移除的无条件只读字段 |
| --- | --- |
| `sc.financing.loan` | `due_date` |
| `payment.request` | `name` |
| `sc.fund.account.operation` | `note` |
| `sc.labor.request` | `request_date`, `contractor_id`, `note` |
| `sc.equipment.request` | `project_id`, `supplier_id`, `request_date`, `note` |
| `sc.equipment.settlement` | `name`, `project_id`, `settlement_date`, `supplier_id` |

- 新受管门禁：`make verify.business_config.field_policy_declaration_parity`
  （`scripts/verify/business_config_field_policy_declaration_parity.py`，只读 shell 门禁）。
  修复前 `contradiction_count=14`（FAIL，逐条列出）；修复后 `contradiction_count=0`（PASS）。
  报告 `artifacts/backend/business_config_field_policy_declaration_parity.json`。
- 判据与边界文档：`docs/product/field_policy_declaration_parity_v1.md`
  （区分“矛盾声明”与真实 ACL/字段权限拒绝、合法隐藏规则、系统生成字段、未识别 widget 默认值）。

### B. 8 例“运行时导航未交付” = 声明口径漂移（探针改消费交付声明）

事实（四份受管声明互相一致，全部不含这 6 个独立入口）：

- `scripts/verify/baselines/formal_business_product_menu_policy_v1.json`（当前锁定基线，89 菜单）
- 运行态发布策略 `sc.product.policy("construction.standard")`：89 菜单
- 日常验收导航策略 `config/frontend/acceptance_environments_v1.json` → `daily.navigation_policy`
  `min_actions=max_actions=89`
- 交付声明 `docs/product/frontend_business_entry_acceptance_v1.csv`：89 行

各入口在运行态的 `ir.ui.menu` 记录仍 `active=True`，但**不在**上述任一交付面内；其能力由声明的
统一载体承接（运行态契约 `current_account_workspace_contract.xml` /
`company_project_refund_workspace_contract.xml` 的 `fact_models`）：

| 业务代码 | 目标模型 | 声明的交付载体 |
| --- | --- | --- |
| `finance.loan.project_borrow_company` | `sc.financing.loan` | 往来款登记（`sc.current.account.workspace`） |
| `finance.fund.transfer` | `sc.fund.account.operation` | 往来款登记 |
| `finance.deposit.bid.pay` / `finance.repayment.registration` | `sc.expense.claim` | 往来款登记 |
| `finance.self_funding.income` | `sc.self.funding.registration` | 公司&项目退款（`sc.company.project.refund.workspace`） |
| `finance.payment.apply.receive` | `payment.request` | 付款申请（已声明创建入口） |

探针改动（`frontend/apps/web/scripts/business_form_user_perspective_acceptance.mjs`）：

1. `loadDeclaredEntryKeys()` 不再并入 `config/frontend/authoritative_navigation.json`
   （那是**每角色菜单授权面**，仍是发布导航策略门禁的输入，不是交付声明），只消费交付声明 CSV。
   `declaredEntryCount` 由 140 收敛为 **89**。
2. 两例重指向已交付承载入口：`settlement.income` → 收入结算；`finance.receipt.income.progress` →
   收款登记。
3. 6 例按上述载体收敛：`finance.payment.apply.receive` 重指向付款申请（创建旅程保留）；
   另外 5 例改为 **统一载体断言** —— 复用 `assertDeclaredEntryActions`（捕获交付 action 契约，
   要求渲染的 header 动作集**精确等于**声明基线可见集），并新增 fail-closed
   `checkRetiredConsolidation`：退役的独立身份不得出现在交付声明中，也不得出现在运行态导航中。
   这不是放宽断言：原先断言的“独立创建面”在产品中并不存在，改为真实契约陈述 + 漂移检查。
4. 汇总守卫（`..._summary_guard.mjs`）新增：consolidated 用例必须绑定退役身份且
   `retiredAbsentFromDeclaration=true`、必须消费到非空声明动作集；`MIN_CASE_COUNT=20` 不变。

实证（驳回一次错误绑定）：把 5 例直接绑到工作台载体跑**创建旅程**会失败
（`openCreateFromMenu`: "the declared entry exposes no create control"；工作台入口不暴露列表级“新建”控件），因此不能复用创建旅程，
只能走声明动作集断言。

**结果**（`artifacts/playwright/business-form-user-perspective/report.json`，本地受管运行态
`sc_dev_demo` @ `127.0.0.1:18081`，`sc_test_admin`）：

- 20/20 用例通过（15 创建旅程 + 5 统一载体断言），`declaredEntryCount=89`，
  `declaredEntryAssertions=1`，`consoleErrors=0`。
- 汇总守卫 PASS（`caseCount=20`、`failures=0`、`missing=0`、`undeclared=0`、`consolidated=5`、
  `consolidatedUnbound=0`、`leaked=0`）。
- 未入门的观察（保持可见、未放宽）：`settlement.income` 声明可编辑但未渲染
  `requested_fund_amount / invoice_ref / invoice_date / adjustment_ids`（与生效于 `due_date`
  的同类声明-投影漂移有待判定，属证据项，未纳入 gate）。

### 本轮未完成 / 下一步

1. 上述 `settlement.income` 4 个字段的声明-投影漂移判定（是真投影缺陷还是合法空态/字段权限）。
2. CSV 两行 `partial_passed`（日常合同、付款申请）的运行态证据收敛。
3. 89 条交付面一次性用户级验收结论。**分支目标仍未完成。**

---

## 续轮 2（2026-10-08）：`settlement.income` 4 字段判定 + 声明消费口径修正

上一轮留下的唯一未决项是：`settlement.income` 的交付契约声明
`requested_fund_amount / invoice_ref / invoice_date / adjustment_ids` 可见且可编辑，但页面一个都不渲染。
本轮按“先钉事实、再定责任层”的顺序收口，结论是 **声明消费口径错误，不是产品缺陷、不是投影缺陷**。

### C.1 取证链（三层独立证据，全部在本地受管运行态 `sc_dev_demo` @ `127.0.0.1:18081`）

1. **交付契约**（`ui.contract.v2 op=model render_profile=create`，探针实际捕获的同一条响应）：
   `mainData.id = "NewId_0x72831417a3b0"`。
   - 该值由**服务端**下发：用 node 直连 `/api/v1/intent`（绕开浏览器）复取，仍得
     `mainData.id = "NewId_0x..."`，`typeof === "string"`。
   - 它是 **Odoo ORM 的未保存记录虚拟 id**（`models.NewId`，`__str__` 为 `NewId_0x<hex>`；
     仓库内 `addons_external/oca_server_ux/base_tier_validation/models/tier_validation.py:252`
     即按 `isinstance(rec.id, models.NewId)` 判定）。
   - 它同时是**已冻结的契约约定**：`docs/contract/snapshots/api_onchange_intent_admin.json`
     早已记录 `ui_contract_raw.patch.id = "NewId_0x735997d2e080"`。因此**不能**为迎合消费方改成
     `false` 或删除。
2. **声明体（原生 arch）**：`addons/smart_construction_core/views/core/settlement_views.xml`
   的六个 group 明确写 `invisible="not id"`——`执行与匹配`（含 `requested_fund_amount`）、
   `发票信息`（含 `invoice_ref`、`invoice_date`）、`扣款调整`（含 `adjustment_ids`），
   另有 `付款申请` / `采购订单` / `系统办理信息`。语义即“记录保存后才显示”（“仅当记录已有 id”）。
3. **交付页面**：容器树**忠实地**携带判据（不是丢判据）：
   `modifiers.invisible = {"kind":"not","expr":{"kind":"field_truthy","field":"id"},"raw":"not id"}`；
   前端按**真实记录状态**求值（新记录 `formData.id` 为假）→ 六组隐藏 → 4 字段不渲染。**页面是对的。**

### C.2 根因

探针的地面真值函数 `collectNativeFieldVisibility()` 只拿 `dataContract.mainData` 求值，
把 `NewId_0x...` 当成了**真值**字符串，于是 `not id` 求值为 `false`——把声明整体倒置，
把“新建态按声明正确隐藏”的区域误判成“声明可见但未渲染”。

这与 `due_date` 是**外观相同、成因相反**的两类问题，必须按同一组问句区分：

| 问句 | `due_date`（第一次） | `settlement.income`（本次） |
| --- | --- | --- |
| 声明之间互相一致吗？ | ❌ 模型级无条件只读 vs 入口声明可编辑 | ✅ 一致 |
| 页面渲染符合声明吗？ | ❌ 与声明不一致 | ✅ 一致（声明即“保存后才显示”） |
| 因此责任层 | 声明体所属层（P1） | 消费侧（验收探针） |

### C.3 修复（只改消费侧，最小面）

`frontend/apps/web/scripts/business_form_user_perspective_acceptance.mjs`：

1. 新增未保存记录哨兵规则 `UNSAVED_RECORD_ID = /^NewId_0x[0-9a-f]+$/i` 与
   `declaredRecordValues()`：按既有契约约定，把 `NewId_*` 解析为“未保存记录”（`id` 为假）。
2. `collectNativeFieldVisibility()` 改用它求值；并把可见性由“最后一次出现覆盖”改为
   **任一次出现可见即可见**（交付状态契约是按**字段**而非按 occurrence 陈述的；
   `purchase_order_ids` 有两个 occurrence，一显一隐，旧聚合会误报为 native-hidden）。
3. 新增 `createRecordIdKind` 证据：`absent` / `unsaved_sentinel` / `persisted`。

不做的事（守住边界）：**不改**声明体、**不改**页面、**不改** ACL/字段权限/合法隐藏规则、
**不加**模型特判、**不新增**第二套全局测试框架。

### C.4 反向锁定（收紧，不是放宽）

汇总守卫 `frontend/apps/web/scripts/business_form_user_perspective_summary_guard.mjs` 新增三条 fail-closed：

- `createRecordIdKind` 不得为 `persisted`：create 契约若绑到已持久化记录则整套求值无效，直接失败。
- `declaredVisibleNotRendered` 必须为空：由“证据项”**升级为硬门禁**——地面真值修正后，
  “声明本 profile 可见可编辑、且自身与全部祖先 `invisible` 均解析为假”的字段必须真实渲染。
- 每个 create 用例必须声明到**非空**可见可编辑字段集，防止“把一切都判为隐藏”让门禁空转（反空洞）。

同一批还顺带修正的**同族消费口径**问题：`declaredVisibleEditable` 的 occurrence 聚合
（见 C.3 第 2 条）。

### C.5 结果（本地受管运行态）

- `verify.system_user_experience.business_form_user_perspective`：
  **20/20 通过**（15 创建旅程 + 5 统一载体断言），`declaredEntryCount=89`，`failures=0`，
  `consoleErrors=0`，`declaredVisibleNotRendered=[]`（全 20 例归零），
  `createIdentityKinds=[absent, unsaved_sentinel]`（含 `unsaved_sentinel` 1 例，无 `persisted`）。
- 汇总守卫 PASS：`caseCount=20`、`declaredEditableCases=15`、`consolidated=5`、
  `consolidatedUnbound=0`、`leaked=0`。
- **未放宽必填门禁的证明**：`settlement.income` 的 `declaredRequired` 修复前后一致
  （`project_id / contract_id / partner_id / line_ids`）；修复只会让“新建态本就隐藏”的字段
  退出 `declaredVisibleEditable`，而该集合在修复前就已经全部被渲染（`missing=[]`），故
  `declaredRequired ⊆ DOM` 的既有通过结论不受影响。
- `make verify.business_config.field_policy_declaration_parity` PASS（`contradiction_count=0`）。
- `make ci.local.iteration` PASS（`coverage=L1_only`）。
- 判据与区分方法写入 `docs/product/field_policy_declaration_parity_v1.md` 第 7 节，
  避免同类现象第三次被重新判定。

### 本轮更新后的剩余项

1. ~~`settlement.income` 4 字段判定~~ → **本轮已收口**（消费口径）。
2. CSV 两行 `partial_passed`：经查已在本 run 中 RESOLVED，CSV 现为 **89/89 `passed`**；
   `付款申请` 行仍需在本次候选**部署到日常库后**复验一次（见下）。
3. 89 条交付面一次性用户级验收结论：需在候选部署到日常开发服务器后出具，
   并显式区分**本地 `sc_dev_demo`** 与**日常 `sc_demo`** 证据。
4. **分支目标仍未完成**，不得标记完成。

## 续轮 3（2026-10-08）：P0 平台内核投影 + 前端渲染机制 + 探针声明消费（run blockers 25–32）

与 `due_date`／`settlement.income` 同一批收口的还有四条根因。它们外观相似但责任层各不相同，逐条按
责任层修复，未放宽任何断言、ACL、字段权限或合法隐藏规则，未加模型特判。以下为长表补充说明，逐条结论
索引仍以 `.agent/runs/FE-BUSINESS-ENTRY-ACCEPTANCE-GAP-CLOSURE/run.json` blockers 25–32 为准。

### D. 表单结构面 `surfaces: []` ＝ P0 平台内核字段 API 调用错误（blocker 25）

- 责任层：P0 平台内核（`addons/smart_core/handlers/ui_contract_v2.py::_model_surface_capabilities`）。
- 泄漏链：该方法用 `fields_get(load=False)` 查询真实字段，而本 Odoo 版本不接受 `load` 关键字 →
  `TypeError` 被 `except Exception` 吞成空集合 → 每份契约都声明
  `formStructureContract.surfaces = []` → 客户端把空列表读成「本页不声明任何区域」→
  **全部表单的协作区消失**。纯单测（注入 `capabilities`）绕过了这条路径，所以一直绿灯。
- 修复：改为受支持的 `fields_get()`；只有「本环境无此模型」或 env double 无 ORM 面时才允许回答空。
  字段 API 异常不再被转换成错误默认值（真实异常必须冒泡）。
- 锁定：`addons/smart_core/tests/test_form_structure_surface_capability_orm.py`
  （真实 ORM，4 例，target `verify.local.dev.form_structure_surface_capability.orm`）。

### E. 协作区面板只读态被宿主覆盖 ＝ P0 前端渲染机制（blocker 26）

- 责任层：P0 前端渲染机制（`frontend/apps/web/src/pages/contractForm/CanonicalNativeFormSurface.vue`、
  `ContractFormDriverHost.vue`）。
- 根因：宿主向 `NativeCollaborationPanel` 显式传入 `:readonly`，覆盖了契约已解析的面板声明——
  声明为可交互的面板会被宿主按表单 `renderMode` 降级成只读。**面板模式的唯一所有者是声明，不是渲染模式。**
- 修复：移除该覆盖绑定（不改组件、不改声明）。
- 锁定：`verify.frontend.collaboration_primitives.browser`（声明 live→`controls=2`/`upload=1`，
  声明 readonly→`controls=0`/`upload=0`，`declarationConsumed=true`，8 例）。

### F. `system.init` 对全部用户 500 ＝ P0 平台内核把目录节点当禁用项（blocker 31）

- 责任层：P0 平台内核（`addons/smart_core/delivery/menu_service.py::project_canonical_navigation`）。
- 根因：投影把 `is_clickable=False` 一律读成「显式禁用」，而交付引擎对每个已发布目录组节点
  （`target_type=directory`、`delivery_mode=none`、`availability_status=ok`、`reason_code=DIRECTORY_ONLY`）
  恰好下发该标记；客户端契约本就把「无 action 目标且无 container 授权」的节点解析为
  `state='container'`。2026-10-07 17:02 发布的产品策略把两个目录组（menu 666 项目预算、menu 592 成本报表）
  带入已发布导航后，所有该策略用户的 `system.init` 都 fail-closed 抛
  `ValueError('disabled canonical navigation node requires a server reason')` → HTTP 500。
  运行日志首次出现 2026-10-07 17:08:03，之前最后一次成功 17:00:43；324 个导航节点里 322 个根本不含该键。
- 边界澄清：**不是本分支未提交改动引入**——导航路径不含本分支改动文件，`menu_service.py` 自
  2026-10-02 未变，触发条件是策略数据命中一个既有判据。
- 修复：仅当节点**拥有目标**（`action_id > 0` 或路由 container 授权）或 `availability_status` 自身声明
  禁用时，才要求服务端 `disabled_reason`；纯目录保持 `state='container'`。拒绝信息附带 menu/action/key，
  便于定位。未新增隐藏、未放宽 ACL、未加模型特判。
- 锁定：`addons/smart_core/tests/test_canonical_navigation_projection.py`
  （4 例，target `verify.local.dev.canonical_navigation_projection.orm`）＋ 运行态回读
  `.runtime/agent-runs/FE-BUSINESS-ENTRY-ACCEPTANCE-GAP-CLOSURE/nav_projection_system_init_readback.json`
  （HTTP 200，324 节点，`container=61`/`enabled=263`，0 个与客户端身份规则冲突）。

### G. 退役探针断言 + 夹具身份 ＝ P4 验收工具（blockers 27–30、32）

- **项目台账 notebook**：原断言期望退役的默认项目表单（11 tabs）；改消费声明
  （`view_project_overview_form`（view 1761）声明 `notebook_tabs=[]` → 渲染 0），DOM 仍逐字段对声明校验。
- **关注者旅程**：原用 ORM `is_following` 快照当浏览器期望（关注态随当前用户变化、快照会漂移），
  且 `data-state=ready` 自首次挂载即为真，立即计数会与 `chatter.followers.list` 响应竞态。
  改为从契约投影声明的关注者能力（绑定浏览器实际加载的面：`project.project` action 519、
  `payment.request` action 809），等待权威 live list 响应，再要求恰好一个声明按钮镜像它，并按序要求
  声明记录上的全部声明 update intent；ORM 往返仅留作后端证据。加固：只有成功信封
  （`ok=true` 且 `count>=0`）才可作 live 权威，失败/截断响应不可再被读成「未关注」。
- **付款关系面**：原断言统计 `[data-floorplan-region="relation"]`，而付款面已不再渲染该区域
  （`data-detail-composition-adopted=false`，仅 `data-floorplan-region=audit` 存在），选择器结构上恒为 0。
  改为声明驱动：从契约投影声明的关系集合（唯一字段节点 → `component_key=sc.payment.settlement_detail_collection`、
  `relation=payment.request.line`、`fieldInfo.subview.policies {can_create:false, inline_edit:true, can_unlink:true}`、
  `column_count=8`），带 fail-closed 唯一性/完整性/镜像策略漂移检查。
  `can_create=false` **是声明本身**，未新增自动创建能力，未触碰 ACL/字段权限。
- **付款夹具身份**：改为受管 xmlid `smart_construction_demo.payment_request_floorplan_demo_record`，
  fail-closed 要求 `state=='draft'`，并绑定 `make local.dev.reset_payment_request_fixture`，不再硬编码记录 id。
- **因导航投影变更重跑的受影响门禁**（`menu_service.py` 已成为所有读取已发布导航树证据的 check 的声明输入）：
  `verify.local.dev.project_create_contract_action_scope`（23 组断言，`intentFailures=[]`、`browserErrors=[]`，
  夹具清理 `remaining=0`）、`verify.frontend.collaboration_primitives.browser`（8）、
  `verify.frontend.release_navigation_policy.guard`（5）、
  `verify.frontend.role_surface_exposure_declaration.guard`（10）、
  `verify.local.dev.form_structure_surface_capability.orm`（4）。

### H. 渲染档策略不得新隐藏原生 required 字段 ＝ P0 平台内核投影责任（blocker 36）

- 责任层：P0 平台内核（`addons/smart_core/handlers/ui_contract_v2_projection.py::apply_field_policies_to_v2_status`）。
- 事实：原生表单的**已交付布局**是字段可见性的结构权威。渲染档策略（`field_policies`）只能收紧
  `readonly`/`required` 语义，**不得**把一个「原生交付状态声明为 required、且原生可见」的 occurrence
  新隐藏掉——`visible=false` 且 `required=true` 是一组**不可满足**的声明，等于把结构所有权交回第二个 owner。
- 边界（守死）：字段/记录权限只由权限面承载（`globalStatus` / `auth`），从不经这些渲染档策略下发；
  因此本守卫**不能**放宽访问，**不能**复活一个原生已结构隐藏的字段（原生 `NATIVE_MODIFIER_INVISIBLE`
  的 occurrence 保持不可见），也**不**使用 `critical` 覆盖。它只拒绝「新隐藏 required 且原生可见」。
- 这是用户要求的「钉住首次产生 `visible:false / auth:"none"` 的位置、修复通用投影责任」，
  与 A 节的 P1 声明一致性修复**互补**：A 节消掉矛盾声明的源头，H 节让通用投影不再把矛盾变成结构丢失。
- 锁定：`addons/smart_core/tests/test_ui_contract_v2_boundaries.py::test_native_form_policy_never_hides_a_required_occurrence`
  （required+原生可见 → 保持 visible（readonly）；非 required → 仍按策略隐藏；原生结构隐藏 → 不复活）。
- 未放宽的证明：同测试断言非 required occurrence 仍被策略隐藏、原生隐藏 occurrence 仍 `auth="none"`，
  故 `declaredRequired ⊆ DOM` 一类既有通过结论不受影响；`business_form_user_perspective` 20/20
  与 `declaredRequired` 修复前后一致。

### 本轮验证汇总（本地受管运行态 `sc_dev_demo` @ `127.0.0.1:18081`；HEAD `93032a3d`）

| 门禁 | 例数 | 结果 |
| --- | ---: | --- |
| `verify.system_user_experience.business_form_user_perspective` | 20 | passed |
| `verify.local.dev.project_create_contract_action_scope` | 23 | passed |
| `verify.frontend.collaboration_primitives.browser` | 8 | passed |
| `verify.frontend.release_navigation_policy.guard` | 5 | passed |
| `verify.frontend.role_surface_exposure_declaration.guard` | 10 | passed |
| `verify.local.dev.form_structure_surface_capability.orm` | 4 | passed |
| `verify.local.dev.canonical_navigation_projection.orm` | 4 | passed |
| `verify.business_config.field_policy_declaration_parity` | — | PASS（`contradiction_count=0`） |
| `ci.local.iteration` | — | PASS（`coverage=L1_only`） |

以上均为本地 `sc_dev_demo` 证据，与日常 `sc_demo` 是两套运行栈，不能互相冒充；日常结论需在候选部署后
单独取证。**分支目标仍未完成。**

## 续轮 4（2026-10-08）：PR #607 合并 → 日常部署 `24e05cd5` → 详情面/工作台收口（run blockers 37–42）

### 身份与运行态

- 分支 `fix/frontend-business-entry-contract-payment-closure-20261007`，HEAD `25845e97`；PR #607 已 squash 合并为
  **`24e05cd54685645498843bf29b222fed3f595d9e`**（`25845e97^{tree} == 24e05cd5^{tree}`）。
- 日常开发服务器 `http://1.95.85.92:18081` 现served **`24e05cd5`**（`sc_demo`、`ENV=dev`），
  受管入口链路：`daily.runtime.main.bundle_sync` → 远端 `make mod.upgrade MODULE=smart_core` /
  `MODULE=smart_construction_core` → `verify.frontend.build` → `daily.runtime.source_revision.align`。
- 本地 `sc_dev_demo` @ `127.0.0.1:18081` 与日常 `sc_demo` @ `1.95.85.92:18081` 是两套栈，证据不可互相冒充。

### A. `workbench-only` 失败 ＝ 探针声明消费口径过期（P4 验收工具），不是渲染回归

- 现象：`verify.daily_dev.list_surface.readonly.browser`（`LIST_SURFACE_DAILY_OBSERVATION_SCOPE=workbench-only`）
  在 `scripts/verify/frontend_list_surface_structure_browser.mjs:1012` 超时
  （`[data-semantic-component="ScCard"]:visible` 30s 未出现）。旧日常版本 `e384b832` 同路由同断言通过。
- 钉事实（served `24e05cd5`，`wutao`）：
  - 落地面 `/s/projects.list` **确实渲染**：`SceneView` `data-state` 由 `loading` → `ready`；
    其后 `ListPage` / `ProductListSurface` / `ScTable` 出现（`共 750 条`），整页 `ScEmptyState=0`、`console_errors=[]`。
  - 该页的卡片节点是 `div.t-card.list-card-container`，同时带
    `data-semantic-component="ProductListSurface"` 与 `data-semantic-primitive="ScCard"`；全页 `ScCard` 组件标识为 0。
- 根因：本批次修的是设计系统基元语义标识的**优先级**。
  旧写法 `{ ...$attrs, ...semanticPrimitiveIdentity('ScCard') }` 让基元身份**覆盖**消费者声明，
  于是这个节点被冒名标成 `ScCard`；新写法 `{ ...semanticPrimitiveIdentity('ScCard'), ...$attrs }`
  让**消费者声明获胜**，并新增无条件发布的 `data-semantic-primitive`。
  `scripts/verify/frontend_primitive_adapter_guard.py` 明确声明了这一契约（“消费者在基元根上的声明获胜；
  否则基元自身不可寻址”）。**探针原来靠的正是被修掉的那个冒名行为。**
- 修复（只改 P4 探针消费口径）：新增 `CARD_PRIMITIVE_SELECTOR = '[data-semantic-primitive="ScCard"]'`，
  声明落地面与 `router /` workspace home 两处“卡片已渲染”断言改消费**声明的基元标识**。
- 为什么不是放宽：修复前后**节点集合相同**（旧行为下基元节点一律被强制标成 `ScCard`，
  新行为下这些节点一律带 `data-semantic-primitive="ScCard"`），断言强度不变；
  未改任何产品代码、ACL、字段权限、合法隐藏规则，也未使用 `critical` 覆盖。
- 结果：`workbench-only` light / dark 均 `rc=0`（served `24e05cd5`）。

### B. 详情面其余项（served `24e05cd5`，1440/390 × 明暗，全部 `rc=0`）

| scope | 断言 | 结果 |
| --- | ---: | --- |
| `detail-only` | 8 | passed（`declared_entry_route` / `exact_record_contract` / `declared_renderer` / `return_to_source`） |
| `form-profiles` | 12 | passed（声明的 create/edit/readonly 入口 + 渲染档消费） |
| `workbench-only` | 2 | passed（修复后） |

产物：`.runtime/final-acceptance/detail-lane-24e05cd5/`。原清单中“创建/编辑与工作台的最小证据差额”就此闭合；
列表矩阵未重跑（本轮的探针改动不在其执行路径上，89/89 既有结论不受影响）。

### C. 关系交互：一次真实“点击打开 → 返回原记录 → 标签和动作恢复”（served `24e05cd5`）

- 证据：`.runtime/final-acceptance/relation-roundtrip-24e05cd5/20261007T224226/summary.json`，`status=pass`。
- 源记录 `construction.contract.income/2331`（`action_id=578`、`menu_id=904`），页面自身契约声明 14 个
  relation entry，其中 4 个声明可打开：`project_id 马鞍村库房`、`partner_id 测试11`、`handler_id 吴涛`、`tax_id 9%`。
- 4 个全部由**真实点击**判定为 `opened`；首个完成受验证的往返：`return_*` 契约齐全，
  返回后 `path/title/statusbar/tabs/actions` 全部恢复、`error_free=true`；
  `denied_requests=0`、`console_errors=0`。
- 该证据取代 `e384b832` 的关系往返证据：本批次改动了动作/标签呈现代码
  （`contractActionPresentation.ts`、`actionPresentation/actionRuleDerivation.ts`），旧证据的“标签与动作恢复”断言已失效。

### D. 事实澄清：受管 fixture 身份对 `wutao` 不可用（多公司隔离正确，非缺陷）

- `make daily.runtime.record_identity.resolve` 在 served `24e05cd5` 上 PASS，绑定的是 fixture 稳定标识
  （`fe_project_a`=2014 / `fe_general_contract_a`=1719 / `fe_delivery_hardening_payment_request_a`=36178 …）。
- 但这些记录属于 `smart_construction_acceptance_fixture.fe_company_a/b`（21/22），
  而验收账号 `wutao` 是 **user 16、company 1**。直接记录路由被产品**正确拒绝**：
  `/r/sc.general.contract/1719` → `reason=PROJECT_SCOPE_DENIED`；
  `/r/payment.request/36178` → `PROJECT_SCOPE_DENIED`；`/r/project.project/2014` → `PERMISSION_DENIED`。
- 因此用户级关系证据使用 company 1 的业务记录（与上一次已接受的日常证据同一身份），
  并由探针自身在 PASS 时再次验证该绑定；不新增硬编码，也不改绑到 fixture。

### E. 本轮新发现（与本轮改动无关，独立登记）

- `make verify.frontend.playwright_vendor_coupling.guard` 在**干净 HEAD**（把本轮改动 stash 后）同样失败：
  报 `scripts/verify/local_dev_project_create_contract_driver_probe.mjs 2 > baseline 1`，
  即合并批次新增了一个 vendor 内部选择器而未同步收缩/更新声明基线。
  本轮改动的探针自身基线项（4）未被点名。
- 判定：独立、既存、非部署阻断（同一棵树的远端四项必需检查在 `25845e97` 全 success）。
  仍需由归属层处理，且**不得**靠抬高基线通过。

### F. 状态边界（本轮不主张上线）

- 批次验收：详情面本轮收口完成（A–D）。
- 主线集成：PR #607 已完成（squash `24e05cd5`）；合并不等于部署，但该 revision 已部署且已回读对齐。
- 版本发布：**未主张**。产品交付：**未主张**。
- 剩余：89 条交付面在已部署 revision 上的**单一用户级统一裁决**（逐条证据已在，整体结论与剩余失败尚未落笔）。
- **分支目标仍未标记完成。**

## 续轮 5（2026-10-08）：89 条交付面的单一用户级统一裁决（run blocker 43）

### 身份与复用前提
- served revision = `24e05cd54685645498843bf29b222fed3f595d9e`（PR #607 squash-merged），
  base_url `http://1.95.85.92:18081`，数据库 `sc_demo`，`ENV=dev`。
- 裁决输入为**只读状态计算** `make verify.frontend.business_entry.matrix.evidence_scope.status`，
  登录固定 `fixture_role_config_admin`（session company 21）。原因：89 条交付面按**发布导航策略**
  （nav 策略 min=max=89）复核，用 `wutao`（company 1）会把 89 条全部判 stale。
- 该入口只重算“声明指纹 ↔ 既有观测”的匹配，**不重跑浏览器、不改任何运行态**；未重新取证的条目属复用。

### A. 覆盖裁决（89/89）
- `state_counts = {"checked": 9, "passed": 80}`；`stale = 0`、`uncovered = 0`、`undecidable = 0`。
- 9 条 `checked`（其声明指纹与 F7B7C2EE 批准的 89 条基线逐字段相等，构成行级等价性证明）：
  `menu_sc_operating_metrics_project`、`menu_sc_p1_daily_contract`、`menu_sc_product_message_notification_v1`、
  `menu_sc_product_project_lifecycle_v1`、`menu_sc_project_initiation`、`menu_sc_project_kanban`、
  `menu_sc_project_project`、`menu_sc_user_payment_apply`、`menu_sc_workbench_my_todo_fact`。
- 80 条 `passed` 由 `evidence_scope` 引擎复用既有观测：主车道
  `artifacts/frontend-business-entry-matrix/daily-f4279416-full/summary.json`
  （80 entries、`ok=true`、`problems=[]`、`console_errors=[]`），增量为 `daily-aed39bc5-matrix`(3)、
  `daily-ce8b77bf-incremental`(4) 等；引擎判定其输入未变，故不重跑。

### B. 本轮补采：付款申请行
- `artifacts/frontend-business-entry-matrix/incremental/summary.json`：
  `ok=true`、`problems=[]`、`console_errors=[]`、`target_sha=served_revision=24e05cd5`、
  `selection.keys=["smart_construction_core.menu_sc_user_payment_apply"]`、`record_id=36179`、
  `workflow_actions=[save_draft, submit, cancel]`；列表渲染 14 行，搜索 `FE-CORE-FORM-CONFLICT-001` 命中 14。

### C. 负例（权限边界）
- `daily-ce8b77bf-negative-19`：19 例，`ok=true`、`leaked_entries=[]`。
- `daily-ce8b77bf-negative-delta2`：2 例，`ok=true`、`leaked_entries=[]`。
- `artifacts/frontend-business-entry-matrix/negative_closures.json`：10 个候选，`leaked_entries=[]`（无越权泄漏）。
- 2 个**不可判候选**（`fixture_role_executive`、`fixture_role_partner_manager`）：runtime 未向其发布任何导航目标
  （`released_navigation_targets=0`）⇒ 无法区分“拒绝”与“无导航”，记为**未覆盖**，**不计为失败**。

### D. 历史 excluded 车道（非本轮独立证据，附原因）
- `daily-ce8b77bf-full`、`daily-f4279416-matrix` / `daily-f4279416-notrun`：同候选重复。
- `daily-f4279416-project-center`：处于导航投影变更之前。
- `daily-f4279416-workbench`、`daily-f7b7c2ee-workbench`：其问题后续已被 89 条矩阵覆盖。
- `recon-presentations`：仅展示层侦察，不承载交付面判定。
- 以上均**不**作为本轮 89 条裁决的证据，仅登记被排除的原因。

### E. 裁决结论
- **在已部署 revision `24e05cd5` 上，89 条交付面的剩余失败 = 无。**
  coverage 89/89（stale 0、uncovered 0）、`problems=[]`、`console_errors=0`、负例 19/19 无泄漏。
- 该裁决绑定 served revision 与既有观测；**不是**版本发布主张，也**不是**产品交付主张。

### F. 状态边界
- 批次验收：本轮完成。
- 主线集成：PR #607 已完成（squash `24e05cd5`）；合并不等于部署，但该 revision 已部署且已回读对齐。
- 版本发布：**未主张**。产品交付：**未主张**。
- **分支目标仍未标记完成**；唯一独立未决项为既存 vendor-coupling L1 守卫（上一节 E），属归属层处理。

## 续轮 6（2026-10-08）：vendor-coupling L1 守卫收口（run blocker 44）

### 现象与归属
- `make verify.frontend.playwright_vendor_coupling.guard`（受 `verify.frontend.quick.gate` 依赖，
  **属交付门禁**，不只是普通 L1）在干净 HEAD 上报：
  `vendor_internal_selector: scripts/verify/local_dev_project_create_contract_driver_probe.mjs 2 > baseline 1`。
- 责任层：**P4 验收工具**（探针消费口径），不是产品渲染、不是 ACL/字段权限、不是合法隐藏规则。

### 根因
- 该探针在读取工作台 `.native-container--group` 段落标题时，兜底选择器写成了 **TDesign 内部类**
  `.t-card__title`（`:scope > header h3, :scope > header button, .t-card__title`），
  把本文件 literal vendor-internal selector 计数从 1 抬到 2。
- 该兜底**是承重的**：项目台账详情段落以 `ScCard` 渲染（探针实测 `tag=DIV`），
  detail-card 不渲染原生 `<header>`，标题经 ScCard 透传给 TDesign 落到 `.t-card__title`，
  所以不能简单删除。

### 修复（只收紧，不放宽）
- 探针改消费渲染器**已声明的公共面**：
  `:scope > header h3, :scope > header button`（原生容器头）→ 否则读根节点的 `data-group-title`
  （`NativeFormTreeRenderer` 一直在容器根发布该声明属性，探针原本也已把它读进 `title`）。
- 未改任何产品代码、ACL、字段权限、负例，未抬高基线数字。
- 判别力未变（实测等价，非声明）：在受管 `local.dev` 夹具上，修复前后工作台 5 个段落的
  `title`（声明属性）与 `heading`（可见标题）**逐字相等**：
  `基本信息 / 计划与责任 / 责任矩阵 / 项目说明 / 协作资料`。

### 复验
| 层 | 入口 | 结果 |
| --- | --- | --- |
| L1 | `make verify.frontend.playwright_vendor_coupling.guard` | passed（`vendor_internal_selector` files=21 total=104 ≤ recorded 109；`rc=0`，含 7 个单测 OK） |
| L4 | `make verify.local.dev.project_create_contract_action_scope` | passed（`rc=0`，工作台 5 段标题/字段不变，`drivers=1 errors=[]`） |

证据：`.runtime/final-acceptance/vendor-coupling-probe-fix/local_dev_project_create_contract_action_scope.log`。

### 结论
- 守卫恢复通过；`verify.frontend.quick.gate` 的该项阻断解除。
- 该修复只影响探针执行路径：`verify.local.dev.project_create_contract_action_scope` 结果已刷新，
  89 条矩阵 / 详情车道 / 关系往返**不依赖**该探针，其既有通过证据继续复用。

## 续轮 7（2026-10-08）：run 退役（台账收口）

### 身份与依据
- 冻结候选 HEAD `9c64154f1943efa3c95d79a9076e1114d94d1a67`；合并后 `origin/main` = `286a6e1116d2dbb24047347827f6edcd00f932f5`。
- 主线集成：**PR #607**（head `25845e97`，squash `24e05cd5`）+ **PR #608**（head `9c64154f`，squash `286a6e11`）均已合并；
  四项必需检查 `public_guard`、`merge_policy_gate`、`professional_quality_gate`、`frontend_release_gate`
  在精确 HEAD 上全部 success。合并不等于部署，验收裁决绑定的 deployed served revision 仍为 `24e05cd5`。
- 冻结候选 Quick：`.git/codex/evidence/ci.local.quick/9c64154f1943efa3c95d79a9076e1114d94d1a67.json` → PASS。

### 退役动作（纯台账）
- `FE-BUSINESS-ENTRY-ACCEPTANCE-GAP-CLOSURE` 的 run 与 goal 置为 `completed`，并回填 `evidence`（主线集成、冻结候选 Quick、89 条验收裁决）。
- `.agent/active-runs.json` 回到空终止态 `{"schema_version":1,"branches":{}}`，使任何索引项都不再指向已合并的
  `fix/frontend-business-entry-contract-payment-closure-20261007` 分支。
- 注册离线退役 run `FE-BUSINESS-ENTRY-ACCEPTANCE-GAP-CLOSURE-RETIREMENT`（check `run_index_terminal_state` → `verify.agent.resume.unit`）。
- 复验：`make verify.agent.resume.unit` → 30 tests OK；main 上 `make agent.run.resume` → `unregistered`
  （沿用 `ACTIVE-RUN-INDEX-DANGLING-CLOSEOUT` 先例）。
- 已合并 `fix/...` 分支的删除属于独立的 `branch.retire.historical` 车道，**不在本批**。

### 状态边界（最终）
- **批次验收**：完成。**主线集成**：完成（PR #607、PR #608）。
- **版本发布**：未主张（未部署版本、未做 release snapshot）。**产品交付**：未主张。
- 本批无产品、契约、测试、门禁、工作流、运行态或凭据行为变更，仅台账收口。

## 续轮 8（2026-10-08）：已合并分支退役评估（受管入口裁决 = 保留）

### 执行入口与身份
- `make branch.retire.historical`（**只读 dry-run**：`--emit-inventory/--emit-manifest` + `--report`，**无 `APPLY`、无 recovery bundle、无删除**）。
- 绑定 `origin/main` = `2f1ca4e08164851b879ea7eb352ce90076c18cb2`；emit manifest `sha256=f930fa615b8c53b09e79c711647abd6753818a4718f811ee76845a99dba512cd`。
- 证据：`docs/ops/manifests/historical_branch_retirement_assessment_20261008.json`。

### 裁决结果：`eligible=0 skipped=4`，删除 0
| 候选（ancestry 已 contained） | tip | 裁决 | 原因 |
| --- | --- | --- | --- |
| `audit/acceptance-harness-login-contract-retirement-20261007` | `1d8d2863` | skip | 被 `.agent/runs/ACCEPTANCE-HARNESS-LOGIN-CONTRACT-ALIGNMENT-RETIREMENT/run.json` 的 `branch` 字段引用 |
| `audit/daily-acceptance-mainline-continuation-20261006` | `500d6f91` | skip | 被 `DAILY-ACCEPTANCE-MAINLINE-CONTINUATION(-RETIREMENT)` 的 goal/run 引用 |
| `audit/daily-acceptance-mainline-continuation-retirement-20261007` | `03d02790` | skip | 被其后继 retirement run 的 `branch` 字段引用 |
| `fix/acceptance-harness-login-token-contract-20261007` | `a298e9d4` | skip | 被 `ACCEPTANCE-HARNESS-LOGIN-CONTRACT-ALIGNMENT(-RETIREMENT)` 的 goal/run 引用 |

另有 2 个本批 squash 合并分支**根本不进 ancestry manifest**（tip 非 `main` 祖先，status `unmerged`），且同样带载体引用：
- `fix/frontend-business-entry-contract-payment-closure-20261007`（`9c64154f`，squash #608）
- `audit/frontend-business-entry-acceptance-gap-closure-retirement-20261008`（`cf02b067`，squash #609）

### 根因（体系层）
- 退役入口把 `scripts/config/deploy/make/.agent/.github` 当载体根做**纯文本**扫描；而 run 台账的 `"branch"` 是**执行身份字段**（`resolve_run` 要求其等于 `active-runs.json` 注册的分支），退役 run 又恰好执行在它要退役的分支上 ⇒ **自引用死锁**。
- 该字段**不可清**：改 `main` 或置空＝篡改台账身份。先例（`REMOTE-BRANCH-CARRIER-RETIREMENT`/`-B`）只清过**非承重**载体（goal 的 `baseline.branch`、run 的 retained-list、test fixture 占位名），从未改过 run 执行身份，故本批按既有契约属 **"by design 保留"**（与 `REMOTE-BRANCH-BACKLOG-RETIREMENT` 记载一致）。

### 清单事实（`origin`，非 `main`）
- 头总数 73 = contained 4 / unmerged 45 / protected 19 / outside-prefix 5；local-only 无（除 `main`）。
- 兄弟分支 `fix/frontend-business-entry-acceptance-closure-20261007`（`25532a53`，无载体引用）仍 `unmerged`，与 main 分叉 130 文件 / −12046 行，属独立决策，不在"已合并"范围。

### 边界
- 本批**未删除任何引用**、**未清任何载体**、**未放宽任何守卫/断言/前缀策略/审计**、**未改写台账身份**。
- 若日后要真正退役这批分支，需**另行授权**的 P4 变更（把"已完成且未注册的 run 的 `branch` 视为历史记录而非活跃载体"），并需独立复核 —— 本批不推进。
