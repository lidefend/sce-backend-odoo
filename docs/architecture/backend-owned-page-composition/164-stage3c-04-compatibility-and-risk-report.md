# 164 · BNVA-019 Stage 3C-04 · 兼容与风险报告

## 验证

- `test_native_view_parsed_cache`：9/9 PASS。
- `test_page_composition_integrity_guard`：12 PASS；
  `test_page_composition_integrity_guard_rules`：22 PASS（PC-001～PC-011 规则）。
- `test_node_component_validation`：30 PASS。
- `verify.unified_page_contract.v2.assembler`：PASS；
  `verify.unified_page_contract.v2.runtime`：PASS（23 + 135）。
- `make ci.local.quick`：PASS，回执
  `12f0e53363fa4d6a44719a4a01ed8113344c7f57`。

## not_run

- `test_native_view_projection.py`：本地无 lxml + odoo addons 路径，本轮未重跑；
  由 Stage 3A NCP 14/14 与 Quick `verify.unified_page_contract.v2` 套件覆盖。

## 风险

- 五页面 Smoke 沿用 02A 观测（非本轮重新采集），报告需标注证据时间与适用 SHA。
- 尚未穷举全仓历史页面；旧 ownership 兜底已删除，未被观测到的依赖需由
  BNVA-018/BNVA-02 全链路回归兜底。
- `ui_contract_v2.py` 仍超行数预算（4394 / 4198），仅提示不阻断，后续再规划。

