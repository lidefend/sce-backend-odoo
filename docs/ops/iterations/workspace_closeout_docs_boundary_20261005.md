# 工作区整体收口与产品边界守卫模块根修复（P4 运维治理）

- 批次：`WORKSPACE-CLOSEOUT-DOCS-BOUNDARY`
- 分支：`fix/workspace-closeout-docs-boundary-20261005`
- 基线：`main` = `63283e2b3e752a14e44cffca8d3b19be49be4ace`（PR #569 合并后干净主线）
- 责任层：P4 ops/交付治理与验证工具；无产品语义、契约、数据库、夹具或部署改动。

## 1. 产品边界守卫模块根修复（唯一就地修复项）

`verify.docs.product_boundary` 长期 FAIL：`modules documented but not present under addons:
smart_construction_demo`。核对结论：

- `smart_construction_demo` 在 `docs/product/formal_product_boundary_v1.md`
  `## 当前模块归属` 表中正式登记为 **P4 演示工具**，是合法的目录条目；
- 该模块实际位于 `demo_addons/smart_construction_demo`，且
  `scripts/verify/customer_module_extraction_guard.py` **要求**演示模块必须位于
  `demo_addons/`；仓库另有 `customer_addons/` 模块根并被多处守卫当作合法根；
- 缺陷在守卫：`product_boundary_catalog_guard.py` 只扫描 `addons/`，把登记于
  `demo_addons/` 的模块误判为“陈旧文档”。文档与模块均正确，守卫的模块根不完整。

修复（不放宽任何断言、ACL、字段权限或审计）：

- 新增 `modules_under(root)` 与 `present_modules()`，`present_modules()` 汇总
  `addons/`、`demo_addons/`、`customer_addons/`（相对 `ADDONS_ROOT.parent` 解析，
  保持单测可打桩）。
- **`extra = documented - present`** 改为在全部已注册模块根内求差；
  **`missing = addons - documented`**（覆盖率方向）与其余断言完全不变。
- 新增单测 `test_documented_module_in_auxiliary_root_is_not_extra`：锁定“辅助根内
  已登记模块不算 extra”，并同时锁定“任何根下都不存在的登记模块仍算 extra”。

证据：

- `python3 -m unittest test_product_boundary_catalog_guard` = **7 tests OK**
- `make verify.docs.product_boundary` = **PASS**（覆盖 13 个 addon 模块、5 个产品层）
- `make verify.docs.all` = **PASS**（inventory / links / temp guard / contract sync / product boundary 全绿）

## 2. 工作区分支台账决策（收口）

`REMOTE-BRANCH-BACKLOG-RETIREMENT-B` + `REMOTE-BRANCH-CARRIER-RETIREMENT-B` 后，
origin 稳定在 **75** 头（`1 main` + `24 feature` + `19 release` + `16 fix` + `8 codex` +
`3 feat` + `2 backup` + `1 refactor` + `1 audit`）。逐条判定（`git cherry origin/main` 证）：

- **52 条含真实未合并提交的历史分支（保留）**（`git cherry origin/main` 有 `+` 行；如
  `codex/backend-contract-lifecycle-authority-v1` +31、`codex/contract-governance-closure-v1`
  +30、`feature/product-center-baseline-v1-closeout` +29、`codex/long-running-business-iteration`
  +13、`feature/business-task-scene-contract-v2` +9 等）。这些分支携带**未合并工作**，
  受管入口要求 exact-head 已合并证明或 owner `reviewed_explicit`，无二者时删除会造成
  工作丢失。**决策：保留**，不做无授权的强删。
- **3 条内容已合并但前缀不在治理正则内的分支（保留，待前缀策略）**：
  `feat/scene-r3-round7-action-chain-upgrade-pilot`、`feat/scene-r3-round8-final-fallback-eradication`、
  `backup/diverged/release/wutao-single-user-activation-01r`（`git cherry` 无 `+` 行）。
  **决策：保留**。新增前缀到治理正则属守卫策略变更，收益低、回归风险高，且无 owner 前缀策略指令。
- **19 条 `release/*`**（受保护）与 `main`（1）。
- 非 main/非 release 合计 **55** = 52 未合并 + 3 内容已合并。

## 3. Gitee 镜像车道：有界 DENY（单列）

Gitee 仅为镜像；受管 `main.gitee.catchup` 硬绑定历史主线 `de9a230d`，Gitee main 现为
`814bbc28`（⊃ `de9a230d`），**无受管入口**推进到当前 main；Gitee 17 分支无 exact-head 证据。
**决策：维持有界 DENY**，不泛化为“环境全部通过”。推进需新 P4 授权 + 环境前置。

## 4. 开放问题登记（跨层，本轮不修，绑定既有证据）

以下是跨产品层或运行环境的既有问题，各自已有迭代台账；本轮只登记、不改动、不放宽：

1. **定时 CI `release_candidate_gate` schedule 车道**：最新 schedule（`425c0118`，
   2026-10-04T21:50Z）在 `wait_for_candidate_checks` 失败，原因是同 SHA 的
   `frontend_release_gate` schedule 兄弟运行被 `concurrency` **cancelled**，而该 gate
   将非 success 一律判失败。同 SHA 的 push 车道 `frontend_release_gate` = success；
   当前 main 四项必需检查与全部 push 车道均为 success。属**提交绑定的调度车道观察**，
   非当前主线阻断；观察下一次 schedule 在现行 main 上的结果，若复现则为独立 CI 车道专题。
2. **`verify.frontend.fixture.guard` KeyError**：需要 compose 运行环境
   （`check-compose-project check-compose-env`），属重建/快照环境 DENY 车道，未恢复前不进入。
3. **`payment.request._state_from` 不一致**：`["draft"]` 而提交进入 `submit`（OCA
   `restart_validation()` 对该模型不生效）。已在 `scheduled_ci_core_regression_recovery_20261004.md`
   记录，产品行为已由 `approval_policy.py` 修复；`_state_from` 本身属 P1 产品层，独立专题。
4. **发布契约声明不一致 / 关系读取 403**：见
   `scheduled_ci_full_lane_navigation_declaration_20261004.md` 与
   `scheduled_ci_core_regression_recovery_20261004.md`（batch 2，P0 通用消费层，已修复并由单测锁定）。
   前端 full 车道为环境/浏览器车道，未在本轮重跑。
5. **`rendering_detail_state` 排除**：引用既有证据与裁决，不再重复证明。

## 5. 四层状态

- 批次验收：本轮批次完成（守卫修复 + 收口记录）。
- 主线集成：完成至 `63283e2b`（本轮候选合并后推进）。
- 版本发布：未主张。
- 产品交付：未主张。
