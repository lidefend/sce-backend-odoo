# 项目台账 / 项目信息编辑 入口统一（批次记录）

- 分支：`fix/project-ledger-entry-unification-v1`
- 基线：`8892042761eeb8f47a135fd817a9a9d220837620`（origin/main，PR #593 后）
- 记录时身份：HEAD `88920427` + 未提交工作区（单写者）。未冻结、未合并、未发布。
- 本次任务（用户指令）：保留「项目台账」为唯一入口；「项目信息编辑」的功能完整承载过来；
  修契约不一致；全系统产品面统一；权限/契约驱动，不保留专门只读页面。

## 责任层声明（改动前强制边界判定）

- Formal Product Layer：P1（施工行业标准产品）。
- Layer Target：`smart_construction_core`（菜单/动作/视图契约）＋ P4 证据与校验载体。
- Standard vs User-Specific：施工行业标准产品面（唯一台账入口），非客户差异、非一次性运维修复。
- Why Here：台账与编辑能力的唯一入口、菜单归属、动作 context、契约基线均属 P1 标准产品面。
- Why Not Elsewhere：不在 `smart_core` 写入行业语义；不在前端推导菜单或做模型特判；
  不改 P3 低代码运行时配置；不用运维脚本充当长期事实源。
- Blast Radius：项目中心菜单树、`project.project` 台账动作、89 项发布契约与锁定基线、
  P3 表单编排索引（action 506 配置链）、前端导航权威与验收路径。

## 契约依据（先事实后结论）

- `config/product_menu_contract_v1.json`（LOCKED，2026-08-10）：项目中心 → 分组「项目台账」→ 页面「项目台账」，
  `RELEASED_FOUNDATION`。
- 锁定策略 `formal_business_product_menu_policy_v1.json`：
  `menu_sc_project_project` + `action_sc_project_list`，`release_state=released`、`enabled=true`，
  `visible_menu_path = 智慧施工管理平台 / 项目中心 / 项目台账 / 项目台账`。
- 验收环境 `config/frontend/acceptance_environments_v1.json` 的 `required_paths` 明确要求
  「系统菜单 / 项目中心 / 项目台账 / 项目台账」。

## 变更清单

产品代码（P1）：
- `views/menu_product_contract_completion_v1.xml`：删除「项目信息编辑」action 记录与菜单项。
- `actions/project_list_actions.xml`：台账动作 context 去掉硬禁 `'edit': False`，编辑能力改由权限/ACL 驱动
  （保留 `create/delete False`，创建仍归「新项目立项」）。
- `views/core/project_overview_views.xml`：在概览 DOM 之后**追加**台账记录表单的编辑能力分组
  （additive append，不移动原节点，保持 P3 索引路径可解析）。
- `views/core/project_information_edit_views.xml`：保留休眠视图记录，删除其表单动作记录。
- `core_extension_policy_maps.py`：`pm.primary_menu_xmlids` 移除退役菜单。
- `views/menu_product_project_wave1.xml`：**本轮新发现的运行面缺陷修复** ——
  见下节「根因 6」。

锁定/生成载体：
- `config/product_menu_contract_v1.json`、`scripts/ops/promote_product_ten_center_policy.py`、
  `scripts/verify/baselines/formal_business_product_menu_policy_v1.json`(+`.sha256`)、
  `scripts/verify/product_menu_release_manifest_v2_guard.py`、
  `scripts/release/test_locked_menu_policy_contract.py`：菜单数 90 → 89，哈希同步。
- `config/frontend/authoritative_navigation.json`、`config/frontend/acceptance_environments_v1.json`：
  导航权威与验收路径收敛到台账。
- `docs/product/product_menu_contract_v1.md`、`docs/product/frontend_business_entry_acceptance_v1.csv`：
  人工维护载体由「项目信息编辑」改为「项目台账」（csv 仍为 89 项）。
- `docs/frontend_productization/page-surface-inventory.json`：静态盘点上删除退役动作/菜单两条，
  不做全量再生（避免把与本主题无关的历史漂移混入）。

运行面证据（受管 local.dev 车道再生，证据文件、非产品代码）：
- `docs/frontend_productization/domain-rollout/` 下 project/contract/finance/reporting 四个中心的
  coverage 报告与 `systemwide-coverage-audit-v1.json`。其中 contract/finance/reporting 三个兄弟报告
  相对 main 已过期（缺 main 已合并的付款台账等入口），为使 roll-up 反映真实产品面而一并再生。

## 根因

1. **入口重复**：「项目信息编辑」是并行入口，与台账职责重叠，且比台账更可见。
2. **契约不一致**：锁定契约/策略/验收路径要求台账为 released 可见入口，但发布基线与
   前端导航权威仍保留退役入口。
3. **编辑能力错层**：台账动作曾硬禁 `edit`，把可写能力推到「专门只读/编辑页面」，
   违背「权限驱动、非专门只读页面」。
4. **P3 编排索引约束**：台账表单槽绑 `view_project_overview_form`（1703），
   改绑会炸 `CONFIG_TARGET_STALE`（409）——见 `daily_dev_user_level_acceptance_20261005.md` §6.13/§6.14。
   因此编辑能力必须**追加**而非替换。
5. **投影缺陷**（上一轮清单范围）：字段可见性投影的 `visible:false / auth:"none"` 首次产生点已按
   通用投影责任修复，不放宽断言、不加付款模型特判。
