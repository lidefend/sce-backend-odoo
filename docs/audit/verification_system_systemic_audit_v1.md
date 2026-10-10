# 验证体系系统性审计 v1

- 责任层：**P4 运维 / 交付工具**（`make/`、`scripts/`、`.github/workflows/`、证据工具）。
  本审计不改动 P0-P2 产品代码，不放宽任何门禁、断言、ACL、字段权限或负例。
- 审计身份：`audit/daily-dev-mainline-product-acceptance-closeout-20261009`，
  HEAD `2c61584e`，树 `2cc0c6fa`（与 main `282b079c` 树一致）。
- 度量工具：`scripts/audit/verification_lane_coverage.py`，冻结基线
  `scripts/audit/verification_lane_baseline.json`，入口
  `make audit.verification.lane_coverage`。

---

## 0. 结论（先读这一段）

**不是验证"过头"，是验证表面积失控。**

真正的强制内核很薄：4 个门禁锚点、合计可达 144 个 target。其余 93.4% 的 make target
不被任何门禁执行，其中 342 个在全仓库没有任何引用。与此同时，**本地精确 head 车道
（`ci.local.quick`）与远端必需门禁互不包含**：73 个守卫只被本地车道执行，80 个脚本
只被远端执行。

三条由此确定的结论：

1. **"CI 绿"不等于"契约未被破坏"。** `contract_governance_*_split_guard`、
   `construction_core_extension_*_split_guard`、`contract_form_*` 等契约治理守卫
   完全不在远端门禁里，只在本地 Quick 执行。契约驱动架构的强制点目前**不参与 PR 合并判定**。
2. **"CI 绿"不等于"本地会绿"，反之亦然。** 双向漂移使任何一次通过都无法作为另一次
   的复用证据，这是"反复重跑"与"越到后面越慢"的直接机制来源。
3. **防线薄 + 长尾大，是最差组合。** 出问题的是长尾（无人归属、无人度量），不是门禁本身
   过严。治理方向只能是**减法 + 单一来源**，不是再加守卫。

---

## 1. 审计方法与可复现性

度量口径全部机器化，不依赖人工叙述：

| 维度 | 口径 |
| --- | --- |
| target 清单 | 解析 `Makefile` + `make/*.mk`，排除变量赋值、指令行、recipe 行、`%` 模式规则 |
| 依赖图 | 规则前置项 + recipe 内 `$(MAKE) <target>` 递归调用 |
| 车道可达性 | 从声明的车道入口做传递闭包 |
| 门禁锚点 | `scripts/verify/registry.yaml` 的 `gate_anchors` |
| 脚本引用 | recipe 中的 `scripts/**.{py,sh,js}` 路径 + 全仓库 token 级字面量索引 |

复现命令：

```bash
make audit.verification.lane_coverage            # 人类可读摘要
python3 scripts/audit/verification_lane_coverage.py --json /tmp/coverage.json
make audit.verification.lane_coverage.check      # 债务棘轮（只允许缩小）
```

> **方法学更正（必须记录）**：本审计早期版本用 `grep -rn "test.inventory"` 判定"零引用"，
> 而 `.` 在正则中是通配符，会把散文 "test inventory" 也判为命中，产生假阳性。
> 现行实现改用 **token 精确匹配**（`[A-Za-z0-9_][A-Za-z0-9_.\-]*` 词元相等），
> `test.inventory` 这类目标不再被误判。任何"零引用"结论都必须用 token 精确匹配复核。

---

## 2. 实测事实

> **本节是批次 A 之前的快照**（审计当次实测），保留作为治理前基线。批次 A/B 之后的
> 当前实测见 §2.6；凡本节出现的旧值（342 / 73 / 80 / 68 / 167 / 45 / 88）均以 §2.6 为准。

### 2.1 规模与可达性

| 指标 | 数值 |
| --- | --- |
| make target 定义数 | **2183**（其中 `.PHONY` 2014） |
| 门禁锚点数 | **4** |
| 门禁锚点可达 target（并集） | **144**（6.6%） |
| 不可达任何门禁的 target | **2044**（93.4%） |
| 全仓库零引用的 target | **342**（其中 304 仍被声明为 `.PHONY`） |
| `scripts/**` 下 py/sh/js | **2175** |
| 全仓库零引用的脚本 | **50** |

