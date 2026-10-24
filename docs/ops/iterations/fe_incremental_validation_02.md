# FE-INCREMENTAL-VALIDATION-02

> 当前状态：HEAD 9ceac3b22 + 本地规划器映射及记录的未提交差异。采集实现的定向测试有效；完整 Quick 已取消，未签发通过回执。以下冻结描述为历史过程，不代表当前交付资格。
> 本次收口执行 39 项纯 Python 规划器测试（0.640 秒），独立差异复核通过。未执行前端构建、类型检查、浏览器、后端模块全量或新一轮冻结。
> 只采集、不复用：实际后端测试减负仍为 0 秒。未推送、更新 PR、合并或部署。

P4 验证工具；基于 fix/fe-incremental-validation-01 @ 1ddade160，保留上一批未提交的调查记录。范围：既有 backend_impact_plan 的实际文件读取映射、定向回归、执行器回执设计。

不改产品逻辑、测试断言、远端门禁；不执行 pip 缓存试验、不启用复用、不推送/合并/部署。静态读取映射属于验证工具，不能转移到 P0–P3 产品规则。只将可静态证明的具体文件关联给实际读取者，保留不支持读取的可见限制，不宣称已得到完整依赖闭包。

本批从上批原始证据继续，不重跑 14 模块。回滚只需撤销本批工具与记录，不涉及数据库。

## 回执设计（待实现，当前不得据此跳过执行）

复用既有 backend_test_suite 工作流、make test、orm_result_guard 和 evidence_scope，不新增测试注册表、缓存服务或另一套决策引擎。作用域以现有 module plan、实际测试标签和实际执行列表为准。

| 回执字段组 | 必需内容 | 采集点 |
| --- | --- | --- |
| provenance | repository、PR、integration base、candidate SHA/tree、run ID/attempt、job ID、workflow blob | 现有精确 checkout/plan；base 绑定不可变运行事件，不从事后可变 PR 字段补写 |
| target/scope | 现有 target、module、ORM/Python 类型、执行命令、tags、测试文件清单与实际执行测试身份/数量 | 现有 Resolve module list 与 module 循环；计划范围与真实完成范围必须相等 |
| inputs | 测试代码、被测模块及依赖闭包、实际 JSON/fixture/config、生成物及其源、执行脚本/Make/workflow 的路径与 blob/mode 摘要 | 精确 Git 树；before/after 均覆盖删除和重命名；未解析动态读取不得冒充完整闭包 |
| toolchain | Python 实际版本、pip 版本、安装后包清单及包内容/下载摘要、Node 等实际参与工具身份 | ORM：test.sh 中 pip 完成后、odoo exec 前，在实际测试容器内采集；Python 模块：宿主执行前采集 |
| environment | 实际 Odoo 镜像、正在使用的数据库/Redis 镜像 ID及 RepoDigest、runner image/架构、规范化配置、数据库初始化/fixture指纹、角色权限来源 | Build images 后及每个 module attempt 前；读取运行容器，不能只读取可变标签 |
| result | 真实退出码、guard判定、非零数量、实际测试身份摘要、开始/结束时间、重试记录、原始日志 SHA256 | 当前 PIPESTATUS、ORM guard/Python nonzero guard之后；最后尝试不得掩盖旧失败日志 |
| retention | completed_at、expires_at、策略身份、原始日志和回执 artifact ID/digest | 当前工作流结束时归档；缺文件/过期/策略改变均拒绝复用 |

### 验证顺序与可信来源

1. 从同仓受管 workflow 的指定 run/attempt 下载不可变归档，并通过平台 API 校验 run、job、workflow 来源与结论。JSON 自报 PASS 或 SHA256 自洽不等于来源可信；离线导入只能消费已经验证来源且带原始归档摘要的本地证据副本。
2. 验证必需字段、类型、版本、完整 SHA/tree、target、命令及实际覆盖一致；测试数为零、执行中断、退出非零、目标不匹配一律拒绝。
3. 重算日志与输入清单摘要，检查测试源码、断言、依赖、生成物来源、执行定义与环境身份；任何未知读取、缺失环境字段都不得以默认值补齐。
4. 核验有效期及当前策略；当前候选再构造一份决策记录引用历史 artifact/run/hash。不能将旧回执换上新 SHA。
5. 只有通过以上验证的真实成功结果，才允许适配到现有 evidence_scope units/ledger；由该引擎判断输入一致与失效。后端适配器只接受 executed/pass，不将引擎通用的 declared 状态当作测试执行成功。
6. 未来输出 RUN/REUSE/BLOCK 仍须保留完整集成范围；未知/不可验证为 BLOCK 或明确全量回退，不能默默删除必需目标。新 SHA 的远端必需 gate 仍执行当前裁决与聚合。

有效期须使用受管固定策略；不能让任意输入文件自行延长 expiry。当前阶段尚未选定或执行该策略，不提供假设的“有效历史回执”。历史 #722 日志缺少的镜像和包指纹不能通过今天安装/拉取补造。

### 执行器接入位置与失败处理

- 当前 executor 已能提供真实退出码、非零测试数、module-qualified 测试身份、数据库 summary、每模块原始日志及执行范围校验；无需改测试断言。
- 当前缺少容器内安装后环境记录、逐目标完整 inputs 清单和成功回执归档。计划在现有循环中采集；成功回执只在所有对应条件满足后签发，失败仅归档诊断。
- 容器内环境采集应仅输出允许字段，禁止完整环境变量、数据库连接凭据或带凭据的下载 URL。随机密码不进入复用键；角色/权限声明、fixture 和数据库初始化规范必须进入。
- 临时数据库/容器编号和时间戳仅是来源信息，不单独引起失效；镜像、数据库版本、配置与fixture身份必须影响输入键。不能借规范化去掉真实差异。
- 验证器未来必须覆盖：日志/回执篡改、过期、错误 target、漏跑、零测试、失败结果、源码/测试/生成物/环境变化，以及完整相等的正例。当前只完成设计，没有实现验证器或启用历史回执消费。

## pip 缓存单独处理（本轮仅设计）

