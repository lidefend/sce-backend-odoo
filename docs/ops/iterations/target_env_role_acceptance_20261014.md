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

## 10. 数据域天花板「遍历锚点」语义缺陷与收口（2026-10-15，部署面 `48214f7a`）

### 10.1 更正 9.x 中已记录的结论

9.4 之后的一轮只读探针曾在部署面 `48214f7a` 上读到一次 `contract.request.http_status=200`，
按当时读数把「目标环境支付合同 403」记为已关闭。**该记录不成立，现更正。**

同一命令、同一 expected SHA 的可复现读数如下：

| 时间（CST） | 入口 | 结果 |
|---|---|---|
| 2026-10-14 23:34 | `make verify.daily_dev.acceptance.readonly.probe` | `contract.request.http_status=200`，custody 1,049,446 B 落盘 |
| 2026-10-14 23:44 | 同上 | `contract.request.http_status=403`，custody 952 B |
| 2026-10-15 00:21 | 同上 | `contract.request.http_status=403` |

原因：23:31 的候选发布重启了 odoo 容器（`source_revision.align` 回执 `restarted=true`，容器日志
`15:35:17Z` 起进程重载、`Registry loaded`），23:34 那一次读数由**尚未重载 registry 的 worker** 服务，
因此读到了规则写入前的旧快照。从 `15:44:53Z` 起部署面稳定拒绝。

### 10.2 权威根因（部署面服务端日志）

```
15:44:53Z [intent] intent=ui.contract.v2 ... record_id=36184 op=action_open model=payment.request
15:44:53Z Access Denied by record rules for operation: read on record ids: [14], uid: 210, model: sc.business.category
15:44:53Z POST /api/v1/intent?db=sc_demo HTTP/1.1" 403 - 92
```

403 不是 `payment.request` 被拒，而是合同装配要读的参考数据 `sc.business.category`(id 14) 被拒。

部署库 `ir.rule 851`（`smart_construction_core.rule_sc_data_scope_sc_business_category`，
`global=True`、`groups=[]`、`write_date=2026-10-14 15:29:16Z`）当时的域为：

```
['|', ('approval_policy_id.company_id', '=', False),
     '&', ('approval_policy_id.company_id', 'in', company_ids),
          ('approval_policy_id.company_id', 'in', user._sc_data_company_ids())]
```

Odoo 把遍历项 `('approval_policy_id.company_id', '=', False)` 编译为
`approval_policy_id IN (SELECT id FROM <策略表> WHERE company_id IS NULL)`；当记录的
`approval_policy_id IS NULL` 时该式为 NULL 而非 TRUE，于是声明中「未归属=共享、保持可见」的那一支
**恰好对被静默隐藏**。声明 `enforced`、域却比声明更严 ⇒ 参考数据在真实角色下不可读 ⇒ 合同装配 403。

### 10.3 自有层修复

`scripts/verify/sc_data_scope_ceiling_generate.py` 新增 `unset_branch_terms()`：遍历锚点的未归属分支
渲染为两事实之并——「没有父」∪「父无归属公司」，即
`['|', '|', ('父', '=', False), ('父.公司', '=', False), '&', <allowed>, <purpose>]`。
自有列锚点（`company_id`）保持单项不变；声明 `unsetOwner: unknown` 的 4 条仍严格、不获得该分支。

产物经唯一允许的写入入口 `make verify.sc_data_scope.ceiling.sync` 重新生成：143 条规则中
**57 条变化**（= 61 条遍历锚点 − 4 条 `unknown`），其余零改动。

本地非零定向验证（均为受影响层）：

| 入口 | 结果 |
|---|---|
| `make verify.sc_data_scope.ceiling.check` | 15 tests OK；`SC_DATA_SCOPE_CEILING=connected rules=143` |
| `make verify.sc_data_scope.rule_coverage` | 15 + 38 tests OK，`uncovered=[]` |
| `make verify.data_space.policy.unit` | 12 tests OK |
| `make verify.data_space.provisioning.guard` | `PASS roles=customer_production,industry_acceptance,platform_internal_demo invariants=9`；34 tests OK |

