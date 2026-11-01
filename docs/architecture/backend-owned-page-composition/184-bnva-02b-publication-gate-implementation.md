# 184 · BNVA-02B-02B · 发布门禁实现

## 变更

- `business_structure_integrity.py`：新增 `extract_compatibility`、
  `publication_gate`、`BLOCKING_CODES`、`LEGACY_REQUIRED_KEYS`。
- `ui_business_config_contract.py`：
  - `_publication_gate_for(record)` / `_publication_gate_error(gate)`。
  - `_append_published_version` 新版本路径执行门禁，blocked 抛 `ValidationError`。
  - 版本 `snapshot_json` 携带 `_publication_gate`；`restore_published_version`
    剔除后再恢复。

## 兼容声明位置

`contract_json.view_orchestration.compatibility`（不新增 DB 字段）：

```json
{"legacyCompatible": true, "compatibilityReason": "...",
 "compatibilityScope": ["model/action/view"], "unresolvedDiagnostics": [...],
 "owner": "...", "migrationStatus": "..."}
```

