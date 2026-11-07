# CI-SCOPE-01-R1 分类与执行车道闭合

## 身份与边界

- 基线：`b154eae313cf65428d16325b0dfc3faaa68d919c`
- 分支：`fix/fe-loop-02-ci-path-ownership-20261107`
- Formal Product Layer：P4
- Layer Target：CI path ownership、风险车道、ORM runtime 匹配与 workflow sandbox 依赖

本批不修改产品运行时、Renderer、浏览器验收、候选构建或部署。

## 远端失败事实

候选 `c76b008b7dd8aa2ca4e0c62650ef0cc58f7f794d` 的
`professional_quality_checks` 在以下断言失败：

- Gitee Gate Plan 将控制面路径与后端质量工具路径组合误判为
  `standard_backend`。
- 纯 CI 控制面仍被 workflow 的后端业务选择条件带入 ORM/模块套件。
- `scripts/ci/*orm*` 把 `gitee_formal_executor.py` 中的 `formal` 子串误判为 ORM
  输入，导致全量 ORM scope。
- GitHub hosted runner 虽已安装 `bubblewrap`，实际 sandbox 仍不能执行真实
  `bwrap` 测试，说明仅检查版本不等于依赖可用。

`merge_policy_gate` 的失败是精确 HEAD 事实依赖失败后的联动结果。

## 实施与验证

### 分类与执行车道

- Gitee Gate Plan 的高风险后端测试改用真实 `addons` runtime 路径；控制面与后端质量工具
  组合明确断言为 `governance`。
- `backend_runtime_changed` 成为 GitHub professional/merge workflows 与 Gitee Gate Plan
  选择 `standard_backend` 的唯一业务运行时条件。
- `backend_changed` 继续表示后端归属和工具链责任，但不再单独触发业务模块或 ORM。
- 纯 CI 工具链、纯前端工具链、后端质量工具、后端业务运行时和前后端混合五类场景
  同时覆盖分类器、backend impact planner 与正式 gate plan。

### ORM glob 收窄

旧规则 `scripts/ci/*orm*` 将 `gitee_formal_executor.py`、`gitee_formal_queue.py` 和
`gitee_formal_worker.py` 中的 `formal` 子串误识别为 ORM 输入。规则现收窄为：

- `scripts/ci/orm_*`
- `scripts/ci/*_orm_*`

真实 ORM guard 与 frontend fixture ORM entry 仍要求 ORM；formal CI 工具不再要求。

### Bubblewrap 真实依赖

`professional_quality_checks` 不再只检查 `bwrap --version`，而是执行与正式 executor
相同的 `--unshare-all` 最小 sandbox。若 hosted runner 限制 user namespace，则安装
AppArmor 工具并加载仓库内受管的 `deploy/gitee-ci/bwrap-userns-restrict` profile 后重试。
本地真实 bwrap smoke 已通过。

### 本地结果

- `verify.ci.path_ownership.unit`：16 tests PASS。
- `verify.ci.workflow.contract`：402 tests PASS。
- 当前批次 13 个变更路径：`backend_runtime_changed=false`、后端模块不适用、
  `orm_required=false`、普通 PR 有效 professional lane 为 `governance`。
- `make ci.local.iteration`：4 个必需目标全部执行并通过，`notRunTargets=0`，
  `testsRun=true`。
- 执行回执：
  `.runtime/frontend-dev-validation/executions/20261107T124428Z-1008532-491336538/receipt.json`

远端门禁仍待新 HEAD 最终执行。
