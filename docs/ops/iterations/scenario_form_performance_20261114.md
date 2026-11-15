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

### 后端组件来源

最终节点里的“组件”不是后端临时发明的业务组件，也不是前端绕过契约自行推断的语义。
当前只有以下显式来源：

- 模型字段声明包含 `sc_feedback_usage`、且字段用于 `interaction` 时，
  `native_advisory.project()` 先验证精确 view XMLID、locator、occurrence 和原生条件，
  再把对应原生 host 投影为 `sc.feedback.message`。没有字段声明，不生成节点。
- 原生 legacy alert 只有在存在可解析内容来源、原生 locator 和显式可见条件时，
  `_project_legacy_native_layout` 才投影为同一 feedback 组件；CSS alert 本身只表示呈现，
  不推导业务严重度。
- record-error feedback 来自已复核的模型字段声明，激活字段、内容字段、依赖和审查证据
  必须同批成立，并在最终交付阶段读取当前记录。
- `sc.navigation.anchor` 只接受显式携带原生来源的节点，当前未发现通用后端自动生成路径。

因此本次优化复用的是这些已投影声明的来源证明，不增加新的组件来源。

### 第三批结果：最终声明证明复用

assembler 在 `evaluate_runtime=False` 时生成请求内 proof。proof 绑定模型、视图类型、
form view id、记录、draft 状态、actor、context 和原生树；每个 feedback 声明另按组件配置、
来源节点、条件及 container 唯一出现次数签名。

最终校验的行为：

- 声明和来源签名未变时，直接复用来源、native advisory/draft 和依赖计划，不再重复解析
  或重新执行静态来源检查。
- 最终树新增声明、修改组件配置、修改来源字段、造成 container 重复或请求范围变化时，
  只对该声明执行完整来源检查。
- 所有声明在最终阶段仍共用当前记录事实读取；error activation/content 仍由
  `validate_record_errors` 同批证明；最终可见性和裁剪后引用检查没有跳过。
- 跨请求缓存不保存该 proof。assembled-cache 命中仍重新做 actor 权限判断，不缓存授权结果。

验证：

- 节点校验 36 项通过，包括未变化声明跳过来源检查但读取当前事实、配置变化重验、
  来源字段变化重验、native feedback 依赖计划复用及 assembler proof sink。
- 契约边界主套件 171 项及关联 53、62、5 项通过；native advisory 17/43 项通过。
- V2 action/assembler/runtime/status、入口等价和表单结构 authority 目标通过。
- 隔离 `sc_test` ORM 3 项通过，回执
  `.runtime/test-baseline/1794633175389575442/receipt.json`，运行期间源未变化。
- conditioned-feedback ORM 26 个场景、34 项子测试为 0 failed / 0 error。
- assembled contract cache 提升到 v47，输入摘要重签为
  `bb900b00565a33dd0421ba206adfa2eec86a9eeaee77e4827ec265f997967bef`。

未测量 proof 复用带来的实际 HTTP 或 SQL 降幅。该批只证明重复静态来源工作被消除且
最终记录求值没有绕过。下一步进入中间表示和复制收敛；合并、部署继续暂停。

### 第四批结果：中间表示和复制收敛

native form 的 canonical 输入原先在 `deepcopy(marker)` 之外，又分别深拷贝
`fieldDescriptors`、`layout`、`capabilities`、`subviews`、`headerButtons` 和动作列表。
这些对象来自同一份 native marker，且 V2 builder 在真正修改节点前仍会建立自己的副本。

本批改为：

- 每个请求只建立一份隔离的 owned marker，canonical source 的 fields、form layout、
  capabilities、subviews 和 header buttons 直接读取这份 owned graph。
- 页面元数据、记录、搜索、权限、动作和 runtime 输入也使用该 owned graph，不在同一装配入口
  重复深拷贝。
- 输出节点继续走现有 `_normalize_native_layout_nodes()`、field widget 和 action builder；
  这些 builder 对将要修改的结构自行复制，因而最终 contract 不与输入共享可变节点。
- `form_governance` 仍从输入单独取得，因为它是 native marker 外的请求级声明。

新增隔离测试同时证明：

- 装配完成后输入 source 与装配前完全相同。
- 装配后修改 source 的 layout/descriptor 不会改变已生成 contract。
- 修改 contract layout 不会回写 source。

验证：

- mobile compact assembler 145 项通过；契约边界主套件 171 项及 53、62、5 项关联套件通过。
- assembler guard 通过。
- 隔离 `sc_test` ORM 3 项通过，回执
  `.runtime/test-baseline/1794633471640538460/receipt.json`，源在运行期间未变化。
- conditioned-feedback ORM 26 个场景、34 项子测试为 0 failed / 0 error。
- assembled contract cache 提升到 v48，输入摘要重签为
  `046e904b4d6d7154a9e90873082c6ef9b94f393ec90732c49ed5ba1bd10c7768`。

本批只证明同一 native marker 不再被多次完整复制，没有把复制次数下降换算成 HTTP 耗时。
下一步进入初始化有效交付的“先生产、后消费”顺序；合并、部署继续暂停。

### 第五批结果：初始化有效交付顺序

