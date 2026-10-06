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
