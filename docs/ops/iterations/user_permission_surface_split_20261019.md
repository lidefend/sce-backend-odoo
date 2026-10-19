# 人员档案 / 数据权限产品面职责拆分

状态：候选离线、事务 ORM 与契约演练通过；尚未部署，目标页面验收未执行。

任务：`P1-USER-PERMISSION-SURFACE-SPLIT-20261019`

基线：`feature/user-permission-surface-split-20261019` /
`7cada7699c5340bc85c40d735fba60cee1b22965`

## 判定

人员档案与数据权限的信息混同属于**产品面未收口**，不是 Demo 数据越界：
本次未修改任何 `demo_addons` 种子，也未持久修改既有业务或授权事实；
事务测试及三视图演练包含已回滚的数据库写入。两个入口继续使用同一
`res.groups` 与 `sc.project.member.assignment` 权限事实，没有新增第二套授权表，
也没有复制授权数据。

本批替代 `business_entry_surface_normalization_batch_2a_20260913.md` 中“待产品
决策：是否收回业务配置管理员在人员档案中的授权维护能力”的未决状态。决策结果
是职责拆分，且数据权限入口对业务配置管理员与行业配置管理员均保持可达。

## 职责矩阵

| 入口 | XMLID | 承载 |
|---|---|---|
| 人员档案 | `action_sc_runtime_user_management` / `view_sc_runtime_user_form` | 姓名、联系方式、部门、岗位、在职、登录账号/密码、档案附件、主公司（账号归属事实） |
| 数据权限 | `action_sc_product_data_permission_v1` / `view_sc_data_permission_user_form` | 主公司与允许公司范围、业务权限角色、项目成员授权，四段结构与只读身份 |

人员档案的 tree/search 不再声明业务角色；form 不再声明允许公司、业务角色和
项目成员授权，也不再保留“授权维护（兼容入口）”页。账号页的公司分组更名为
“账号归属公司”，仅保留 `company_id`。

数据权限视图保持四段：

1. `sc_permission_identity` 人员身份（`name` / `login` / `active`，只读）
2. `sc_permission_company_scope` 主公司与允许公司
3. `sc_permission_business_roles` 业务权限角色
4. `sc_permission_project_scope` 项目数据范围

## 能力不回退证据

静态声明证据（本批未改动入口授权）：

- `menu_sc_product_data_permission_v1` 的 `groups` 同时包含
  `group_sc_cap_config_admin` 与 `group_sc_cap_business_config_admin`。
- `action_sc_product_data_permission_v1` 的 `groups_id` 同时包含
  `group_sc_cap_config_admin` 与 `group_sc_cap_business_config_admin`。
- `addons/smart_construction_core/tests/test_data_permission_surface.py` 已增加
  menu/action 两组授权断言，并保留既有
  `test_runtime_menu_visibility_delivers_product_config_to_business_admin`
  对业务配置管理员菜单可见性的运行态断言。

结论：删除人员档案内的兼容授权页不会切断现有授权维护者的入口能力。运行态
菜单可见性测试本次未执行，原因见“未覆盖/阻断”。

## 改动清单

- `addons/smart_construction_core/views/support/runtime_user_management_views.xml`
  - 人员档案 form 删除 `sc_compatible_authorization_maintenance` 页；
  - 删除 `sc_user_role_group_ids` 与 `sc_project_member_assignment_ids` 控件；
  - 删除账号页 `company_ids`，`sc_company_scope` 改为 `sc_account_company`
    “账号归属公司”，只保留 `company_id`；
  - tree/search 删除业务角色相关列与搜索项；
  - 数据权限视图未改。
- `addons/smart_construction_core/tests/test_data_permission_surface.py`
  - 人员档案断言改为“不含权限控件与允许公司”，覆盖 form/tree/search；
  - 数据权限断言四段结构、身份只读、授权可编辑、不用
    `sc_user_role_group_ids`；
  - 增加数据权限 menu/action 双组授权断言。
- `addons/smart_core/utils/contract_governance_enterprise_forms.py`
  - 通用企业用户表单投影删除 `sc_user_role_group_ids` 的 `permissions`
    分组与字段归类，避免非原生路径继续投影人员授权控件。
- `addons/smart_core/utils/contract_governance_registry.py`
  - 企业用户表单字段顺序与标签移除 `sc_user_role_group_ids`。
- `scripts/verify/contract_governance_enterprise_forms_split_guard.py`
  - 同步字段顺序、三组结构和“不得投影授权字段”断言。
