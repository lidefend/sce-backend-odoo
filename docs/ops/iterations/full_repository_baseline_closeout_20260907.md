# Full Repository Baseline Closeout — 2026-09-07

## 1. 本轮变更

- 目标：在既有 `audit/full-repository-baseline-20260907` 候选上完成恢复升级、演示数据、进度场景权限与受管交付门禁收口。
- 完成：
  - `smart_construction_core` 升级到 `17.0.0.162`；历史迁移在旧租户表/列或新父模型元数据尚未建立时保持可重放，并由后续 registry 同步继续收口。
  - 演示项目显式绑定公司；S67 场景包使用业务管理员角色语义，避免依赖平台管理员身份。
  - `project.progress.entry` 向成本只读、成本用户和成本经理提供分层 ACL、动作、菜单及项目成员/公司记录规则；只读角色无写、创建、删除权限。
  - 修正 my-work 幂等测试补丁位置及付款工作项审计事实预期。
  - 公司快照以同一项目经理身份比较主、次公司；动作闭环以独立财务角色字段契约快照验证付款审批状态。
  - 本地健康检查固定使用系统 `curl`，规避不支持 `--write-out` 的兼容包装器。
- 未完成：未执行提交、独立审查、远端推送或 PR 更新；这些操作必须绑定后续冻结 commit 和完整候选指纹。

## 2. 影响范围

- Formal Product Layer：P1 construction industry standard product；P4 ops delivery tool。
- Layer Target：`smart_construction_core` migration/security/demo authority；scene company/action-closure verification orchestration。
- 模块：`smart_construction_core`、`smart_construction_demo`、`scripts/dev`、`scripts/verify`、`make/dev_test.mk`。
- 启动链：否。
- contract/schema：不改变公开 contract/schema；仅改变角色化验证快照的采样身份和独立状态文件。
- default route / public intent：否。
- Blast Radius：项目进度菜单/动作/模型权限、旧租户增量升级、演示项目公司锚点、双公司和动作闭环报告。财务/风险角色权限未扩大。

## 3. 风险

- P0：无已知未缓解 P0 风险；平台内核、公开 intent 与前端契约消费未改动。
- P1：进度记录新增读取面可能暴露跨项目数据；通过全局公司规则和项目经理/关注者成员域限制，并以只读 ACL 测试锁定。
- P1：历史数据库结构差异可能继续暴露更早版本缺口；本轮迁移仅补齐已实际触发的缺失表/列/父模型元数据，仍须由 clean-install 与租户演练分别验证。
- P2：本地 `curl` 路径依赖 Linux 系统位置；允许通过 `CURL_BIN` 显式覆盖，默认环境已验证。

## 4. 验证

- `make ci.local.quick`：PASS；测试清单 1355 项，前端 lint 0 error / 31 个既有 warning，严格类型检查与构建 PASS。
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=project_progress_read_boundary`：PASS，3 tests / 0 failures / 0 errors。
- `make local.dev.upgrade MODULE=smart_construction_core`（`CODEX_NEED_UPGRADE=1`）：PASS。
- `make local.dev.sync_demo`：PASS；demo authority checks PASS。
- `make verify.scene.base_contract_source_mix.role_matrix.guard`：PASS；executive/pm/finance/ops 均为 66 个场景。
- `make verify.scene.base_contract_source_mix.company_matrix.guard`：PASS；company 1 与 company 3 均为 66 场景、asset ratio 0.9091、runtime-minimal ratio 0.0909。
- `make verify.product.delivery.action_closure.smoke`：PASS；付款申请、项目台账、预算管理 3/3。
- `make verify.restricted`：PASS；frontend、scene readiness、action closure、module capability、backend contract closure、governance truth 全部 PASS。
- `make local.dev.health`：PASS；`project=sc-local-dev`、`db=sc_dev_demo`、`dbfilter=^sc_dev_demo$`。
- 过程中发现并修复的失败：PM runtime-minimal 7/66、主公司管理员资产覆盖 17/66、动作闭环复用 PM 快照导致 `workflow_states<1`。最终重跑均已转绿。

## 5. 产物

- Snapshot：`artifacts/local-dev/snapshots/20260907T092832Z/`（数据库 dump + filestore archive）。
- Mainline summary：`artifacts/backend/delivery_mainline_run_summary.json`。
- Company matrix：`artifacts/backend/scene_base_contract_source_mix_company_matrix_report.json`。
- Action closure：`artifacts/backend/product_delivery_action_closure_report.json`。
- Delivery scoreboard：`docs/product/delivery/v1/delivery_readiness_scoreboard_v1.md`。
- Generated inventory：`docs/engineering_convergence/test_inventory.csv`（1355 entries）。
- Playwright / browser artifact：N/A；本轮没有前端页面实现，restricted 使用契约与前端构建门禁。

## 6. 回滚

- Commit：当前仍为未提交候选；提交后使用该批次 commit 的普通 `git revert`，禁止重置或覆盖用户工作区。
- 代码回滚后：通过 `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core make local.dev.upgrade MODULE=smart_construction_core`，再执行受管 fixture sync、快照与 restricted 门禁。
- 数据恢复证据：保留 `artifacts/local-dev/snapshots/20260907T092832Z/`；当前仓库没有 `local.dev.restore` 入口，若需要写回该持久开发库，必须作为独立 P4 治理任务补齐或使用已授权恢复流程，不能手工拼装数据库命令。

## 7. 下一批次

- 目标：冻结完整 tracked+untracked 候选指纹，完成独立只读审查，并在审查通过后形成单一可回滚提交。
- 前置条件：确认当前 31 个文件组成一个可接受产品结果，且没有新的非本轮写入或共享数据库竞争。
- 阻塞：当前无本地验证阻塞；独立审查与远端发布尚未执行。
