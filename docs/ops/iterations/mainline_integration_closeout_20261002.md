# 主线集成收口（2026-10-02）

**Run**：`MAINLINE-INTEGRATION-CLOSEOUT`（`.agent/runs/MAINLINE-INTEGRATION-CLOSEOUT/run.json`）
**分支**：`fix/mainline-integration-closeout`（baseline `main@f7783e1ad755d5fb79924531493c8922384d9517`）
**目标**：恢复期结束后收口主线的在途表面——对齐页头守卫与 PR #525 采纳的官方字体表达、关闭已被整合的 PR #522、完成两个已合入但未关闭的 run、清理 active-runs 遗留绑定。

## 背景盘点（起点事实）

- 台账 `form_structure_compatibility_consumers_v1.json` 已清零（正式消费者 PR #512 归零；最后一个
  otherStateConsumer 由 PR #514 退役）。9-16 记忆中的「42 项 / G02 发票组未集成」已过时：G02 及全部
  迁移组经 9-17 起的表单结构消费稳定化批次链合入（`feature/uc4-invoice-native-lowcode` 分支已按
  惯例清理，产物文件全部在 main：`formal_form_invoice_journey.mjs`、`test_invoice_native_lowcode.py`、
  `uc4_invoice_native_lowcode_20260916.md` 均确认存在）。
- main 链（时间序）：#521 字段语义单一权威 → #522（open，见下）→ Gitee 临时集成（bc98f5e65 等）→
  #523 GitHub 历史恢复 → #524 agent resume/增量证据复用 → #525 官方模板渲染采纳 → #526 验收收敛 →
  #527 契约托管 → #528 FE-TPL closeout → #529 定时 CI full 车道修复 → #530 CI-SCHEDULED closeout。

## 实施一：PR #522 收口（关闭而非合并）

PR #522「前端页头入口权威统一（P0 表达收口第二刀）」创建于 2026-09-21 23:31（head `22390c84f`，
base `de9a230d3`，29 提交，创建时五工作流全绿）。创建后被 Gitee 集成与 GitHub 恢复窗口打断。

**整合事实核验**（关闭依据）：

- 其 13 个交付文件已全部经 `bc98f5e65`（2026-09-23，"consolidate retained page header and
  stability work"）进入 main。
- 逐文件比对（#522 头 vs `main@f7783e1ad`）：
  - **IDENTICAL（4）**：`productPageHeaderAdapters.ts`、`ScPageHeader.vue`、`page/PageHeader.vue`、
    批次记录 `frontend_page_header_entry_authority_20260922.md`——核心 src 交付一字不差。
  - **差异（9）全部为 main 侧领先演进**，无 #522 独有未落地内容：
    - 守卫 `+3/-1`：CONTRACT-ACT-01 动作分区重构（`normalizeActionSemantics`）；
    - 契约测试 `+1/-1`：no-useless-escape 修复（PR #529 的 lint 清债）；
    - `KanbanPage.vue` `+0/-2`：main 侧移除 `fieldToneByValue` 传递（状态色调解析收敛后不再需要）；
    - 测试守卫 `+12`、localized display `+14`、`make/frontend.mk` `+190/-15`（含 #529 新注册的
      `verify.frontend.lint`）、复杂度预算/清单/切换日志（生成物与文档）。
- 结论：PR #522 的实质交付**已在 main 且被后续批次继续演进**，合并只会制造重复；按整合事实
  **关闭**并删除远程分支。

## 实施二：页头守卫排版断言对齐（PR #525 后的现实）

**发现**：main 上 `verify.frontend.product_page_header.unit` 红灯（守卫 RC=1、单测 70 中 6 失败）。
三个失败断言：

| 断言 | 旧字面量（守卫钉住） | #525 后现实 |
| --- | --- | --- |
| native field label | `.label {\n  font-size: var(--sc-product-text-sm);` | `.label {\n  font: var(--sc-font-mark-small);` |
| native readonly body（收缩槽） | `.readonly-value {…font-size: var(--sc-product-text-body);`（font-size 在尾部） | `font: var(--sc-font-body-medium);`（font 简写在头部，属性顺序改变） |
| native record title 响应式 | `font-size: 24px` | `font: var(--sc-font-headline-small);` |

