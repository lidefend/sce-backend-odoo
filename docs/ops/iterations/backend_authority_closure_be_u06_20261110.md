# BE-U06 Approval Contract Closure

## Scope

本批次从已复审的 `54dbbc1e9ae5864030ea9dfd8cd2b4409ef7f6cd` 继续，验证真实
`tier.review` 任务如何经过当前审批策略、当前身份和原生视图/动作，形成最终
`UiContractV2Handler` 页面契约，再由 `ExecuteButtonHandler` 使用交付动作身份执行并在
服务端重验。

模型级 Odoo ACL、记录规则和业务状态机继续由所属模型负责。本批次只收口这些既有事实
如何进入能力/页面契约、如何被前端消费，以及执行入口如何重验当前事实。

## Samples

| 样本 | 角色 | 已证明的链 |
| --- | --- | --- |
| 付款申请审批（主样本） | 财务审核人 | 真实任务 → 待办 → 最终页面 → 通过/拒绝动作 → reason 输入 → 服务端执行 → 任务与业务状态回读 → 工作列表返回 |
| 日常合同审批（非付款对照） | 财务审批人只有单据读权限 | 同一任务来源执行明确审批方法，不顺带取得合同普通写权限；完成后任务来源消失 |

## Integrated Corrections

| 缺口 | 所属层 | 收口结果 |
| --- | --- | --- |
| `record_button` 未收集、未发送契约声明的动作输入 | P0 `smart_core` + 通用前端运行时 | 前端先收集 `required_params`，后端只接受最终动作规则声明的参数；缺参或夹带未声明参数在执行前拒绝 |
| 工作流动作输入在 V2 投影中丢失 | P0 `unified_page_contract_v2_assembler` | `required_params`、`requires_reason`、`reason_input` 与同一动作身份完成投影，原生 presentation 权威保持 |
| 付款驳回视图仍调用无 reason 参数的 `reject_tier` | P1 `smart_construction_core` | 原生按钮改为现有 `action_approval_reject(reason)`，待办来源授权同步该身份 |
| 财务工作区重新发布 `reject_tier` 旧方法 | P1 业务动作投影 | 业务动作声明的 method 优先；旧别名仅兼容，付款最终契约不再出现 `reject_tier` |
| V2 schema 未声明动作输入字段 | P0 正式契约 schema | 正式 schema、示例摘要与运行时 schema 摘要同源绑定 |

没有新增权限引擎、审批状态机、页面路由或前端业务特判。

## Contract And Execution Evidence

| 层 | 结果 |
| --- | --- |
| 后端 ORM | `verify.approval.contract_closure.orm` 3/3 PASS。真实审批任务、最终 V2 契约和 `ExecuteButtonHandler` 使用同一动作身份；缺 reason 与未声明参数在副作用前返回 400；合法 reason 执行后任务和单据均为 `rejected`；旧动作重放返回 403。 |
| 通用执行边界 | `verify.execute_button.authority.unit` 37/37 PASS。待办来源仍只授权当前任务、当前审批人及明确决定方法。 |
| 前端契约消费 | `verify.frontend.approval_contract.closure.unit` 12 cases PASS。空/取消 reason 请求数为 0；填写 reason 后只发一次 `execute_button`，并携带同一动作身份及 `action_params.reason`。 |
| V2 契约 | assembler/action/status/runtime、schema 与 lifecycle 目标均 PASS；最终动作规则支持声明输入，schema digest 与示例一致。 |
| 增量门禁 | clean HEAD `4e3b66f2c` 上 `make ci.local.iteration` 27/27 个映射目标零退出，零未映射路径。最终 `financial_workspace_contract` 单动作收敛后，按影响面重跑审批 ORM 3/3 与 contract-header 143 checks/cases，均通过。 |

关键原始证据：

- `.runtime/test-baseline/1794315937128907744/odoo.log`（最终单动作收敛 ORM）
- `.runtime/test-baseline/1794315441716950134/odoo.log`（27 目标增量聚合中的 ORM）
- `.runtime/frontend-dev-validation/executions/20261110T125713Z-2307750-553156593/receipt.json`
- `.runtime/final-acceptance/my-work-approval/report.json`

