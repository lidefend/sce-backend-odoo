# 427 · BNVA-04 PR #790 Assembler Differential

## unified_page_contract_v2_assembler.py

PR #790 独立增量（+39 行）：

- 引入 TECHNICAL_FIELD_CODES。
- 新增 `_page_composition_widget_field_codes()`：从 layoutContract.containerTree 收集实际渲染字段。
- 新增 catch-all 归属：未归属且非技术字段的渲染字段归入 `slot:primary_facts` / `group:other_facts`。

Feature 状态：

- 三处符号均在：TECHNICAL_FIELD_CODES（行18）、_page_composition_widget_field_codes（行766）、
  widget_field_codes 使用（行820）。
- 缓存版本 v25-legacy-fallback-retirement（PR #790 为 v15）。
- Feature 短约 720 行来自其它 BNVA 重构，不来自删除 PR #790 增量。

## 分类

STRICT_EVOLUTION——Feature 已吸收并推进 PR #790 的 catch-all 归属能力。
