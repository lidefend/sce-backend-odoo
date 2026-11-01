# 408 · BNVA-04 Runtime Source Alignment

## P4-06D-01A · 源码版本固定（完成）

- 产品提交：`b7e2383a1`（smart_construction_core 两个产品化契约 + 视图修正 + manifest 注册；
  治理钩子顺带刷新 `complexity_budget_report.md` scanned files 5017→5018）。
- 文档提交：`381af4abc`（BNVA-04-06 证据 387-407 + run record）。
- 当前 HEAD：`381af4abc661bf643d2f9934c6d83ad92fda1858`；工作树干净；未 Push / Merge。

## P4-06D-01B · 运行环境对齐（已核实）

- sc_clean 容器源码挂载指向 `/home/lidefend/workspace/sce-backend-odoo-pc01`（本工作树）。
- db=sc_clean，dbfilter=^sc_clean$，project=sc-local-clean。
- `local.clean.health` PASS；`local.clean.entry_identity.verify` =
  `{"alias":"clean","database_name":"sc_clean","lifecycle_state":"active","namespace_id":"ns_c6fed472e939"}`。

## P4-06D-01C 前置阻断（未执行写库）

- `LOCAL_CLEAN_MODULES` 默认 `sc_norm_engine`，无法用现有受管入口确认 sc_clean 已安装
  `smart_construction_core`；存在「升级」实际变成「安装」的风险。
- 仓库无 sc_clean 的受管点时间备份入口；可恢复路径仅为 `local.clean.rebuild`（一次性重建），
  非点时间备份。两者均需先裁决，再执行写库。

## 停止条件

任一以下条件不满足即停止，不进入升级：目标模块已安装；可恢复备份点已建立；候选 HEAD 与
运行时源挂载一致；db=sc_clean。升级失败保留日志并按备份恢复，不叠加重试。
