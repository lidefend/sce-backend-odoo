# 206 · BNVA-02D · 配置所有权与数据边界

## 三层模型

1. Capability Plane：低代码能力（编辑器/设计器/校验/审批/发布/版本），不拥有业务事实。
2. Configuration Metadata Plane：`ui.business.config.contract` 承载的配置元数据。
3. Business Data Plane：Odoo 业务模型承载的真实业务数据。

## 七项原则

1. 低代码平台是配置能力提供者，不是业务数据所有者。
2. `ui.business.config.contract` 是配置元数据管理载体。
3. Odoo 业务模型是业务数据权威。
4. XML 种子提供产品默认配置。
5. 用户配置是经过授权的租户级元数据定制。
6. 产品升级与用户配置生命周期相互独立。
7. 运行时 Resolver 负责确定有效配置，不负责创造业务事实。

## 来源重定义

| 项目 | Odoo 代码种子 | 用户低代码 |
| --- | --- | --- |
| 本质 | 产品默认配置 | 配置编辑能力 |
| 权威 | Git / Odoo Module | 授权后的配置元数据 |
| 生命周期 | 模块版本 | 草稿/审批/发布 |
| 修改权 | 开发团队 | 授权配置管理员 |
| 业务数据所有权 | 不拥有 | 不拥有 |

`smart_core.lowcode.business_config` 是配置来源标识，不表示低代码拥有独立业务数据。

