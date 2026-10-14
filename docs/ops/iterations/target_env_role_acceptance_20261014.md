# TARGET-ENV-ROLE-ACCEPTANCE · 目标环境真实角色验收（2026-10-14）

范围：在已完成版本发布的目标环境（daily `sc_demo`，服务版本/候选树/发布面均为 main
`d2079888`）上绑定真实代表角色的允许/拒绝证据。**不是**新页面、新组件、语义能力扩展、
契约变更或数据修复。

## 1. 触发事实

| 项 | 值 |
|---|---|
| 目标环境 | daily runtime，`sc-root:/opt/projects/repos/sce-product-odoo` |
| 数据库 / compose / 端口 | `sc_demo` / `sc-backend-odoo-dev` / `18081` |
| 已部署版本 | `/api/runtime-version` → `source_revision=git_sha=d2079888…`，`product_version=1.0.0-rc.20` |
| 快照 | `construction.standard` 106（released 90 / gate 90）；`construction.preview` 107（released 90 / preview 39 / gate 129） |
| 前置 goal | `FE-CONTRACT-RUNTIME-02-VIEW-STRUCTURE-COMPAT`（已完成：批次验收 / 主线集成 / 部署） |

本 goal 承接「版本发布完成」与「产品交付完成」之间的唯一缺口。

## 2. 声明边界

- `Formal Product Layer`：P4（交付/运维验收证据）
- `Layer Target`：`daily_runtime_target_environment_role_permission_acceptance`
- `Standard vs User-Specific`：平台交付验收证据，不改任何 P0/P1/P2 语义
- `Why Here`：目标环境验收属交付层职责，只读取已部署产品面并按声明角色绑定证据
- `Why Not Elsewhere`：不改产品语义、不做前端补偿、不改契约/schema、不以管理员代替真实角色、
  不手工拼装 compose/数据库/凭据命令
- `Blast Radius`：仅目标环境只读验收证据与 `.agent`/`docs` 记账

## 4. 目标环境 403 根因（2026-10-14，部署面 `d2079888`，DB `sc_demo`）

### 4.1 事实回读

| 事实 | 值 |
|---|---|
| `sc.tenant.company.registration` | **2 行**：company 21「FE Company A」、company 22「FE Company B」，`data_purpose=test`，`tenant_key=frontend-productization-fixture`，`active=True`，`is_platform_bootstrap_company=False` |
| `fixture_role_finance`（uid 210） | `company_ids=[21,22]`；持久化成员关系含 `smart_core.group_smart_core_non_customer_data_user`（res.groups 152） |
| payment.request 36180 / 36181 | company_id=**21**（在 FE 数据空间内），`ui.contract.v2` 仍返回 403 |
| payment.request 36029 / 1246、project 1246 | company_id=**1**（受管基线预置的示例公司），无登记行，按设计不在任何责任人数据空间内 |
| `payment.request` 全局规则 | `ir.rule#832`「SC Data Scope - payment.request by allowed companies」，domain 含 `('company_id','in',user._sc_data_company_ids())` |

### 4.2 根因：授权事实被 ORM 缓存遮蔽

`_sc_data_company_ids()` 的文档承诺「成员、注册与当前公司授权每次解析实时读取」，
但实现委托给 `res.users.has_group`，而该方法是 `tools.ormcache('self._uid', group_ext_id)`
**跨请求缓存**。判定链因此变成：

```
用途上限 → has_group(非客户数据组) → 命中 worker 缓存
        → 数据空间为空 → ir.rule#832 命中 ('company_id','in',[])
        → 即使记录就在已登记的 FE 数据空间内，也返回 403
```

决定性只读证据（同一 uid、同一数据库、同一记录）：

| 观测点 | `fixture_role_finance`(210) | `wutao`(16) |
|---|---|---|
| shell 直接 SQL / 关系表 | 有 (152,210) 行 | 无该行 |
| HTTP `/web/dataset/call_kw` `res.users.has_group` | **false** | false |
| shell 内 `env.registry.clear_cache()` + `signal_changes()` 之后的同一 HTTP 调用 | **true** | false（不变） |

即：**HTTP 与 shell 的差异只来自缓存，不来自事实**。受管夹具经 `odoo shell` 写入，
而 shell 是请求周期之外的写入者，不会发出缓存失效信号，长驻 worker 于是一直沿用旧答案。
同一窗口在反向也成立：撤销授权后 worker 会继续放行，属于安全方向的错误。

