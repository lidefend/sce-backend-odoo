# 下一轮前端收敛任务计划：FE-CONSUMPTION-CLOSEOUT-20261126

## 1. 状态、目标与启动边界

**状态：ACTIVE。所有者已明确启动，当前在合格主线上执行 FC-00。**

本计划编制时读取的候选是 `e62a4b5dcdf726b3c15292cddde185925b0d5725`（PR #1013）；它是规划参考，不是已通过全量资格的主线基线。当前主线 CI 收口继续遵守所有者“暂停等结果”的指令；写入本计划不触发提交、推送、合并、部署、数据库操作或新一轮验证任务。

下一轮的产品结果：**用户面对场景化业务，在公司和项目上下文内，通过统一前端完成查询、录入、关联、审批、批量办理和导入；前端完整消费后端契约，不能替后端补权限、规则或业务含义。**

正式启动须同时满足：

1. 所有者明确启动本专题，解除“只计划、不执行”的限制。
2. 当前 CI 收口完成，重新读取已合格的最新 main，绑定精确 SHA、Base 和受影响输入；不沿用本文候选的 CI 结果。
3. 复用现有登记的工作树及运行环境，建立本专题唯一 run；本次不激活新 run、不替换当前分支的 CI run 绑定。
4. 执行 FC-00 时复用第 2 节现状核对，补齐动态与运行态证据后固定当前产品事实集合、已有证据及真实缺口。旧任务的 `planned` 或 `verification_pending` 标签不能直接视为当前代码缺失。

本次写入属于 P4 任务规划。未来实现的主要归属是 P0 通用前端消费与表现机制；P0 后端契约机制、P1 行业配置缺口按事实归属修复，不能藏进前端。P2 客户规则、P3 企业配置事实保持各自权威。

## 2. 已知输入与需要重新证明的部分

| 规划输入 | 当前能确认的事实 | 不能据此声称的结果 |
| --- | --- | --- |
| 当前 decoder、types、occurrence 回归 | 页面协议仅接受当前 2.7；已清理不用的旧身份分支、根别名读取；存在旧协议拒绝负例 | 全部业务入口已完成真实办理验收 |
| `frontend_contract_basis_ledger.json` | 当前登记的 `openContractDefects` 为空 | 未登记缺口不存在，或运行态已无前端推断 |
| `component-driver-takeover-inventory-v1.json` | 当前摘要记录 33 个 required drivers，missing/adapter_unconsumed 为 0；另有 2 个 bridge behavior bypass 记录 | 静态归属等于实际交互正确，或这 2 个记录天然就是缺陷 |
| `NativeImportWizard.vue` 与 `api.data.import` 验证入口 | 已存在用户导入向导和后端映射能力 | 每个可创建的数据面均已完整开放导入、错误修正与结果回读 |
| 企业角色和 recordset 改造 | 前序工作已建立相关模型及契约执行路径 | 本轮规划已独立证明其跨公司与真实浏览器闭环 |
| `FE-CONVERGE-01`、`FE-CLOSE-01`、`FE-CONTRACT-FIDELITY-02` 与组件完成计划 | 可复用责任分类、历史问题及测试资产 | 可以按旧数量、旧状态或旧协议设计重新实施 |

本次是有限源码与计划核对，不是新的全量产品审计。上述数量仅描述所读文件，不作为未来验收阈值。

旧计划中“后端下发 componentKey”、旧协议兼容、固定提交数、普通迭代强制全量 Quick、固定两条浏览器旅程等表述，**不作为本轮执行约束**。遵守所有者最新裁定与当前架构：后端声明业务语义，前端在既有组件注册机制中解析实现身份；只接受当前页面契约。独立子契约的当前版本不因数字不同而被当作旧页面兼容删除。

### 2.1 当前前端主链路：已有底座，禁止另起一套

此次进一步按候选源码读取了路由、契约客户端、数据 API、动作编排、导入向导、值格式化、上下文与关系请求控制，并对 `src` 下直接网络请求和旧导入函数调用作了文本核对。没有启动新测试或浏览器。结论分为源码事实和行为待证，不将静态观察冒充已复现故障。

| 环节 | 当前实现与源码锚点 | 收敛判断 |
| --- | --- | --- |
| 入口 | `src/router/index.ts`：场景 `/s/:sceneKey`、菜单 `/m/:menuId`、动作 `/a/:actionId`，记录 `/f/` 与 `/r/` 均进入 ContractFormRoute；SceneView 还可嵌入 ActionView/ContractFormPage | 多种入口不等于多套引擎。下一轮须验证同一动作/记录身份跨入口一致，不能删除合法场景入口来做表面统一。 |
| 契约加载 | `src/app/contracts/v2/client.ts`：`ui.contract.v2` → `decodeContractV2Snapshot` → `createContractV2Store`；声明 `2.7.x`；创建缓存 key 含数据库、token、context epoch、请求参数，复用受 runtime contract 控制 | 已有统一加载/缓存机制，保留。重点是调用方上下文完整性、失效与返回后是否仍归当前页面，而非重写 loader。 |
| 业务请求 | `src/api/intents.ts` 的 intentRequest/intentRequestRaw 使用 `/api/v1/intent`；`src/api/data.ts#importRecords` 使用 `api.data.import` | 本次抽查的导入和主业务链已经走意图通道。不能把“所有业务调用均已全面证明”写成既成事实。 |
| 公共认证 | `src/services/accountActivation.ts` 存在直接 fetch，调用 activation/password-recovery/page-contracts 公共认证端点；另一个直接 fetch 位于通用 API client | 当前确实存在公共认证协议入口。须单独登记并裁定其与“唯一执行通道”的边界，不擅自当作豁免，也不因关键词把未登录引导当成普通业务绕行删除。 |
| 组件体系 | `@sc/ui`、已有 design-system 包装、primitive/adapter/composite 与生成注册资产已经存在；driver 清单没有 missing/adapter_unconsumed | 保留现有组件底座，收敛真实消费者和交互状态；不能再造统一组件层或仅以静态登记清零验收。 |
| 关系异步 | `useRelationRuntime.ts` 已有 generation、request owner、searchGeneration 和 disposed 控制；`contextEpoch.ts` 有共享请求身份/取消机制 | 不是“没有异步隔离”。复用机制，查未接入或生命周期不闭合的调用端；保留已有迟到响应回归。 |
| 全局取消 | `api/client.ts` 的 fetch 默认消费 `currentContextSignal()`；会话/公司切换路径已有 context 更新 | 导入风险不能描述为完全没有取消能力；需验证自带 signal、响应已返回、组件卸载及后续回调这些边界。 |
| 批量动作 | `useActionViewActionRuntime.ts`：多选没有 recordset 声明即报契约缺口；recordset 使用 `[execIds]` 形成一次请求；collection capability resolver 按声明 scope/intent 映射执行器 | 批量主执行机制已存在。下一轮查事实配置是否声明、每项动作是否实际进入该通道、结果计数及失败/审批语义，不能重新实现 N 次单条循环。 |
| 原生导入 | `NativeImportWizard.vue` 已有 describe/inspect/validate/execute，原生字段/解析选项/映射、模板、导入兼容更新导出、错误消息和结果；ActionView 通过 collection runtime 打开 | 不应安排“从零建设导入向导”。应验完整用户操作、所有适用数据面的声明覆盖、生命周期和错误重试。 |
| 业务值 | FieldValue/FormSection 已接入 `presentDeclaredBusinessValue`；`formatDisplayValue` 在有描述符时也委托该解释器 | 不能再把 formatDisplayValue 的所有调用判作第二权威；真正要核的是无描述符分支、值被字符串化及语义兜底是否进入生产业务面。 |

以上路径均相对 `frontend/apps/web/`。下表的“待证”不是可放行项，未来实施前必须给出证据或登记缺陷。

### 2.2 现状驱动的首批稳定性清单

| 编号 | 本次源码确认的现象 | 精确判断与下一轮处置 | 归属任务 |
| --- | --- | --- | --- |
| FE-S01 | `frontend_contract_basis_ledger.json` 明写扫描仅覆盖分页/取数规模类默认值模式；当前 openContractDefects 为空 | **覆盖边界已确认**。空台账和该守卫 PASS 不能证明语义推断清零。补“声明→消费者→负例”的矩阵，复用已有 declarationBindings，不能只加字符串守卫。 | FC-00/01/08 |
| FE-S02 | `utils/display.ts#formatUndeclaredDisplayValue` 仍有无字段描述的数组/关系样式/附件文本解释；有描述符路径已转交统一解释器 | **旁路代码存在，生产暴露范围待证**。逐一确认调用者输入，业务值必须有声明；确属纯文本/机制工具的保留受限用途和正反例，不一刀切删除格式化工具。 | FC-01/03 |
| FE-S03 | `businessValuePresentation.ts#formatBusinessPercentage` 无 digits 时使用 2 位最大精度；`resolveMonetaryScale` 无 digits 时可从货币代码经 Intl 得出精度；presentDeclaredBusinessValue 会调用这些函数 | **语义兜底分支已确认，上游是否保证声明完整需证明**。核对后端精度权威及所有调用者；适用业务值缺声明必须显式拒绝，不让默认格式掩盖缺口。 | FC-01/03 |
| FE-S04 | `FieldValue.vue` 的 attachmentLinks 直接解析 props.value，模板先于普通文本显示链接；`display.ts` 有附件字符串模式解释 | **按文本外观选择附件表达的源码路径已确认**。核实正式附件声明、普通字符字段与外部链接边界；补“普通文本不能因形似附件而获得附件行为”负例，迁回声明驱动消费。当前未执行浏览器复现，不宣称已发生越权。 | FC-01/03 |
| FE-S05 | `KanbanPage.vue#rowTitle` 从 titleField 回退到 name/display_name/id；formatValue 找不到 column option 时可进入无描述符格式化 | **回退链存在，触发条件待证**。确认 titleField 的声明与空态策略，证明合法空值、未知字段和关系值不被错误改名或裸露 ID；保留后端声明的标题策略。 | FC-03 |
| FE-S06 | `NativeImportWizard.vue` 与 `useActionViewCollectionActionRuntime.ts` 有本地 Promise、busy 和 await 后回读，但这些文件未直接接入 shared request owner 或卸载清理；底层 API 已有全局 AbortSignal | **生命周期证明缺口，尚非已复现串数据故障**。验证关闭/路由卸载/切公司、响应已完成后的旧回调、Promise 结算、busy 恢复及只刷新原所属页面；能复用现有 owner 就不新建一套控制器。 | FC-04/06 |
| FE-S07 | `actionViewCollectionCapabilityRuntime.ts` 仍导出 pickImportFile、executeActionViewCollectionImport 旧式预览确认流程；本次 src 和脚本检索未找到调用者，而生产 collection runtime 已使用 NativeImportWizard | **疑似无消费者旧流程**。实施时核对动态/外部导出及测试依赖后删旧入口与无用导入，不保留第二套导入流程；不能把这一辅助函数的测试当作产品向导验收。 | FC-06 |
| FE-S08 | ActionView 3764 行、ContractFormPage 2214 行、ListPage 2192 行、schema 3671 行、session 1981 行；已有 composable 拆分但核心编排仍集中 | **维护风险，不按行数判产品缺陷**。新增变化优先进入已有责任模块；仅在状态所有权、重复编排或不可测边界被证实时作局部分离，行为保持回归，禁止整轮“大拆文件”。 | 各任务/FC-07 |
| FE-S09 | 已有 2 个 bridge behavior bypass 登记，指向 NativeNodeComponent 的 alert 与 ProfessionalManyToManySelect 的 select | **已登记待裁定表面，不能自动等同于错误**。核对是否消费完整状态/键盘/清理机制，选择保留有依据复合组件或归入既有 driver，不仅修改清单标签。 | FC-07 |
| FE-S10 | 历史计划仍宣称必须传播后端 componentKey、旧设计状态未同步；本轮 CI 曾漏选源码摘要依赖，现候选已补声明依赖和负例 | **规划及验证一致性风险已确认**。只沿当前协议做验收，不恢复旧兼容。矩阵/样本/摘要/选测同时随受影响源码更新；当前候选 CI 完成前不视为合格主线。 | FC-00/01/08 |
| FE-S11 | router 中仍有独立公共认证请求路径；主业务意图通道与该路径职责不同 | **执行边界须明确**。平台侧核实未登录阶段的协议入口和授权事实，给出保留受管认证入口或统一到既有通道的明确方案；不由前端自行造第三条路径。 | FC-01 |

**据此收窄实施策略：**第一批先锁住 FE-S01～S05 的语义输入与消费、FE-S10 的验证依赖；随后处理 FE-S06/S07 的导入生命周期与遗留流程。导航/企业角色/批量能力按现有实现做配置完整性和行为验收，不预设重写。视觉与文件结构整理放在权威和生命周期稳定后，不能反过来以 UI 统一掩盖事实不一致。

FC-00 未来应复用本节已完成的源码核对，只对新主线差异、未解析的动态调用与运行态事实补查，不重新扫描全部历史任务。首轮目标是关闭这些具有源码锚点的问题或待证边界，再扩展当前事实矩阵暴露的新问题。

## 3. 冻结的职责和产品边界

