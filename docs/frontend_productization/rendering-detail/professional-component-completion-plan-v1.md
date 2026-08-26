# 前端渲染细节专业组件化收敛计划 v1

## 权威与完成口径

- 机器清单：`component-professionalization-inventory-v1.json`。
- 正式范围：仓库内 P0/P1 产品前端；P3 低代码与管理后台单独交付。
- 状态只允许 `governed_primitive`、`governed_composite`、
  `deliberate_native_composite`、`p3_out_of_scope`、`gap`。
- 原生控件不是自动缺陷，但必须有明确复合组件归属和 guard；否则保持 `gap`。
- 全目标完成要求正式 P0/P1 `gap = 0`，并由运行态抽样证明机器清单没有把静态标记冒充产品行为。

## PR 组织原则

- 一个 PR 交付一个可独立验收、可独立回滚的横向产品结果。
- 每个 PR 目标为 12–20 个责任提交；小提交只跑对应定向测试。
- Quick、production build、受管浏览器、指纹和独立评审仅在批次冻结时执行一次。
- 权限、Contract V2、路由、task/workspace、迁移或数据修复不混入低风险前端批次。
- 如果实现暴露新的契约或权限缺口，暂停当前 UI 批次，另立高风险 P0 修复。

## Batch 1：P0 Inline/Full State Completion

分支：`feature/p0-inline-full-state-completion-v1`

目标：建立内联、区块和全页状态的正式密度层级，关闭当前明确的 8 个状态表面。

计划责任提交（18）：

1. 生成全系统 rendering-detail 机器清单。
2. 固化全系统批次计划与完成口径。
3. 新增 `ScInlineState` primitive。
4. 补齐 `ScErrorState` 的 density 与 heading-level 边界。
5. 建立状态 primitive 正反例测试。
6. 收敛 AppShell 公司上下文空状态。
7. 收敛 AppShell 记录上下文 loading/empty/error。
8. 收敛 GlobalMessage 会话列表状态。
9. 收敛 GlobalMessage 消息线程与发送错误状态。
10. 收敛 UnsupportedActionSurface 全页错误状态。
11. 收敛 BlockRenderer 区块错误状态。
12. 收敛 ContractFormDriverHost driver/block/activity 状态。
13. 收敛 x2many readonly empty 与局部 validation 状态。
14. 收敛 collaboration panel/timeline 状态。
15. 建立 state ownership 静态 guard 与反例。
16. 建立 desktop/390px/focus/reduced-motion 浏览器 harness。
17. 接入单一 Make 定向入口并刷新机器清单。
18. 记录交付上下文与确定性工程报告。

本批验收后，8 个 `targetBatch=p0-inline-full-state-completion-v1` 项必须全部退出 `gap`。

## Batch 2：P0 Collection, Navigation and Hierarchy Completion

分支：`feature/p0-collection-state-control-completion-v1`

目标：将 Collection 页面、查询、分组、分页、批量操作、kanban、移动行、
Shell 导航和层级浏览绑定正式复合组件权威，不修改 action、route 或 Contract 权威。

责任提交预算 12–20，覆盖：

- Action/Collection headers、pagination、grouping、batch actions；
- kanban/mobile row、row cell、selection、column header；
- MenuTree、breadcrumb、mobile drawer、workspace context；
- hierarchy browser、planner、worksheet 和 recursive tree node；
- loading/empty/error/disabled/focus 状态身份；
- 真实生产组件的 desktop/390px 抽样；
- 结构化 ownership binding 和 fail-closed guard。

本 PR 容纳两个相邻、同风险的机器 ownership batch：Collection 15 个与
Navigation/Hierarchy 9 个，共 24 个表面必须全部退出 `gap`。
二者共享前端 primitive、state guard 和无 mutation 浏览器证据，因此不机械拆 PR。

禁止把 native control 数量直接当成缺陷，也禁止用目录级 allowlist 跳过扫描。

## Batch 3：P0 Form, Relation, Workflow and Collaboration Completion

目标：完成 Form Fields、Relations/x2many、Workflow、Audit、Collaboration 的渲染细节闭环。

预计 18–20 个责任提交，覆盖：

- FormSection、ProfessionalBase/BusinessValue controls；
- NativeFormTreeRenderer、form header/action blocks；
- relation search、many2one/many2many、one2many validation/pagination；
- workflow disabled reason、primary/overflow/confirm；
- attachment/activity/comment/follower readable fallback；
- create/edit/readonly × task/workspace 组合；
- mutation 精确值与记录级权限降级不变。

## Batch 4：P0 Utility/Scene State and Final Coverage Closure

目标：处理仍在正式产品范围内的认证、错误页、workbench、scene host 和通用 utility 表面，并完成最终机器审计。

预计 12–20 个责任提交，覆盖：

- login/activation/recovery、access denied/not found；
- Workbench/My Work/role home；
- Scene host、contract block grid、generic action/model pages；
- loading skeleton、error summary、page identity 状态；
- 对余下每个 `gap` 作实现、明确复合归属或正式层级重分类；
- 最终 P0/P1 `gap = 0` 的机器断言和受管代表旅程。

## P3 独立计划

以下不阻断 P0/P1 完成，但不得消失在清单中：

- CurrentFormFieldSettingsPanel；
- Business Config panels；
- Menu Config；
- Scene Packages/Health；
- Release Operator；
- Usage Analytics。

它们进入后续 `P3 Admin and Low-code Surface Professionalization`，不得为了清零 P0/P1 将其错误标记为 `governed_composite`。

## 每批统一封板

1. 机器清单生成与 stale check。
2. 受影响 guard/单测非零通过。
3. strict typecheck。
4. Frontend Quick 一次。
5. production build 一次。
6. 最多两条受管浏览器旅程，覆盖 desktop 与 390px。
7. browser errors 0，非保存旅程 mutation 0。
8. 完整候选指纹。
9. 独立只读评审。
10. 一个中等 PR、一次 exact-head CI。
