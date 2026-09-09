# 前端阶段交付包（2026-09-10）

## 1. 交付判定

- 状态：`READY_FOR_PR_AUTHORIZATION`。
- 含义：本地产品结果、受影响行为和代表页面证据已经冻结，可以在获得远端写入授权后进入 draft PR；不代表已经推送、创建 PR、通过远端 CI、具备合并或发布资格。
- 当前分支：`feature/frontend-page-experience-iteration-v1`。
- 当前审查 HEAD：`8cd5cdebcd0b1127e1d7ddcada672077f25afa7f`。
- 工作区：审查时 clean；本交付包只增加 P4 文档，不重新打开前端产品迭代。

## 2. 边界与身份

| 身份 | SHA | 用途 |
| --- | --- | --- |
| 当前 `main` / `origin/main` 合并基线 | `74297675ea86af98af0d222efa4fe692c28e1ffe` | 未来 PR 的完整净差异基线 |
| 前端阶段产品基线 | `3d3975b3d45c1462677df0abcbb5708e4b53e0b1` | 系统页面、共享基础、官方组件和最终表达阶段的起点 |
| 冻结产品候选 | `df3227c38e908b883ed45553e9511b03b59a3348` | 最后一个 P0/P3 产品提交；用户可见产品结论绑定此 SHA |
| 最终验证与冻结证据 | `8cd5cdebcd0b1127e1d7ddcada672077f25afa7f` | 在产品候选后仅修改 3 个验证文件和 2 个文档文件 |
| 整理前完整指纹 | `34c6d7f5815af7727555e17f35ecb00d1708d9222e5b6a5bd41439cef37a96af` | baseline=`74297675…`，7349 paths；绑定交付包整理前 clean HEAD |

Formal Product Layer：本文件及 PR 准备属于 P4。产品净结果包含 P0 通用前端运行时、少量 P0 通用后端装配/错误表达和 P3 配置工作台表达。

Layer Target：共享前端 primitives、页面外壳、集合/表单/层级工作区、配置工作台表达，以及分离列明的 P4 验证和 acceptance 环境恢复工具。

Standard vs User-Specific：均为平台通用交互/表达、管理员配置工作台状态表达和交付治理；没有新增施工行业业务规则、客户偏好或客户数据基线。

Why Here：用户可见表达由通用前端承担；运行时配置页面的既有状态表达属于 P3；测试、证据、PR 元数据和环境恢复入口属于 P4。

Why Not Elsewhere：不把 P4 恢复脚本描述成产品能力，不把业务语义放入前端，不把已撤出的历史 P1 迁移重新纳入候选。

Blast Radius：首页、我的工作、通用列表/详情、关系字段、层级工作区、配置工作台、共享外壳与设计适配层；后端仅涉及既有通用页面装配与失败文案。启动链、public intent、default route、权限裁决和业务写语义不变。

## 3. 分支范围拓扑

整理前只读清单如下：

| 范围 | 提交数 | 净路径数 | 说明 |
| --- | ---: | ---: | --- |
| `74297675…3d3975b3` | 39 | 63 | 本分支在正式阶段基线前已经承载的共享前端基础；属于未来 PR 历史，不能从 PR 差异中隐去 |
| `3d3975b3…df3227c3` | 131 | 155 | 本阶段产品、测试、证据及独立列明的 P4 环境工具 |
| `df3227c3…8cd5cdeb` | 3 | 5 | 仅最终组件证明修正和冻结文档，无产品源码变化 |
| `74297675…8cd5cdeb` | 173 | 191 | 未来 PR 在整理前的完整净差异；分类器按此范围判定风险 |

未来 PR 审核必须同时看完整 `main…PR_HEAD` 范围和本阶段 `3d3975b3…df3227c3` 产品范围。不能只审最后 3 个证明提交，也不能把分支中的 P4 工具算成前端产品改动。

## 4. 产品范围清单

### 4.1 P0 通用前端产品

- 系统外壳与页面层级：`AppShell`、Activity tabs、侧导航、`ProductPageHeader`、首页和“我的工作”的统一标题、内容起点和窄屏操作可达性。
- 集合与详情：通用列表搜索、列可见性/宽度、横向浏览控制、移动记录卡、空/错/加载状态、表单页头、返回上下文和只读详情工作表面。
- 层级工作区：scope 选择、可见记录选择、键盘分隔条、窄屏 drawer、详情和滚动恢复。
- 表单与关系：错误摘要、焦点投影、relation 查询/弹层生命周期、One2Many 单元编辑和窄屏 dialog 边界。
- 主题与视觉规则：明暗/系统主题继承、语义 token、工作区 surface、内容密度、边框和主次操作层级。
- 官方组件接入：锁定既有 `tdesign-vue-next@1.20.5`，通过公开 props、事件和插槽消费，不依赖内部 DOM 结构。

### 4.2 共享组件变化

