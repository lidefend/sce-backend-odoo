# 场景化后表单与系统运行效率专项（2026-11-14）

专题编号：`SCENARIO-FORM-PERFORMANCE-20261114`。唯一结果索引：
`.agent/runs/SCENARIO-FORM-PERFORMANCE-20261114/run.json`。

## 当前轮次：R2 实施与验证

第一轮 PR #886 已合并到 `5d631f6dd304a003f09c72e7de22fde45b8c3dbc`，并已通过既有受管入口部署日常开发服务器。
部署后实际浏览器项目表单检查通过（桌面/手机，8 项记录断言），但仍有等待：初始化请求约 2.55–4.68 秒，主表单契约首次约 1.59 秒、热缓存约 0.75 秒。
这些是单次接口观测，不是点击到可交互时间，也不是同条件 A/B 收益。
部署与原始浏览器证据索引位于本专题 `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/` 的
`deployment-result.json`、`deployed-project-browser.json` 和 `deployed-project-observation.json`。

第二轮复用当前主工作区，分支 `fix/scenario-form-performance-r2-20261114`，基线为上述合并提交。
当前是已修改、未冻结候选；日常部署仍是第一轮主线版本。其他工作树不在本轮范围内。

本轮产品修改：

- P0 `smart_core` 初始化机制在事实生产前计算消费范围，通过独立 context 覆盖服务端集合消费标志。
  P1 `smart_construction_core` 仅在显式 false 时跳过任务、付款、风险、项目、首页对象集合；角色入口、首页块和企业事实仍生成。
  boot 显式请求 workspace、preload/debug 和无标志旧调用保持原行为，原请求参数不被修改。
- P1 场景目标映射读取同源声明 hook，空列表是权威空；非列表或旧 hook 缺失才使用兼容加载器。
  映射仍附加到已授权导航，歧义排除及最终路由校验保持。
- P0 仅在原有 assembled 缓存写入资格成立时复制节点验证快照；位置仍在节点校验之前，所有校验继续执行。
  内部 cache version 更新为 v39，源摘要同步；不涉及对外 schema 或数据库迁移。
- 通用 Vue 组件依据契约字段 type/name 调度，仅 one2many 准备子列契约；many2many 不再发出该无用准备请求。
  不修改标签、附件读取/下载、候选查询和行内编辑机制。

Formal Product Layer / Layer Target：P0 通用初始化、契约与 Vue 消费；P1 行业事实生产和场景映射；P4 既有测试及增量选择器接入。
这些是标准机制的冗余消除，不是客户偏好；不以 P2/P3 配置、前端模型特判或放宽权限替代修复。
影响面限于无 workspace 的 boot、场景目标索引、不可缓存契约快照、many2many 准备调度。
排除隐藏 notebook 卸载/延迟加载、新共享缓存、source-only 缓存读取、其他工作树和未验证的 R2 部署。

现有回归已扩展并执行：初始化语义 23 项、事实合并与生产 4 项、场景投影 19 项、契约边界 167 项；
实际 SFC 挂载 43 断言，继续覆盖附件读取、下载错误、迟到响应和明细分页。
快照测试执行实际 AST 校验区段，覆盖复制次数、校验顺序、快照隔离和节点/能力/引用拒绝；不是完整 ORM 请求或性能测试。
初始化事实测试执行真实生产函数并以 stub 隔离 ORM，不能据此给出 SQL 耗时收益。
新增快照测试首次错误定位包装函数，修正测试选择后通过，原失败日志保留。
增量检查首次发现事实测试未映射至 Make 入口；已接入现有导航测试并登记关联组件挂载测试，选择器 136 项单测通过。
首次 ORM 实际 guard 通过 55 项，但执行期间文档/run 更新触发全树身份变化，整体回执失败；原始回执保留，不能作为成功证据。
后续在源文件与元数据稳定后重跑，期间不再写入受管源文件。
日常原始响应进一步确认 project.tags 为 many2many，collaborator/responsibility 为 one2many；本批预计只消除标签的无用准备，实际请求变化仍待复测。
稳定源文件重跑的 `make ci.local.iteration` 已执行并通过全部 25 个受影响目标。
三次隔离 ORM 回执分别为 55、1、1 项，源文件、配置和镜像一致，进程与结果守卫正常；不改变原失败回执。
严格类型检查、实际 SFC 挂载、场景/导航边界与 v39 缓存输入摘要守卫均通过。
原始日志、单目标回执和未覆盖范围以 run 的当前结果为准。尚未完成第二轮主线集成、部署及同环境 A/B 性能验收。

