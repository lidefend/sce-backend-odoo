# 产品配置能力 · Batch 4 执行记录（2026-10-20）

## 0. 身份

- Worktree：`/home/lidefend/workspace/sce-backend-odoo`
- Branch：`feature/product-configuration-capability-20261020`
- Base（main）：`82dbd9134288576ede315370179858c5ba70ce87`
- 批次起点 HEAD：`241856c29017fb3460e285befc9ccb0c077559c7`
- 阶段身份：HEAD + 显式 dirty 范围（日常开发，未冻结）

## 1. 决策边界

- Formal Product Layer：P1（受控系统参数是行业标准产品语义，归 `smart_construction_core`）。
- Layer Target：`smart_construction_core` 服务/处理器 + `config` 声明 + `scripts/verify` 守卫。
- Module：smart_construction_core / config / scripts.verify / make / docs / .agent。
- 目标（唯一）：以产品批准的参数目录约束系统参数，提供影响预览，变更走变更集（发布/回滚）。
- 范围：参数目录声明、后端投影服务、catalog + preview 两个 intent、guard/测试、make 目标、
  批次记录与 run 台账。
- 不做：不暴露原始 `ir.config_parameter`、密钥、数据库地址或认证信息；不写 P0 变更集模型
  （参数变更集在 P1 层实现）；不在本层做前端页面渲染；不合并 main。

## 2. 实施步骤（本层：目录 + 影响预览）

1. `config/product_system_parameter_catalog_v1.json` + `addons/smart_construction_core/data/`
   运行时副本：6 类 13 参数，每个参数含名称/说明/类型/默认值/允许值/范围/维护角色/影响说明。
2. `services/product_system_parameter_catalog.py`：纯投影 `build_catalog` + 确定性
   `impact_preview`（available 参数校验值域，planned 参数返回 not_implemented，均带影响与
   change_set/audit/rollback 要求）。
3. `handlers/product_system_parameter_catalog.py`：
   - `sc.product.system_parameter.catalog`（只读，注入 cost_ledger_source 当前值）；
   - `sc.product.system_parameter.preview`（仅行业配置管理员，返回影响预览）。
4. `core_extension_intent_handlers.py` 登记两个 intent。
5. `scripts/verify/product_system_parameter_catalog_guard.py` + 单测 + 服务测试 + make 目标。

## 3. 验证结果（本层）

| 层 | 命令 | 状态 | 测试数 |
|---|---|---|---|
| L1 | `python3 -m py_compile`（服务/处理器/贡献注册表） | passed | - |
| L2 | `make verify.product_system_parameter_catalog` | passed | 17（guard 8 + service 9） |
| L2 | `python3 scripts/verify/test_construction_intent_contribution_registry.py` | passed | 2 |

guard 结论：categories=6 parameters=13，无密钥/无原始 ir.config_parameter；cost_ledger_source 为
唯一 available 参数，其余 planned 不伪装可用。

## 4. 未完成（本批剩余层）

- 变更集发布/回滚：P1 层参数变更集（draft → preview → publish → rollback + 审计），对
  `cost_ledger_source` 写/恢复公司字段；需要数据库，离线环境为 `verification_pending`。
- 前端消费：参数目录页 + 影响预览 UI（下一步）。

## 5. 风险与回滚

- 风险：本层为只读投影 + 影响预览，不写库；preview intent 仅授权行业配置管理员。
- 回滚：`git revert` 本层提交；不涉及数据库/服务/部署。

## 6. 下一步

- 提交本层；随后实现 P1 参数变更集发布/回滚，再接前端消费。
