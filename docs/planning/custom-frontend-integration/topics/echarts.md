# P0-2: ECharts 图表库集成 + 资金分析可视化

> 架构校正：通用图表适配器属于 P0，资金指标与分析口径属于 P1。本文为候选设计，实施以根目录 [`README.md`](../../README.md) 为准。

> 执行状态：`ADR-002` 已批准（2026-09-05 Accepted），`echarts@6.1.0` 已精确锁版引入 web 生产依赖，引入纪律由 `verify.frontend.chart_engine.guard` 守卫（见 [G6 执行记录](../G6_CHART_EXECUTION.md)）。本文下方的库导入示意、体积估算、五个业务图表及 API 名称仍为候选输入，正式实现以 ADR-002 条件与 G6 执行记录为准。图表契约只允许后端登记的 metric、dimension 和 dataset ref，不接受前端自由聚合公式或任意 option。

## 技术方案

### 1. 架构设计

```
Contract 2.0 JSON
  ├── view_type: "dashboard"
  ├── fields[]: chart 类型字段
  │     ├── chart_type: bar | line | pie | stacked_bar | gauge | scatter
  │     ├── dataset_ref: 后端授权的数据集引用
  │     ├── metric_refs[] / dimension_refs[]: 后端登记引用
  │     └── presentation: 受限的图形与格式提示
  └── layout: grid | flex
        ↓
ScFinancialDashboard (容器)
  ├── ScChart (通用图表引擎)
  │     ├── ECharts core (按需引入: bar, line, pie, gauge, tooltip, legend, grid)
  │     ├── 主题注入 (Chinese convention: 涨红跌绿)
  │     ├── 响应式 resize
  │     └── Contract 数据绑定
  ├── ScFundFlowChart (资金流入流出)
  ├── ScContractDistributionChart (合同金额分布)
  ├── ScCostAnalysisChart (成本分析)
  ├── ScPaymentExecutionChart (付款执行)
  └── ScProjectHealthChart (项目健康度)
```

### 2. 后端数据源映射

| 图表 | 后端模型 | 聚合维度 | API Intent |
|------|----------|----------|------------|
| 资金流入流出趋势 | `sc.general.contract` + `payment.ledger` + `sc.fund.account` | 按月汇总：收入合同金额 vs 支出合同金额 vs 实际付款 | `api.chart.fund_flow` |
| 合同金额分布 | `sc.general.contract` | 按 contract_direction 分组，按金额区间分布 | `api.chart.contract_distribution` |
| 成本分析 | `project.budget` + `project.dashboard` | 预算 vs 实际 vs 承诺，按成本域分组 | `api.chart.cost_analysis` |
| 付款执行 | `payment.ledger` + `payment.request` | 按月：申请金额 vs 已付金额，执行率 | `api.chart.payment_execution` |
| 项目健康度 | `project.dashboard` | health_state 分布 + schedule_delta + cost_actual_pct | `api.chart.project_health` |

### 3. ECharts 候选引入示意（禁止实施）

> **SUPERSEDED：**以下代码和体积估算没有锁定版本、构建证据或许可证/CVE 审计，只能作为 ADR 输入。

```typescript
// 只引入需要的模块，减小 bundle 体积
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, GaugeChart, ScatterChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart, LineChart, PieChart, GaugeChart, ScatterChart,
  TitleComponent, TooltipComponent, GridComponent, LegendComponent, DataZoomComponent,
  CanvasRenderer
])
```

原型曾估算约 95KB gzip；正式评审必须用冻结基线和候选版本实测，且满足总控性能预算，不能宣称“不会影响首屏”。

### 4. 中国股市配色约定

- 上涨/收入/正数 → 红色 `#E53935`
- 下跌/支出/负数 → 绿色 `#43A047`
- 中性 → 蓝色 `#1E88E5`
- 警告 → 橙色 `#FB8C00`

### 5. 统一页面契约集成方案

图表通过受版本控制的 `visualization.chart` capability 注入统一页面 envelope，不新增顶层字段类型。数据口径和聚合由后端登记并产出，前端只消费受权 dataset ref：

```json
{
  "capability": "visualization.chart",
  "schema_version": "1.0",
  "payload_ref": "authorized-chart-dataset-ref",
  "metric": "registered.metric.key",
  "dimensions": ["registered.dimension.key"],
  "presentation": {
    "kind": "stacked_bar",
    "show_legend": true,
    "show_data_zoom": true
  },
  "actions": {
    "drill": {"intent": "registered.chart.drill", "enabled": true}
  }
}
```

客户端不得提交自由聚合公式、任意查询参数或任意 ECharts option。未知 metric、dimension、payload 版本或未授权 drill action 必须安全降级。

### 6. 文件清单

| 文件 | 体积 | 职责 |
|------|------|------|
| types/chart.ts | ~3KB | 图表数据类型定义 |
| api/chartApi.ts | ~4KB | 5 个聚合数据 API 封装 |
| utils/chartFormatters.ts | ~3KB | 金额格式化、日期格式化、配色生成 |
| stores/useChartStore.ts | ~5KB | Pinia Store：数据加载、缓存、刷新 |
| components/ScChart.vue | ~6KB | ECharts 通用包装器 |
| components/ScFundFlowChart.vue | ~4KB | 资金流入流出趋势（堆叠柱状图） |
| components/ScContractDistributionChart.vue | ~4KB | 合同金额分布（饼图+柱状图） |
| components/ScCostAnalysisChart.vue | ~4KB | 成本分析（对比柱状图） |
| components/ScPaymentExecutionChart.vue | ~4KB | 付款执行（双轴折线+柱状） |
| components/ScProjectHealthChart.vue | ~4KB | 项目健康度（仪表盘+散点图） |
| components/ScFinancialDashboard.vue | ~5KB | 资金分析总看板容器 |

### 7. 里程碑

| 周次 | 交付 |
|------|------|
| ADR | 比较 ECharts、自研/其他候选与“不建设”，完成许可证、CVE、包体和回退评审 |
| W2 | 5 个业务图表组件 + Pinia Store |
| W3 | ScFinancialDashboard 总看板 + Contract 2.0 集成 |
| W4 | 后端聚合 API 开发 + 联调 |
| W5 | Bug 修复 + 性能优化 + 主题适配 |