已有日常原始响应还提供了阶段证据：四次 boot 的事实生产分别为 51/26/23/25 ms，
`build_scene_runtime_surface` 为 1222/1821/1575/1447 ms。后者包含 `EffectiveDeliveryService.resolve()`、
上下文准备、surface builder 及结果整理，不能全归因于场景加载，也不能与其内部子阶段相加。
这说明五集合剪枝并不能解释为消除了秒级主要瓶颈。下一轮应复用现有 startup_subtimings，先拆分
`effective_delivery_resolve`、`prepare_surface_context`、`scene_runtime_surface_apply`、`finalize_surface_result`，
取得实际样本后再决定复用边界；本轮不追加共享缓存或放宽权限。

回退：按本轮产品补丁整体撤销，契约 cache version 与固定摘要一起恢复；无产品数据迁移。
以下保留第一轮研究与执行历史，历史的“未部署”等状态仅描述当时轮次。

## 当前实测：日常服务器慢请求

UTC `2026-11-13T17:09:58`（北京时间 11 月 14 日 01:09:58）只读读取既有 Odoo 日志尾部，
截取近 30 分钟 `/api/v1/intent` POST 记录；保留时间、状态、SQL 次数、SQL/其他耗时，不保存请求体或凭据。
原始脱敏汇总：`.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/daily-request-summary.json`。

| 指标 | 观测 |
| --- | ---: |
| 可解析请求数 | 532 |
| 服务端耗时中位数 | 234 ms |
| 服务端耗时窗口 P95（nearest rank） | 11,020 ms |
| 服务端最大耗时 | 13,961 ms |
| 超过 1 秒 | 183 / 532 |
| SQL 次数中位数 / P95 / 最大 | 66 / 3,244 / 7,739 |
| HTTP 状态 | 200: 494；400: 29；403: 7；401: 1；422: 1 |

最慢记录：UTC 17:04:38.758，HTTP 200，3,244 次 SQL，SQL 5.513 秒、其他 8.448 秒。
多条邻近请求同为 3,244 次 SQL，总耗时 13 秒上下；UTC 17:04:47.966 同查询次数的一次请求仅约 2.229 秒。
这提示固定的大量工作与并发/排队放大都值得追查，但请求次数相同不能证明相同 intent 或相同业务对象。

保证边界：这是日志尾部可解析的混合请求窗口，可能包含自动验证流量；不包含浏览器、网络和渲染耗时；
尚无 trace 到菜单/记录/账号的关联，不把错误响应视为性能通过，不据此证明全部表单根因。
服务端耗时按现有日志末尾 SQL 秒数与其他处理秒数相加，未把嵌套阶段计时重复相加。

同次附近只读环境观察：load average 0.12/0.41/0.55，内存 available 约 3.2 GB，swap 使用 0；
日常 Odoo、Nginx、PostgreSQL 均 healthy；瞬时 CPU 很低。没有观测到持续资源耗尽，不能排除此前峰值竞争。
日常源码挂载 `/mnt/source-addons` 只读，前端来自 `frontend/apps/web/dist-dev`；后续浏览器已回读实际 bundle 摘要（见下）。
身份原日志：`.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/daily-readback.log`。

## 源码调用链与证据分级

```text
点击场景 → SceneView.resolveScene
  → 需要详情时 system.init(scene_key, scene_ready_mode=full, with_preload=false)
  → 场景目标/嵌入页面 → 表单 loadContract(ui.contract.v2)
  → scene_key 存在时场景绑定校验 → 场景配置投影 → 契约缓存/组装
  → 解码/建 store → loadRecord（只读 mainData 覆盖时复用，否则 data read）
  → 主体 status=ok → 后台已选关系标签 → 可见 one2many 明细
```

这是一条可能路径，不表示每次表单进入都会执行全部节点；直接记录入口和已补全场景应分别测量。

