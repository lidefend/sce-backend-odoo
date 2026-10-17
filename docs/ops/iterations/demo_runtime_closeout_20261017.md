# Demo 后续收口（2026-10-17）

## 边界

- 专题仅恢复 Demo；用户模块、性能专题及其他任务继续暂停。
- 受保护历史来源库不得改名、清理、迁移、升级或灌数。
- 声明已登记 `custody.service_face=initialized`；不默认重新建库或初始化。
- `daily.runtime.*` 只读探针会上传远程临时程序并在执行后清理；这是主机临时写，不称“零主机写”。
- 不因任务登记单独开 PR。

## 候选身份

| 项 | 值 |
| --- | --- |
| 分支 | `fix/demo-runtime-closeout-20261017` |
| HEAD | `80da1af3d060201cebbddc58146e940a7f34b570`（origin/main，PR #673） |
| dirty | 是，仅本 run 的 4 个登记文件（`.agent/active-runs.json`、goal、run、本记录） |
| run | `.agent/runs/DEMO-RUNTIME-CLOSEOUT-20261017/run.json` |
| 部署产品树 | `343a51d6ffda12e2b9fa05b098675b2c1e0ddd77`（daily-runtime 分支，未在 main） |
| 声明摘要 | `37b3b2fc91c770f9191e00d64aa90c7910ff299e81da4d8958d9e1992b30a4e5` |
| plan digest | DEMO-01: `be57b83c5377780f2294ed7d0b52ba2c08fc0c6b529f237e5b2fedf0acf939c0`；DEMO-02: `2a6e28bcd50135746502af2acb4f90b2dafb650be963466feb589f6326aea21a` |

## DEMO-01：声明／历史／实际运行事实对照

### 命令与结果

| 命令 | 结果 | 证据 |
| --- | --- | --- |
| `make agent.run.resume` | resolved；`outside_scope=[]` | 本次 stdout |
| `make verify.daily.runtime.database.duty` | PASS；65 + 156 = **221 tests OK** | `.runtime/demo-closeout-20261017/l1-duty-unit.log` |
| `make daily.runtime.database.duty.plan DAILY_RUNTIME_DATABASE_DUTY_SELECTION=demo` | **FAIL**；唯一失败断言 `served_container_publishes_the_declared_runtime_identity` | `.runtime/demo-closeout-20261017/database-duty-plan.json`、`duty-plan-demo.log` |
| `make daily.runtime.database.identity.inventory` | PASS；14 tests OK；失败断言 `[]` | `.runtime/demo-closeout-20261017/database-identity-inventory.json`、`db-identity-inventory.log` |
| `make daily.runtime.routing.inventory` | **FAIL**；`cluster_databases_observed`（探针固定 `psql -U odoo`，demo 集群无该角色）；22 tests OK | `.runtime/demo-closeout-20261017/routing-inventory.json`、`routing-inventory.log` |
| `make daily.runtime.tenant.topology.inventory`（仅 `sc_demo`） | PASS；18 tests OK；失败断言 `[]` | `.runtime/demo-closeout-20261017/tenant-topology-inventory.json`、`tenant-topology.log` |
| `GET :18081/api/runtime-version` | 200；`source_revision=ae4b1ad1…`，`frontend_build_sha256=""` | 本记录“实际”列 |
| `GET :18081/web/login` | 200 | 本次只读 HTTP |

### 对照表

