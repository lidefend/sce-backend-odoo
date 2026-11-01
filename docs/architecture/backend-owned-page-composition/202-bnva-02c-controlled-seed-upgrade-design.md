# 202 · BNVA-02B-02C-02A · 受控种子升级设计

## 迁移记录字段（复用版本快照，不新增平行 Schema）

seed_version / target_version / migration_id / source_definition_digest /
target_definition_digest / migration_status / compatibility_check /
rollback_reference。

## 机制

- 迁移以 `ui.business.config.contract` 记录 + 不可变版本快照为载体。
- `payload_sha256` / `definition_sha256` 作为源/目标摘要；`change_set` 复用为预览
  与审批通道；`restore_published_version` 作为回滚。
- 迁移必须幂等、可中断、可重试；重复执行不产生重复版本。
- 用户公司级覆盖（tenant_lowcoding）不参与种子迁移，保持独立。

## 状态机（设计）

pending → preview → published → rolled_back / failed；每步绑定版本摘要。

