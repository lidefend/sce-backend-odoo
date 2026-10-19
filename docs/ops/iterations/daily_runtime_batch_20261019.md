# 日常开发服务器 Demo 批次（2026-10-19）

状态：daily demo duty 已完成受管重建、数据只读回读与统一入口验收；
候选分支 `feature/daily-batch-demo-multicompany-20261019` 尚未合并主线。

## 边界与环境身份

| 项目 | 事实 |
| --- | --- |
| 本地工作树 | `/home/lidefend/workspace/sce-backend-odoo-local-env` |
| 分支 | `feature/daily-batch-demo-multicompany-20261019` |
| 基线 HEAD | `654a77bda9ddad1c98c29e055df2d19c1cac2497` |
| 远端运行树 | `sc-root:/opt/projects/repos/sce-product-odoo`，detached 同一 HEAD |
| duty | `demo` |
| carrier | `sc-demo-dev` |
| 数据库 / 应用角色 | `sc_demo` / `sc_demo_app` |
| 容器 | `sc-demo-dev-{db,redis,odoo,nginx}-1` |
| 受保护历史源 | `sc-backend-odoo-dev`（本轮不再写入） |

本批只处理日常开发服务器，不写生产环境；用户模块继续暂停。

## 批次结果

| 验证 | 证据 | 结果 |
| --- | --- | --- |
| 发布面收敛 | `.runtime/final-acceptance/daily-deployed/published-face-converge.json` | PASS，`head=654a77bd...`，`duty=demo`，`carrier=sc-demo-dev`，`role=sc_demo_app`，`guard_status=PASS` |
| Demo 受管重建 | `.runtime/final-acceptance/daily-deployed/database-duty-recreate.json` | PASS，恢复点校验通过，drop/create/seed 全部返回 0 |
| 双职责声明计划 | `.runtime/final-acceptance/daily-deployed/database-duty-plan.json` | PASS，`demo` 与 `platform_control` 均无失败断言 |
| 平台职责身份修正 | `.runtime/final-acceptance/daily-deployed/database-duty-refresh.json` | PASS，仅重建平台控制容器，未迁移数据、未安装模块 |
| 统一入口验收 | `.runtime/final-acceptance/daily-deployed/entry-verify-654a77bd.json` | PASS，66/66 断言通过 |

旧的 `.runtime/final-acceptance/daily-deployed/database-duty-seed.json` 是重建前失败尝试的
过期报告，已被 `database-duty-recreate.json` 取代，不作为最终证据。

## Demo 受管重建

重建由 `scripts/ops/daily_runtime_database_duty.py` 的 `recreate` 阶段执行，入口为
`make daily.runtime.database.duty.recreate`。该阶段只接受 `data_purpose=demo` 且不属于
受保护历史源的 duty，并在删除数据库前先捕获并校验本 duty 自己命名空间内的恢复点。

| 项目 | 事实 |
| --- | --- |
| 恢复点 | `/data/backups/daily-demo-dev/sc_demo-20261019T132446Z-4d915622/database.dump` |
| 恢复点 SHA256 | `c1808af2c2856d539cabaa0a3727961fccf61cb346919c9bc2498db81ff881f7` |
| 恢复点条目 | `22603`，`verified=true` |
| drop | `DROP DATABASE ... WITH (FORCE)` 返回 0 |
| 创建 | 5 个受管语句全部返回 0 |
| seed | `profile=demo_full`，`returncode=0` |
| 执行链 | `release_seed` → `demo_company_identity` → `demo_company_secondary` → 字典/项目/合同/财务 → `demo_company_membership` → 其余业务数据 → `demo_90_verify` |

## 平台实例版本漂移修正

本批入口复核发现：demo 实例已加载 `654a77bd`，但平台控制实例的容器环境仍固化为
`86c03b7a`，导致入口验收初次为 64/66。源码挂载本身是同一份最新代码，差异来自容器创建时
写入的 `SC_SOURCE_REVISION`。