| 事实 | 声明 | 历史记录 | 实际运行事实 | 状态 |
| --- | --- | --- | --- | --- |
| 集群 | `sc-demo-dev` / `sc-demo-dev-db-1` | 2026-10-16 重建 | project `sc-demo-dev`，container 存在且 running | 已完成（一致） |
| 数据库 | `sc_demo` | 2026-10-16 初始化并回写 | `sc_demo` 存在，owner `sc_demo_app` | 已完成（一致） |
| 数据卷 | `sc_demo_db_data` | 2026-10-16 重建 | `data_volume_owner=sc_demo_db_data`；单 postmaster、实例卷互异断言 PASS | 已完成（一致） |
| 系统标识 | `7697127891101417510` | — | 观测值相同（plan） | 已完成（一致） |
| 应用角色 | `sc_demo_app`；维护角色 `sc_demo_maintenance` | 2026-10-16 凭据采纳 | `sc_demo_app` 可连接、已认证，来源于 `/opt/projects/secure/daily-runtime-duties/sc-demo-dev.env`；登录角色 `sc_demo_app`/`sc_demo_maintenance` | 已完成（一致） |
| dbfilter | `^sc_demo$` | — | 实例 `ODOO_DBFILTER=^sc_demo$`；`application_instance_filter_is_exact` PASS | 已完成（一致） |
| filestore | scope `sc_demo`；卷 `sc_demo_odoo_data` | — | `/opt/sce-runtime/filestore/sc_demo`；`filestore_namespace_per_database` PASS | 已完成（一致） |
| 路由 | nginx `18081`；odoo `8070`；`list_db=false` | 2026-10-16 接管 | odoo 发布 `8070`；`18081/web/login` 200、`api/runtime-version` 200；`list_db=false` 未被工具观测 | 端口已完成；`list_db` **未知** |
| 部署源码版本 | product_root `/opt/projects/repos/sce-product-odoo` | 2026-10-16 `ae4b1ad1`；2026-10-17 `343a51d6` | 部署树 `343a51d6`；容器发布 `SC_SOURCE_REVISION=ae4b1ad1` | **缺失**（容器陈旧） |
| 前端构建摘要 | `dist-dev/.build-sha256` | `23e9f516…` | 部署文件 `23e9f516…`；容器 `FRONTEND_BUILD_SHA256` 为空；服务端响应 `frontend_build_sha256=""` | **缺失**（容器陈旧） |
| 模块集合 | `smart_core`、`smart_construction_core`、`smart_construction_demo` | 2026-10-16 seed 时版本相同 | 三者 `installed`；共 77 个模块；版本 `17.0.1.1.15` / `17.0.0.171` / `17.0.0.3.0` | 已完成（一致） |
| 服务面 | `custody.service_face=initialized` | 2026-10-16 初始化回写 | 栈运行、路由可用、模块已装 | 已完成（一致） |
| 正式样例链 | carrier `smart_construction_demo`，profile `demo_full`，stages `release_seed → profile` | 2026-10-16 13:38 seed PASS，17 步，remote head `ff66a708` | 现有数据与 seed 结果同量级；当前未重放 | 执行证据已完成；重放必要性 **未知** |
| 当前数据 | `CUSTOMER_BUSINESS_DATA_ALLOWED=false`；`FIXTURE_ALLOWED=true` | seed 生成 | 4 个声明业务模型共 **88 行**：contract 34、payment.request 35、project 15、payment.ledger 4；company 1，`data_purpose=demo`；公司注册完整 | 已完成 |

### 最早阻断

1. **服务容器运行时身份陈旧**：部署树已到 `343a51d6`（新增 `FRONTEND_BUILD_SHA256` 转发），但容器仍发布 `ae4b1ad1` 与空构建摘要。只读 plan 因此按设计 fail-closed。
2. 路由清单的 `cluster_databases_observed` 失败是**工具缺口**（固定 `psql -U odoo`），不是集群缺库；同一报告的实例、dbfilter、端口、卷断言均 PASS。
3. `list_db=false`、当前 seed 是否需重放：**未知**，待后续只读或受管阶段确认。
4. 主机存在 2026-10-16 13:52 的旧残留 `/tmp/sc-daily-legacy-stack-retire.py`；不属于本轮四个探针，本轮探针未见残留。

### 探针副作用（如实记录）

- `daily.runtime.database.duty.plan`：上传 `/tmp/sc-daily-database-duty.py`，在同一 SSH 命令中 `rm -f`。
- 身份/路由/拓扑清单：各自上传 `/tmp/sc-daily-db-identity-inventory.py`、`/tmp/sc-daily-routing-inventory.py`、`/tmp/sc-daily-tenant-topology.py`，执行后 `rm -f`；清理不在 `finally`，执行异常时可能残留。
- 本轮未写业务行、未改 schema、未重建容器、未升级模块、未 seed；报告只写本地 `.runtime/`。


### 验证与门禁

| 层 | 命令 | 结果 |
| --- | --- | --- |
| L1 | `make verify.daily.runtime.database.duty` | 221 tests OK（65 + 156） |
| L1 | `make verify.agent.ledger.unit` | 15 tests OK；guard PASS（goals=110 runs=87） |
| L1 | `make ci.local.iteration` | PASS；`coverage=L1_only`、`unmappedPathCount=0`，建议的 L2 目标即已执行的 duty 单测 |
| L2 | 受管只读清单（identity/routing/topology） | identity PASS、topology PASS、routing 仅工具角色断言 FAIL |

