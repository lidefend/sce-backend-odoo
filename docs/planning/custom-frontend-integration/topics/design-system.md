# SC Design System — 完整设计系统规范

> 本文为候选规范，不建立第二套设计系统。实施必须合并到现有 `@sc/design-tokens` 与 `@sc/ui`，并以根目录 [`README.md`](../../README.md) 为准。

> 供应链管理平台统一设计系统 v1.0
> 
> 覆盖设计令牌、基础组件库、页面级布局模板、Contract 2.0 集成规范

> 执行状态：现有 `@sc/design-tokens` 与 `@sc/ui` 是唯一真相源。本文中的 token 值、组件结构和库选型均为待审计候选，禁止建立第二套实现。

---

## 一、设计原则

### 1.1 核心理念

| 原则 | 说明 |
|------|------|
| **4px 网格** | 所有间距、尺寸均为 4 的倍数，确保视觉节奏统一 |
| **语义优先** | Token 使用语义名（primary、success）而非具体值（#1890ff），主题切换只需改变量值 |
| **层级递进** | 颜色 12 级灰度、阴影 5 级高度、z-index 分层明确 |
| **主题驱动** | 全部通过 CSS 变量输出，支持亮/暗/白标三模式无缝切换 |
| **领域中立** | 通用组件不硬编码金融颜色、币种、工程编码或业务字体 |
| **依赖受控** | 自研或三方方案均须经 ADR；甘特图 SVG、`contenteditable` 和“全部自研”不是既定结论 |

### 1.2 命名规范

- **组件前缀**：所有组件统一 `Sc` 前缀（Supply Chain）
- **CSS 变量**：`--color-*`、`--font-*`、`--spacing-*`、`--shadow-*`、`--radius-*`
- **Token 分层**：`tokens/design-tokens.ts` → `themeEngine.ts` → `ScThemeProvider.vue` → CSS 变量
- **文件结构**：`src/components/` 基础组件、`src/layouts/` 页面模板、`src/tokens/` 令牌

---

## 二、设计令牌体系（Design Tokens）

> 本章表格中的名称和值是历史原型样例，已 `SUPERSEDED`，不得批量导入。实施时先输出“原型 token → `@sc/design-tokens` canonical semantic token”的逐项映射；无法映射的项需单独评审或删除。

### 2.1 颜色体系

#### 品牌主色

| Token | 值 | 用途 |
|-------|------|------|
| `--color-primary` | `#1890ff` | 主操作色 |
| `--color-primary-hover` | `#40a9ff` | 悬停 |
| `--color-primary-active` | `#096dd9` | 点击 |
| `--color-primary-light` | `#e6f7ff` | 浅色背景/选中 |
| `--color-primary-dark` | `#0050b3` | 深色强调 |

#### 功能色

| Token | 值 | 用途 |
|-------|------|------|
| `--color-success` | `#52c41a` | 成功/完成 |
| `--color-warning` | `#faad14` | 警告/待处理 |
| `--color-error` | `#ff4d4f` | 错误/危险 |
| `--color-info` | `#1890ff` | 信息提示 |

#### 金融语义色（涨红跌绿）

| Token | 值 | 用途 |
|-------|------|------|
| `--color-up` | `#f5222d` | 上涨/正向金额 |
| `--color-down` | `#52c41a` | 下跌/负向金额 |
| `--color-flat` | `#8c8c8c` | 持平 |

#### 中性色（12 级灰度）

| Token | 值 | 用途 |
|-------|------|------|
| `--color-bg-base` | `gray-1 #fff` | 基础背景 |
| `--color-bg-subtle` | `gray-2 #fafafa` | 次要背景 |
| `--color-bg-elevated` | `gray-1 #fff` | 卡片/弹窗 |
| `--color-text-primary` | `gray-10 #262626` | 主要文字 |
| `--color-text-secondary` | `gray-7 #8c8c8c` | 次要文字 |
| `--color-text-tertiary` | `gray-6 #bfbfbf` | 辅助文字 |
| `--color-border` | `gray-5 #d9d9d9` | 边框 |
| `--color-divider` | `gray-4 #f0f0f0` | 分割线 |

#### 数据可视化色板

8 色序列：`#1890ff #52c41a #faad14 #f5222d #722ed1 #13c2c2 #eb2f96 #fa8c16`

#### 状态色

| 状态 | 色 | 用途 |
|------|------|------|
| draft | `#bfbfbf` | 草稿 |
| open | `#1890ff` | 进行中 |
| pending | `#faad14` | 待处理 |
| done | `#52c41a` | 完成 |
| cancelled | `#f5222d` | 已取消 |
| overdue | `#ff4d4f` | 已逾期 |

### 2.2 排版体系

