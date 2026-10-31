# C 轨 · 项目工作空间协作组件定位

## 结论

项目工作空间不使用 PC-02 合同表单的 `Professional*` 协作组件。这些组件全部位于
`frontend/apps/web/src/pages/contractForm/`，是合同表单专属。

项目工作空间的协作区由通用 `NativeFormTreeRenderer.vue` 渲染 Odoo 原生 mail 字段：

- 关注者：`message_follower_ids`（mail.followers x2many），按通用关系渲染，22 人
  连续展开来自通用渲染，非专属 FollowerManager。
- 附件：`message_attachment_ids`，通用附件渲染，容器宽度来自通用布局。
- 协作日志：Odoo mail chatter 的通用投影。

## 整改方向

优先检查 `NativeFormTreeRenderer` 与 mail 字段的现有属性（折叠、头像、列表/上传分离），
通过配置收敛，不重造组件，不套用合同表单 `Professional*` 选择器。

## 待闭合

关注者/附件/时间线的精确 DOM 节点与布局来源需一次项目专用选择器采集。
