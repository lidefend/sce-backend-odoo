# P1-3: 甘特图组件 — 技术方案

> 架构校正：时间轴 renderer 属于 P0，施工任务、日历、依赖与写动作属于 P1。本文为候选设计，实施以根目录 [`README.md`](../../README.md) 为准。

## 0. 执行状态

`ADR-PENDING`：本专题不得按自研 SVG 或任何第三方库直接实施。任务数据、日历、依赖与关键路径由后端权威定义；前端只在 ADR 批准后实现 renderer。

## 1. 候选方案（原“选型决策”已废止）

### 评估对比

| 方案 | 优点 | 缺点 | 决策 |
|------|------|------|------|
| 自研 | 零依赖、完全可控 | 开发量大（3-4周）、功能有限 | ❌ |
| frappe-gantt | 轻量（30KB）、Vue 友好 | 依赖多、功能简单、无缩放 | ❌ |
| dhtmlx-gantt | 功能强大、专业 | 商业授权、体积大（500KB+） | ❌ |
| vue-ganttastic | Vue 3 原生、封装 dhtmlx | 仍有商业授权问题 | ❌ |
| 自研（SVG + 交互层） | 可控、可按需裁剪 | 无障碍、虚拟化、交互和长期维护成本高 | 待 ADR |

> **SUPERSEDED / 禁止实施：**“最终决策：自研 SVG 甘特图”及其零依赖、500 任务性能和固定 `view_type` 结论均无有效 ADR 或基准证据。正式 ADR 必须比较自研与候选库的许可证、供应链、包体、无障碍、500 任务数值预算、维护成本与回退方案。

## 2. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + TypeScript)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 ScGanttChart.vue                      │   │
│  │  ┌────────────┐  ┌────────────────────────────────┐  │   │
│  │  │ 任务列表    │  │  时间轴 + 任务条 + 依赖线      │  │   │
│  │  │ (左侧表格)  │  │  (SVG 画布)                    │  │   │
│  │  └────────────┘  └────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ganttApi.ts (Intent API) + ganttEngine.ts (SVG引擎) │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                   后端 (Odoo)                                │
│  project.task 模型 → api.data intent 返回                   │
│  字段: name, date_start, date_end, parent_id,                │
│        progress, state, user_id, depends_on                  │
└─────────────────────────────────────────────────────────────┘
```

## 3. 组件设计

### ScGanttChart — 核心甘特图组件

**布局**：
- 左侧：任务列表表格（名称、负责人、进度、状态）
- 右侧：SVG 时间轴 + 任务条 + 依赖连线
- 顶部：时间刻度（日/周/月切换）
- 底部：状态栏（任务数、进度统计）

**交互**：
- 拖拽任务条 → 调整开始/结束日期
- 拖拽任务条左右边缘 → 调整持续时间
- 右键任务条 → 菜单（编辑/删除/添加子任务/添加依赖）
- 鼠标悬停 → Tooltip（任务详情）
- 双击 → 打开任务详情弹窗
- 滚轮 → 水平滚动时间轴
- Ctrl+滚轮 → 缩放（日/周/月视图切换）

**Props**：
```typescript
interface ScGanttChartProps {
  model: string          // project.task
  projectId: number      // 项目 ID
  domain?: unknown[]     // 额外筛选
  readonly?: boolean     // 只读模式
  zoomLevel?: 'day' | 'week' | 'month'  // 初始缩放
  showCriticalPath?: boolean           // 显示关键路径
  showProgress?: boolean               // 显示进度条
  showDependencies?: boolean          // 显示依赖线
}
```

## 4. 数据模型

```typescript
interface GanttTask {
  id: number
  name: string
  date_start: string       // ISO date
  date_end: string         // ISO date
  parent_id: number | null
  progress: number          // 0-100
  state: 'draft' | 'open' | 'done' | 'cancelled' | 'pending'
  user_id: { id: number; name: string } | null
  depends_on: number[]      // 前置依赖任务 ID
  is_milestone?: boolean    // 里程碑
  color?: string            // 自定义颜色
  duration_days?: number    // 计算字段
}

interface GanttConfig {
  zoomLevel: 'day' | 'week' | 'month'
  showCriticalPath: boolean
  showProgress: boolean
  showDependencies: boolean
  rowHeight: number
  barHeight: number
  todayLine: boolean
  weekendShading: boolean
}
```

## 5. SVG 渲染引擎

### 5.1 时间轴

```typescript
function renderTimeline(svg, startDate, endDate, zoomLevel) {
  // 根据缩放级别计算刻度
  // day: 每天一格
  // week: 每周一格
  // month: 每月一格
  // 绘制刻度线 + 日期标签
}
```

### 5.2 任务条

```typescript
function renderTaskBar(task, config, rowY, dateToX) {
  const x = dateToX(task.date_start)
  const width = dateToX(task.date_end) - x
  const height = config.barHeight

  // 主条
  <rect x={x} y={rowY} width={width} height={height} rx={3}
        fill={task.color || stateColors[task.state]} />

  // 进度填充
  <rect x={x} y={rowY} width={width * task.progress / 100} height={height}
        fill={progressColor} opacity={0.3} />

  // 里程碑（菱形）
  if (task.is_milestone) {
    <polygon points={...} fill="#fa8c16" />
  }

  // 任务名标签
  <text x={x + 4} y={rowY + height / 2}>{task.name}</text>
}
```

### 5.3 依赖线

```typescript
function renderDependency(fromTask, toTask, dateToX, rowYs) {
  // 从 fromTask 的右端 → toTask 的左端
  // 绘制 L 形或 S 形连线
  // 箭头指向 toTask
}
```

## 6. 后端数据接口

### Intent API

```json
{
  "intent": "api.data",
  "params": {
    "model": "project.task",
    "op": "list",
    "domain": [["project_id", "=", 42]],
    "order": "date_start",
    "contract_mode": "default"
  }
}
```

### 更新任务

```json
{
  "intent": "api.data",
  "params": {
    "model": "project.task",
    "op": "write",
    "id": 123,
    "values": {
      "date_start": "2024-04-15",
      "date_end": "2024-05-20"
    },
    "contract_mode": "default"
  }
}
```

## 7. 统一页面契约集成

甘特图作为受版本控制的 `planning.gantt` capability 注入统一页面 envelope，不创建新的顶层页面类型：

```json
{
  "capability": "planning.gantt",
  "schema_version": "1.0",
  "payload_ref": "authorized-task-projection-ref",
  "calendar_ref": "authoritative-calendar-ref",
  "readonly": true,
  "allowed_actions": [],
  "presentation": {"default_zoom": "week"}
}
```

日历、工期、依赖合法性、关键路径和写权限均由后端权威计算。首批只读；后续写动作必须携带原版本并支持冲突回滚。

## 8. 里程碑

| 周次 | 交付物 |
|------|--------|
| W1 | 类型定义 + API 封装 + SVG 引擎核心 |
| W2 | ScGanttChart 组件 + 时间轴 + 任务条 + 依赖线 |
| W3 | 交互层（拖拽/缩放/右键/Tooltip）+ Contract 集成 |

## 9. 依赖

- 无新增前端依赖
- 后端：project.task 模型已有 date_start/date_end/parent_id 字段
