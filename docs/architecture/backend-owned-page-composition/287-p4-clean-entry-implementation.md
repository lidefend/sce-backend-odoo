# 287 · P4 Clean Entry Implementation

## 变更文件

- `scripts/dev/local_clean_entry_identity_core.py`（新增）：纯绑定计划。
- `scripts/dev/local_clean_entry_identity.sh`（新增）：受管 ensure / verify。
- `scripts/dev/local_clean_env_prepare.sh`：写入 clean 入口环境变量。
- `config/ops/local_clean_runtime_entry.v1.json`（新增）：clean 入口声明。
- `make/dev.mk`：新增 `local.clean.entry_identity.ensure` / `.verify`。

## 命名空间创建结果

```json
{
  "action": "create_alias",
  "alias": "clean",
  "namespace_id": "ns_c6fed472e939",
  "database_name": "sc_clean",
  "lifecycle_state": "active",
  "demo_database_name": "sc_demo",
  "platform_database_name": "sc_platform_control"
}
```

`demo` / `platform` 绑定保持原值，未被修改。
