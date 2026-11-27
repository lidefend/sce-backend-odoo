# E1：契约执行权全量源码扫描与主要操作链审计

基线：`0d17e91e7190e1a293e4e6ac969c39738a87218f`。状态：源码扫描已完成，架构候选；动态操作覆盖和性能收益 NOT_VERIFIED。未修改产品、Schema、缓存或数据库，未启动浏览器/ORM 验收。

## 1. 全量的含义和证明边界

对 git 跟踪的 `frontend/apps/web/src` 与 `frontend/packages` 中所有 TS/TSX/JS/Vue 文件做 AST 扫描，不抽样只扫命名为 Runtime 的文件。后端权威入口另建文件摘要清单。完整路径、行号、摘要、导入关系和未解析情况见 [inventory](e1_source_inventory.json)，可复现方法见 [method](inventory_method.md)。

| 项目 | 数量 | 含义 |
| --- | --- | --- |
| 前端源码文件 | 874 | 全量读取并记录内容 SHA-256 |
| 后端权威入口文件 | 85 | handler/controller/契约生成/缓存及幂等相关路径摘要；不是全后端语义证明 |
| 请求相关候选调用点 | 319 | 152 个传输名称调用、125 个 API 导入调用、25 个 API 同名回调候选、10 个契约运行器调用、7 个间接表达式候选 |
| 候选调用所在文件 | 94 | 传输包装、API、调用方可能重复计入 |
| 逆向导入闭包候选模块 | 164 | 模块级保守近似，不是运行时调用图 |
| intent 属性声明 | 94 个字面量、93 个动态值 | 包含声明与参数构造，不能当请求次数或独立 intent 数量 |
| TS 解析诊断 | 0 | 不证明类型完整、动态分支可达或回调效果已解析 |

不以静态扫描制造“全量业务审计完成”：Vue 模板执行、依赖注入、动态 intent、namespace alias 和第三方依赖尚有语义解析边界；即使相对导入闭包完整，也不能证明每次用户交互触发了多少请求。所有候选均保留 execution_proven=false。32 个回调/间接表达式候选应优先人工追踪，不得按名称直接判定为真实网络调用。

## 2. 真实源码链与裁定

路径均相对仓库根，摘要和定位见 inventory。VERIFIED 只用于静态事实。

