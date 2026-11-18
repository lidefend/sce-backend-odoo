# 自定义前端契约承接与业务办理旅程研究 V1

- 研究基线：`9821a9c688cbd4abb44f378051fc6c6362c5d8cd`
- 研究对象：Contract V2 前端消费，以及 91 个正式业务入口的用户办理证据
- 当前状态：`research_complete_product_work_pending`
- 产品行为变更：无
- 自动矩阵：[Contract V2 消费矩阵](contract-v2-consumption-research-v1.json)、
  [91 入口业务证据矩阵](business-entry-journey-evidence-v1.csv)

本专题只做只读研究。结论按“声明 → 前端消费 → 实际行为”三段绑定；合法空态、菜单可达、
选择器存在、ORM smoke 和真实页面办理分别记账。

## 一、结论

当前前端**不是“仅仅刚能运行”**。字段、布局、关系、明细行、动作状态、权限、表单写回、
冲突恢复和支付申请完整链路已有较强的契约消费与行为锁。47 个重点 facet 中，33 个已有
契约消费和对应证据，说明契约驱动渲染的主干是成立的。

但也不能称为“契约已完整承接、91 个业务入口都已完成用户办理”。当前可以确定的是：

- 4 个入口达到其 CSV 声明职责范围内的页面完整证据：项目台账、项目启停管理、日常合同、
  付款申请。
- 1 个入口有页面创建写证据：新项目立项；未覆盖后续完整生命周期。
- 16 个入口只有列表/详情读取证据。
- 64 个入口只有合法空态/列表表面证据，没有详情、保存、动作或状态回读闭环。
- 3 个入口只有呈现/授权表面证据。
- 3 个入口仍为 `pending`：我的工作、项目预算、菜单配置。
- 3 个入口有真实页面流程动作；1 个入口有附件上传/刷新/下载；1 个入口验证了可交互分页。
- 88 个 CSV `passed` 是历史证据结论；没有一行证据把 served/source identity 绑定到本次研究
  基线 `9821a9c6`，因此不能把它们直接声明为“当前基线的 88 项全量通过”。

因此，用户视角的准确结论是：

> 框架和若干高价值链路已经能按契约高效办理，但绝大多数业务入口还没有当前基线的完整用户
> 旅程证据，部分已声明能力仍未被前端消费，不能判定全量业务“高效且完整办理”。

## 二、证据口径

### 2.1 业务闭环分级

| 级别 | 数量 | 允许得出的结论 | 不允许得出的结论 |
| --- | ---: | --- | --- |
| `full_declared_scope` | 4 | CSV 声明职责内的查询、写入、动作/状态或附件等已按页面证据完成 | 未经声明的权限、角色、数据量和后续流程 |
| `write_create_partial` | 1 | 已从页面创建并回读新记录 | 后续提交、审批和完整生命周期 |
| `read_detail_only` | 16 | 列表及详情读取可用 | 可保存、可提交或流程可推进 |
| `declared_empty_read_only` | 64 | 当前角色/公司作用域下空态和读取权限符合声明 | 有数据时的详情、写入、动作和审批 |
| `surface_only` | 3 | 入口、呈现和部分授权边界可观察 | 任何业务办理闭环 |
| `pending` | 3 | 已有部分表面证据 | 正式验收完成 |

“空态合法”和“业务完成”同时可以成立吗？只有入口本身被声明为只读报表或只读事实面时才可能。
对可创建、可审批的业务单据，空态只能证明当时没有数据，不能证明“有数据后能办”。

### 2.2 当前基线回绑

`business-entry-journey-evidence-v1.csv` 保留了历史 served/candidate identity。当前基线回绑数为
`0`。这不自动否定历史证据，但要求下一轮按输入依赖做确定性影响分析或重新采集。不能用
“文件名相同”“标签相同”或“模型相同”把旧证据继承给新 SHA。

### 2.3 三个不能互相替代的通过面

| 证据面 | 当前覆盖 | 结论边界 |
| --- | --- | --- |
| 81 正式办理能力矩阵 | 菜单、动作、模型、CRUD 权限、合同存在性、URL | 不是页面办理；且 `search=0` 是测量口径缺陷 |
| 12 核心流程 ORM smoke | savepoint 内创建、编辑、回滚，不是页面 | 与 91 入口仅 4 个 XMLID 精确重合；其余 8 个不能回填 |
| 91 入口产品证据 | 入口/页面/部分页面写办 | 当前只有 4 个达到声明职责完整面 |

