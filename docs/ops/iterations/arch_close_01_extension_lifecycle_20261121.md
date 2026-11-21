# ARCH-CLOSE-01 R2 — Extension Lifecycle 与基线债务整合

## 当前裁定

2026-11-21：R2 实现与本地验证完成，待新 HEAD 的远端 CI 和独立只读复审。
不作合并批准；未合并、未部署、未迁移持久库或客户数据。

同一 PR #953、同一 feature 分支；原评审 HEAD 为
`b2586f40e96bf0bbba7d1d5e261c6155318f2120`，base 为
`09be7ab696bb9201efe1cdd66c22ff8e3c3d6d88`。以下回执绑定该父提交加显式
R2 工作树源码；冻结后的提交身份以 PR HEAD 和本轮发布回读为准。旧 HEAD 的远端结果
不能作为 R2 通过证明。当前 run 是唯一结果索引：
`.agent/runs/ARCH-CLOSE-01-EXTENSION-LIFECYCLE/run.json`。

## 最终实现及边界

- **P0 生命周期**：服从 Odoo 17 Registry.ready 与 _init_modules。在 Registry
  构建中，只允许已安装且完成加载的 Provider 贡献，不缓存不完整上下文；正常运行期
  保留配置启用与已安装双重校验。未通过吞掉异常、全局放宽状态或第二套生命周期管理器修复。
- **P0 启用授权**：名单仅来自 ir.config_parameter；Loader 忽略 Context 名单，
  请求路由移除该 Context 键。已安装的 Owner 模块也不能因请求伪造名单而获得执行权。
- **P0 Hook 合同**：共享 system-init 数据按声明顺序处理，公共消费者统一走 run_all
  入口；Handler 重复替换或删除明确失败，模块名单反转不改变结果。保留 Registry 专属
  不可变 Handler Mapping、多数据库隔离、三个 ordered_merge 和 identity 唯一所有权。
- **P1 产品启用**：Core 新安装仅声明自身，完整组合由 Bundle 声明。已有数据库中的旧
  noupdate 配置不被静默重写；若其声明仍含未安装模块，运行期继续明确拒绝，另行走所有者
  确认的精确数据库配置修订。本轮不执行该持久数据操作。
- **P0/P1 实际基线修复**：原生按钮身份合并、Odoo 17 Ribbon 文字、低代码权限/原生视图
  绑定校验、无 HTTP 请求时的平台身份解析、声明式默认产品和企业启用命名空间、备用金
  业务搜索视图、Scene Registry 初始化入口来源。组装缓存按现有机制提升到 v96，并绑定
  全部输入摘要，确保修复不会被旧缓存遮蔽。
- **测试基线修订**：使用当前入口命名空间凭据、已注册合成业务公司及实际工作流前提；
  保留跨公司、越权、超限和终态事实不可变负例。企业初始化旅程与 Scene 所属规则在 Scene
  套件验证；Core 独立安装不再错误加载 Scene 规则。权限矩阵文档同步，不改变业务 ACL。
- **P4 范围**：脏回执跨 HEAD 复用要求运行输入一致；62 个已有基线路径显式映射到所属模块
  基线，未知路径仍拒绝。完整运行依赖登记包含本地模块闭包、OCA、运行器、文档/schema 和
  数据范围声明，生命周期额外包含 Owner。Core 基线显式使用 Core-only 模板。8 个临时
  定向包装入口在完整基线覆盖后退役，原始证据保留；零引用上限从 673 收紧到 671。
- **P4 远端执行**：复用现有 CI dependency_baseline 准备器，为 smart_core 生命周期矩阵
  准备无测试污染的辅助模板，严格绑定 CI run/attempt/shard、SHA、Compose 项目和临时库。
  正常 smart_core 目标仍全新安装；准备成功后才开启矩阵。不豁免 changed-test coverage。

## v96 最终完整 ORM 结果

| 必需范围 | 实际执行 | 结果 | 原始回执目录 |
| --- | ---: | --- | --- |
| smart_core 完整模块 | 697 | PASS | `.runtime/test-baseline/1795270208817140648` |
| Construction Core 完整模块（Core-only） | 1487 | PASS | `.runtime/test-baseline/1795269498057372126` |
| Scene 完整模块 | 18 | PASS | `.runtime/test-baseline/1795270133197296308` |
| 真实双数据库生命周期矩阵 | 2 | PASS | `.runtime/test-baseline/1795269072352920467` |

