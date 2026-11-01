# 297 · P4 Finance Action 709/908 Business Adjudication

## 只读事实

| 项目 | Action 709 | Action 908 |
| --- | --- | --- |
| External ID | `action_sc_payment_execution` | `action_sc_payment_execution_actual_outflow` |
| 名称 | 付款执行 | 实付登记 |
| res_model | sc.payment.execution | sc.payment.execution |
| view_mode | tree,form | tree,form |
| view_id | 空（模型默认视图） | 1657（tree） |
| 显式视图绑定 | 无 | tree=1657 `view_sc_payment_execution_tree`；form=1658 `view_sc_payment_execution_form` |
| 产品化配置 | `sc_payment_execution_productized_form_v1` | `payment_execution_actual_outflow_productized_form_v1` |
| 配置 identity | `["name"]` | 空 |
| 菜单绑定 | `menu_sc_company_expense`（公司支出） | `menu_sc_payment_execution`（实付登记） |

## 业务判断（待产品最终确认）

- 两者同属 `sc.payment.execution` 模型。
- 709 是正式产品化主表单：`native_semantic_surface` + identity `name`。
- 908 是下游“实际付款登记”入口：显式实付树/表单视图，配置未声明 identity。
- 财务角色发布导航当前进入 908，而不是 709。

## 结论

支持“709 承担正式产品化主表单、908 保留实付登记业务职责”的假设方向；本轮只读，未修改菜单或
Action。709 的正式菜单入口仍待产品确认。