回执在 runtime 环境下按设计不可复用（`stale: runtime evidence requires authoritative environment readback`），不是测试失败。

### 证据索引

- `.runtime/demo-closeout-20261017/database-duty-plan.json` / `duty-plan-demo.log`
- `.runtime/demo-closeout-20261017/database-identity-inventory.json` / `db-identity-inventory.log`
- `.runtime/demo-closeout-20261017/routing-inventory.json` / `routing-inventory.log`
- `.runtime/demo-closeout-20261017/tenant-topology-inventory.json` / `tenant-topology.log`
- `.runtime/demo-closeout-20261017/l1-duty-unit.log`、`agent-ledger-guard.log`、`ci-local-iteration.log`
- 历史 seed 回执：`.runtime/final-acceptance/daily-deployed/database-duty-seed.json`（2026-10-16 13:38，PASS）

### 下一精确步骤

按 DEMO-02 执行 **Demo 专属受管 refresh**（`DAILY_RUNTIME_DATABASE_DUTY_SELECTION=demo` + 声明摘要），使容器发布 `343a51d6` 与 `23e9f516…`；随后重跑只读 plan，要求 `served_container_publishes_the_declared_runtime_identity` 转 PASS。当前无模块版本漂移，不进入 upgrade；不刷新共享源码/前端目录，不触碰三个职责。

## DEMO-02：Demo 专属受管 refresh

### 执行前置

| 项 | 执行时事实 |
| --- | --- |
| 本地候选 | 分支 `fix/demo-runtime-closeout-20261017`；HEAD `80da1af3d060201cebbddc58146e940a7f34b570`；dirty 仅本 run 的 4 个登记文件 |
| 部署产品树 | `/opt/projects/repos/sce-product-odoo`；HEAD `343a51d6ffda12e2b9fa05b098675b2c1e0ddd77`；detached、`git status --porcelain` 为 0 行 |
| 来源追溯 | 宿主 `FETCH_HEAD` 与 `reflog` 均指向 `343a51d6`；该提交在本地 `fix/daily-runtime-payload-import-closeout-20261016` 与 `origin/fix/daily-runtime-payload-import-closeout-20261016` 上存在 |
| 合并声明 | 原始文件 sha256 `16ae2580dcd5342c29d5c3229669556c46ebbef5d7562a4d108ab3540d360f88`；工具合并 managed binding 后的完整声明摘要 `37b3b2fc91c770f9191e00d64aa90c7910ff299e81da4d8958d9e1992b30a4e5` |
| managed binding | `/opt/projects/secure/daily-runtime-duties/daily_runtime_duty_instances.v1.json`，sha256 `e5d1fa0533aa96440c25ca45cf967c80644f12eba064fc668a4d416cc2de940f` |
| 三个职责 | `platform_control`、`demo`、`customer_tenant_dev` 均为 `role_compliance=compliant`、`service_face=initialized` |
| 影响边界 | refresh 只重渲染所选 duty 的栈文件和 env，按 `db/redis → odoo → nginx` 启动；无 `--build`、无模块安装/升级、无 seed、无数据库初始化，不触碰未选职责 |

### 命令与结果

| 命令 | 结果 | 证据 |
| --- | --- | --- |
| `make daily.runtime.database.duty.refresh`（`SELECTION=demo`、完整声明摘要、`EXPECTED_SHA=343a51d6…`） | PASS；`EXIT=0`；65 + 156 = **221 tests OK**；`failed_assertions=[]` | `.runtime/demo-closeout-20261017/duty-refresh-demo.log`、`database-duty-refresh-demo.json` |
| `make daily.runtime.database.duty.plan`（刷新后） | PASS；`EXIT=0`；`failed_assertions=[]`；plan digest `2a6e28bc…` | `.runtime/demo-closeout-20261017/duty-plan-demo-after-refresh.log`、`database-duty-plan-after-refresh.json` |
| `GET /api/runtime-version` | 200；`source_revision=343a51d6…`；`frontend_build_sha256=23e9f516…`；`database=sc_demo`；`environment=demo` | `.runtime/demo-closeout-20261017/http-after-refresh.json` |
| `GET /web/login` | 200 | `.runtime/demo-closeout-20261017/http-after-refresh.json` |
| `make verify.agent.ledger.unit` | PASS；15 tests OK；guard PASS | `.runtime/demo-closeout-20261017/agent-ledger-guard-demo02.log` |
| `make agent.run.resume` | resolved；`outside_scope=[]` | `.runtime/demo-closeout-20261017/agent-run-resume-demo02.json` |
| `make ci.local.iteration` | PASS；16 tests OK；`unmappedPathCount=0` | `.runtime/demo-closeout-20261017/ci-local-iteration-demo02.log` |

