# 会话过期后的命名空间登录恢复

身份：fix/session-expired-namespace-return-20261020 @ aba882dfcfeb8e05dbcea321d4b7ba713f0b9b7f + 本批 owned dirty scope。

## 现象

登录状态过期后，页面跳到 `/login?reason=session_expired`，丢失当前入口前缀；在 `/t/demo` 或 `/platform-admin` 下重新登录时，后续请求回到根入口，无法按当前职责认证，表现为路由错误、登录不了。

## 根因

`sessionExpiredRecovery.ts` 用 `location.assign('/login?reason=session_expired')` 直接跳转，绕过 `createWebHistory` 的入口基路径；同时把包含基路径的 `window.location.pathname` 存入返回路径，登录后经 router 再次拼接基路径，形成二次前缀。

`suggested_action/runtime.ts` 的登录/产品跳转也使用 `window.location.href` 直接写根路径，属于同一机制缺陷。

## 修复

- 在 `services/entryNamespace.ts` 提供统一的 `stripEntryBasePath`，与既有 `entryScopedPath` 配对。
- 过期恢复按当前 pathname 解析入口基路径：跳转到 `entryScopedPath('/login?reason=session_expired')`，返回路径先剥离基路径再存储。
- 安全返回路径兼容旧值：读取时再次剥离当前基路径，避免旧会话遗留值造成二次前缀。
- 建议动作的所有内部跳转统一消费 `entryScopedPath`，不再直接写根路径。
- 守卫改为要求存在 entry-scoped 登录跳转，防止回归。

## 边界

不修改认证协议、token 签发、服务端命名空间解析或数据库选择；只在既有入口契约内修正客户端跳转与返回路径。

## 验证

- `make verify.frontend.system_state_recovery.unit`：PASS（47 条断言、6 项 Python 测试、守卫 PASS）。
- `make verify.frontend.suggested_action.runtime_guard`：PASS。
- `make verify.frontend.delivery_hardening.guard`：PASS；28 项守卫单测 PASS。
- `make verify.frontend.typecheck.strict`：PASS。
- `make verify.frontend.build`：PASS（使用 `/tmp` 最小构建环境文件，未写入仓库；产物未包含物理数据库名）。
- `make ci.local.iteration`：PASS（dirty 迭代态，L1 only；定向 L2 由上述非零目标覆盖）。

浏览器验收断言同步改为按当前入口计算：租户入口期望 `/t/<alias>/login`，平台入口期望 `/platform-admin/login`；会话过期返回路径按入口相对路径断言，并覆盖旧值二次剥离。`local_dev_candidate_visual_smoke.mjs` 的会话恢复与安全返回断言同样改为入口作用域。

浏览器用例本身尚未在 `/t/demo` 目标环境执行，列为部署后验收项。
