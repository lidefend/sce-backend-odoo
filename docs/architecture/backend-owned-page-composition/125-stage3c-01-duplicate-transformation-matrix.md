# 125 · BNVA-019 Stage 3C-01 · 重复转换矩阵

## 真正重复 vs 合法多解析

| arch | fromstring 位置 | 判定 |
| --- | --- | --- |
| form 主 arch | `native_view_projection` + `app_view_config` | 已收敛（共享缓存），1 次 |
| tree arch | `app_view_config`（tree） | 合法（独立视图） |
| search arch | `app_search_config` | 合法（独立视图） |
| kanban/pivot/graph arch | 各自 parser | 合法 |
| calendar/gantt/activity arch | 各自 parser | 合法 |
| 内联 x2many 子视图 arch | `parsers Tree Form.py` | 合法（子视图独立 arch） |
| fallback 重新解析 | `app_view_config._fallback_parse:748` | 兜底，非正常路径 |
| onchange / draft / component 用途 | `native_onchange_spec` / `draft_feedback` / `node_component_validation` | 独立用途，可迁移 |

## 剩余可消除项（3C-02/03 范围）

1. `_fallback_parse` 在解析失败时重新 fromstring —— 可改为复用已缓存 root。
2. `native_onchange_spec` / `draft_feedback` / `node_component_validation` 直接
   读 arch —— 部分可消费 Canonical Model。
3. 内联 x2many 子视图解析是独立子 arch，不是重复，不应强行合并。

