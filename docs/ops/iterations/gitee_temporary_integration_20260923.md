# 工作区接管与临时 Gitee 集成结果索引

## Desktop 接管执行（2026-09-23，基线 db160f72）

### 实际线上执行结果

- `2f7d58fb` 首次最终 Quick 在 `verify.tenant.product_payload_boundary` 失败：公开扫描工具
  重复硬编码客户标识，属于 P4 工具边界缺陷；不是客户正文/秘密命中。修复为导入既有边界守卫的
  `CUSTOMER_IDENTITY_TOKENS`，不添加豁免，扫描来源摘要新增该权威文件。定向公开扫描 5 项及
  边界守卫 10+11 项通过。因检测规则来源变化，最终公开范围重新全量扫描，不复用旧规则的客户命中结论。
  新候选只重做受影响检查与一次最终 Quick；不重新安装未变化的线上执行器。

- `1feb780b95e910c905fb4d95ed7447f40db7ef0b` 增量更新成功，精确计划摘要
  `d42b4ee5cc5d55cf434c93b1a65e947164387a01675af7312590b4f1a42b8682`，备份
  `/var/lib/gitee-ci/update-backups/incremental-s0g_x39h`。原凭据保持，receiver/worker active、ci-only。
- 用户完成 Gitee 新签名密钥保存后，`make gitee.ci.secret.rotate` 完成服务端对应轮换；receiver active，
  备份 `/var/lib/gitee-ci/update-backups/secret-rotation-itahha8l`。密钥不进入源码/日志/公开范围。
- 新增 P4 发布证据校验替换 CI-only 写死拒绝，保留 clean/Quick/生成证据及远端回读。候选、平台观察、
  证据文件摘要和线上实际模块/配置共同绑定；独立正式合并阻塞不变。
- L2：`make verify.gitee.integration.unit verify.gitee.publication_gate.unit`，42+10 项通过，
  身份为 1feb780b + 本轮 scripts/ops、make/codex.mk、本文及 allowlist dirty。不重复原验收/worker 测试。
- 独立审查 1feb780b 未发现首次真实 Push 确定阻塞；实际线上运行可信 check harness，直接加载同一
  unittest 模块，不声称执行 Make wrapper。完整 clone 与测试共用 120 秒，首次实测决定是否足够。
  后续 frozen 回执及真实 CI 结果写 artifacts，避免为回写结果反复改变候选。

- 镜像 timer 已 disabled/inactive；service 保留历史 failed，MainPID=0。首次工具将 failed 误判为未停止，
  属 validation_tool_defect；修正为与 updater 一致接受 inactive/failed+PID=0，不再重复停用。
- 以 5db04d9a 精确计划执行 update：已安装 bubblewrap=0.9.0-1ubuntu0.3，备份
  `/var/lib/gitee-ci/update-backups/incremental-od5jpxr3` 完成。probe 因 AppArmor userns capabilities 拒绝失败；
  原文件恢复，receiver/worker 保持停止，平台 WebHook 仍暂停。没有推送。
- 归因 environment_defect：kernel audit 明确拒绝 bwrap 的 setpcap/net_admin；不是缺少包或项目测试失败。
- 采用 Ubuntu 官方安全说明链接的上游专用 profile（ABI4），未改全局安全开关。
  来源 https://gitlab.com/apparmor/apparmor/-/raw/v4.0.3/profiles/apparmor/profiles/extras/bwrap-userns-restrict
  SHA256 `a964037f6cf0df1099f14226b037eaedde6237c86e715188e93eb460b30be859`，本地及线上一致。
  profile 允许 bwrap 建立 namespace，但对子进程叠加 capability deny；不是通用 unconfined 豁免。
- `make gitee.ci.sandbox.probe EXPECTED_HEAD=5db04d9a3f666cff1ef6011352ce7bbcb1d87caf` 线上 passed。
  探针与 worker 的用户/主要 systemd hardening 一致，验证 `/etc/gitee-ci` 不可见及外网连接失败。
  可据该环境恢复事实重新预演并执行 update；不复用旧计划摘要。
- 私有轮换文件仅保存在 Git metadata 的 codex/private（0600），不属于源码或证据归档。浏览器凭据更改由
  用户按工具 handoff 规则提交；绝不把截图中的原密钥归档或复述。

用户要求本任务直接执行，授权沿用既有受管 CI 更新、镜像隔离及 CI-only 验收方案；不含 main 补齐、合并、
产品部署。用户确认公开范围及同组客户标识授权继续有效。当前为 P4 日常开发与高风险运维受管执行，非冻结交付。

- 用户截图确认平台 mirror 列表为空、Gitee Go 显示开通页；不再以平台读取 token 缺失作为这两项阻塞。
- 登录后的 WebHook 2106026 页面已实时确认原 Push/PR/check-run active；执行暂停 active 并取消 check-run，
  页面返回“更新成功”。保留 Push/PR，后续验收前恢复 active。receiver 仅接受 push_hooks/merge_request_hooks，
  check-run 原本会被拒绝，不推定曾发生循环。密钥截图不归档，既有签名密钥须轮换。
- 当前安装预演与 db160f72 checkpoint 完全一致：active_jobs=0、bwrap 不存在，plan_sha256=b225d22b7c4af3d3a61220f5ed102cc2f8d9b007804726ce114044be091aca80。
- 边界：P4/scripts/ops、make/codex.mk、既有 CI host；不更改 P0—P3、业务 DB、旧 runner 或两个未合并专题。
- 新增受管 mirror isolate 入口，固定主机与两个 unit；make -n 与 diff 检查通过。后续结果追加在本节对应原始证据中。

[English](gitee_temporary_integration_20260923.en.md)

## 身份与边界

当前控制分支 `fix/gitee-temporary-integration-v1`，HEAD／基线
`de9a230d3faab18dd60a219f445f932a8af9d7f5`，本批为未提交开发态，不是冻结候选。
用户授权全面接管现场、先收口再迭代，并要求在 GitHub 受限时调整主线集成流程。
按临时 Gitee 车道实施；永久更换主仓、改远端 URL、强推、自动合并和部署不在本批。

- Formal Product Layer：P4。
- Layer Target：既有 Git 发布／主线历史补齐流程。
- Module：`scripts/ops`、`make/codex.mk`、治理文档和 `.agent`。
- Standard vs User-Specific：运维治理，不是行业或客户产品语义。
- Why Here：现有发布入口强依赖不可用的 GitHub，须明确有界替代入口。
- Why Not Elsewhere：不在 P0—P3、数据库或前端补偿远端治理问题。
- Blast Radius：三个新 Make 入口；默认只读。旧 `pr.push`、主线同步、镜像命令语义保持不变。
- 风险高于普通文档：实际 APPLY 可写远端，因此要求精确身份、clean、祖先证明、备份及回读。

## 接管现场

| 项目 | 核实结果 | 处置 |
| --- | --- | --- |
| 原主工作区 | main@de9a230d，干净 | 已创建本批控制分支；main 引用未变 |
| 稳定性工作树 | `sce-backend-odoo-uc4-g10-engineering-process-native-v1`，`feature/frontend-stability-gate-baseline-v1@baad61f12e6a7fff0e5b9953609be5f5d52fbdff`，干净，123 个主线外提交 | 原样保留，不继续守卫扩张 |
| 页头专题 | `feature/frontend-page-header-entry-authority-v1@22390c84f7d2447e055b6e1c67a194778ce9a10a`，29 个主线外提交 | 保留引用；历史记录称 PR #522，当前远端无法核实 |
| 两专题交集 | `make/frontend.mk`、复杂度报告、组件接管清单、delivery context log | 后续串行集成，不机械同时应用 |
| 分支／stash／Git 锁 | 31 个本地分支；无 stash 引用；未发现 `.lock` | 不推断其均已合入，不批量删除 |
| 受管运行环境 | persistent/sample/clean 三个 profile 健康检查通过 | 保留数据库、卷及服务 |
| 旧候选前端 | 进程 709450，已删除的 material 专题目录，SHA `25cb3cd106ead9dd09b3f2b68ed152fbd413da0f` | 受管 down 校验后停止，PID 文件已移除 |

