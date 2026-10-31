# 06 · Security and Permissions

## Odoo native

- `project.group_project_user`：项目普通用户。
- `project.group_project_manager`：项目经理。
- ACL 与 record rules 决定模型和记录级权限。
- 视图 button 的 `groups` 决定原生按钮可见性。

## SCE extension

SCE 扩展：

- `group_sc_cap_project_read`
- `group_sc_cap_project_user`
- `group_sc_cap_project_manager`
- `group_sc_cap_cost_manager`
- `group_sc_super_admin`

## Principle

前端可见性来自服务端契约权限投影，服务端始终是最终授权者。任何入口都不能只靠
前端隐藏来保护。