## Browser Journey

最终报告绑定：

| 身份 | SHA / 路径 |
| --- | --- |
| 实际后端产品 | `078d3ed6ae84fa417131c44560d214e40090a7c6` |
| 当前测试脚本 | `078d3ed6ae84fa417131c44560d214e40090a7c6` |
| 前端构建基线 | `078d3ed6ae84fa417131c44560d214e40090a7c6` |
| preview entry | `/assets/index-CqEtIObJ.js` |
| preview entry SHA-256 | `7fc59d9d367ad2799d92a4f3fb7e94f163fa0b41d9991408b871c62cd2657e73` |
| report SHA-256 | `e4084b79adc1c7d4e7840d67fc79ecbd349218474ca0d48eeda1732fe1fe0c44` |

实际用户旅程：

- J07 待办计数、详情往返、提交、公司 A/B/A 隔离：PASS；`todo_before=6`、`initiated_before=7`。
- J08 从真实待办打开审批页，页面显示事项身份和后端金额；从审批页执行通过；`tier.review` 与付款申请回读批准；待办从 8 降至 7。
- 拒绝路径先经过后端声明的安全确认，再打开 reason dialog；空 reason 时请求数为 0；填写后请求使用 `action_approval_reject` 并携带 `action_params.reason`；服务端回读 `rejected`，同记录不再处于 `pending` 审批状态。
- 项目成员无法看到付款事实，直接访问审批记录进入拒绝页。
- 1440×900、1280×800、390×844 均无水平溢出。

未覆盖：

- 非付款对照已完成 ORM 契约与执行闭环，但本轮没有为它增加第二个浏览器页面旅程。
- 付款审批以单一审批级别样本验证；多级审批的中间状态仍由既有流程测试覆盖，不在本批次伪称已做浏览器验收。
- 本结果为候选批次验收，不代表推送、合并、部署或目标生产环境产品交付。

## Exit

- 审批页面、动作、reason 输入和执行目标来自同一最终契约。
- 执行时重新加载契约并重验任务、记录、权限和状态；旧页面不构成执行授权。
- 前端只负责收集声明输入、展示状态和调用执行，没有新增付款或审批业务判断。
- U06 增量已具备冻结和独立只读复审条件。

## BE-CLOSE-01 Cumulative Delivery And PR Preparation

状态：U01—U06 本地实施范围关闭，候选已冻结并完成本地独立复审。GitHub 目标主线在候选
设计基线之后前进了两个提交，当前分支尚未同步，因此 PR 集成准备保持
`verification_pending`；尚未推送、创建 PR、取得远端 CI 或部署。

### Candidate And Commit Inventory

- 设计基线：`1ad805b621de6ced0a497c5a5f6e10bec358896d`
- 当前候选：`94acf7ce6974546ba9415b579e6701dfaaec075d`
- 提交数：30
- 变更文件：107（31 新增、76 修改）
- 审查结论：本地独立复审 `APPROVE`，无 S0/S1/S2

| 切片 | 提交 |
| --- | --- |
| U01 权威映射 | `6bba76043ffdee0474a0f91f3390634c6b792180` |
| U02 授权边界 | `017a395cc55ce91f73cec87d539feec95cb98ad7` |
| U03 能力与入口身份 | `53e949fa0a8dc1c1504ca0bab52bd770b8bbd401` |
| U04 发布与用户投影分离 | `11986acb3d3b4ee677149f05c28d6dbe63c245a5` |
| U05 partner 页面声明 | `f1b9c5997a298d6a8a160c519831167c644ba644` |
| U05B project finalize 迁移 | `8a35c7718b1a39318f89a22587405359c264d225` |
| U05C 两项复审 S1 整改 | `54dbbc1e9ae5864030ea9dfd8cd2b4409ef7f6cd` |
| U06 审批契约与办理闭环 | `f78e3956a`、`bff019bbc`、`375e8551a`、`aee7d6432`、`3f81e67ea`、`a6315c12f`、`a7bb927d6`、`a3001d6f2`、`b074044a9`、`995939bad`、`a2b5a86a8`、`40ad974c8`、`17351a68b`、`ed04063a8`、`9d9da7383`、`cd08cca11`、`ffe91a818`、`4adf8b874`、`4e3b66f2c`、`1eab2fd57`、`078d3ed6a`、`2fb80a110`、`94acf7ce6` |