| 操作族 | 已追踪链 | 事实与执行权结论 | 证据状态 |
| --- | --- | --- | --- |
| 契约读取 | v2/client.ts → intentRequestRaw → api/client.ts → intent_dispatcher → ui_contract_v2 | record-free create 有 snapshot/etag 条件；记录契约与动作加载仍走在线路径。不能把静态结构复用扩成记录权限复用 | VERIFIED |
| 表单加载 | useFormPageLifecycleRuntime → useRecordPageLifecycle.reload → loadContract → loadRecord | 生命周期已有 route/active/retained 判断；reload 有 in-flight 身份保护，不能笼统说每次激活都重复请求 | VERIFIED |
| 只读记录呈现 | loadRecord → readonlyMainDataCoversFields → 契约 mainData 或 readContractFormRecord | 数据覆盖字段时已有省读分支；字段缺失时的补读必要，编辑态不能按只读策略擅自放宽 | VERIFIED |
| 列表查询 | useActionViewLoadRequestRuntime.executeLoadDataRequest → loadAssigneeOptions → listRecordsRaw | 字段、域、上下文本地组织；查询、总数、分组和权限在线。经办人查询位于列表请求准备路径 | VERIFIED |
| 经办人选项 | useActionViewAssigneeRuntime.loadAssigneeOptions → listRecords → api.data | hasAssigneeField 守卫通过后每次调用均查询；未见该函数内按身份/内容复用。能否省读依赖准入和失效声明 | VERIFIED；收益 NOT_VERIFIED |
| 字段编辑/onchange | useRecordFormState → fieldRequiresServerOnchange → debounce/changedFieldSet → triggerOnchange | 已按契约筛选需要服务器联动的字段，并非所有输入都发 onchange；原生计算不可直接搬到浏览器 | VERIFIED |
| 草稿反馈 | useDraftFeedbackEvaluation → describe/evaluate → triggerOnchange | 300ms debounce、版本/上下文/序列保护已经存在；describe 依赖能否纳入静态资产需另证，evaluate 涉及当前草稿事实 | VERIFIED |
| 关系选择与新建 | useRecordRelationships/useRecordRelationshipNavigation → relation contract、查询、create | 本地选中/显示/集合编辑与在线权限、查询、持久化分离；关系新建不是 local 操作 | VERIFIED |
| 保存与业务动作 | ActionSemantics → record.save / contract.action / sceneMutationRuntime → intent | 参数组织本地；保存、审批、支付、配置授权由后端执行。payload_schema 不自动代表离线资格 | VERIFIED |
| 动作后刷新 | useActionViewActionRuntime.applyActionRefreshPolicy → projectionRefreshRuntime → load/sessionLoadAppInit | 未声明 on_success 时回退整页 load；不同目标按顺序执行，同名目标才去重 | VERIFIED |
| 初始化刷新 | ActionView.vue 注入 sessionLoadAppInit → session.loadAppInit → app.init | workbench 与 role surface 回调都可进入同一入口；session 只合并在途同 epoch 初始化，顺序完成的调用不因旧 Promise 自动复用 | VERIFIED；同一生产策略是否同时选择两者 NOT_VERIFIED |
| 客户端命令与本地呈现 | actionSemantics/pageContractActionRuntime/布局及格式化工具 | 返回、丢弃输入、导航参数、布局和纯输入处理已有本地执行能力；目的页读取另算 | VERIFIED |
| 输入暂存 | intakeAutosave → useIntakeAutosaveRuntime → browser_local_storage | create-only 白名单和恢复/丢弃，明确排除附件、子记录、业务状态等；不是待提交业务队列 | VERIFIED |
| 附件 | useNativeAttachmentRuntime → 当前页 File 暂存 / uploadFile / file intent | 成功上传项移出当前页队列；未证明崩溃恢复与持久离线幂等 | VERIFIED/NOT_VERIFIED 分项 |
| 导入、批量、导出 | api/data、executeButton、files、boqImportPreview → intent → 相应 handler | 文件准备和选中集合本地；服务端权限/原生向导/事务不能删除。各种 handler 的事务幂等统一性未完成运行验收 | VERIFIED/NOT_VERIFIED 分项 |
| 配置、角色与目录 | menuConfig/businessConfig/productSystemParameter/productCapabilityCatalog/platformCapabilityExplorer API → intent | 查看目录与修改配置不能混为 local；发布、审批、当前权限保持服务端权威 | VERIFIED（传输与 API 边界） |
| 协作、消息、工作台、遥测 | chatter/globalMessages/myWork/usage/telemetry API → intent | 读取和状态变更按真实操作划分；不因调用名为 refresh/read 就自动允许缓存 | VERIFIED（传输与 API 边界） |
| 认证启动 | services/accountActivation.activationRequest → /api/v1/auth/* | 实际存在独立匿名激活/找回/公开认证页面 HTTP 路径，不是行业业务第二执行器；规范需明确“业务统一通道”范围，不宣称全仓所有网络请求只有 intent URL | VERIFIED |

## 3. 第一批性能研究候选：不直接下放业务权力

| 优先级 | 候选 | 现有事实 | 省请求的必要条件 | 当前结论 |
| --- | --- | --- | --- | --- |
| A | 同一动作刷新事务合并相同初始化效果 | 两个 projection target 可映射到同一 sessionLoadAppInit，执行器仅按 target 名去重 | 找到真实生产 refresh_policy 同时触发的证据；确认两次之间没有要求重新裁决的身份/状态变化 | 最小运行器组织机会；尚未证明线上重复次数 |
| A | 经办人选项不随每次翻页/排序重复查询 | loadData 每次进入选项加载，守卫通过便请求 | 用户/公司/项目/域/字段身份完整；后端声明选项可复用及失效；不能以静态名册推断权限 | 声明＋运行器机会；不能直接加任意 TTL |
| B | 用精确刷新替代无策略整页 load | 缺 on_success 时整页刷新 | 生产者声明受影响投影，响应携带完整有效补丁或明确重读范围，证明其他事实不受影响 | 优先补声明，不把整页刷新直接删除 |
| B | 契约结构与记录事实分开加载 | reload 顺序读取契约及记录，当前缓存裁定保护动态权限 | 静态结构依赖闭包、权限/记录 overlay 与资产身份齐备；本轮缓存规范先裁定 | E2 研究，不能马上改为编辑契约缓存 |
| C | 反馈 describe 绑定纳入静态运行资产 | 描述与 evaluate 分离，已有 debounce/版本保护 | 证明描述不依赖实时权限/规则/记录，绑定可静态发布且正确失效 | 仍待来源审计；evaluate 不据此变本地 |

不能计算“319 个点里可去掉多少 HTTP”。当前可确认的是 3 类优先研究机会（刷新效果合并、选项查询复用、刷新范围收敛），不是 3 个已证实生产性能缺陷。没有测得可删除请求数、延迟下降或离线覆盖率。

已存在的能力不重复立项为收益：并发读取合并、recordViewLoadRuntime 的短窗口/在途去重、表单生命周期 retained 判断、只读契约 mainData 复用、按声明筛选 onchange、新建契约缓存、本地暂存和客户端命令。

## 4. 四项评审补充的落点

- 解释器/业务运行器：规范 §4.1；算子需登记、版本化、明确输入输出及副作用，不形成任意低代码业务引擎。
- Runtime Asset Integrity：规范 §5.1；结构、组件、算子、数据/字典依赖、可信来源与身份/用途同时有效。
- 状态语义：规范 §6.1；本地输入、传输受理、审批与付款事实分别表达，禁止泛化 success。
- 企业增量更新：规范 §5.2 与 E2；编译验证后原子发布/激活，保留未提交输入，按当前声明重验；不恢复旧协议兼容执行。

## 5. E1 后续闭环标准与暂停边界

源码扫描完成不表示 E1 的每个真实操作链都已验收。继续研究时应：

1. 逐一解析动态 intent、回调注入与 Vue 模板触发，将候选点连接到实际后端声明和 handler；标注无法证明项，不能静态默认为 local。
2. 从真实生产契约挑选列表翻页、同页返回、字段编辑、关系弹窗、保存/审批、配置发布等旅程，记录上下文、触发事件、完整依赖、实际请求身份及原因。
3. 对 A/B 候选建立请求预算和失效矩阵；比较相同事实输入下的重复读取，必须保留权限/公司/项目/记录版本变化时的必要重读。没有浏览器证据前不报节省比例。
4. 在所有者确认阶段范围后才开展 E2/E3；IndexedDB、队列、Schema 扩展、预编译及缓存实现均未授权。

本轮仅发布独立文档 Draft PR，不合并、不部署、不恢复主线 CI 收口。PR 平台自动检查与文档必要治理检查不冒充运行验收。原主线暂停记录保存在 `0ef40ca76709bac912f7a721a34ece11bc91142c` stash，原 runtime 结果索引不变；不丢弃该记录。
