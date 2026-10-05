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

- **批次验收**：进行中。部署与夹具车道 PASS；1440/light 全路由走查 90/90 通过，暴露 1 个真实产品缺陷（会计科目表 403）；根因已定案并修复，PR #573 已合并，sc-root 已部署复验（`action_open action=291 menu_id=182` 由 403 转 200）。能力权限驱动收口本地全绿（守卫 90 入口 0 违规 + 负例闭环，22+25 定向测试与 22 锁测试通过，见 §6.10），**尚未提交 / 未同步远端**。
- **主线集成**：main=`3f424993c9f378aaeedd2f26080545ad37ea3f8e`（PR #573 已合并）；四项必需检查全 pass。
- **版本发布**：未主张。
- **产品交付**：未主张（待完成模板/视口/主题无死角验收、关联往返与独立复核）。

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


### 3.5 集成与部署复验（PR #573，sc-root）

- PR #573 squash 合并到 `main=3f424993c9f378aaeedd2f26080545ad37ea3f8e`；候选 HEAD
  `025dbe15cd43f188fe8200c126a78e33c203fd60` 的 `ci.local.quick` receipt 通过；必需检查
  `public_guard`、`merge_policy_gate`、`professional_quality_gate`、`frontend_release_gate` 全 pass。
- sc-root 日常仓快进到 `3f424993`，`make mod.upgrade MODULE=smart_core` + `make restart` PASS。
- HTTP 复验（wutao，`X-Anonymous-Intent: 1`）：`action_open action=291 menu_id=182` → **200**（修复前 403）；
  无 `menu_id` 的 `action=291` → 200；负例 `menu_id=999` → 403、`action=999` → 403（无回归）。
- 发布权威面：wutao 87 pairs + 5 containers；`decision(182,291)=True`，`decision(182,999)=False`。

### 3.6 本地开发验证为何未暴露该 403（覆盖边界，非执行不勤）

在 `sc_dev_demo` 实测（`make odoo.shell.exec ENV=dev ENV_FILE=.env.dev DB_NAME=sc_dev_demo`）：

- **无同一条失败路由**：本机 menu `182` = `发票/报告/管理`、action `291` = `退款通知`(`account.move`)；
  `名称 like 科目` 为空，唯一“会计”菜单是 `194 = 发票/配置/会计`（无 action）——按 id 无法复现。
- **本地没有“发布导航”对象**：`sc.edition.release.snapshot` 计数 = 0；发布路由授权面对 uid1 与 wutao
  均 `primary_actions=0 / pairs=0`。403 的产品症状要求“已发布 GA/default_visible 入口被拒”，本地不成立。
- **缺陷类别本地存在，但无入口跑该差分**：用基线 `4ba044e0` 的祖先组交集规则重放，本机 wutao 430 个
  canonical 可见菜单中有 **84** 个会被 deny（68 个带 action），主因 `设置`(43)、`系统管理（内部）/Smart Core Admin`(11)、
  `项目 → SC 能力-行业配置管理员`(8)；admin(uid1) 204 可见中 deny **13**（10 个带 action）。
- **本地测试为声明驱动**：入口是 `make local.dev.test MODULE=smart_core TEST_TAGS=...`，harness 用合成声明
  `_authority(pairs=[(182,291)])`（`addons/smart_core/tests/test_intent_permission_menu_visibility.py:10`）断言规则本身，
  与被测代码同源假设，构造性通过。
- **修复后本地更不可验证**：新门禁消费发布权威，本机权威为空即 fail-closed；`sc_demo` 是唯一有效运行态。
- 结论：本地是 feature 迭代库，结构性缺少“已发布导航 + 真实业务角色”夹具；该缺陷是 1440/light 全路由
  走查在 sc-root 上首次以真实产品导航跑通时才暴露。可落地改进：在 sc-root 增加“发布导航 vs 门禁判定”
  一致性探针（只读，复用既有受管入口，不新建框架）。

### 3.7 「项目台账」发布面缺口（产品册有、发布未对齐；本轮修复）

**缺口（必须明确说明）**：产品册（`config/product_menu_contract_v1.json`、
`config/product_menu_release_manifest_v2.json`）把「项目台账」声明为 GA/default_visible，但运行时实际消费的发布基线
`scripts/verify/baselines/formal_business_product_menu_policy_v1.json` 的「项目中心」中**没有**该入口。
即：**产品册有的功能，发布面没有对齐**。用户登录后 `/s/projects.list?menu_id=291&action_id=506` 的
`ui.contract.v2 op=action_open` 每次复现 **403**。

**根因（两类叠加，非单一）**

1. 发布基线缺项：基线不含 `(项目台账 menu=379 / action=506)`，`published_pairs` 中无 `action 506`。
2. carrier 身份不一致：`smart_construction_scene/providers/projects_list_provider.py:19` 的
   `fallback_strategy.menu_xmlid=menu_sc_root`，经 `smart_core/core/scene_provider.py:466`
   （在 registry 升级之后执行）覆写场景声明身份，把 carrier 从声明的 `menu_sc_project_project(379)`
   改成根容器 `menu_sc_root(291)`。而 `291` 是 action-less 容器，精确 pair 判定 `(291,506)` **恒为 False**。

只读探针（sc_demo, wutao）实测：`DEC_291_506=False`、`DEC_379_506=False`、`PAIRS_506=[]`、
`291 in published_menu_ids=True` 但 `PAIRS_MENU291=[]`。
**因此“只把 379/506 发布出去”不足以消除 403**；必须同时让有效 carrier 回到声明身份。