| 主题 | 本轮遵守的规则 |
| --- | --- |
| 唯一事实链 | 原生视图及配置事实 → 后端解析、权限裁剪和契约生成 → 严格解码 → 既有统一运行时和组件消费 → 用户行为与后端回读。验证重点是我们的组合、生成和消费，不是重测 Odoo 引擎本身。 |
| 唯一执行通道 | 页面、按钮、向导、导入和批量写入均经现有意图请求路径进入 handle 执行链；不新增业务 RPC、直连 ORM 或绕过服务的写入通道。下载等已登记传输机制仍须有后端授权，不扩展成第二条业务执行链。 |
| 缺失声明 | 有可见、可定位的契约缺口状态；修复所属 P0/P1 声明后再消费。前端不得按模型、字段名、按钮文案、角色码补业务默认值或猜权限。 |
| 权限与入口 | 后端给出可访问结果；具有只读权限应有入口，空数据不等于无权限。完全无可访问内容的入口不应投影；父分组按有效子入口投影。不得以列表长度推断授权。 |
| 动作可用性 | 授权不足与业务条件不满足分别声明。正常情况下不能先提供无权限入口、点击后才告知无权；过期会话、并发撤权及公司切换中的权限变化由后端拒绝，前端及时刷新并清楚反馈。 |
| 公司与项目 | 集团内公司同样公司级隔离；公司、项目与用户有效授权上下文均来自后端。切换上下文不得携带旧请求、旧选择、旧缓存或旧可执行动作。前端隐藏不是安全边界。 |
| 审批 | 权限决定能否执行，审批规则决定如何推进；无规则由统一机制自动通过。有规则时待审批尚未生效，取消不得改变有效权限；已生效后的撤回便利操作是另一次受控设置，不把它伪装为取消。 |
| 企业角色 | 用户面对职责与能力组合、变更影响和生效事实；版本、来源与快照用于后端审计。发布不暗改现有授权，迁移、撤销按来源重算，前端不暴露底层组拼装。只使用已准入能力，不趁 UI 收敛扩大能力目录。 |
| 原生能力 | 优先完整交付 Odoo 原生向导、导入、数据管理与权限执行结果；只有确认现有机制无法表达时，才提出最小通用增强，不改原生机制。 |
| 初始化与菜单 | 平台可统一的标准配置由初始化提供，同时保留合法的管理员调整能力。产品配置与业务场景同层；场景结构锁定，菜单来源、收录及顺序来自配置事实，初始化引用正确；禁止前端固定菜单名单或数量。 |
| 开发期清理 | 不建设旧页面契约兼容或旧数据迁移包袱；不等于允许未确认删除持久库。一次性测试和持久环境依照现有受管授权分别处理。 |

不新增第二套页面引擎、权限引擎、值解释器、审批引擎或并行组件目录；不以大规模换 UI 库、文件拆分数量或代码行数作为收敛目标。

## 4. 工作包、顺序与退出条件

所有工作包初始为 `planned`，每项都先复用当前能力，只修经过证据确认的差距。由同一执行者统筹，按依赖顺序实施；独立纯检查可批量执行，不派生多个产品事实源。

| ID / 优先级 | 工作包与具体范围 | 依赖 | 必须交付的证据和退出条件 |
| --- | --- | --- | --- |
| FC-00 / P0 | **当前事实与缺口基线**：从正式菜单、场景、动作、视图、能力和现有登记表推导入口集合及消费路径；逐项核对历史问题是否仍存在；盘点主路径和旁路 | 合格 main + 启动授权 | 唯一覆盖矩阵；每项标为已证明、待验证、确认缺陷或有理由的不适用；绑定来源文件/事实 ID、消费者、测试入口。不能抄旧数量，也不能把 NOT_VERIFIED 写成 PASS。 |
| FC-01 / P0 | **契约生成—消费一致性**：根对象、字段/列出现身份、动作身份、结构/状态/数据/运行时载体、原始值与描述符完整性；旧兼容和隐式兜底逐点退出 | FC-00 | 正例跑真实生产者或其权威输出到真实 decoder/store；负例覆盖丢字段、错身份、旧协议、非法语义及未经声明的动作。确认缺口在所属声明层补齐，前端不能自行恢复。 |
| FC-02 / P0 | **导航、产品配置与授权呈现**：场景投影、初始化引用、配置入口完整性、办理顺序、深链接、面包屑、公司/项目上下文、只读与无权限表现 | FC-01 | 正式配置事实与投影集合逐项一致，无重复/遗漏/硬编码名单；只读空列表入口可达，无权入口不投影；合法直达可打开，伪造/过期请求后端拒绝；公司切换不复用旧授权。 |
| FC-03 / P0 | **查询、列表和表单的值与状态一致性**：查询/排序/分组/分页、列配置、只读详情、创建/编辑/保存、dirty state；金额/比例/时长/日期/时区/selection/relation/附件语义在不同表面保持同义 | FC-01、FC-02 | 相同事实跨表面解释一致；0/false/空值/负数不混淆；未知 selection、不完整关系/货币/时区声明明确失败；显示文本不写回业务值；失败保留草稿，成功回读服务器事实。 |
| FC-04 / P0 | **关系字段、明细与异步生命周期**：many2one/many2many/one2many、内嵌向导、分页查询、domain/context、onchange、行身份、附件请求与资源释放 | FC-03 | 迟到响应不能覆盖新记录/公司/项目/查询；关闭或卸载后不提交结果；连续增删改不串行身份；只读与不可见状态忠实消费；保存 payload 与回读精确对应，错误可修正。 |
| FC-05 / P0 | **动作、审批和批量办理**：表头/行/详情/溢出菜单动作一致，单记录/recordset 执行范围、确认、进度、失败反馈、批准后刷新；含企业角色管理办理 | FC-02、FC-04 | 有声明且有资格才出现对应办理能力；recordset 一次声明范围的一次请求，不隐式 N 次单条循环；后端逐记录复核；审批中不冒充生效，无规则按统一机制生效；角色新增、迁移、撤销有来源回读，保留其他授权。 |
| FC-06 / P0 | **原生导入向导完整交付**：从所有可新建数据面推导导入覆盖表；上传、预览、映射、选项、校验、确认、执行、错误定位修正、结果回读；至少覆盖配置主数据与角色分配 | FC-05 | 用户实际操作产品向导完成导入；创建能力不自动等于导入授权，缺口回到契约/权限事实处理。每个适用创建面有明确导入可达性；业务上不适用的对象有显式依据。验证重复、必填、关系匹配、类型、无权字段、跨公司数据、错误重试，不以脚本直接写库代替。 |
| FC-07 / P1 | **公共表现、可访问性与性能**：复用现有 primitive/adapter/composite，统一标题/动作区、列表/表单密度、loading/empty/error/disabled/保存反馈、焦点/键盘、响应式、请求/渲染开销 | FC-02～FC-06 对应功能成立 | 对两个 bridge bypass 及其他当前盘点项逐项裁定保留或归一，不能只把计数改成 0；1440/390 代表表面无非预期横向溢出和遮挡；键盘与焦点回归；同条件请求数和耗时无无解释退化，禁止靠丢数据/权限检查提速。 |
| FC-08 / P0 | **真实用户闭环与清理封板**：按事实矩阵覆盖配置管理员、业务经办、只读用户及公司/项目边界；删除已替代路径、无用 fixture/过期规则，核验生成证据、选测和当前主线资格 | FC-00～FC-07 | 所有适用单元有证据，无阻断缺陷、无未归属旁路、无未解释的 NOT_VERIFIED；定向、远端 PR 与新主线全量各自合格；运行环境、候选身份和未覆盖项明确，不能把 CI 等同于部署或全部业务验收。 |

建议以“可独立验收、可独立回滚的产品结果”组织 PR：FC-00/01、FC-02、FC-03/04、FC-05/06、FC-07/08 为初始分组。FC-00 后按实际依赖调整；不为满足固定 PR 数量或提交数拆分。涉及 P0/P1 的修复按归属分提交，验证仍围绕同一用户结果，不另造环境。

### 后端缺口处理规则

每个确认缺口登记 `BE-<工作包>-<序号>`，包含：声明责任层、原生事实来源、错误契约样本、实际消费者、最小修复、正负例、影响集和阻断的前端单元。处理顺序为声明修复 → 生产者定向验证 → 同 run 后端回执 → 消费回归 → 用户行为证明。

契约已足够而前端丢失/改写的，只改通用消费者；标准初始化、菜单组织或行业默认缺失的，归 P1；企业自定义事实缺失的，不用平台硬编码替代。不因“前端专题”把后端真实缺口留作无主事项，也不扩大到与用户结果无关的原生机制改造。

## 5. 验收矩阵与真实办理旅程

### 5.1 覆盖模型

唯一矩阵以正式事实生成，不维护另一份手写菜单或角色目录。每个单元至少记录：

`入口/场景事实 → 原生 Action/View → 当前契约与 source authority → 实际消费者 → 用户/公司/项目/状态 → 预期行为 → Make/浏览器证据 → 源码与环境身份 → 结论/缺口归属`。

自动配置与契约核对覆盖全部正式入口；运行态按入口类型、动作执行范围、权限状态、数据类型和组件消费路径划分等价类。每个新增/变更或独特路径必须有行为证明，不能用“代表页通过”覆盖未证明的不同路径。代表旅程数量由矩阵决定，不预先限制为两条，也不每次微小修改重跑全角色×全页面笛卡尔积。

### 5.2 必须覆盖的旅程

| 旅程 | 用户操作 | 关键判定 |
| --- | --- | --- |
| J-01 初始化到配置可用 | 配置管理员进入产品配置，查看初始化已提供的标准数据，再维护允许调整的业务配置 | 层级与排序来自事实；无重复配置负担；修改后前端展示与后端事实一致 |
| J-02 查询到办理再回读 | 经办从列表筛选/分组进入记录，修改含关系和明细的表单，保存并返回列表 | 原始值、记录身份、分页/选择上下文正确；失败保留输入，成功刷新事实 |
| J-03 用户导入 | 管理员在真实导入向导上传样本、映射、校验、修错、执行、查结果 | 不用脚本代办；错误行可定位；执行次数和提交范围符合后端契约；预览/取消不产生最终业务写入 |
| J-04 单条与批量审批 | 同一类事项按单条及声明的批量入口办理；分别覆盖无规则、有规则、拒绝/取消、并发变化 | 审批前未生效、取消无影响；审批通过再生效；禁止自引用审批造成配置治理死循环；部分失败/原子性由后端声明，前端如实表达 |
| J-05 企业角色授权 | 配置管理员组合已准入能力、发布、通过用户分配/导入分配、预览影响、按规则办理；目标用户重新登录；再变更、明确迁移、撤销 | 用户理解职责与生效事实即可；原分配不暗迁移；权限变化可追溯、Token Epoch/缓存变化正确；多来源授权不误删 |
| J-06 只读、无权限与隔离 | 只读用户打开无数据列表；无权用户导航及直接请求；多公司用户切换公司与项目 | 有读权限保留入口；无权不暴露入口；后端仍拒绝绕行；原生全局组不能被前端误当全公司业务授权 |
| J-07 异步、异常与可访问性 | 快速切换记录/公司、连续搜索、关闭附件/向导、重复点击、网络失败、会话过期；桌面/窄屏键盘办理 | 不串数据、不重复执行、不把旧响应写回；焦点可恢复、提示可读；无吞错或无依据的成功反馈 |

新的一次性库可在未来实施授权下复用受管机制：demo 作为配置参照，配置管理员通过产品操作形成等价配置及代表性闭环。脚本只负责受管环境、必要测试输入和只读回读，不代替用户配置、导入、授权与审批。此处是验收设计，本轮没有创建库或运行旅程；完整行业业务闭环仍不自动纳入本专题。

## 6. 验证、效率与证据机制

| 层次 | 未来执行责任 | 复用与边界 |
| --- | --- | --- |
| 当前规划写入 | 仅校验 YAML、任务依赖、文件引用与 diff | 不运行产品测试、浏览器、CI、构建或数据库操作；文档校验通过不代表产品验证通过 |
| 本地精准验证 | `make ci.local.iteration`，按真实依赖选择非零生产者/decoder/store/组件/动作测试 | 先廉价静态与纯测试，再受影响运行态；同层已知失败一次收集。引用的源码摘要、配置和生成器也属输入；失败/零收集/未知不能通过 |
| 后端影响 | 仅验证我们改变的契约生成与原生组合边界 | 改生产逻辑须保留受影响 owning-module 覆盖；完整模块集成下沉远端，不把 Odoo 原生机制单独设为本专题研发对象 |
| 前端行为 | 真实消费者正负例 + 受管代表旅程 + 后端事实回读 | 除确有隔离需要外复用环境。证据按实际输入、断言、上下文及环境身份失效，部署动作本身不自动使全部证据失效 |
| PR 集成 | 当前 HEAD 对当前 Base 的四项必需工作流及适用的后端收口机制 | 保留严格门禁；不拿旧 HEAD 成功顶替，不因纯文档/纯测试误触发无关 ORM，也不漏选真实依赖 |
| 主线发布资格 | 最终最新 main 的受管全量资格审计 | 与 PR、本地通过分开记录；不默认部署持久环境 |

优先复用以下已存在入口（只是后续候选，不是本次执行清单；FC-00 按影响选择并核对）：

- 契约：`verify.frontend.contract_fidelity.plan.unit`、`verify.frontend.contract_basis.unit`、`verify.frontend.contract_v2_occurrence_authority.unit`、`verify.unified_page_contract.v2.web_consumer`、`verify.unified_page_contract.v2.web_architecture`、`verify.contract.page_v1_zero_residue.guard`。
- 导航：`verify.backend.navigation_delivery.unit`、`verify.frontend.navigation_shell.unit`、`verify.frontend.navigation_policy.unit`、`verify.frontend.collection_navigation_controls.unit`。
- 表单/关系/动作：`verify.frontend.contract_record_action_state.unit`、`verify.frontend.professional_relation_field.unit`、`verify.frontend.professional_relation_lifecycle.unit`、`verify.frontend.relational_action_primitives.unit`、`verify.frontend.professional_workflow.unit`。
- 导入：`verify.smart_core.api_data_import.unit`，配合既有 NativeImportWizard 的实际消费与受管用户旅程；缺少前端定向入口时在该工作包补最小入口，不假称现有覆盖已足够。
- 表现与最终消费：`verify.frontend.systemic.convergence.static`、`verify.frontend.typecheck.strict`、`verify.frontend.pr.unit`、`verify.frontend.release.unit`；完整消费单元集用于合适的收口点，不每个小改动重复执行。

契约变化必须检查三件事一起更新：生产事实/消费者、受影响断言与样本、选测和回执依赖。守卫失败不得仅改字符串或数量消除；负例须证明实际突变能被抓到。生成证据在有可解释的源变化后刷新，不删除旧失败日志，不以新摘要改写旧候选结果。

## 7. 完成定义、风险与回退

全部满足才可称本专题“前端收敛验收完成”：

1. 当前正式事实集合全部有归属与覆盖结论，无未解决的授权/数据串扰/契约生成与消费阻断。
2. 需要声明的产品语义没有前端兜底；当前协议之外的页面输入被拒绝；组件实现身份归前端，无第二套事实链。
3. 已适用的创建、单条、批量、导入和审批路径可由真实用户办理，且写入、回读、界面一致；正常路径不出现“有入口但初始无访问权限”。
4. 公司/项目/权限变更与异步场景无越界或旧态覆盖；拒绝、取消、重复操作和失败重试都有可判定结果。
5. 公共表现与可访问性通过声明的表面和状态覆盖；性能数据有固定条件，任何退化有归因及处置。
6. 当前候选所需本地、PR 与主线证据各自成立，原始日志和缺口关闭证据能从唯一 run 追到。

