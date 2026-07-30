# FIELD-ARCH-P0-01 结果

`FIELD_ARCH_P0_01_RESULT=FAIL`

## 结论

字段数值语义修复有效，但产品字段架构尚未收口。`p1_visible_*` 不是租户私有映射键：
它们由 P1 产品源码动态注册为全局非存储字段，并进入运行时视图契约。
因此没有历史值物理列不等于没有公共产品污染。

同时，运行库存在 11 个无 company/tenant 归属的手工扩展物理列。
数据库按客户隔离可阻止客户数据库之间共享业务值，但不能解决同库多公司字段发现，
也不能让新租户获得纯净的标准产品字段集合。

## A-H 直接回答

- A：`p1_visible_*` 当前属于 P1 产品源码中的历史兼容层，不是租户映射元数据。
- B：它们污染公共产品源码和全局模型元数据，但自身不形成物理列；另有 11 个手工扩展形成公共物理列。
- C：客户数据库之间不可互相发现字段；同一租户库的不同公司会发现相同别名和手工字段定义。
- D：否。单公司产品候选库仍有 801 个别名，当前源码安装会生成 759 个。
- E：正式审批、计算、聚合和统计不依赖别名；但 862 个页面/搜索/导出兼容契约仍依赖别名身份。
- F：会。已观察到 151 个源码删除后仍残留的元数据，其中 103 个仍被视图引用；手工扩展也会增加每租户 schema。
- G：不满足。正式字段本身稳定，但行业产品包仍携带历史身份，扩展字段载体也未治理。
- H：先切换正式视图和契约，再隔离租户扩展载体，最后以可回滚迁移清理旧元数据并建立新租户门禁。

## 基线

- branch: `audit/field-arch-p0-01`
- start SHA: `2b68039cfc5410b22c54ded596140ef2470ad5d4`
- end SHA: `2b68039cfc5410b22c54ded596140ef2470ad5d4`
- tree: `1d1c64435da6f0d2eec4bc86f4086925b53dce85`
- b15535c ancestor: `true`

## 分母与落点

- 产品 Python 静态字段声明：4712
- 产品源码动态历史别名：759
- 运行时 ir.model.fields：21992
- public schema 物理列：14663
- 运行时历史别名：910
- 源码与运行时交集：759
- 源码已移除但注册表残留：151
- 运行时可达历史字段契约：862
- 仍被视图引用的旧别名：103
- 仅注册表残留的旧别名：48
- 历史别名物理列：0
- 租户手工扩展公共物理列：11

## 依赖判断

- 正式审批/计算/统计权威依赖历史别名：0
- 展示/搜索/导出兼容依赖：862
- 已解析正式来源：747
- 无正式来源：12
- 已解析正式数值来源：146

747 个已解析别名的数值、排序、筛选和合计由正式字段承担；12 个未解析别名必须
失败关闭并等待业务决定。页面列身份和兼容搜索仍直接依赖别名，
所以“正式业务不再依赖历史字段”只能对计算权威成立，不能对整个产品运行成立。

## 双企业与新租户

- 跨客户数据库字段发现：0
- 同租户跨公司全局字段定义：921
- 普通财务管理角色跨公司值读取：0
- 跨客户数据库契约泄露：0
- 同租户 A/B 公司相同付款契约别名数：28
- 新租户纯净初始化：FAIL
- 独立验收库别名数量：{'isolated_customer_uat': 910, 'sc_frontend_acceptance': 801, 'one_company_product_candidate': 801}

客户数据库之间的字段和值由数据库边界隔离；直接 `ir.model.fields` 元数据接口也
对普通用户拒绝访问。但同一租户库的正式页面契约向两个公司投影同一组历史别名，
字段定义不是公司级隔离。更关键的是，新客户库会从 P1 源码重新获得整套历史别名。

## 规模判断

- schema growth model: PER_TENANT
- metadata growth model: UNKNOWN
- view growth model: UNKNOWN
- cache growth risk: MEDIUM
- multi-tenant scale assessment: FAIL

按客户独立数据库可把手工列膨胀限制在单租户库，但当前产品每安装一次就注册整套
历史别名；且已观察到 151 个跨版本残留，说明元数据/视图增长不是稳定常数。

## 最终判断

- product_formal_fields_stable=PASS
- tenant_extension_isolation=FAIL
- legacy_mapping_metadata_isolated=FAIL
- industry_generalization=FAIL
- production_field_architecture_ready=FAIL

## 后续任务

1. FIELD-ARCH-P0-02 formal-view cutover and legacy alias dependency removal
1. FIELD-ARCH-P0-03 tenant extension metadata/value carrier isolation
1. FIELD-ARCH-P0-04 reversible stale ir.model.fields/view cleanup migration
1. FIELD-ARCH-P0-05 fresh-tenant and cross-tenant field discovery regression gate

## 机器摘要

```text
FIELD_ARCH_P0_01_RESULT=FAIL
SOURCE_DECLARED_FIELDS=5471
IR_MODEL_FIELDS=21992
PUBLIC_PHYSICAL_COLUMNS=14663
LEGACY_PROJECTION_FIELDS=910
RUNTIME_REACHABLE_FIELD_CONTRACTS=862
UNINVENTORIED_FIELDS=0
LEGACY_FIELDS_IN_PRODUCT_SOURCE=759
LEGACY_FIELDS_IN_GLOBAL_MODEL_METADATA=910
LEGACY_FIELDS_AS_PUBLIC_COLUMNS=0
PUBLIC_SCHEMA_TENANT_FIELDS=11
UNCLASSIFIED_FIELDS=0
LEGACY_ALIAS_BUSINESS_DEPENDENCIES=0
LEGACY_DISPLAY_ONLY_DEPENDENCIES=862
UNRESOLVED_FORMAL_SOURCES=12
CROSS_TENANT_FIELD_DISCOVERY=0
INTRA_TENANT_CROSS_COMPANY_FIELD_DISCOVERY=921
CROSS_TENANT_VALUE_ACCESS=0
CROSS_TENANT_CONTRACT_LEAKAGE=0
NEW_TENANT_CLEAN_BOOTSTRAP=FAIL
SCHEMA_GROWTH_MODEL=PER_TENANT
METADATA_GROWTH_MODEL=UNKNOWN
MULTI_TENANT_SCALE_ASSESSMENT=FAIL
PRODUCT_FORMAL_FIELDS_STABLE=PASS
TENANT_EXTENSION_ISOLATION=FAIL
LEGACY_MAPPING_METADATA_ISOLATED=FAIL
INDUSTRY_GENERALIZATION=FAIL
PRODUCTION_FIELD_ARCHITECTURE_READY=FAIL
```

## 审计方法与安全边界

- Python AST 枚举 P0/P1 字段声明和动态别名生成。
- 只读 SQL 枚举全部 ir.model.fields、public schema 列和 ir.ui.view 字段引用。
- 两公司 ORM 探针使用临时财务管理角色并在同一事务中回滚。
- 另两个隔离数据库只读取字段数量，用于区分客户数据库与公司边界。
- 未读取或输出业务字段值；仅对 11 个手工字段统计非空记录数量。

本轮没有删除字段、修改业务值、升级数据库或覆盖 18093。
所有临时 ORM 用户/公司上下文探针均显式回滚。
