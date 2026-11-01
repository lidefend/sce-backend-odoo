# 329 · BNVA-03 Project Initiation Entry Fix

## 修复

在 `pm` 角色 `primary_menu_xmlids` 头部加入 `smart_construction_core.menu_sc_project_initiation`。

## 验证

- `test_identity_resolver_entry_target.py`：15/15 OK（原 14/15）。
- 未修改原生菜单、ACL、Record Rules 或正式角色定义。