应将受管 runner 缓存目录以唯一登记的 bind mount 映射到测试容器的 PIP_CACHE_DIR，在依赖安装前 restore、成功任务后 save；宿主路径、容器路径和缓存版本必须一致。宿主 ~/.cache/pip 的现有空路径不能证明容器缓存生效。key 应绑定 Python/pip/平台与实际测试依赖锁定身份，而非仅 requirements-odoo。

先解决测试依赖可复现身份；未经核实不猜测现有未锁包版本。后续验收需同一受管环境两次独立安装，比较包版本/摘要，核对 cache hit 与安装耗时；缓存命中不等于测试结果复用。当前未运行这两次安装，未声明缓存收益。

## 当前范围限制

本轮完成明确 JSON/fixture Path 读取的静态补充，不是完整 Python 动态依赖分析。未解析站点随计划输出；读写库、动态 import、数据库与角色上下文仍需对应实际执行证据。完整依赖闭包未被证明之前，不启用 REUSE。

## 所有者补充：运行时动态契约是权威

静态测试读取关系仅是一类输入依赖，不是产品契约，也不是完整的影响范围裁决。三份 JSON 的已知测试读取边来自源码；不能反向将这些文件升级为运行时契约的固定权威。

实际源码链已确认：smart_construction_scene/core_extension.py 的 smart_core_surface_policy_file_default 提供默认文件；smart_core/core/scene_delivery_policy.py 通过扩展钩子及 SCENE_DELIVERY_POLICY_FILE 解析实际路径，再加载策略。默认文件与实际生效内容可能不同。因此，先前“只影响一个测试模块”的表述仅指本次提取的直接测试读取边，不能解释为产品影响闭包。

回执还必须包含独立的 runtime_contract 输入组：

- 由现有受管运行时核验读取实际发布/生效契约，绑定权威身份与内容摘要、声明来源及发布状态；不能仅以仓库 SHA 或默认 JSON 摘要代替。
- 绑定命名空间/租户/公司、数据库、角色及有效授权范围，以及会改变契约投影的运行配置。测试账户标识不等于权限上下文。
- 记录动态来源解析结果及相应声明/生成器/配置依赖。源码未变但发布状态、有效契约、权限或来源发生变化时，相关回执失效。
- 运行时未提供必要权威身份或不能回读，不补造“版本号”、不使用静态 JSON 兜底证明，复用决策为 BLOCK。
- 内容规范化只能沿用已声明的契约规范，不能为让指纹相等任意删除字段。原始回读证据保留摘要与来源。

本批不会改动产品契约来源、添加前端业务判断或把动态声明固化为静态规则。当前解析器输出的是源码文件读取的可证明子集；未来决策器必须在静态输入、动态契约、环境和执行证据全部闭合后才允许 REUSE。

## 定向验证结果

既有 `make verify.ci.workflow.contract` 通过：30 + 17 + 24 + 8 + 9，共 88 项；其中影响分析 24 项覆盖实际 JSON 读取、删除/改名、普通文档不误命中、原有 unknown-impact 保护及作用域反例。日志：`.runtime/fe-incremental-validation-02/workflow-contract-reviewed.log`。

精确 PR 源码回放记录 `real-dependency-replay-final.json` 证明三份 JSON 的直接测试读取者是 smart_construction_scene；未解析站点 33 个。该回放是静态子集观察，不是动态契约验收或完整影响闭包。源码无变化情况下不重复执行 14 模块；本批测试复用收益仍为 0 秒。

实际改动仅两份 P4 Python 工具/测试文件及本批上下文记录。上一批原始调查、失败与缓存日志全部保留。本地 HEAD 为 1ddade160，加本批明确未提交差异；不是冻结或远端集成候选。回执验证器、pip 缓存运行修复、增量跳过与远端对照未实施，本轮交付为依赖修复与回执设计。

独立复核：已报告问题全部闭合，最终两文件差异及动态契约回执设计无阻断意见；复核绑定上述 HEAD + 未提交差异，不代表交付准入。


## 续作：执行观察回执实现（当前状态，覆盖上文“仅设计”的历史阶段）

本轮继续限定 P4 验证工具：在现有 backend_test_suite 模块循环增加执行观察采集与 artifact 留存，未改产品逻辑、业务断言或测试选择策略。HEAD 仍为 1ddade160d7759ebb2fcda03c162d42593461e45 加未提交差异；不是冻结候选，未推送、合并或部署。

已实现：

- backend_test_receipt.py 收集精确源码 head/tree/base、实际模块/标签/数据库、测试源码 blob、结果与非零数量、逐目标墙钟耗时（秒级，ORM 包含其重试耗时）、日志摘要。Python 单测单独记录 collected/skipped/executed，拒绝全部跳过。
- ORM 容器完成 pip 安装后采集 Python 与包版本、RECORD 元数据摘要；后者不是安装文件逐一校验。记录实际 Docker image ID、数据库/Redis镜像及工具版本。没有新建数据库或环境。
- 归档前从父环境及本次实际使用的受管临时 env 文件读取允许的秘密字段并脱敏；不执行或上传 env 文件，不记录完整 compose config。当前只归档最终成功 attempt；旧失败日志和 GitHub 原任务日志保留，不能宣称已经归档完整重试历史。
- 验证器核对外部给定摘要、源码身份、文件完整性、结果和固定 24 小时观察有效期，拒绝篡改、链接、过期及自行声明可复用。这是本地观察格式的保守约束，不是已经批准的跨候选复用有效期/SLA；正式复用策略仍待接入现有控制器。
- workflow 增加逐 shard artifact 上传配置，但尚未发布或在远端实际运行。采集失败不签发成功观察，既有测试继续按原选择执行。

所有新观察固定 reuse_ready=false。仍缺平台不可变来源核验、测试完整依赖闭包以及实际生效的动态契约/权限/配置回读。whole-tracked-tree 仅保守绑定源码，不能代替这些输入。当前没有可复用的正式后端成功回执，也没有新增跳过机制。