## 三、契约承接完整度

自动矩阵共审计 47 个 facet，结果如下：

| 判定 | 数量 | 含义 |
| --- | ---: | --- |
| `aligned` | 33 | 声明、消费和针对行为的断言一致 |
| `consumption_defect` | 9 | 契约已表达，但前端未消费、消费不完整或用错 |
| `expression_gap` | 2 | 契约/规则自身无法稳定表达消费所需身份或结构 |
| `terminal_capability_gap` | 1 | 当前终端只有可读降级，不能提供等价交互 |
| `evidence_gap` | 2 | 存在消费或元数据，但缺少足够的行为/边界证明 |

### 3.1 已承接较好的逻辑

- 字段身份、类型、widget provenance、原生 occurrence 身份。
- required/readonly/invisible/disabled 及 `widgetStatus/buttonStatus/containerStatus/selectorStatus`。
- 字段/容器布局、24 网格跨度、表单结构权威和声明式协作/审计表面。
- domain/context、关系搜索、受控新增、one2many 命令和行身份。
- 筛选、保存筛选、自定义筛选/分组、分组、默认顺序、页大小。
- 动作身份、intent、执行范围、刷新策略、确认/原因输入和主次动作。
- 页面/字段/按钮/记录能力、拒绝原因、删除策略和 `if_match` 冲突保护。
- 提交 readiness、字段/表单错误、焦点、草稿保留和会话恢复。
- 原生 Action View Set、renderer registry 和未知 renderer 的显式失败关闭。

这些能力不是靠选择器字面证明；多数有生产 helper 或生产 presenter 驱动的非零行为测试。

### 3.2 P0 消费缺口

| 缺口 | 分类 | 现状 | 用户影响 | 负责层 |
| --- | --- | --- | --- | --- |
| `workflowContract` 结构 | 表达缺口，关键 | schema 只约束 `submissionRequirements`，其余运行时字段 `additionalProperties=true` | 非法状态栏/动作/证据门可能静默消失或形成不一致的下一步 | P0 |
| transitions 动作身份 | 表达缺口 | 只能按 kind/name/label 模糊匹配动作 | 同名动作、标签改名或命名漂移时，下一步可能缺失或指向错误操作 | P0/P1 |
| `search_panel` | 消费缺口 | 后端 parser/schema/serializer 都有，前端源码无消费者 | 有分区/分类字段时，用户拿不到原生搜索面板，只能在大量记录里用通用关键字 | P0 |
| `searchContract.fields` | 消费缺口 | 未进入 ActionView 搜索控件 | 用户看不到契约声明的可搜索字段，查找效率依赖单一全文字段 | P0 |
| `searchContract.default_sort` | 消费缺口 | 前端只消费 `default_order`/`defaults.order` | 若生产方使用 `default_sort`，用户看到的顺序与契约默认不一致 | P0 |
| `intakeAutosave` | 消费缺口 | runtime 已接线，但 `intakeAutosaveFields` 固定为空 | 新增过程中关闭/刷新页面，本地自动草稿不保存任何字段 | P0 |
| Action readiness 三轴 | 消费缺口 | 严格解码，但 ActionView 不读取 blocked/unresolved 结果 | 后端声明“业务执行未就绪”时页面仍可能呈现可操作表面 | P0 |
| runtime control plane | 消费缺口 | patch/lazy/virtualization/retry/hydration 等只解码/透传 | 非默认策略不改变行为，契约承诺与终端行为脱节 | P0 |
| `validationRules` | 消费缺口 | 无业务表单消费点 | 用户不能得到契约声明规则的即时字段反馈，只能等后端报错 | P0 |
| runtime `fieldSemantics` | 消费缺口 | 无业务消费点 | 同一字段语义可能来自另一套 descriptor，存在双来源风险 | P0 |
| `businessWorkspace/businessActions` | 消费缺口 | resolver 无调用方 | 后端一旦发出这些声明，前端不会据此形成工作区/业务动作 | P0 |

`search_panel` 当前在 91 个产品入口 XML 中没有发现 `<searchpanel>`，因此是**潜在消费缺口**；
但 `sc_norm_engine` 已存在搜索面板声明，且该能力已在 Contract V2 中发布，不能因当前样本为空
就删除或视为未声明。

