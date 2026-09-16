# UC2 主线集成关闭与 U-C3 结构分组启动

## 当前批次：正式表单低代码合成与发布回滚闭环

开发取证起点为`f848108b71a937c1a4e7d406bac3bac76664c889`加本批工作区修改；以下浏览器/定向测试是开发态记录。最终冻结身份、Quick receipt与独立复核以`artifacts/lowcode-form-loop/`内最终结果为准。主样板 action546/view1428，未命中反例 action547/view1431。旧路径台账44；三份U-C3行业XML保留且未导入运行库。核心整改已由用户复核通过；预览安全与设计器组件两项收口完成定向自验，最终集成门禁待收齐｜本批未集成｜未部署｜89入口用户验收未完成。

### 本轮评审整改（同批记录）

评审复现成立：旧编译器边改树边检查，父组隐藏和子字段必填的补丁顺序能改变安全结果。现先合成全部胜出属性，再完成分组/顺序，最后遍历实际有效树及祖先约束；两种顺序均拒绝。保留未被配置加重的原生条件限制，等价布尔表示归一；分组内部遵循最终排序而非点击选择顺序。

普通设计器接入现有“表单设置”入口，针对原生权威表单生成稳定节点补丁，支持已有字段标签、显隐、同区域排序和同区域新增分组。只编辑配置源，预览/发布/业务页仍调用同一后端编译器。保存绑定打开时的配置定义；恢复旧草稿不能静默重置基线；回滚后重新读取基线。三份U-C3 XML继续隔离，自定义字段不在本轮实现和验收范围。

入口运行诊断发现：已授权的“表单设置”在最终契约中缺少 entitlement 判定，通用渲染器按门禁隐藏。修复在服务端已有配置管理员/ACL检查之后输出授权结论，并完整投影到V2；不放松前端权限门禁。新增非管理员不发出该入口的反例。此前浏览器工具找不到入口记为失败；该阶段未发生配置或业务写入。随后发现新建页把此本地动作归成object并要求已保存记录，按明确ui.local_mode/ui.mode修复通用动作分类，未改变其他业务动作授权。

当前定向结果：编译器51项、设计器helper7项及渲染连续分段5项、严格typecheck、header动作测试通过；恢复旧草稿/打开后并发修改、正式表单发布回滚、正式配置入口授权各1个事务方法通过。组合反例覆盖父组隐藏＋子字段必填的两种顺序、跨配置覆盖、分组后祖先限制及合法无关补丁顺序；同名配置分组在不同父节点具有不同导航锚点。

实际UI补验还修复两处消费问题：解码器必须保留无名分组的空名称，不能变成null导致稳定目标失效；渲染器必须按最终树交错呈现字段与分组，同时保留相邻字段列布局、按钮折叠菜单及既有可见性过滤。初次分段遗漏可见性过滤使隐藏备注仍显示，浏览器明确失败，补回后闭环通过。一次空白登录页登记为环境故障，经local.dev.frontend.watch恢复；未重置demo。

正式设计器完整UI旅程已通过（开发态自验，非用户验收）：从入库正式入口“表单设置”编辑标签、排序、分组和非必填显隐，保存→预览→发布→业务页刷新→回滚恢复。发布内容、最终契约、浏览器行为分别passed；预览与正式有效结构/字段策略/动作一致；正文分组与导航同源，来源页签点击入库明细能正确返回。实际坐标检查配置分组在库位之前，仓库与库位仍在同一行。出库action547契约及实际页面未串配置。回滚后同一设计器再次编辑、保存和预览通过；新草稿未发布，运行基线已恢复，业务指纹未变，浏览器错误0。

本次为桌面代表样板；没有扩大到全移动矩阵、业务保存或自定义字段。设计器支持同一区域排序和一个新分组，不宣称支持任意跨父节点拖拽。既有工具A→B→A证据仅承接未变部分，不替代本次普通UI路径。


