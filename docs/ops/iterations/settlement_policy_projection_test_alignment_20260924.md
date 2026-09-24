# 结算收入表单断言对齐已发布的原生结构权威（2026-09-24）

本记录只收口一个**陈旧断言**，不是产品缺陷修复：断言仍在要求已被产品决策退役的第二套结构来源。

## 层与边界声明

- Formal Product Layer：P1 施工行业标准产品（`smart_construction_core` 的已发布结构声明与其回归测试）。
- Layer Target：`smart_construction_core/tests/test_payment_settlement_component_profile.py`。
- Standard vs User-Specific：已发布产品标准，不是客户偏好、也不是运行时配置。
- Why Here：断言写的是"哪个机制拥有结构"，只有产品标准层能回答。
- Why Not Elsewhere：不隐藏断言、不跳过测试、不放宽到"存在即通过"；不改契约数据来迁就一条测试。

## 定位结论

| 事实 | 值 |
|---|---|
| 测试 | `TestPaymentSettlementComponentProfile.test_income_settlement_form_preserves_policy_sections_and_detail_semantics` |
| 首次错误位置 | 第 71 行 `structure["sourceAuthority"]["governance_source"]["categoryCode"]` → `KeyError: 'categoryCode'` |
| 真实契约 | `mode=native_structured_form`、`layoutPolicy=container_tree_authority`、`formStructureAuthority=native_authority`、`presentationMode=task` |
| 治理来源 | `business_view_orchestration`，`businessConfigContracts=[settlement_income_native_form_v1]`、`configuredSections=[]`、`compatibilityDependencies=[]`、`slots=[]`、`fieldRoles={}` |
| 解析动作/视图 | action 781 / view 1764（与 UC1 记录一致） |

产品数据 `addons/smart_construction_core/data/settlement_order_form_productization_contract.xml` 已发布
`business_config_contract_settlement_income_native_form`（priority 20、`status=published`、`active=True`、
`composition_mode=native_semantic_surface`），绑定同一个收入结算动作；`resolve_form_structure_governance`
据此置 `form_structure_authority=native_authority`，`ui_contract_v2` 走原生权威分支，返回原生 containerTree
而不再投影分类策略的 slots/fieldRoles。

时间线：测试上次修改 `6885840f`（2026-09-14，#472）；原生权威收口 `28b7695d`（2026-09-16，#481）退役
action 781 / view 1764 并声明 `nativeStructureAuthority=true`、`configuredSectionsEmpty=true`、
`compatibilityDependenciesEmpty=true`，浏览器证据记为已通过并由用户接受。**测试未被同步对齐，自此一直为红**。

## 判定

- 不是回归：最近的主线合并（`61b8d712..39a90e6d`）未触碰表单结构代码，仅改动 `__manifest__.py` 版本与
  一份契约声明数据（给退役记录补 `status='draft'`）。
- 不是环境差异：原生契约是产品数据（随安装发布），不是客户迁移或本地草稿数据。
- 不是前端问题：契约本身即按原生权威生成，前端按契约渲染。
- 该测试标签 `payment_settlement_component_profile` 目前不在任何 make/scripts 门禁内，因此长期未被发现；
  它仍会出现在结算受影响的定向验收里，构成假信号。

## 最小修改路径（本次实施）

把断言改为已记录的产品决策，而不是删掉断言：

1. 断言原生权威身份：`mode`、`layoutPolicy`、`formStructureAuthority`、`formPresentationMode`。
2. 断言"唯一结构机制"：`configuredSections == []`、`compatibilityDependencies == []`、`slots == []`、`fieldRoles == {}`、
   `businessConfigContracts == ["settlement_income_native_form_v1"]`。
3. 断言原生 containerTree 仍携带业务对象/发票锚点与 `attachment_ids` 字段，且**不**出现策略派生的
   `formStructureRole`（策略重新接管结构即失败）。
4. 保留原有明细语义断言（`line_ids` 子视图列与合同来源修饰符）不变。
5. 方法名同步为 `test_income_settlement_form_uses_recorded_native_structure_authority`。

策略投影路径（`formStructureRole` 覆盖）仍由 `addons/smart_core/tests/test_ui_contract_v2_boundaries.py`
与前端 `canonical_form_presenter_test.ts` 覆盖，本次未减少该能力的覆盖。

## 定向验证

- 修改前：`make local.dev.test MODULE=smart_construction_core TEST_TAGS=payment_settlement_component_profile`
  → 6 passed / 1 error（`sc_dev_demo`，受管 `local.dev`）。
- 修改后：同一命令 → `0 failed, 0 error(s) of 7 tests`。
- 诊断只在运行期临时打印契约，随后已还原；仓库不保留诊断代码。

## 状态与边界

- 本地提交，未推送、未合并。
- 与结算工作表候选 `56db713c` 改同一测试文件的不同方法，无文本重叠；本结论不改变该候选的取舍。
- 结算批次记录 `docs/ops/iterations/worksheet_action_scope_runtime_20260924.md` 由该候选携带，合并时可将本节并入，不新建第二份盘点。

## 门禁接线（同一 PR）

前文指出的“该标签不在任何门禁内”已在本 PR 内修复。

### 触发范围

`config/ci/risk_tiering_v1.json` 已把 `addons/**` 归入 `standard_backend_paths`，因此
**结算产品代码与 `addons/smart_construction_core/tests/test_payment_settlement_component_profile.py`
都在同一触发范围内**，两端的 `backend_changed` 均为 true，无需新增路径规则。

