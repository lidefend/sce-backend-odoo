# 会话过期后的命名空间登录恢复（收口记录）

Run: `.agent/runs/SESSION-EXPIRED-NAMESPACE-RETURN-20261020/run.json`
Goal: `.agent/goals/SESSION-EXPIRED-NAMESPACE-RETURN-20261020.yaml`
交付分支: `fix/session-expired-namespace-return-20261020`
收口元数据分支: `docs/session-expired-namespace-return-closure-20261020`
交付基线: `aba882dfcfeb8e05dbcea321d4b7ba713f0b9b7f`
集成基线: `main` @ `9e2774e95aa1380d85a62c463c8853e4b077843b`
日期: 2026-10-20

## 1. 现象

登录状态过期后，页面跳到 `/login?reason=session_expired`，丢失当前入口前缀；在 `/t/demo` 或
`/platform-admin` 下重新登录时，后续请求回到根入口，无法按当前职责认证，表现为“路由不对、
登录不了”。

## 2. 根因

- `frontend/apps/web/src/app/sessionExpiredRecovery.ts` 用 `location.assign('/login?reason=session_expired')`
  直接跳转，绕过 `createWebHistory` 的入口基路径。
- 同一处把包含基路径的 `window.location.pathname` 存入返回路径，登录后 router 再次拼接基路径，
  形成二次前缀（`/t/demo/t/demo/...`）。
- `frontend/apps/web/src/app/suggested_action/runtime.ts` 的登录与产品跳转同样直接写根路径，
  属于同一机制缺陷。

这是前端入口命名空间丢失缺陷，不是 Odoo 认证或命名空间解析故障。

## 3. 修复

| 层 | 改动 |
| --- | --- |
| `services/entryNamespace.ts` | 新增 `stripEntryBasePath`，与既有 `entryScopedPath` 配对，作为唯一入口作用域工具 |
| `app/sessionExpiredRecovery.ts` | 过期跳转改为 `entryScopedPath('/login?reason=session_expired')`；返回路径先剥离基路径再存储 |
| `app/sessionExpiredRecovery.ts` | 读取返回路径时再次剥离当前基路径，兼容旧会话遗留的带前缀值 |
| `app/suggested_action/runtime.ts` | 所有内部跳转统一消费 `entryScopedPath`，不再直接写根路径 |
| 守卫 | `frontend_system_state_recovery_guard.py` 要求存在 entry-scoped 登录跳转，防止回归 |
| 浏览器验收 | `frontend_delivery_hardening_browser.mjs`、`local_dev_candidate_visual_smoke.mjs` 改为按当前入口计算 `/t/<alias>/login`、`/platform-admin/login` 与入口相对返回路径 |

边界：不修改认证协议、token 签发、服务端命名空间解析或数据库选择；只在既有入口契约内修正客户端跳转与返回路径。

## 4. 批次验收

| 目标 | 结果 |
| --- | --- |
| `verify.frontend.system_state_recovery.unit` | PASS（47 条断言 + 6 项 Python 测试 + 守卫） |
| `verify.frontend.suggested_action.runtime_guard` | PASS |
| `verify.frontend.delivery_hardening.guard` | PASS（28 项守卫单测） |
| `verify.frontend.typecheck.strict` | PASS |
| `verify.frontend.build` | PASS（`/tmp` 临时构建环境文件，未写入仓库；产物不含物理数据库名） |
| `verify.frontend.component_driver_takeover.unit` | PASS（前端源变更导致输入摘要更新，13 项测试） |
| `ci.local.iteration` | PASS（dirty 迭代态，L1） |

用例覆盖：租户入口、平台入口、旧返回路径兼容、递归登录（登录页再次过期）。

## 5. 主线集成

| 项 | 值 |
| --- | --- |
| PR | https://github.com/lidefend/sce-backend-odoo/pull/696 |
| 合并方式 | squash |
| 合并 SHA | `9e2774e95aa1380d85a62c463c8853e4b077843b` |
| 合并时间 | 2026-10-19T22:37:32Z |
| 合并树 | 与冻结候选树完全一致 |
| 必需 CI | `frontend_release_gate`、`professional_quality_checks`、`professional_quality_gate`、`public_guard`、`merge_policy_gate`、`release_candidate_gate`、`python310_runtime_compatibility` 全部通过 |

## 6. 日常开发服务器部署

服务器 `sc-root`，源码目录 `/opt/projects/repos/sce-product-odoo`。

