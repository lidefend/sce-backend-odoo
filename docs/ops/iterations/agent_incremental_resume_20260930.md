# P4 增量续跑闭环 — 2026-09-30

唯一结果索引：`.agent/runs/P4-INCREMENTAL-RESUME/run.json`；工具回执位于当前工作树 `.runtime/agent-runs/P4-INCREMENTAL-RESUME/`。

## 边界与基线

- 分支 `fix/agent-incremental-resume`，基线 `818d7c7fe316e8ce6c2e4f3ccd6354d23c5f4064`，开工 clean。
- 独立受管工作树 `sce-backend-odoo-agent-resume`。原产品工作树保留；本批不争用业务运行环境，不改业务源文件，可独立验收与回滚。
- Formal Product Layer：P4；Layer Target：执行状态、增量建议和 checkpoint；Module：`.agent`、`scripts/ops`、`scripts/verify`、对应 Make 入口。
- Standard vs User-Specific：通用交付工具机制；Why Here：执行状态与证据复用属于 P4；Why Not Elsewhere：不向产品契约、前端呈现或数据库加入执行规则。
- Blast Radius：本地建议和恢复提示；不执行历史命令，不放宽发布门禁，不安装控制器服务。
- L0：每日 HEAD + dirty；L1：`make ci.local.iteration`；L2：resume/planner/controller 离线非零定向测试。L3/L4 不适用（无业务或运行环境改动）；L5 本地独立复核，未请求发布，远端门禁不执行。

## 结果

批次验收完成。统一入口已进入 AGENTS、工作流、日常 L1 和控制器 launch/resume；原工作树没有修改。

| 层级 | 命令／观察 | 结果 | 原始证据（相对本工作树） |
| --- | --- | --- | --- |
| L1 | `make ci.local.iteration` | passed，16 项政策测试；范围 26 路径，未扫描整个分支历史 | `.runtime/agent-runs/P4-INCREMENTAL-RESUME/iteration.log` |
| L2 | `make verify.agent.resume.unit` | passed，30 项 | 同目录 `resume.log` |
| L2 | `make verify.frontend.dev.incremental.unit` | passed，19 项 | 同目录 `planner.log` |
| L2 | `make verify.codex.agent_controller` | passed，37 项及 shell/service 静态校验 | 同目录 `controller.log` |
| 批次行为复核 | 实际本分支 `--plan-worktree` | 3 个 reusedTargets、targets=[]、testsRun=false；没有重跑已通过检查 | 同目录 `reuse-plan.log` |
| 独立复核 | B 线只读复核与定向复核 | 初审 3 项 P2 已全部关闭，无剩余阻断 | 同目录 `independent-review.md` |

测试候选为上述基线 + 本批声明 dirty 范围；三份结构化回执记录源 HEAD、dirty、输入摘要、日志摘要及耗时。
首轮 25/16/37 的日志保留为 `*-first.log`；后续共享工具修复使相关输入失效，因此只重跑受影响的三组工具测试。
收口仅修改目标、run 状态和本记录；它们不改变三组测试的声明输入，结果按影响分析保留，不为了提交身份重复运行。

## 已设置的统一机制

- 分支直接映射到一个 run；首次登记与续跑分开，不再默认进入已完成历史前端计划。
- 所有执行器遵循同一入口。ci.local.iteration 对缺失／非法 run 拒绝；控制器只附加上下文，不执行历史动作。
- 日常差异以批次基线计算，包含已提交、暂存、未暂存、未跟踪及重命名两端；整个分支比较需显式选择。
- 执行前 begin 记录依赖；执行后 record 拒绝期间输入漂移、零测试或缺失日志；证据变化按项失效。
- 复用建议、待运行与未变失败分开；终态任务不能继续 begin/record；根目录和内部状态不能作为递归依赖。
- 官方接管任务登记指向现有批次记录第 32/35/36/37/38 段，保留最新已知缺口；不导入旧结果为当前通过。

## 完成边界与后续

