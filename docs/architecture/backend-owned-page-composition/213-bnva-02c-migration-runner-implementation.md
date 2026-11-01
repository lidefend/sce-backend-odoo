# 213 · BNVA-02B-02C-02B-02 · Migration Runner 实现

## 新增

- `addons/smart_core/core/controlled_seed_migration.py`：纯逻辑核心。
- `addons/smart_core/tests/test_controlled_seed_migration.py`：16 项单测。

## 薄编排层

- `SeedIdentity(module, external_id)` 稳定身份。
- `migration_id(module, external_id, seed_version, target_digest)` 跨模块唯一。
- `plan_migration` / `decide_execution` / `verify_target_digest` /
  `rollback_reference`。

Runner 不直接写数据库；执行委托现有 `replace_and_publish` /
`restore_published_version` / change_set。

