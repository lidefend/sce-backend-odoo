# ADR-002：前端图表渲染引擎（ECharts）

- 状态：Accepted（2026-09-05 批准；批准范围=仅本 ADR，ADR-004/005/006 维持 Proposed 待批。批准即接受全部 6 项内置条件，`visualization.chart` capability 可进入 G6 只读实现；写入路径仍按总控 G7 门禁另行决策）
- 范围：custom-frontend-integration G5 / Chart 专题
- 决策项：是否引入 ECharts、固定版本、bundle 预算与引入方式

## 背景

总控计划 §18 决策待办：「ECharts 是否引入、固定版本和 bundle 预算」。图表契约边界已由专题文档锁定：只允许后端登记的 metric、dimension 和 dataset ref，不接受前端自由聚合公式或任意 option。本 ADR 只裁决渲染引擎与引入方式，不裁决业务图表清单。

## 事实核查（2026-09-03）

| 项 | 结论 | 来源 |
| --- | --- | --- |
| 最新版本 | 6.1.0（2026-05-19 发布） | echarts.apache.org/download |
| 许可证 | Apache-2.0（内嵌 d3 子组件为 BSD-3-Clause，均宽松） | 官方下载页 / licensie 扫描 |
| 已知漏洞 | 6.1.0 无已知漏洞（Snyk） | snyk.io/vuln/npm:echarts |
| 运行时依赖 | 仅 tslib + zrender | Snyk 依赖树 |
| 体积 | 全量 ~360KB gzip；tree-shakeable core + 按需引入后原型估算 ~95KB gzip | 第三方 2026-06 实测 + 专题原型估算 |

## 决策（已批准，2026-09-05）

**批准引入 `echarts@6.1.0`（精确锁定 minor，patch 升级须过门禁），条件如下：**

1. **只允许 tree-shakeable 引入**：`echarts/core` + 按需 Chart/Component + 单一 `CanvasRenderer`；禁止 `import * as echarts from 'echarts'` 全量引入（守卫拦截）。
2. **bundle 预算**：图表子集 gzip ≤120KB；超出即回审。测量以冻结基线 + 候选版本实测为准，不得引用原型估算值作为验收。
3. **不进首屏**：图表 renderer 经路由级/块级 dynamic import 懒加载；主 chunk 体积预算不变。
4. **契约先行**：仅消费 `visualization.chart` capability（后端登记 metric/dimension/dataset ref）；前端不得自行聚合财务/项目事实（总控 §3 表格禁令）。
5. **涨红跌绿**：涨/收入/正数→红、跌/支出/负数→绿的中国市场约定在 adapter 层固化为主题 token，不由业务组件散落配置。
6. **主题对齐**：颜色经现有 `@sc/design-tokens` 语义 token 注入（含 chart 色板 token），禁止图表内硬编码色值（现有 design_token_system 守卫语义延伸）。

## 替代方案与否决理由

| 方案 | 体积(gzip) | 许可证 | 否决/保留理由 |
| --- | --- | --- | --- |
| Chart.js 4.x | ~68KB | MIT | 更小但图表类型/交互/大数据量能力弱于 ECharts，中文生态与文档弱 |
| AntV G2 5.x | ~321KB | MIT | 体积与 ECharts 相当，无决定性优势，社区规模较小 |
| 自研 SVG | - | - | 长期维护成本高，专题文档已列为待 ADR 但不推荐 |

## 回退策略

- `visualization.chart` capability 未注册/校验失败 → 块级降级为通用空态（复用 G3.2 四态状态机模式），不白屏。
- 移除 echarts 依赖不影响任何既有能力（图表是纯增量 capability）。

## 后果

- 新增 1 个生产依赖（当前 Web 生产依赖仅 Vue/Pinia/Vue Router，本 ADR 是首个新增大型依赖，须同步更新体积/安全评审记录）。
- 批准后 G6 才能开始图表 renderer 实现；renderer 实现仍须单独立项拆分。
