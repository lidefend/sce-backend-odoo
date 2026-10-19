# 系统权限角色专题

AUTH-01 基线：2eb4cae26b5a013cb2cebc5706df34047ea7847e；工作树复用，分支 audit/system-permission-roles-20261019。

所有者裁决：角色承载系统权限；岗位与任职由用户定义，不授予系统权限。

边界：本批 P4 离线声明核对和 P0/P1 设计文档。复用现有 role_catalog；不另造权限事实源，不修改产品运行代码、组、ACL、数据库或前端。行业默认归 P1；通用注册、发布、授权投影归 P0。离线声明不能证明实际安装、最终授权或用户可用性。

L0 HEAD+dirty范围；L1语法/diff/iteration；L2离线工具非零反例测试。L3/L4未运行：当前不修改运行逻辑，不具备完整运行验收结果。L5未开始：未冻结、未发布候选。

下一步：构建声明清单、继承闭包与目录覆盖差集，记录未知外部组和表达式，不把缺口报告伪装成产品门禁通过。

## 本轮结果

离线核对工具按P1 manifest加载顺序解析组关系，支持替换/追加/删除/清空；遇到未知表达式报告incomplete，外部依赖组保持unknown。8项反例测试通过。声明组63、可分配20、role_catalog代码9；21条角色行中，客商资料管理员是唯一无目录候选的可分配组。owner角色声明存在但当前未标记可分配。多数物资/采购/会计等角色通过继承命中project_member；候选命中不是最终身份或授权结论。

真实只读事务观察：服务器已由其他工作切到654a77bda9ddad1c98c29e055df2d19c1cac2497，不继承本地2eb4cae的运行身份。16名含角色组的活跃内部用户、覆盖14类角色组；restricted为0，身份/能力角色词表不同15例。此差异不直接证明功能错误，也不构成全部20个可分配角色验收。报告仅含UID与角色来源，不读取口令。原始证据.runtime/system-permission-roles/runtime.json、runtime-read.py、runtime.log。

已完成：本批离线工具、设计契约、首轮真实身份观察。未完成：依赖组完整闭包、全部授权写入口清单、真实system.init最终导航及代表操作、未覆盖角色的受管验收。AUTH-01整体仍verification_pending，不宣布权限体系已修好。

下一最早步骤：对照实际生效版本补齐未覆盖角色及直接授组路径；优先核查客商资料管理员和业务身份/能力词表分叉。未修改产品源码、数据库、岗位或授权组。撤销本批仅需撤销新增工具/文档；无需数据库恢复。

## AUTH-01 续跑：授权写入口与证据差集

身份：audit/system-permission-roles-20261019 @ 2eb4cae26b5a013cb2cebc5706df34047ea7847e + run.scope 中未提交工具/文档；未冻结。原主工作树的 dispatch-supervisor 改动不属于本任务，未触碰。

Formal Product Layer=P4；Layer Target=离线权限审计；Module=scripts/verify + make/role_authority.mk；Standard vs User-Specific=通用核验机制；Why Here=只枚举源声明和写入候选，不成为授权事实；Why Not Elsewhere=不在前端补角色、不用脚本修复或授予权限；Blast Radius=本专题离线报告。P1 产品缺陷仅登记。

影响分析：修改 inventory 工具及其测试和 Make 包装，失效集合仅 inventory_unit 与新 write_candidates。原 runtime.json 保持历史观察，不能提升为当前运行验收。新写入口盘点首次扫描 addons/scripts 下 Python/XML（排除 tests/ 与 test_*），不是重跑用户矩阵；2680 个输入以摘要绑定，160 个候选分布在 71 个文件。字典可能是读取/快照，须人工归因；动态键、SQL、原生 Odoo 和私有模块仍未闭环，不称全部授权写入口已覆盖。

已人工核实的路径：

| 来源 | 写入载体 | 当前判断及收敛归属 |
| --- | --- | --- |
| P1 runtime_user_management.py：两个权限字段 inverse、safe_vals、create/write | res.users.groups_id | 旧角色投影；显式与继承来源未分开，交 AUTH-03 单一分配服务 |
| P1 approval_scope.py：_inverse_user_ids | res.groups.users 整体替换 | **AUTH01-F01：与已确认岗位不授予权限边界冲突**；sudo 反向授组，不能漏审 |
| P1 approval_scope.py：action_create_user | 新建或复用用户后写 groups_id | **AUTH01-F01 同源入口**；以审批岗位选择决定组授权 |
| P1 auth_signup.py：_apply_user_defaults | groups_id 追加 | 来自 sc.signup.default_group_xmlids 运行配置，需核查实际配置及特权继承，不据静态源码断言已越权 |
| P0 hooks.py | 管理员组追加 | 安装技术授权，须独立登记并保留受管初始化路径 |
| P0 tenant_payload_operator.py | provision/grant/revoke 的 groups_id | 技术导入授权，已有独立授权与前后校验，不应作为普通业务角色入口 |
| P0 tenant_payload_import_batch.py：_enroll_data_space_operators | groups_id 追加 | 数据空间操作员登记，须保持租户与环境边界 |
| P4 scripts/ops、scripts/release、scripts/verify 及 fixture | 用户组追加/替换 | 技术初始化、修复与验收不能成为长期产品授权真源；候选清单保留，未执行这些写入 |
| XML res.users/groups 声明 | groups_id / users / implied_ids | 初始化或升级路径，离线出现不证明已安装；纳入候选输入 |

AUTH01-F01 证据链：approval_policy.py 的 APPROVAL_SCOPE_GROUP_XMLIDS 明确映射岗位到权限组；approval_scope.py inverse / wizard 执行授组；ir.model.access.csv 的 access_sc_approval_scope_business_config 与 wizard ACL 允许业务配置管理员维护。源码行为已确认，真实用户路径尚未执行；不能声称线上复现或漏洞利用。修复归 P1 岗位事实与 P0 授权分配分离，不能简单删除已有组成员或仅改界面文案。

未覆盖角色的确定性差集：当前 inventory.roles 中 assignable=true 的 XMLID 减去历史 runtime.json users[*].assigned_or_inherited_role_groups，得到 accounting_manager、accounting_read、accounting_user、business_admin、general_user、partner_manager、settlement_manager（均为 smart_construction_core.group_sc_role_ 前缀）。共7项；历史观察的14类含非可分配组，不能直接计算20-14。两份输入版本不同，此结果只用于补证计划，不证明当前数据库缺角色。已有观察也不是 system.init/实际操作验收。

验证：L1 make ci.local.iteration 通过（原始日志 .runtime/system-permission-roles/iteration-continue.log）；L2 make audit.system.permission_role.write_candidates 的14项测试通过，扫描初次因既有空 dashboard_views.xml 报 incomplete（write-candidates.log）。归因 P4 工具将空文件当作非法 XML；修复为空文件保留摘要且无声明，并加入回归断言，重新执行同一入口通过（write-candidates-recovered.log）。产物 write-candidates.json，authorization_verdict=not_evaluated。

L3/L4 not_run：本次没有产品运行改动，仍须先核对受管运行身份再补真实导航/操作；不以历史版本回执替代。L5 not_run：AUTH-01 尚有缺口，不能冻结/发布。批次 verification_pending；主线、部署、用户验收均未完成。回滚只撤销本次工具/文档差异，不涉及数据库。

下一步：以候选清单核完动态/原生/私有写入口，并在明确受管运行身份下补7类角色与真实 system.init/代表操作；AUTH01-F01 纳入后续分层修复单，禁止用增加用户组补平差异。

## AUTH-01 续跑：实际继承闭包、ACL 与最终导航

本轮继续 P4 核验工具，新增 system_permission_runtime_observation.py 及非零反例测试，复用 make/role_authority.mk。未改 P0/P1 产品实现。身份仍为2eb4cae26 + run.scope dirty；未冻结。

受管目标：sc-root / daily-dev-demo / duty=demo / sc-demo-dev / sc_demo；数据库卷 sc_demo_db_data；应用/filestore 卷 sc_demo_odoo_data，命名空间 sc_demo。复用 daily_runtime_duty_odoo_shell.py 和原 SSH 身份，不新建环境或凭据。原始挂载回读 demo-mounts-readback.jsonl。运行源码654a77bda9ddad1c98c29e055df2d19c1cac2497，报告从运行容器环境回读，不使用本地HEAD替代。首次 HTTP runtime-version 对127.0.0.1请求返回400，未当作身份成功；以远端Git回读、受管挂载及运行报告绑定身份。

数据库探针 SET TRANSACTION READ ONLY、拒绝commit、finally rollback；用户视角用 su=False，只读取UID和授权元数据，不读取口令，不新建用户/授组。返回20个可分配组及完整数据库trans_implied_ids闭包；闭包无未解析XMLID。13类有现有活跃内部用户承载，7类缺证与上轮离线差集一致。13个代表UID的5模型×4操作ACL已观测，但多角色用户的ACL不能归因于单一角色，也不证明记录规则/intent/实际操作通过。13人均无sc.approval.scope写ACL，不能用他们复现AUTH01-F01。

实际registry的res.users/res.groups MRO共37条create/write/unlink实现记录（含同文件多个类），每条含源文件SHA256。原生Odoo、mail、hr、auth_signup及smart_core/P1扩展有明确来源；这只补齐加载实现链，不等于全部动态调用入口已审完。另核实动态写路径：api_data.py / api_data_write.py接受经过滤的模型值执行create/write；tenant_payload_import_service._apply_system_user允许groups_id且经过adapter.assert_import_operator后sudo写入。上述路径必须纳入AUTH-03同一分配权威/技术授权例外设计，不能被仅查字面groups_id的扫描漏掉。

最终导航观察：使用真实SystemInitHandler.run，13名代表用户均su=False；13份返回均具有system_init.navigation声明且missing_authority_count=0。12名有非空动作导航；管理层UID49的visible/authorized action count均为0。无HTTP登录或router gate，本结果只能证明handler层观察，不能声称全链路验收。

