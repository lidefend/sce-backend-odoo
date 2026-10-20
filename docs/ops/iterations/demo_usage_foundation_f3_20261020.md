# Demo 用户使用基础数据迭代 · F3 批次记录（2026-10-20）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F2 提交：`8e43ca7744b7420d6dff5b7de376222cba6c2077`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（active）
- Runtime：`sc-local-dev`（db=sc_dev_demo）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling / demo data carrier）
- Layer Target：`demo_addons/smart_construction_demo`（银行账户数据载体 + ORM 验收）+
  `make/dev.mk`（受管 ORM 入口）
- Why Here：银行账户是 U1 主数据，由 P4 demo 数据载体承载；只读 ORM 验收不承载产品语义
- Why Not Elsewhere：不改 P0/P1/P2/P3 产品行为、不手工拼 Compose/DB
- Blast Radius：新增 1 个 XML 载体 + manifest 1 处 + 1 个 ORM 测试 + 1 个 Make 入口

## 3. 本批单一目标

读取 U1/U2 主数据候选集，识别缺口并补齐可直接选择的银行账户；日期/金额失真（DUF-04）
只分类不盲改。

## 4. 只读回读结论

`res.partner=67`、`res.partner.bank=0`、`account.tax=9`、`uom.uom=29`、
`sc.dictionary=66`、`project.cost.code=9`、`sc.material.catalog=3`、
`sc.material.price=1`、`project.project=33`、`project.task=163`。

- 银行账户缺失（bank=0）：U1 缺口，已补 `16_bank_accounts.xml`（9 个账户）。
- 税/单位/字典/成本科目/材料均存在，非零。
- DUF-04 日期：1 个项目 start_date=2025、7 个任务 date_deadline=2025
  （`25_project_tasks.xml` 3 条 + `s10_contract_payment/25_workbench_actions.xml` 4 条），
  属业务日历规则，留 F8 收口，不在本批盲改。

## 5. 产物与文件范围

新增：

- `demo_addons/smart_construction_demo/data/base/16_bank_accounts.xml`：9 个虚构银行账户
- `demo_addons/smart_construction_demo/tests/test_demo_usage_foundation_master_data.py`：
  U1/U2 主数据存在性 + 日期分类的只读 ORM 验收（fail-closed 断言 bank≥9）
- `docs/ops/iterations/demo_usage_foundation_f3_20261020.md`（本记录）

修改：

- `demo_addons/smart_construction_demo/__manifest__.py`：注册 16_bank_accounts.xml
- `demo_addons/smart_construction_demo/tests/__init__.py`：导入新测试
- `make/dev.mk`：`verify.local.dev.demo_usage_foundation_master_data.orm`
- `docs/demo/product_gap_registry_v1.md`：登记缺口 #15
- run.json / goal.yaml：F3 证据与阻断

排除：不改产品视图/动作/安全/模型；不手工组装 Compose/DB；不改 DUF-04 日期金额。

## 6. 阻断

`make local.dev.upgrade MODULE=smart_construction_demo` 因既有产品/客户视图绑定缺陷失败：
`_update_user_groups_view` 抛 `action_sc_review_group_authority 对 res.users 无效`。

- 分类：product_defect（P1/P2/P3 视图/动作绑定）
- 影响：16_bank_accounts.xml 无法受管加载进 sc_dev_demo，银行账户缺口在运行时仍未闭合
- 与 F3 demo 数据无关：该缺陷在模块升级视图再生时暴露，并非本批改动引入
- 处置：登记缺口 #15 / DUF-06；不改 owning layer（超出 F3 P4 范围）；ORM 验收保持 fail-closed

## 7. 验证结果

| 命令 | 状态 | 层 | 说明 |
|---|---|---|---|
| `make verify.local.dev.demo_usage_foundation_master_data.orm`（诊断） | passed | L3 | 上述计数与日期分类 |
| `make local.dev.upgrade MODULE=smart_construction_demo CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_demo` | blocked | L3 | product_defect 视图校验失败 |

## 8. 回滚

- 删除 16_bank_accounts.xml、ORM 测试，撤销 manifest/tests/__init__/make/dev.mk 改动；
- 撤销 product_gap_registry_v1.md、run.json、goal.yaml 改动；
- 无数据库数据写入（升级失败未落库），无产品层改动。

## 9. 下一步精确动作

修 owning layer 的 res.users 视图/动作绑定（DUF-06），再 `local.dev.upgrade
MODULE=smart_construction_demo` 加载银行账户，重跑
`verify.local.dev.demo_usage_foundation_master_data.orm` 后继续 F4。
