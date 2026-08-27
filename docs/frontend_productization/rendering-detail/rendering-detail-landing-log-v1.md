# 渲染细节落地记录 v1（组件体系引入后）

> 分支：`feature/p0-theme-profile-switching-v1`（连续迭代段）
> 范围：TDesign 组件体系收敛后，正式 P0/P1 产品前端渲染细节的治理与呈现落地
> 约束遵守：未触碰 Contract V2 / action / route / 后端契约；纯前端迭代

## 1. 背景

组件体系已收敛到 TDesign 单底层（tdesign-modern + sc-native 降级，UI5 已移除）。
「组件体系引入后的渲染细节落地」的目标是：让产品页面的渲染状态表面、
页面模式（heading 所有权）等细节进入机器治理，而不是依赖人工维护。

本轮连续迭代处理了渲染细节验证暴露的 **2 个实质缺口**（均位于通用列表页
`ListPage.vue`，是 render 细节治理的最后一公里）。

## 2. 迭代明细

### 2.1 ListPage 渲染状态表面治理（commit 13e73fae）

**问题**：`verify.frontend.rendering_detail_state.unit` 3 个测试失败，根因是
`ListPage.vue` 的渲染状态锚点 `data-semantic-component="ListPage"` 与
`:data-list-status="status"` 挂在 `<ScPage>` 根组件上，而权威绑定要求落在
语义 `<section>` 元素（与姊妹页 `KanbanPage` 的 section 模式一致）。
`ListPage` 历史上从 `<section>` 根演进到 `<ScPage>` 根时 guard 未同步，成为
最后一个未治理的 formal P0/P1 渲染表面。

**修复**：将状态锚点从 `<ScPage>` 移到主表格 `<section>`（
`sc-product-main-surface`，承载列表主内容），`<ScPage>` 保留布局属性。

**验证**：42 tests OK；`rendering_detail_state_guard` PASS surfaces=79；
机器清单 gap=0。

### 2.2 ListPage 重复 heading owner 收敛（commit 9437d887）

**问题**：`verify.frontend.page_pattern_reference_parity.unit` 失败——`ListPage`
错误态额外渲染 `<ScPageHeader>`，而页面标题所有权已由 `ListSurfaceHeader`
持有，产生 **duplicate heading owner**，违反页面模式单一标题原则。

**修复**：移除错误态 `<ScPageHeader>` 块及其 import；错误细节已由
`StatusPanel` 完整呈现（title/message/trace-id/error-code/reason/retry），
无需第二标题来源。

**验证**：8 tests OK；`page_pattern_reference_parity_guard` PASS surfaces=13。

## 3. 全量验证结论

| 维度 | 结果 |
| --- | --- |
| `verify.frontend.rendering_detail_state.unit` | 42 tests OK；inventory surfaces=151 gaps=0 |
| `verify.frontend.page_pattern_reference_parity.unit` | 8 tests OK；guard PASS surfaces=13 |
| `verify.frontend.overlay_lifecycle.unit` | PASS canonical=3 consumers=3 formal_gaps=0 |
| `verify.frontend.state_dashboard.unit` | PASS surfaces=3 states=loading,empty,error,disabled,focus |
| `verify.frontend.theme_profile.unit` | PASS profiles=3 |
| `verify.frontend.collection_*.unit`（抽查） | 全部 PASS |
| `typecheck:strict` | EXIT=0 |
| `pnpm build` | EXIT=0 |
| `make verify.frontend.quick.gate` | 全量（后台） |

## 4. 机器清单刷新

修复连锁刷新 3 份机器清单（均已 current）：
`component-professionalization-inventory-v1.json`（151 表面 gap=0）、
`visual-projection-inventory-v1.json`、
`official-design-alignment-inventory-v1.json`（196 样式源、0 vendor 选择器 gap、
0 visual literal gap）。

## 5. 后续候选

- 若后续引入新页面（如行业模型页面），沿用 ListPage 的「语义 section 承载
  渲染状态锚点 + 单一 heading owner」模式。
- 视觉密度/层次细节（间距、圆角、阴影）如需进一步打磨，建议以受管浏览器
  截图基线推进（browser acceptance），避免纯静态 guard 无法覆盖的视觉主观项。