### 10.4 同源发现：13 条手写遍历锚点（本轮**不改**，登记为独立 P1 批次）

`addons/smart_construction_core/security/sc_record_rules.xml` 另有 13 条手写全局规则带同一种
单一遍历未归属项，语义缺陷完全相同：

| 规则 | 锚点 |
|---|---|
| `rule_sc_workflow_workitem_tenant_business_admin_company` / `rule_sc_workflow_log_tenant_business_admin_company` | `instance_id.company_id` |
| `rule_sc_boq_version_allowed_company` / `rule_sc_boq_line_allowed_company` / `rule_sc_boq_import_batch_allowed_company` / `rule_sc_boq_analysis_allowed_company` / `rule_sc_boq_summary_component_allowed_company` | `project_id.company_id` |
| `rule_sc_cost_plan_allowed_company` / `rule_sc_cost_plan_line_allowed_company` / `rule_sc_cost_plan_node_allowed_company` | `project_id.company_id` |
| `rule_sc_boq_analysis_norm_allowed_company` / `rule_sc_boq_analysis_resource_allowed_company` | `analysis_id.project_id.company_id` |
| `rule_sc_material_supplier_return_line_company` | `return_id.company_id` |

只读回读（部署库 `sc_demo`）显示这 13 个模型当前均为 **0 行**，故在该库属潜在缺陷、未观测到运行影响；
但其中 `project.boq.analysis.norm.line` 与 `project.boq.analysis.resource.line` 是声明里的
`source_bounded` 权威载体，不能长期停留在“声明与实现不一致”。

不在本批修改的理由：它们是**手写 P1 安全规则**，与本次修复的 P4 生成器不是同一自有层；
在没有任何实测影响的条件下改动 13 条安全规则，正是本批刚发现的失败模式（改完才暴露）。
后续 P1 批次应把这几条**迁移进声明/注册体系并重新生成**，而不是逐条手工打补丁。

### 10.5 发布前置（必须）

天花板 XML 属于 `smart_construction_core`，而 daily 发布链默认只升级 `smart_core`
（`DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES ?= smart_core`），且模块树未变时会复用升级。
因此本修复必须显式携带：

```
DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES=smart_core,smart_construction_core
```

否则规则不会重装，`ir.rule 851` 仍是旧域，探针会继续 403。

### 10.6 状态口径

- 批次验收：**未完成**（本地静态/生成器测试已过；安装态与部署态探针待复核）；
- 主线集成：上一 PR 已合并（`ddd697c2`）；本批候选待发布合并；
- 版本发布 / 产品交付：**未声明**。

## 11. 遍历锚点修复的集成、发布与只读验收（2026-10-15，部署面 `91a220ab`）

本章关闭第 10 章末尾「批次验收未完成」的口径，并落实 10.5 的发布前置。

### 11.1 基线分叉与主线集成（PR #660）

PR #659 以 squash 合入 main（`ddd697c2`），而本分支仍带着**同树不同历史**的旧提交 `48214f7a`，
于是 `make pr.push` 的 `conflict_guard` 拒绝推送（exit 7：PR merge ref 无法构建、门禁会派发零检查）。

受管入口 `make workspace.branch.sync-main` 按设计**拒绝已发布的远端同名分支**（“published history
cannot be rewritten”），因此按守卫自身给出的恢复路径执行 `git merge origin/main`：两处冲突
（本 run 台账 `.agent/runs/TARGET-ENV-ROLE-ACCEPTANCE/run.json` 与本章所在迭代记录）均取分支侧，
因为 main 侧内容与本分支基线 `48214f7a` **逐字节一致**，取分支侧不丢任何 main 内容；
合并结果树与合并前 HEAD 树用 `git write-tree` 比对**逐字节一致（零内容变化）**。

