# 平台、行业与客户租户数据库架构治理规则

状态：生效
规则版本：1.0
生效日期：2026-07-24
权威入口：仓库根目录 `AGENTS.md`

本文件是数据库架构的单一权威规则正文。其他文档只能引用或摘要本规则，不得复制出
另一份竞争性规则。该规则约束数据库创建、复制、升级、迁移、销毁、模块生命周期、
租户开通、用户与多公司设计、fixture、验收环境、filestore、session、备份恢复以及
跨租户接口和分析。

## 1. 架构模型与术语

```text
DATABASE_ARCHITECTURE_MODEL=CONTROL_PLANE_PLUS_DATABASE_PER_CUSTOMER_TENANT
```

正式架构由三层组成：

1. 平台控制面；
2. 行业能力与可选公共目录；
3. 每个客户租户独立的业务数据面。

辅助数据存储不改变上述三层模型，其边界冻结如下：

| 存储 | 独立性 | 允许存放 | 禁止存放 |
|---|---|---|---|
| 平台控制库 | 必须独立 | 租户注册、路由、版本、授权、订阅、运行状态和审计索引 | 客户项目、合同、付款、员工档案等业务数据 |
| 行业能力层 | 原则上不是业务数据库 | 版本化模块、字段/字典/表单/流程/权限模板和报表定义 | 客户实际业务记录 |
| 客户租户库 | 每个企业客户独立 | 本客户的用户、组织、项目、合同、财务、审批和附件元数据 | 其他客户数据 |
| 平台运维库 | 建议独立 | 任务执行、迁移批次、监控、备份目录和发布记录 | 客户业务正文和敏感附件 |
| 分析汇总库 | 按需独立 | 经授权、脱敏或聚合后的跨租户指标 | 未授权业务明细和身份数据 |

“客户租户”表示企业客户或受合同、法律、审计约束的独立组织；“自然人用户”表示
租户库内的人员账号。不得用“用户”同时指代两者。环境数据库隔离、客户租户数据库
隔离和 Odoo 多公司是三个不同维度，必须分别判定。

本规则规定目标架构和所有新租户的强制边界。历史
`docs/adr/ADR-001-single-database-colocated-platform-core.md` 仅记录当期单一生产
运行时中平台模型与该租户业务模型共置的历史决策，不得据此让不同客户共享业务库，
也不得替代本规则对独立平台控制库、新租户和生产库创建方式的约束。既有环境若要迁移
到本规则，必须另立迁移任务，不得在普通安装或升级中隐式切换。

## 2. 平台控制数据库

```text
PLATFORM_CONTROL_DATABASE_REQUIRED=true
PLATFORM_CONTROL_DATABASE=sc_platform_control
PLATFORM_CONTROL_DATABASE_LOGICAL_NAME=sc_platform_control
PLATFORM_CONTROL_DATABASE_CONTAINS_CUSTOMER_BUSINESS_DATA=false
PLATFORM_ADMIN_NE_TENANT_DATA_ACCESS=true
```

平台控制库只允许保存：

- 租户注册及稳定 `tenant_id`；
- 租户与数据库、域名、入口的路由映射；
- 产品版本及行业包版本；
- 租户启用、冻结、归档等生命周期状态；
- 授权、订阅及许可状态；
- 数据库创建、升级、备份、恢复任务元数据；
- 源码 SHA、镜像 digest、环境身份；
- 跨租户运维审计索引；
- 健康状态和容量元数据。

平台控制库禁止保存：

- 客户项目、合同、付款、结算和台账；
- 客户员工和用户档案；
- 客户审批正文及审批轨迹；
- 客户内部业务角色和项目授权明细；
- 客户业务附件；
- 其他客户业务正文或敏感数据。

平台管理员拥有租户生命周期管理权，不因此自动获得租户业务数据访问权。控制面任务
必须使用控制面专属权限；租户业务访问必须另有明确授权和审计。

## 3. 行业能力层

