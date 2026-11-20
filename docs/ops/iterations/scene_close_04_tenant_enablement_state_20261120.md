# SCENE-CLOSE-04：企业场景启用事实与当前可用性收敛

Base/main: `80f98fa25deea70f658ffecd93b0668103928c85`

Branch: `fix/scene-close-04-tenant-enablement-state-20261120`

## 产品结果

平台发布可用性变化时，企业原来保存的场景启用选择继续准确显示。对于当前目录仍能识别的场景，有维护权的管理员可以执行停用；写入后按原公司、原场景回读，并刷新目录与导航。不可用的 inactive 场景不能被重新启用或通过企业选择恢复导航资格。

## 层级与作用域

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | `smart_construction_scene` 企业场景目录、启用事实和既有前端消费 |
| Standard vs User-Specific | 施工产品标准与公司运行时选择 |
| Why Here | 企业持久化选择、当前产品可用性和场景导航事实由施工场景域生产 |
| Why Not Elsewhere | 前端不自造状态或动作；平台发布继续决定当前可用性；原生 ACL 继续决定执行资格 |
| Blast Radius | 企业场景目录、停用/启用动作、目录刷新、导航过滤和既有前端激活消费 |

## 验证边界

本轮只执行纯契约、既有真实生产函数和前端消费链测试。ORM、模块基线、模块升级、fixture、浏览器矩阵、部署和全产品验收不在本轮范围。

## 实施前责任门禁

| Gate | 状态 | 责任入口 | 依据 |
| --- | --- | --- | --- |
| 精确 base/HEAD 与范围 | required | `make agent.run.resume`、增量规划器 | 固定 base `80f98fa2`、本批分支和 11 个登记路径 |
| owning module baseline | excluded | `smart_construction_scene` ORM 基线 | Owner 明确限定纯契约范围，不声称 ORM 覆盖 |
| 既有受影响测试族 | required | `verify.navigation.publication_consumers.unit` | 场景目录、实际激活 handler、导航与事实边界 |
| 新增行为测试 | required | `test_tenant_scene_activation.py` | 保存事实、当前可用性、动作、写入回读与导航拒绝 |
| 契约消费 | required | `verify.frontend.workspace_scenario_lifecycle.unit` | 真实 `useScenarioActivation` 与受控传输 |
| 前端生产源码 lint/type/build | excluded | 前端源码车道 | 本批只修改既有 TypeScript 消费测试，由已登记 esbuild 目标实际执行 |
| runtime/browser | excluded | 受管运行与浏览器车道 | Owner 明确限定纯契约，不产生部署或用户验收结论 |
| 远端必需门禁 | required | 四项受保护 PR 检查 | 待 clean 候选推送后绑定精确 HEAD |

## 执行记录

- Owner preparation: new run registered on main `80f98fa2`; LC-CONTEXT-01 post-merge bookkeeping commit `c4e6ec2b` is carried by the branch history.
- Product implementation: catalog enablement now reads the saved company selection independently from current product availability; a saved true selection remains disableable while navigation continues to fail closed.
- Product implementation: inactive or unqualified scenes never gain enablement through the new projection, and an explicit disable writes the original `business.v1:` key for the original company and is accepted only after authoritative readback.
- Frontend consumption: an unavailable but saved-enabled scene exposes only the declared `disable` action whose `enabled:false` is the requested target state; the real consumer writes that target, accepts the false readback, refreshes navigation and consumes the disabled catalog response.

## 验证结果

- `test_tenant_scene_activation.py`：103 项通过。实际生产链覆盖“目录生成 → 停用动作 → `scenario.activation.set` → 原公司/原存储键回读 → 目录重读”；不可用场景强发启用返回 409，企业保存值未被发布可用性变化改写。
- `verify.navigation.publication_consumers.unit`：266 项前置及目标测试通过。
- `verify.frontend.workspace_scenario_lifecycle.unit`：471 项前置、lifecycle 与持久化案例通过；新增 `business_scenario_unavailable_disable_test` 为 5 个案例，包含请求参数、false 回读、导航刷新、目录重读和旧停用动作不残留。
- `make ci.local.iteration`：exit 0，实际执行 5 个必需目标；无未映射路径、无缺失登记、无复用，ORM 目标仅进入 `excludedTargets`。
- 其他登记目标：恢复入口 67 项、增量选择 187 项、场景事实边界 1 项、账本 18 项、CI 契约 475 项、中心投影 9 项，均通过。
- `ci.delivery.freeze.prepare`：通过。测试清单、复杂度报告、拆分队列、契约结构指纹及其他受跟踪生成证据均 current；场景测试文件因新增回归体量上升，复杂度报告和拆分队列据此刷新。

首次前端定向运行发现新增用例未恢复测试会话的公司上下文，导致后续既有 readiness 用例看到错误公司。该问题属于测试夹具隔离，已将测试恢复为进入前的公司后重新执行；产品消费逻辑未因此修改。

ORM、模块基线、模块升级、fixture、浏览器矩阵、部署和全产品验收未执行，也不由本轮结果推定通过。
