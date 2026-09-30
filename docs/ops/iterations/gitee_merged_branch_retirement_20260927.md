# Gitee 已合并历史分支退役入口（P4 工具）

## 身份与边界

- 基线 `60e037c5b98c1db92381ea5f4887382638089535`（实时 Gitee main）。本记录随代码提交，非冻结发布候选。
- Formal Product Layer: P4。Layer Target: `make branch.retire.historical` /
  `make branch.cleanup.feature` 两个受管清理入口及其脚本、测试与 allowlist 记录。
- 归属理由：分支引用退役属于运维交付工具，不属于平台契约、行业标准或客户模块语义；
  产品代码未改动，前端未改动，无数据库升级。
- 已知限制：本车道没有 Gitee PR 凭据，开放 PR 检查只能在报告中记录为
  `open_pr_check=none`，不冒充已完成的平台检查。
- 未新增环境、未新增备份、未重建数据库；本地只跑定向检查，完整 CI 交远端 PR。

## 本轮边界（对应用户裁决）

- `02a63d5b` 之后的本轮之前固定使用 GitHub `origin/main`，无法直接清理 Gitee 分支。
- 两个工作树此前分别占用已合并的 J13、CI 调度分支，使这两条分支无法退役。
- 9 条未包含于 `main` 的分支（含 3 条 `release/*`）只登记、不删除、不擅自合入。

## 入口扩展（无新工具，复用既有受管入口）

`scripts/ops/retire_historical_branch_refs.py`：

- 新增 `--remote`（默认 `origin`，Gitee 用 `gitee-mirror`）、`--expected-main`（必填完整 SHA）、
  `--open-pr-provider {github,none}`。
- 删除前先读所选远端实时 `main` 并与 `--expected-main` 比较，漂移即在上游拒绝，不进入任何删除分支。
- 非 `origin` 远端必须显式 `--open-pr-provider none`，报告记录 `open_pr_check=none`。
- 条目包含性核验：本地与远端 tip 均须包含于绑定 main；缺少本地对象时标记
  `containment in <remote>/main is unproven` 并跳过，不按“分支不存在”处理。
- 运行载体扫描（`scripts`、`config`、`deploy`、`make`、`.agent`、`.github`）命中的分支跳过；
  `docs/` 历史叙述不算载体。
- 新增只读 `--emit-manifest` / `--emit-inventory`：按实时 `main` 生成退役 manifest 与全量清单
  （分支名、远端／本地 SHA、包含关系、工作树占用、运行载体引用），不删除任何引用。
- manifest 允许 `local.state=absent`（Gitee 独有引用），此条目只退役远端引用；
  若本地引用实际存在则判为漂移并跳过。`main`、`master`、`release/*` 结构性排除。
- 远端删除为 `--force-with-lease=refs/heads/<b>:<sha>`，本地删除为 `git update-ref -d`；
  **没有 force 开关**。

`scripts/ops/branch_cleanup_safe.sh`：

- 删除 `CLEANUP_FORCE`；要求 `EXPECTED_BRANCH_SHA` 与 `EXPECTED_MAIN_SHA`（均完整 SHA）。
- `APPLY=1` 须 `CLEAN_BRANCH_CONFIRM=DELETE_EXACT_REVIEWED_BRANCH`。
- 拒绝 `main`/`master`/`release/*`、被工作树检出、当前检出、以及不包含于所选远端 main
  且非 `origin` 时无法用合并 PR 证明的分支；远端读取失败按拒绝处理。
- `CLEAN_BRANCH_REMOTE` 选择远端，默认 `origin`。

## 本轮实际处置（`gitee-mirror`，绑定 main `60e037c5`）

工作树先行处置：主工作树转入本 P4 分支（基于实时 main）；`sce-backend-odoo-upgrade-compat`
确认 clean 且无进程占用后转为 detached live main。两个已合并分支因此不再被工作树占用。

清单：31 条非 main 分支 = 22 条包含于 main + 3 条受保护 `release/*` + 6 条未包含。

预演：`eligible=21 skipped=1`（唯一 skip 为 `fix/gitee-temporary-integration-v1`，仍被
`.agent/goals/GITEE-TEMPORARY-INTEGRATION.yaml` 等 6 个运行载体引用）。

执行：`retired=21`（远端 21 条全部按 lease 删除；其中 17 条同时删除本地引用，
4 条为 Gitee 独有引用，记 `local_absent_confirmed`）。恢复 bundle
`artifacts/branch-retirement/20260927/gitee-historical-branches.bundle` 校验通过（39 heads）。

回读：远端剩 11 条（`main` + 6 条未包含 + 3 条 `release/*` + 1 条载体绑定），本地剩 12 条；
工作树 2 个（本 P4 分支 + detached live main）。未新增第三个工作树。

## 保留清单（未删除，仅登记）

- 未包含于 main：`feature/gitee-orm-restricted-channel`、`feature/user-identity-activation-p0`、
  `fix/candidate-gate-closure-01`、`fix/clean-repository-ci-governance`、
  `fix/gitee-unpublished-branch-sync`、`fix/product-ten-center-runtime-closure`。
- 受保护发布分支：3 条 `release/*`（行业成品镜像、客户燃料专题、用户认证）。按公开范围
  规则，本条不落客户品牌标识；完整分支名见未跟踪证据 `artifacts/branch-retirement/20260927/gitee-branch-inventory.json`。
- 运行载体仍绑定：`fix/gitee-temporary-integration-v1`（清零载体引用后再单独退役）。
- 本地存在但远端没有的分支（不在本轮远端清单范围，未触碰）：`audit/formal-entry-gap-intake`、
  `feature/frontend-business-entry-closure`、`fix/ci-integrated-closeout-20260925`、
  `fix/dev-form-contract-upgrade`、`fix/settlement-worksheet-action-scope` 及 3 条本地
  `release/*` 引用。

## 后续固定收尾

每次 PR 合入后按同一入口处置已合并分支：生成清单 → 预演 → `APPLY=1` 退役 → 回读远端、
本地引用与工作树。分支被运行载体引用时先清零载体，再由后续专题退役。

## 验证

| 层 | 命令 | 结果 |
|---|---|---|
| L1 | `make verify.branch.retire.historical` | 21 例通过（含实时 main 漂移拒绝、未合并跳过、载体引用跳过、远端不可读、非 origin 需显式 provider、远端独有引用退役、emit 只读清单） |
| L1 | `make verify.workspace.worktree.guard` | 76 例通过（含无 force 开关、lease 绑定、保护/占用拒绝、SHA 漂移拒绝） |
| L4 | 开发服务器／前端／浏览器 | 不适用（本轮无产品代码与前端改动） |
