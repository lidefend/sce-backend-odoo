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

## 结论

`to_define` 是合法 Selection，问题在 `status_with_color` 的状态语义/颜色映射未覆盖
`to_define`，渲染为“?”。修复应落在通用状态映射层（补充 `to_define` 的中性语义），
不新增业务状态，不为 PC-01 加前端模型特判。

## 尚未闭合

产生“?”文本与 `data-semantic-status` 的具体映射表/组件文件，需一次定向捕获状态卡
文本节点与 `data-widget-type`/`data-semantic-status` 属性后确认。
