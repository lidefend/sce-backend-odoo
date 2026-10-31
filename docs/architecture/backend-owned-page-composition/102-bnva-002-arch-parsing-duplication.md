# 102 · BNVA-002 · Arch 解析重复审计

## 结论

同一个合并 arch 字符串在 view_Parser 体系里被 `etree.fromstring` 重复解析约 15+ 处，
根因是缺少统一 Canonical AST——每种视图解析器（form/tree/kanban/pivot/graph/calendar/
gantt/activity/search）各自重新解析原始字符串。

## 解析重复矩阵（节选，均位于 smart_core）

| 位置 | 动作 | 判定 |
| --- | --- | --- |
| view_Parser/base.py:41 `_parse_arch_root` | etree.fromstring | 基础入口 |
| view_Parser/base.py:104 | etree.fromstring | 重复解析 |
| view_Parser/base.py:175 | 再 _parse_arch_root | 重复 |
| view_Parser/contract_Parser.py:109 `_lossless_parse_xml` | 遍历已解析 root | 保真遍历 |
| view_Parser/contract_Parser.py:208 | 再 _parse_arch_root | 重复 |
| view_Parser/parsers Tree Form.py:510/699/721 | etree.fromstring | 重复 |
| view_Parser/parsers Tree Form.py:1551/1555/1572/1576 | 内联 x2many 子视图重复解析 | 重复 |
| view_Parser/parsers Kanban Pivot Graph.py:51/132/164 | etree.fromstring | 重复 |
| view_Parser/parsers_Calendar_Gantt Activity.py:51/96/150/326 | etree.fromstring | 重复 |
| app_view_config.py:684/748 | etree.fromstring | 重复 |

## 根因

- `get_view()` 返回 arch 字符串，没有共享的结构化中间表示。
- 每个解析器独立 `etree.fromstring` + 自行遍历，产生重复解析和字段 label 回填。
- `_lossless_parse_xml` 与 `_parse_form_view` / `_parse_tree_view` 对同一棵树做两遍遍历。

## 对应修复

BNVA-005 Canonical AST：把合并 arch 解析一次，生成统一 NativeView 结构
（containers / fields / provenance），后续 form/tree/kanban 等视图解析器共享该结果，
消除 ~15 处重复 `etree.fromstring`。
