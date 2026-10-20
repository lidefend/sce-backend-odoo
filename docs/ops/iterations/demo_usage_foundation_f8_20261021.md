# Demo 用户使用基础数据迭代 · F8 批次记录（2026-10-21）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F7 提交：`d500158f171c4fcda02dd9b69ebe3f5c02a0d762`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（active）
- Runtime：`sc-local-dev`（db=sc_dev_demo，nginx 18081）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling / 浏览器验收）
- Layer Target：`scripts/verify/user_entry_delivery_browser_acceptance.js`（Playwright 多角色浏览器验收）
- Why Here：浏览器验收只消费发布面与契约，不承载产品语义
- Why Not Elsewhere：不重排前端 dist、不改前端登录契约

## 3. 本批单一目标

业务全功能账号 + 关键角色的浏览器验收：首屏非空、下一步明确、无技术词/错误码/空壳卡、
页面证据与 API/ORM 回读一致。

## 4. 工具修正（已提交）

- `DEFAULT_PASSWORD` 从 `'demo'` 校正为 `'123456'`（对齐所有者 2026-10-21 demo 口令）；
- 新增 `business_full`（demo_full）角色条目，`direct_business` 模式，目标
  `/s/projects.list`，预期文本 `/项目列表/`。

## 5. 运行结果与阻断

`make verify.user.entry.delivery.browser_acceptance` 对 6 个角色条目全部失败：
登录页 `input[autocomplete="username"]` 30s 超时，console 报
`Failed to load resource: the server responded with a status of 409 (Conflict)`。

- 分类：environment_defect（前端 dist 与后端契约不匹配 / 前端资源 409）
- 影响：浏览器验收无法登录进入首屏；HTTP 层登录/system.init 已由 F2 验收通过，
  说明后端契约正常，问题在前端 dist 服务
- 处置：登记阻断 DUF-07；不在 demo 层重建/重排前端 dist

## 6. 验证结果

| 命令 | 状态 | 层 | 说明 |
|---|---|---|---|
| `make verify.user.entry.delivery.browser_acceptance` | blocked | L4 | 6/6 角色登录页 409 Conflict；工具修正（口令/business_full）已就位 |

## 7. 回滚

撤销 `user_entry_delivery_browser_acceptance.js` 的口令与角色条目改动即可。

## 8. 下一步精确动作

修 owning layer 的前端 dist 服务（重建/刷新 18081 所服务的 dist 与后端契约一致），
再跑 `verify.user.entry.delivery.browser_acceptance`；随后以业务日历规则收口 DUF-04。