- 合并提交：`91a220ab`；远端 fast-forward `48214f7a..91a220ab`；无 force push、未改写已发布历史。
- 四项必需检查（`public_guard` / `merge_policy_gate` / `professional_quality_gate` /
  `frontend_release_gate`）在 `91a220ab`（base `ddd697c2`）全部通过。
- 合并为 squash 单亲提交 **`34a22c61`**，其树与 `91a220ab` 逐字节一致；合并不触发产品部署。

合并门禁的一个操作要点（避免再次踩坑）：`make pr.merge` 要求**精确 HEAD** 的 `ci.local.quick`
回执，缺失时 fail-closed 兜底。**在 `make` 命令行上传入 `PR=`/`EXPECTED_HEAD=` 会经 MAKEFLAGS
传给子 make，分片会以 `MISS makefile injection or command overrides cannot sign coverage` 拒绝签署**，
须先单独执行 `make ci.local.quick`（本次 8/8 分片通过，2m24s，回执写入
`.git/codex/evidence/ci.local.quick/91a220ab76f3f581b4a233b2774979b2023205da.json`），
再用 `make pr.merge` 复用该回执。

### 11.2 目标环境重发布（显式模块升级）

```
make daily.runtime.candidate.release \
  DAILY_CANDIDATE_EXPECTED_SHA=91a220ab76f3f581b4a233b2774979b2023205da \
  DAILY_CANDIDATE_EXPECTED_OLD_SHA=48214f7ac7e27eac62137408fbd17c69878b53ad \
  DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES=smart_core,smart_construction_core \
  DAILY_RUNTIME_PUBLISHED_FACE_LOGIN=wutao
```

- `daily.runtime.candidate.bundle_sync` PASS：`deployment_mode=candidate`、`old_sha=48214f7a` →
  `source_sha=91a220ab`、`origin_main_mutated=false`。
- `daily.runtime.source_revision.align` PASS：`SC_SOURCE_REVISION=91a220ab`、容器已重启
  （这正是上一轮 200 假象的来源：读到的是未重载 registry 的 worker）。
- `daily.runtime.published_face.converge` PASS：`modules=[smart_core, smart_construction_core]`、
  `module_tree_ids={smart_core: 0a1dcfb4…, smart_construction_core: e250945d…}`、
  `module_upgrade_returncode=0`、`guard_status=PASS`。

日志：`.runtime/final-acceptance/target-env-role/daily-release-91a220ab.log`、
报告：`.runtime/final-acceptance/daily-deployed/published-face-converge.json`。

### 11.3 部署面只读回读（规则与角色可见性）

部署库 `sc_demo`，`ir.rule` 851（`smart_construction_core.rule_sc_data_scope_sc_business_category`，
global、groups=[]）升级后（`write_date 2026-10-14 16:41:43.989043`）的域：

```
['|','|',('approval_policy_id','=',False),('approval_policy_id.company_id','=',False),
      '&',('approval_policy_id.company_id','in',company_ids),
          ('approval_policy_id.company_id','in',user._sc_data_company_ids())]
```

即声明语义「未归属 = 共享」已按并集表达。以 `fixture_role_finance`（uid 210，company 21/22）读取：

|读数|结果|
|---|---|
|`sc.business.category` id 14|可读（名称「付款申请」，`approval_policy_id=False`，正是此前被静默隐藏的未归属行）|
|同模型 `search_count`|47|

### 11.4 只读验收探针（受管顺序：fixture → 记录身份 → 探针）

| 步骤 | 入口 | 结果 |
|---|---|---|
| 1 | `make daily.runtime.lifecycle_fixture.prepare` | PASS（carrier `FE-LC` id 2022，`draft`，`reset=false`）|
| 2 | `make daily.runtime.record_identity.resolve` | PASS（`served_revision=91a220ab`）|
| 3 | `make verify.daily_dev.acceptance.readonly.probe` | **PASS** |

探针事实（`.runtime/final-acceptance/target-env-role/readonly_probe_91a220ab.log`）：