“机器缺口数为 0”“页面能打开”“单测全绿”“PR 已合并”都不能单独替代上述定义。无法证明的单元保留 NOT_VERIFIED 并阻止宣称全专题完成；不适用必须绑定产品事实，不能为了清零扩大排除范围。

主要风险及处置：

- **旧计划误导**：只继承仍成立的职责，不继承旧协议/数量/未更新状态；在新 run 登记复用、替代、待验证关系，保留旧历史事实。
- **界面掩盖声明缺口**：停止受影响单元，回到所属后端声明层；其他已独立成立的工作可继续。
- **误扩权限或能力目录**：本专题不新放行能力；若发现权限组合缺陷，按安全问题修复并补最小边界证明。
- **重复造轮子**：先证明原生及现有组件不能表达，再评审最小增强；不按页面分别建设导入/审批/批量引擎。
- **大改导致难以定位**：以独立用户结果分批，限制每批事实权威和环境，先修根因再更新快照。
- **回退**：以对应 P0/P1/P4 提交为单位回退；前端回退不得恢复已退役协议。涉及数据的未来变更单列受管恢复方案，不随 UI 回退暗改数据。

最终分别报告：批次验收、主线集成、部署、用户交付。未执行的部署和未覆盖的完整行业业务验收保持明确，不扩大本专题结论。

## 8. 任务领取和下次唯一动作

任务登记：`.agent/goals/FE-CONSUMPTION-CLOSEOUT-20261126.yaml`。本计划是唯一详细任务表，不再新建并行台账。

**下次唯一动作：获得实施指令并确认主线全量资格后，启动 FC-00，输出当前事实推导的覆盖矩阵和首批可实施缺口。** 本次不自动开始 FC-00，不修产品、不迁移数据、不合并当前 PR。

## 9. 开工准备包

专题运行记录：`.agent/runs/FE-CONSUMPTION-CLOSEOUT-20261126/run.json`；源码观察矩阵：同目录 `coverage_matrix.json`。运行记录保持 planned，预留分支尚未创建或绑定，当前 CI 任务绑定保持不变。

准备包包含 11 项源码观察及源文件摘要、9 个工作包的依赖、7 类用户旅程。源码观察不是全量产品覆盖矩阵，也不是行为通过回执；正式入口、视图和动作集合由 FC-00 从当前产品事实推导。

首批为 FC-00、FC-01：先确认守卫覆盖范围及证据依赖，再建立未声明值格式、数值精度、附件文本误识别和看板标题回退的区分性用例。对应 FE-S01/02/03/04/05/10。涉及展示层的修复归 FC-03，不能因首批建立用例就提前认定问题已关闭。后续处理导入生命周期、旧导入路径消费者、复杂编排、组件桥接及公开身份请求边界。

候选验证入口已登记在 run 的 check_candidates；它们仍为 not_run。业务值验证入口包含浏览器依赖，正式选测前确认环境和影响集。当前只验证准备包的结构、引用、摘要及任务台账，不运行产品测试。

开工顺序：

1. 按实施指令核对最新主线的全量资格，替换参考候选；只复核发生变化的源码观察。
2. 保全本次未提交的专题文件，完成当前 CI 任务交接后复用合规工作树，不覆盖原任务绑定。
3. 创建并绑定实际专题分支，冻结首批文件范围、检查入口和环境，再将 run 改为 active 并执行 `make agent.run.resume`。
4. 输出事实覆盖矩阵及首批负例，先证明生成声明，再证明前端消费；仅对确认的缺口实施所属层修复。

准备完成不等于实施开始。当前候选 SHA 只是源码观察参考，不作为已合格主线或产品验收证据。

### 2026-11-27 激活记录

所有者明确要求按本计划在全新主线开始前端收敛。专题已从已通过六项完整审计的
`a92114f0efb6733253d827e3a9985af21ab96be6` 创建受管工作树和分支
`fix/fe-consumption-closeout-20261126`，准备包四项文件保持原摘要迁入。当前只进入
FC-00/FC-01，不继承规划参考候选的 CI 结论，不写数据库、不部署、不发布。

### 2026-11-27 FC-00/FC-01 首批本地切片

合格主线上重新核对了准备包所列 11 个源码观察的文件摘要，全部未变化，因此没有重扫
历史任务或重建环境。首批只处理已由源码和区分性用例同时确认的声明消费缺口：

| 事实链 | 修复 | 证据 |
| --- | --- | --- |
| 业务值必须有字段描述符 | 无描述符不再按值外形格式化，直接抛 `ContractGapError`；普通字符字段形似附件引用时仍按原文显示 | `verify.frontend.business_semantics.unit`，TAP 1 + unittest 21 |
| 金额与比例精度必须声明 | `presentDeclaredBusinessValue` 对 money/percentage 要求合法 `digits`；百分比缺精度不再默认两位，也不再从币种代码猜金额精度 | `verify.frontend.business_semantics.unit`、`verify.frontend.professional_business_value.unit` |
| 附件行为必须有声明身份 | V2 store 保留 `attachmentRole`，列投影保留 `relation`/`attachmentRole`；`ir.attachment + attachmentRole` 才启用链接，普通文本和普通字段不获得附件动作 | `verify.frontend.contract_shape_projection.unit` 25 cases；`verify.frontend.collection_row_cell.unit` 9 tests |
| 看板标题来自 `title_field` | 标题只消费声明的 `title_field` 与字段描述符，删除 `name/display_name/id` 回退 | `verify.frontend.collection_kanban_record_card.unit` 11 tests |

受影响的既有集合消费链也通过：`verify.frontend.collection_view_semantics.unit` 82 项、
`verify.frontend.contract_basis.unit` 15 项；`ci.local.iteration` 的 lint、严格类型检查、
治理检查及选中目标全部退出零。使用临时非秘密构建配置执行 `verify.frontend.build`，
生产结构构建成功并生成指纹
`48d42a5d27f60a958bd51cedff19b1a73ac113d826648e8873232d4b59c7e040`。

当前结论只属于本地精准验证和组件运行时观察。真实菜单/角色业务旅程、完整正式入口矩阵、
远端 PR CI、主线资格、部署和产品交付均未完成；FE-S01 的语义覆盖全集、FE-S10 的完整选测
依赖以及 FE-S06～S11 仍保持待验证。下一步应继续 FC-00 的正式入口/动作/视图推导，并把
FC-01 扩展到其余生产者和未消费声明；形成可独立验收的产品结果后再提交干净候选。

### 2026-11-27 FC-00 正式入口矩阵与 FC-01 边界扩展

继续核对时，正式入口 universe 守卫首先失败：当前场景组织和正式产品策略已经是
**143** 页，验收 CSV 仍停留在旧 **132** 个 action 单元，缺少 AUTH-02 新增的 11 个产品
配置入口。该差异发生在当前前端改动之前，分类为 `baseline_evidence_defect`。

处理只修改 P4 验收声明，不改产品语义：

- 从当前正式策略、场景组织和原生 view/action 声明补齐 11 个产品配置入口；
- 新增入口全部标记 `pending`，不继承任何历史通过；
- 将 universe guard 的期望从 132/131 更新为 143/142；
- 校验结果为 143 个场景页、142 个 action 行、1 个 scene 行，无 missing/extra；
- 在 run 的唯一覆盖矩阵中逐项写入 143 个 `menu_xmlid`、action/carrier、模型、声明的
  query/write 责任、声明消费族、来源行摘要和当前运行态状态；当前运行态统一为
  `not_run_current_candidate`。

同时关闭两项 FC-01 边界：

- FE-S10：`verify.frontend.dev.incremental.unit` 280 项通过，证明当前声明和守卫变更会触发
  universe/evidence-scope 选择；`verify.frontend.business_entry.evidence_scope.unit` 201 项
  通过，覆盖复用、失效、路由与观察绑定；
- FE-S11：平台冻结文档明确规定 activation/recovery bootstrap 是绑定专用 adapter 和精确
  route 的唯一例外，不能扩展为 `/api/v1/auth/*` 通配；`verify.frontend.intent_channel.guard`
  8 项通过，业务 intent 仍统一走 `/api/v1/intent`。

FC-00 至此完成“从当前正式事实推导唯一入口矩阵”的职责。当前运行态仍未执行：143 个单元
均没有本候选的页面、角色、公司或业务旅程回执，因此不得引用历史 143/143 结果。FC-01 的
语义覆盖全集和后续 FC-02～FC-08 继续推进。

### 2026-11-27 FC-01 声明→消费→停机绑定扩展

`frontend_contract_basis_ledger.json` 新增三条真实绑定，不再只依赖字符串守卫：

| 语义面 | 声明站点 | 消费与停机 | 负例证据 |
| --- | --- | --- | --- |
| 金额/比例精度 | `unified_page_contract_v2_assembler._strict_field_descriptor` 发布 `digits` | `businessValuePresentation.requireDeclaredBusinessDigits`；缺失/非法抛 `contractGapError` | `verify.frontend.business_semantics.unit` 22 项 |
| 附件关系身份 | 同一描述符投影发布 `attachmentRole` | V2 decoder 对 `ir.attachment` 缺角色报 `FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED` | `verify.p0_contract_producer.p0a.unit` 72 项 |
| 看板标题 | `load_contract._extract_kanban_semantics` 发布 `title_field` | `presentCollectionKanbanTitle`；缺字段或描述符抛 `contractGapError` | `verify.frontend.collection_kanban_record_card.unit` 11 项 |

`verify.frontend.contract_basis.unit` 通过，当前为 24 个 declaration bindings、9 个机制豁免、
3 个受登记逻辑站点、0 个未闭合契约缺陷。该扩展仍未证明全仓所有语义消费面已覆盖；
FE-S01 继续保持阻断，直到完整语义矩阵完成。

### 2026-11-27 切换到隔离 clean 开发库

所有者要求后续开发只使用干净库。当前 `sc_clean` 原状态不健康：默认健康契约要求
`sc_norm_engine`，但模块未安装且 `sc_norm_specialty` 关系不存在；clean namespace
也未建立。处理没有回退到 `sc_dev_demo`。

受管目标：

- `make local.clean.rebuild LOCAL_CLEAN_MODULES=smart_construction_bundle
  CONFIRM_LOCAL_CLEAN_REBUILD=REBUILD_ISOLATED_REHEARSAL`
- `make local.clean.install LOCAL_CLEAN_MODULES=sc_norm_engine`
- `make local.clean.entry_identity.ensure`

最终 clean 身份：

- project `sc-local-clean`，database `sc_clean`，dbfilter `^sc_clean$`；
- 三个专属卷 `sc_local_clean_{db,redis,odoo}_data`；
- `SC_ALLOW_DEMO_DATA=0`，无 fixture/客户数据；
- 模块 `smart_construction_bundle`、`sc_norm_engine`；
- backend source revision `7293a927e99254c5a9bff522fe520b61cb67dde6`；
- namespace `clean` / `ns_c6fed472e939`；
- frontend build fingerprint
  `d7aca7a969c082a96cdcca68501a31ece7c8d8e678a6179089b632a189c6c6f9`。

`local.clean.health`、`local.clean.entry_identity.verify` 和
`/t/clean/api/runtime-version` 均通过。该运行态属于环境与启动证据，不等于 143 个业务
入口的页面、角色或办理验收。

### 2026-11-27 FC-01 金额精度旁路与选测闭包

继续核对共享业务值权威时发现，上一轮“金额精度必须声明”的收口只覆盖
`presentDeclaredBusinessValue` 主入口；底层金额显示、输入值格式和输入步长仍可从
币种代码推断精度。该路径属于 P0 通用消费缺陷，代码会从正式契约缺口继续得到格式化
结果。

本切片只改声明消费层和验证工具：

- `resolveMonetaryScale`、`formatMonetaryDisplayValue`、`formatMonetaryInputValue`
  与 `monetaryInputStep` 全部要求合法 `digits`，缺失或非法即 `ContractGapError`；
- 币种代码/币种标签只保留为显示信息，不再参与精度推导；金额输入 API 删除币种参数，
  避免调用方误以为币种可以替代声明；
- “我的工作”金额事实缺少 `digits` 时同样停机，不再默认两位小数；
- 专业业务值控件、规范表单、明细行金额输入同步改为只消费声明精度；
- 负例覆盖通用金额显示、金额输入、输入步长、活动面金额和“我的工作”金额事实。

验证过程中同时修复两项 P4 漏选/误判：

- 共享业务值权威变化现在选中专业控件、规范表单、活动面、支付结算、层级工作台、
  列表、看板与行单元格这些直接消费者；
- `verify.frontend.action_surface_renderer_registry.unit` 改用 `node --test` 产生真实
  TAP 计数，并从“零引用待决目标”台账移除；业务断言和架构守卫未放宽。

最终 `make ci.local.iteration` 在明确 dirty scope 上执行 30 个目标、19 个测试目标、
703 个测试，全部退出零。原始回执：

`.runtime/frontend-dev-validation/executions/20261126T221548Z-508620-392256933/receipt.json`

回执 SHA256：
`5f1b2cb17f943681971243064839449ed4e95b57a55266d6e98aa001a3accb73`。

产品改动已提交为 `913de131b32bcf1c7788b2f4171581a0e937111f`。按该精确 SHA
重建 clean 前端后，生产结构构建通过并生成指纹
`f377fa7b8022e64c6e271ca42a7c107f537335642140640ac6d2d29a5a326aef`。

clean 运行态权威回读：

- `/t/clean/api/runtime-version` 同时返回源码
  `913de131b32bcf1c7788b2f4171581a0e937111f` 与前端构建指纹
  `f377fa7b8022e64c6e271ca42a7c107f537335642140640ac6d2d29a5a326aef`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter 仍为 `sc-local-clean` / `sc_clean` / `^sc_clean$`，
  namespace 为 `clean` / `ns_c6fed472e939`。

租户前缀 `/t/clean/build-info.json` 会回落到 SPA HTML，这是入口路由行为，不能当作
构建身份 JSON；本次已保留该诊断文件并用根路径 JSON 完成回读。

该证据只证明当前 clean 环境、构建和启动身份，不证明 143 个业务入口的页面、角色或办理
流程。远端 PR CI、主线资格、部署和用户验收均未完成。

