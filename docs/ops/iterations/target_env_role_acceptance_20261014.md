# TARGET-ENV-ROLE-ACCEPTANCE · 目标环境真实角色验收（2026-10-14）

范围：在已完成版本发布的目标环境（daily `sc_demo`，服务版本/候选树/发布面均为 main
`d2079888`）上绑定真实代表角色的允许/拒绝证据。**不是**新页面、新组件、语义能力扩展、
契约变更或数据修复。

## 1. 触发事实

| 项 | 值 |
|---|---|
| 目标环境 | daily runtime，`sc-root:/opt/projects/repos/sce-product-odoo` |
| 数据库 / compose / 端口 | `sc_demo` / `sc-backend-odoo-dev` / `18081` |
| 已部署版本 | `/api/runtime-version` → `source_revision=git_sha=d2079888…`，`product_version=1.0.0-rc.20` |
| 快照 | `construction.standard` 106（released 90 / gate 90）；`construction.preview` 107（released 90 / preview 39 / gate 129） |
| 前置 goal | `FE-CONTRACT-RUNTIME-02-VIEW-STRUCTURE-COMPAT`（已完成：批次验收 / 主线集成 / 部署） |

本 goal 承接「版本发布完成」与「产品交付完成」之间的唯一缺口。

## 2. 声明边界

- `Formal Product Layer`：P4（交付/运维验收证据）
- `Layer Target`：`daily_runtime_target_environment_role_permission_acceptance`
- `Standard vs User-Specific`：平台交付验收证据，不改任何 P0/P1/P2 语义
- `Why Here`：目标环境验收属交付层职责，只读取已部署产品面并按声明角色绑定证据
- `Why Not Elsewhere`：不改产品语义、不做前端补偿、不改契约/schema、不以管理员代替真实角色、
  不手工拼装 compose/数据库/凭据命令
- `Blast Radius`：仅目标环境只读验收证据与 `.agent`/`docs` 记账

## 3. 结果

见结果索引 `.agent/runs/TARGET-ENV-ROLE-ACCEPTANCE/run.json`。本文件随实际执行结果更新。

状态边界：批次验收 / 主线集成 / 版本发布 / 产品交付 必须分开汇报；未绑定的层不得声明完成。

## 4. 目标环境只读探测（2026-10-14，部署面 `d2079888`，DB `sc_demo`）

受管只读载体 `odoo.shell.exec`（`sc-root`，远程 HEAD 回读 = `d2079888`）实测：

| 事实 | 值 |
|---|---|
| `sc.tenant.company.registration` 行数 | **0**（无任何数据空间登记） |
| `sc.environment.role` | 未声明 |
| `is_platform_bootstrap_company=True` 公司 | 无 |
| fixture 自有公司 | `fe_company_a`→21「FE Company A」、`fe_company_b`→22「FE Company B」 |
| `fixture_role_finance` | uid 210，company_ids [21,22]，非客户组=False，`_sc_data_company_ids()`=**[]** |
| payment.request 36178 | company_id=21，`check_access_rights('read')`=ok，`check_access_rule('read')`=**AccessError** |
| 全局规则 | `ir.rule#832`「SC Data Scope - payment.request by allowed companies」 |

结论：`/api/v1/intent`（`ui.contract.v2`）403 的唯一根因是**目标库未完成数据空间登记**，
使 PR #654 的全局用途上限规则 fail-closed 命中 `('company_id','in',[])`。

## 5. 本轮产品修复（工作区，已验证）

### 回归 1：契约导航丢失「角色首页」

- 事实：契约 `index` 声明 90（`config/frontend/acceptance_environments_v1.json` →
  `navigation_policy.action_count_authority`，principal_role `business_config_admin`），
  部署实测 89。
- 根因：Odoo `_visible_menu_ids()` 以 action 为中心，`menu_sc_workspace_home`（`res_model=""`、无 action、
  `entry_target_policy=scene_entry`）永不可见；PR #654 让授权阶段消费该集合，于是该载体在授权链被丢弃。
