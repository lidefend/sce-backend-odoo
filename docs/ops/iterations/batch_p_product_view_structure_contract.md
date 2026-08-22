# Batch-P Release Note

## 1. 本轮变更

- 目标：建立正式产品菜单到 Odoo 有效视图的可复现结构契约，并清除该新契约的 `v1` 别名。
- 完成：增加 clean-install 导出、受控基线、漂移门禁、专项测试和语义化 Schema `product_view_structure_contract/1.0.0`。
- 未完成：验证尚未收口前，本批次不得发布。

## 2. 影响范围

- 模块：`scripts/contract`、`scripts/verify`、`make/contract.mk`、`make/dev.mk`、`contracts/generated`。
- 启动链：否。
- contract/schema：是，仅新增产品视图结构证据契约。
- default_route：否。
- public intent：否。

## 3. 风险

- P0：错误的视图解析或不完整菜单覆盖会形成不可信基线；门禁对缺项、失败项、零 surface 和漂移失败关闭。
- P1：正式菜单策略仍是冻结输入，本批次不修改其版本或行业语义。
- P2：不消费 demo、sample、客户租户或低代码运行态数据。

## 4. 验证

- 命令：`python3 -m unittest scripts.verify.test_product_view_structure_contract -v`。
- 命令：`make verify.contract.view_structure`。
- 命令：`make local.clean.view_structure_gate`。
- 结果：待本批次验证完成后更新。

## 5. 产物

- snapshot：`contracts/generated/product_view_structure_contract.json`。
- candidate：`artifacts/contract/product_view_structure_contract.json`。
- guard report：`artifacts/backend/product_view_structure_contract_guard.json`。
- e2e：N/A；本批次不修改用户界面或启动链。

## 6. 回滚

- commit：本批次尚未提交。
- 方法：仅移除 Batch-P 新增文件并回退 `make/contract.mk`、`make/dev.mk` 中的 Batch-P targets；不得回退同工作区其他既有变更。

## 7. 下一批次

- 目标：本批次通过独立复核后再由 Owner 决定；当前不自动扩展范围。
- 前置条件：专项测试、静态 guard 与 governed local.clean drift gate 全部通过。