刷新完成时间：`2026-10-17T20:24:20+08:00`。Demo odoo 容器创建时间：`2026-10-17T20:24:13.506+08:00`。

### 实际变更对象

| 对象 | 刷新前 | 刷新后 | 结论 |
| --- | --- | --- | --- |
| Demo odoo 容器 | `0e0cd65fafddd6b52d59fdc6064f7c281419ea83b4b67484047159ace0d209e7` | `618fdb8956aeb0b229a6763ac68b3370dcaee234fe4129bde4585777a0c42bb1` | 重建；镜像未变 |
| Demo odoo 环境 | `SC_SOURCE_REVISION=ae4b1ad1…`；`FRONTEND_BUILD_SHA256` 缺失 | `SC_SOURCE_REVISION=343a51d6…`；`FRONTEND_BUILD_SHA256=23e9f516…` | 已对齐部署树和前端产物 |
| Demo 栈文件 | `duty-stack-b9d0305dc0dc.yml`，sha256 `b9d0305dc0dc…` | `duty-stack-45cc48f55bed.yml`，sha256 `45cc48f55bed…` | 旧栈文件被受管清理 |
| Demo env | sha256 `59db7dc069aad22114886d6db2387675a91bea9666108eaf1425400fa934505f` | sha256 `dd25bc954d6897500421b0624d045d10da541e382cdcb652af01199e298b76e6` | 凭据摘要全部保持不变 |
| Demo db / redis / nginx | — | 容器 ID、创建时间、镜像均未变 | 未重建 |
| platform_control / customer_tenant_dev 全部容器 | — | 8 个容器的 ID、创建时间、镜像均未变 | 未重建、未刷新 |

容器身份逐项对照见 `.runtime/demo-closeout-20261017/container-identity-comparison.json`：12 个容器中仅 `sc-demo-dev-odoo-1` 变化，其余 11 个完全一致。

### 刷新后运行事实

| 事实 | 观测值 |
| --- | --- |
| 部署源码 | `343a51d6ffda12e2b9fa05b098675b2c1e0ddd77`；宿主部署树 dirty 0 |
| 容器源码 | `SC_SOURCE_REVISION=343a51d6ffda12e2b9fa05b098675b2c1e0ddd77` |
| 前端构建 | 产物 `.build-sha256` 内容 `23e9f516c4f415428075eec70ddc457ebb7193dc8aff63a26d103a3df73bad22`；文件 sha256 `08ebf332dca47a7eec313dc94bf2f7221881e1e202405dee56139b1929efab44`；容器与接口一致且非空 |
| 集群 | `sc-demo-dev`；`system_identifier=7697127891101417510` |
| 数据库 | `sc_demo`；owner `sc_demo_app`；`allow_connections=true` |
| 数据卷 | `sc_demo_db_data`、`sc_demo_redis_data`、`sc_demo_odoo_data`；挂载与刷新前一致 |
| 应用角色 | `sc_demo_app`；login true、super false、createdb false、createrole false；指定凭据认证成功 |
| dbfilter | `^sc_demo$`；容器环境回读一致 |
| 模块 | 77 个 installed；`smart_core 17.0.1.1.15`、`smart_construction_core 17.0.0.171`、`smart_construction_demo 17.0.0.3.0`，与刷新前一致 |
| 服务面 | db/redis/odoo/nginx 均 running；odoo/nginx healthy |

刷新报告中的 `cluster.config_files` 是 materialise 前的观测；刷新后宿主回读和 plan 均指向 `duty-stack-45cc48f55bed.yml`。

### 恢复准备