验证：make verify.ci.workflow.contract 共 106 项通过（30+17+18+24+8+9）；18 项新回执测试包含真实临时 unittest 执行、ORM 合成日志守卫反例、全跳过、未导出密码脱敏、篡改/过期/错源/缺环境/禁止覆盖。日志 receipt-contract-reviewed.log 中 ORM FATAL 来自预期拒绝反例，不是产品运行失败。临时测试仓库和模拟镜像身份仅用于工具单测，不计作实际 backend CI 证据。

另有 shell/workflow run-block 语法与 diff 检查通过；verify.guard.registry 的 24 项测试及登记审计通过，未修改 registry 或 baseline。此前 88 项映射阶段记录保留为历史；当前 106 项结果覆盖同一目标的新增依赖。未重跑 14 模块/673 项业务测试，未重走 UX 旅程。

本轮仍无后端测试复用节省，实测收益记为 0 秒。下一步是为受控执行补齐可信来源和动态契约回读，并由唯一 evidence_scope 控制器作复用裁决；不能以当前观察器冒充已完成精准增量验证。pip 持久化缓存及其两次安装对照仍未实施。

续作独立复核完成：全跳过及未导出秘密两项 S1 已关闭，当前所审差异无剩余阻断。未重复运行产品测试；运行时复用前提缺失仍保留。


## 续作：平台来源及契约—事实关联（2026-10-24）

所有者新增约束：契约必须动态，且契约与事实层数据关系必须锁定。事实至少分为两类，不能相互代替：原生模型/字段/视图/动作/访问规则等结构事实，以及断言真正消费的业务记录、状态、关联对象、查询结果集合。JSON 是载体，不是另一个可手工维护的事实权威。

源码链核实：ui_contract_v2_authority.seal_runtime_contract 在实际交付边界调用既有 seal_unified_page_contract，记录 sourceSha256、contractSha256、source authority 和可能的 publishedVersionRef。unified_page_contract_v2_data 从源载荷投影 mainData/tableRows/relationRows 等。sourceSha256 只覆盖传入载荷，不等于已证明所有原生数据库事实和业务读取范围完整。

因此增加 contract_source_binding 校验，直接调用既有 contract_lifecycle 的规范化及摘要规则，不另造契约格式。源事实载荷与契约摘要必须同时一致；模型、字段、domain、记录值的单独变化会被拒绝。该检查仅证明给定材料相互一致，不证明材料来自真实数据库，更不证明契约正确表达了源事实的业务语义；后者仍由原有业务/契约测试断言验证。缺少事实范围权威回读时，统一保留 fact_scope_readback_missing，禁止复用。

后续受管回读的必要关联边界：

1. 同一次测试/交付读取中的实际源载荷、最终契约、发布/配置及生成器身份；不能用仓库默认 JSON 代替。
2. 数据库与公司/租户、执行用户、有效角色/权限、查询模型/字段/domain/context，以及实际消费的数据源与关联路径。
3. 结构事实与相关业务事实的变化分别使所依赖目标失效；新增/删除满足筛选的记录会改变结果集合，因此仅现有 record IDs/write_date 不足以证明查询未变。
4. 使用同一一致性读取边界或有明确前后读校验，避免把不同时点的契约和数据拼成假证据；单独时间戳、数据库名称或全库哈希均不能替代具体读取依赖。
5. 相关字段、状态、关联对象、权限或结果集合变化须使对应目标失效；无关记录不应机械触发全量。缺少可靠映射时明确 BLOCK/受管全量回退，不猜测无影响。

本轮没有在 P4 新增产品语义或修改 P0/P1 契约；本地开发库的既有探针不能作为 CI 临时测试库的权威快照，因此未重跑本地角色/浏览器验收来填补该缺口。

平台来源实现：同一 receipt 工具增加只读 GitHub GET 核验，固定受管仓库及 numeric repository ID，绑定 run attempt/head/workflow、artifact ID/name/digest、源码 tree 及回执来源。ZIP 在内存解析、不按成员路径解压；拒绝越界路径、链接、重复项及超限大小。平台来源通过后仍保持 reuse_ready=false，额外保留 execution_definition_not_attested：候选自己输出的成功材料，不因为来自 GitHub 就成为可信测试执行证明。

本地定向验证 114 项通过（原 88 + 回执 26），含错误 run/attempt/head、外国仓库、过期或错属 artifact、摘要与 tree 错配、ZIP 路径/链接、契约与事实变更反例。日志 origin-contract.log。这些平台测试使用明确模拟 API/压缩包，不是远端实际 artifact 验收；尚无当前新格式的远端真实回执，未宣称已取得正式复用资格。


来源边界补充：真实 GET attempts/1 核验历史 run 40094940241 成功、head 88b4c1609eb2802f95a0b367a44efffd985db173、仓库 ID 1307419149，结果保存在 platform-origin-transport.json；只证明 API 传输与运行元数据，不是新回执端到端认证。

独立复核发现 artifact 平台元数据只绑定 run/head，而名称和回执中的 attempt 可由上传者声明。已收紧输出为 requested_attempt + artifact_attempt=not_attested，并保留 artifact_attempt_not_attested；不能声称精确 attempt 的 artifact 来源已认证。修正后 114 项再次通过，最终日志 origin-contract-reviewed.log。需要平台可验证的 artifact-attempt 关联及可信执行定义，才可继续消除来源缺口。

当前仍为本地未提交 P4 差异，不是冻结/远端准入；业务逻辑、daily、PR 和 CI 状态未修改，测试复用节省仍为 0 秒。接下来应在受管执行边界采集同一读取上下文的源事实与最终契约，连同权限/查询集合证据绑定到测试目标；不能用另一个环境或手填 JSON 补齐。

最终定向独立复核确认 S2 已闭合，本次所审实现范围无剩余阻断；保留所有真实运行和复用前提缺口。


## 续作：同次交付、同事务的真实只读事实采集

P4 新增 backend_contract_fact_readback_probe.py 与 7 项工具单测，并以既有 local.dev 包装登记 local.dev.runtime.contract_fact_readback.probe。复用受管 .env.dev、sc-local-dev/sc_dev_demo 和 odoo.shell.exec 的独立进程；没有新环境、数据库、凭据、业务记录或权限改动。未重新执行 UX-01/02/03。

