# Backend Suite Module Isolation — Batch-CI-F1

## 1. 本轮变更

- 目标：恢复 nightly `backend_test_suite` 的逐模块语义，使 clean CI 只运行目标模块的 clean-safe 测试，并拒绝零测试伪绿。
- 根因：默认 `sc_smoke,sc_gate` 经公共 tag 规范化后同时包含裸全局标签，且旧模块限定格式不符合 Odoo 17 的 `[-][tag][/module][:class][.method]` 语法。安装任何依赖 `smart_construction_core` 的模块都会重复运行其 P1 测试；这些测试依赖受治理 `local.dev` demo/fixture，不能在每个临时 clean DB 中成立。
- 完成：
  - 模块发现从“存在 `tests/` 目录”收紧为“存在 `tests/test_*.py` 文件”。
  - 修正公共 tag 规范化：裸 tag 只生成 `tag/module`，不再追加全局 tag，并保留合法的 Odoo selector。
  - 为 12 个已知模块声明模块限定的 clean-safe 默认 selector；`smart_construction_core` 使用 `sc_install`，完整 P1 `sc_gate` 仍由 `local.dev` 权威入口负责。
  - 无专用 clean tag 的模块使用 `/<module>`，仍只允许目标模块测试。
  - 手动 override 的裸 tag 自动限定到当前模块；跨模块显式 selector 失败关闭。
  - 每个模块必须出现非零成功摘要；`0 tests` 或缺少可信摘要均失败。
  - 新增 GA020/GA021 守卫和行为测试，防止模块隔离与非零证据回退。
- 未完成：精确候选 head 的远端 `workflow_dispatch`，需在提交并通过 `make pr.push` 后执行。

## 2. 影响范围

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：GitHub Actions backend test orchestration and workflow security guard。
- 模块：`.github/workflows/backend_test_suite.yml`、`scripts/_lib/common.sh`、`scripts/verify/github_actions_security_guard.py` 及其测试。
- Standard vs User-Specific：仓库级 CI 治理标准。
- 启动链：否。
- contract/schema：否。
- default_route / public intent：否。
- 数据库：workflow 继续使用原有 run-scoped project、临时数据库、卷和凭据；未新增 profile、数据库、端口、卷或 fixture。

## 3. 风险

- P0：无产品运行时代码改动。
- P1：nightly clean suite 不再错误地把依赖 `local.dev` fixture 的完整 P1 gate 当作 clean-install 测试；完整 `sc_gate` 的权威不变。
- P4：模块新增测试但未登记专用 clean tag 时会走 `/<module>` fallback；非零摘要门禁会阻止空测试伪绿。
- 缓解：默认 selector 与真实测试 tag 的对应关系、公共 tag 规范化行为由 20 个行为/守卫测试覆盖；跨模块 override 被拒绝。

## 4. 验证

- `make verify.ci.scheduled_gates`：PASS，20 个 GitHub Actions guard tests 及相关 scheduled-gate tests 全部通过。
- `python3 scripts/verify/test_github_actions_security_guard.py`：PASS，20/20。
- `python3 scripts/verify/github_actions_security_guard.py`：PASS，GA020/GA021 均关闭。
- `make verify.restricted`：FAIL（环境阻断），候选静态、前端 typecheck/build 与多数边界守卫已通过；live scene probe 因 `runtime probe authentication unavailable: source=dev_test_bootstrap` 失败。
- `make verify.backend.guard`：FAIL（同一环境阻断），trace_id `2d9b393b2d67`，登录返回 401；此前 backend/controller/intent 边界检查均通过。
- `make verify.guard.registry`：FAIL（基线已有 4 个无关 orphan scripts：`test_backend_business_fact_model_audit.py`、`test_scene_inventory_freeze_guard.py`、`test_scene_inventory_test_boundary_guard.py`、`test_scene_r3_action_target_scene_resolution.py`）。
- 原始失败证据：GitHub Actions run `34061579629`, job `101562930320`, exact SHA `5a18788534981a2025bc24acecb9bfb1740b0f7c`。

## 5. 产物

- 迭代记录：本文件。
- 远端失败日志：`https://github.com/lidefend/sce-backend-odoo/actions/runs/34061579629`。
- contract snapshot：N/A（无 contract/schema 改动）。
- browser/e2e：N/A（无前端或用户旅程改动）。

## 6. 回滚

- 回退本批次 workflow、GA020/GA021 守卫及其测试提交。
- 不需要模块升级、数据库恢复、fixture reset 或 contract snapshot 回退。

## 7. 下一步

- 提交冻结候选，通过 `make pr.push` 发布同一 head，并对该分支执行一次 owner-authorized `backend_test_suite` workflow dispatch；只有全模块非零通过后才可将本批次标记为完成。