| 优先级 | 源码确认事实 | 待验证假设与下一步 | 归属 |
| --- | --- | --- | --- |
| A | `SceneView.vue:564` 场景详情补全调用 `system.init`；`:919`、`:931` 等待补全后才继续解析；仅记录最后一次完整场景 scope | 切换 A→B→A 可能重复启动链。抓取补全次数和等待时间，确认相同 epoch 下复用/失效语义 | P0 前端机制/P1 场景消费 |
| A | `system_init.py:1253` 构建导航、`:1319` 装载能力；关闭 preload 并不跳过这些阶段 | 场景定向补全仍支付全局初始化成本；测 navigation/capability/scene 各段，评估复用现有权威快照或收窄服务路径 | P0 |
| A | `ui_contract_v2.py:340` 带 scene_key 时调用完整场景 provider；`:691` 在契约缓存查询前校验 | 高 SQL 是否来自此处；按相同合法入口对照并保留发布/授权语义，记录场景加载次数 | P0/P1 |
| A | `scene_registry.py:438` 读取声明后逐场景过滤 tiles；`:456` 合并 DB、导入、内容注册和资产声明 | 单记录开表单是否遍历所有场景/卡片；拆分只读绑定身份和完整呈现投影的成本，禁止新增平行权威 | P1 |
| B | `useRecordPageLifecycle.ts:458` 先契约后记录；`:380` 已对只读 mainData 做完整性复用 | edit/create 与 readonly 分开统计，不盲目并行未知字段/权限依赖；评估契约内数据覆盖和重复读 | P0 |
| B | 同文件 `:464` 辅助数据后台加载；`:542` 先选中关系标签再可见明细；关系字段内部 Promise.all | 主体可见与可编辑分开计时；关系读扇出可能与其他请求竞争，需按实际字段/明细数归因 | P0 |
| B | V2 client 解码并建立 store；新建缓存路径 JSON 克隆 snapshot/rawBody，action 路径直接请求 | 测响应字节、JSON parse、解码、store、长任务与 DOM；没有 CPU trace 前不宣称渲染是主因 | P0 |
| C | 当前系统健康与资源瞬时采样正常，慢请求仍有大量 SQL | 在复现窗口采集 SQL fingerprint/重复次数、并发与等待；有证据后才考虑查询批量化、索引或容量配置 | P0/P1/P4 |

已存在的请求去重、只读 mainData 复用、辅助数据后置和请求作用域缓存不重做。
不得以删除 scene_key、跳过 ACL/公司/发布校验、全局缓存授权或延长 TTL 换取假改善。

## 历史基线与观测能力缺口

- `docs/ops/audit/system_performance_baseline.md` 是 10 月 17 日受控探针基线；不代表当前浏览器体验。
- `docs/ops/iterations/capability_load_performance_20261110.md` 在候选 `b121f66de6ec20e7cea11301b03789e3323f04aa`
  记录付款详情中位数 373 ms、新建 1218 ms、登录 2051 ms。仅作定位线索；环境、入口和源码不一致，不能直接计算本轮回退比例。
- 现有 `local.dev.runtime.record_form.probe` 固定 `sc_dev_demo`、finance demo、action 878、6 次热样本，参数无 scene_key，
  且不含 HTTP/序列化/浏览器；不能覆盖本次日常服务器场景路径，因此本轮不运行它冒充用户复现。
- 现有探针单测 `make verify.system.performance.baseline.unit` 本轮真实执行 72 tests、PASS；这是工具验证，不是产品性能通过。
- 原日志缺少可直接关联的 intent 名称与阶段耗时；不能按时间邻近猜测 trace 归属。

## 分批执行与验收

1. **PERF-01 日常基线与归因（当前）**：复用日常现有浏览器认证/验收入口，绑定实际 bundle、源码、数据库、普通业务角色、公司和记录；
   捕获点击、首个请求、各请求等待/TTFB/下载、契约解码、主体可见、表单可交互、关系明细完成。关联 trace 与 SQL 次数；
   先选项目、合同、付款三类表单，至少含简单与明细较多各一例。不得手工借用本地 demo 凭据。
2. **PERF-02 场景公共开销**：仅对 PERF-01 证实的最大公共成本修复；优先目标为场景定向解析、同请求重复事实复用、批量权限/目标解析。
   每项提交记录调用次数与 SQL 的前后变化，契约结构/授权/拒绝结果保持等价。跨请求缓存必须先给出完整失效方案。
3. **PERF-03 表单读取与渲染**：按实测优化重复读取、关系请求调度和大契约解析；契约仍决定字段、权限、状态、数据依赖。
4. **PERF-04 回归与持续预算**：将场景入口、新建、已有表单、A→B→A、公司切换接入现有定向性能探针，形成可追溯趋势。