实现边界：PostgreSQL 强制 READ ONLY + REPEATABLE READ；拒绝 commit；观察器仅包裹该进程的实际 seal_runtime_contract，原方法返回后读取源载荷及最终契约。权限检查与实际分发共用完整 intent envelope；契约模型、源模型、mainData.id 必须与请求目标一致。finally 恢复观察器/请求 shim、回滚事务并恢复 commit 方法。实际记录读取始终使用非 sudo 的财务 actor；仅策略声明读取使用 shell 管理身份，未扩大业务读取权限。

保留失败过程：

- readback-runtime.log：首版 source target mismatch，exit 2；独立复核同时发现旧性能探针模板使用裸 params 进行权限检查，已在本新探针修正为完整 envelope，拒绝即不得分发。没有将此推断成产品权限缺陷，也未改既有旧探针。
- readback-runtime-reviewed.log：精确目标校验确认旧数字 action 878 在该库实际是 sc.receipt.income，exit 2。这是测试工具跨环境数字 ID 假设错误，未改产品或数据消除失败。
- 改用 smart_construction_core.action_payment_request_pay 的实际 XMLID，读取其原生 res_model/domain 后选择已有可读记录。模型不再由脚本猜测；action domain/context 摘要随报告绑定。

真实结果 readback-runtime-action.log：exit 0，一次成功观察。环境 sc-local-dev/sc_dev_demo；财务 uid 47、company 1；实际 action 760，payment.request(3)；实际 publishedVersionRef=ui.business.config.contract:146@1。同一事务 snapshot 642040:642040: 内读取契约/source、结构字段摘要、47 个所选存储字段的事实摘要、该模型策略声明摘要、用户组/context 摘要，并重复读取所选事实确认一致。事务只读模式和隔离级别来自数据库查询，非手填声明。原始业务字段值未输出。

提取报告 readback-runtime.json；readback-identity.json 绑定 HEAD 1ddade160 + dirty、探针及报告摘要。运行中实际加载的 lifecycle/authority 文件哈希与本工作树对应源文件一致。该回读是采集器机制验证，不是历史 CI 的事实快照，不作为后端成功结果写入复用账本。

必须保留的限制：source/contract 一致、记录身份一致、同快照事实两读一致，不等于已经逐字段证明契约投影值与事实值等价；action context 哈希也不是完整 UI 上下文验收。相关计算字段、关联模型权限、完整查询依赖与结果集合覆盖仍不完整，reuse_ready=false。未修改产品契约来弥补这些缺口。

定向验证：make verify.ci.workflow.contract 121 项通过（原 114 + 本采集器 7），日志 readback-contract-action.log；verify.guard.registry 24 项及审计通过，无 registry/baseline 修改。独立复核确认权限/目标绑定修正及 XMLID 动态解析无剩余实现阻断，认可上述严格限定的运行证据口径。

下一步应把这些同次读取事实与原有后端执行目标对齐，并补足明确目标的投影值对应及依赖闭包；不能用本地库快照给远端 14 模块/673 测试授权复用。未推送、合并、部署；测试复用节省仍为 0 秒。


## 续作：直接原生标量字段三方值核对

沿已存在 ui_contract_v2 的 record hydration、source.record 与 assembler mainData 复制链实现 P4 比较，不新增产品语义。字段集合从实际 source/mainData 与运行时 _fields 得出；只比较 store 且非 compute/related/translate/company_dependent 的原生标量字段，使用既有 lifecycle.canonical_json 的交付序列化规则。id 由独立目标校验负责，不计入字段值数量。不增加字符串强转、false/null 默认值或金额容差。非覆盖字段逐项记录原因，零可比字段失败，任一侧值不等失败；输出仅字段名和结果，不输出原始值。

事实读取改为实际交付者 owner.env 下的记录；仍要求同一游标、同一 uid、非 sudo，并记录交付 context 与比较字段元数据摘要。重复读取也使用该事实记录的同一上下文。

真实受影响探针执行 parity-runtime.log exit 0：sc-local-dev/sc_dev_demo，uid 47/company 1，action 760，payment.request(3)。18 个 checked_fields 三方值一致，mismatch 0；77 个 uncovered_fields（65 个计算/上下文相关、9 个关联/非标量投影、3 个某侧缺值）。这些是覆盖分类，不是 77 个产品缺陷；没有为提高覆盖而改业务或数据。full_projection_parity=false，projection_value_coverage_incomplete 等 blocker 保留，reuse_ready=false。

报告 parity-runtime.json 与 parity-identity.json 绑定本次探针/报告摘要、HEAD 1ddade160 + dirty。已确认运行加载的 lifecycle/authority 哈希与当前工作树相符。旧 readback 成功和失败记录均保留，不覆盖。本地证据仅支持该记录的这 18 个字段，不证明完整契约、查询集合、关联对象或其他记录。

make verify.ci.workflow.contract 126 项通过（此前 121 + 新增 5 项三方比较测试），日志 parity-contract.log；新增反例包含任一侧改值、缺值与转换字段未覆盖、零非 ID 可比字段、类型混淆和既有日期序列化。独立代码复核无阻断，真实结果口径另作定向复核。未重跑无变化 registry 或完整 Quick；未执行远端写入、合并、部署，测试复用收益仍为 0 秒。

后续仍需将采集接入真实 CI 目标，并针对确实影响该目标的计算/关联依赖、查询集合和环境身份完成范围证明。不能把本地部分字段相等升级为旧 673 项测试的复用资格。

实际证据独立复核完成：日志/提取 JSON 一致，探针、报告与两项加载源码哈希匹配；18/0/77 的限定口径成立，不授予完整投影或 CI 复用资格。


## 续作：真实 CI 目标的已知输入清单与历史回放

停止扩大本地产品探针，回到 backend_suite_plan 既有目标与分片。新增可选 --input-inventory，记录精确 Git 树的 mode/kind/OID、已登记模块依赖闭包、直接文件读取及共享执行输入；外部模块、未解析读取、缺失路径、symlink/submodule 等 special entries 显式保留。known_inputs_sha256 只覆盖已知输入，dependency_closure_complete=false/reuse_ready=false，不是另一个复用裁决器。原选择集合和分片完全保持。