6. **运行面缺陷（本轮新发现，关键）**：`menu_sc_project_ledger_group_v2`（分组名「项目台账」，
   锁定契约 `RELEASED_FOUNDATION`）被 `menu_product_project_wave1.xml` 置为 `active=False`，
   而 `menu_product_navigation_v2.xml` 又把 `menu_sc_project_project` 挂到该分组下。
   结果：**唯一入口「项目台账」在运行面被隐藏**，用户看到的是重复入口里那个「项目信息编辑」。
   契约与运行面在此处分叉；静态 guard 只校验契约内部一致性，不能发现运行面隐藏，故此前未被捕获。
   修复：在 wave1 对该分组显式 `active=True`（并注明契约依据），使运行面与锁定契约一致，
   已有库升级时同步收敛。不动其它 v2 分组退役（契约未声明它们）。

## 验证矩阵（命令 / 身份 / 结果）

| 层 | 命令 | 身份 | 结果 |
|---|---|---|---|
| L1 | `make verify.product.menu.contract_v1.guard` | dirty 工作区 | PASS（锁定契约内部一致 + 运行面校验位） |
| L1 | `make verify.product.menu.release_manifest_v2.guard` | dirty | PASS `centers=10 contract_pages=89 accounting_pages=6 total=89` |
| L1 | `make verify.contract.structure_lock` | dirty | PASS `domains=14 fingerprint=current` |
| L1 | `python3 scripts/release/test_locked_menu_policy_contract.py` | dirty | 18 tests OK（旧哈希与 90 计数已更新为 89） |
| L1 | `python3 -m unittest scripts.ops.test_promote_product_ten_center_policy` | dirty | 4 tests OK |
| L3 | `make local.dev.upgrade MODULE=smart_construction_core` | sc-local-dev/sc_dev_demo | 退役 menu/action/act_window.view 已删除；`local.dev.ready` + `local.dev.demo.authority` PASS |
| L3 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=core_extension_v2_finalize` | sc_dev_demo | 23 tests，0 failed |
| L4 | `make verify.frontend.professionalization.project_domain.runtime` | sc_dev_demo | PASS `actions=30 gaps=0`（台账 action 重新成为运行面） |
| L4 | `make verify.frontend.professionalization.{contract_domain,finance_center,reporting_center}.runtime` | sc_dev_demo | 均 PASS（兄弟报告过期已再生） |
| L4 | `make verify.frontend.professionalization.systemwide_coverage.runtime` | sc_dev_demo | PASS `runtime=93 covered=93 uncovered=0 gaps=0` |

负例控制：修复前 `project_domain.runtime` 以 `EXPECTED_DOMAIN_ANCHOR_MISSING`
（`action_sc_project_list`）失败，修复后同命令 PASS —— 证明该断言确能检出「唯一入口被隐藏」。

## 复用与未覆盖项

- 复用上一轮已通过的 `smart_core` 契约边界测试（`test_ui_contract_v2_boundaries.py`，122 tests OK）；
  本轮未改动其输入，直接沿用。
- **未覆盖（环境门控）**：`contracts/generated/product_view_structure_contract.json` 需在
  `local.clean` 车道再生（guard 强制 `runtime_profile=local.clean` / `sc_clean` / `demo_data=False`），
  本工作区无 clean 车道（新环境权威需单独授权 P4）。该基线在 main 上即已过期（仍含退役入口），
  非本分支回归；`verify.contract.view_structure` 不在 `ci.local.quick`，不阻断本批次。
- 挂载者独占 DENY：沿用既有结论，仅作为重建/快照车道阻断，不泛化为「环境全部通过」。

## 交付状态边界

- 批次验收：待独立复核后确认。
- 主线集成：未完成（未推送、未合并、未过远端必需检查）。
- 版本发布：未完成。
- 产品交付/用户视角验收：待日常开发服（`sc_demo`）受管升级 + 用户 `wutao/123456` 登录复核。

---

## 第二轮：承载完整性与声明漂移收口（用户指令：保留项目台账，编辑能力必须完整承载）

用户确认：保留「项目台账」为唯一入口；「项目信息编辑」的功能必须完整承载过来，从最基础的信息
在全系统产品面完整统一；编辑能力必须权限/契约驱动，不得保留专门只读页。

### 本轮变更

- `views/core/project_overview_views.xml`：台账「提交立项」按钮补 `groups` 声明。
- `tests/test_core_extension_v2_finalize.py`：新增两条**行为锁**——
  - `test_retired_project_edit_composition_is_fully_carried_into_the_ledger`：
    退役表单的**全部字段与按钮**都必须出现在台账表单（差集为空），
    且 `responsibility_ids` 保持 `editable="bottom"`；台账动作 context 仍 `create/delete=False`、
    `no_duplicate=True`、不再硬禁 `edit`。
  - `test_project_ledger_submit_button_binds_the_model_group_authority`：
    台账 `提交立项` 按钮声明的 `groups` 集合必须**等于** `project.project.action_sc_submit`
    方法源码中 `has_group(...)` 实际校验的集合。
- `scripts/verify/business_config_guard_inventory.py`：修复 `_target_body` 解析伪阳性——
  目标体被 `ifeq/else/endif` 包裹时，旧解析在首个非制表行停下，错误报告「缺少命令体」。
  新解析消费制表行、空行与 make 条件指令，并在 `verify.other` 处停止；新增 `_target_body_self_test`
  自检（条件体保留、普通体保留、无体目标不臆造、未声明目标不匹配）。
- `docs/frontend_productization/product-page-patterns-v1.md`：两处入口矩阵行加退役注记，
  指向唯一台账记录入口，不重写历史行。
- `make/dev.mk`：新增已注册门禁 `verify.contract.project_ledger_entry_carrier.orm`，
  按既有 `.orm` 范式复用注册的 `local.dev` 车道（`local.dev.ready` + `test.safe`），
  让承载锁成为可复跑、非零计数的定向证据，而非一次性运行。

### 新增根因

7. **声明漂移（组权限）**：台账「提交立项」按钮原先**无 `groups`**，但 `action_sc_submit` 方法硬校验
   `group_sc_cap_project_user/manager/super_admin`。结果：界面把按钮渲染给无权限用户 → 点击必失败。
   修复：按钮声明与模型校验面对齐（用锁测试钉住，不用文本出现证明正确性）。
8. **校验工具伪阳性**：`business_config_guard_inventory` 对 ifeq 包裹的目标体误报缺体，
   使 guard 结论不可信。修复解析并加自检。

### 本轮验证

| 层 | 命令 | 身份 | 结果 |
|---|---|---|---|
| L1 | `python3 scripts/verify/business_config_guard_inventory.py` | dirty | PASS `make_sources=17 scanned_files=36 assertions=151 negative_self_test=PASS` |
| L2/L3 | `make verify.contract.project_ledger_entry_carrier.orm` | sc-local-dev/sc_dev_demo | PASS `0 failed, 0 error(s) of 25 tests`（含新增两条承载/权限锁） |

### 承载完整性结论（登记口径）

- 退役「项目信息编辑」表单的字段集合、按钮集合 ⊆ 台账表单（`ONLY in retired = []`）。
- 台账记录页协作能力（chatter/attachments/followers/timeline/user_search_intent）与锁定契约一致。
- 编辑能力由入口 context（不再硬禁 `edit`）+ 字段分组 + ACL 驱动，不依赖专门只读视图。

### 未覆盖 / 复用

- 复用 0978c0cc 已通过的锁定契约/清单/结构锁 guard 与运行面 coverage 报告（输入未变）。
- `product_view_structure_contract.json` 仍需 `local.clean` 车道再生（环境门控，非本分支回归）。
- 日常库（`sc_demo`）受管回读仍待提交后执行：远端运行仓 `sc-root:/opt/projects/repos/sce-product-odoo`
  当前为 `0978c0cc`（detached、干净），尚不含本轮 groups 修复与承载锁。

---

## 续轮（2026-10-06）：运行契约承载锁 + 投影身份根因（P0）收口

- 记录时身份：HEAD `589d6a2d`（含 0978c0cc/589d6a2d 两笔）+ 本轮未提交工作区（单写者）。
- 本轮任务：把「声明层承载完整」推进到「**运行契约层承载完整**」，并修掉让运行契约丢失
  已声明字段的**通用投影责任**；不放宽断言、不加 `project.project` 特判、不用 `critical` 覆盖 ACL。

### 新增根因（P0 投影身份，非业务特判）

9. **投影源 token 对字段策略不敏感**：`smart_core` 的组装契约缓存以
   `build_projection_source_token` 为失效键。`ui.form.field.policy` 原先只按「最新一行的
   `write_date`」参与 token，而 `write_date` 是**秒级**且同事务内可完全相同：把一行从
   `active=True` 改为 `False`（A→B）时 token 不变，进程内热缓存与**库内持久化 source asset**
   （按 `asset_version=source_token`）继续命中 → 修复后仍投影出修复前的旧契约。
   修复：比照既有的 `ui.business.config.contract` 先例，`ui.form.field.policy` 改为绑定
   **model/action 范围内的定义集合**（`id/write_date/active/visible/field_name/action/sequence/
   label/role_group_ids`），任一字段策略的定义变化立即改变 token。按模型能力守卫（缺
   `field_name/visible/active` 字段时回退到原「最新行」逻辑），不改变其它模型行为。
10. **退役遗留 overlay 未随入口退役清理**：P2 服务
    `smart_construction_core/services/project_ledger_field_overlay_repair.py` 由**声明派生**
    台账必需字段集合（台账原生表单 ∪ 退役「项目信息编辑」表单的 `//field/@name`），只退役
    `model=project.project`、台账 action、`visible=False`、`active=True`、且字段∈必需集合的
    遗留行；幂等、单 action/model 范围，不触碰 ACL/记录规则/字段权限。迁移
    `migrations/17.0.0.170/pre-migration.py` 在升级时执行；受管入口
    `make project.ledger.field_overlay.repair`（默认 report，`PROJECT_LEDGER_OVERLAY_ACTION=apply` 执行）。

