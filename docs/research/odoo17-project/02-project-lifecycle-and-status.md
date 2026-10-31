# 02 · Project Lifecycle and Status

## Status fields

`project.project` 上至少存在三类状态：

- `stage_id`：Odoo 原生项目阶段（project.project.stage）。
- `last_update_status`：项目更新状态（`to_define` / `on_track` / `at_risk` / ...）。
- `lifecycle_state` / `sc_approval_state` / `sc_execution_state`：SCE 扩展状态。

## project.update 写回机制

`project.update.status` 是快照状态；Odoo 原生逻辑通过项目更新记录驱动
`project.project.last_update_status` 与 `last_update_id`。

已在本轮 Native View Action 调查中验证：

- 创建 `project.update` 后，`last_update_status` 会从 `to_define` 更新。
- `last_update_id` 指向最新更新记录。
- 删除测试记录后状态回退。

## project_update_all_action

`project_update_all_action` 是 Window Action，目标模型 `project.update`：

- `binding_model_id=false`。
- `binding_view_types=list,form`。
- `view_mode=kanban,tree,form`。
- `domain=[('project_id','=',active_id)]`。

它不是 bound action，而是被原生项目表单 stat button 与项目看板菜单项引用。

## Key distinction

不要把 `stage_id`、`last_update_status`、`lifecycle_state` 混为一谈：

- `stage_id` 是原生项目阶段。
- `last_update_status` 是项目更新快照状态。
- `lifecycle_state` 是 SCE 建筑项目生命周期。
- `sc_approval_state` 是 SCE 立项审批状态。

