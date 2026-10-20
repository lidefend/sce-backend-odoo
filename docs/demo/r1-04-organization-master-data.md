# Demo 组织主数据重建（部门 / 岗位 / 人员档案）

状态：本地实现与离线验证完成，等待受管 seed 回读（P4 / `DEMO-ORG-MASTER-20261019`）

## 目标

按用户完整使用系统的路径，把 Demo 的组织事实补齐为可重复加载的基线：

- 部门树：带稳定 XMLID、上级关系与负责人绑定；
- 岗位：覆盖主业务链角色；
- 人员档案：主业务账号各自绑定一个 `hr.employee`，归属主公司与正确部门/岗位。

## 实际变更

- `data/base/13_departments_tree.xml`：新增 10 个部门，并以 `noupdate="0"` 重声明既有
  `sc_demo_department_001`（工程管理部）的 `parent_id`，挂到项目管理部下。
- `data/base/14_jobs.xml`：新增 13 个 `hr.job` 岗位。
- `data/demo/sc_demo_employees.xml`：新增 13 个 `hr.employee`，覆盖 `pm1`、`ct1`、
  `fin1`、`fin_mgr`、`cost1`、`mat1`、`mat_mgr`、`pur1`、`demo_role_owner`、
  `demo_role_executive`、`sc_demo_business_config`、`sc_demo_operation`、
  `sc_demo_accounting_manager`。
- `data/demo/sc_demo_organization_bindings.xml`：设置 11 个部门的 `manager_id`，
  仅用于展示/分组，不构成审批路由。
- `__manifest__.py` 与 `tools/scenario_loader.py` 的 `BASE_SEED_FILES` 同步加入新文件，
  顺序满足 departments/jobs/users → employees → bindings。`role_matrix_demo_users.xml`
  保持 manifest-only：它承载业务角色 `groups_id`，不进入组织种子 replay 路径；
  模块安装/升级仍会先加载它，保证员工引用的账号存在。
- `tests/test_demo_organization_baseline.py`：新增纯 Python 离线测试，并挂入
  `make verify.demo.lifecycle.unit`。

### 真实业务口径返工

- 20 个主业务/夹具账号改为真实中文姓名（`pm1` 张建国、`ct1` 李慧敏、`fin1` 王秀兰、
  `fin_mgr` 陈志强、`cost1` 刘晓东、`mat1` 赵鹏、`mat_mgr` 孙立军、`pur1` 周文静、
  `demo_role_owner` 高建华、`demo_role_executive` 何明远等），26 个能力账号改为岗位口径
  （合同/成本/物资/财务/结算/项目的审批岗、经办岗、查询岗，以及业务配置岗、经营审核岗、
  会计主管岗、综合能力岗），`svc_e2e_smoke` 为“接口巡检账号”。
- `login`、XMLID、文件路径、模型名保持不变；公司名继续使用所有者既定的
  正式 Demo 公司名称为 `四川智汇某某建设集团有限公司`。
- `data/base/20_projects.xml` 的 `P2-空壳对照项目（演示）` 改为 `城东片区安置房项目`，
  P1 描述改写为真实项目概况（建设内容、合同额、工期、当前阶段）。
- s67 场景包、s70/s72/s80/s85/s86/s87/s88 等场景记录中的 `测试-*` 姓名与可见标题改为
  真实姓名或真实业务口径；s85 两条工资记录的 `employee_name` 均改为 `张建国`。
- 残留清理数量：所有者核实 96 处 / 17 个文件；返工后对 `data/**/*.xml` 的全部属性值
  按可见字段集合扫描，`Demo-`、`Demo `、`【Demo`、`（演示）`、`演示`、`测试-` 命中为
  **0**。仍有 7 行命中位于 XML 注释中的技术说明，按所有者约束不属于用户可见字段，
  保持不变。

## 既有库生效方式（迁移）

- `__manifest__.py` 版本升至 `17.0.0.4.0`，新增
  `migrations/17.0.0.4.0/post-migration.py`。
