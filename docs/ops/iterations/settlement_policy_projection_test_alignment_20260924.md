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