运行态证据回填后，又在 clean HEAD `c9cab224d0fc0c075ad20e89f7c92ff7bf1b635d`
执行一次 `make ci.local.iteration`：36 个必需目标全部有通过结论，其中 12 个本轮实际执行、
24 个按未变输入复用；本轮实际执行测试 402 项，退出零，`outside_scope=[]`。回执：

`.runtime/frontend-dev-validation/executions/20261126T222229Z-553917-405463817/receipt.json`

回执 SHA256：
`14484d21c4915ef16da422bca5c255259d8b91926d96cb4f2f19609b55d602a5`。

此后只允许修改 run/文档并提交；若再改产品源码或验证依赖，必须重新建立当前候选证据。

### 2026-11-27 FC-01 temporal 声明消费收口

继续检查字段语义时确认，P0 已发布 `fieldDescriptor.temporal.kind` 与
`timezoneAuthority`，V2 解码器也要求该声明；但业务值展示没有携带 temporal，
`formatTemporalFieldValue` 还会把 `00:00:00` 的 datetime 按值外形降级成日期。
这属于“契约已声明、前端未消费”的 P0 通用消费缺陷。

本切片完成：

- date/datetime 业务值必须携带与字段类型匹配的 `temporal`；缺失或冲突抛
  `ContractGapError`；
- datetime 不再按午夜值推断日期类型，午夜仍输出时间；
- `timezoneAuthority=user` 从应用运行时用户时区转换；`record` 权威缺少
  `recordTimeZone` 时停机；
- temporal 元数据贯通 V2 字段描述符、规范表单、列表、看板、活动面、主从明细、
  页面块指标和“我的工作”；
- 增加缺失 temporal、kind 冲突、午夜、UTC→Asia/Shanghai 转换和记录时区缺口的
  区分性用例；
- `frontend_contract_basis_ledger.json` 新增 temporal 的声明→消费→停机绑定；
- 删除已过期的 business-value split allowlist 项，因为按值外形拆分的路径已退役。

`make ci.local.iteration` 在 `f666e67dc2897bd2e273c82657d0a7560d95cd00`
加当前 owned dirty scope 上执行 18 个目标、复用 27 个未变目标，本轮执行 524 项测试，
全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261126T224248Z-684804-543451597/receipt.json`

回执 SHA256：
`d13b72fed3fc8d102fde5080794ce51f07bf324e707920908d46a3aa3af08faf`。

产品改动提交后必须按新精确 HEAD 重建 clean 前端与 Odoo 容器；当前运行态仍属于上一
产品候选。远端 PR CI、主线资格、部署和用户验收均未完成。

产品改动已提交为 `c73bb6d0f504ceaed507befc2472313d11f06689`，随后按该 SHA
重建 clean 前端并用 `046332dc0f6f6ad74e6e29a37b9bf0ce2c726c6a600c5201e158f68eb5c8ee14`
构建指纹重建 Odoo 容器。回读结果：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA 与构建指纹；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health`、`local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 仍严格为 clean 专属身份。

在该 clean HEAD 上再次执行 `make ci.local.iteration`：45 个必需目标全部成立，其中
15 个本轮执行、30 个按未变输入复用，执行测试 439 项，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261126T224644Z-712232-380062170/receipt.json`

回执 SHA256：
`11a29f38df92e13a0667e712f166e6dee60de781ff40d9550e4b0e803d2cc2ec`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。

### 2026-11-27 多态引用缺口并线后的 clean 精确候选复验

此前待审核的后端缺口不是权限、数据库或通用关系渲染能力，而是主线的最终 V2 字段描述符
丢失了 Odoo 原生 `many2one_reference` 的模型指针声明。原生生产者已经解析出
`model_field`，但 `_strict_field_descriptor` 没有把它作为 `referenceModelField` 送到最终
wire contract；同时前端 decoder 把 `many2one_reference` 与 `many2one/one2many/many2many`
一样要求固定 `relation`。真实契约因此会在严格解码阶段停机，无法进入通用渲染。

该缺口已由最新主线 `bfc954c0b6fe2bbaa5a94c017ef8c69ec983d9a5`（`Merge PR #1018`）
同时解决：

- 严格生产者保留并校验 `referenceModelField`，不再从最终边界重建或丢弃原生模型指针；
- 前端 decoder 对 `many2one_reference` 要求该字段，并把固定关系字段类型单独处理；
- schema、真实 contract 解码、缓存版本失效和增量选测已接入；
- 固定 relation 与多态 reference 保持不同语义，`reference` 原生值仍可保留自身模型身份。

本专题通过受管 `make workspace.branch.sync-main.extended` 将 22 个本地提交重放到该主线，
产品冲突为零。没有在本专题修改任何后端文件；主线修复属于继承输入，不属于本专题后端改动。
`origin/main` 已确认是当前 HEAD 的祖先。`bfc954c0b` 只有合入事实和源码复核，没有对应的
全量发布资格回执，因此不把该候选写成 scheduled release qualified。

产品候选提交为 `309158b3b4a40db001cfa54c3493f937022561c1`。按该精确 SHA 重建
clean 前端，构建指纹为
`f31b8461d155af579a678ed9e941fdb974202b03d802431f4342bb91d827f3d8`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，没有使用 dev/sample/acceptance
  或客户数据。

在该 clean 精确 HEAD 上执行 `make ci.local.iteration`：47 个必需目标全部成立，其中
19 个本轮执行、28 个复用，10 个测试目标执行 572 项测试，5 项静态检查通过，
`unmapped_paths=0`，退出零。前端契约台账保持 31 个 declaration bindings、
0 个未闭合缺陷。回执：

`.runtime/frontend-dev-validation/executions/20261127T014601Z-2033232-56232980/receipt.json`

回执 SHA256：
`a3553590405b8ab0ac5217da737fc62022a2eeff9fc622a7ab0bd5dd4725f373`。

当前没有待提交审核的后端缺口。143 个业务入口的当前候选页面、角色和办理旅程仍未执行；
远端 PR CI、`bfc954c0b` 上的主线全量资格、部署和用户验收均未完成。

### 2026-11-27 FC-01 字段描述符第二次投影收口

多态引用生产者修复后继续核对前端主链路，确认严格 decoder 虽然已经收到完整
`fieldDescriptor`，但 V2 normalized store 和表单字段映射仍会做第二次缩减：

- `referenceModelField` 在 `resolveContractV2FieldDescriptorMap` 中被丢弃；
- `filename` 只从 `componentConfig` 读取，描述符独有声明不会进入表单字段；
- 表单 DTO 又丢弃 `digits`、`unit`、`temporal`、`currencyField`、
  `attachmentRole` 以及其余已声明 facet。

这会让刚接入的多态模型指针再次不可见，并使二进制文件名伴生字段、金额/比例/时长、
时区呈现和附件能力在表单消费路径上依赖第二载体或丢失。归属仍是 P0 前端契约消费与投影，
没有修改后端。

本切片完成：

- `resolveContractV2FieldDescriptorMap` 保留 `referenceModelField`，并以严格描述符
  回退消费 `filename`；
- `toContractV2FormFieldDescriptor` 完整保留组件/语义身份、引用指针、关系、附件角色、
  精度、单位、时区、货币、帮助、可查询/可排序及结构角色等已声明 facet；
- 表单字段和前端 schema 类型补齐相同字段，避免只靠未类型化透传；
- 增加描述符独有 `filename`、`referenceModelField`、`digits + unit + temporal +
  attachmentRole` 的区分性矩阵，共 39 个断言；
- 用同一投影验证百分比按声明精度/单位呈现，附件行为只凭声明 `relation + attachmentRole`
  生效；
- 刷新 `remediation_design.json` 的源码摘要；该摘要首次失败被分类为
  `baseline_evidence_defect`。

过程中还处理了两项 fail-closed 门禁：

- run 未登记 `contracts/v2/types.ts` 时按 `outside_scope` 停止，补充 owned scope 后重跑；
- 稳定 V2 投影拒绝多余的 snake_case `currency_field` 别名，最终只保留规范
  `currencyField`，没有放宽守卫白名单。

