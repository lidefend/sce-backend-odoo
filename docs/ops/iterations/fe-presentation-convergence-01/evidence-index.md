# 证据索引

## 本轮截图

| 文件 | 内容 |
| --- | --- |
| /tmp/fepc01r/f1-before.png | F1 校准：帮助浮层滚动前 |
| /tmp/fepc01r/f1-after-inner-scroll.png | F1 校准：内部滚动容器滚动后 |
| /tmp/fepc01r/f23-ledger.png | F2/F3 校准：项目台账列表 |
| /tmp/audit_project_detail_full.png | 项目详情整页（基线轮） |
| /tmp/audit_ledger.png | 项目台账列表（基线轮） |

## 关键运行时读数

- 项目详情帮助触发字段：经营方式、预算差异(台账)、最新进度(%)、描述、分析账户、可见性、别名、任务名称、分析账户（9 个）。
- 帮助浮层滚动测量（F1 校准）：滚动 router-host 578px 后，浮层 y 491→-109，触发控件 y 453→-147，相对距离保持约 38px，判定为“随触发控件滚出视口”，无相对错位；点击空白后浮层仍存在。
- 项目台账单元格可见文本（F3 校准）：第一行可见 td 的 innerText 为“状态： 草稿”“合同总额： ¥11,227,000.00”，与列头语义重复，确认为真实显示而非辅助文本。
- 项目台账（F2 校准）：13 个表头，scrollWidth 1424 > clientWidth 1081，横向溢出 343px，判定为列集合超过视口的预期设计。
- 菜单搜索（F7 校准）：搜索“日常合同”同时高亮“日常合同”（construction_contract，在上）与“日常合同结算”（sc.settlement.order，在下），此前进入空列表为 last() 误选，疑似测试误操作。
- 项目台账：`t-table__content` scrollWidth 1424、clientWidth 1081，横向溢出约 343px，15 条记录。

## 既有证据复用

- `docs/ops/iterations/feature_gap_reverification_20261027.md`：17 组功能缺陷重验结论。
- `docs/ops/iterations/demo_recreate_closeout_20261028.md`：demo 定稿重建与发布面收敛。
- `.runtime/demo-user-walkthrough-20261026/`：历史走查证据根（本任务未重跑，仅引用）。
