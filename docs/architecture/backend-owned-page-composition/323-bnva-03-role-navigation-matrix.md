# 323 · BNVA-03 Role Navigation Matrix

## 状态

- 静态：由 XML `groups` + 角色组定义构建（VERIFIED_STATIC）。
- 运行时：仅 fixture_role_finance 有 clean 运行时导航证据（15 条）；其余角色在 sc_clean
  无 fixture 用户，运行时 NOT_RUN。

## 关键发现

`test_identity_resolver_entry_target.py`（15 项）1 项失败：

- `test_multi_role_project_manager_keeps_project_intake_executable_surface` 期望项目负责人
  复合角色的 `primary_menu_xmlids` 包含 `menu_sc_project_initiation`，实际不包含。
- 说明项目负责人角色面缺少“项目发起/立项”入口，这是真实导航缺口，不是配置数量问题。
