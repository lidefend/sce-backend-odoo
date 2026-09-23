# GitHub 受限期间的临时 Gitee 集成

[English](gitee_temporary_integration_v1.en.md)

本车道是仓库所有者于 2026-09-23 授权的 P4 流程调整，不是永久更换仓库。
`origin` 保持 GitHub，`gitee-mirror` 保持 `git@gitee.com:leegege/sce-product-odoo.git`。
既有 `gitee_webhook_ci_v1.md` 的 Gitee 主仓说明属于历史部署方案；本次是否可用须按当前身份验证。

## 起点与顺序

- GitHub 本次读取返回 HTTP 403 `Sorry. Your account was suspended`，`pr.status` 包装退出 0 不代表通过。
- Gitee main 为 `b9e3e56a80c02c1eb277d2ac573e10286c4cd8e8`，是本地主线
  `de9a230d3faab18dd60a219f445f932a8af9d7f5` 的祖先，相差 133 个提交。
- 页头专题 `22390c84f7d2447e055b6e1c67a194778ce9a10a` 与稳定性专题
  `baad61f12e6a7fff0e5b9953609be5f5d52fbdff` 均未集成到本地主线；两者有共同修改文件，
  必须串行处理集成冲突与受影响验证，不能凭工作区干净直接合并。

1. 使用合规控制分支执行只读检查及 `main.gitee.catchup` 预演。
2. 查清并受管隔离自动同步、机器人和部署副作用，建立单一写入窗口；审阅精确历史补齐范围并获得执行授权，clean 控制分支验证恢复 bundle 后才执行历史主线快进。
3. 对新候选完成既有 L0—L5、独立审查和外部证据归档。Quick 与冻结候选一致；证据按输入复用。
4. 用 `pr.push.gitee` 发布候选；创建 Gitee 同仓 PR，记录源／目标完整 SHA。
5. 核实 Gitee webhook/worker 所跑门禁、精确 SHA、非零测试和日志；仅 Push 公开守卫不能替代 PR
   专业门禁，也不能仅用 HTTP 健康状态证明 CI 成功。缺少原 required checks 的能力时登记阻断并补齐，不能降级。
6. 所有者批准合并方法后走受保护 Gitee PR。合入前重新核对 head/base；平台若不能原子绑定 reviewed HEAD 与目标 main，
   不通过旧机器人或直接 push 绕过。实际合并能力当前未验收，不宣称已完成主线切换。

## 命令

```bash
make verify.gitee.integration.unit
make gitee.integration.inspect EXPECTED_HEAD=<当前完整HEAD> GITEE_EXPECTED_MAIN=<实时Gitee主线SHA>
make main.gitee.catchup EXPECTED_HEAD=<当前完整HEAD> GITEE_EXPECTED_MAIN=<实时Gitee主线SHA>
# 仅在具体历史补齐已获授权后添加：
# APPLY=1 GITEE_INTEGRATION_CONFIRM=FAST_FORWARD_HISTORICAL_GITEE_MAIN

make pr.push.gitee EXPECTED_HEAD=<冻结候选SHA> GITEE_EXPECTED_MAIN=<已对齐Gitee主线SHA>
# 完成审查、归档后发布添加：
# APPLY=1 GITEE_INTEGRATION_CONFIRM=PUBLISH_EXACT_GITEE_CANDIDATE
```

默认均不写远端。历史补齐只推送固定历史主线 SHA，且在 Git common directory 的
`codex-recovery/gitee-temporary-integration/` 创建并验证 bundle；不依赖不可读的实时 GitHub。
因此它证明的是“保存并复制已观测的历史主线”，不是重新证明 GitHub 当前状态。
普通 push 的服务端快进约束始终保留；禁止 force/lease、改保护规则、删分支、自动部署。
检查后到 push 间远端仍可能变化：普通快进不是旧 SHA 的原子锁定，远端先推进到候选的中间祖先仍可被接受。
历史补齐必须排除其他写入者并建立单一写入窗口。非快进由服务端拒绝，不能放宽保护。
push 异常或回读失败输出 `status=uncertain`、`retry_allowed=false`（退出 3）；先只读检查远端，不能盲目重试。

## 退出与恢复

GitHub 恢复后先只读获取两端精确 main，判断祖先关系并审阅 Gitee 新增提交；经授权再通过受管流程
同步 GitHub。分叉必须单独裁决，禁止自动反向镜像、强推或覆盖另一端。恢复后停用本临时车道。
只读验收已证实旧 Gitee→GitHub 镜像 timer 仍启用，且部署脚本与本地禁用版本不同；本轮未启停。
停止方案和完整门禁缺口见[唯一批次记录](iterations/gitee_temporary_integration_20260923.md)。
目前完整 CI 等效性、分支保护和原子 head/base 合并未证明，通道不可用于正式集成。
本工具无通用 PR 合并或远端回滚权限：新产品回滚走单独审查的回退 PR；历史补齐不重写历史。

## 本轮验收边界

工具检查及模拟失败关闭测试可以在本地完成；主线补齐、候选发布、Gitee CI、PR 合并、GitHub 恢复、
部署和用户验收逐项记录。未执行项不得由本地测试替代。


## 当前可行性裁决

按同批限定核查，精确合并裁决为**当前不可实现**：原生合并没有双 SHA 原子条件证明，
等效锁定没有覆盖全部写入者（含管理员绕过）的配置及行为证据。停止扩建完整 Gitee CI。
Gitee 暂定位为历史镜像／候选保存通道；保存候选仍须先完成自动化隔离和发布保护，当前不能推送。
隔离执行单、未查明平台路径、恢复条件和 CI 最小设计统一见[批次记录](iterations/gitee_temporary_integration_20260923.md)。
自动化停用与远端写入均需在执行单审阅后分别授权；历史补齐的精确范围授权要求保持不变。


