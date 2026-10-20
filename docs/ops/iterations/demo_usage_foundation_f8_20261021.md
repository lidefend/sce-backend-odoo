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

## 5. 运行结果与发现

定位并解决两个浏览器侧问题（DUF-07 / 缺口 #16）：

- 登录页带客户端 `?db=` 提示被前端拒绝为 409 `NS_DATABASE_HINT_CONFLICT`：去掉 `?db=`；
- 浏览器未走 `/t/demo/` 命名空间导致 `NS_NAMESPACE_REQUIRED`：`FRONTEND_URL` 默认改走
  `/t/demo`，并对 `targetPath` 断言做命名空间前缀归一化；
- 同时校正默认口令 `'demo'` → `'123456'`，并新增 `business_full`（demo_full）角色条目。

重跑结果：6 个角色条目中 4 个通过——`pm`、`pm_my_work_menu`、`finance`、
`business_full`（demo_full 首页非空：待我处理 34 + 付款申请卡片 + 常用入口）。

剩余两个发现：

- `executive`（管理层）首页报「菜单树为空，请尝试刷新初始化」：产品层导航面问题
  （管理层仅 1 个交付入口），登记缺口 #17；
- `pm_my_work_back_home` 的「返回角色首页」按钮已不存在（my-work 页按钮变为「刷新」），
  该点击链断言过时，属 F8 遗留的脚本口径修正项。

## 6. 验证结果

| 命令 | 状态 | 层 | 说明 |
|---|---|---|---|
| `make verify.user.entry.delivery.browser_acceptance` | partial | L4 | 6 条目 4 通过；business_full 首页非空；executive 菜单树为空（#17） |

## 7. 回滚

撤销 `user_entry_delivery_browser_acceptance.js` 的口令与角色条目改动即可。

## 8. 下一步精确动作

修 owning layer 的管理层导航面（#17），修正 my-work 返回首页脚本断言，再跑完整
浏览器验收；随后以业务日历规则收口 DUF-04（2025 日期 / 50-100 样例金额）。
