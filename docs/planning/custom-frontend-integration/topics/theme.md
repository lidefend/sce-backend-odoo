# P3 主题/白标系统 — 技术方案

> 架构校正：主题引擎属于 P0，客户品牌默认属于 P2，管理员即时配置属于 P3。本文为候选设计，实施以根目录 [`README.md`](../../README.md) 为准。

> 执行状态：现有主题和设计令牌只做增量收口，不新建 Theme Engine。本文中的固定色板、任意 `customTokens`、Base64/任意 URL 资产、功能开关和租户配置存储方案均为 `SUPERSEDED`。

## 1. 目标

为 sce-product-odoo 前端添加完整的主题系统和多租户白标定制能力，实现：
1. 亮色/暗色/跟随系统三种显示模式
2. 受白名单约束的品牌语义 token（是否提供预设色板待产品确认）
3. 多租户白标配置（品牌名与受控 Logo 资产；功能权限不属于主题）
4. CSS 变量驱动，所有组件引用语义色，零硬编码色值
5. Contract 2.0 集成，后端下发主题配置

## 2. 设计原则

1. **CSS 变量驱动** — 所有色值通过 `--sc-*` CSS 变量引用，运行时切换零重渲染
2. **语义色优先** — 组件使用 `var(--sc-primary)` 而非 `var(--sc-blue)`，换主题不改组件代码
3. **依赖受控** — 本专题不预设零三方或指定三方方案，新增依赖必须走 ADR
4. **Contract 集成** — 主题配置由后端 Contract JSON 下发，前端消费
5. **渐进增强** — 不影响现有组件，组件逐步迁移到 CSS 变量即可受益

## 3. 架构概览

```
┌────────────────────────────────────────────────────────────┐
│                    Contract 2.0                            │
│  {                                                         │
│    "theme": {                                              │
│      "mode": "auto",                                       │
│      "brand": { brandName, brandPrimary, logo, ... },      │
│      "tokenOverrides": { allowlisted semantic tokens }     │
│    }                                                       │
│  }                                                         │
└─────────────────────┬──────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────┐
│              ScThemeProvider.vue                           │
│  (根组件包裹，初始化主题系统)                                  │
└─────────────────────┬──────────────────────────────────────┘
                      │
           ┌──────────┼──────────────┐
           │          │              │
┌──────────▼──┐  ┌───▼────────┐  ┌──▼──────────────┐
│themeEngine  │  │ScTheme     │  │ScWhiteLabel     │
│.ts          │  │Switcher.vue│  │Panel.vue        │
│             │  │(用户切换)    │  │(管理员配置)       │
└──────┬──────┘  └────────────┘  └─────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│          CSS 变量注入 (:root / documentElement)               │
│  canonical semantic variables from @sc/design-tokens         │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│     所有 Sc 组件通过 var(--sc-*) 引用颜色/圆角/阴影/间距         │
│     主题切换时 CSS 变量实时更新，零重渲染                        │
└──────────────────────────────────────────────────────────────┘
```

## 4. Token 体系

> 本章所有固定值和预设色板均为历史原型样例，已 `SUPERSEDED`。实际值只来自现有 `@sc/design-tokens` 或经过来源、类型、对比度和 allowlist 校验的 P2/P3 配置。

### 4.1 颜色 Token

| Token | 语义 | 亮色值 | 暗色值 |
|-------|------|--------|--------|
| `--sc-primary` | 品牌主色 | `#4f7cff` | `#5b85ff` |
| `--sc-success` | 成功/已完成 | `#52c41a` | `#73d13d` |
| `--sc-warning` | 警告/待处理 | `#faad14` | `#ffc53d` |
| `--sc-danger` | 危险/下跌 | `#f5222d` | `#ff4d4f` |
| `--sc-bg` | 页面背景 | `#f0f2f5` | `#0d1117` |
| `--sc-bgCard` | 卡片背景 | `#ffffff` | `#161b22` |
| `--sc-textPrimary` | 主文字 | `#1a1a1a` | `#e6edf3` |
| `--sc-textSecondary` | 次文字 | `#666666` | `#8b949e` |
| `--sc-border` | 默认边框 | `#e8e8e8` | `#30363d` |
| `--sc-chart-color-1~8` | 图表色板 | 8色序列 | 暗色调序列 |

