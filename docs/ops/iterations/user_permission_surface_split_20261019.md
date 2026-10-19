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

## 部署后集成收口补验

候选 2714c3a06b2006cb5f358bbbe24742fd7db93bf3 已在日常服务器受管同步，三个人员视图 apply/verify、demo/platform_control refresh 和入口核验通过；10 个业务/授权事实表摘要不变，无升级、seed/reset。两入口 form-profiles 共 24 项、detail-only 共 16 项通过，1440/390 宽度均无运行错误。原始证据在 `.runtime/p1-user-permission-closeout/`；外部归档见该目录 archive receipt。权限角色显示 #117 留作关系标签来源后续调查，不宣称完整权限 UX 已收口。

首轮精确 HEAD Quick 在守卫登记检查失败：unittest 模块写法被识别为文件消费但未被归类为 Make 接线。P4 最小修正为等价的 unittest 文件路径写法，测试断言不变。影响集仅 make/runtime_ops.mk 的这一验证命令及台账；产品、浏览器探针和部署工具输入未变，已完成页面/业务事实结果保留，新的候选重新取得 Quick。主线集成仍 pending。

### 集成探针过期断言修复（P4）

Quick v2 在 cef06a367 启动后，独立复核发现更早集成前置缺口，已主动停止，不记 PASS。现有 path_ns_c 探针及 evolution 绑定仍要求裸根308跳Demo，与生效入口声明要求400/NS_NAMESPACE_REQUIRED相冲突；还硬编码 admin 密码。仅修验收工具与绑定：裸根拒绝、两职责admin显式凭据输入（缺失在网络前停止）、SSH stdin传递凭据且参数安全引用。保留同名登录、跨库重放拒绝、退出隔离与公司拒绝，不改认证、入口或数据库事实。9项探针单测与27项绑定单测通过。实际凭据须取既有受管权威，不能把数据库密码/引导密钥推定为网页密码；已请求现有路径，不要求改密码。

完整合并证据还要求列表结构与关系回环，其现有声明最小项不由40个定向表单项替代。复用已有只读入口和受管记录解析，不补fixture。现有测试产生的 aaaa… 空 evidence manifest不是验收回执，不得继承。待工具收敛后统一冻结、补实际证据、取得Quick及远端门禁。

复核补充：远端非零退出即使返回PASS JSON也必须失败，并将传输失败写入报告。受管 `daily.runtime.record_identity.resolve` 已只读解析2714实际部署的现有记录，证据 `record_identity_report.json`；未安装或补充夹具。

### 日常实测纠正与前置闭合

所有者要求直接核验日常环境。两职责现有同名admin认证、双向token重放拒绝、退出隔离、公司越权拒绝均通过，未改密码或业务/授权事实。凭据缺口已消除。

纠正上一节错误判断：生效声明 `daily_runtime_entry.v1.json.public_entry` 明确裸网页根308转 `/t/demo/`，仅无命名空间API拒绝。此前据检查名称误推网页根必须400，是验收工具判断错误，不是产品缺陷。探针改为消费目标仓现有重定向声明，拒绝未声明/错误/外域跳转；保留API400与全部身份隔离。9项定向单测通过，实际23/23检查通过。

人员列表首次因浏览器网络切换失败，结构108/108、记录8/8和5个负例均过但不认可整份报告；四次HTTP200和版本稳定回读证明恢复后，仅该入口补验，结果全过、运行错误0。关系回环13项声明、4项可打开，返回路径/标题/状态栏/页签/动作恢复且零错误。现只剩最终候选身份绑定、Quick、远端门禁和受保护合并，不再请求重复授权。

### 验证入口覆盖收口

afdf候选四套精确运行证据均PASS且已外部归档；Quick在verification lane覆盖检查阻断，发现4个新增入口没有执行引用。P4修正：两项纯单测接入本地/远端共同架构套件；两个人工受管操作（三视图部署/恢复、local.dev回滚演练）登记owner/运行依据，不接自动CI。经独立复核，工具重生成的基线仅将这两条操作加入冻结身份集合，raw上限794→796；未登记项及所有其他豁免阈值保持0。记录型统计为实际测量更新，不充当功能验收。产品/浏览器/部署工具输入不变；新增候选仍按现有精确绑定门禁收口。

两纯测试依赖直接写入 make/ci.mk 的原始架构套件定义，避免旧守卫将跨文件同名追加规则误识别为覆盖原recipe；没有修改守卫或增加假豁免。guard registry与覆盖守卫PASS，完整受影响架构聚合PASS（含387个Node脚本语法检查）。此前未执行的同层检查已集中完成，无剩余已知代码/工具阻断。

### 远端测试加载修复（d354 后续）

P4 / make/frontend.mk：Node22 的 strip-types 不解析传递依赖中的无扩展名 contractGap 导入；远端 frontend_release_gate 39231770945 因 localized_display 测试无法加载而失败，产品构建通过。改用既有 esbuild 打包测试机制并保留原 import.meta.url，使源文件断言仍检查仓库实际文件。范围为验证入口及本记录/run；不改变 P0/P1/前端产品源码。L1 iteration + L2 localized_display 为最早检查；L3/L4 的四套 d354 运行证据按未变输入复用，禁止改造产品代码迁就测试解析。新精确 HEAD 仍需 Quick、独立复核、远端门禁。