```text
INDUSTRY_CAPABILITY_IS_VERSIONED_PRODUCT_ASSET=true
INDUSTRY_CATALOG_DATABASE_OPTIONAL=true
INDUSTRY_SHARED_TRANSACTION_DATABASE_FORBIDDEN=true
TENANT_RECORD_CROSS_DATABASE_FOREIGN_KEY_FORBIDDEN=true
```

行业能力主要作为版本化产品资产存在，包括：

- `smart_construction_core`、`smart_construction_portal`、
  `smart_construction_bundle` 等行业模块和产品包；
- 字段及表单模板；
- 流程模板；
- 权限和角色模板；
- 行业基础字典；
- 报表定义；
- frontend contract、intent 和 bundle。

行业能力包安装到各客户租户数据库。多个客户不得共同写入一个“行业业务数据库”。

未来若建立行业公共目录库，它只能是只读发布源，并必须同时满足：

- 不承载客户交易记录；
- 不保存客户个性化业务数据；
- 客户业务记录不得跨库外键引用目录库；
- 目录通过带版本和哈希的数据包发布；
- 租户库本地保存实际生效版本；
- 更新不得绕过租户升级流程直接写入全部生产库。

## 4. 客户租户数据库

```text
ONE_CUSTOMER_TENANT_ONE_PRODUCTION_DATABASE=true
ONE_HUMAN_USER_ONE_DATABASE=false
TENANT_DATABASE_SHARED=false
TENANT_FILESTORE_SHARED=false
TENANT_SESSION_STORAGE_SHARED=false
TENANT_DATABASE_CREDENTIAL_SHARED=false
CROSS_TENANT_ACCESS_DEFAULT_DENY=true
```

一家独立企业客户，或者有法律、审计、合同隔离要求的组织，必须拥有独立生产数据库。
禁止不同客户共享业务数据库。

同一企业租户内的自然人账号共同使用本租户数据库，并通过以下机制隔离：

- `company_id`；
- `allowed_company_ids`；
- 项目成员关系；
- 业务角色；
- ACL；
- record rule；
- 显式授权范围。

禁止为每个自然人账号建立数据库。自然人账号生命周期不能替代租户数据库生命周期。

## 5. 集团、多公司与跨租户协作

```text
MULTI_COMPANY_WITHIN_TENANT_ALLOWED_BY_GOVERNANCE_DECISION=true
LEGAL_ISOLATION_REQUIRES_SEPARATE_TENANT_DATABASE=true
```

集团客户开通时必须明确选择并记录：

- 集团共享租户：一个租户数据库内多个 `res.company`；
- 子公司独立租户：每个需要强隔离的子公司使用独立数据库；
- 混合模式：多个租户数据库，由平台控制面记录集团关系。

数据库边界由合同、法律、审计及数据治理决定，不得仅根据 Odoo 多公司能力自动判断。

不同租户数据库之间禁止建立 ORM 关系、数据库外键或附件引用。跨租户协作只能通过
显式接口、交换单据或经治理批准的数据服务完成。

## 6. 租户环境生命周期单元

```text
TENANT_DATABASE_INDEPENDENT=true
TENANT_DATABASE_ROLE_INDEPENDENT=true
TENANT_FILESTORE_INDEPENDENT=true
TENANT_SESSION_NAMESPACE_INDEPENDENT=true
TENANT_BACKUP_AND_RESTORE_INDEPENDENT=true
TENANT_PURGE_SCOPE_INDEPENDENT=true

CROSS_TENANT_ORM_REFERENCE=false
CROSS_TENANT_ATTACHMENT_REFERENCE=false
TENANT_DATABASE_CREDENTIAL_SHARED=false
TENANT_RECORD_CROSS_DATABASE_FOREIGN_KEY_FORBIDDEN=true
```

每个租户环境必须作为完整生命周期单元管理：

```text
TENANT_ENVIRONMENT =
    DATABASE
  + DATABASE_ROLE
  + FILESTORE
  + SESSIONS
  + TMP
  + LOG_SCOPE
  + BACKUP_POLICY
  + ENCRYPTION_CONTEXT
  + DOMAIN_OR_ROUTE
  + PRODUCT_VERSION
  + INDUSTRY_PACK_VERSION
```

