# 69 · Guard Rule Alignment Implementation（4G-02C）

## 结论

`page_composition_integrity_guard.py` 已按 ARCH-DECISION-004 完成 PC-001～PC-011
全规则对齐，版本升至 `1.1.0`。

## 主要变更

1. 两层权威（PC-001）：同时检查业务组合（slots）与布局拓扑（containerTree）；
   containerTree 不得替代 slots。
2. 引用规范化：`slot:<id>` / `group:<id>` 与裸 id 统一解析，修复 PC-005 主 slot
   排除失效。
3. 类型健壮性：`fieldRefs` / `groups` 为非法标量时输出结构化诊断，不抛
   TypeError。
4. Schema 驱动辅助 role：`allowed_slot_roles` 从 evidence 读取，不再硬编码；
   无 Schema 时保守 NOT_VERIFIED。
5. 重复键检测：JSON 解析阶段用 `object_pairs_hook` 检测重复 key，`field:*`
   重复键使 PC-004 FAIL。
6. 证据充分性：PC-007～PC-010 只接受 VERIFIED + 范围匹配 + 规则级充分证据；
   PC-008 要求权限边界覆盖，TEST_EXECUTION 成功不再自动 PASS。
7. PC-011 新增：containerTree 结构完整性、引用有效性、归属冲突、slots↔container
   映射一致性。
8. 报告补齐：`execution_timestamp`、`page_classification_summary`、
   `evidence_summary`、`evidence_trust`、`parse_diagnostics`、`remediation_hint`；
   Markdown 增加状态计数、NOT_VERIFIED 清单、FAIL 清单。

## 文件

- 修改：`scripts/verify/page_composition_integrity_guard.py`（v1.1.0）。
- 修改：`scripts/verify/test_page_composition_integrity_guard.py`（PC-005
  Schema 驱动断言）。
- 修改：`scripts/verify/test_page_composition_evidence_contract.py`（PC-008
  充分性断言）。
- 新增：`scripts/verify/test_page_composition_integrity_guard_rules.py`（22 项）。

## 关键机制

- `_slot_ref` / `_group_ref`：统一引用身份。
- `_trusted_items`：只保留 VERIFIED 且范围匹配的证据。
- `_sufficient_items`：在可信证据上追加规则级 type/coverage 过滤。
- `_load_json_detect_duplicates`：解析期重复键检测。

## 约束

未改 assembler、业务 Schema、业务字段、业务配置、ACL / Record Rules、数据库；
未删 Legacy fallback、未迁移页面、未改变发布阻断策略、未重建 Candidate。
