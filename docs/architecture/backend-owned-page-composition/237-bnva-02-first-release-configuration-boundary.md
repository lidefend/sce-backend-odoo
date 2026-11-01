# 237 · BNVA-02 · 首次产品发布配置边界

## 原则

首次产品发布时：

1. 低代码平台是能力提供者（表单/Section/FieldOwnership 配置器、校验、发布、版本）。
2. 产品默认业务配置由产品（代码）提供，是当前版本的权威定义。
3. 用户低代码配置数据尚不存在，由用户未来创建。

能力建设 ≠ 用户配置数据迁移。不要为了证明 Migration Runner 有用而人为制造
迁移数据。

## 对 84 条配置的重新定位

这 84 条是**产品默认配置资产**，不是历史用户数据：

- 46 条 form_productization：Section 已带 fields，缺 Identity 声明 → 补 Identity。
- 19 条 form_sections_v1（title-only）：逐项判断是否属于首次发布产品功能，退役不自动恢复。
- 1 条 identity-only 伴生：核实关联。
- 18 条 native/tree/search：原职责管理。

## Migration Runner 定位

保留纯逻辑核心、SeedIdentity/migration_id、幂等状态机；暂缓真实 Odoo 集成与
历史用户数据迁移；未来出现真实租户配置 + 不兼容结构变化时再启用。

## noupdate 复检

已切 noupdate=1 的 32 个文件需复检：哪些真应冻结，哪些产品默认需随模块升级
持续更新。暂不回滚/重改，先厘清更新所有权。

