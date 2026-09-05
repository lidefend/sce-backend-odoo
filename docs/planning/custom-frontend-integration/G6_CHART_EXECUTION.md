# G6 图表引擎执行记录（G6.1 只读实现 + G6.2 图表扩展）

> 状态：G6.1 已合流（PR #436，main=7701070f）；G6.2 进行中（分支 `feature/custom-frontend-integration-g6-chart-v2`）
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

## 5. 体积预算实测（G6.1 Task #99，2026-09-05 实测，按修订后口径 PASS）

测量方法：真实 vite/rollup 生产构建（`--mode production`，与发布产物同一
工具链），app 主入口 + 探针入口（与 `ChartDatasetPanel.loadEngine()` 完全
同款的动态按需 import：core + Bar/Line/Pie + Grid/Tooltip/Legend +
CanvasRenderer）双入口构建；对纯 app 构建做 chunk 集合差分，差分 chunk
即 echarts 子集懒加载 chunk。gzip 按 level 9 计（比 vite 报告口径更保守）。

| 测量项 | 预算（ADR-002 条件 2，2026-09-05 修订口径） | 实测 | 状态 |
| --- | --- | --- | --- |
| 首屏：主 chunk 不含 echarts | 主 chunk 体积维持基线不变 | 主 index chunk gzip 192.9KB→192.6KB，差分内无 echarts 代码；echarts 仅存在于动态 import 产生的 10 个独立懒加载 chunk | **PASS**（条件 3 懒加载成立） |
| 懒加载图表子集 gzip | ≤400KB（修订前 ≤120KB，实测回审后修订，见 ADR-002 修订记录） | **364.6KB**（raw 1081.5KB；chunk 构成：charts 84.1 / Axis 83.4 / components 81.4 / graphic 49.8 / keyframeAnim 48.6 / renderers 12.9 / core 2.2 / 其余 ~2） | **PASS**（原口径 FAIL，超 3 倍，触发回审） |

### 根因分析（原口径 FAIL 的原因）

1. **echarts 6.1.0 package.json 声明 `sideEffects: ['lib/chart/*.js', 'lib/component/*.js', ...]`**：
   `echarts/charts`、`echarts/components` 桶文件 `export *` 自这些副作用模块，
   bundler（rollup/esbuild 均验证）不能因「导出未使用」删除它们；
2. 已实测排除引入姿势因素：命名导入 / 解构导入 / 深路径副作用引入
   （`import 'echarts/lib/chart/bar.js'`）三种写法产物体积相同
   （esbuild 合并口径均 548.3KB raw / ~186.6KB gzip）；
3. 大头是共享内部模块（Axis 坐标轴 / graphic 图形 / keyframe 动画），
   即便裁剪图表种类（bar-only）与组件（去 Tooltip/Legend）实测仍
   138.9KB gzip（esbuild 口径，超原预算），**120KB 预算在 echarts 6.1.0
   按需子集上不可达**；
4. ADR 输入阶段的原型估算 ~95KB gzip 严重失真（未计入 Axis/graphic/
   动画等共享模块与 sideEffects 约束）。

### 影响面与缓解事实

- 全部体积**位于懒加载 chunk**：用户未打开图表块则永不下载（条件 3
  首屏不受影响已实证）；内容寻址文件名强缓存后仅首次产生流量。

### 决策记录（2026-09-05，用户批准方案 A）

原口径 FAIL 触发 ADR-002 条件 2 回审，三方案（A 修订预算口径 /
B 裁剪子集 / C 重开引擎选型）呈报后用户批准**方案 A**：预算拆分为
「首屏预算不变 + 懒加载图表子集 ≤400KB gzip」两口径，实测 364.6KB
满足。修订全文与依据见 `docs/adr/ADR-002-frontend-chart-engine-echarts.md`
修订记录节。

## 6. G6.2 图表扩展（2026-09-05，双新 chart 批次）

复用 G6.1 已收口的图表全链（注册表 / chart.yaml v1 / intent 降级链 /
chart_dataset 通用组件），零新增架构、零前端改动（`normalizeChartType`
已白名单 bar/line/pie）。数据源映射来自 `topics/echarts.md` §2 候选表。

### 登记 chart（visualization_chart_definitions.py）

