# 195 · BNVA-02B-02C-01 · 配置所有权矩阵

| 来源 | 创建者 | 维护者 | 修改方式 | 升级覆盖 | 回滚 |
| --- | --- | --- | --- | --- | --- |
| 代码种子（product_release） | 模块 XML（su） | 代码模块 | Git + 模块升级 | noupdate=0 重写；=1 保留 | 版本快照 |
| 用户配置（lowcode） | 前端用户 | 配置管理员 | 前端草稿/审批/发布 | 不受升级影响 | 版本快照 + restore |
| 用户覆盖种子 | 前端用户 | 配置管理员 | 独立公司级配置 | 不受升级影响 | 版本快照 + restore |

## 关键机制

- 来源戳在 `contract_json.view_orchestration.context.source`，不是独立 DB 字段。
- 非 su 写全局种子被 `company_id` 校验阻断；覆盖只能走独立公司级配置。
- `source_authority_json` / `payload_sha256` / `definition_sha256` / 版本快照提供追溯。

