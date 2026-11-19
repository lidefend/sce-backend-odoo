# SCENE-CLOSE-03: 平台业务场景组合管理闭环

Status: active

Base: `630c3338274cf3906522f06f7011cf5ba9958f66`

Branch: `feature/scene-close-03-admin-composition-ux-20261120`

## 产品结果

管理员能够分别判断原生能力是否可用、产品组合是否引用该能力，以及企业是否启用相关业务场景。发布控制台分别展示当前草稿、冻结候选和当前生效版本的业务场景组合，并能进入已有的共享 `sc.product.scenario` 原生维护视图。

## 层级与作用域

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P0/P1 |
| Layer Target | 平台管理与发布读模型；施工业务场景共享维护载体 |
| Standard vs User-Specific | 平台机制与施工产品标准共享定义；不是企业私有配置 |
| Why Here | `smart_core` 生产通用发布/能力契约，`smart_construction_core` 拥有原生场景定义 |
| Why Not Elsewhere | 前端不得推断产品归属，也不得把共享定义标成产品私有 |
| Blast Radius | 能力目录、发布控制台、业务场景维护入口和业务配置状态文案 |

## 验证边界

本轮保持纯契约验证：真实生产函数、内存 I/O 和现有前端消费链。ORM、模块基线、模块升级、fixture、浏览器矩阵、环境重建与部署不在本轮范围。

## 已实现

- 能力目录将原生执行可用性从产品资格、产品发布和企业启用事实中拆开；未收录或未发布不再撤销已成立的原生执行资格。
- 发布冻结与控制台草稿共用同一业务组合装配函数，避免持久化策略与维护源产生两套草稿。
- 发布控制台分别投影当前草稿、冻结候选和当前生效组合，并比较名称、顺序、intent 与入口变化。
- 候选和生效组合只读取各自冻结快照，维护源后续变化不会改写这两态。
- 后端声明已有 `sc.product.scenario` 原生 action/menu、共享维护作用域、真实读写可达性和返回回读契约。
- 前端消费严格解码三态组合、维护入口和错产品身份；进入维护后使用原产品控制台路径返回，组件重新挂载时重新请求控制面。
- 业务配置提示已改为“保存到待发布变更 → 草稿预览 → 统一发布”，不再声称不支持未发布效果预览。

## 纯契约验收

| 编号 | 结果 |
| --- | --- |
| C1 | 原生权限通过、产品未取得资格时，`available_to_current_user` 与 `visibility.can_use` 仍为真，产品资格事实保持未满足 |
| C2 | 菜单、动作组或模型 ACL 拒绝时，原生可用性继续拒绝 |
| C3 | 控制台草稿与冻结流程调用同一个组合装配函数 |
| C4 | 草稿、候选、生效各自携带独立身份和组合内容 |
| C5 | 名称或 intent 改变但数量不变时，后端差异仍识别变化 |
| C6 | 空组合、无候选、无生效版本分别返回明确状态 |
| C7 | 维护目标来自后端 action/menu 身份；前后端均拒绝错产品；返回原产品路径后重新加载 |
| C8 | 发布和回滚动作回读重新解码完整控制面，组合三态不从前端推导 |

## 验证结果

`ci.local.iteration` 已通过，受影响目标包括能力目录、发布控制台后端、产品中心、已发布面、场景导航消费、前端契约单测、lint、严格类型和增量规划回归。frontend lint 仅保留仓库已有的 warning，没有 error。ORM、模块基线、升级、浏览器矩阵和部署未执行。

首次远端纯契约分片错误地在无 `node_modules` 的 runner 上选择了依赖 esbuild 的
`verify.frontend.platform_capability_explorer.unit`。该目标仍由安装受锁前端依赖的
`frontend_release_gate` 执行，现仅从 `.github` 契约专用 target 列表移除；
Python/Node 无依赖的控制面检查范围不变。

## 复审修复

- 维护入口只在普通当前用户环境中判断模型 `read/write`，`sudo()` 仅用于读取模型字段元数据；菜单组和动作组独立校验。
- 施工维护提供者、action/menu、共享作用域和产品适用性由 P1 扩展声明；P0 只做通用投影，平台及其他行业产品明确返回不适用。
- `release.operator.surface` 成为维护返回回读 intent；返回产品取自该声明而不是可能过期的 URL。
- `return_url`、`return_label`、`return_product_key` 已进入通用导航保留字段，ActionView 实际消费并生成返回控制台链接。
- 场景与入口排序使用有符号整数；中心顺序显式 `0` 不再被默认成 `10`，`0 -> 10` 会产生差异。
- 冻结候选的业务场景摘要和数量优先读取 `snapshot_json.release_draft`，不再只依赖 `meta.release_draft`。

一次增量规划因新增 P1 扩展文件自动选中页面冻结和权限真值 ORM；运行在首个
`verify.daily.permission_truth.capability.orm` 处被立即中断，日志只有
`STATUS: interrupted`，未产生测试结论。该目标、页面冻结目标和项目冻结目标已加入本轮
明确排除集合；中断结果不计为通过。