**修复（方案 A：对齐发布面，不放宽断言、不加模型特判、不删 landing scene）**

- 发布面：`scripts/ops/promote_product_ten_center_policy.py` 增唯一绑定
  `项目中心/项目台账 → menu_sc_project_project + action_sc_project_list`（`project.project`，path 4 层）；
  重生成基线 89→**90** 与 `.sha256`（`1b7c0700…`）。
- carrier：`projects_list_provider.py` 的 `fallback_strategy.menu_xmlid` 与 `delivery_handoff.user_entry`
  对齐为 `menu_sc_project_project`。P0 机制不动（`test_scene_provider_target_identity_merge.py`
  已声明 critical scene 采信 provider 身份，故修在 provider 数据层）。

**定向验证（本地，非零）**

- 发布面 28 项：`promote_...`（幂等一致）、`test_promote_product_ten_center_policy`(4)、
  `product_menu_contract_v1_guard`(PASS)、`product_menu_release_manifest_v2_guard`(PASS 90/90)、
  `test_locked_menu_policy_contract`(18)、`baseline_policy_integrity_guard`(PASS)、
  `product_primary_center_baseline_guard`(PASS)、`test_product_menu_contract_v1_guard`(5)。
- carrier 63 项：`test_action_only_scene_semantic_supply`(59，含新增声明消费锁)、
  `test_scene_provider_target_identity_merge`(4)。
- 负例控制：把 provider 回退身份临时改回 `menu_sc_root` → 新测试 FAILED(1)；恢复后 59 OK。

**存量失败（非本轮引入，基线 HEAD 同样失败，单列不阻断）**：
`scripts/verify/formal_menu_no_legacy_carrier_guard.py` 报
`menu_sc_self_funding_advance_income/refund missing from formal product baseline`。

**待部署复验**：候选分支经受管 `daily.runtime.candidate.bundle_sync` 刷到 sc-root 后
`make mod.upgrade MODULE=smart_construction_core` + `make restart`，复验登录不再 403、
有效 pair→200、90 入口全 200、负例 403 不回归。

### 3.8 菜单入口重复的事实（待整合决策）

重复分三类，只有 scene/entry 层的「同 `(menu,action)` 多认领」是真重复：

- `scene_registry_content.py:143/152`：`projects.list` 与 `projects.ledger` 的 target **完全相同**
  （`menu_sc_project_project`+`action_sc_project_list`），名字同为「项目台账」；`projects.ledger`
  在产品册标注为**「项目台账（试点）」**（`scene_catalog_v2.md:91`）。
- `scene_registry_content.py:694`：`projects.execution` 亦声明 `menu_sc_root`+`action_sc_project_list`。
- `core_extension.py:110`：`NAV_MENU_SCENE_MAP` 同时把 `menu_sc_project_project` 与 `menu_sc_root`
  映射到 `projects.list`。
- policy 侧同一 `res_model` 多菜单（`project.project`×5、`account.move`×4、`sc.invoice.registration`×4）
  属**正常多入口**，不是整合对象。

## 4. 待办

- 修复部署后复验：1440/light 走查 0 错误；模板级验收（含写循环）；视口/主题矩阵；关联往返（须真实点击）；独立复核。
- 「项目台账」缺口（§3.7）本地已双修（发布面 90 项 + carrier 身份对齐），定向 L2 绿并含负例控制；待候选部署到
  sc-root 后复验登录不再 403、有效 pair→200、90 入口全 200、负例 403 不回归。未复验前不得宣称该缺口已关闭。
- 菜单入口整合（§3.8，待调度裁决）：`projects.ledger`（试点）与 `projects.list` 同 target、`projects.execution`
  与根容器同 target、`NAV_MENU_SCENE_MAP` 双重映射；建议作为**独立小批次**收口（`projects.ledger` 转 alias、
  不新增菜单行、不动 ACL），避免重开已通过的列表证据。
- 运行态身份缺口（已知，未关闭）：sc-root `/api/runtime-version` 仍报 `4ba044e0`，`.env.dev` 的
  `SC_SOURCE_REVISION` 未随 `daily.runtime.main.bundle_sync` 刷新，且无受管刷新入口；验收身份绑定
  sc-root git HEAD + DB + 构建产物，不以该声明 SHA 作为通过依据。
- 后续统一（已记录的重复）：`handlers/route_authority_validate.py` 与 `handlers/system_init.py` 仍内联同构的
  发布权威构建，应改为复用 `delivery/runtime_route_authority.py`；为不改动其既有 P0 契约测试，本轮未合并。
- 能力权限驱动收口（§6.10）本地全绿但**未收口**：待干净 SHA 冻结 + 独立复核 + 候选 bundle sync 后，
  在 sc-root 复验守卫 0 违规并刷新 5180 预览；可选实跑远端 `form-profiles` 范围。

## 5. 发布面同口径统一与预览边界收敛（本轮）

### 5.1 分叉点

发布面存在三份副本：产品册意图 → 仓库锁定基线 JSON → 运行时发布快照 DB。
锁定契约层已保证「策略 released == 锁定基线」，但守卫比较的是
**快照 `page_count`（released+preview 有效页）** 与 **策略 released 计数**，两侧口径不同；
同时运行时快照不随基线自动刷新。现场 `construction.preview` 的 active 快照 #31 是旧提交
`72a15338104d` 的 163 页遗留全量、且全部标记 `release_state=released`，而当前锁定基线与策略
均为 90。发布门只统计 `released`，所以这条未声明的 released 漂移既不报错也不可见。