完整模块与生命周期合计 **2204 项通过**，均 source_unchanged=true、cleanup=absent。
原始日志为目录下的 odoo.log，执行/清理详情为 receipt.json。生命周期覆盖 Core-only、
完整 Bundle 安装、Core/Scene 单独升级、已启用扩展卸载、Registry 重建、模块顺序反转、
双数据库隔离及 Context 伪造负例；测试在退出时回读临时库已不存在。

## v96 定向消费补充证据

以下与完整基线存在重叠，不重复计入 2204：

| 既有入口 | 实际执行 | 原始回执目录 |
| --- | ---: | --- |
| `verify.extension.runtime_context.orm` | 6 | `.runtime/test-baseline/1795269362962969991` |
| `verify.extension.native_alignment.orm` | 4 | `.runtime/test-baseline/1795269353220081364` |
| `verify.extension.hook_authority.orm` | 4 | `.runtime/test-baseline/1795269056772685425` |
| `verify.admin_close_01.runtime.orm` | 4 | `.runtime/test-baseline/1795268881355103469` |
| `verify.daily.permission_truth.capability.orm` | 80 | `.runtime/test-baseline/1795268931586360530` |
| `verify.page.finalize.authority.orm` | 1 | `.runtime/test-baseline/1795269387020237504` |
| `verify.page.project_finalize.authority.orm` | 1 | `.runtime/test-baseline/1795269405686221518` |
| `verify.scene.company_route_scope_cache.orm` | 8 | `.runtime/test-baseline/1795269418657149068` |
| `verify.smart_core.intent_smoke.orm` | 10 | `.runtime/test-baseline/1795270446490905419` |

所有 runtime 回执经 agent.run.begin / agent.run.record 绑定声明输入和原始日志。
测试环境沿用 sc-local-test/sc_test；生命周期仅使用已登记的 sc_test_arch_* 临时克隆。
没有客户库或持久产品发布快照操作；发布/回滚测试夹具均随测试事务回滚。

## 离线及增量门禁

- 30 个选中的离线入口通过，原始日志在当前 run 目录的 r2-offline-*。
- 增量执行器 206 项单测通过；CI 模板准备器 10 项单测通过。
- 缓存组装、名称绑定、平台架构、CI workflow contract、Hook、消费路径及验证车道检查通过。
- **ci.local.iteration：PASS（exit 0）**；36 个实际执行入口，无未执行必需目标。
  聚合回执：`.runtime/frontend-dev-validation/executions/20261121T134758Z-1424600-110210034/receipt.json`。
  完整门禁日志：`.runtime/agent-runs/ARCH-CLOSE-01-EXTENSION-LIFECYCLE/r2-local-iteration4-v96.log`。
  公开扫描已执行，未沿用无权威依据的旧扫描结果。
- 早期失败和 v95 回执仅作诊断历史，不能替代上述 v96 结果；临时定向入口定义保存在同一
  run 的 ignored retired-focused-checks.json，不建立第二份结果台账。

## 尚待完成及回滚

推送 clean 新 HEAD 后验证全部必需远端 CI，随后交独立审查者只读复审。
本地通过不代表远端、主线集成、部署或用户验收完成。无前端源码变更，本轮不新增浏览器矩阵；
远端正式前端门禁仍须满足。回滚以有界 P0/P1/P4 修订为单位，不涉及客户数据恢复。

提交钩子按既有流程刷新测试覆盖清单、复杂度报告及拆分队列三份生成报告，已纳入 scope；生成器未产生额外产品源码变化。

## Exact HEAD 16b5eb3 remote follow-up

Remote public, release-candidate and frontend gates passed; professional backend suites failed. The two native lifecycle tests executed without the original Registry initialization failure. Fresh module installation exposed baseline test ownership and fixture assumptions hidden by local Bundle templates. Seventeen UM-P1/P2/P3 industry ORM families move unchanged to Construction; four runtime extension consumer classes now use Odoo post_install. Scene fixtures explicitly enable installed providers via database configuration. Platform and Scene full baselines now use their respective module templates.