门禁锚点各自可达规模：

| 锚点 | 车道 | 可达 target |
| --- | --- | --- |
| `ci.local.quick.run` | local | 68 |
| `ci.professional.backend.shard-verify` | remote | 45 |
| `verify.frontend.pr.unit` | remote | 20 |
| `verify.frontend.release.audit` | remote | 71 |

### 2.2 车道覆盖

| 车道 | target | 脚本 |
| --- | --- | --- |
| `local.iteration`（L1 静态入口） | 3 | 5 |
| `local.quick`（本地精确 head 证据） | 68 | 167 |
| `remote.professional.backend.verify` | 45 | 88 |
| `remote.professional.backend.tests` | 6 | 9 |
| `remote.professional.backend.reports` | 4 | 9 |
| `remote.standard_backend` | 5 | 9 |
| `remote.frontend.standard` | 20 | 18 |
| `remote.frontend.full` | 71 | 68 |

### 2.3 双向漂移（本审计的核心发现）

- **73 个守卫只被 `local.quick` 执行，远端任何车道都不执行。**
  构成：`contract_governance_*_split_guard` 22 个、`construction_core_extension_*_split_guard`
  12 个、`contract_form_*` 7 个、`frontend_page_contract_*` 2 个、前端边界守卫 3 个，
  其余 26 个（`formal_product_field_purity_guard`、`tenant_extension_storage_guard`、
  `g1_acceptance_baseline_guard`、`ui_contract_v2_responsibility_map_guard`、
  `login_envelope_consumption_guard`、`backend_contract_lifecycle_authority_guard`、
  `list_field_semantic_integrity_guard` 等）。
- **80 个脚本只被远端执行，本地 Quick 不执行**（主要是 frontend release /
  professional 家族及其 `test_frontend_*` 单测）。

**成本不是漂移的理由。** 实测 73 个"仅本地"守卫全部独立运行合计约 **65 秒**，
其中绝大多数单脚本 `0.02–0.30s`，只有 `login_envelope_consumption_guard` 约 6 秒；
整体相对于 professional gate 的 9–14 分钟关键路径可以忽略。漂移纯属**手工清单缺少单一来源**。

### 2.4 门禁清单重复

`professional_quality_gate` 有 6 条模式（`full` / `mainline` / `standard_backend` /
`standard_frontend` / `governance` / `fast`），每条**手写**自己的 make 调用清单。
`ci.professional.backend.shard-verify`（18 项）与聚合目标 `ci.professional.backend`（20 项）
互为交叉子集，差异包括：

- shard-verify 独有：`verify.frontend.playwright_vendor_coupling.guard`、
  `verify.frontend.role_surface_exposure_declaration.guard`、`verify.product.release.version`；
- 聚合独有：`ci.generated_reports.guard`、`architecture.complexity_baseline_lock`、
  `test.unit` / `test.contract` / `test.e2e.preflight`。

本次 PR #639 的实战缺口就出在这里：`standard_backend` 是普通 PR 在 `HIGH_RISK/full`
降级后的常用路径，它的手写清单缺了 `verify.product.release.version`，导致"VERSION
字面量重复"通过全部远端必需门禁，只在本地精确 head Quick 暴露。**清单重复即漂移源。**

### 2.5 证据与遥测

- `.git/codex/evidence/ci.local.quick/` 已有 **204** 个回执，**9.5 MB**，无保留策略、
  无按 head 去重、无清理入口。
- 回执只在 **suite 开始时工作区 clean** 才签发；集成期（几乎总是 dirty）会静默打印
  `evidence disabled: worktree was not clean at suite start` 且不留回执——高价值证据
  在最需要它的时候最容易缺失，且失败是静默的。
- 分片入口 `ci.local.quick.shard` / `ci.local.quick.compose` 已实现并自测，但**无任何
  真实使用**，Quick 仍是单体全有或全无：中断即无回执。
- **无任何耗时 / 成功率 / 降级率采集。** `docs/ops/ci_feedback_latency_v1.md` 只有静态
  目标区间，没有真实测量。仓库内检索 `slo` 无实现。
