# 244 · BNVA-02C-02A-R · 产品与低代码配置归属判定原则

## 待正式裁定的原则（Product Configuration Ownership Principle）

> 定义产品标准业务功能、默认业务页面结构和标准操作流程的配置，属于产品发布
> 所有权；低代码只提供对产品默认配置进行授权定制的能力，不承担产品默认业务
> 结构的定义责任。

## 五类归属

| 归属 | 含义 |
| --- | --- |
| PRODUCT_CORE | 产品核心默认配置，随产品版本演进 |
| PRODUCT_TEMPLATE | 产品提供的标准模板 |
| TENANT_CUSTOMIZATION | 授权后的用户差异配置 |
| LEGACY_COMPATIBILITY | 历史兼容 |
| RETIRED | 退役，保留追溯 |

## 证据事实（静态判定）

66 条种子配置的 `context.source` 全部为
`smart_construction_core.product_release`，无一条 `smart_core.lowcode.*`。
因此来源戳层面没有把产品配置误标为低代码。真实问题不是归属标签错误，而是
产品默认配置的完整性缺口与退役生命周期治理。

