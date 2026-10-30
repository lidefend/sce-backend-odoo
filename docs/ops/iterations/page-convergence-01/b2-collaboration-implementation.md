# PAGE-CONVERGENCE-01A · B2 实施记录

## 已实施（配置）

- 协作资料组字段标签明确：`tag_ids` →「项目标签」，`collaborator_ids` →「协作者」。
- 责任矩阵树列标签明确：`role_key` →「责任岗位」，`user_id` →「责任人」，`note` →「说明」。

载体：`addons/smart_construction_core/views/core/project_overview_views.xml`。

## 待浏览器验证

- 桌面 1440 与窄屏下责任矩阵/协作资料/chatter 的空态与对齐。
- 关注者数量动态读取（不写死 19）。
- 评论与活动时间线不混排。

