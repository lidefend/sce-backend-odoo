# 330 · BNVA-03 Payment Execution Action Adjudication

## 只读事实

| 项 | 709 | 908 |
| --- | --- | --- |
| 名称 | 付款执行 | 实付登记 |
| domain | `[]` | `[('source_kind','=','actual_outflow')]` |
| context | `search_default_group_project=1` | `default_source_kind=actual_outflow` + 层级工作表 |
| 产品配置 | 有（identity name） | 有（无 identity） |

## 裁定

709 是付款执行主入口（不限 source_kind），908 是“实际付款登记”下游入口（限定
source_kind=actual_outflow）。二者不是重复入口，是主入口与下游登记入口的关系。
