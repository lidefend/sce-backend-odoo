# Daily Dev User-Level Acceptance（日常开发服务器用户级交付验收，2026-10-05）

Run: `.agent/runs/DAILY-DEV-USER-LEVEL-ACCEPTANCE/run.json`
Branch: `codex/daily-dev-user-acceptance-20261005`
Baseline: `4ba044e037a7bf2c3d737eaec94ea891fc602581` (`main`，PR #572 后)
Date: 2026-10-05
Runtime repository: `sc-root:/opt/projects/repos/sce-product-odoo`
(`ENV=dev`, `ENV_FILE=.env.dev`, `DB_NAME=sc_demo`)
Owner acceptance entry: `http://1.95.85.92:18081/`（自定义前端），口令 `wutao/123456`

## 1. 目标与责任层

- **Formal Product Layer**：P4（ops delivery / 运行态验收工具）+ P0（验收暴露出的 `smart_core` 契约/权限机制缺陷）。
- **Layer Target**：日常开发运行态（sc-root）主线提升 + 用户视角产品交付验收；`smart_core` 意图菜单权限投影。
- **Module**：`.agent`、`docs/ops/iterations`、`frontend/apps/web/scripts`（P4 只读走查/模板验收工具）、`addons/smart_core/security`（P0 菜单可见性投影）。
- **Standard vs User-Specific**：P0 修复是平台机制（通用菜单可见性语义），无行业/客户语义；P4 是运维交付工具。
- **Why Here**：把权威 `main` 精确 SHA 提升到日常运行态并以真实用户无死角验证，属交付验收层；验收暴露的通用权限投影缺陷归 `smart_core`。
- **Why Not Elsewhere**：不改 P1 行业语义、P2 客户偏好/数据基线、P3 运行配置；不放宽 ACL/字段权限/记录规则；不为单一模型（account/付款）加特判。
- **Blast Radius**：sc-root 日常运行仓、其前端静态产物与 dev compose profile、`sc_demo` 的 wutao 验收数据与口令；不改隔离验收库、`sc-local-*`、生产租户、通用登录默认。带 `menu_id` 的意图门禁改为消费**发布路由授权面**（与 `system_init` 同一有效策略权威），不再用原生菜单可见性或祖先组；菜单配置意图保留自身访问/范围校验。动作组与模型 ACL/记录规则校验不变。

## 2. 状态（四层分列）

- **批次验收**：进行中。部署与夹具车道 PASS；1440/light 全路由走查 90/90 通过，暴露 1 个真实产品缺陷（会计科目表 403），已定位根因并修复（待部署复验）。
- **主线集成**：main=`4ba044e0`（PR #572 已合并）；本分支修复待 PR。
- **版本发布**：未主张。
- **产品交付**：未主张（待修复部署后完成模板/视口/主题无死角验收与独立复核）。

### 部署与夹具（已 PASS）

- served SHA：`8a77c237` → `4ba044e0`；`/api/runtime-version` 回读 `git_sha=4ba044e0…`,
  `database=sc_demo`, `environment=dev`。
- `make mod.upgrade MODULE=smart_construction_core` PASS；`make verify.frontend.build` PASS；
  `make restart` PASS。
- 夹具三入口 PASS：`ensure`（carrier=installed, finance_uid=210）→
  `resolve`（expected_sha=4ba044e0）→ `readonly.probe`（runtime_identity/login/contract 11/11,
  `errors=[]`）。
- `sc_demo` 备份：`sc-root:/opt/projects/backups/20261005T023211-pre-user-acceptance-sc_demo/sc_demo.pgdump`。

## 3. 执行记录

### 3.1 全路由只读走查（sc-root, 1440×1000, light）

- 工具：`frontend/apps/web/scripts/user_page_visual_coverage.cjs`（修复 `init.navigation.nav` 读取 bug；
  新增 HTTP≥400 捕获、横向溢出、console error 统计）。
- 结果：`totalDiscovered=90, actionOk=90, actionFailed=0; formsScanned=54, formFailed=0,
  formSkipped=35(no records); overflow=0; requestFailure=0`。
- 唯一失败：`会计账务中心 / 会计科目表`，3 处 403（`ui.contract.v2 op=action_open` 与 `op=model`）。

### 3.2 会计科目表 403 根因（P0，已修复）

事实（sc-root 实测）：

- `ui.contract.v2 op=action_open action_id=291` → **200**；加 `menu_id=182` → **403
  `PERMISSION_DENIED 用户无权访问菜单 会计科目表`**。
- wutao 的 `system.init` 导航**包含** menu 182 / action 291；`route_authority.primary_actions`
  授权该路由（`allowed_operation=read`）；role surface 无 denied 项。
- `ir.ui.menu._visible_menu_ids()` 含 182；`account.account` 读权限完整（47/47）。
- 缺陷在 `addons/smart_core/security/intent_permission.py::_menu_visible_for_user`：其祖先链要求
  **每个父菜单的 groups 都必须与用户组相交**，与 `docs/product/formal_product_boundary_v1.md`
  （父级即使隐藏，只要存在可见子菜单仍须作为运行态承载菜单显示）和
  `docs/security/SC_Permission_Blueprint.md`（禁止用菜单可见性代替权限控制）冲突。父级「会计」
  需要 `account.group_account_manager`，wutao 只读组没有，故被子菜单连带拒绝。

### 3.3 权威源裁决：发布路由授权面，而不是原生菜单可见性

事实（sc-root / sc_demo 实测，`docs/product/menu_configuration_runtime_boundary_v1.md` §1 与
`.agent/decisions/contract-first.yaml` ARCH-DECISION-001 为判据）：

- 产品策略**收录**该菜单：`config/product_menu_release_manifest_v2.json` 中「会计账务中心」锁定一级、
  `maturity: GA`、`default_visible: true`，二级「会计科目」`RELEASED`，scope 含「会计科目表」。
- 产品自身运行态发布导航（`FinalMenuNavigationService` → DeliveryEngine）对 wutao 输出 menu 182
  「会计科目表」（action 291，`/a/291?menu_id=182`），共 110 个 flat 节点。
- 发布授权面 `route_authority`（`MenuService.build_route_authority` +
  `filter_route_authority_by_publication`）97 对 `(menu_id, action_id)`；`(182,291)` 位于
  `primary_actions`，`allowed_operation=read`、`required_capability=menu_action_read`；
  `denied_actions` 无 291。
- 无管理员隐藏意图：`ui.menu.config.policy` 对 181/182 无记录；platform release gate 未 `fail_closed`。
- 原生可见性远宽于发布：wutao 的 `ir.ui.menu._visible_menu_ids()` = 532，其中 344 个 act_window 菜单
  **未发布**（如 `设置/技术/操作/窗口动作`、`设置/技术/参数/系统参数`）。
- ARCH-DECISION-001：发布与入口契约须共享同一有效策略权威；动作声明/原生菜单存在不构成发布授权；
  `handlers/system_init.py` 亦声明「一个导航契约同时拥有渲染树和它的 route authority」。

裁决：403 是缺陷（产品已发布该入口），既非产品策略隐藏也非 ACL。但门禁的正确权威是**发布路由授权面**，
不是原生 `_visible_menu_ids()`——直接用原生可见性会把放行面从 97 扩大到 341 个未发布入口，违反
ARCH-DECISION-001。

修复（supersedes 本分支先前以 canonical 可见性为权威的 `69b1ddab`）：

- 新增 `addons/smart_core/delivery/runtime_route_authority.py`：按 `system_init` 同一口径构建
  发布路由授权面（identity → product policy → release gate → delivery nav → publication filter）；
  不可得时返回 `{}` 让调用方 fail-closed。
- `intent_permission` 的 `menu_id` 校验改为消费该权威：声明里存在 `(menu_id, action_id)` 才放行；
  权威不可得即拒绝（不回落原生可见性）；`ui.menu_config.*` 配置意图保留自身访问/范围校验。
- 保留原判定方向：去掉「每个父菜单 groups 都必须相交」的祖先链（`formal_product_boundary_v1.md`
  父级承载规则），父级承载语义仍在 delivery builder 的原生事实层内生效。

验证：

- `addons/smart_core/tests/test_intent_permission_menu_visibility.py`（声明对的放行、未发布的原生可见菜单
  拒绝、容器承载、权威不可得 fail-closed、门禁消费声明）→ `make local.dev.test
  MODULE=smart_core TEST_TAGS=intent_permission_menu_visibility` **5/5 PASS**。
- `addons/smart_core/tests/test_intent_permission_operation_policy.py`（改为按发布声明消费：
  拒绝/fail-closed/配置意图豁免）→ 24/24 PASS。
- 全量 `smart_core/tests` 独立 unittest 扫描：109 通过、8 个与门禁无关的既有环境/桩失败
  （`ImportError: odoo.*`、`ir.filters unavailable` 等，均未引用被改门禁，已核对不受影响）。
- 先前记录的语言标签失败 `test_explicit_form_view_preserves_mixed_text_and_field_order`
  (`'电话' != 'Phone'`) 与本改动无关（既有）。

### 3.4 门禁性能收口：进程级缓存 + 受管失效

事实：`build_runtime_route_authority` 首次构建约 180–480ms（拆解 `menu_facts`≈197ms、
`build_route_authority`≈165ms），旧 `_visible_menu_ids()`≈0ms；而门禁对**每个**已鉴权 intent 调用一次
（`controllers/intent_dispatcher.py`），是每页面的性能回退，必须在集成前收口。

修复（P0 平台机制，不用模型特判）：

- `ScProductPolicy.published_route_authority` 以 Odoo `tools.ormcache`（默认缓存桶）按
  `(dbname, uid, company_id, 有效组指纹)` 进程级缓存发布权威；
  `delivery/runtime_route_authority.py::build_runtime_route_authority` 成为该缓存入口（内部
  `_build_runtime_route_authority` 为纯构建，失败仍返回 `{}` fail-closed）。
- 失效链（不放宽任何断言）：菜单/动作/XMLID/记录规则/用户写入由 Odoo 核心 `registry.clear_cache()`
  自动覆盖；`sc.product.policy`、`sc.edition.release.snapshot` 的 create/write/unlink 显式
  `clear_cache()`；`principal_group_signature` 覆盖本 build 不自动信号化的 implied-group 变更。

证据（sc_dev_demo，`make odoo.shell.exec` 实测）：冷 180–225ms → 热 1.0–1.1ms；
显式 `env.registry.clear_cache()` 后重回冷（186ms）再热（1.4ms），证明命中与失效链路均生效。

归属核对（`make local.dev.test MODULE=smart_core TEST_TAGS=smart_core`）：

- 带本改动：16 failed / 18 error of **416** tests。
- `git stash` 本改动后同命令：16 failed / 18 error of **414** tests。
- 失败用例集合逐条比对**完全一致**（34 项：`um_p1/p2/p3` 成本期间、分包结算状态、语言标签
  `'电话' != 'Phone'` 等）。均为 sc_dev_demo 夹具/日期漂移的**既有**失败，与本改动无关；
  本改动新增的 2 例测试全部通过。


## 4. 待办

- 修复部署后复验：1440/light 走查 0 错误；模板级验收（含写循环）；视口/主题矩阵；关联跳转往返；独立复核。
- 后续统一（已记录的重复）：`handlers/route_authority_validate.py` 与 `handlers/system_init.py` 仍内联同构的
  发布权威构建，应改为复用 `delivery/runtime_route_authority.py`；为不改动其既有 P0 契约测试，本轮未合并。