产品改动提交为 `743e60a2985490d7d71f5ee2526ac769fc497eab`。dirty 候选上的
`make ci.local.iteration` 执行 25 个目标、复用 23 个未变目标，15 个测试目标执行
636 项测试、5 项静态检查，`unmapped_paths=0`，全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T020023Z-2145975-92132550/receipt.json`

回执 SHA256：
`e12a3b5712574e0dd9721b554eb1627ed1c2f54f59ec06a7682a99ec46e17087`。

按产品提交重建 clean 前端，构建指纹为
`0e02a841e2bdb7083d7fefb7868fde09fe47f59d884886e5ac8091474e9dafa0`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份。

在该 clean 精确 HEAD 上执行 `make ci.local.iteration`：48 个必需目标全部成立，其中
19 个本轮执行、29 个复用，9 个测试目标执行 556 项测试，5 项静态检查通过，
`unmapped_paths=0`，全部退出零。真实多态生产者输出再次由前端 decoder 消费通过。
回执：

`.runtime/frontend-dev-validation/executions/20261127T020359Z-2175883-645743875/receipt.json`

回执 SHA256：
`6ac5b1b8349e811a71ecd7944972f81f4e6dc08d0e2ec048098b58b5f6f81149`。

143 个业务入口的当前候选页面、角色和办理旅程仍未执行；远端 PR CI、
`bfc954c0b` 上的主线全量资格、部署和用户验收均未完成。

### 2026-11-27 FC-02 页面身份声明化与选测补口

本切片属于共享前端呈现消费层，不修改后端契约、权限或数据。页面身份不再把
`display_name` / `name` 当作未声明的默认业务标识，只消费显式
`recordDisplayName`，或契约表单 profile 声明的 `title_field` / `primary_fields`。

完成内容：

- 删除通用页面身份和契约表单身份中的 `display_name` / `name` 兜底；
- 页面身份测试迁移到显式表单 profile 声明，并增加未声明名称不得补写记录标题的负例；
- 页面身份生产与测试输入显式映射到 `verify.frontend.page_identity`，同时验证无关前端路径
  不会误选该目标；
- 页面身份生产源码变化后，通过所属入口刷新组件接管清单输入摘要。

验证：

- `make verify.frontend.page_identity`：页面身份 smoke `34` 条、生命周期 smoke `28` 条、
  writer/integration 守卫全部通过；
- `make verify.frontend.dev.incremental.unit`：`287` 项测试通过；
- `make ci.local.iteration`：`63` 个必需目标全部成立，其中 `54` 个本轮执行、`9` 个复用；
  `36` 个测试目标执行 `1414` 项测试、`10` 项静态检查，`unmapped=0`、`not_run=0`、
  `blocked=0`，退出零；契约基座为 `42` 个绑定、`0` 个未闭合缺陷。

回执：

`.runtime/frontend-dev-validation/executions/20261127T090759Z-1881458-983503464/receipt.json`

回执 SHA256：
`bd7f73baf4de7617ab92f2494340501f42323827e211bf58a762a51f9cd400e8`。

产品切片提交为 `7e04ed26a2c7d04b6e078b35e3bbc3ec9598ee0c`。在该精确 HEAD 上执行
`make verify.frontend.build ENV=dev ENV_FILE=/home/lidefend/workspace/sce-backend-odoo/.env.dev`：
`build-info.json` 的源码 SHA 与 HEAD 一致，生产构建指纹为
`c1c73d5e3cba6d2301282a4ee905b5656f123f1ce8c8be0e278466d4ee55f9ef`。

构建日志：
`.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/page-identity-build.log`

日志 SHA256：
`66604153a27d7e9871057e1dd3c3ac8f010a15dbbaae571adfcb2964b819525d`。

生产角色/公司旅程、143 个业务入口浏览器矩阵、远端 PR CI、主线资格、部署和用户验收
仍未完成。

### 2026-11-27 FC-02 路由标题归一到页面契约

本切片删除 `router` 与 `pageIdentityRoute` 各自维护的静态业务标题表，页面身份和活动标题
统一消费 `page_contracts.pages.*.texts.title`，工作台允许消费
`page_orchestration.page.title`。契约未声明标题时直接抛出 `ContractGapError`，不再回退
“配置工作台 / 场景健康 / 产品发布 / 导航异常”等前端业务文案。

同时删除 ActionView 页面身份的 `legacyTitle` 第四路兜底。动作页身份只消费正式动作契约标题、
场景声明、动作/菜单投影；无权访问、请求失败、记录详情和记录表单保留明确的通用机制文案。

验证：

- 页面身份 smoke `34` 条、生命周期 smoke `33` 条与身份守卫通过；
- 导航壳、页面模式、严格类型和契约基座守卫通过，契约基座仍为 `42` 个绑定、`0` 个未闭合缺陷；
- `make ci.local.iteration`：`70` 个必需目标全部成立，其中 `57` 个本轮执行、`13` 个复用；
  `39` 个测试目标执行 `1526` 项测试、`10` 项静态检查，`unmapped=0`、`not_run=0`、
  `blocked=0`，退出零。

回执：

`.runtime/frontend-dev-validation/executions/20261127T092802Z-2084720-627610702/receipt.json`

回执 SHA256：
`a2d2e6dccff08a1e5bf238a52b25285ddc9f5cf0afd70d2d5d4cc0a284467cf2`。

产品切片提交为 `a9dc3b2d987cbc1374ac0f6fa09739dac1f95970`。精确 HEAD 生产构建的
`build-info.sha` 与 HEAD 一致，构建指纹为
`42ddc0fdc9649584bd6110eab9a4f0cf4c8eda2ae43941d242f5ed84274e5fce`；日志
`.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/route-title-build.log`，
日志 SHA256 `4b2808ea8d7b8c497dcb5773af2c425df60deb4d803138d71047b4ab3ba606a7`。

下一项是地址栏 URL 收敛：区分正式路由身份、后端声明的必需上下文和可重建的瞬时 UI 状态，
避免 scene/menu/action/return/context 参数重复堆叠。当前候选尚未做运行态 URL 回读。

### 2026-11-27 FC-02 canonical scene URL

场景路径 `/s/:sceneKey` 已承载场景身份，因此不再在 query 中重复写入
`scene/scene_key/sceneKey`，也不再写入仅用于展示的 `scene_label`。SceneView 内部所有
`router.replace` 共用同一剥离函数，避免这些值在加载和场景切换后重新回流地址栏。

`menu_id/action_id` 暂时保留：嵌入式 ActionView 和路由回读仍实际消费这两个声明引用。
本次只删除路径已表达的身份和可重建的展示标签，没有删除权限或业务执行所需上下文。

验证：

- `verify.frontend.route_query.unit` 经 Node TAP 执行非零用例并通过；
- 选测器 `288` 项、严格类型、场景入口、导航壳和契约基座全部通过；
- `make ci.local.iteration`：`73` 个必需目标全部成立，其中 `72` 个本轮执行、`1` 个复用；
  `53` 个测试目标执行 `1721` 项测试、`11` 项静态检查，`unmapped=0`、`not_run=0`、
  `blocked=0`。

回执：
`.runtime/frontend-dev-validation/executions/20261127T094406Z-2241047-640349705/receipt.json`

回执 SHA256：
`4f9ac4fcbfa8a09d2686b90097843a0bca78aeacc8a069864b1d45a0810b4ffe`。

产品切片提交为 `3466b4dbdd6e231b5b51d583178c02d436060089`。精确 HEAD 构建指纹为
`f82ec97cae784d9d73eaa92ef398b7eb8feaf792820acc388c82509dff633259`，构建
`build-info.sha` 与 HEAD 一致；日志
`.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/canonical-scene-url-build.log`，
日志 SHA256 `3a3e502c772da83eab2ff4f1329be9969e57742fb30a8ff60078a270f761ed4b`。

实际浏览器地址栏回读、剩余 context 参数的分类、远端 CI 和用户验收仍未完成。

### 2026-11-27 FC-02 entry title 退出 URL

入口标题改为正式页面/动作身份契约后，不再需要作为地址栏参数传递。本切片从契约导航
白名单、入口目标构造和表单身份输入中移除 `entry_title`，同时保留
`menu_id/action_id/context_raw/domain_raw` 等实际执行或回读上下文。

后端入口 presentation title 仍可参与反馈或其他呈现，但不会写回 URL；创建页标题改由
`authoritative_action_name`、动作契约或业务分类声明决定。跨模型动作导航增加负例，
证明同一模型和跨模型跳转都不保留 `entry_title`。

验证：

- 路由归一、跨模型动作导航、页面身份 smoke 和严格类型全部通过；
- `make ci.local.iteration`：`74` 个必需目标全部成立，其中 `73` 个本轮执行、`1` 个复用；
  `54` 个测试目标执行 `1722` 项测试、`11` 项静态检查，`unmapped=0`、`not_run=0`、
  `blocked=0`。

产品切片提交为 `5c255b7613f37ff4cc59e2bdec23e114b1118aa0`。在该 clean 精确 HEAD 上恢复
受影响集合：`74` 个必需目标全部成立，其中 `24` 个本轮执行、`50` 个复用；`11` 个测试
目标执行 `654` 项测试、`5` 项静态检查，`unmapped=0`、`not_run=0`、`blocked=0`。

回执：
`.runtime/frontend-dev-validation/executions/20261127T100426Z-2429142-187623519/receipt.json`

回执 SHA256：
`5c05576db0ccede93507523eba9f68cf11f467a4bb7d18c410f352cf08ed9903`。

精确 HEAD 构建指纹为
`9e4d558654ebe480a570ae94ad6897351b0ec02bc6022f8ac41dc28fc6ff596e`，构建
`build-info.sha` 与 HEAD 一致；日志
`.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/entry-title-url-build.log`，
日志 SHA256 `4b48d6151dcab40a50917984822de5c34afa724d39b4d2376b2117b72c35560f`。

剩余可重建展示参数主要是 `return_label` 与 business-category label；随后需要受管浏览器的
当前地址栏回读，不能只以纯函数结果宣称页面 URL 已优化。

### 2026-11-27 FC-02 return label 从契约重建

返回目的地 `return_url` 和产品归属继续保留；可重建的 `return_label` 从地址栏中移除。
ActionView 通过 `return_url` 解析目标路由，再消费其页面契约身份生成“返回 + 目标标题”，
发布控制台与企业初始化不再各自把展示文案写入 URL。

验证：

- 平台能力浏览器、场景生命周期、页面动作守卫和严格类型检查通过；
- `make ci.local.iteration`：`76` 个必需目标全部成立，其中 `35` 个本轮执行、`41` 个复用；
  `21` 个测试目标执行 `865` 项测试、`6` 项静态检查，`unmapped=0`、`not_run=0`、
  `blocked=0`。

回执：
`.runtime/frontend-dev-validation/executions/20261127T101416Z-2532766-453572306/receipt.json`

回执 SHA256：
`7fb022c0402ab323b7f6fc3b464ad24e9c8f05a72f2e460e2475c0b746d538ea`。

产品切片提交为 `1a7344da961118e3db9457702477bba1c8b34202`。精确 HEAD 构建指纹为
`ff46cc84d7f2ce60668994beb1f99e3d2d7e5e9a1b0b53448cfa78faebbff41c`，构建
`build-info.sha` 与 HEAD 一致；日志
`.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/return-label-url-build.log`，
日志 SHA256 `27b33604867aa6cb96652e62a578e361bc2ab960c58a6b24b0d44c1581adf0f0`。

下一步需要在受管浏览器中回读场景入口和跨模型返回链路的实际地址栏，再判断业务分类
label 是否应删除；当前只证明纯构造与组件契约。

### 2026-11-27 FC-02 business-category label 退出 URL

新生成的业务分类导航只保留 code、category id、允许 code 与 default values；
`current/default_business_category_label` 不再写入或跨路由传播。旧深链中的 label 仍可被
当前表单读取，但辅助同步会清理它，避免继续扩散。展示标签由当前关系选择契约或页面身份
提供。

同时把 URL 去污染规则加入页面身份守卫，禁止重新引入：

- `/s/:sceneKey` 下重复的 `scene_key/scene_label`；
- `entry_title`；
- `return_label`；
- business-category 展示 label 的导航白名单。

验证：

- 路由归一、跨模型动作导航、canonical form presenter 和严格类型通过；
- `make ci.local.iteration`：`76` 个必需目标全部成立，其中 `40` 个本轮执行、`36` 个复用；
  `26` 个测试目标执行 `926` 项测试、`6` 项静态检查，`unmapped=0`、`not_run=0`、
  `blocked=0`。

回执：
`.runtime/frontend-dev-validation/executions/20261127T102631Z-2646869-746704896/receipt.json`

回执 SHA256：
`8ef19601f63bb1c2ed4fe64ea29c61d65f5252544795b8caa851ed34eff7ddcd`。

产品切片提交为 `b8e8a0c6972462ab25f96380a7112cfdb31101e8`。精确 HEAD 构建指纹为
`fcd8a00c11f5300c573ddb18f56d50b6b5e74553758615914eca623ea4dc7174`，构建
`build-info.sha` 与 HEAD 一致；日志
`.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/url-presentation-query-build.log`，
日志 SHA256 `082188015803dd1e9cb6895b8896a955cf489cd2df01a47b0c1213188bd6f9d8`。

深度浏览器目标 `verify.frontend.page_identity.deep.browser` 本次未运行：受管 Compose
acceptance profile 未显式选择，预检在启动容器和写入数据前拒绝。真实地址栏回读、远端 CI
和用户验收仍未完成。

### 2026-11-27 主线 relationActiveActions 契约并入

主线 `9395d93f92badffc87d32c5979cf7c70e374e975` 已包含 P0 PR #1026 的
`relationActiveActions` FieldDescriptor 发布，并包含 PR #1024 的候选扫描边界修复。
#1019 通过受管 published-branch 入口建立并校验恢复 bundle，随后以 merge commit
`d352aa3221e9ade09d27da60413e6c580fa6a11a` 追加该主线。

冲突解析保持前端只在 `fieldDescriptor` 上读取业务语义，同时接收主线新增的
`relationActiveActions`；兼容 schema 同时保留 `relationField`、`referenceModelField`、
`attachmentRole` 和 `relationActiveActions`。相关源码哈希与全部派生收敛证据均已重建。

在该合并候选上执行 `make ci.local.iteration`：61 个目标、43 个测试目标、
1512 项测试、11 项静态检查全部通过，`unmapped=0`、`not_run=0`、`blocked=0`。
真实生产者到严格前端消费者的 relation 契约集成通过。回执：

`.runtime/frontend-dev-validation/executions/20261127T074128Z-1031756-379838348/receipt.json`

同一源码的生产前端构建通过，构建指纹
`968f32fc064ce1cf2e43c116fb095e9f0a63cb93909c1230b757655fae11dd67`。

首次本地迭代暴露的 P4 失败是 Quick 并发测试跨 mock 作用域读取不同内存前提；
测试已改为在同一前提内计算期望与执行值，相关治理门禁重跑通过。远端 exact-head CI、
143 业务入口浏览器矩阵、角色/公司旅程、部署和用户验收仍未执行或未宣称完成。

### 2026-11-27 FC-01 legacy widget 采集器单一语义权威

扫描剩余生产消费者时发现，`unifiedPageContractV2.ts` 的旧 widget 采集器仍可从
`componentConfig` 回填 `relationEntry`、`widgetOptions`、`subview`、字段类型和关系，
并把这些值作为兼容投影返回。这形成了 `fieldDescriptor` 之外的第二套语义来源。

本切片完成：

- 旧 widget 采集器只从 occurrence `fieldDescriptor` 读取 `fieldType` 与 `relation`；
- 返回的 `componentConfig` 仅保留传输字段，移除关系、选择、精度、单位、时区、
  domain/context、relationEntry、relationActiveActions、widgetOptions 和 subview 等业务语义；
- 增加伪造 componentConfig 的类型、关系、relationEntry、widgetOptions、subview、
  selection 均不生效的负例；
- Web V2 consumer 守卫禁止重新引入 `componentConfig.*` 语义 fallback。

`make ci.local.iteration` 执行 53 个目标、复用 9 个未变目标，36 个测试目标执行
1385 项测试、10 项静态检查全部通过，`unmapped=0`、`not_run=0`、`blocked=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T080051Z-1260505-664266119/receipt.json`

同一产品源码的生产前端构建通过，构建指纹
`fbaa6fdb4bf40b46f42e6241932e24035ce9a58aaf8c7facc899db0cdf526b56`。

首次完整迭代发现生产源码变化后的组件接管派生清单摘要过期；按拥有层重建清单后，
剩余受影响目标全部通过。该结果不证明生产角色/公司页面、143 入口矩阵或用户验收。

随后主线 `0d17e91e7`（#1027 exact push history scan）通过受管
published-branch 同步并入候选，merge commit 为
`caedddcb5d96d8fd7e523a9a903659c3355176cf`，无冲突。该新基线本地迭代执行
61 个目标、43 个测试目标、1512 项测试和 11 项静态检查，全部通过。

### 2026-11-27 FC-01 native layout 只消费 fieldDescriptor

继续扫描发现原生表单适配器仍把 `fieldInfo` 和 `componentConfig` 作为字段类型、
关系、widget options、subview、modifier 和必填校验的语义来源，并在
`contractV2WidgetToNativeFieldNode` 中反向生成 `fieldInfo` 副本。这些兼容路径已删除：

- 原生字段节点只从 occurrence `fieldDescriptor` 或同一 canonical store 的 strict
  descriptor 读取语义；
- 没有 `fieldDescriptor` 时不再从 `fieldInfo` 猜测，字段 schema 保持缺失并进入显式契约缺口；
- widget 采集器直接输出 `fieldDescriptor`，不再合成 `fieldInfo`/`field_info`；
- 相应测试夹具迁移到 strict descriptor，并覆盖 descriptor 与冲突 legacy 数据同时存在时
  descriptor 唯一生效。

`make ci.local.iteration` 执行 53 个目标、复用 9 个未变目标，36 个测试目标执行
1385 项测试、10 项静态检查全部通过，`unmapped=0`、`not_run=0`、`blocked=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T083412Z-1580824-776757870/receipt.json`

同一产品源码的生产前端构建通过，构建指纹
`b286877279f54dc6f337e6a783f941853ca85f1a36f7576e6c9dd683f6966969`。

该切片只是本地单测与组件验证，不代表生产角色/公司页面、143 入口矩阵完成。

### 2026-11-27 FC-02 导航与创建能力查漏

FC-02 按收敛和查漏补缺启动，没有新增页面能力。正式导航基线先通过：

- `verify.frontend.navigation_shell.unit`：场景 hydration、菜单授权、面包屑、键盘和
  导航守卫；
- `verify.frontend.intent_request_identity.unit`：28 个请求身份用例；
- `verify.frontend.business_entry.matrix.universe`：143 个正式入口集合完整。

首轮源码审计发现 `relationCreateMode` 仍按 `sc.dictionary` 模型名推断 quick create。
后端已经在 `relation_entry.create_mode` 显式声明该能力，因此前端模型特判会形成第二套
创建授权。该分支已删除：

- 只有声明的 `create_mode=quick/page/dialog` 和相应资格才能产生创建能力；
- 模型名、默认值或字段外观都不能自行产生快速新建；
- 增加对应的区分性负例。

`make ci.local.iteration` 在该切片上执行 53 个目标、复用 9 个未变目标，
36 个测试目标执行 1385 项测试、10 项静态检查全部通过。回执：

`.runtime/frontend-dev-validation/executions/20261127T085058Z-1727166-883290215/receipt.json`

同一产品源码的生产前端构建通过，构建指纹
`784b50ede63f2ff343d27170d319b7036436cf00bf0eca95e083eead40da3bc9`。

生产角色/公司页面和 143 入口浏览器矩阵仍未运行；下一步继续检查面包屑、深链及
公司/项目上下文呈现。

### 2026-11-27 FC-01 原生表单与附件分类语义收口

本轮按“本地一个合格切片即发布、后续直接更新同一 PR”的方式推进。draft PR #1019
（`https://github.com/lidefend/sce-backend-odoo/pull/1019`）从
`13b59532d` 开始，先后更新到 `3b8ee1bc1` 和 `a134da7dd`。远端检查不作为本轮
继续实施的等待条件，也没有据此宣称集成通过。

#### 原生表单字段语义

- canonical → native form bridge 的 `technical` 与 `surfaceRole` 只从
  `fieldDescriptor` 投影；
