# 219 · BNVA-02B-02C-02B-03A · Odoo Runner 集成

## 薄适配层

- `classify_record(source, active, view_type, composition_mode, has_sections, name)`
  初步分类（最终所有权在 03B/03C 逐条确认）。
- `run_migration(record, module, external_id, seed_version, target_payload,
  expected_source_digest)`：resolve 后委托现有发布服务。

## 委托点

- 执行：`record.replace_and_publish(target_payload)`（内部走发布门禁与版本快照）。
- 失败：`record.restore_published_version(snapshot)`。
- 摘要：`verify_target_digest(record.contract_json, target_digest)`。
- External ID 解析：`ir.model.data`（module + name）。

Runner 不绕过发布服务直接写记录。

