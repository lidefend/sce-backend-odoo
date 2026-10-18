# 统一执行器回执与调度草案

## 归属与边界

本批 `AGENT-DISPATCH-INBOX-20261017`，P4 ops delivery tool；分支
`fix/agent-dispatch-inbox-20261017`，基线 `80da1af3d060201cebbddc58146e940a7f34b570`，dirty。
复用第二工作树，不改 Demo 工作树，不增加第三棵工作树。
范围限回执、身份检查、任务下发/确认、后台只读审核、私有队列迁移和交接文档。

授权模型是：**所有者持续授权 → 总调度在范围内裁决并下发 → 执行器执行 → 门禁验收**。
模型输出和后台草案本身不是执行授权；但已登记的总调度可以在所有者授权范围内下发并推进可执行任务，
不需要所有者对已覆盖的动作逐次确认。任务记录内的 `authorization` 引用就是该任务允许动作的依据。
`automatic_execution=false` 只表示后台进程不会自行运行执行器，不表示执行器没有授权。
执行器 `run.json` 仍是结果权威；回执只引用它和原始证据，不复制整套台账。
任务记录中的 `authorization` 是执行授权的唯一依据；`run.json` 的 `authorization`
必须与任务引用一致（id 相同且 status active）。缺少 run 授权不是“等待所有者授权”，
而是回执事实不完整，执行器应补齐后继续。`execution_authorized` 是废弃字段，禁止写入新回执；
如需表达后台是否自动运行，只能使用 `background_auto_execution`。

共享箱位于用户私有目录 `$HOME/workspace/.sce-dispatch`，不进入公开 Git。
目录 0700、JSON 文件 0600；不得提交密钥、原始客户数据或凭据到摘要。
审核会把回执摘要、路径、哈希、任务记录和队列资源声明发送给当前 Codex 配置的模型；
不会上传引用日志全文。本机同用户进程属于信任边界，本机制不认证同用户下的执行器身份。

## 唯一调度者与 lane 入口

当前唯一调度者为 `codex-main-dispatcher-20261018C`，接管时间
`2026-10-18T06:03:53+00:00`，记录在私有 `config.json` 并由 `status` 回读。
接管历史保留在 `dispatcher_history`；任何时刻只允许一个当前调度者。

本次接管后已核验并登记的真实 git 根：

| lane | repository | 说明 |
| --- | --- | --- |
| `demo` | `/home/lidefend/workspace/sce-backend-odoo` | 既有 Demo 工作树 |
| `user` | 客户模块工作树（路径由部署登记，不进公开仓） | 客户模块 lane |
| `frontend` | `/home/lidefend/workspace/sce-product-odoo-clean-root` | 回执与证据根。**生产前端源码在主仓** `/home/lidefend/workspace/sce-backend-odoo/frontend/`；clean-root 内的前端树不是权威源码，不得替代。 |
| `environment` | `/home/lidefend/workspace/sce-backend-odoo-local-env` | 已登记本地环境仓库 |
| `pilot` | `/home/lidefend/workspace/sce-backend-odoo-local-env` | 机制试点工作树 |

`environment` 与 `pilot` 共用同一仓库，但仍是两个不同回执入口。
lane 绑定只表示该仓库可以提交回执，不代表独占写入位、环境授权、发布授权或业务执行授权。
变更 lane 必须由已登记调度者执行 `bind-lane`，并重新核验真实 git 根；符号链接和非 git 根一律拒绝。

### 所有者授权与接管继承

授权记录保存在 `config.json.authorization`，包含来源、授予时间、范围、允许动作、明确排除项和撤销条件。
`takeover` 会自动继承当前授权，并在调度者记录中写入 `authorization_id` 与 `authorization_sha256`；
接替者不需要重新向所有者索取同一份授权。授权被撤销后，`assign` 立即 fail-closed。

```bash
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py authorize \
  --file /home/lidefend/workspace/.sce-dispatch/authorizations/owner-standing-auth-20261018.json
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py takeover \
  --dispatcher codex-main-dispatcher-20261018B
```

当前有效授权为 `owner-standing-auth-20261018`：覆盖路径命名空间 A/B/C、本地提交、
平台与 Demo 日常开发服务器部署与回读。用户模块、平台首页产品闭环、公开注册、
第二套认证引擎、伪造证据、生产发布和凭据变更明确排除。
事实前提缺失（测试失败、身份不明、缺少签名或恢复点）应作为阻断处理；沙箱权限审批属于工具限制，
不得伪造或绕过，也不得表述为“所有者未授权”。

