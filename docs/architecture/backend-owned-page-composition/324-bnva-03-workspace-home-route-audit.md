# 324 · BNVA-03 Workspace/Home/Route Audit

## 事实

- scene seed 默认载荷绑定 `action_sc_project_list` + `menu_sc_project_project`。
- 场景：workspace.home、projects.intake、projects.list。
- 前端 `useWorkspaceHome.ts`、`sceneRegistry.ts` 消费 workspace home 契约。

## 结论

workspace/home 由后端场景契约驱动，前端只消费；未发现前端自造首页。运行时逐角色首页投影
在 sc_clean 无多角色 fixture，NOT_RUN。
