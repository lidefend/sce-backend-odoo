# 项目资料维护页面产品化 · 实施与证据记录

日期：2026-09-11<br>
基线：`origin/main@8f709938ca312e0ecea928945a31f39830c8ec24`<br>
交付分支：`feature/p1-project-profile-page-productization-v1`<br>
状态区冻结候选：`12395fffb1d4dc3faa9917222a12e8d4c9661c02`<br>
整页结构候选（历史）：`afec3fd304b39103b16e528aaa8353556e7990da`<br>
最终产品候选：`20f21091700d0c265fac2238f8cfd6f66533f20d`<br>
文档交付身份：本文件所在提交（产品候选之后仅目标、报告与交付记录）

## 结论

项目资料维护整页产品结果已在 `20f21091…` 完成开发阶段冻结：默认正文由“基本信息、计划与责任、责任矩阵、关联业务”四个真实业务分区组织，日期、权限、动作及手动保存语义保持；共享前端只显示可见、非 notebook 且带稳定锚点的显式业务分区，既有隐藏章节策略不变。页面级章节模式由同一结果驱动标题和导航，拆分渲染不会重新推导或产生重复通用标题。

`3a3df400…` 的现场复核证明移动状态修改、放弃与重新读取链路可用，但同时确认原生 selection 不具备顺序流程拓扑，不能继续默认投影为 Steps。状态区候选 `12395fff…` 因此统一采用“当前状态标签 + 官方 Select + 独立业务动作”：桌面、窄桌面和手机消费同一 selection、readonly、busy 与草稿链路；只有契约未来明确提供顺序流程时才允许另行使用 Steps。该历史候选的状态证据保留，整页结构证据由 `afec3fd3…` 承载，导航稳定态与最终共享消费者结论由 `20f21091…` 承载。

受管 Frontend Quick 在历史状态区候选 `a65c29ff…` 完整通过；整页实现继续完成 P1 最终合成视图所有权、关联集合内容声明、空态、只读行变更标题和协作记录等宽表达。独立复核随后在 `afec3fd3…` 发现“关联业务”点击锁定释放后回退到“责任矩阵”；`7f081856…` 的增强断言又准确暴露页尾目标不能物理到达锚点时的共享消费者失败。最终 P0 修复统一点击修正与滚动判定锚点，并只在一次点击释放时保留仍可见、但因滚动终点不能到达锚点的目标；下一次手动滚动继续使用普通锚点算法，不延长或永久锁定。完整 `make verify.local.dev.frontend.quick.gate` 已在最终产品候选 `20f21091…` 重新通过。

关联业务 notebook 由 P1 合成视图明确放入 `col="1"` 的业务分区；P0 只补齐通用渲染器对单列容器的消费，不按 widget、关系类型、项目模型或字段名猜测跨度。WBS、清单、工程结构、合同、资料与投标的身份列顺序也由原生子视图声明。共享协作区改为单层记录边界、紧凑关注者和完整名称入口；章节当前态不再因滚动容器到达底部而强制跳到最后章节。

受管模块升级、后端合成视图定向测试、P0 定向测试和最终产品 HEAD 的完整 Frontend Quick 已通过。`afec3fd3…` 的整页浏览器联合复核继续证明 1440/1082/390/320、明暗主题、全部声明页签与后半页结构，但其旧导航断言仅覆盖点击即时态，不再计为稳定态通过。`20f21091…` 的定向证据补齐点击即时态、锁定释放稳定态、正反向手动滚动，以及驾驶舱 fallback、启停专用表单和付款只读共享消费者。最终有效运行均为零业务写入、零浏览器错误、零失败。P4 fixture 旧快照继续独立登记，不由本产品分支修复，也不再混作整页产品缺陷。

## 产品层与归属

| 项目 | 归属 | 理由 |
|---|---|---|
| 项目字段分组、顺序、名称 | P1 `smart_construction_core` 原生项目视图 | 属于建筑行业标准项目资料维护方式 |
| 显式业务分区标题与导航优先级 | P0 通用 native form renderer | 只消费可见 `group` 的公开 `string` 与 `data-sc-anchor`，不识别模型名或字段名 |
| 权限、流程、保存、金额和契约 schema | 未修改 | 本专题只调整表达和既有视图组织 |
| demo fixture 快照不一致 | 独立 P4 治理事项 | 不由本产品分支修复、豁免或重建 |

## 关联业务布局与能力盘点

本表是后半页统一实施清单。整页结构样本以 `afec3fd3…` 的项目 8 为准，导航稳定态补证以 `20f21091…` 的同一记录为准；浏览器验证逐项切换全部声明页签，并按字段、集合、空态及不可见状态分别断言，零个集合不能再通过集合页签检查。