### 5.2 统一机制（同口径比较 + 预览可声明，不放宽断言）

- `locked_menu_policy_contract` 新增 `normalized_page_release_state`、`policy_preview_rows`、
  `assert_snapshot_matches_policy_release_states`、`resolve_declared_product_keys`。
- `production_menu_release_gate_guard` 改为：快照 released ↔ 策略 released、快照声明 preview ↔
  策略 preview、有效总数与发布门三处一致；released 集合对锁定基线再断言；非有效页直接拒绝。
  预览额外页只有被策略显式声明为 `preview` 才允许 → **可控、可知道**；未知产品范围失败关闭。
- daily 车道统一为一次入口：`release.daily_product_navigation.refresh`（刷新两个产品快照）、
  `release.daily_product_navigation.converge`（刷新→重启→守卫）；`release.daily_dev.acceptance.publish`
  增加 `verify.daily_dev.product_menu_release_gate.guard` 依赖。守卫默认声明**全量产品范围**，
  显式声明替代单纯收窄。

### 5.3 现场收敛与复验（sc-root sc_demo / ENV=dev / git HEAD 9121b064）

- `release.daily_product_navigation.refresh`：standard 快照 #35、preview 快照 #36，
  各 `policy_menu_count=90 / snapshot_menu_count=90`，`locked_baseline_sha256=1b7c0700…`。
- `make restart` 后 `verify.daily_dev.product_menu_release_gate.guard`：**PASS**（standard #35 +
  preview #36；released 90 / preview 0 / gate 90；10 个正式顶层分组；契约 `exact_match=true`）。
- 失败关闭负例：`DAILY_PRODUCT_MENU_PRODUCT_KEYS=construction.bogus` → 退出码 2，
  `PRODUCT_MENU_CATALOG_PRODUCT_KEYS_INVALID`。
- 403 端到端复验（wutao）：登录落地 `/s/projects.list?menu_id=379&action_id=506`；
  POS(379,506)→200（74407B）；NEG(865,506)→403；`system.init` 导航 112 节点 / 90 个带 action / 含 379。
  早期探针 `NAV action_count=0` 系读取路径错误（导航在 `data.navigation.nav`），非导航缺失。

### 5.4 顺带修正：主线既有门禁失败（陈旧期望）

`verify.product.menu.runtime_closeout.guard` 在 main `3f424993` 与候选 `b3804cf5` 上均失败
（stash 后复现，确认与本次改动无关）。根因：PR #400 有意把
`menu_project_funding_actual_event_allocation` 发布到财务中心（`active=True`）并从
`LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS` 移除，但守卫 `HIDDEN_XMLIDS` 仍保留陈旧隐藏期望。
修正为移除该陈旧期望（不改动产品发布决定、不放宽其它断言），守卫恢复 PASS（43 条）。

### 5.5 仍未关闭

- L0 身份缺口：sc-root `/api/runtime-version` 仍报 `4ba044e0`，`.env.dev SC_SOURCE_REVISION`
  未随候选同步刷新且无受管入口；验收身份继续绑定 sc-root git HEAD + DB + 构建产物。
- 详情页 1440/390 明暗核对、真实关联往返、创建/编辑与工作台最小证据差额 —— 待下一执行单。

## 6. 详情收口（1440/390 × 明暗）+ 关系往返 + 关联目标协作投影缺陷

运行环境：日常库运行时 `http://127.0.0.1:18081`（=sc-root `http://1.95.85.92:18081`），
`sc_demo`，账号 `wutao`；真实有数据的列表入口 `/a/506?menu_id=379`
（`project.project.tree`），源记录 `project.project/581`。

### 6.1 L0 身份缺口闭合（受管入口）

`/api/runtime-version` 原先报 `4ba044e0`，与 sc-root 已部署 HEAD 不一致。新增受管入口
`scripts/ops/daily_runtime_source_revision_align.py`（+8 单测）与
`make daily.runtime.source_revision.align`（确认串
`ALIGN_DAILY_RUNTIME_SOURCE_REVISION_WITH_DEPLOYED_HEAD`）。实跑后
`git_sha=source_revision=9121b06427266e13712171e599907b4b461aefc2`，证据
`.runtime/final-acceptance/daily-deployed/source-revision-align.json`。

### 6.2 详情页实拍核对（通过）

以受管车道 `make verify.daily_dev.list_surface.readonly.browser` 的 `detail-only` 范围，
`1440/390 × light/dark` 各一次：`record_checks` 的 `declared_entry_route`、
`exact_record_contract`、`declared_renderer`、`return_to_source` 全部为真；
`driverErrorCount=0`、`detailAdopted=true`、`console_errors=[]`、`denied_requests=[]`、
`failed_responses=[]`。证据 `.runtime/final-acceptance/detail-closeout/{light,dark}.json`
与同名截图目录。

探针侧同时修掉一处**探针缺陷**（非产品缺陷）：移动端 `390` 原先用
`.collection-mobile-record-row__card` 当 opener，而卡片主体是“选择”语义，点击不导航；
改为消费声明的打开动作 `[data-semantic-action="open-record"]`（桌面仍用
`.cell-primary-link`），并新增 `LIST_SURFACE_COLOR_SCHEME=light|dark` 断言
`[data-sc-theme-resolved]` 已解析。未放宽任何断言。

### 6.3 真实关联往返（通过）

真实点击 `project.project/581` 的 `user_id` 关系按钮 → 目标
`/f/res.users/1?menu_id=438&action_id=723&return_model=project.project&return_field=user_id&return_record_id=581`
→ `goBack` 后 URL 与进入前完全一致、源记录恢复（count 1）、动作集 `before==after`。
归还契约携带 `return_model/return_field/return_record_id/return_action_id/return_menu_id`。

