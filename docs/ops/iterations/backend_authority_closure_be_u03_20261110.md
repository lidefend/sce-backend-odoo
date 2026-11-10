# BE-U03 Capability Entry Identity

状态：本地批次验收完成；主线集成、部署和数据库能力目录迁移未执行。候选分支
`codex/be-u03-capability-entry-identity-20261110`，基线为
BE-U02 候选 `017a395cc55ce91f73cec87d539feec95cb98ad7`。

## 目标

保留已有能力键和菜单派生键，但明确两类身份的职责：

- `business_capability`：由声明式 capability registry 维护，包含稳定能力身份、Provider 和资格语义。
- `entry_compatibility_alias`：由产品菜单投影产生，只表达当前产品入口，不证明业务能力、
  成熟度或执行资格。

本批不批量改名、不迁移数据库能力目录、不新建第二套能力平台。

## 层与范围

- `Formal Product Layer`：P0，支撑 P1 行业能力声明。
- `Layer Target`：能力身份、菜单入口别名、交付能力投影。
- `Module`：`smart_core`、`smart_construction_core`。
- `Why Here`：身份契约由平台机制提供，施工能力与菜单由行业标准模块声明。
- `Why Not Elsewhere`：前端、数据库目录数据和发布快照都不能自行创造能力身份。

## 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.capability.identity_boundary.unit` | PASS，4 tests；业务能力与菜单别名身份分离 |
| `make verify.backend.authority_closure.unit` | PASS，7 tests；G01 锚点与新身份契约一致 |
| `PYTHONPATH=. python3 scripts/ops/test_promote_product_ten_center_policy.py` | PASS，23 tests；五个锁定契约产物与源投影一致 |
| `make verify.capability.identity_boundary.orm` | PASS，18 tests；真实 capability registry 与产品策略维护一致 |
| `make verify.frontend.dev.incremental.unit` | PASS，107 tests；U03 路径均有专属目标 |
| `make ci.local.iteration` | PASS，affected targets=7；一次性 `sc_test` ORM 重验 18/18 |

第一次 ORM 失败为 `product_defect`：身份字段改变了锁定产品策略的序列化投影，而运行入口仍校验旧
基线。使用唯一生成入口 `scripts/ops/promote_product_ten_center_policy.py --write` 重生成运行时契约、
验证基线与 SHA 锁后重跑。第二次 ORM 18 项中 17 项通过，唯一失败是新测试错误地假设单菜单维护会
重算整个能力列表；测试改为验证实际能力生成器后重跑 18/18。菜单投影测试首次因缺少本地
`PYTHONPATH` 失败，属于验证工具调用错误，使用仓库根目录重跑 23/23。原始失败日志均保留。

提交钩子刷新了测试覆盖 registry、复杂度预算、拆分队列和测试清单；差异只描述新增测试与文件规模，
不改变产品断言，已纳入本批范围。

覆盖限制：

- `construction.menu.*` 与 `catalog.menu.*` 旧键未删除或重命名。
- 正式 `sc.capability` 数据库目录与代码 registry 的最终迁移/收敛未在本批执行。
- 本批证明身份与投影一致，不证明租户数据库已迁移、产品已发布或前端已验收。

## 回退

回退 BE-U03 提交即可。本批不改变 schema、数据库数据、ACL、发布快照或部署产物。
