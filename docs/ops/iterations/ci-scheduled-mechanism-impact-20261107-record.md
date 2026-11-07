# CI-SCHEDULED-MECHANISM-IMPACT-20261107 记录

分支 `fix/scheduled-ci-mechanism-impact-rg`，基线 `4ad25ec9`（main，已合入 #828/#829）。

## 根因

定时 professional_quality_gate（main `0bf5fb00d`）在 `verify.capability.module_tooling.unit` 失败：
`test_mechanism_impact_maps_oca_to_capabilities` 期望 `contract.settlement.audit` 在
`impact["base_tier_validation"]`，实际只有 4 项。根因是 `_mechanism_impact()` 用外部 `rg` 子进程
逐 capability 找 `_name` 模型文件，非零退出被静默当空结果；调度 self-hosted runner 上 `rg`
环境敏感，导致 `sc.settlement.order`（`addons/smart_construction_core/models/core/settlement_order.py`）
漏掉。本地 `rg 15.2.0` 复现通过（5 项），与 runner `rg 14.1.0` 行为不一致，属环境敏感。

## 修复

改为纯 Python AST 扫描（`rglob("*.py")` + `_name_declares` / `_inherit_declares`），与
`_mechanism_dependencies` 同口径，消除外部二进制依赖；结果确定，`contract.settlement.audit` 恢复映射。

## 验证

- `python3 -m unittest scripts.verify.test_module_capability_index`：17 项通过。
- `_mechanism_impact()["base_tier_validation"]` 现含 `contract.settlement.audit` 共 5 项。