重新核对暂存原型后，只移植产品与测试 hunk，没有沿用原型中的旧分支/run 登记。

初始化现在按以下顺序执行：

1. 先解析身份和公司范围。
2. 在导航和能力消费者之前执行一次
   `EffectiveDeliveryService(env).resolve(params)`。
3. 能力注册表消费同一 `effective_delivery.route_authority`，不再为取得路由资格自行触发
   完整有效交付。
4. `NavDispatcher` 仍负责版本、兼容元数据和 legacy feature flags，但其独立生成的树在清洗、
   标签补全和指纹计算前被有效交付的 `nav` 替换。导航不再形成第二套上游事实。
5. 原有末尾的 role surface、默认落点和 scene 处理读取同一个 effective delivery 结果。

兼容边界：

- P0 capability provider 先把 `published_authority` 传给扩展 hook；旧 hook 不接受该关键字时，
  provider 回退到原签名调用。
- 有效交付为空时仍保留其明确结果，不因空列表触发第二次构建。
- 用户、公司、产品或发布 scope 不同时仍分别解析；本次共享仅限定在同一个 system.init 请求。

验证：

- `verify.backend.navigation_delivery.unit` 通过，覆盖菜单批次、菜单 ACL/权威、导航编译和
  system.init 最终路由静态顺序。
- 菜单元数据 10 项、system.init menu boundary 7 项和 contract entry equivalence 10 项通过。
- capability identity boundary 6 项、契约边界主套件 171 项及 53、62、5 项关联套件通过。
- `sc_dev_demo` 上新增的 same-scope capability ORM 用例通过：published pair 构建收到
  effective delivery authority，没有另行解析路由权威。

`verify.system_init.snapshot_equivalence` 因未提供 `E2E_BASE_URL` 没有启动，归类为
`environment_defect`，不记为产品失败或通过。为遵守“只在需要时重建”的执行要求，没有重建
完整 fresh `sc_test` capability 组，只运行了直接受影响的同作用域 ORM 用例。

本批证明初始化事实顺序已经收敛，但没有测量本次候选相对 A 的实际初始化耗时、SQL 数或
表单可用时间。下一步进入同环境 A/B 执行准备与测量；合并、部署继续暂停。

### P4 结果：测试库模板复用

`ci.local.iteration` 原先每个 ORM 目标都会重建 `sc_test`、重新安装模块并生成启动资源，
单个目标约五分钟。现改为：

- 默认直接执行 `local.test.test` 仍保持 fresh-database 语义。
- 只有 `ci.local.iteration` 设置 `LOCAL_TEST_REUSE_DATABASE=1`。
- 首次按 schema/install 输入、profile 和 Odoo 镜像准备一次 `sc_test_template`。
- 增量模板一次性安装 `smart_construction_bundle` 模块超集，避免按目标顺序遇到缺失模块再重建。
- 每个 ORM 目标从模板克隆新的 `sc_test`，测试之间仍相互隔离。
- 目标模块未安装、schema/install 输入变化、profile 或镜像变化时重建模板。
- schema 指纹只覆盖 manifest、models、data、security、views、migrations、hooks 和测试依赖，
  不因普通 handler 代码变化重建数据库。

实际双跑同一组 3 项 ORM：

- 首次建立模板并克隆执行：28.67 秒，回执
  `.runtime/test-baseline/1794635249589859327/receipt.json`。
- 第二次直接克隆模板执行：8.92 秒，回执
  `.runtime/test-baseline/1794635285640751862/receipt.json`。
- 两次均 `source_unchanged=true`、`fresh_database=true`、
  `database_template_reused=true`，执行同一 schema 指纹。

runner 单测 15 项和 local development lifecycle 52 项通过。该 28.67→8.92 秒是测试执行器
初始化开销下降，不是用户表单打开时间，也不计入产品 A/B 收益。

### PR #887 复审修正结果

正式复审在 `9e0f046f5a2ee3160b006018c4162e73a2844c8b` 上确认 5 项 P2。当前工作树已完成
对应修正，尚未提交或重新推送：

1. 初次记录快照从原生 XML 布局字段出现位置、Odoo `get_view` 的字段需求和显式早期依赖选取；
   `fieldDescriptors` 仅保留为字段元数据，不再驱动读取集合。
2. capability hook 在调用前按签名适配可选参数，保留 provider 顺序、旧 `(env, user)` 签名和
   有意返回空列表的结果；同时补回旧 capability-group hook 的接线。
3. `sc_test_template` 的候选身份写入 PostgreSQL 数据库注释，克隆前读取核对；工作树 marker
   不再证明共享模板身份。
4. 模板指纹覆盖 manifest 可达的 Python 与安装数据，包括 `wizard/` 下的 Python/XML。
5. `form_interactive_ms` 在实际 ready 条件处结束，额外契约重放校验移到计时样本之后。

跨环境验证还发现并修正了两项验证归属问题：`_fallback_parse()` 现在会在没有
`_arch_root` 时解析传入的 `arch`；P0 测试不再硬依赖 `project.project` 或
`smart_construction_core` XMLID，而是使用核心模型和最小测试事实表达同一规则。