验收矩阵：冷启动与热打开分开；原生入口与场景入口必须为同一合法目标；readonly/edit/create 分开；
普通角色与另一权限角色分开；当前公司切换、权限撤销、场景发布撤销、快速切换/取消请求必须保持拒绝与数据隔离。
受控比较同环境、同数据规模、同角色、同网络、同前端包；采样注明 n，热路径至少 20 次才作初步 P95，
小样本只报告窗口分布，禁止把 6 次最大值宣传为稳定尾延迟。配置变动、负载与冷缓存状态单列。
沿用既有详情中位数预算 1200 ms、新建 1600 ms、登录 3000 ms、公司切换 2000 ms；
这些是既有受控探针预算，日常完整浏览器 SLA 必须明确操作边界后判定，不改阈值求通过。
成功条件是同口径点击到可交互改善、慢路径 SQL/重复调用下降、语义回归通过，不以单个函数变快收口。

## 第一批实现与浏览器归因

日常原有版本的项目表单（project.project，record 1，action 588，menu 382）在 1440/390 两个视口完成
8/8 路由、契约、渲染器、返回来源断言，无运行时错误。该结果只覆盖项目代表页，不代表全部表单。
`daily-browser-timed.json` 保留 51 条请求计时和 trace；完整初始化请求浏览器耗时约 1.96–3.28 秒，
两条契约请求约 1.43/0.99 秒。此为小样本请求耗时，不能相加当作点击到可交互时间。
运行身份为 daily/sc_demo/demo/ns_000000000002；实际前端摘要
`28294465acb972c9f60f99934c3f81b28a2e603852cdc654fc954be9bbe6c074`。

明确的重复开销：后端 `scene_shell_compiler.py` 声明 `meta.content_kind=native_delegate`，
项目入口没有 blocks 是完整原生委托声明；SceneView、ActionView、useRecordContractSemantics
却均以无 blocks 为理由请求 full system.init。三处统一消费现有 content_kind，原生委托不再补全；
设计型场景及未知类型保持原有补全路径，不增加模型特判或前端业务默认值。
新增单元断言覆盖原生/设计型/未知内容类型与有无内容的组合。实际浏览器候选调用次数仍待验证。

契约绑定原先调用完整场景 provider，其中逐卡片计算访问投影；绑定校验只消费目标身份。
改用现有 `smart_core_delivery_scene_declarations` 同源有效声明接口；未安装该扩展时保留原 provider，
空声明不回退旧内容。校验器及后续权限/发布/记录访问机制保持原样；新增拒绝和兼容性用例。
装配缓存版本升至 v38 并重签输入摘要，防止旧缓存掩盖变更。

system.init 的 `build_scene_runtime_surface` 阶段观测约 1.48–3.32 秒，但该阶段还包含
`EffectiveDeliveryService.resolve`，不能归因全部为场景 shell 构建；后续应进一步拆分测量。

P4 工具修复：只读拦截器补充已存在的只读 `workspace.scenario.projection.get`，
继续拒绝 activation/projection 的写请求；增加脱敏请求时序记录，不保存凭据或请求数据。
首次浏览器失败原因为此拦截器遗漏，修复后 8/8 通过，原失败报告保留。

## 验证、限制与下一步

- 全部结果、原始日志和失败恢复索引以 run.results 为准；最新增量验证处理全部 20 个映射目标。
- P0 后端边界测试、同源声明测试、前端场景契约测试、严格类型检查和契约依据检查已执行通过。
- 首次实现增量检查因装配摘要变化失败；已提升版本和重签，复验通过，不删除失败记录。
- 日常浏览器基线通过；候选浏览器及端到端 A/B 未执行。现有候选静态服务要求 clean 精确 SHA，
  当前 dirty 状态不满足，未绕过入口或把基线冒充候选。
- 合同、付款、创建/编辑、角色/公司切换、权限/发布撤销及稳定 P95 尚未验收。
- 本地改动未提交、未推送、未合并、未部署；专题保持 verification_pending，不能称批次或产品验收完成。
- 回退：撤销本专题 P0/P4 改动，缓存版本与装配摘要一并恢复；本轮无数据库写入。
- 下一步：候选收敛并冻结后，经既有 local.dev 候选入口验证三处不再多发 full system.init、设计型场景仍补全；
  再在选定日常发布版本进行同入口、同角色、同记录的前后测量，扩展到合同/付款及热路径至少 20 次。
  在此之前不声称秒数收益或全系统问题已解决。