workflow 在原 Resolve module list 步骤生成详细清单，并将同份 scope-plan.json 归档到原执行观察 artifact 目录。详细清单不写入 job summary，避免多 MB 摘要；工作流尚未推送或运行新版本。此处没有把本地 fact probe 接入 CI 或宣称动态事实覆盖完成。

精确只读回放：集成 base 96c860d0fb041c556b687afaad6dc689528785e5，head 88b4c1609eb2802f95a0b367a44efffd985db173。pr722-input-plan.json 仍选择 14 目标，包含 1875 个已知文件；完整 JSON 2106307 字节，使用共享文件索引而非每目标复制 blob 元数据。13 个目标的已登记模块范围内存在未解析读取，不能因此声称完整闭包。三份实际消费的 docs JSON 已绑定到 smart_construction_scene。

对上一候选 459e4f133056fadbefd46451ae9190a9f91e314d 的 Git 树逐路径比较，14 个目标的已知输入身份均相等。pr722-target-readiness.json 逐目标列出数量、差异、历史回执缺失和环境/动态事实/依赖缺口：全部 reuse_readiness=BLOCK，可复用数 0；这是准备度分析，不是替代现有 CI 的执行或跳过决策。历史完整成功日志仍不等于可消费回执。只读分析没有调度业务测试，实际测试减负仍为 0 秒。

验证：verify.ci.workflow.contract 132 项通过（此前 126 + 6 项输入清单测试），覆盖真实 JSON、传递依赖、已知输入改变、普通文档不误绑定、缺失/未解析/特殊路径、循环依赖、确定性、原分片不变；workflow shell 与 diff 检查通过。独立只读复核无阻断。工具 HEAD 1ddade160 + dirty、分析器摘要与被分析历史 head 分别记录，不混为一个版本。

下一步的限制是原始执行证据，而非继续增加本地页面核验：新格式回执及真实测试环境/契约事实输入只能由对应受管 CI 执行产生，不能从旧日志或本地库补造。远端更新仍未授权；当前阶段不跳过必要 CI、不推送、不合并、不部署。


## 采集版候选收口：计划绑定与逐次诊断归档

回执现绑定实际 scope-plan 的原始字节 SHA256、head/base、目标成员及 known-input 指纹；verify 需提供匹配的计划，平台归档验证也检查该绑定。缺失/篡改计划不得通过，包括平台 ZIP 摘要同步变化的反例。nightly/显式全量保持 base 空，不再用 head 冒充集成基线。此绑定仍是完整性约束，不是完整依赖证明或复用批准。

每次 ORM/Python 尝试独立存放脱敏日志和诊断元数据，进程/tee 退出码分别保存；attempt 诊断永远不等于成功回执。任一尝试的日志或归档失败锁存到模块结束，后续重试成功不能清除，也不能签成功回执。成功重试仍保留之前正常采集到的失败过程。实际 shell 循环使用替身执行器覆盖 8 个路径，真实 ORM 结果守卫未放宽，无 Docker/业务测试执行。

计时为整数秒的执行管道墙钟时间（含 tee；ORM 累加各尝试），执行结束后立即采样，排除归档采集开销。不能将它称为纯测试函数耗时，也没有凭此宣布性能收益。

最终定向验证：make verify.ci.workflow.contract 139 项通过（30+17+12+32+24+14+10），candidate-validated.log。独立复核发现的首轮 tee 失败被重试覆盖问题已修正并闭合；最后计划缺失/篡改反例及计时复核无阻断。早期 candidate-contract.log 的字符串位置断言失败和 candidate-loop-contract.log 的模拟日志时间戳缺失均保留；通过调整生产分支顺序保留原守卫、修正测试夹具解决，未放宽断言。

本轮只构成可审阅的未冻结采集候选。正式 freeze/verify、Quick、新候选远端 artifact 正例、CI 环境/动态契约事实闭包均未完成，不能宣布增量减负或合并准入。远端更新仍须单独授权；当前不触发远端执行。

回退边界：本批修改限 P4 选择器/回执/工作流/测试包装/本地诊断及文档。若采集器运行失败，CI 失败并保留诊断，不改变业务模型、权限或数据；回退采集接入必须同时保持原有测试选择、结果守卫和必要 CI，不能借回退移除原门禁。实际 Docker/GitHub 归档链路仍需受控验证，当前单测不能替代它。

最终 ci.local.iteration 通过（L1 only，candidate-iteration-final.log）；已登记 139 项定向结果。审阅包保留当前未提交文件摘要、补丁、原始失败及通过日志索引；没有冻结或远端资格声明。


## 本地冻结准备

既有 ci.delivery.freeze.prepare 完整通过（freeze-prepare.log）；仅刷新四份派生报告：测试覆盖登记、测试清单、清单摘要、复杂度报告。没有提高 baseline、删除历史证据或修改生成器。清单大量行变化来自顺序 ID 重排，需按实际路径核对新增测试资产。139 项定向测试输入未变化，不重复执行；旧 candidate-review.json 保留为冻结前审阅记录。

本次冻结限定采集版，不宣称测试复用、动态事实完整覆盖或远端成功。后续 clean HEAD 的 Quick、独立复核及完整身份放在 .runtime/fe-incremental-validation-02 中，避免为写入自身 SHA 再次修改候选。受控远端执行仍待单独授权；当前不推送、不更新 PR、不合并、不部署。


## 首次冻结后的 GA020 定向恢复

34843e21a（tree 0d5483be9dade4972e38f0965d515edf1f1a5eff）独立审查通过，但完整 Quick 失败且未签发回执，原始 frozen-quick.log 保留。GA020 要求直接捕获 module_status="${PIPESTATUS[0]}"；采集版先保存整个数组，与既有静态要求不一致。修复仅将测试退出码和完整管道状态放在同一条赋值中同时捕获，既有安全守卫不变；真实工作流 shell 回归进一步检查首轮测试码 0/137 与 tee 失败码 7，确保失败重试不能覆盖证据失败。

