# Backend Authority Closure Map v1

基线：`1ad805b621de6ced0a497c5a5f6e10bec358896d`。本文件只固定源码职责与调用事实，
不证明当前租户数据库、部署版本或用户验收状态，也不修改任何运行语义。

## 统一口径

后端只保留一种事实关系：一个事实有一个维护权威，可以有多个只读投影；一个业务动作有
一套执行规则，展示时预判和服务端执行时重验可以各发生一次。

| 能力维度 | 允许回答的问题 | 不允许替代的问题 |
| --- | --- | --- |
| 产品可用 | 当前订阅或功能开关是否允许该产品能力 | 用户能否看到入口、读取记录或执行命令 |
| 入口可见 | 当前身份的发布路由是否包含该菜单/动作 | 是否已经发布、企业是否启用、动作是否可办理 |
| 数据可访问 | 当前模型 ACL、记录规则、公司和业务范围是否允许 | 页面能否显示、产品版本是否交付 |
| 业务可执行 | 所属业务方法和执行入口是否允许当前状态下的命令 | 其他业务模型、其他记录或其他命令是否也可执行 |
| 管理可操作 | 平台或租户管理职责是否允许当前管理操作 | 是否自动进入客户业务数据 |

`construction.menu.*` 当前只能作为入口身份或兼容别名。它不构成独立业务能力资格，
不能据一个菜单带有该键就推导能力成熟度、发布资格或执行权限。

## 三条真实样本

| 样本 | 事实维护 | 交付与启用 | 运行投影 | 最终执行 |
| --- | --- | --- | --- | --- |
| 日常合同查询 | `ir.ui.menu`、`ir.actions.act_window`、`sc.general.contract` | 产品策略/有效发布快照；企业场景启用 | `published_route_authority` + `UiContractV2Handler` | `check_intent_permission` 重验 ACL/记录规则，再由 Odoo ORM 读取 |
| 付款申请审批 | `tier.review` 与 `payment.request` 审批状态 | 待办来源由任务事实产生，不从审批菜单反推 | `authorize_review_origin` + `UiContractV2Handler` | handler 重验组、范围和幂等；`payment.request`/`sc.approval.policy` 重验当前审批人和完整链路 |
| 平台职责 | namespace audience 与声明式 platform duty catalog | 平台控制身份仅决定管理职责面 | platform duty controller 只投影职责 | `_platform_env` 每请求重验平台身份；平台身份不提供租户业务范围 |

逐项源码引用、每条事实的唯一维护者和禁止授予项位于
`backend_authority_closure_map_v1.json`。守卫会解析这些路径、Python 符号、XML 记录、
模型名和 JSON 值；只写在文档里的“负责”不构成通过。

## 当前交叉点

| 缺口 | 当前源码事实 | 后续收口 |
| --- | --- | --- |
| `BE-U01-G01` | 菜单 XMLID 派生 `capability_key` | `BE-U03` 把能力定义、目录资格和入口兼容别名拆开 |
| `BE-U01-G02` | `permission.check` 的 `allow=true` 主要表达订阅/功能开关 | `BE-U02` 明确 API 命名、返回语义及消费者 |
| `BE-U01-G03` | 租户配置管理员可跳过通用 intent 组门槛和付款审批 handler 组门槛 | `BE-U02` 限定配置职责，业务命令回到业务身份 |
| `BE-U01-G04` | 场景发布构建使用发布者可见集合 | `BE-U04` 发布冻结产品定义，再按使用者投影 |
| `BE-U01-G05` | 行业 finalize 后置钩子仍修改最终页面 | `BE-U05` 将页面重定义迁回声明与编排层 |

这些是源码审查结论，不是对当前数据库已有未发布内容或越权访问的运行时证明。

## 保留边界

- Odoo 模型 ACL、记录规则、公司范围与业务范围继续是数据访问权威。
- `published_route_authority` 继续是当前用户发布导航权威，不能退回原生菜单存在性。
- `authorize_review_origin` 继续核对任务、审批人、状态、记录访问、公司和业务范围。
- `execute_button` 的当前契约、动作身份、状态和执行重验不因减少重复动作生产者而删除。
- 平台控制身份、租户配置身份和客户业务身份继续是三个不同职责。

## 验证

`make verify.backend.authority_closure.unit` 执行离线单测和仓库映射检查。测试必须非零收集，
并验证源码引用漂移、重复事实维护、投影授权、执行无重验和缺失后续卡片归属均失败关闭。
