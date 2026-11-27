# VERIFY-SYSTEM-CLOSEOUT-01 / R1 审计结论

审计基线：`bfc954c0b6fe2bbaa5a94c017ef8c69ec983d9a5`（PR #1018 合并提交）。独立分支：`audit/verify-system-closeout-01-20261127`。本包只增加审计材料、可复现的隔离实验和任务记录；没有修改产品、验证器、CI 策略、数据库或性能预算，也没有派发、部署或合并。

**R1 独立复审：APPROVE WITH SCOPE CORRECTIONS；验证体系和当前主线全量资格尚未收口。** 本次复审认可审计事实，不授予 R2 修复、合并或部署权限。失败日志中的模拟 run ID 101–106 是隔离传输桩，不是 GitHub 真实故障运行。

## 当前主线事实

`mainline_workflow_matrix.json` 保存精确 HEAD 的实际 GitHub Run 和 Job 状态。当前只有四条 `push` 运行，均成功：

| 工作流 | 运行 | 范围判断 |
| --- | --- | --- |
| public_guard | [45923448372](https://github.com/lidefend/sce-backend-odoo/actions/runs/45923448372) | VERIFIED：本次 push 门禁成功 |
| professional_quality_gate | [45923448422](https://github.com/lidefend/sce-backend-odoo/actions/runs/45923448422) | VERIFIED：本次 push 成功；backend_impact_suite、demo、acceptance 均 skipped，不能称完整后端通过 |
| frontend_release_gate | [45923448260](https://github.com/lidefend/sce-backend-odoo/actions/runs/45923448260) | VERIFIED：选定前端与 managed_orm 成功；不等于完整浏览器交付验收 |
| merge_policy_gate | [45923448264](https://github.com/lidefend/sce-backend-odoo/actions/runs/45923448264) | VERIFIED：push 聚合成功 |

**P0 / NOT_VERIFIED：当前 SHA 没有完整主线资格。** 直接原因是尚无该 SHA 的 schedule/operator 全量责任链：缺少独立辅助套件和 release_candidate_gate，专业后端完整分片亦未执行。本轮没有发现这四条 push 运行失败，因此不能将“资格未证明”描述成“当前主线 CI 再次失败”。

历史 `a92114f0efb6733253d827e3a9985af21ab96be6` 的六条 operator 工作流实际全部成功，本轮重新回读确认；它只证明历史身份。主线里的 MAIN-CI 记录仍是 verification_pending，且停在较早基线；上轮本地结项材料保存在 stash，并未进入该主线。记录滞后与当前资格缺失须分别处理，不能给旧回执改 SHA。

## 已复现的问题

### F01 · P1 · FAILED：聚合索引复用忽略环境身份

定位：`scripts/ops/incremental_execution.py:reuse_identity/verified_receipt`；`scripts/verify/frontend_dev_incremental.py:execute_targets`。

真实 Make 子进程完成四个隔离目标后，保持源码和日志不变，将传入的 `environmentIdentitySha256` 从 64 个 `a` 改为 64 个 `b`。执行器仍直接复用四项，执行数为零并返回 PASS。原始证据：[环境变化](evidence/resume-environment_changed.log)、[实验脚本](resume_replay.py)，结构结果见 `failure_replay_matrix.json`。

原因：精确聚合缓存的 `reuse_identity()` 只保留 runtime tree 和 verifier authority，环境字段被丢弃。另一条逐目标恢复路径会比较环境字段，但前者可先命中。换 run ID 也能命中该聚合索引；跨 run 的普通本地复用不能直接等同于合法的同 run 通道交接。

边界：`execute_worktree()` 对缺少有效见证的已登记 runtime 检查另有 `non_reusable_targets` 保护，本实验**不证明所有 ORM 都会跨环境误复用**。复现证明的是聚合入口没有兑现显式环境身份约束；当前默认 identity 生产者本身也没有填入这两个环境字段。

最小 R2：统一两条复用路径的身份约束；明确本地跨 run 复用与同 run handoff 的不同权限；环境身份无法证明的相关目标必须重跑。保留未变输入可复用的正例，禁止简单关闭所有缓存。

### F02 · P0 · FAILED：本地主线核验器只核对工作流外壳

定位：`scripts/ci/main_full_release_dispatch.py:load_manifest/verify_full`。

通过生产 CLI、仅替换外部 git/GitHub 传输，分别复现：

- 没有 release-condition 文件，六条元数据 success，仍签发 PASS：[日志](evidence/replay-missing_condition.log)。没有下载或验证正式发布条件，也没有核对该条件引用的 run 集合与 manifest 一致。
- manifest 的 expected_tree 换成任意合法 40 位 SHA，仍 PASS：[日志](evidence/replay-wrong_tree.log)。核验阶段只检查格式，没有和目标 commit 的树重新比对。
- 起始 main 正确，首次轮询后模拟 main 前进，仍 PASS：[日志](evidence/replay-main_advanced_during_wait.log)。传输轨迹显示只在等待前查询一次 main。

远端 `release_candidate_gate.yml` 本身有等待后 main 回读，`release_condition.py` 会拒绝 stale main；这些正例仍成立。本问题是**本地正式核验入口的独立证明不足**，不能据此宣称远端已真实发布错误版本。

最小 R2：核验精确 release artifact、树、依赖 run/attempt 和必需 Job/分片证据；完成等待后重新读取当前 main。不要把 `gh run conclusion=success` 独自当正式资格回执。

### F03 · P2 · FAILED：终态失败被未完成任务延迟报告

定位：`scripts/ci/main_full_release_dispatch.py:verify_full`。

一条必需工作流 completed/failure，另一条 in_progress，`--wait-seconds 0` 返回“still pending”，没有输出已知失败：[日志](evidence/replay-failed_and_pending.log)。使用正等待预算时同一控制流继续查询全部六条，直到全终态或超时。

远端 shell 聚合会在看到终态失败时直接退出，并非同一个缺陷；但只输出首个失败，未输出完整矩阵。五个查询串行，不代表五个验证工作流串行执行。

最小 R2：每轮先归并完整失败/取消/等待矩阵，存在必需终态失败立即失败；减少重复查询并记录耗时。保留等待预算，不用缩短超时掩盖问题。

### F04 · P1 · FAILED：后一个 Runner 成功可遮住被 Shell 吞掉的子失败

定位：`scripts/verify/frontend_dev_incremental.py:test_execution_metrics/_run_make_target`。

临时 Make recipe 真实执行失败的 `node --test`，随后同一 Shell 执行成功的 Node 测试。Shell 退出 0，执行器只解释最后一份完整 TAP，将目标记为 passed、testCount=1：[真实双 Runner 日志](evidence/replay-masked_child_failure.log)。对照实验：单 Runner 失败、非零退出加 PASS 文本、零测试、全跳过、残缺 TAP、混合残缺摘要均被拒绝。

本例证明结果协议的边界缺口，**尚未定位到当前正式 recipe 里确有同样的吞错写法**。不能把日志中任意 FAILED 文本都当失败：负例测试会正常打印预期失败，嵌套汇总归属必须保留。

最小 R2：在正式多 Runner 入口强制传播每个子退出码，并形成有执行身份的最终聚合；补真实 Shell 负例与合法嵌套负例正向回归。不要简单全局扫描 ERROR 字符串。

### F05 · P2 · FAILED：现有 Node 生产者仍缺少本地选测映射

生产者 `scripts/verify/frontend_action_view_route_lease_race.test.mjs` 存在，Make 入口 `verify.frontend.action_view_route_lease_race.unit` 真实运行 TAP 1 项通过：[日志](evidence/native-node.log)。同一生产者路径进入生产增量 CLI，直接 BLOCKED/unmapped：[日志](evidence/unmapped-node.log)。责任分类器将其归为 frontend_quality_tooling，但本地未选到目标。

这是开发期固定阻断，已知入口不会“假通过”；不能把它扩写成远端已漏跑测试。450 条可静态识别的测试生产者/目标边中，84 条单路径选测为空，257 条没有直接选中同名责任目标。聚合目标可能合法覆盖后者，须先逐项追踪，不能把数字全算缺陷。

最小 R2：补该已证实映射及真实执行回归；按聚合闭包分类剩余边，证明有实际责任再决定修复。不要批量给所有路径加完整前后端全量套件。

## 已证明与未证明

VERIFIED：本基线执行器单测 281 项、changed Odoo tooling 15 项、车道审计单测 74 项通过；Workflow 契约、main-full 6 项、integration-cycle 28 项、backend iteration 13 项及其前置回归通过。分组原始日志、入口和哈希见 `evidence_index.json`；没有把嵌套诊断里的 `Ran N` 累加成测试总数。

VERIFIED：真实 SIGINT 使运行以 130/interrupted 结束；只改一个依赖并提交到临时 Git 后，恢复执行 1 项、复用 3 项；清除临时回执后全跑 4 项结果相同。日志篡改阻止旧聚合成功复用。实验使用隔离生产者，不冒充完整业务 ORM/前端验收。

VERIFIED：真实 selector CLI 选择最新失败 Run，而非旧成功 Run；现有同 Run Job 回归拒绝借用旧 Run 缺失 Job。release-condition CLI 拒绝缺辅助套件、失败、跨 HEAD、过期 main 和未完成结果。这里是受控输入验证，不是远端破坏性故障注入。

NOT_VERIFIED：所有新增/删除文件、动态 Make/Workflow 调用都通过真实业务 Runner 与发布条件端到端贯通；全部生产者的摘要协议完整覆盖；真实跨 ORM/浏览器/契约的混合中断恢复。对应缺口在矩阵中保留，没有把规划函数或结构审计 PASS 当作闭环证明。

NOT_VERIFIED：旧本地回执用于当前输入的逐份授权。已盘点现存本地增量回执并检查日志哈希，但没有验证全部环境和依赖闭包，因此不签发当前可复用证明；更不能作为 main 资格。

结构审计当前值为 670 个零引用目标、103 个未引用脚本、22 个缺失资产目标、22 个 local-only 脚本、92 个 remote-only 脚本。全部有既有登记，没有新增未登记增长；这不是功能覆盖结论。完整条目保留在覆盖矩阵，P2 债务需要独立处置。

## 下一轮最小整改顺序

| 批次 | 分类与范围 | 必须保留的验证入口 |
| --- | --- | --- |
| R2-A | 主线资格与回执安全：先 F02（P0），再 F01，后 F03；独立交付审查，尚未授权 | 本包隔离复现，`verify.frontend.dev.incremental.unit`、`verify.ci.main_full_release.unit`、`verify.integration.cycle.unit`、release-condition/Workflow 回归 |
| R2-B | 测试执行与覆盖完整性：F04、F05及其余 84 条边的聚合覆盖确认；独立交付审查，尚未授权 | 真实 Make/Node 负例、原生竞态 Make 目标经过增量入口、`verify.ci.workflow.contract`、覆盖登记守卫 |
| R2-C | 历史债务：先核实 22 个缺资产目标，再分批治理无引用目标、过期登记和持续覆盖检查；保留有恢复价值的工具，尚未授权 | 逐项分类/处置与 `verify.verification.lane_coverage`；不能删除失败史或放宽基线 |
| R3 | 精确候选 CI、受保护合并后主线全量 | 经另行审查授权后执行 `make release.main_full EXPECTED_MAIN=<当时精确40位main>`；同 SHA 全责任和正式 artifact 验证 |

产品代码修复：NOT_APPLICABLE；当前复现均属于 P4 工具或证据边界。部署：NOT_APPLICABLE；未执行。完整业务浏览器验收：NOT_VERIFIED。本包不授权 R2，更不授权合并。


## R1 独立复审边界修正（2026-11-27）

复审对象为 PR #1020 的 `83cc97f93bdf17757e744109fbac1e2e3b88db7c`，审计源码基线不变。R1 可作为 R2 事实依据；PR 继续 Draft，不合并、不部署。以下是后续整改验收标准，不是执行授权。

- F01 保持 P1：权威环境指纹必须有生产者，环境等价无法证明时只重跑相关目标；保留静态检查的安全复用。不能推导所有 ORM 都可跨环境误复用；跨 run 内容复用与同 run handoff 分别定义。
- F02 提升 P0：精确 main SHA → 真实 commit tree → 六工作流的 Run/Attempt/Job → 完整后端分片及辅助证据 → 正式 artifact → 与 manifest 交叉核对 → 再读 main → PASS/DENY。缺一项不得签发 PASS。
- F03 保持 P2：必需终态失败优先 FAIL；没有失败且仍在运行才 PENDING；必需任务缺失 FAIL/DENY，身份不符 DENY。保留等待预算并输出完整矩阵。
- F04 保持 P1：已证明执行器可假成功，尚未证明正式业务验证已因此漏检。每个子 Runner 的退出状态进入汇总，保留合法嵌套负例，不能全文搜索 ERROR/FAILED 代替协议。
- F05 保持 P2：已证明本地反馈阻断，不是静默通过。允许聚合目标承接多个生产者，追踪 producer → owner target → actual execution → result evidence，不强制一脚本一目标。

验证状态分别记录 **SELECTED、DISPATCHED、EXECUTED、PASSED、REUSABLE**，不得互相代替。121 份回执仅限所选工作区本地增量记录；隔离 SIGINT 实验不证明混合 ORM/浏览器恢复；670/103 等结构债务不要求在 R2 大扫除。

每批保留修复前失败证据，验证工具单测、真实入口、故障拒绝、恢复与安全复用、覆盖登记、本地精确候选回执和新 HEAD PR CI。合并后主线资格由 R3 独立完成；不得用尚有缺陷的核验器旧 PASS 证明整改成功。影响明确时不扩大无关 ORM/浏览器；影响未知时只保守扩大无法证明的责任范围。

**CI Qualification、Product Acceptance、Deployment Qualification 是三项独立结论。** R2-A、R2-B、R2-C 分开交付、分开审查；R3 使用届时最新 main。下一步等待所有者明确授权 R2-A，当前不实施。