- `componentConfig` 不能隐藏一个未声明 technical 的字段，也不能复活 technical 字段；
- 重复关系字段的导航归属只使用 `fieldDescriptor.subview` 与 canonical
  `fieldType/widgetType`；
- `componentConfig` 的 subview/nativeWidget 不能再改变重复关系出现位置的所有权；
- 台账增加到 36 个声明绑定、0 个未闭合缺陷。

该切片本地组合门禁执行 26 个目标、复用 22 个，15 个测试目标执行 648 项测试、
6 项静态检查，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T035709Z-3035874-670527603/receipt.json`

回执 SHA256：
`8f8aca7c3159a7135f819d4a687608b75481dee10a65f48a9feea589339f93e3`。

#### 附件关系业务分类

- 附件能力只由 `fieldDescriptor.relation === ir.attachment`、描述符附件
  `widgetType` 或契约 activity 角色决定；
- `componentConfig.widget=many2many_binary` 不再把普通业务关系排除出导航；
- 前端 `componentKey=ProfessionalAttachmentCollection` 只表示实现选择，不再成为
  附件业务语义；
- 新增“传输形似附件”“实现形似附件”仍进入关系导航，而描述符声明附件被排除的
  区分性用例；
- 生产源码变化后通过受管入口刷新 component-driver inventory。

该切片本地组合门禁执行 27 个目标、复用 21 个，16 个测试目标执行 666 项测试、
6 项静态检查，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T040338Z-3087960-992769241/receipt.json`

回执 SHA256：
`5117921667aa07d728f28b1adf1a88de6c9fa55d71668bde310fd6a7e6316430`。

本轮最后 clean 运行态仍绑定 `e26341a03`；`b3cbe05f` 和 `3fbfdaa3` 两个后续产品
提交只完成了本地受影响目标验证并同步到 PR。远端 CI、集成资格、143 个业务入口的
浏览器矩阵、部署和用户验收均未在本轮宣称完成。

### 2026-11-27 FC-01 record-form widget 与收藏身份收口

继续按同一 PR 增量发布：

- record-form schema 的 `widget` 只从 canonical `widgetType` 解析；
- record-form `widgetSemantics` 只从 canonical `widgetOptions` 解析；
- layout `componentConfig.nativeWidget/widgetSemantics` 不再提供或覆盖这些字段语义；
- 收藏字段持久化只认后端声明的 `boolean_favorite` 原生控件；
- 中文标签“仪表板”、字段名 `is_favorite` 和 `componentConfig` 均不能再把普通
  checkbox 提升为收藏字段；
- 契约台账保持 37 个绑定、0 个未闭合缺陷。

两次受影响目标门禁各执行 27 个目标、复用 21 个，16 个测试目标执行 666 项测试、
6 项静态检查，`unmapped_paths=0`：

- `.runtime/frontend-dev-validation/executions/20261127T042121Z-3223848-620740478/receipt.json`
  SHA256 `3ce3065e1e75ee4d5d5229a647a1642798086c2f91d660578f48b26bb942bc06`
- `.runtime/frontend-dev-validation/executions/20261127T042643Z-3265132-295910211/receipt.json`
  SHA256 `ff676a47115310dc2759295244a01956822b104c074b9d303e3ef8faf0e6a06a`

随后对完整 HEAD `37b836c96bf2deb3aad20b1d333aac4c86477dec` 重新运行
`make ci.local.iteration`，依赖的 `verify.contract.polymorphic_reference.integration`
在 Odoo 已报告 `2 tests, 0 failed, 0 errors` 且进程退出 0 的情况下，被本地测试回执记为
`count=0/status=failed`，因此外层非零并 fail-fast。该项归类为 P4 验证工具缺陷；本次没有
为它修改产品代码，后续前端目标在该次尝试中为 `not_run`，不冒充通过。

PR #1019 当前更新到 `37b836c96bf2deb3aad20b1d333aac4c86477dec`。远端集成、浏览器
矩阵、部署和用户验收仍不属于当前本地迭代结论。

### 2026-11-27 FC-01 批量负责人候选声明消费

后端 `batch_policy.assignee_options` 已完整声明负责人查询，但前端仍默认
`res.users`、`id/name`、空 domain、`name asc` 和 80。该切片移除这些前端产品默认：

- `model`、`fields`、`domain`、`order` 与正整数 `limit` 只从清单批量策略消费；
- 字段为空、domain 非数组、order 为空或 limit 非法均以 `ContractGapError` 停机；
- 纯声明解析拆到独立 runtime 模块，与 API client 解耦；
- 契约台账达到 38 个绑定、0 个未闭合缺陷。

本地组合门禁执行 27 个目标、复用 21 个，16 个测试目标执行 666 项测试、
6 项静态检查，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T043934Z-3393976-531192137/receipt.json`

回执 SHA256：
`5327ff8b553c820198d5232bd782f490942dcbc77b834fc3a19ce67fd3f88e0c`。

PR #1019 已更新到 `298ff9e26146ed11ba62c6d6fa0e1abb004b6095`。远端集成、浏览器
矩阵、部署和用户验收仍未在本轮宣称完成。

### 2026-11-27 FC-01 收藏 schema 身份收口

继续清除收藏字段的名称推断：

- `buildNativeFieldSchemas` 与 canonical/native schema 装饰只认声明为
  `boolean_favorite` 的控件；
- 字段名为 `is_favorite` 但控件声明为普通 checkbox 时，仍按普通布尔字段处理；
- 声明为 `boolean_favorite` 的字段仍正常从正文提取并装饰到文本标题；
- 该切片不新增契约绑定，继续使用既有的原生身份与字段描述符绑定。

本地组合门禁执行 27 个目标、复用 21 个，16 个测试目标执行 666 项测试、
6 项静态检查，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T044806Z-3471019-884606900/receipt.json`

回执 SHA256：
`fc82d0c9d52e7dc97546736fc9f080f2a55309bdff4169d77a56689269d7fecb`。

PR #1019 当前更新到 `6286e216b868a8fe93af4ae8e750f22aa0315052`。远端集成、
浏览器矩阵、部署和用户验收仍未在本轮宣称完成。

### 2026-11-27 FC-01 关系内联创建声明收口

后端已声明 `inline_create.name_field/match`，前端却在投影和三个创建消费点回退
`name/exact_label`。本切片移除这些第二权威：

- enabled 内联创建缺少 `name_field` 或 `match` 时抛 `ContractGapError`；
- record-form、关系导航和动作创建都使用声明的 `name_field`；
- disabled 声明仍允许空创建字段；
- 两个旧创建旅程夹具补齐正式声明，未通过放宽生产规则迁就测试；
- 契约台账达到 39 个绑定、0 个未闭合缺陷。

本地组合门禁执行 33 个目标、复用 15 个，22 个测试目标执行 802 项测试、
6 项静态检查，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T050053Z-3589222-127628259/receipt.json`

回执 SHA256：
`ba05929b83941a2c7f521a8a6c8c728862bba9ebeb7de3d55c33a4b022d355d9`。

PR #1019 当前更新到 `8c8f1fc7935522eb385971d9e01e5d648be1032b`。远端集成、
浏览器矩阵、部署和用户验收仍未在本轮宣称完成。

### 2026-11-27 FC-01 ActionView 看板标题权威收口

虽然 Kanban presentation 已要求声明 `title_field`，ActionView 的标题选择仍有
`display_name → name → 首列 → id` 回退链。本切片补齐入口层：

- ActionView 只消费声明的 `title_field`；
- 标题字段必须属于声明的 Kanban 字段集合；
- 缺少标题声明或声明不在字段集合中即 `ContractGapError`；
- 非 Kanban 空字段集返回空标题字段，不产生无关页面错误；
- 纯标题选择模块从 V2 策略消费 hook 中拆出，未通过关闭静态守卫解决检查；
- 契约台账达到 40 个绑定、0 个未闭合缺陷。

本地组合门禁执行 33 个目标、复用 15 个，22 个测试目标执行 802 项测试、
6 项静态检查，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T051336Z-3751010-136436832/receipt.json`

回执 SHA256：
`1a9e0e8640fa1c2672770230d4cc8af207862ee2d7d71ede82ea9b16ad28fab5`。

PR #1019 当前更新到 `ca2e773dfebe0d9e60d366ed3a1bc8f240bf9cca`。远端集成、
浏览器矩阵、部署和用户验收仍未在本轮宣称完成。

### 2026-11-27 FC-01 主筛选预算声明收口

后端 `surface_policies.filters_primary_max` 始终由用户表面策略发布，前端缺失时却
默认 5。该切片移除第二套预算：

- 主筛选预算只消费声明的非负整数；
- 显式 0 是合法声明，表示不展示主筛选；
- 缺失、负数、小数或字符串声明均以 `ContractGapError` 停机；
- 不再用默认值或 `Math.floor` 夹取吸收非法声明；
- 契约台账达到 41 个绑定、0 个未闭合缺陷。

本地组合门禁执行 33 个目标、复用 15 个，22 个测试目标执行 802 项测试、
6 项静态检查，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T052524Z-3882287-708020276/receipt.json`

回执 SHA256：
`a16930f8a14a9d2cbc1d5f6fe299045a83e2c312135c180d76c1fd7b52a8e39f`。

PR #1019 当前更新到 `3bdb21bb17079fe48e0649c247441297092087be`。远端集成、
浏览器矩阵、部署和用户验收仍未在本轮宣称完成。

### 2026-11-27 FC-01 筛选与动作预算统一

继续移除前端可见规模默认：

- 总筛选数只消费 `surface_policies.filters_max`，移除硬编码 8；
- 主筛选数继续消费 `filters_primary_max`；
- 主动作数只消费 `actions_primary_max`，移除默认 4；
- 三种预算统一使用一个严格非负整数解析器，显式 0 保留；
- 契约台账更新为 42 个绑定、0 个未闭合缺陷。

两段本地组合门禁分别执行 33 和 38 个目标，最终动作预算门禁执行 900 项测试、
6 项静态检查，`unmapped_paths=0`。最终回执：

`.runtime/frontend-dev-validation/executions/20261127T054526Z-4077036-791169283/receipt.json`

回执 SHA256：
`b7641c95d758483f4ee92d7d54abd3eefea0670594408bfa82b62ee4ca3fbe54`。

PR #1019 当前更新到 `3722406c16b2047fbb0db0d84111c931775590bf`。远端集成、
浏览器矩阵、部署和用户验收仍未在本轮宣称完成。

### 2026-11-27 FC-01 ActionView 列表列字段语义单一权威

继续核对列表列投影时确认，字段描述符已提供类型、控件、组件身份、币种字段、精度、
单位、时区与选择项，但 ActionView 列表 schema 在描述符之后展开整个
`componentConfig`，后者仍能覆盖这些业务字段语义；请求字段语义函数也反向优先读取
`componentConfig`。同时 V2 normalized store 丢失了已声明的 `currencyField`。本轮只在
P0 前端消费及投影层修复，未修改后端。

本切片完成：

- V2 normalized store 原样保留 `fieldDescriptor.currencyField`；
- ActionView 列表列的类型、控件、组件身份、币种字段、精度、单位、时区、选择项、
  可见性和可排序性只从 `fieldDescriptor` 消费；
- `componentConfig` 只保留列表自身传输声明：`value_field`、`sort_field`、
  `aggregate`、`filter_field`、`export_field`、`optional` 等；
- 冲突的 `componentConfig` 不能覆盖描述符语义，不能引入关系目标或选择项；
- `sortable=true` 原样透传，不再只剩显式的 false；
- 增加 58 项投影用例，覆盖冲突组件配置、币种依赖、传输字段保留和语义不回流；
- 台账新增 ActionView 列表列语义绑定，现为 35 个绑定、0 个未闭合缺陷。

恢复事实：

- 第一次选测失败于 `store.ts` 的过期基线哈希，已刷新到真实源码摘要；
- 第二次选测失败于描述符局部变量被推断为空对象，已补严格
  `ContractV2FieldDescriptor` 类型；
- 初始 clean 构建曾误用不存在的截断派生 SHA，已拒绝该身份，并用真实完整 HEAD
  `e26341a037f85c338acba2750006f816d41004a4` 重建和重跑。

产品提交为 `5d29d70e165c1efdf05984425613e323d55f6bdf`，治理绑定提交为
`e26341a037f85c338acba2750006f816d41004a4`。clean 前端指纹为
`8dd6497bf847a5b3486c2c801a3b083cf024755a9fe61b044dbdb7fd6e663f84`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 返回完整源码 `e26341a03`、上述指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一完整源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份。

在该 clean 精确 HEAD 上执行 `make ci.local.iteration`：19 个目标本轮执行、29 个复用，
9 个测试目标执行 556 项测试，5 项静态检查通过，`unmapped_paths=0`。回执：

`.runtime/frontend-dev-validation/executions/20261127T034718Z-2961168-415126651/receipt.json`

回执 SHA256：
`26db8f32bb3b0633647582dafae0232b54b19068f48582c3b007f335c6974c37`。

回执仍保留 9 个已有 passed 结果的 registration-missing 标记，属于选测/注册卫生缺口。
143 个业务入口的当前候选页面、角色和办理旅程仍未执行；远端 PR CI、
`bfc954c0b` 上的主线全量资格、部署和用户验收均未完成。

### 2026-11-27 FC-01 effective field-status consistency 消费收口

继续核对 canonical 表单描述符与有效状态时确认：字段描述符声明
`invisible/readonly/required`，而运行时 `widgetStatus` 会叠加修饰条件。前者是后端静态业务约束，
后者可以按当前记录收紧呈现，但此前前端没有阻止后者放宽前者。该缺口只在 P0 前端消费路径修复，
本轮未修改后端代码。

本切片完成：

- `fieldDescriptor.invisible=true` 不得被有效状态改为可见；
- `fieldDescriptor.readonly=true` 不得被有效状态改为可编辑；
- `fieldDescriptor.required=true` 不得被有效状态改为可选；
- 有效状态比描述符更严格仍合法，正常保留；
- 三种非法放宽分别以
  `field.<fieldCode>.status_consistency.<invisible|readonly|required>` 抛
  `ContractGapError`；
- 台账补上声明站点、消费符号、停机符号、回归目标和行为测试的完整绑定；
- 台账现为 34 个声明绑定、0 个未闭合缺陷。

聚焦验证：

- `make verify.frontend.contract_basis.unit`：15 项测试通过，台账守卫
  `bindings=34 open_defects=0`；
- `make verify.frontend.canonical_form_presenter.unit`：canonical 主行为用例 177 项，
  连同 typed native comparison、relation projection、workflow/action authority 等附属用例均通过。

治理绑定提交为 `0334aeac3a5c5384fef318f588be1c7c031fdffd`，其中包含产品提交
`b82905bc176d2c5240f77b9a9d5df42d5e3574ba`。按 `0334aeac3` 重建 clean 前端，构建指纹为
`d93cb03d87f43345f47337c222fe24d9a3e77491c7c70b846be26cb3d1227ede`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回 `0334aeac3`、上述构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，未使用 dev/sample/acceptance
  或客户数据。

在该 clean 精确 HEAD 上执行 `make ci.local.iteration`：19 个目标本轮执行、29 个复用，
9 个测试目标执行 556 项测试，5 项静态检查通过，`unmapped_paths=0`，全部目标结果为 passed。回执：

`.runtime/frontend-dev-validation/executions/20261127T032949Z-2816162-850488001/receipt.json`

回执 SHA256：
`e3666a8ef195ae35aff68d122b964d0e0a678434efcce2dff0fe9c2d1e1ccf8d`。

回执仍将 9 个已有 passed 结果的目标列为 `registrationMissingTargets`；这是选测注册/台账卫生
缺口，本轮没有把它当作产品成功证明，也没有改写回执为无缺口。143 个业务入口的当前候选页面、
角色和办理旅程仍未执行；远端 PR CI、`bfc954c0b` 上的主线全量资格、部署和用户验收均未完成。

### 2026-11-27 关系目标向唯一契约收敛

复核上一轮实现后纠正了方向：前端不应在
`componentConfig.relation/relationModel/relation_model` 与
`fieldDescriptor.relation` 之间比较或选一个，而是只消费正式
`fieldDescriptor.relation`；这些兼容投影不再参与关系产品语义。

本切片删除了五个核心消费者中的兼容分支：

- canonical form presenter；
- V2 normalized field descriptor store；
- canonical form renderer 的字段描述符投影；
- contract V2 widget → native field bridge；
- ActionView 列表列投影。

现在的行为是：

- `fieldDescriptor.relation` 存在时直接消费；
- `componentConfig` 中的关系别名不能覆盖、补充或充当 fallback；
- canonical `many2one` 缺少正式关系目标时抛 `ContractGapError`；
- 测试同时覆盖“componentConfig 冲突但 canonical 有效”和“componentConfig 唯一但 canonical 缺失”两个方向。

契约台账绑定同步改为单一权威表述，停止符号为 `requireDeclaredText`，目前仍为
32 个绑定、0 个未闭合缺陷。组件接管清单和 `remediation_design.json` 源码摘要按最终
源码刷新。

产品改动提交为 `28542de40c3f31e1cb3a45efe1562035f88c7d6c`。dirty 候选上的
`make ci.local.iteration` 执行 27 个目标、复用 21 个未变目标，16 个测试目标执行
655 项测试、6 项静态检查，`unmapped_paths=0`，全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T022524Z-2347904-979289514/receipt.json`

