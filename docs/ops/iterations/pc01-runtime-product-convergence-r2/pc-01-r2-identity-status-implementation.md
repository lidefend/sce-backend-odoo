# PC-01 R2 · B 轨身份与状态整改实施

分支：`feature/pc01-r2-identity-status`。基线 `e6335f9ed`。

## B1 身份去重

`project_overview_views.xml`：

- 页头身份摘要保留 `project_code`、`user_id`（你的项目角色）、`owner_id`、`project_type_id`。
- 移除页头重复的 `manager_id`（项目经理已保留在责任信息组）。
- 移除“项目身份”组内重复的 `project_code`（编号只在页头突出一次）。
- 移除“责任信息”组内重复的 `user_id`（你的项目角色已保留在页头）。
- 责任信息组保留 `manager_id`、`cost_manager_id`、`doc_manager_id`。

四类责任字段（user_id/manager_id/cost/doc）仍完整，不删除模型字段，不改变权限。

## B2 恢复状态字段渲染

`project_views.xml`：移除 `last_update_status` 的 `widget="status_with_color"` 与
`status_label`，改为普通只读 Selection 字段并设 `string="项目状态"`。

效果：前端通用 Selection 渲染恢复，`to_define` 消费合法 Selection 显示名“设定状态”，
不再出现无意义问号；`lifecycle_state` 与 `sc_approval_state` 继续独立；不新增业务状态。

## 验证

- XML 良构与 `verify.contract.structure_lock`：PASS。
- 运行时 DOM 复核待 P4 审计入口可用后执行（预期 `data-field-name="last_update_status"` 计数
  为 1，文本“设定状态”；`user_id`/`manager_id`/`project_code` 各 1 次）。

未修改模型计算、ACL、record rule、导航、业务数据；未部署、未合并。