### 6.4 关联目标协作块“记录不存在”：真实可见缺陷（已修）

**现象**：目标页根 `data-form-model="res.users" data-state="ok"`、`data-field-fail-closed` 计数 0，
但可见红色告警 `记录不存在`（`role="alert"`）位于
`section.native-chatter-block → section.sc-native-contract-collaboration`。

**事实**：`chatter.timeline` 是 `projection_only / no_business_fact_authority` 的可重建投影，
按当前**业务/公司作用域**门控。实测同一意图：`res.users/2`、`res.partner/1`、`res.company/1`、
`project.project/581` 均 200 且有条目；`res.users/1`、`res.users/3`、`res.company/21` 均 404
（作用域外行）。`res.users` 页面契约声明 `capabilities.collaboration=true`，面板是**声明面**，
且既有契约测试明确“已保存记录始终保留协作面板”。

**根因**：前端把权威的“作用域外”答复（404 `NOT_FOUND`）灌进了**记录级错误通道**，于是在一个
已经正常渲染的记录页上打印“记录不存在”。

**修复（仅 P0 前端投影层，无模型特判、不覆盖 ACL/字段权限、不放宽断言）**：
- `professionalCollaborationModel.isCollaborationAuthorityAbsence(cause)`：识别
  `403/404` 与 `NOT_FOUND/PERMISSION_DENIED/*_SCOPE_DENIED`；系统/网络失败不匹配。
- `useNativeChatterRuntime.loadTimeline`：命中权威缺席时置 `unavailable` 并清空错误/时间线，
  不再进错误通道；成功时复位。
- `collaborationContract.nativeCollaborationUnavailableMessage` 增加
  `authorityDenied` → 中性声明态“当前记录不在所选业务范围内，暂不显示协作日志。”
  （复用既有 `unavailableMessage` 空态机制，同时自然抑制不可用的撰写入口）。

**复验**：本地 vite dev（`/api` 代理到日常后端）下，源 `project.project` 仍为 3 条时间线且无错误；
目标 `res.users/1` 变为中性态、正文不再出现“记录不存在”。单测
`professional_collaboration_model_test`（含 7 条权威缺席用例）、
`native_collaboration_presentation_test` 与 `contract_form_collaboration_authority.unit` 全绿，
`vue-tsc --noEmit` 与 `eslint` 均 0 退出。

### 6.5 关联目标残余请求（记录，不阻塞）

- `chatter.timeline res.users/1 → 404`：即 6.4 的权威作用域答复，展示层已修。
- `api.data op=read res.company ids [2,21,22,1] → 403`：调用方公司作用域外记录被拒；
  目标页未渲染公司字段、无 fail-closed 标记、无可见错误。

两者均属权威边界（**不是** 缺陷，也不据此放宽或强制覆盖），仅登记事实。

### 6.6 环境与本地清理

- 受管预览 `5180`（隔离验收前端）与在用后端 `18082` 保留（18082 有 10 条活动连接）。
- 清理本会话与更早遗留的临时监听：`5199`（本次 vite dev）、`3002/5173`（`/tmp/td-starter`
  的 mock vite）、`5175`（游离 `release_static_server` 预览）、`8443`（`/tmp/github_proxy.py`
  临时 TCP 转发）。日常运行时 `18081` 及其余受管 compose 环境未动。

### 6.7 仍未关闭

- 创建/编辑与工作台的最小证据差额（下一步执行单）。
- 容器化受管环境的批量退役仍需按既有受管入口逐项确认，不在本次擅自下线。

### 6.8 端口转发与孤儿环境清理（2026-10-05 追加）

**事实澄清**：本机不存在任何 ssh `-L/-R`、socat、autossh、kubectl port-forward、frp
进程；此前看到的"大量端口"全部是 docker 发布端口，来自历史会话／已删除工作树遗留的
compose 项目，不是转发隧道。清理后 `docker-proxy` 端口与在用发布端口完全一致
（`8070`、`18081`、`18082`、`19083`）。

**清理范围**：

- 孤儿项目（compose 工作目录已删除）：`sc-backend-odoo-test`、`sc-boundary-06-queue`、
  `sc-contract-governance-v1`、`sc-contract-lifecycle-v1`、`sc-contract-snapshot-v1`、
  `sc-fe-audit-20260805`、`sc-frontend-acceptance-e6ddae1`、`sc-nav-pro-01`、
  `sc-product-center-v1`、`sc-ten-center-clean`、`sc-tenant-rc-product`。
- 本仓库内遗留项目（`.env.local.clean`／`.env.local.sample`／`.env.prod.sim` 已不存在，
  已无受管入口）：`sc-local-clean`、`sc-local-sample`、`sc-demo-lifecycle`、
  `sc-fe-r2-p1-01`、`sc-backend-odoo-prod-sim`、`sc-personnel-test`、
  `sc-p0-decoupling`、`sc-core035-mvp-20260727044923-2dc17f`。
- 无主已退出容器 35 个。**未删除任何数据卷。**
- 保留：日常运行时 `18081`/`8070`；隔离验收 `18082`、凭证容器 `19083`、预览 `5180`。

