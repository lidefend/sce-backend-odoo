# P4 Scheduled CI Gates Batch-A

## 1. 本轮变更

- 目标：修复定时 CI 的事件身份误判、共享工件写入竞争和动态凭据日志暴露。
- 完成：允许受管 `schedule` 前端发布事件；串行化 professional shards 并验证宿主原子写；掩码 backend suite 动态凭据；同步重新激活的 frontend release CI identity 测试生命周期登记。
- 未完成：远端 exact-head scheduled run；公共 delivery context switch log 由并行前端工作树占用，待其释放后追加。

## 2. 影响范围

- 模块：P4 GitHub Actions、CI 验证器和专项测试。
- 启动链：否。
- contract/schema：否。
- default_route / public intent：否。

## 3. 风险

- P0/P1/P2 产品风险：无产品代码改动。
- P4 风险：professional full gate 改为串行，运行时间可能增加；超时同步从 45 分钟提高到 90 分钟。
- 缓解：保持原有三个 shard 的命令和失败关闭语义，容器型测试 shard 最后执行。

## 4. 验证

- `make verify.ci.scheduled_gates`：PASS；61 个非零专项测试，Actions 安全扫描 PASS，宿主原子写探针 PASS。
- `make verify.branch.governance.consistency verify.baseline.iteration.execution.policy`：PASS；14 个分支治理测试、3 个基线策略测试及两个守卫均 PASS。
- `make security.secrets.scan`：PASS；10 个扫描器单元测试通过，全范围扫描退出码为 0。
- `make guard.registry.seed`：PASS；移除 1 个 stale orphan 条目，随后 audit 扫描 1274 个脚本并 PASS。
- `git diff --check`：PASS。
- `make verify.restricted`：NOT_RUN；该产品主线门禁包含本批次排除的前端重型链路和已知 P0/P1 产品阻断，不以无关失败替代 P4 专项证据。
- PR：[\#398](https://github.com/lidefend/sce-backend-odoo/pull/398)。首次 exact-head professional run [33585140881](https://github.com/lidefend/sce-backend-odoo/actions/runs/33585140881) 在进入 shards 前由 `verify.guard.registry` fail-closed，归因为本批次新增 Make 引用尚未移除 stale orphan 登记；已在本批次修复，等待新 head 重跑。
- 远端 scheduled/candidate CI：`verification_pending`，只接受修复后 exact-head 新运行作为完成证据。

## 5. 产物

- 代码层证据：Git diff 与完整候选指纹。
- 运行日志：本地命令输出；远端 GitHub Actions 日志待发布后生成。
- contract/e2e：N/A（本批次不改产品契约且不运行共享环境）。

## 6. 回滚

- 回退本批次 P4 提交即可；不涉及数据库、卷、fixture 或产品数据。

## 7. 下一批次

- 目标：在前端工作树释放后追加公共 context switch log，并发布 exact-head 候选验证定时门禁。
- 前置条件：当前前端产品化工作树完成或冻结；GitHub CLI 恢复有效认证。
