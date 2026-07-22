# ADR-001：生产平台内核单库共置

- 状态：Accepted
- 范围：current production release
- 决策：`single_database_colocated_platform_core`
- 业务数据库：`sc_production`
- 平台数据库：`sc_production`
- 未来双库：必须单独立项迁移

## 背景

`smart_core` 是平台逻辑边界，但逻辑边界不等于必须使用独立物理数据库。当前生产只有一套 Odoo/Nginx 运行时、数据库备份恢复链路和权限边界；`sc_production` 已安装 `smart_core` 并持有平台模型、产品策略和登录路由。代码此前在配置缺失时猜测 `sc_platform_core`，形成“运行时单库、代码猜双库”的半配置状态。

## 决策

本期生产保持平台能力启用，并由 `sc_production` 同时权威持有业务数据和当前租户的平台数据。`smart_core.platform_release_db` 必须显式设置为当前服务端锁定的 `sc_production`。`system.init` 只能从当前 registry 读取活动发布快照；客户端 header、body、URL、Cookie 均不参与业务库或平台库选择。

下列模型在本期生产与业务模型物理共置：

- `sc.subscription.plan`
- `sc.subscription`
- `sc.entitlement`
- `sc.usage.counter`
- `sc.ops.job`
- `sc.product.policy`
- `sc.edition.release.snapshot`
- `sc.release.action`
- `sc.login.route`
- tenant payload/import 相关模型

仓库通用代码不再把 `sc_platform_core` 当作缺省数据库。生产缺少配置、配置与当前数据库冲突、或缺少有效活动快照时必须失败关闭，不得展示未经发布快照约束的完整导航。非生产独立平台库只能通过显式配置启用。

## 约束

- 禁止在 `sc_production` 与 `sc_platform_core` 之间隐式回退、双读或双写。
- 独立 `sc_platform_core` 仅属于非生产开发/实验拓扑，不是生产事实来源。
- 不废弃订阅、授权、套餐、用量或发布治理能力。
- 物理共置不削弱租户、公司、ACL、记录规则或业务范围隔离。
- 快照必须由版本控制的产品策略和现有发布服务生成，不能手工插表或复制开发数据。
- 数据库与对应 filestore 必须成对备份、校验并在隔离容器恢复演练。

## 后果

本期无需引入未经验证的双库权限、一致性、备份、恢复和监控设施。未来若采用双库，必须新增 ADR，并独立完成数据归属、迁移、跨库一致性、最小权限、备份恢复、监控和回滚设计；不得在普通发布中暗中切换。

英文版本：[ADR-001-single-database-colocated-platform-core.en.md](ADR-001-single-database-colocated-platform-core.en.md)
