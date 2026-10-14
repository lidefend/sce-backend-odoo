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