- `contract.request.http_status=200`（intent `ui.contract.v2`，`client_type=web_pc`，`delivery_profile=full`，
  `render_profile=edit`，`action_id=780`，`menu_id=550`，`model=payment.request`，uid 210，company 21，
  role_code `finance`），11 项声明检查全绿；
- custody 落盘：`response_bytes=1049473`、`response_sha256=f1fe33f2…f016`、
  `artifacts/backend/daily_dev_acceptance_probe.contract.json`；
- 导航（`wutao` / `business_config_admin`）：`nav_leaf_count=90`、`nav_gate_kept_leaf_count=90`、
  `nav_admitted_entry_count=90`、`nav_required_path_misses=[]`、`nav_forbidden_label_hits=[]`、
  `nav_required_action_mismatches=[]` —— **90/90，0 miss**；
- 运行身份：`served_sha=91a220ab`、`frontend_build_sha256=cf803d03…`（未变）。

**记录身份漂移（非缺陷）**：同一稳定标识
`smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a`（记录身份
`FE-DELIVERY-HARDENING-001`）的数值行号由 36184 变为 **36186**；探针的
`resolution_unique_target`（`identifier_resolved_pairs=1`、`distinct_claiming_identifiers=1`、
`competing_identifiers=[]`）证明绑定的是“被服务的行”而非猜测的数据库 id —— 这正是本仓库
禁止钉死数值 id 的原因。

受管回执：`make agent.run.begin` → 复跑探针 → `make agent.run.record`
（`.runtime/agent-runs/TARGET-ENV-ROLE-ACCEPTANCE/daily_readonly_acceptance_probe.json`，
`test_count=11`、`status=passed`、log 指向上述探针日志）。
注意顺序：`readback` 产物在 `begin` 之后会被探针重写，导致输入指纹变化而 fail-closed；
应先复跑探针、再 `begin`、再 `record`。

### 11.5 状态口径（本轮）

- **批次验收：完成**（本批=遍历锚点语义修复：本地 L1/L2 生成器与守卫测试 + 部署面只读验收
  `http 200` 与导航 90/90）；
- **主线集成：完成**（PR #660 已合并，main = `34a22c61`）；
- **版本发布：未完成**（仍为候选面 `product_version=1.0.0-rc.20`）；
- **产品交付：未声明**（本批仅覆盖 `business_config_admin` 导航面与 finance 角色的一个契约身份）。

待办（不在本批）：

1. 13 条手写遍历锚点规则迁移进声明/注册体系并重新生成（独立 P1 批次，见 10.4）；
2. 其余代表角色（pm / owner / project_member）的允许/拒绝证据，以及“按角色期望载体”
   （`open_p4_probe_has_no_per_principal_expectation_carrier`）；
3. 本轮的台账与文档 delta **不单独开 PR**：`pr.merge.local_quick_gate` 明确拒绝仅含
   `.agent/` 与 `docs/` 的簿记候选，故随下一个产品候选一同提交。

## 12. 数据空间开通与 89 入口矩阵对比（2026-10-15，部署面 `46ce8e12`）

本章收口第 10–11 章之后暴露的**归属空白**：发布面已正确，但平台没有声明 `sc_demo`
的环境角色，于是同一批业务数据在「公司归属上限」这一层被整体挡下。

### 12.1 触发事实与根因

`sc_demo` 的 `sc.environment.role` **未声明**，读取方按缺省回退 `customer_production`；
公司 1（环境主公司，真实主体名称按仓库公开范围脱敏）没有任何归属登记，于是 143 条数据域天花板规则里的
`company_id in user._sc_data_company_ids()` 求值为**空集**。实测后果：公司 1 的 34,891 条
`payment.request` 对包括管理员在内的所有账号不可见，89 个正式入口里 **68 个 `empty`**。

这是**维度错位**，不是权限放宽问题：平台需要一个**环境角色声明**来决定「这个库是
客户生产空间还是平台自有演示空间」，而不是让每个业务模型自己猜。修复方向是把这条
声明变成**平台产品能力**（`make daily.runtime.data_space.onboard`），并在模块升级前
用归属门禁把「先开通、再升级」的顺序钉死。

