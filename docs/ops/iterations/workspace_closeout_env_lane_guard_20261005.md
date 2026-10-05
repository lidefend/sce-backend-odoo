# 工作区收口：环境车道 frontend fixture 守卫修复（2026-10-05）

Goal `WORKSPACE-CLOSEOUT-ENV-LANE-GUARD` / 批次 A。基线 main `16908106`（PR #570 后）。
本轮只修 `scripts/verify/frontend_productization_fixture_guard.sh` 自身的两处守卫缺陷，
不动产品代码，不放宽任何断言 / ACL / 字段权限 / 审计 / 负例。

## 1. 责任层

- **Formal Product Layer**：P4（ops 交付 / 验证工具）。
- **Layer Target**：`scripts/verify` 下前端验收夹具守卫（受管验证工具）。
- **Module**：`scripts/verify`、`scripts/common/frontend_acceptance_guard.sh`（只读依赖）。
- **Standard vs User-Specific**：平台验证机制。
- **Why Here**：守卫本身要证明「消费 DB_NAME 的受管夹具入口会 fail-closed 拒绝非验收库」，
  属于同一验证层的工具正确性。
- **Why Not Elsewhere**：不涉及 P0 前端契约/平台机制、P1 行业语义、P2 客户偏好或数据基线、
  P3 运行配置，也不做数据库 / 夹具 / 迁移 / 发布 / 部署。
- **Blast Radius**：一个守卫脚本的拒绝环入口绑定 + 受保护演示库解析；无产品代码变更。

## 2. 根因（本机可复现）

1. **指纹库未绑定**：守卫硬编码 `DB_NAME=sc_demo` 调
   `scripts/verify/frontend_productization_history_fingerprint.py`。`sc_demo` 存在但为空
   （`project` 未安装），脚本读 `project.project` 直接抛 `KeyError: 'project.project'`。
   受管 `local.dev` profile 的演示库是 `sc_dev_demo`（`.env.dev` 的 `DB_NAME`，
   `project` + `smart_construction_*` 已安装）。
2. **拒绝环入口错误**：守卫用 `make acceptance.frontend.fixture DB_NAME=<denied>` 断言拒绝。
   该目标（`make/runtime_ops.mk:1795`）走 `scripts/dev/frontend_acceptance_operation_entry.sh`，
   **不消费 `DB_NAME`**，也不会执行目标 DENY 断言，因此 `succeed` → 守卫误报
   `FAIL accepted DB_NAME=sc_demo`。
   真正消费 `DB_NAME` 且 fail-closed 的入口是
   `scripts/verify/frontend_productization_fixture.sh`（source
   `scripts/common/frontend_acceptance_guard.sh`，`guard_frontend_acceptance_scope` 产出
   `[DENY] frontend acceptance fixture requires DB_NAME=sc_frontend_acceptance`，rc=20）。

## 3. 修复（仅一处守卫脚本）

- 受保护演示库解析改为优先级：`FRONTEND_FIXTURE_GUARD_DB` → 受管 profile 的 `DB_NAME`
  （`make verify.frontend.fixture.guard` 在 `$(RUN_ENV)` 下运行，`local.dev` 绑定 `sc_dev_demo`）
  → 遗留默认 `sc_demo`。**不硬编码 `sc_dev_demo`**。
- 未绑定 / 未安装 / 空的库 → 明确 `[DENY] verify.frontend.fixture.guard needs a provisioned
  demo DB ...`，rc=2，替换原裸 `KeyError`。
- 拒绝环改为调用真实消费 `DB_NAME` 的 fail-closed 入口：
  `DB_NAME=<denied> SC_ENVIRONMENT=acceptance SC_ALLOW_DEMO_DATA=1 bash
  scripts/verify/frontend_productization_fixture.sh`，断言不变：
  `^\[DENY\] frontend acceptance fixture requires DB_NAME=sc_frontend_acceptance`。

## 4. 证据（受管入口，本机）

- 基线（未注入）：`make verify.frontend.fixture.guard` → rc=0；
  拒绝环 `sc_demo / postgres / arbitrary_database / <empty>` 4/4 `exit=20`；
  `[verify.frontend.fixture.guard] PASS sc_dev_demo fingerprint unchanged`；
  指纹 `FRONTEND_HISTORY_FINGERPRINT={"db": "sc_dev_demo", "demo_module_state": "installed", ...}`。
- 负例对照：临时把 `guard_frontend_acceptance_scope` 放宽为 `return 0` 后重跑，
  守卫在首个拒绝库即 `[verify.frontend.fixture.guard] FAIL database guard did not fail first`，
  rc=2；随后从备份复原，`git diff` 为空。证明断言真正检出注入，而非复述缺陷。
- 未绑定路径：`make verify.frontend.fixture.guard DB_NAME=sc_demo` → 明确 DENY，rc=2（fail-closed）。
- `bash -n` 通过。

原始日志（`.runtime/agent-runs/WORKSPACE-CLOSEOUT-ENV-LANE-GUARD/`，本地 receipt，非交付证据）：

- `ci_local_iteration.log`：`make ci.local.iteration` PASS，planner 推荐目标 `verify.frontend.fixture.guard`。
- `verify_frontend_fixture_guard.log`：目标运行通过，拒绝环 4/4 `exit=20`，指纹不变。
- `negative_control_relaxed_guard.log`：放宽守卫注入后 `FAIL database guard did not fail first`，rc=2。
  注入点是 `scripts/common/frontend_acceptance_guard.sh` 的 `guard_frontend_acceptance_scope`
  临时 `return 0`，已从备份复原（`git diff` 为空）。该拒绝环入口是只读验证脚本
  （`scripts/verify/frontend_productization_fixture.py` 首行声明 "Read-only verification"），
  负例只作用于非权威空库 `sc_demo`，受保护的 `sc_dev_demo` 始终未被写入。

## 5. 排除项

- 不新增全局测试框架；不为标签改写历史；不改分支前缀策略 / Gitee 镜像车道。
- 产品层开放项（`payment.request._state_from`、发布契约声明/关系 403 台账、`rendering_detail_state`
  裁决）保持登记，不在本轮修复。

## 6. 台账与索引约定

- `.agent/active-runs.json` 按本仓 workspace-closeout 先例（PR #569 / #570，合并提交
  `63283e2b` / `16908106` 均未改动该文件）在**提交态收敛为空索引**；分支运行指针只在本地
  工作树用于 `make agent.run.resume` / `ci.local.iteration` 的解析。
- 因此 L1 `ci.local.iteration`（PASS）是**内环**证据，采集时分支索引已注册；冻结 HEAD 不再
  运行该内环门禁，冻结头流程只跑一次 `ci.local.quick`。
- run 状态与 goal 状态置 `completed`（批次验收、证据、文档、回滚已记录）；主线集成仍以受保护
  PR 合并后为准。

## 7. 四层状态

- 批次验收：本批次完成（守卫修复 + 证据 + 负例对照）。
- 主线集成：待本候选经受保护 PR 流程合并后推进。
- 版本发布：未主张。
- 产品交付：未主张。