| 能力组 | 主要组件 | 最终变化 |
| --- | --- | --- |
| 输入与选择 | `ScInput`、`ScSelect`、`ScRelationField` | 公开属性/事件、清除、远程搜索、弹层会话和响应归属 |
| 操作 | `ScButton`、`BlockMetricRow` | 结构化内容由适配层承载；disabled/loading 由真实 props 投影；鼠标/键盘 exactly-once |
| 表面 | `ScCard`、`ScPanel` | Card 公开 body/actions 扩展点；新增通用 `workspace` tone，减少重复包框 |
| 状态 | `ScErrorState`、`ScErrorSummary`、`ScInlineState`、`StatusPanel` | 统一错误、空态、加载、恢复操作和焦点表达 |
| 浮层 | `ScDialog`、`ScDrawer` | 初始焦点、嵌套恢复、body lock、窄屏边界和 Escape 返回 |
| 数据表达 | `ScTable`、`ScMoney`、集合行/列组件 | 横向访问、列宽/可见性、币种权威和移动事实完整性 |
| 主题桥 | design tokens、TDesign theme、`SceneUiProvider` | 语义 token、明暗主题及 scene surface 继承，不另建视觉体系 |

### 4.3 P0 后端与 P3 表达

- P0 后端：`page_assembler.py` 透传层级列/详情显示元数据；`execute_button.py` 仅澄清不支持动作的通用失败文案。
- P3：配置工作台拆分 loading/empty/error/draft/published/rollback-failed 等已有状态的表达与窄屏布局；没有执行配置发布、回滚或业务写入。
- 后端测试文件用于证明既有真实 ORM/配置生命周期边界，不构成新增业务语义。

## 5. P4 范围单列

### 5.1 前端验证与证据工具

- `scripts/verify/local_dev_candidate_visual_smoke.{sh,mjs}`、`scripts/dev/local_dev_candidate_frontend.py`：受管 local.dev 候选、页面矩阵和最终交互证据。
- `scripts/verify/frontend_*_guard.py` 及对应非零测试：页面身份、组件适配、关系、层级、主题、集合、官方设计清单和图表公开入口守卫。
- `scripts/audit/generate_frontend_*_inventory.py` 与 `docs/frontend_productization/rendering-detail/*.json`：生成清单及四项官方设计零缺口证据。
- `make/frontend.mk`、`make/runtime_ops.mk`：既有前端/配置验证入口的增量接线。
- `docs/ops/iterations/frontend_*_20260909.*`：阶段计划、历史诊断、最终通过和证据索引。

### 5.2 夹带在分支历史中的 acceptance 环境工具

以下文件属于独立 P4 环境恢复能力，不属于前端产品改善：

- `scripts/dev/frontend_acceptance_baseline_rebuild.sh`
- `scripts/dev/frontend_acceptance_runtime.sh`
- `scripts/verify/test_frontend_acceptance_baseline_rebuild.py`
- `make/dev.mk`
- `docs/ops/environment_tiers_unified_runbook_v1.md`
- `docs/ops/iterations/frontend_acceptance_fixture_namespace_rebuild_design_20260909.md`

它们提供 fail-closed audit、dry-run、整卷冷备/恢复和失败注入测试。实际 destructive apply、acceptance 重建、fixture reset 和 release gate 均未在本轮执行。历史 `.163/.164` P1 迁移及资金 fixture 改动已从当前净候选撤出；Git 历史和旧 acceptance 数据库事实仍保留，但不能算作本 PR 的产品能力或通过证据。

## 6. 证据索引

| 结论 | 候选/命令 | 最终证据 | 状态 |
| --- | --- | --- | --- |
| 官方组件公开接入和四项清单归零 | `f9797273`；Frontend Quick | `frontend_official_component_usage_cleanup_20260909.md` | PASS |
| Input/Select/Card/Alert 与正式页面按钮行为 | `c755e551` | `artifacts/playwright/frontend-final-component-behavior-light-1440-390-c755e551/summary.json`、dark 1088/320 对应摘要 | PASS；mutation 0，errors/failures 0 |
| `ScButton` disabled/loading props | `make verify.frontend.overlay_lifecycle.browser` | `structuredButtonProps`：1 → disabled 1 → loading 1 → restored 2 | PASS；组件浏览器测试，不冒充正式页面 |
| Alert 单次重试 | `c755e551` 正式页面只读旅程 | 四个桌面/移动组合均 `operationCount=1`、`retryRequestCount=1` | PASS |
| 全局表达 | 产品 `df3227c3`，证据 `c755e551` | `frontend-final-expression-{light-1440-390,dark-1088-320}-c755e551/summary.json` | 20/20 PASS；mutation 0，errors/failures 0 |
| 层级工作区 | `ea971cea` / `abda1089` | `frontend_hierarchical_workspace_c1_20260909.md` 及 drawer 补验报告 | PASS |
| 付款列表/详情与返回上下文 | `178df07b` | `frontend_payment_journey_expression_closure_20260909.md` | PASS；只读样板 |
| 配置工作台状态表达 | `de1c04cd` / `dc6e81d6` | `frontend_system_page_experience_closure_20260909.md` 与独立页面矩阵 | PASS；empty changeset，无配置写入 |
| 产品候选静态/构建/生成清单 | `df3227c3` | `make verify.frontend.quick.gate` 留存记录 | PASS |
| 最终证明修正的受影响门禁 | `8cd5cdeb` | 9 candidate tests；10 overlay unit；27 Python + 46 JS primitive scenarios；10 browser scenarios | PASS |
| 完整工作树身份 | `8cd5cdeb` | `artifacts/fingerprints/frontend_expression_final_acceptance_8cd5cdeb.json` | PASS；digest `44aa1c4c…`，7349 paths |