针对UID49仅补了一次诊断（make audit.system.permission_role.demo_navigation.diagnostic ROLE_PERMISSION_DIAGNOSTIC_UID=49），未重跑其他12名。确定性影响集合={49}：新增输出role_surface/navigation_meta/default_route，只为解释空导航。诊断确认role_code=executive，deny_all_navigation=false，唯一primary_menu_xmlid=menu_sc_historical_payment_fact；本地P1 core_extension_policy_maps.py同样声明这一唯一主入口，test_role_surface_project_member.py明确登记该入口为未发布历史菜单，要求交付或显式拒绝。返回仍有workspace.home默认路由、91项能力但0个导航动作；平台release meta为ACTIVE_RELEASE_SNAPSHOT_NOT_FOUND。结论：身份已识别，空导航与当前受限暴露声明相符；管理层标准业务面仍未完成用户可用性验收，不能误报为“身份识别失败”，也不能擅自扩大菜单/组。未将缺少release snapshot单独推定为根因。

输入/结果复用：首次本轮iteration通过（iteration-runtime-probe.log）；探针测试先4项后增加恶意/非法UID拒绝与去重排序共6项通过（runtime-probe-unit-diagnostic.log）。后续仅增加导航诊断字段、严格UID输入验证及逐用户flush进度输出，合法UID下授权/导航执行输入未变，保留demo-observation.json和demo-navigation.json；诊断原件demo-navigation-49.json。L2结果仅为工具反例测试；运行态结果均标observation，不注册为可复用runtime gate，因尚未建立权威环境readback依赖。没有重跑整个业务矩阵或冻结门禁。

本轮产物位于.runtime/system-permission-roles/：demo-observation.log/json、demo-navigation.log/json、demo-navigation-49.log/json，全部保留原件。AUTH-01仍verification_pending；主线、部署、用户验收均not_run。剩余：7类角色需现有受管隔离验收载体的见证，不可在Demo临时授组；HTTP/实际代表操作、动态/私有入口审查未闭环；AUTH01-F01岗位授组仍待分层修复。下一步先确认可复用隔离验收载体及已声明角色fixture范围，再补7类见证与操作反例；不能用生成导航成功代替产品收口。

## AUTH-01 事务回归执行前边界

Formal Product Layer=P4验收 / P1测试归属；Layer Target=smart_construction_core.tests；Module=smart_construction_core（只新增测试和注册，无产品实现变更）。标准不变量为岗位不授予权限、角色不改岗位、撤销最后角色来源后能力消失；因此在后端真实ORM测试，不在前端或脚本补产品语义。Blast Radius=7类缺证角色岗位分离 + 2条撤权反例；不修改行业角色默认值、数据库schema或公共intent，不需要模块升级。

复用local.dev.test/test.safe，local.dev.ready已通过。TARGET_DATABASE_ROLE=development；TARGET_TENANT_ID=synthetic-workflow-tests（既有BusinessTransactionCase事务夹具）；TARGET_ENVIRONMENT_ID=sc-local-dev；IS_PLATFORM_CONTROL_DATABASE=false；IS_INDUSTRY_CATALOG_DATABASE=false；IS_CUSTOMER_TENANT_DATABASE=false（非生产测试载体）；IS_ISOLATED_REHEARSAL_DATABASE=false；CUSTOMER_BUSINESS_DATA_ALLOWED=false（本次不导入）；FIXTURE_ALLOWED=true（显式事务测试）；EXACT_DATABASE_FILTER_CONFIRMED=^sc_dev_demo$；FILESTORE_IDENTITY_CONFIRMED=sc_local_dev_odoo_data/sc_dev_demo；DB卷=sc_local_dev_db_data。复用已有凭据与Make入口，不新建数据库、端口或卷。测试创建的公司、用户、岗位全部由BusinessTransactionCase/TransactionCase回滚；只在隔离测试进程运行，无Demo远端授组。

L0当前HEAD+dirty scope；L1 iteration/py_compile；L2仅system_permission_separation标签的9条ORM测试。L3升级跳过：无schema或产品运行改动。L4浏览器与L5冻结/发布跳过：已知权限缺陷未闭环，不运行后置大门禁。角色测试覆盖业务不变量，不替代远端7类用户HTTP旅程验收。

### 事务回归结果与 AUTH01-F02

L1 make ci.local.iteration通过，日志iteration-separation.log。L2 make verify.local.dev.system_permission.separation.orm执行9个测试（以odoo.tests.result为准，stats的11包含夹具统计，不能当用例数），7通过、2失败、0错误。7类角色岗位变更不改组集合，角色变更不改岗位，均通过；这是隔离事务中的不变量验证，不是远端缺证用户已交付。两条撤权反例均在真实ORM失败：客商管理员角色移除后contact_manager仍在；移除物资管理角色并保留物资经办角色后material_manager能力仍在。原始日志separation-orm.log。

新增AUTH01-F02（P1产品缺陷，收口阻断）：runtime_user_management.py的_inverse_assignable_user_groups与_sc_runtime_user_safe_vals分别保留user.groups_id - assignable，非可分配能力组即使来自已删除角色也被再次当作直接组写回。没有修改产品代码或弱化断言。

为区分缓存/权限效果/授权来源，仅新增并执行两个独立同层用例：make verify.local.dev.system_permission.revocation_diagnosis.orm；1通过、1失败、0错误。通过项证明两种不同授予历史（仅角色 vs 角色+显式能力）最终groups_id集合完全相同，不能逆推显式授权。失败项先由非sudo客商角色实际列黑名单再撤销，确认阳性对照；删除角色、invalidate及registry.clear_cache后再次action_sc_add_blacklist仍成功，未按预期拒绝（UserError not raised）。证明实际业务动作仍可执行，不只是组集合差异。日志revocation-diagnosis-orm.log。没有重跑未变的7项岗位测试或前轮导航；累计11个不同用例8通过3失败，批次仍failed/verification_pending。

执行后受管权威回读：make local.dev.system_permission.cleanup.readback通过。users/companies/jobs/action_targets计数全0，证明本次合成对象未残留；原始日志separation-cleanup-readback.log。该命令只读，不执行清理或删除；TransactionCase回滚是恢复机制。远端Demo授权与运行配置未改。

修复边界必须先解决来源信息丢失：
1. P0显式角色分配与技术/历史直接授权分别记录来源；P1声明20类行业角色绑定，不把单一呈现role_code当作全量授权。
2. 有效权限由全部有效角色闭包与独立明确授权来源重算；移除一个角色保留其他角色的重叠能力，移除最后来源才撤销能力。
3. 旧groups_id无法判断来源的部分进入历史例外/待确认状态，不自动删除、不伪装为已确认直接授权；不能宣称撤权完成而仍静默保留能力。
4. 两个旧权限字段、审批人员向导、signup/导入/技术写入口按既定用途接入同一来源服务；岗位只能维护任职事实。
5. 复用本次三个失败测试作为修复验收，另补直接技术授权保护、并发和旧会话撤权；先修拥有层，再恢复后置运行/发布验证。

下一最早步骤改为P0/P1授权来源载体与兼容投影的实施设计，明确历史未归因组的拒绝/提示契约，再实现F02。现有run维持一个结果索引，不另外开工作树或复制覆盖表。L3/L4/L5保持not_run：已知L2产品失败未修复，不进行升级、浏览器、冻结或发布。

## F02 实现前与升级边界

本轮Formal Product Layer=P0通用来源记录/P1行业角色消费；Layer Target=smart_core.res_users_group_authority与smart_construction_core.runtime_user_management。Module依赖smart_construction_core→smart_core已有，不新增依赖。标准机制与角色声明分离：P0不认识行业XMLID，P1选择assignable和internal组。前端不承担授权计算，未改public intent。Blast Radius=用户组create/write与反向组写、两个角色维护入口、token_version既有失效链；新增JSON字段需受管升级smart_core（17.0.1.1.18），旧行不回填猜测来源。

L1 iteration-authority-implementation.log及authority-model-guard.log通过，L2 assignment-unit.log为10项非零纯逻辑反例通过。旧3项ORM失败的拥有层输入已修改，进入修复后待验证状态；因新增字段，先完成必要L3 schema升级再运行受影响ORM，不能用缺字段错误充当产品回归。新代码影响本专题全部16项ORM，所以重跑此精确集合；没有重跑导航矩阵。

目标仍为受管本地sc-local-dev/sc_dev_demo，^sc_dev_demo$，数据库sc_local_dev_db_data与filestore sc_local_dev_odoo_data/sc_dev_demo，非生产开发载体；无远端Demo写入，不导入客户数据。make local.dev.snapshot提供升级前数据库/filestore恢复点，日志authority-preupgrade-snapshot.log；升级仅走make local.dev.upgrade MODULE=smart_core。新增来源字段可随代码回退停用，恢复数据库须显式走受管恢复入口，不能在共享环境自动覆盖后来写入。


### F02 候选实现与验证结果

候选身份仍为2eb4cae26b5a013cb2cebc5706df34047ea7847e + run.scope所列未提交改动，未冻结。P0新增受保护JSON来源快照，仅服务端记录提交的根组、实际闭包、修订和操作者；历史未知或漂移显式拒绝角色维护。P1两个入口按根组重算，保留其他角色和明确直接授权，不再把整个有效组集合当直接授权。反向组写使来源失效；客户端不能伪造来源字段。此载体是最小来源快照，不是完整版本化角色产品或完整审计历史。

升级前snapshot目录artifacts/local-dev/snapshots/20261019T145836Z，数据库与filestore哈希逐项核验通过。第一次升级因未声明schema需求在写入前被guard拒绝；补齐真实schema授权参数后make local.dev.upgrade MODULE=smart_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_core成功，既有demo authority检查通过。该结果只证明字段升级与基线检查，升级过程中不涉及schema的实现细化由后续ORM验证，不复跑升级。恢复点仅供受管恢复，不自动覆盖共享数据。