- 本地批次：完成；主线：未集成；运行控制器：未安装新版；产品部署／用户交付：不属于本批。
- 所有执行器的统一规范已在本候选实现；其他工作树及运行中的服务要在正常集成／安装后才消费新版本，不能宣称当前已全局启用。
- 本地回执是执行器对实际日志与测试数的声明，不是防恶意执行器的认证，也不替代 CI。工具无法强制约束绕过受管入口的任意外部命令。
- 自动复用只覆盖声明的离线依赖与环境；依赖遗漏必须补齐并使对应结果失效。运行环境证据始终要求既有受管回读，不自动继承。
- 回滚：撤销本专题责任提交；无数据库或服务变更，原产品工作树保留。
- 下一步：本地责任提交完成后等待受管主线集成／服务更新车道；原产品任务按其 run 的具体未闭合项继续，不重做全仓盘点。

## GitHub 独立主线集成阶段

用户要求产品分支继续开发、本批只集成智能体协作优化。新分支 `fix/agent-resume-mainline` 以 GitHub main `72ad88e6949508f3760a15101d61f288c7cf70d9` 为基线，复用已完成历史恢复的工作树；原 `fix/agent-incremental-resume@44429fd7` 保留冻结只读。只提取该提交的 P4 差异，不携带其前置产品历史，不登记仍在开发的 WEB 任务，不修改产品工作树。
原表中的通过结果仅为来源批次记录，不冒充当前主线候选证据。当前 run 已绑定新分支与基线并重新开启集成阶段。L1：iteration；L2：resume/planner/controller 三组工具测试；L3/L4：无业务运行环境变化，跳过数据库、浏览器和服务安装；L5：独立审查、生成证据、冻结 Quick、GitHub 四门禁和受保护 Merge commit。
Formal Product Layer=P4；Layer Target=统一执行上下文与增量验证；Module=.agent/控制器/验证工具/Make；属于通用工程机制，不包含 P0-P3 业务语义。回滚为独立回退本 PR，无数据库恢复事项。当前状态 verification_pending。

新基线结果：L1 16 项通过；L2 resume 30、planner 17、controller 37 全部通过（planner 另两项仅存在于未集成产品前置分支，本批不导入）。实际 begin/record 后，三个目标均 reusable、targets=[]、testsRun=false；只读续跑没有再次执行测试。当前候选批次验收通过；主线集成待冻结 Quick 和新 PR 检查。
生成准备通过：7 项组件检查和全部报告 current；生成差异仅新增工具/测试对应清单及行数。未修改产品源、安装控制器服务、运行数据库或浏览器。新基线验证日志位于本工作树同名 .runtime 目录；旧工作树原日志保留。

### 可信历史扫描复用补齐

用户指出最终 Quick 仍重复无关全扫。已取消 `81788ca9a` 的 Quick（无回执）；旧日志保留为 `quick.log`。根因：回执生产者使用 linked gitdir，消费者仅查 common-dir；整份 make/ci.mk 比较又把无关 L1 接线视为所有扫描权威变化。
本批新增 P4 修复：仅发现同一 common-dir 的 Git 登记工作树回执，继续校验完整 payload/head/tree/main 祖先，不复制或制造回执；Make 只忽略唯一静态 ci.local.iteration 规则，其余所有入口、变量、依赖和调用保持比较。缺失、重复或动态规则失败关闭。
helper 的检测/覆盖代码、scanner/policy/例外名单与 producer 权威继续校验；回执查找的兼容转换绑定精确已审阅旧/新 AST 摘要，任何未登记的未来信任校验变化都失效。首次复核发现按函数名永久排除过宽，已用精确迁移对与负例关闭。
33 项扫描复用/秘密扫描测试通过，实际三类扫描均找到真实 `83ba6406` Quick 回执，对等树 main `72ad88e6` 使用 incremental；历史检查结果 `reachable_scan=trusted_base_incremental`，仍扫描每个候选中间提交和新路径出现的旧 blob。实际增量日志为 `incremental-public-scans.log`，选择记录为 `trusted-scope-plan.log`。
Make alias 改变声明输入，已只重验受影响的 30/17/37 工具测试；不重做业务验收。最终 Quick 必须针对新冻结候选，但已验证主线历史不再全扫。远端 runner 无本地可信回执时仍执行其必需检查，不能把本地复用声明冒充远端通过。
