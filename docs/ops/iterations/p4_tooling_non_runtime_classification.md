# P4 工具归类为非 Odoo 运行时（C 批次）

责任层：P4 交付工具。目标：`scripts/ops/**`、`scripts/ci/**`（P4 交付/验证工具）
不再落入 `unknown_impact` → 全量逐模块 ORM 套件。

## 修复

- `backend_impact_plan.NON_RUNTIME` 由具体 test 模式扩展为 `scripts/ci/**` 与
  `scripts/ops/**`（与既有 `scripts/verify/**` 对齐）。
- 优先级不变：CONTROL_PLANE（有归属单测门禁）与 GLOBAL（`orm_result_guard.sh`、
  workflow、make 等 shared-runtime）仍在 NON_RUNTIME 之前判定。
- 有归属单测的工具继续走 CONTROL_PLANE；其余 P4 工具归 NON_RUNTIME（无 ORM）。

## 验证

- `test_backend_impact_plan.py` 29 项 PASS（新增 P4 工具非 ORM 断言）。
- `verify.ci.workflow.contract` PASS。
