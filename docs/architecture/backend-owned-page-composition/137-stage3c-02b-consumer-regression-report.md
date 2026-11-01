# 137 · BNVA-019 Stage 3C-02B · 消费者回归报告

## 迁移前后矩阵

| 消费者 | 原始 arch 来源 | 新数据来源 | 复用 Carrier | 是否仍需独立解析 |
| --- | --- | --- | --- | --- |
| fallback_parse | view_data | view_data._arch_root | 否（同 view_data） | 否 |
| onchange_spec | 独立请求 get_view | 不变 | 否 | 是（独立请求） |
| draft_feedback | 独立请求 get_view | 不变 | 否 | 是（独立请求） |
| node_validation | 组装期 get_view | Carrier _arch_root | 是 | 否（无 carrier 时回退） |

## 事实来源统一

同请求 Form 主 arch 的 get_view / fromstring 均为 1 次。独立请求（onchange /
feedback）保持各自解析，不是重复。