- 修复：`MenuFactService.export_authorized_menu_facts()`（按 `groups_id` + 祖先链 ACL 过滤，fail-closed）
  成为授权来源；`export_visible_menu_facts()` 保持渲染语义不变。

### 回归 2：fixture 遗留载体无法完成数据空间入驻

- 事实：`smart_construction_acceptance_fixture` 已安装，但目标库无登记；
  旧版 fixture 先绑定 `fe_company_a/b` 再补登记能力，HEAD 版 `_company()` 对此直接
  `RuntimeError(... use governed baseline reset)`，即目标库无法重跑 fixture。
- 修复：fixture 对**自己 XMLID 锚定**的遗留公司改走声明维护入口
  `data_space_provisioning.adopt_business_company(...)` 收养一次（幂等、逐公司、fail-closed：
  非自有公司 / bootstrap 公司绝不收养）。定位为「新增平台维度 → 迁移收养」，
  与「自有业务事实冲突 → 基线重置」区分。

### 修复 2 在目标环境的首轮执行结果（2026-10-14）

经受管入口 `make daily.runtime.lifecycle_fixture.prepare`
（`CONFIRM_DAILY_RUNTIME_LIFECYCLE_FIXTURE=DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE`，
`DAILY_RUNTIME_EXPECTED_SHA=d2079888…`，仅写 `daily_dev` fixture 范围）驱动**工作区** builder：

- 登记收养路径已生效（`_require_activity_company` 通过，说明 FE 公司登记已在本事务内建立）；
- 随后被**另一处既有载体漂移**阻断：
  `RuntimeError: Activity move ownership mismatch; use governed baseline reset`
  —— `fe_activity_journal_entry`（`account.move` id 8）company_id=**1**（受管基线预置的示例公司，非 FE Company A），
  而 fixture 声明其属于 FE Company A；
- 事务整体回滚：复测 `registration_count` 仍为 0，**目标库未被改动**。

即：`sc_demo` 存在两类事实，需分开处置：

| 事实 | 性质 | 处置方向 |
|---|---|---|
| FE 公司缺数据空间登记 | 新平台维度未迁移 | 本轮修复（收养），已验证可执行 |
| `fe_activity_journal_entry` 公司归属漂移 | 自有业务事实冲突 | fixture 自身声明的「governed baseline reset」，或单列受管数据修复 |

## 6. 状态

- 批次验收：**未完成**。两条产品回归已修复并通过所属层门禁；
  目标环境验收仍受「目标库未完成登记 + 需部署修复后才能达到契约 90」双重阻塞。
- 主线集成：本棒后续完成（产品修复走受保护 PR）。
- 版本发布：沿用上一棒（目标环境 = main `d2079888`）。
- 产品交付：**未声明**。

## 7. 交接

| 项 | 值 |
|---|---|
| 候选分支 | `audit/target-env-role-acceptance-20261014` |
| 候选 HEAD | `36bbf88cdf181bc0b8d6f15d5549cd204974e958` |
| 基线 | `d2079888`（main，含 PR #654/#655/#656） |
| PR | https://github.com/lidefend/sce-backend-odoo/pull/657（base `main`，远端门禁运行中） |
| 目标环境 | daily `sc_demo`，部署面仍为 `d2079888`（未变） |
| 未改动 | 目标库（复测 `registration_count`=0）、部署 checkout、任何业务数据 |

下一精确步骤：

1. 等 PR #657 在**该精确 HEAD 与基线**上远端门禁通过（新 HEAD 不继承旧结果）；
2. 取得所有者裁定：`fe_activity_journal_entry` 公司归属漂移如何处置
   （受管基线重置 / 按行受管修复）；
3. 集成并重新发布 daily 后，重跑受管 fixture 入驻与分角色只读验收，
   绑定允许/拒绝证据。未完成前不得声明批次验收或产品交付完成。
