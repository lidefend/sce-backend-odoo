# 系统页面基线独立审查与交付准备

日期：2026-09-09

状态：独立复审与 `verify.frontend.release.local` 待最终文档候选冻结后执行

原始基线：`3d3975b3d45c1462677df0abcbb5708e4b53e0b1`

实现方阶段报告 HEAD：`30b5febb6fd1a19de598ac34a28375e43a5f6352`

独立审查修正产品候选：`dc6e81d683e48d101cf9ec76e00f58a59a9a2811`

## 1. 审查结论与范围

首次独立审查结论为 `REQUEST_CHANGES`，没有 S0，但存在三类 S1：配置工作台层级归属错误；XML stub 与失败 mock 的证明边界不可信；直接异常路由和根 overflow 断言不足以证明真实权限拒绝及顶栏/浮层自身不越界。修正严格限定为：

- P0：`AppShell.css` 的窄屏顶栏动作容纳，不改变导航 authority、页面身份或业务动作。
- P3：配置工作台仍使用既有实现；本轮只修正文档归属，没有写配置数据。
- P4：回滚失败 fake 调用真实 production seam；浏览器报告记录完整输入、加载完成选择器、顶栏子动作边界及实际路由 authority 拒绝。
- P4：补充全量 scope manifest、artifact SHA-256 清单和 PR 草稿。

没有 P1/P2 修改，没有新增页面、业务流程、合同语义、数据库、fixture、端口、volume 或验证入口。产品候选相对原始基线为 82 路径；加入 4 个最终交付文档后，交付 HEAD 的完整范围为 86 路径，归属及逐路径回退见 `frontend_system_page_baseline_scope_manifest_20260909.csv`。

## 2. 验证可信度

stdlib XML stub 仅用于宿主机缺少 lxml 时加载隔离单元测试，不视为真实运行环境恢复，也不声称与 lxml 等价。它没有覆盖产品 XML parser 的全部失败语义。

修正候选执行了两个受管、非零的真实 Odoo tagged 测试：

- `make local.dev.test MODULE=smart_core TEST_TAGS=runtime_view_contract`：4 post-tests，统计 6 tests，0 failed / 0 errors；覆盖真实 ORM、运行时契约再校验与 fail-closed。
- `make local.dev.test MODULE=smart_core TEST_TAGS=business_config_change_set`：15 post-tests，统计 17 tests，0 failed / 0 errors；覆盖真实 ORM、解析器、配置变更集生命周期和回滚。

隔离回滚失败测试的 fake 现实现 `restore_published_version()`，抛出受控 `RuntimeError`，并断言 seam 确实被调用；不再因缺失方法产生 `AttributeError` 而误通过。

## 3. 独立页面证据

修正候选 `dc6e81d6…` 在受管 5176 服务、`sc_dev_demo`、`sc_test_admin` 会话执行两套完整矩阵：

| 矩阵 | 页面类型 | 结果 |
| --- | --- | --- |
| 1088 桌面 + 390 移动，明色 | 首页、工作列表、付款集合/详情、层级工作区、配置工作台、authority denied、404 | PASS；mutation 0；errors/failures 为空 |
| 1440 桌面 + 320 移动，暗色 | 同上 | PASS；mutation 0；errors/failures 为空 |

关键独立断言：

- 每个页面记录具体 `expectedLoadedSelector`、可见数量与 PASS，加载/错误/空态不能替代预期完成表面。
- 320/390 顶栏检查 `.topbar-actions` 及每个可见直接子动作；动作同时位于外壳与视口内，`horizontalClipped=false`。
- 层级 drawer 覆盖初开、Escape 关闭并恢复焦点、重开、打开态 320↔390 切换；panel、surface、标题、关闭按钮、树节点均在视口内。
- 未授权 action `/a/999999?menu_id=999999` 经现有 router authority 进入 `/access-denied`，并核对 `from` 与 `NAVIGATION_AUTHORITY_DENIED` 后返回首页。该证据不是后端 HTTP 403 或多角色授权证明。
- 配置工作台真实空 changeset、60→0→60、真实对象选择与状态口径继续通过；付款记录 15 的 `¥50.00` 保持冻结。

证据目录：

- `artifacts/playwright/frontend-system-baseline-review-light-1088-390/`
- `artifacts/playwright/frontend-system-baseline-review-dark-1440-320/`

目录位于仓库外 artifact authority，通过 `frontend_system_page_baseline_evidence_manifest_20260909.csv` 的逐文件 SHA-256 与产品候选、完整输入绑定。

## 4. 门禁与交付判定

修正前置静态门禁均已通过：`verify.business_config.unit`、`verify.frontend.page_identity`、`verify.frontend.style_system.guard`、候选脚本 9 个单测、Node 语法和 `git diff --check`。本文件冻结后由独立审查者对同一交付候选复审；只有复审无 S0-S2，才运行受管 `verify.frontend.release.local`。

本文件不预写 release PASS。最终命令结果必须绑定运行时的完整 HEAD，且执行后工作区保持干净；远程推送、PR 创建、合并和发布不在授权内。

## 5. 已知限制与回退

- 浏览器角色仅 system administrator；未扩大为多角色、登录旅程或配置写权限验收。
- 真实数据库只证明 empty changeset；其他展示状态由非零单元覆盖，未发布或回滚配置。
- 受控 503 沿用原产品候选证据；本次修正未触及读取恢复逻辑。
- 性能、独立移动端及 fallback 页面能力不在本阶段。
- build large chunk warning 仍存在，没有性能量化结论。

回退先按 formal layer 和文件执行：P0 顶栏修正可回退 `5d9e994b`；P4 fake 与验证器可分别回退 `e3e134c0`、`dc6e81d6`；历史混合提交依全量 manifest 的路径与 commit 列回退。不得用回退测试载体掩盖产品缺陷。
