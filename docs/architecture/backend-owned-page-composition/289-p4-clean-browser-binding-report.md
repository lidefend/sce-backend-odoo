# 289 · P4 Clean Browser Binding Report

## HTTP 会话证据（同一次会话）

```json
{
  "namespace": {"alias": "clean", "namespace_id": "ns_c6fed472e939"},
  "database": {"runtime_version_db": "sc_clean", "auth_db": "sc_clean"},
  "user": {"login": "fixture_role_finance", "uid": 6, "is_admin": false, "is_system": false, "is_internal_user": true}
}
```

## 独立浏览器会话

```json
{
  "entry_url": "http://127.0.0.1:18083/t/clean/login?redirect=/",
  "clean_prefix": true,
  "login_input_count": 2,
  "after_login_url": "http://127.0.0.1:18083/t/clean/",
  "console_errors": []
}
```

浏览器未复用 acceptance 会话或历史登录态；登录后回到 `/t/clean/`，无控制台错误。
