# P2-2 移动端响应式适配 — 技术方案

> 架构校正：通用响应式渲染属于 P0，不另建移动业务真相源，也不以引入 Tailwind 为前提。本文为候选设计，实施以根目录 [`README.md`](../../README.md) 为准。

## 1. 目标

收口现有 SCE Web 的同一套 renderer，使其在总控计划定义的五视口保持一致业务语义。本专题不是新建移动端工程，也不重新建设已经存在的列表、表单、导航或主题能力。

## 2. 设计原则

1. **单一 renderer** — 桌面、平板和移动共享 runtime、assembler、组件与业务状态，不叠加第二套移动页面
2. **职责受限** — 后端仅提供 `presentation_hints`（字段优先级、折叠许可和语义），断点与容器布局由前端决定
3. **现状收口** — 以冻结 SHA 的现有实现为基线，只处理证据化差距，不从零建设
4. **触摸优先** — 所有交互区最小 44×44pt（iOS HIG），手势替代部分桌面操作
5. **性能优先** — 移动端首屏 <2s，按需加载移动端组件

## 3. 架构概览

> **SUPERSEDED：**下图中的 `Contract 2.0 surface_mapping` 与后端断点映射已废止。正式实现使用统一页面 envelope 的受限 `presentation_hints`；后端不下发 xs/md/lg 布局，前端现有 responsive/container runtime 负责断点与表格/卡片/表单形态。

```
┌─────────────────────────────────────────────────────┐
│                    Contract 2.0                      │
│  surface_mapping: {                                  │
│    xs: { nav: 'tabbar', list: 'card', form: 'step' },│
│    md: { nav: 'drawer', list: 'card', form: 'group' },│
│    lg: { nav: 'sidebar', list: 'table', form: 'full' }│
│  }                                                   │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│              responsive.ts (断点检测)                 │
│  isMobile() / isTablet() / useResponsive()           │
└──────┬───────────┬───────────┬──────────────────────┘
       │           │           │
┌──────▼──┐  ┌────▼───┐  ┌───▼────────┐
│Nav 组件  │  │List 组件│  │Form 组件    │
│(3 模式)  │  │(卡片式) │  │(分组+底部弹窗)│
└─────────┘  └────────┘  └────────────┘
       │           │           │
┌──────▼───────────▼───────────▼──────────────────────┐
│              gestures.ts (手势层)                     │
│  onSwipe / onLongPress / onDoubleTap / onPullToRefresh│
└─────────────────────────────────────────────────────┘
```

## 4. 组件设计

### 4.1 ScMobileNav — 响应式导航

| 模式 | 触发断点 | 交互 |
|------|---------|------|
| tabbar | <768px (手机) | 底部 5 个 Tab，点击切换 |
| drawer | 768-1024px (平板) | 左上汉堡按钮，左滑抽屉 |
| sidebar | ≥1024px (桌面) | 固定左侧边栏 |

**Contract 集成**：
```json
{
  "surface_mapping": {
    "nav_mode": "auto"
  }
}
```
前端读取 `nav_mode: "auto"` 时调用 `getRecommendedNavMode()` 自动匹配。

### 4.2 ScMobileList — 响应式列表

**桌面端**：标准表格视图（通过 `#desktop` 插槽提供）
**移动端**：卡片列表 + 下拉刷新 + 搜索 + 筛选标签

```typescript
interface MobileField {
  key: string
  label: string
  type?: 'text' | 'amount' | 'date' | 'percent' | 'badge'
}
```

**关键交互**：
- 下拉刷新：`onPullToRefresh` 手势，阻尼系数 0.5，阈值 80px
- 卡片点击进入详情
- 筛选标签横向滚动（`-webkit-overflow-scrolling: touch`）
- 搜索栏固定在顶部，实时过滤

### 4.3 ScMobileForm — 响应式表单

**桌面端**：完整表单（通过 `#desktop` 插槽提供）
**移动端**：分组卡片式表单 + 底部弹出选择器

**字段类型映射**：
| Contract field_type | 移动端渲染 |
|---------------------|-----------|
| char / text | `<input>` 文本 |
| integer / float | `<input type="number">` |
| monetary | 金额输入（¥ 前缀） |
| date / datetime | `<input type="date">` |
| selection | 底部弹出选择器 |
| boolean | 开关组件 |

**Contract 集成**：
```json
{
  "fields": [
    { "key": "name", "label": "名称", "type": "char", "required": true, "group": "基本" },
    { "key": "amount", "label": "金额", "type": "monetary", "group": "财务" }
  ],
  "field_groups": [
    { "title": "基本信息", "keys": ["name", "partner_id"] },
    { "title": "财务信息", "keys": ["amount", "currency_id"] }
  ]
}
```