回执 SHA256：
`eda0ba9a4f546e1dfb860c531e812f9737ec0ed28e0a6bd6f68a5686c7e3979c`。

按产品提交重建 clean 前端，构建指纹为
`189bdb8c0ab110a6a65767541f55eb7efda66dd550b4c026a7316861a2bc0cca`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份。

在该 clean 精确 HEAD 上执行 `make ci.local.iteration`：48 个必需目标全部成立，其中
19 个本轮执行、29 个复用，9 个测试目标执行 556 项测试，5 项静态检查通过，
`unmapped_paths=0`，全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T022945Z-2382566-128679342/receipt.json`

回执 SHA256：
`4507f12d1b8b84e877b1e8328c038d486e805c4eedd4f396cd538b7e96565374`。

143 个业务入口的当前候选页面、角色和办理旅程仍未执行；远端 PR CI、
`bfc954c0b` 上的主线全量资格、部署和用户验收均未完成。

### 2026-11-27 FC-01 canonical 关系目标一致性收口

上一轮补齐描述符透传后继续核对 canonical form presenter，确认关系目标仍存在第二条
静默选择路径：当 `componentConfig.relation`、`relationModel` 或 `relation_model` 与
`fieldDescriptor.relation` 不一致时，presenter 按先后顺序直接采用其中一个；若字段尚未
选值，一致性检查甚至不会执行。运行时关系控件此前已有同类停机，但 canonical 呈现路径
仍可能按错误模型显示或准备导航。

本切片完成：

- canonical presenter 收集全部非空关系目标声明；唯一或一致时原样消费，不一致即抛
  `ContractGapError` 并指向 `field.<name>.relation_model_consistency`；
- 该校验在 `many2one` 字段投影时执行，不依赖当前是否已有选中值；
- 增加 `componentConfig.relation=res.partner` 与
  `fieldDescriptor.relation=project.project` 的冲突用例，先证旧实现不抛错；
- `frontend_contract_basis_ledger.json` 新增 canonical 关系目标绑定，回归守卫为
  `verify.frontend.canonical_form_presenter.unit`；
- 增量选测规则纳入 `contractFormPresenter.ts`，并验证 presenter 变化必须同时选择
  canonical form 与 primitive adapter 合同测试；
- presenter 源码变化后通过既有生成入口刷新 component-driver takeover inventory。

首次选测规则修改后，反例发现 presenter 路径没有选择 primitive adapter；补齐通用表单路由
后通过。组件接管清单过期按 `baseline_evidence_defect` 分类，并由受管生成器修复。

产品改动提交为 `b10ba042f54db884d5dbe912bc3a26b43beff571`。dirty 候选上的
`make ci.local.iteration` 执行 43 个目标、复用 5 个未变目标，28 个测试目标执行
1142 项测试、10 项静态检查，`unmapped_paths=0`，全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T021211Z-2242546-122517043/receipt.json`

回执 SHA256：
`d6ea3e2625b8f5b77136901ca973a75e6d0b19b57767f435bb60e2bee33886e1`。

按产品提交重建 clean 前端，构建指纹为
`49a3d162de0bf9c66f9ec32ad8c712e11a831c90cc78643f5e033bcca22ddab0`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份。

在该 clean 精确 HEAD 上执行 `make ci.local.iteration`：48 个必需目标全部成立，其中
19 个本轮执行、29 个复用，9 个测试目标执行 556 项测试，5 项静态检查通过，
`unmapped_paths=0`，全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T021717Z-2283555-82478939/receipt.json`

回执 SHA256：
`8cf4b0e20f3e00b4a1ec0ed20cc39e41d7313905e08ba075b280cdeb731885b4`。

143 个业务入口的当前候选页面、角色和办理旅程仍未执行；远端 PR CI、
`bfc954c0b` 上的主线全量资格、部署和用户验收均未完成。

### 2026-11-27 FC-01 plain value-shape 前端消费收口

继续检查 plain collection 回退时确认，普通 `char/text/html` 字段遇到对象会按
`display_name/label/name` 推断业务标签，遇到数组会直接拼成业务文本；同时显式 locale
映射对象反而被当作空值。这是纯前端值外形推断缺陷，本轮未修改后端。

本切片完成：

- plain 字段只接受标量或明确 locale key 的映射，并按当前/回退 locale 选择文本；
- 对象中的 `display_name/label/name` 不能自动升级为业务标签；
- 任意数组不能自动拼成业务列表；
- 无法证明值语义的 plain 形状抛 `ContractGapError`；
- 静态守卫禁止恢复对象标签推断；
- `frontend_contract_basis_ledger.json` 新增 plain text value-shape 绑定。

`make ci.local.iteration` 在 `94b0e83d78c9827b2fbee04375ec058534f3eab6`
加当前 owned dirty scope 上执行 25 个目标、复用 22 个未变目标，其中 16 个测试目标
共执行 676 项测试、6 项静态检查，`outside_scope=[]`、`unmapped_paths=0`，全部退出零。
原始回执：

`.runtime/frontend-dev-validation/executions/20261127T004923Z-1610133-35668117/receipt.json`

回执 SHA256：
`b72e59f509d8ee22ef2e7e6355d4b406d9a4bc5ac62d3121eab96564fedd168a`。

该证据只证明当前前端 dirty 候选的本地精准消费与治理检查。产品提交后仍需按新精确 HEAD
重建 clean 前端与 Odoo 容器，并在 clean HEAD 重新执行本地增量入口。143 个业务入口的
当前候选页面、角色或办理旅程仍未执行，远端 PR CI、主线资格、部署和用户验收均未完成。

产品改动已提交为 `dc0bd3f9ea87baa5d11fecaf1b4afde27dd0f097`，并按该 SHA 重建
clean 前端，构建指纹为
`839e5e5e741f6d19f357cc75350149b82d49ac6299d0c38ac32bbd1d3d61a9ce`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，未使用 dev/sample/acceptance
  或客户数据。

在该 clean HEAD 上执行 `make ci.local.iteration`：47 个必需目标全部成立，其中
16 个本轮执行、31 个复用，8 个测试目标执行 489 项测试，5 项静态检查通过，
`unmapped_paths=0`，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T005356Z-1645849-501396715/receipt.json`

回执 SHA256：
`c212cf448412fa333552885fc1ffd1e8df20427134543229647ed52e45b4f971`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。

### 2026-11-27 FC-01 通用 float 精度消费收口

继续检查 status、boolean、JSON 后，现有 status 选择/类型停机、boolean 类型词表和 JSON
只读展示未发现新的未声明业务分支。通用数值呈现仍有一个实质缺口：`float` 没有
`digits` 时默认显示两位，而契约并未提供该默认值。

本切片完成：

- 共享 `formatNumericFieldValue` 对 `float` 强制消费合法 `digits`；
- 缺失或非法精度抛 `ContractGapError`，空值也必须先具备显示精度声明；
- `integer` 的 0 位精度继续来自已声明字段类型，不冒充前端默认；
- 列表汇总、主从明细、列表/看板/表单和本地化显示统一使用该 formatter；
- 更新既有测试载体，为依赖两位小数的 float 显式声明 `digits`；
- `frontend_contract_basis_ledger.json` 新增通用 float 精度绑定；
- 静态守卫禁止重新引入未声明两位小数回退。

`make ci.local.iteration` 在 `c849d7b9f3ba12115e62e5b18474696adccbcd39`
加当前 owned dirty scope 上执行 26 个目标、复用 21 个未变目标，其中 17 个测试目标
共执行 713 项测试、6 项静态检查，`outside_scope=[]`、`unmapped_paths=0`，全部退出零。
原始回执：

`.runtime/frontend-dev-validation/executions/20261127T001639Z-1368391-544409898/receipt.json`

回执 SHA256：
`d4df165aff9b9ba1fcfc499eabbddc84e753205c3319fbc8090e5faa308c8cbe`。

该证据只证明当前 dirty 候选的本地精准消费与治理检查。产品提交后仍需按新精确 HEAD
重建 clean 前端与 Odoo 容器，并在 clean HEAD 重新执行本地增量入口。143 个业务入口的
当前候选页面、角色或办理旅程仍未执行，远端 PR CI、主线资格、部署和用户验收均未完成。

产品改动已提交为 `5f355f6cbe88572f67497a63f2496bcdb619e814`，并按该 SHA 重建
clean 前端，构建指纹为
`ce53266d5359d4a2a9c7ace8444e06b87db40abecbc5c863da47230979cfa1e6`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，未使用 dev/sample/acceptance
  或客户数据。

在该 clean HEAD 上执行 `make ci.local.iteration`：47 个必需目标全部成立，其中
16 个本轮执行、31 个复用，8 个测试目标执行 488 项测试，5 项静态检查通过，
`unmapped_paths=0`，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T002046Z-1400371-287900326/receipt.json`

回执 SHA256：
`83b6189569bb99b5fbca0ab4e5978a51c5efd8cde8fc196d6b817cc861a77c04`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。

### 2026-11-27 FC-01 relation label 权威消费收口

继续核对 many2one/many2many 候选项与已选记录时发现，缺少权威显示标签时会生成 `#<id>`，
检索结果也使用同类回退。这会把数据库主键冒充业务名称，违反契约缺声明即停机。

本切片完成：

- 已选 relation ID 没有权威标签时不再生成 `#id`，选择项只保留真实 label；
- relation option 或 search row 缺少 `display_field/display_name/name` 标签时抛
  `ContractGapError`；
- 候选查询与选中标签水合对 `ContractGapError` 重新抛出，不再被一般请求错误处理吞掉；
- `parseMany2oneDisplay` 对裸 ID 或空标签返回空，不合成业务文本；
- 增加选项、搜索结果、异步候选加载和静态守卫负例；
- `frontend_contract_basis_ledger.json` 新增 relation option label 权威绑定。

首次统一入口在 relation 行为、契约与组件检查通过后停于 lint，原因是删除合成逻辑后遗留
两个未消费兼容参数；移除参数并重跑 relation 目标与 lint 后，最终 `make ci.local.iteration`
执行 31 个目标、复用 16 个未变目标，其中 21 个测试目标执行 792 项测试、7 项静态检查，
`outside_scope=[]`、`unmapped_paths=0`，全部退出零。原始回执：

`.runtime/frontend-dev-validation/executions/20261126T235634Z-1228375-184515308/receipt.json`

回执 SHA256：
`2c1b77d3ba53468a66a1275a0ba8034f183a66ff0e1502733eb1d7d74d17833c`。

该证据只证明当前 dirty 候选的本地精准消费与治理检查。产品提交后仍需按新精确 HEAD
重建 clean 前端与 Odoo 容器，并在 clean HEAD 重新执行本地增量入口。143 个业务入口的
当前候选页面、角色或办理旅程仍未执行，远端 PR CI、主线资格、部署和用户验收均未完成。

产品改动已提交为 `5116d46aa6a60dfa0b18bada3b47c9e5a3809577`，并按该 SHA 重建
clean 前端，构建指纹为
`d9a873eff26fdc78a384d8700ad2e5afddb21e3f63ca8c6db76e479a52f291be`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，未使用 dev/sample/acceptance
  或客户数据。

