# CI-HISTORY-EVIDENCE-01 记录

分支 `fix/ci-backend-coverage-skip-detection`，基线 `0bf5fb00d`（main，已合入 #827）。

## 根因

#828 在 `3eb0cafa6` 的 `verify_coverage` 失败并非历史执行证据复用断裂，而是
`backend_changed_test_coverage.py:verify_logs` 的 ORM skip 判定子串误报：

```python
skipped = any('skipp' in line.lower() and row['class'] + '.' + row['method'] in line
              for line in text.splitlines())
```

分片 3 回执 `smart_construction_core/orm/execution.log` 首行是
`dev test ... tags=...` 选择行，列出全部 5 个 selector。兄弟方法
`test_notice_skipped_without_declared_field` / `test_notice_skipped_for_unrelated_model`
提供 `skipp` 子串，而每条 selector 又含 `SubmissionReadinessNoticeP1Tests.<method>`，
于是 5 条实际已执行（`Starting` 标记齐全，526 项 0 失败）的方法全部被误判 skipped→pending。

## 修复

skip 判定改为精确结果行匹配：`Class.method` 后紧跟空白与 `skipp` token，
选择行不再命中。新增回归
`test_selection_tags_line_does_not_mark_executed_method_as_skipped` 使用真实失败形状。

## 验证

- `PYTHONPATH=scripts/ci python3 -m unittest test_backend_changed_test_coverage test_backend_test_receipt test_backend_suite_plan`：153 项通过。
- 用本次失败分片 3 的真实回执重放：5 条 P1 用例由 pending 纠正为 executed。