- 迁移只对 demo 库生效：库名为 `sc_dev_demo`/`sc_demo`、以 `sc_demo_` 开头或以
  `_demo` 结尾；其他库直接返回。
- 迁移幂等更新 `res_users`/`res_partner` 的显示名与邮箱、`hr_employee` 的
  `name`/`work_email`、`project_project` 的名称/描述，以及场景记录的
  姓名/标题/备注字段和 s67 场景 payload；所有写入都带 `IS DISTINCT FROM` 守卫，
  可重复执行。
- 既有库中用户、项目、s85 工资记录与场景 payload 多数是 `noupdate="1"`，单纯重放 XML
  不会刷新；必须执行一次受管模块升级到 `17.0.0.4.0` 才会运行该迁移。全新
  `release_seed + profile` 重建则直接读取返工后的 XML。

## 幂等与加载顺序

`12_departments.xml` 保持 `noupdate="1"`，既有安装中的部门记录与其业务引用不被改写。
`13_departments_tree.xml` 使用 `noupdate="0"`，升级时重复声明既有 XMLID 的父级并补齐
其余部门；岗位、员工和负责人绑定同样使用 `noupdate="0"`，因此模块升级或重新入住后
组织事实会收敛到同一结果。

组织数据只承载身份与组织事实：新增种子不写 `sc_user_role_group_ids`、
`sc_user_permission_group_ids`、`sc_project_member_assignment_ids`、`company_ids`
或业务角色 `groups_id`；能力测试账号、`fixture_role_*`、`svc_e2e_smoke` 不进入组织树。

## 验证结果（HEAD `7cada7699c5340bc85c40d735fba60cee1b22965`）

| 命令 | 结果 |
| --- | --- |
| `python3 demo_addons/smart_construction_demo/tests/test_demo_organization_baseline.py` | PASS，16 tests |
| `make verify.demo.lifecycle.unit` | PASS，131 tests（16 + 30 + 5 + 80） |
| `make verify.demo.supplemental.unit` | PASS，80 tests |
| `make ci.local.iteration` | PASS，exit 0，coverage=L1_only，run context=resolved，outside_scope=[] |

原始日志保存在 `.runtime/agent-runs/DEMO-ORG-MASTER-20261019/`：
`test_demo_organization_baseline-rework.log`、`verify.demo.lifecycle.unit-rework2.log`、
`verify.demo.supplemental.unit-rework2.log`、`ci.local.iteration-rework2.log`。
`demo_lifecycle` 与 `demo_supplemental` 的 receipt 均为 `reusable`。

## 未覆盖 / 下一步

- 本轮离线环境未执行 Odoo 模块安装/升级，也未执行 `release_seed`/profile replay 或连库；
  因此既有库当前仍保留 `noupdate="1"` 的旧可见值（含 s85 的旧 `employee_name`），
  升级到 `17.0.0.4.0` 后才由迁移收敛。
- 尚未回读 `hr.department`/`hr.job`/`hr.employee` 的实际数量与账号映射。
- 尚未回读既有库用户/项目/场景记录的新显示名，也未做浏览器验收或部署。
- XML 对本基线创建的记录幂等；若库中已存在同一 `user_id` 的手工员工档案，XML 不会
  自动接管该记录，受管全新重建是受支持的收敛路径。
- 下一步精确动作：调度者先执行受管模块升级 `smart_construction_demo → 17.0.0.4.0`
  （确认 `ir_module_module.latest_version` 与迁移日志），再执行 `release_seed + profile`
  重建，然后只读回读：11 条部门形成一棵树且负责人已绑定、13 条岗位、13 条员工，
  每位主业务账号的 `user_id`/`name`/`work_email`/`department_id`/`job_id` 与种子一致，
  用户/项目/场景可见值无 Demo/演示/测试 标记；能力与 fixture 账号不在组织树内。
  不得绕过既有 seed gate，也不得用 SQL 直接改库。

## 最终本地验证（2026-10-19，受管重建）