- 数据卷未替换、未清空；本次没有模块升级、没有 schema 迁移、没有 seed，因此不涉及业务行回滚。
- 当前已审阅栈 `duty-stack-45cc48f55bed.yml` 与 env `sc-demo-dev.env` 均保留，容器故障时可由同一受管定义重建。
- 回退所需身份已记录：旧 odoo 容器 `0e0cd65f…`、旧源码 `ae4b1ad1…`、旧栈 sha256 `b9d0305dc0dc…`、旧 env sha256 `59db7dc0…`。回退须通过受管入口重新渲染旧审阅提交，不得直接改写数据库或手写业务终态。

### 保留项

- 路由清单固定 `psql -U odoo`：登记 P4 小修复，按声明维护角色连接并补反例测试。
- `list_db=false`：容器环境已回读为 false，但受管配置回读工具仍待补；接口 200 不用于证明该项。
- seed 重放：现有 17 步成功回执和行数不足以证明幂等性或证明必须重放；DEMO-03 先检查关联与业务行为，再确定最小重放范围。
- 临时探针异常清理缺口：本批不删除旧残留，继续登记。

### 本轮结论

**Demo 运行身份刷新完成。** 这不是最新主线部署，也不是 Demo 产品验收完成。

## 新载体入驻准备（暂停旧环境）

### 暂停决定

- 按调度指令，旧 Demo 环境不再执行新的写操作；已完成的 DEMO-02 refresh 保留结果，不回滚、不重跑。
- 暂停指令到达时没有在途写操作：refresh 已于 `2026-10-17T20:24:20+08:00` 完成，因此不存在被中断的事务。
- DEMO-03（正式样例链与重复执行验收）暂不启动；旧环境的 seed、replay、模块升级和进一步刷新全部暂停。
- 下一步改为“新载体入驻准备”，但新载体的主机、项目、数据库、端口、卷、凭据和部署源码尚未登记，不能由执行器推定。

### 只读盘点结果

| 项 | 观测 | 结论 |
| --- | --- | --- |
| 本机 SSH 别名 | `sc-root`、`sc-prod` | 无第三个新载体别名 |
| `sc-root` | 承载既有 `platform_control`、`demo`、`customer_tenant_dev` 三个职责及历史来源 | 旧载体，继续暂停写入 |
| `sc-prod` | 主机名 `ecs-f99b-7619`；运行 `sc_production`；`/opt/projects` 为空 | 生产宿主，不是待入驻空载体 |
| 受管 duty 实例 | `daily_runtime_duty_instances.v1.json` 仅含 `customer_tenant_dev` / `sc_tenant_demo_dev` | 新载体若为 customer duty，需走 managed 文档；若为 demo duty，需改模板声明 |
| 仓库声明 | `config/ops/daily_runtime_database_duties.v1.json` 仅含 `platform_control`、`demo` | 无新载体 duty 身份 |

本次盘点只读，未连接新载体、未安装服务、未创建目录、未写数据库。

### 暂停后的登记校验

| 命令 | 结果 | 证据 |
| --- | --- | --- |
| `make verify.agent.ledger.unit` | PASS；15 tests OK；guard PASS | `.runtime/demo-closeout-20261017/agent-ledger-guard-newcarrier.log` |
| `make agent.run.resume` | resolved；下一步已切到新载体入驻准备 | `.runtime/demo-closeout-20261017/agent-run-resume-newcarrier.json` |
| `make ci.local.iteration` | PASS；L1；`unmappedPathCount=0` | `.runtime/demo-closeout-20261017/ci-local-iteration-newcarrier.log` |
| `make verify.daily.runtime.database.duty` | PASS；65 + 156 = **221 tests OK** | `.runtime/demo-closeout-20261017/verify-duty-newcarrier.log` |

### 入驻前置身份（缺一不可）

新载体必须由调度方明确给出下列事实，执行器不得用默认值补齐：

| 类别 | 必需字段 |
| --- | --- |
| 主机 | SSH 别名、主机名/IP、`DAILY_RUNTIME_SSH_HOST` 绑定 |
| duty | `duty` 名称、`data_purpose`（demo/customer/platform_control）、`environment_id`、`tenant_key` |
| 数据库 | `database`、`database_role`、`dbfilter`、维护角色、系统标识 |
| 集群 | `compose_project`、数据库容器名、`data_volume`、`odoo_data_volume`、`redis_data_volume` |
| 存储 | `filestore_scope`、`session_namespace`、`backup_namespace` |
| 路由 | nginx 宿主端口、odoo 回环端口、`list_db` |
| 源码 | 部署产品树绝对路径、部署源码 SHA、前端产物目录与构建摘要 |
| 声明 | 声明文件路径、完整声明摘要、managed binding 路径与摘要（如适用） |
| 凭据 | 既有受管 env 文件路径（不新增凭据权威） |
| 恢复 | 恢复点、备份命名空间、回退路径 |