- `docs/audit/guard_registry/guard_registry.json`：active 1321，
  `gate_enforced` **159**、`manual_lane_only` **1162**、`gate_required` **3**。

### 2.6 当前实测（批次 A/B 之后，2026-10-11）

以 `make audit.verification.lane_coverage` 实测：

| 指标 | 审计时 | B1/B2 后 | B3 后（当前） | 说明 |
| --- | --- | --- | --- | --- |
| 零引用 target | 342 | 336 | **760** | B3 修正 target 引用口径后求真：只有两份**约束性**文档声明执行入口，其余 `docs/`/`.agent/` 是叙述（见 B3） |
| 零引用脚本 | 50 | 104 | **103** | B2 求真后 104；B3 把关系回环探针接线到受管 make 入口，离开死面名册（-1） |
| 引用缺失资产的 target | 未测 | 未测 | **226** | B3 新增的硬校验登记类：配方调用了仓库里不存在的路径 → 该 target 无法运行 |
| `local.quick` 覆盖 | 68 target / 167 脚本 | 75 / 173 | **77 / 174** | 批次 A 接入单一来源；B3 脚本识别帧加入 `.mjs/.cjs/.ts` |
| `remote.professional.backend.verify` | 45 / 88 | 54 / 157 | **56 / 158** | 同上 |
| 仅本地守卫 | 73 | 5 | **5** | 批次 A 修复；5 条按方向登记豁免（unregistered 0） |
| 仅远端脚本 | 80 | 74 | **83** | B3 帧修正后显出 9 条真正只在远端执行的 Node/TS 探针，已登记豁免 |

门槛结论：**D1/D2/D3 已修复并被必需门禁强制**；D4 已被看见并加棘轮（raw 只减不增、
unregistered/stale 必须为 0，且由 `verify.contract.architecture.suite` 强制）；D5/D6 待批次 C/D。

---

## 3. 缺陷分级

| 编号 | 缺陷 | 影响 | 责任层 |
| --- | --- | --- | --- |
| D1 | 本地车道与远端门禁双向漂移（73 / 80） | 契约治理守卫不参与合并判定；通过不可复用 | P4 |
| D2 | 契约驱动架构守卫不在远端必需门禁 | 远端全绿不能证明契约未被破坏 | P4 |
| D3 | 6 条风险车道手写清单重复，无单一来源 | 每次改动都可能漏项（PR #639 实证） | P4 |
| D4 | 表面积失控：2044 target 无门禁归属、342 零引用；50 脚本零引用 | 认知成本、假信心、维护负债 | P4 |
| D5 | 证据工具在 dirty 时静默失效；回执无保留策略 | 高价值证据缺失且不可见 | P4 |
| D6 | 无车道耗时 / 成功率 / 失败归因遥测 | "高效"不可度量，无法回归验证 | P4 |

严重度排序：**D1 ≈ D2 > D3 > D4 > D5 > D6**。
D1/D2 直接侵蚀正确性；D3 是系统性复发机制；D4-D6 是效率与可信度债务。

---

## 4. 根因

1. **没有"单一必需集合"声明。** 每个入口各自维护一份 target / script 清单，靠人保持同步。
   只要有两个手写清单，就必然漂移；漂移方向随机，所以既能"CI 绿本地红"，也能"本地绿 CI 红"。
2. **守卫的接线方式不统一。** 远端用**前置项**（prerequisites），本地 Quick 大量用
   **recipe 体**逐行 `python3 scripts/...`。前置项会被 `$(MAKE)` 传递闭包覆盖，
   recipe 体不会——这正是 73 个守卫"看不见"的技术原因。
3. **没有表面积预算。** target 与脚本可以无限增长，无基线、无 `review_by`、无棘轮，
   于是"加个 make target"成为零成本操作。
4. **没有度量闭环。** 没有耗时与成功率数据，就无法证明某次治理真的提升了效率，
   也无法阻止下一轮回归。

---

## 5. 治理方案（批次）

原则：**减法与单一来源优先；每批可独立验收、可独立回滚；不新增全局测试框架；
不放宽任何门禁。**

### 批次 A —— 车道单一来源（最高优先）

- **A1** 建立"必需守卫集合"的单一来源声明，让 `ci.local.quick.run` 与
  `ci.professional.backend.shard-verify` **消费同一份集合**，而不是各自复制。
