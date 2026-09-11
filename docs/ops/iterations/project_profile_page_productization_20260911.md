# 项目资料维护页面产品化 · 实施与证据记录

日期：2026-09-11<br>
基线：`origin/main@8f709938ca312e0ecea928945a31f39830c8ec24`<br>
交付分支：`feature/p1-project-profile-page-productization-v1`<br>
产品与测试候选：`3a3df40054661ae6542f820125dbe5454b82a2f6`<br>
文档交付身份：本文件所在提交（仅目标与本报告）

## 结论

项目资料维护的产品实现与受影响范围定向验证已完成：默认正文由“基本信息、计划与责任、责任矩阵”三个真实业务分区组织，日期、权限、动作及手动保存语义保持；共享前端只显示可见、非 notebook 且带稳定锚点的显式业务分区，既有隐藏章节策略不变。页面级章节模式由同一结果驱动标题和导航，拆分渲染不会重新推导或产生重复通用标题。

最终候选已补齐移动状态编辑、精确状态节点承接和中等宽度页头分层。绑定 `3a3df400…` 的项目编辑、驾驶舱 fallback、启停专用表单与付款只读定向诊断在 1440/1088/390/320、明暗主题下通过，零业务写入、错误和失败。受管 Quick 在此前 `264da59d…` 通过；之后仅修改受影响页头、状态适配与验证脚本，并从最早失效门禁补跑定向测试、严格类型、官方组件接管清单、候选 build 和浏览器矩阵，不冒充最终 HEAD 全量重跑 Quick。

当前仍不能冻结为 fixture reset 后的正式浏览器验收候选：受管 `make local.dev.sync_demo` 精确归因到 `sc_dev_demo` 中一个旧的已审批结算快照，与当前不可变事实基线不兼容。当前实现正确拒绝覆盖已审批事实；修复该环境前提需要独立授权的 P4 重建或修复／重放，本产品分支不处理。

## 产品层与归属

| 项目 | 归属 | 理由 |
|---|---|---|
| 项目字段分组、顺序、名称 | P1 `smart_construction_core` 原生项目视图 | 属于建筑行业标准项目资料维护方式 |
| 显式业务分区标题与导航优先级 | P0 通用 native form renderer | 只消费可见 `group` 的公开 `string` 与 `data-sc-anchor`，不识别模型名或字段名 |
| 权限、流程、保存、金额和契约 schema | 未修改 | 本专题只调整表达和既有视图组织 |
| demo fixture 快照不一致 | 独立 P4 治理事项 | 不由本产品分支修复、豁免或重建 |

## 关键边界证明

### 权限等价

从原“施工信息”祖先节点移出的 P1 字段逐字段保留 `smart_construction_core.group_sc_cap_project_read`，没有把权限粗放地加到整个新分组。测试同时比较基础视图与最终合成视图的 `groups`、`invisible`、`readonly`、`required` 有效约束，并通过 `get_view` 验证具有和不具有项目读取能力组时的结果。

### 日期与保存语义

`date_start` 保留在“计划与责任”主区，与单据日期、计划开工和计划竣工共同呈现；没有因标签含义不清将必填字段降到辅助页签。草稿提示明确为手动“保存修改”，并把“提交立项”说明为状态推进与完整校验动作；未新增自动保存。

### 隐藏章节与通用标题

标题与导航共同消费同一组业务分区：业务分区必须是可见 `group`、具有非空权威标题和显式 `data-sc-anchor`，且不能位于隐藏祖先或 notebook 内部。递归遇到隐藏祖先即停止，notebook 内锚点不能单独触发全页权威分区模式。普通布局容器、仅有 `string` 的节点、隐藏节点和普通页签不会因此获得新标题。存在显式业务分区时，旧的字段语义推导标题和关系字段主导航被抑制；没有显式分区的其他表单继续使用原回退路径。定向测试包含隐藏祖先、仅 notebook 锚点和拆分渲染三类反例。

### 首屏与动作职责

项目身份、唯一可交互状态、保存和流程动作集中在页头；“保存修改”与“提交立项”同时可见但职责分开，正文不再重复原生 header。动作呈现保留后端权威 occurrence 去重，但不会因动作在 primary 解析中被降级就删除独立的次级 header 动作。草稿提示明确说明手动保存和提交立项的不同效果，不承诺自动保存。

最终截图人工复核显示：390px 明色与 320px 暗色首屏均能辨识项目身份、草稿状态、保存和提交入口，并到达项目名称及客户等首个关键可编辑字段；未删除状态编辑、字段或缩小字号。移动端用真实 `ScSelect` 消费同一 `lifecycle_state`、同一 selection、readonly 和 busy 状态；只修改本地草稿，切换后还原并刷新，未产生写请求。桌面七段状态在 1440/1088 下保持完整标签，页头身份、状态与动作分层，不再挤碎标题。

桥接层只隐藏页头实际承接的同一 canonical 节点身份，不再按 `widget=statusbar` 批量隐藏。149 项 canonical presenter 用例覆盖两个不同状态字段、页头未承接和只读承接反例；启停专用表单的状态按既有 readonly 表达，仍由原有动作推进，未扩大状态写权限。

### 响应式边界

最终诊断除根文档外检查正文、控件、弹出层和表格边界。桌面责任矩阵表格的外框保持在内容区域内，内部允许的横向滚动能够到达最远列；移动端采用既有卡片表达。真实关系选择弹层被找到且边界检查通过。这里证明的是外层不裁切、内层可达和弹层可操作，不把允许滚动的表格误判为页面溢出。

## 共享视图消费者