L2真实ORM：system_permission_separation 16项全部通过，原三项失败转绿，含移除最后角色能力消失、保留其他角色、明确直接授权保留、未知历史拒绝、反向写失效、来源字段防伪、token_version增长及清缓存后实际黑名单动作拒绝。既有runtime_user_management/user_module_product_closure 35项全部通过。用例数取odoo.tests.result，不把夹具统计计为用例。原件separation-orm-authority-v1.log、authority-user-management-compat.log。

末次纯函数边界修复仅增加commands非list/tuple时GroupAuthorityGap，防止None/False等触发未捕获TypeError；assignment-unit-final.log中10项测试通过，新增非法值作为子用例。确定性影响集合为纯函数非法顶层输入用例；已执行51项ORM的list/tuple输入路径逐分支保持不变，保留原始结果，不重跑整批。此说明不产生可复用runtime receipt：尚未登记运行环境readback依赖。model_declaration guard的声明输入不受该修复影响。

执行后local.dev.system_permission.cleanup.readback通过，users/companies/jobs/action_targets全部为0，原件authority-cleanup-readback.log。测试事务回滚完成，无远端Demo授权写入。此前远端导航观察属于旧运行基线，不能代替本候选行为证明。

F02原撤权缺陷已有候选修复与局部行为证据；系统权限收口仍verification_pending。AUTH01-F01岗位/审批向导授组、历史来源对账入口、并发及HTTP旧会话撤权、7类远端角色业务旅程、动态私有写路径和独立审查仍未闭环。L4浏览器全矩阵、L5冻结/发布不执行：这些前置缺口未收口。本地开发数据库schema升级完成；主线集成、版本部署、用户验收均未执行。下一最早步骤为F01所属P1审批岗位授组路径的反例和修复，不把本轮51项测试称为整个权限体系验收完成。

最终make ci.local.iteration通过（iteration-authority-final.log，L1_only），git diff --check通过；纯逻辑10项、ORM16+35项均为非零结果。随后仅同步结果索引/本记录，不改变代码与测试输入。


## F01 审批岗位授组收口边界

Formal Product Layer=P1；Layer Target=approval_scope模型与原生视图；Module=smart_construction_core。Standard vs User-Specific=行业标准审批执行组投影；Why Here=旧岗位入口在该模块直接sudo授组；Why Not Elsewhere=P0不应认识审批岗位，前端不补权限判断，P4不清洗历史授权。Blast Radius=scope.user_ids写入、旧新增向导、新旧动作、授权人员只读展示；不改变审批policy执行组映射或既有组成员。旧方法保留为明确拒绝兼容桩，统一提示到用户系统角色维护；不新增第二份岗位事实。

L0沿用当前HEAD+run.scope dirty；L1语法、模型声明、iteration；L2新增精确F01 ORM集合，先失败反例再修复，旧F02实现未变不全批重跑。原生视图声明需要P1升级（无数据库列新增），升级后检查实际get_view及字段元数据；L4全浏览器矩阵/L5冻结暂不运行，其他已知系统级缺口未闭合。

环境复用development / synthetic-workflow-tests / sc-local-dev / sc_dev_demo / ^sc_dev_demo$，db卷sc_local_dev_db_data，filestore sc_local_dev_odoo_data/sc_dev_demo；显式BusinessTransactionCase合成夹具回滚，无客户导入、远端授组或新凭据环境。升级前走local.dev.snapshot保留恢复点；只读回读扩展精确夹具名称确认无残留。


F01原始ORM结果approval-scope-before.log：5项中4失败0错误，分别为直接user_ids写入、旧向导为现有用户授组、旧向导建账号、打开旧向导；角色维护的正向投影通过。修复后approval-scope-after.log五项全通过，非sudo业务配置管理员执行。新增测试通过assertRaises+savepoint验证明确拒绝及权限不变，不修改已有用户组事实。无新持久化字段，P1版本17.0.0.172仅用于模型元数据/原生XML升级。

L1 approval-scope-iteration.log通过，approval-scope-model-guard.log中6项守卫测试通过且重复声明为0。随后仅删除停用向导的姓名/登录/密码输入、追加一个实际get_view测试；产品模型未变，保留五项已执行结果，只补实际视图断言。宿主缺少lxml的XML语法诊断失败，改用标准库ElementTree验证通过；Odoo运行测试沿用镜像内lxml，不新安装依赖。snapshot路径artifacts/local-dev/snapshots/20261019T150746Z，manifest.txt两份归档SHA256逐项核验通过。升级仅运行make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core；结果待后续权威回读。

静态写入候选输入有实际变化：F02增加P0来源写钩子，F01删除审批授组语句。旧160项清单失效，仅保留baseline原件write-candidates-before-authority-fixes.json；刷新既有离线扫描入口以反映当前候选，不扩展运行态矩阵。


### F01 本地候选验证结论

受管P1升级成功（approval-scope-upgrade.log），demo authority回读通过。随后仅执行新增test_runtime_view_declares_readonly_without_grant_actions：1项通过0失败0错误，耗时2.46s（approval-scope-runtime-view.log）。真实非sudo维护者fields_get返回user_ids.readonly=true，实际get_view中人员只读，旧打开/执行按钮不存在，旧向导不显示密码字段。与前述5项行为测试共同覆盖声明、原生视图消费、模型实际拒绝和系统角色投影；没有据此冒充前端浏览器验收。

最后local.dev.system_permission.cleanup.readback通过：两类测试公司的精确名称、全部注册测试登录、岗位及动作对象计数均0（approval-scope-cleanup.log）。事务回滚恢复完成。新旧测试用例之外的远端授权未操作。本地升级是开发环境改动，不是部署/发布。

更新写入候选清单158项（write-candidates.json），原始160项保存在write-candidates-before-authority-fixes.json。工具14项测试通过（write-candidates-authority-fixes.log）。计数下降不等于动态调用全部审完；新增P0钩子与移除F01写入均属于当前扫描输入。最终git diff --check通过。

F01已从未修复阻断移至本地候选验证通过；F02前轮局部结果保留原始证据，不升级为本次运行态可复用receipt。系统权限批次仍verification_pending：历史未知来源的对账确认入口、并发与HTTP旧会话撤权、7类角色实际业务旅程和独立复核尚未完成。主线集成、版本部署、用户验收均not_run。下一步优先历史授权来源对账，避免现存账号只能被拒绝而无法受控完成维护；不得以直接猜测groups_id历史替代确认。


## 历史授权来源确认入口边界

Formal Product Layer=P0；Layer Target=smart_core原生授权来源确认向导/审计；Module=smart_core。标准通用机制，不认识行业角色XMLID；P1仅以已有行业角色做集成反例。Why Here=确认原生授权根来源属于平台权限机制；Why Not Elsewhere=不能由前端猜测根组，也不以P4脚本长期写来源。Blast Radius=新增管理员操作入口、TransientModel与审计模型、当前来源快照；确认不写groups_id，不授予/撤销能力。历史不可恢复，界面明确这是管理员从现在起确认来源，不能把它写成历史事实。

仅base.group_system且原生目标write ACL/record rule通过者可确认；业务配置管理员不继承此权限。必须显式选择根组、填写依据，根闭包与当前有效组精确相等。预览保存服务端快照，提交锁用户并比较组/定义/来源/公司状态，漂移拒绝；同预览不能重复使用。审计保存操作者、确认依据、确认前状态、根与有效组，公开create/write/unlink不允许。P0声明原生向导、只读列表和用户入口，不修改前端或公共intent。

L0继续2eb4cae26b5a013cb2cebc5706df34047ea7847e+dirty；L1语法/模型守卫/iteration；L2真实非sudo/越权/漂移/闭包反例；新模型需L3 smart_core升级后运行ORM，再验证实际视图。环境复用sc-local-dev/sc_dev_demo，^sc_dev_demo$，sc_local_dev_db_data与sc_local_dev_odoo_data/sc_dev_demo，synthetic-workflow-tests事务夹具，无远端或客户数据写入。L4/L5保留未完成，仍有HTTP/并发/最终复核缺口。首个resume因check指向local.dev.test而非verify目标失败；仅补正式verify.local.dev.system_permission.approval_scope.orm并改结果索引后resume通过，旧实际测试证据未伪造为新回执。

新增3项同入口安全反例：审批者在打开后失去系统管理员权限、组定义变化、目标停用；本轮精确集合14项。首轮新模型schema尚不存在，所以未用缺表执行伪造红灯；先完成必需schema升级，再运行真实测试。迭代/模型声明守卫已通过（reconcile-iteration.log/reconcile-model-guard.log），snapshot为artifacts/local-dev/snapshots/20261019T151411Z，数据库/附件哈希均与manifest.txt一致。


来源确认首次14项ORM全通过（reconcile-orm.log，3.23s），随后只增测管理员原生用户入口/审计表单消费1项并通过（reconcile-entry-view.log，2.31s），共15项。当前用户原生表单中入口仅系统管理员可见，业务配置管理员实际get_view不返回按钮；审计表单与字段均只读，历史动作绑定目标用户域。没有重跑未变的F01/F02矩阵或把新增覆盖伪称全部浏览器验收。

新增模型分类为租户库内认证/授权运行元数据：wizard按原生TransientModel创建者隔离并额外校验系统管理员+目标用户write ACL/record rule；确认审计仅系统管理员可读，公开create/write/unlink拒绝，无客户业务正文、跨租户关系或另建公司业务授权事实。snapshot保存target user_id，在目标删除导致关系为空后仍有原始数值身份；这项无schema的快照补充发生在升级完成后，15项ORM已使用最终代码，升级只作新模型与视图落库证明。

因新增来源确认公开动作与服务端审计写点，前轮158项静态候选清单需要刷新；原件另存write-candidates-before-reconciliation.json。这是已有扫描输入实际变化，不触发全运行矩阵。首次无残留回读已通过六类计数0；追加入口测试后再次回读同一精确夹具集合。