验证结果：

- `make ci.local.iteration`：41 个受影响目标通过，无未映射路径、无未执行目标。回执
  `.runtime/frontend-dev-validation/executions/20261114T071532Z-1065015-55502259/receipt.json`。
- 仅安装 `smart_core` 的隔离 `sc_test`：8 个原 CI 失败相关用例通过，回执
  `.runtime/test-baseline/1794640293370985139/receipt.json`。
- 已安装 P1 的 `sc_dev_demo`：同一组 8 个用例通过。
- 真实 XML carrier/projection ORM：1 项通过，回执
  `.runtime/test-baseline/1794639707155587749/receipt.json`。
- capability hook 兼容 ORM：3 项通过，回执
  `.runtime/test-baseline/1794639231458808147/receipt.json`。
- capability identity boundary ORM：26 项通过；权限事实 capability ORM：63 项通过。
- assembled contract cache 提升为 v49，输入摘要重签为
  `d4b9230f4a6287cfcf469bd9761737104152bd45415f2c2b7ebc5850693d0162`。

当前候选仍不能宣称主线集成或性能收益：精确提交后的远端必需 CI、独立复审以及该累计候选的
同环境 A/B 均未执行。合并、部署继续暂停。

### 发布预检重复执行纠正

复审修正提交后，`pr.push` 仍会无条件重跑完整的 41 个受影响目标，即使 clean HEAD 的运行时
文件字节与提交前已验证的 dirty 工作树完全相同。该行为来自增量执行器只对 `HEAD` 树取摘要，
并把 `worktreeClean` 纳入复用身份。

现修正为：

- `runtimeTreeSha256` 对当前 tracked、dirty 和 untracked 运行时文件的实际字节计算；
- `HEAD` 和 clean/dirty 状态只保留为回执来源信息，不再单独决定复用；
- 运行时字节、目标集、验证器权威或目标日志任一变化仍然拒绝复用；
- 增量复用 schema 提升为 v2，旧索引不会被继续解释。

新增测试覆盖 dirty 验证后提交为 clean HEAD 时复用身份不变、运行时内容变化时不复用、
工作树变化确实进入临时标识，以及日志被篡改时仍拒绝复用。后续又扩展到 passed、interrupted
和 failed 聚合回执的逐目标续用，只废弃由变更路径重新选中的目标和失败目标；
`verify.frontend.dev.incremental.unit` 143 项通过。该修正属于 P4 执行效率，不改变产品代码
或性能结论。

### CI 首轮失败修正

`6fe21559d` 的远端首轮执行中，shard 3、2、1、managed ORM、frontend gate、public guard 和
professional quality checks 通过；shard 0 暴露两项问题：

- capability 空结果测试仍绑定旧 dispatcher，未覆盖生产新增的兼容关键字入口；
- `sc_ui_usage=interaction` 的模型字段没有进入稀疏记录快照依赖，导致付款申请只读契约缺少
  `legal_next_action_display`。

修正方式：

- capability 测试改为绑定 `call_extension_hook_first_compatible`，空列表语义继续短路；
- `_dispatch_native_form_source()` 从模型字段对象收集显式 `sc_ui_usage=interaction` 字段，
  作为请求内早期记录依赖，不从完整 `fieldDescriptors` 猜测；
- handler 输入变化后 assembled contract cache 提升到 v50，摘要重签为
  `f273c060bf429179f427d6137ab6752a59b480407aa59578a4b59d2c63a9a382`。

定向 ORM 三项通过；最近一次 `ci.local.iteration` 从上一份 41 目标回执复用 33 项，只重跑
受影响的 8 项并全部通过。`verify_coverage` 的模块不一致是 shard 0 失败后的派生失败，
需要新精确提交的远端执行确认。

### R10 冷启动重复构建与隔离 A/B 准备

`Formal Product Layer`：P0 初始化路由事实消费；P1 场景能力投影；P4 性能验收工具。
`Layer Target`：`SystemInitHandler`、scene runtime context、scene registry tile 过滤、
capability scene target 和 R10 isolation profile。
`Why Here`：重复构建发生在当前请求已有 `EffectiveDeliveryService.resolve()` 结果，却被
scene/capability consumer 再次查找的边界。
`Why Not Elsewhere`：不把请求事实写入全局缓存，不删除最终权限过滤，也不通过前端或客户配置
补足后端事实。
`Blast Radius`：`system.init` 冷启动、capability target 映射、scene tile 可见性、同一请求的
用户/公司/权限作用域，以及隔离 A/B 的资源声明。

已实现：

- `SystemInitRuntimeContext` 携带本次请求已经生成的 `published_authority`，并经
  `SceneRuntimeOrchestrator`、scene provider、registry provider 和
  `sc.scene._filter_payload_tiles()` 传给原生 capability 访问判断。
- capability scene target lookup 现在只消费与 actor 无关的有效场景声明，并只缓存
  `target`、`alias_of`、`identity_owner` 等身份字段；不再把按用户过滤后的 tiles 放入
  `_SCENE_MAP_CACHE`。
- 最终场景 tile 过滤、原生权限判断和 `published_route_authority()` 的 ormcache 回退仍保留。
  没有把请求级 authority 写入全局缓存。