`wutao`(uid 16) 的 403 不是缺陷：它本就不持有非客户数据组，
读不到 `data_purpose=test` 的 FE 数据空间正是双向隔离的设计结果。

### 4.3 根因修复（工作区，已验证）

- **拥有层**：`addons/smart_core/models/res_users.py::_sc_data_company_ids()` 改为读取持久化成员关系
  （与原生 `_has_group` 同一断言，去掉跨请求缓存）；新增
  `_sc_resolved_group_ids()` / `_sc_current_group_ids()` 两个事实读取助手。
- **回归门禁**：新增 `verify.local.dev.data_space_uncached_membership.orm`
  （tag `data_space_uncached_membership`，4 个用例）。绑定证据：修复版 **4/4 通过**；
  临时还原旧实现后 **4/4 失败**。
- **通道层**：`scripts/ops/daily_runtime_lifecycle_fixture_prepare.py` 在提交后显式
  `clear_cache() + signal_changes()`，使受管 shell 通道自己宣告失效；
  其单测固定该行为（18 项通过）。

## 5. 本轮产品修复（工作区，已验证）

### 回归 1：契约导航丢失「角色首页」

- 事实：契约 `index` 声明 90（`config/frontend/acceptance_environments_v1.json` →
  `navigation_policy.action_count_authority`，principal_role `business_config_admin`），部署实测 89。
- 根因：Odoo `_visible_menu_ids()` 以 action 为中心，`menu_sc_workspace_home`（`res_model=""`、无 action、
  `entry_target_policy=scene_entry`）永不可见；PR #654 让授权阶段消费该集合，于是该载体在授权链被丢弃。
- 修复：`MenuFactService.export_authorized_menu_facts()`（按 `groups_id` + 祖先链 ACL 过滤，fail-closed）
  成为授权来源；`export_visible_menu_facts()` 保持渲染语义不变。
- 状态：**已合入 main**（PR #657 → `28e19f60`）。部署面仍为 `d2079888`，故目标环境读数仍为 89，
  需重发布才会变为 90。

### 回归 2：fixture 遗留载体公司归属漂移

- 事实：`fe_activity_journal_entry`（`account.move` id 8）company_id=**1**（受管基线预置的示例公司），
  而 fixture 声明其属于 FE Company A；受管 `ensure_fixture` 因此 fail-closed，夹具无法完成入驻。
- 修复：按与 `_reconcile_project_company` 相同的边界，构建器收敛**自己这一行**——
  仅当分录为草稿、从未过账且无日记账行时改写 `company_id/journal_id/currency_id` 并重置 `name="/"`；
  任何已过账的漂移仍然抛 `Activity move ownership mismatch; use governed baseline reset`。
  区分依据：这是「夹具自有、且可证明不含业务事实」的行，不是基线重置，也不放开守卫。
- 验证：受管入口 `make daily.runtime.lifecycle_fixture.prepare` 在目标库执行 **status=PASS，carrier id=2022**；
  `verify.daily_dev.acceptance_fixture.unit` 31 项通过。

### 守卫边界（本轮未做）

- 未为 demo 放开任何写入权限、未注入绕过 token、未改写登记行 `data_purpose`。
- 未把「平台 + 行业 + 客户」语义写入平台内核；数据空间事实仍唯一来自
  `sc.tenant.company.registration`。

## 6. 状态
- 批次验收：**未完成**。三条产品缺陷已在拥有层修复并通过所属层门禁；
  目标环境只读验收仍需在**重发布后**重新绑定（部署面 `d2079888` 不含本轮修复）。
- 主线集成：回归 1 已完成（PR #657 → `28e19f60`）；回归 2/3 与 403 根因修复已在新分支重放、
  定向通道重跑，待推送并按所有者「CI 通过即合并」规则走受保护 PR 合并。
- 版本发布：**未完成**。目标环境仍为 `d2079888`。
- 产品交付：**未声明**。

## 7. 分支重放与证据刷新（2026-10-14）

本主题的前 4 个提交（含回归 2）已由 PR #657 以 **squash 同树**方式进入 main：
PR 头 `3fe59346` 与合并提交 `28e19f60`（单亲）的树逐字节一致（`git diff` 为空），
即该主题内容已全部在 main 上。

但远端同名分支已发布，治理规则禁止改写已发布历史，受管入口
`make workspace.branch.sync-main` 对存在远端同名分支的分支一律 fail-closed。
因此增量改在新分支继续，并保留已发布分支引用不再改写：

