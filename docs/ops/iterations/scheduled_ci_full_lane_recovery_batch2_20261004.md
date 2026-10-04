# 定时 CI full 车道恢复 第二批（CI-SCHEDULED-FULL-LANE-RECOVERY-B，2026-10-04）

## 现象与身份

- owner 报告 `github.com/lidefend/sce-backend-odoo` 定时 CI 失败。schedule 触发的失败集（`main 6d9c45b5cd97`）：
  - `frontend_release_gate` run `37155823091` / job `111298873980`：**真失败**。
  - `release_candidate_gate` run `37155960135`：级联（等待四个门禁全 success，frontend 失败即 fail）。
  - `backend_test_suite` run `37158252861`：self-hosted Huawei runner（**独立车道，见末节**）。
  - 同批 `professional_quality_gate`（run `37155734235`，12m55s）与 `merge_policy_gate`（run `37155658701`）为 success。
- **为什么 PR 全绿而定时红**：PR/push 车道按风险分级把 frontend 降到 `standard`/`skip`；`schedule` 在 workflow 里被强制 `frontend_mode='full'`，
  `verify.frontend.release.unit` 的 30 个目标才全部执行。这些守卫不在 `verify.frontend.pr.unit` 内，
  因此 `#525`（官方模板采用，`2d164a1f`，2026-10-01）合入后的守卫漂移没有在 PR 上暴露。

## CI 失败的实际位置（原始日志，未推断）

`gh run view --job 111298873980 --log-failed` 的关键行：