### 代码层硬约束（入驻前必须承认）

- `demo` 的数据库命名目前只允许 `sc_demo`；若新载体仍用 `sc_demo`，会与既有 `demo` duty 的数据库名重复，`validate_declaration` 以 `duties ... share database=...` 拒绝。
- 同一数据库名只能有一个可写 duty；历史来源只能登记为 `protected_historic_sources`，不能作为写入目标。
- 新载体若使用新数据库名，必须同步修改 `naming.database` 规则或明确其 duty 类型；不能靠改版本号或放宽校验绕过。
- 现有声明、栈模板、`ops_root`、`product_root`、前端产物目录和凭据路径均按 `sc-root` 书写；新主机若路径不同，需要独立声明或显式声明覆盖，不能复用旧路径猜测。
- 新环境或新凭据权威必须单独授权；本专题不自行创建 Compose 项目、数据库、端口、卷或凭据。

### 前置通过后的受管顺序

1. 只读校验候选声明：`make verify.daily.runtime.database.duty`。
2. 只读计划：`make daily.runtime.database.duty.plan`，绑定完整声明摘要。
3. 经调度审核后，才允许 `apply` / `initialize`；两者都必须绑定 reviewed digest 与确认令牌。
4. 仅 demo duty 允许按声明执行 `release_seed → demo_full`；customer duty 不得灌客户数据。
5. 执行后回读容器、数据库、卷、dbfilter、模块、源码与前端摘要，并保留恢复路径。

当前状态：**新载体入驻准备就绪，等待调度方提供精确载体身份。** 旧环境保持暂停，不进入 DEMO-03。

## 2026-10-17 运行时缺陷闭环（本地 sc-local-dev / sc_dev_demo）

原始失败：`demo.load.full` 在 `step_demo_showroom.py:183 → settlement_order.py:1444` 触发
`construction.contract` AccessError。归因为 P1：结算明细创建会无条件校验继承自父结算单的
合同可见性，而结算经办能力没有合同只读。

修复：

- `addons/smart_construction_core/security/sc_capability_groups.xml`：`group_sc_cap_settlement_user`
  显式继承 `group_sc_cap_contract_read`（只读），结算主管经同一继承链获得；未放宽记录规则。
- `addons/smart_construction_core/models/core/project_core.py`：项目结项守卫对
  `project.settlement` / `payment.request` 的存在性计数改用内部提权，避免把财务读权限
  变成项目经理结项的前置条件；不向操作者返回记录。
- 新增 `addons/smart_construction_core/tests/test_settlement_contract_read_capability.py`。

验证（本地开发栈，非部署、非生产验收）：

| 命令 | 结果 |
| --- | --- |
| `make local.dev.upgrade MODULE=smart_construction_core` | PASS；运行库回读确认结算经办继承“合同中心只读” |
| `make local.dev.demo.seed STEPS=demo_showroom` | 修复前 FAIL；补能力后通过合同校验，暴露结项守卫缺财务读；守卫修复后 PASS |
| `make demo.load.full` | PASS，exit 0；日志 0 次 `AccessError`、0 次 `make: ***` |
| 新增静态测试 / `role_acl_minimum_set_guard.py` | 4 tests OK / PASS |

证据：`.runtime/demo-local-20261017/demo-load-full-after-fix.log`。剩余阻断与下一步以
`.agent/runs/DEMO-RUNTIME-CLOSEOUT-20261017/run.json` 为准。

## 2026-10-17 BATCH-02：载体身份、路由角色与受管回读

本批只做代码修复与只读取证，未刷新、播种、重放、升级、部署，也未写数据库/容器/生产数据。

### 新载体与暂停对象

- 新载体：`sc-local-dev` / `sc_dev_demo` / 角色 `odoo` /
  `system_identifier=7674830867180216358`；卷 `sc_local_dev_db_data`、
  `sc_local_dev_odoo_data`；入口 `http://127.0.0.1:18081`。