- **A2** 把 73 个"仅本地"守卫逐条定性：**必须远端强制的**接线到远端车道；
  **确属本地/诊断的**在 `scripts/verify/registry.yaml` 显式登记豁免理由。
  目标：`local_only_scripts = 0` 或全部有登记理由。
- **A3** 把 6 条风险车道的手写清单改为由风险分类器输出车道 → 目标映射，消除手写重复。
- 验收：`make audit.verification.lane_coverage.check` 中 `local_only_scripts` 与
  `remote_only_scripts` 归零或全部登记；`ci.professional.backend.shard-verify` 本地可跑通。
- 回滚：单文件回退 `make/ci.mk` + workflow。

### 批次 B —— 僵尸面处置

- 342 个零引用 target 与 50 个零引用脚本走既有 `wire_or_retire` 机制：
  接线、登记理由、或退役到 `retired/`。
- 目标：`targets_zero_reference` 与 `scripts_unreferenced_anywhere` 归零。
- 验收：`make verify.guard.registry` 与 `make audit.verification.lane_coverage.check` 同时通过。

#### B1 —— 记账层（已完成，2026-10-11）

僵尸面此前**无归属、无纪律**：既不在棘轮里，也没有名册，新增死面不会触发任何失败。
B1 先补齐"记账"这一前提，三条路径（接线 / 登记理由 / 退役）才有可执行载体。

- **登记名册**：`scripts/audit/verification_lane_dispositions.json`，
  targets 336 条、scripts 44 条，每条含 `disposition` / `owner` / `reason` / `review_by`。
- **棘轮口径拆分**：`--check` 现在同时校验
  - `max_targets_zero_reference` / `max_scripts_unreferenced_anywhere`：**raw，只减不增**；
  - `max_targets_zero_reference_unregistered` / `max_scripts_unreferenced_unregistered`：**必须为 0**；
  - `max_stale_*_dispositions`：**必须为 0**（登记过的面不再是死面 → 名册必须同步删除，
    防止名册退化成永久白名单）。
- **枚举能力**：`--list-zero-reference` / `--list-unreferenced-scripts`，便于逐条处置。
- **自测接线**：`scripts/audit/test_verification_lane_coverage.py`（13 项）接入
  `verify.contract.architecture.suite`，因此**本地 Quick 与远端必需门禁同时执行**。
  仪器本身仍不接入门禁（表面积不能被自己度量）；接入的是"活仓库不变式"断言。

#### B1 附带的方法学修正：脚本引用不再只看路径

`scripts_unreferenced_anywhere` 原口径只认 **文件路径**（`scripts/**/*.py` 字面量）。
一只通过点号导入被消费的模块（`from scripts.contract.x_common import ...`）因此被误判为死面。
现追加**点号模块名**索引，`49 → 44`，并清掉 5 条随之过期的登记。这是纯口径求真，未删除任何文件。

随后追加**唯一 basename** 索引：仅当 basename 全仓库唯一、且引用不来自 `docs/` 或
`.agent/`（叙述性文件只"讲述"脚本，不消费它）时计入，`44 → 38`，再清 6 条过期登记。
被清掉的 6 条经复核均为真实消费：`ensure_testdeps.sh`（`scripts/ci/run_ci.sh`）、
`render_nginx_conf.sh`（`Dockerfile.production-candidate` 与 `docker-compose.production-candidate.yml` 入口）、
`registry_audit/*`（`docker-compose.registry-audit.yml` 与 `test_registry_audit_environment.py`）。

> 归一化护栏：basename 索引会天然被"清单型"文件污染（任何按名字列出脚本的登记表都会让被列者
> 看起来"被消费"）。因此该索引只认**全仓库唯一**的 basename；`scripts/verify/registry.yaml`
> 这类清单只列 py/sh 的 **脚本名**，而 `scripts/verify/**/*.{py,sh}` 已由本仪器按所有者排除
> （见 B2 责任边界），二者不互相掩盖。

#### B2 —— 真实退役（已完成，2026-10-11）

退役前**先修工具**：只有"零引用"的口径可信，删文件才可逆地安全。

