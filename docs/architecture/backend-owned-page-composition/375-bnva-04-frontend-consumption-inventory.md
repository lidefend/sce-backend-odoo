# 375 · BNVA-04 Frontend Consumption Inventory

## 69 个 Workflow 的前端消费面（证据驱动）

| 分类 | 数量 | 判定 |
| --- | --- | --- |
| VUE_PRODUCT_PAGE | 50 | 有 ui.business.config.contract（自定义 Vue 显式消费） |
| VUE_CONTEXTUAL | 25 | 有角色面菜单，无产品契约，经原生投影消费 |
| ODOO_NATIVE | 44 | 有原生菜单但不在角色面（汇总/配置/中间对象），非 Vue 主页面 |

## 结论

真正需要评估契约补足的只有 25 个 VUE_CONTEXTUAL，且多数是台账/事实/汇总/上下文对象，
原生投影可覆盖；44 个 ODOO_NATIVE 不应进入业务页面产品化队列。