### 责任层声明（本轮增量）

- `addons/smart_core/utils/load_contract_response_cache.py`：P0 平台内核（契约缓存身份/投影机制）。
- `addons/smart_construction_core/services/|migrations/|__manifest__.py`：P1 标准产品面（唯一台账入口的承载修复）。
- `scripts/ops/repair_project_ledger_field_overlay.py` + `make/dev.mk`：P4 受管入口/证据载体。

### 本轮验证

| 层 | 命令 | 身份 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | dirty `589d6a2d` | PASS（仅 L1，建议 L2 定向） |
| L2 | `make verify.contract.project_ledger_entry_carrier.orm` | sc-local-dev/sc_dev_demo | PASS `29 tests 0 failed`（含运行契约承载锁 + stale overlay 检出/修复锁） |
| L2 | `make verify.business_config.formal_list.unit` | offline | PASS `122 + 7 + 51 + 5 = 185 tests`（含 cache 新增 2 条 token 锁） |
| L2 | `make verify.form_structure_authority_unification.unit` | offline | PASS `201 tests` |
| L2 | `make verify.business_config.guard_inventory` | offline | PASS `assertions=151 negative_self_test=PASS` |
| L3 | `make project.ledger.field_overlay.repair`（report） | sc-local-dev/sc_dev_demo | PASS `status=noop`，`required_fields` 含 `project_code` |

