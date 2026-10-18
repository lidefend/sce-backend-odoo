# 日常入口命名空间拒绝与平台职责官方入口收口（2026-10-18）

## 身份

- 分支：`fix/daily-entry-registry-closure-20261018`
- 基线：`5f177d4b7207022902c63a1582a9362faf4ea350`
- 范围：日常入口 nginx 路径命名空间、日常 duty 渲染绑定、平台职责契约与官方 action。

## 变更

- 入口新增已声明别名白名单：形状合法但未登记的 `/t/<alias>/` 返回 `404 NS_UNKNOWN_NAMESPACE`，不再回落到 SPA 或默认上游。
- 缺失命名空间保持 `400 NS_NAMESPACE_REQUIRED`；客户端数据库头/查询参数保持 `409 NS_DATABASE_HINT_CONFLICT`。
- 日常 duty 渲染从受管入口声明解析 `SC_DECLARED_NAMESPACE_ALIASES`，并强制内部面绑定 loopback、仅服务 nginx 可公开绑定。
- 本地 `docker-compose` 入口声明默认别名 `demo`，避免本地 `/t/demo` 因空白名单 404。
- 平台职责改为官方 surface：租户登记、维护访问、订阅实例使用官方 window action；发布运营使用已声明 SPA 路由；前端面板删除原始 JSON、手搓表格与 API 白名单。

## 验证

| 入口 | 结果 |
|---|---|
| `make -s verify.daily.runtime.entry` | PASS，28 项 + 静态守卫 PASS |
| `make -s verify.daily.runtime.database.duty` | PASS，249 项（65 身份 + 28 入口 + 156 duty） |
| `make -s verify.platform.duty.contract.unit` | PASS，Python 26 项 + Node 4 项 |
| `make -s verify.frontend.typecheck.strict` | PASS，两段 `vue-tsc` |
| `make -s verify.tenant.product_payload_boundary` | PASS，10 + 11 项，通用租户协议 PASS |
| `make -s ci.local.iteration` | PASS，四份定向回执全部 reusable |
| `git diff --check` | PASS |

回执位于 `.runtime/agent-runs/DAILY-ENTRY-REGISTRY-CLOSURE-20261018/`；本地回执不是远端 CI，也不是合并授权。

## 边界

- 本批不处理客户租户运行身份漂移；客户租户部署继续暂停。
- 入口验收不等于登录后双身份隔离验收；后者仍按独立场景验证。
