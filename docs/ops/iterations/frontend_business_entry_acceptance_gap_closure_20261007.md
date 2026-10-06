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
  （record 2019 / company 21 / menu 970 / action 1178 / 起点 draft+draft）。

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
  SC_ACCEPTANCE_OUTPUT_DIR=artifacts/frontend-business-entry-lifecycle/daily-6c8e07f7
```

原始证据：`artifacts/frontend-business-entry-lifecycle/daily-6c8e07f7/summary.json`（正式，受管 run 记录）、
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
| L4 | `make verify.frontend.business_entry.lifecycle.browser` | PASS（复用） | 6 | 正式受管 run；输入文件自 run 后未变，按未变输入复用，不重跑 |

未跑层的显式理由：

- L3（受管模块升级 / 运行时冒烟）：本批次未改产品运行时代码；日常服务器仍由
  `make pr.push` 之外的既有主线承载，发布不触发产品部署，故不适用于本轮候选。
- L5（独立复核 / 生成报告 / 完整发布门禁 / 精确头发布）：待本次冻结后由远端必需检查与独立复核执行。

`make ci.delivery.freeze.prepare` PASS（生成报告 `docs/engineering_convergence/` 已刷新并一并提交）。
