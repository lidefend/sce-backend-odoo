# 05 · Project Views and Components

## Native views

`project.project` 原生视图包括：

- form：`project.project.form`（id 944）。
- kanban：`project.project.kanban`（id 951）。
- tree：`project.project.tree`（id 946）。
- search：`project.project.select`（id 945）。

## SCE views

SCE 在原生视图上扩展：

- `project.project.form.sc.overview`（id 1776）：项目概览/台账唯一记录入口。
- `project.project.form.sc.core`（id 1513）：继承原生 form 的按钮盒与字段。
- `project.project.kanban.lifecycle`（id 1422）：生命周期看板。

## Button box

原生 `oe_button_box` 位于原生项目表单，包含：

- 任务。
- 项目更新（`project_update_all_action`）。
- 执行结构。
- 工程量清单。
- 预算/成本、合同、物资/采购、结算/财务等 SCE 扩展入口。

## Component strategy

项目工作空间应优先由原生视图结构承载，SCE 只通过契约消费，避免为每个入口
复制一套专用 Vue 组件。

