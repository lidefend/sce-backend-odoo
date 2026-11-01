# 320 · BNVA-03 Navigation Asset Inventory

只读盘点（数据库：sc_clean，正式产品模块安装态）。

| 资产 | 数量 |
| --- | --- |
| ir.ui.menu | 719（带 action 555，无 action 164） |
| ir.actions.act_window | 742 |
| ir.act_window.view | 262 |
| ir.ui.view | form 703 / tree 592 / search 327 / qweb 317 / kanban 75 / pivot 48 / graph 30 / activity 10 / calendar 8 / hierarchy 3 |

## act_window res_model 分布（前若干）

sc.expense.claim 26、sc.project.capability.roadmap 17、project.task 14、project.project 13、
account.move.line 12、stock.picking 11、account.move 10、construction.contract.expense 9、
sc.invoice.registration 8、payment.request 8、res.config.settings 8、res.partner 8 …

## 完整性

- 菜单指向缺失 action：0（无悬空 action 引用）。
- 无菜单引用的 act_window：233（需区分上下文动作、向导、报表、内嵌动作与真正孤立项）。