## 自动 CI 验证与正式合并分离

最新阶段允许准备自动 CI，不要求先解决精确合并。首次最小验收选择现有 worker，复用
`ENV=test make verify.gitee.integration.unit`；正式合并仍阻塞，部署不在范围。
平台副作用未查清前不推送。当前 `pr.push.gitee` 仍要求历史 main 补齐；候选按 SHA 构建没有该技术依赖，
但必须先在同一受管入口实现并验证显式 CI-only 用途，不能绕过检查。尚未实现或授权实际推送。
具体触发、负向测试、权限缺口及恢复方案见同一批次记录的“自动 CI 可用性验证准备”。


## 本地 CI-only 实现（线上仍禁用）

- 显式 `GITEE_CI_MODE=ci-only` 使用原 receiver/worker 的独立 `ci_acceptance_jobs` 表；默认仍为 legacy。
  仅接受 `leegege/sce-product-odoo`、`refs/heads/fix/gitee-temporary-integration-v1` 的 Push 与完整 SHA。
- 固定服务端检查器加载 `scripts.ops.test_gitee_temporary_integration`，即现有 Make 定向目标的同一测试集。
  直接使用 unittest 的 testsRun 减 skipped 计算有效计数，不解析 OK 文本、不硬编码 36，也不运行候选提供的 Make 配方。
- 服务端完成 clone/checkout 身份核对后，通过已有 `/usr/bin/bwrap` 隔离网络、PID 和文件系统。
  只挂载系统 `/usr`、临时工作目录和只读服务端检查器；不挂载凭据、部署目录或 mirror。
  线上须先证明 bubblewrap/用户命名空间可用及系统挂载范围不含敏感配置；不可用记 environment_error，禁止降级无隔离运行。
- 120 秒超时/精确 SHA 取消会 kill/wait，sandbox PID namespace 回收脱离进程组的子进程。
  工作目录清理后才保存 receipt，字段含完整 SHA、checkout_sha、退出码、有效测试数、日志和终态。
  终态为 success/failed/timed_out/cancelled/environment_error；未启动或无报告字段可为 null。
  以任务表按精确 SHA 查询的终态为权威；日志/receipt 不能授权合并。重复 SHA 不重跑，旧 SHA 结果不会写入新 SHA。
- 精确取消能力为受管 worker CLI `--cancel-sha <完整SHA>`（必须 ci-only 模式）；仅实现能力，
  线上取消/启用仍须已有隔离执行单审阅及受管入口，不直接在服务器运行任意命令。
- 预演：`make pr.push.gitee GITEE_PUBLICATION_PURPOSE=ci-only EXPECTED_HEAD=<sha> GITEE_EXPECTED_MAIN=<sha>`。
  输出全部 `commits_relative_to_main`、changed_paths、additional_visible_code_possible；这是相对 main 的范围，
  不冒充对所有远端 refs 的首次可见性证明。可能公开整个落后历史，不只是新增 CI 文件。
  dirty 预演仅分析已提交 HEAD，excludes_uncommitted_changes=true。正式发布必须重新按 clean 新 HEAD 预演。
- 现阶段 CI-only 的 APPLY 一律拒绝平台自动化证据缺失；保留普通发布 Quick、身份、漂移、普通 FF 和不确定回读机制。
  后续打开实际 CI-only transport 必须是基于真实配置证据的受审改动，不能靠自行填写“已隔离”绕过。
- 安装打包只补齐两个服务端模块，不设置模式、不安装新 runtime、不改变线上默认行为；本轮未安装。


## 保留配置的增量更新入口

使用 `make gitee.ci.server.update EXPECTED_HEAD=<本地完整HEAD>` 生成只读预演，不调用旧 install。
预演列出旧/新文件 hash、source SHA、工具 hash、配置及凭据状态摘要、服务和任务状态、固定包版本。
实际执行还要求：公开范围与平台隔离已批准、clean source、最新精确 plan hash，及
`APPLY=1 GITEE_UPDATE_PLAN_SHA256=<摘要> GITEE_UPDATE_CONFIRM=APPLY_REVIEWED_CI_INCREMENTAL_UPDATE`。
参数不是审批替代；当前禁止 APPLY。

只允许三个 CI 代码文件、两个既有 env 和 worker unit 的已确认差异。secret、SSH 身份、端口、数据库、
其他配置保留；旧 runner 不处理。停 receiver admission 后核对队列，备份目标文件/权限并验证，
使用 SQLite backup API 验证 CI 元数据备份，不操作业务数据库。安装固定 bubblewrap 包后，在 gitee-ci
用户及受限 systemd 探针下验证 namespace/网络/凭据隔离；不支持就停止并恢复目标文件，不能无沙箱执行。
探针设 RuntimeMaxSec=30/TimeoutStopSec=5/KillMode=control-group，不新增常驻执行器。

恢复保留旧文件字节/权限/所有者，移除本次新增文件并回读；外来修改或损坏备份则停止恢复，不能覆盖。
恢复后保持 CI 服务停止，避免重新启动 legacy 副作用；包不会自动 purge/autoremove，须核查消费者后决定。
输送或回读不确定时明确 uncertain、禁止自动重试，先检查服务器备份/包状态/服务。
实际平台配置隔离与正式候选推送仍需按批次执行单完成；安装成功也不是线上 CI 验收通过。
