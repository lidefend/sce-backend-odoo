# 产品视图契约载体 V1

英文版本：[Product View Contract Carriers V1](product_view_contract_carriers_v1.en.md)

## 定位

该契约是 P4 证据资产，用于保存正式产品视图经过 `LoadContractHandler` 最终响应后的 normalized 与 semantic 载体。它不是运行时契约权威，也不得补写、猜测或修复缺失能力。

## 采集边界

- 仅允许 `local.clean`：`sc-local-clean` / `sc_clean` / `^sc_clean$` / `demo_data=false`。
- 请求固定 `include=all`、`force_refresh=true`，避免 304 无载体响应。
- 运行库出现仓库无法证明只读性的 `app.contract.service` 时失败关闭。
- 采集使用独立数据库 cursor，并同时设置 session 与 transaction read-only；采集后必须回滚并恢复连接默认值。该保证覆盖数据库写入，不宣称拦截未登记的外部副作用。
- `tree` 是 Odoo 17 规范类型；不得向 handler 请求 `list`。
- 采集输入必须是同一候选指纹下重新导出并通过结构门禁的 `artifacts/contract/product_view_structure_candidate.json`，不得使用历史 tracked 基线代替。
- 数据库视图通过 `context.requested_view_id` 绑定本次运行记录；synthetic default 不得伪造该 ID。

## 载体规则

- normalized 只记录最终响应的 `/data/views/<type>`；search 额外允许 `/data/search`。
- `/data/native_view/*` 是投影别名，不得重复计数。
- semantic 只接受 `/data/semantic_page`，且必须满足 `version=v1`、`source=load_contract`。
- 所有值使用键排序、紧凑 JSON、UTF-8 计算 SHA-256；数组顺序保持不变。
- artifact selector 必须是可解析 RFC 6901 JSON Pointer。
- 每个 surface 精确绑定结构基线的 `contract_ref`、`view_ref` 和三项结构 hash。
- stable selector 只使用跨数据库稳定字段和 runtime authority，不包含数值 `menu_id`、`action_id` 或 `requested_view_id`。

## 失败策略

handler 错误、304、normalized carrier 缺失、surface 覆盖不完整、身份或 hash 漂移均使 exporter/guard 非零退出。semantic 缺失可以记录为 `normalized_only`，但不得推导为存在。

Schema：`contracts/schemas/product-view-contract-carriers-v1.yaml`。
