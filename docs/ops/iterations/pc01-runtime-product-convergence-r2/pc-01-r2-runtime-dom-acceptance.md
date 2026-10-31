# PC-01 R2 运行时 DOM 验收记录

- 工具：`verify.frontend.project_workspace_dom.browser`，candidate profile。
- 目标：`/r/project.project/1?action_id=590&menu_id=382`。
- served SHA：`b7a5b987b62b8c1b6f9dca2cbe52119cd6206669`。
- 结果：PASS，四视口无横向溢出，无控制台错误、无 pageerror、无 5xx。

## 证据

- 身份字段 DOM 计数：`pc-01-r2-project-identity-audit.json`
- 协作区与四视口几何：`pc-01-r2-collaboration-geometry.json`
- 状态问号根因：`pc-01-r2-status-rendering-root-cause.md`
- 截图：`.runtime/final-acceptance/project-workspace-dom/viewport-*.png`

## 关键结论

- B1：`user_id` 与 `manager_id` 各出现 2 次，身份重复属实；`project_code` 也出现 2 次。
- B2：`last_update_status` 走 `status_with_color` 状态组件，未以标准字段节点渲染；
  `to_define` 未映射导致“?”。
- C：项目工作空间协作区不使用合同表单的 `Professional*` 组件；4 个
  `data-field-help-trigger` 均渲染为“?”，确认项目说明上方问号来源。

未修改产品代码、业务数据、ACL、导航；未部署、未合并。