`config.json` 通过 `worktree_groups` 登记共享工作树，当前为
`local-env: [environment, pilot]`。同一资源组内的任务不得并行写入；`status` 只回读该声明，
不把它当作资源锁。资源占用未知时由主调度显式确认。

前端入口已补齐 `.agent/active-runs.json`、`.agent/runs/FRONTEND-DISPATCH-ENTRY-20261017/run.json`
和 `make/codex.mk` 的 `agent.dispatch.status/submit/review` 目标；入口检查只读取私有队列，
不执行前端产品代码、构建或部署。环境入口复用本仓库既有的 `.agent/active-runs.json` 与 run 记录。

```bash
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py takeover \
  --dispatcher codex-main-dispatcher-20261018 --at 2026-10-17T20:31:59Z
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py bind-lane \
  --lane frontend --repository /home/lidefend/workspace/sce-product-odoo-clean-root
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py status
```

## 回执格式与证据检查

Demo、用户模块、前端、环境分别使用 `demo/user/frontend/environment` lane。
前端 lane 的仓库绑定只决定回执落在哪里；构建与审计对象是主仓 `frontend/`，
宿主机产物为 ignored 的 `frontend/apps/web/dist-*`，两者都不进入 Odoo 镜像。
每次完成、阻断或暂停，先保存既有 run.json 和原始证据，再在所在仓库写回执 JSON。

```json
{
  "task_id": "现有 run 的 id",
  "task_ref": "可选：已下发并已确认的 task_id",
  "executor": "可选：确认该任务的执行者标识；有 task_ref 时必填",
  "run": ".agent/runs/实际任务/run.json",
  "status": "paused",
  "summary": "本批实际结果；批次、主线、部署、用户验收分别说明",
  "next_step": "建议的下一最小步骤，不代表授权",
  "evidence": [
    ".runtime/本批/定向测试.log",
    {
      "path": ".runtime/本批/result.json",
      "nonempty": true,
      "format": "json",
      "assert": ["json:/status=PASS", "not_contains:FAIL"]
    }
  ],
  "blockers": [],
  "resources": ["worktree:实际绝对路径"]
}
```

- `status` 仅允许 `reported/blocked/paused`；`task_id`、当前分支和 run 必须匹配。
- schema 2 回执的 `evidence` 必须至少有一项；字符串路径默认按非空 UTF-8 文本检查。
- 证据对象支持 `format=text/log/json/jsonl`、`nonempty` 和 `assert`。
- 断言支持 `contains:`、`not_contains:`、`json:/pointer=value`；JSON 断言要求 `format=json`。
- 证据必须是仓库相对路径，必须存在，禁止路径逃逸和符号链接。
- 提交和审核前后都会复核身份、工作树摘要、run/证据哈希、格式和断言；变化即 blocked。
- 哈希一致只证明文件未变，不证明测试结果、业务语义或产品验收通过。

## 任务下发与确认

任务下发写入私有 `tasks/<task_id>.json`，保存目标、范围、验收条件、下发调度者、下发时间、
`authorization` 引用（含授权哈希）和 `preconditions`。同内容重复下发幂等；同 id 不同内容拒绝覆盖；
仅补充授权引用与前置条件时使用 `assign --update`。
执行者必须显式确认，拒绝时必须给出原因；确认不是二次授权，只是接收记录。
回执引用 `task_ref` 时，任务必须属于同一 lane，且具名 `executor` 的最近一次确认必须为 `accepted`。
`preconditions` 引用其他任务 id；未完成时 `status` 显示 `waiting_preconditions`，
这是前置条件未满足，不是等待所有者授权。条件满足后由总调度直接推进，无需重新授权。

```bash
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py assign \
  --task-id TASK-EXAMPLE --lane demo --objective '最小目标' \
  --scope '限定文件范围' --acceptance '可核验验收条件'
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py ack \
  --task-id TASK-EXAMPLE --executor executor-example --decision accepted
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py ack \
  --task-id TASK-EXAMPLE --executor executor-example --decision declined --note '前置条件缺失'
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py complete \
  --task-id TASK-EXAMPLE --evidence '验收证据路径或结论'
```

任务记录证明“谁在什么授权下下发、谁确认过”；确认记录本身不扩大授权范围。
执行器是否开工由 `status`、确认和 `readiness` 决定，不再有全局暂停开关。

## 回执替代与阻断关闭