处置：用 `make daily.runtime.database.duty.refresh` 只重建 `platform_control` 声明的
容器，不迁移数据、不安装模块。refresh 报 PASS，平台容器 `SC_SOURCE_REVISION` 回读为
`654a77bda9ddad1c98c29e055df2d19c1cac2497`；随后入口验收 66/66 PASS，前端指纹
`2d2a898ebf745de60ef9c1dbe4967d1fbc5e2538ddbea3889ac03057b624a456`。

## Demo 数据只读回读

| 项目 | 事实 |
| --- | --- |
| 公司 | 2 家：`四川智汇某某建设集团有限公司`（id 1）、`四川智汇某某建设集团第二工程有限公司`（id 2，parent 1） |
| 可见标记 | 公司名不含 `Demo` / `演示` |
| 数据空间 | 2 条，均 `tenant_key=sc-demo-main`、`data_purpose=demo`、`active=true` |
| 活跃用户 | 51 |
| 项目 | 15 |
| 施工合同 | 30；同一 `project_id + subject` 重复数 0 |
| 结算单 | 13（`sc_settlement_order`） |
| 采购单 | 11 |
| 发票 | 4 |
| 付款执行 | 3 |
| HR | 部门 12、岗位 13、员工 14（含 base 管理员） |
| 集团级账号 | `admin`、`wutao`、`demo_full`、`demo_role_owner`、`demo_role_executive`、`fin_mgr`、`fin1`、`demo_finance`、`demo_audit`、`sc_demo_accounting_manager`、`sc_demo_business_config`、`sc_demo_operation` 的 `company_ids` 均含两家公司 |
| 验收夹具记录 | `fe_company_a` / `fe_company_b` / `fe_project_a` / `fe_user_finance` 均为 0 |

## 验收夹具口径

Demo 是标准平台租户，只承载产品自己的 `smart_construction_demo` 数据链。本批同步修正
`config/ops/daily_runtime_database_duties.v1.json`：

- 移除 demo duty 的 `acceptance_fixture` 声明，并记录 `acceptance_fixture_policy`；
- `section_11.FIXTURE_ALLOWED` 改为 `false`；
- demo `stack.modules` 移除 `smart_construction_acceptance_fixture`。

因此后续受管重建不会再把 `FE Company A/B` 和夹具身份写进 demo 库。夹具模块与隔离验收
车道本身保留，不删除、不改造。声明修改后的双职责 plan 已 PASS。

需要如实登记的漂移：当前 demo 库是修改前那次重建产生的，`smart_construction_acceptance_fixture`
模块仍处于 installed，但夹具记录为 0，模块处于惰性状态；下一次受管重建会按新声明不再安装它。
依赖夹具身份的 `make verify.daily_dev.acceptance.readonly.probe` 车道目前没有适用于 demo 的
载体，状态为“待专用验收载体”，不得当作 PASS。

## 事故与保护

2026-10-19 曾误将受保护历史源 `sc-backend-odoo-dev-db-1/sc_demo` 执行模块升级。事故记录见
`.agent/runs/DAILY-RUNTIME-BATCH-20261019/incident-historic-source-upgrade-20261019.md`。
历史源尚未恢复，需所有者单独裁决；本批未再次写入该载体。

发布面收敛入口已改为从 duty 声明解析 carrier、数据库角色和环境文件，并拒绝操作员环境文件
绑定其他 carrier。历史源与 demo duty 同名 `sc_demo`，后续任何入口都必须按
carrier/container/data volume 识别目标，不能只看数据库名。

## 未覆盖与阻断

- 统一入口的登录后隔离尚无完整浏览器场景：本批 66 项入口断言覆盖路径命名空间、数据库提示
  拒绝、cookie 作用域与两职责版本一致性，但不等于“同一浏览器分别登录平台与 demo 后的
  会话、退出、权限隔离”已完成验收。
- `FE Company A/B` 夹具在 demo 无记录；隔离验收车道需要单独载体，当前未运行。
- 受保护历史源误升级事故保持登记状态，恢复方案未执行。
- 候选分支尚未合并 `main`，也未宣称主线集成完成。

## 下一精确步骤

提交并推送 `feature/daily-batch-demo-multicompany-20261019`，按普通 PR 流程执行远端必需
CI；CI 通过并完成独立复核后再合并主线。合并前不重复执行会写入 demo duty 的重建/升级。
