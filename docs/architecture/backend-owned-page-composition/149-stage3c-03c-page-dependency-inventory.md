# 149 · BNVA-019 Stage 3C-03C-01 · 页面依赖盘点

## 五个样本（运行时核验）

| 页面 | structureAuthority | slots | 是否 primary_facts |
| --- | --- | --- | --- |
| project.project 590/1776 | native_form_slots | sheet | 否 |
| project.project 652/944 | container_tree | [] | 否 |
| payment.request 649/1773 | task_sections | business_* | 否 |
| sc.payment.execution 709/1658 | container_tree | [] | 否 |
| sc.receipt.income 708/1655 | (无) | [] | 否 |

## 结论

已知样本都不依赖旧 ownership 兜底。旧兜底仅在原生投影抛异常的兼容回退路径可达，
不在正常业务流程中触发。

