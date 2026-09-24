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
- `make local.dev.test MODULE=smart_construction_core TEST_TAGS=rr_gate`：**`0 failed, 0 error(s) of 7 tests`**（原 5 项 + 新增 2 项）。
  - 日志出现 `Access Denied by record rules for operation: read on record ids: [1337], uid: 2497, model: project.boq.line`，即拒绝路径被真实执行，不是仅断言通过。
- 新增用例：
  - `test_boq_line_project_scope`：成本岗可读本项目行；列表读取不含他项目行；按 ID `read()` 抛 `AccessError`（证明是规则拒绝而非列表过滤）；经理保持全量。
  - `test_boq_line_scope_matches_parent_version_scope`：清单行范围必须与 `project.boq.version` 一致，防止再次偏离。
- 非空验证：修复前同一环境的实测为 40 行且 `read()` 成功，修复后为 0 行且 `AccessError`；新增断言在修复前必然失败。

## 明确未覆盖与边界

- **规则定义本身不是证明**：本节结论**不是**由“看到了 `ir.rule` 定义”推出的。规则的存在、域文本或
  组配置都不能单独证明某角色不可越权；这里的判断依据是受管库上的**实际读取结果**（`ir.rule._compute_domain(model,'read')`
  的有效读域 + `with_user` 下的 `search_count` + 按 ID `read()` 抛 `AccessError`）与**具体角色/组组合**。
  未实测的组合逐条列在下方，不得把本结论外推为“所有角色、所有读取入口都已收敛”。
- **公司维度未实测**：`project.boq.line` 无 `company_id`，且 `Demo Secondary Company` 无任何项目/清单数据，因此“两个公司的清单行读取”无法在现有受管夹具上构造。修复沿用父模型语义：范围完全由项目成员关系承载，与 `project.boq.version` 完全相同。
- `项目中心只读(82)` 只有该组、没有 100/101 的用户在清单行与版本上都不受限。这是父模型既有语义，本批**不改变**，属于待产品确认的独立问题，不计入本次修复。
- 未验证列表菜单可达性；动作 534（工程量清单）只授予 100/101/102，82 无法从菜单进入清单列表，残余暴露仅为直接 RPC 读取。
- 本轮不纳入结算 ORM 门禁接线、附件 404、报表投影与显式创建。

## 状态

- 批次验收完成：是（BOQ 清单行范围修复，定向 7/7）。
- 主线集成完成：否。版本发布完成：否。产品交付完成：否。