| 页签／区域 | 内容类型与当前来源 | 期望跨度 | 权限来源 | 已知样本与实施结论 |
|---|---|---|---|---|
| 投标管理 | P1 XML 的可编辑 `tender_bid_ids` 表格集合 | 所在 `col="1"` 关联业务内容区全宽 | 页签 `group_sc_cap_project_user`，字段原 context/子视图不变 | 项目 8 为空态；最终外框 width ratio 1，显示单一“添加投标记录”入口和紧凑空态，未新增数据 |
| WBS 结构 | P1 XML 的可编辑 `wbs_ids` 表格集合 | 全宽；名称与编码优先于维护序号 | 成本用户／经理组 | 3 条记录；最终外框 width ratio 1，首个业务身份列为“WBS 名称”，示例身份可直接识别 |
| 工程量清单 | P1 XML 的操作组、只读摘要和只读 `boq_line_ids` 表格 | 操作／摘要服从既有组网格，明细全宽 | 成本用户／经理组，维护动作继续限成本经理 | 1 条记录；最终外框 width ratio 1，首个业务身份列为“清单名称”，金额只消费既有事实 |
| 工程结构 | P1 XML 的可编辑 `work_ids` 表格集合 | 全宽；名称、编码和层级先于维护序号 | 成本用户／经理组 | 3 条记录；最终外框 width ratio 1，首个业务身份列为“WBS 名称”，未修改 domain |
| 合同 | P1 XML 的只读计数／金额摘要和可编辑 `contract_ids` 表格 | 摘要使用既有组网格，明细全宽 | 页签合同读取组；明细继续限合同用户／经理 | 5 条记录；最终外框 width ratio 1，“合同标题”位于平台编号之前并可直接识别，金额口径不变 |
| 工程资料 | P1 XML 的只读计数摘要和 `document_ids` 表格 | 摘要使用既有组网格，明细全宽 | 页签项目读取组；明细继续限超级管理员 | 5 条记录；最终外框 width ratio 1，首个业务身份列为“资料名称”，与协作附件保持独立 |
| 驾驶舱 | P1 XML 的只读经营摘要普通字段 | 既有双组网格，不按集合规则放大 | 财务读取组，财务字段原附加组不变 | 只读；不是关系集合，不受 P0 集合跨度修复影响 |
| 经营概况 | P1 XML 的来源字段、成本进度摘要和既有对象动作 | 既有组网格 | 项目读取组；成本字段／动作维持原组约束 | 只读事实与动作混合；不改金额、动作或权限 |
| 描述／设置 | Odoo 基础项目合成视图原生页签 | 继续服从基础视图布局 | 继承基础视图有效约束 | 当前可见但本专题不重排；最终只做共享容器回归 |
| 协作／系统 | Odoo/P1 合成页签中的任务名称、标签、任务和协作者等辅助字段 | 既有页签宽度 | 继承各字段有效约束 | 不提升为主业务分区；不与页面级协作记录混称 |
| 页面级协作记录 | P0 `NativeCollaborationPanel`：入口、关注者、协作附件、记录列表、独立审计 | 内容区全宽；关注者紧凑，记录单层边界且等宽 | 继续消费协作契约的 enabled/readonly/capability | 项目 8 多条记录；最终截图确认时间线条目等宽、单层边界，附件与审计仍为独立职责 |

跨度由视图容器和已有显式字段尺寸决定：`关联业务 col="1"` 使 notebook、page 与字段区逐层继承唯一内容列；P0 不根据 table/tree/list widget、关系模型或字段名推断宽度。原有字段类型安全默认值和 XML／低代码显式尺寸优先级保持不变。

## 关键边界证明

### 权限等价

从原“施工信息”祖先节点移出的 P1 字段逐字段保留 `smart_construction_core.group_sc_cap_project_read`，没有把权限粗放地加到整个新分组。测试同时比较基础视图与最终合成视图的 `groups`、`invisible`、`readonly`、`required` 有效约束，并通过 `get_view` 验证具有和不具有项目读取能力组时的结果。

### 日期与保存语义

`date_start` 保留在“计划与责任”主区，与单据日期、计划开工和计划竣工共同呈现；没有因标签含义不清将必填字段降到辅助页签。草稿提示明确为手动“保存修改”，并把“提交立项”说明为状态推进与完整校验动作；未新增自动保存。

### 隐藏章节与通用标题