- `scripts/verify/user_permission_view_contract_boundary_guard.py`
  - 按入口拆分字段/分组标签与禁止项；
  - 人员档案检查不含允许公司、业务角色、项目成员授权；
  - 数据权限检查四段结构、独占字段与业务配置管理员入口授权。
- `scripts/verify/local_dev_personnel_authorization_browser.mjs`
  - 授权旅程改走数据权限入口；
  - 人员档案增加“无兼容授权页、无项目成员授权、无允许公司”断言。
- `docs/ops/iterations/user_permission_surface_split_20261019.md`
  - 本记录。

## 原执行器验证结果（接管前）

| 命令 | 结果 |
|---|---|
| `pwd && git rev-parse --show-toplevel && git branch --show-current && git rev-parse HEAD && git status --porcelain=v1` | PASS；分支与 HEAD 符合基线 |
| `python3 -m py_compile <涉及脚本与测试>` | PASS |
| `xml.etree.ElementTree` 解析三个 XML | PASS（3/3） |
| `python3 scripts/verify/contract_governance_enterprise_forms_split_guard.py` | PASS |
| `python3 -m unittest scripts.verify.test_local_dev_personnel_authorization_fixture -v` | PASS（7 tests） |
| `make verify.user_module.product_boundary` | PASS |
| `make ci.local.iteration` | 首次因调度器登记的 `.agent/active-runs.json` 未在 run scope 内返回 reconcile；将该登记文件纳入 scope（未改其内容）后复跑 PASS；`baseline_iteration_execution_policy_guard` 16 tests OK，`status=resolved` |

## 接管前未覆盖项（后续状态见接管结果）

- `make verify.user_permission_view_contract_boundary.guard DB_NAME=<库名>`：
  **not_run**。现有 `sc-local-dev-odoo-1` 挂载
  `/home/lidefend/workspace/sce-backend-odoo/addons`，不是本工作树；容器内视图仍包含
  `sc_compatible_authorization_maintenance`。直接运行会把另一个工作树的旧代码
  当成本批证据，因此不执行。
- Odoo 定向测试 `test_data_permission_surface` 与
  `test_user_module_product_closure`：**not_run**。原因同上：没有绑定本工作树的
  可用本地库与既有租约，且本批不写库。
- `scripts/verify/local_dev_personnel_authorization_browser.mjs` 的浏览器旅程：
  **not_run**。需要 `sc_dev_demo`、前端候选与租约；本次只做 `node --check`
  静态语法校验和 fixture 单测（7 tests）。
- `contracts/generated/product_view_structure_contract.json`：**not regenerated**。
  该文件是另一分支 / `sc_clean` 的生成基线（`authority.branch` 为
  `feature/native-view-action-semantics-closure-v1`），本工作树没有绑定数据库可重导出；
  未手改生成物。有库环境应通过结构导出 lane 重新生成后再做基线比对。

## 边界确认

- 未修改 `demo_addons` 种子；未写数据库；未 commit/push/部署。
- 未修改 `.agent/active-runs.json` 内容；该文件中的本任务分支登记由调度器维护。
- 未修改前端业务代码；本次只同步了验证脚本。

## 原执行器下一步（由下方接管结果替代）

在有本工作树绑定租约的环境中执行：

1. `make verify.user_permission_view_contract_boundary.guard DB_NAME=<库名>`
2. Odoo 定向测试 `test_data_permission_surface` 与
   `test_user_module_product_closure`
3. 如需要，运行浏览器授权旅程确认数据权限入口可完成创建、停用、恢复与最终停用

若运行态守卫暴露契约投影差异，优先在 P1 视图/声明层修正，不放宽断言。


## 接管收口结果（2026-10-19）

所有者确认原执行器已停止；当前助手接管同一候选，保留原有改动，未 commit/push。
职责：P1 人员入口声明与权限事实边界；P0 只移除已有兼容投影中的重复控件；
P4 修复只读守卫与复用 local.dev 的回滚演练入口。无前端业务代码改动。

所有者补充的产品规则：Demo 已独立建库，产品面对演示人员与普通企业人员采用同一规则。
不得依赖 demo 前缀、姓名或演示标识推导人员可见性或权限。保留部署/备份环境身份，
不更名现有账号、不删除环境登记。本次不进行演示数据重建。

修复与验证：

