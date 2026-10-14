# FE-CONTRACT-RUNTIME-02 · 运行时视图结构兼容收口（2026-10-14）

范围：修复目标环境 `daily.runtime.published_face.converge` 在 main `a2c3971179` 上的部署阻断，
并把该节点恢复到已提交的权威视图结构基线。**不是**新页面、新组件、语义能力扩展或基础镜像升级。

## 1. 触发事实

| 项 | 值 |
|---|---|
| 部署入口 | `make daily.runtime.published_face.converge`（`EXPECTED_SHA=a2c3971179…`，login `wutao`） |
| 结果 | `MODULE_UPGRADE_FAILED` |
| 失败节点 | `smart_construction_core/views/core/cost_domain_views.xml:562`，视图 `project.progress.entry.tree` 定义无效 |

前 3 步（bundle sync → source_revision align → frontend build）均 PASS，部署树与 served revision 已是 `a2c39711`。

## 2. 根因（三条独立证据）

1. **基础镜像 RNG 差异（字节级）**：`addons/base/rng/common.rng` 的 `<rng:define name="field">` 内
   `<rng:optional><rng:attribute name="help"/></rng:optional>`：
   - 本地镜像 `odoo17-odoo:latest`（`17.0-20260630`）：该 define 内 `help` 出现 4 次；
   - 目标镜像（`17.0-20251222`）：同一 define 只有 3 次，**缺这一行**。
   `tree_view.rng` 通过 `<rng:ref name="field"/>` 复用它，所以列表列上的 `help` 本地可校验、目标机被拒。
2. **全仓唯一性**：对 HEAD `a2c39711` 扫描全部 RNG 校验型视图（tree/list/search/kanban/pivot/graph/calendar/
   gantt/activity）内带 `help` 的 `field`，命中 **恰好 1 处**，即上述节点。→ 无需扩大改动面。
3. **契约基线漂移**：已提交基线与实测哈希一致地证明该属性从未属于权威结构：
   - 基线节点载荷 `{"attrs":{"name":"progress_rate","type":"float"},"tag":"field"}`
     → `value_sha256 = a2084c5e4d1b86947e16f70bda1c79902e91248a0dbdaa89c3c1a95a12de2bde`（与基线文件逐字相同）；
   - 含 `help` 的载荷哈希不同。基线最后更新于 `d3bdb3aa`（PR #399，早于 PR #654）。
   → PR #654 修改了视图结构输入却**未重新生成** `contracts/generated/product_view_structure_contract.json`，
   代码与自身契约静默分叉。

## 3. 修复

```
- <field name="progress_rate" help="累计完成比例（0–100）。例如 35 表示 35%。" />
+ <field name="progress_rate"/>
```

- 该属性仅用于列表表头 tooltip（`web.ListHeaderTooltip`），移除不改变字段、标签、模型文档与任何业务能力；
  python 侧 `progress_entry.py::progress_rate` 的字段说明保持不变。
- 修复后解析结构重新等于权威基线，**无需**改写基线文件。
- 备选路径（保留 tooltip 需升级目标基础镜像）不在本棒范围；如需，应作为独立交付项由所有者裁定。

## 4. 验证与状态

见本棒结果索引 `.agent/runs/FE-CONTRACT-RUNTIME-02-VIEW-STRUCTURE-COMPAT/run.json`。
状态边界：本棒只做到「批次验收 / 主线集成 / 部署到目标环境」中实际通过的层级；
**不得**报「产品交付完成」。

## 5. 本棒新增证据：目标语法本地复现 + 全仓扫描

### 5.1 方法

不部署、不写目标环境：把**目标镜像**（`odoo17-odoo:17.0-20251222`）的 RNG 语法只读取回本地
（`docker exec … cat …/base/rng/*.rng`），在本地容器内用 lxml `RelaxNG` 以**目标语法**校验本地代码。
等价于在本地复现目标机在模块升级时执行的视图结构校验。

### 5.2 单节点前后对照（`view_project_progress_entry_tree`）

| 语法来源 | 修复前（含 `help`） | 修复后 |
|---|---|---|
| 目标 `17.0-20251222` | **INVALID** `RELAXNG_ERR_EXTRACONTENT: Element tree has extra content: field` | **VALID** |
| 本地 `17.0-20260630` | VALID | VALID |

第二行解释了本缺陷为何长期不可见：本地基础镜像语法更宽松，本地升级/校验**不可能**发现它。
因此「本地升级通过」不构成目标兼容证据，本棒不以本地结果替代目标验收。