来源确认收尾：本地smart_core 17.0.1.1.19升级和demo authority回读通过（reconcile-upgrade.log）；最终无残留回读六类全0（reconcile-final-cleanup.log）。静态写入清单刷新仍为158项，工具14项测试通过（write-candidates-reconciliation.log），不将静态候选计数当动态私有入口完整证明。目标用户确认审计只在合成事务生成并回滚，没有真实账号批量确认。

该机制局部验收已通过；批次整体verification_pending，主线/版本部署/用户验收not_run。未运行真实多事务并发、HTTP旧会话撤权和最终独立审查；7类角色业务旅程及真实历史依据仍未完成。下一最早步骤为HTTP旧凭证撤权的实际拒绝证据及受管并发反例。日常候选未冻结，未生成Quick或发布；本地schema升级不能表述为产品部署。

最终L1 make ci.local.iteration通过（reconcile-iteration-final.log），git diff --check通过。此后仅更新同一结果索引与本记录；15项实际ORM结果、升级和回读证据保持原件引用，不伪造runtime复用回执。


## HTTP 撤权验证边界

Formal Product Layer=P4验证/P1合成行业见证；Layer Target=smart_construction_core.tests.TestSystemPermissionHttp；Module=smart_construction_core（本轮先只新增测试，无产品逻辑或schema变更）。复用BusinessTransactionCase+HttpCase事务和现有local.dev.test；禁止沿用历史测试中的独立cursor commit及签名参数覆盖。目标development/synthetic-workflow-tests/sc-local-dev/sc_dev_demo，^sc_dev_demo$，db/filestore卷沿用sc_local_dev_db_data/sc_local_dev_odoo_data。只读取已有活跃namespace/alias与认证配置；缺失则环境前置失败，不建立新环境或凭据权威。

L0当前HEAD+run.scope dirty；L1语法与iteration；L2/L3两个HttpCase反例，JWT先真实密码登录并认证请求成功，再撤角色验证旧token 401，重新登录认证成功；原生session先实际黑名单操作成功，撤角色后旧会话操作拒绝且权威对象保持未列黑。不将纯token_version增长作为HTTP撤权通过。无schema，跳过升级；L4全矩阵/L5冻结仍不执行。真实并发需要另核验事务隔离工具能力，不能用串行漂移测试冒充多事务结果。

HTTP首跑失败归类environment_prerequisite：setUpClass发现sc_dev_demo无现存active namespace+alias，0 tests/1 error（http-revocation.log），不能算两项失败或通过。将仅JWT需要的namespace前置移到登录方法，独立原生session反例不依赖该路由声明，允许只执行其精确用例；JWT暂不重复相同失败。没有更改产品鉴权。


原生会话独立用例通过（http-native-session.log，1项，实际HTTP先列黑/解除，再撤角色后拒绝且仍未列黑）。只读受管回读http-prerequisite-readback.log：namespace_count=0/active_alias_count=0，entry_secret/route_version/JWT安全长度全部已有配置；未输出任何密钥。Odoo真实Registry.cursor在test_cr存在时返回共享TestCursor，commit只释放savepoint不提交物理事务。因此更正早先仅据源码commit判断“持久提交风险”的推断：不能据此断言旧测试实际落库，也不能把其线程执行当真实多事务证据。

P4最小恢复：抽取既有smart_core.tests.TestIntentSmoke的namespace夹具函数，保持原suite-entry与namespace ID生成/数据库绑定语义，供本测试复用；不复用原测试的固定密钥覆盖。只在HttpCase事务内安装既有测试路由，重用既有sc_dev_demo/入口密钥/route version/JWT签名权威，测试结束应回读namespace_count=0。无新增库、卷、端口、profile或凭据权威。影响集合=新增JWT用例+原smoke中一条默认密码登录用例（验证提取前后兼容）；已通过原生session输入不变，不重跑。真实本地持久命名空间仍未注册，不能以此报告本地入口部署完成。

JWT恢复后真实登录和system.init阳性请求已200，但撤权阶段遭HttpCase后台GET共享测试游标竞争，ProgrammingError:no results to fetch（http-jwt-revocation.log，1项error）。归类validation_tool：test transaction的主线程ORM写缺少Registry.test_lock，与后台请求争用同一游标；不是认证/授权结果。仅给主线程撤权ORM段加既有test_lock串行保护，不改鉴权逻辑或断言，然后重跑该1项。


JWT精确重跑已通过（http-jwt-revocation-locked.log，1项，15.13s）：真实密码登录200，system.init阳性200，角色撤销后原token的同入口401/AUTH_REQUIRED，重新密码登录200，新token同入口200。测试锁仅保护主线程ORM与共享测试游标，不替代真实请求鉴权。由于_revoke测试辅助段也被原生session用例调用，补跑该1项而不是继承旧工具输入证据；同时补原TestIntentSmoke.test_anon_login_intent_default_contract_mode验证夹具提取兼容。旧测试原有配置写仍在测试事务内；补跑前采集配置摘要，结束后回读摘要一致与namespace/alias无残留，以证明恢复，不输出凭据。

并发能力结论：当前HttpCase/Registry.cursor共享同一TestCursor，不能据线程数声称独立事务。来源确认成功会产生不可公开删除的持久审计；真正的跨事务提交竞争需要已有受管、可整体恢复的隔离验收承载，不能在持久Demo库私自提交再SQL删审计。当前只读确认了限制，未创建新库或改变隔离策略，真实并发仍not_run。


### HTTP 撤权候选结论

原生会话重跑+旧smoke登录兼容2项全通过（http-native-and-fixture-compat.log）；结合独立JWT通过项，本轮3个不同有效用例全部通过，不计前置失败0tests，不重复累计原生会话的两次运行。未修改产品鉴权逻辑，只补真实请求反例、复用测试namespace夹具和修正测试并发游标保护。

HTTP配置恢复：http-config-before-smoke.log与http-config-after-smoke.log的结构化回读整体相等，配置聚合摘要相等（不输出密钥），namespace_count/suite_alias_count均0，签名/entry/version前置仍有效。无残留回读http-final-cleanup.log六类全0；另补旧smoke固定登录smart_core_tester纳入同一精确谓词，最终回读引用http-all-fixture-cleanup.log。此次补谓词不改变测试或产品输入。

最终make ci.local.iteration通过（http-iteration-final.log），diff检查通过。两条本地真实HTTP撤权链已验证：旧JWT认证拒绝、新JWT可用，旧原生session业务动作拒绝。不同于远端完整角色操作验收，不据此标记所有20类角色交付。真实并发、动态私有写路径审查、7类缺证角色业务操作和最终独立复核仍未闭合。整体verification_pending；主线、版本部署、用户验收均not_run。


## 会计角色日记账操作精确集合

Formal Product Layer=P1权限标准的验证（P4执行入口）；Layer Target=smart_construction_core/tests；Module=smart_construction_core；Standard vs User-Specific=行业角色映射验证。Why Here=SC声明映射原生account能力，实际ORM行为必须在行业角色身份下验证；Why Not Elsewhere=不在前端推导，不向P0加入会计语义。Blast Radius=仅新增测试和受管入口/精确夹具清理，产品代码不变。

本轮影响推导：新增测试文件→新增accounting_read/accounting_user/accounting_manager三个日记账配置边界key；已有HTTP/岗位/确认测试输入不变，不重跑。L0=2eb4cae26b5a013cb2cebc5706df34047ea7847e + run.scope dirty。L1=ci.local.iteration；L2=新增三项真实ORM读写/拒绝；L3=精确事务清理回读。无schema变更不升级；L4/L5因已知总体缺口不运行。复用sc-local-dev/sc_dev_demo、synthetic-workflow-tests、^sc_dev_demo$及原有卷，事务回滚，不确认真实账号来源。日记账配置不等于凭证记账/审批全流程。

本轮三项实际ORM通过：accounting_read/accounting_user真实read成功、create/write均AccessError且权威对象不变；accounting_manager真实create/write成功，撤角色后write被拒绝且保留撤权前值。日志accounting-orm.log为3 tests/0 failed/0 errors，1.99s；统计器5含setup等，不报作5项用例。L1 accounting-iteration.log通过；git diff --check通过。清理回读accounting-cleanup.log七类全0，未改真实账号。既有HTTP与来源确认输入不变，未重跑。

本轮关闭的是会计日记账配置子集，不是三类会计角色全流程，也未填补远端7类角色真实活跃见证空缺。后续精确集合为general_user/business_admin/settlement_manager实际操作及会计经办凭证办理；真实多事务、动态入口完整性及独立复核仍待完成。批次verification_pending；主线集成、版本部署、用户验收not_run。回滚本轮仅移除新增测试import/文件、make入口和清理扩展，无产品代码或schema变更。


## 字典与结算角色精确操作集合
Formal Product Layer=P1权限标准验证/P4执行入口；Layer Target=smart_construction_core.tests；Module=smart_construction_core；Standard vs User-Specific=行业标准角色。Why Here=角色到原生ACL/业务动作的映射属于行业声明；Why Not Elsewhere=不在前端或P0添加行业语义。Blast Radius=新增测试、make入口、精确夹具清理；无产品代码/schema变更。
新增输入仅test_system_permission_business.py，派生key为general_user字典只读、business_admin字典维护/撤权、settlement_manager结算办理/合同禁止修改/撤权；不重跑已通过会计和HTTP集合。L0=2eb4cae26b5a013cb2cebc5706df34047ea7847e+run.scope dirty；L1 iteration→L2三项ORM→L3清理回读；无schema跳过升级，已知总体缺口阻断L4/L5。复用local.dev/sc-local-dev/sc_dev_demo、^sc_dev_demo$、synthetic-workflow-tests及已登记卷，所有合成记录事务回滚。

字典/结算三项通过（business-orm.log，3 tests/0 failed/0 errors，3.80s）。继续同批补accounting_user真实凭证办理：受影响输入仅accounting测试新增方法，复用原setUpClass和三项已通过方法，不重跑原日记账配置子集。新增精确key=accounting_user平衡凭证创建/过账、accounting_read拒绝凭证创建、撤经办角色后拒绝创建；一个端到端测试包含三个独立身份断言。仍为P1测试/P4执行、同一事务回滚，未更改产品声明。

