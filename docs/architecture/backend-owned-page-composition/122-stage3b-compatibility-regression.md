# 122 · BNVA-019 Stage 3B · 兼容与回归

## 契约输出

| 页面 | 结构权威 | 结果 |
| --- | --- | --- |
| project.project 590/1776 | native_form_slots | 不变，manager_id 在 mainData |
| payment.request 880 | container_tree | 不变，slots=0 |

## 回归范围

- native_view_projection 14/14
- native_view_parsed_cache 4/4
- contract_admission_policy 5/5
- 精确 HEAD Quick：待补

## 已知边界

请求缓存按 cursor + uid + 关键 context 隔离；有界 LRU。它是内部优化，不替代权限，
也不进入公开契约。

