# Demo 用户使用基础数据迭代 · F2 批次记录（2026-10-20）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F1 提交：`329e43c364310048e8800359fcc6c394078e4d16`
- Run：`DEMO-USAGE-FOUNDATION-20261020`（active）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling）
- Layer Target：`scripts/verify` + `make/dev_test.mk`（多角色只读启动验收）
- Module：`smart_construction_demo`（demo 侧），不改产品 addons
- Why Here：角色/公司/项目范围的启动验收是 P4 验证工具，只消费公开
  login/system.init/my.work.summary 契约
- Why Not Elsewhere：不写数据库、不补事实、不伪造首屏、不硬编码产品角色语义
- Blast Radius：新增 3 个文件 + 2 个 Make 目标；无运行时数据/权限/流程变更

## 3. 本批单一目标

校正并验收身份、公司与项目范围：业务全功能账号与关键角色登录后
role_surface 正确、公司作用域正确、默认路由存在、首屏可读，负例登录被拒。

## 4. 产物与文件范围

新增：

- `scripts/verify/demo_usage_foundation_role_scope_manifest.json`
  - 11 个账号：全功能（wutao/demo_full）、pm、finance、owner、executive、cost、
    project_member、contract/purchase/material 能力席位
  - 每账号声明 expectation（role_code / valid_surface）、expected_role_code、
    first_screen_expectation（non_empty / record）、label
  - company_scope 权威声明（company_id=1、allowed=[1]）；公司名称属于环境展示值，
    不作为仓库内的固定客户标识；1 个负例（错误密码拒绝）
- `scripts/verify/demo_usage_foundation_role_scope_probe.py`
  - 只读运行时探针：login → system.init → my.work.summary
  - 断言 role_code / 公司作用域 / 默认路由 / 首屏非空（按声明）/ 负例拒绝
  - 首屏计数只记录不伪造；readback 落 `.runtime/agent-runs/DEMO-USAGE-FOUNDATION-20261020/role_scope_readback.json`
- `scripts/verify/test_demo_usage_foundation_role_scope_probe.py`
  - 14 例离线单测：完整 / 缺失 / 非法声明 / 重复键 / 角色与公司不匹配 / 首屏空断言 / 负例

修改：

- `make/dev_test.mk`：`verify.demo.usage_foundation_role_scope.unit`（离线）+
  `verify.demo.usage_foundation_role_scope.smoke`（运行时只读）
- run.json / goal.yaml：F2 证据与下一批边界

排除：未改 demo 数据载体、模型、timer、reset；未写数据库；未改产品层。

## 5. 运行时只读验收结论

环境：`sc-local-dev`（db=sc_dev_demo，http://127.0.0.1:18081，namespace=demo）。

`summary.overall_pass=true`；account_passed=11 / account_failed=0；negative_passed=1。

| 账号 | role_code | 首屏合计 | 首屏断言 |
|---|---|---|---|
| wutao（纯能力） | business_full | 0 | record |
| demo_full（验收主账号） | business_full | 116 | non_empty ✓ |
| demo_role_pm | pm | 0 | record |
| demo_role_finance | finance | 0 | record |
| demo_role_owner | owner | 1 | record |
| demo_role_executive | executive | 179 | record |
| cost1 | cost | 183 | record |
| demo_role_project_read | project_member | 0 | record |
| ct1 | project_member | 180 | record |
| pur1 | project_member | 1 | record |
| mat_mgr | project_member | 182 | record |

负例：wutao 错误密码登录被拒（denied=true）。

## 6. 发现与归属

1. 身份/角色/公司作用域全部正确，无需改 P4 数据载体。
2. 全功能账号首屏非空：`demo_full`（含 `group_sc_cap_project_read` 与项目成员）todo=44 等
   合计 116；`wutao`（纯 `group_sc_business_full`，无项目成员）首屏为空——由成员/事实派生，
   是正确的产品行为，不是缺陷。验收主账号以 `demo_full` 为准。
3. pm/finance 首屏 todo=0：审批/结算事实尚未生成，属 F4/F6/F7 依赖，不在 F2 伪造。
   该「各角色首屏非空」部分与 DUF-03 的 F8 浏览器验收一起收口。

## 7. 验证结果

| 命令 | 状态 | 层 | 测试数 |
|---|---|---|---|
| `make verify.demo.usage_foundation_role_scope.unit` | passed | L2 | 14 |
| `python3 scripts/verify/demo_usage_foundation_role_scope_probe.py` | passed | L3 运行时只读 | 11 账号 + 1 负例 |

## 8. 回滚

删除 manifest/probe/test 三文件，撤销 `make/dev_test.mk`、run.json、goal.yaml 改动。
无运行时数据写入，无数据库/模型/权限变更需回退。

## 9. 下一步精确动作

F3（业务主数据与表单可用性）：按 F1 manifest 的 U1/U2 requirement 回读公开表单候选集，
校正客商/银行/税/付款条件/单位/材料/字典/成本项，登记并修复日期/金额样例失真（DUF-04）。
