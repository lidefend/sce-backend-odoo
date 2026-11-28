# P1 企业场景配置事实边界

## 产品结果

企业初始化中的“业务场景配置”必须执行公司级场景启停动作，不得打开全局场景定义列表，也不得把场景交付路由当作按钮目标。

## 事实边界

| 事实 | 权威载体 | 责任 |
| --- | --- | --- |
| 场景定义 | `sc.product.scenario` | 产品级组织、导航入口与场景启用定义 |
| 企业启停 | 公司级 `ir.config_parameter` 场景启用事实 | 当前企业是否选择该已发布场景 |
| 场景交付 | `smart_construction_scene` 与 `enterprise.setup` | 只组合已发布场景、企业启停和原生菜单/动作，不反向成为配置按钮目标 |

工作台、集合等纯组合交付面可以没有独立业务事实，只由场景组合；企业初始化、场景启停等配置面必须有原生模型、视图与动作事实。

配置层硬门禁：配置 XML 和配置动作不得使用 `/s/`、`sc_web_route` 或 URL 场景动作作为目标；企业初始化也不得重新引用全局场景定义动作。门禁由 `verify.frontend.page_contract_boundary.guard` 执行。

后续统一规则：场景目标直接描述用户要完成的业务结果，并可作为声明式校验输入反向检查事实配置是否满足；事实层仍只提供模型、记录、关系、状态、权限和原生动作，不反向引用场景。

## 层级与边界

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | `smart_construction_core` / `smart_construction_scene` 原生企业场景启停应用、视图与动作 |
| Module | `smart_construction_core`, `smart_construction_scene` |
| Standard vs User-Specific | 施工产品标准 |
| Why Here | 产品场景定义、公司级启停事实及原生配置界面均属于 P1 产品能力 |
| Why Not Elsewhere | 前端不按按钮文字猜目标；P0 不承载行业场景语义；P3 不修补标准产品缺口 |
| Blast Radius | 企业初始化场景组、对应原生 action/view 与公司级启停方法；不改角色、ACL、已发布菜单、场景交付实现或持久数据 |

## 验证责任

| 检查入口 | 所属层 | 变化依据 | 状态 |
| --- | --- | --- | --- |
| `make ci.local.iteration` | 本地精准 | XML、模型方法及受影响定向测试 | passed |
| `make verify.enterprise.initialization.journey.orm` | 本地运行态 | 企业初始化与场景启停行为 | passed, 3 tests |
| `make verify.admin_close_01.backend.unit` | 本地精准 | 核心配置事实、权限及场景契约 | passed |
| `make verify.daily.permission_truth.capability.orm` | 本地运行态 | 企业配置与权限真实链路 | passed, 85 tests |
| `make verify.extension.lifecycle.orm` | 本地运行态 | 扩展生命周期矩阵 | passed, 2 tests |
| `make verify.frontend.dev.incremental.unit` | 本地精准 | 新事实路径选测映射 | passed, 287 tests |
| `make verify.frontend.page_contract_boundary.guard` | 本地精准 | 配置层禁止引用场景动作 | passed |
| `make verify.smart_construction_scene.module_baseline` | PR 集成 | owning module baseline | deferred_remote |
| `make verify.smart_construction_core.module_baseline` | PR 集成 | owning module baseline | deferred_remote |
| exact-head required PR CI | PR 集成 | 当前源/目标身份 | pending |

## 变更记录

- 初始根因：企业初始化按钮引用 `action_sc_product_scenario`，把场景定义配置误当为企业启停。
- 当前处理：从 `smart_construction_core` 基础页移除对场景定义动作的错误引用；由 P1 场景事实扩展提供 `sc.product.scenario` 的企业启停树视图、动作和对象方法，并让企业初始化页引用该原生动作。场景交付层保持只读组合。