### 5.3 全仓扫描（证明改动面已闭合）

范围 `addons/ + addons_external/ + demo_addons/`（371 个 XML），命中 432 个受 RNG 校验的 view arch
（`tree/search/graph/pivot/calendar/activity`），逐条以**目标语法**校验：

| 版本 | invalid |
|---|---|
| 修复前（HEAD `a2c39711`） | **1**（即该节点，与目标失败同一错误） |
| 修复后（本候选） | **0** |

→ 目标升级此前停在该视图；修复后同类节点在目标语法下已为零。

### 5.4 与本次改动无关、本轮**不**处理的既有红

1. **`local.dev.upgrade`（sc_dev_demo）**：升级到 demo 场景种子
   `smart_construction_demo/data/scenario/s60_project_cockpit/10_cockpit_business_facts.xml:3` 时
   `ir.rule` 抛 `AccessError`（被 convert 包成 `ParseError`）。属于数据范围规则与 demo 种子的既有红，
   与本视图改动无关，本轮不放宽任何守卫、不修。本地 dev 环境未留坏状态（`make local.dev.health` PASS）。
2. **目标库不受该红影响**：`sc_demo` 的 `smart_construction_demo = uninstalled`
   （`smart_construction_core`/`smart_core` = installed），目标升级路径不加载 demo 场景数据。
3. **`verify.contract.view_structure` / `gate.contract.view_structure` 在 main 上恒红**：PR #654 改了
   菜单策略（`menu_sc_product_project_edit_v1` → `menu_sc_project_project`）却未重新生成
   `contracts/generated/product_view_structure_contract.json`，守卫先校验基线自身，故在 main 上即失败。
   非本改动引入；本轮不改写权威基线，也不把它当成本改动的 owning gate。

### 5.5 本棒的验证分层

| 层 | 入口 | 结果 |
|---|---|---|
| L0 身份 | 分支/HEAD/工作区指纹 | `fix/fe-contract-runtime-02-runtime-view-compat` @ `a2c39711` + 显式脏区 |
| L1 静态 | 目标语法 RNG 校验（本地复现） | 修复前 1 invalid → 修复后 0 invalid |
| L2 定向 | `verify.product_view_structure.contract.unit` | PASS 25 |
| L2 定向 | `verify.contract.structure_lock` | PASS（fingerprint=current） |
| L1 入口 | `make ci.local.iteration` | PASS（`change_state=dirty`，L1 only） |
| L3 目标 | `daily.runtime.candidate.bundle_sync` → `daily.runtime.published_face.converge` | 见 §6 |
| L3 本地 | `local.dev.upgrade` | 未通过，原因无关（§5.4.1），已声明不阻塞 |

> 显式声明的跳过层：`gate.contract.view_structure`（权威基线自身在 main 上红，见 §5.4.3）；
> `local.clean.view_structure_gate`（同一守卫，同因）。

## 6. RUNTIME-BOUNDARY-FIX-03 · 预览面发布快照口径修复

### 6.1 触发事实

视图修复让目标环境 `smart_construction_core` 升级成功（`construction.standard` 快照 id 97 生成），
但同一次 `daily.runtime.published_face.converge` 在下一步失败：

```
LockedMenuPolicyContractError: LOCKED_MENU_SNAPSHOT_MISMATCH:
construction.preview contains non-released snapshot page
```

### 6.2 根因

PR #654 引入了新的锁定 P1 产品定义
`addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json`，其
`product_policy_profiles` / `delivery_rule` 明确声明：`construction.standard` = 已正式发布条目；
`construction.preview` = 已发布 + 显式 `preview` 条目（实测 90 released + 39 preview）。
但 `scripts/release/initialize_colocated_platform_snapshot.py` 冻结后的后置断言仍是「只允许 released」的
`assert_snapshot_matches_locked_contract`，会把任何 preview 页判为不合法。

运行期权威 `scripts/verify/production_menu_release_gate_guard.py`（决定入口能否打开的那道门）**早已**使用宽容口径
`assert_snapshot_matches_policy_release_states`。因此不是声明错了，而是**初始化器滞后于已声明的交付规则**。

### 6.3 修复

```python
- post_snapshot_match = assert_snapshot_matches_locked_contract(contract, product_key, pages)
+ post_snapshot_match = assert_snapshot_matches_policy_release_states(
+     contract, product_key, pages, policy.menu_groups,
+ )
```