底层日志、对象存储或基础设施可以共享，但必须具备稳定的 `tenant_id` 和
`environment_id` 命名空间、权限隔离、独立备份恢复和精确清理能力。共享基础设施
不得导致租户间凭据、对象路径、恢复范围或清理范围混用。

## 7. DEV、验收与生产环境隔离

```text
DEV_UAT_PROD_DATABASE_SEPARATION_REQUIRED=true
ONE_REHEARSAL_TASK_ONE_DATABASE=true
EXACT_DATABASE_FILTER_REQUIRED=true
CROSS_ENVIRONMENT_FILESTORE_SHARING=false
CROSS_ENVIRONMENT_SESSION_SHARING=false
```

典型命名仅是候选格式，不代表未经确认的实际数据库名：

```text
sc_tenant_<tenant_code>_dev
sc_tenant_<tenant_code>_uat
sc_tenant_<tenant_code>_prod
```

每个 Odoo 实例必须采用精确数据库约束：

```text
ODOO_DB=<exact_database>
ODOO_DBFILTER=^<exact_database>$
LIST_DB=false
```

数据库名、filter、filestore、session 和运行身份必须共同核验。仅改变端口或容器名
不能证明环境隔离。

## 8. 正式生产库创建规则

```text
PRODUCTION_CREATION_MODE=CLEAN_INSTALL_PLUS_CONTROLLED_IMPORT
PRODUCTION_DATABASE_MUST_BE_NEW=true
DIRECT_DEMO_TO_PRODUCTION_PROMOTION_FORBIDDEN=true
```

正式生产库必须通过以下路径产生：

```text
新建空白数据库
→ 安装冻结版本产品模块
→ 验证空库产品能力
→ 导入签名迁移载荷
→ 导入并核验附件
→ 完成用户、组织、权限和业务关系校验
→ 完成增量同步和最终切换
```

禁止复制、清理或改名 `sc_demo` 后直接作为客户生产库。现有数据库角色冻结为：

```text
LEGACY_AUTHORITY_DATABASES=LEGACY_SOURCE_A,LEGACY_SOURCE_B
CANDIDATE_MASTER_DATABASE=sc_demo
CANDIDATE_MASTER_IS_PRODUCTION=false
PLATFORM_INTERNAL_DEMO_TENANT=true
CUSTOMER_PRODUCTION_TENANT=false
DEVELOPMENT_DATABASE_IS_BUSINESS_EVIDENCE=false
```

`sc_demo` 只能作为平台内部演示、整理和迁移分析的候选来源，不能成为正式客户生产
租户。历史权威库的存在不代表允许 Codex 访问；访问仍需独立明确授权。

## 9. 数据、模块、fixture 与账号生命周期

```text
MODULE_UNINSTALL_NE_BUSINESS_DATA_PURGE=true
MODULE_UNINSTALL_NE_DATABASE_CLEANUP=true
ISOLATED_ENVIRONMENT_PURGE_NE_MODULE_UNINSTALL=true
FIXTURE_CLEANUP_NE_MODULE_UNINSTALL=true
IMPORT_ROLLBACK_NE_BLIND_DELETE=true
ACCOUNT_DEACTIVATION_NE_USER_DELETION=true
SCHEMA_OWNERSHIP_NE_BUSINESS_DATA_OWNERSHIP=true
```

客户主数据、业务历史和附件的生命周期独立于产品模块生命周期。模块卸载前必须完成
数据归属和引用影响评估；若标准卸载会删除必须保留的数据，必须阻止卸载、改为停用，
或先迁入生命周期独立的正式载体。

fixture 只允许进入明确隔离的验收或开发租户：

```text
FIXTURE_ALLOWED_DATABASES=EXPLICITLY_ISOLATED_ACCEPTANCE_ONLY
FIXTURE_ALLOWED_IN_UAT=false
FIXTURE_ALLOWED_IN_PRODUCTION=false
```

fixture 清理必须按命名空间和创建批次精确执行。导入回滚必须先检查后续业务引用；账号
停用不得物理删除共享用户、员工、审计轨迹或业务责任关系。