### 接线内容

1. `scripts/test/admin_vis_p3_project_record_rule_orm.sh` 的固定标签白名单新增
   `payment_settlement_component_profile`（白名单机制不变，仍拒绝任意标签）。
2. 新增 `make test.payment-settlement.component-profile.orm`，复用既有隔离测试库机制：
   独立 compose 项目、独立数据库 `sc_test_admin_vis_p3_<ts>_<rand>`、`-i smart_construction_core`
   后 `-u smart_core --test-tags`，**不连接持久开发库**，并在退出时校验容器/网络/卷/数据库清单与前置快照逐项相同。
3. `.github/workflows/professional_quality_gate.yml` 新增步骤
   `Prove settlement component profile with real ORM`，条件 `BACKEND_CHANGED == 'true'` 且
   `PROFESSIONAL_MODE ∈ {full, standard_backend, mainline}`。

### 拒绝语义集中到共享守卫

新增 `scripts/ci/orm_result_guard.sh`，由隔离运行器 `source` 后调用 `evaluate_orm_outcome`：

- `status == 124|137` → `7`（超时）；
- 其它非零进程状态 → 原样透传（测试失败）；
- 退出码 0 但没有 `0 failed, 0 error(s) of [1-9][0-9]* tests`（含 `of 0 tests`、日志缺失）→ `4`。

`timeout --signal=TERM --kill-after=30 "${SC_AUTHORIZATION_ORM_TIMEOUT_SECONDS:-3600}"`
包裹真实执行，使“卡死”也返回失败。

### Gitee 执行器：能执行什么、不能执行什么

**不能**执行 ORM 本体。`scripts/ci/gitee_formal_executor.py` 的 `recipes()` 只实现
`public_guard/required|skip_fast`、`merge_policy_gate/fast|required`、`frontend_release_gate/standard|skip`、
`professional_quality_gate/fast|governance|standard_frontend|standard_backend`；其余 lane 抛
`unsupported_lane_requires_runtime_preparation`。且每条命令都在
`bwrap --unshare-all --ro-bind /usr /usr` 沙箱内执行，没有 docker、没有数据库，`standard_backend`
的实际内容是 `make test.unit`（Python/Node 语法）、`make test.contract`、`make test.e2e.preflight`
与租户静态校验 —— 无法收集 `TransactionCase`。因此**本轮不宣称 Gitee 已接上 ORM 执行**；
把 ORM 命令塞进该 lane 只会让门禁在沙箱里失败。

**能**执行的部分已接线：`scripts/ci/orm_result_guard.sh --self-test` 被加入
`public_guard/required`（候选 PR 在 Gitee 上实际落到该 lane）以及各 `professional_quality_gate`
lane 的 `common`。该自检无容器依赖，覆盖通过、零测试、无可解析报告、日志缺失、进程失败、超时 124/137
共 7 项判定。

**剩余平台缺口（P4，需另行授权）**：`professional_quality_gate` 在 `professional_mode == full`
且 `candidate = true` 时没有可用 recipe，会返回 `environment_error`；这与 plan 中记录的
`blockers = ["isolated_product_runner_not_accepted"]` 一致。该 lane 的运行时能力属于平台/部署层，
不在本 PR 内解决。

另外，Gitee worker 运行的是 `/opt/gitee-ci/sce-product-odoo` 下的受控副本，由
`deploy/gitee-ci/install.sh`（root）部署；**仓库内的接线要在控制器副本刷新后才会生效**，
这一点由部署车道确认，本 PR 不宣称已生效。

### 定向验证

| 项目 | 命令 | 结果 |
|---|---|---|
| 标签收集 | `make local.dev.test MODULE=smart_construction_core TEST_TAGS=payment_settlement_component_profile` | `0 failed, 0 error(s) of 7 tests`（7 个用例名见运行日志） |
| 隔离库端到端 | `make test.payment-settlement.component-profile.orm` | `REAL_ORM_TEST_RESULT=PASS`；`sc_test_admin_vis_p3_20260924135517_891b17c3` 上 `0 failed, 0 error(s) of 7 tests`；容器/网络/卷/数据库前置=后置摘要一致，临时库与临时资源均已移除 |
| 拒绝语义 | `bash scripts/ci/orm_result_guard.sh --self-test`、`make verify.orm.guard.self_test` | `ORM_RESULT_GUARD_SELFTEST=PASS checks=7` |
| 接线契约 | `python3 -m unittest scripts.ci.test_ci_risk_workflow_contract` | 13 项通过 |
| 触发范围 | `recipes("public_guard","required", main)` | 含 `["bash","scripts/ci/orm_result_guard.sh","--self-test"]` |
| 静态 | `python3 scripts/ci/python_syntax_check.py scripts/ci`、`node_syntax_check`、`github_actions_security_guard.py`、`git diff --check` | 通过 |

**未执行**：隔离环境下的“测试失败”和“超时”两个端到端变体（各需一次完整隔离运行）。二者目前由
共享守卫的 7 项自检逐分支覆盖，并由接线契约固定；本轮不把它们记为已端到端验证。

## 状态（补充）

- 批次验收完成：是（断言对齐 + 门禁接线，定向与隔离库均已跑通）。
- 主线集成完成：否。版本发布完成：否。产品交付完成：否。
