# 381 · BNVA-04 Consumption Scope Reconciliation

## 口径说明

187 个 sc.* 模型的互斥划分：

| 桶 | 数量 | 说明 |
| --- | --- | --- |
| VUE_PRODUCT_PAGE | 50 | 有 menu + productized contract |
| VUE_CONTEXTUAL | 25 | 有 menu（角色面），无 productized contract |
| ODOO_NATIVE | 44 | 有原生 menu，但不在任何角色面 |
| HAS_ACTION_ONLY | 11 | 有 action，无 menu |
| TECHNICAL_INFRASTRUCTURE | 57 | abstract / transient |

50 + 25 + 44 + 11 + 57 = 187。

69 个 Workflow（无 productized contract）= 25 VUE_CONTEXTUAL + 44 ODOO_NATIVE。
因此 `50 + 25 + 44 = 119` 不是模型总数，而是“Vue 产品页 + 无契约 Workflow”的并集，
其中 25+44=69 为同一 69 个 Workflow 的两个互斥子集。历史 69 口径与 119 口径不冲突。
