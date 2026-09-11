# 项目资料维护页面产品化 · 实施与证据记录

日期：2026-09-11<br>
基线：`origin/main@8f709938ca312e0ecea928945a31f39830c8ec24`<br>
交付分支：`feature/p1-project-profile-page-productization-v1`<br>
产品与测试 HEAD：`190ea8d9d5126dd8beeb4c3cabe7d4fbedca03fb`<br>
文档交付身份：本文件所在提交（仅目标与本报告）

## 结论

项目资料维护的产品实现与定向验证已完成：默认正文由“基本信息、计划与责任、责任矩阵”三个真实业务分区组织，日期、权限、动作及手动保存语义保持；共享前端只显示带稳定锚点的显式业务分区，既有隐藏章节策略不变。

当前不能冻结为正式浏览器验收候选。受管 `make local.dev.sync_demo` 在本分支改动之外的 `smart_construction_demo` 既有结算单发票快照断言处失败。之后绑定 exact HEAD 的浏览器结果仅作为只读诊断证据，不替代 fixture reset 后的正式验收。

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

业务标题必须同时满足：可见 `group`、非空权威标题、显式 `data-sc-anchor`。普通布局容器、仅有 `string` 的节点、隐藏节点和普通 notebook 页签不会因此获得新标题。存在显式业务分区时，旧的字段语义推导标题和关系字段主导航被抑制；没有显式分区的其他表单继续使用原回退路径。

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
| P0 定向 | `make verify.frontend.native_section_navigation.unit` 通过；native form structure boundary guard 通过 |
| 前端工程 | strict typecheck 通过；lint 为 0 error、32 个既有 warning |
| Quick | 静态步骤通过；本独立 worktree 缺少本地 `.env.dev`，Quick 内 build 步骤为环境前提失败；受管 exact-head candidate build 通过 |
| 基线截图 | `project-profile-before-light-8f709938` 与 `project-profile-before-dark-8f709938`，绑定基线、零写入 |
| exact-head 诊断 | `project-profile-diagnostic-light-190ea8d9`（1440/390）与 `project-profile-diagnostic-dark-190ea8d9`（1088/320），均通过、零写入、零错误 |
| 消费者诊断 | `project-profile-consumers-diagnostic-light-190ea8d9`，信息编辑、驾驶舱 fallback、启停专用表单在 1440/390 均通过、零写入 |
| 产品与测试指纹 | `artifacts/fingerprints/project_profile_page_productization_candidate_190ea8d9.json`，7387 paths，digest `32d2d17ba02224c045eb91a9281a3965846167bec91b54d4a72a8c4bad9ab1cc` |

## 未关闭项

- 正式浏览器候选冻结：等待独立 P4 demo fixture 快照问题治理后，从 fixture reset 门禁恢复。
- 真实保存、提交立项、状态变更和多角色业务旅程：本专题未执行，也未用只读诊断替代。
- 全部 Odoo 原生项目入口逐一浏览器遍历：未执行；范围由共享合成视图测试和代表消费者诊断约束。
- PR、CI、合并、发布：均未执行。

回滚顺序为先回退 P0 renderer 提交，再回退 P1 项目视图提交；不需要数据库业务数据回滚。