A separate P0 defect lost applied configuration provenance in native form structure projection when no industry override was present. The final native carrier now retains the actual resolved configuration rows; no preview validation is relaxed. Cache version v97 binds the correction. Standalone smart_core change-set preview/publish/rollback suite: 31 passed, original receipt `.runtime/test-baseline/1795271774822517808/receipt.json`. Full owning-module revalidation and a new exact-head remote run remain required.

## R3 hotfix — third-party run-all providers

The final prefix validated against `cae4c5ac` exposed one contract regression: known
Provider ordering was explicit, but the same rule also rejected a legitimate
installed customer extension from the three public `run_all` hooks. Odoo module
installation remains the execution prerequisite and `ir.config_parameter` remains
the enablement authority; the Hook contract now distinguishes those facts from
membership in the built-in product composition.

- Known Providers retain their declared execution order and are all still required
  by the static contract guard.
- A contract may explicitly allow additional third-party Providers. Those
  Providers append after the known sequence in deterministic module-name order and
  cannot alter the order of the known product providers.
- `smart_core_register` remains strict: duplicate Intent replacement or removal
  still fails; no duplicate registration exception was introduced.
- `smart_enterprise_base` stays out of the production Provider contract because it
  is an auxiliary source directory without an Odoo manifest, not an installable
  module.

Focused results at `cae4c5ac` plus the five-file R3 hotfix:

| Check | Tests | Result |
| --- | ---: | --- |
| extension runtime context | 15 | PASS |
| Hook contracts and guard | 8 | PASS |
| Hook resolver | 8 | PASS |
| extension consumers | 137 | PASS |
| extension lifecycle ORM | 2 | PASS |
| extension runtime-context ORM | 6 | PASS |
| extension native-alignment ORM | 4 | PASS |
| extension Hook-authority ORM | 4 | PASS |

The first exact-head remote run exposed a P4 validator defect in
`scripts/ci/orm_result_guard.sh`: the Odoo log can start the same test identity
multiple times while its final summary counts unique tests. The old guard summed
raw start lines and rejected a clean `smart_core` run (`238` summary tests versus
`310` start lines). The guard now deduplicates module/class/method identities and
fails when the summary exceeds unique starts; failures, missing identities, zero
collection and wrong selected-database starts remain fail-closed. Its self-test
now covers duplicate and additional starts and passes 33 cases. Replaying the
failed remote `smart_core` log through the corrected guard returns:

`ORM_RESULT_GUARD=PASS tests=238 expected=self identity=odoo.addons.smart_core.tests.`

After that tool correction, `make ci.local.iteration` passed with 41 required
targets and no skipped required target. Original aggregate receipt:
`.runtime/frontend-dev-validation/executions/20261121T172459Z-2611843-775842303/receipt.json`.
The aggregate includes the current owning-module baselines:

| Module | Tests | Result | Original receipt |
| --- | ---: | --- | --- |
| smart_core | 473 | PASS | `.runtime/test-baseline/1795283365386266244` |
| smart_construction_core | 1711 | PASS | `.runtime/test-baseline/1795282603187453047` |
| smart_construction_scene | 18 | PASS | `.runtime/test-baseline/1795283294140227408` |
| smart_construction_bundle | 31 | PASS | `.runtime/test-baseline/1795282526286212393` |
| smart_construction_portal | 4 | PASS | `.runtime/test-baseline/1795283281982353685` |
| smart_license_core | 6 | PASS | `.runtime/test-baseline/1795283449190898842` |
| smart_owner_core | 5 | PASS | `.runtime/test-baseline/1795283466152317478` |
| smart_owner_bundle | 4 | PASS | `.runtime/test-baseline/1795283458477173427` |

After registering those original receipts, `make agent.run.resume` reports
`reusable=30`, no stale checks, `outside_scope=[]` and `blockers=[]`.
The tree is not yet a frozen candidate: delivery evidence preparation, commit,
new exact HEAD publication, all required remote CI and independent review remain
pending.
