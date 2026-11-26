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
