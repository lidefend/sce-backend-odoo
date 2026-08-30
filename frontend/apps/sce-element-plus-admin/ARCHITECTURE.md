# 前后端渲染逻辑分析

## 请求链路

1. `login` Intent 返回 Token。
2. 路由守卫调用 `system.init`，取得用户、角色、公司、导航、工作台和路由权限。
3. 服务端导航节点转换为 Vue Router 地址，由 Element Plus `el-menu` 渲染。
4. Action 页面调用 `ui.contract.v2`，读取 `pageInfo`、`layoutContract`、`statusContract`、`actionContract`、`dataContract`、`searchContract`。
5. 列表数据统一走 `api.data`；分页、搜索、Domain、排序和分组参数由页面状态组成。
6. 记录详情再次加载只读或编辑 Contract，以 Contract 字段生成 Element Plus 表单。
7. 新建、更新、删除、onchange 和按钮分别走 `api.data.create`、`api.data.write`、`api.data.unlink`、`api.onchange`、`execute_button`。

## 职责边界

- Odoo 后端负责模型、状态、权限、字段元数据、原生视图解析和业务动作。
- Contract 层负责把 Odoo 语义标准化为前端可消费的数据结构。
- Vue 前端只负责通用渲染、交互状态、请求反馈和响应式布局。
- 隐藏按钮不是安全边界，所有写操作仍由后端最终校验。

## Element Plus 映射

| 契约语义 | Element Plus |
| --- | --- |
| 导航树 | `el-menu` / `el-sub-menu` |
| 集合视图 | `el-table` / `el-card` / `el-pagination` |
| 搜索与筛选 | `el-input` / `el-select` / `el-dialog` |
| 记录表单 | `el-form` / `el-form-item` / 字段组件 |
| 业务动作 | `el-button` / `el-dropdown` / `ElMessageBox` |
| 页面状态 | `el-skeleton` / `el-empty` / `el-alert` / `ElMessage` |
| 场景区块 | `el-card` / `el-row` / `el-table` |
