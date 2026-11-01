# 154 · BNVA-019 Stage 3C-03C-02A · 运行时观测报告

## 观测结果（candidate 运行时）

| 页面 | native_success | native_failure | default_fallback | catch_all_entered |
| --- | --- | --- | --- | --- |
| project.project 590/1776 | 2 | 0 | 0 | 0 |
| payment.request 649/1773 | 1 | 0 | 0 | 0 |
| project.project 652/944 | —（container_tree） | — | 0 | 0 |
| payment.request 880（container_tree） | — | — | 0 | 0 |

## 结论

- 原生投影对使用它的页面 100% 成功，无失败。
- DEFAULT fallback 实际执行 0 次。
- 旧 ownership catch-all 实际执行 0 次、补充字段 0。

## 覆盖限制

只观测了已知 Form Action/View 与若干发现的动作，未穷举全仓页面；仅凭本观测
不宣称全仓零依赖，但已覆盖五个已知样本及其代表性权威路径。

