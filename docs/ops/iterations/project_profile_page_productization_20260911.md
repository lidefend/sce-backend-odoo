# 项目资料维护页面产品化 · 实施与证据记录

日期：2026-09-11<br>
基线：`origin/main@8f709938ca312e0ecea928945a31f39830c8ec24`<br>
交付分支：`feature/p1-project-profile-page-productization-v1`<br>
产品与测试 HEAD：`83d6c5a5b5799077448320862a4663f48725b4fa`<br>
文档交付身份：本文件所在提交（仅目标与本报告）

## 结论

项目资料维护的产品实现与定向验证已完成：默认正文由“基本信息、计划与责任、责任矩阵”三个真实业务分区组织，日期、权限、动作及手动保存语义保持；共享前端只显示可见、非 notebook 且带稳定锚点的显式业务分区，既有隐藏章节策略不变。页面级章节模式由同一结果驱动标题和导航，拆分渲染不会重新推导或产生重复通用标题。

受管 Quick 已在最终产品与测试 HEAD 通过；绑定该 HEAD 的只读浏览器诊断也在 1440/1088/390/320、明暗主题下通过，零业务写入、错误和失败。但当前仍不能冻结为正式浏览器验收候选：受管 `make local.dev.sync_demo` 在 `smart_construction_demo` 结算单发票快照断言处失败。之后的浏览器结果仅作为 exact-head 诊断证据，不替代 fixture reset 后的正式验收。

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

最终截图人工复核显示：390px 明色与 320px 暗色首屏均能辨识项目身份、草稿状态、保存和提交入口，并到达项目名称及客户等首个关键可编辑字段；未删除状态编辑、字段或缩小字号。桌面首屏同时展示“基本信息”和“计划与责任”的核心字段。

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
| P0 定向 | `make verify.frontend.native_section_navigation.unit` 通过（7 项章节边界）；canonical presenter 143 项通过；native form structure、scene component bridge 等 guard 通过 |
| 前端工程 | 最终 HEAD 的 strict typecheck、build、官方组件与生成清单检查均通过 |
| Quick | `make verify.local.dev.frontend.quick.gate` 在 `83d6c5a5…` 完整通过。早期直接运行未受管 Quick 时因独立 worktree 缺少 `.env.dev` 失败，仅保留为无效环境诊断，不再代表最终门禁状态 |
| 基线截图 | `project-profile-before-light-8f709938` 与 `project-profile-before-dark-8f709938`，绑定基线、零写入 |
| 早期诊断 | `b45e52d9` 暴露重复通用标题和提交动作仍在正文；`d755f33d`/`6b66d99d` 的动作权威证据确认提交立项是独立次级 header 动作。这些失败结果用于定向修复，不计为最终通过 |
| 最终 exact-head 诊断 | `project-profile-closure-light-83d6c5a5`（1440/390）与 `project-profile-closure-dark-83d6c5a5`（1088/320），绑定 `83d6c5a5…`，均通过、零写入、零错误、零失败；章节、页头、首屏字段、表格最远端与关系弹层证据均通过 |
| 消费者诊断 | `project-profile-consumers-diagnostic-light-190ea8d9`，信息编辑、驾驶舱 fallback、启停专用表单在 1440/390 均通过、零写入 |
| 产品与测试指纹 | `83d6c5a5…`，7388 paths，digest `85a40e81f4cdaf0a9d93b20fc8302553ec9a70f4d2706acec301f88750ec13ca`；候选已通过受管入口停止 |

## fixture 失败诊断

`make local.dev.sync_demo` 使用注册的 `sc-local-dev`、数据库 `sc_dev_demo`，失败位置为 `demo_addons/smart_construction_demo/seed/steps/step_40_contracts_demo.py:331` 的 `_ensure_invoice_info`。断言要求已审批／非草稿演示结算单同时满足：`invoice_ref` 存在、`invoice_date` 存在，且 `invoice_amount == round(amount_total * lifecycle ratio, 2)`；当前输出为“已审批演示结算单的发票快照与标准样本不一致”。

受管输出没有给出失败记录身份及各字段的预期／实际值，因此尚不能在本专题内判断是 fixture 前提失效、断言脚本问题还是产品数据问题。取得具体预期／实际值需要独立授权的 P4 诊断能力；本分支未手工查询或修改数据库、未降低断言、未重建 fixture，也未把该失败归因成本轮 P0/P1 产品实现。

## 未关闭项

- fixture 归因与正式浏览器候选冻结：先由独立 P4 诊断提供失败记录及预期／实际值并完成分类，再从 fixture reset 门禁恢复；不能仅凭当前复合断言称为“fixture 已确认”。
- 真实保存、提交立项、状态变更和多角色业务旅程：本专题未执行，也未用只读诊断替代。
- 全部 Odoo 原生项目入口逐一浏览器遍历：未执行；范围由共享合成视图测试和代表消费者诊断约束。
- PR、CI、合并、发布：均未执行。

回滚顺序为先回退 P0 renderer 提交，再回退 P1 项目视图提交；不需要数据库业务数据回滚。
