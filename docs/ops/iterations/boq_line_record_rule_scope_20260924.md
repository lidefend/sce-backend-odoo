# BOQ 清单行记录规则范围修复

## 身份与边界

- 基线 `39a90e6da4f25c6942fdddb7aa07032dd02da7cc`（实时 Gitee main）。本记录随代码提交，非冻结发布候选。
- Formal Product Layer: P0。Layer Target / Module: `smart_construction_core` 记录规则（`security/sc_record_rules.xml`）。
- 权限边界的唯一归属层是模型记录规则；不使用动作 domain、前端过滤或工作表域补洞。
- 中等风险：`project.boq.line` 的所有读取。改动只让清单行与其父模型 `project.boq.version` 的范围一致，不新增业务语义。
- 未修改客户模块目录、未恢复旧配置、未重建数据库。L2 定向验证使用受管 `make local.dev.*`；因改动属于模块 security/data，按 `guard.codex.fast.upgrade` 的要求经 `CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core` 执行一次模块升级后运行定向测试。

## 根因

`project.boq.line` **完全没有 `ir.rule`**。ACL 只授予读给 `成控中心经办(101)`、`成控中心审批(102)`、`项目中心只读(82)`；没有记录规则时 ACL 即最终边界。

同族模型都已按项目成员范围收敛，只有清单行缺失：

| 模型 | 项目成员范围 | 成控经理全量 |
|---|---|---|
| `project.boq.version` | 462（groups: cost_read 100 + cost_user 101） | 463（cost_manager 102） |
| `project.boq.import.batch` | 464 | 465 |
| `project.boq.analysis` | 有 | 有 |
| **`project.boq.line`** | **缺失** | **缺失** |

`project.boq.line` 没有 `company_id` 字段，公司隔离与项目隔离都只能经 `project_id` 表达；父模型正是这样做的。

## 修复前实测（受管开发库 `sc_dev_demo`，只读）

有效读域 `ir.rule._compute_domain(model, 'read')`：

| 用户 | 组 | `project.boq.line` | `project.boq.version` |
|---|---|---|---|
| `demo_cost` (48) | 82,100,101 | `[]` | 项目成员范围 |
| `pm1` (7) | 82,100,103 | `[]` | 项目成员范围 |
| `sc_project_viewer` (17) | 82 | `[]` | `[]` |

实际读取（`with_user`）：

- `demo_cost`：清单行 `search_count` = **40/40**，可 `read()` 项目 1、2、4 的行；同一用户版本 `search_count` = **0**。父模型受保护、子模型全量泄漏。
- `pm1`：清单行 40，版本 2。同一用户在两个模型上范围不一致。
- `sc_cost_mgr` (22)：40 / 25，符合经理全量预期。

即：**越权真实存在**，且表现为“版本不可见但清单行可见”的不一致。

## 修复

在 `sc_record_rules.xml` 中为 `model_project_boq_line` 补两条与父模型逐字对齐的规则：

- `rule_sc_boq_line_project_scope`：`['|', ('project_id.user_id','=',user.id), ('project_id.message_follower_ids.partner_id','=',user.partner_id.id)]`，groups = cost_read + cost_user。
- `rule_sc_boq_line_manager_all`：`[(1,'=',1)]`，groups = cost_manager。

不在动作 domain、工作表域或前端补洞；不改变 ACL。

## 修复后实测

| 用户 | 组 | 版本 | 清单行 | 读取被拒 |
|---|---|---|---|---|
| `demo_cost` | 82,100,101 | 0 | **0**（原 40） | 是 |
| `pm1` | 82,100,103 | 2 | **5**（原 40） | 与版本一致 |
| `sc_project_viewer` | 82 | 25 | 40 | 与版本一致（无范围的规则组） |
| `sc_cost_mgr` | 82,101,102 | 25 | 40 | 经理全量 |

`demo_cost` 的有效读域由 `[]` 变为项目成员范围；其清单行数量与版本数量恢复一致。

## 定向验证