### Closed Findings And Product Changes

| 范围 | 收口结果 |
| --- | --- |
| 两项 U05 复审 S1 | 未知/遗留能力行不再默认成为业务能力；页面声明对照经真实 `UiContractV2Handler` 最终契约验证。关闭提交为 `54dbbc1e9`。 |
| 授权边界 | 配置管理员只在显式配置 intent 保留职责；普通业务、付款和审批命令仍要求对应业务组、任务来源、ACL、记录规则和业务范围。 |
| 能力身份 | `business_capability` 与菜单派生 `entry_compatibility_alias` 分离；旧键保留，但不再证明能力资格。 |
| 发布与启用 | 场景版本冻结产品定义，运行请求按当前用户重新投影；企业启用只收紧交付范围，不授予业务权限。 |
| 页面声明 | partner sparse field policy 和 project 原生页面退出目标 finalize 结构覆盖；兼容路径保留并明确范围。 |
| 审批输入与执行 | 同一动作身份贯穿最终 V2 契约、前端输入收集、`execute_button` 参数重验和唯一业务方法；付款通过／驳回闭环已验证。 |

### Verification Scope

| 验证层 | 结果 |
| --- | --- |
| 静态／单元 | U01—U05 既有定向守卫、能力身份、授权、页面声明和前端运行时检查均由原批次记录承接；U06 新增审批前端契约 12 cases、执行边界 37/37。 |
| ORM | U05 partner/project 最终契约用例通过；U06 付款与日常合同真实 `tier.review` 审批 3/3 通过。 |
| 浏览器 | 付款审批 J07/J08、页面通过、reason 驳回、任务／单据回读、返回工作列表、公司隔离、项目成员隔离和 1440×900／1280×800／390×844 通过。 |
| 独立复审 | U01—U05 累计复审承接此前结论；U06 最终增量本地独立复审为 `APPROVE`。 |
| 远端 | 未推送、无 PR、无远端 CI、无合并或部署。 |

### Runtime Evidence Carry-Forward

浏览器报告实际绑定后端产品、前端构建基线和测试脚本
`078d3ed6ae84fa417131c44560d214e40090a7c6`。当前候选 `94acf7ce6` 相对它的差异是
本文件和上游详情回读断言合并；产品运行时输入未变：

```text
git diff --name-only 078d3ed6a..94acf7ce6
docs/ops/iterations/backend_authority_closure_be_u06_20261110.md
scripts/verify/frontend_my_work_approval_browser.mjs

git diff --quiet 078d3ed6a..94acf7ce6 -- \
  addons frontend make contracts config docs/architecture
runtime_inputs_equal=yes

addons tree:   68d5f9e2405d8ea05c5f63fb3f82235d59a6c030 (both)
frontend tree: 3285fabf65697b100796c4fac8a475f5ae1b106c (both)
```

`078d3ed6a` 的产品行为证据仍可承接；新增的上游详情金额断言尚未在当前候选重跑，待 GitHub
主线同步后与受影响审批旅程一起验证。该差异不触发后端重建、发布快照刷新或夹具全量重置。

### Target Main And Publication Preparation

用户明确目标为 GitHub：