当前复核现场（2026-09-16）：使用已有受管账号`sc_test_admin`登录5174后打开[设计器草稿122](http://127.0.0.1:5174/f/sc.material.inbound/new?menu_id=494&action_id=546&activity_page_id=ap_mu3lbscw_fshych&config_mode=form_field_configuration&change_set_token=lfTCb1b2NtOTCgNqsoIQ10hUyTA97CJ9)，点击“验证并预览”可重新签发预览。当前[配置预览](http://127.0.0.1:5174/f/sc.material.inbound/new?action_id=546&view_id=1428&menu_id=494&preview_token=0tcPl-ZMUWsDpxS1oa9IfMEasBFgZK_bh7lNXQU8n_s&preview_role_key=system_admin)有效至2026-09-16 12:38:52 Asia/Shanghai；需要同一账号登录，链接不绕过鉴权。草稿未发布，默认业务页已恢复。预览到期只需重新签发，不重跑旅程。

### 第二轮产品收口：预览安全与设计器组件

用户已实测确认稳定节点分组、标签/排序、备注隐藏、跨页签导航，且重跑编译器51项通过；本轮不再重复这些矩阵或A→B→A。发布/回滚沿用既有真实UI证据。本轮只补预览安全、桌面和390px窄屏。

- P0 / frontend + smart_core：预览保留原有create/edit状态与字段契约，不以切换业务页面状态实现安全限制。页头常驻“未发布配置预览 · 不产生业务写入”，显示公司、角色、action/view作用域和返回原设计器草稿入口。保存/提交入口关闭，动作保留原适配身份但enabled=false，协作使用既有readonly和能力门禁。所有统一API请求附带限制上下文，统一intent分发及直接Base处理路径均在业务执行前拒绝写入；旧execute_button覆写run也不能跳过。跨域请求允许该限制header，不赋予任何新权限。
- P3 / BoundFormSettingsPanel：使用ScSelect、ScForm、ScFormField、ScInlineState；左右排列字段编辑与待发布摘要，窄屏改为单列。摘要逐项显示标签、顺序、分组、显隐，仍由同一组稳定节点补丁生成。未新增配置存储或前端结构解释器。
- P4 / 既有local.dev.form_lowcode.browser：增加PREVIEW_CLOSURE与PREVIEW_OBSERVE限定模式。使用草稿122，UI重新签发预览；不发布、不回滚、不保存业务数据。补验desktop/narrow、统一选择器、四类摘要、返回设计器及实际api.data.create拒绝（使用非法字段保险，不可能创建合法业务记录）；完整配置基线与入/出库业务指纹保持不变。

失败及恢复：权限纯测试的旧FakeEnv未接受context参数，先报26处错误；仅修正测试替身签名后22项通过，未修改权限规则。初版清空动作适配列表导致契约不能渲染，已改为保留身份、禁用动作。强制readonly页面状态的尝试已撤销。滚动截图发现独立sticky提示被既有页头遮挡，改为复用页头notice槽和高度计算，观察工具加入elementFromPoint遮挡断言。一次Vite空白页为环境故障，受管frontend.watch于12:56重启至pid1612515，未重置数据库。

定向证据（同一索引）：`preview-write-guard.log` 7项、`preview-router-test.log` 9项（含旧run覆盖拒绝）、`preview-operation-policy.log` 操作分类6项、`preview-permission-fixture-retest.log` 权限22项；`preview-summary-unit.log` 原7+5项及四类摘要断言；`preview-closure-typecheck.log`严格类型检查通过；`final-lint.log` 0 errors/36 warnings。`preview-closure-browser.log`及`browser/closure-report.json`记录桌面/窄屏、实际写拒绝、返回设计器passed及浏览器错误0；滚动与窄屏摘要补验passed（含elementFromPoint确认无遮挡），补图单列`preview-closure-observation.log`/`browser/closure-observation.json`，不冒充又跑一次业务旅程。

三份U-C3源码的原始文件、binary patch及SHA256已保存在工作树外`/home/lidefend/workspace/.codex-evidence/workspace-archives/20260916/uc3-pending/`，恢复源为`uc3-uncommitted.patch`，逐文件可读性/哈希已核对；三份改动已从本批工作区隔离，`git apply --check`确认补丁可重新应用；本批提交不包含它们。台账维持44，供应商退货、自定义字段、action777、结算demo金额问题及未覆盖业务写入继续独立登记。

### 实际失效层与修复

- P0 / smart_core：原生owner与合法配置误冲突；配置源优先级错误；原生容器缺稳定身份。后端针对稳定occurrence绑定解释一次node_patches，在原生树上执行标签、顺序、同容器分组、布局和显隐，校验只读/必填/字段权限，输出唯一有效树。保留原生及行业默认；旧名称猜测的结构覆盖在已迁移表单明确拒绝，未迁移表单不扩改。
- P0发布安全：校验配置管理员、公司及action/view/角色；stage及使用时由服务端认证来源；禁止直接ORM改写变更集状态/载荷，阻止跨公司/全局默认删除；锁定并比较完整定义后发布/回滚。预览限实际认证角色，不用字符串冒充角色权限。
- P0运行态复现：同一事务A→B，write_date不变时缓存返回A。缓存token改为相关配置定义hash、版本、状态和active集合；发布内容回读、最终契约核验、浏览器行为分别记录。最终契约必须包含实际应用的配置来源；readonly/required同步到最终字段描述符使用的载体。
- P0浏览器实际复现：未发布预览来源id=0被前端按正式记录id拒绝。契约和解码器增加明确的change_set_preview来源，只有该类来源允许0，不伪造发布记录ID。首次完整旅程通过后，截图发现配置分组使未归属该分组的notebook明细导航消失；通用导航保留这些明细，不重复加入已被显式分组承接的集合。
- P4：同批及续跑复用既有盘点，只核对受影响身份；按用户明确授权，既有受管环境内补齐验收工具无需逐点重复审批；禁止新环境/凭据及跳过硬门禁仍有效。复用local.dev工具、账号、数据及端口，增加限定表单闭环模式，写前保留基线，结束恢复并回读业务数据。修复健康检查对受限curl包装的不兼容。

归属：通用合成/安全属于P0，不写入行业业务规则；测试包装与审批去重属于P4，不承载产品语义。P1仅增加正式入口事务测试，不改变库存、金额、业务必填、审批或业务动作实现。影响范围为通用表单编排及配置生命周期，按L1→L2→限定运行旅程推进；无需schema升级，不执行sync_demo、不导入三份U-C3 XML、不重跑UC1/UC2矩阵、不跑Quick。

### 单一结果索引

原始日志均在 `artifacts/lowcode-form-loop/`，不复制日志或另建交付包。

| 层 | 受管入口／命令 | 结果与证据 |
|---|---|---|
| L0 | 当前分支/HEAD/dirty核对 | feature/uc3-native-structure-grouping；上述开发候选；保留UC2及历史工作树 |
| L1 | make ci.local.iteration | passed，16项策略测试；designer-iteration-final.log；包含最终渲染修复后的检查 |
| L1 | python3 addons/smart_core/tests/test_view_orchestrator.py | passed，51项，combinations-unit.log；最终树组合约束、优先级覆盖、分组顺序及原生条件限制 |
| L1 | test_backend_contract_boundaries.py / test_native_view_parser_surfaces.py / test_load_contract_response_cache.py | passed，11/34/5项；沿用本批原日志，未受后续生命周期修改影响 |
| L2 | make verify.frontend.typecheck.strict / verify.frontend.contract_v2_runtime_policy.unit | passed；designer-decoder-final.log；运行策略6、预览来源2、解码后无名节点绑定1 |
| L2 | verify.frontend.bound_form_configuration.unit / verify.frontend.contract_header_action.unit | passed，helper7项、连续渲染分段5项及既有动作链+新增未保存设计器入口1；designer-order-final.log、designer-header-final.log；最终严格类型检查designer-renderer-typecheck.log |
| L2 | local.dev.test 精确并发stage方法 / 正式表单闭环方法 / 配置入口授权方法 | passed，各1项；designer-concurrency-final.log、designer-final-contract.log、designer-entry-contract-final.log。旧草稿不能重基；非管理员不发入口 |
| L2 | make local.dev.test MODULE=smart_construction_core TEST_TAGS=/smart_construction_core:TestFormalFormLowcode | passed，2个事务场景；transaction-test.log；A/B/A、字段/分组/排序/隐藏、3项拒绝、action/view/角色/公司及维护权限隔离，业务记录未变 |
| L2 | make local.dev.test MODULE=smart_core TEST_TAGS=/smart_core:TestBusinessConfigChangeSet | 16项中12passed、4旧夹具error；修正夹具后仅补验4项passed；change-set-test.log、change-set-retest.log；覆盖完整定义漂移拒绝及受管写入保护 |
| L3 | make local.dev.restart / make local.dev.frontend.watch | 现有sc-local-dev/sc_dev_demo，8070/5174；运行候选代码，无模块升级；修复curl探针后前端ready |
| 限定浏览器 | make local.dev.form_lowcode.browser | 完整旅程passed；browser/report.json：默认→预览A→发布A→预览B→发布B→回滚A→恢复默认；预览/正式有效树、字段策略及动作相同，action547未变化，4项拒绝显式诊断，业务数据指纹未变。导航缺口已补受影响部分，待用户集中复核，不称批次验收完成 |
| L2补验 | verify.frontend.contract_v2_runtime_policy.unit / verify.frontend.native_section_navigation.unit | passed，预览来源2项及原运行策略6项；导航原28项及新增配置分组/独立notebook反例；frontend-preview-test.log、navigation-test.log |
| L2补验 | local.dev.test正式表单单旅程 / 回滚后重新发布单方法 | passed，各1个事务场景；form-retest.log、republish-test.log；其他未变通过项沿用 |
| 限定浏览器 | FORM_LOWCODE_DESIGNER=1 make local.dev.form_lowcode.browser | passed；designer-browser-final.log、browser/designer-report.json；普通设计器全闭环、同页回滚后再次编辑、出库页面隔离、发布基线恢复、业务指纹未变；designer-draft/preview/published/rollback/outside-scope.png为本次画面 |
| L5 | 生成预检/冻结/Quick/独立复核 | 生成预检passed（freeze-prepare.log）；冻结后Quick receipt及同HEAD独立复核写入既有未跟踪证据目录，不回写本文件制造新候选；未执行PR发布、部署或清理 |

权限/作用域反例使用事务内测试身份与公司并回滚；实时浏览器只用既有sc_test_admin和当前公司，不修改真实个人偏好。自定义字段模型扩展未改、未覆盖。未迁移表单的旧名称型设计器全面转换不在本轮范围；原生权威表单已接入普通设计器。仍分别记录配置保存、发布、最终契约、页面行为结果。

运行响应的SC_SOURCE_REVISION为unknown，未冒称冻结SHA；本轮以受管restart/current工作树挂载、HEAD+dirty及工具核对的compiler内容身份记录开发现场。最终完整身份留到冻结，不将当前现场作为最终交付证据。

5174为本批开发现场；5176保留的UC2前端仍在，但共享后端已切换本批代码，因此不宣称它保持UC2原候选身份。配置态导航补验passed：`FORM_LOWCODE_NAV_ONLY=1 make local.dev.form_lowcode.browser`，见`navigation-browser.log`及`browser/navigation-report.json`。保管配置、入库明细、协作记录同时存在；来源页签→明细章节点击激活原生明细页签，非必填备注隐藏；截图`configured-field.png`和`configured-detail-navigation.png`覆盖实际字段/分组/明细，实际滚动容器MAIN.router-host，scrollTop=620。`navigation-preview.png`为真实顶部。预览输入与完整旅程A相同；仅前端导航函数变化，后端合成/权限/发布/回滚/配置输入不变，因此复用A/B/A/default结果，不重复完整旅程。

现场：http://127.0.0.1:5174/f/sc.material.inbound/new?menu_id=494&action_id=546 。保留变更集94的测试预览（仅sc_test_admin，发布基线不变），有效至2026-09-16 11:55:14 Asia/Shanghai；精确链接在`browser/navigation-report.json.review.url`。过期后应经受管preview入口重新签发，不能绕过创建者/公司检查。浏览器恢复结果passed，原始完整旅程与导航补验均确认业务指纹未变。工具失败草稿已受管撤销，发布版本审计保留；仅此复核草稿保持ready。

该段为上轮工具闭环记录；本轮整改及普通设计器UI结果以上方索引为准。此前变更集94预览已过期，不作为当前可复核链接。未扩大自定义字段、跨角色冒充预览或全89入口验收；尚不冻结、不Quick、不清理。

## U-C3 低代码边界复核（2026-09-16，历史分析）

以下保留此前分析过程；当前实施及验证状态以上方结果索引为准。

用户要求全面分析低代码能力后，暂停扩大原生迁移。候选为 `f848108b71a937c1a4e7d406bac3bac76664c889` 加未提交的证照/制度原生视图与两份行业配置修改；这些修改尚未验收、未升级运行库。主线剩余和本地台账均保持44，不改写UC2既有证据结论。

本次为只读代码链路分析，未运行Quick、浏览器矩阵或数据库写入；不是运行态验收。核查产品/契约边界文档、配置工作台与表单设计器、配置选择/排序、结构冲突诊断、原生渲染编排、发布/版本/回滚及现有测试。主要发现：

- `form_structure_authority.diagnose_structure_ownership` 未按来源区分旧行业结构与合法租户配置：存在native owner时，action/view scoped结构声明会报冲突，全局结构会被标为旧结构抑制。合法低代码顺序/分组/布局有被拒绝或抑制的风险；不能将“无任何配置结构”作为迁移验收条件。
- `ViewOrchestrator._apply_form_spec` 在明确view_id时保护原生成员，并限制layout替换和字段排序；只放开冲突检查不足以恢复配置端与业务端一致。
- 变更集 `_verify_runtime_item` 对非菜单项只检查published状态与payload哈希，不解析最终页面契约。因此现有 `runtime_verified` 不能单独证明表单布局生效。
- 统一排序常量目前为generated=10、user_preference=15、industry=20、tenant_lowcode=40，与边界文档所列行业默认先于客户偏好的顺序不一致；修复前需定向证明实际覆盖及既有测试意图。
- 原生排序测试存在view_id=None场景；其通过不能证明正式action/view配合租户配置的能力。菜单、列表/搜索、审批、版本机制有独立载体，本次未发现足够证据宣称它们整体失效，也未重新证明其运行态通过。

修正后的收敛目标：原生视图提供默认结构，P2偏好及P3显式配置通过后端受控合成进入唯一有效结构；正文、导航和设计器消费同一解释结果。退役对象是重复的旧默认结构/镜像重组路径，不是低代码产品能力。保留配置作用域、版本审计、回滚、自定义字段及原生权限/必填/只读/动作约束；不能以字符串source单独替代写入授权。

下一步先在P0补“正式action/view + 已发布租户排序/分组/显隐配置”的定向反例，覆盖作用域隔离、配置预览/发布/回滚以及最终结构一致；据此最小修复后端合成机制，再继续P1的666/862。对UC1/UC2复用既有默认页面证据，仅补受影响的配置链路，不重跑整套浏览器矩阵。89入口产品验收与兼容消费者指标分别记录。

状态：**UC2 主线集成完成，不等同于产品交付完成。** PR #482 已 squash 合入 `main@e802f7239bf005482a352caa64eb9da0e78a085a`。入库、出库批次验收完成，保留既有未覆盖项；本轮未报告部署，版本发布不登记完成；89 个入口的整体用户交付验收仍未完成。主线剩余兼容消费者 **44**，本地已验证剩余 **44**。

台账将原 `publishedCount=46` 改为 `mainlineRemainingCount=44`（显示名“主线剩余”），不保留含混的发布数别名。仓库执行代码未引用旧字段；历史 UC1 审计字段与原始证据保持原义，不据此宣称部署。已核对原审查候选 `25cb3cd106ead9dd09b3f2b68ed152fbd413da0f` 与合入提交的 addons/frontend/scripts 内容一致，546/547 原生结构退役产物已合入，44 项原条目未增删。

## 候选与边界

- 基线：`main@28b7695dc9f1cebbbe9bd5d715e951c6dec8a4da`。
- 产品与取证候选：`f1dbaa9950263f735b0619a08b545f8f199f5982`；完整指纹 `f9780e4b60fb625cdaa8b73a8cdb7a5217dd1069a989b64d4c5721e7290304da`。
- 分支／唯一写入工作树：`feature/uc2-material-native-v1` / `sce-backend-odoo-material-handling-v1-uc2-material-native-v1`。两个无关历史工作树未操作。
- P0：原生 statusbar 在新建态保留节点身份但不显示状态，避免同一状态回落到正文；章节导航显露 notebook 目标、定位并同步高亮。
- P1：`smart_construction_core` 材料入库／出库原生视图与分类契约。
- P4：受管只读浏览器矩阵、退库路径解析、证据和台账。
- 业务边界：库存、计价、保存、审批、状态方法、ACL 与 record rule 均未修改；供应商退货不在本批。

## 实际入口与覆盖

| 范围 | 正式身份与原生来源 | 已覆盖 | 结果／未覆盖 |
|---|---|---|---|
| 入库 | menu 494 / action 546 / `material.inbound` / view 1428 | `S80-MIN-001` received 查看、空白新建；桌面 1440×960、移动 390×844 | 通过；无合法 draft，未做编辑 |
| 出库 | menu 495 / action 547 / `material.outbound` / view 1431 | `S80-MOUT-001` issued 查看、空白新建；桌面、移动 | 通过；无合法 draft，未做编辑 |
| 退库（批外调查） | 内部 XML 定义 action 548 / `material.return` / 共用 view 1431 | 正式菜单、角色路由、action 547 分类、供应商退货边界 | **不在正式 89 项基线；无正式可达用户路径，另立业务能力专题；未把直接 action URL 当成验收路径** |

没有为补齐查看或编辑态创建、保存或修改业务数据。最终 8 个材料组合及非材料反例捕获到的业务写请求为 0，运行前后业务指纹一致。

## 唯一结构与兼容退出

action 546 与 547 的实际契约均满足：

- `layoutPolicy=container_tree_authority`；
- `formStructureAuthority=native_authority`；
- `compatibilityDependencies=[]`；
- action 546 解析到 view 1428，action 547 解析到 view 1431；
- 入库旧基础章节、生成字段顺序、P1 业务事实排序和 action 产品化结构按精确 XMLID 停用；
- 出库旧生成结构与 action 产品化结构按精确 XMLID 停用；
- 分类模板只保留 required、readonly、visible 等字段语义，不再提供章节结构。

因此入库、出库两个技术消费者已从剩余数组移除；合入后主线剩余 `46→44`，本地剩余 44。退库不重复计数，供应商退货不纳入本批。

## 信息组织、导航与交互

- 入库现有记录由页头唯一承接“已入库”：状态区 1、状态标签 1、正文状态字段 0。新建页状态区 0、正文状态字段 0，由页面的新建／未修改元信息表达当前模式。
- 入库 `document_status`、`quantity_summary`、`tax_included_amount` 的可见实例均为 0；`total_qty` 与 `amount_total` 各 1。明细继续保留逐行数量、单价、金额与原生合计，未改计算规则。
- 入库正文页签为“入库明细／说明与附件／来源追溯”；出库为“材料明细／说明与附件／来源追溯”。章节导航与 notebook 来自同一原生树。
- 从“来源追溯”点击顶部明细章节后，目标由不可见 0 变为可见 1，正确激活明细页签并定位关系锚点；活动导航为 `aria-current=location`。
- 新建态明细保留原生添加能力；已入库、已出库记录的明细为只读。新建备注探针跨三个页签保持，未触发保存。
- 入库保留提交、确认入库、退回草稿、取消、带入验收明细；出库保留提交、确认出库、退回草稿、取消和调拨关联动作。按钮继续由原方法、状态和权限控制。
- P0 非材料反例为人员档案：章节目标可见且唯一高亮，证明通用修复未绑定材料语义。

## 退库路径调查（UC2 范围外）

退库不属于 action 546、547 的本批正式范围，且当前不能宣称可用，依据如下：

1. 正式 89 项产品导航基线不含退库菜单。
2. `menu_sc_material_return` 的父菜单停用，管理员菜单搜索无“退库”。
3. 角色 route authority 列表为空。
4. action 547 的正式业务分类不包含 `material.return`；模型虽有 return 类型定义，但没有把普通出库入口变成正式退库入口的权威路由。
5. action 548 的 XML 定义或直接 URL 不能替代用户可达路径。
6. action 554“材料退货”对应 `sc.material.supplier.return`，属于供应商退货，明确排除。

后续另立业务能力专题：以可追溯原出库记录为起点，先核实来源关联、可退数量、库存方向和权限，再确定正式入口。该专题不直接放开出库分类，不复活旧菜单。执行者未擅自新增菜单，退库调查结论不阻断 UC2 正式范围冻结。

## 结果索引

| 层 | 入口／命令 | 状态 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | passed | 16 tests；最终 P0/P1 变更的静态与架构入口通过 |
| L1/P4 | XML parse、`node --check`、`python3 -m unittest scripts.verify.test_frontend_material_domain_rollout` | passed | 5 tests；浏览器断言按唯一状态区域取证 |
| L2/P0 | `make verify.frontend.professional_workflow.unit` | passed | 10 模型例、5 Python guards |
| L2/P0 | `make verify.frontend.canonical_form_presenter.unit` | passed | 170 cases；新建 statusbar 保留归属且不显示业务状态 |
| L2/P1 | `TestUserFeedbackBusinessViews.test_material_inbound_form_uses_handling_identity_and_business_first_line_order` | passed | 1 个精确方法，非零；0 failed/error |
| L2/P1 | 出库原生契约与无正式退库角色路径的精确方法 | passed | 既有候选结果复用；相关产品输入未变 |
| L3 | `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make local.dev.upgrade MODULE=smart_construction_core` | passed | `sc-local-dev` / `sc_dev_demo`；demo authority passed；未执行 `sync_demo` |
| L4 | 最终材料矩阵与非材料反例 | passed | 8 个材料组合、1 个非材料反例、25 张截图、0 写请求、0 浏览器错误 |

中间候选曾因两类取证问题失败：一是把新建 statusbar 节点身份清空，导致“草稿”回落正文；二是 Playwright 把组合徽标当作单一文本节点，`exact` 定位不到实际存在的“已入库”。前者由 P0 通用归属修复，后者由 P4 按唯一业务状态区域逐行取证；失败未被改写为通过。

`local.dev.sync_demo` 未执行。既有“期望 280000、实际 0”的结算演示数据问题继续单列，未修改金额或演示事实。action 777 保持原未通过状态。

## 浏览器证据与现场

- 证据摘要：`tmp/uc2/material-batch-f1dbaa99/browser-batch-review/summary.json`。
- 截图：同目录 25 张，摘要记录逐文件 SHA-256。
- 身份：HEAD `f1dbaa9950263f735b0619a08b545f8f199f5982`，完整指纹 `f9780e4b60fb625cdaa8b73a8cdb7a5217dd1069a989b64d4c5721e7290304da`。
- 滚动事实：桌面表单顶部 `formTop=101`、标题 `headingTop=133`；移动 `formTop=135`、标题 `headingTop=155`；实际滚动所有权为 `.router-host`，顶部截图时 `scrollTop=0`。
- 受管现场：`http://127.0.0.1:5176`。提交本记录后的仅文档候选可承接上述浏览器证据，因为产品、脚本、数据库、账号和运行配置输入未变；运行服务仍须绑定最终完整 HEAD。

原始浏览器证据保持不变。既有外部归档位于 `/home/lidefend/workspace/.codex-evidence/workspace-archives/20260916/uc2-material-native/25cb3cd106ead9dd09b3f2b68ed152fbd413da0f/`，引用 `archive-receipt.json`、`archive-verification.json`、`merge-receipt.json`；33 个文件与25张图的可读/哈希验证结论复用。Quick receipt 绑定原冻结候选，独立复核与四项 required checks 已通过；这些不是新规划候选的验证结果。本轮不重跑、不重建归档、不清理工作树、不重绑5176现场。

## UC2 四层状态与独立问题

| 层次 | 状态 |
|---|---|
| 批次验收 | 546/547 已完成；无合法既有草稿编辑样本，未新增保存及权限运行矩阵覆盖 |
| 主线集成 | PR #482 / e802f7239bf005482a352caa64eb9da0e78a085a 已完成 |
| 版本发布 | 本轮未报告部署，不登记完成 |
| 用户交付 | 正式89入口整体交付验收未完成 |

退库无正式可用能力，另立来源关联、可退数量、库存方向、权限评估专题；不直接放开出库分类，不复活旧菜单。action777保持原未通过；结算demo期望280000/实际0原因未定。三者不混入UC2完成结论。

## 剩余44项：按结构关系分组

仅使用既有 `form_structure_compatibility_consumers_v1.json.entries`，保留每项历史sourceHead与证据状态；未重新扫描89入口或数据库。以下view数字是原台账的运行ID，后续实施使用XMLID并重新核对所选组的实际契约。分类是排程依据，不证明旧路径已退出；sections为空也不能直接扣减。

共同旧路径为台账的 `legacy structure slots → frontend compatibility floorplan`。各组精确旧配置名已写入台账 `nextBatch.groups[].legacyConfigurations`。标为“机制族”的组不表示共用一张原生表单，实施仍按列出的子组隔离条件与权限。

| 组 | 入口清单（action） | 视图/继承与旧路径 | 必须保留；代表场景；风险 |
|---|---|---|---|
| G01 资料证照（首组，2） | 证书管理666、制度文件862 | 同model/view1703；根 `view_sc_document_admin_document_form`，源XML无inherit_id；两项action产品化覆盖 | fact_type条件、有效期、附件、来源、办理动作；两入口新建/查看，跨页签及权限否定例；中风险 |
| G02 发票（4） | 进项785、开票申请786、销项787、预缴788 | 同view1651；共享form_sections + P1业务事实 + 各action产品化覆盖 | 发票/税额/明细/红冲/来源和分类权限；每入口契约，进销项明细与预缴条件代表；高风险 |
| G03 收入（2） | 收款登记637、公司收入806 | 同view1644；共享sections/P1事实 + 两种产品化覆盖 | 合同、账户、抵扣与责任余额、明细；项目/公司各一例及公司边界；高风险 |
| G04 支出（2） | 实付837、公司支出808 | 同view1647；共享sections/P1事实/实付v2 + action覆盖 | 来源申请、付款账户、凭证、状态动作；申请驱动实付/公司费用两类；高风险 |
| G05 费用（3） | 报销792、公司项目扣款798、备用金793 | 同model，view1633/1632为两个根表单；扣款与备用金共view；生成覆盖和action覆盖 | 报销、扣款、备用金条件与责任余额、来源、账户；两根表单各一例及同view分类反例；高风险 |
| G06 抵扣（2） | 税额抵扣790、项目专项抵扣879 | 同view1654；共享sections/P1事实 + action覆盖 | 认证、税额、发票/预缴来源和明细；两个分类各核契约及条件；高风险 |
| G07 薪资（4） | 核算清单873、社保公积884、工资薪酬858；发放874 | 前三共view1697，发放为伴随view1700，不冒充同view；生成与action覆盖 | 人员/期间/薪资社保字段、发放记录、敏感权限；核算/社保条件+发放关联，不改算法；高风险 |
| G08 上下文工作台（3） | 班组借扣875、往来款877、公司项目退款878 | 独立view1932/1933/1934；同“办理上下文/说明”配置形状，非同model | 路由上下文、业务去向、帮助、各自操作权限；每入口上下文与动作核对；高风险 |
| G09 用量履约（3） | 劳务871、机械570、分包575 | view1461/1476/1491；劳务advisory继承劳务原生表单；共sections/P1事实机制，机械/分包另有action覆盖 | 用量/工期/合同清单/计价只读事实及来源；劳务继承帮助、机械数量、分包明细代表；高风险 |
| G10 工程过程（5） | 安全682、质量867；日志729；工程资料597、进度527 | view1741/1550/1893/1560/1389；处理表单、安全质量子组；日志三层覆盖；资料进度生成路径子组 | 责任/整改/验收结果、日志内容附件、进度数量；按三个子组取代表，状态和来源逐入口核对；中风险 |
| G11 轻表单/管理配置（6） | 消息860、岗位883、资产885；审批727、系统参数887、编码888 | 各自view1910/2070/1908/1887/2072/2074；无共享根，entry或generated机制族 | 消息只读/已读语义、岗位职责、资产归属；配置权限、审批条件、编号格式；前3中风险、后3高风险，分开验收 |
| G12 项目立项（1） | 724 | view1503项目专用创建；另有project.edit_project及多层继承，不能整model停用；project_project_form_structure_v1 | 创建身份、参建关系、合同工期、必填和来源；立项新建+非立项表单反例；高风险 |
| G13 日常合同/结算（2） | 合同687、结算876 | view1757/1764；结算共用UC1根，仍有daily_contract_settlement action覆盖 | 合同分类、结算来源/明细/动作；日常合同与结算各一例，UC1结算结构不退化；高风险 |
| G14 汇总与保证金（4） | 成本归集523、盈亏522、资金汇总646；保证金778 | 独立view1379/1377/1669/1540；均generated路径，汇总只读与保证金办理分子组 | 只读聚合口径、钻取来源；保证金合同与状态动作；汇总一例/保证金一例，禁止改计算；高风险 |
| G15 税务申报（1） | 880 | 独立view1659，tax_filing_form_v1 | 申报期间、税额测算、来源治理和权限；只读测算+合法新建代表；高风险 |

同一resolved view只说明共用候选。发票、薪资等根表单的有效继承组合还需实施时按所选组核对，未从历史ID推断运行继承已验证。劳务advisory继承和项目继承扇出来自本次有限源码核查。以上15组共44项，无重复、无漏项；不把额外状态消费者886重复计入。

## U-C3 首组执行范围

选择 G01：666证书管理与862制度文件，同一model、同一原生form，同一说明/附件页签、状态动作与来源字段，可一次迁移共享结构，并分别保留fact_type条件。无需新增库存、金额或业务计算规则。相比财税/薪资大组，跨模型关系较少；权限差异明确，风险可通过既有授权正反例控制。

- 正式action：`action_sc_certificate_registration` / `action_sc_product_policy_document_v1`。保留前者certificate_registration与后者policy_document的domain/default；政策列表使用 `view_sc_policy_document_tree`，不误换成通用列表。
- 原生来源：`addons/smart_construction_core/views/core/document_admin_document_views.xml` 的 `view_sc_document_admin_document_form`。只迁移必要章节、字段顺序、来源追溯和说明/附件布局。原生当前“历史来源”组为空，旧配置含四个legacy来源字段，实施必须补齐，不能停配置后丢失来源。证照配置中的project_id及制度名称label/分类readonly同样逐项保留。
- 退出目标：`business_config_contract_document_admin_certificate_productized_form_v1`、`business_config_contract_policy_document_form_v1` 的sections、结构字段sequence/group_title与entry_semantic_surface重组；保留fact_authority、fact_type_authority、标题/帮助和字段语义。模型级 `business_config_contract_sc_document_admin_document_form_structure_generated` 是需核查的潜在重叠路径，不能仅因本台账未命中便全局关闭。
- 同model的公司存档、借阅不扩为新增正式入口；若调整共享根或模型级覆盖影响它们，补有限结构反例以避免退化，不复活菜单、不计入本批扣减。
- 权限：证照action允许business_initiator/business_config_admin；制度action仅business_config_admin。模型ACL允许发起人读写创建而非删除，配置管理员拥有删除权限；保留action与模型两层约束、公司/记录规则和附件可见性。密级字段不是新增授权机制，本批不得自行设计密级权限。
- 原有提交、完成、取消、重置草稿及日期一致性规则保持不变；不通过直接调用动作完成浏览器取证。

代表验收：两个正式菜单各查实际契约，新建+可用现有记录；桌面以证照新建/制度查看、移动以制度新建/证照查看覆盖共用布局与不同条件。核对隐藏组不能导航、页签切换保留未保存说明、附件与来源可读；分别检验发起人证照权限和制度入口不可达。已有合法草稿才补编辑，无样本就记录，零保存现场不冒充保存能力验收。两入口都需最终无结构覆盖/无兼容依赖和浏览器证据后才能从44扣减，预计最多44→42；当前保持44。

按整组连续实施与定向验证 → 一次集中浏览器复核 → 冻结并走PR主线集成门禁。普通缺陷在批次内修复；新增业务规则、权限扩张、库存/金额口径变化才升级讨论。

## 本轮执行与承接

- 分支：`feature/uc3-native-structure-grouping`，基线 `e802f7239bf005482a352caa64eb9da0e78a085a`；主工作目录承接UC3文档准备，UC2 linked worktree与5176现场原样保留，两个历史工作树未动。
- Formal Product Layer=P4；Layer Target=兼容消费者台账与批次排程；Module=docs/ops/iterations；Standard vs User-Specific=工程记录。Why Here=主线集成状态与规划不属于业务模型；Why Not Elsewhere=不改P0机制、P1规则或P2/P3偏好；Blast Radius=本台账及本记录。
- 后续实施归P1 `smart_construction_core` 原生视图和精确配置退役，已有P0通用机制复用；本轮未实施U-C3产品改动。
- L0：起始完整指纹 `db4d78613db67a3ddd895b70937e5ab080fa9f411bd68e4ba1a6affb9f038230`。L1：`make ci.local.iteration` 通过（16 tests，仅静态门禁、不产生候选receipt）；JSON解析、44项分组集合一致性、UC2合入内容比对、文档diff检查均通过。本轮低风险文档变更，L2/L3/L4不运行（未变产品、脚本和运行输入），L5/Quick不运行（用户明确要求，尚非冻结集成候选）。UC2历史通过结果只证明原候选，不冒称本分支新门禁。
- 回滚范围仅本台账与记录改动；原证据和运行态均未变。下一步直接按G01整组实施，复用已登记local.dev及模块测试入口，不新增环境、fixture或治理专题。

## U-C3 执行边界调整（同批持续记录）

本次P4只调整仓库执行规则，不改变U-C3首组666/862。原硬要求：AGENTS、工作区规则及.agent元数据对日常验证也要求完整指纹/双指纹承接；现已显式改为分阶段身份。原额外习惯：逐修复交付包、重复摘要、为文档提交重拍/重绑定；立即停止。一个批次一份记录，开发HEAD/dirty → 集中代表面产品复核 → 最终冻结一次完整证据归档；证据按输入影响失效。既有工具的强制SHA/clean/receipt校验、高风险写入的受管对象/权威回读/恢复措施照常执行。

变更范围：AGENTS.md、执行白名单/工作区规则、.agent上下文/决策与既有规则守卫；P4执行治理，非P0/P1产品行为。最低验证为规则静态与现有非零定向测试；无产品/运行变化，跳过模块升级、浏览器、Quick和新交付包。UC2继续登记主线集成完成，复用归档，不补材料。U-C3尚处规划/开发阶段，本记录不宣称冻结或交付。

四层状态口径已写入仓库规则及上下文：批次验收、主线集成、版本部署、用户交付分别判定。UC2实况为“批次验收完成（保留未覆盖项）｜主线集成完成（#482）｜未报告部署｜89入口整体未验收”；UC1仅据合并证明主线集成，不宣称部署。U-C3为“开发准备｜未集成｜未部署｜未验收”。一PR可承载多个批次，一版本可包含多个PR；兼容清零只衡量结构收敛，正式89入口需按职责验查询、办理、关键写入、权限及使用支持。仅选定交付版本时组织跨批次验收，复用有效证据。

规则调整验证：`make verify.baseline.iteration.execution.policy` 通过（16 tests），`git diff --check`通过；无产品/运行输入变化，未生成完整指纹、未运行浏览器/Quick/发布验收。本规则变更尚为本地提交，未宣称主线已生效。