| 层级 | 字号 | 字重 | 行高 | 用途 |
|------|------|------|------|------|
| Display | 48px | bold 700 | 1.2 | 数据大屏 |
| H1 | 30px | bold 700 | 1.2 | 页面标题 |
| H2 | 24px | semibold 600 | 1.2 | 区块标题 |
| H3 | 20px | semibold 600 | 1.4 | 卡片标题 |
| H4 | 18px | medium 500 | 1.4 | 小标题 |
| Body | 14px | normal 400 | 1.5 | 正文基准 |
| Caption | 13px | normal 400 | 1.4 | 次要文字 |
| Label | 12px | normal 400 | 1.4 | 标签/辅助 |

字体族：
- 正文：`"PingFang SC","Microsoft YaHei",sans-serif`
- 数字：`"DIN Alternate","Roboto",sans-serif`
- 等宽：`"SF Mono","Consolas",monospace`

### 2.3 间距体系

4px 网格，间距 token：`4/8/12/16/20/24/32/40/48/64/80/96`

### 2.4 圆角

| Token | 值 | 用途 |
|-------|------|------|
| `--radius-sm` | 4px | 输入框、按钮 |
| `--radius-md` | 6px | 卡片 |
| `--radius-lg` | 8px | 弹窗 |
| `--radius-xl` | 12px | 大容器 |
| `full` | 9999px | 胶囊/圆形 |

### 2.5 阴影

5 级高度：xs → sm → md → lg → xl → 2xl

### 2.6 Z-Index

| 层 | 值 | 用途 |
|----|------|------|
| base | 0 | 默认 |
| dropdown | 1000 | 下拉 |
| sticky | 1020 | 吸顶 |
| drawer | 1040 | 抽屉 |
| modal | 1060 | 弹窗 |
| popover | 1080 | 气泡 |
| tooltip | 1100 | 提示 |
| loading | 1200 | 全局加载 |

---

## 三、基础组件库

### 3.1 组件清单

| 组件 | 文件 | 用途 |
|------|------|------|
| ScButton | ScButton.vue | 按钮（7 种类型 × 5 种尺寸 × ghost/block/round/loading） |
| ScInput | ScInput.vue | 输入框（text/number/password + prefix/suffix/clearable） |
| ScSelect | ScSelect.vue | 选择器（单选/多选/搜索/远程） |
| ScTable | ScTable.vue | 表格（排序/选择/条纹/边框/插槽渲染） |
| ScCard | ScCard.vue | 卡片（4 种变体：default/elevated/outlined/filled） |
| ScModal | ScModal.vue | 弹窗（5 种位置：center/right/top/bottom/left + 5 种尺寸） |
| ScTag | ScTag.vue | 标签（9 种类型 + closable/dot/round） |
| ScPagination | ScPagination.vue | 分页（总数/页大小/跳转/省略） |
| ScEmpty | ScEmpty.vue | 空状态（4 种类型：default/search/error/network） |
| ScLoading | ScLoading.vue | 加载（3 种尺寸 + overlay/fullscreen） |
| ScStatCard | ScStatCard.vue | 统计卡片（数值/前缀/后缀/趋势/图标） |
| ScToolbar | ScToolbar.vue | 工具栏（搜索 + 操作插槽） |
| ScFilterBar | ScFilterBar.vue | 筛选栏（input/select/date + 重置） |
| ScBreadcrumb | ScBreadcrumb.vue | 面包屑导航 |
| ScTabs | ScTabs.vue | 标签页（3 种变体：line/card/pill + badge） |

### 3.2 组件 Props 速查

#### ScButton

```
type: primary | secondary | success | warning | error | info | text | link
size: xs | sm | md | lg | xl
block: boolean       // 撑满宽度
round: boolean       // 胶囊形
ghost: boolean       // 透明背景
loading: boolean
disabled: boolean
icon: string         // SVG 字符串
href: string         // 渲染为 <a>
@click: MouseEvent
```

#### ScTable

```
columns: ScTableColumn[]
data: T[]
rowKey: string
selection: boolean
selectionMode: single | multiple
selectedKeys: (string|number)[]
sortKey / sortOrder: string | 'asc'|'desc'
bordered / stripe: boolean
size: sm | md
slots: cell-{key}   // 自定义单元格渲染
@sort / @rowClick / @update:selectedKeys
```

#### ScModal

```
modelValue: boolean
title: string
placement: center | right | top | bottom | left
size: sm | md | lg | xl | full
closable / maskClosable: boolean
width: string
bodyStyle: CSSProperties
@update:modelValue / @close
```

---

## 四、页面级布局模板

### 4.1 ScPageLayout — 页面壳

```
Props:
  title: string           // 品牌名
  logo: string            // Logo URL
  sidebar: boolean        // 是否显示侧栏
  menu: MenuGroup[]       // 菜单数据
  activeMenu: string
  theme: 'light'|'dark'
  themeSwitchable: boolean

Slots:
  header-center / header-right
  default                // 页面内容

Events:
  menuClick(item)
  themeChange(theme)
```

### 4.2 ScListPage — 列表页

```
Props:
  title, breadcrumb, searchable, searchPlaceholder
  filters: FilterConfig[]
  columns: ScTableColumn[]
  data, rowKey, selection
  total, current, pageSize, showPagination

Slots:
  actions              // 标题栏操作按钮
  filters              // 自定义筛选区
  toolbar-actions      // 工具栏右侧
  default              // 替换默认表格
  cell-{key}           // 自定义单元格

Events:
  search, sort, pageChange, rowClick, update:filterValues
```