### 4.4 gestures.ts — 手势工具

| 手势 | 用途 | 实现 |
|------|------|------|
| onSwipe | 列表项滑动操作、页面切换 | touchstart/end + 方向判断 |
| onLongPress | 列表项长按弹出菜单 | touchstart + setTimeout(500ms) |
| onDoubleTap | 快速编辑 | 两次 touchend 间隔 <300ms |
| onPullToRefresh | 列表下拉刷新 | touchmove + translateY 阻尼 |

## 5. 响应式断点策略

| 断点 | 宽度 | 设备 | 布局策略 |
|------|------|------|---------|
| xs | <640px | 手机竖屏 | 单列，底部Tab，卡片列表 |
| sm | 640-768px | 手机横屏 | 单列，底部Tab |
| md | 768-1024px | 平板 | 双列，抽屉导航 |
| lg | 1024-1280px | 小桌面 | 多列，侧边栏 |
| xl | ≥1280px | 桌面 | 完整布局 |

## 6. 样式体系

> **SUPERSEDED / 禁止实施：**原“项目已使用 TailwindCSS”结论与主仓库现状不符，示例响应式类不得复制。

继续使用现有 `@sc/design-tokens`、`@sc/ui` 与应用 CSS。只有独立 ADR 证明收益、迁移成本、包体和维护边界后，才可评估新增样式依赖；Mobile 专题本身无权引入。

## 7. 视口配置

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
```

- `user-scalable=no`：禁用双指缩放，防止误触
- `viewport-fit=cover`：支持 iPhone 刘海屏安全区域
- CSS 使用 `env(safe-area-inset-*)` 处理安全区域

## 8. 性能优化

| 优化项 | 策略 |
|--------|------|
| 组件懒加载 | 移动端组件 `defineAsyncComponent` 按需加载 |
| 图片优化 | `<img>` 使用 `loading="lazy"`，移动端加载缩略图 |
| 列表虚拟化 | >100 条数据启用虚拟滚动 |
| 触摸节流 | `touchmove` 使用 `requestAnimationFrame` 节流 |
| CSS containment | 卡片使用 `contain: layout style paint` |

## 9. 关键页面走查

### 9.1 看板（Dashboard）
- 桌面：4 列指标卡片 + 图表网格
- 平板：2 列指标卡片 + 图表堆叠
- 手机：1 列指标卡片 + 图表纵向滚动

### 9.2 合同列表
- 桌面：表格（合同编号/对方/金额/已收/已付/状态/日期）
- 手机：卡片（合同名称+状态标签 + 金额+对方 + 日期+操作）

### 9.3 BOQ 树视图
- 桌面：完整树形表格
- 平板：树形表格（隐藏部分列）
- 手机：手风琴式折叠树，点击展开子节点

### 9.4 甘特图
- 桌面：左侧任务列表 + 右侧甘特条
- 手机：仅列表视图 + 点击查看时间线详情

### 9.5 表单编辑
- 桌面：单页完整表单
- 手机：分组卡片 + 底部固定操作栏 + 底部弹出选择器

## 10. 统一页面契约扩展

```json
{
  "presentation_hints": {
    "field_priority": ["identity", "status", "amount", "date"],
    "collapsible_groups": ["secondary", "audit"],
    "semantic_emphasis": ["primary_action", "validation_error"]
  }
}
```

前端使用容器宽度和现有响应式规则决定表格、卡片、分组和导航形态；后端不声明断点或设备专用页面。

## 11. 文件清单

| 文件 | 说明 |
|------|------|
| `src/utils/responsive.ts` | 断点检测、设备判断、useResponsive Hook |
| `src/utils/gestures.ts` | 滑动/长按/双击/下拉刷新手势 |
| `src/components/ScMobileNav.vue` | 三模式导航（tabbar/drawer/sidebar） |
| `src/components/ScMobileList.vue` | 卡片列表 + 下拉刷新 + 搜索 + 筛选 |
| `src/components/ScMobileForm.vue` | 分组表单 + 底部弹出选择器 |
| `demo/mobile-demo.html` | 可视化演示页面 |

## 12. 前后端边界

1. 桌面、平板和手机消费同一页面 envelope、权限、动作和业务数据 API；不得按设备建立第二套契约或业务事实接口。
2. 后端只可通过正式 `ui.presentation_hints` 声明字段优先级、可折叠性和语义强调，不声明断点、设备类型或导航形态。
3. 前端依据容器宽度、统一断点和现有设计令牌选择表格、卡片或摘要布局；缺少 hints 时使用安全默认布局。
4. 图片响应式使用标准 `srcset`/尺寸策略或受控资产变体，不把设备身份作为权限或业务数据裁剪依据。