同时为每个颜色生成 RGB 通道变量：
```css
--sc-primary: #4f7cff;
--sc-primary-rgb: 79, 124, 255;
```
用于 `rgba(var(--sc-primary-rgb), 0.2)` 组合透明色。

### 4.2 排版 Token

| Token | 值 |
|-------|-----|
| `--sc-fontFamily` | `-apple-system, BlinkMacSystemFont, ...` |
| `--sc-fontFamilyMono` | `"SF Mono", "Fira Code", ...` |
| `--sc-fontSizeBase` | `14px` |
| `--sc-fontSizeLg` | `16px` |
| `--sc-fontSizeXl` | `18px` |
| `--sc-fontWeightSemiBold` | `600` |
| `--sc-lineHeightBase` | `1.5` |

### 4.3 圆角 Token

| Token | 值 |
|-------|-----|
| `--sc-radius-sm` | `4px` |
| `--sc-radius-md` | `8px` |
| `--sc-radius-lg` | `12px` |
| `--sc-radius-xl` | `16px` |
| `--sc-radius-full` | `9999px` |

### 4.4 阴影 Token

| Token | 亮色 | 暗色 |
|-------|------|------|
| `--sc-shadow-sm` | `0 1px 2px rgba(0,0,0,0.06)` | `0 1px 2px rgba(0,0,0,0.3)` |
| `--sc-shadow-md` | `0 2px 8px rgba(0,0,0,0.08)` | `0 2px 8px rgba(0,0,0,0.4)` |
| `--sc-shadow-lg` | `0 4px 16px rgba(0,0,0,0.1)` | `0 4px 16px rgba(0,0,0,0.5)` |

### 4.5 间距 Token

| Token | 值 |
|-------|-----|
| `--sc-spacing-xs` | `4px` |
| `--sc-spacing-sm` | `8px` |
| `--sc-spacing-md` | `12px` |
| `--sc-spacing-lg` | `16px` |
| `--sc-spacing-xl` | `20px` |
| `--sc-spacing-2xl` | `24px` |
| `--sc-spacing-3xl` | `32px` |

## 5. 组件设计

### 5.1 ScThemeProvider — 主题提供者

**职责**：应用根节点包裹，初始化主题系统

```vue
<template>
  <ScThemeProvider :mode="'auto'" :brand="brandConfig">
    <App />
  </ScThemeProvider>
</template>
```

**Contract 集成**：
```vue
<ScThemeProvider :contract-config="contract.theme" />
```

### 5.2 ScThemeSwitcher — 主题切换器

**职责**：用户侧亮/暗/自动切换 + 品牌色板选择

**交互**：
- 点击展开下拉面板
- 3 种模式（亮色 ☀️ / 暗色 🌙 / 跟随系统 🖥️）
- 仅允许产品批准的品牌 token 白名单
- localStorage 只保存个人亮/暗/跟随系统偏好；租户品牌从后端权威配置读取
- 恢复默认按钮

### 5.3 ScWhiteLabelPanel — 白标配置面板

**职责**：管理员侧多租户品牌配置

**配置维度**：
| 维度 | 字段 |
|------|------|
| 品牌信息 | 系统名称、英文名称、版权信息 |
| Logo | 亮色/暗色 Logo 的受控附件或静态资产引用（禁止 Base64 和任意外链） |
| 品牌色 | 主色、深色变体、辅助色 |
| 行业定制 | 建筑工程/房地产/物流/制造/通用 |
| 登录页 | 标语、看板标题 |
| 功能开关 | 不属于主题；由后端 capability/permission 单独下发 |

**实时预览**：配置面板右侧模拟应用界面，实时反映品牌名、Logo、主色和模块可见性。

## 6. 预设品牌色板

| ID | 名称 | 主色 | 场景 |
|----|------|------|------|
| ocean-blue | 海蓝 | `#4f7cff` | 默认/通用 |
| forest-green | 森绿 | `#389e0d` | 环保/农业 |
| sunset-orange | 日落橙 | `#fa541c` | 能源/物流 |
| royal-purple | 紫罗兰 | `#722ed1` | 创意/科技 |
| graphite-dark | 石墨灰 | `#262626` | 高端/极简 |
| construction-yellow | 工程黄 | `#d4b106` | 建筑工程 |

