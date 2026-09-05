# G6 图表引擎执行记录（G6.1 只读实现）

> 状态：进行中（分支 `feature/custom-frontend-integration-g6-chart-v1`）
> 决策依据：[ADR-002](../../../adr/ADR-002-frontend-chart-engine-echarts.md)（Accepted，2026-09-05）
> 本文件是图表专题的**依赖/体积/安全评审记录**（ADR-002「后果」节要求的持续更新载体）。

## 1. 依赖评审记录

| 项 | 记录 |
| --- | --- |
| 新增生产依赖 | `echarts@6.1.0`（精确锁版，无 `^`/`~`），web 生产依赖 4 项 → 5 项 |
| 许可证 | Apache-2.0（内嵌 d3 子组件 BSD-3-Clause，宽松） |
| 传递依赖 | 仅 `tslib` + `zrender` |
| 已知漏洞 | 6.1.0 无已知漏洞（Snyk，ADR-002 事实核查 2026-09-03） |
| 引入方式 | `pnpm -C frontend/apps/web add -E echarts@6.1.0`（pnpm 9.12.3，与 CI corepack 版本一致） |
| 锁文件 | `frontend/pnpm-lock.yaml` 已更新（+3 packages） |

## 2. 引入纪律与守卫

- `scripts/verify/frontend_chart_engine_guard.py`（`make verify.frontend.chart_engine.guard`，
  已挂入 `ci.local.quick`）钉死：
  1. **精确锁版**：web dependencies 必须为 `6.1.0`；patch 升级须改守卫基线一并过门禁；
  2. **tree-shakeable**：禁止 `from 'echarts'` 全量引入，仅允许
     `echarts/core|charts|components|renderers|features|types` 子路径；
  3. **单一 CanvasRenderer**：`echarts/renderers` 只允许 `CanvasRenderer`，禁 SVGRenderer。
- 负例已验证：全量引入与 SVGRenderer 探针均 exit 1。

## 3. 后端 capability 契约（G6.1 Task #96，已完成）

- 契约：`contracts/domain/chart.yaml` v1（registry 已登记，结构指纹已刷新 domains=10）
- 注册表：`addons/smart_construction_core/services/visualization_chart_registry.py`
  （纯 Python，fail-fast 登记纪律：key/metric/dimensions/source_authority/builder 缺一不可）
- Fetch intent：`project.dashboard.chart.fetch`
  （降级链 MISSING_PARAMS / CHART_NOT_REGISTERED / PROJECT_NOT_FOUND / CHART_DATASET_ERROR，
  全部结构化不抛异常，前端渲染通用空态不白屏）
- 单测：`addons/smart_construction_core/tests/test_visualization_chart_capability.py`
  16 例桩加载（经 `verify.visualization.chart.capability` 挂入 ci.local.quick）

## 4. 前端 adapter 与只读组件（G6.1 Task #98，已完成）

- design-tokens：`tokens/semantic.{light,dark}.json` 新增 chart 节（涨红跌绿：
  up=红 / down=绿，up_strong/down_strong，neutral/warning，series_1~6），
  经 `build_tokens.py` 输出 CSS 变量 `--sc-semantic-chart-*`（双主题）
- API 封装：`frontend/apps/web/src/api/chartFetch.ts`
  （`fetchChartDataset({chartKey, projectId})` 消费 `project.dashboard.chart.fetch`，
  类型对齐 chart.yaml v1 series 形状：name + metric + dimensions + points）
- presentation Model：`frontend/apps/web/src/app/presentation/chartDataset.ts`
  （四态状态机 ready / empty / error / degraded_shape；纯函数无运行时依赖，
  CHART_NOT_REGISTERED 等结构化错误透传不白屏）
- 渲染 adapter：`frontend/apps/web/src/components/chart/chartAdapter.ts`
  （纯数据 option 构建，无 echarts/DOM 依赖；单系列 bar 逐柱环比涨红跌绿着色，
  line/pie 按 series_1~6 色序；palette 经注入读取函数解析 CSS 变量，
  缺失时走与 semantic.light 一致的 fallback，等价 `var(--x, fallback)` 语义）
- 只读组件：`frontend/apps/web/src/components/chart/ChartDatasetPanel.vue`
  （echarts 动态按需 import：core + charts/components/renderers 子路径，
  use BarChart/LineChart/PieChart + Grid/Tooltip/Legend + CanvasRenderer，
  不进首屏 bundle；ResizeObserver 自适应；引擎加载失败结构化降级不白屏）
- 单测：`frontend/apps/web/scripts/chart_dataset_model_test.ts`
  （Model 四态 + palette 解析 + option 构建含涨红跌绿着色断言；
  经 `verify.frontend.chart_dataset.unit` 挂入 ci.local.quick /
  verify.frontend.pr.unit / verify.frontend.release.unit，并复跑
  frontend_chart_engine_guard 钉死引入纪律）
- 类型检查：`verify.frontend.typecheck.strict`（vue-tsc）全绿

## 5. 体积预算实测（G6.1 Task #99 填写）

| 测量项 | 预算 | 实测（冻结基线 + 候选版本构建） | 状态 |
| --- | --- | --- | --- |
| 图表子集 gzip | ≤120KB | 待测（renderer 懒加载实现后） | 待办 |
| 主 chunk 体积 | 不变 | 待测 | 待办 |

> 原型估算 ~95KB gzip 仅作 ADR 输入，不作为验收依据（ADR-002 条件 2）。

## 6. 待办

- [x] Task #97 收口：守卫与依赖记录入库（本文件）
- [x] Task #98：图表 adapter（涨红跌绿 token 化）+ 四态只读组件
- [ ] Task #99：懒加载接线 + gzip 预算实测（填 §5）
- [ ] Task #100：驾驶舱图表块挂接 + 首个真实 chart 登记 + 降级路径 E2E 验证
- [ ] Task #101：门禁 + PR + squash 合流收口
