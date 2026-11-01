# 235 · BNVA-02B-02C-02C-01 · 历史配置迁移矩阵

| 配置 | 组 | 缺口 | 建议 |
| --- | --- | --- | --- |
| 46 条 form_productization | sections+fields | 缺 Identity | A 补 Identity |
| 13 条 active title-only | title-only | 缺 fields+Identity | B Legacy 或 C 待定 |
| 6 条 retired title-only | active=False | — | D 退役/归档 |
| payment_request_form_sections_v1 | views.form={} 空占位 | 空 | 核实消费者后退役/补齐 |
| sc_receipt_income_form_sections_v1 | active=False 退役 | — | 保留追溯，不自动恢复 |

不得根据文件名/注释推断；每条按来源/所有权/消费者/原生结构逐项治理（02C-02）。