**根因**：PR #525 采纳官方字体 token（`--sc-font-*` 的 font 简写）改写了 `FormSection.vue` 与
`NativeFormTreeRenderer.vue`，但该守卫不在 PR 车道（standard 只跑 `lint:src`）也不在
`ci.local.quick`（其组成不含 `verify.frontend.quick.gate`），只存在于
`verify.frontend.quick.gate` 与 `verify.frontend.release.unit`（定时 full 车道
`verify.frontend.release.audit` 的第一步）。9-30 起 lint 22 error 让 release 命令早退，
**该红灯被掩盖**；PR #529 修好 lint 后，下一次定时运行（cron `30 18 * * *`）会在
`release.unit` 暴露——属 #529 诊断「级联掩盖」清单的漏项。

**修复**（守卫断言对齐现实，非产品代码改动）：

- `scripts/verify/frontend_product_page_header_guard.py`：三个 marker 对齐 #525 后字面量
  （`.label` 用 `font: var(--sc-font-mark-small)`；`.readonly-value` 用 `font: var(--sc-font-body-medium)`
  打头的完整收缩槽序列；record title 用 `font: var(--sc-font-headline-small);`），并加注释说明
  断言演进原因。
- `scripts/verify/test_frontend_product_page_header_guard.py`：负例 fixture
  `test_native_readonly_body_typography_stays_in_shrinkable_slot` 的 replace 目标同步为新字面量
  （旧字面量已不在真实文件中，replace 变 no-op 导致断言失效）；失败消息文案同步
  （"native readonly body font token and shrinkable slot"）。

**验证**：`make verify.frontend.product_page_header.unit` 全绿——
model/adapter 契约测试（esbuild bundle）+ `python3 -m unittest`（70 tests OK）+
守卫本体（`[frontend_product_page_header_guard] PASS adapters=3`）。6 个失败测试全部为排版断言
级联，修复后归零、无新增失败。

## 实施三：两个已完成 run 的关闭

| Run | 分支头 | 合入事实 | 关闭动作 |
| --- | --- | --- | --- |
| `GITHUB-RECOVERY` | `fix/github-history-recovery@83ba64063` | PR #523（merge `72ad88e69`，2026-09-30T06:52:33Z）；分支头为 main 祖先 | status→completed，补 `completion.mainline`，`next_exact_step` 置完成说明 |
| `P4-INCREMENTAL-RESUME` | `fix/agent-resume-mainline@b6ea04f0d` | PR #524（merge `fff226d7b`，2026-09-30T07:32:36Z）；分支头为 main 祖先 | 同上；`cancelled_quick`（`81788ca9a` 无回执）保留为历史事实，注明被后续 Quick 回执取代 |

两分支相对 main 均零领先提交（`git log origin/main..<branch>` 为空）。

**active-runs 清理**：删除三个遗留绑定——`fix/agent-resume-mainline`（run 关闭）、
`fix/run-closeout-fe-template-adoption`（FE-TPL run 已 completed，closeout 分支已随 #528 合并删除）、
`codex/close-scheduled-ci-full-lane-recovery`（同理，随 #530 合并删除）；新增本批
`fix/mainline-integration-closeout` 绑定。

## run 检查登记（executor-recorded）

- `guard_realign`：target `verify.frontend.product_page_header.unit`，passed（70 单测 + 守卫 PASS
  adapters=3），证据 `.runtime/agent-runs/MAINLINE-INTEGRATION-CLOSEOUT/guard_realign.{log,json}`。

## 状态

主线集成收口第一刀：**守卫对齐完成、PR #522 关闭、GITHUB-RECOVERY 与 P4-INCREMENTAL-RESUME 关闭、
active-runs 清零至本批**｜待冻结→exact-head Quick→保护 PR。后续批次（独立 run）：
backend-contract-l4 集成、contract-slo-telemetry 集成。