## 7. 统一页面契约集成

### 7.1 `ui.theme` capability 边界

- `mode` 只允许 `light`、`dark`、`auto`。
- 品牌名称、版权和 Logo 只能来自 P2/P3 权威配置；Logo 使用受控附件或静态资产引用，不接受任意 URL、Base64 或可执行内容。
- token 覆盖使用 canonical semantic key、类型校验、来源校验、对比度校验和 allowlist；禁止覆盖布局、z-index、安全状态色和可访问性底线。
- 主题契约不承载 capability 开关或权限。能力可见性只来自后端正式 capability、permission 和 action。
- 未通过校验的品牌或 token 配置必须回退到平台默认值并记录 drift。

### 7.2 前端消费流程

```
1. runtime 校验 `ui.theme` 的 schema 版本、配置来源和资产引用。
2. assembler 只保留 allowlist、类型和对比度校验通过的语义 token。
3. ScThemeProvider 把有效配置映射到现有 `@sc/design-tokens`。
4. 主题变化通过统一订阅接口通知延迟加载的 renderer。
5. 校验失败时回退平台默认主题并记录 drift，不影响页面基础能力。
```

### 7.3 Presentation hints 边界

```json
{
  "presentation_hints": {
    "density_preference": "compact_allowed"
  }
}
```

后端不得通过主题契约指定断点或导航形态；实际 compact/nav 布局由前端根据容器和统一响应式规则决定。

## 8. 暗色模式实现策略

### 8.1 CSS 变量 + data-theme 属性

```html
<html data-theme="dark">
```

```css
:root { --sc-bg: #f0f2f5; ... }
:root[data-theme="dark"] { --sc-bg: #0d1117; ... }
```

### 8.2 ECharts 暗色适配

ECharts 不自动读取 CSS 变量，需要主题切换时手动重设：

```typescript
themeManager.onChange((mode, tokens) => {
  chart.setOption({
    color: tokens.colors.chartColors,
    textStyle: { color: tokens.colors.chartTextColor },
    xAxis: { axisLine: { lineStyle: { color: tokens.colors.chartGridColor } } },
    yAxis: { splitLine: { lineStyle: { color: tokens.colors.chartGridColor } } },
  })
})
```

### 8.3 自动模式

```typescript
const mq = window.matchMedia('(prefers-color-scheme: dark)')
mq.addEventListener('change', () => {
  if (currentMode === 'auto') themeManager.apply()
})
```

## 9. 组件迁移指南

现有组件迁移到 CSS 变量只需替换色值：

```vue
<!-- 迁移前 -->
<style scoped>
.card { background: #ffffff; border: 1px solid #e8e8e8; }
.card h3 { color: #1a1a1a; }
.btn-primary { background: #4f7cff; }
</style>

<!-- 迁移后 -->
<style scoped>
.card { background: var(--sc-bgCard); border: 1px solid var(--sc-border); }
.card h3 { color: var(--sc-textPrimary); }
.btn-primary { background: var(--sc-primary); }
</style>
```

迁移后组件自动支持主题切换和白标定制，零逻辑改动。

## 10. 文件清单

| 文件 | 说明 |
|------|------|
| `src/types/theme.ts` | 类型定义（ColorTokens / TypographyTokens / WhiteLabelConfig / ContractThemeConfig） |
| `src/utils/themeEngine.ts` | 主题引擎（预设Token / CSS变量生成 / 品牌色应用 / 主题管理器单例） |
| `src/components/ScThemeProvider.vue` | 主题提供者（根组件包裹，Contract 集成） |
| `src/components/ScThemeSwitcher.vue` | 主题切换器（亮/暗/自动 + 色板选择） |
| `src/components/ScWhiteLabelPanel.vue` | 历史白标配置面板候选；迁移时仅保留受控品牌资产与 allowlisted token 预览，删除功能权限配置 |
| `docs/TECH_DESIGN.md` | 技术方案文档 |
| `demo/theme-demo.html` | 可视化演示页面 |
