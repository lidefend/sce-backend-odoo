# 产品能力迭代 V2 交接（2026-10-20）

## 身份

- Repository：`/home/lidefend/workspace/sce-backend-odoo`
- Branch：`feature/product-iteration-v2-20261020`
- Main baseline：`74063688e928d25c8e65037ac3306956c954244d`
- 计划：`docs/product/product_iteration_v2_20261020.md`
- Run：`.agent/runs/PRODUCT-ITERATION-V2-20261020/run.json`

## 当前状态

- 产品实现：`not_started`
- Run 状态：`planned`；接管执行器完成身份回读后、开始 Batch 7 写入前切为 `active`
- 批次 7–12：`not_started`
- main 集成/部署/用户验收：保持当前稳定状态；V2 不直接推送 main

## 执行器启动

```bash
git switch feature/product-iteration-v2-20261020
git status --short
make agent.run.resume
```

确认 planning commit、当前分支和 clean HEAD 后，把 run 从 `planned` 切为 `active`，再开始 Batch 7：

1. 读取 `config/product_system_parameter_catalog_v1.json`；
2. 读取审批/付款相关的 `smart_construction_core` 服务与 `payment_request_available_actions.py`；
3. 先写参数值域、审批事实和影响预览的声明/服务测试；
4. 再补前端消费和浏览器断言；
5. 按批次记录证据，不把 partial/planned 伪装成 available。

## 批次顺序与停点

Batch 7 → 8 → 9 → 10 → 11 → 12。每个批次完成后：

- 更新 run 结果索引；
- 写同一批次记录；
- 清理该批次的 dirty 范围；
- 不提前合并 main；
- 下一批只在上一批定向测试与验收通过后开始。

## 边界

- 不在 demo 工作树修改 demo timer、reset、数据清理。
- 不新增数据库/租户/Compose/凭据/生产权限。
- 不绕过变更集、影响预览、审计和回滚。
- 不允许前端按菜单、角色名、模型前缀或参数名推导产品语义。
- 工具/文档直达 main 通道只服务工具维护和文档，不服务本产品分支。

## 交接产物位置

- 计划：`docs/product/product_iteration_v2_20261020.md`
- 批次记录：`docs/ops/iterations/product_iteration_v2_batchN_20261020.md`
- Run：`.agent/runs/PRODUCT-ITERATION-V2-20261020/run.json`
- 浏览器/运行时证据：按现有 `artifacts/` 与 `.runtime/` 受管路径生成，不在 docs 复制日志。

## 第一个精确动作

Batch 7 先完成 `approval_mode` 和 `default_payment_terms` 的产品声明、服务端校验、影响预览和变更集链路；随后把审批岗位提示与组织负责人路由改为 `tier.review` 驱动，再进入前端和浏览器验收。