## 唯一结果索引

| 层／入口 | 身份／结果 | 原始证据与限制 |
| --- | --- | --- |
| L0 preflight | 两工作区初始干净；控制分支现为 dirty（本批文件） | 本次命令回执；未生成最终交付指纹 |
| `make pr.status`（受管 GH_CONFIG_DIR） | failed/environment_defect：HTTP 403 account suspended | 包装返回 0，但内容明确失败；不计通过 |
| `make local.env.status` | passed，persistent/sample/clean 身份和健康通过 | 本次命令回执，非业务验收 |
| 旧候选 down 初次 | failed/调用输入：缺 CANDIDATE_GIT_HEAD | 零停止；补齐当前 SHA 与受管确认后再执行 |
| `make local.dev.candidate.frontend.down` | passed，绑定 baad61f1 控制身份，严格校验孤儿进程 | 旧进程已停；无数据库变更 |
| `python3 scripts/ops/local_quick_evidence.py verify --expected-head baad61f12e6a7fff0e5b9953609be5f5d52fbdff` | passed，原 Quick 回执 VERIFIED | Git worktree metadata 下 `codex/evidence/ci.local.quick/<sha>.json`；没有重跑 Quick |
| 稳定性 L1：`make verify.frontend.style_system.guard verify.frontend.scene_component_bridge.guard verify.frontend.release_navigation_policy.guard` | passed；桥接 129 checks／262 自检，导航 85 叶／4 角色 | 原工作树 `artifacts/workspace-takeover-20260923/l1.log`；不代表独立审查或浏览器通过 |
| 本批 L1：`make ci.local.iteration` | passed，16 非零 policy tests；dirty，L1_only | `artifacts/gitee-temporary-integration/l1.log` |
| 本批 L2 初次定向 | failed，27 tests 中 1 failure：push 后 ref 缺失错误未明确 readback 阶段 | owning P4；已补 readback 错误上下文，明确远端可能已变 |
| 本批 L2 第二次 | failed，3 errors：测试 fake 的同名布尔属性遮蔽新方法 | validation_tool_defect；已将夹具属性改名 |
| `make verify.gitee.integration.unit` 最终 | passed，27 tests | `artifacts/gitee-temporary-integration/l2.log`；含零写反例、精确 refspec、备份检查和读回失败 |
| Gitee 只读 inspect | passed，main=b9e3e56a，133 commits ahead，writes=0 | `artifacts/gitee-temporary-integration/inspect.json`；delivery_gate=false |
| `make main.gitee.catchup` 默认预演 | 只读方案，目标固定 de9a230d | `artifacts/gitee-temporary-integration/catchup-plan.json`；非执行批准 |
| `make gitee.ci.server.status` | 服务 active／health ok，存在 systemd 配置未重载提示 | `artifacts/gitee-temporary-integration/gitee-ci-status.log`；未启停／重载服务，未证明候选 checks |

L1 后的 readback 修订只影响新 Python 脚本与夹具；以定向 27 tests 和语法/diff 检查覆盖。
政策、Make 配方及受管环境身份未变，原 L1 政策结果承接，避免机械重跑。
L3：无模型、模块或运行装载修改，跳过升级。L4：无产品页面改动，不跑浏览器矩阵。
L5：本批未提交／未冻结，独立审查、最终 Quick、外部归档和发布均 not_run；不拿旧专题回执覆盖本批。

## 收口与下一步

历史主线快进方案为 `b9e3e56a80c02c1eb277d2ac573e10286c4cd8e8` →
`de9a230d3faab18dd60a219f445f932a8af9d7f5`，133 commits，祖先关系已证明。
它不包含页头／稳定性专题，也不包含本批未提交工具。具体执行需所有者批准，并在执行时重新核对。
Gitee 专业门禁覆盖与受保护 PR 精确 HEAD 合并能力未通过；线上反向镜像仍启用（见下方专项核查），旧机器人不能用于新候选。
GitHub 恢复后的回同步和从 Gitee 更新本地主线须单独受管收口，现有 `main.sync` 仍走 GitHub，禁止直接调用它冒充新车道。

批次：verification_pending；主线集成：未执行；部署：未执行；用户验收：未执行。
89 入口工作保留为下一产品目标；本轮未将之前的 86/89 报告关联升级为业务验收通过。
回退：本批文件均未提交，可按精确 owned diff 还原；不影响两个冻结专题。实际历史补齐后不倒退远端主线，
恢复 bundle 用于保全历史，产品回退走审查 PR。


## 临时集成流程验收：仅步骤 1—3（2026-09-23）

本次身份仍为上述 HEAD + 本批显式 dirty 范围；无远端写入、主线补齐、合并、部署或线上服务变更。
本节是同一结果索引的增量，不是新的交付报告。P4 工具修订仅涉及两个新增 Python 文件和本批文档。
L1 原政策结果承接：Make 配方、政策输入、受管环境未变；新增脚本语法解析及 diff whitespace 检查通过。
L2 执行 `make verify.gitee.integration.unit`：36 tests passed（0.180s 测试体，约 2s 命令）；
证据 `artifacts/gitee-temporary-integration/l2-acceptance.log`。L3/L4 无模块/产品运行影响，跳过；
L5 因下表已知通道阻塞保持 not_run，不执行 freeze.prepare、最终 Quick、提交或冻结。
本次验证不替代在线事件验收。下一最早步骤是补齐 P4 CI/平台只读证据与机制，不能跳至发布。

### 线上身份与证据

只读 SSH 到既有 `1.95.2.123`，读取 systemd 选定属性、进程非敏感环境、安装脚本和只读 SQLite。
没有读取输出凭据值。原始证据均在 `artifacts/gitee-temporary-integration/`：

- `live-audit.json`：UTC 2026-09-23 03:30:47；receiver PID 2309968、worker PID 2309973，
  自 2026-07-20 16:30:03 CST 运行。安装目录无 Git 元数据，不能赋予一个未经证明的部署提交号。
  安装脚本 mtime 为启动前一秒；磁盘文件与当前仓库脚本一致，未做进程内存级代码证明。
- receiver/worker 共用 `gitee_webhook_ci.py` SHA256
  `cf52ef6e60efe0321420b5c2f3884d8720ea379734bc1f33d09fe51be69cd046`；runner
  `gitee_ci_run.sh` SHA256 `ffd22ef31005bc620ff95fad0aff249215cd9b4f302f4e78648be2d782c713b3`。
- `live-queue-automation.json`：实际 sender 为 owner `leegege`（Push/PR），PR 另允许 `sce-ci-bot`；
  仓库限定 `leegege/sce-product-odoo`，路径 `/hooks/gitee`，时钟偏差 300 秒。
  worker 设置 mirror source `/var/lib/gitee-mirror/source.git`，无状态回传 token 环境项。
  队列按完整 SHA 作主键，当前远端 main=b9e3e56a 的历史 Push 任务 failed/exit 2。
  7 个 PR 和 7 个 Push 历史成功均不是当前候选证据；其余 4 PR、134 Push 失败不能直接归因当前代码。
- `automation-state.log`：保留 systemd 同名多值属性，证实镜像定时器每分钟触发，active/enabled；
  `actions.runner.Leedefend-sce-product-odoo.ci-1-95-2-123.service` 也为 active/running/enabled。
