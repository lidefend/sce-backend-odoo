# Active-Run Binding Retirement Guard（run 绑定退役闭环，2026-10-06）

Run: `.agent/runs/ACTIVE-RUN-BINDING-RETIREMENT-GUARD/run.json`
Branch: `codex/active-run-binding-retirement-guard-20261006`
Baseline: `cb5ca646193007bef8b1aa0a94d4dade1edf69f0`（`main`，PR #592 后）

## 1. 动机：一个反复出现的记账循环

用户观察到每次收口都要多付一次「提交 + 冻结 + 一次 quick」。事实链如下
（`git log main -- .agent/active-runs.json`）：

| PR | 提交 | 对 `.agent/active-runs.json` 的改动 |
| --- | --- | --- |
| #586 | `48441a3b` | 清成 `{}` |
| #589 | `dd75f83c` | 写入 `codex/daily-dev-user-acceptance-completion-20261006` 绑定 |
| #591 | `b0f0dba5` | 改绑到 `codex/daily-dev-user-acceptance-closeout-20261006`，该分支随即退役 → **悬空** |
| #592 | `cb5ca646` | 清回 `{}` |

即：候选 PR 把自己的分支绑定写进 `main`，分支随后被退役，`main` 便留下一条指向
**已删除分支**的映射；而没有任何门禁或入口阻止这个状态被静默造出。清理它需要
一次完整的 PR 周期，这就是重复劳动的来源。

## 2. 责任层与边界

- **Formal Product Layer**：P4（ops delivery 工具层）。
- **Layer Target**：`scripts/ops/branch_cleanup_safe.sh`（受管分支退役入口）。
- **Standard vs User-Specific**：运维工具，非行业/客户语义。
- **Why Here**：退役入口是唯一知道「分支即将消失」的地方，因此也是唯一能在删除前
  阻止悬空绑定的地方。
- **Why Not Elsewhere**：不改 `agent_run_context` 的解析规则，不改 CI 门禁，
  不放宽任何退役/删除前置条件，不引入强制开关。
- **Blast Radius**：`branch_cleanup_safe.sh` 及其行为测试；不涉及运行态、数据库、容器。

## 3. 改动

`scripts/ops/branch_cleanup_safe.sh`：在 APPLY 之前新增 fail-closed 前置条件——
若所选 remote 的 `main` 仍在 `.agent/active-runs.json` 中绑定**待退役分支**，则拒绝退役，
并提示「先用一个普通已合并 PR 清除绑定」。

- 读取对象固定为 `--expected-main` 指向的那个 main SHA，不重新解释远端状态。
- 对象本地缺失时先 `git fetch <remote> main`；仍不可读则**拒绝**（fail-closed），
  绝不把「读不到」当成「没有绑定」。
- 绑定表不可解析（非对象、缺 `branches`、JSON 损坏）同样拒绝。
- 忽略绑定**其它**分支的情形：只有指向待退役分支自身才是悬空风险。

## 4. 验证

- 新增行为测试（`scripts/ops/test_safe_worktree_cleanup.py`，
  `GovernedBranchCleanupScriptTest`）：
  - `test_retirement_is_refused_while_main_binds_the_branch`：命中 → 非零退出、远端与本地分支都保留。
  - `test_retirement_allows_a_main_that_binds_another_branch`：绑定他分支 → 正常退役。
- `make verify.workspace.worktree.guard`：见 §5。
- `make ci.local.iteration`：见 §5。
- 未放宽任何既有测试：`test_apply_deletes_remote_then_local` 等路径的 main 无索引文件，
  走「carries no run index」分支，行为不变。

## 5. 结果

- `make verify.workspace.worktree.guard` → `Ran 125 tests ... OK`（含新增 2 例）。
  收据：`branch_cleanup_guard`（`status=passed`，`test_count=125`），原始日志
  `.runtime/agent-runs/ACTIVE-RUN-BINDING-RETIREMENT-GUARD/branch_cleanup_guard.log`。
- **负例基线（证明探针有效）**：把 `branch_cleanup_safe.sh` 换回改动前版本，
  `GovernedBranchCleanupScriptTest` 变为 `Ran 11 tests ... FAILED (failures=1)`，
  失败点正是 `test_retirement_is_refused_while_main_binds_the_branch`（`AssertionError: 0 == 0`）；
  恢复改动后 11/11 OK。即该断言锁的是真实行为，不是文本出现。
- `make ci.local.iteration` → `status=resolved`、`outside_scope=[]`、PASS。
- 未放宽任何既有断言；既有退役路径（main 无索引文件）行为不变。

## 6. 四层状态

- 批次验收：通过（改动为本批范围内，定向非零测试 + L1 全绿）。
- 主线集成 / 版本发布 / 产品交付：本记录仅覆盖批次层，未在写入时主张。