会计凭证新增1项通过（accounting-entry-orm.log，1 test/0 failed/0 errors，2.86s）：非sudo经办创建平衡凭证并action_post，权威回读posted且balance合计0；只读角色真实read成功/create拒绝；撤经办角色后create拒绝，记录计数仍1。原三项日记账方法及setUpClass均未变，保留原件，不冒充重新执行或可复用runtime receipt。

本轮合计新增4项实际用例通过，两次对应L1通过，最终diff检查通过。business-entry-cleanup.log精确15类夹具残留全0（包含凭证/明细/科目/结算/合同/字典）。产品代码无新增改动，未部署、未合并、未确认真实用户权限来源。七类缺见证角色现在具有本地代表性操作样本；这不消除远端真实见证空缺，不代表完整业务旅程或批次验收完成。批次verification_pending；主线/部署/用户验收not_run。后续优先处理动态入口审计、受管真实多事务、历史依据及统一产品复核，不重复已通过集合。


## F03 令牌版本写入权威
Formal Product Layer=P0；Layer Target=smart_core res.users认证版本与logout；Module=smart_core；Standard vs User-Specific=通用认证机制。Why Here=令牌失效是平台安全事实；Why Not Elsewhere=不由P1角色或前端控制。Blast Radius=用户安全字段写入、令牌版本及logout；先复现context跳过/客户端直接版本写入，再只修服务端权威。沿用P1合成事务见证和受管local.dev。
L0=2eb4cae26b5a013cb2cebc5706df34047ea7847e+run.scope dirty。新增精确key=context不能禁用撤权epoch、客户端不能伪造epoch、私有撤销操作递增；L1 iteration→L2三项→L3旧JWT与logout真实HTTP。不把新行锁视作真实多事务通过。无schema变化无需升级；完整冻结/发布仍阻断。受影响文件res_users.py/login.py→HTTP认证撤销及相关用户写入集；其他业务旅程不机械重跑。

F03两项真实反例复现（epoch-before-orm.log，2 failed/0 errors/2 tests），归类P0产品缺陷。修复：write拒绝客户端token_version、忽略旧skip上下文；私有_sc_bump_token_epoch在目标行锁下读取并递增，logout改用该私有方法。无字段/schema更改，测试进程加载代码，不宣称常驻服务已更新。
影响推导追加：res.users.write变化→原16项角色写入+新增3项、runtime_user_management/user_module_product_closure原35项均受影响，合计54项定向用户写入回归；HTTP认证/撤销依赖变化→原2项+新增恶意context及logout2项，精确4项。其他岗位/字典/结算页面不扩成全矩阵。L1 epoch-after-iteration通过；新增logout HTTP也验证旧JWT拒绝，不只依赖epoch增长。

F03收尾：epoch-user-orm.log为54 tests/0 failed/0 errors（20.40s）；epoch-http.log为4 tests/0 failed/0 errors（33.94s），含context攻击、logout、普通JWT撤权/重登和原生session实际动作拒绝。原两项红灯证据保留，不覆盖。HTTP配置before/after解析对象完全一致，epoch-cleanup.log精确15类残留均0；git diff --check通过。
HTTP契约生成仍出现权限及fields_view_get相关错误日志；本轮认证正向/拒绝断言全部通过，日志保留，不称完整契约启动链通过。本轮只关闭F03本地候选缺陷，未部署常驻运行时、未合并、未确认真实账号。其他历史测试为原候选观察，不因本轮源码变化伪造新runtime receipt。后续优先检查原生反向组写和reified字段的epoch/来源失效、真实多事务与独立复核；批次verification_pending。回滚F03需成对回滚res_users与logout调用及对应新增测试；无数据/schema迁移。


## 反向组与原生组字段失效审计
Formal Product Layer=P0；Layer Target=smart_core用户/组授权失效；Module=smart_core；Standard vs User-Specific=平台机制。Why Here=反向成员与继承定义同样改变认证权限事实；Why Not Elsewhere=无需P1角色或前端特殊处理。Blast Radius=原生res.groups users/implied_ids及res.users reified组字段；无schema变动。L0沿用2eb4cae26b5a013cb2cebc5706df34047ea7847e+run.scope dirty。新增四个key：反向加/移成员、继承定义变化、in_group字段撤销。L1 iteration→L2精确四项→必要修复→受影响回归/HTTP。复用sc-local-dev/sc_dev_demo、synthetic-workflow-tests及原卷，仅事务合成组/用户，不真实授撤权。其他已通过集合不重跑；L4/L5仍受整体缺口阻断。

F04：四条反例全部只在epoch断言失败（reverse-before-orm.log，4 failed/0 errors/4 tests），成员与来源失效断言已通过，归类P0遗漏。修复res.users.write将in_group_/sel_groups_也视作安全写；res.groups users/implied_ids修改对旧/新成员并集调用私有epoch递增。无新增权限或新schema。受影响精确回归：23项separation+35项用户管理+15项来源确认，共73项；新增3项HTTP分别验证反向移组/原生字段/定义变更后旧JWT 401。原F03四项HTTP的产品路径未改：groups_id普通写及logout仍走相同分支，因此不重跑原四项；本轮不声称新并发证明。

F03/F04新增私有epoch写点和logout调用使旧静态写入口索引过时，故刷新已有verify.system.permission_role.write_candidates；原件保存在write-candidates-before-epoch-fixes.json。该输入变化只触发静态清单更新，不代表动态完整性或全矩阵验收，也不重跑产品页面。

F04本轮收尾：73项ORM通过（reverse-user-orm.log，24.75s），新增3项HTTP通过（reverse-http.log，31.01s），均真实登录后先system.init成功，再组写入后旧JWT收到401/AUTH_REQUIRED。静态入口工具14项通过，候选158；原四项红灯及旧清单均保留。reverse-config-before/after解析对象完全一致；reverse-cleanup.log精确16类残留全0；diff检查通过。无schema/模块升级，无部署。
本地write入口缺口已关闭；create/unlink生命周期、sel_groups原生选择字段的直接见证、真正多事务竞争仍未完成。完整启动链不以认证测试外推；历史资料、独立审查和统一批次验收仍待完成。批次verification_pending，主线/版本部署/用户验收not_run。回滚本轮只撤P0两处失效传播改动及新增测试/文档，无业务数据迁移。


## 组生命周期与原生选择字段
Formal Product Layer=P0；Layer Target=smart_core res.groups生命周期失效；Module=smart_core；Standard vs User-Specific=通用机制。Why Here=组创建附成员/删除同样改变认证事实；Why Not Elsewhere=不在行业角色或前端补偿。Blast Radius=仅原生组create/unlink及已有sel_groups路径，新增合成类别/组事务回滚。L0=2eb4cae26b5a013cb2cebc5706df34047ea7847e+run.scope dirty。复用sc-local-dev/sc_dev_demo、synthetic-workflow-tests、原有卷，不改真实账户。
新增精确key：create带users、unlink已有成员、实际fields_get声明的sel_groups从高到低。L1 iteration→L2三项，先复现再修复；正向变更及来源失效/epoch断言，另校验无关用户不失效。无schema升级；L4/L5仍因全局缺口跳过。

F05首次3项执行结果2通过/1失败，失败仅删除组epoch不递增（lifecycle-before-orm.log），create带users已走已有write失效路径，实际sel_groups声明降级也通过，故不修改这些产品路径。修复仅res.groups.unlink：原成员加锁→原生删除成功→使现存原成员来源未确认并递增epoch。删除拒绝不得产生状态写。新增批量删除及普通用户拒绝删除两项。精确受影响集合=删除原反例+新增批量/拒绝共3项ORM、删除后旧JWT1项HTTP；原create/selection测试输入执行路径未改变，保留原件结果，不重跑全73项。无schema/数据库生命周期改动，不升级。

删除三个精确ORM用例全部通过（lifecycle-after-orm.log，3 tests/0 failed/0 errors）；原create/selection2项通过继续引用lifecycle-before-orm.log，不把原失败命令整体改成通过。新增公开unlink覆盖使写入口工具输入变化，刷新同一清单并将旧件保存write-candidates-before-group-unlink.json；无全产品矩阵重跑。

F05收尾：创建/选择2项原通过证据保留，删除3项精确ORM通过（3.31s），真实HTTP删除后旧JWT拒绝1项通过（13.40s）。工具14项及静态门禁通过，清单候选仍158；不据此声称动态/私有入口完整。HTTP配置before/after解析完全一致，lifecycle-cleanup.log精确17类残留0，diff检查通过。当前已检查的原生组create/write/unlink和选择字段路径形成声明/实际操作/认证后果证据，真实多事务、历史授权资料、独立复核及整体业务验收仍未闭合。批次verification_pending；主线/部署/用户验收not_run。无schema变更或真实用户授权变更。回滚F05仅新增unlink override及测试/文档，无数据迁移。下一步统一当前候选复核，避免继续机械重跑已通过集合。


## 当前候选统一复核（未冻结，非独立审查）
Formal Product Layer=P4证据归并/P0传输边界验证；Layer Target=当前run及smart_construction_core.tests；Module=smart_core机制见证。Why Here=收敛真实调用边界和现有证据；Why Not Elsewhere=不改前端/角色业务语义。L0=2eb4cae26b5a013cb2cebc5706df34047ea7847e+run.scope dirty。修正文档首段仍称AUTH-01只读的过期状态，完整permission_role/revision/assignment及角色发布UI保持未来设计，不冒充当前实现。

对158候选作源代码定向分流：77 XML声明；81 Python候选包含73 dictionary/8 assignment。approval_policy.py:_sync_tier_server_action_groups写的是ir.actions.server可调用组，并非res.users授权；验收fixture返回users数组也不是反向组写。auth_signup默认配置只在新账号创建路径应用，既有账号密码重置跳过；tenant_payload_operator的准备/授予/撤销经既有身份校验并调用原生用户ORM，tenant_payload_import_batch非客户空间登记亦走groups_id写；smart_core post_init是安装时平台管理员载体，不能当普通角色委派入口。上述为阅读结论，不是新增运行验收。P0/P1生产代码的res_groups_users_rel检索仅发现既有只读SELECT，直接SQL增删在uncached_membership测试中模拟越权威外修改，不作为受管写入通道。