```
21:39:51 [verify.frontend.scene_component_bridge.guard] FAIL the collaboration authority's reviewed imports
         must resolve and stay environment-blind: the imported module
         `frontend/apps/web/src/app/contracts/v2/store.ts` is no longer a pure function of its input:
         the module reads the runtime environment (`document`), so its rule can differ between the gate and
         the browser; `store.ts` runs a statement while it loads, and the collaboration authority links it:
         `{constkind=asText(deletePolicy.policy_ki`
21:39:51 make[1]: *** [make/frontend.mk:74: verify.frontend.scene_component_bridge.guard] Error 1
21:41:05 [frontend_build_fingerprint] PASS sha256=cbf7982ccd957c7c96817575780ae527c83efd4ea52dfad0af8f2993cfbea6af
21:41:05 [frontend_static_release_audit] PASS evidence=artifacts/frontend-release-audit/static.json
21:41:05 [frontend_release_audit] FAIL evidence=artifacts/frontend-release-audit/report.json
```

- `make verify.frontend.release.audit` 中 `verify.frontend.release.unit` 失败即 `status != 0`，
  后续 `db.frontend.acceptance.ensure`、`verify.frontend.page_identity.browser`、
  `verify.frontend.delivery_hardening.release.browser` **全部被短路跳过**。
  即浏览器车道在本次失败中从未执行，其通过与否在修复前不可判定；静态审计与构建指纹本身是 PASS。
- `verify.frontend.release.unit` 内部按顺序执行，`scene_component_bridge.guard` 早于
  `professional_component_registry.unit`，所以 CI 只报出前者；后者是本地补齐同层失败时发现的下一道。

## 根因 B：`scene_component_bridge.guard` 两处文本分析缺陷（守卫缺陷，不是 `store.ts` 缺陷）

`scripts/verify/frontend_scene_component_bridge_guard.py` 对 import 闭包做源码文本分析，两处把合法代码读成违规：

1. `_environment_reference_failures` 在闭包遍历里对**原始** `target_text` 扫描，未先 blank 注释/字符串。
   `store.ts:495` 的文档注释里出现单词 `document`，被当成运行时环境读取。
2. `_module_statements` 把 `function resolveDeclaredDeleteStateGate(...): { blocked: boolean } { const kind = ...`
   的函数体 `{` 误判为新语句——类型字面量的 `}` 与函数体的 `{` 相邻，仅凭后随字符不可区分，
   于是把合法函数体读成“模块加载时执行的语句”，报出 `{constkind=asText(deletePolicy.policy_ki`。

**修复（改动均在守卫自身）**：

- 新增 `_js_previous_significant()`，`_module_statements` 增加 `body_group` 状态：
  open bracket 时若组属于已开语句，则 `body_group = character == "{" and _can_end_statement(_js_previous_significant(...))`；
  `}` 只在 `closes_body` 时结束声明；每组复位。
- import 闭包的环境检查改为先 `_blank_comments_and_strings(target_text)` 再扫描。
- 自检用例新增 4 条：`): { blocked: boolean } {` 声明体、该体之后的新语句仍被抓、注释内 `document` 通过、字符串内 `document` 通过。

**证据**：`make verify.frontend.scene_component_bridge.guard` → `PASS checks=129 collaboration_self_check=266`
（另含 6+7 项 unittest 全绿）。最小探针：语句数 50→49（误报消失），blank 后环境引用 `[]`。

## 根因 A：`professional_component_registry.guard` 的字段迭代器判定过约束

`FormSection.vue` 在 `#525` 中为“官方 detail 组合”新增外层
`<template v-for="(segment, segmentIndex) in detailFieldSegments">`，字段迭代器
`<div v-for="(field, index) in segment.fields" …六个语义标记…>` 被包在其内。

守卫用 `enclosing_vfors()` 收集祖先 v-for（由内向外）后判定 `len(loops) == 1 and loops[0] in field_iterators`：

- 字段路径的每个 renderer 分支现在有 **2** 层祖先循环 → 全部判为“not rendered by the field iterator element”；
- `ScDescriptions #item` 只读事实路径里的同一个 `ProfessionalBusinessValueControl` 分支，
  其最近循环是 segment 模板 → 同样被判违规。

最小探针（`/tmp/probe_reg.py`，用守卫自身 helper）dump 出的实际值：

```
FIELD_ITERATORS: [(29, 'div', 'segment.fields')]
branch idx=52 elem=ProfessionalBusinessValueControl loops=[(29,'div','segment.fields'), (8,'template','detailFieldSegments')] in_field_iter=True
branch idx=12 elem=ProfessionalBusinessValueControl loops=[(8,'template','detailFieldSegments')]              in_field_iter=False
```

即“最近一层循环就是字段迭代器”这一实质不变量**仍然成立**；`len(loops) == 1` 是旧模板形态的实现细节。

**修复**：

- `loops_over_the_field_list()` 改为 `bool(loops) and loops[0] in fields`：只认**最内层**循环是字段迭代器。
  中间层若插入其它包装循环，`loops[0]` 就不是字段迭代器，仍会被判违规（`test_semantic_markers_on_an_ancestor_iterator_fail` 等负例继续通过）。
- 字段迭代器要求按**元素**聚合：一个元素可能有多个渲染面（只读事实面 + 可编辑字段面），
  只有当该元素所有会 dispatch 该 renderer 的分支都不在字段迭代器下时才报错。
  断言仍是精确的“每个已注册 renderer 必须由字段迭代器下的分支 dispatch”，未放宽。

**证据**：`make verify.frontend.professional_component_registry.unit` → `PASS cases=137` +
`Ran 147 tests … OK` + `[frontend_professional_component_registry_guard] PASS`。
（修复前 `Ran 147 tests … FAILED (failures=64)`，守卫报 17 条。）

## 根因 D：两处结构计数基线被 `#525` 的受管命令改变

同层独立失败（`make -k verify.frontend.release.unit` 一次性收敛）另外两条，均为 `#525` 新增**受管** `ScButton` 命令导致计数基线漂移，非语义放宽：

- `verify.frontend.action_view_page_actions.unit`：`ActionView expected 11 governed page-action projections, found 14`。
  `#525` 新增 `<template #leading>`，把 header 的 3 个投影（reload/create/header.actions）放到列表卡片 leading 槽位，
  与 `#actions` 通过 `standardListOperationsInCard` 互斥渲染。守卫新增 `<template #leading>` 声明标记，
  期望值改为显式常量 `EXPECTED_SC_BUTTON_PROJECTIONS = 14`；断言仍是精确计数，第 15 个标签依然被拒。
- `verify.frontend.relational_action_primitives.unit`：`X2Many must retain exactly 9 governed commands alongside readonly disclosure`。
  `#525` 为三个只读摆位（只读表格操作列、只读行列表、移动行）各新增 1 个受管 `打开` 命令（`adapter.one2manyCanOpenRow`），
  基线 9 → 12。守卫新增 `<template #_action="{ row }">`、`colKey: '_action'`、`adapter.openOne2manyRow(field.name, row)` 声明标记，
  期望值改为 `X2MANY_GOVERNED_COMMANDS = 12`。

**未放宽的证明**：两个测试文件仍以“追加一个平行命令即失败”断言守卫（`test_projection_count_rejects_parallel_action`、
`test_readonly_disclosure_does_not_expand_command_authority`），并改为直接引用守卫常量，避免再次硬编码数字。

## 复用与不重跑

- 09-30 的运行（`36785831049`）在旧模板上是绿的；本次只按“输入变化”失效相关层：
  `#525` 改动了 `FormSection.vue`、`ActionView.vue`、`X2ManyRelationRenderer.vue`，故对应守卫单测与守卫目标重跑；
  与之无关的 `release.unit` 其它目标沿用本次整跑结果（`make -k` 一次收敛全部同层失败）。
- 构建产物、后端与受管 fixture **未变更**，无需重建；`frontend_static_release_audit` / 构建指纹在 CI 中已 PASS。

## `backend_test_suite` 结论（独立车道，单列，不泛化）

- 10-03/10-02 的 schedule：`failed to create network sc-suite-*_default: all predefined address pools have been fully subnetted`
  + `failed to resolve reference docker.io/library/nginx:latest ... i/o timeout` → self-hosted runner 的 Docker 地址池耗尽 / 网络。
- 10-01（job `110630743697` / run `36940538473`，19m56s）：镜像拉取超时之外，`smart_construction_core` 出现
  `25 failed, 35 error(s) of 471 tests` 的长期真实红（典型 `'approved' != 'submitted'`、缺 `groups_id`、`cursor already closed`）。
- 结论边界：该车道属 runner 基础设施 + 长期真实红，**不作为本批次已通过或环境全局通过的证据**；
  需要该车道自身恢复到可跑状态后单独诊断，本轮不重建前端来“验收”后端修复。

## 冻结前的生成产物

`make ci.delivery.freeze.prepare` PASS（candidate=unfrozen）。该入口按源码行数机械刷新了两份被跟踪的
生成报告，已随本批次提交、不做人工改写：

- `docs/engineering_convergence/complexity_budget_report.md`：
  `frontend_scene_component_bridge_guard.py` 7007→7122、`frontend_professional_component_registry_guard.py` 1908→1923。
- `docs/engineering_convergence/split_plan_queue.md`：同上两条拆分队列的行数同步。

`contracts/generated/contract_structure_fingerprint.json` 与其余生成证据已是最新（无改动）。

## 未验证边界

- `verify.frontend.release.audit` 的浏览器段（`verify.frontend.page_identity.browser`、
  `verify.frontend.delivery_hardening.release.browser`）依赖 CI 内的隔离验收栈（`sc_frontend_acceptance`、
  `ODOO_PORT=18082`、随机凭据），本地不可复现。它们在失败运行中被短路，故其状态在 CI 复跑前为**未验证**。
- 本轮不改变任何 decrease-only 基线。
