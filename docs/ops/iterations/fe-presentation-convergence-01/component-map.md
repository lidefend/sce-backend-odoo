# 组件映射（页面 / 契约 / 运行时 / 公共组件）

基线：主线 `f9a291ae`，运行时 `3f46dd7e`，前端构建 `5690cde9`。

## 页面到运行时

| 页面 | 入口 | 运行时 |
| --- | --- | --- |
| 项目详情 | `/r/project.project/15` | ContractFormPage（record 15） |
| 项目台账 | `/a/588?menu_id=382`（project.project） | ListSurface / t-table |
| 角色首页 | `/s/workspace.home` | WorkspaceHome |
| 表单配置 | `/admin/business-config` | BusinessConfigSurface |

## 公共组件与使用点

| 组件 | 文件 | 使用点 |
| --- | --- | --- |
| ScPopover | `components/design-system/ScPopover.vue` | 字段帮助浮层（FormSection.vue `data-field-help`），基于 TDesignPopup |
| ScTooltip | `components/design-system/ScTooltip.vue` | 通用 hover 提示，基于 TDesignTooltip |
| ScButton | `components/design-system/ScButton.vue` | 帮助触发按钮 `?`（`data-field-help-trigger`） |
| FormSection | `components/template/FormSection.vue` | 字段分组、帮助浮层、字段渲染 |

## 字段帮助链路

1. 契约字段带 `help`（原生 Odoo 字段 help 属性）。
2. `formSection.mapper.ts` 经 `resolveHelpText` 解析为 `helpText`。
3. `FormSection.vue` 在 `helpText` 存在时渲染 `ScPopover`（`NATIVE_FIELD_HELP_TRIGGER='click'`）+ `?` 触发按钮。
4. `ScPopover` 渲染 `TDesignPopup`，浮层内容为帮助文本。

## 待核实的绑定

- ScPopover 未显式声明 `attach`，浮层挂载点与滚动容器的关系需在实现层确认（影响 F1）。
- 项目台账列集合声明来源（P1 列表声明或运行时配置）需定位，确认 F2/F3 的修复层。
- 角色首页区块集合与标题的来源契约需定位，确认 F5/F6 的归属。
