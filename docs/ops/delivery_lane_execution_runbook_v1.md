# 交付车道执行 Runbook v1

本文件是受管交付车道的**执行顺序与易错点规则**。目标是让不同执行器按同一顺序执行、
不重复踩同一个坑；能被机制拦截的已尽量机制化（见第 1、2 节），机制化不掉的顺序在此固化。

## 0. 身份与前置

所有交付动作前必须完成：确定目标仓库与工作树、`git rev-parse --show-toplevel`、
`git branch --show-current`、`git rev-parse HEAD`、`git status --porcelain=v1 --untracked-files=all`，
以及 `make agent.run.resume` 返回 `resolved`。

## 1. GitHub 主线集成（受保护合并）

严格顺序：

1. 确认 `origin/main` 无漂移，记录 old main SHA。
2. `make ci.local.iteration`（L1 便宜先跑）。
3. `make ci.delivery.freeze.prepare`（生成证据，审查后提交）。
4. 若 journal 保存/角色探针输入有变化，按受管入口重放（`verify.local.dev.journal.save` /
   `verify.local.dev.journal.role`）。
5. `make ci.local.quick`——在 clean 冻结 HEAD 上直接跑。
6. 独立复核 + 外部归档 `make workspace.evidence.archive`。
7. `make pr.push` → `make pr.create`。
8. 等四项必需检查全绿且源/目标身份一致：
   `public_guard`、`merge_policy_gate`、`professional_quality_gate`、`frontend_release_gate`。
9. `make pr.merge.preflight PR=<n> EXPECTED_HEAD=<full-sha>`。若报合并证据套件阻断，先按第 2 节重录。
10. `make pr.merge PR=<n> EXPECTED_HEAD=<full-sha>`（squash）。
11. `make main.sync` 回读 main，核对合并树与候选树一致。

机制化已拦截的坑：

- `pr.merge.local_quick_gate` 的 Quick 回退现在剥离 `MAKEOVERRIDES` 再跑，不再因
  `PR=/EXPECTED_HEAD=` 命令行变量误触 “makefile injection or command overrides cannot sign coverage”。
- 前端增量不再触发后端 ORM：`backend_impact_plan.py` 已将 `make/frontend.mk` 列入 `NON_RUNTIME`。

## 2. 合并证据重录（preflight 阻断 evidence suite 时）

触发条件：preflight 报 `frontend_presentation` / `list_surface_structure` / `relation_roundtrip`
“source is not an ancestor of the head” 或 “inputs changed”。注意 squash 合并后旧分支 head
不是新 main 的祖先，必须重录到新候选，不能复用旧 bound_head。

严格顺序（验收运行时在线：`sc-backend-odoo-acceptance` / `sc-fe-r2-p1-01`）：

1. `make frontend.standard.preview.build`（在候选 head 重建验收预览）。
2. `make frontend.standard.preview.up`（监听器切到新 dist）。
3. `make backend.acceptance.up`（把验收后端 SC_SOURCE_REVISION 切到候选 head）。
4. `make acceptance.runtime.contract_receipt`（重新生成合同回执）。
5. 依次重跑三套：
   - `make verify.frontend.presentation.local.browser`
   - `make verify.frontend.list_surface_structure.browser`
   - `make verify.frontend.relation_roundtrip.browser`
6. 录入：

```bash
REL=$(ls -d .runtime/acceptance/local/<head>/relation-roundtrip/*/summary.json | head -1)
python3 scripts/ops/acceptance_evolution_record.py --stage merge \
  --suite frontend_presentation=.runtime/final-acceptance/frontend-presentation/header.json \
  --suite list_surface_structure=.runtime/final-acceptance/list-surface-structure.json \
  --suite relation_roundtrip="$REL" \
  --output .runtime/acceptance-evolution/evidence.v1.json
```

7. 回到第 1 节第 9 步重跑 preflight。

机制化已拦截的坑：

- `standard-contract-prerequisite` 在生成合同回执前先核对验收后端 `SC_SOURCE_REVISION == HEAD`，
  不匹配即退出并提示先 `make backend.acceptance.up`，不再等到 probe 报 `runtime_identity_not_verified`。

## 3. 日常开发服务器（sc-root）部署

前置：服务端 `verify.daily_dev.runtime_repo.clean` 通过。严格顺序：

1. `daily.runtime.main.bundle_sync`（代码快进，核对 old/new SHA 与 clean）。
2. `daily.runtime.database.duty.refresh`（先重建容器到新版本，recreate services，不跑迁移）。
3. `daily.runtime.database.duty.upgrade`（再跑模块迁移，含升级前恢复点）。
4. `daily.runtime.frontend.build`（构建服务前端包）。
5. `daily.runtime.source_revision.align`（demo 与 platform_control 两个 duty 各一次）。
6. `daily.runtime.published_face.converge`。
7. `daily.runtime.entry.verify`。
8. 回读两个 duty 的 `/api/runtime-version`，确认 `source_revision == 目标 SHA`。

顺序不可反：`refresh` 必须先于 `upgrade`，因为 upgrade 的就绪断言要求容器已发布新版本。

## 4. 只读走查复现真实报错

只读观察器会拦截 `api.onchange`，导致新建表单出现“网络异常”假象；要复现真实按钮/动作报错时，
必须脱离观察器（不加 route 拦截），并以真实登录 + 真实点击抓取 `execute_button` 响应与最终跳转。

## 5. 按钮动作导航权威模型

- 菜单/导航面导航 → `routeAuthority`（已发布叶子）。
- 按钮返回动作导航 → 按钮执行本身授权；`buttonNavigationAuthority.ts` 发放一次性、绑定精确目标、
  短时有效、用后即失效的导航权威，由路由守卫消费。

## 6. 交付状态口径

批次验收、主线集成、部署、用户验收四个状态分开报告；合并不等于部署，部署不等于交付。
