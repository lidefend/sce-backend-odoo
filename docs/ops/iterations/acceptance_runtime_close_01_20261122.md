# ACCEPTANCE-RUNTIME-CLOSE-01-20261122

## 结论边界

本批是 P4 验收运行工具收口，不是产品前端整改，也不代表 R09 产品验收通过。
R09 的最终业务结论保持为 2/4 完整流程 PASS、2/4 FAIL；本批只处理运行身份、
备份写入者、回滚容器识别和验收声明中的工具缺陷。

## 精确身份

- 产品基线：`fe635515dda270ed230d07a77ed4bcc9ab4fe5ac`
- P4 初始候选：`299f9b6266ab238380fc1749f589f1e6712aa3c9`
- 工作分支：`audit/FE-RUNTIME-RESEARCH-01-R09-20261122`
- 产品源码增量：`addons/`、`demo_addons/`、`addons_external/` 与
  `frontend/apps/web/src/` 相对产品基线为零
- 验收环境：`local/sc-fe-r2-p1-01/sc_frontend_acceptance`

主线在首次发布尝试前前进到 `cb182c9e94abe515b0d987fc514bc46ca98d1cfb`。
候选已通过 `workspace.branch.sync-main` 重放到该精确 main，重建生成报告后的新
HEAD 为 `638f9a9599b9c299148dd34b0ca745c2b7d81b34`。旧
`873a8091ef0560b360efd0fa3efe2c4fc1f566b3` 仅保留为被同步取代的本地身份，
不能用于复审或发布。

## 层与范围声明

- `Formal Product Layer`: P4 ops delivery tool
- `Layer Target`: acceptance runtime identity, backup writer selection,
  recovery-custody classification and acceptance contract declaration
- `Module`: `config/acceptance`, `scripts/dev`, `scripts/verify`,
  `docs/engineering_convergence`
- `Standard vs User-Specific`: ops delivery tool
- `Why Here`: 这些变更只影响验收构建、启动、备份、恢复审计与验证
- `Why Not Elsewhere`: 不改变产品契约、权限、模型、业务状态或前端执行语义
- `Blast Radius`: 验收候选身份、数据库备份写入者、恢复审计容器分类、
  验收契约能力声明；不写业务数据、不重建数据库、不重新运行 R09

## 进入本批的候选改动

1. `299f9b62` 已建立运行身份绑定和规范数据库写入者选择。
2. 后续未提交 P4 收口补齐验收契约已经使用的
   `view.pivot.v1`、`view.graph.v1`、`view.calendar.v1`、`view.gantt.v1`、
   `view.activity.v1`、`view.dashboard.v1` 能力。
3. 恢复审计只排除“已停止、名称精确匹配
   `sc-backend-odoo-acceptance-rollback-*` 的 one-off Odoo 回滚载体”；
   运行中的或命名不同的额外消费者仍 fail-closed。
4. 修正 carrier discard 对当前 profile 字面量的陈旧断言。
5. 将验收运行启动、baseline rebuild 及三个相关测试登记到增量验证路径映射，
   修复 `ci.local.iteration` 因 5 个已改动 P4 路径未映射而 fail-closed 的工具缺口。
6. 新增轻量 `verify.acceptance.runtime.tooling.unit`，承载上述工具的真实非零单测；
   完整 `verify.acceptance.runtime.baseline_rebuild.unit` 继续由该轻量目标组成。
   这样开发增量车道不会选择名称含 `build` 的候选专用目标，也不放宽其禁令。
7. 保持 `verify.acceptance.artifact.unit` 的显式目标引用；
   `backend_acceptance_up.sh` 和 artifact 测试路由到该目标，其余验收运行工具路由到
   轻量 tooling 目标，避免重复执行并保持验证面基线不增长。
8. P4 runtime 从 sibling worktree 启动时发现旧 `frontend_build_sha256` 把
   `../<worktree>` 路径段计入摘要；现已改为进入 dist 根目录后对 `./` 内容求哈希，
   并增加“不同 worktree 路径中相同内容得到相同 digest”的回归测试。
9. 独立复审 S1：外部传入的 `FRONTEND_BUILD_SHA256` 过去可绕过 dist 绑定。
   现在只要 `index.html` 存在就始终重算 observed digest；传入值不一致立即拒绝，
   且在任何 Docker mutation 之前失败。
10. 独立复审 S2：dist 文件顺序固定为 `LC_ALL=C sort -z`，消除 locale 依赖。
    artifact 目标现有 12 个非零测试。

## 门禁责任

| Gate | State | Owner target / reason |
| --- | --- | --- |
| exact base/head identity | required | git preflight |
| owning module baseline | excluded | P4 tooling has no Odoo runtime behavior |
| existing affected tests | required | registered P4 unit/environment/recovery targets |
| focused changed tests | required | baseline rebuild and carrier discard units |
| contract/schema consumer | required | acceptance environment guard |
| frontend lint/type/build | excluded | no product frontend source delta |
| browser journey | excluded | no product behavior delta; reuse R09 evidence, do not relabel |
| remote required gates | required after publication | exact-head GitHub PR |

## 验证状态

已通过：

- `verify.acceptance.runtime.baseline_rebuild.unit`：
  81 + 10 + 129 个测试通过，验收环境 source guard PASS。
- `verify.frontend.acceptance.environment.guard`：
  63 个测试通过；15 个只读运行身份凭据确认案例通过。
- `acceptance.runtime.baseline_recovery.audit` 只读审计：
  profile=local，project=`sc-fe-r2-p1-01`，
  database=`sc_frontend_acceptance`；fixture 分类和卷挂载审计 PASS，
  未执行数据库或文件系统修复。
- 首次 `ci.local.iteration`：前置静态和前端治理门禁通过，随后因 5 个 P4
  验收工具/测试路径未登记影响映射而 fail-closed；归类为验证工具缺口，
  不是测试失败，也没有跳过。
- 路径映射修正后又由验证面基线拦下 `verify.acceptance.artifact.unit` 的
  零引用增长；最终恢复显式引用，并拆分 artifact 与 runtime tooling 两个
  轻量目标，保持验证面范围不变。
- 最终 `ci.local.iteration`：8/8 required targets 通过，`unmappedPathCount=0`，
  `testsRun=true`，trusted scans 完成，验证面处于冻结基线内。
  原始 receipt：
  `.runtime/frontend-dev-validation/executions/20261122T033231Z-1619625-646681715/receipt.json`
  （SHA256 `c6d796774ef1b495052822fad0df2f7292e4ff8a6fbe39cc3c0487657633f48e`）。
  执行目标测试数为 10、129、18、67、19、40、63、208。
- R2 clean HEAD `0dfe3d4dd` 的最终增量回执为
  `.runtime/frontend-dev-validation/executions/20261122T042330Z-1914635-330298370/receipt.json`
  （SHA256 `b6888f348dd50b7842bbf008c41b93cfcc2c8f027a5dd065665d447e8dfe4ecc`）。
- `ci.delivery.freeze.prepare` 连续两轮 PASS；generated reports current，
  frontend contract basis open defects=0，list-surface evidence bindings valid。
- `frontend_acceptance_baseline_rebuild.sh` 最终为 499 行；本 P4 收口没有
  新增复杂度拆分项。

候选现进入 `verification_pending`：待 clean commit 后取得精确 HEAD 独立复审、
发布独立 PR、完成精确 HEAD 远端检查和 pending merge decision。未执行项不会在这里记为通过。

## 回退

回退本批 Git 提交及 `.agent` 运行元数据即可。产品源码和
`sc_frontend_acceptance` 数据库不因本批回退而改变。
