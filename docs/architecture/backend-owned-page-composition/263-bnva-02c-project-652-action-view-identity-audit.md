# 263 · BNVA-02C-02B-03 · project 652 Action/View 身份审计

## 状态

`not_run`：652/944 为运行时数值 ID，需隔离库解析 `ir.model.data`。本地 Odoo 应用
容器未运行（仅 db/redis），无法只读解析。

## 待核验项

Action 652 / View 944 的 External ID、真实 Model、View 绑定；
`project_overview_form_structure_v1` 实际作用域；Identity 配置绑定列表 Action
（`action_sc_project_list`）的原因；是否需关联详情 Action。

不修改任何配置，待隔离库核验后再决定是否复用 590 的 Identity Summary。

