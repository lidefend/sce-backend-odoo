# SCE Element Plus Admin

独立的 Vue 3 + TypeScript + Element Plus 工程管理中后台。项目不依赖原仓库的前端 workspace，默认通过 Vite 代理连接 Odoo 开发环境。

## 启动

```bash
npm install
npm run dev
```

默认地址：`http://localhost:3010`。后端代理目标由 `VITE_API_PROXY_TARGET` 配置，默认是 `http://127.0.0.1:18081`；数据库和租户分别由 `VITE_ODOO_DB`、`VITE_TENANT` 配置。

## 页面

- 登录与会话恢复
- 后端动态菜单、公司上下文和响应式应用壳层
- 工作台和我的工作
- Contract 驱动的列表、搜索、筛选、分组、分页、卡片/看板
- Contract 驱动的详情、创建、编辑、删除、onchange 和业务动作
- Scene Contract 场景页
- 运行诊断

## 架构约束

前端不解析 Odoo XML，不根据角色或模型硬编码业务权限。导航、字段、权限、动作和页面结构均以 `system.init` 与 `ui.contract.v2` 的返回为准，写操作继续由后端 ACL、record rule 和业务状态机裁决。