- **模块说明符索引（口径求真）**：`require('./x')`、`from x import` 这类**无扩展名**消费
  此前完全漏检，会把活脚本判死。典型误判两条：`scripts/verify/intent_smoke_utils.js`
  （被 `act_url_missing_scene_report.js:7` 等十余处 `require`）与 `scripts/verify/lib/scene_snapshot.js`
  （被 4 处 `require('./lib/scene_snapshot')`）。现按**消费方语言**解析：`.js` 消费方走 Node
  解析（`.js/.ts/index.js`），`.py` 消费方走 Python 解析（`.py/__init__.py`）；同名跨语言
  （如 `intent_smoke_utils.{js,py}` 并存）不再产生歧义，歧义即拒绝。
- **受管退役入口**：仪器新增 `--retire SCRIPT` / `--retire-all --reason`（默认仍只读）。
  退役把文件**移动**到 `scripts/retired/<原子路径>`（保留恢复价值与 git 历史），在
  `scripts/retired/retirements.json` 记录 `retired_to` / `reason` / `last_commit`，并**删除**
  对应登记——名册不会退化成永久白名单。**仍被任何一处引用的脚本一律拒绝退役。**
- **结果：零引用脚本 38 → 1（该 1 后来被证明是欠计，见下方 B2 收尾）。**
  - 退役 35 条，其中 8 条为 `scripts/verify/**/*.js`（`guard_registry_audit` 语料只含 py/sh，
    故由本仪器负责）。
  - 保留 1 条并改归属：`scripts/tenant_payload/__init__.py` → `package-marker`
    （包结构标记，`--retire-all` 对 `package-marker`/`retain` 明确跳过，不批量删除）。
  - 清理 8 条 stale 登记：6 条被 basename / docker-compose / Dockerfile 真实消费，
    2 条因上述仪器修正转为活面。
- **责任边界（显式声明，不再靠巧合）**：`scripts/verify/**/*.{py,sh}` 归
  `scripts/verify/registry.yaml` + `guard_registry_audit.py`（必需门禁，孤儿必须登记或退役，
  现 1408 条在册）；本仪器负责其余 `scripts/**`（owned surface 732）。二者不重复登记：
  本仪器仍把它们作为**引用解析目标**，但不计入自身死面统计。
- **自测 22 项**接入 `verify.contract.architecture.suite`，本地 Quick 与远端必需门禁同时执行：
  锁定解析语义（相对/裸模块、跨语言同名）、退役语义（移动 + 记录 + 去登记 + 拒绝活面）、
  以及"活仓库不变式"（unregistered=0 / stale=0 / raw ≤ 棘轮 / 不重复计数）。

#### B2 收尾 —— 引用模型求真（已完成，2026-10-11）

B2 的"38 → 1"是在**有缺陷的引用模型**下测得的。收尾复核时发现：

- **根因（度量层）**：原模型把 `docs/`（审计报告、清单、矩阵、`test_inventory.csv`、
  `guard_registry.json`）中的脚本路径也当成消费方。**审计文档必然逐一列出被审计脚本**，
  于是整个长尾被叙述性文本"复活"，指标长期显示干净。
  **这正是"反复重跑却收不了口"的度量根因**——不是验证过多，而是"死面"从未被看见。
- **修正**：叙述性文件（`docs/`、`.agent/`）对全部四种命名方式（完整路径、点号模块名、
  唯一 basename、模块说明符）一律**不作为**消费证据。
- **真值**：修正后零引用脚本由 1 跳回 **106**。这**不是回归**，而是此前被掩盖的真实值；
  逐条核实：全部无 make / workflow / 脚本消费，通配与动态调用复核无命中。逐族处置后为 **104**。
- **受管登记入口（与 `--retire` 对称）**：
  - `--register-script SCRIPT --disposition D --reason R --owner O --review-by DATE`。
    **拒绝登记仍有引用的脚本**（否则立即产生 stale 条目、名册退化为白名单）；
    disposition 取自封闭词表 `SCRIPT_DISPOSITION_VOCABULARY`，新增分类必须在评审中显式加入。
  - `--register-batch PATH`：审阅过的 JSON 清单一次登记一整族（一次测量、逐条同样校验、
    任一条非法则整体不写），避免 N 次手改 JSON。
  - 自测 22 → **27 项**（登记入口 4 项守卫 + 1 项"名册 disposition 必须落在封闭词表内"）。