### 4.3 ScFormPage — 表单页

```
Props:
  title, description, breadcrumb
  showFooter, submitText, submitting

Slots:
  actions              // 标题栏操作
  default              // 表单内容
  footer               // 自定义底栏

Events:
  submit, cancel
```

### 4.4 ScDashboardPage — 看板页

```
Props:
  title, breadcrumb
  stats: StatItem[]     // KPI 卡片数据
  projectOptions, activeProject
  periods, activePeriod
  gridCols, gridRowHeight

Slots:
  controls              // 自定义控件区
  kpi                   // 自定义 KPI 区
  default               // 图表网格
  detail                // 底部详情

Events:
  projectChange, periodChange
```

---

## 五、统一页面契约集成规范

### 5.1 设计系统与 Contract 的关系

统一页面 envelope 是后端驱动的 UI 契约，设计系统是前端渲染的基石。二者关系：

```
统一页面 envelope → capability payload/ref → assembler → 现有设计令牌与基础组件 → 渲染
```

### 5.2 契约边界

- 页面 envelope 只声明页面身份、权限、动作、版本与通用状态。
- 主题通过受版本控制的 `ui.theme` capability 提供模式、受控品牌资产引用和经过 allowlist 校验的语义 token 覆盖。
- 组件只消费现有 `@sc/design-tokens` 的 canonical semantic token；本文早期章节中的固定 token 名和值仅作为盘点输入，不是可创建的第二套实现。
- 页面模板只接收 assembler 输出，不直接解释后端字段，也不请求业务 API。
- 未知 capability 或不支持的版本显示可解释安全空态，不按字段名、模型名或路由猜测。

### 5.3 主题切换流程

1. runtime 校验 `ui.theme` 的版本、来源和覆盖白名单。
2. assembler 将有效配置映射到现有 canonical semantic token。
3. Theme Provider 应用已验证的模式和 token 映射。
4. 组件通过现有设计令牌适配；无效覆盖被拒绝并记录 drift。
5. localStorage 仅持久化个人亮/暗/自动显示偏好，不保存租户品牌真相。

---

## 六、已有模块集成

### 6.1 模块 → 设计系统映射

| 模块 | 使用的基础组件 | 页面模板 |
|------|--------------|---------|
| BOQ 工程量清单 | ScTable, ScCard, ScToolbar, ScTag, ScModal | ScListPage |
| ECharts 图表 | ScCard, ScStatCard, ScTabs | ScDashboardPage |
| Excel 导入导出 | ScButton, ScModal, ScTable | 嵌入 ScListPage |
| PDF 生成 | ScButton, ScModal | 嵌入工具栏 |
| 甘特图 | ScCard, ScButton, ScTag, ScToolbar | 独立全屏页 |
| 富文本编辑器 | ScButton, ScModal, ScTag | 嵌入 ScFormPage |
| 移动端 | ScMobileNav, ScMobileList, ScMobileForm | 响应式布局 |
| 主题/白标 | ScThemeProvider, ScThemeSwitcher | ScPageLayout |

### 6.2 统一交互规范

- **搜索**：防抖 300ms，回车触发，清空即重置
- **分页**：默认 10 条/页，可选 10/20/50/100
- **排序**：点击表头切换 asc→desc→无，单字段排序
- **筛选**：change 即触发，重置按钮一键清空
- **加载**：overlay 覆盖内容区，spinner + 文字
- **空状态**：根据场景选择 default/search/error 类型
- **弹窗**：居中弹窗用 center，侧滑用 right，移动端用 bottom

---

## 七、文件结构

```
design-system/
├── docs/
│   └── DESIGN_SYSTEM.md              # 本文件
├── src/
│   ├── tokens/
│   │   └── design-tokens.ts          # 完整令牌定义
│   ├── components/                    # 15 个基础组件
│   │   ├── ScButton.vue
│   │   ├── ScInput.vue
│   │   ├── ScSelect.vue
│   │   ├── ScTable.vue
│   │   ├── ScCard.vue
│   │   ├── ScModal.vue
│   │   ├── ScTag.vue
│   │   ├── ScPagination.vue
│   │   ├── ScStatCard.vue
│   │   ├── ScEmpty.vue
│   │   ├── ScLoading.vue
│   │   ├── ScToolbar.vue
│   │   ├── ScFilterBar.vue
│   │   ├── ScBreadcrumb.vue
│   │   └── ScTabs.vue
│   └── layouts/                      # 4 个页面模板
│       ├── ScPageLayout.vue
│       ├── ScListPage.vue
│       ├── ScFormPage.vue
│       └── ScDashboardPage.vue
└── demo/
    └── design-system-showcase.html   # 综合展示页面
```

---

## 八、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-08-05 | 初始版本：15 个基础组件 + 4 个页面模板 + 完整令牌体系 |