### 12.2 基线再分叉与合并（`46ce8e12`）

`origin/main` 此时含 PR #660 的 squash 提交 `34a22c61`（与本分支 `91a220ab` **同树**）。
本分支带着 `ce3c9d24`（数据空间开通代码）尚未集成，于是再次按守卫恢复路径执行
`git merge origin/main`：

- 仅 **2 处记账冲突**（本 run 台账与本章所在迭代记录），均取分支侧；逐项比对确认分支侧
  为该内容的超集，不丢 main 任何内容；
- 合并提交 **`46ce8e12`**，合并结果树与合并前 HEAD 树用 `git write-tree` 比对
  **逐字节一致（零内容变化）**；无 force push、未改写已发布历史。

### 12.3 目标环境发布（`served=46ce8e12`）

| 步骤 | 入口 | 结果 |
|---|---|---|
| 1 | `make daily.runtime.candidate.bundle_sync` | PASS（`old 91a220ab → 46ce8e12`，bundle `sha256=9644899a…`，`origin_main_mutated=false`）|
| 2 | `make daily.runtime.source_revision.align` | PASS（`/api/runtime-version` 回读 `git_sha=46ce8e12`，容器已重启，`frontend_build_sha256=cf803d03…` 未变）|

### 12.4 受管开通（`daily.runtime.data_space.onboard` PASS）

只读计划 `make daily.runtime.data_space.onboard.plan` 的事实：
`environment_role=customer_production`、`main_company_id=1`、`bootstrap_company_ids=[]`、
`registration_rows=2`、`registered_company_ids=[21,22]`、`registered_purposes=['test']`、
`demo_registration_company_ids=[]`、`operators_pending_enrollment=null`。

**首次** `published_face.converge` 按设计**被拦截**：
`MODULE_UPGRADE_FAILED … ValueError: DATA_SPACE_UNREGISTERED_BUSINESS_DATA_OWNER:1`——
正是新增的**升级期归属门禁**，证明「先开通、再升级」的顺序正确。

执行开通（`CONFIRM_DAILY_RUNTIME_DATA_SPACE_ONBOARD=ONBOARD_DAILY_RUNTIME_DEMO_DATA_SPACE`，
`DAILY_RUNTIME_EXPECTED_SHA=46ce8e12…`）**PASS**：

- `environment_role=platform_internal_demo`；公司 1 被**收养**（adopt，`declared_role` 明示
  `already_owns_registration`，非重贴标签）；
- `registered_company_ids=[1,21,22]`、`registered_purposes=['demo','test']`、
  `registration_rows=3`、`demo_registration_company_ids=[1]`；
- `operators_pending_enrollment=[]`；4 项 post_conditions 全绿
  （`role_declared` / `main_company_is_not_a_carrier` / `main_company_registered_as_demo` /
  `operators_pending_enrollment_is_empty`）。

写入面仅限平台自有归属元数据（1 个 `ir.config_parameter` + 1 行
`sc.tenant.company.registration`），**未删** 21/22 的 fixture 登记（`purpose=test` 不变，
仍为验收 fixture 归属锚）。报告：`.runtime/final-acceptance/daily-deployed/data-space-onboard.json`。

### 12.5 发布面收敛（PASS）

`make daily.runtime.published_face.converge`
（`DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES=smart_core,smart_construction_core`、
`LOGIN=wutao`、`CONFIRM=REFRESH_DAILY_RUNTIME_PUBLISHED_FACE_FROM_LOCKED_CONTRACT`）**PASS**：

- `guard_status=PASS`、`module_upgrade_returncode=0`、`expected_sha=46ce8e12…`；
- `snapshot_version=daily-navigation-preview-46ce8e1214d5`、`locked_released_menu_count=90`、
  `gate_page_count=129`、`product_key=construction.preview`（`construction.standard` 90/90）。

报告：`.runtime/final-acceptance/daily-deployed/published-face-converge.json`。

