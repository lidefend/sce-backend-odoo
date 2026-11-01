# 355 · BNVA-04 Industry Model Extension Matrix

smart_construction_core 对标准模型的 `_inherit` 扩展（MODEL_INHERITANCE）：

| 标准模型 | 继承次数 |
| --- | --- |
| project.project | 7 |
| purchase.order | 2 |
| account.move / account.move.line / account.tax | 各 1 |
| stock.picking / stock.move | 各 1 |
| product.template | 1 |
| hr.job / hr.department | 各 1 |
| res.partner.category / res.partner.bank | 各 1 |
| mail.notification | 1 |

`_inherits`（委托继承）仅 2 处。总体以 `_inherit` 扩展标准模型为主，没有为标准模型复制平行 sc.* 模型。
