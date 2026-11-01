# 292 · P4 Finance sc.payment.execution Runtime

## 环境

namespace=clean，database=sc_clean，user=fixture_role_finance。

## 结果

| 项目 | 结果 |
| --- | --- |
| 菜单 | `menu_sc_payment_execution`（实付登记） |
| Action | 908 |
| Menu id | 339 |
| ui.contract.v2 | 捕获 |
| 控制台错误 | 0 |
| 列表 pageComposition | `unclassified_historical` |
| 诊断 | `PAGE_COMPOSITION_FIELD_OWNERSHIP_MISSING`（warning） |

## 发现

财务角色发布导航中的“付款执行”入口指向 action 908（实付登记），而非产品化主表单
`sc_payment_execution_productized_form_v1` 绑定的 action 709。需要产品确认 709 的
正式菜单入口，以及 908 与 709 的页面归属关系。