| 项 | 值 |
| --- | --- |
| 部署前 SHA | `80aae6f5537c2babc12c333e6041d6e20236e865` |
| 部署后 SHA | `9e2774e95aa1380d85a62c463c8853e4b077843b` |
| 前端构建指纹 | `7e1232929056743641c46eeed185099517da2541deeba73776cbfd1d0e68e0ed` |
| 前端交付方式 | 仅静态构建，未放入 Odoo 镜像 |
| 刷新职责 | `demo`、`platform_control` |
| duty declaration digest | `40238c6c254e7c1bf49f2430db48e1ae29147c8e9f2c00e259e9f6305bf93b8e` |
| entry digest | `ab1845b2ee503a9b79e24967e0a0102473f9a61c5b23b439a68364620a2b6589` |

受管入口（按序执行，均 PASS）：

1. `make daily.runtime.candidate.bundle_sync`
2. `make daily.runtime.frontend.build`
3. `make daily.runtime.database.duty.refresh`
4. `make daily.runtime.entry.verify`

部署后回读（`make daily.runtime.entry.verify` = PASS）：

- `/t/demo/api/runtime-version`：`9e2774e9…`，`sc_demo`，指纹 `7e123292…`
- `/platform-admin/api/runtime-version`：`9e2774e9…`，`sc_platform_control`，指纹 `7e123292…`
- 公网发布端口仅 `18081`（`sc-demo-dev-nginx-1`）；`18082`、`8070`、`18083` 仅回环
- 根路径 `/` 返回 308 → `/t/demo/`，不静默选库
- 未声明命名空间：`NS_UNKNOWN_NAMESPACE` 404；根路径 API：`NS_NAMESPACE_REQUIRED` 400；数据库提示冲突：`NS_DATABASE_HINT_CONFLICT` 409
- 登录 Cookie 分别限定 `Path=/t/demo/` 与 `Path=/platform-admin/`

回执：`.runtime/final-acceptance/daily-deployed/{candidate-bundle-sync,frontend-build,database-duty-refresh,entry-verify}.json`
（`.runtime` 被 Git 忽略，不随本记录提交。）

## 7. 实机浏览器回归（租户入口）

真实浏览器，`/t/demo`，账号 `admin`：

| 步骤 | 结果 |
| --- | --- |
| 登录页 | `http://1.95.85.92:18081/t/demo/login` 200 |
| 起始页 | `/t/demo/my-work` |
| 注入 401 `SESSION_EXPIRED` | 跳转 `/t/demo/login?reason=session_expired` |
| 返回路径 | `/my-work`（无入口前缀重复） |
| 过期提示 | 可见 |
| 重新登录 | HTTP 200 |
| 恢复落点 | `/t/demo/my-work` |
| 登录后返回路径 | 已清空 |
| 页面错误 | 无 |

回执：`.runtime/final-acceptance/daily-deployed/session-expired-namespace-return-9e2774e.json`，`pass=true`。

## 8. 平台入口过期重登录（补齐）

平台管理员账号 `admin`：按所有者口径使用简单默认口令，后续由所有者自行修改维护；本文档不保存口令。原库内口令与约定不一致，已通过 Odoo ORM（`res.users` 口令字段）重置，未使用 SQL 直写，未改动模块或视图。

真实浏览器，`/platform-admin`：

| 步骤 | 结果 |
| --- | --- |
| 登录 | 200，落在 `/platform-admin/?platform_admin=1` |
| 起始页 | `/platform-admin/?platform_admin=1` |
| 注入 401 `SESSION_EXPIRED` | 跳转 `/platform-admin/login?reason=session_expired` |
| 返回路径 | `/?platform_admin=1`（入口相对路径，无前缀重复） |
| 过期提示 | 可见 |
| 重新登录 | 200 |
| 恢复落点 | `/platform-admin/?platform_admin=1` |
| 登录后返回路径 | 已清空 |
| 会话 Cookie | `session_id`，`HttpOnly`，`Path=/platform-admin/` |
| 页面错误 | 无 |

回执：`.runtime/final-acceptance/daily-deployed/session-expired-namespace-return-platform-9e2774e.json`，`pass=true`。

## 9. 双入口同名账号会话隔离

同一浏览器、两个标签页，两侧登录名同为 `admin`：

| 断言 | 结果 |
| --- | --- |
| 平台登录后，租户入口未登录 | `/t/demo/login?redirect=/my-work`，未接管平台会话 |
| 租户登录（`123456`）后平台标签页仍有效 | 仍为 `/platform-admin/?platform_admin=1`，未被踢回登录 |
| 平台登录期间租户会话仍有效 | `/t/demo/my-work` 正常，未被平台会话覆盖 |
| 两侧页面错误 | 无 |

回执：`.runtime/final-acceptance/daily-deployed/dual-entry-session-isolation-9e2774e.json`，`pass=true`。

## 10. 未覆盖范围

- 未执行生产环境发布；本轮只覆盖日常开发服务器。
- 平台管理员口令目前只存在于目标库内，没有声明式初始化来源：若平台库被重建，口令需要重新设定。这是已登记的缺口，未在本轮扩大改造范围。
