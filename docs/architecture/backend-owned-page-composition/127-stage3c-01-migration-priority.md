# 127 · BNVA-019 Stage 3C-01 · 迁移优先级

## 可安全迁移（消费 Canonical Model / 共享 root）

| 消费者 | 迁移方式 | 优先级 |
| --- | --- | --- |
| `_fallback_parse` | 复用已缓存 root | P1 |
| `native_onchange_spec` | 消费 NativeView field_metadata/modifiers | P2 |
| `draft_feedback` | 消费 NativeView 结构身份 | P2 |
| `node_component_validation` | 消费 Canonical Model 容器树 | P3 |

## 必须保留（合法独立 arch）

| 消费者 | 原因 |
| --- | --- |
| tree/kanban/pivot/graph/calendar/gantt/activity/search parser | 各自视图类型独立 arch |
| 内联 x2many 子视图 parser | 子视图独立 arch |

## 迁移顺序建议

1. 先落地请求级 carrier（修复缓存生命周期）。
2. 再让 `_fallback_parse` 复用共享 root。
3. 逐步把 onchange/draft/validation 迁到 Canonical Model 消费。
4. 不拆 `unified_page_contract_v2_assembler.py`；先消重复职责，再按真实边界拆分。