**误伤与受管恢复（自曝）**：项目级按 label 清理时连带移除了
`sc-fe-r2-p1-01` 的 one-off 验收后端 `sc-backend-odoo-acceptance`（`18082`）。
恢复路径全部走受管入口：重建凭证容器 `sc-fe-r2-p1-01-odoo-1` →
`make acceptance.runtime.preflight` PASS → `make backend.acceptance.up` PASS →
`make backend.acceptance.health` PASS。`sc_fe_r2_p1_01_db/redis/odoo` 三卷与
`sc_frontend_acceptance` 库完好。

**两项真实发现（记录，非产品门禁）**：

1. **口令漂移**：postgres 卷内 `odoo` 角色口令与当前 `.env.dev` 声明权威不再一致
   （env 文件 mtime 晚于卷 initdb）。即清理前该车道靠"旧容器 env 与卷一致"在运行，
   下一次受管重启同样会认证失败。已按当前声明权威重置角色口令，未改数据。
2. **自举缺口**：凭证容器缺失时，本地受管验收入口
   （`acceptance.runtime.preflight`、`db.frontend.acceptance.ensure`、
   `backend.acceptance.up`、`frontend.acceptance.up`）都在 `load_profile` 前置 DENY，
   没有本地自举路径。本次以仓库自带 `compose_dev` 封装、按 profile 解析出的精确身份恢复；
   是否补自举入口属 P4 决策，本轮未擅自新增。

**非本分支**：`127.0.0.1:39083` 为其他用户（root）预存在监听，无 sudo 不可处理。

### 6.9 无关数据回收（2026-10-05 追加，所有者授权"清理无关数据"）

判据：**只删未被任何容器引用、且未被本仓库构建声明引用的对象**。命名卷删除不可逆，
已按所有者明确指令执行。

| 对象 | 清理前 | 清理后 | 说明 |
| --- | --- | --- | --- |
| 镜像 | 101 个 / 54.47GB | 4 个 / 3.656GB | 仅留 `nginx:latest`、`odoo17-odoo:latest`、`postgres:15`、`redis:7-alpine`（在用容器的镜像）；清掉约 89 个未引用镜像，主体是其他分支的 `ghcr.io/lidefend/sce-product` 发布快照（`1.0.0-rc.18~20`、`candidate-*`、`sha-*`） |
| 构建缓存 | 39.19GB | 659MB | `docker builder prune`，回收 37.59GB + 0.95GB |
| 数据卷 | 1423 个 / 108.4GB | 9 个 / 4.055GB | `docker volume prune -a`；回收匿名卷 8.395GB + 命名卷 96GB |
| 容器 | 95 总 / 50 运行 | 8 运行 / 8 总 | 移除最后一个停止容器 `sc-test-odoo-sc_dev_demo` |

命名卷回收 Top：`sc-production-blocker-matrix_migration-safety-db` 33.46GB、
`sc-boundary-06-queue-db` 7.11GB、`sc-boundary-06-bridge-db` 7.04GB、
`sc-production-candidate-db` 6.30GB、`sc-core035-mvp-*-db-data` 6.15GB、
`sc_local_sample_db_data` 4.98GB、`sc_dev_db_data` 及其 `_recovery_/ _corrupt_20260817`
各 4.18GB、`sc_prod_sim_db_data` 2.96GB、`sc_contract_snapshot_db_data` 1.51GB。

**保留的卷恰为在用集合**：`sc_local_dev_{db,odoo,redis}_data`、
`sc_fe_r2_p1_01_{db,odoo,redis}` 及 4 个运行容器匿名卷；清理后卷可回收量为 0B。

清理后回读：日常 `18081`、验收后端 `18082`、预览 `5180` 均可访问，8 个容器全部 healthy。

**操作要点**：`docker volume prune` 默认只清匿名卷，必须 `-a` 才清命名卷——这解释了
第一次仅回收 8.395GB、而 96GB 命名卷仍在的现象。

### 6.10 能力权限驱动收口：视图独占能力违规（2026-10-05 追加）

**架构判据（所有者确认）**：*我们的产品不应该有专门的只读页面，必须是权限契约驱动*。
落到机制上：某入口的 `create/edit/delete/duplicate` 不得由 **view arch 单独阻断**；
拒绝必须来自权限（ACL / 记录规则）或入口声明（action context），视图只能呈现。

**根因定位链（消费侧，不是文本侧）**：
`addons/smart_core/utils/contract_governance_form_render.py:53,88,114,122,129` →
`effective(record cap) = view ∧ model ∧ record ∧ entry`；前端唯一驱动
`frontend/apps/web/src/views/ActionView.vue:7,1459,1479` ← `store.ts:545` ←
`status.effectiveRecordCapabilities`。因此「view 独占」= 上述四因子中 view=false 而其余三项皆 true。

**守卫（P4 工具，新增）**：`scripts/verify/formal_entry_capability_authority_guard.py`

- 读版本化正式菜单基线（`scripts/verify/baselines/formal_business_product_menu_policy_v1.json`），
  对每个 enabled `menu_xmlid` 经 `UiContractV2Handler` 取 `statusContract.globalStatus`，
  断言**不得**出现 `viewCapabilities[op]=false ∧ modelRights[op]=true ∧ entryCapabilities[op]=true`。
- 消费检查而非文本检查：删选择器字符串不能"通过"。
- Make 入口 `make verify.formal_entry_capability_authority.guard`（`make/runtime_ops.mk:442-445`），
  并纳入 `verify.system_user_experience.quick` 依赖链（`make/runtime_ops.mk:451`）。

**结果与负例闭环**：

