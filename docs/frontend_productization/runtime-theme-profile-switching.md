# Runtime Theme Profile Switching（运行态风格 Profile 切换）

> 状态：已实现（分支 `feature/p0-theme-profile-switching-v1`）
> 目标阶段：产品化路线图 Tokens → Primitives 之后的「运行时风格」能力
> 与明暗模式关系：**正交维度**，profile × mode 可自由组合

## 1. 背景与问题

产品此前只有 **light/dark 明暗切换**（`data-sc-theme`，见 `theme.ts`）。而设计系统层已经定义了 3 套权威风格 Profile（`frontend/packages/ui/src/kits/tokens.ts` 的 `SCENE_DESIGN_TOKEN_PROFILES`）：

| Profile id | 定位 | 品牌 | 强调 | 圆角 |
|---|---|---|---|---|
| `enterprise-neutral` | 企业中性（默认） | #0a6ed1 | #eaf3fc | 7px / 12px |
| `business-soft` | 柔和商务 | #087f6a | #e4f4f0 | 10px / 14px |
| `accessible-contrast` | 高对比（可达性） | #004f9e | #d9ecff | 5px / 8px |

但这些 Profile **没有运行时消费入口**——`SceneUiProvider` 支持 `tokenProfile` prop，但 `apps/web` 从不使用它；`SceneObjectPage` 又把 `--sc-scene-*` 硬编码在 `:root`。结果是：产品只有明暗切换，战略上的「运行状态切换界面风格」链路是断的。

## 2. 设计决策

### 2.1 为什么在 web 侧做，而不复用 SceneUiProvider

产品应用的实际渲染链是：

```
<ScTheme> (light/dark, data-sc-theme)
  └─ design-tokens (--sc-semantic-*)
       └─ kits/tdesign/theme.css :root 层 (--td-* = var(--sc-semantic-*))
            └─ Scene* 组件 / 业务页面
```

`apps/web` **不挂载 SceneUiProvider**（它是 demo/未来产物），因此 `--td-*` 由 `:root` 层的 **semantic 驱动**分支提供（`--td-brand-color: var(--sc-semantic-surface-interactive)` 等）。结论：**覆盖 `--sc-semantic-*` 即可同时驱动原生组件与 tdesign 变量桥**。所以本轮不引入 provider，而是新增一个与明暗并列的产品级维度。

### 2.2 正交性契约

- 明暗层（`tokens.light.css` / `tokens.dark.css`）继续拥有 **surface / text** 令牌。
- Profile 层只拥有 **brand / emphasis / focus / border / radius / status** 令牌——这些在明暗下语义一致。
- 唯一例外：`accessible-contrast` 在**非暗色**表面下额外抬高文字对比（`:not([data-sc-theme='dark'])`）。

这样 `dark × business-soft`、`light × accessible-contrast` 等组合都可预期，互不污染。

## 3. 实现

| 文件 | 改动 |
|---|---|
| `apps/web/src/styles/theme.ts` | 新增 `ScThemeProfile`、`SCENE_THEME_PROFILES`、`isSceneThemeProfile`、`applyThemeProfile` / `bootThemeProfile` / `nextThemeProfile` / `persistThemeProfile`；`data-sc-theme-profile` 属性 + localStorage `sc_theme_profile` |
| `apps/web/src/styles/tokens/profile.css` | 3 个 `[data-sc-theme-profile=...]` 作用域块，覆盖 semantic 品牌/强调/焦点/边框/状态/圆角令牌 |
| `apps/web/src/styles/tokens/index.css` | 末尾 `@import './profile.css'`（保证覆盖 tdesign-bridge 默认值） |
| `apps/web/src/main.ts` | `bootTheme()` 后调用 `bootThemeProfile()` |
| `apps/web/src/layouts/AppShell.vue` | topbar 新增「风格」切换按钮（3 选 1 循环，与明暗按钮并列），onMounted 加载持久化值 |
| `scripts/verify/frontend_theme_profile_guard.py` | 静态 guard（见 §4） |
| `make/frontend.mk` | 新增 `verify.frontend.theme_profile.unit` 并挂入 `verify.frontend.quick.gate` |

### 3.1 运行时链路

```html
<html data-sc-theme="light|dark" data-sc-theme-profile="enterprise-neutral|business-soft|accessible-contrast">
```
`profile.css` 按 `data-sc-theme-profile` 覆盖 `--sc-semantic-*` → `kits/tdesign/theme.css :root` 层的 `--td-*` 联动 → 页面组件即时变色/变圆角，**无需刷新**。

## 4. 验证

`make verify.frontend.theme_profile.unit`（已挂入 quick.gate）：

1. **完整性**：profile.css 声明全部 3 个 profile 作用域块。
2. **一致性**：business-soft / accessible-contrast 的品牌色、controlRadius、surfaceRadius 与 `kits/tokens.ts` 权威值逐字段相等。
3. **运行时模型**：theme.ts 暴露 3 个 id + `isSceneThemeProfile` + `nextThemeProfile` 循环覆盖全部。
4. **正交性**：profile.css 不得覆盖 `--sc-semantic-surface-page/panel`（破坏明暗层所有权）。

## 5. 后续迭代候选

- 将 profile 提升为**组织级配置**（按公司/租户下发默认 profile），而非仅个人偏好。
- `SceneUiProvider` 的 `tokenProfile` 与产品 `data-sc-theme-profile` 打通（若未来启用 provider）。
- 为 3 个 profile 补充截图基线，纳入 browser acceptance。