### 12.6 89 入口矩阵对比（开通前 → 开通后，无回归）

命令（`make verify.frontend.business_entry.matrix.browser`，`ACCEPTANCE_TARGET_SHA=46ce8e12`，
`wutao` / `sc_demo` / `http://1.95.85.92:18081`）：
结果 `ok=true completeness=complete entries=89 problems=0 console_errors=0`。

| 状态 | 开通前 `91a220ab` | 开通后 `46ce8e12` |
|---|---|---|
| `empty` | 68 | **41** |
| `ok` | 20 | **42** |
| `ready` | 0 | 5 |
| `true` | 1 | 1 |

**27 项 `empty → 非空`（`ready` 视为非空）**：待办事项、投标项目、施工日志、劳务成本登记、
材料入库、机械台班登记、薪资核算清单、收入合同、支出合同、日常合同、收入结算、支出结算、
成本归集、项目盈亏分析、付款申请、实付登记、公司支出、公司&项目扣款、资金汇总、预缴登记、
销项开票、进项发票、税额抵扣、劳务分包报表、工资薪酬、流程审批配置、字段管理。
**回归项 = 0**。

`ready` 5 项（收入合同 / 支出合同 / 收入结算 / 支出结算 / 实付登记）属矩阵既有的「就绪」
状态（页面可达、集合就绪），非缺陷。

### 12.7 41 项残留 `empty` 的只读归因（全部非归属缺陷、非回归）

用自包含远端 Odoo shell 探针逐项核对模型行数与规则，结论分四类：

1. **模型本身 0 行（29 项）**：`sc.safety.issue`、`sc.quality.acceptance`、
   `sc.project.document`、`sc.site.variation`、`tender.opportunity/document`、
   `sc.material.outbound`、`sc.subcontract.register`、`sc.hr.salary.payment`、
   `sc.contract.change`、`project.cost.plan`、`sc.tax.filing`、`account.move.line`、
   `account.analytic.*` 等。
2. **有数据但「未归属不共享」是声明语义**（`company_id=False` 且 `project_id` 为空 → 不共享）：
   `sc.document.admin.document`（uid16 可见 5,948，仅 `company_document_archive`；
   `certificate_registration` / `policy_document` 归属空），`sc.hr.payroll.document`
   （uid16 可见 233；另 10,733 行 `company_id=False` 不共享），`ir.sequence`（uid16 可见 50）。
3. **角色分组 + 动作域组合**：`sc.expense.claim` 66,510 行中 12,552 行通过公司+用途天花板，
   但动作域按 `business_category_id`（18=报销 / 备用金）过滤的主体行对 uid16 不可见，
   可见行类别为 28 → 返回 0；`tender.bid` 有 13,101 行但动作域要求 `state='won'` → 0。
4. **原有已知项**：`account.move` 仅 1 行且属 company 21（test 空间），uid16（演示域）
   不可见，正确；`project.progress.entry` 唯一 1 行属他人项目，`project_id.user_id` 规则
   不匹配 → 0（正确拒绝）。

原始输出：`/tmp/sce-night/attribution*.raw` 及对应 `*_probe.py`。

### 12.8 受管只读验收探针（`http 200` + 导航 90/90）

按登记顺序：`lifecycle_fixture.prepare`（`FIXTURE_RC=0`）→ `record_identity.resolve`
（`RESOLVE_RC=0`）→ 只读探针（`EXIT=0`，`dev_acceptance_release_probe_schema_guard PASS`）。

- `contract.request.http_status=200`（`op=action_open`、`action_id=780`、`menu_id=550`、
  `model=payment.request`、`record_id=36188`、`fixture_role_finance` uid 210、company 21、
  `client_type=web_pc`、`delivery_profile=full`、`render_profile=edit`）；11 项声明检查全绿，
  `contract.integrity_reason=ok`；
- custody 落盘：`response_bytes=1049471`、`response_sha256=ef038e8a…`、
  `artifacts/backend/daily_dev_acceptance_probe.contract.json`；
