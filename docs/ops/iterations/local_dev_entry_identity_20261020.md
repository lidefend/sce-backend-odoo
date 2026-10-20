# local.dev 入口命名空间一致性修复（2026-10-20）

## 1. 问题

local.dev 的 SPA 正常，但 `/t/demo/api/v1/intent` 返回：

```text
421 NS_NAMESPACE_TARGET_MISMATCH
namespace ns_000000000002 binds sc_demo but this instance serves sc_dev_demo
```

根因：`smart_core` 的全局 namespace seed 把 `ns_000000000002` 固定绑定到 `sc_demo`；
local.dev 使用同一份 seed，但实际服务 `sc_dev_demo`。日常 `/t/demo` 的 `sc_demo` 绑定是
正确的，不能改全局种子或日常入口。

## 2. 修复

- 新增 `scripts/dev/local_dev_entry_identity.sh`：
  - `ensure`：只在 `sc-local-dev / sc_dev_demo` 上运行；
  - 通过 `sc.platform.namespace.alias` 与 `sc.platform.namespace` 解析 `demo` 别名；
  - 若 `demo` 绑定其他库且本地库没有 namespace，则把本地 namespace 绑定修正为
    `sc_dev_demo`；若本地库已有 namespace，则把 `demo` 别名重定向到它；
  - 保留日常 `sc_demo` 的 namespace/entry 不变。
- 新增 `scripts/dev/local_dev_entry_identity_core.py` 纯决策逻辑，覆盖 noop、更新绑定、
  重定向别名、创建 namespace/alias、恢复 retired alias、歧义失败。
- `local.dev.upgrade.run` 在模块升级后自动执行 `entry_identity.ensure`。
- 新增只读 `local.dev.entry_identity.verify`：同时核对 namespace 和
  `/t/demo/api/runtime-version` 的实际 DB。

## 3. 验证

| 命令 | 结果 |
|---|---|
| `make verify.local.dev.entry_identity.unit` | 7 tests PASS |
| `make local.dev.entry_identity.ensure` | `update_database`；`ns_000000000002 -> sc_dev_demo` |
| `make local.dev.entry_identity.verify` | PASS，alias=demo namespace=ns_000000000002 database=sc_dev_demo |
| `POST /t/demo/api/v1/intent` | `401 AUTH_REQUIRED`，不再是 `421 NS_NAMESPACE_TARGET_MISMATCH` |

## 4. 边界

- P4 环境/路由修复，不改 P0-P3 产品契约，不改 demo 数据，不改日常 `sc_demo` 入口。
- 不新建数据库、Compose project、卷、端口或凭据。
- `ensure` 使用本地写租约；`verify` 只读。
- 浏览器/HTTP 验收前必须运行 `verify`。

## 5. 回滚

回退本批 commit；本地 namespace 绑定可通过受管 `local.dev.rebuild_demo` 或后续
`entry_identity.ensure` 恢复，不涉及产品数据恢复。