在该 clean HEAD 上执行 `make ci.local.iteration`：47 个必需目标全部成立，其中
16 个本轮执行、31 个复用，8 个测试目标执行 487 项测试，5 项静态检查通过，
`unmapped_paths=0`，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T000040Z-1260833-860212837/receipt.json`

回执 SHA256：
`e036b24fb6ab17aa715d7d9853415847e5c324ae03041c153b7cc8818a53a6ee`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。

### 2026-11-27 FC-01 relation target 一致性与选测归属收口

继续检查关系声明链时确认，`fieldDescriptor.relation` 与 `relationEntry.model` 可能同时
存在；前端原实现只会静默采用前者，不验证两者是否指向同一模型。该冲突会让字段查询
模型 A，却按模型 B 的关系权限、创建模式和读取字段执行。

本切片完成：

- `relationModel` 同时读取两个声明载体；一致时返回唯一目标，冲突时抛
  `ContractGapError` 并指向 `field.<name>.relation_model_consistency`；
- 增加一致声明与冲突声明的区分性用例；
- `frontend_contract_basis_ledger.json` 新增 relation target 一致性绑定；
- 把 `relationDescriptor.ts`、对应测试和 run 检查登记到既有
  `verify.frontend.professional_relation_field.unit`，修复 `outside_scope`；
- relation 生产源码变化后，通过既有
  `refresh.frontend.component_driver_takeover.inventory` 刷新生成物摘要。

首次统一入口因 run 归属/检查登记缺失 fail-closed；补齐后第二次又因 component inventory
过期失败，分类为 `baseline_evidence_defect` 并由受管刷新入口修复。最终
`make ci.local.iteration` 执行 40 个目标、复用 7 个未变目标，其中 27 个测试目标执行
1072 项测试、10 项静态检查，`outside_scope=[]`、`unmapped_paths=0`，全部退出零。
原始回执：

`.runtime/frontend-dev-validation/executions/20261126T234521Z-1140323-836895090/receipt.json`

回执 SHA256：
`29a80a47753df24d6e05f07d2df9022e62340799bf33f6c65fa408c921611484`。

该证据只证明当前 dirty 候选的本地精准消费与治理检查。产品提交后仍需按新精确 HEAD
重建 clean 前端与 Odoo 容器，并在 clean HEAD 重新执行本地增量入口。143 个业务入口的
当前候选页面、角色或办理旅程仍未执行，远端 PR CI、主线资格、部署和用户验收均未完成。

产品改动已提交为 `65a5eee7dbd7398c621e11a13a8162220dc52929`，并按该 SHA 重建
clean 前端，构建指纹为
`82fcb130f131581bef44578e0c6ed436f829dc56f3790e8bb7652b17a5224431`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，未使用 dev/sample/acceptance
  或客户数据。

在该 clean HEAD 上执行 `make ci.local.iteration`：47 个必需目标全部成立，其中
16 个本轮执行、31 个复用，8 个测试目标执行 486 项测试，5 项静态检查通过，
`unmapped_paths=0`，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261126T235008Z-1178188-562756328/receipt.json`

回执 SHA256：
`b5879247a069700d89ef42ff484f8aad4c44a62491d80520a6878a2bc288a2e2`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。

### 2026-11-27 FC-01 canonical selection 声明消费收口

继续核对 relation/selection 消费链时确认，V2 `fieldDescriptor.selection` 已经由解码器
校验并保留，但 canonical 表单投影只读取 `componentConfig.selection`。当选择项只存在于
描述符时，控件得到空选项；旧投影还会在缺少 label 时用存储 key 自造标签。这属于 P0
通用选择语义消费缺陷。

本切片完成：

- canonical/native 表单统一通过 `declaredSelectionOptions` 消费选择项；显式
  `componentConfig.selection` 优先，否则消费 `fieldDescriptor.selection`；
- 显式配置存在但 key/label 非法时停机，不静默回退到另一载体；
- selection 类型没有任何有效选项时抛 `ContractGapError`，不渲染空选择器；
- 选择标签只接受声明 label，不再把 storage key 当作用户可见标签；
- 增加描述符独有选择项、非法显式配置、完全缺失声明和静态回退守卫；
- `frontend_contract_basis_ledger.json` 新增 `fieldDescriptor.selection` 到
  canonical 控件的声明→消费→停机绑定。

`make ci.local.iteration` 在 `5da6f2521b60a4049aa115927bd10d9f9f91a06d`
加当前 owned dirty scope 上执行 29 个目标、复用 17 个未变目标，其中 19 个测试目标
共执行 727 项测试、7 项静态检查，`unmapped_paths=0`，全部退出零。原始回执：

`.runtime/frontend-dev-validation/executions/20261126T233447Z-1051376-403036631/receipt.json`

回执 SHA256：
`5aaa6d12d93e4536f26e824b059900da96241d618ec45b0f5e8ae9a603cc7a5e`。

该证据只证明当前 dirty 候选的本地精准消费与治理检查。产品提交后仍需按新精确 HEAD
重建 clean 前端与 Odoo 容器，并在 clean HEAD 重新执行本地增量入口。143 个业务入口的
当前候选页面、角色或办理旅程仍未执行，远端 PR CI、主线资格、部署和用户验收均未完成。

产品改动已提交为 `7d48d24a48ffab4084eb77f5d90a53f9583411a4`，并按该 SHA 重建
clean 前端，构建指纹为
`84697fd54e2a17475d86edf5cdd6520c6467963b496335ff24a30ee50a1d5f5d`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，未使用 dev/sample/acceptance
  或客户数据。

在该 clean HEAD 上执行 `make ci.local.iteration`：46 个必需目标全部成立，其中
16 个本轮执行、30 个复用，8 个测试目标执行 485 项测试，5 项静态检查通过，
`unmapped_paths=0`，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261126T233812Z-1080079-514198129/receipt.json`

回执 SHA256：
`cbe16d769b49789d2c9e7d5f40c1f6bcac4575f23d73f2a1b7bb47861b00292d`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。

### 2026-11-27 FC-01 collection component identity 消费收口

继续检查 V2 列投影时发现，字段描述符已经携带 `componentKey`，但列表列投影只允许
`sc.value.duration` 与 `sc.value.percentage` 两个身份，其余已登记身份会被静默清空。
这会让状态等通用展示控件退化成无身份的值渲染，属于 P0 前端契约消费缺陷。

本切片完成：

- 列投影使用既有的 `isRegisteredComponentKey` 语义注册表校验声明身份，已登记身份原样
  保留，不再维护局部产品身份 allowlist；
- 未登记但已声明的身份抛 `ContractGapError`，不静默丢弃、不从字段类型或标签猜测替代；
- 增加 `sc.display.status` 身份保留、List selection 标签消费和未知
  `sc.unknown.component` 停机的区分性用例；
- 静态守卫禁止重新引入 duration/percentage 局部 allowlist；
- 重新生成 component-driver takeover inventory，记录变化后的生产源码输入摘要。

`make ci.local.iteration` 在 `757b84dcf183946a42f0d1ce1fb3c8ec866fbd02`
加当前 owned dirty scope 上执行 25 个目标、复用 21 个未变目标，其中 16 个测试目标
共执行 671 项测试、6 项静态检查，`unmapped_paths=0`，全部退出零。原始回执：

`.runtime/frontend-dev-validation/executions/20261126T232422Z-959415-419794986/receipt.json`

回执 SHA256：
`092b283a3941dfbad38f8982f558455954073ace75dd8909fd079f8d313bd230`。

该证据只证明当前 dirty 候选的本地精准消费与治理检查。产品提交后仍需按新精确 HEAD
重建 clean 前端与 Odoo 容器，并在 clean HEAD 重新执行本地增量入口。143 个业务入口的
当前候选页面、角色或办理旅程仍未执行，远端 PR CI、主线资格、部署和用户验收均未完成。

产品改动已提交为 `b3598c112f35a6e0676e4744ea16239092cc950c`，并按该 SHA 重建
clean 前端，构建指纹为
`fe998421ada71ca76b1547224569dc427975321abbbc21b3de597dad62f72f65`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份，未使用 dev/sample/acceptance
  或客户数据。

在该 clean HEAD 上执行 `make ci.local.iteration`：46 个必需目标全部成立，其中
16 个本轮执行、30 个复用，8 个测试目标执行 484 项测试，5 项静态检查通过，
`unmapped_paths=0`，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261126T232923Z-1004249-565697291/receipt.json`

回执 SHA256：
`7e890da06a4a354f5f890f5b59585e5fb0eaf7f5fbffa3558ce75a8ae222e8a0`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。

### 2026-11-27 FC-01 percentage/duration 单位消费收口

继续按 P0 描述符条件规则核对时发现，percentage/duration 虽要求声明
`digits` 与 `unit.kind/code/label`，V2 解码器也执行一致性校验，但前端业务值只读取
`componentKey` 和精度；duration 仍按硬编码算法折算成“小时/分钟”，忽略了声明单位。

本切片完成：

- percentage 与 duration 都必须消费合法声明单位；缺失或 kind/code/label 不一致即
  `ContractGapError`；
- duration 按声明 `digits + unit.label` 呈现，不再自行把十进制工时折算成硬编码分钟；
- V2 normalized store 补齐 `digits`、`unit`、`temporal` 描述符透传，避免列投影丢语义；
- 表单、专业控件、列表、看板、主从明细和页面块指标均保留声明单位；
- 增加 percentage/duration 缺单位、duration 缺精度、声明精度与标签的区分性用例；
- `frontend_contract_basis_ledger.json` 新增声明的单位绑定；
- 选中并执行 `standard_collection_composition.unit`，其语义标签矩阵同步改为声明输出。

`make ci.local.iteration` 在 `a6f9f264be0d9f1afcc848fe4f84a35609a13396`
加当前 owned dirty scope 上执行 44 个目标、复用 2 个未变目标，本轮执行 1071 项测试，
全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261126T231335Z-884622-163141097/receipt.json`

回执 SHA256：
`6b3a88ac3c3a0cd32d0b154143258c387adfab80aab53e0cb20474962b3a5def`。

产品改动提交后仍需按新精确 HEAD 重建 clean 运行态。远端 PR CI、主线资格、部署和
用户验收均未完成。

产品改动已提交为 `8b7292830f63f58c3ecee5689047bfac8924e9ed`，并按该 SHA 重建
clean 前端，构建指纹
`d48e6857e7f90acfdef5f3dc542ae57de6d3c6754d657ffa86ea3a015c95d099`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA 与构建指纹；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health`、`local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份。

在该 clean HEAD 上执行 `make ci.local.iteration`：46 个必需目标全部成立，其中
16 个本轮执行、30 个复用，执行测试 483 项，退出零。回执：

`.runtime/frontend-dev-validation/executions/20261126T231905Z-923969-285675006/receipt.json`

回执 SHA256：
`9c19a6f252157767b4540dd313a10d522f15bbf5d6a5e06c58ef244ae09432e6`。

仍未执行 143 个业务入口的当前候选页面、角色或办理旅程，也未完成远端 PR CI、主线资格、
部署和用户验收。


### 2026-11-27 开工条件回读

主线 `a92114f0efb6733253d827e3a9985af21ab96be6` 已通过六项完整审计，证据为 `.runtime/main-full-release/a92114f0efb6733253d827e3a9985af21ab96be6.json`。此前源码观察保持原身份，不改写为新主线证明；正式启动时仅复核已变化的观察输入。专题仍为 planned，实施未开始，当前只恢复准备文件。

### 2026-11-27 canonical 字段语义只读正式契约

后端 strict component 已完成语义化，因此前端不再从 `componentConfig` 读取业务字段语义。
这里只有一份业务权威：后端 `fieldDescriptor`。前端实现注册表只负责把这些语义映射到本地组件；
`componentConfig` 可以继续承载传输和瞬时运行值，但不能提供或覆盖字段类型、语义、关系、
选择项、精度、单位、时区、domain、context、relationEntry 或 widgetOptions。

本切片完成：

- V2 normalized store 只从 `fieldDescriptor` 构造字段描述符；
- canonical presenter 只从 `fieldDescriptor` 读取 `fieldType`、`semanticType`、
  `currencyField`、`size`、`widgetOptions` 和关系目标；
- canonical renderer 只从 `fieldDescriptor` 读取类型、语义、选择项、精度、单位、
  时区、关系、widget 与文件名；
- Contract V2 widget → native bridge 与 ActionView 列投影不再把
  `componentConfig` 作为字段语义 fallback；
- 前端 `semantic_registry` 继续是唯一组件实现选择器：后端仅声明
  `semanticType/fieldType`，前端据此选择组件并校验能力、呈现模式和契约版本；
- 契约测试夹具全部迁移到正式 `fieldDescriptor`，并增加“组件配置不能覆盖
  canonical semantics”的负例；
- `frontend_contract_basis_ledger.json` 新增 canonical 字段语义载体绑定，目前为
  33 个绑定、0 个未闭合缺陷。

dirty 候选上的 `make ci.local.iteration` 执行 27 个目标、复用 21 个未变目标，
16 个测试目标执行 655 项测试、6 项静态检查，`unmapped_paths=0`，全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T025952Z-2596075-738421512/receipt.json`

回执 SHA256：
`6d29c6eb8635a2067b6f0a2edbd149e32c19413f27a2049b02416c37f2d641be`。

产品改动提交为 `0b4fdca10ca4721c95c6980ce6b0b0c9c02f7979`。按该 SHA 重建 clean
前端，构建指纹为
`c6a351a580041ed577bde8a839b189e9a4fd0c10064e5a5cf3cd35b5880257bc`。

clean 运行态回读：

- `/t/clean/api/runtime-version` 同时返回上述源码 SHA、构建指纹、`sc_clean`、
  namespace `ns_c6fed472e939` 与 alias `clean`；
- 根路径 `/build-info.json` 返回同一源码 SHA；
- `local.clean.health` 与 `local.clean.entry_identity.verify` 均通过；
- project/database/dbfilter/namespace 保持 clean 专属身份。

在该 clean 精确 HEAD 上执行 `make ci.local.iteration`：48 个必需目标全部成立，其中
19 个本轮执行、29 个复用，9 个测试目标执行 556 项测试，5 项静态检查通过，
`unmapped_paths=0`，全部退出零。回执：

`.runtime/frontend-dev-validation/executions/20261127T030434Z-2634508-474197078/receipt.json`

回执 SHA256：
`d8430d3d1b0b0b07cad114933f6a24d483a453cebefdba3275316075fa54b706`。

143 个业务入口的当前候选页面、角色和办理旅程仍未执行；远端 PR CI、
`bfc954c0b` 上的主线全量资格、部署和用户验收均未完成。
