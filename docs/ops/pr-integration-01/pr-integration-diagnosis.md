# PR-INTEGRATION-01 · 诊断

## 问题

PC-01 PR #781 在 GitHub CI 全绿后，`make pr.merge` 仍被阻断，暴露本地验证与合并准入之间的断层。

## 真实失败路径

`pr.merge.preflight`（`validation_delivery_plan.py` → `acceptance_evolution_binding_guard.py`）报告：

- `frontend_presentation` / `relation_roundtrip`：受影响前端运行时（浏览器）套件在
  `.runtime/acceptance-evolution/evidence.v1.json` 无记录 → `no recorded runtime evidence`。
- `list_surface_structure`：已有记录，但 `bound_head` 不是当前 head 的祖先且输入指纹不一致
  → `source is not an ancestor of the head`（carry-forward 被正确拒绝）。

## 根因

`pr.push` / `pr.create`（发布阶段）不强制校验本地 Quick 与验收演进运行时证据，这些只在
`pr.merge`（合并阶段）检查。GitHub CI 只覆盖远端质量门禁，不覆盖这两类本地/浏览器证据，
因此缺口延迟到合并时才暴露。

## 结论

需要把发布准入前移：在 push 之前证明本地 Quick 与受影响运行时套件证据齐全，且精确绑定候选
SHA 与 base SHA。不降低 CI 标准，不伪造证据，不把远端 CI 当作本地 Quick。
