# 数据权限能力基线 v1

数据权限复用既有能力模型：用户身份以 `res.users` 为权威，可分配业务角色以受控
`res.groups` 为权威，项目范围以 `sc.project.member.assignment` 为权威。正式入口只维护
当前公司可维护的非特权内部用户，不创建账号、不暴露原生 ACL/record rule，也不复用 UI
契约列表。

权限变更继续经过 `sc_runtime_user_management` 后端上下文和能力组白名单，前端只渲染契约。