## 候选浏览器复验推进

继续使用 P4 既有 local.dev 候选浏览器入口，追加每个页面阶段的脱敏 intent 计数、请求完成耗时，
并允许代表入口断言定向 full system.init 次数。只记录 intent、scene_key、模式与耗时，不保存登录请求体。
候选工具原本未被增量规划覆盖；补齐 static_proxy_target 单测入口及规划映射，17 个既有工具测试通过。
新增观测不会改写业务数据。原生项目入口先覆盖场景→列表→记录→返回；设计型场景随后按真实可用入口补全。
本地提交用于候选浏览器身份绑定，不代表最终交付冻结、远端集成或部署。前次未提交状态为历史阶段；
最新候选 SHA、运行时回读及浏览器原始结果保存在当前 run 引用的忽略证据目录。

候选 c754960051657b8ac3ecde8a7157dde482574265 已完成构建与本地服务身份回读；
首次启动因同工作区旧静态服务 SHA 拒绝，受管 down/up 后恢复。提交 hook 的四份派生报告均已审阅，
仅对应行数、位置及内容摘要变化。日常服务未变更。

浏览器结果为失败，不得按单测通过收口：默认 system_admin 无项目台账；demo_pm 的真实角色
为 project_member，只有我的工作入口。改选已授权的原生用户管理场景后，列表就绪断言仍超时，
只读诊断捕获一次定向 full system.init；原因仍待追查。两角色首页对照通过且业务 mutationCount=0，
这只证明基础认证与初始化可用。P4 工具补充脱敏场景身份及异常时保存 execution.json，避免超时丢失现场。

后续校正：用户管理存在 enterprise.user 声明，不能由菜单 XMLID 猜测原生场景 URL。前述超时保留失败，
归为入口身份未证实；既不能说性能通过，也不能据此断言候选产品回归。下一次使用启动响应中的准确场景身份。

## 本次续跑的最终结果

浏览器源码候选：6b8382da77ce4cfef6bbe084f5c911538184a041；前后端、数据库和 filestore 已绑定同一受管本地环境。
产品代码与 c75496005 相同，后一提交只补充 P4 失败现场与声明身份记录。

- **原生列表/表单往返通过**：启动响应明确声明的 `entry.smart_construction_core.menu_sc_product_data_permission_v1`，
  system_admin，res.users record 8，桌面/手机均完成列表→表单→返回；各视口 full 场景补全为 0，
  浏览器错误 0、业务 mutationCount 0。原始结果 `candidate-native-record/summary.json`。
- **原生空列表通过**：编号规则实为 0 条数据，正常 empty 状态，补全 0 次。先前要求 ok/非空导致超时，
  不是产品挂起。`candidate-native-state/summary.json` 保留准确状态和截图；不把空列表当作表单往返。
- **设计型补全保留，但整页验收失败**：enterprise.setup 桌面/手机各 1 次 full 请求（约 2270/1914ms），
  SceneView ready，运行错误 0、业务 mutationCount 0；两视口 H1 数量均为 0，工具整体 FAIL。
  不降低标题断言求通过，不把局部调用行为成功冒充整页成功；标题缺口需回声明/呈现归属层处理。
- **入口失败已归因**：本地项目角色/菜单与日常不同；用户管理实际为 designed_scene enterprise.user，
  原生推定 URL 不存在。工具现在记录声明路由与类型，后续入口均取启动契约。

最新 25 项映射的增量执行通过；诊断补充工具 17 tests 通过。原始失败与恢复记录均保留在唯一 run 索引。
本地候选静态服务和后端目前运行 6b8382da7；未执行数据库升级/重置/权限修复，未推送、未合并、未部署日常。
本次证据仅证明通用原生路径消除重复补全及设计型补全仍存在，不可跨环境计算日常提速比例。
专题仍 verification_pending：补齐设计页呈现检查，按受保护流程集成首批改动后，在选定日常版本测量项目/合同/付款
同入口同角色数据；热样本至少 20 次，另测创建/编辑、角色与公司切换。

## 标题缺口收口

