# 197 · BNVA-02B-02C-01 · 历史配置分类

| 配置 | source_type | owner | lifecycle | runtime_consumer | compatibility_status | recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| payment_request_form_sections_v1 | 代码种子 | 代码模块 | published, views.form={} | 空占位 | FORM_STRUCTURE_EMPTY | 核实占位后补齐或退役 |
| sc_receipt_income_form_sections_v1 | 代码种子 | 代码模块 | active=False 退役 | 无（原生 1644） | 退役未解析 | 确认消费者后清理或保留 |
| 只有 title 的 sections | 代码种子 | 代码模块 | published | task_sections 空成员 | 缺 key/fields/identity | 补 fields 或降 Legacy |
| published 但结构为空的配置 | 代码种子 | 代码模块 | published | 空占位 | FORM_STRUCTURE_EMPTY | 治理或退役 |

原则：配置存在 ≠ 运行时消费；published ≠ 完整；active ≠ Formal。

