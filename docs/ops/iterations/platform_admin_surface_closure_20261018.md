# 平台管理员可见面、职责文案与入口会话隔离收口（2026-10-18）

## 身份

- 分支：`fix/platform-admin-surface-closure-20261018`
- 基线：`fedb92e0e3aaf7e4ccd4c6e1cac28f422ab015f2`
- 范围：平台管理员可见面、命名空间登记标签、数据库治理映射、发布运营读模型、入口 cookie 作用域。

## 变更

- 平台职责面板改用项目官方 `ScTable` 渲染，职责名称与状态使用后端下发的中文标签，不再显示 `platform.*` 能力串。
- 命名空间登记列表改为 `namespace_id/display_name/primary_alias/lifecycle_state/audience`，物理数据库名只保留为内部绑定，不再进入列表。
- 维护访问列表改为中文 `access_label`，不再显示 `MA-sc_` 维护记录主键。
- 数据库治理补充生命周期、数据用途、维护能力与维护状态的中文映射。
- 发布运营读模型英文文案中文化；平台内核没有业务页面时按 `not_configured/未配置` 渲染，不再判为阻断。
- 平台命名空间种子与管理控制台名称中文化，并新增 `17.0.1.1.17` 后迁移，使已有数据库同步更新。
- nginx 入口按 `$sc_entry_cookie_path` 设置 `proxy_cookie_path`：平台入口为 `/platform-admin/`，租户入口为 `/t/<alias>/`，隔离两个职责的会话 cookie。
- 入口静态守卫新增 cookie 路径隔离断言。

## 验证

| 入口 | 结果 |
|---|---|
| `test_platform_admin_duty_contract.py` | PASS，26 项 |
| `test_release_operator_surface_copy_backend.py` | PASS，7 项 |
| `test_platform_company_access_manifest_guard.py` | PASS，7 项 |
| `make -s verify.daily.runtime.entry` | PASS，28 项 + 静态守卫 |
| `test_platform_company_access_manifest_guard.py` | PASS，7 项；独立 guard 脚本在未改动的 `pack_controller.py` 与 `scene_orchestration.py` 上暴露基线既有失败，本批不处理 |
| `pnpm -C apps/web typecheck` | PASS |
| `eslint PlatformDutyPanel.vue ReleaseOperatorView.vue` | PASS |
| `make -s verify.agent.ledger.unit` | PASS，18 项 + 台账守卫 |
| `make -s ci.local.iteration` | PASS，四份定向回执全部 reusable |

## 边界

- 本批不改变平台控制库与租户库的认证边界；平台库不代验租户密码、不代发租户身份。
- 本批不处理客户租户运行身份漂移；客户租户部署继续暂停。
- 入口 cookie 隔离不等于登录后双身份隔离验收；后者仍按独立场景验证。
