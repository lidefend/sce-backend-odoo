# PC-02 · 综合合同 P1/P2 运行时验收报告

结论类型：RUNTIME_ACCEPTANCE。

## 1. 冻结候选

- Branch: `feature/contract-detail-productization-01`
- Candidate HEAD: `71cf327cb5d5f25bc971d2edbdba7dbc6e60adc1`
- served_revision: `71cf327cb5d5f25bc971d2edbdba7dbc6e60adc1`
- profile: `candidate`
- compose project: `sc-fe-candidate-770`
- database: `sc_frontend_acceptance_candidate`
- database namespace UUID: `ns_0af74d2911bf`
- backend: `http://127.0.0.1:18088`
- frontend preview: `http://127.0.0.1:5178`

## 2. 验收目标

- 模型: `sc.general.contract`
- 权威 Action: `smart_construction_core.action_sc_general_contract`（action_id 758）
- 权威 Menu: `smart_construction_core.menu_sc_p1_daily_contract`（menu_id 663）
- 表单: `view_sc_general_contract_form`
- 登录: `fixture_role_config_admin`

## 3. 两个方向的结果

| 方向 | entry | 记录 | route | 视口 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 收入合同 | `contract` | `fe_general_contract_a`（GC2600001） | `/r/sc.general.contract/2?action_id=758&menu_id=663` | 1440/1024/768/390 | PASS |
| 支出合同 | `general_contract_expense` | `fe_general_contract_b`（GC2600002） | `/r/sc.general.contract/3?action_id=758&menu_id=663` | 1440/1024/768/390 | PASS |

两个方向均无横向溢出、无控制台错误、无 pageerror、无 5xx HTTP 响应。

## 4. P1 身份带断言

- `contract_name` 主标题唯一渲染
- `contract_no`、`contract_direction`、`contract_type`、`name` 渲染
- `state` 生命周期 statusbar 独立呈现（`[data-status]` 存在）
- `validation_status` 独立保留，不与 `state` 合并

## 5. P2 金额与履约语义

- `amount_total` 在原始金额与最终执行金额语境通过标签区分，避免误认为两个独立金额
- `change_amount_total` 零值不解释为“无变更”
- 收入方向突出 invoice/received 收款履约
- 支出方向突出 paid 付款履约

## 6. 四视口证据

每个方向、每个视口采集整页截图和几何数据：

`.runtime/final-acceptance/contract-form-presentation/<entry>/viewport-<key>.png`

几何证据见
`.runtime/final-acceptance/contract-form-presentation/<entry>/summary.json`。

## 7. 冻结边界

- 变更单是否汇总到最终合同价：NOT_VERIFIED
- 结算金额是否允许超过最终合同价：NOT_VERIFIED
- 历史付款与新系统付款边界：NOT_VERIFIED

## 8. 未改变

未修改金额计算、ACL、record rule、审批逻辑、权威导航、业务数据。未新增合同专属 Vue。