本轮恢复的受影响集合为 workflow 的执行状态采集、其 shell 回归及 GitHub 安全守卫。此前产品旅程和本地字段回读输入不变，不重跑。新 Quick 仅在定向结果与差异复核通过、生成报告同步和新候选冻结后执行；旧失败候选不能算通过。

定向恢复完成：GitHub 安全守卫及其 18 项测试通过，139 项 workflow 契约测试通过（ga020-targeted.log）；独立复核确认同条赋值保留原始 [137,7] 管道状态，无守卫变更或豁免。


## 验证范围纠偏：本地定向规划

P4 / 既有 frontend_dev_incremental 本地规划器 / 通用验证编排。仅补现有路径到既有 Make 检查的映射，不新建注册体系。后端采集器、选择器、执行包装及相应测试选择 verify.ci.workflow.contract；backend_test_suite.yml 同时选择 verify.github_actions.security，使 GA020 在迭代阶段可被选中。名称带 frontend 的规划器及其测试均为 Python 工具，不代表前端产品检查。未知工具路径仍为 unmapped，必须人工确定非零 L2；规划输出保持 recommendation_only、candidateEvidence=false、testsRun=false。

36 项规划器测试通过，日志 routing-targeted.log，现有 agent ledger 已记录；独立两文件差异复核无阻断。139 项工作流与 18 项安全测试输入未变，不重复；未将旧原始日志伪装为新签发的受管回执。取消的 Quick 原日志保留，9ceac3b22 不具备 Quick PASS。

可复现只读计划 local-routing-plan.json：基于 1ddade160 到当前 HEAD + dirty 的本批 26 路径，frontend/addons/demo_addons/customer_addons/contracts 产品源码变化为 0。现有本地映射推荐 baseline policy、workflow contract、planner unit、GitHub security 四个工具目标；计划本身不执行它们。上一候选继承的 1ddade160 不混入本批影响集合，完整集成范围仍须另行核对。

尚未解决的远端粗粒度问题：既有 risk_tiering_v1.json 将 make/ci.mk 整文件列入 frontend_full_paths，所以当前远端分类仍是 frontend_mode=full。该结果必须如实保留；本地映射修复不等于远端已精准分类。后续应证明具体 Make 目标、依赖及共享变量的影响后再调整，不能直接删去该路径或把未知作用当作不影响。本轮没有修改远端策略，不授予远端跳测，不启动新的冻结/Quick 循环。


## 本地定向映射收口

39 项纯 Python 定向测试通过（routing-recovery-test.log，0.640 秒），无前端产品执行。补齐逐路径 fallback 后再合并目标，防止一个已知后端或前端路径掩盖同批未知前端输入；纯后端仍只选工具目标。两文件实现独立复核无阻断。

原 routing-final-test.log 的一项失败来自夹具把已登记 frontend/packages/ui 路径当成未知；改用真正未映射的 frontend/apps/web/src/newFeature.ts，保留断言。该失败首次被执行器误登记为通过，已通过既有 begin/record 更正为 failed，保留 routing-correction-record.log；修改夹具后重新 begin、执行成功才 record passed。未修改回执控制器、测试断言或远端门禁。

范围裁决：1ddade160..当前候选的采集增量未改前端产品源；88b4c160..当前候选的完整未发布集成范围另含继承的 frontend_decision_authority 工具及 ci.generated_evidence.preflight 接入。不能以增量无前端产品变化直接推导整个 PR 可跳过所有前端相关验证。make/ci.mk 整文件远端分类仍粗粒度，本地映射收口不代表远端分类已修复；未移除规则、制作跳测凭证或启动远端 CI。

本地映射批次已完成，整体 FE-INCREMENTAL-VALIDATION-02 仍 verification_pending（真实 CI 新回执、动态事实完整闭包及复用收益未完成）。本次只保存本地改动，不重新开启 freeze.prepare/Quick；集成、合并和部署状态均未变化。


## 远端分类输入的最小 Make 目标范围证明（仅本地实现）

P4 / ci_risk_classifier / 既有风险分类器。保留 frontend_full_paths 中的 make/ci.mk，只有精确 40 位 base/head、与路径差异相同的 merge-base..head、两端均为普通 100644 blob 时读取内容。仅允许 verify.ci.workflow.contract 原声明下的单行、无变量/重定向/管道/续行的 Python 脚本或 unittest/py_compile 命令变化；目标头、依赖、共享变量、其他目标、echo、注释等其余内容必须完全相同。不是通用 Make 解析器，不可证明时保留 full。

CLI 显式 --path 不启用 Git 证明；缺失对象、非完整 SHA、symlink、超时、非法 UTF-8 均保守。HIGH_RISK/professional full 不变，既有后端车道仍执行 workflow contract；其他前端路径独立决定 standard/full，workflow_dispatch/release 仍为 full。没有替换后端回执裁决，也没有授权跳过 673 项测试。

独立复核发现 text=True 会规范化 Git blob 换行，使字节证明不严格；已改为 bytes 严格 UTF-8 decode，真实 Git 反例覆盖保留区 CRLF 与裸 CR。verify.ci.orm_selection.unit 最终 34+17=51 项通过（make-scope-bytes-tests.log，0.181+0.366 秒测试运行时间），定向复核无剩余阻断。Git fixture 同时覆盖 dirty 文件不参与证明、分叉基线用 merge-base、普通文件变 symlink、其他 frontend 路径保留及动态命令拒绝。旧测试日志及审查发现保留。

实际已存在提交的只读对照：相对 1ddade160 的采集增量 frontend_mode full→skip；相对 88b4c160 的完整未发布变更仍 full→full，继承的交付入口改动没有被排除。两者 professional_mode 均 full。最终精确版本对照写入 .runtime/fe-incremental-validation-02/make-scope-final-comparison.json；分析不执行测试，不是远端 CI 成功或实测耗时收益。

本轮未修改风险政策 JSON、workflow 必需检查或产品源码；未跑完整 Quick、前端构建/类型检查/浏览器、14 模块全量。只形成可审阅本地 checkpoint；未推送、合并或部署。真实远端回执、动态事实完整依赖及后端测试复用收益仍 verification_pending，节省仍记 0 秒。

