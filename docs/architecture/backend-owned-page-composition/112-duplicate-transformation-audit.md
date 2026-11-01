# 112 · BNVA-019-07 · 重复解析与重复推导识别

> 目标：列出同一原生事实被多处重复解析/推导的现状，作为 BNVA-019 收敛输入。

## 1. Arch 解析重复

同一合并 arch 在 `view_Parser` 体系被 `etree.fromstring` 重复解析（BNVA-002）。

| 位置 | 动作 |
| --- | --- |
| `view_Parser/base.py` | `_parse_arch_root` / 多处 fromstring |
| `view_Parser/contract_Parser.py` | `_lossless_parse_xml` + 再次 `_parse_arch_root` |
| `view_Parser/parsers Tree Form.py` | 多处 fromstring，含内联 x2many 子视图 |
| `view_Parser/parsers Kanban Pivot Graph.py` | 多处 fromstring |
| `view_Parser/parsers_Calendar_Gantt Activity.py` | 多处 fromstring |
| `app_view_config.py` | fromstring |
| `core/native_view_projection.py` | 独立 fromstring（Canonical AST） |

根因：没有共享的结构化中间表示，每个解析器各自 fromstring + 遍历。

## 2. 业务结构双轨

| 轨道 | 位置 | 状态 |
| --- | --- | --- |
| 原生投影 | `native_view_projection.py` | 主路径 |
| 旧字段名启发式 | `ui_contract_v2_form_structure.py` | fallback + selected-authority 路径 |

启发式仍保留 `identity/relation/term/amount/status/collaboration/detail/source/
history_check` 等字段名分类清单，作为 `native_authority` /
`entry_semantic_surface` 页面与异常回退的输出。

## 3. 字段元数据重复

- `fields_get()` 在 `native_view_projection` 与 `page_assembler._to_fields_map`
  等路径重复调用。
- XML `string` 与 `fields_get().string` 的 label 回填逻辑分散在多处。

## 4. Modifier 处理重复

`view_Parser/base.py._collect_modifiers` 对每个属性做 `safe_eval(expr, {})`，
对记录相关表达式返回 None；`native_view_projection` 只原样投影 raw。两者并存
造成「原始表达式 + 空上下文求值结果」两套信息。

## 5. 收敛方向（BNVA-019 之后）

- 原生事实只采集一次（Canonical AST）。
- 业务语义只声明一次（配置）。
- 契约只投影一次（Assembler 统一输入）。
- 前端只消费一次。