标题与导航共同消费同一组业务分区：业务分区必须是可见 `group`、具有非空权威标题和显式 `data-sc-anchor`，且不能位于隐藏祖先或 notebook 内部。递归遇到隐藏祖先即停止，notebook 内锚点不能单独触发全页权威分区模式。普通布局容器、仅有 `string` 的节点、隐藏节点和普通页签不会因此获得新标题。存在显式业务分区时，旧的字段语义推导标题和关系字段主导航被抑制；没有显式分区的其他表单继续使用原回退路径。定向测试包含隐藏祖先、仅 notebook 锚点和拆分渲染三类反例。

### 首屏与动作职责

项目身份、唯一可交互状态、保存和流程动作集中在页头；“保存修改”与“提交立项”同时可见但职责分开，正文不再重复原生 header。动作呈现保留后端权威 occurrence 去重，但不会因动作在 primary 解析中被降级就删除独立的次级 header 动作。草稿提示明确说明手动保存和提交立项的不同效果，不承诺自动保存。

最终截图人工复核显示：390px 与 320px 首屏均能辨识项目身份、草稿状态、保存和提交入口，并完整显示项目名称；390px 能继续到达客户控件，320px 的客户控件未完整进入首屏，因此不计为“关键字段全部首屏可见”。未删除状态编辑、字段或缩小字号。

1082/390/320 均用真实 `ScSelect` 消费同一 `lifecycle_state`、同一 selection、readonly 和 busy 状态；每个视口实际打开选择器，七个原 selection 标签完整可读，切换后显示“已修改 1 项”，随后还原并刷新，未产生写请求。当前状态由 `ScStatusBadge` 独立表达，保存与提交立项仍是独立动作；状态字段区域内 `ScSteps` 数量为 0。状态槽按实际容器宽度组织，移动纵向布局使用内容高度，不再依赖扩大桌面断点或禁止 TDesign 内部标题换行。

桥接层只隐藏页头实际承接的同一 canonical 节点身份，不再按 `widget=statusbar` 批量隐藏。149 项 canonical presenter 用例覆盖两个不同状态字段、页头未承接和只读承接反例；启停专用表单的状态按既有 readonly 表达，仍由原有动作推进，未扩大状态写权限。

### 响应式边界

最终诊断除根文档外检查正文、控件、弹出层和表格边界。桌面责任矩阵表格的外框保持在内容区域内，内部允许的横向滚动能够到达最远列；移动端采用既有卡片表达。真实关系选择弹层被找到且边界检查通过。这里证明的是外层不裁切、内层可达和弹层可操作，不把允许滚动的表格误判为页面溢出。

## 共享视图消费者

| 消费者 | 关系 | 验证结论 |
|---|---|---|
| 项目信息编辑，action 861 / menu 681 | 默认解析 `project.edit_project` 合成视图 | 四个权威分区及导航身份一致 |
| 项目驾驶舱，action 605 / menu 468 | kanban/tree 后的默认 form fallback | 打开项目 19 后得到相同项目资料结构 |
| Odoo 其他未指定专用 form 的 `project.project` 入口 | 同一默认合成视图 | 属于实际影响范围；由后端合成视图测试覆盖，未宣称全入口浏览器遍历 |
| 项目启停管理，action 863 / menu 682 | 显式绑定独立 lifecycle form | 保持专用项目标识、计划信息与状态动作，不被项目资料分区替换 |
| 项目立项与快速创建 | 显式绑定专用 create forms | 不消费本次编辑表单重组，保持独立 |

## 验证索引

