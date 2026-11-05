# 后端事实与执行收敛：BE-00 / BE-01

状态：verification_pending。源码基线：`c819daff496deab474bf97b84031bfd50db148bc`（#812 已合并）。本批不修改公共契约或前端。

## 正式维护与执行边界

| 事实 | 正式维护位置 | 生效与消费 | 执行边界 |
|---|---|---|---|
| 入口与场景 | `ir.ui.menu`、`sc.product.scenario/entry`；业务场景、菜单配置入口 | `scenario_surface_projection.load_runtime_surface/runtime_menu_scope` 同供导航与企业过滤 | `runtime_route_authority` 保留原生发布、权限及作用域；缺失拒绝，豁免只绕过场景启用 |
| 页面组织 | `ui.business.config.contract`；表单配置入口 | 启用且发布、模型/公司/角色/Action/View 适用、运行期校验后进入 V2 | 保存仍由字段政策、权限、ORM 约束决定 |
| 字段政策 | `ui.form.field.policy`；字段维护入口 | 公共契约投影当前政策 | 服务端写入重新校验 |
| 审批 | `sc.approval.policy/step`；审批配置入口 | 当前公司优先、共享政策其次；投影 OCA tier definitions | 付款方法启动/推进审批，既有运行实例优先 |
| 状态 | 付款记录及 `state_machine.py` | `workflow_contract_service` 投影状态与编辑性 | 状态转换仍是代码；不存在可任意配置状态机的正式入口 |
| 动作 | 原生视图按钮、`ir.actions.*`、业务配置 | V2、工作流服务；仍有 `PROFILE_BY_MODEL` | `execute_button` 重取当前动作契约并授权，再执行模型方法 |

企业启用的正式处理器 `scenario_activation.py` 经 `tenant_scene_activation.write_tenant_enablement` 写系统参数 `sc.scene.tenant.enablement.*`；`sc.scene.company.enablement` 是兼容回读，不是唯一存储权威。本批同源的是场景归属，不能宣称企业启用存储已归一。

## 目标库升级前观察

通过受管 `make audit.daily.demo.data_inventory DAILY_DEMO_OBSERVATION=scenario`，绑定远端源码 `54bed83383ee2e03773141430bdd6d50ca4f932b`，只读事务观察 demo duty `sc_demo`：

- 17 个启用场景，79 条入口关联。
- 注册表尚无 `sc_scenario_exempt`；不是新版本下的 missing 判定，也没有旧候选 true 值可供追溯。
- 场景种子和外部中心标记为 1；场景入口 scope 标记不存在。
- 表单配置、审批配置、字段维护、菜单配置、业务场景五个正式菜单都存在且当前无场景关联。
- 原始证据：`.runtime/be00-be01-scenario-before.log`；版本检查 `.runtime/be00-be01-entry-before.json` 指出服务器尚未部署 #812。只读观察 PASS 不代表产品验收 PASS。

升级不会自动为这五项授予豁免。所有者已明确同意这五项显式豁免；这是本次维护决定，不是由缺关联推断历史合法性。执行器沿正式 ir.ui.menu.write 实施，保留原生资格和角色校验。未知菜单始终不自动豁免。

## BE-01 尚待闭合

1. 复用干净的既有部署工作树 release/be01-daily-c819daff，按既有 Make 部件入口发布固定主线 c819daff；保留主线集成工作树的他人改动。代码同步、构建、服务刷新、两库声明模块升级、最终入口版本检查已通过。
2. 五项配置已全部由 false 显式改为 true，逐项前后值及角色组保留在 `.runtime/be01-configure.log`；独立进程回读通过。
3. `demo_full`（uid 42、su=False）实际初始化与服务端授权服务对照已通过：291 missing 双拒绝、72 bound 双允许、7 bound 双拒绝、4 exempt 双允许、1 exempt 双拒绝。逐一核验全部导航对，范围限当前可检索动作菜单，不包含 HTTP 认证及浏览器。
4. 重复升级 demo 已通过，独立回读五项声明均保持 true，角色组不变；再运行导航/服务端对照结果一致。证据 `.runtime/be01-repeat-readback.log`、`.runtime/be01-repeat-delivery.log`。撤销与删除关联的不恢复规则沿用已合并 c819 的定向 fixture 证据，本次不破坏性修改日常库关联。

## 后续批次与公共接口

BE-02：`product_menu_source.py` 的 JSON 发布资格，以及 `product_policy_sync`、`locked_menu_policy_contract` 的锁定文件校验仍存在。区分运行期事实维护与发布时身份/引用/摘要证明；原生能力发布与 `sc.scene/sc.scene.version` 组合发布分别诊断。

BE-03～05：仅以实际页面及付款为样本，核对 `core_extension` finalize/normalize Hook、`workflow_contract_service.PROFILE_BY_MODEL` 的分组、标签、顺序、默认展示及动作组织。可配置项迁入既有事实模型；金额检查、锁、事务、审批实例、状态转换及审计保留代码执行。

FE-00＋FE-01 已有独立工作分支 `codex/fe-converge-01-presentation`，本批不覆盖该工作。现有契约保持稳定；缺失业务声明在后端登记处理，前端不增加模型判断作为补偿。

## 本批回报

- 已有正式配置能力：场景名称/顺序/关联、明确豁免；适用范围内发布页面配置；审批启停、公司、步骤、执行组及金额上下限。目标库已部署 c819 并升级；五项豁免维护已落库。
- 本批没有删除产品代码或运行时文件依赖；增加的是现有受管审计入口的场景只读模式及五项显式维护操作。#812 已统一归属读取，BE-02 文件约束待收口。
- 仍需代码：事务、锁、金额约束、状态转换、审计与服务端授权；页面 Hook 中的常规配置缺口另批迁移。

## 五项显式维护入口

`make daily.demo.scenario.configure` 默认只读回读。`SC_SCENARIO_CONFIGURATION_PHASE=apply` 要求专用确认；在既有 demo duty 上绑定精确源 SHA、数据库 UUID、五项 XMLID 与菜单 ID，任一场景绑定冲突即停止。仅写 `sc_scenario_exempt`，提交前确认角色未变；跨进程重新回读。原始修改前值记录在配置日志中，回退须按记录恢复这一个字段，不能重新初始化场景或覆盖其他菜单。

该入口属于 P4 一次性维护，已作独立代码复核并登记用途；不成为新的业务规则来源或无人值守 CI。

## 仍未完成的产品入口

业务场景维护菜单 `smart_construction_core.menu_sc_product_scenario_business_config`（720）已显式豁免，但在 demo_full 的原生发布 authority 中仍未交付，导航及服务端均拒绝；原生产品目录 JSON 不包含该 XMLID。该事实不应通过更多场景豁免或前端分支掩盖，纳入 BE-02 的正式产品目录维护/发布链收口。其余四个配置入口双端允许。

因此：c819 主线版本部署、五项配置写入及授权服务对照已完成；五入口完整可用和整个架构收敛仍未完成。新增 P4 工具尚未进入主线，也未将它们当作已发布产品源码。
