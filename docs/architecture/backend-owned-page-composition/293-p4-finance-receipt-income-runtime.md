# 293 · P4 Finance sc.receipt.income Runtime

## 环境

namespace=clean，database=sc_clean，user=fixture_role_finance。

## 结果

| 项目 | 结果 |
| --- | --- |
| 菜单 | `menu_sc_receipt_income` |
| Action | 708 |
| Menu id | 338 |
| ui.contract.v2 | 捕获 |
| 控制台错误 | 0 |
| 列表 pageComposition | `unclassified_historical` |
| 诊断 | `PAGE_COMPOSITION_FIELD_OWNERSHIP_MISSING`（warning） |

## 未验证

Receipt 表单面的 Notebook（责任余额 / 收款台账）属于详情/表单消费，sc_clean 无记录，
尚未取得真实数据来源与消费者证据。