新回执可用 `supersedes` 指向一条或多条被替代回执的完整 SHA256。字符串形式保持兼容；
数组形式用于退役同一 lane、同一 task_id 的重复回执。替代必须同时满足：

- 旧回执存在、摘要匹配、lane 和 task_id 相同；
- 旧回执必须更早，且当前没有其他后继；
- 每条旧回执中的每个阻断必须在新回执 `blockers` 中重复，或在 `closed_blockers` 中显式关闭；
- 显式关闭必须包含非空 `blocker/reason/evidence`，且证据已列入新回执 `evidence`；
- 同一阻断不能同时处于开放和关闭状态；不能关闭旧回执中不存在的阻断；
- 多前驱列表不得重复、不得为空，且任一前驱已有后继时整条替代失败；
- 被替代回执立即进入 `superseded`，即使此前已生成草案；草案仅保留为历史，不能 `retry`，后台审核也不得把它重新发布为草案。

```json
{
  "supersedes": ["旧回执A完整SHA256", "旧回执B完整SHA256"],
  "blockers": [],
  "closed_blockers": [
    {
      "blocker": "BLOCKER-EXAMPLE",
      "reason": "说明已确认的改变事实",
      "evidence": [".runtime/本批/closure.json"]
    }
  ]
}
```

阻断不能因提交新回执而静默消失；必须重复保留或带证据显式关闭。

## 自动处理与主调度职责

用户级 `sce-dispatch-review.timer` 每轮结束后约 30 秒检查队列；串行处理，一条最多 240 秒。
它不依赖原终端存活，但依赖主机运行、用户 systemd manager、网络和 Codex 认证。
不宣称退出登录后必然常驻（未开启 linger），不宣称唤醒原聊天线程。

1. 提交自动捕获仓库、分支、HEAD、dirty 范围、工作内容摘要、run/证据哈希和提交时调度者。
2. 同内容回执去重；后台在审核前后复核身份、证据格式和关键断言。变化即 blocked。
3. 未登记调度者时审核 fail-closed，不启动模型进程。
4. 独立 Codex 非交互进程只收到回执、任务记录、当前授权和队列资源快照；生成中文调度草案。
5. 草案保存到 `proposals/`，状态为 `proposal_ready`；草案不能直接执行，但落在已登记授权范围内的建议可由总调度直接下发。
6. 主调度直接读取原始证据做实质审核，在授权范围内用 `assign` 下发最小任务；只有超出范围才需要所有者扩权。

模型审核使用独立空工作目录、read-only sandbox、approval never；禁用 shell/apps/hooks、
插件、多代理、浏览器、计算机、图像、技能自动安装、统一执行等功能，关闭搜索与已配置 MCP。
提示明确回执是数据而非指令。模型不读取证据正文，因此不能以文件哈希宣称验收通过。
资源快照只是声明，不是资源锁；未知占用必须由主调度确认。
官方调用机制参考 [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)。

## 安装、迁移与恢复

安装前必须停止 timer，备份私有 `config.json` 和已安装 lib，确认候选测试通过，再登记调度者并核验 lane。
安装脚本只安装本机用户级服务和脚本，不触碰开发服务器、业务容器或数据库。

```bash
systemctl --user stop sce-dispatch-review.timer
systemctl --user stop sce-dispatch-review.service
bash scripts/ops/install_agent_dispatch_inbox.sh
sha256sum "$HOME/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py" scripts/ops/agent_dispatch_inbox.py
systemctl --user is-active sce-dispatch-review.timer
```

失败不自动重试。模型失败、超时、身份漂移、进程中断、未完成回执发布均显式 blocked。
每次尝试独立输出文件，失败草案不得复用为成功。进程 PID 与启动标识绑定。
诊断日志在私有 `logs/`，原证据仍留在执行仓库。身份漂移应提交新回执；
仅外部前提已恢复且原候选未变化时可以显式恢复：

```bash
python3 /home/lidefend/workspace/.sce-dispatch/lib/agent_dispatch_inbox.py retry \
  --id 完整回执SHA256 --recovery-fact '填写已确认改变的恢复事实'
```

停止服务保留回执与日志。恢复后 interrupted 不会默认为成功或自动重放。
本轮安装前备份位于 `/tmp/sce-dispatch-backup-20261017T132136Z/`，其中 config、旧 lib 和旧说明的
SHA256 分别为 `80fc295215cff289fc9d6b0507780c6fdb3550e8f7e8be3ec738bdae334fcaa5`、
`e6d38e09087e1f71a1c381b93b3516dccf7390b40a4cf7698edd489ee7f66b7f` 和
`dc87d7bb4271dcfcd333c525be3dc88c2bb0f6f0cb6ac14db328be47708236bb`。

