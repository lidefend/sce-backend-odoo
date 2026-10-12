# 交付语义 vs 渲染实现：契约边界 v1

本文件固化「契约可以表达为了某终端如何交付、不能表达前端组件如何布局和渲染」的边界裁定，
以及该裁定在代码、守卫与投影上的落点。它是 `FE-CONTRACT-RUNTIME-01` 边界收口的规范依据，
不属于渲染说明文档，也不描述任何具体组件。

## 1. 三层责任

```
业务语义 (business semantics)     语义契约 / 域契约：字段业务含义、状态、权限事实
        ↓
交付语义 (delivery semantics)     终端投影契约：为某终端交付哪些字段/动作、密度、可见预算
        ↓
渲染实现 (render implementation)  前端与 Runtime：组件选型、栅格、响应式宽度、渲染调度
```

- 契约（含终端投影）只表达**前两层**。
- 第三层由前端渲染器与运行时策略持有，不得由契约替其选定或改写。

## 2. 裁定表

| 字段/关注点 | 裁定 | 归属 |
|-|-|-|
| `clientType` | 保留 | 交付层 |
| `deliveryProfile` | 保留 | 交付层 |
| `adaptMode` | 保留 | 交付层 |
| `deliveryDensity`（原 `clientDensity`） | 改名保留：只用 `standard`/`compact` 表达"给该终端交付的信息密度" | 交付层 |
| `mobileCollapse` / `maxVisibleContainers` / `maxVisibleWidgets` / `maxVisibleActions` | 保留 | 交付层（终端裁剪事实） |
| `componentRegistry[key].version` | 保留 | 交付层（组件身份 + 版本） |
| `span`（宽度分面） | 保留改义：语义为"信息如何分配给终端" | 交付表达 |
| `columns` | **删除** | 前端布局（`layoutSpan.layoutGridUnits()` 唯一权威） |
| 移动端 `span=1` 重写 | **删除** | 前端响应式 |
| `componentConfig.mobile.fullWidth` | **删除** | 前端布局 |
| `runtimeContract.renderStrategy` 的终端注入 | **删除** | Runtime 内部策略 |
| `runtimeContract.virtualization.mobile` 的终端注入 | **删除** | Runtime 内部策略 |
| `adapter` / `selectedAdapter` / `selected_adapter` / `fallback`（组件注册表内） | **禁止** | 前端组件词汇 |

密度取值属于交付语义（`standard`/`compact`）；把它映射成 UI Kit 的视觉密度（如 `cozy`）是前端职责。

## 3. 机制落点

后端终端投影 `addons/smart_core/core/unified_page_contract_v2_client.py::trim_unified_page_contract_v2`
只做交付裁剪：容器/字段/动作预算、`statusContract` 收敛、`deliveryProfile`、`deliveryDensity`、
`adaptMode`、`mobileCollapse`、`meta.deliveryTrim` 记账。它**不得**改写 `runtimeContract` 的渲染策略，
不得声明栅格列数，不得按终端改写字段宽度或注入 CSS 级全宽指令。

投影边界清洗 `addons/smart_core/handlers/ui_contract_v2_projection.py`：

- `normalize_component_registry_entries`：剥离组件注册表里的渲染特性（`adapter`/`selectedAdapter`/`selected_adapter`/`fallback`）。
- `normalize_layout_hints_entries`：剥离 `layoutHints` 里的渲染实现（`columns`/`gridColumns`/`cssWidth`/`renderStrategy`/`virtualization`）。

守卫 `scripts/verify/unified_page_contract_v2_client_guard.py`：

- 源契约与每个终端的投递面都必须**不得出现**渲染实现键（fail-closed，源侧同样拦截，避免只在下游静默剥离）。
- 终端投影必须保留 `runtimeContract`（除 `deliveryProfile` 外不得改写）。
- 组件注册表每项必须声明 `version`；出现渲染特性即失败。

前端消费：`ContractFormDriverHost.vue` 用 `layoutHints.deliveryDensity` 决定 UI Kit 密度，用本地
`layoutGridUnits()` 决定列数；`professionalComponentRegistry.contractComponentBinding()` 只校验 `version`，
遇到渲染特性键即 fail-closed。

## 4. 终端区分规则

- **要区分终端**：区分的是"交付事实"——该终端交付哪些字段/动作、可见预算、密度结论、折叠结论。
- **不区分终端**：渲染实现（框架组件名、列数、CSS 宽度、渲染调度、虚拟化策略）对所有终端同一套前端实现。
- 手机端"功能减少"= 后端按终端裁剪的交付事实（`maxVisible*`、容器裁剪、`meta.deliveryTrim` 记账），
  必须有后端事实依据，不得由前端自行判断。

## 5. 反例（不得回流）

- 契约里出现 `ElInput`/`ElTable`/`WxInput`/`H5Input` 等框架组件名或 `selectedAdapter`。
- `layoutHints.columns = 24/1` 或 `gridColumns`。
- 终端投影把 `renderStrategy` 改成 `scheduled`、给移动端注入 `virtualization.mobile`。
- 终端投影把移动端 `span` 重写为 `1` 或注入 `mobile.fullWidth`。
