# 170 · BNVA-02A · 页面配置就绪度

| 页面 | 当前配置 | 结构成熟度 | 缺口 | 优先级 |
| --- | --- | --- | --- | --- |
| project.project 590/1776 | native_semantic_surface + identity_fields | formal | 最少，正向样板 | P0 |
| project.project 652/944 | 无独立入口配置 | unclassified_historical | 需 Identity/Section/Ownership | P1 |
| payment.request 649/1773 | `views.form={}` 占位 | 未声明 | 需补完整结构声明 | P1 |
| sc.payment.execution 709/1658 | entry_semantic_surface（8 标题 section） | task_sections 空成员 | 补 section 字段成员 | P1 |
| sc.receipt.income 708/1655 | 配置已退役，指向原生 1644 | 无权威/无分类 | 原生视图需补业务声明 | P2 |

PC-01 / PC-02 产品化样板：作为首个正式结构样板，不能以结构侧通过代替运行时权限与
兼容条件全通过。

原则：配置存在 ≠ 运行时消费；section 标题 ≠ 字段归属。

