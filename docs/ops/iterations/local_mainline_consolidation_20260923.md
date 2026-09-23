# 本地存量改动主线收敛（2026-09-23）

## 范围与权威

所有者要求先把本地全部整理进入主线。本批以已合并的 Gitee main
`65363dca5bdfa9cd0577a90f54f09af03bae7467` 为唯一集成基线。
本地 main 已快进到该提交；候选分支为 `fix/local-mainline-consolidation-v1`。
层级为既有前端表达/运行态责任与 P4 验证；无业务数据迁移、部署或新环境。

32 条本地分支、2 个干净工作树、无 stash 已盘点。不能把非祖先分支等同未交付：
历史 squash 合并必须以完整树、既有交付记录和后续权威实现逐项判定。
旧分支、外部证据及恢复 bundle 保留，不删除、不强推、不恢复被后续实现替代的旧语义。
逐分支原始索引位于现有外部证据目录的 `local-mainline-inventory.json`。

## 本次承接

- 页头入口专题：`22390c84f7d2447e055b6e1c67a194778ce9a10a`，共同基线 de9a230d，13 路径。
- 前端稳定性专题：`baad61f12e6a7fff0e5b9953609be5f5d52fbdff`，共同基线 de9a230d，23 路径。

承接各专题最终责任差异，不重放其反复修订的历史。产品源码无重叠冲突；
共享 Makefile 的不同挂点同时保留。上下文日志先验证共同前缀完全一致，再保留两边追加记录。
复杂度报告、组件接管 inventory 和拆分证据按整合后源码重新生成。
旧专题报告保留为历史证据，不将其中旧 HEAD 或旧“未合并”描述当成当前结论。

## 验证与交付边界

本地仅运行轻量迭代检查和受影响的页头、协作权威、专业组件注册定向测试。
完整风险选择 CI 在远端运行；提交后只接受当前 PR/head/base 的结果。
两个专题的既有源码审查和纯函数证据可按输入一致性承接；本批不宣称新增浏览器验收。
协作区运行态可见性的真实浏览器验收仍为明确未覆盖项。

最终状态、独立审查、公开范围与平台合并回读记录到同一外部证据目录，
不为填写最终 SHA 再制造文档提交和重复 CI。CI 通过后按所有者持续授权合入受保护 main；
合并成功后同步本地 main，产品部署仍独立。

## 首次真实前端 CI 的资源修复

PR !6 的 bc98f5e6 在 2026-09-23 16:47:49 被服务器全局 OOM 中断，
esbuild 的匿名驻留内存约 691 MiB；主机物理内存约 1.7 GiB。Worker 自动重启，
该次检查不是通过。固定可信 sandbox 环境增加 Go 256MiB GC 软目标、GOGC50、
GOMAXPROCS2、Node old-space512MiB、UV线程2和make串行。此为资源调优而非
硬内存隔离承诺；不删除测试、放宽门禁或把完整CI移到本地。最终有效性以新SHA
在远端完成同一门禁为准；失败仍阻断合并。

## 专用 CI 主机收敛与构建预算

所有者确认1.95.2.123仅用于CI，非CI数据无需保留，授权删除旧业务负载。
移除两套历史Odoo栈的8个容器和6个卷，清除闲置Docker镜像/构建缓存；
停用Docker/containerd及旧GitHub runner自启动，删除旧部署目录和runner工作缓存。
保留Gitee receiver/worker、凭据、固定运行时、离线依赖、Nginx TLS入口及系统安全服务。

b026的远端单元测试已完成，但Vite构建命中人为512MiB Node堆上限；
清理后将可信Node old-space预算调至1024MiB，其他Go/并发限制保持。
此前运行和维护中断不能作成功证据，新提交必须重新完成全部远端门禁。

## 构建工作集与主机总内存保护

3f00749d远端回执：public_guard112测试、professional_quality_gate30测试、
frontend单测145测试通过；Vite build退出134，实际达到1024MiB Node堆上限。
原GitHub前端作业使用ubuntu-latest，并非这台2GB服务器。
本轮Node堆预算2048MiB，既有worker增加MemoryHigh896M、MemoryMax1152M、
MemorySwapMax2G、OOMPolicy=kill和LimitCORE=0；使用现有2GB swap，不增加磁盘
或改变全机swappiness。主机物理内存受cgroup硬限额保护，超额仍失败，不减测试。
这些数值仍需远端真实验收；不把清理完成或单项通过当成整轮通过。


## Merged PR historical checks repair

P4 / CI reporting: PR6 merged into f3c97b9194159a8de717d8ddb6dbd7262d659ee5 after all four current-source checks succeeded. The periodic reporter subsequently rejected the normal merged lifecycle as a stale open-PR snapshot. Split reporting-only historical identity from execution identity. Two platform reads must agree on merged state, merge timestamp, original PR/repository/ref/head/base and PR ID; only an exact valid successful stored receipt can restore historical success. Open-PR drift, API failure, closed/unmerged PRs and failed/incomplete receipts remain fail-closed. No new task execution or merge eligibility is granted by the historical snapshot.

Validation: 46 focused identity/queue/worker tests passed, including historical restoration and identity/receipt rejection. Full CI remains remote. Update and readback evidence will remain in existing external artifacts. PR6 source receipt is retained; do not rerun its product build to repair presentation.

## 剩余历史控制器资产的最小承接

P4 控制器提取自 113ad564 的两个实现/测试文件，父版本与当前主线完全一致；
不承接旧 demo、浏览器验收和过时上下文日志。增加 agent_progress 的健壮性修复。

已完成：恢复提示携带历史上下文；无 final 的失败仍保存可读进度；日志缺失、
非对象事件或读取失败不阻断失败终态持久化。无 session 重启仅接受任务目录、
完整 Git 身份和干净工作区匹配，且事件流只含启动/明确失败事件的情况。
任何命令开始、命令完成、未知或畸形事件均拒绝自动重启，需先核对已发生的写入。
已有 session 的恢复机制保留，完整防重放目标仍为 active，不宣称已经完成。

36 项隔离控制器测试通过，独立复核通过；未启动真实控制器、发送通知或修改运行服务。
完整 CI 仍交远端。历史审计和工作流改动已由后续主线承接；旧 detail-operation
对原生集合一刀切禁删的方案已被后续按动作区分的权威实现替代，保留原分支供追溯，
不恢复旧行为。原始分支分类与指纹证据保存在 local-historical-review.md。

本次承接基线为 d7433e95（含 PR6、PR7）。控制器及测试内容与已复核的315a2561一致，CI状态修复保留。最终验证、发布和合并结果见既有外部证据索引。

当前基线定向验证：python3 -m unittest scripts.verify.test_codex_agent_controller 实际运行30项并通过；历史36项保持原证据范围，不作为本次新计数。一次尝试不存在的test_agent_progress模块仅为命令选择错误，已核对agent_progress测试位于上述控制器套件；未据其生成通过证据。ci.local.iteration及generated_reports刷新通过。