同一进程受控对照（仅 shell 诊断，不是 HTTP/browser 样本）：

| 口径 | resolve/build | SQL | elapsed |
| --- | ---: | ---: | ---: |
| 旧全局查找路径 | 2 / 2 | 1,766 | 1,464.399 ms |
| 当前请求 authority 路径 | 1 / 1 | 1,590 | 1,215.744 ms |

修复后三个新进程样本均为 `resolve=1`、`build=1`、`SQL=1,590`，elapsed 为
`1,351.914 / 1,260.662 / 1,293.810 ms`，route authority hash 和 57 个 capability
输出保持一致。该结果证明重复生产链路被收敛，不是实际用户耗时收益。

P4 隔离准备：

- 新增只读 profile、continuity contract、受管 Make 入口及 profile 单测。
- `verify.r10.performance_ab.profile` 9 项、`r10.performance_ab.plan` 和
  `r10.performance_ab.preflight` 通过。
- preflight 确认当前 A 四个容器存在；R10 容器、卷、网络、路径不存在；端口
  `18181/18182` 可用；没有创建快照、容器、网络或卷。
- Candidate B 部署与正式 Cold/Warm A/B 仍未执行，合并和部署继续暂停。

本轮定向验证：

- scene target 跨主体缓存边界、声明读取、tile 过滤和入口 target：64 项通过。
- 受影响真实 ORM：42 项通过，回执
  `.runtime/test-baseline/1794649732744739201/receipt.json`，运行期间源指纹未变化。
- 修复后的 `make ci.local.iteration`：43 个目标全部通过，`verificationPassed=true`、
  `unmappedPathCount=0`，回执
  `.runtime/frontend-dev-validation/executions/20261114T100812Z-2040968-920561893/receipt.json`。
- 初轮 `ci.local.iteration` 的唯一失败是既有 scene tile 测试桩未接受新增
  `published_authority` 关键字，归因为 `validation_tool_defect`；已更新该测试桩，并保留
  失败回执 `.runtime/frontend-dev-validation/executions/20261114T093846Z-1856661-274860467/`。

当前没有将 189.633 ms 的第二次 resolve、诊断 SQL 差值或测试模板收益换算为用户可见
性能收益。R10 的正式 Cold/Warm A/B 仍需隔离 A/B 环境和单独部署授权。

### R10 隔离 A/B 实测结果

在独立 PostgreSQL、Redis、Odoo 卷和 Compose 项目上恢复同一份
`sc_demo-20261114T102211Z-8d8c07d0` 快照。两臂均使用逻辑库 `sc_demo`、账号
`demo_full`、公司 1，并实际打开 `project.project/2`。A 为基线 `5d631f6`，B 为
`5d0381f`；后续提交只修改 R10/P4 工具，不改变产品运行时源码。

每臂采 1 个 cold 和 3 个 warm 样本，桌面 1440x900、手机 390x844。10 次浏览器报告全部
通过。正式 timing 未启用 profiler；因执行端不能直连公网端口，两臂对称使用 SSH 本地转发。

| 指标 | Cold A → B | Warm 中位数 A → B |
| --- | ---: | ---: |
| 初始化 browser | 2,558.373 → 2,096.982 ms（-18.0%） | 2,694.856 → 2,328.087 ms（-13.6%） |
| 初始化 server | 2,055.500 → 1,582.500 ms（-23.0%） | 2,000 → 1,346.500 ms（-32.7%） |
| 点击到表单可用 1440 | 2,294.710 → 2,225.760 ms（-3.0%） | 1,848.794 → 1,951.698 ms（+5.6%） |
| 点击到表单可用 390 | 1,868.072 → 1,736.991 ms（-7.0%） | 1,839.710 → 1,550.712 ms（-15.7%） |
| 主契约 server 1440 | 1,249 → 960 ms（-23.1%） | 691 → 611 ms（-11.6%） |
| 主契约 server 390 | 555 → 473 ms（-14.8%） | 662 → 475 ms（-28.2%） |

结论：初始化与后端主契约耗时已有实际改善，手机点击到表单可用也有改善。桌面 warm 的点击到
可用时间在三个样本中反而增加 5.6%，因此不能宣称桌面端用户等待时间已经稳定改善。

结果文件：

- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r10/ab/result.md`
- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r10/ab/comparison-r10.json`

两臂当前保留运行供复查。销毁、推送、合并和正式部署均需下一次明确授权。

### R11 前端表单交付性能诊断

本轮为只读专项，没有修改前端或后端产品代码。候选关系已核对：
`526a1044b` → B 运行源码 `5d0381f` → 当前 HEAD `297fe1c1c` 均为祖先关系。
B 相对 PR HEAD 多出 R10 后端产品修复；B 之后到当前 HEAD 没有
`addons/`、`frontend/apps/web/src` 或 `frontend/apps/web/scripts` 差异。

原先每臂 3 个 warm 样本显示桌面表单可用时间增加 5.6%。扩展到每臂 9 个正式
warm 样本（每个视口 9 个）后结论改变。分阶段 instrumented 扫描使用每臂 9 个
桌面、3 个手机样本，仅用于定位阶段，不与正式耗时混用：

