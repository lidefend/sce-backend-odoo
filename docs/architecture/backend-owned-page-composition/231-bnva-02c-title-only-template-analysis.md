# 231 · BNVA-02B-02C-02C-01 · title-only 模板分析

## 范围

`view_orchestration_form_section_contract_data.xml` 的 19 条 `*_form_sections_v1`。

## 状态

- 13 条 active=True、6 条 active=False（已退役）。
- 全部 sec_fields=0（只有 section 标题，无字段成员）。
- 全部 idf=0（无 Identity）。

## 逐项治理方向

| 结论 | 条件 | 处理 |
| --- | --- | --- |
| 结构事实完整 | 有对应原生 Group + 可明确字段 | 补 fields + Identity |
| 历史结构仍使用 | 有运行时消费者 | 显式 Legacy Compatible |
| 已无消费者 | active=False 或不可达 | 评估退役 |
| 证据不足 | 无法确认消费者/原生结构 | Unclassified Historical |

不按文件名/注释推断；不批量补字段。