- `api-swagger_doc.json`：Gitee 官方 Open API 5.4.93 的公开接口定义；无远端写调用。
  来源：[官方 Swagger](https://gitee.com/api/v5/swagger_doc)。

### 原要求与 Gitee 实际执行对应

原要求以当前 `.github/workflows/` 及受管发布规则为准；下表不是凭历史服务健康判定等效。

| 门禁／原要求 | Gitee 实际执行 | 证据 | 缺口／结论 |
| --- | --- | --- | --- |
| Public Guard：当前风险分类、工作流契约、安全、历史和证据工具检查 | Push/PR 都只编译四个历史/安全脚本，运行两组历史/安全测试、`verify.repository.clean_history`、release scan、Actions security guard | live-audit runner；`public_guard.yml` | 部分复用；缺当前分类器、工作流/候选/合并策略及证据工具等检查，未等效 |
| Professional Quality：按 base/head 风险路由的专业门禁与受管模块测试 | Push 跳过；PR 安装前端依赖（`--frozen-lockfile=false`）后 `make ci` | runner；`professional_quality_gate.yml`；`make/ci.mk` 的 ci 配方 | 旧聚合目标不等于当前工作流；未证明分片、风险模式、报告及环境身份 |
| Frontend Release：固定工具链、锁文件、lint/typecheck/test/build，按风险运行完整 release 测试 | 未独立执行该工作流；只可能间接经旧 `make ci` 运行其中部分 | runner；`frontend_release_gate.yml` | 未覆盖/未证明当前完整命令与门禁结果 |
| Merge Policy：当前风险分类、授权检查汇总 | 无对应汇总/回传 | receiver/worker；`merge_policy_gate.yml` | 缺失，不能以本地 Quick 代替 |
| 本地冻结 Quick、独立审查、外部归档绑定同一候选 | 新 P4 publish 核对 Quick 和 generated evidence；当前候选 dirty，均未执行 | 新脚本；本记录 | 工具前置检查只是一部分，L5 尚未完成 |
| 失败不能通过 | runner `set -euo pipefail`；worker 非零 exit→failed | runner/Queue.complete | 非零失败路径存在；未对当前完整事件验收 |
| 零测试不能通过 | worker 只看 exit code，没有 test count 检查 | Queue.complete | 缺失，退出 0 的零测试可能通过 |
| 超时/取消不能通过 | subprocess 无 timeout，RuntimeMax=infinity，无取消协议；重启将 running 重排 | worker/loaded unit | 未有可靠超时/取消终态；不能证明所需语义 |
| 输出与最终结果一致 | result.txt 写 PASS 之后才做 mirror handoff；同 SHA 重跑前不清旧结果 | runner | handoff 失败仍可能留下 PASS 文件，Push 旧成功可残留；不能仅读该文件授权 |
| 完整 SHA 与 PR 更新失效 | runner detach/final HEAD 比对完整 SHA；队列主键 SHA，Push→PR 可升级 | runner/queue schema | 已绑定执行 SHA；未绑定 base、最新 PR head，旧 SHA 结果未因 PR 更新撤销 |
| required checks 真正阻挡 main 合入 | 无 Gitee check-runs 回传实现；平台保护配置尚无授权只读 API 证据 | receiver/worker；公开 API 支持 head_sha check-runs | 未证明，阻塞；SSH refs 无法证明保护和管理员例外 |
| 实际 PR 事件触发完整检查 | 本轮没有创建/更新 PR | 本轮只读边界 | not_run；保留到通道条件满足后用本 P4 候选验收 |

已询问登记的只读 API 凭据路径，当前未获提供。分支保护、required checks、平台 WebHook、机器人授权、
托管流水线及部署触发器配置因此为未证明；不把主机扫描无匹配解释为平台没有自动化。

### 精确合并：blocked

旧 `scripts/ops/gitee_pr_bot.py` 在查询 PR 后调用 PUT merge，只传 merge_method 等参数，
没有预期源 SHA 或目标 main SHA；不能消除查询与合并之间的竞态，也不能绑定旧授权失效。
官方 5.4.93 `PUT /v5/repos/{owner}/{repo}/pulls/{number}/merge` 参数列表同样未声明 head/base CAS。
这证明当前工具和已查 API **没有可用的原子绑定证据**，不是断言平台所有产品版本都绝无此能力。
暂无经验证的等效服务端锁定机制；正式合并保持 blocked，不试探调用 merge，不直接 push main 替代新候选合并。
恢复条件：平台可证明源/目标双绑定并拒绝漂移，或受管等效锁覆盖所有写入者且有竞态反例测试；
同时 required checks、审查必须绑定同一候选与有效目标基线。

### 自动化副作用与停用方案（未执行）

安装的反向镜像脚本 hash `b1aa24b356378585bb32c1b22e71ef61b8927cbd51451960280aacfeeaabeefb`，
目标 **`Leedefend/sce-product-odoo`**，与当前 origin 不同；本地同名脚本已经 fail-closed，线上却仍是旧实现。
worker 对通过公开检查且仍为远端 main 的 Push 交接到 source.git，定时器随后可向旧 GitHub 仓库快进。
当前镜像 service 最近失败不等于停用，未来环境恢复仍可能触发。systemd 显示 NeedDaemonReload=yes，
禁止不加分析地 reload/reinstall（可能激活其他磁盘配置）。

主机已扫描的 systemd/cron/source.git hooks 中没有独立合并机器人或部署触发器证据；
GitHub runner 存在且运行，平台侧与 runner 所接工作流是否部署仍未知。
受管停用方案须先纳入既有 P4 运维入口：精确 host/unit 白名单和显式停用确认，保存选定非敏感配置，
停用并停止 mirror timer、停止其 service，验证 disabled/inactive 且无正在执行的镜像；
保留 CI receiver/worker 和数据。随后核实平台 hooks/机器人/部署全部写入者，再登记单一写入窗口。
恢复不得简单 enable：先比较 source.git 与两端精确 SHA、审查累计变化和副作用，再单独授权恢复。
本轮只记录方案，无 systemctl 变更、凭据变更、平台 hook 变更。

### P4 修订、竞态测试与历史预演

- 普通快进 push 不是“远端旧 SHA 锁定”。新增本地真实 bare Git 测试：先观察 A，另一写入者推进 B，
  再 push 后继 C 仍成功；分叉 D 被拒绝且 C 保留。只写 unittest 临时目录，无网络。
- push 非零/超时及回读异常都给出 `status=uncertain`、`retry_allowed=false`、退出码 3；
  不声称远端零写入。只读回查确认状态后再决定恢复，不自动重试。已有分支快进、主线在 preflight 后漂移、
  写入成功后超时、回读失败后只读恢复均有用例。
- catchup 验证 bundle 自身 refs/heads/main 完整 SHA，并检查 bundle 后控制分支未漂移；
  错误 bundle、验证失败、控制分支变化都在 push 前拒绝。
- 历史补齐必须先排除自动写入者并安排单一写入窗口；普通 FF 保护不代替该条件。
  保护分支拒绝时停止，不改保护、不 force。推送结果不确定时也不重试。
- 最新 `make main.gitee.catchup EXPECTED_HEAD=de9a230d3faab18dd60a219f445f932a8af9d7f5 GITEE_EXPECTED_MAIN=b9e3e56a80c02c1eb277d2ac573e10286c4cd8e8`
  只读通过；原始 `catchup-plan-acceptance.json` 的 applied=false，仍是原 133 提交历史范围。
  clean 控制分支、已生成并验证的恢复 bundle、自动化隔离和精确执行授权均未齐备。

结论：本地工具定向修订已验证；临时通道验收仍 blocked/verification_pending。
候选 dirty、未提交、未冻结；主线集成、部署、用户验收均未执行。两个产品专题保留不动。


## 自动化隔离准备与精确合并裁决（同批增量）

范围：P4／临时通道运维与可行性裁决／本批规程、结果索引和 goal。
不修改 CI 或产品代码；不执行服务停用、权限变更、远端写入、历史补齐、合并和部署。
HEAD 仍为 de9a230d3faab18dd60a219f445f932a8af9d7f5，原 dirty 范围保留。
使用既有 project-governance-codex、sce-governed-delivery 治理；依照阶段规则不提前冻结。

### 1. 自动化隔离执行单（可审阅，未授权执行）

增量原证据：`artifacts/gitee-temporary-integration/isolation-readonly.json`，
采样 UTC 2026-09-23 03:39:03。首次只读解析因 `.runner` UTF-8 BOM 失败，未发生远端修改；
改为 utf-8-sig 后成功。不是重试未变化的环境故障。

| 精确对象 | 触发、方向及影响 | 当前任务／证据边界 | 停用、验证与恢复入口 |
| --- | --- | --- | --- |
| host 1.95.2.123：`gitee-to-github-mirror.timer` → `gitee-to-github-mirror.service` | 每分钟；source.git main → GitHub `Leedefend/sce-product-odoo` main；可写主线，继而触发该仓库工作流 | timer active/enabled；service failed，MainPID=0；只证明采样时无执行，下一分钟仍可能启动 | 需在既有 P4 Make 增补精确 pause/status/restore 入口（目前不存在）。经单独授权，保存 unit/启用状态，先关 timer 再停止 service；验证 timer disabled/inactive、service 无 PID/cgroup 子进程、source/目标 SHA 已记录。restore 须核对积压与目标 SHA、单独授权；不得直接使用 install/run/seed 充当恢复 |
| 同 host：`gitee-webhook-ci.service`、`gitee-ci-worker.service`；安装目录 `/opt/gitee-ci/sce-product-odoo` | `/hooks/gitee` 接收 owner 或允许 PR bot 事件；worker clone Gitee 候选、执行候选代码；成功 main Push 可写 `/var/lib/gitee-mirror/source.git` main | receiver/worker 运行；pending/running 队列为空；source main=`aaad9e06d5e0d70d92041b65b8a4ae9003fb7cda`。受检 runner 明确交接本地 refs；候选任务可执行任意仓库脚本，其全部运行能力不因 CI 名称被视为无副作用 | 现有只读 `make gitee.ci.server.status` 可用；无安全 pause/resume 入口。若不能证明任务沙箱不会写外部系统，则隔离范围必须含 receiver admission+worker：先关闭精确 hook/admission，核查/排空队列，再停 worker，确认无子进程；不得改 DB 清任务。恢复先审查积压完整 SHA、任务归属和写能力，再单独启用，不能自动消费旧队列 |
| Gitee `leegege/sce-product-odoo`，配置脚本意图 WebHook `https://1.95.2.123/hooks/gitee`、title=`sce-product-odoo-self-hosted-ci` | 脚本意图 Push+PR；当前平台 hook ID、事件、启用状态及其他 URL 尚未知 | 没有登记的只读 API 凭据路径；无法枚举全部 hooks 或投递中任务 | 必须先取得平台只读导出（ID、事件、URL 的脱敏身份、active、最近投递）。再对精确 ID 制定 disable/verify/restore；不得调用 `gitee.ci.repository.configure`，它会改保护、创建 PR 并测试 hook，不能作隔离入口 |
| Gitee owner/管理员、协作者、`sce-ci-bot`、deploy key/API token 和平台流水线 | 可通过 push/API/PR 写源分支/main 或自动合并；真实权限、绕过、流水线/部署规则未知 | receiver 接受 bot 不证明 bot 目前调度运行；主机已查范围无独立 bot 服务，不涵盖平台/其他主机 | 平台权限与自动化清单、活动任务、所有管理员绕过必须枚举；每个写入者精确身份对应停用和恢复。现有 `gitee.pr.bot.merge` 是旧固定候选手工入口，禁止调用；不能把“本次不调用”当远端锁 |
| `actions.runner.Leedefend-sce-product-odoo.ci-1-95-2-123.service` | GitHub `https://github.com/Leedefend/sce-product-odoo` 注册 runner agentId=2、agentName=ci-1-95-2-123、pool Default，目录 `/opt/actions-runner`；处理该仓库调度任务，可能有任务定义的写入/部署副作用 | active/running；进程只有 runsvc.sh/node/Runner.Listener，无 Worker；最近 Worker 日志 mtime 2026-07-20。不能证明远端没有排队任务或未来调度；注册文件不是平台授权范围的完整证明 | 保持运行，不因镜像隔离顺带停掉。先确认该仓库维护归属、平台 queued/in_progress、环境部署与调度权限；如确需停用须另行审阅专用 runner 入口，先 drain 后停。恢复还须审查积压任务；禁止卸载、删除凭据或牵连其他 runner |
| 两端平台的部署 WebHook／集成应用／流水线和 GitHub 旧仓库工作流 | Push/PR/定时/手动事件可能部署；本地当前 `.github/workflows` 不能代表旧仓库部署版本 | 精确对象、活动任务与实际权限均未证明；本地扫描只发现当前门禁和手动工作流，不能代替线上清单 | 暂无可执行停用对象；先取得旧 GitHub 仓库及 Gitee 平台只读清单，逐一明确 target/environment/触发/权限/恢复。未知对象不允许推送或创建 PR 来试探 |

隔离前置条件：所有未知路径清零或以平台机制证明不可写；任务静默需在执行时再核对，不能复用本次瞬时采样。
每个变更保留旧配置、精确对象、前后状态和恢复步骤。部分停用失败时停在安全阻断态，不继续写远端；
恢复必须按已成功修改的对象逆序处理，禁止未审查积压直接恢复自动任务。
当前完成的是**隔离执行单准备**，不是隔离完成；未知路径明确保持阻塞，不宣称枚举完成。

### 2. 精确合并裁决：当前不可实现

本轮核查终点已经到达，不继续寻找其他接口或扩建 CI。

| 限定路径 | 配置／实现证据 | 行为证据 | 裁决 |
| --- | --- | --- | --- |
| 平台原生合并 | 已保存官方 Open API 5.4.93 PUT merge 参数，无 expected source/head 或 target/base 参数；旧 bot GET→PUT 无原子条件。官方保护接口的配置调用不能证明所有写入者受到锁定 | 未执行远端变更；未有原子拒绝源/目标漂移的既有证明 | 当前不可实现：已查机制不足；不把未公开的可能能力当可实施方案 |
| 等效锁定流程 | 没有远端源/目标双锁配置，没有管理员、API、key、bot、定时/平台任务的完整写权限清单与禁写证明；本地锁和单一写入窗口不补足此条件 | 未有并发写入拒绝、锁失败恢复证据 | 当前不可实现：缺配置及行为证明，不以暂时空闲代替锁 |

“当前不可实现”限定于当前权限、已登记工具和可取得证据，不推断 Gitee 所有产品永远不支持。
若日后出现新平台能力证明，按以下**已准备但未执行**用例重新立项核查，不能重复无边界搜索：

1. 绑定仓库、PR、源 H、目标 B、审查与 checks；只有 H/B 相符且 required checks 完整时可成功一次。
2. 在请求发出前及服务端处理窗口分别改变源 H、目标 B；旧授权必须被原子拒绝且目标不发生旧候选合并。
3. 等效锁测试覆盖 owner/admin bypass、协作者、deploy key、API/bot、自动任务；检查至合并整个区间对源/目标写入均拒绝，仅允许绑定候选的合并执行者完成限定操作。
4. 锁获取部分失败、进程崩溃、超时/网络失联、目标漂移时不得合并；恢复须可读回原保护配置且不扩大写权限，无法确认则保持锁定并人工恢复。无无人值守自动解锁窗口。
5. 成功后读取实际合并源/基线与 main，检查日志、审查、构建身份一致。所有用例须另行审阅精确对象及远端变更授权，不拿两个产品专题试验。

后续路线选第二条：**Gitee 暂定位历史镜像／候选保存通道，正式主线集成保持阻塞**。
候选保存也必须先完成自动化隔离和原发布保护；当前不允许马上 push。历史补齐仍暂停。
本地产品开发和验收可按受管流程继续；两个既有产品专题本批不动，不能为打通通道而拼接。

### 3. P4 剩余改动清单与最小 CI 设计

以下均为待实施设计；通道可行性条件未变化前，不启动完整 CI 重建。

| 项目／最小改动 | 定向测试／验收用例 | 收口条件 |
| --- | --- | --- |
| 隔离工具：给既有 P4 运维增加精确对象 pause/status/restore；默认 plan，身份/确认、前后快照和失败恢复 | 错 host/unit/确认拒绝；有活动任务拒绝；部分停用失败不写远端；只恢复实际变更对象；配置漂移拒绝恢复；mock 单测后单独授权线上验证 | 所有写入者清单可读且受控，未知项清零；不共享停用其他 runner |
| 发布保护：将隔离状态和使用目的纳入既有 publish/catchup 前置，不降低 clean/Quick/审查/回读门禁 | 缺隔离或过期环境身份拒绝；目标/候选漂移拒绝；仅候选保存不能授权主线合并；不确定结果仍禁止自动重试 | 隔离输入来源有权威且执行时有效；不接受自填布尔值冒充远端约束；此时才实现并补受影响测试 |
| 零测试：按任务清单解析结构化测试计数，对声明必须测试的任务强制 count>0，解析缺失失败 | 0 tests/空报告/损坏报告/全跳过拒绝；有效非零测试通过；非测试任务按清单明确 N/A | 每个受影响测试命令均有可靠报告适配，不靠 stdout 单一 OK 文本 |
| 超时／取消：worker 有界截止、受控子进程组终止、终态持久化；按 attempt 隔离输出并最后原子发布 receipt | 超时、取消、子进程残留、重启、完成与取消竞态；不得保留旧 PASS；重启有确定恢复状态 | 终态仅 success/failure/timed_out/cancelled 等明确结果；缺结果不能成功，无无限 running |
| 完整回传：按当前必需检查清单创建 pending 并逐项回传，最终聚合 fail closed；平台 required checks 配置另验 | 缺项、失败、未完成、回传失败、重复/乱序回调、权限错误都不放行 | 本地结果、平台 checks、保护规则三者匹配；正式合并阻塞未解除时不得宣称可集成 |
| 旧结果失效：attempt 绑定 repo/PR/H/B/策略版本；源变化废弃旧授权，目标变化按确定影响分析决定重跑 | 旧 H 成功迟到、新 H 失败、B 漂移、PR 重开、同 SHA 不同 PR/目标；无法证明独立影响即失效 | 最新身份查询与平台执行约束共同成立；查询本身不充当原子锁 |
| 构建身份：受检出 SHA、base、事件、命令清单、策略版本、attempt/日志统一绑定；移除宽松 lockfile 安装 | 检出不符、日志/回执串候选、重复任务覆盖、锁文件变动均失败 | 依据当前 required workflow 的命令映射逐项覆盖；旧 `make ci` 名称不作为等效证据 |
| 最终同批收口 | 只重跑实际新增/受影响测试；整体验证和独立审查依赖精确冻结候选 | 未知副作用和交付阻塞关闭后才准备生成证据/提交/冻结；不为消除 dirty 提前 finalization |

验证承接：两个 Python 文件、Make 配方及运行配置本轮未改，原 36 项 L2 结果有效，未重跑。
本轮 L0 核对当前分支/HEAD/dirty；L1 为文档差异检查。L2 无代码变化而承接；L3/L4 无运行或产品修改而不执行；
L5 因明确阻塞保持 not_run。批次 verification_pending；主线集成、部署、用户验收均未执行。


## 自动 CI 可用性验证准备（同批增量，正式合并独立阻塞）

本轮按最新指令调整依赖：本地开发/定向验证可继续；远端推送等待触发副作用明确；正式合并独立阻塞；
部署不在范围。精确合并不再阻塞 CI 准备或未来独立 CI 验收，不重启精确合并探索。
P4／既有 CI 执行器选择和候选验证准备；本轮仅更新本批文档与 goal，不修改服务或工具行为。
HEAD 仍为 de9a230d3faab18dd60a219f445f932a8af9d7f5 + 原 owned dirty 范围，两个产品专题不动。

### 1. 候选推送触发清单及平台读取缺口

**目前不能声称清单完整，也不能断言候选推送不会触发部署或外部同步。**
已再次请求登记的只读凭据路径或平台配置导出；未获得前停止平台泛化探索，不调用配置/测试 API。
与上节隔离执行单共用下列增量，不另建报告。

| 事件／自动化 | 已证实的执行路径 | 仍需精确配置证据／读取权限 |
| --- | --- | --- |
| 候选分支 Push → 已知 receiver/worker | 若 WebHook 实际订阅并投递，接收允许 sender 的 push_hooks，按完整 after SHA 入队；执行公开检查。已部署代码未保留/限制 push ref，因此不能仅凭候选分支名认定 admission 已隔离 | Gitee 仓库 hooks 只读权限：全部 hook ID、启用状态、Push/PR/tag 事件、目标用途、最近投递及进行中任务；配置脚本的意图不是线上清单 |
| Push → mirror handoff → 旧 GitHub | runner 在 Push 后比较候选 SHA 与实时 main，相等才交接 source.git；timer 可把 source main 写到旧 GitHub main。普通新候选 H 不等于 main 时不交接，但分支名本身不提供禁同步保证；旧积压也可独立运行 | 停用/验证沿用精确 mirror timer/service 执行单；移除候选模式交接能力并证明；未实际执行 |
| PR → worker | 若实际投递，接受同仓 PR、owner/允许 bot；执行当前旧 `make ci`，不是本次最小验收目标 | hook PR 配置和其他 PR 机器人/应用清单，应用安装范围、写权限及自动合并规则；本次不创建 PR |
| 标签 → receiver／平台 | 当前配置脚本意图 tag_push_events=false；receiver 对 push_hooks 没有 refs/heads 限制，不能据此证明 tag 永远不执行；其他 hooks/Go 未知 | tag 订阅及所有流水线触发 ref/filter，最近投递；最小验收模式须明确拒绝标签 |
| Gitee Go 流水线 | 仓库当前开通状态、流水线 ID、启用与自动触发、运行任务均未知 | Go 项目/仓库流水线只读：完整 YAML/步骤、触发器、凭据引用名/权限（无值）、环境、运行记录、额度/并发/超时；只读资源与权限页面或脱敏导出 |
| 机器人、应用、可写身份及部署 | 未取得平台完整枚举，不能排除任意 Push/PR/tag 引发合并、部署或跨仓写入 | 仓库成员/继承角色/管理员绕过、deploy key 写权限、应用/bot 授权范围、自动化调度、部署环境/审批配置的只读管理视图；token 只需元数据，不索取值 |
| 旧 GitHub runner | 已知属于 Leedefend/sce-product-odoo，可能消费反向同步导致的任务；不因采样空闲而停用 | 旧仓库工作流、queued/in_progress、部署和集成配置只读证据；沿用原归属检查，不再次全面扫描主机 |

输出只保留 hook ID、脱敏目标主机/用途/路径标识、事件和状态；URL query/userinfo、令牌、密钥、secret 值均不进入报告。
缺少上述读取能力时，判定为“未查清、阻塞推送”，不是“无触发器”。官方公开文档不能替代目标仓库配置。

### 2. 执行器选择：现有 worker（首次最小验收单一路线）

选择依据是复用已登记资源、最小依赖以及可核实的现有入口；不是宣称现有 worker 已满足可信 CI。
不创建 Gitee Go 流水线，不触发任务、不购买资源，也不同时维护两套流水线。

| 核查项 | Gitee Go | 现有 worker／选择依据 |
| --- | --- | --- |
| 开通与配置权限 | 当前仓库未证明；官方企业权限说明不能直接推断本个人仓库权限 | 已安装 receiver/worker；后续修改走既有受管 P4 配置入口与单独线上授权 |
| 执行环境 | 当前可选镜像/工具版本、容器能力未知 | 新只读证据 `ci-executor-readonly.json`：Python 3.12.3、Git 2.43.0、GNU Make 4.3；适合最小检查。另有 Node 22.22.0、pnpm 9.15.9、Docker CLI 29.1.3，但未证明服务用户或 daemon 权限，不据此批准完整前端/容器检查 |
| 时长/并发/超时 | 当前套餐、剩余额度、单任务上限、并发均未知；宣传额度不是仓库可用额度 | 现有单 worker 串行；最小测试本地历史约 0.180s，不依赖业务服务；拟任务 deadline 120s、超时终止宽限 5s，必须验证而非沿用无限运行 |
| 身份/结果 | 公开能力不能证明此仓库的 SHA/日志/失败状态行为 | 已有完整 SHA 检出比对与队列；仍须补 attempt 身份、非零计数、超时/取消、终态和可读结果 |
| 隔离/接入成本 | 未证明不部署、凭据隔离及所有自动触发配置，不能认定接入更低成本 | 复用现有 host/queue/目录；须隔离候选执行与 receiver secret、status 凭据、mirror 写路径。当前同服务用户能力不等于安全隔离，未完成前不执行候选 |

参考仅用于能力背景：[Gitee Go 官方介绍](https://gitee.com/features/gitee-go)、
[企业成员权限说明](https://gitee.com/help/articles/4159?skip_mobile=true)。
未把其公开套餐或企业角色规则当成本仓库实况。选择 worker 后停止 Go 扩展设计；若后续收到明确相反的仓库配置证据，再评审选择，不能并行建设。

### 3. 首次最小 CI 验收方案（prepared，未触发）

正常检查固定为现有 `ENV=test make verify.gitee.integration.unit`，当前 36 项 Python unittest，
只使用 mock 和临时本地 Git 仓库，不读写业务数据库；依赖 Python/Git/Make，不需要 Node、Odoo 或 Docker。
本轮不重复运行这 36 项；原日志 `l2-acceptance.log` 继续有效，未来线上执行属于新的环境链路验收。

触发方式：仅目标仓库中**单一已登记候选分支的真实 Push WebHook**，绑定 branch、完整 H、事件 ID；
不创建 PR，不推 main/tag，不伪造 hook。候选分支沿用本 P4 分支，具体发布 H 在收敛和所需发布检查后确定，
当前 dirty SHA 不能冒充待发布候选。只有第一项副作用清零且执行配置审阅完成后才安排真实触发。

服务端受管配置选择 `ci_chain_acceptance` 模式，固定命令/受控负向用例清单；候选或 payload 不能提供任意 shell 命令、
超时时间、结果文件路径或授权标志。每个 case 独立 attempt/目录；受控夹具生成于测试临时目录，不修改产品源码。
运行候选检查的低权限执行边界不能读取 WebHook/status token、写 mirror 或部署目录；抓取身份只读且不暴露写凭据。
结果发布由服务端受信进程完成，候选生成的 PASS 文本不能直接转为平台成功。

| 用例 | 操作／预期 | 通过标准 |
| --- | --- | --- |
| 正常 | 真实 Push H → 确认 clone/checkout H → 固定 Make 检查 | receipt/log/checkout/event/H 全一致；结构化 unittest testsRun=36、失败/错误=0（未来测试新增时按受审清单更新预期），有效执行计数>0；exit 0 且平台或受管状态查询可读 |
| 故意失败 | 同 H 的受控临时 unittest 夹具含一项 assert 失败 | case=failed、非零退出；attempt 有独立失败日志，绝不生成该 case 成功 |
| 零测试 | 受控 empty TestSuite，常规 runner 会 exit 0 | 受管包装根据 count=0 判 failed/zero_tests；不接受缺失/损坏测试报告 |
| 超时 | 受控阻塞夹具超过专用短测试 deadline（例如 2s） | timed_out，宽限后无子进程，不能留 running/PASS；正式正常检查 deadline 120s |
| 取消 | 受控可等待夹具开始后，通过精确 job/attempt 取消入口 | cancelled，子进程结束，完成与取消竞态不能改成成功；取消功能须先补齐，不能把杀整个 worker 当通过 |
| 新提交隔离 | 后续受审候选 H2 真实 Push；H1 晚到结果、H1 成功仍保留历史 | H2 从 pending 开始；查询最新候选不读 H1 成功；H2 的 SHA/attempt 独立。不以修改产品代码制造失败 |

负向 case 的期望失败可使**验收汇总**通过，但必须保留原 case 的 failed/timed_out/cancelled 终态，
不能把故意失败伪装成产品检查成功。首次可接受受管只读查询+日志读取作为结果通道，须逐 case 可追溯；
这不等于平台 required checks 可阻止合并。完整回传与门禁等效属于后续单独验收。

### 4. 独立发布路径、精确待变更及恢复

已核查 `Integration.publish`：除 remote main 为候选祖先外，还强制 HISTORICAL_MAIN(de9a) 为 remote main 祖先。
故当前 b9e 主线会被现有 `pr.push.gitee` 拒绝；`candidate.mirror.gitee` 又要求 GitHub 对应分支精确 SHA。
**现状没有可直接执行的独立候选发布路径。** runner 本身 clone/fetch H 并 detach，不技术依赖 main 先补齐。
历史补齐从 CI 关键路径移除；不能通过直接 git push、删除断言或改用旧入口绕过当前保护。

| 精确待变更 | 最小实现与新增/受影响测试 | 恢复方案／进入条件 |
| --- | --- | --- |
| 同一发布入口的用途区分 | 在 `pr.push.gitee`/既有 Python 工具内设计显式 CI-only 用途，保留默认集成模式原约束；CI-only 绑定单一分支/H/观测 main/隔离配置版本，仅移除历史 main 已补齐要求，返回 merge_authorized=false。clean、Quick、审查/归档、普通 FF、回读和不确定恢复保留 | 尚未实现；需同步 allowlist/规程并定向验证落后 main 的 CI-only 可预演、默认仍拒绝、main/tag/错分支/隔离缺失拒绝、漂移拒绝。撤回该用途不删除远端候选、不回退 main |
| 现有 receiver/worker 验收模式 | `scripts/ci/gitee_webhook_ci.py`、runner 和对应测试：精确 ref/event allowlist，attempt/case 状态、计数、deadline/cancel、受信 receipt；不运行旧 make ci 或 mirror handoff | 先本地定向测试，再受管部署到既有安装路径；保存原脚本 hash/配置/队列兼容快照。失败停止候选入队，保留日志；schema 不兼容不得盲目降级 worker |
| 运行隔离与配置 | 复用现有 systemd/目录，移除验收子任务的 mirror 写能力与凭据访问，审阅现有用户/组和执行权限，精确 job 取消入口 | 若必须新增账户/沙箱等环境权限，单列 P4 配置授权，不在业务中临时拼装；恢复原配置前核实队列和自动化副作用，保持外部同步关闭 |
| 平台触发与外部自动化 | 取得完整 ID 清单后才决定禁用哪些 hook/Go/deploy；已知 mirror timer/service 沿用上节精确执行单；已知 hook 仅选定 Push 验收用途 | 当前 ID/配置未知，不能生成可执行平台变更。保存旧事件/active/过滤状态；独立授权后修改并回读。恢复旧自动化须再授权，不能在验收清理时自动打开部署/反向镜像 |
| 验收清理 | 删除仅本 attempt 临时工作目录，保留不可变日志/receipt；不自动删分支、不动两个产品专题 | 先证明子进程退出；保留失败现场索引，未知写结果只读核对，不自动重推 |

本轮执行器选择不需要改工具源码，故未扩建 worker、未放松 publish；以上是首次验收前的明确剩余实现范围。
原 36 tests 与 Python/Make 输入不变，L2 承接不重跑；只读版本探测不是任务执行权限/完整依赖通过。
L1 文档 whitespace 检查；L3/L4 未改运行或产品，not_run；L5 暂不冻结/Quick。
批次 verification_pending；自动 CI 链路尚未验收；主线合并 blocked；部署/用户验收未执行。


## 本地 CI-only 最小实现与集中复核

本轮实际实现，仍在同一 P4 批次。Formal Product Layer=P4；Layer Target=既有 CI worker 与候选发布；
Module=scripts/ci、scripts/ops、scripts/verify、既有安装打包与 Make；运维机制不属于 P0—P3，
不更改产品业务规则/数据；影响仅显式验收模式和新发布用途，legacy 默认保持。
平台材料仍未到位；交接只接受既有凭据文件路径，或管理员注明仓库/导出时间的配置导出。
不重复索要，不把截图未覆盖项目当已证明。远端写入、服务修改和线上任务保持禁止。

### 实际文件职责

| 文件 | 实际行为 |
| --- | --- |
| scripts/ci/gitee_webhook_ci.py | 显式模式选择；验证精确 ref；复用接收签名；路由独立验收队列/执行器；取消入口。未启用时仍为原执行路径 |
| scripts/ci/gitee_ci_acceptance.py | 固定 repo/branch/SHA；独立队列表；duplicate/取消/迟到结果隔离；trusted checkout；bubblewrap 无网络/凭据构建；超时、kill/wait、工作目录清理、身份回执 |
| scripts/ci/gitee_ci_acceptance_check.py | 服务端固定 unittest suite，使用运行结果动态有效计数；零测试/全跳过失败。对应 Make 目标同一测试集，不执行候选任意 Make 配方 |
| scripts/ops/gitee_temporary_integration.py | 既有入口添加 purpose=ci-only；允许落后 main 的预演、完整历史范围披露、无集成资格回执；APPLY 因平台证据缺失硬阻塞 |
| scripts/verify/test_gitee_ci_acceptance.py | 真实 sandbox/进程/本地 Git checkout 测试，受控失败夹具，不改产品代码 |
| scripts/ops/test_gitee_temporary_integration.py | 新用途和错误范围零写测试；原共享发布逻辑回归 |
| deploy/gitee-ci/install.sh、scripts/ops/install_gitee_webhook_ci.sh | 打包安装新模块，原模式默认不变；没有执行安装或改线上配置 |
| make/codex.mk、规程/allowlist/goal | 新本地测试入口与显式用途，记录使用约束；不授权线上写入 |

### 验证及影响分析

阶段身份为 de9a230d3faab18dd60a219f445f932a8af9d7f5 + 上述 owned dirty 范围（含本批原有文档）。
L0 preflight 已核对；L1 `make ci.local.iteration` passed（原始 l1-ci-only.log），后续仅受影响脚本语法、
安装脚本 `bash -n` 和 diff 检查；不以反复 Quick 代替诊断。

| 层／命令 | 实际结果 | 原始证据（artifacts/gitee-temporary-integration/） |
| --- | --- | --- |
| L2 `make verify.gitee.ci_only.unit` 初版 | 11 tests passed，1.244s | l2-ci-only.log |
| L2 同入口，增加真实 checkout、签名 admission 与 cancel/finish 竞态 | 14 tests passed，1.373s | l2-ci-only-final.log |
| L2 同入口，集中复核后完整受影响集合 | 16 tests passed，1.624s；其中真实 sandbox 又运行当前固定发布 suite，动态取得非零计数 | l2-ci-only-reviewed.log |
| L2 `make verify.gitee.integration.unit` | 39 tests passed，0.251s | l2-publication-ci-only.log |
| L2 `python3 scripts/verify/test_gitee_webhook_ci.py` | 18 tests passed，0.497s | l2-worker-legacy.log |
| 只读 `make pr.push.gitee ... GITEE_PUBLICATION_PURPOSE=ci-only` | passed preview，writes=0/applied=false | ci-only-preview.json |

原 36 项中发布函数、FakeLane 及共用入口有变化，因此完整重跑该小测试文件为 39 项；没有重跑无关产品测试。
legacy 的 18 项用于证明模式默认行为。之后修订仅验收异常分支和新模块，不影响 legacy 路径，承接这 18 项。
L3 线上 worker/bwrap/systemd 用户权限 not_run；无模块/数据升级；L4 浏览器不适用；L5 未执行 Quick/冻结/发布。

集中复核为本轮本地行为复核，不冒充独立最终审查。发现并关闭：取消与完成竞态、报告 symlink/非普通文件风险、
验收模块未进入安装包、初始化失败终态归类。对应补验已通过。
测试明确检查了临时工作目录消失、实际后台子进程不再存在（含 setsid 逃离进程组）、
构建看不到敏感环境/宿主凭据路径且外网连接失败、真实 clone/checkout 身份、结果文件身份、
旧 SHA 晚完成不能改变新 SHA、零/全跳过测试失败。不是只断言状态字符串。

限制：这是同仓已审候选的受限 CI 检查，不声称能防止恶意测试代码伪造自身 unittest 断言结果；
测试代码本身仍需审查。父进程结果身份与终态不由 payload 命令控制，sandbox 不含线上凭据。
线上实际 kernel/bwrap/服务用户能力未验证，不允许无 sandbox 降级。结果仍不是正式合并授权。

### 已执行预演范围

当前只读预演绑定 Gitee main=b9e3e56a80c02c1eb277d2ac573e10286c4cd8e8，
候选 HEAD=de9a230d3faab18dd60a219f445f932a8af9d7f5：相对 main **133 个提交、1234 个差异路径**。
JSON 列出全部完整 commit SHA 与路径；additional_visible_code_possible=true。
这包含已存在的历史主线代码，不只是 CI 改动，可能新增 Gitee 可见代码范围；没有证明这些对象在其他远端 refs 中不存在。
当前工具与文档 dirty 改动未包含（excludes_uncommitted_changes=true），不把本次预演称为新代码发布方案。
本地提交后若将来发布，必须重新按最终 clean SHA 生成范围；不重跑未变测试只为换 SHA。
实际 CI-only APPLY 一律拒绝，等待平台配置证据及受审放行实现；普通集成路径不放宽。

### 尚未执行的线上变更

1. 查清平台 hooks/Go/可写身份/部署配置并完成原隔离执行单；旧 runner 保持不动。
2. 核对现有主机 bubblewrap、用户命名空间及服务用户限制；精确配置显式 ci-only 模式，部署模块并回读 hash。
3. 经受审证据绑定打开 CI-only 实际发布，重新披露新 HEAD 历史范围；未授权前不能改成布尔开关放行。
4. 真实候选 Push、在线负向用例/取消/日志查询；线上验收全部 not_run。

恢复：默认 legacy 未改；本地可按 owned diff 回退。日后模式回退须停止本模式任务、确认 PID 清理、保留独立表与原始结果；
不删除队列历史、不自动恢复反向同步或部署。当前结论：**本地实现已验证，线上验收受权限阻塞**。
本地阶段不是主线集成/版本发布/产品交付；正式合并继续独立阻塞，两个产品专题未动。


最终复核补验：清除候选中已有的计数文件，防止检查器提前退出继承旧成功。
`make verify.gitee.ci_only.unit` 最终 **17 tests passed / 1.750s**，原始 `l2-ci-only-closed.log`；
包含真实 sandbox 运行当前 39 项固定 suite、进程回收和旧报告反例。既有 39/18 项结果输入未变化，承接不重复。
allowlist 变更后定向重验 `make verify.baseline.iteration.execution.policy`，原始 `l1-policy-ci-only.log`。
本轮形成本地迭代检查点供审阅，非冻结交付候选，不执行 freeze.prepare 或 Quick。
提交后的只读预演存 `ci-only-preview-checkpoint.json`，它才包含本批已提交改动；先前 133 提交预演保留时间语境。


检查点复核再补一项：验收模式也保留签名时间戳重放约束，同一投递/同一 SHA 去重，
重用同一签名时间戳投递不同 SHA 则拒绝且不入队。新增反例后，受影响验收集合最终
**18 tests passed / 1.708s**，原始 `l2-ci-only-replay.log`；39 项发布和 18 项 legacy 结果继续承接。
本地检查点预演现包含 **134 个提交、1247 个差异路径**（相对 b9e main），dirty=false；
结果仍非集成资格，实际远端写入为零。本地检查点不是最终冻结，不触发 Quick。


## 真实 Push 目标：公开范围与增量更新实现（第 1—3 步）

用户已决定保持公开；本轮不补齐 main、不合并产品专题、不部署产品。使用原自建 receiver/worker，
P4 仅新增公开历史扫描与受管增量更新能力。3dd58b82 原检查点保留，新改动另建提交。

### 公开范围精确裁决（仅绑定 3dd58b82）

重新读取 41 个远端 refs；对原来缺失的 4 个 PR MERGE 对象执行受管仓库的精确 fetch
（不创建仓库，不更新分支，不写远端，`--no-tags --no-write-fetch-head`）。扫描前后 refs 文本一致。
现在全部远端对象可解析。候选相对这些 refs 新增 **134 commits / 2739 blobs**；
相对 main 的 1247 diff paths 与新增内容对象数不是同一指标。

原始 `artifacts/gitee-temporary-integration/publication-history-scan-3dd58b82-final.json` 包含：全部新增提交 SHA、
每个新增 blob 的完整 SHA/内容 SHA256/大小/全部历史路径、commit 内容 hash、扫描器与规则目录 hash。
按 Git 对象扫描，无后缀/大小跳过；历史中间版本均覆盖。此范围无二进制跳过，也无在候选最终树完全消失的新增 blob 路径；
已删除内容仍经遍历历史树纳入判定，已在远端可达的旧内容不算新增公开内容。删除中间秘密的反例测试通过。

| 分类 | 结果／裁决 |
| --- | --- |
| 凭据/秘密 | 当前高置信规则确认命中 0；初始 6 个 blob 的 7 个旧指纹匹配来自 LC-006/LC-008，规则目录明确 NORMAL_TEXT；按既有目录分类，不打印正文或添加豁免 |
| 个人数据规则 | 未豁免命中 0，精确使用既有 full-blob/path/rule/classification 豁免登记；不扩展豁免范围 |
| 客户资产/受限材料 | 未发现新增客户文件载荷；有下述两个普通 P4 文件含具名客户标识引用，缺少这些标识对外公开的明确依据，保留具体授权项 |
| 普通项目代码 | 2739 新增内容对象及 134 commit 元数据已遍历；模式扫描不是对未知秘密的数学证明，扫描覆盖和局限均保留；不能据此自动放行后续新候选 |

**具体待确认清单（不泛问全部历史）：**

- `scripts/verify/tenant_product_payload_boundary_guard.py`，blob `0f66fd4257b98c7dd119e8ef71ec1c1c48b780a7`：
  具名客户标识处于 `CUSTOMER_IDENTITY_TOKENS` 防泄漏规则常量；技术所有权=P4，标识公开授权属于项目/客户资产责任人，现有材料未提供。
- `scripts/verify/test_tenant_product_payload_boundary_guard.py`，blob `0273b43eac554933dc04ef28a73f12d8c770ab27`：
  对应客户模块/归档命名拒绝测试及指纹日志测试；无客户业务正文。需明确允许这些具名测试标识随公开源码发布，或另行治理历史范围。

结论：**3dd58b82 不予发布放行**；当前阻塞是上述精确标识公开依据与平台配置权限，不是发现已确认的活跃密钥。
不删除最新文件来冒充历史清理，不改写历史、不新建仓库或另行上传绕过。

### 平台触发清单

此前凭据文件路径/注明仓库和时间的管理员导出仍未到位，不再次索要令牌。
已知 Push→receiver→worker，满足 SHA=main 时可能交接 mirror；镜像 timer 仍是既有隔离对象。
所有 Push/PR hooks 的 ID/订阅/active/分支过滤、Go 触发器、自动合并身份、部署/反向同步全部路径，
以及本次候选分支会命中哪些规则，仍缺配置读取权限；不能补写“无其他触发器”。
第 2 步明确 blocked/configuration_access；不做猜测性平台探测，不执行隔离。

### 增量更新实际实现

- `scripts/ops/gitee_ci_incremental_update.py`：新受管入口默认只读；固定 host、三个模块及六个目标路径；
  source SHA+工具 hash+旧/新内容/凭据状态摘要绑定预演。只编辑模式与 mirror 交接项、worker 写路径，保留其他 env 字节和凭据。
- `scripts/ops/gitee_publication_scope.py`：精确远端 refs 差集的历史内容扫描，复用现有秘密/个人数据规则，不输出匹配值。
- 两个 `scripts/verify/test_gitee_*` 新测试文件、`make/codex.mk`、规程/allowlist 同步。
- 线上流程代码包含固定 bubblewrap 包、受限 namespace 探针、文件+CI SQLite 备份校验、服务启动回读、失败恢复。
  apply 前核验 mirror 停用和队列为空；不自动替用户隔离未知平台规则。
- 旧 `gitee.ci.server.install` 未调用；secret/SSH key/端口/业务 DB 不重建，不修改旧 runner。

### 定向验证与预演

基线 3dd58b82 + 本轮 owned dirty；L1 `make ci.local.iteration` passed，证据 l1-incremental-update.log。
新 Python 语法检查通过。L2 新增更新测试从 12 项扩展到 **15 passed / 0.337s**（l2-incremental-update-reviewed.log），
验证计划漂移/凭据漂移零写、配置保留、备份可读完整、sandbox 失败停止、服务失败恢复、损坏备份拒绝、默认预演无写。
这些测试使用临时文件/SQLite 与 fake systemctl/apt，不冒称线上恢复演练。
扫描测试初次因空对象集合处理错误失败（4 项中 1 error），owning P4；修复空集后 **4 passed / 0.166s**
（l2-publication-scope-final.log）：已删历史秘密、远端已有对象排除、缺对象失败关闭、二进制不静默跳过。
扫描器修改后仅重跑受影响扫描与其测试。原 18/39/18 组及 worker 源未改，承接不重跑。

已执行 `make gitee.ci.server.update EXPECTED_HEAD=3dd58b82...` 只读预演，证据 incremental-install-plan.json：
现有两服务 active、CI 活动任务 0、bwrap 不存在、固定包 bubblewrap=0.9.0-1ubuntu0.3、writes=0。
该预演绑定开发时 updater hash；最终本地新提交后重新生成 source/head/hash 对齐的预演（incremental-install-plan-checkpoint.json）。
工具通过 SSH stdin 做只读检查，没有持久安装文件、创建备份、安装软件包或启停服务。

当前仅第 1—3 步：公开授权和平台配置未齐，L3 线上安装、L4真实事件、L5冻结/Quick/独立交付审查全部 not_run。
新本地提交是可审阅开发检查点，不覆盖3dd58b82；第4步必须重新按最终冻结候选生成公开范围，不能自动沿用本次结论。


补充统计：2739 个新增 blob 对应 1245 个不同历史路径；另两项 main diff 路径不等于新内容暴露。
扫描前后 refs 一致性已通过 byte compare。allowlist 变更后受影响政策定向检查通过（l1-update-policy.log）。
本地新文件源码 hash 和两组测试输入关联保存在 incremental-update-local-evidence.json；提交不改变这些输入，
后续只重做绑定新 source SHA 的只读安装预演，不重跑未变化测试。