- 导航（`wutao` / `business_config_admin`）：`nav_leaf_count=90`、`nav_gate_kept_leaf_count=90`、
  `nav_admitted_entry_count=90`、`nav_required_path_misses=[]`、`nav_forbidden_label_hits=[]`、
  `nav_required_action_mismatches=[]` —— **90/90，0 miss**；
- 运行身份：`served_sha=46ce8e12…`、`frontend_build_sha256=cf803d03…`。

日志：`.runtime/final-acceptance/target-env-role/readonly_probe_46ce8e12.log`。

### 12.9 状态口径（本轮）

- **批次验收：完成**（本批=数据空间开通边界：平台归属声明产品化 + 升级期归属门禁 +
  部署面开通 `PASS` + 89 入口矩阵 27 项 flip / 0 回归 + 只读探针 `http 200`、导航 90/90）；
- **主线集成：待 PR**（候选 `46ce8e12` 尚未合并；main 仍为 `34a22c61`）；
- **版本发布：未声明**（仍候选面 `product_version=1.0.0-rc.20`）；
- **产品交付：未声明**（本轮仅覆盖 `business_config_admin` 导航面、finance 角色一个契约身份
  与 89 入口列表面可达性；未覆盖其余代表角色与跨角色业务闭环）。

待办（不在本批，仅登记不动手）：

1. 13 条手写遍历锚点规则迁移进声明/注册体系并重新生成（独立 P1 批次，见 10.4）；
2. 其余代表角色（pm / owner / project_member）的允许/拒绝证据与「按角色期望载体」
   （`open_p4_probe_has_no_per_principal_expectation_carrier`）；
3. 本轮台账与文档 delta 与产品候选 `46ce8e12` 同一 PR 提交（仓库拒绝纯簿记候选）。


## 13. 主线集成与发布面归一化复核（2026-10-15）

第 12 章的候选面验收完成后，本轮把该主题送入 main，并把每日运行面从「候选快照」归一化到
「主线修订」，再在同一身份上重跑复核。本节记录该收口的真实事实与仍未声明的事项。

### 13.1 主线集成（PR #661）

- 候选 `dbbb4d84` 在 `make ci.local.quick` 于**精确 HEAD** 通过（8/8 分片，回执
  `.git/codex/evidence/ci.local.quick/dbbb4d84c74472d15ea99f6412071ec2b6a42f0c.json`）后推送至 `origin`。
- PR #661（base `main`）四项必需检查 `public_guard`、`merge_policy_gate`、
  `professional_quality_gate`、`frontend_release_gate` 均在**该精确源提交**上、针对**该精确目标基线**
  成功；随后经 `make pr.merge.prep PR=661` 回报 `merge_policy_gate` 状态，再由
  `make pr.merge PR=661 EXPECTED_HEAD=dbbb4d84…` 以 squash + `--match-head-commit` 完成受保护合并。
- 合并结果 `eae0c1c0` 为**单亲**提交（父 `34a22c61`），其树与候选头 `dbbb4d84`
  **逐字节一致**（`git diff --stat dbbb4d84 eae0c1c0` 为空）。合并本身不触发产品部署。
- 候选携带内容：数据空间主题提交 `ce3c9d24` + 零内容基线合并 `46ce8e12` + 本轮台账/迭代记录/
  测试覆盖登记 delta（`64c85b18`、`06d2c56b`、`dbbb4d84`）。本轮**未**另开纯簿记候选。

### 13.2 发布面归一化（候选 → 主线）

此前每日运行面处于**分离头候选** `46ce8e12`。本轮按受管 main 模式入口依次执行：

