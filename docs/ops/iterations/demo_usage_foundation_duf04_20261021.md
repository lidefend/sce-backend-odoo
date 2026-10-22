# Demo 用户使用基础数据迭代 · DUF-04 日期口径收口（2026-10-21）

## 1. 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- Branch：`feature/demo-iteration-line-20261020`
- F8 提交：`ff5499009307be10fa1aa3400ec2c5a552402e05`
- Runtime：`sc-local-dev`（db=sc_dev_demo）

## 2. 层级声明

- Formal Product Layer：P4（ops delivery tooling / demo 数据载体）
- Layer Target：demo 数据 XML + `scripts/verify/local_dev_demo_date_caliber_repair.py`
- Why Here：日期口径是 demo 数据质量，由 P4 载体承载并受管修复
- Why Not Elsewhere：不写产品状态、不绕过审批、不伪造终态

## 3. 日期口径规则

demo「今天」= 2026-10-20（F7 tick 窗口）。可办理工作项（任务 deadline、草稿付款申请、
草稿发票）落在 2026-10 当前窗口；项目工期起点 2025-01 与成本/合同/展示历史保留为
两年期项目的合法历史。金额未发现 50/100 样例（仅 BOQ-100 编码）。

## 4. 变更

- XML：任务 deadline（25_project_tasks + s10 workbench）、付款申请（s10/s20/s30/s66）、
  发票（s10）平移 2026-10；项目描述对齐 2026-10 阶段；noupdate=0 使重建生效；
- `scripts/verify/local_dev_demo_date_caliber_repair.py`：既有库对齐（7 任务 + 8 付款 +
  2 发票 + 2 项目，草稿按规则扫尾）；
- `test_demo_usage_foundation_master_data.py`：新增 fail-closed 日期口径断言
  （草稿任务/付款日期不得早于 2026-01-01）。

## 5. 验证

| 命令 | 状态 | 层 | 测试数 |
|---|---|---|---|
| `make verify.local.dev.demo_usage_foundation_master_data.orm` | passed | L3 | 2 |

回读：`project.task.date_deadline` 2025 计数 = 0；草稿付款/发票 2025 日期 = 0；
`project.project.start_date` 2025 计数 = 1（项目工期起点，合法历史）。

## 6. 回滚

恢复 XML 日期为 2025 值并重跑修复脚本反向写回；无产品层改动。

## 7. 下一步精确动作

F1–F8 与 DUF-01/04/05/06/07 全部收口；主线集成、部署、用户验收由所有者授权。