浏览器 artifact 位于本地受管 artifact authority，未作为 Git 产品源码提交。5174 不是本批证据；最终候选使用受管 5176，完成后已停止。

## 7. 历史失败与最终通过分离

- 首轮系统页面独立审查为 `REQUEST_CHANGES`：配置层级说明、XML stub 证明边界、顶栏/浮层断言和真实 authority 路由证据不足。后续修正通过，旧失败报告只保留审计轨迹。
- exact HEAD `016a8443…` 的历史 `verify.frontend.release.local` 为 FAIL：验证器将权限拒绝误等同普通详情，归类为 P4 `validation_tool_defect`。该失败不改写为 PASS，也不由本地视觉证据替代。
- acceptance 数据库曾升级到 `.164` 而当前源码恢复为 `.162`；未重建前不能作为当前产品候选的 release authority。
- `frontend-global-expression-before-*` 属于对照基线；最终通过只引用 `frontend-global-expression-after-*` 和 `frontend-final-expression-*`。

## 8. PR 与 CI 只读核对

- `make pr.status`：当前分支无关联 PR；当前账户无开放 PR。没有执行 push、PR 创建或 PR 更新。
- 权威远端：`origin=https://github.com/lidefend/sce-backend-odoo.git`；base 为 `main`。
- 当前完整 PR 范围经 `ci_risk_classifier.py` 判定：`lane=HIGH_RISK`、`backend_changed=true`、`frontend_full_required=true`、`frontend_mode=full`、`professional_mode=full`，原因包含 `high_risk_path` 与 `unknown_path_fail_closed`。
- 合并资格所需 exact-head 检查：`public_guard`、`professional_quality_gate`、`frontend_release_gate`、`merge_policy_gate`。当前均为 `not_run`，因为远端分支和 PR 不存在。
- `release_candidate_gate` 是独立的发布资格，不是普通 PR 合并资格；本地整理不触发它。
- `ci.local.quick` 的 exact-head 合并证据需在最终 PR HEAD 冻结后按受管入口生成或复用；本轮没有为了文档整理机械重跑。

## 9. 后续依赖清单

| 依赖 | 当前状态 | 后续独立任务 |
| --- | --- | --- |
| 契约缺口 | 本阶段未新增或补写 contract/schema；现有链仍为 `login → system.init → ui.contract` | 若业务页面缺少正式字段、动作或权限原因，单独按契约专题处理，不回到前端猜测 |
| 多角色 | 未覆盖 | 以正式角色 fixture 执行独立授权/可见性矩阵 |
| 真实写入 | 未覆盖 | 对保存、提交审批、配置发布/回滚分别建立受权业务验收；不复用本批只读结论 |
| 当前版本 acceptance 环境恢复 | 未执行 | 独立 P4 任务：通过受管重建使验收数据库、filestore、session、fixture 和当前源码版本重新形成可信 authority；只证明当前版本载体，不证明旧版本升级 |
| 旧版本升级兼容 | 未证明；尚未冻结明确源版本样本 | 独立兼容专题：先定义源版本数据库、filestore、模块版本、数据特征和预期迁移结果，再执行受管增量升级与兼容验收；不能由当前版本环境重建替代 |
| PR/CI | 未运行 | 获得授权后 push、创建 draft PR，冻结 exact head 并等待四项 required checks |
| 发布验收 | 未运行 | 独立授权 acceptance/release candidate 流程；不得把 merge gate 等同发布 gate |

这些事项均不阻断“待授权进入 PR”，但阻断“可合并”或“可发布”的提前声明。当前版本 acceptance 环境恢复与旧版本升级兼容没有前后替代关系；是否分别启动及其样本 authority 均需另行授权。

## 10. 风险与回退

- PR 范围大：相对 main 有 191 个整理前净路径，且含后端、Make 和未知路径，因此必须按 HIGH_RISK 审查，不能只看 UI 截图。
- 环境工具与产品同分支：PR 描述和 reviewer 路由必须显式分开 P0/P3 产品、P4 验证、P4 acceptance 恢复工具。
- 产品回退边界：前端阶段整体回到 `3d3975b3`；官方组件适配以 `f9797273` 为独立节点；最终表达以 `648e4d4b`、`df3227c3` 为独立节点；证明修正为 `c755e551`。
- P4 acceptance 恢复工具可按 `aba26adc`、`c6f5658e` 独立回退，不要求回退产品候选。
- 本地文档整理可按本交付包提交整体回退；不会改变数据库、fixture、远端或运行服务。

## 11. 下一步

唯一下一步是获得“进入 draft PR”的明确授权。授权后仍须先确认 clean worktree、最终完整 SHA、base SHA 和 PR body，再仅通过受管 `make pr.push` / `make pr.create` 执行；本文件没有授予这些远端写操作。