| 入口 | 结果 |
|---|---|
| `make daily.runtime.main.bundle_sync` | PASS，`normalized_from_candidate=true`，`old_sha=d2079888` → `source_sha=eae0c1c0`，`bundle_sha256=a20a8020…` |
| `make daily.runtime.source_revision.align` | PASS，`served git_sha=source_revision=eae0c1c0`；`frontend_build_sha256=cf803d03…` **未变**（前端源未移动，绑定的是内容指纹） |
| `make daily.runtime.published_face.converge` | PASS，`guard_status=PASS`、`module_upgrade_returncode=0`、`snapshot_version=daily-navigation-preview-eae0c1c00af9`、`locked_released_menu_count=90`、`gate_page_count=129`、`guard_user=wutao` |

`eae0c1c0` 与 `46ce8e12` 的差集**仅**为台账、迭代记录、测试覆盖登记与受管脚本 docstring
（产品模块与前端源零改动），因此归一化不改变已验收的产品行为，只把**服务身份**对齐到主线。

### 13.3 归一化后的复核（同一服务身份）

- 登记顺序执行：`daily.runtime.lifecycle_fixture.prepare`（`FIXTURE_RC=0`）→
  `daily.runtime.record_identity.resolve`（`RESOLVE_RC=0`）→ `verify.daily_dev.acceptance.readonly.probe`
  （`EXIT=0`，schema guard PASS）。
  - `contract.request.http_status=200`（`payment.request`、`action 780`、`menu 550`、`record_id 36190`、
    `fixture_role_finance` uid 210、company 21、`web_pc` / `full` / `edit`），11 项声明检查全绿；
  - custody 落盘 `response_bytes=1049444`、`response_sha256=3e79c2b0…`；
  - 导航：`nav_leaf_count=90`、`nav_gate_kept_leaf_count=90`、`nav_admitted_entry_count=90`、
    `nav_required_path_misses=[]`、`nav_forbidden_label_hits=[]`、`nav_required_action_mismatches=[]`；
  - 身份：`expected_sha=served_sha=eae0c1c0…`、`frontend_build_sha256=cf803d03…`。
  - 日志：`.runtime/final-acceptance/target-env-role/readonly_probe_eae0c1c0.log`。
  - 运行态回执已按受管顺序重录（`make agent.run.begin` → `make agent.run.record`，
    `AGENT_TEST_COUNT=11`）。
- 89 入口矩阵在 `served=eae0c1c0` 重跑：`ok=true`、`completeness=complete`、`problems=0`、
  `console_errors=0`；状态分布 `empty=41 / ok=42 / true=1 / ready=4`，另 1 项为
  `smart_construction_core.menu_sc_p1_expense_contract`（支出合同）的
  `page.goto: Timeout 30000ms exceeded` 传输态超时。
  - 按入口声明的单键重跑（`SC_ENTRY_MATRIX_KEYS=…`，独立输出目录）得到 `list_status=ready`、
    `records_rendered=50`、`record_id=3827`，与 `46ce8e12` 轮**完全一致** → 判定为**瞬时传输超时，
    非产品回归**。
  - 证据：`artifacts/frontend-business-entry-matrix/daily-eae0c1c0-full/` 与
    `.../daily-eae0c1c0-expense-contract/`。

### 13.4 状态口径（截至本节）

- **批次验收：完成**（数据空间开通边界：开通 PASS + 27 项 flip / 0 回归 + 探针 `http 200`、导航 90/90）；
- **主线集成：完成**（PR #661 → `eae0c1c0`，单亲 squash，树与候选逐字节一致）；
- **版本发布：未声明**（每日面为**预览面**，本轮把服务身份归一到主线修订并复核，
  不等于选定版本的发布、升级与冒烟闭环）；
- **产品交付：未声明**（仍未覆盖其余代表角色的允许/拒绝证据与跨角色业务闭环）。

### 13.5 待办（仅登记，不在本批动手）

1. 13 条手写遍历锚点全局 `ir.rule` 公司天花板迁入声明/注册体系后重新生成（独立 P1 批次）；
2. 其余代表角色（pm / owner / project_member）允许/拒绝证据与按角色期望载体
   （`open_p4_probe_has_no_per_principal_expectation_carrier`）；
3. `local.dev.rebuild_demo` 场景加载失败（历史缺陷），仅在确有 demo 重建需求时处理。