| 层级 | 结果 |
|---|---|
| P1 后端 | `make local.dev.upgrade MODULE=smart_construction_core` 通过；最终布局所有权定向 `TestCoreExtensionV2Finalize.test_project_maintenance_form_uses_authoritative_business_sections` 非零通过（1 method，Odoo 统计 3 tests），同时保留此前 18 个方法、Odoo 统计 20 tests 的完整结果 |
| P0 定向 | `make verify.frontend.native_section_navigation.unit` 通过（7 项章节边界）；canonical presenter 149 项通过；professional workflow 10 个模型用例与 4 个 guard 用例通过；ProductPageHeader 28 个模型用例与 8 个 guard 用例通过 |
| 前端工程 | `a65c29ff…` 的受管 Frontend Quick 完整通过；`12395fff…` 的 strict typecheck、候选 build、定向守卫、官方组件接管清单及生成清单检查通过。`ScSteps` 不再提供内部 DOM 样式入口；专门反例会对 `:deep(.t-steps-item__title)`、原生控件绕行和 selection 重新接入 Steps fail closed |
| Quick | `make verify.local.dev.frontend.quick.gate` 在最终产品候选 `20f21091…` 按受管入口完整通过，包含 strict typecheck、build、官方组件守卫、表单布局、关系集合、协作、章节导航及生成清单门禁 |
| 基线截图 | `project-profile-before-light-8f709938` 与 `project-profile-before-dark-8f709938`，绑定基线、零写入 |
| 早期诊断 | `b45e52d9` 暴露重复通用标题和提交动作仍在正文；`d755f33d`/`6b66d99d` 的动作权威证据确认提交立项是独立次级 header 动作。这些失败结果用于定向修复，不计为最终通过 |
| 既有结构诊断 | `project-profile-closure-light-83d6c5a5`（1440/390）与 `project-profile-closure-dark-83d6c5a5`（1088/320）继续证明当时的章节、首屏、表格和关系弹层；`project-profile-consumers-diagnostic-light-190ea8d9` 仅证明当时的三个项目消费者，不用于覆盖最终状态交互 |
| 状态回归历史证据 | `3a3df400…` 的两份消费者摘要保留为先前 Steps/移动 Select 实现的历史证据，不覆盖最终状态选型；人工现场复核另记录 1082/390/320 的修改、放弃与 320 首屏限制 |
| 最终项目编辑诊断 | `project-profile-status-edit-light-12395fff-retry`（1082/390）与 `project-profile-status-edit-dark-12395fff`（1082/320），状态记录 `draft → in_progress → draft`，刷新仍为 `draft`；每个视口 1 个 Select、1 个状态标签、0 个 Steps，七个标签完整，控件在视口内，章节落点无遮挡，零写入/错误/失败 |
| 最终消费者诊断 | `project-profile-status-consumers-light-12395fff`（1082/390）与 `project-profile-status-consumers-dark-12395fff`（1082/320），覆盖驾驶舱 fallback、启停专用表单和付款只读；均通过、零写入、零错误、零失败。可写 fallback 为 1 个 Select + 1 个标签；两个只读消费者为 0 个 Select + 1 个标签；均为 0 个 Steps |
| 整页结构联合复核（历史候选） | `project-profile-whole-page-light-afec3fd3`（1440/390）与 `project-profile-whole-page-dark-afec3fd3`（1082/320），绑定同一 `sc_dev_demo` 和结构候选。责任矩阵、投标、WBS、清单、工程结构、合同、资料集合均占满所属内容列；投标空态紧凑；合同标题作为主身份；11 个 notebook 页签逐项声明内容类型/数量并验证；协作记录为等宽单层边界。两份摘要均 `pass=true`、mutation/errors/failures 为 0；其导航结论仅覆盖旧脚本的即时态，已由后续失败记录和修复候选替代 |
| 导航失败保留 | 独立现场复核在 `afec3fd3…` 复现“关联业务”稳定后回退到“责任矩阵”。`project-profile-navigation-consumers-light-7f081856` 的增强断言进一步在驾驶舱和付款页尾章节得到 `pass=false`；mutation/errors 为 0。该结果保留为真实失败证据，不计入通过样本 |
| 最终导航稳定态 | `project-profile-navigation-stable-light-20f21091`（1082/390）与 `project-profile-navigation-stable-dark-20f21091`（1082/320）。六个入口均核对目标身份、标题、无遮挡、点击即时 `aria-current` 和锁定释放后的稳定 `aria-current`；责任矩阵→关联业务→协作记录及反向返回通过，正反向手动滚动当前态也通过。两份摘要均通过、零写入、零错误、零失败 |
| 最终共享消费者回归 | `project-profile-navigation-consumers-light-20f21091`（1082/390），覆盖驾驶舱 fallback、启停专用表单和付款只读。此前 `7f081856…` 页尾失败的入口均在锁定释放后保持目标当前态，普通手动滚动仍可切换；摘要通过、零写入、零错误、零失败。`afec3fd3…` 的明暗共享消费者结果只保留为导航修复前的结构/页头证据 |
| 环境失败记录 | `project-profile-status-edit-light-12395fff` 首次运行因 Chromium 两次 `ERR_NETWORK_CHANGED` 失败；候选和 local.dev health 随后均通过，独立 retry 成功。该失败不删除、不计入产品通过样本 |
| 最终候选指纹 | `20f21091700d0c265fac2238f8cfd6f66533f20d`，7389 paths，digest `bb5afe1b2a2a23b913be37023d611be0a92f82bda8db8dc89d1b2eb54a7540db`；受管候选固定在 5176 并保持运行，供独立复核使用 |

## PR 完整差异与审查路由

