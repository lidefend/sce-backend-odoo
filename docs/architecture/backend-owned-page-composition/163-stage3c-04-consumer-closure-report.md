# 163 · BNVA-019 Stage 3C-04 · 消费者收敛报告

## 已收敛

| 消费者 | 数据来源 | 状态 |
| --- | --- | --- |
| `_fallback_parse` | Canonical Model / Layout Adapter | 已收敛（02B-01） |
| `node_component_validation` | Canonical Model 节点身份 | 已收敛（02B-04） |
| V2 Assembler | 规范化输入，不再重读/重解析/重推导 | 已收敛（03A/03B/03C） |

## 保留独立（按裁定）

| 消费者 | 原因 |
| --- | --- |
| `native_onchange_spec` | onchange 独立请求，服务端授权由 Odoo 决定 |
| `draft_feedback` | 输入 View 可能异于当前请求主 View |

## 遗留清理审计（仅登记）

| 项 | 状态 | 处置 |
| --- | --- | --- |
| `BUSINESS_FORM_STRUCTURE_HISTORY_*` 四常量 | 无生产消费者 | 下一轮独立清理 |
| `record_catch_all` | 无调用方 | shadow 诊断保留，下一轮评估 |
| `record_default_fallback` | 因无 `primary_facts` slots 不再触发 | shadow 诊断保留 |
| `view_Parser.base._safe_get_view_data/_lossless_parse_xml` | 仍服务独立视图类型/保真解析 | 保留 |

