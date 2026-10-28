# 证据索引

## 本轮截图

| 文件 | 内容 |
| --- | --- |
| /tmp/help_before_scroll.png | 帮助浮层展开后、滚动前 |
| /tmp/help_after_scroll.png | 帮助浮层滚动后 |
| /tmp/audit_project_detail_full.png | 项目详情整页 |
| /tmp/audit_ledger.png | 项目台账列表 |

## 关键运行时读数

- 项目详情帮助触发字段：经营方式、预算差异(台账)、最新进度(%)、描述、分析账户、可见性、别名、任务名称、分析账户（9 个）。
- 帮助浮层滚动测量：滚动内部容器 400px 后，浮层 y 491→91，触发控件 y 453→53，相对距离保持约 38px。
- 项目台账：`t-table__content` scrollWidth 1424、clientWidth 1081，横向溢出约 343px，15 条记录。

## 既有证据复用

- `docs/ops/iterations/feature_gap_reverification_20261027.md`：17 组功能缺陷重验结论。
- `docs/ops/iterations/demo_recreate_closeout_20261028.md`：demo 定稿重建与发布面收敛。
- `.runtime/demo-user-walkthrough-20261026/`：历史走查证据根（本任务未重跑，仅引用）。
