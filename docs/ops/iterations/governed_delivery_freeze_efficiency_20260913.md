# 受管交付冻结效率收口

## 目标与边界

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：本地 L1→L2 handoff、冻结前生成证据准备、冻结后只读推送校验。
- Module：`make/ci.mk`、`scripts/verify/frontend_dev_incremental.py`、
  `scripts/ops/git_safe_push.sh` 及其非零测试和治理文档。
- 目标：相同候选不重复验证；所有可能改动 tracked 内容的生成动作在最终提交前完成；前端改动在开发期获得
  可执行的已登记 L2 建议。
- 不做：不扩大或删除 Quick/远端 required checks，不改变 PR 合并算法，不修改 P0–P3、数据库、fixture、
  runtime profile、浏览器或业务数据。

## 已确认根因

1. exact-head receipt 已能复用；材料 PR #468 的最终 `pr.merge` 明确命中 `REUSE`，并未重新运行 Quick。
2. `pr.push` 仍主动刷新 tracked 生成文件，陈旧时虽然会在远端访问前停止，但必须再提交并重新运行 Quick，
   因此冻结边界位置不正确。
3. `ci.local.iteration` 只提示人工选择 L2；既有前端增量映射没有覆盖 `frontend/packages/ui`，模板消费者改动
   也不会建议 primitive adapter，导致材料旧候选的该缺陷直到远端前端门禁才暴露。
4. 基线 `git_safe_push.sh --self-test` 仍要求 Quick 直接依赖组件清单守卫，但最新 Quick 已通过
   `ci.generated_evidence.preflight` 聚合承接；该失败归为 `validation_tool_defect`。

## 实施语义

- `make ci.local.iteration` 保持 L1-only，只输出相对 `origin/main` 的已提交差异与当前 tracked/untracked
  差异所映射的前端 L2 建议；输出明确为 `recommendation_only`、`testsRun=false`，不能冒充验证证据。
- `make ci.delivery.freeze.prepare` 是唯一聚合刷新入口：刷新通用生成报告、组件接管清单和 ContractForm
  拆分证据后立即运行只读预检。执行者审阅并提交差异，随后才冻结 HEAD 并运行一次 Quick。
- `make pr.push` 只验证 clean worktree、稳定 HEAD 和 `ci.generated_evidence.preflight`；不调用任何
  `refresh.*`，陈旧时零远端访问退出并指回冻结前准备。

## 验证计划

- L1：`make ci.local.iteration`、Python/shell 语法和 `git diff --check`。
- L2：前端增量映射单元、基线迭代策略单元、`git_safe_push.sh --self-test`，均须非零。
- 冻结前：真实运行 `make ci.delivery.freeze.prepare`，审阅生成差异并提交。
- 冻结后：只运行一次 `make ci.local.quick`；随后独立复核。P4 纯工具改动不需要模块升级、数据库、fixture、
  contract snapshot 或浏览器验收。

## 实施期验证结果

- L1：Python 编译、shell 语法和 `git diff --check` 通过；首次候选的 `make ci.local.iteration` 内含策略守卫
  12 项通过，并输出 14 个变更路径、0 个前端自动映射目标、`testsRun=false` 与
  `manualNonZeroL2Required=true`，未生成交付收据。
- L2：前端增量映射 10 项、基线迭代策略 12 项、`git_safe_push.sh --self-test` 13 个隔离场景通过。
  策略测试曾因使用不支持其同目录导入的 `python -m unittest` 调用方式失败；改回测试文件的既有直接入口后
  通过，归为 `command_invocation_error`，未修改产品或门禁语义。
- 基线推送自测要求旧的 Quick 直接依赖，修正为检查当前 `ci.generated_evidence.preflight` 聚合依赖后，
  13 个场景确认陈旧证据在远端访问前失败、正常推送路径不调用任何 `refresh.*`。
- 首次冻结前准备在组件清单生成处因新工作树缺少 UI 包依赖而停止，归为 `environment_defect`；未原样重试。
  通过受管 `make fe.install.cached` 以 lock SHA
  `0d3d8c93500e64b12a8d572bfe87e68aa359de632c63b31185870bc81ac1f6f2` 离线恢复依赖后，
  `make ci.delivery.freeze.prepare` 完整通过：测试清单 1366 条、组件清单守卫 7 项且 35 个必需点无缺失、
  ContractForm 拆分证据 1866 行。生成差异仅同步 `git_safe_push.sh` 的确定性复杂度行数。

## 首次独立复核与关闭

- 首次冻结候选 `57570dfbc40873ddea39d47dbf1f624e187658bd` 的 Quick 通过并签发 receipt，随后独立复核
  `REQUEST_CHANGES`：混合改动会掩盖未映射路径，映射器单测没有受管入口，冻结/推送边界的行为锁不完整。
  该 HEAD 与 receipt 立即降为历史证据，不用于后续候选。
- 计划器现在逐路径计算覆盖；“UI theme + 后端模型”同时输出 primitive-adapter 建议和后端路径的
  `manualNonZeroL2Required=true`。输出增加 `unmappedPathCount`/`unmappedPaths`，让人工 L2 handoff 可执行。
- 新增 `verify.frontend.dev.incremental.unit` 和 `verify.pr.push.unit` 两个受管入口并纳入 Quick；删除映射测试
  的陈旧 orphan 登记。registry 审计通过：1308 个脚本、1199 个被引用、109/109 orphan 已登记。
- 策略守卫锁定冻结准备的三个 refresh 后接 preflight 的顺序，以及 Quick 对两项 P4 单测的依赖；push
  15 个隔离场景进一步覆盖陈旧证据、预检致脏和 HEAD 漂移均在任何 `remote`/`ls-remote`/push 前停止。
- 修复后 L1 策略守卫 16 项通过并对 18 个当前 P4 路径全部保留人工 L2；受管 L2 为映射器 11 项、
  策略守卫 16 项、push 15 个隔离场景，均通过。

## 风险与回滚

- 风险：路径映射只能给建议，未知路径仍需人工选择非零 L2；不会自动宣称覆盖。
- 风险：`pr.push` 不再帮忙生成文件，未执行冻结前准备的候选会更早失败；错误信息提供唯一恢复入口。
- 回滚：整体回退本批 P4 提交；无数据库、运行态或产品数据回滚。