## 10. 跨租户分析

```text
CROSS_TENANT_ANALYTICS_REQUIRES_EXPLICIT_GOVERNANCE=true
```

跨租户分析只能使用明确授权、脱敏或聚合后的数据。禁止默认将客户业务明细同步到平台
控制库或行业目录库。分析数据集必须记录租户授权、用途、字段范围、保留期和删除责任。

## 11. 所有数据库任务的强制前置判定

所有后续 Codex 任务在任何数据库或关联存储操作前必须先回答：

```text
TARGET_DATABASE_ROLE=
TARGET_TENANT_ID=
TARGET_ENVIRONMENT_ID=
IS_PLATFORM_CONTROL_DATABASE=
IS_INDUSTRY_CATALOG_DATABASE=
IS_CUSTOMER_TENANT_DATABASE=
IS_ISOLATED_REHEARSAL_DATABASE=
CUSTOMER_BUSINESS_DATA_ALLOWED=
FIXTURE_ALLOWED=
EXACT_DATABASE_FILTER_CONFIRMED=
FILESTORE_IDENTITY_CONFIRMED=
```

涉及数据库写入但无法确认数据库角色时，必须停止：

```text
RESULT=SAFE_STOP_DATABASE_ROLE_UNRESOLVED
NEXT_TASK=CONFIRM_TARGET_DATABASE_ROLE_AND_TENANT
```

计划向平台控制库或行业目录库写入客户业务数据时，必须停止：

```text
RESULT=SAFE_STOP_DATABASE_ARCHITECTURE_VIOLATION
```

不同客户准备共享业务数据库、filestore、数据库凭据或跨库 ORM 关系时，必须停止：

```text
RESULT=SAFE_STOP_CROSS_TENANT_ISOLATION_VIOLATION
```

准备将 `sc_demo`、开发库或长期演练库直接提升为生产库时，必须停止：

```text
RESULT=SAFE_STOP_INVALID_PRODUCTION_PROMOTION
```

## 12. UM-P1 与 UM-P2 强制继承

```text
P1_MUST_INHERIT_DATABASE_ARCHITECTURE_POLICY=true
P2_MUST_USE_NEW_ISOLATED_TENANT_REHEARSAL_DATABASE=true
```

UM-P1 必须按本规则区分：

| P1 所有权类别 | 正式所有者/载体 | 数据库与生命周期约束 |
|---|---|---|
| 平台控制面资产 | 平台控制面 | 只保存租户生命周期和路由元数据，不保存客户业务数据 |
| 行业产品资产 | 版本化行业能力包 | 安装到租户库；不得形成多客户共享写入的行业业务库 |
| 租户业务资产 | 客户租户库 | 每个企业客户独立；禁止跨租户 ORM、外键和附件引用 |
| 企业共享主数据 | 由治理决策确定的单一租户库 | 可供该租户内多公司共享，不得默认跨租户共享 |
| 客户业务历史 | 客户租户库及独立 filestore | 不随模块卸载或 fixture 清理而删除 |
| fixture | 新建隔离的开发/验收租户 | 禁止进入 UAT、生产、`sc_demo`、DAILY 和 18086 对照库 |
| 迁移控制与追溯数据 | 平台控制库或独立运维库 | 只保存任务元数据、批次和审计索引，不保存客户业务正文 |

UM-P2 安装演练的默认目标只能是新建、隔离的客户租户演练库，不得使用平台控制库、
行业公共目录库、`sc_demo`、DAILY、18086 对照库、UAT 或生产库。

## 13. 规则变更与例外

- 本规则的任何例外必须有明确治理决策、影响范围、期限、审计责任和退出条件。
- 例外不得允许跨客户共享业务数据库、filestore 或数据库凭据。
- 例外不得允许将平台控制权解释为租户业务数据访问权。
- 规则修改必须作为独立治理任务处理；不得夹带在数据库、模块或部署操作中。
- 本规则本身不授权创建 `sc_platform_control` 或任何租户数据库，也不授权迁移既有环境。