| chart key | 类型 | 数据源 | series | 聚合口径 |
| --- | --- | --- | --- | --- |
| `project.payment.execution` | line | payment.request + payment.ledger | 申请金额 / 已付金额 | 月桶 ISO `YYYY-MM`（search_read + Python 归桶，**刻意不用 read_group `:month`**：本地化月标签无法字典序排序）；申请侧排除 cancel 按 `date_request`，已付侧仅 posted 按 `paid_at`，缺失侧不造点 |
| `project.contract.distribution` | pie | sc.general.contract | 合同金额 | read_group 按 `contract_direction` 分组求 `amount_total`，排除 cancel；方向缺失（False）不造点；selection 展示名解析（支持 callable selection） |

命名纪律：CHART_KEY_REGEX 钉死**三段键**（`domain.entity.name`），四段键
`project.contract.direction.distribution` 曾被注册表 fail-fast 拒绝，已
改为 `project.contract.distribution`。

### 块挂接（四处接线，G6.1 先例镜像）

- 新 builder：`project_dashboard_builders/project_payment_chart_builder.py`
  （`block.project.chart.payment`，复用 `ProjectChartBuilder._chart_registered`，
  forbidden/empty/ready 四态信封）
- `builders/__init__.py` BUILDERS 元组 → `project_dashboard_service.py`
  ZONE_BLOCKS/RUNTIME_BLOCK_MAP/zones dict →
  `project_dashboard_scene_content.py` zone_blocks（chart 块后、finance 前，
  secondary/stack）

### ACL 降级语义（E2E 实证）

`_safe_*` 辅助函数在模型访问被 ir.model.access 拒绝时返回空映射 →
空 series → 空态渲染（不抛异常不白屏）。E2E 三视角（探针
`tmp/g62_chart_batch_e2e.sh`，`USER_LOGIN` 可切角色）：

| 视角 | chart_payment 块 | payment.execution | contract.distribution |
| --- | --- | --- | --- |
| 成控 sc_cost_mgr | 合法空态 | 合法空态（ACL 无权） | 合法空态（ACL 无权） |
| 财务 sc_finance_mgr | ready | ready：申请金额 4 点（2025-02:5,000,000 / 2025-03:10,060,000 / 2025-04:1,200,000 / 2025-08:360,000），已付 0 点（缺失侧不造点） | 空态（合同模型无权） |
| 合同 sc_contract_mgr | ready | 空态（付款模型无权） | ready：支出合同 600,000 / 收入合同 680,000 |

降级路径：未登记 key → `CHART_NOT_REGISTERED` 结构化返回（前端渲染
通用空态不白屏）。

### 测试与门禁

- `test_visualization_chart_capability.py`：16 → **33 例**（登记 / 月桶
  ISO 排序 / 缺失月不造点 / 状态过滤 domain 断言 / 空态降级 / handler
  端到端 line 投影）
- `test_project_chart_builder.py`：8 → **14 例**（payment 块身份 / empty /
  ready / fetch_params / 文案 / 可见性）
- `make/ci.mk` verify.visualization.chart.capability py_compile 清单追加
  新 builder 文件
- `make ci.local.quick` 全绿（2026-09-05 实测 7m51s，typecheck strict
  PASS，ESLint 0 error）
- 前端零改动：chart_engine_guard / chart_dataset.unit 双 PASS 不变

## 7. 待办

- [x] Task #97 收口：守卫与依赖记录入库（本文件）
- [x] Task #98：图表 adapter（涨红跌绿 token 化）+ 四态只读组件
- [x] Task #99：懒加载接线（组件内动态 import）+ gzip 预算实测
  （原口径 FAIL → ADR-002 条件 2 修订（方案 A）→ 修订口径 PASS）
- [x] Task #100：驾驶舱图表块挂接 + 首个真实 chart 登记 + 降级路径 E2E 验证
  （PR #436 squash 合流，main=7701070f；E2E 五路径全绿）
- [x] Task #101：门禁 + PR + squash 合流收口
- [x] G6.2-A~D：数据源审计 + 后端实现 + 前端零改动确认 + 三视角 E2E
- [x] G6.2-E：PR + squash 合流收口（本 PR 自身即收口载体；门禁已全绿）
