# P4 Scheduled Backend Suite Batch-A

## 1. 本轮变更

- 目标：修复 `backend_test_suite` 定时 CI 的跨模块测试泄漏、零测试误通过，以及测试夹具对本地开发数据的依赖。
- 完成：按 Odoo 的 `tag/module` 语法将 `sc_smoke`、`sc_gate` 限定到当前模块；工作流逐模块保留日志、传播 Odoo 退出码，并要求非零测试成功摘要。
- 完成：补齐 bundle 测试注册，并为所有由定时工作流发现的测试模块登记至少一个有意义的 `sc_smoke` 或 `sc_gate` 测试。
- 完成：将失败测试的项目、成本科目、仓库、合同、币种、审核组和生命周期夹具改为测试数据库内自包含数据，不再依赖 `local.dev` 演示数据或固定 USD 假设。
- 未完成：远端 exact-head `backend_test_suite` 运行；发布候选后生成。

## 2. 影响范围

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：定时 backend CI workflow、治理测试入口和测试夹具。
- Standard vs User-Specific：仓库级 CI 治理能力，不属于客户基线、管理员运行配置或产品业务规则。
- Why Here：问题由定时工作流测试选择、失败传播和测试夹具可移植性共同触发，应在 P4 入口及测试层修复。
- Why Not Elsewhere：不修改 P0 平台机制、P1 建筑行业标准、P2 客户产品、P3 低代码配置、前端渲染或正式数据库数据。
- Blast Radius：仅影响定时测试模块选择、受管 `make test` 的裸标签归一化和测试数据库夹具；不影响菜单、模型字段、产品契约或公开 intent。
- 启动链：否。
- contract/schema：否。
- default_route / public intent：否。

## 3. 风险

- P0/P1/P2 产品风险：无产品实现代码或数据库迁移改动。
- P4 风险：`scripts/_lib/common.sh` 的裸标签归一化改为正确的 `tag/module` 选择器，所有通过该入口运行的裸标签测试都会被限定到目标模块。
- 缓解：显式包含 `/` 的既有选择器保持原样；安全守卫覆盖模块限定、退出码传播和非零测试摘要；所有定时模块均通过静态标签清单检查。
- 剩余风险：远端 runner 环境尚需 exact-head 定时工作流确认。

## 4. 验证

- `DB_NAME=sc_test_scheduled_backend_scoped MODULE=smart_construction_core TEST_TAGS='sc_smoke/smart_construction_core,sc_gate/smart_construction_core' make test`：PASS；`0 failed, 0 error(s) of 430 tests`。
- `DB_NAME=sc_test_scheduled_bundle_scoped MODULE=smart_construction_bundle TEST_TAGS='sc_smoke/smart_construction_bundle,sc_gate/smart_construction_bundle' make test`：PASS；工作流等价复跑为 `0 failed, 0 error(s) of 2 tests`。
- `make verify.ci.scheduled_gates`：PASS；所有专项测试均非零，Actions 安全扫描及 artifact guard PASS。
- `PYTHONPATH=scripts/verify python3 scripts/verify/test_github_actions_security_guard.py`：PASS；15 个测试。
- `python3 scripts/verify/github_actions_security_guard.py`：PASS。
- `make verify.branch.governance.consistency verify.baseline.iteration.execution.policy`：PASS；14 个分支治理测试、3 个基线策略测试及对应守卫均通过。
- `make security.secrets.scan`：PASS；10 个扫描器单元测试通过，全范围扫描确认 0 个高置信命中。
- Python 编译检查及 `git diff --check`：PASS。
- 定时模块标签清单：PASS；13 个 Odoo 测试模块均至少包含一个 `sc_smoke` 或 `sc_gate` 测试。
- `make verify.restricted`：NOT_RUN；该产品主线门禁包含本批次范围外的重型链路，本批次以 P4 专项静态守卫及非零 Odoo 运行证据验收。
- 远端 exact-head scheduled CI：`verification_pending`。

## 5. 产物

- 初始候选指纹：`/tmp/scheduled-ci-fingerprint-initial.json`。
- 中间候选指纹：`/tmp/scheduled-ci-fingerprint-interim.json`，digest `e5dd59cf009e3c7a06fad9e5f9417946d2452f5f84dd1ebf5de8c1aabdfce775`，7310 paths。
- bundle 工作流等价日志：`/tmp/scheduled-bundle-scoped.log`。
- 最终候选指纹：`/tmp/scheduled-ci-fingerprint-final.json`；发布前冻结。
- 远端 GitHub Actions 日志：发布后补齐。
- contract/e2e：N/A；本批次不改产品契约，不写共享验收数据库。

## 6. 回滚

- 回退本批次提交即可；不涉及正式产品数据、共享数据库、卷或 fixture 恢复。

## 7. 下一批次

- 目标：发布 exact-head PR 候选，运行并核对 `backend_test_suite`，通过后按授权合并和清理工作树。
- 前置条件：本地最终指纹、治理门禁及 clean commit 完成。
