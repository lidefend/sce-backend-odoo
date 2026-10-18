# 日常入口会话 Cookie 路径隔离收口（2026-10-19）

## 背景

平台命名空间 `/platform-admin` 经过两层 nginx：服务入口面把路径原样转给平台职责面，
平台职责面再剥离前缀后转给平台 Odoo。两层都执行了 `proxy_cookie_path / <namespace>/`，
浏览器收到的会话 Cookie 变成 `Path=/platform-admin/platform-admin/`，该路径没有路由，
平台原始 Odoo 登录页无法复用会话。

同时，入口刷新只执行 `docker compose up -d`，模板虽由容器启动脚本渲染，但容器未变化时
不会重建，已审阅的模板改动可能不生效。

## 修复

- 新增 `map $sc_entry_platform_strip $sc_proxy_cookie_path`：入口面（0）按请求路径设置
  Cookie 路径，平台职责面（1）保持 `/`，只由入口面改写一次。
- `start_route()` 使用 `up -d --wait --force-recreate`，刷新即重建路由容器并重新渲染模板。
- 入口验收新增：Demo 登录 Cookie 精确为 `/t/demo/`，平台登录 Cookie 精确为
  `/platform-admin/`；已渲染配置必须包含平台感知 Cookie 映射。
- 数据库提示头统一包含 `X-Odoo-Database`、`X-Odoo-DB`、`X-DB`、`X-Odoo-DB-Locked`
  与 `?db=`，nginx 与 Odoo 两层都显式拒绝；客户端伪造 `X-SC-Namespace` 不能覆盖路径命名空间。

## 验收

- `make verify.daily.runtime.entry`
- `make verify.daily.runtime.database.duty`
- `make daily.runtime.entry.verify`
- 日常服务器外部回读两个登录响应的 `Set-Cookie` 路径。