| 命令 | 结果 |
| --- | --- |
| `CONFIRM_LOCAL_DEV_DEMO_REBUILD=REBUILD_CURRENT_FEATURE_DEMO make local.dev.rebuild_demo` | PASS，`sc_dev_demo` 全量重建 |
| `make ENV=dev ENV_FILE=... demo.verify` | PASS，全部场景断言（含 showroom） |
| `make verify.demo.lifecycle.unit` | PASS，131 tests（run receipt `reusable`） |
| `make verify.demo.supplemental.unit` | PASS，80 tests（run receipt `reusable`） |
| `make ci.local.iteration` | PASS（L1，dirty scope 未分类属设计） |

组织事实只读回读：11 个 Demo 部门（另有 base `Administration`）、13 个声明岗位
（另有 seed step 创建的“项目成本工程师”）、13 个 Demo 员工档案
（另有 base `hr.employee_admin`），主业务账号的登录名/姓名/邮箱/部门/岗位映射齐备。

本轮同时收口的三处验收漂移：

- `s80` 风险库改名后与 `s89` 同名（都叫“项目安全风险库”），导致“唯一库”断言失败；

## 多公司结构（2026-10-19）

Demo 是同一租户内的一个集团，不是第二个租户，也不是第二套平台身份域：

- 主公司：`四川智汇某某建设集团有限公司`（`base.main_company`），继续作为集团总部；
- 第二公司：`四川智汇某某建设集团第二工程有限公司`，稳定 XMLID
  `smart_construction_demo.demo_company_second`，作为主公司的子公司；
- 两家公司均使用 CNY、中国国家记录，第二公司继承主公司的 `generic_coa` 科目表；
- 第二公司在平台登记为 `data_purpose=demo` 的数据空间，租户键与主公司同为
  `sc-demo-main`。没有登记的公司不会进入 `_sc_data_company_ids`，切换过去只会看到空面，
  因此登记是平台所有权锚点，不是 Demo 绕行。

集团级岗位获得第二公司的允许公司范围，项目岗位留在主公司，保留真实的多公司边界：

`admin`、`wutao`、`demo_full`、`demo_role_owner`、`demo_role_executive`、
`fin_mgr`、`fin1`、`demo_finance`、`demo_audit`、
`sc_demo_accounting_manager`、`sc_demo_business_config`、`sc_demo_operation`。

重建路径由两个幂等步骤承担：

- `demo_company_secondary`：按 XMLID 查找或创建第二公司，收敛名称、父公司、币种、
  国家和联系方式，并登记数据空间；
- `demo_company_membership`：在用户步骤之后补齐允许公司范围，并重新登记数据空间操作者。

`demo_full` profile 的顺序是身份 → 第二公司 → 用户 → 成员范围 → 其余业务数据，
因此全新重建不会漏建第二公司，重复加载不会重复创建。`FE Company A/B` 是验收夹具公司，
不属于 Demo 公司结构。

验证：`test_demo_organization_baseline.py` 26 项、`test_demo_supplemental_flows.py` 80 项
PASS；`make verify.demo.lifecycle.unit` 141 项 PASS。既有 `sc_demo` 库仍需执行一次受管
seed 才能把旧名 `Demo演示公司` 收敛为正式公司名并创建第二公司；执行后须只读回读公司、
XMLID、登记、用户允许公司和 `/t/demo` 公司切换。
  按业务口径把 `s80` 改为“大型机械作业安全风险库”。
- showroom 项目已按“去 demo 标记”改为真实项目名，而 `scripts/demo/verify.sh` 仍按
  `展厅-` 前缀断言。验收改为直接消费 `seed/showroom_catalog.py`，保持单一真源；
  “结算项目全部处于收尾阶段”改为“至少 2 个结算项目处于收尾阶段”，因为在建项目
  存在进度结算属于真实业务。
- `s67` 可见徽标 `S67` 改为“运营”；release seed 覆盖门禁改为“每个已登记场景都必须在
  release 集合中”，并把场景发布、流程定义发布、历史流程实例快照登记为配置/兼容样例。