| 1440x900 | A 中位数 | B 中位数 | 变化 | A P90 | B P90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 初始化 browser | 2,604.1 ms | 2,261.7 ms | -13.1% | 2,756.4 | 2,422.6 |
| 初始化 server | 2,062 ms | 1,349 ms | -34.6% | 2,070 | 1,396.5 |
| 表单可交互 | 1,829.4 ms | 1,763.2 ms | -3.6% | 2,114.9 | 1,951.7 |
| 主契约 browser | 1,128.1 ms | 1,004.3 ms | -11.0% | 1,174.6 | 1,097.3 |
| 主契约 server | 691 ms | 520 ms | -24.7% | 698 | 615 |

手机表单可交互中位数为 A `1,803.2 ms`、B `1,680.1 ms`（-6.8%）。因此，之前
3 样本的桌面“回退”属于样本波动，不能作为前端回归结论。

冷进程扩到每臂 5 个后，桌面表单可交互中位数为 A `2,325.1 ms`、B `2,130.5 ms`
（-8.4%），P90 为 `2,748.3` 对 `2,542.9 ms`；手机表单可交互为
`1,736.2 → 1,554.0 ms`（-10.5%）。每臂 5 个冷进程均访问 record 2。

分阶段诊断发现两个剩余热点：

- 每次打开表单会触发 11–12 次约 409 KB 的完整 session 序列化，合计约
  4.5–4.9 MB localStorage 写入；直接写入约 22–26 ms，CPU 中 `persist`
  自身耗时约 72–85 ms。调用来自 activity page 注册、标题/脏状态更新，以及每个
  intent 响应后的 `recordIntentTrace()`。
- 核心字段和 18 个输入已出现后，到当前 ready 边界仍有约 500 ms；期间完成
  2–3 个关系模型契约、chatter 和 follower 请求。关系契约请求并行发出，不是
  串行 N+1；它们最长约 294–329 ms。

现有 `form_interactive_ms` 把核心表单渲染和辅助关系/协作就绪合在一起。字段与输入
实际进入 DOM 的时间比当前 ready 边界约早 500 ms，但不能据此提前宣布 ready；
下一步应先定义并验证核心可交互边界，再决定辅助数据是否必须阻塞。

建议的后续实施顺序：

1. 合并 session 持久化写入，并把 transient intent trace 从完整 session snapshot
   中分离。
2. 增加 core-ready 与 auxiliary-ready 两个显式边界，并用真实输入/按钮操作验证
   core-ready。
3. 评估由父契约携带关系列描述或批量关系描述，避免核心表单出现后的契约尾部。
4. 只有实施计时证明仍有收益时，再处理字段映射 memoization 或 Vue 更新。

9 个 warm 原始报告、阶段扫描和结论位于
`.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r11/`。本轮未合并、未部署、
未修改产品代码；A/B twin 继续保留。

clean-head 复核还发现，提交钩子刷新测试清册后，R10 plan 中列出的三个 snapshot 运维入口
已经被验证工具识别为执行引用，但 dispositions 仍把它们登记为零引用目标。该问题归因为
`baseline_evidence_defect`，只移除了三个已经失效的登记，没有放宽任何检查或验证范围；
`make audit.verification.lane_coverage.check` 通过。产品代码和业务输出没有变化。

为避免同类问题再次在 commit 之后才暴露，pre-commit 刷新并暂存生成证据后立即执行
`audit.verification.lane_coverage.check`。若生成清册使登记失效，commit 在写入 Git 对象前
直接失败并指出需要清理的登记。该 P4 修正的 74 项 lane coverage 单测通过，未改变产品代码、
验证范围或基线允许值。

### R12-A Session 持久化生命周期审计

本轮为只读审计。已完整追踪 Session Store、restore、activity page、router、intent
trace、上下文切换和导航展开状态的写入者及恢复读取者。

当前快照实测 `421,339` 字节，其中主要构成为：

| 字段 | 字节 | 所有权 |
| --- | ---: | --- |
| `menuTree` | 242,266 | Derived/live，恢复时主动丢弃 |
| `scenes` | 74,293 | Derived/live，恢复时主动丢弃 |
| `workspaceHome` | 30,323 | Derived/live，恢复时主动丢弃 |
| `roleSurfaceMap` | 27,598 | Derived/live，恢复时主动丢弃 |
| `initMeta` | 18,914 | Derived/live |
| `capabilityCatalog` | 12,996 | Derived/cache |

这些字段已经超过 406 KB。真正的 Durable Session 数据只有身份、上下文、activity
tab、展开偏好和 boot guard 等小体量状态。

已确认的结构问题：

- `recordIntentTrace()` 每收到一个 intent 响应就序列化完整 Session，实际只更新四个
  transient diagnostic 字段。
- `loadProductCapabilityCatalog()` 会调用 `persist()`，但 product catalog 根本不在
  持久化快照中，属于无收益完整写入。
- 标题、dirty、活动 tab 时间戳和 runtime query 都会各自触发完整写入。
- `activityPages.settling` 是瞬态但被持久化；`dirty` 在恢复时固定清为 false，因此
  它不提供跨刷新未保存值恢复。