- `make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_construction_core`：PASS，`local.dev.ready` / `local.dev.demo.authority` 均通过。
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=rr_gate`：**`0 failed, 0 error(s) of 8 tests`**（原 5 项 + 新增 3 项）。
  - 日志出现 `Access Denied by record rules for operation: read on record ids: [1337], uid: 2497, model: project.boq.line`，即拒绝路径被真实执行，不是仅断言通过。
- 新增用例：
  - `test_boq_line_project_scope`：成本岗可读本项目行；列表读取不含他项目行；按 ID `read()` 抛 `AccessError`（证明是规则拒绝而非列表过滤）；经理保持全量。
  - `test_boq_line_scope_matches_parent_version_scope`：清单行范围必须与 `project.boq.version` 一致，防止再次偏离。
  - `test_boq_line_cross_company_scope`：跨公司反例与经理例外的实际范围，见下节。
- 非空验证：修复前同一环境的实测为 40 行且 `read()` 成功，修复后为 0 行且 `AccessError`；新增断言在修复前必然失败。
- 跨公司断言的**非空性实测**：把本轮新增的两条全局公司规则（`ir_rule` id 518/519）置为 `active=false` 后重跑同一套件，
  得到 `1 failed, 0 error(s) of 8 tests`，失败点为 `test_boq_line_cross_company_scope`（`AssertionError: True is not false`）；
  随后按权威回读确认两条规则恢复为 `active=true`（`select id,name,active,global`），且未连带改动其它规则
  （`select count(*) from ir_rule where active=false` = 1，为既有的标准门户规则 id 151）。
  即：新增断言在缺少本轮修复时确实失败，不是恒真断言。

## 跨公司维度（本轮补测，并据此修复）

`project.boq.line` 与 `project.boq.version` 都没有 `company_id`，公司边界只能经 `project_id -> project.project.company_id` 表达。
本轮在受管开发库（`sc_dev_demo`）用**事务内创建 + `rollback`** 的探针构造了第二个公司、
一个二级公司项目、以及一个“二级公司项目但负责人是主公司用户”的项目，实测各角色的列表读取与按 ID 读取。
无残留：探针创建的 `res_company` / `zz*` 用户 / `ZZ*` 清单行在回读中均为 0，`ROLLED_BACK=true`。

**修复前实测**

| 角色 | 主公司行 | 二级公司行 | 二级公司行（负责人=主公司用户） | 二级公司版本 |
|---|---|---|---|---|
| 主公司成本经办 | 可读 | 不可读（列表 0 / 按 ID `AccessError`） | **可读** | 不可读 |
| 主公司成本经理 | 可读 | **可读** | **可读** | **可读** |
| 二级公司成本经办 | 不可读 | 可读 | 不可读 | 不可读 |

即修复前存在两个真实跨公司读取口子：

1. **项目成员命中即放行**：主公司成本经办是二级公司某项目的负责人，该项目本身对其返回
   `AccessError`，但其清单行可读、版本可读（项目不可见而清单行可见）。
2. **经理例外没有公司维度**：`[(1,'=',1)]` 与分组规则都是“无公司条件”，主公司成本经理可读二级公司的
   清单行与版本，而同一记录下 `project.project` 对该用户是拒绝的。

**修复**

在 `project.boq.version`、`project.boq.line` 上各补一条**全局**（不带 `groups`）公司规则，与既有的
`rule_sc_tender_opportunity_company` 同型：

```
['|', ('project_id.company_id', '=', False), ('project_id.company_id', 'in', company_ids)]
```

全局规则与分组规则是 **AND** 关系，因此成员范围规则与经理例外都在公司边界之内生效，而不是替换其中任何一个。
这一点不是由规则文本推断，而是由有效读域实测确认：

| 角色 | 有效读域 |
|---|---|
| 主公司成本经办 | `&`（公司规则）`|`（项目负责人 / 项目关注者） |
| 主公司成本经理 | 仅公司规则（原为 `[(1,'=',1)]`） |

**修复后实测**

| 角色 | 主公司行 | 二级公司行 | 二级公司行（负责人=主公司用户） | 二级公司版本 |
|---|---|---|---|---|
| 主公司成本经办 | 可读 | 不可读 | **不可读** | 不可读 |
| 主公司成本经理 | 可读（含他人项目） | 不可读 | 不可读 | 不可读 |
| 二级公司成本经办 | 不可读 | 可读 | 不可读 | 可读 |
| 二级公司成本经理 | 不可读 | 可读 | 可读（仍在二级公司内） | 可读 |

二级公司经理仍能读到“负责人是主公司用户但项目属于二级公司”的行，这与修复前的 `project.boq.version`
语义一致（经理例外在该公司范围内覆盖全部项目），属既有语义，本批不改。

## 明确未覆盖与边界

- **规则定义本身不是证明**：本节结论**不是**由“看到了 `ir.rule` 定义”推出的。规则的存在、域文本或
  组配置都不能单独证明某角色不可越权；这里的判断依据是受管库上的**实际读取结果**（`ir.rule._compute_domain(model,'read')`
  的有效读域 + `with_user` 下的 `search_count` + 按 ID `read()` 抛 `AccessError`）与**具体角色/组组合**。
  未实测的组合逐条列在下方，不得把本结论外推为“所有角色、所有读取入口都已收敛”。
- **公司维度已实测并修复**：见上节。原先“公司维度未实测”的原因不是模型不可验证，而是当时没有构造跨公司夹具；
  沿真实关联（`project_id.company_id`）即可测。修复前实测到两处真实跨公司读取，修复后同一探针复测为拒绝。
- **同族模型仍未收敛（已登记，未在本批修复）**：`project.boq.import.batch`、`project.boq.analysis`、
  `project.boq.analysis.norm.line`、`project.boq.analysis.resource.line`、`project.boq.summary.component`、
  `project.cost.plan` 等使用与清单行修复前完全相同的“项目成员范围 + 经理全量”形状，且都没有公司条件。
  已实测其中 `project.boq.import.batch`：主公司成本经理对二级公司批次 `search=1 / read_ok`，
  而其有效读域为 `[(1,'=',1)]`，同一记录下 `project.project` 对其拒绝。这是既有暴露，本批未修，单独登记。
- `项目中心只读(82)` 只有该组、没有 100/101 的用户在清单行与版本上都不受限。这是父模型既有语义，本批**不改变**，属于待产品确认的独立问题，不计入本次修复。
- 未验证列表菜单可达性；动作 534（工程量清单）只授予 100/101/102，82 无法从菜单进入清单列表，残余暴露仅为直接 RPC 读取。
- 本轮不纳入结算 ORM 门禁接线、附件 404、报表投影与显式创建。

## 状态

- 批次验收完成：是（BOQ 清单行范围修复 + 跨公司边界修复，定向 8/8；含非空性反例与有效读域实测）。
- 主线集成完成：否。版本发布完成：否。产品交付完成：否。