### 3.3 终端能力缺口

`calendar`、`gantt`、`dashboard` 当前登记为 `core.readable_records` fallback。它们是显式失败
关闭，不是静默错误，但用户只能读记录，不能获得日历、时间轴或仪表板的等价交互。是否接受这种
降级必须由产品决策，不能把它计为“renderer ready”。

## 四、用户办理效率与逻辑

### 4.1 已被页面证据证明有效的链路

付款申请是当前最完整的用户闭环：页面创建、提交、审批、驳回、纠正重提交、取消、附件上传/
刷新/下载、分页、明细编辑/删除、关系选择清除和回读均有证据。它证明当前契约前端架构能够承载
复杂业务，而不是只能展示列表。

项目台账证明字段、关系、明细、必填拒绝、草稿保留、纠正重试和列表/详情返回可连续办理。
项目启停管理证明状态相关动作、确认弹窗、溢出动作和刷新回读能按契约推进。日常合同证明状态阶梯、
终态零动作和授权拒绝可形成业务一致的页面行为。

### 4.2 当前无法证明的高频任务

以下任务在多数入口没有当前基线的完整浏览器证据：

1. 新建后保存，再从列表重新找到该记录。
2. 必填/关系错误定位到具体字段或明细行。
3. 保存失败保留草稿、修正后重试。
4. 提交、审批、驳回、重提、取消及状态回读。
5. 附件上传、刷新、下载和历史。
6. 超过一页的数据下搜索、分组、换页和返回上下文。
7. 角色拒绝后回到可继续工作的页面，而不是停在技术错误面。
8. 390px 现场办理，而非只看页面不溢出。

### 4.3 效率问题

**查找效率不足。** 搜索面板和契约字段搜索没有进入前端。对项目、合同、付款、发票、人员、
资料等高记录量业务，仅依赖通用关键字会增加找单据时间，也容易让用户误以为“搜不到就是没数据”。

**下一步不稳定。** workflow 可用动作本身已消费，但 transitions 缺少稳定 action identity，
且状态栏非法结构可能静默隐藏。用户最需要“当前该做什么、为什么不能做、做完去哪”时，页面可能
缺少可解释的下一步。

**中断恢复不完整。** 提交 readiness、内存草稿和会话恢复已有机制，但新增入口的 autosave 字段
为空，刷新/关闭页面的本地恢复没有真正保存业务输入。这直接违背高频长表单的恢复预期。

**只读降级会改变任务方式。** 日历、甘特和仪表板只能看记录时，用户需要改用列表/表格完成同样
任务。若产品接受该降级，应按入口明确能力与限制；若不接受，应补交互终端而不是扩大 fallback。

**空态证据过多。** 64 个入口只有合法空态。空态设计本身可以通过，但它不告诉用户“首次新建、
保存、提交、审批、附件、回读”是否顺畅。用户侧效率不能从空页面推导。

### 4.4 用户体验证据本身

`system_user_experience_coverage_v1.json` 声明 12 个旅程，其中 8 个标有浏览器证据，
`UX-J005`、`UX-J007`、`UX-J008`、`UX-J012` 没有浏览器证据。现有
`frontend_role_journey_audit.mjs` 还把多个 journey ID 映射到同一角色的第一个路由，且未被
Make/CI 作为旅程门禁引用；它不能证明这些不同任务已分别办理。

## 五、证据真实性问题

1. **能力矩阵搜索统计错误。** `formal_business_operation_capability_matrix.py` 读取
   `layoutContract.searchProfile`，而交付契约使用 root `searchContract`；81 行全部显示
   `search=0` 是测量工具缺陷，不是产品事实。
2. **核心 ORM smoke 不可按标签回填。** 12 个 smoke 入口与 91 个产品入口只精确重合 4 个
   XMLID；另外 8 个必须保持独立证据身份。
3. **contract render authority 矩阵不是行为矩阵。** 363 个 schema 路径的“已分类”不等于
   前端已消费；`search_panel` 就被当前工具标成 rendered/interaction，但实际没有任何消费者。
4. **历史入口证据未回绑当前基线。** 当前不能把 88 个历史 `passed` 作为 `9821a9c6` 的
   当前 88 项通过；需要按代码和服务输入影响分析复用，或重新采集。