- 新分支：`fix/data-space-uncached-membership-ceiling-closeout`（自旧 HEAD `e7e3da8b` 建立）；
- 受管重放：`make workspace.branch.sync-main DEPENDENCY_PR=657 DEPENDENCY_HEAD=3fe59346
  DEPENDENCY_MERGE=28e19f60`（PASS，零冲突，已生成恢复 bundle）；
- 影响分析：重放后与旧 HEAD 仅相差 3 个台账文件（本棒自身改动），**产品内容逐字节一致**；
- 台账改绑：run/goal 的分支绑定改为新分支，`baseline_sha` 对齐 `28e19f60`，
  同时解除旧分支在 `.agent/active-runs.json` 的绑定——据此该已合并主题的远端同名分支
  后续可由受管 `make branch.cleanup.feature`（合并 PR 证明 + 精确 lease）退役。

新身份下的定向通道重跑并写回 run 回执（全部非零通过）：

| 通道 | 目标 | 计数 |
|---|---|---|
| navigation_delivery_unit | `verify.backend.navigation_delivery.unit` | 56 |
| frontend_navigation_shell_unit | `verify.frontend.navigation_shell.unit` | 106 |
| product_entry_publication_unit | `verify.product.entry_publication.unit` | 31 |
| product_menu_monotonic_unit | `verify.product.menu.monotonic.unit` | 6 |
| data_space_provisioning_guard | `verify.data_space.provisioning.guard` | 34 |
| data_space_policy_unit | `verify.data_space.policy.unit` | 12 |
| daily_fixture_lane_unit | `verify.daily_dev.acceptance_fixture.unit` | 31 |
| daily_lifecycle_fixture_prepare_unit | `verify.daily.runtime.lifecycle_fixture.prepare` | 18 |
| data_space_uncached_membership_orm | `verify.local.dev.data_space_uncached_membership.orm` | 4 |

- L1：`make ci.local.iteration` **PASS**（clean，L1_only）；台账一致性
  `verify.agent.ledger.unit` 15 + `verify.agent.resume.unit` 43 **PASS**。
- 生成物：`make ci.delivery.freeze.prepare` **PASS**（生成物已最新，无需改动）。
- 冻结候选：`b4da1056`。
- 边界说明：本 run 的 `environment.kind=runtime`，按现有台账语义，本地离线回执一律为
  **不可复用观察**（非交付门禁、非 CI 回执）；上表计数是当轮真实观察，不作为可继承证据，
  也不替代目标环境重发布后的实机验收。

## 8. 交接

| 项 | 值 |
|---|---|
| 候选分支 | `fix/nav-node-level-menu-acl-closeout`（增量分支；已合并的发布分支 `fix/data-space-uncached-membership-ceiling-closeout` 按“禁止改写已发布历史”保留在 `2ef444d6`） |
| 集成基线 | `abddd401`（`origin/main`；与已合并候选 `2ef444d6` 树逐字节一致） |
| 已合入 | PR #657（导航授权来源 + fixture 数据空间收养）、PR #658（数据空间无缓存成员上限等 7 提交） |
| 已发布 | daily `sc_demo` 部署面 = `2ef444d6`（`/api/runtime-version` 回读，`frontend_build_sha256=cf803d03…` 与旧一致，前端树未变故未重建） |
| 本轮写入 | 仅 `daily_dev` fixture 范围（FE 数据集、其数据空间登记与项目生命周期载体）；无租户业务数据、无 schema、无部署 checkout 改动 |

下一精确步骤（顺序不可颠倒）：

1. `make ci.delivery.freeze.prepare` → 提交本轮两处根因修复与其台账/文档更新 → 冻结干净 HEAD → 仅一次 exact-head `make ci.local.quick`；
2. `make pr.push` + `make pr.create`，按所有者「CI 通过即合并」规则走受保护 PR 合并；
3. 经受管入口重发布 daily（`make daily.runtime.candidate.release`，绑定新 expected SHA）；
4. **先** `make daily.runtime.lifecycle_fixture.prepare`，**再** `make daily.runtime.record_identity.resolve`，**最后** `make verify.daily_dev.acceptance.readonly.probe`（顺序见 9.2，颠倒会绑定到重建前的记录 id）；
5. 只读验收须读到 `nav_leaf_count=90`、`nav_required_path_misses=[]`、`contract.http_status=200` 且 custody 落盘；
6. 未完成前不得声明批次验收、版本发布或产品交付完成。

