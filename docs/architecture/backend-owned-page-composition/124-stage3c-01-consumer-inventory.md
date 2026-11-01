# 124 · BNVA-019 Stage 3C-01 · 消费者盘点

> 只读审计。标记每个消费者在原生事实链上的角色。

## 标记含义

A 原生 arch 获取 · B XML 解析 · C Canonical Model 消费 · D 原生结构遍历 ·
E 业务语义推导 · F 布局结构生成 · G 最终 Contract 输出

## 消费者清单

| 文件 / 函数 | 角色 | 说明 |
| --- | --- | --- |
| `native_view_projection.project_native_view` | A/B/C/D | NCP 入口：get_view + fromstring + 遍历 → NativeView |
| `native_view_projection.build_native_form_structure_contract` | C/E | Business Structure Adapter（slots/ownership） |
| `app_view_config._safe_get_view_data` | A/B/D | LDP 入口：get_view + fromstring，并写入共享缓存 |
| `app_view_config._generate_from_fields_view_get` | F | 布局解析编排 |
| `app_view_config._fallback_parse` | B/D | 解析失败时的兜底重新解析 |
| `view_Parser.base._parse_arch_root` | B | root=None 时的解析入口 |
| `view_Parser.contract_Parser.OdooViewParser` | D/F | Layout Adapter 主体 |
| `view_Parser/parsers Tree Form.py` | D/F | tree/form 布局 + 内联 x2many 子视图解析 |
| `view_Parser/parsers Kanban Pivot Graph.py` | D/F | kanban/pivot/graph 布局 |
| `view_Parser/parsers_Calendar_Gantt Activity.py` | D/F | calendar/gantt/activity 布局 |
| `page_assembler._fetch_initial_data` | F/G | 列表/表单首屏 |
| `page_assembler._inject_relation_entry_contract` | E/G | 关系入口（relation_descriptor 消费） |
| `ui_contract_v2._enrich_native_form_composition` | C/E | NCP 编排 |
| `ui_contract_v2._inject_business_operation_contract` | C/E | 业务操作结构 |
| `unified_page_contract_v2_assembler` | C/G | 最终契约组装 |
| `native_onchange_spec` / `draft_feedback` / `node_component_validation` / `view/base` | A/B | 特定用途的独立 arch 读取 |

## 关键结论

Form 主视图在 Stage 3B 已收敛为一次获取、一次解析。剩余 fromstring 分两类：

1. 不同视图类型（tree/kanban/search/子视图）各自解析自身 arch —— 合法，非重复。
2. 特定用途读取（onchange / draft feedback / component validation / fallback）
   —— 独立用途，部分可迁移到 Canonical Model。

