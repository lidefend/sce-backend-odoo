# FEPC-13I-00 实施前核查

结论：可以拆分为受控实施任务，但**现有代码尚不具备新关系的安全端到端交付能力**。本PR只记录位置、差距和准入；不授权I1实施，不新增正式协议标识。设计不可通过简单添加字段或改版本常量直接上线。

## 基线与证据边界

GitHub main与本地起点均为 `44e7e8447a77ff347ac2cdaf25d8c28b759e61ff`，开始时main工作区干净。服务端源码 assembler及lifecycle当前版本为2.2.0；Web请求声明2.0/2.1/2.2，严格decoder只接受对应外层版本及结构1.0/1.1。这是源码协议能力，不等于部署身份。

按本轮“不重复采集Demo”约束，运行版本只复用已审查的 [FEPC-13R观察](runtime-title-observation.json)：服务端source_revision=`3da65c5c6f3909cb81c0316c85f8a622c952965a`，前端build=`c565398e8482eda9b7a8a17d6742bfb3149b615011cf8cf8faeafc881d46f92f`。这是最后一次已知读回，不是本轮重新确认的当前部署版本。实际是否已变化未验证。没有登录、API、截图或业务点击。

设计依据为已合并 [FEPC-13D-R1](title-identity-projection-contract.md) 及其矩阵/计划；外层2.3、结构1.2、能力标识仍为候选。源文件位置见 [变更地图](fepc-13i-change-map.json)，后续阶段及测试见 [发布顺序](fepc-13i-test-and-release-sequence.md)。

## 1. 现有发布载体能否表达精确绑定？

**部分具备：载体和occurrence校验可复用，身份关系与布局版本锁尚未具备。**

`addons/smart_core/model/ui_business_config_contract.py` 的 ui.business.config.contract 已有 model/action_id/view_id/role_key/company_id、contract_json、version_no、payload_sha256、definition_sha256、source_authority_json及published生命周期。`_check_view_orchestration_payload`识别form下的node_patches等结构；JSON字段能存内容不等于内容已受支持或被消费。

`core/form_configuration_compiler.py:compile_form_configuration` 将有效布局按native_locator建唯一索引，重复locator报错；patch要求target与expected(type/name/occurrence_index)一致，否则CONFIG_TARGET_STALE；set只允许label/visible/readonly/required/columns，并有同优先级冲突校验。它不接受身份关系语义，也没有以“定义绑定的完整有效布局摘要”验证投影授权。

最小未来改动应在**同一受管发布载体的专门定义验证与编译阶段**增加关系的显式许可、绑定输入及解析，不将recordIdentity伪装成node_patches.set.visible。复用现有view/定义版本和来源权威，增加精确有效布局身份绑定校验，输出当前唯一widgetRef。无须另建配置表/模型；但具体定义payload的批准结构需I1审查，不因本报告提到载体即获得新增字段授权。

nativeLocator、occurrenceIndex、fieldCode/节点类型与当前widgetId可用于校验；sourcePosition仅诊断。已存在的definition_sha256描述配置定义，lifecycle source/contract摘要描述源/交付，不等于已实现“绑定时的有效布局摘要”检查。必须将该检查做实，不能用其中任意一个哈希名称替代语义证明。

## 2. 验证、协商、旧投影与序列化能否按顺序完成？

**有可插入边界，但现有链不完整，且必须覆盖缓存早返回。**

当前链：`ui_contract_v2.handle` → `_handle_contract`（模型/动作/scene分支及源缓存）→ assembler →治理/记录/状态投影→validate_final_nodes→节点能力验证→`trim_unified_page_contract_v2`→validate_delivered_references→`seal_runtime_contract`→IntentExecutionResult→controller `request.make_json_response`。

关键分叉：

- handler约960行的assembled缓存命中直接seal并return，绕过下面普通组装段。
- 常规路径约1264–1349行执行节点校验、trim和seal；scene路径约3753行另有同类处理。
- 外层handle还做成功结果的节点能力检查，但此时已seal；不能仅在这里删字段却不重新封装摘要。

`core/unified_page_contract_v2_client.py:trim_unified_page_contract_v2`处理clientType/deliveryProfile及移动端数量限制，并非按accepted_contract_versions进行旧协议投影。已检索的ui.contract.v2交付链中没有发现所需的新旧格式选择器；发送accepted版本列表不构成实际协商证明。

`handlers/ui_contract_v2_authority.py:seal_runtime_contract`和`core/contract_lifecycle.py:seal_unified_page_contract`生成来源/发布引用、合同摘要、etag、snapshotId与观测记录。**封装摘要不是目标JSON Schema校验**；该路径没有提供本关系按协商版本的最终schema验证。正式schema是 `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json`，不是可随意改写版本字符串的模板。