## 9. 目标环境重发布与只读验收事实（2026-10-14，部署面 `2ef444d6`）

### 9.1 重发布结果（受管入口）

- `make daily.runtime.candidate.release`（`CONFIRM_DAILY_CANDIDATE_BUNDLE_SYNC` /
  `CONFIRM_DAILY_RUNTIME_SOURCE_REVISION_ALIGN` / `CONFIRM_DAILY_RUNTIME_PUBLISHED_FACE` 三项显式确认，
  `DAILY_CANDIDATE_EXPECTED_SHA=2ef444d6…`，`DAILY_CANDIDATE_EXPECTED_OLD_SHA=d2079888…`）**PASS**：
  `git_sha=source_revision=2ef444d6`；`published-face-converge` PASS，`upgrade_mode=run`，
  `module_tree_ids.smart_core=8790ae2e…`，`construction.standard` gate `page_count=90 / released=90`。
- `make daily.runtime.record_identity.resolve` PASS（`served_revision=2ef444d6`）。
- `make daily.runtime.lifecycle_fixture.prepare` PASS（carrier id=2022 / company 21 / draft）。

### 9.2 只读验收 FAIL 的两处归因（均已定位到自有层）

| # | 现象 | 归因 | 处置 |
|---|---|---|---|
| 1 | `contract.request.http_status=404`，`INTENT_NOT_FOUND 记录 [36180] 不存在` | 探针绑定的记录身份是**重建前**的产物：`record_identity.resolve` 先于 `lifecycle_fixture.prepare` 运行，`ensure_fixture` 重建 FE 数据集后该行变为 36182（并新增 36183） | 顺序缺陷，非产品缺陷：固定为 prepare → resolve → probe。绑定是 fail-closed 的（陈旧 id 只会 FAIL，不会静默通过） |
| 2 | `nav_leaf_count=89`、`nav_required_path_misses=["系统菜单 / 会计账务中心 / 会计科目表"]` | 契约面 90 有**两处**独立丢失：(a) 无 action 的「角色首页」载体被旧的“可渲染集合”授权源排除（已在本分支修复，部署态回读已见 `系统菜单 / 工作台 / 角色首页`）；(b) 同一分支新增的**祖先链校验**把 `account.menu_action_account_form`（菜单 182）静默丢掉 | (a) 已生效；(b) 已按平台规则修复（见 9.3） |

部署态只读回读（uid 16，DB `sc_demo`）确认 (b)：菜单 182 自身组
`account.group_account_readonly` 已授予，父级 181/173 仅授予 `account.group_account_manager`；
`in_visible=true`、旧 `in_authorized=false`、修正规则 `in_authorized=true`。

### 9.3 根因修复（自有层，`smart_core`）

`ir.ui.menu._visible_menu_ids` 的平台规则是**逐节点** ACL：先按节点自身 `groups_id` 过滤
（非 debug 再减去 `base.group_no_one`），只有**已授予**的文件夹才会被顺带向上抬升；
因此“叶子已授予、但中间文件夹只授予其他角色”的已发布条目在平台眼里依然可见。

本分支曾在 `MenuFactService._authorized_menu_ids()` 额外要求整条 `parent_path` 都被授予，
比平台更严，于是静默丢掉了「会计科目表」，并使契约面从 90 掉到 89。

- 修复：`_authorized_menu_ids()` 只保留平台同款**逐节点**过滤；被拒祖先不入 facts，
  由 `_build_tree` 按原生投影语义重新挂根。
- 回归钉：`verify.backend.navigation_delivery.unit`（`addons/smart_core/tests/test_menu_acl_carrier_authorization.py`）
  以“已授予叶子在只授予其他角色的文件夹下仍被授权”替换原先的“祖先被拒则永不授权”。
- 部署态规则模拟（uid 16）：可见集合 496 ⊆ 修正授权集合 555；旧授权集合 312 ⊆ 固定集合 555，
  且 182 进入固定集合、1004 保留 ⇒ 重发布后应为 90 且 0 条 required-path miss。

### 9.4 尚未完成

- 上述修复尚未重发布到目标环境，因此 `nav_leaf_count=90` 与合同 custody 落盘仍需实机复核；
- 分角色验收仍需绑定**每责任人显式允许/拒绝期望**，不能用单一 `wutao` 探针替代。
