# B2 状态问号根因

证据链（candidate，served `b7a5b987b`）：

1. 字段值：`project_project.last_update_status = to_define`（`sc_demo` 与 candidate 均如此）。
2. 字段契约：`ttype=selection`，值域包含 `to_define`，声明显示名“设定状态”。
3. 视图：`<field name="last_update_status" widget="status_with_color" status_label="项目状态" />`。
4. 前端：src 中无 `status_with_color` 特殊处理；本次 DOM 审计显示
   `[data-field-name="last_update_status"]` 计数为 0，说明该字段不是标准字段节点，
   而是由状态组件渲染。

结论：`to_define` 是合法 Selection 值，问题不在数据或契约，而在 `status_with_color`
状态组件的值/颜色映射未覆盖 `to_define`，因此渲染为“?”。

修复方向：给状态组件补充 `to_define` 的中性映射（显示“设定状态”），不新增业务状态，
不把合法值伪装成“数据不可用”；非法值或契约错误仍失败关闭。

尚未定位：产生“?”文本的具体组件文件与映射表（需下一次定向 DOM 采集状态卡文本节点）。