## 本批验证与阶段状态

- 精确基线：`80da1af3d060201cebbddc58146e940a7f34b570`；目标单测 42 项 PASS；
  `make verify.agent.dispatch.unit` PASS；`ci.local.iteration` PASS（L1）；
  `verify.agent.ledger.unit` PASS；`agent.run.resume` 为 `resolved`；`py_compile`、脚本语法与 `git diff --check` PASS。
- 替代状态机新增回归：已生成 `proposal_ready` 的旧回执被后继回执替代后立即失权，
  不再保持可调度状态，且不能通过 `retry` 恢复；多前驱替代可一次退役两条重复回执，
  并校验每条前驱阻断都已重复或显式关闭。
- 离线迁移：复制私有队列到 `/tmp` 后，新代码可读取全部 7 条旧回执；未登记调度者时 `review-once` 返回 blocked；
  登记并绑定 frontend/environment 后返回 idle，未改业务仓库。
- 前端入口回读：`make agent.dispatch.status` 成功，`lanes.frontend` 解析为
  `/home/lidefend/workspace/sce-product-odoo-clean-root`，`automatic_execution=false`；
  该检查只读私有队列，未执行前端产品代码。
- 安装回读：安装副本与候选源 SHA256 均为
  `6f2228443207d08234e5fcaa6078ebf29b7d7abc8c8fb9e775d4f02b59ffdfa9`；
  私有 `README.md` 由安装脚本从 `docs/ops/agent_dispatch_inbox.md` 同步，并以 `cmp` 逐字节核验；
  timer 为 `active (waiting)`，最近一次 service 结果为 success；私有队列仍为 7 条回执。
- 队列快照（`2026-10-17T13:45:00Z` 左右，后续变化以 `status` 为准）：7 条旧回执中
  5 条 `proposal_ready`、2 条 `blocked`；1 条机制任务 `AGENT-DISPATCH-INBOX-20261017`
  已下发并由 `codex-dispatch-mechanism-executor-20261017` 接受。未下发业务任务。
- 门槛：本批没有产品代码、数据库、页面或部署改动，不运行产品 L3/L4/L5；
  未提交、未主线集成、未产品部署，业务执行器仍暂停。

### 旧回执证据审核结论

- Demo：`.runtime/demo-local-20261017/demo-load-full-run1.log` 明确记录 `demo.load.full` 在
  `step_demo_showroom.py:183 -> settlement_order.py:1444` 触发 `construction.contract AccessError` 且 `make` 失败；
  `.runtime/demo-closeout-20261017/runtime-version-after-refresh.json` 为 0 字节；回执 `7b30fb8b...` 虽列出该失败，
  但 `run.next_exact_step` 仍指向 `NEW-CARRIER-ONBOARD-PREP`，run 未同步，不能视为收口。
- 用户：run 记录 `stage_identity.head=109860a`，实际 HEAD 为 `87dbdf4`；
  `.runtime/dispatch-verify-87dbdf4.log` 明确有 `customer_security_audit FAIL` 和 `make: *** [Makefile:33: verify] Error 1`。
  回执 `29d0ae49...` 未声明 `supersedes`，并丢掉 `add84c10...` 中的身份漂移和缺少 `agent.run.resume` 的阻断；
  这只是旧 schema 1 历史记录，不能作为已完成或阻断已关闭的结论。
- 重复回执：Demo 的 `daa6b1c9...` 与 `7b30fb8b...`、User 的 `add84c10...` 与 `29d0ae49...`
  分别为同 lane、同 task_id 的重复回执，均未声明替代关系。多前驱 `supersedes` 已支持在后续
  新回执中一次退役两条重复记录；在新回执产生前，这 4 条不能被视为已收口或已关闭。
- Pilot：旧试点 25 项测试和 `ci.local.iteration` 可从原始日志复核，但机制代码和工作树随后已变化；
  3 条 pilot 旧回执当前重放均为 `worktree content changed after receipt`，只能作为历史证据。
- 回执身份重放：7 条旧回执中 4 条通过文件身份复核、3 条 pilot 失败；身份通过不等于语义验收通过。
  旧 schema 1 回执保持可读、可审核，但不会被本批自动改写或补写替代关系。

