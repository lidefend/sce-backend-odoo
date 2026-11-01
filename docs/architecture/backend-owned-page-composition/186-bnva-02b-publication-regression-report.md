# 186 · BNVA-02B-02B · 发布回归报告

## 测试

- `test_business_structure_integrity`：21/21 PASS（含 11 校验 + 10 门禁）。
- `py_compile` / `git diff --check`：PASS。
- `verify.unified_page_contract.v2.assembler` / `.runtime`：PASS（135）。

## 五样本门禁 Shadow

| 页面 | verdict |
| --- | --- |
| project 590/1776 | formal |
| project 652/944 | 无配置 |
| payment.request 649/1773 | blocked |
| sc.payment.execution 709/1658 | blocked |
| sc.receipt.income 708/1655 | blocked |

## 说明

- 门禁只在新增版本路径阻断；历史已发布配置未被删除或静默升级。
- 未改业务配置、未改公开 V2 Schema、未改数据库结构。

