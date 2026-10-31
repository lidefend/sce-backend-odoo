# 04 · Collaboration and Chatter

## Odoo mail.thread / mail.activity.mixin

`project.project`、`project.task`、`project.update`、`project.milestone` 都继承
mail thread / activity mixin，因此原生具有：

- `message_follower_ids`：关注者。
- `message_ids`：消息。
- `activity_ids`：活动。
- 附件能力。

## SCE current projection

SCE 当前项目工作空间通过通用 mail 渲染链消费关注者、附件、时间线。

PC-01 R2 C 轨需要解决的不是“没有能力”，而是：

- 关注者摘要与折叠。
- 附件列表与上传入口分离。
- Chatter 评论/活动/附件的信息层级。
- 帮助触发器是否有有效帮助内容。

## Status

当前 P4 DOM 审计显示 candidate 项目概览页有 4 个 help trigger，均为 `?`，且
`followerNodes / attachmentNodes / timelineNodes` 在审计探针中为 0。这提示
需要进一步确认通用 mail 渲染链的实际 DOM 结构，而不是新增组件。

