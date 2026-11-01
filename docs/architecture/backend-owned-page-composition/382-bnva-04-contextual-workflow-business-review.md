# 382 · BNVA-04 Contextual Workflow Business Review

25 个 VUE_CONTEXTUAL 逐类判定：

| 判定 | 对象 | 数量 |
| --- | --- | --- |
| PROFESSIONAL_PAGE_REQUIRED | sc.quality.issue、sc.tax.certificate.registration | 2 |
| EMBEDDED_CAPABILITY | quality recheck/rectification、safety recheck/rectification、contract.event、output.invoice.adjustment、receipt.invoice.line | 7 |
| CONTEXTUAL_NATIVE_SUFFICIENT | ledger/fact/summary/position 类（output/expense/income.ledger、finance.business.fact、counterparty/capital position、interfund、responsibility summary、operating.metrics） | ~14 |
| NOT_VERIFIED | dashboard.cockpit.fact、dictionary/business.category 的产品意图 | ~2 |

结论：真正需要专业页面的仅 2 个；其余为内嵌或原生投影足够。