- 暂停对象：远端 `sc-demo-dev`（`sc_demo`，`sc_demo_maintenance`，
  `system_identifier=7697127891101417510`）、本地旧副本 `sc_demo`、`sc_production`、
  `sc-backend-odoo-prod`。旧 `sc-root`/`sc-prod` 不再作为新载体。
- 来源：`/tmp/env-carrier-identity-20261017.json`、
  `/tmp/env-carrier-topology-20261017.json`；固化证据
  `.runtime/demo-blocker-batch-02/carrier-readback.json`。

### 修复

- `scripts/ops/daily_runtime_routing_inventory.py`：移除硬编码 `psql -U odoo`。
  角色优先级为显式 `--database-role` → 集群容器环境 `POSTGRES_USER`/`PGUSER`/`DB_USER`；
  缺失或冲突时 `cluster_error` 非空并 FAIL。新增 `--local` 只读本机载体模式（必须同时给出
  database、cluster container、compose project）以及 `--expect-compose-project` 断言。
- 上传探针改为 `try/finally` 清理；`scripts/ops/daily_runtime_legacy_stack_retire.py`
  与 `scripts/ops/daily_runtime_database_identity_inventory.py` 同样把 upload 纳入
  `try`（失败也执行 `rm -f`），`/tmp/sc-daily-legacy-stack-retire.py` 残留已确认归属并删除。
- 交叉审查 F1/F2：`list_db_env` 现在有消费断言 `database_enumeration_closed`（发布
  host port 的 serving 实例必须为空或 false，`1/true/yes/on` 均 FAIL）；非零
  `pg_control_system()` 写入 `cluster_system_identifier_error`，由
  `cluster_system_identifier_observed` 断言 FAIL 而不是把空值当成功。角色发现路径
  增加字符集校验（`DATABASE_ROLE_INVALID`），本地探针改走 stdin，不再写固定
  `/tmp` 路径。
- `make agent.run.resume` 在声明 `kind=runtime` 的 run 上仍把 `daily_duty_unit`
  报告为 `stale`（"runtime evidence requires authoritative environment readback"）；
  该目标本身已重跑 221 tests PASS 并重录 receipt，stale 属台账复用规则限制，
  因此对应阻断保持开放，未在本批关闭。
- `scripts/ops/daily_runtime_database_identity_inventory.py`：新增 `list_db is False`、
  exact dbfilter、configured `db_name` 断言与 `--local` 受管回读。
- 新增 `addons/smart_construction_core/tests/test_project_close_guard_internal_privilege.py`：
  两个结项守卫必须经 `.sudo()` 计数且不返回记录。

### 只读实测

| 命令 | 结果 |
| --- | --- |
| routing inventory `--local`（sc-local-dev） | PASS，角色 `odoo`，`cluster_error` 空，含 `sc_dev_demo` |
| routing inventory `--duty demo --ssh-host sc-root` | PASS，角色 `sc_demo_maintenance`，`cluster_error` 空 |
| routing inventory 故意错误角色 | FAIL，`cluster_error` 非空（fail-closed） |
| database identity inventory `--local` | PASS，`list_db=False`、`dbfilter=^sc_dev_demo$`、`db_name=sc_dev_demo` |
| `POST /web/database/list` | JSON-RPC AccessDenied，无库名 |
| 定向单测 | routing 40 / legacy 39 / identity 20 / guard 3 / settlement capability 4，全部 OK |
| `make verify.daily.runtime.database.duty` | PASS，65 + 156 tests |
| `make ci.local.iteration` | PASS（L1 only；4 个未映射产品路径按设计待远端/风险选择） |

已知基线失败（非本批改动）：`test_um_p1_contract_settlement_visibility_boundaries.py`
的 `sc_record_rules.xml` 域期望不一致；该 XML 与 HEAD 完全一致。

DEMO-03 结论：本批不需要额外 replay；修复后的 `demo.load.full` 已在 `sc_dev_demo`
实际执行 `demo_showroom` 与 `demo_full` 两条 seed 链（日志第 8/13/18 行）并以
`demo_90_verify` 与 Odoo 重启结束。该结论不声称 seed 幂等或未来重放无损。

证据目录：`.runtime/demo-blocker-batch-02/`。