- **逐族定性（104 条，owner=platform-team，review_by=2027-06-30）**：

| disposition | 条数 | 含义 |
| --- | --- | --- |
| `runtime_audit_probe` | 53 | `scripts/ops/validate_*.sh`：受管 DB 上的运行时审计手工入口 |
| `browser_acceptance_probe` | 41 | `scripts/verify/*_acceptance.js` / `*_browser_acceptance.js` / `*_smoke.js` / `direct_acceptance_*` / `fe_scene_*`：Playwright 契约驱动探针 |
| `ci_legacy_tooling` | 2 | `scripts/ci/ci_gate.sh`、`checkout_from_ci_mirror.sh`：仓库内零消费，但 Gitee 侧 CI 配置不在仓库内、无法在仓库内证明外部不再引用，**登记不退役** |
| `audit_tooling` / `ops_tooling` | 2 + 2 | 审计/运维一次性工具，登记待接线或退役 |
| `product_tooling` / `candidate` | 1 + 2 | 产品化工具与待定候选 |
| `package-marker` | 1 | `scripts/tenant_payload/__init__.py`，非债务 |

- **本轮再退役 2 条**（有明确替代证据）：`scripts/verify-fix.sh`（屏幕闪烁一次性验证清单，
  同族三条已在 B2 退役）、`scripts/demo/frontend_productization_fixture.sh`（零消费的弃用转发 shim，
  转发目标与受管入口均存在，保留期已结束）。
- **基线重写**：`max_scripts_unreferenced_anywhere` **1 → 104**。这**不是放宽**：冻结前的 1 是
  错误口径的产物，104 才是当前真实值；棘轮语义不变（只减不增），`unregistered`/`stale` 仍必须为 0。
  `max_targets_zero_reference` 保持 336（由 B3 处置）。
- **可追踪的未接线长尾**：94 条探针（53 + 41）**尚未接线**。其中
  `scripts/verify/record_relation_roundtrip_acceptance.js` 正是本 run 详情关系回环证据
  （`round_20261010_detail_relation_roundtrip`，`T-ASSET-944`）引用的资产，却**无受管派发**——
  这是"登记 ≠ 接线"的直接证据，列为 **B3 首条接线目标**（接线必须走 fixture 稳定标识解析，
  不得硬编码记录号）。

#### B3 —— target 侧引用求真 + 首条接线（已完成，2026-10-11）

B2 只修了**脚本**侧的"散文复活"，**target 侧是同一个缺陷**：`read_doc_invocations` 原先把
`docs/` 下任何 `$()`/`$(MAKE)` 调用都当成执行引用。审计报告、清单、矩阵必然会**引用它们所审计的
target 名**，于是这一类长尾被自己的审计文本"复活"。修正为：只有两份**约束性**文档
（`docs/ops/codex_execution_allowlist.md`、`docs/ops/codex_workspace_execution_rules.md`）
声明执行入口，`docs/` 与 `.agent/` 其余文件一律视为叙述。

- **真值跳升**：零引用 target **336 → 759**（+423：`history_probe_runbook` 146 / `candidate` 109 /
  `diagnostic_cli` 95 / `ops_runbook` 27 / `release_runbook` 27 / `ops_tooling` 15 / `tenant_runbook` 4）。
  这**不是回归**，而是此前被叙述性文本掩盖的真实值。
- **登记入口补全（关键前置）**：`--register-batch` 原先只写 `scripts` 桶，若直接登记将把 400+ 个
  **target 名写进脚本名册**。已改为支持 `{targets:[...], scripts:[...]}` 双桶（条目键
  `name`/`script`/`target` 均可），并新增 `TARGET_DISPOSITION_VOCABULARY` 承载 make 侧独有分类
  （`one_shot_projection_write`、`one_shot_replay_adapter`、`frontend_develop`、`gate_candidate`）。
  另补 `--unregister-script`（**拒绝注销仍无引用的脚本**）与 `--record-missing-assets`。
  自测 27 → **42 项**。
