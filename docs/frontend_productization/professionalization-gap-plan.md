# 全系统前端专业化 Phase 0 基线与缺口计划

## 身份与范围

- 基线提交：`1068da05ea9b198f97bbf06b49b7361fabbd9e4f`
- 审计类型：静态、可复现、只读；未启动浏览器、服务、数据库或 fixture。
- Formal Product Layer：P4（工程盘点与证据）；后续 Tokens/Primitives/Shell 等产品实现应分别按 P0 立项。
- 扫描器：`scripts/audit/generate_frontend_professionalization_baseline.py`。
- 输出：`page-surface-inventory.json`、`navigation-authority-inventory.json`、`design-token-inventory.json`、`component-coverage-inventory.json`。

## 当前证据摘要

| 维度 | 静态证据 | 解释 |
| --- | ---: | --- |
| 路由页面面 | 24 | Vue Router 的正式静态入口；record 的 task/workspace 必须由运行时 Contract V2 判定。 |
| 已观察 action/menu 表面 | 70 | 历史角色旅程 CSV，不能视为全量当前权限目录。 |
| 声明式 window action | 416 | XML 静态定义；不等于当前用户可访问的 action。 |
| 声明式菜单 | 422 | XML 静态定义；运行时可见性应以后端导航解释为准。 |
| CSS 变量 | 131 | 需要 Phase 1 归类为 primitive / semantic / component / pattern。 |
| 硬编码色彩词法命中 | 0 | 先作为 allowlist 输入；不把扫描命中直接等同为违规。 |
| 已有 `Sc*` 组件 | 25 | 有基础目录，但无统一 readiness/capability registry。 |
| Phase 2 精确 primitive 缺口 | 8 | 以请求 API 名称严格比对；别名须显式决定。 |

## P0 缺口（平台通用机制）

1. **Design Token v1 权威层缺失。** 现有变量、硬编码值和组件样式共存；Phase 1 应先建立四层 token taxonomy 与 allowlist，再迁移，而不批量改业务布局。
2. **Primitive Adapter API 尚未完整。** `components/design-system` 已提供一部分 `Sc*` 组件，但请求的输入、tabs、table、badge、tooltip、dropdown、form field、loading 等精确 API 未全部存在。Phase 2 应先声明 alias/缺口，再只迁移 Shell 所需组件。
3. **导航权威尚未被一个 Canonical Navigation Model 显式收束。** 静态代码已有 session/menu、router、AppShell、PrimaryNavigation 和 activity 等路径；Phase 3 应仅由后端提供可见性、父链、action/menu 配对、disabled reason、排序和层级，前端仅保留交互状态。
4. **页面 Header 存在多个呈现入口。** Shell 顶栏、`PageHeader`、`ScPageHeader`、列表 Header 和表单/场景 Header 应在 Phase 4 统一 presentation model；本审计不决定视觉重构。
5. **组件能力登记不完整。** 组件和 renderer 已散布在多个目录，但没有一份能声明 `componentKey → capability → fallback → readiness` 的唯一机器可读 registry。Phase 6 需要建立该 registry 和 fail-closed guard。

## P1 缺口（行业能力，等待 P0 registry）

1. 项目、合同、付款、结算等领域表面已通过 action/model 被观察到，但其 component profile 不能由模型名或标签在前端推断；应在 Phase 9 由行业模块以正式契约声明。
2. x2many、workflow、audit、collaboration 等复杂业务能力需要在 Phase 7/8 建立通用 capability 后再按领域接入；当前仅记录 renderer 位置与缺口，未提出模型特判。

## 运行态证据缺口

- 当前用户最终导航树、菜单父链、无权入口、收藏/最近使用、折叠偏好及深链恢复需要未来受管运行态抽样。
- action/view/role/presentationMode 组合需要 Contract V2 trace；静态扫描不得推测 task/workspace。
- 390px overflow、键盘焦点、Drawer Escape 与业务 mutation 需要后续每个 P0 批次的受管浏览器证据。

## 实施顺序与独立 PR 边界

1. Tokens → 2. Primitives → 3. Navigation Shell → 4. Page Header → 5. Page Patterns → 6. Component Registry → 7/8. 通用组件能力 → 9. 行业组件 → 10. 业务域推广。

每项均独立分支/PR、独立指纹和回滚点；Phase 0 不承载任何产品改动。任何业务域发现 P0 缺口时，应暂停业务域批次，回到独立 P0 修复。

## 下一步

对本审计进行只读评审，确认四份 JSON 的字段边界与 P0/P1 分类。通过后仅启动 `feature/p0-design-token-system-v1`，不并行启动 Shell 或行业组件写入。