P0 通用 SceneView 的独立办理入口区域原先使用固定“综合办理”三级标题，无页面一级标题。
现改为 H1 消费已解析的后端 scene.label；不新增业务标签、模型特判或默认产品语义，
不影响原生委托、嵌入列表/表单与补全调度。模板变化的组件驱动清单摘要已按既有生成入口刷新。
前次原生往返结果依赖未变；本轮仅重验设计型企业初始化的标题与补全，保留原始 H1 失败记录。

标题复验候选 `259d196df90c5bd7805e0c6d1c271387084a2e44`：桌面和手机均 H1=1、
定向 full 初始化=1、页面 ready、横向溢出=0、运行错误=0、业务 mutationCount=0，浏览器整体 PASS。
截图确认标题为契约声明的“企业初始化”。此范围不包含异步企业诊断/场景激活子面板完成断言。
最新 25 项增量检查 PASS；原生表单证据依赖不变（本次只改 handlingEntryGroups 有内容的区域），
保留并复用原始 6b8382da7 的两视口往返结果。首批本地定向验证已收口，日常收益验收仍未进行。

发布前仍需独立的精确候选复核与证据归档；作者自检不能代替独立复核。
远端 origin/main 只读回查仍为 f4f87939bcafcd35a5a0b18017b36464056a78e9，未发现基线漂移。
主线集成、日常部署与用户验收均未完成。

## PR #886 CI 崩溃诊断续跑

正式 COMMENT review 绑定 c101d7464dbfde82e8d525f3c3679220bd00fb12；未确认 P1/P2 源码问题，
但 professional_quality_gate 与 merge_policy_gate 失败，public_guard 与 frontend_release_gate 成功。
独立核对全部四个 shard：冻结 13 模块，成功 receipt 12 模块，唯一缺失 acceptance fixture。
覆盖集合拒绝符合预期，不能补造回执或将计划 192 项称为通过。底层退出 139 被 make 包装为 2，
现有自动重试没有触发；原始崩溃原因尚无栈证明。

P4 最小诊断仅保留 scripts/test/test.sh 中容器 PYTHONFAULTHANDLER=1；不改变产品行为、
测试选择、重试或覆盖规则。local.test/sc_test 临时同样启用诊断后执行 acceptance_fixture_gate，
实际收集 7 项（四项 guard、三项冻结测试），全部通过且退出 0；源码、镜像、profile 均未漂移，
一次性测试容器已清理。本地诊断开关随后恢复，原始回执位于
.runtime/test-baseline/1794596361693371600/receipt.json。该运行未复现，不证明 CI 偶发或已修复。

受影响 runner 单测 14 项、依赖准备单测 8 项通过。组合 lifecycle 单测 51 项中 2 项失败：
未修改的 local.clean 测试仅提供 ENV 输入，缺少其脚本读取的入口变量，pipefail 提前退出。
该失败保留为独立限制，未记为通过；不扩大本次崩溃诊断去修改其他环境工具。
临时 local runner 改动缺少增量映射的阻断也保留；恢复临时开关后按实际保留改动重新验证。

进程环境 patch 与后台线程交互仅为调查假设，不能在没有崩溃栈时宣称根因。
后续需在远端原有运行链采集诊断并完成全部冻结覆盖；主线未合并，日常未部署，A/B 验收未完成。

恢复临时开关后的 ci.local.iteration 26 项映射定向检查全部通过；仅表明诊断候选本地验证通过。

## 后端执行组织收敛

R7 保留为已有优化基础。后续按端到端契约生成成本推进，不再按单点热点决定顺序。

1. 原生视图、字段需求和定位索引贯穿契约链。
2. 记录读取依据明确消费者和依赖组织，同作用域业务结果复用。
3. 来源证明、当前记录求值与最终交付校验拆清。
4. 在前三批稳定后减少中间表示和复制。
5. 初始化有效交付先生产、后消费，并统一发布快照选择。

第一批范围：`app_view_config.py`、`native_view_parsed_cache.py`、
`native_view_projection.py`、`page_assembler.py`、最终节点校验及调用点。
完成条件是同一有效视图只解析一次，字段描述和定位索引复用，权限与拒绝语义不变。

初始化顺序原型不在这一批实施。其补丁保存在
`.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/backend-execution-order/deferred-init-order.patch`
（SHA-256 `18fc0862fef954822211a1567614c62504d307986c6342d559791e8f7fe4931e`），
待第五批重新确认后接入。