## 六、完善顺序

### P0：先补契约承接，不先改页面外观

1. 为 `workflowContract` 建立闭合 schema，至少覆盖 actions、availableActions、statusbar、
   transitions、evidenceGate、record/model 身份和拒绝原因；transitions 必须引用稳定动作身份。
2. 消费 `search_panel`、`searchContract.fields` 和统一默认排序键；删除或迁移竞争键前必须先
   核清生产方，不能前端任选一个。
3. 让 `intakeAutosave` 从契约读取允许字段、策略和恢复边界；当前空字段数组必须改为显式消费或
   明确声明不适用。
4. 把 Action readiness 与 runtime control plane 按声明落实为行为或显式“不支持”停机；
   禁止继续把仅透传字段标成已消费。
5. 消费 `validationRules`，并统一 runtime `fieldSemantics` 与其他字段语义载体的权威关系。

### P1：补业务语义与终端能力

1. 对 47 个重点 facet 逐项决定 calendar/gantt/dashboard 是接受降级，还是补交互能力；决定
   必须落到入口能力声明，不能靠 README。
2. 对高频长表单明确 autosave、离开保护、提交失败重试和审批后下一步。
3. 为项目、合同、付款、材料、分包、税务六类主链建立角色化页面旅程；实际填写字段、明细、
   关系、动作和回读，不以空态或 ORM 代替。

### P4：修复证据并建立可执行门禁

1. 把 91 入口矩阵与当前基线绑定，记录受影响/可复用/需重采集合。
2. 修复能力矩阵 search 统计口径；将搜索字段、筛选、分组、搜索面板分别统计。
3. 为每个入口形成统一字段：入口可达、呈现、查询、详情、创建、字段校验、关系/明细、保存回读、
   业务动作、审批/状态、附件/历史、授权拒绝、当前证据身份。
4. 把 `full_declared_scope` 作为入口通过的最低完整等级；`read_detail_only`、
   `declared_empty_read_only`、`surface_only` 分别保留为中间态，不能显示为完整通过。
5. 让角色旅程脚本按任务执行不同步骤；删除“同一个首个路由冒充多个 journey”的审计方式。

## 七、可交付判定

下一轮前端专题如果宣称“契约承接完整、业务高效办理”，至少需要同时满足：

- 47 个 facet 的消费缺口和表达缺口全部关闭，或由产品明确接受并登记终端限制。
- 91 个入口无 `pending`、无未回绑当前基线证据。
- 每个可写入口有详情、字段校验、保存回读和声明动作证据；有审批的入口有状态转换证据。
- 每个附件业务入口有上传/刷新/下载/历史证据；有分页业务的入口有真实换页和返回上下文。
- 至少覆盖 6 个角色、12 个不同 UX journey，不再复用同一路由冒充不同任务。
- 搜索面板、字段搜索、默认排序、草稿恢复等用户效率能力有“声明 → 消费 → 行为”证据。

在这些条件满足前，结论只能是：**核心框架已具备契约驱动能力，部分高价值链路已能完整办理；
全量业务承接和用户效率仍未闭环。**

## 八、验证与回滚

- 本批为 P4 研究产物，没有修改契约、权限、模型、业务动作或前端运行时代码。
- 自动矩阵由
  `scripts/audit/generate_frontend_contract_business_journey_research.py --check`
  复现，非零离线测试均已通过。
- 回滚只需撤销本审计分支，不涉及数据、服务、部署或外部状态恢复。

| 检查入口 | 结果 | 测试数 | 首次证据 |
| --- | --- | ---: | --- |
| `make verify.frontend.contract_business_journey_research.unit` | PASS | 8 | `.runtime/agent-runs/FE-CONTRACT-BUSINESS-JOURNEY-RESEARCH-20261118/research_matrix.log` |
| `make verify.agent.ledger.unit` | PASS | 18 | `.runtime/agent-runs/FE-CONTRACT-BUSINESS-JOURNEY-RESEARCH-20261118/agent_ledger.log` |
| `make verify.docs.links` | PASS | 5 | `.runtime/agent-runs/FE-CONTRACT-BUSINESS-JOURNEY-RESEARCH-20261118/docs_links.log` |

这些是本地研究/工具检查，不等于主线合并、版本发布或用户交付验收。
