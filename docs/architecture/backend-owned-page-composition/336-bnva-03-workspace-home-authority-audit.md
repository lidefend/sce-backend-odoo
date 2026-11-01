# 336 · BNVA-03 Workspace/Home Authority Audit

## 事实

- 后端 scene seed 默认载荷绑定 `action_sc_project_list` + `menu_sc_project_project`。
- 场景键：workspace.home、projects.intake、projects.list、project.management 等。
- 前端 `useWorkspaceHome.ts`、`sceneRegistry.ts` 消费后端场景契约。

## 结论

workspace/home 是后端场景投影，前端只消费，不存在第二套首页业务入口权威。运行时多角色首页
在 sc_clean 无 fixture，NOT_RUN。