| 消费者 | 关系 | 验证结论 |
|---|---|---|
| 项目信息编辑，action 861 / menu 681 | 默认解析 `project.edit_project` 合成视图 | 三个权威分区及导航身份一致 |
| 项目驾驶舱，action 605 / menu 468 | kanban/tree 后的默认 form fallback | 打开项目 19 后得到相同项目资料结构 |
| Odoo 其他未指定专用 form 的 `project.project` 入口 | 同一默认合成视图 | 属于实际影响范围；由后端合成视图测试覆盖，未宣称全入口浏览器遍历 |
| 项目启停管理，action 863 / menu 682 | 显式绑定独立 lifecycle form | 保持专用项目标识、计划信息与状态动作，不被项目资料分区替换 |
| 项目立项与快速创建 | 显式绑定专用 create forms | 不消费本次编辑表单重组，保持独立 |

## 验证索引

| 层级 | 结果 |
|---|---|
| P1 后端 | `make local.dev.upgrade MODULE=smart_construction_core` 通过；`TestCoreExtensionV2Finalize` 18 个方法、Odoo 统计 20 tests，零失败 |
| P0 定向 | `make verify.frontend.native_section_navigation.unit` 通过（7 项章节边界）；canonical presenter 149 项通过；professional workflow 10 个模型用例与 4 个 guard 用例通过；ProductPageHeader 28 个模型用例与 8 个 guard 用例通过 |
| 前端工程 | `3a3df400…` 的 strict typecheck、候选 build、官方组件接管清单及生成清单检查通过；ScSteps 通过公开 wrapper 属性选择不换行标题，未绕过 TDesign 组件 |
| Quick | `make verify.local.dev.frontend.quick.gate` 在 `264da59d…` 按受管入口完整通过。其后的页头、状态适配和验证脚本改动只补跑受影响门禁，不写成最终 HEAD 全量 Quick |
| 基线截图 | `project-profile-before-light-8f709938` 与 `project-profile-before-dark-8f709938`，绑定基线、零写入 |
| 早期诊断 | `b45e52d9` 暴露重复通用标题和提交动作仍在正文；`d755f33d`/`6b66d99d` 的动作权威证据确认提交立项是独立次级 header 动作。这些失败结果用于定向修复，不计为最终通过 |
| 既有结构诊断 | `project-profile-closure-light-83d6c5a5`（1440/390）与 `project-profile-closure-dark-83d6c5a5`（1088/320）继续证明当时的章节、首屏、表格和关系弹层；`project-profile-consumers-diagnostic-light-190ea8d9` 仅证明当时的三个项目消费者，不用于覆盖最终状态交互 |
| 最终消费者诊断 | `project-profile-status-consumers-light-3a3df400`（1440/390）与 `project-profile-status-consumers-dark-3a3df400`（1088/320），覆盖项目编辑、驾驶舱 fallback、启停专用表单和付款只读；均通过、零写入、零错误、零失败。项目编辑移动状态记录 `draft → in_progress → draft`，刷新仍为 `draft`；正文同名状态节点为 0；动作 key 无重复 |
| 最终候选指纹 | `3a3df40054661ae6542f820125dbe5454b82a2f6`，7388 paths，digest `f9c01718914923b41e3a3c9e39e980f249cf203da69fb9a6442030e695af86b5`；候选已通过受管入口停止 |

## fixture 失败诊断

本轮只运行一次受管 `make local.dev.sync_demo`，使用注册的 `sc-local-dev` 与 `sc_dev_demo`。最小诊断输出定位到 `sc.settlement.order(25)`（`SET-DEMO-PJ-EXEC-01`），状态 `approve`：

- 金额依据：`round(amount_total=400000.0 × lifecycle ratio=0.7, currency rounding=2)`，预期 `invoice_amount=280000.0`，实际 `0.0`，不匹配。
- `invoice_ref` 预期非空，实际 `INV-SET-DEMO-PJ-EXEC-01`，匹配。
- `invoice_date` 预期存在，实际 `2026-09-07`，匹配。

只读源码与历史核对表明：`ScSettlementOrder._IMMUTABLE_FACT_STATES` 包含 `approve/done/cancel`；`_ensure_invoice_info` 只在 draft 写入正确金额，对已审批记录只校验且拒绝改写。该不可变事实规则与种子调整在 `031ae353` 同时进入。结论是持久 `sc_dev_demo` 保留了早于当前基线的已审批演示快照，当前同步门禁正确拒绝篡改它；不是本轮 P0/P1 回归，也不是应降低的断言。测试仅增加精确诊断文本，定向 `TestDemoShowcaseGate.test_contract_seed_uses_controlled_fact_lifecycles` 通过（1 method，Odoo 统计 3 tests）。

## 未关闭项

- 正式浏览器候选冻结：P4 归因已完成；仍需另行授权并选择受管的 local.dev 重建，或针对旧快照的修复／重放路径，然后从 fixture reset 门禁恢复。本分支未执行二者。
- 真实保存、提交立项、状态变更和多角色业务旅程：本专题未执行，也未用只读诊断替代。
- 全部 Odoo 原生项目入口逐一浏览器遍历：未执行；范围由共享合成视图测试和代表消费者诊断约束。
- 文档治理：inventory、temp guard、contract sync 通过；product boundary 仍因仓库既有 `smart_construction_demo` 文档／目录不一致失败，81 个既有坏链未重跑，二者均不在本产品专题清理。
- PR、CI、合并、发布：均未执行。

回滚顺序为先回退 P0 renderer 提交，再回退 P1 项目视图提交；不需要数据库业务数据回滚。