- 当前没有 Session 级 `pagehide`/`visibilitychange` flush，也没有跨标签页 storage
  协调；现行为是即时写和 last-write-wins。

R12-A 建议只做最小架构收敛：

1. 在现有 Pinia Store 内显式生成 Durable Snapshot。
2. transient intent trace 不再触发 durable persist。
3. 连续、可合并的 durable UI 更新通过单次调度写入。
4. 关键上下文和 `pagehide`/`visibilitychange=hidden` 同步 flush。
5. 第一阶段保留多标签页 last-write-wins，不引入新的合并框架。

未修改前端/后端产品源码，未改 R10/R11 原始数据，A/B twin 未变。R12-B 需等待独立审查。
交付物位于 `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/`。

### R12-B Session 生命周期实施

独立审查确认架构方向成立，并要求在实施前补齐四项边界。实施按三项提交推进：

| 批次 | 提交 | 内容 | 结果 |
| --- | --- | --- | --- |
| B1 | `f780bbe45` | 版本化 Durable Snapshot、严格 `user`/`recordContext` 白名单、legacy/current/future/corrupt 迁移 | 48 例通过，严格类型检查通过 |
| B2 | `e3440e2de` | 单 pending 合并、generation 取消、transient 去写入、capability catalog 去写入、生命周期 flush | 25 例通过，workspace lifecycle 与 143 项映射测试通过 |
| B3 | 当前记录提交 | 登录/刷新/上下文/activity/dirty/logout/401/多标签/quota 完整恢复回归与受控测量 | 34 例通过 |

Durable Snapshot 现在由显式字段构造，不再展开 live Session：

- `user` 只保存 `id`、`name`；权限字段由当前 `system.init` 重建。
- `recordContext` 只保存模型、记录、公司、经营方式和 request context；不保存
  `company_options`、`operation_options`、`options`、`selector` 或消息等实时契约。
- activity 只保存恢复身份、标题、路由、runtime query、时间和必要的记录上下文；
  `dirty` 与 `settling` 留在内存。
- menu/scenario 展开偏好、active tab、cache epochs 和 boot intent 保持恢复。

持久化行为：

- 连续 durable 更新共用单 pending，flush 时读取最新状态。
- 身份、上下文、tab 结构、启动完成和退出边界可直接写入。
- `clearSession()` 首先递增 persistence generation、取消定时器并清除 pending，再删除
  Snapshot 与 token；旧 generation 已排入事件队列的回调也会在写入前失败关闭。
- `pagehide` 与 `visibilitychange=hidden` 共用同一 flush；第一次消费 pending，
  第二次不写。
- `recordIntentTrace()`、dirty、settling 和 product capability catalog 不再触发
  durable Session 写入。
- 多标签页仍保持 last-write-wins，没有新增跨标签页协调。

旧快照迁移已在生产 Store 路径验证：

- 无 `schemaVersion` 的旧快照按 legacy 读取，只提取 durable allowlist；
- 当前版本按白名单恢复；
- 损坏 JSON 和未知未来版本只丢弃 Snapshot，token 仍从 `sessionStorage` 独立恢复；
- `menuTree`、`capabilityCatalog`、`initMeta` 等旧派生字段即使格式异常也不阻止登录。

受控进程内测量使用生产 Snapshot builder 和 restore 路径。legacy 基线是按 R12-A
`421,339` 字节字段清单重建的同尺寸测试载荷，不代表当前真实业务数据；候选状态是
包含真实 store 类型结构的测试 fixture：

| 指标 | 结果 |
| --- | ---: |
| Durable Snapshot | 1,383 bytes |
| 模拟 12 次更新 | 1 次 durable write |
| 合并更新 | 11 |
| 单次持久化 `stringify` | 2 次 / 0.022 ms |
| 单次 `setItem` | 0.021 ms |
| restore 中位数（20 次） | 0.259 ms |

这些是 Node.js 受控测量，不是浏览器点击到可用时间或部署 HTTP 数据，不替代独立复审后的
真实浏览器 A/B。性能证据：
`.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12-b-performance.json`。

本批未修改后端产品代码、PR #887、R10/R11 原始证据、A/B twin 或业务数据；未部署、
未合并。下一步是基于当前精确 HEAD 和保留证据执行独立 R12-B 复审。

### R12-B-R1 故障路径修复

第二次复审前只修复独立审查确认的两个故障路径，不改变 Snapshot schema、迁移规则、
正常路径合并或用户业务语义。

P1 将持久化结果明确区分为 `full`、`degraded`、`failed`：

- 只有 full 写入成功才清除完整恢复义务；
- degraded/failed 保留独立 retry-needed；
- 下一次 lifecycle flush 或新的 Durable 更新会从当前最新状态重新构造 full snapshot；
- full retry 成功后才清除 retry-needed；
- 失败不会自动创建紧循环重试；
- `clearSession()` 同时清除 pending、retry-needed 和旧 generation。

P2 将存储异常隔离：

