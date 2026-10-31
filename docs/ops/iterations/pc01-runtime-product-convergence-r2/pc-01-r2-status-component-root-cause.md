# B2 · status_with_color 组件根因定位

## 证据链

1. 值：`last_update_status = to_define`。
2. 契约：Selection，`to_define` 声明显示名“设定状态”。
3. 视图：`widget="status_with_color"`，`status_label="项目状态"`。
4. 前端映射：`formSection.mapper.ts` 把 `widget` 原样透传为 `effectiveWidget`，
   `FormSection.vue` 以 `data-widget-type` 输出，未对 `status_with_color` 做模型特判。
5. 通用状态组件：`ScStatusBadge.vue` 通过 `value` / `semantic` / `label` 渲染徽标，
   `data-semantic-status` 决定颜色。
6. DOM：`[data-field-name="last_update_status"]` 计数为 0，说明该字段由状态组件渲染，
   不是标准字段节点。

## 定向采集修正结论

- `[data-widget-type="status_with_color"]`、`.sc-status-badge`、
  `[data-semantic-component="ScStatusBadge"]` 在项目工作空间 DOM 中均为 0。
- `[data-field-name="last_update_status"]` 计数为 0。
- “项目状态”对应的“?”实际是 `data-field-help-trigger`，`aria-label="项目状态"`，
  与“经营方式”“描述”“分析账户”同属帮助触发按钮。

最终结论：`last_update_status`（合法 Selection，`to_define` → “设定状态”）在项目
工作空间视图里被声明，但前端未渲染为字段或状态徽标，属于“声明未消费”；用户看到的
“项目状态: ?”是字段帮助按钮，不是状态值。

修复方向：恢复 `last_update_status` 的展示（显示“设定状态”或等价的合法状态文本），
并在通用状态展示层为 `to_define` 提供中性语义；帮助按钮若没有有效 help 内容则收敛。
