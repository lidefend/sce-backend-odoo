# DEMO-02 主项目收入回款闭环与可办理样例

## 身份与边界

- 任务：`DEMO-02-RECEIPT-CHAIN`
- 仓库：`sce-backend-odoo`
- 集成基线：`2dd8e2f7ded8a39916d40bb5e81f654c55c9b3cd`（PR #884 合并提交）
- 分支：`feature/demo-02-receipt-chain-20261113`
- Formal Product Layer：P4 Demo 交付工具
- Layer Target：`smart_construction_demo` 收款数据、场景编排、验证与演示说明
- Module：`smart_construction_demo`
- Standard vs User-Specific：虚构演示数据，不是行业标准、客户基线或生产数据
- Why Here：固定与可办理回款样例属于专用 Demo 模块，消费真实模型和公开业务动作
- Why Not Elsewhere：不改 P1 收款模型/审批/权限，不用前端推导资金口径，不进入正式 seed/验收夹具
- Blast Radius：`DEMO-PJ-EXEC` 收入合同与收款链、`daily_receipt` 事实、Golden ORM 与 Demo 文档

## 数据安全边界

- 运行载体：`sc-local-dev`
- 数据库：`sc_dev_demo`
- 数据库角色：客户租户 Demo 开发库
- 正式客户业务数据：不允许
- Demo/合成夹具：允许
- 数据库、filter 与 filestore：沿用既有 `local.dev` 受管配置
- 共享库写入：必须使用 `local_dev_write_lease`

## 产品结果

1. `DEMO-PJ-EXEC` 固定 120,000 元收款申请完成真实到账，并生成 `received` 收款登记与 `posted/in` 资金台账。
2. 同一项目保留另一张已批准收款申请，以及一张字段完整、待用户继续办理的收款登记草稿。
3. 固定记录与可办理记录使用不同稳定身份，重复加载不复制到账事实、不回退用户进度。
4. `daily_receipt` 场景事实绑定主项目的新收款事实，并校验项目身份。
5. README 说明已完成回款、可办理单据、角色交接、处理入口和台账核对位置。

到账权威口径为 `received` 收款登记及关联 `posted/in` 资金台账；不使用包含已批准申请的 `ProjectFinanceBuilder.summary.received` 冒充实际到账。

## 当前状态

- 数据写入、重复加载、业务路径 ORM 校验和开发增量检查已完成。
- 首轮候选已发布为 PR #885；独立评审的三项 P2 已在 Demo 层修正，修正候选尚待提交和重新发布。
- 本批未修改 P0-P3 产品模型、审批、权限、契约或前端，也没有重跑模块升级、全产品导航或浏览器矩阵。

## 用户办理路径

DEMO-02 不按“每张表有一条记录”组织，而是按用户在系统中的实际办理顺序组织：

1. 用户从主项目收入合同 `DEMO-PJ-EXEC` 查看合同额 1,200,000 元及两行合同依据。
2. 对已完成的固定样例，用户从 120,000 元收款申请进入，看到申请 `done`、收款登记 `received` 和资金台账 `posted/in`，三处金额一致。
3. 对可办理样例，财务经办先从“收款申请”看到已批准的 180,000 元第二期进度回款，再打开同源收款登记草稿核对并提交。
4. 提交后由当前审批实例中的审批席位处理；财务主管随后执行“登记实收”。完成后收款申请变为 `done`，系统生成 `posted/in` 资金台账。
5. 业务项目成员只能在其授权范围内查看结果，不能代替财务席位完成登记实收。

固定记录与可办理记录使用不同申请、不同 XMLID。可办理草稿只创建一次，重复加载不会覆盖用户后续修改的金额、状态或办理进度。

收款账户使用项目公司的账户快照，往来单位继续保留业主；业主名称不进入收款账户字段。旧库已有 `confirmed` 登记时，同步从当前状态直接继续“登记实收”，不会重复调用确认动作。

## 评审修复

PR #885 的独立评审在 `56c7dc9c016e1903a98ce59a6879e6c6f7647dc8` 上提出三项 P2，均限定在 Demo 数据脚本和测试：

1. `confirmed` 收款登记可以从当前状态继续实收，不再重放 `action_confirm`。
2. 固定 120,000 元登记和可办理 180,000 元草稿使用项目公司账户快照，往来方仍为业主，并补充账户归属断言。
3. 新建样例断言到账日等于声明的合同起始日；已有到账允许晚于合同起始日，同时必须与资金台账日期一致。

修正后受管 Demo 重建完成。权威回读为：主项目 ID 1，收入合同 ID 79；固定收款申请 ID 94、`done`/120,000；收款登记 ID 14、`received`/120,000；资金台账 ID 17、`posted/in`/120,000；可办理申请 ID 110、`approved`/180,000；可办理草稿 ID 15、`draft`/180,000。固定和可办理收款账户均为公司 `四川智汇某某建设集团有限公司` / `DEMO-COMPANY-ACCOUNT-001`，往来单位为业主。

随后重放 `demo_40_contracts,demo_01_business_chain,demo_02_receipt_chain`，上述 ID、金额、状态、账户和日期保持不变；固定收款与资金台账各 1 条，没有重复到账。

## 验证结果

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 只读数据盘点 | 通过 | `.runtime/agent-runs/DEMO-02-RECEIPT-CHAIN-20261113/readonly_inventory.log` |
| 首次补链 | 通过 | `.runtime/agent-runs/DEMO-02-RECEIPT-CHAIN-20261113/demo02_seed_first.log` |
| 重复加载 | 通过；主记录 ID、金额、状态和方向不变 | `.runtime/agent-runs/DEMO-02-RECEIPT-CHAIN-20261113/receipt_chain_replay_readback.log` |
| `make ci.local.iteration` | 通过；4 个受影响目标真实执行 | `.runtime/frontend-dev-validation/executions/20261113T152356Z-258180-678994812/receipt.json` |
| Demo lifecycle unit | 83 项通过 | 上述增量执行回执 |
| Demo scenario step unit | 9 项通过 | 上述增量执行回执 |
| Golden ORM | 12 项通过 | 上述增量执行回执 |

中途一次增量检查在 `verify.demo.lifecycle.unit` 报错。归因为 `validation_tool_defect`：补充流程使用只含 `construction.contract` 的轻量 fake env，而新增固定合同解析无条件读取 `project.project`。修复为只在环境提供项目模型时启用该解析；之后同一受影响检查 83/83 通过，完整增量计划再次通过。该失败、回执和恢复事实保留，不计作产品缺陷。

## 下一步

提交并冻结评审修复候选，更新 PR #885；等待新 SHA 的四项必需检查及独立复审。合并不等于部署或产品交付。
