# 288 · P4 Nginx Namespace Isolation

## 渲染变更

- 根路径重定向由硬编码 `/t/demo/` 参数化为 `/t/${SC_PROXY_DEFAULT_NAMESPACE}/`。
- clean 环境注入 `SC_PROXY_DEFAULT_NAMESPACE=clean`。
- clean 环境注入 `SC_DECLARED_NAMESPACE_ALIASES=clean`。
- `NGINX_ENVSUBST_FILTER` 增加 `SC_PROXY_DEFAULT_NAMESPACE`。

## 验证

| 请求 | 结果 |
| --- | --- |
| `GET /` | 308 → `/t/clean/` |
| `GET /t/clean/api/runtime-version` | 200，`database=sc_clean`，`namespace_alias=clean` |
| `GET /t/demo/api/runtime-version` | 404 `NS_UNKNOWN_NAMESPACE` |
| 白名单渲染 | `~^(clean)$` |

`demo` 在 clean 入口不再是可路由命名空间，不存在静默回退。