- 口径：快照不得出现 `{released, preview}` 之外的页面；released 页严格等于锁定基线；preview 页严格等于策略声明的 preview 集合。
- 未放宽：未声明的、hidden/retired 的页面仍然 fail-closed（`others` 与 preview 增/缺检查）。
- 报告键：`snapshot_menu_count` 语义不变（= released 计数），新增 `snapshot_preview_page_count` /
  `snapshot_effective_page_count`；`snapshot_normalized_sha256` 取 `released_normalized_sha256`。
- 绑定测试 `scripts/release/test_production_colocated_release.py` 同步断言新后置门且必须收到 `policy.menu_groups`。

### 6.4 验证分层

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `python3 -m py_compile scripts/release/initialize_colocated_platform_snapshot.py` | PASS |
| L1 | 真实基线本地复算：`construction.standard` released=90/preview=0；`construction.preview` released=90/preview=39 | 声明口径 PASS；旧 released-only 门报 MISMATCH（符合预期） |
| L2 定向（记账 check `published_face_snapshot_contract`） | `make verify.role_surface.landing.contract.unit` | PASS 33 |
| L2 定向（记账 check `published_face_gate_parity`） | `make verify.product_menu_release_gate.contract.unit` | PASS 8 |
| L2 诊断 | `python3 scripts/release/test_production_colocated_release.py` | PASS 27（诊断级，见 6.5） |
| L1 入口 | `make ci.local.iteration` | PASS（四个 check 全部 reusable） |
| L3 目标 | `daily.runtime.candidate.bundle_sync` → `source_revision.align` → `published_face.converge` | 见 §7 |

### 6.5 声明：绑定测试的 owning target 在 main 上红（非本改动）

唯一运行该绑定测试的已登记入口是 `verify.production.release_contract`。它在 main `a2c39711` 与 HEAD `45796be9`
上都会失败，且与本次改动无关：

```
scripts/release/test_production_release_contract.py::test_admin_identity_tool_has_a_python310_ci_runtime_gate
  requires 'needs: [professional_authorization, python310_runtime_compatibility]'
  in .github/workflows/professional_quality_gate.yml
```

而该 workflow（最后一次变更是 PR #646，本分支未改动）里 `professional_quality_gate` 只有
`needs: professional_authorization`；57 个用例中 56 个通过。这属于 CI workflow 定义与其契约测试之间的**既有主线红**，
本棒不放宽、不修。

因此本棒的记账 check 绑定到能通过、且真实覆盖共享契约函数与运行期权威口径的两个窄入口；
绑定测试保留为**诊断观察**。为它补一个独立可登记的窄 verify 入口属于 P4 工具缺口，不阻塞本次部署修复。

## 7. RUNTIME-BOUNDARY-FIX-04 · 发布面收敛校验器口径 + 目标环境收敛结果

### 7.1 触发事实

FIX-03 生效后，目标环境两个产品快照都按声明口径生成（standard id=100 released 90 / preview 0；
preview id=101 released 90 / preview 39），但同一条 `daily.runtime.published_face.converge` 改为报：

```
PUBLISHED_FACE_SCOPE_DRIFT
snapshot=[{construction.standard: released 90, policy 90, gate 90},
          {construction.preview:  released 90, policy 90, gate 129}]
```

### 7.2 根因（与 FIX-03 同一交付规则口径的第二处残留）

`scripts/ops/daily_runtime_published_face_converge.py` 的**远端片段**和**本地二次校验**都要求：

```
snapshot_released_page_count == policy_released_menu_count == gate_page_count
```

preview 产品的 gate 页数按锁定 P1 定义应为 released+preview（129），于是**正确收敛**的快照被判为漂移。
运行期决定入口能否打开的 `production_menu_release_gate_guard.py` 一直使用 released+preview 的有效口径，
只有收敛校验器滞后。

### 7.3 修复

两处断言统一改为锁定 P1 产品定义的声明口径：

```
snapshot_released_page_count == policy_released_menu_count
snapshot_preview_page_count  == policy_preview_menu_count
gate_page_count              == policy_released_menu_count + policy_preview_menu_count
```

`products` 记录新增 `policy_preview_menu_count` / `snapshot_preview_page_count`。
未声明的 preview、对不上的 preview 计数、不等于有效总量的 gate 仍 fail-closed；released 页仍严格等于策略声明。
新增两条反例测试：合法 preview 口径被接受、gate 忽略声明 preview 被拒。

