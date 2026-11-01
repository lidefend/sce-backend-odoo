# 298 · P4 Finance Test Record Creation Report

## 结论

BLOCKED：无法在不超出授权范围的前提下创建三条隔离草稿记录。

## 必填字段事实（sc_clean 模型定义）

| 模型 | 必填字段 |
| --- | --- |
| payment.request | name, type, project_id, partner_id, currency_id, amount |
| sc.payment.execution | name, source_origin, source_kind, state, project_id, currency_id |
| sc.receipt.income | name, source_origin, source_kind, state, project_id, finance_identity_state, amount, currency_id |

## sc_clean 依赖记录现状

| 模型 | 记录数 |
| --- | --- |
| project.project | 0 |
| construction.contract | 0 |
| res.partner | 7（均为系统/基础对象，无业务往来单位） |
| payment.request / execution / receipt | 0 |

## 原因

三个模型都强制 `project_id`（project.project，必填且无默认值）；payment.request 还强制
`partner_id`（业务往来单位）。sc_clean 无任何项目、合同或业务往来单位，因此通过真实产品
创建流保存草稿必然缺少必要依赖。

按所有者约束“缺少必要依赖时停止并报告，不擅自扩展创建范围”，未创建项目/合同/往来单位，
未使用 sudo 或直接 ORM/SQL 写入。
