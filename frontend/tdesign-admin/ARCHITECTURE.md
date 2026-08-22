# Smart Construction TDesign Admin

本目录由 `tdesign-starter-cli` 的 Vue 3 `all` 模板生成，作为新管理端唯一的 UI 基座。腾讯 starter 的布局、主题设置、国际化、标签页、列表、表单、详情、结果页和权限路由均保留；Odoo 业务能力通过 `src/api/odoo.ts` 和动态路由接入。

## 分层

- `src/layouts`: starter 官方应用壳层、侧栏、顶部操作区、页签和主题设置。
- `src/pages`: starter 示例页面与业务页面；`pages/odoo/action` 是后端 action contract 的运行时入口。
- `src/router`: starter 固定路由和运行时动态路由。
- `src/store`: Pinia 用户、权限、设置、通知和页签状态。
- `src/api/odoo.ts`: Odoo intent envelope、token、`X-Odoo-DB`、`X-Tenant` 和 `X-Trace-Id` 适配层。
- `src/locales`: 中英文资源及 TDesign 组件语言包。

## 登录链路

1. 登录页调用 `login` intent，token 保存到 `localStorage`。
2. 路由守卫调用 `system.init`，恢复用户、角色、动态菜单、工作台和业务范围。
3. 动态菜单转换为 starter 的 `RouteRecordRaw`，由官方 `SideNav` 渲染。
4. 业务 action 进入 `pages/odoo/action/index.vue`，使用 `ui.contract.v2` 获取真实页面 contract。

## 本地运行

```bash
npm install
npm run dev:linux
```

开发端口默认为 `3002`，若端口占用 Vite 会自动选择下一个端口。开发代理把 `/api` 转发到 `http://127.0.0.1:8070`。

环境变量见 `.env.development`：固定数据库为 `sc_dev_demo`，租户为 `default`。