- **新增硬校验登记类：引用缺失资产的 target**（`absent_assets` 桶）。判据是机器可验证的：
  配方里出现的脚本路径在仓库中不存在 → `make <target>` 必然失败。实测 **226** 条，其中 187 处引用
  指向 `scripts/migration/*`——该目录在 `.gitignore` 第 116 行被政策性地排除出"干净产品仓库"
  （客户迁移物料 never enter），另有少量被改名/从未加入的 `scripts/verify/*` 与根 `scripts/*.mjs`。
  每条登记 `missing_asset`（**由测量写入，不靠人手抄**）+ owner + reason + review_by；
  `--check` 强制 `unregistered=0`、`stale=0`（配方一改、记录即失效）。
  **未擅自删除 226 条规则**：它们属于"历史重放/客户迁移"边界，规则去留是 owner 的政策判断，
  本轮只把"不可执行"这一事实变成有归属、只可缩小、不可静默增长的数字。
- **顺手修正的度量帧缺陷（引入即发现并修掉）**：脚本识别正则原先只认 `.py|.sh|.js`，
  且**没有路径边界**，于是 `frontend/apps/web/scripts/foo_test.ts` 会被读成仓库根的
  `scripts/foo_test.ts`（138 条"缺失路径"假阳性）。修正为 `(?<![A-Za-z0-9_./\-])` 起边界 +
  `.mjs|.cjs|.ts`：既让 Node/TS 探针进入车道漂移统计（显出 9 条真正仅远端执行的探针，已登记），
  又消掉假阳性。`max_remote_only_scripts` 74 → 83 已按"口径纠正"记入基线 `metric_corrections`。
- **B3 首条接线（登记 ≠ 接线）**：`scripts/verify/record_relation_roundtrip_acceptance.js`
  是本 run 详情关系回环证据所引用的资产（`T-ASSET-944`），却无受管派发。现已：
  1. 增加受管入口 `verify.daily_dev.relation_roundtrip.browser`（只读、`guard.prod.forbid`、
     要求 `ACCEPTANCE_TARGET_SHA` / 登录 / `ACCEPTANCE_RECORD_RESOLUTION`）；
  2. 探针**删除硬编码记录号**（原默认 `project.project/581/506` 已移除），改为读受管
     `acceptance.record_identity_resolution.v1` 信封，按 `RELATION_RESOLUTION_KEY` 取声明身份，
     校验 `model/record_id/action_id/menu_id` 齐备且唯一，并断言 served revision 与
     `/api/runtime-version` 一致；显式身份只能由 `RELATION_IDENTITY_SOURCE=explicit` 打开（诊断用）。
  3. 接线后该脚本离开零引用名册（-1），新 target 进入登记（`browser_acceptance_probe`，+1）——
     这正是"接线"与"登记"两字之差的真实代价与收益。
- **基线重写**：`max_targets_zero_reference` 336 → **760**（口径求真，非放宽），新增
  `max_targets_missing_asset_unregistered=0` / `max_stale_missing_asset_dispositions=0`。
  `verification_lane_baseline.json` 内的 `metric_corrections` 现在**由仪器常量写入**，
  不再只存在于 JSON 里——`--write-baseline` 会重写该文件，只写在文件里的说明会在下次冻结时丢失。

### 批次 C —— 迭代效率

- 默认启用 `ci.local.quick.shard` / `.compose` 分片路径，使中断不再等于零证据。
- Quick 在非 clean 工作区时的行为收敛：显式失败或要求 `--diagnostic`，禁止静默无回执。
- 回执保留策略：按 head 去重 + 保留 N 个 + 显式清理入口（当前 204 个 / 9.5 MB 无上限）。

### 批次 D —— 度量与遥测

- 为 8 条车道采集真实耗时、成功率、失败归因，落盘到既有证据目录。
- 与 `docs/ops/ci_feedback_latency_v1.md` 的静态目标对齐，形成可回归的延迟预算。

### 批次 E —— 棘轮接线

