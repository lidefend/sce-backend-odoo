# DEMO-01 项目业务链数据完善

## 身份与边界

- 仓库：`sce-backend-odoo`
- 基线：`70ad2e6af3b6794a9bcba0ea2b4dde499a6ecf07`（PR #880 合并后主线）
- 分支：`feature/demo-business-chain-data-20261113`
- 工作树：`/home/lidefend/workspace/sce-backend-odoo-demo-business-chain-20261113`
- Formal Product Layer：P4 演示交付工具
- Module：`smart_construction_demo`
- 目标：形成一条可解释、可追溯、可重复加载的项目业务样板

本批只修改虚构 Demo 数据、其加载/校验机制和说明。P0-P3 的产品语义、权限、契约、菜单、正式 seed、验收夹具和客户数据不在范围内。发现产品缺陷时记录所属层和影响，不在 Demo 层兜底。

## 初始事实

- `origin/main` 已核对为 `70ad2e6af3b6794a9bcba0ea2b4dde499a6ecf07`。
- 主工作树承载另一项 CI 主题且存在 3 个既有修改，已保留不动。
- detached 验收工作树及其运行进程已保留不动。
- 本工作树从精确主线新建且初始 clean。

## 数据安全边界

- 运行载体：`sc-local-dev`
- 数据库：`sc_dev_demo`
- 数据库角色：客户租户 Demo 开发库
- 正式客户业务数据：不允许
- Demo/合成夹具：允许
- 数据库与 filestore 身份：沿用既有 `local.dev` 受管配置
- 写库前必须通过 `local.dev` 写锁；只读盘点不写库

## 验收标准

1. 相同 profile 重复加载不复制主项目、合同、结算、申请或执行记录。
2. 主项目、合同、结算、付款申请、付款执行、台账和项目汇总引用一致。
3. 金额、日期和状态能从汇总追溯到业务事实。
4. 固定展示记录与可操作草稿的重复加载语义不同且明确。
5. 通过现有正式入口观察项目经理、财务和管理层可见性；产品层缺陷另行登记。

## 执行结果

### 已实现

- 选择 `DEMO-PJ-EXEC` 作为 DEMO-01 主项目；补齐固定日期、周期、说明和经营资料。
- 新增 `demo_01_business_chain` 受管种子步骤，在合同种子之后生成：
  - 已审批付款申请 → 付款执行 → 已过账支付台账；
  - 可从台账追溯的 160,000 元已支付事实；
  - 一条 120,000 元“第二期分包付款”可操作草稿。
- 固定展示记录使用稳定 XMLID；可操作草稿只在不存在时创建，重复加载不覆盖用户推进后的状态。
- DEMO-PJ-EXEC 不再由通用驾驶舱样板注入第二套合同和收付款事实。
- 新/重建结算在提交前写入结算金额、送审金额和审定金额。
- 补齐集团级 Demo 账号的第二经营公司成员关系。
- 将可见角色名中的“示例”占位改为正式岗位名称。
- 修正 README：S10 已由 manifest 默认加载。

### 运行态主链

| 环节 | XMLID / 结果 |
| --- | --- |
| 项目 | `smart_construction_demo.sc_demo_project` |
| 支出合同 | `sc_demo_exec_expense_contract`，明细 400,000 元，含税 452,000 元 |
| 结算 | `sc_demo_exec_settlement`，状态 `approve`，总额 400,000 元，关联采购依据 |
| 付款申请 | `sc_demo_exec_payment_request`，状态 `done`，160,000 元，收款账户完整 |
| 付款执行 | `sc_demo_exec_payment_execution`，状态 `paid`，160,000 元 |
| 支付台账 | `sc_demo_exec_payment_ledger`，状态 `posted`，160,000 元 |
| 可操作草稿 | `sc_demo_exec_actionable_payment_draft`，状态 `draft`，120,000 元 |

重复执行同一 `demo_01_business_chain` 步骤后，以上 XMLID 对应 ID、执行/台账/草稿数量均保持不变。

### 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.demo.lifecycle.unit` | PASS，145 项 |
| `make verify.demo.scenario_step.unit` | PASS，9 项 |
| `make verify.local.dev.golden_chain.orm` | PASS，3 项 |
| `make local.dev.verify_demo` | PASS，全部 Demo 验收项 |
| `make verify.demo.role_startup.smoke` | PASS，项目经理正式入口、导航和工作台可用 |
| `make verify.demo.usage_foundation_role_scope.smoke` | PASS，11/11 账号及错误密码负例通过 |
| `make fe.install` / `make local.dev.frontend` | PASS，锁定依赖安装与候选静态包构建成功 |
| `make local.dev.health` | PASS，持久开发入口和后端健康通过 |

受管 `local.dev.rebuild_demo` 最终完成了数据库重置、release seed 和 `demo_full`；主链与业务验收全部通过。外层命令仅在最后的前端 HTTP 健康检查因当前工作树没有静态构建产物而返回 404。入口 namespace 已通过 `local.dev.entry_identity.ensure` 从旧的 `sc_demo` 修复为 `sc_dev_demo`。

重建后再次执行 `demo_01_business_chain`，所有 XMLID、状态和数量保持不变；主项目只有 2 张合同，通用驾驶舱合同与付款残留均为 0。

### 未闭环项

1. **产品汇总缺口**：`ProjectDashboardService` 引用未注册的 `sc.evidence.summary.service`，正式 `summary_rows` 回退为 0；真实付款台账为 160,000 元。该缺陷属于 P0/P1，未在 Demo 层造投影绕过。
2. **增量入口收口**：前端依赖和构建已补齐，账号矩阵通过。`ci.local.iteration` 的 dry-run 计划仍要求部署阶段的 `daily_runtime_entry` 证据；该证据不属于本地 Demo 数据验收，需按正式发布/远端 CI 阶段处理。

### 运行态变更与回滚

已执行：Demo 模块升级、`local_dev_write_lease` 下的 DEMO-01/公司成员种子写入、`local.dev.restart`。没有推送远端、创建 PR 或部署。源码回滚为撤销本专题提交；运行库 Demo 数据回滚应使用受管重建，不执行无审计的批量删除。