- 修复前 23 条违规 / 14 入口；修复后 `FORMAL_ENTRY_CAPABILITY_AUTHORITY_OK entries=90`（0 违规）。
- 负例（先确认注入前基线守卫正常）：给 `project.edit_project` 注入 `create="0"` → 守卫精确报
  `menu_sc_project_project: view arch is the sole blocker of 'create'`；移除注入 → 恢复
  `OK entries=90`。证明"注入被检出"，不是"探针恒绿"。

**修复按其声明位置落层（不改标签、不加模型特判、不放宽 ACL）**：

| 入口 / 文件 | 处理 |
| --- | --- |
| `views/core/project_overview_views.xml` | 根 form 去 `create/edit/delete/duplicate="0"` |
| `views/core/project_information_edit_views.xml:3540` | 去根 `create/delete="false"` |
| `views/core/project_views.xml:3528` | extension 4 个 `attribute` `0→1`；`action_project_cost_ledger_quick` context 加 `delete:False` |
| `views/core/cost_domain_views.xml` | profit_compare form 去 create/edit/delete；两 action 加 context；cost_ledger 去 `delete="false"` |
| `views/projection/fund_daily_views.xml` | form 去 create/edit/delete；action 加 `edit:False,delete:False` |
| `views/support/{company_project_refund,current_account,team_loan_deduction}_workspace_views.xml` | form 去 `edit="1" delete="0"` |
| `views/menu_product_contract_completion_v1.xml` | 多 action 加 `delete:False`/`edit:False`；blacklist form 去 `create/delete="false"` |
| `views/core/tax_filing_views.xml`、`tax_certificate_registration_views.xml` | 去 `delete="0"`/`delete="false"`；action 加 context |
| `views/support/runtime_user_management_views.xml` | 去 `delete="0"`（保留 create/edit） |
| `actions/project_native_action_overrides.xml` | `action_sc_project_list_form_view` view_id → `project.edit_project`；`action_project_dashboard` context 显式 `create/edit/delete:False,no_duplicate:True` |
| `actions/project_actions.xml` | `action_sc_project_overview` context 显式 `create/edit/delete:False,no_duplicate:True` |

**行为等价**：`delete/edit` 均为**显式声明**（不是键缺席），未把 create/edit 的默认→拒绝语义倒置；
`no_duplicate:True` 即拒绝。用户可见只读行为不变，只是"谁拥有该能力"从视图移回声明层。

**锁测试**（`addons/smart_construction_core/tests/test_core_extension_v2_finalize.py`）：
两处锁改为"视图非硬拒 + 消费 entry capability"；dashboard 用例不再断言
`source["views"]["form"]["capabilities"]`，改断言 `entryCapabilities` 与
`effectiveRecordCapabilities` 皆 False。结果 `0 failed, 0 error(s) of 22 tests`；
`TestProductMessageNotification + TestLightFormsConfigurationNativeLowcode`
`0 failed, 0 error(s) of 25 tests`（`sc_dev_demo`）。

**编排契约已核清（交接的待办 2 为伪风险）**：`ui.business.config.contract` id=139
`project_project_form_structure_v1` 绑定 action=724（`action_project_initiation`）/
view=1503（`view_project_create_form`），与本次改动的 action 506 / view 1761 **无关**；
全库 `project.project` 仅此一条 form-structure 契约记录。`action_sc_project_list`(519) 的
form 槽运行时 view_id = `project.edit_project`(936)，与源码一致。既有 precedent：
`action_sc_product_project_edit_v1` 同样故意引用原生 `edit_project` 作只读展示。

**探针 addendum（列表面 / 表单 profile）**：`scripts/verify/frontend_list_surface_structure_browser.mjs`
扩展 scope 至 `['all','record-only','detail-only','workbench-only','form-profiles']`；
`form-profiles` 执行体观测"声明 create → 点新建 → `/f/<model>/new` → form 契约 profile=create"
与"声明 edit → 点行 → record 契约 profile=edit"，否则记 `not_applicable`；
`not_applicable` 计入 satisfied，空 viewports 判 `incomplete`。锁
`scripts/verify/test_frontend_list_surface_search_contract.py` 同步更新，
`make verify.frontend.list_surface_search_contract.unit` → 22 tests OK + receipt PASS。
**锁定声明与行为，不把选择器字符串、`44px`、`60px` 文本出现本身当作正确性证明。**
旁证：`playwright_vendor_coupling_guard.py` OK（vendor 104 / 记录 109，余量 5；geometry 33/33，余量 0）、
`python3 -m unittest scripts.verify.test_frontend_standard_preview` OK、`git diff --check` 干净。

### 6.11 记录边界（2026-10-05 追加）

1. **P1 归属纠正**：`ListPage.css`、`theme.css`、`ProductListHeader.vue` 的通用展示行为属
   **P0 前端渲染机制**，不是 P1。已在原 run `FE-TPL-OFFICIAL-TEMPLATE-ADOPTION` 记录，此处引用；
   **不为标签改写提交历史**。`rendering_detail_state` 的排除引用既有证据与裁决。
2. **候选证据复用**：`02d28a06d → 6f07ff09a` 三个提交（`8fddb1f14` 前端布局、`146e47a2d` 探针/工具、
   `6f07ff09a` run.json 元数据）不影响后台与构建产物；探针变化已由本次报告覆盖，
   **无需仅因 HEAD 不同重新构建**。
3. **环境 DENY 单独保留**：只作为重建/快照车道的阻断结论，绑定实际入口依赖与独立复核依据，
   **不泛化成"环境全部通过"**。两个挂载者属同一项目不足以证明符合独占要求；非当前授权的挂载者须走
   既有受管入口处理并复验 audit，保留在用的 `18082`，不得放宽审计或直接操作容器绕过 DENY。