### 7.4 目标环境收敛结果（实跑两次）

第一次（候选树 `f12fc5fa`，本脚本尚为脏区）：

| 产品 | snapshot_id | released | preview | gate | guard |
|---|---|---|---|---|---|
| `construction.standard` | 100 | 90 | 0 | 90 | PASS |
| `construction.preview` | 101 | 90 | 39 | 129 | PASS |

`upgrade_mode=run`（`smart_core` + `smart_construction_core` 均完成升级）。

第二次（把候选 bundle 与 served revision 同步到已提交的 `8fff184a`，两侧同一 SHA，作为最终部署证据）：

| 产品 | snapshot_id | released | preview | gate | guard |
|---|---|---|---|---|---|
| `construction.standard` | 102 | 90 | 0 | 90 | PASS |
| `construction.preview` | 103 | 90 | 39 | 129 | PASS |

`upgrade_mode=reused`（`smart_core` tree `b3058e0d…`、`smart_construction_core` tree `5ee929a6…` 与上次收敛逐字相同），
`expected_sha = head = 8fff184a076480d020a5df20466a22dea5a50635`，`guard_status=PASS`。

### 7.5 本棒最终验证分层

| 层 | 入口 | 结果 |
|---|---|---|
| L1 | `make ci.local.iteration` | PASS（五个 check 全部 reusable） |
| L2 定向 | `verify.role_surface.landing.contract.unit` | PASS 33 |
| L2 定向 | `verify.product_menu_release_gate.contract.unit` | PASS 8 |
| L2 定向 | `verify.daily.runtime.published_face.converge` | PASS 24 |
| L2 诊断 | `python3 scripts/release/test_production_colocated_release.py` | PASS 27 |
| L3 目标 | `daily.runtime.candidate.bundle_sync` → `source_revision.align` → `published_face.converge` | **全部 PASS**（§7.4） |

结论：**批次验收完成**；目标环境部署（候选 bundle 同步 + 服务版本对齐 + 发布面收敛）已完成。
主线集成与产品交付分别以 PR #655 合并、目标环境真实角色/公司/权限用户验收为准，尚未声明。

## 8. 主线集成与目标环境最终对齐

### 8.1 受保护 PR 合并

| 项 | 值 |
|---|---|
| PR | #655 `fix/fe-contract-runtime-02-runtime-view-compat` → `main` |
| 候选头 | `6e60001ba94e7058029750f713514e6886c82099` |
| 必需检查 | `frontend_release_gate` / `merge_policy_gate` / `public_guard` / `professional_quality_gate` 均 success（绑定该候选头） |
| 合并前本地门 | `pr.merge.local_quick_gate` 证据未命中 → fail-closed 回退执行 `ci.local.quick`（8 分片全 PASS 并落证据） |
| 合并方式 | squash，合并提交 `17d148ad7a647afc6c79301ac409ad0dbc1177ae` |

> 状态：**主线集成完成**（合并提交已回读）。**合并不等于部署**，部署见 8.2。

### 8.2 目标环境对齐 main（部署）

| 步 | 入口 | 结果 |
|---|---|---|
| 1 | `make daily.runtime.main.bundle_sync` | PASS，`normalized_from_candidate=true`；目标树由 detached 候选 `8fff184a` + `refs/heads/main a2c39711` 归一为 `main 17d148ad` |
| 2 | `make daily.runtime.source_revision.align` | PASS；`served.source_revision` `8fff184a` → `17d148ad`，`.env.dev.bak` 已留，restart 成功 |
| 3 | `make daily.runtime.published_face.converge` | PASS；`upgrade_mode=reused`，`guard_status=PASS` |

最终部署证据（main `17d148ad`）：

| 产品 | snapshot_id | released | preview | gate | guard |
|---|---|---|---|---|---|
| `construction.standard` | 104 | 90 | 0 | 90 | PASS |
| `construction.preview` | 105 | 90 | 39 | 129 | PASS |

### 8.3 三态结论

| 维度 | 结论 |
|---|---|
| 批次验收 | **完成**（L1 + 三条 L2 定向 + 目标环境收敛；五条记账 check 全部 reusable） |
| 主线集成 | **完成**（PR #655 squash 合并 `17d148ad`，必需门 success） |
| 版本发布/部署 | **完成**（目标环境 `sc_demo` 服务版本、候选树、发布面均为 main `17d148ad`） |
| 产品交付 | **未声明**（目标环境真实角色/公司/权限用户验收仍待执行） |