- 负例纪律：`test_stale_ledger_field_overlay_is_detected_and_repaired` 先断言**未注入基线**已承载
  `project_code`，再注入同形 stale 策略证明**确实丢失**（可检出），最后受管修复后**恢复**。
- 锁定的是「声明消费 + 实际投影行为」，不把选择器字符串/文本出现当正确性证明。

### 未覆盖 / 复用

- 复用 589d6a2d 前已通过且输入未变的离线 guard 与运行面 coverage 报告。
- 日常库 `sc_demo` 受管回读仍待提交后执行；本轮 P0 token 变更会连带使既有持久化 source asset
  在新 token 下自然失效，无需手工清缓存。

### 结构整理（同轮）

- 把台账「运行契约承载」两条锁从 `tests/test_core_extension_v2_finalize.py` 抽出为独立文件
  `tests/test_project_ledger_runtime_contract.py`（`@tagged("core_extension_v2_finalize")`，
  在 `tests/__init__.py` 注册），避免既有大测试文件因本轮新增而越过复杂度拆分阈值；
  同 tag 使 `verify.contract.project_ledger_entry_carrier.orm` 行为不变。

---

## 续轮（2026-10-06）：运行契约「声明消费」锁 + 两处承载边界裁决

- 记录时身份：HEAD `5d1dfaeb`（0978c0cc/589d6a2d/5d1dfaeb 三笔）+ 本轮未提交工作区（单写者）。
- 本轮任务：把「**声明（groups 等）必须在运行契约层被稳定消费**」钉成可回归的锁，并对两处
  疑似承载缺口给出**证据裁决**；不放宽断言、不加 `project.project` 特判、不用 `critical` 覆盖 ACL。

### 新增锁（P1 产品面的验证载体）

11. **按钮组权限的运行契约消费锁**：
    `tests/test_project_ledger_runtime_contract.py::test_ledger_submit_button_group_authority_is_enforced_in_the_runtime_contract`。
    用 `UiContractV2Handler` 直读同一台账 action 的 `layoutContract`，钉住两侧行为：
    - `member`（`base.group_user + group_sc_cap_project_read + {group_sc_cap_project_user,
      group_sc_cap_project_manager, group_sc_super_admin}`）运行契约**必须含** `action_sc_submit`；
    - `outsider`（`base.group_user + group_sc_cap_project_read + group_sc_cap_contract_read`，
      能正常解析同一契约但**不含**声明组）运行契约**必须不含** `action_sc_submit`，
      且**必须仍含**未加组约束的 `action_sc_start`（负例对照：证明"缺按钮"来自组权限，
      而不是契约整体解析失败）。
    锁的是**声明消费与实际行为**（按用户身份跑真实 handler），不以选择器字符串/文本出现为正确性证明。

### 裁决 A：退役表单的 `<chatter groups=...>` 不是台账的承载缺口（不修）

- 事实（本地 `sc_dev_demo` 直读 `UiContractV2Handler`，`/tmp/ledger_collab_probe.py`）：
  - 台账 action 运行契约 `runtimeContract.collaboration` = `{chatter, attachments, followers,
    timeline, sourceAuthority, user_search_intent}`，`chatter.enabled=True`、3 个 action，
    `attachments/followers/timeline` 均 `enabled=True`；退役 view 与之**逐项一致**。
  - 差异只在**布局节点**：退役 view 的 `layoutContract` 有 `chatter` 容器 token，台账为 `[]`。
- 判定依据：前端协作区的单一权威 `resolveCollaborationVisibility`（`contractRuntimeVm.ts`）
  明确「运行能力（capability）是布局节点的**替代**，不是可将其关闭的条件」；台账契约以
  **运行能力声明**承载协作面，由 `CanonicalNativeFormSurface` 在 `showCollaborationPanel` 为真时
  渲染，与退役页一致。前端读的是 `store.snapshot.runtimeContract.collaboration`
  （`app/contracts/v2/store.ts`），即**契约本身**。
- 无回归证明：`git show main:.../project_overview_views.xml` 中台账表单**本无** `<chatter>` 节点；
  本分支对台账的改动是**追加**资料维护区，未新增/移除 chatter 声明。退役页 `<chatter groups=...>`
  是**已退役入口**的布局区声明；唯一入口以运行能力承载同一能力，符合「运行时契约驱动」。

### 裁决 B：台账概览头部 5 个字段未带 `groups` 不是权限放宽（不修）

