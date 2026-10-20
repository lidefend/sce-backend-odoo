# Demo 用户使用基础数据迭代 · F4 批次记录（2026-10-21）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F3/DUF-06 关闭提交：`6fcd63fcd0c1b0b5e9a3d74480980a0d1f8b1fd8`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（active）
- Runtime：`sc-local-dev`（db=sc_dev_demo）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling）
- Layer Target：`demo_addons/smart_construction_demo/tests` + `make/dev.mk`（审批/编号/权限只读 ORM 验收）
- Why Here：验收审批策略、步骤、审批人、编号规则与权限边界，只读消费产品契约
- Why Not Elsewhere：不写 ir.config_parameter、不改 P3 变更集、不改产品审批/权限代码
- Blast Radius：新增 1 个 ORM 测试 + 1 个 Make 入口；无数据/权限/流程变更

## 3. 本批单一目标

验证第一笔业务提交后审批链路真实可用：每级审批有真实内部用户、编号规则激活、
未授权角色不能办理；只回读、不补配置。

## 4. 只读回读结论

`sc.approval.policy=15`、`sc.approval.step=35`、`zero_reviewer_steps=[]`、
`ir.sequence active=65`。

- 每个审批步骤的 `approve_group_id`（或策略 `manager_group_id` 兜底）都有至少一个
  active 内部用户，不存在“某级永远无人可批”的步骤。
- 编号规则 65 条激活。
- 既有 `demo_action_roles`（7 例）与 `test_demo_api_scenario`（四层审批链、真实审批人、
  非审批人拒绝）在当前运行时通过。

结论：审批/编号/权限基础配置已就绪，本批无需 P4 数据修复。

## 5. 产物与文件范围

新增：

- `demo_addons/smart_construction_demo/tests/test_demo_usage_foundation_approval.py`：
  fail-closed ORM 验收（policies>0、steps>0、zero_reviewer_steps=[]、numbering_active>0）
- `docs/ops/iterations/demo_usage_foundation_f4_20261021.md`（本记录）

修改：

- `demo_addons/smart_construction_demo/tests/__init__.py`：导入新测试
- `make/dev.mk`：`verify.local.dev.demo_usage_foundation_approval.orm`
- run.json / goal.yaml：F4 证据与下一批边界

排除：未改审批策略/步骤/编号规则/权限数据；未写 ir.config_parameter；未改产品代码。

## 6. 验证结果

| 命令 | 状态 | 层 | 测试数 |
|---|---|---|---|
| `make verify.local.dev.demo_usage_foundation_approval.orm` | passed | L3 | 1 |
| `make verify.local.dev.demo_action_roles.orm` | passed | L3 | 7 |

## 7. 回滚

删除 F4 ORM 测试，撤销 tests/__init__、make/dev.mk、run.json、goal.yaml 改动。
无运行时数据写入。

## 8. 下一步精确动作

F5（项目启动基线与提交前就绪）：回读项目负责人/成员、资金基线、预算、BOQ/WBS、
合同/采购依据，验证 ready/partial/blocked 四态与付款提交前硬前置。