4. **固定口令独立复核**：`SC_ACCEPTANCE_FIXTURE_PASSWORD ?= scdevpass`（`make/dev.mk:741`，由已合并提交
   `2d164a1f` / PR #525 引入，非本轮）仅作用于既有隔离 fixture；`LOCAL_CONTRACT_LIFECYCLE_PASSWORD`、
   `LOCAL_CONTRACT_SNAPSHOT_PASSWORD` 同为隔离 profile；日常/通用登录默认
   `E2E_LOGIN/E2E_PASSWORD = wutao/123456` **未改变**。同一结论已在
   `FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/run.json` 记录，本次仅做有界复核并引用。

### 6.12 仍未关闭（本轮）

- 本轮改动**尚未提交**（工作区 20 改 + 1 新增）；未做 clean 冻结、独立复核与候选 bundle sync。
- 远端 `sc-root` 日常运行态仍是 `9121b064`；能力权限守卫在远端的 0 违规结论**待同步后复验**。
- 远端 `form-profiles` 列表范围实跑为可选项：本地证据由锁测试 + 探针单测覆盖，未跑浏览器矩阵。
- 四层状态分列不变；整体分支目标**暂不**标记完成。

### 6.13 候选纠偏与冻结前修复（2026-10-05 追加）

独立只读复核 `3f424993c..14267a68` 发现一处真实缺陷，已闭环；另有一处冻结前阻断已修复。

1. **`menu_sc_project_project`（项目台账）`create` 被静默放开（已修）**
   - 事实链：`action_sc_project_list` 的 form 槽由 `view_project_overview_form`
     （根级 `create/edit/delete/duplicate=0`）改为原生 `project.edit_project`，但
     `action_sc_project_list` 的 `context` 仍是 `{}` → `effective.create` 由 `False` 翻为 `True`
     （`group_sc_cap_project_user`/`manager`/`business_config_admin` 均 implied `group_sc_cap_project_read`）。
   - 判定：`project_overview_views.xml` 注释已点名两个消费 action
     （`action_sc_project_overview` / `action_sc_project_list`），但只有前者拿到声明 → **漏声明**，
     不是产品决策；且 `新项目立项`(`action_project_initiation`) 已拥有创建入口，台账再出现「新建」与之重复。
   - 修复：`action_sc_project_list` context → `{'create': False, 'edit': False, 'delete': False,
     'no_duplicate': True}`；未动 ACL / 记录规则 / 字段权限，未加模型特判，未改绑 1843。
   - 复验：`UiContractV2Handler(menu_sc_project_project)` → `write/create/unlink/duplicate` 的
     `entryCapabilities` 与 `effectiveRecordCapabilities` 均为 `False`；14 个原视图拒绝入口等价复核
     `PREV_DENIED_OPS=23 STILL_DENIED=23 PROBLEMS=0` → `ENTRY_EQUIVALENCE_OK`。新增锁
     `test_project_ledger_entry_declares_readonly_and_projection_follows`：
     `TestCoreExtensionV2Finalize` **23 tests, 0 failed**（原 22）。守卫复跑 `entries=90`。
2. **`ci.local.quick` 的 G1 基线指纹阻断（已修）**
   - `b3804cf5` 把 `acceptance_environments_v1.json` 的 `min/max_actions` 89→90（§3.7 项目台账发布面修复），
     未同步刷新 `G1_BASELINE_EVIDENCE.json` 资产指纹 → `[g1_acceptance_baseline_guard] FAIL
     fingerprint drift ... recorded fbc07a7a560a... actual 3820890a7127...`。
   - 修复：`python3 scripts/verify/g1_acceptance_baseline_guard.py --write
     --baseline-sha 3f424993c9f378aaeedd2f26080545ad37ea3f8e`；diff 仅 3 行
     （`baseline_sha` / environments `sha256` / `collected_at`），复验 `[g1_acceptance_baseline_guard] PASS`。
3. **守卫已知盲区（记录，不静默修复）**：谓词单向
   （`view=false ∧ model=true ∧ entry=true`）且以超级用户运行（`modelRights` 恒真），**无法**检出
   「视图原本拒绝 → 去拒绝后未声明 → 翻为允许」这一类；`form-profiles` 探针 scope 把
   `not_applicable` 计入 satisfied，故对整体只读目标会「通过」。独立复核以「全库 138 菜单命中 23 条
   原生违规」自证谓词非空转。二者列为本轮之后的 P4 工具改进项。

**待办（下一执行单）**：刷新生成证据 → 提交使 HEAD 前移 → `make ci.local.quick` 一次 →
候选 bundle sync → 远端升级 `smart_construction_core` → 复验守卫 0 违规 + 刷新 5180 预览 → 四项交回。
四层状态分列不变；整体分支目标**暂不**标记完成。

### 6.14 受管远端回读暴露的持久化低代码回归（2026-10-05 追加）

候选经受管 `daily.runtime.candidate.bundle_sync` 刷到 sc-root 后，按流程执行
`make mod.upgrade MODULE=smart_construction_core` + `make restart`，随即运行受管守卫，**远端复验失败**：

```
AssertionError: smart_construction_core.menu_sc_project_project: action_open contract did not succeed
ok=False  code=409  reason_code=CONFIG_TARGET_STALE
configuration=view_orchestration:project.project:form:action:506:view:0:custom_user_flat
target=/form[1]/sheet[1]/div[1]/div[1]/div[3]/field[1]
```