- 事实：静态比对两表单 `//field/@name -> groups` —— 退役表单 19 个字段挂
  `group_sc_cap_project_read`；台账资料区承载了其中 14 个的 `groups`（并集 ⊇ 退役），
  仅 `location/manager_id/operation_strategy/project_code/project_type_id` 在**概览头部**以
  无 `groups` 形式出现（`project_code` 在资料区**另有**一条带 `groups` 的声明）。
- 判定依据：台账唯一入口的菜单 `menu_sc_project_project` 自身 `groups="...group_sc_cap_project_read"`
  （`views/menu.xml:24`）——**能打开台账的用户必已具备 project_read**，故概览头部不重复声明
  不产生任何越权可见；`location` 在头部为 `invisible="1"`。属展示层归一，非权限放宽，
  符合「不覆盖合法隐藏规则、不放宽 ACL/字段权限」。

### 本轮验证

| 层 | 命令 | 身份 | 结果 |
|---|---|---|---|
| L1 | `make ci.local.iteration` | dirty `5d1dfaeb` | PASS（仅 L1，建议 L2 定向） |
| L2 | `make verify.contract.project_ledger_entry_carrier.orm` | local.dev/sc_dev_demo | PASS `32 tests 0 failed`（含新增组权限锁；`test_ledger_submit_button_group_authority_is_enforced_in_the_runtime_contract` 实际执行并通过） |
| L3 | 日常 `ui.contract.v2` 回读（wutao/123456，`rb_ledger506.json`） | daily/sc_demo@`5d1dfaeb` | `project_code` 在布局；`action_sc_submit` 状态契约 `visible=true/disabled=false`；`action_sc_start` `visible=false`（`ACTION_NOT_VISIBLE_IN_STATE`，状态驱动非权限）；`runtimeContract.collaboration.chatter.enabled=true` |
| L3 | 日常导航回读（governed `probe_login`，wutao） | daily/sc_demo@`5d1dfaeb` | PASS `nodes=111 actions=89 leaves=89 forbidden=[] required_miss=[]`；含「项目台账」，无「项目信息编辑」 |

- 复用：`5d1dfaeb` 已通过且运行面输入未变的 L2 结果（formal_list 185、form_structure 201、
  guard_inventory 151、field_overlay.repair noop、load_contract_response_cache 9）继续有效，
  本轮产品/运行面**零改动**（仅新增测试文件 + 文档/元数据），故日常部署 `5d1dfaeb` 仍为有效运行候选。

### 未覆盖 / 下一步

- 详情页 1440/390、明暗主题视觉核对与「点击打开 → 返回原记录 → 标签与动作恢复」真实交互，
  以及创建/编辑与工作台最小证据差额，仍待执行。
- `VIEW_STRUCTURE_BASELINE_CLEAN_LANE` 与运行环境 DENY 维持既有结论，未放宽。

### 补充：日常受管回读入口实跑结论（修正上面 L3 的口径）

- 上面 L3 两行是**受管探针模块 + 登记配置**的第一手诊断回读（wutao/123456），不是受管门禁入口。
  本轮补跑了登记入口 `make verify.daily_dev.acceptance.readonly.probe`（daily 契约实例
  `config/acceptance/backend_contract_instance_daily_v1.json`；`ACCEPTANCE_TARGET_SHA=5d1dfaeb`；
  以 `SC_ACCEPTANCE_RUN_ID` + `.runtime/gen_daily_confirmation.py` 生成 ≤10 分钟
  `daily-readonly-credential-confirmation.v1` 信封确认固定口令，未放宽任何审计/断言）。
- 结果：**runtime_identity PASS**（`served_sha == expected_sha == 5d1dfaeb`）；
  **login PASS**（wutao：`nodes=111 actions=89 leaves=89 forbidden=[] required_miss=[]`，
  role `business_config_admin`，含「项目台账」）；**contract custody FAIL**。
- FAIL 归因（与本轮候选**无关**，本轮仅新增测试 + 文档/元数据）：
  - `record_resolution_served_sha_mismatch`：daily 探针消费的是
    `ACCEPTANCE_RECORD_RESOLUTION=artifacts/backend/acceptance_record_identity.json`，
    该产物 `expected_sha=dfa6fa49`、companies `a=8/b=9`，而 daily 夹具身份
    `fixture_role_finance` 绑定公司 `[21,22]`；
  - 因此 `fixture_role_finance` 对解析出的 `payment_request` 目标（record 1849 / action 775 /
    menu 545）请求 `ui.contract.v2` 得到 **HTTP 403**，连带
    `request_target_binding/contract_custody_*/contract_schema_*` 未通过。
- 责任层：**P4 日常验收夹具车道**（daily 需用受管生产者在**服务中 SHA**下重生成 daily 作用域的
  record-identity 产物；daily 入口不应复用 acceptance profile 的解析产物）。
  不属本轮候选回归，保持 blocker `DAILY_ACCEPTANCE_CONTRACT_CUSTODY=pending_env_gated`。

### 更正：日常受管车道本身完整；缺的是「在服务中 SHA 重跑解析」这一步