动态execute_button先验证声明的actionContract来源与状态再getattr，裸方法名没有调用权威；这不代表所有可能的运行配置已审计。新增精确HTTP key=原生RPC禁止调用4个私有来源/令牌方法，验证拒绝后状态与epoch不变。无产品代码更改；L1 iteration→L3该HTTP1项（真实传输断言，非纯工具）→配置/清理回读。其余已有F01–F05结果保留原件。尚未完成全候选独立审查/浏览器复核、真正并发或真实历史资料核对。

本轮私有RPC用例仅走原生session，不创建namespace、不写JWT/entry配置，因此不重跑配置快照；前轮配置恢复原件仍在。清理回读覆盖既有精确合成身份。本轮已核验run.results中所有log/source_log文件存在，不生成新的冻结指纹或把文件存在当行为通过。

统一证据复核收尾：新增真实私有RPC 1项/4子情形通过（consolidation-private-rpc.log，3.04s）；四方法均返回odoo.exceptions.AccessError且每次权威回读source/epoch不变。L1及diff通过，consolidation-cleanup.log精确17类0。run.results原件引用无缺失；归并结论只在原run记录，未建立第二份结果表。
该次复核由实施者完成，仅为源码边界与证据准备，不伪装独立审查或完整产品验收。前端浏览器/完整业务旅程、真实多事务、历史授权依据与独立审查仍是明确未完成项。已向所有者询问历史依据位置，尚未收到，不从有效组反推来源。目标文档已纠正当前阶段；后续完整role注册/发布模型仍属未实施设计。批次verification_pending；主线/部署/用户验收not_run。


## 真正多事务探针准备（未授权启动新档案）
Formal Product Layer=P4；Layer Target=已有local.contract-lifecycle受管入口扩展；Module=验证工具，P0机制不变。Why Here=真实独立事务需独立cursor与已提交合成身份；Why Not Elsewhere=不向产品添加审计删除后门，不在persistent demo提交/擦除不可变历史。Blast Radius=仅已登记sc-contract-lifecycle-v1/sc_contract_lifecycle/^sc_contract_lifecycle$；沿用sc_contract_lifecycle_db_data/sc_contract_lifecycle_redis_data/sc_contract_lifecycle_odoo_data及固定8079/18090。当前与canonical工作树的lifecycle env均不存在，仅发现canonical contract-snapshot env存在，不能跨专题挪用。
当前阶段仅准备探针与单元边界测试，不prepare/rebuild/up/写库。运行前要求明确确认、精确库/filter、非TestCursor及源文件hash匹配；实例初始化和最终discard均经现有受管入口。场景为同一向导双确认、同一目标不同向导双确认、双epoch并发递增，真实提交胜者后新事务权威回读；失败记录保留，禁止SQL删审计。合成身份/审计留在隔离档案，最终仅经受管discard回收；这是新环境权威待所有者确认，不能由继续开发推定。L0当前HEAD+dirty；L1 iteration/语法→L2安全前置纯测试；真实L3暂not_run。

准备完成：concurrency-probe-iteration.log静态通过；concurrency-probe-unit.log 7项安全边界测试通过；py_compile及diff检查通过。未执行任何环境prepare/rebuild/up或数据库写入，三个真实并发场景仍not_run。源码绑定4个P0机制文件hash；线程在屏障前读取同一快照并记录不同backend_pid/transaction_id，防止串行调用伪装并发；遇序列化冲突按明确测试场景在新事务验证败者拒绝或重试一次epoch增量。

待授权的具体动作：1) make local.contract-lifecycle.prepare（缺env但存在旧卷时现有工具拒绝，立即停止，不传override）；2) 确认新建档案后，CONFIRM_LOCAL_CONTRACT_LIFECYCLE_REBUILD=REBUILD_ISOLATED_CONTRACT_LIFECYCLE make local.contract-lifecycle.rebuild LOCAL_CONTRACT_LIFECYCLE_MODULES=smart_core；3) SC_CONFIRM_PERMISSION_CONCURRENCY=RUN_ISOLATED_PERMISSION_CONCURRENCY make local.contract-lifecycle.system_permission.concurrency，保存输出及三项权威回读；4) 归档后仅对本次新建档案执行CONFIRM_LOCAL_CONTRACT_LIFECYCLE_DISCARD=DISCARD_ISOLATED_CONTRACT_LIFECYCLE make local.contract-lifecycle.discard并读取卷清理确认。若发现既有数据/环境所有权冲突则停，不覆盖。身份为隔离技术验证库，不是客户或demo权威；仅P0合成认证用户/组/来源审计，不装P1或客户数据。

授权依据：AGENTS.md第67行明确New environment or credential authority still requires separately authorized P4 work；工作区规则第52行也排除新环境/凭据权威。此处需要的是激活缺失隔离档案的权限，不是重复申请已授权代码改动。仍不执行冻结、发布或部署。

所有者已明确同意上一轮具体启用/并发测试/回收计划。受管prepare成功创建本工作树mode600档案（concurrency-profile-prepare.log），旧卷守卫未发现冲突；开始按批准命令初始化smart_core技术隔离库。此次不涉及sc_dev_demo、sc_demo或客户数据，真实并发结果尚未产生。沿用原验收候选HEAD+dirty、源码hash门禁、持久审计保留与受管discard回收约束。


### 已授权的真实并发结果
本轮三个真实独立事务场景全部首次通过（concurrency-runtime-first.log / concurrency-runtime.json）：same_review与distinct_reviews均一方commit、另一方SerializationFailure；败者在新事务重试明确拒绝，每个目标恰好一条不可变审计。epoch_increment一方冲突后在新事务执行一次预定重试，权威回读0→2，无丢失更新。每组均有两个不同backend_pid与transaction_id，屏障前已建立快照；不是共享TestCursor或串行模拟。4个P0源文件SHA256与当前候选完全相同。
原始日志、结构化回读及准备/初始化日志已保存并逐文件读取校验hash（concurrency-evidence-hashes.json）。随后按授权执行受管discard，concurrency-profile-discard.log确认三个固定卷全部删除，服务/网络回收；未SQL擦除审计，未触及持久demo或客户库。现有工具保留mode600 ignored env用于后续受管管理，不属于产品证据或新部署。清理日志也加入hash清单并复核。
本轮没有修改产品实现或探针输入，因此复用上一轮L1与7项前置测试；不重跑历史矩阵。真实并发阻断的三个具体场景已关闭，不外推为无限负载压力保证；独立复核、统一产品验收、真实历史依据和远端业务见证仍未闭合。批次verification_pending；主线/版本部署/用户验收not_run。


## F06 已确认向导的服务端只读
Formal Product Layer=P0；Layer Target=smart_core sc.group.authority.reconcile.write；Module=smart_core；Standard vs User-Specific=通用授权确认机制。Why Here=后端声明confirmed后根组/依据readonly，但公开write目前可改，与审计显示脱节；Why Not Elsewhere=不能靠UI readonly代替服务端权威。Blast Radius=仅完成状态向导写入拒绝，未完成向导编辑继续支持；无schema或角色权限变动。L0当前2eb4cae26b5a013cb2cebc5706df34047ea7847e+run.scope dirty。L1 iteration→L2新增反例→修复→精确确认模型回归及HTTP确认/审计旅程。沿用local.dev合成事务，无新环境。

F06真实反例1项内产生3个失败断言（依据可改/根组可改/最终根组已变），0 errors（review-readonly-before.log），不报作3项测试。修复write先核验权限、锁向导行、重读confirmed，完成后拒绝编辑；未完成仍原生write。action_confirm仍通过super更新完成标记。精确影响为确认模型16项ORM与新增原生RPC完整确认/审计/拒绝后改1项；未改角色目录、登录或epoch代码。并发原3场景的action_confirm与epoch执行函数未改变，新增write锁影响前置向导填写；旧结果保留原hash，不冒称当前全文件hash相同，需对新增编辑与确认竞争单独验证后再最终冻结。

F06模型16项全通过；并发探针新增editor_only精确模式，原baseline3项不重跑。模式守卫/身份前置8项通过，L1通过。新增场景confirm_first与edit_first通过屏障保证两事务快照重叠，先行操作持锁后才允许后行操作尝试；检查后行冲突后新事务重试的拒绝/成功及向导与审计依据一致。沿用所有者已授权的同一隔离档案、身份、工具与prepare/rebuild/执行/discard范围，仅新增受影响场景，属于已授权修复后的必要定向验证；不请求重复授权、不创建新凭据体系。

F06收尾：16项确认ORM、1项真实native HTTP旅程、8项P4安全前置全部通过。editor_only两个真实并发场景通过：confirm_first后行编辑SerializationFailure后新事务重试AccessError；edit_first后行确认冲突后重试成功，审计和向导依据均为修改后的值；各自唯一审计、独立backend_pid/transaction_id。原baseline3项未重跑，原源码hash证据保留，本轮JSON记录当前4个产品文件hash。
证据editor-concurrency-runtime.log/json已读取校验并保存hash；受管discard确认三个固定卷删除，清理日志亦纳入editor-concurrency-evidence-hashes.json。local.dev精确17类残留0（review-readonly-cleanup.log）。本轮未改真实账号、未部署常驻产品、未升级schema；静态/语法/diff通过。F06局部验收闭合，整体verification_pending，最终独立审查/统一产品验收/真实历史依据仍未完成。