**根因（本地验证为何未暴露）**：候选把 `action_sc_project_list` 的 form 槽由
`view_project_overview_form` 改为原生 `project.edit_project`；而 sc_demo 上存在 3 条持久化的
P3 低代码编排配置（`ui.business.config.contract` id 2000/2111/2112，均绑定 action 506），
其中 id 2000 的 `node_patches` 目标 xpath 只存在于**旧**的 form 组合中 → 目标失效 → 409。
本地 `sc_dev_demo` 这类配置 **COUNT 0**，因此本地 L2/探针证据**不可能**暴露该 409；
这是「本地能过、日常库会炸」的典型缺口，正是受管远端回读的价值。

**修复（回到最小必要改动）**：清掉视图硬拒本身已足以消除守卫违规，
form 槽改绑并非必需，且它同时改变了用户可见行为并破坏持久化运行时配置 →
**回退该改绑**（`project.edit_project` → `view_project_overview_form`），
保留入口声明（`{'create': False, 'edit': False, 'delete': False, 'no_duplicate': True}`）。
本地修复后复验：守卫 `entries=90`；`TestCoreExtensionV2Finalize` 23/23；
14 入口等价复核 `PREV_DENIED_OPS=23 STILL_DENIED=23 PROBLEMS=0` → `ENTRY_EQUIVALENCE_OK`；
该入口 `view=True`（中性）而 `entry=False`（声明权威）。

**未采纳的替代（留所有者裁决）**：保留原生 form，转而用受管低代码修复入口重定向/退役该 P3 配置。
两者都不放宽审计、不加模型特判、不动 ACL/记录规则/字段权限。远端 409 在重新同步并复跑守卫前
**不宣称已关闭**。

### 6.15 缺表恢复缺口：`init()` 只建索引不建表 + 外键被快照缓存吞掉（2026-10-05 追加）

**暴露路径（原始复现）**：`CODEX_NEED_UPGRADE=1 make acceptance.module.upgrade MODULE=smart_construction_core`
在 `sc_frontend_acceptance` 上以
`psycopg2.errors.UndefinedTable: relation "sc_contract_slo_observation" does not exist` 崩溃，
栈为 `init_models → check_tables_exist → env[name].init()`。

**根因一（建表责任）**：Odoo 对缺表模型只调用 `model.init()`（`Registry.check_tables_exist`，
`odoo/modules/registry.py`；`odoo/modules/loading.py` 也是同一入口），不调用 `_auto_init()`。
`contract_slo_observation.py` / `idempotency_record.py` 覆写的 `init()` 只写 `CREATE INDEX`，
因此这条路径下根本没有能力建表 → 任何缺该表的数据库在模块升级时必崩。

**根因二（外键被静默跳过）**：只让 `init()` 建表还不够。`Registry.is_an_ordinary_table` 用进程级缓存的
`pg_class` 快照回答；该快照生成于缺表之时，早于本次新建的表，且同一轮内不再刷新，于是
`Many2one.update_db_foreign_key`（`odoo/fields.py`）直接 early-return，外键被静默跳过。
表现为**顺序相关**：同一轮恢复里只有第一个模型保住外键。

**修复（通用责任层，无模型特判）**：新增
`addons/smart_core/core/model_table_recovery.py::ensure_table_on_init`，表存在时严格 no-op；
缺表时以私有 `_post_init_queue` / `_foreign_keys` / `_is_install` 上下文运行 `_auto_init`，
立即 flush 被延迟的外键，再跑 `registry.check_indexes` + `check_foreign_keys`，并重置
`_ordinary_tables`，使局部或过期快照都不可能遮蔽新表。两个模型在 `init()` 首行调用它。

**证据**：
- L2：`make local.dev.test MODULE=smart_core TEST_TAGS=model_init_table_recovery` →
  4 tests / 0 failed / 0 errors / exit 0。`tests/test_smart_core_model_init_table_recovery.py`
  先断言负例基线（两表存在），再丢表，然后经真实 `check_tables_exist` 入口断言表 + 全部 7 条外键
  （逐条 + 计数）+ 全部 3 条声明索引（含 `sc_contract_slo_observation_identity_time`）恢复，
  并完成一次可用的 ORM 写入。
- **根因二锁定 + 负例控制**：`test_recovery_survives_stale_ordinary_tables_snapshot` 在丢表后注入
  一份"缺表时"的 `Registry._ordinary_tables` 快照；把 `ensure_table_on_init` 的 `_ordinary_tables`
  重置行注释掉后该用例失败（`missing foreign key sc_idempotency_record.actor_uid -> res_users.id`，
  1 failed / EXIT=2），恢复即通过——证明该断言非空转，确实锁住根因二。
- **opt-in 静态守卫**：`test_every_smart_core_init_override_calls_recovery` 扫描
  `addons/smart_core/models/`，要求每个 `init()` 覆写都调用 `ensure_table_on_init`（扫描数非零），
  避免未来新增覆写静默重落根因一。
- 端点：验收库两表各 0 行，丢表后 `CODEX_NEED_UPGRADE=1 make acceptance.module.upgrade
  MODULE=smart_construction_core` → `Models have no table ...` → `Recreate table of model ...` →
  **EXIT=0**（无 `UndefinedTable`、无 `Model ... has no table`）；回读两表存在且 7 条外键、
  3 条声明索引齐全。
- `smart_core` 模块版本**不 bump**：改动只作用于升级期、对既有库无 schema 变化；且
  `scripts/verify/backend_contract_lifecycle_runtime_schema_guard.py` 用 manifest 版本锁定 L4
  运行时产物，bump 会无谓使其失效。
