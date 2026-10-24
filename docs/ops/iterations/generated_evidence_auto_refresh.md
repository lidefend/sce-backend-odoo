# 派生物自动刷新（A 批次）

责任层：P4 交付工具。目标：让自动生成的 tracked 派生物（test inventory、complexity
report、split plan、semantic registry、component-driver inventory、contract form
split evidence 等）在**提交前自动刷新**，而不是在 Quick/push 里因过期失败后再手工刷新。

## 设计

- `refresh.generated_evidence`：唯一刷新合集（refresh.generated_reports +
  component_driver_takeover.inventory + contract_form_split_evidence +
  contract.semantic.registry.generate）。
- `scripts/ops/pre-commit_refresh_generated.sh`：pre-commit 钩子，提交前自动刷新并暂存
  派生物目录。
- `agent.hooks.install`：受管安装入口（`git rev-parse --git-path hooks`，兼容 worktree）。
- `ci.delivery.freeze.prepare` 改用 `refresh.generated_evidence`（单一来源）。

## 防御边界

- 派生物 = 主动增量输入 → 自动刷新，不再作为硬门禁。
- 硬门禁保留在 Quick/push 的 `ci.generated_evidence.preflight`（只读）：刷新后仍不一致
  = 生成器漂移或手工篡改，fail。