- 实时目标：`origin/main = fb5f5c82fe7404939cd697ea99e1f2ba237b0310`
- 设计基线 `1ad805b62` 同时是当前候选与目标 main 的合并基点
- 候选相对目标：29 个独有提交；目标相对候选：2 个独有提交
- 只读 `git merge-tree --write-tree origin/main HEAD` 返回冲突
- 冲突路径：`.agent/active-runs.json`、覆盖率注册表、复杂度预算、拆分队列、审批浏览器脚本
- 前四类属于 run 合并与可再生成证据；审批浏览器脚本同时承载上游详情金额回读和 U06 页面办理，需要语义合并后重验
- 当前未纳入的 GitHub 主线提交为 `d014af2e8`、`fb5f5c82f`，其改动包含能力加载性能、前端用户流程及浏览器消费检查

目标同步必须使用 `workspace.branch.sync-main.extended`。当前候选有 30 个本地提交，超过
普通入口的 12 提交上限，因此需要仓库所有者对该精确提交数和受影响冲突处置作出明确授权；
不得裸 merge/rebase，也不得把旧候选的浏览器结果直接标成同步后结果。

Gitee 的 `main=2fb35361342399cc6404dbde066e346ece91213d` 仅作为补充观察，不是本次
GitHub PR 目标。基于 Gitee 旧 refs 生成的公开扫描结果不用于 GitHub 发布判断。

发布前只读检查：

- `make verify.pr.push.unit`：18 个 push 隔离场景 PASS
- `make ci.delivery.freeze.prepare`：PASS，无生成差异

`public_guard`、`merge_policy_gate`、`professional_quality_gate` 和
`frontend_release_gate` 尚未运行，因为尚无远端 PR；它们是 PR 集成门禁，不由本地
`APPROVE` 替代。

### Preserved Limits And Rollback

- 非付款审批只完成 ORM／契约闭环，未做独立浏览器旅程。
- 多级审批中间态未做浏览器验证，不能表述为全部审批流程已交付。
- `construction.menu.*`／`catalog.menu.*` 旧键、数据库能力目录迁移、非原生兼容路径和
  无调用方包装函数继续由既有台账管理，不在本卡扩大清理。
- 代码回退只回退对应模块、契约 schema 与前端消费提交；不回滚审批业务数据、审计记录、
  发布版本或企业启用数据。数据库迁移和发布内容如需回退，按各自恢复入口另办。

外部边界：当前保持未推送、未创建 PR、未合并、未部署。

## BE-CLOSE-01 GitHub Main Synchronization Result

GitHub 主线同步已通过受管 `workspace.branch.sync-main.extended` 完成。同步前候选为
`9cba692c0ec24038a11dda5763c1be0f857533ec`，预同步 Quick 回执有效；目标
`origin/main=fb5f5c82fe7404939cd697ea99e1f2ba237b0310` 已通过 rebase 成为当前候选祖先。
同步时生成了恢复 bundle：

```text
/home/lidefend/workspace/sce-backend-odoo/.git/codex-recovery/branch-sync/
  codex-be-u05-page-declaration-authority-20261110-9cba692c0ec24038a11dda5763c1be0f857533ec.bundle
```

实际冲突处置保持精确语义：

| 路径 | 处理 |
| --- | --- |
| `scripts/verify/frontend_my_work_approval_browser.mjs` | 保留上游 `approvedForm`／`approvedAmountField`／`cross_page_readout` 和 U06 页面审批、reject safety、`action_approval_reject`、`action_params.reason`；最终文件与预同步候选逐字节一致。 |
| `.agent/active-runs.json` | 按分支键三方合并。 |
| `scripts/ci/personal_data_false_positives.json` | 按精确 `(rule_id,path,blob_id,classification)` 并集；同一精确键仅 reason 文案并行时保留主线措辞。 |
| 覆盖率、复杂度预算、拆分队列 | 使用主线版本完成历史重放，再由正式生成器重建。 |

同步工具本身的原生 P4 收口提交包括：

- `fdec0454a`、`787de12de`、`8ec36dcaf`、`9cba692c0`：审批脚本语义并集、精确扫描豁免并集、逐路径责任身份和受管生成器边界。
- 同步后治理更正 `5cf3b42c3`：更新 rebase 后 run baseline／scope，登记主线新增测试组和验证目标，移除已完成上游 run 的索引项，并为 `frontend_dev_incremental` 的实际消费者补足新主线目标预期。
- 生成提交 `0f1960897` 重新生成覆盖率、复杂度预算和拆分队列。