- Snapshot 读取、删除失败不再阻止 restore、logout 或 401；
- 内存 Session 先完成清理；
- localStorage Snapshot 删除失败不会阻止 per-tab token 删除；
- 两个存储介质同时抛异常时，内存清理和 generation 失效仍完成。

验证结果：

- 原有 Session 定向测试：107 例通过（snapshot 48、scheduler 25、recovery 34）；
- 新增 P1/P2 强制反例：28 例通过；
- workspace lifecycle：通过；
- 增量映射测试：144 例通过；
- 严格类型检查：通过；
- lint：无错误，仅有 4 个既有 warning。

本修复仍未证明浏览器真实写入次数和用户可见性能；第二次独立复审通过后再执行浏览器恢复验证和
R12 A/B。未修改后端、PR #887、R10/R11/R12-A 原始证据、A/B twin 或业务数据。

### R12-B-R1 复审、浏览器恢复与隔离 A/B 收口

独立复审绑定产品提交 `91a55152c153541bc85b5739559f6cbe77b3499c` 和树
`790f883f1cfcdb5b7415390e77d26c2b3925d666`，独立复现了 degraded retry、
storage 异常清理和 generation 失效边界，结论为
`approved_for_exact_head_acceptance`。产品提交后的四个提交只修改 P4 守卫、覆盖登记和
隔离 A/B 工具，不改变 Session 产品运行时。

最终候选 `b3a685bfab7934e5eec1f7c0f6cb36c79dce5096` 的完整 Quick 为 8/8
shard PASS，回执位于 `.git/codex/evidence/ci.local.quick/`。隔离 B 已刷新为该提交并由
运行端点回读确认，bundle 为
`dc3552784b5fa2cd2b0a542d035f9c3f86bcbb861674b30d89d97b9cb34d1466`；A 保持基线
`5d631f6dd304a003f09c72e7de22fde45b8c3dbc`，bundle 为
`b05764fe83fac60b3bccc81187b53d4fcdc590ac844ea8dc214170edb2c551bd`。

真实浏览器恢复验证在 B 的 `/t/demo`、账号 `demo_full`、公司 1 和
`project.project/2` 上通过。首次进入和刷新各产生 3 次 durable 写入，最终 Snapshot 为
1,046 bytes；损坏 Snapshot 后 token 保留并重新打开同一表单，activity、tab 和公司恢复，
`user` 仅有 `id`/`name`，`dirty`/`settling` 未进入持久化，页面错误为 0。
原始结果：
`.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/browser-verification-b.json`。

正式 A/B 原始组采用每臂、每视口 9 个 warm 和 9 个 cold 样本，共 36 份报告、
72 次视口交互；所有样本均从同一 `record 2` 进入，正式耗时关闭 profiler。每份报告
重新回读服务端 SHA、bundle、主契约状态和运行错误，汇总错误数为 0。cold 样本前通过
受管入口清空两臂 Redis 并重启 Odoo/Nginx。

独立复审发现固定 A→B 顺序可能影响 Warm 桌面结果，因此保留原 36 份报告，并新增
9 对 Warm B→A 和 3 对 Cold B→A 交叉样本。新增报告使用独立进程、相同数据库快照、
账号、公司、权限、`project.project/2` 和 bundle 身份；正式计时仍关闭 profiler。

| Warm 点击到表单可交互 | A 中位数 | B 中位数 | 变化 | B 胜出 |
| --- | ---: | ---: | ---: | ---: |
| 1440，正式 A→B，9 对 | 1,825.133 ms | 1,568.570 ms | -14.06% | 9/9 |
| 1440，反向 B→A，9 对 | 1,684.015 ms | 1,694.302 ms | +0.61% | 5/9 |
| 1440，合并，18 对 | 1,742.952 ms | 1,586.611 ms | -8.97% | 14/18 |
| 390，正式 A→B，9 对 | 1,731.114 ms | 1,389.985 ms | -19.71% | 9/9 |
| 390，反向 B→A，9 对 | 1,787.315 ms | 1,365.674 ms | -23.59% | 9/9 |
| 390，合并，18 对 | 1,747.128 ms | 1,387.877 ms | -20.56% | 18/18 |

| Cold 点击到表单可交互 | A 中位数 | B 中位数 | 变化 | B 胜出 |
| --- | ---: | ---: | ---: | ---: |
| 1440，正式 A→B，9 对 | 2,439.529 ms | 2,016.283 ms | -17.35% | 9/9 |
| 1440，反向 B→A，3 对 | 2,276.024 ms | 1,913.765 ms | -15.92% | 3/3 |
| 1440，合并，12 对 | 2,416.185 ms | 1,969.407 ms | -18.49% | 12/12 |
| 390，正式 A→B，9 对 | 1,797.581 ms | 1,505.569 ms | -16.24% | 9/9 |
| 390，反向 B→A，3 对 | 1,789.774 ms | 1,311.509 ms | -26.72% | 3/3 |
| 390，合并，12 对 | 1,793.677 ms | 1,494.721 ms | -16.67% | 12/12 |