## 2026-10-20 开发阶段独立审计与证据索引修正
Formal Product Layer=P4；Layer Target=run依赖及交付证据；Module=工程记录；Standard vs User-Specific=通用验证治理；Why Here=补齐实际HTTP确认旅程依赖并核对原件；Why Not Elsewhere=不改P0/P1语义，不以前端补权限。Blast Radius=run、goal及本记录。L0保持2eb4cae26b5a013cb2cebc5706df34047ea7847e+既有dirty，未冻结。
补齐http_revocation遗漏的确认模型、注册、manifest、ACL及原生视图依赖；旧运行仍仅为执行观察，不能形成可复用runtime receipt。74个原件引用均存在，两份并发归档清单共9个文件SHA256相符；文件/摘要正确不代表新增行为验证。goal同步F06，run/goal均标记verification_pending。产品与测试执行输入未改，精确新增运行集合为空；跳过L2/L3重跑及L4矩阵，L5冻结仍受已登记缺口阻断。按project-governance-codex的B线只读独立审计要求启动开发阶段源码审计；不冒充冻结最终审查。

独立审计指向既有P1用户维护过滤的context与关系命令边界。新增精确反例集合=client_context_cannot_bypass_native_group_authority、company_relation_commands_cannot_write_company_records；Formal Product Layer=P1，Layer Target=runtime_user_management，Module=smart_construction_core；Why Here=行业业务配置管理员的委派写入；Why Not Elsewhere=不得由P0编码行业角色或前端补安全过滤。仅新增测试，尚不改产品。L1→L2两个反例；无schema变更，无升级/浏览器/冻结。复用sc-local-dev/sc_dev_demo/^sc_dev_demo$及固定filestore，BusinessTransactionCase synthetic-workflow-tests注册公司的事务回滚；不写真实公司/账号、不提交合成数据。

F07反例执行2项/3失败断言/0errors（delegation-before-orm.log）：省略/伪造上下文均导致特权组写入，公司关系UPDATE可改合成公司。P1产品缺陷，非环境问题；首先失败的subTest已污染同测试后续状态，修正为每个subTest包裹savepoint，避免后续断言误归因。修复业务配置非系统管理员始终经安全过滤，仅env.su且内部标记才绕过递归；公司命令复用P0严格成员操作解析，拒绝0/1/2及非法结构。新增创建上下文绕过与公司CRUD拒绝两项。精确回归集合=separation类及既有runtime_user_management兼容类；不改P0源码，不重跑并发、业务矩阵或模块升级。

F07首轮修复58项ORM通过（delegation-after-orm.log）；独立复审指出自身tz/lang原生偏好被过滤。新增1项正向反例真实失败（delegation-preference-before.log），归P1兼容回归。最终仅对非su、自身用户、全部字段属于原生SELF_WRITEABLE_FIELDS的请求保留super路径；敏感组写仍进入过滤，混合字段也不获此例外。下一精确集合=5项新增安全/偏好ORM及1项原生HTTP综合旅程；原58项中非自身偏好路径未变，不重跑全类。HTTP仅native cookie，不改namespace或JWT配置。新增创建身份改为auth01_context_0/1，清理读回精确列表补齐；已完成L1后仅测试身份字符串变化，语法检查通过，不据此重跑原全静态。

F07收尾：首轮58项定向ORM通过；修复自助偏好后仅重验5项精确安全/兼容用例，全通过（delegation-final-orm.log）；真实native HTTP 1项通过（delegation-final-http.log），无context及伪造context不增权，公司UPDATE明确ValidationError，自己时区保存成功。58与5有重叠，不合计为63个独立用例。最终L1通过，diff检查通过。独立审计者只读复审认可self-only原生字段例外边界；该结论仅开发阶段定向复审，未冒充最终冻结审查。原始2项3失败及偏好1项失败日志保留。
精确17类测试残留全0（delegation-cleanup.log），含新增auth01_context_0/1及被拒绝公司命令标识；未改真实账号或提交夹具。产品代码不涉及schema/模块data，无升级；测试入口新进程加载当前源码，不代表常驻环境已部署。P0并发源码未改，不重建已回收档案。run/goal状态verification_pending；历史依据、远端角色见证、导航与统一产品验收、最终独立审查仍未闭合；主线集成/版本发布/用户验收均未完成。回滚F07仅P1过滤/成员命令解析与自助例外及配套测试/证据，无数据迁移。


## F08 委派创建默认上下文审计
Formal Product Layer=P1；Layer Target=runtime_user_management.create；Module=smart_construction_core；Standard vs User-Specific=行业管理员委派机制；Why Here=safe_vals过滤后仍原样透传context至sudo；Why Not Elsewhere=P0不编码行业管理员语义，前端不得承担安全校验。Blast Radius=仅用户维护委派创建/上下文边界。当前HEAD 2eb4cae26b5a013cb2cebc5706df34047ea7847e+既有dirty。先新增default_partner_id合成反例，验证不能绑定并修改合成特权用户的联系人；L1→L2精确1项，未改产品逻辑。沿用sc-local-dev/sc_dev_demo/^sc_dev_demo$及固定filestore，BusinessTransactionCase测试公司/事务回滚，不动真实账号、不提交数据，无schema升级。L4/L5因整体缺口未关闭而不运行。

F08前置2项真实ORM均失败、0errors（default-before-orm.log）：default_partner_id关联了合成特权用户联系人，default_sc_project_member_assignment_ids形成了隐式项目授权。P1输入校验缺陷，非环境故障。独立B线只读审计提出相同根因。修复仅在委派sudo边界剔除default_*，保留已非sudo校验的safe_vals、既有语言/公司上下文及sc_default_initial_password兼容；create/write都使用同一私有上下文过滤，避免write触发的嵌套create注入。精确回归集合=separation与runtime_user_management两类，因为委派创建及写入共用入口改变；不重跑P0并发和全角色业务矩阵。清理名单加入三个精确新账号及测试项目。无schema/data改动，不需升级。

F08收尾：61项定向ORM全部通过（default-after-orm.log），含两条注入反例及既有创建/初始密码/公司/岗位/项目维护兼容；新增native HTTP 1项通过（default-after-http.log），同时提交伪造内部标记、默认联系人及默认项目授权后，仍成功创建独立联系人且无夹带项目授权，原联系人名称不变。L1、语法及diff通过。HTTP新增与清理范围调整仅影响自身执行输入，已语法检查并实际执行，不重跑原全静态。
独立只读复审认可两条路径封闭及参数兼容，仅覆盖F08开发阶段修复，不构成冻结最终审查。default-before-orm.log的2失败原件保留。精确清理增加项目授权回读，共18类残留全0（default-cleanup.log）；P0/隔离档案未改，不重建已回收环境、不跑旧并发矩阵。批次verification_pending；主线集成/部署/用户验收仍未完成。回滚仅撤销P1上下文过滤私有方法及两处委派调用和配套测试，无数据迁移。历史授权依据、远端角色/高管导航与统一产品验收缺口仍按原run保留。


## F09 委派操作与原生记录规则
Formal Product Layer=P1；Layer Target=runtime_user_management create/write；Module=smart_construction_core；Standard vs User-Specific=行业管理员委派权限机制；Why Here=公司与非特权过滤不能覆盖原生ACL/record rule；Why Not Elsewhere=不新增P0平行权限引擎、不让前端验证替代服务端。Blast Radius=仅委派用户创建/修改的原生权限拒绝。L0=2eb4cae26b5a013cb2cebc5706df34047ea7847e+dirty，未冻结。新增2项反例：事务内全局规则禁止精确合成用户write/create；L1→L2定向验证后再判定修复。沿用sc-local-dev/sc_dev_demo/^sc_dev_demo$、固定filestore、BusinessTransactionCase synthetic-workflow-tests公司，规则与数据事务回滚，无真实账号/部署/新环境。无schema变化，无升级；已知整体缺口仍阻断L4/L5。

F09首次2项反例均失败（rule-before-orm.log，2 failed/0 errors），原生规则拒绝被委派sudo绕过。修复P1：write在任何委派写入前检查原环境ACL/record rule；create先查ACL，在内部savepoint创建后恢复原环境检查create规则，拒绝连同关联副作用回滚。测试新增规则允许的正向目标；创建拒绝测试不使用调用方savepoint，验证产品内部回滚后用户与联系人均未遗留。独立B线确认归属与修复顺序；精确回归为separation及runtime_user_management两类，因共用委派入口改变，不重跑P0并发或全业务矩阵。

F09收尾：63项定向ORM通过（rule-after-orm.log），覆盖拒绝create/write、允许目标正向操作及既有兼容；新增native HTTP 1项通过（rule-after-http.log），两类请求均返回AccessError，目标原名不变、拒绝创建的用户与联系人不存在。L1、语法、diff通过。L1之后新增HTTP/清理工具的影响只限新增用例与回读，均语法检查及实际执行，无产品源码再改。独立只读复审认可原调用环境规则校验和内部保存点边界，仅开发阶段定向结论，不替代冻结交付审查。原2项失败证据保留。
精确清理含新增临时ir.rule、账号与联系人，共19类残留全0（rule-cleanup.log）。无模块schema/data变更，无升级或真实账号写入；产品与测试均在现有受管local.dev加载，不代表部署。批次仍verification_pending，主线集成/发布/用户验收未完成。回滚F09仅P1原生检查及创建保存点和配套测试/记录，无数据迁移。下一步仍按原run缺口推进统一验收、历史依据与远端见证，不机械重跑已通过矩阵。


## F10 人员关联字段读取边界
Formal Product Layer=P1；Layer Target=runtime_user_management safe_vals及既有formal_user_management inverse；Module=smart_construction_core；Standard vs User-Specific=行业人员委派维护。Why Here=部门/岗位关系经sudo落入员工，不得绕过原生读取规则；Why Not Elsewhere=不由前端或P0编码行业人员字段。Blast Radius=委派人员部门/岗位关联。L0保持2eb4cae26b5a013cb2cebc5706df34047ea7847e+dirty。新增2项反例/4子场景，覆盖跨公司及同公司read规则拒绝；L1→L2，先观察再改产品。沿用sc-local-dev/sc_dev_demo/^sc_dev_demo$及固定filestore，BusinessTransactionCase synthetic-workflow-tests公司/临时规则，全部事务回滚。无schema变化、新环境或真实账号写入，L4/L5仍因全局缺口不运行。

