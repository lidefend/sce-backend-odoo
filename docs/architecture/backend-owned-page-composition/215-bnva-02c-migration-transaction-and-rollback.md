# 215 · BNVA-02B-02C-02B-02 · 迁移事务与回滚

## 快照

迁移前保存完整版本快照（`ui.business.config.contract.version`），记录源版本与
payload/definition 摘要。

## 失败恢复

- 执行失败 → `restore_published_version` 恢复原发布版本。
- 恢复后重验 payload_sha256 / definition_sha256。
- 恢复不污染 tenant_lowcoding。
- 不假设跨库事务天然原子；每步在 ORM 事务/savepoint 边界显式落点。