## 远端步骤来源采集（e28b59911 后的本地未提交增量）

上述“未推送/真实远端回执未完成”为历史阶段状态。经 Owner 单独批准，e28b59911ea2fb66f1f9cdad54754e72ef0486c2 已进入 draft PR #723，四项必要 CI 通过；14 个后端目标的回执来源已核验，673 项仍全量执行，复用收益为 0。列表与关系证据由既有控制器批准沿用。当前合并准入停在 exact-head Quick 缺失，远端普通 PR 成功不等于完整 Quick 成功。当前索引为 `.runtime/fe-incremental-validation-02/remote-integration-status.json`，保留所有旧记录。

本次 P4 仅在既有 `backend_test_receipt.py` 增加 `observe-job` 只读入口及负例测试。固定 GitHub 仓库和 GET 接口，绑定 run、attempt、job、head、workflow 及提交 tree；保留逐步骤 success/failure/skipped，不把绿色 job 推导为其脚本内部全部执行。平台候选身份不等于实际 checkout，输出明确列出 checkout、执行定义、目标覆盖、环境及依赖闭包的证据缺口；`quick_receipt`、`reuse_ready` 均为 false。未修改 Quick 控制器、必需门禁、产品语义或权限，也未建立第二套复用决策引擎。

40 项相关 Python 测试通过，耗时 2.705 秒，独立只读复核无阻断。真实 API 采集核验后端 job 120891884947 与前端 job 120891827326（均 attempt 1、远端 e28b59911），普通检查 success、完整检查 skipped 被分别保留。前端数据来自既有运行的只读查询，没有重新执行前端检查。采集器源码摘要、测试日志及观察文件摘要绑定于 `.runtime/fe-incremental-validation-02/job-observation-validation.json`。本轮没有签发正式 Quick 回执、提交、推送、合并或部署；下一步仍须绑定实际执行定义与输入/环境，不能将这些观察直接登记为 REUSE。

后续补齐执行时的 workflow 定义身份采集：`GITHUB_WORKFLOW_SHA/REF` 与实际被测 `source_head/tree` 分开保存。PR 的 workflow 可能取自合并引用，不能用测试 checkout SHA 替代。缺失记录为 `not_captured`，有值也仅为 `producer_observed/attested=False`；格式错误、单边缺失、外仓库及自认证拒绝。兼容历史回执缺字段，既有平台认证、执行定义及动态事实依赖缺口没有被豁免。未修改 workflow 或必需检查；执行时实际采集尚待后续单独授权发布后验证。

本地最终 46 项相关测试通过（2.790 秒，`workflow-identity-final-tests.log`），独立复核无阻断；前一个 45 项中间运行仅作历史记录。使用新验证器对四个原始归档内的 14 份回执执行本地完整性回读，14/14 通过且均保留 workflow 字段缺失和 `reuse_ready=False`。这不是新的平台认证或测试执行，未重跑 673 项测试。当前源码与日志摘要绑定于 `workflow-identity-validation.json`；此前 40 项结果属于前一版采集器。当前本地修改未提交，远端仍为 e28b59911，Quick 准入仍未通过，测试复用节省仍为 0 秒。

以上为实施时状态。采集器增量以四个已审阅文件保存为本地 checkpoint，提交身份及精确增量分类记入 `.runtime/fe-incremental-validation-02/collector-checkpoint.json`。提交前再次核对 46 项测试的源码与日志摘要一致，沿用结果，不重复执行。checkpoint 仅保存本地工作，不是正式候选冻结或交付资格；未运行生成准备、完整 Quick、前端或 ORM 验收，不触发远端 CI。当前远端仍为 e28b59911；新提交不得继承其 CI 成功。

## 采集器启动入口边界诊断（141e0994c 后未提交增量）

精确 e28b59911..141e0994c 差异触发 `unknown_impact:scripts/ci/backend_test_receipt.py`，原选择仍为 14 模块 full；没有执行该计划。`scripts/test/test.sh` 确实在 ORM 前调用采集器 `environment`，因此不能整文件加入 NON_RUNTIME。此次在既有影响规划器增加独立诊断字段，不修改 select、required 输出或远端 CI。

比较仅读取两端普通 Git blob 和未变化的启动脚本，保留模块初始化、environment 分支与受限代码范围。参数解析、动态初始化、嵌套作用域、赋值表达式和反射无法证明时返回 unproven；不是通用 Python 依赖分析，也不证明环境等价。真实两端指纹一致，字段 `reuse_authorized=False/selection_changed=False` 保持，不能据此制造历史 REUSE。

独立复核报告的顶层动态执行、嵌套绑定及 lambda 赋值表达式遗漏已通过保守拒绝关闭。白名单收紧期间一次未允许现有算术常量导致 12 个测试错误，原日志 `collector-entrypoint-reviewed-tests.log` 保留；修正固定初始化形状后最终 38 项通过（0.603 秒，`collector-entrypoint-closed-tests.log`），定向复核无剩余已报阻断。源码摘要、结果与真实提交对照见 `.runtime/fe-incremental-validation-02/collector-entrypoint-validation.json`。未改产品、未执行前端/ORM/Quick、未推送或部署，实际测试复用收益仍为 0。

## 最终收口裁决：BLOCKED，不具备交付资格

本节为当前裁决；前述未提交、checkpoint 和各阶段结果均保留历史含义。独立复核确认采集能力的本地实现通过，但不能把旧执行缺失的事实补写为已认证。整体精准增量验证目标仍未完成，run 保持 verification_pending；不是把“采集通过”改称“减负完成”。

本次新增的有界 AST 诊断不参与模块选择，也不能促成合法 REUSE。为避免长期维护不完整的 Python 等价分析器，已将其 160 行实现和 118 行测试从候选撤回；原始 patch、哈希、38 项测试、失败日志及真实提交比较均保存在现有 `.runtime/fe-incremental-validation-02/collector-entrypoint-archive.json` 所指证据中。前述诊断结果仅为归档观察，不是当前候选提供的运行功能。