### 第一批结果：原生视图复用

- `_safe_get_view_data()` 保留 Odoo `models` 字段需求，并按当前模型的所需字段取得描述；
  only-needed 字段集合与解析结果存入 `RequestScopedCarrier`。
- carrier 同时以请求 view_id（默认 `0`）和解析后的 source view_id 记录同一对象，避免默认视图
  再次调用 `get_view()`。
- `project_native_view()` 优先消费 resolved view 的字段描述；只有在没有该事实时才调用
  `fields_get()`。
- 最终节点校验在 fresh/cached 两条路径都传入 request-scoped parsed view；模型、视图类型、
  locator 和字段索引由同一解析对象复用。
- assembled contract cache 从 v39 提升至 v40，输入摘要重签为
  `88faa40db054db7d18e2e9e4269e7c44f98e09d50e6714b36108a9ebc13499c3`。

验证：`verify.business_config.formal_list.unit` 287 项通过，
`verify.unified_page_contract.v2.assembler` 通过；隔离 ORM 的 carrier/最终校验 2 项通过，
原始回执 `.runtime/test-baseline/1794630004874637351/receipt.json`，源在运行期间未变化。

### 第二批结果：记录依赖与校验阶段

首批原生视图复用之后，记录读取改为服务明确消费者：

- 首次记录快照取既有种子字段和原生表单显式字段，不再按源字段顺序扩到预算上限。
- 最终 modifier 只补真正缺失的依赖；同模型、同记录、同 actor、同 context 复用当前请求
  recordset，并把缺失字段合并为一次批量 `read()`。
- 合并读取失败时仍逐字段回退，单个字段被拒不会抹掉可读兄弟字段，也不绕过 ACL 或记录规则。
- draft 表单继续使用现有 draft proof，不要求伪造已保存记录。

校验职责开始拆分：

- assembler 保留声明、来源、配置和 actor 字段/记录权限证明，不加载当前字段值，也不写回最终可见性。
- 最终 handler 仍执行当前记录求值、error activation/content 同批证明、最终可见性和引用校验。
- `validate_final_nodes(..., evaluate_runtime=True)` 默认兼容入口不变；显式
  `evaluate_runtime=False` 只用于装配阶段。

这一步起源于增量 ORM 暴露的真实回归：初版拆分把保存记录的权限证明放到了 draft 分支之前，
导致新表单被要求已有 record。修复为先识别 draft，再对已保存记录做权限证明，并加入 draft
回归测试。修复后 conditioned-feedback 的 26 个场景、34 项子测试为 0 failed / 0 error。

定向结果：

- 契约边界主套件 171 项通过；同目标的 53、62、5 项关联套件通过。
- 节点校验 32 项通过；native advisory 的 17 和 43 项通过。
- platform duty、产品菜单、场景中心、system.init 边界及 V2 action/assembler/runtime/status
  定向目标通过。
- 隔离 `sc_test` 的真实 ORM 3 项通过，回执
  `.runtime/test-baseline/1794632565043660383/receipt.json`，运行期间源未变化。
- `sc_dev_demo` 的 conditioned-feedback ORM 通过；页面 finalize authority ORM 1 项通过，
  回执 `.runtime/test-baseline/1794632178043540846/receipt.json`。
- assembled contract cache 提升到 v45，输入摘要重签为
  `9c564685159219081108b9bf08ae212e69ea4b6e55821a287e9da3ea2829e55c`。

`local.test` 按登记策略为每个 ORM 目标新建 `sc_test`，包括启动 Odoo、加载 77 个模块和生成
资源，因此单目标约五分钟。此次在已确认无关的 project-finalize/workspace-route ORM 前停止，
保留中断回执而不是把未执行目标记成通过：

- `.runtime/frontend-dev-validation/executions/20261114T043908Z-191136-733149811/receipt.json`
  为 draft 回归修复前的失败回执。
- `.runtime/frontend-dev-validation/executions/20261114T044839Z-244811-364447798/receipt.json`
  为修复后执行到 27 个目标后由操作者中断的回执；27 个已完成目标均通过。

未重跑项及原因：project finalize 不重定义页面结构，本次记录读取与校验拆分没有改变该规则；
workspace 路由权限不在改动面。实际表单 SQL 数、HTTP 耗时和点击到可用时间仍未测，
不能宣称本批性能收益。合并、部署继续暂停。