建议I1交付统一的版本化finalizer边界：先完整验证源关系（非法关系不因旧客户端而略过），再协商/旧投影，再校验该目标版本的schema与交付引用，再seal最终字节对应的结构；更新pageInfo、lifecycle definition及外层meta的版本/摘要一致性，最后controller序列化。所有正常/缓存/scene返回必须进入同一保证，不应复制三套不同规则。若保留缓存预封装，协商影响后必须使旧摘要复用失效。

## 3. 是否有真实可固定的旧Web decoder？

**有。** 固定整个源码提交 `44e7e8447a77ff347ac2cdaf25d8c28b759e61ff`，入口 `frontend/apps/web/src/app/contracts/v2/schema.ts:decodeContractV2Snapshot`；该文件Git blob为 `e7a15c6dd66cee05eed4ad09d08c3d968a424099`。不能只拷贝此文件：它依赖legacyLayoutNormalizer、formStructureRoles、nodeComponentPresentation及@sc/schema，必须固定同提交的依赖图、workspace锁文件和fixture。

既有 `verify.frontend.contract_v2_runtime_policy.unit` 与 `verify.frontend.contract_v2_occurrence_authority.unit` 直接加载真实decoder；本轮均运行通过，日志 `.runtime/fepc13i00/decoder-baseline.log`，含非零case输出（runtime policy主组6、preview2、published ref3；occurrence的native context4、required coverage7、selected identity7等）。这些是已有基线测试，不是新关系兼容证明，不汇总成未由runner输出的总测试数。

严格行为已由源码确认：rejectUnknownKeys、外层版本正则、structureVersion枚举和navigation仅title。后续必须用固定旧decoder跑**新服务端真实生成的降级payload**，而不是只手工写一个旧fixture。误发新字段/新版本的负例必须拒绝。通用contract_version_compatibility.py允许未知key，不能替代此decoder。

## 4. 缓存与patch是否已足够？

**部分缓存隔离已有基础；新绑定和patch证明仍有缺口。**

`utils/load_contract_response_cache.py:build_projection_cache_key`包含namespace/db/uid/role/company/allowed_company_ids/lang/tz/model/view_types及剔除请求时间等运输字段后的params，因此目前请求中的版本与能力列表可以进入该key，并非完全缺少能力隔离。

但`projection_base_params`刻意移除record_id/active_id等，create/preview等走动态路径；handler通常只为无记录且非create的情况存assembled切片。必须保持这一结构缓存/记录overlay分界，不能把recordIdentity的实时值或是否为空缓存进跨记录基础结果。

`assembled_snapshot_gate_matches`额外只检查cache_version/client_type/delivery_profile/limit_params和结构存在；它依赖外层cache_key，不独立证明新版本绑定。必须为新交付投影加入有效定义/布局身份及协商输出的依赖保证，或保持基础缓存纯粹并在每次返回重新finalize，不能仅修改该gate的字符串版本。

source_token已有视图/模型字段/动作/权限/用户等来源变化与代码指纹，并对业务配置绑定definition_sha256/version_no/status/active等。但源失效token不是原生occurrence绑定授权证书；仍需在当前有效布局验证精确绑定。缓存测试应覆盖A→B→A定义变化、继承节点移动、不同record、角色/公司/profile、能力/版本交替和缓存命中早返回。

assembler的onchange转换（`assemble_unified_page_patch_v2`相关代码，约790–829行）生成layoutPatch/statusPatch/dataPatch/runtimePatch和以patch内容计算的etag/snapshotId；这是补丁自身身份，未见base快照+有效layout/binding一致性证明。不得把snapshotId字段存在当作base校验已实现。v1应禁用携带新关系的未证明patch路径并要求全量契约刷新；若未来允许仅数据patch，必须另证base与绑定不变及原子更新。旧表单patch行为不因本任务擅自改变。

## 5. 最小拆分与阻断项

| 状态/缺口 | 归属及解除条件 |
| --- | --- |
| 未正式批准候选协议标识 | 进入I1前显式批准实施范围和协议版本；本PR不升级标准 |
| 定义载体有基础但无身份关系/完整布局锁 | I1a扩展同一载体验证、精确引用编译与负例；默认不输出新关系 |
| 无完整协议协商/安全旧投影/目标schema验证 | I1b覆盖所有返回路径、最终seal及真实旧decoder测试；保持发布禁用直到端到端准入 |
| patch缺base/layout/binding证明 | 新关系v1走完整刷新；不得删除兼容要求以接纳旧patch |
| 前端尚无新类型/解码/可访问消费 | I2独立PR；完成前生产客户端不能宣称新能力 |
| 隔离集成与回滚未验证 | I3独立验收；不对Demo临时配置启用 |

结论不是“设计无法兼容”，而是“兼容必须由上述新增验证与交付机制证明”。任何I1b关键分支不能形成合法旧payload，应报告阻断，不缩减旧客户端范围。完整任务顺序见下一文档。09-04仍未修复，F1继续待核实、暂不修复。
