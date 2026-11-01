# 153 · BNVA-019 Stage 3C-03C-02A · 零 fallback 观测设计

## 观测点

1. 原生投影成功/失败：`ui_contract_v2` 两处 `project_native_view` try/except。
2. DEFAULT 回退：回退产物含 `primary_facts` slot 时记录。
3. 旧 ownership catch-all：`_page_composition_contract` 的
   `primary_facts/other_facts` 分支记录补充字段数。

## Shadow 载体

`native_projection_shadow.py`：诊断专用计数器，不记录字段值/凭据，不改变契约输出。

## 统计口径

- native_success / native_failure
- default_fallback
- catch_all_entered / catch_all_fields
- failure_categories / authority

「函数可达」与「实际执行」分开：只有计数器实际递增才算执行。

