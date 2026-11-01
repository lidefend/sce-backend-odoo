# 291 · P4 Finance payment.request Runtime

## 环境

- namespace=clean，database=sc_clean，user=fixture_role_finance。
- 入口 `http://127.0.0.1:18083/t/clean`。

## 结果

| 项目 | 结果 |
| --- | --- |
| 菜单 | `menu_sc_user_payment_apply` |
| Action | 880 |
| Menu id | 559 |
| ui.contract.v2 | 捕获 |
| 控制台错误 | 0 |
| 列表 pageComposition | `unclassified_historical` |
| 诊断 | `PAGE_COMPOSITION_FIELD_OWNERSHIP_MISSING`（warning，V10） |

## 未验证

表单面（Identity `name`、七个 Section、FieldOwnership、保存/重新进入）未在本轮产生，
原因是 sc_clean 无业务记录，列表→详情回读无记录可打开。需先以受管测试数据创建记录。
