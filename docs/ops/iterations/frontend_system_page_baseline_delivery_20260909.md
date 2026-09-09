# 系统页面基线独立审查与交付准备

日期：2026-09-09

状态：页面独立复审已通过；P1 acceptance 兼容改动已撤出；Frontend Quick 已恢复，受管整环境重建等待 destructive 授权

原始基线：`3d3975b3d45c1462677df0abcbb5708e4b53e0b1`

实现方阶段报告 HEAD：`30b5febb6fd1a19de598ac34a28375e43a5f6352`

独立审查修正产品候选：`dc6e81d683e48d101cf9ec76e00f58a59a9a2811`

## 1. 审查结论与范围

首次独立审查结论为 `REQUEST_CHANGES`，没有 S0，但存在三类 S1：配置工作台层级归属错误；XML stub 与失败 mock 的证明边界不可信；直接异常路由和根 overflow 断言不足以证明真实权限拒绝及顶栏/浮层自身不越界。修正严格限定为：

- P0：`AppShell.css` 的窄屏顶栏动作容纳，不改变导航 authority、页面身份或业务动作。
- P3：配置工作台仍使用既有实现；本轮只修正文档归属，没有写配置数据。
- P4：回滚失败 fake 调用真实 production seam；浏览器报告记录完整输入、加载完成选择器、顶栏子动作边界及实际路由 authority 拒绝。
- P4：补充全量 scope manifest、artifact SHA-256 清单和 PR 草稿。

没有 P1/P2 修改，没有新增页面、业务流程、合同语义、数据库、fixture、端口或 volume。页面实现阶段没有另造验证入口；本次独立 P4 环境任务只增加了所选恢复路径缺失的受管 audit、dry-run/apply 和非零测试入口。首次正式 release gate 在持久化 `sc_frontend_acceptance` 上暴露的付款历史兼容问题曾被实现为 `.163/.164` 迁移和资金基线 fixture 修订；后续范围审计确认，旧人工 fixture 升级失败不能单独证明客户历史兼容需求，因此这些改动已通过后续可审计提交撤出当前前端候选。其历史提交和数据库执行事实仍保留，不改写历史。

当前候选继续以原始基线为范围 authority；页面产品范围不再扩大。本批只增加 P4 受管恢复入口、测试和文档，并刷新已有生成清单；归属及逐路径回退见 `frontend_system_page_baseline_scope_manifest_20260909.csv`。

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

修正前置静态门禁均已通过：`verify.business_config.unit`、`verify.frontend.page_identity`、`verify.frontend.style_system.guard`、候选脚本 9 个单测、Node 语法和 `git diff --check`。

首次 release gate 在 frontend 静态、单元和构建通过后，于持久化 acceptance 增量升级失败。曾执行的 `.163/.164`、fixture 修订、模块升级及 snapshot 只作为已撤出候选的历史证据，不再计入当前页面候选 PASS。当前 `sc_frontend_acceptance` 已实际升级到 `17.0.0.164`，而源码候选恢复为 `17.0.0.162`，因此该运行态在受管重建前不得用于当前候选验收。

撤出前最后一次 `verify.frontend.release.local` 在 exact HEAD `016a844351aa92ddfd9a4f639a72f30ed784edfe` 上仍为 FAIL：静态、构建、受管升级、fixture、snapshot 和 25 个页面身份检查通过；`delivery_hardening` 将非 fixture 财务用户创建的 `FE-A-PR-001` 放入“我的付款申请”动作上下文，产品正确返回 403，验证器却等待普通详情工作区而超时。该结果归类为 P4 `validation_tool_defect`，不能通过放宽权限或改写业务记录消除。

当前候选已通过完整 `verify.frontend.quick.gate`。生成清单差异被证明来自上次清单生成后合法修改的 `AppShell.css`；TDesign 锁定版本、package/lock 输入未变化，通过原 `refresh.frontend.rendering_detail.inventory` 入口更新后只有 `inputDigest` 改变，全部语义统计保持一致。

P4 只读审计确认数据库为 `17.0.0.164`，而源码仍为 `17.0.0.162`；数据库、filestore、session 均精确绑定现有 profile，未发现兼容 `.162` 的完整备份。可靠性复核又发现 PostgreSQL 卷包含额外 `sc_odoo`（约 7.5 MB、0 public tables、无 Odoo registry），因此默认预检必须阻断，不能只备份主库后删除整卷。加固入口要求显式数据库全集并冷备整个 PostgreSQL 卷，逐步验证停止、备份、删除、解包与恢复结果。正式 release gate、fixture reset、snapshot 与新浏览器验收仍为 `not_run`，等待 clean 候选预演和对 `sc_odoo` 及三个精确卷的 destructive 授权。

本文件不预写 release PASS。最终命令结果必须绑定运行时的完整 HEAD，且执行后工作区保持干净；远程推送、PR 创建、合并和发布不在授权内。

## 5. 已知限制与回退

- 浏览器角色仅 system administrator；未扩大为多角色、登录旅程或配置写权限验收。
- 真实数据库只证明 empty changeset；其他展示状态由非零单元覆盖，未发布或回滚配置。
- 受控 503 沿用原产品候选证据；本次修正未触及读取恢复逻辑。
- 性能、独立移动端及 fallback 页面能力不在本阶段。
- build large chunk warning 仍存在，没有性能量化结论。
- 现有 acceptance 数据库已执行撤出候选中的 `.163/.164`，不能代表当前源码候选，也不会执行逆向数据迁移。
- 受管整环境恢复方案与预演记录于 `frontend_acceptance_fixture_namespace_rebuild_design_20260909.md`。实现与 dry-run 已完成，实际删除/覆盖未执行；通用命名空间清理不再是当前版本恢复的前置。

回退先按 formal layer 和文件执行：P0 顶栏修正可回退 `5d9e994b`；P4 fake 与验证器可分别回退 `e3e134c0`、`dc6e81d6`；历史混合提交依全量 manifest 的路径与 commit 列回退。曾执行的 P1 数据迁移不可通过代码回退逆向恢复，现有 acceptance 环境只能通过未来明确授权的受管重建重新成为当前页面候选证据。