Warm 桌面合并改善为 `-8.97%`，但反向组中位数略慢 `0.61%`，说明结果对采样顺序敏感。
不能把固定 A→B 的 `-14.06%` 单独宣传为稳定、无条件收益。Warm 手机在两种顺序中均为
9/9 胜；Cold 的合并样本为 9 个 A→B 加 3 个 B→A，不平衡，只作为方向性证据，不作稳定保证。

Warm 初始化服务端中位数为 `2,086 → 1,409 ms`（-32.45%），初始化浏览器中位数为
`2,611.282 → 2,091.160 ms`（-19.92%）。Warm 主契约服务端中位数在桌面为
`683 → 513 ms`，手机为 `538 → 486 ms`；主契约浏览器中位数在桌面为
`1,105.715 → 972.462 ms`，手机为 `967.047 → 872.463 ms`。这些是隔离候选环境的观察，
不是生产 SLA。

独立的 profiler/storage 诊断使用每臂 2 个桌面和 2 个手机表单打开，不与正式耗时混合。
从列表批准记录进入时，A 中位数为 12 次 durable 写入、`4,915,228.5 bytes`、
`setItem` 24.0–24.1 ms，CPU 样本中的完整 `persist` 自身耗时中位数为
`73.832–76.062 ms`；B 为 2 次写入、`2,894 bytes`、`setItem` 0.05–0.1 ms。
B 在采样分辨率下没有再出现完整 Snapshot `persist` 帧，不能把“未出现”写成精确 0 ms，
但可以确认该热点已从样本中消失。

性能结论按五项分别限定：

- 后端初始化：Warm 服务端中位数 `2,086 → 1,409 ms`，浏览器中位数
  `2,611.282 → 2,091.160 ms`；方向稳定。
- 主契约服务端：Warm 桌面 `683 → 513 ms`，手机 `538 → 486 ms`；方向稳定。
- 表单交互：Warm 手机稳定改善；Warm 桌面合并改善但顺序敏感；Cold 方向改善但反向样本有限。
- Session 持久化：真实浏览器从列表打开表单的 durable 写入中位数为 `12 → 2`，
  累计约 `4.9 MB → 2.9 KB`；该收益与 Warm 桌面统计口径无关。
- 统计限制：固定顺序、反向顺序与合并结果必须同时保留，方向性结果不得写成产品 SLA。

原始和补充证据：

- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/ab/formal-comparison.json`
- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/ab/order-stratified-comparison.json`
- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/ab/warm-sequence.log`
- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/ab/cold-sequence.log`
- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/reverse-order-crossover.log`
- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/session-a-instrumented.json`
- `.runtime/agent-runs/SCENARIO-FORM-PERFORMANCE-20261114/r12/session-b-instrumented.json`

### R10 输入版本迁移

原始 `r10-manifest.json` 的 38 项输入和历史哈希保持不变。当前新增
`r10-current-input-manifest.json`，记录其中 35 项仍一致、3 项因
`b3a685bfa` 的 Candidate B redeploy 工具扩展而变化：

- `scripts/ops/r10_performance_ab_lifecycle.py`
- `scripts/ops/test_r10_performance_ab_lifecycle.py`
- `make/r10_performance.mk`

迁移记录包含三个文件的旧/新 SHA256、变更提交、diff 范围、原/current input-set digest，
以及 `deploy`、`cold_reset` 两个既有函数的 AST 源码哈希。两函数在变更前后哈希一致，
变更仅新增 B redeploy 路径，没有删除文件，也没有改写原始 A/B 报告。原 R10 manifest 和
R11 的 13 项 manifest 保持不变；R12 的 59 项 manifest 已被后续版本覆盖，按下一节如实记录。

### R12 manifest 历史沿革

独立复审确认：更早的 R12 59 项 manifest 已在其原路径被后续 93 项版本覆盖，当前无法从
`.runtime`、`.git/codex` 或常见备份文件中恢复。不得重建 59 项文件冒充原始版本。

经所有者明确授权，现存且已验证的 93 项 manifest 作为 R12 最终完整证据清单，并保留当前
93 项文件的独立冻结副本：

- `r12-final-manifest-v93.json`
- SHA256 `ac578105c13b02b72da3376fc91cba0f44c40d69482503bddbfaddc303d2502f`
- 文件模式 `0444`

历史说明记录在 `r12-manifest-lineage.md`，其中包含所有者授权原文、原 59 项不可恢复事实、
搜索范围、v93 manifest 身份和 v93 时点的最终结果快照
`r12-final-result-at-v93.md`。v93 是有授权的替代证据清单，不是原 59 项文件的恢复件。
其绑定的 tracked 文件可由提交 `d748195681bbdeaa0956ee8f1ab84acfe41cd597` 恢复。

当前成果证明后端事实复用和前端 Session 生命周期治理产生了真实、可量化的候选环境收益；
同时保留 Warm 桌面的顺序敏感性及 Cold 样本限制。它不等于生产部署验收，也不授权 Core
Ready 提前实现。A/B twin 和快照继续保留；当前候选中尚未推送的提交、PR 和部署边界
保持分离。

下一步是提交本次证据收口，针对新的 clean HEAD 再执行一次 Quick，并请求最终独立复审。
该复审及当前 HEAD 的远端必需 CI 完成前保持 `verification_pending`。
