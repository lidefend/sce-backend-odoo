# 314 · BNVA-02 Closeout Change Ownership

## 资产盘点（39 处，全部保留）

| 类别 | 文件 | 数量 |
| --- | --- | --- |
| P0 正式产品代码 | ui_business_config_contract.py、backend_contract_boundaries.py | 2 |
| P0 测试与 Guard | test_backend_contract_boundaries.py、test_view_orchestrator.py | 2 |
| P4 local.clean 环境/入口工具 | make/dev.mk、docker-compose.yml、nginx 模板、clean runtime entry、6 个脚本 | 10 |
| P4 验收证据（286–306） | clean namespace/入口、财务页面运行时、依赖阻塞、临时角色报告 | 17 |
| 内核收口（307–313） | 7 份矩阵与最终验收 | 7 |
| run record | .agent/runs/BNVA-02/run.json | 1 |

## P0 修复单元对应关系

- `ui_business_config_contract.py` 使用 `lowcode_publication_gate_applies`（来自
  `backend_contract_boundaries.py`），将 product_release 排除出低代码门禁。
- `test_backend_contract_boundaries.py` 新增 5 条来源边界回归；`test_view_orchestrator.py`
  修复发布门禁接入后的测试 namespace。