- 上节把 FAIL 归因为「P4 车道缺口」**不准确**。实际是登记流程漏跑了一步：
  `make daily.dev.acceptance_contract.resolve`（`make/dev.mk:905`）——它要求
  `ACCEPTANCE_TARGET_SHA` 且校验 `served_sha == ACCEPTANCE_TARGET_SHA`，然后在
  `DAILY_DEV_ACCEPTANCE_DB=sc_demo`（`SC_ACCEPTANCE_FIXTURE_SCOPE=daily_dev`）上用受管生产者
  `scripts/verify/frontend_delivery_hardening_runtime_ids.py` 重写
  `ACCEPTANCE_RECORD_RESOLUTION`（默认 `artifacts/backend/acceptance_record_identity.json`，
  gitignored）。旧产物 `expected_sha=dfa6fa49`、companies `a=8/b=9` 是**上一个 SHA 的遗留**。
- 在 daily 主机按登记入口重跑解析后（`ssh sc-root` + `ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo`
  + `ACCEPTANCE_TARGET_SHA=5d1dfaeb`），产物更新为 `expected_sha=5d1dfaeb`、companies `a=21/b=22`、
  `payment_request` 目标 record 36154 / action 780 / menu 550。
- 随后在 daily 主机跑 `make verify.daily_dev.acceptance.readonly.probe`（wutao/123456 +
  ≤10 分钟 `daily-readonly-credential-confirmation.v1` 信封）→ **整体 PASS**：
  - `runtime_identity` PASS（`served_sha == expected_sha == 5d1dfaeb`）；
  - `login` PASS（wutao `nodes=111 actions=89 leaves=89 forbidden=[] required_miss=[]`，含「项目台账」）；
  - `contract` PASS（`fixture_role_finance` uid 210，公司 `[21,22]`，`resolved_sha == served_sha`，
    11/11 checks true，`http_status=200`（此前 403），custody `response_sha256=bb739fa2…`，
    `integrity_reason=ok`）；`[dev_acceptance_release_probe_schema_guard] PASS`。
- 结论：登记序列固定为 **resolve → probe**；产物按 SHA 失效属预期，不是审计放宽，也未改探针框架。

## 详情车道 FAIL 根因与修复（P0 渲染层：幻影脏字段）

### 现象与证据
- `detail-closeout-5ba6398e`（readonly 剖面）：`passed=true`、`denied_requests=[]`。
- `detail-closeout-5d1dfaeb`（edit 剖面）：`passed=false`，**8/8 记录全部通过**、`failures=[]`，
  但 `runtime.denied_requests` = 2 笔 `api.onchange`，`console_errors` = 2 条
  `net::ERR_BLOCKED_BY_CLIENT.Inspector`（被车道 fail-closed 拦截的 fetch）。
- 对照：`res.partner/8754`（可编辑、无 m2m tags）打开时**无任何 onchange** ⇒ 不是"所有可编辑表单都会触发"。

### 根因链（已钉死）
1. 编辑权限翻转（`5d1dfaeb` 后 `project.project,581` 为 `edit`）是**正确的权限驱动结果**，
   它只是让各字段 setter 从"被 `isFieldWritable` 短路"变为真正可达。
2. `ProfessionalManyToManySelect` 的 `selectedIds` setter / `onChange`
   → `adapter.setRelationIds` → `useRecordFormState.setRelationIds`，在挂载回写时
   传入**与记录基线完全相同**的 id 集合；实测请求体 `tag_ids=[[6,0,[]]]` ⇒ 数值未变。
3. 旧实现 `markFieldChanged` **无条件**加入 `dirtyFieldSet`，并按
   `fieldRequiresServerOnchange`（该字段有 `field_x_show/hide` 生成的
   `{sourceWidgetId:"field.tag_ids", dispatchMode:"server", intent:"ui.form_field_policy.set"}` 配置规则）
   加入 `changedFieldSet` → 300ms 后发出 `api.onchange`。
4. 观测车道 `dailyReadonlyRequest` 白名单不含 `api.onchange` → fail-closed 记 denied。

结论：**这是消费端臆造语义**——契约只声明了权限与字段策略，从未声明"变更意图"；
`markFieldChanged` 把"setter 被调用"当成"值已变化"。

### 修复（P0 泛化渲染职责，无特判、无 ACL 覆盖、无断言放宽）
- `frontend/apps/web/src/pages/contractForm/useRecordFormState.ts` 新增 `syncFieldDirty`：
  仅当 `comparableFieldValue(当前草稿值) !== comparableFieldValue(契约下发的记录基线)` 才标脏/派发；
  回退到基线会清脏、清 `changedFieldSet` 并在其空集时取消待发 onchange 定时器。
- 值 setter（`setBooleanField`/`setMany2oneField`/`setRelationIds`/`setSelectionField`/
  `setTextField`/`setTechnicalCompanionTextField`）改用 `syncFieldDirty`。
- `commitMany2oneInline` 的**显式意图**路径仍用 `markFieldChanged`（该处确有待创建关联，语义未削弱）。
- 比较只使用契约下发的记录基线数据，不推导权限/字段策略；无 `project.project`/`tag_ids` 特判。

### 验证（负例先行）
- 新增 `frontend/apps/web/scripts/contract_form_dirty_semantics_test.ts`
  （目标 `verify.frontend.contract_form_dirty_semantics.unit`，沿用既有 esbuild+node 单测形态，未引入新框架）。
- **负例证明**：同一测试对修复前源码**失败**
  （`AssertionError: an identical relation value must not be dirty`，`1 !== 0`）；修复后 `PASS`。