保留的实现仅为既有采集器的 job/step 来源核验及独立 workflow 身份保存，46 项定向测试证据的源码/日志哈希仍匹配；14 份历史回执兼容回读不等于执行重跑或复用授权。远端 e28b59911 的 14 模块/673 项测试已实跑，workflow 墙钟 716 秒，目标执行耗时之和 1046 秒（并行，不能与墙钟混用），后端测试复用节省为 0 秒。构建缓存收益不计入测试复用。

Quick 仍 BLOCKED：41 个顶层目标中 12 个静态可达不是完整执行证明；其余 29 个不能据此直接判为必须重跑。现有控制器仅接受同候选分片组合或纯 bookkeeping 的完整回执沿用，不能把普通 PR 绿色检查拼成 Quick PASS。后端 REUSE 仍 BLOCKED：历史回执缺失被认证的执行定义、artifact attempt、动态契约/事实范围与完整依赖闭包，新采集字段不能倒填这些事实。

最终本地身份、差异清单、原始证据哈希、远端只读回查、准入阻断及回滚范围统一写入 `.runtime/fe-incremental-validation-02/closeout-package.json`。本地 checkpoint 不是正式冻结候选；未运行 freeze.prepare/完整 Quick/前端或 ORM 验收，未推送、更新 PR、合并或部署。下一步只允许基于具体缺口定义最小补证范围后重新进入执行，不能继续堆叠观测代码，也不能默认全跑 14 模块或放宽门禁。

## Owner 纠偏：远端后续运行复用历史验证，不限 main

上节 BLOCKED 为此前本地 Quick 方向的历史裁决，不作为当前远端增量工作的停止条件。Owner 明确目标是远端后续运行按目标复用前次有效结果，增量来源包括 PR、分支、候选及同候选重试；撤回一次性本地 Quick 请求。集成基线仍描述完整交付范围，不能代替逐目标的历史证据选择。

在既有 `backend_suite_plan.py` 增加可重复 `--previous-candidate` 的审核模式：每个目标分别优先查找已知源码输入匹配的历史候选，再按 Git 距离和 SHA 确定顺序。支持当前 SHA 用于重试比较；无法证明关系的非祖先候选明确拒绝，尚不支持跨 rebase 的历史等价证明。保留原 modules/shards 和远端执行选择，不新增注册系统；输入差异裁决调用已有 `evidence_scope`，历史 inventory 仅为 observed，不冒充成功回执。

24 项定向测试通过（0.010 秒），覆盖不同目标选不同候选、同 SHA、顺序及重复项、删除/模式变化、缺少目标和库存自称 passed 不得复用；独立复核无阻断。真实对照 integration base 96c860d0、当前 063fd46c、历史 e28b59911/88b4c160：14 个目标均选 e28 输入作比较，仅已知共享输入 `scripts/ci/backend_test_receipt.py` 改变，因此 shadow 计划为 RUN 14、REUSE 0、BLOCK 0；没有执行该计划。结果绑定在 `.runtime/fe-incremental-validation-02/remote-target-history-validation.json`。

这是历史输入比较，不是历史成功回执选择或远端复用完成：previous_receipt 为空、环境与成功范围未认证，workflow 尚未接入，实际节省仍为 0。下一步接入逐目标真实 run/attempt 回执的选择和认证，再由既有证据引擎裁决；不回到本地 Quick 主线、不以 shadow RUN 自动启动全量测试。本轮未推送、合并或部署。

## 远端历史证据发现与认证收口（审核模式，尚未启用复用）

本次范围属于 P4 既有 CI 工具：历史运行发现、逐目标成功回执来源核验及审核选择；没有修改产品、workflow 或必需检查。复用仍由既有 evidence_scope 裁决，不另建测试注册或缓存系统。支持分别发现 schedule、PR、push 和手工运行，不限定 main；精确 Git 祖先约束仍存在，跨 rebase 未覆盖。

实际核查纠正此前证据判断：定时验证并非没有可用历史记录。8ff4cad7f3eb38152e74ec9222297bd692612c07 的后端定时 run 40034423582 有正式日志：13 个 ORM 模块 601 项及 smart_construction_scene 71 项，共 14 模块 672 项；专业质量 run 40027635534 的全量 shards 实际通过。前端 run 40027784970 的 artifact 12534522803 摘要与平台一致，绑定 SHA/tree/run/attempt，页面验收 32/32。三类最近各五份成功运行已保存索引。后端与专业质量没有同名回执 artifact，不等于没有执行证据；旧日志尚未转成可被现有逐目标回执消费者认证的复用证明。

新 --receipt-history 只接受定位字段，核验平台归档来源后按目标优先选已知输入匹配的成功记录，再按时间与身份稳定排序。最新坏回执被拒绝时继续寻找旧有效记录；捕获结构错误并保留拒因，不能由候选异常中断全部选择。32 项规划器、47 项回执和 10 项历史发现测试通过，共 89 项；真实 validator 反例覆盖摘要正确但 issued_at 缺失或类型错误。独立复核关闭最后 S2，无剩余已报范围内阻断。

真实只读重放退出码 0：e28b59911 的 14 份来源全部核验成功，无拒绝；目标为 063fd46c 的审核计划 RUN 14、REUSE 0、BLOCK 0，原因是共享已知输入改变。没有执行这些 RUN。规划器源码另以工作树文件哈希绑定，不能把所比较提交当作工具源码身份。来源认证也不等于 artifact attempt、完整依赖闭包、动态契约事实及执行环境均已证明。

证据集中在 .runtime/fe-incremental-validation-02/remote-history-closeout.json，保存源码、日志、原始平台数据与归档摘要。当前实现仍是 shadow：未接入远端执行选择，实际测试复用节省 0 秒。此前本地 Quick 裁决保留为历史记录，不作为当前增量目标。没有重新执行前端、ORM、UX 或完整 Quick，没有推送、合并、部署。

本子范围完成审阅，整体 FE-INCREMENTAL-VALIDATION-02 仍 verification_pending。剩余工作限定为既有证据引擎上的输入/环境等价证明与远端消费，不能把本次来源选择完成称作减负完成，也不能用人工声明将旧全量成功变成新候选通过。
