# 产品菜单治理 M0–M3

本目录是 P4 只读治理产物，不是正式产品菜单配置。正式菜单仍由 P1 行业模块、P2 用户模块和 P3 低代码配置按既有权威链提供；这里不修改任何 XML ID、action、权限或运行时数据。

## 架构定位

- Formal Product Layer：P4 运维交付工具。
- Layer Target：静态菜单资产审计、证据 Schema 与候选信息架构评审材料。
- Module：`scripts/verify` 与 `docs/engineering_convergence/menu_governance`。
- Standard vs User-Specific：本轮不作 P1/P2/P3 产品归属结论，只记录候选与未决事项。
- Why Here：盘点、差异、迁移草案和验收夹具属于可重放治理证据。
- Why Not Elsewhere：P0 不应承载施工命名，P1/P2/P3 在产品评审前不应接收猜测出的配置，前端不得硬编码菜单树。
- Blast Radius：只新增生成器、测试和文档；菜单 XML、数据库、ACL、action、Shell、图标、设计令牌与运行时解析均不变。

## 单一生成入口

```bash
python3 scripts/verify/menu_governance_inventory.py
python3 scripts/verify/menu_governance_inventory.py --check
python3 -m unittest scripts/verify/test_menu_governance_inventory.py
```

生成器拥有以下文件，禁止人工修改：

- `menu_capability_inventory.json`
- `menu_capability_inventory.md`
- `menu_migration_mapping.csv`

`--release-candidate` 是未来 M4+ 的失败关闭入口；当前 M1 资产账含有待治理风险，因此本阶段不以该入口通过作为完成条件。

## 阶段状态

| 阶段 | 状态 | 结论 |
| --- | --- | --- |
| M0 | 完成 | 精确 SHA、静态口径和未覆盖范围已冻结 |
| M1 | 完成 | manifest 加载链的静态菜单资产覆盖 100% |
| M2 | 框架完成 | 静态 action/group 链已记录；运行时角色、路由与标杆会话证据未采集 |
| M3 | 候选框架完成 | 词典、候选三级树、逐项迁移表与产品待决项已建立，未发布产品事实 |

详细结论见 [M0 基线](M0_BASELINE.md)、[M2 证据框架](M2_CAPABILITY_EVIDENCE.md) 和 [M3 候选方案](M3_NAMING_TAXONOMY.md)。