- 定向 L2 全过：`contract_form_collaboration_authority`(102) / `record_form_return`(18) /
  `professional_relation_field` / `professional_relation_lifecycle`；`typecheck` 通过、`lint:src` 0 error。
- 与本改动无关的**预存在**失败：`verify.frontend.contract_form_save_failure_recovery.unit`
  在 HEAD 上同样报 `boundSurfaceKey` 上下文缺字段，未改动。

### 责任层归属
- 该修复属 **P0 前端渲染机制**（通用契约消费/渲染责任），非 P1 业务语义，非 P2 客户偏好。

- 产品修复提交：`fix(frontend): 契约基线值比较消除幻影脏字段(P0 渲染层)`（前端源码 + 负例单测 + make 目标，一笔）。

## 后端场景化边界收口：`协作记录 + 历史审计` 合并为契约声明的 surface

### 用户裁决
- 审计入口给特殊角色，出现与否**必须契约 + 角色权限驱动**；"有数据定义、没有权限也不应该出现"。
- 后端"场景化"（scene/layout/surface 三条线）界限要一次性定死，不再反复。

### 根因（此前两条入口 + 可见性漂移）
1. `协作记录`/`历史审计` 从未出现在 `ui.contract.v2 → formStructureContract.sourceSectionTitles`
   （交付报告内两词出现 0 次）：两个标签都是前端自造。
   - `nativeSectionNavigation.ts` 旧 `workspaceSurfaceNavigationItems()` 硬编码两个顶层条目。
   - `ObjectTaskPage.vue` 另有一份硬编码 `surface:activity`/`surface:audit` 导航条目。
2. 审计区块可见性由**运行时数据**决定：
   - `ContractFormDriverHost.vue` 旧 `auditAvailable = showCollaborationPanel && auditEvents.length > 0`；
   - `NativeCollaborationPanel.vue` 旧 `v-if="showAuditTimeline !== false && auditEvents.length"`。
   ⇒ 时间线未加载时少一个页签（light/dark 差异）、无审计角色的用户也能看到该区块。
3. 同一语义存在两个顶层入口（`协作记录` 与面板内 `历史审计`），任务模式与工作区模式布局不一致。

### 边界（新增 `docs/architecture/form_structure_surface_contract_boundary_v1.md`）
| 层 | 载体 | 负责 |
| --- | --- | --- |
| 场景/导航 | `scene_ready_contract`/`system.init.nav` | 菜单、action、scene 身份 |
| 页面契约 | `ui.contract.v2` 快照 | 单个 (scene, action, model, view, record, role, company, lang) 的投影 |
| 布局 | `layoutContract` | Odoo 原生视图元素的位置（容器树） |
| 状态/动作/数据 | `statusContract`/`actionContract`/`dataContract` | 权限状态、动作、数据源 |
| 语义结构 | `formStructureContract`（`projection_only`） | 槽位、字段角色、**声明的 surfaces** |
| 角色/能力 | `res.groups` + 能力注册表 | 谁能用哪个能力 |

`scene_key` 在 `ui.contract.v2` 中只作绑定/授权校验与入口身份，**不是页面 body 的权威**；
非字段区块只能声明在 `formStructureContract.surfaces`，不得放进 layout，也不得从 scene 推导。

可见性单一规则（唯一方向）：
```
visible = 契约声明该 surface
          AND (无 audit 子声明 OR audit.authorization.state == 'allow')
          AND 无其它已声明治理规则压制
```
运行时数据永远不是可见性权威。

### 三层落地
- **smart_core（机制）**：`ui_contract_v2.py` 新增 `FORM_STRUCTURE_SURFACE_POLICY_HOOK`、
  `project_form_structure_surfaces()` 与归一化函数；四处 `form_structure_contract` 统一加 `"surfaces"`；
  hook 无声明时**只回退模型能力区块（activity），绝不声明 audit**，且不出现任何产品能力键。
- **smart_construction_core（策略）**：hook `smart_core_form_structure_surface_policy` 声明 activity surface，
  其 `audit.authorization` 复用能力注册表 `capability_authorization_for_user(user, "governance.runtime.audit")`
  （未声明能力 → `deny/UNDECLARED_CAPABILITY`），与 `system.init.capabilities` 同源。
- **前端（只消费）**：`schema.ts` 严格解码 `surfaces`（未知键/未知 state 抛 `ContractV2DecodeError`）；
  `store.ts`/`contractRuntimeVm.ts` 提供 `resolveContractV2FormStructureSurfaces`、
  `declaredCollaborationSurface`、`declaredAuditAuthorized`；`ContractFormDriverHost`、
  `ObjectTaskPage`、`CanonicalNativeFormSurface`、`NativeCollaborationPanel` 全部改为声明驱动，
  硬编码标签/`auditEvents.length` 判定清除；`surfaces === undefined`（契约无法声明）才走 legacy 路径。
- **契约文档同步**：`form_structure_contract_v2.md` 补充 `surfaces` 说明；
  规范 schema `unified_page_contract_v2.schema.json` 增加 `formStructureSurface*` 定义（`additionalProperties:false`）。

### 验证（负例先行，均为真实模块执行）
- 新增 `frontend/apps/web/scripts/form_structure_surface_contract_test.ts`
  （目标 `verify.frontend.form_structure_surface_contract.unit`，esbuild+node 形态，未新增框架）：
  真实解码 + 真实 store 解析 + 真实投影函数；覆盖 (a) 无声明、(b) 声明但 `deny/pending/coming_soon`、
  (c) 声明且 `allow`（含空时间线仍渲染）、标签取自声明、未知键/未知 state 必须解码失败。
  **负例证明**：把 `declaredAuditAuthorized` 换成"声明即授权"后同一测试 FAIL。