- **已由既有接线满足（2026-10-11）**：`--check` 本体仍**刻意不接入**必需门禁
  （仪器度量表面积，接入即自我指涉），但自测 `audit.verification.lane_coverage.test`
  已在 `verify.contract.architecture.suite` 内，而该套件同时被 `ci.local.quick.run`
  与 `ci.professional.backend.shard-verify` 消费。自测含两条**活仓库不变量**：
  "新死面必须已登记"（unregistered=0）与"raw 债务不得超冻结基线"。
  因此新增死面会**直接让必需门禁失败**，棘轮已是强制而非建议，无需新接线。
  剩余工作只是把 raw 债务继续压到 0（B3 及 C/D）。

---

## 6. 度量基线与目标

基线文件 `scripts/audit/verification_lane_baseline.json` 把指标分成两类：

**硬校验（债务，只允许缩小）**

| 指标 | 冻结值 | 目标 |
| --- | --- | --- |
| `max_targets_zero_reference` | 760 | 0 |
| `max_scripts_unreferenced_anywhere` | 103 | 0 |
| `max_targets_missing_asset_unregistered` | 0 | 0（226 条已登记，只可缩小） |
| `max_stale_missing_asset_dispositions` | 0 | 0 |
| `max_local_only_scripts` | 5 | 0 或全部登记豁免 |
| `max_remote_only_scripts` | 83 | 0 或全部登记豁免 |

> `max_local_only_scripts` / `max_remote_only_scripts` 的冻结值已在批次 A 后重写为实测的
> **5 / 83**（原 73 / 80 是 A 之前的实测值；B3 脚本识别帧修正后 74 → 83，详见
> `verification_lane_baseline.json` 的 `metric_corrections`，该字段由仪器常量写入）。

**仅记录（体积，不硬校验）**：`recorded_targets_defined`、`recorded_targets_unreached_from_anchor`、
`recorded_anchor_union_targets`，由 `review_by` 到期复核。

> **口径说明（实测教训）**：棘轮最初把"体积"也设为硬校验，结果本审计工具自己新增两个
> 手工入口就把 `targets_unreached_from_anchor` 从 2044 顶到 2046 而失败。
> 合理的手工 / 诊断车道即使不被门禁可达，也仍是**有归属**的正当表面积；
> 对 +1 失败只会阻塞真实工作而不减少债务。因此硬校验只保留**无归属、无执行**的债务指标，
> 体积指标记录并到期复核。

`--check` 仅在债务指标**增长**时失败，因此不阻塞现有迭代，只禁止债务继续膨胀。

---

## 7. 验收与回滚

- 每批次验收：`make ci.local.iteration`（L1）→ 受影响非零 L2 定向测试 →
  `make audit.verification.lane_coverage.check`；涉及车道改动时另跑受影响的
  `ci.professional.backend.shard-*` 本地验证。
- 本审计自身属 P4 文档与只读工具，不进入 Quick / 远端门禁，不改变任何既有判定。
- 回滚：全部改动集中在 `scripts/audit/`、`make/guards.mk`、`docs/audit/`，
  单点回退即可，不影响产品代码。

---

## 8. 未决与风险

- 2047 个"无门禁归属"的 target 尚未分类为"合理手工车道 / 文档车道 / 僵尸"，
  这是治理不确定性的主体。B3 已把其中全部 760 个**零引用** target 与 226 个**引用缺失资产**的
  target 变成"有归属、可缩小"的登记项，但"物理退役"仍是逐族 reviewed 工作：
  226 条中 187 处指向 `scripts/migration/*`，规则去留取决于"客户迁移物料不进入干净仓库"这条
  边界政策由谁承载（是保留为声明式外部入口，还是移出产品仓库），这是 owner 的政策判断，
  本轮**未**擅自删规则。
- `recorded_targets_missing_asset=226` 是**已登记**的不可执行面，不是通过项。要让它归零，
  只有两条路：恢复脚本，或按族退役规则；两者都需要独立证据与边界。
- 车道划分依据的是**声明**（workflow 中的 `make` 调用与 make 前置图）。
  通过 `package.json` / `pnpm` 间接执行的守卫已尽量纳入远端车道，但仍可能存在
  "被脚本内部动态调用"的盲区；任何据此得出的结论都应保留该限制说明。
- `scripts/verify/registry.yaml` 的 `gate_required` 只有 3 项，是否过窄需要批次 A 一并裁定。
- 本审计不改变任何完成状态判定：批次验收 / 主线集成 / 版本发布 / 产品交付仍分别独立结论。