### Post-Sync Verification

| 验证层 | 当前精确结果 |
| --- | --- |
| 增量执行 | `make ci.local.iteration` PASS，执行 34/34 个映射目标，零未映射路径；receipt：`.runtime/frontend-dev-validation/executions/20261110T163329Z-87345-216479830/receipt.json`。 |
| 审批 ORM | `verify.approval.contract_closure.orm` PASS 3/3。 |
| 能力／场景 | `verify.daily.permission_truth.capability.orm` PASS 13/13；当前验收库已升级 `smart_core`、`smart_construction_core`，依赖链同时重新加载 `smart_construction_scene`。 |
| 前端审批契约 | `verify.frontend.approval_contract.closure.unit` PASS 12 cases；执行边界 37/37；canonical presenter、contract header、incremental unit 111/111 均 PASS。 |
| 浏览器 | `verify.frontend.my_work_approval.browser` PASS。付款通过、页面驳回 reason、任务／单据回读、工作列表更新、公司隔离、项目成员隔离及 1440×900／1280×800／390×844 均 PASS。 |
| 当前运行身份 | 后端、前端、测试脚本和浏览器报告均为 `5cf3b42c3c838b6e28651245c5c46d4a5ca98f19`；数据库 `sc_frontend_acceptance`。 |
| 浏览器报告 | `.runtime/final-acceptance/my-work-approval/report.json`，SHA-256 `b26f89c4720b80c835e978a55e0239c023872202146389458ed4736596086d5b`。 |

验收旧后端由受管 `backend.acceptance.up` 按同步候选重建为不可变 Git artifact；既有验收库通过
登记模块升级更新。因历史 rollback custody 容器仍被有意保留，未执行会删除这些恢复凭据的
baseline rebuild。前端 release 产物和 standard preview 身份均重新绑定到当前候选。

### Current Candidate And Integration Boundary

- 设计基线：`1ad805b621de6ced0a497c5a5f6e10bec358896d`
- 同步后候选：`5cf3b42c3c838b6e28651245c5c46d4a5ca98f19`
- 相对 `origin/main`：32 个提交、113 个变更路径
- `origin/main` 是当前候选祖先；`main_only_commits=0`
- U01—U05 的原 `APPROVE` 仍作为历史承接；同步增量与 P4 收口尚待本卡结束后的只读独立复审
- 远端分支仍不存在，无 PR、远端 CI、合并或部署

外部边界仍为推送前停止。下一停点是 `ci.delivery.freeze.prepare` 和同步增量只读复审，不是继续
增加产品功能。

### Independent Review Remediation

首轮同步增量只读复审结论为 `REQUEST_CHANGES`，没有发现审批业务回归，但指出两项证据／工具边界：

1. 之前引用的 34/34 增量回执产生于 `0f1960897` 的脏工作树，不能代表后续 clean HEAD。
2. 审批脚本语义并集只验证关键字符串，未证明 `new_main` 对该文件的全部新增行均被保留。

两项已按复审要求修正：

- `ecbd2a537` 在 `safe_branch_sync_main.py` 中新增主线新增行集合校验；只有 `new_main` 相对
  replay base 的每条新增行都在当前候选最终文件中存在，且关键审批行为标记同时存在时，语义并集
  才可放行。
- 在 clean HEAD `ecbd2a537d3b1e94c193cd7ed8a6bf12ef7397d0` 上重新执行
  `make ci.local.iteration`，34/34 映射目标 PASS，零未映射路径。新回执：

```text
.runtime/frontend-dev-validation/executions/
  20261110T170348Z-276355-687099407/receipt.json
```

该回执绑定 clean 候选和当前 runtime tree；S2 修改仅属于 P4 同步/验证工具，不改变
`addons`、`frontend`、产品契约或审批执行链，因此 `5cf3b42c3` 上取得并在
`e4e1bd2ef` 文档提交后承接的审批浏览器报告仍有效。