- 后端 `addons/smart_core/tests/test_ui_contract_v2_boundaries.py` 新增
  `FormStructureSurfaceBoundariesTest`（5 项，共 127 passed）：平台回退不得声明 audit、
  声明归一化（含 `reason_code→reasonCode`）、畸形/重复声明被丢弃、未知 state 不得变 allow。
  **负例证明**：把未知 state 改成 `allow` 后该测试 FAIL。
- 夹具负例证明：schema 去掉 `surfaces` 后 `verify.unified_page_contract.v2.assembler`
  FAIL（`Additional properties are not allowed ('surfaces' was unexpected)`），恢复后 PASS。
- 守卫更新（由文本断言升级为声明消费断言，不引入新框架）：
  `frontend_form_canvas_wide_grid_guard.py`、`frontend_professional_audit_guard.py`、
  `frontend_v2_policy_projection_guard.py`（新增 `coming_soon` 白名单 + 绑定后端能力治理生产者）。

### 责任层归属
- 机制/归一化/契约键：**P0 platform kernel product（`smart_core`）**。
- surface 声明与审计能力键：**P1 construction industry standard product（`smart_construction_core`）**。
- 渲染消费：**P0 前端渲染机制**（通用契约消费，无产品特判）。

## 后端场景化边界收口（scene / surface 命名与权威，2026-10-06 续）

### 事实（排查结论）
- `scene` 一词在后端承担**三个不同对象**：S1 导航通道 `sc.menu.config.scene`
  （`web/pm/finance/mobile`，P0）、S2 业务场景身份 `scene_key`（P0 `smart_scene`
  内核 + P1 `smart_construction_scene` 内容）、S3 发布场景快照
  `sc.scene.snapshot`/`release_surface_scene_contract`（P0 delivery）。
- `surface` 一词承担**四个不同对象**：F1 `contract_surface`（user/native）、
  F2 `role_surface`（`system.init.role_surface`）、F3 交付面 `scene_surface`
  （交付策略白名单）、F4 `formStructureContract.surfaces`（本批新增声明面）。
- 绕的根因不是缺机制，而是缺一张总表；同一对象在不同层被复读。

### 已钉死的边界（文档 + 行为锁）
- 新增 `docs/architecture/backend_scene_surface_authority_boundary_v1.md`：三对象/四对象总表、
  三条硬规则（R1 页面体只来自 `ui.contract.v2`，`scene_key` 仅绑定授权；R2 入口由
  scene-ready + 交付面 + 角色能力共同决定；R3 可见性单条 fail-closed）。
- 新增 `addons/smart_core/tests/test_backend_scene_surface_boundary.py`
  （目标 `verify.backend.scene_surface_boundary.unit`，10 项）：**执行投影函数**断言
  排除原因码闭集、已注册交付面白名单 fail-closed、`_normalize_surface` 开放命名空间的已知边界。
  **负例先行**：把 `_select_surface_policy` 注入为恒 `enabled=False` 后，已注册面两例立即 FAIL。

### 登记为待裁决缺口（不掩盖、不放宽）
- **未注册交付面 fail-open**：`_normalize_surface` 开放命名空间 + 未注册面
  `_select_surface_policy` 返回 `enabled=False`，导致调用方（含传入业务 `scene_key`）
  可绕过 F3 交付白名单。角色/能力门仍生效，但只声明 `delivery_mode` 的场景会多出。
  收紧为 fail-closed 属产品可见性决策，登记 `SCENE_SURFACE_UNREGISTERED_FAIL_OPEN=decision_pending`。
- **交付策略默认关闭** fail-open 已作为显式边界在测试中锁定（`smart_construction_scene`
  已 seed `sc.scene.delivery.policy.enabled=1`），不作为"环境通过"依据。
- S1 由 S2 前缀推导、`SURFACE_POLICY_FILE_DEFAULT` 指向不存在的策略文件，均登记待收敛。

### 本批定向验证（未变的通过证据继续复用）
`verify.backend.scene_surface_boundary.unit`、`verify.frontend.form_structure_surface_contract.unit`、
`verify.frontend.form_structure_contract_projection.unit`、`verify.frontend.native_section_navigation.unit`、
`verify.frontend.contract_form_collaboration_authority.unit`、`verify.frontend.native_form_structure_responsibility.unit`、
`verify.form_structure.contract.guard`、`verify.unified_page_contract.v2.assembler`、
`verify.unified_page_contract.v2.stable_projection`、`verify.unified_page_contract.v2.guard_inventory`、
`verify.frontend.contract_v2_render_authority.unit`、`verify.business_config.formal_list.unit`、
`verify.frontend.contract_form_dirty_semantics.unit` 全绿。

### 预存在无关失败（非本批引入，勿归因本改动）
`verify.form_view.native_structure.boundary_guard` 期望 `NativeFormTreeRenderer.vue` 含
`if (authoritativeBusinessSectionMode.value) return '';`，该 token 在本分支 HEAD 与本机 `main`
均已缺失；本批未触碰该文件。登记为预存在漂移，待独立处理。
