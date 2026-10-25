# 测试基线可复现性契约 v1

## 成立条件与范围

基线必须绑定同一冻结源码、执行器、测试集合和运行环境，以实际执行证据成立，不能以注册表通过或退出码零代替。最终状态由本地证据、当前候选必需 CI、独立复核及主线合并共同确定；本文不是通过回执。

| 层面 | 机器校验与证据 |
| --- | --- |
| 资产身份 | 测试清单采用路径派生稳定 ID，增删资产不重排其他身份 |
| 离线复现 | `scripts/verify/test_baseline_manifest.json` 的完整模块集合，在三个新进程中正序、逆序、固定随机种子运行；逐测试 ID 与结果相同，非零、无重复、无缺项、无跳过 |
| ORM 复现 | 声明的契约组装确定性、低代码契约写入权限两组，共 6 个用例；每轮重新创建既有专属 `sc_test`，临时应用数据目录，正序/逆序/固定随机的类内方法顺序，实际日志身份与顺序必须匹配 |
| 运行身份 | 固定既有 `sc-local-test`、独立数据库角色与卷、精确 filter、源码挂载；隔离环境和 Make 参数穿透；镜像与已安装 Python 包摘要一致 |
| 结果守卫 | 共用 ORM guard 拒绝零测试、错误数据库/模块、失败和截断结果；超时清理本次精确容器，失败留下失败证据，不重试变绿 |
| 证据有效性 | 运行前后完整 tracked/untracked 源码内容和权限指纹一致；日志/子报告摘要回查；启动及失败使旧成功回执失效 |
| flaky | 当前 quarantine 为空；不稳定、skip、expected failure 不计入已通过集合，也不自动排除。增加例外前须独立设计/审查，不得降低必需断言 |
| 集成 | 最终候选完整 Quick、当前源/目标的四项必需 CI、独立代码复核、外部归档、受保护 PR 合并和 main 回读 |

离线范围由 manifest 明确列出，覆盖基线执行、选择、证据来源、回读和注册表机制。ORM 隔离证明是这两组的**类内方法顺序**证明，不扩大为类间、模块间或全仓任意测试的证明。完整产品集成仍由当前候选风险选择的 CI 套件负责。其他历史测试覆盖债务保留在既有覆盖注册表中，不计入上述已证明范围。

## 受管使用

1. `make local.test.prepare`：只读校验既有私有 profile、卷归属及 Compose 源码挂载；不创建第二套凭据。
2. `make local.test.test MODULE=smart_core TEST_TAGS=<明确选择>`：串行使用专属测试库；每次重建 **仅 sc_test**，安装请求模块并运行测试，至少实际执行一个请求模块用例。
3. `make local.test.baseline`：运行并验证上述 ORM 三轮；原始日志和回执位于 `.runtime/test-baseline/`。
4. `make verify.test.baseline`：运行 manifest 离线三序验证，已接入完整 Quick。
5. `make verify.test.baseline.ready`：只读回查当前源码的完整离线/ORM回执、用例集合、顺序和日志哈希；生成本地验收状态，不授予远端合并或部署资格。

`local.test.up/down` 仅启动/停止本 profile 的 db/redis。测试不启动持久 Odoo/nginx，不影响开发、demo、验收或生产数据库。既有 profile 的历史 `SC_ENVIRONMENT=dev` 凭据文件保持只读；实际测试容器强制 `test`、禁止 demo，并从真实环境与测试日志回读。

## 复用边界

Quick 已登记套件通过既有 `evidence_scope` 与成功祖先回执按输入判断复用；未登记或未知输入继续 RUN。套件命令、Make/workflow定义和相关依赖变化会使证据失效。

普通 ORM 历史结果复用仍关闭：静态文件扫描的 `static_inputs_resolved` 不等于动态依赖完整，`dependency_closure_complete` 明确保持 false；artifact-attempt、运行时契约和事实来源等缺口不能被包装成可信通过。全量执行可以建立正确的测试基线，不要求为了复用率降低证据标准。

## 历史与验收记录

PR733 提供稳定清单和初始本地 profile；PR734 修正探针并接入 Quick 指纹；PR732 建立后端证据来源边界。2026-10-26 本轮补齐真实隔离执行、非零守卫、三序比较与失败回执失效，并把上述两组 ORM 标签接入远端固定选择。当前执行状态、原始证据、失败归因及最终候选见 `docs/ops/iterations/test_baseline_closure_20261026.md` 与对应 run；冻结后的 CI/合并证据留在原始 runtime 索引及外部归档。