相对 `origin/main@8f709938ca312e0ecea928945a31f39830c8ec24`，最终产品候选包含 55 个提交、44 个路径、1960 行新增和 294 行删除；交付整理及受管 push 预检又更新三份既有交付记录和两份确定性工程收敛报告，完整 PR 路径集合因此为 46。最终交付 HEAD 的分类器结果保持 `HIGH_RISK`、`frontend_mode=standard`、`professional_mode=full` 与 `unknown_path_fail_closed`，不手工改写或降级；实际必需 PR 检查仍以受管入口和远端 exact-head 结果为准。

| 分类 | 路径数 | 准确范围 |
|---|---:|---|
| P1 产品 | 4 | `smart_construction_core` manifest、项目资料最终布局视图、原项目视图及投标扩展继承点 |
| P1 定向测试 | 1 | `test_core_extension_v2_finalize.py` 的最终合成视图、权限与内容声明测试 |
| P0 通用产品 | 18 | native form presenter/renderer、页头、状态、章节导航、关系集合、单元格与协作区；没有项目模型或字段名特例 |
| P0 定向测试 | 2 | canonical presenter 与 native section navigation 非零测试 |
| P4 fixture 诊断 | 2 | demo 合同种子诊断及其测试；只增强既有失败的可观测性，不修复或重放数据 |
| P4 浏览器与静态验证 | 10 | 受管候选脚本、结构/页头/布局/组件守卫及其测试 |
| 生成清单 | 6 | component takeover、rendering detail、official design alignment、visual projection，以及 push 预检确定性刷新的 complexity budget 与 split-plan queue |
| 交付文档 | 2 | 本报告与既有 context switch log |
| 目标记录 | 1 | `.agent/goals/PROJECT-PROFILE-PAGE-PRODUCTIZATION.yaml` |

完整差异不包含契约 schema、权限规则、金额口径、关系 domain、保存/流程实现、数据库迁移、acceptance 重建或发布配置。P0 回滚边界是通用渲染与导航提交，P1 回滚边界是项目合成视图提交；P4 诊断和生成清单可随对应实现一起回退，无需业务数据回滚。

Draft PR 标题与正文已写入本地 `artifacts/pr_body.md`。本节冻结时必需 CI 尚未运行，不预填通过；后续 push 与 PR 创建状态以远端实时结果为准，ready、merge、release 不在本次授权内。

## fixture 失败诊断

本轮只运行一次受管 `make local.dev.sync_demo`，使用注册的 `sc-local-dev` 与 `sc_dev_demo`。最小诊断输出定位到 `sc.settlement.order(25)`（`SET-DEMO-PJ-EXEC-01`），状态 `approve`：

- 金额依据：`round(amount_total=400000.0 × lifecycle ratio=0.7, currency rounding=2)`，预期 `invoice_amount=280000.0`，实际 `0.0`，不匹配。
- `invoice_ref` 预期非空，实际 `INV-SET-DEMO-PJ-EXEC-01`，匹配。
- `invoice_date` 预期存在，实际 `2026-09-07`，匹配。

只读源码与历史核对表明：`ScSettlementOrder._IMMUTABLE_FACT_STATES` 包含 `approve/done/cancel`；`_ensure_invoice_info` 只在 draft 写入正确金额，对已审批记录只校验且拒绝改写。该不可变事实规则与种子调整在 `031ae353` 同时进入。结论是持久 `sc_dev_demo` 保留了早于当前基线的已审批演示快照，当前同步门禁正确拒绝篡改它；不是本轮 P0/P1 回归，也不是应降低的断言。测试仅增加精确诊断文本，定向 `TestDemoShowcaseGate.test_contract_seed_uses_controlled_fact_lifecycles` 通过（1 method，Odoo 统计 3 tests）。

## 未关闭项

- 正式 fixture-backed acceptance：P4 归因已完成；仍需另行授权并选择受管的 local.dev 重建，或针对旧快照的修复／重放路径，然后从 fixture reset 门禁恢复。本分支未执行二者。该事项不撤销 `20f21091…` 的开发阶段整页产品冻结与只读联合复核结论。
- 真实保存、提交立项、状态变更和多角色业务旅程：本专题未执行，也未用只读诊断替代。
- 全部 Odoo 原生项目入口逐一浏览器遍历：未执行；范围由共享合成视图测试和代表消费者诊断约束。
- 文档治理：inventory、temp guard、contract sync 通过；product boundary 仍因仓库既有 `smart_construction_demo` 文档／目录不一致失败，81 个既有坏链未重跑，二者均不在本产品专题清理。
- 在本地交付包冻结时，PR、CI、合并、发布尚未执行；后续以远端 exact-head 状态为准。当前产品结论不是 merge-ready 或 release-ready。

回滚顺序为先回退 P0 renderer 提交，再回退 P1 项目视图提交；不需要数据库业务数据回滚。