首次2项结果2失败断言+2errors（personnel-before-orm.log）。隐藏部门/岗位的read规则均被绕过，属P1产品缺陷；跨公司两个errors来自Odoo assertRaises不接受异常tuple（TypeError），产品调用尚未发生，属测试工具缺陷。改用共同UserError基类并仅重跑跨公司这一独立用例，产品输入未变；不能把工具错误报为产品跨公司失效。

修正断言后跨公司1项/2子场景均实际失败（personnel-company-before-orm.log，2failed/0errors）；原生HR未保护该sudo inverse路径。修复safe_vals在sudo前验证所选关联ID/存在性、原调用者read ACL/rule、关联公司与最终用户公司一致（无公司关联保持既有HR共享语义），保留False清空。新增同公司关联/清空正向与create隐藏关联拒绝两项；拒绝后检查无员工/用户副作用。精确回归separation及runtime_user_management两类，共用委派入口输入改变；P0未改，不重跑并发或全业务矩阵。

F10收尾：67项定向ORM通过（personnel-after-orm.log），含跨公司/隐藏关联拒绝、create无副作用、合法同公司关联和清空；新增native HTTP 1项通过（personnel-after-http.log），隐藏岗位返回AccessError且无员工，允许岗位实际保存到员工。独立只读复审认可原caller read检查和最终公司一致性，仅开发阶段限定结论，不冒充冻结审查。L1、语法、diff通过；L1之后的新增HTTP及清理输入均语法检查且实际执行。首次2failed+2工具errors及修正工具后的跨公司2failed原件均保留。
精确清理新增部门/员工范围，规则计数键改为authority_rules，共21类残留0（personnel-cleanup.log）。无schema/data改动、模块升级、新档案或真实用户写入，常驻部署状态不变。回滚仅P1 safe_vals关联校验及配套测试/证据，无数据迁移。批次verification_pending；主线集成/版本部署/用户验收仍未完成。历史依据、远端角色/高管导航及统一产品验收仍需按原run推进。


## F11 公开建立人员档案动作边界
Formal Product Layer=P1；Layer Target=formal_user_management.action_sc_ensure_employee_profile；Module=smart_construction_core；Standard vs User-Specific=行业人员维护公开动作；Why Here=该动作独立于write，可达sudo employee创建；Why Not Elsewhere=复用既有后端权限机制，不改前端/P0。Blast Radius=公开建立档案动作及调用边界。HEAD 2eb4cae26b5a013cb2cebc5706df34047ea7847e+dirty未冻结。新增3项反例：原生用户write规则、特权目标、default_job_id注入。L1→L2精确3项；现有sc-local-dev/sc_dev_demo/^sc_dev_demo$与固定filestore、synthetic-workflow-tests事务回滚，无真实账号或新环境。无schema变化；L4/L5仍因全局缺口跳过。

F11前置3项结果2failed/0errors：write规则与特权目标两条绕过成立；default_job_id探针通过，未据静态猜测改helper默认上下文。产品修改仅公共action：原环境write ACL/rule、整批人员维护/公司检查；非sudo非系统管理员复用可维护目标过滤，先整批预检后调用原helper。保留原生系统管理员及内部inverse路径。新增批量混合目标零副作用及两次调用唯一员工。通过离线检索公开action调用点，精确受影响集合=5项新测试+TestUserModuleProductClosure既有公开动作正向/普通用户拒绝2项，共7项；helper/inverse未改，其余67项及P0并发不重跑。formal_user_management路径及既有调用测试已补入run scope/依赖。

F11收尾：7项精确ORM通过（profile-after-orm.log），覆盖新增拒绝/整批预检/幂等及既有公开动作正反例；新增native HTTP 1项通过（profile-after-http.log）：拒绝目标返回AccessError无员工，允许目标连续两次调用只产生1条员工。独立只读定向复审通过，仅开发阶段结论；原3项2失败原件保留，默认岗位探针原已通过，不冒充修复。L1、语法、diff通过；后续HTTP与清理工具增量已实际执行。
精确清理范围补齐既有UserModuleProductClosure夹具的账号/公司/项目/部门/岗位及新规则，21类残留全0（profile-cleanup.log）。无schema/data变更，无模块升级、真实用户修改或部署。回滚F11仅公开action预检与配套测试/证据，不影响私有helper/inverse，无数据迁移。批次仍verification_pending；主线集成/发布/用户验收未完成。沿用原run剩余历史依据、远端角色/高管导航、统一产品验收与最终冻结审查缺口。


## 连续收口：区分代码集成与产品交付
用户要求直接迭代直到收口，不再每修一处停止。限定开发独立复核P0来源/确认/epoch及P1全部本专题公开写入未确认新阻断；actor UID未错记，intent/RPC失败有事务回滚依据，不把内部调用方吞异常的假设报为线上部分提交漏洞。原生assignment重新归属与委派编辑不同是现存产品边界问题，未有全入口禁止依据，不擅自扩改。
最新受管demo只读回读source_revision仍654a77bda9ddad1c98c29e055df2d19c1cac2497，20角色/13见证/7缺失不变（demo-observation-current.log/json）。该诊断用于确定剩余集合，不是重跑失败验收；无变化不再跑导航矩阵，也未创建账号/权限。历史资料问题仍待用户答复。
依据AGENTS Completion Status Boundaries及普通PR最新车道，本次可独立集成结果限定为F01-F11已验证的通用安全修复：历史来源未知拒绝变更是正确产品行为，不要求推断历史来源后才合入防护；远端缺7见证及未发布高管菜单是原有完整产品交付缺口。旧blockers原样保留于run.product_acceptance_gaps，不删除、不改判通过；完整role/revision/assignment产品化仍未实施。代码集成检查与产品交付检查分开，整体goal继续verification_pending。
本次统一安全批次复核引用原始F01-F11定向结果、确认native view/真实HTTP及5个真实多事务场景（原3+编辑2），不将日志存在或源码字面当行为证明。覆盖范围包括岗位不授予角色、来源未知拒绝/显式确认、撤权认证失效、公开动作/委派原生规则和关联边界；浏览器呈现及全角色业务旅程未完成，不冒称整体批次产品验收完成。F11仅公共action修改，已通过7项精确回归；其余已测输入路径未改，不重跑全矩阵。
P4文档/生成证据准备阶段：执行ci.delivery.freeze.prepare并审阅生成差异，再按结果推进clean候选、冻结独立审查及受保护PR车道；不越过失败门禁。使用release-note-and-doc-update技能同步本记录。回滚按P1委派/岗位入口→P0认证/来源机制的依赖逆序撤销代码，新增来源/审计字段保留数据，不删除真实历史记录。升级只用于模块schema载体，非全量重建。

冻结准备首次失败于verify.agent.ledger.unit（18 tests/1failed），明确7条台账错误。自有goal扁平格式1条；其余6条基线错误：PRODUCT-MENU扁平格式、两个DEMO goal仍active与completed runs矛盾（组织目标被两run引用）及两个已完成run残留活动索引。三个相关基线goal在修复前与HEAD字节一致。P4最小前置修复仅规范两个goal外层结构、同步两个已完成目标状态、移除精确两个completed索引项；不改其他任务实现/部署状态。依据组织run已记录PR689精确merge f67126ce832c658a19320b11bd182a92f9c14103及完成说明，标签记录明确所有者确认和交接。原约束/后续部署范围原文保留。此为当前候选冻结必须消费的台账前置，纳入同run.scope，不另建环境/工作树。先验证18项台账单测，再依据已改变的台账输入重试冻结准备；不无条件重试原失败。

18项台账单测通过；改变台账输入后ci.delivery.freeze.prepare通过（freeze-prepare-after-ledger.log）。生成差异已审阅：测试资产1567→1572导致排序编号后移，扫描文件4900→4920，模块版本按本候选更新；无新增产品语义。纳入run.scope后保存P0/P1/P4责任提交。
远端精确检查发现：GitHub权威main=86c03b7a3a502028e5ad656f7c8cb34fd3bedff4，当前任务基线在其上包含0f896044a/2eb4cae26两条菜单配置前置提交，查询对应branch全部状态PR返回空。Gitee main=41c7a9dd4c6a854dc344ca1d7f4033186f66c35a，是任务基线的祖先且落后124提交；不能将“main前进”初步判断当作事实，已纠正。不得把本专题责任提交连同无关历史悄然发布。该前置集成依赖是具体发布阻断，最终Quick/推送保持pending；仍可保存本地责任提交和准备精确候选审查，不能宣称主线集成。post-commit证据仅写既有.runtime区域，tracked run引用integration-finalization.json。

### 主线集成续跑（2026-10-20）

所有者要求集成主线；以 GitHub main `86c03b7a3a502028e5ad656f7c8cb34fd3bedff4` 为目标，显式纳入两条菜单前置提交并完成独立补审。首轮 clean Quick 在 `774220255` 因 Makefile 274 行超过 272 行失败。P4 修复仅合并末尾 include 行，顺序及目标定义不变，不放宽门禁。重验静态入口及权限工具单元测试；P0/P1源与原运行时测试输入不变，沿用原证据。最终身份、Quick和远端状态继续写原 run 指向的 post_commit_receipt；尚未合并、部署或全产品验收。

第二轮Quick在G1工具矩阵摘要处失败；菜单前置遗漏的摘要经生成器更新，保留原基线SHA。同层定向诊断发现四个工具测试虽有Make模块名入口但未被注册器识别，改为同一unittest的文件路径调用，不加豁免。产品代码与运行时输入不变，原验证继续承接；本轮仅重验受影响工具、声明与基线绑定。

同层检查继续补齐六组新增Odoo测试的按需入口登记及快照，未声称常驻CI覆盖；G1 15项、演进绑定27项、注册器18项、四组工具38项和菜单8项通过，模型声明/事实来源及菜单元数据6项通过。所有失败原日志保留在同一运行证据目录。