- 原执行器留下的无账号自动建用户逻辑已删除；接管后补齐首选账号的角色、启用和内部用户检查。
- 守卫去除 demo/legacy 前缀、姓名及旧客户档案存在性的推断，按当前人员入口声明验证。
- 人员档案修改主公司时不得扩大既有允许公司范围；允许在已有范围内切换。
- 旧测试三项失败来自未登记的默认公司。复用 BusinessTransactionCase 后，26 项模型测试通过，
  保留公司与授权拒绝用例，没有放宽 ACL 或记录规则。
- 用户资料、项目授权与公司范围 9 项，加数据权限/入口四项，共 13 项 Odoo 测试通过。
- 只读守卫 9 项、既有授权工具 7 项离线测试通过，表单投影守卫通过。
- 新增 local.dev.user_permission.rehearsal：沿用 sc-local-dev/sc_dev_demo 与主工作树受管凭据，
  临时 shell 从当前工作树加载源码，校验 XML SHA；只在事务中更新三个 ir.ui.view，禁止 commit，
  验证 XML、入口权限、ACL、人员域和实际契约后强制 rollback。
- 演练 PASS；用户、公司、员工、伙伴、角色、公司/角色关系、项目授权、关注关系、租户公司登记
  共 10 张表前后摘要一致，三个原视图恢复。此证据不等于已部署。
- ORM 测试创建事务夹具并回滚，不能称“从未执行写操作”；演练临时写产品元数据，
  不持久改变业务事实。未运行浏览器授权创建/停用/恢复旅程。

原始结果与日志统一引用本 run.json 和 .runtime/p1-user-permission-closeout/。
旧失败日志保留，后续 PASS 不覆盖失败历史。当前 HEAD 加显式 dirty 范围，不是冻结候选。

剩余：目标环境的持久视图更新、人员档案/数据权限两个页面的定向浏览器验收；
原 test_personnel_form_excludes_authorization_and_allowed_company_scope 的安装态测试尚未运行。
禁止为了验证把种子、真实用户或授权关系重置。部署时复用既有受管入口并先核对目标身份；
元数据更新完成后只读核对事实及页面，不运行授权写入旅程。主线集成、部署、用户验收均未声明完成。

回退：本轮候选演练已恢复原视图；源代码改动未提交，按本批 diff 单独回退，
不得 reset 其他任务或清理已有业务数据。

## 所有者确认的后续顺序

先完成本批 P1 日常开发服务器定向部署与受保护主线集成；Demo 数据完整调整
在 P1 合入主线后独立继续。本批不补数、不重置、不重放 seed。后续数据批次
按真实用户操作、中文业务数据、完整角色办理与展示链路验收，不引入 Demo
名称或前缀驱动的产品权限/可见性特判。环境数据库身份仍用于受管操作防误写。

## 受管部署准备复核

所有者已授权日常开发服务器部署和受保护主线集成。P1/P0 产品代码复核无剩余
S0/S1；P4 三视图工具经独立复核并运行 28 项测试通过。部署限定三个人员视图
arch_db，源权威仍是行业 XML，不运行模块升级、seed 或事实迁移。工具包含
精确候选/声明/实际数据库集群身份、原始翻译载荷备份、事实表锁与摘要、
契约检查后唯一提交、原子回执以及中断 reconcile/条件恢复。

当前补充验证：10 项只读守卫测试、28 项部署工具测试、ci.local.iteration、
ci.delivery.freeze.prepare 均 PASS。最新 local.dev 事务演练可见 50 名合格用户，
独立资格集合无遗漏，10 张业务/授权事实表摘要一致，三视图全部恢复。
本地没有现存停用人员样本，该运行态分支不声明通过；停用资格仍有离线/事务测试。
原始日志见当前 run.json，不复制为另一份结果索引。

生成报告新增 2 个测试资产（1564→1566），扫描文件新增 4 个（4895→4899），
需拆分数量仍为 71；既有 5 个已部署未集成提交导致的代码行数变化随生成物校正，
没有手改生成物。GitHub main 基线为 76aa6705685d60ca00b12184f0e1c8aa64a571a7，
本分支继承 65f844623、8a4767b8a、994c03e70、157bf6762、7cada7699，
PR 必须明确包含这五个既有候选提交；既有 Demo 种子源代码不代表本轮重放数据。

下一步形成清洁候选，在日常目标先 plan 后 apply/verify，刷新受影响职责并执行
两个入口的只读浏览器验收；精确 HEAD Quick/远端必需门禁通过才按保护规则合并。
此时仍未部署、未集成、未作用户验收完成声明。
