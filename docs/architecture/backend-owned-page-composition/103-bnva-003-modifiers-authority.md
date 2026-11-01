# 103 · BNVA-003 · Modifiers 权威报告

## 结论

`get_view()` 返回的 arch 里 modifiers 是**原始表达式、未求值**；后端用
`safe_eval(expr, {})`（空上下文）只能解析静态字面量（`1`/`0`/`True`），
记录/上下文相关表达式（如 `invisible="not reject_reason"`）求值失败返回 None。
因此 modifiers 的权威必须拆成两层：后端保留原始表达式，前端按记录运行时求值。

## 实测事实

- arch field 节点 50 个，带 `modifiers` JSON 的 0 个。
- 原始 `invisible` 11 个、`readonly` 18 个、`required` 2 个。
- `_collect_modifiers`（base.py:163）对每个属性执行 `_safe_eval_expr`，
  其实现是 `safe_eval(expr, {})`，空命名空间。

## 问题

1. 静态字面量（`invisible="1"`）可解析为 True。
2. 记录相关表达式（`invisible="not reject_reason"`）在空上下文下 NameError →
   返回 None，后端无法确定可见性。
3. 列表视图的每行记录值不同，modifiers 本就不能在契约组装期一次性求值。

## 权威边界（建议）

| 层 | 职责 |
| --- | --- |
| 后端 | 原样投影 modifiers 原始表达式，仅对静态字面量做辅助解析 |
| 前端 | 按当前记录运行时求值 invisible/readonly/required |
| Guard | 校验 modifiers 投影不丢失、不改变原始表达式语义 |

## 对应修复

BNVA-015：收敛 modifiers 处理——后端不再假装能用空上下文求值记录相关表达式，
契约中同时携带 raw 表达式与（可选的）静态解析结果，前端消费 raw 做运行时求值。
