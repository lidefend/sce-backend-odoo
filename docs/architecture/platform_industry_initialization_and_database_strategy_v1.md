# 平台初始化、行业初始化与数据库策略 v1

状态：所有者确认（2026-10-14）
权威边界：`docs/governance/database_architecture_policy.md`（数据库架构唯一权威）
执行登记：`.agent/runs/FE-CONTRACT-RUNTIME-02/run.json`
声明文件：`addons/smart_core/data/tenant/database_strategy.v1.json`
本文件只描述初始化顺序与策略选择，不复制、不替代数据库架构政策。

## 1. 所有者裁定

```text
PLATFORM_INITIALIZATION_STRAIGHTENED=true
INDUSTRY_INITIALIZATION_FOLLOWS_PLATFORM_ONBOARDING=true
TENANT_DATABASE_STRATEGY_SELECTABLE=true
FORMAL_CUSTOMER_COMPANY_OWNS_DEDICATED_DATABASE=true
DEMO_IS_FIRST_ONBOARDED_COMPANY=true
BUSINESS_DATA_NEVER_IN_PLATFORM_BOOTSTRAP_COMPANY=true
```

- 平台初始化与行业初始化必须彻底理顺：先决定数据库策略，再接入（onboard）本库的业务公司，
  最后才安装/落行业初始化数据。
- 单库多公司（`single_db_multi_company`）与每客户独立建库
  （`database_per_customer_tenant`）是可选择策略，必须按环境角色显式声明并登记。
- 正式客户公司必须拥有独立数据库；不得把两个正式客户放进同一个业务库。
- demo 是入住平台的第一个演示公司：它是一等数据空间（`data_purpose=demo`），
  不是技术件，也不是平台 bootstrap 公司。
- 平台 bootstrap 公司（`base.main_company`/`is_platform_bootstrap_company=True`）
  永远不是业务租户，不承载任何业务数据。

## 2. 初始化顺序（唯一顺序）

```text
1. 平台技术基线      smart_construction_bootstrap   语言/时区/币种基线
2. 平台机制          smart_core                     契约/权限/注册权威
3. bootstrap 公司标记  smart_core.data               base.main_company 标记为技术载体
4. 数据库策略声明     addons/smart_core/data/tenant/database_strategy.v1.json
5. 数据空间接入       smart_core.security.data_space_provisioning
                     -> 创建并注册本库业务公司（purpose=demo/test/customer）
6. 行业初始化         smart_construction_core + smart_construction_seed
                     -> 行业字典/菜单/税/项目阶段落在已接入的业务公司
7. 客户差异化         smart_construction_custom / 客户模块
```

违反该顺序（先落业务数据、后接入数据空间）会产生“归属未知的业务数据”，
只能由受管迁移处理，不得在普通安装/升级中隐式归入某个公司。

## 3. 策略语义

| 策略 | 含义 | 允许的环境角色 | 禁止 |
| --- | --- | --- | --- |
| `database_per_customer_tenant` | 每个正式客户公司独立数据库；库内可有多个 `res.company`（集团/多公司） | `customer_production`、`customer_uat` | 跨库 ORM/外键/附件引用 |
| `single_db_multi_company` | 一个数据库内多个业务公司，按公司维度 + 数据用途隔离 | `platform_internal_demo`、`industry_acceptance`、受治理的集团共享租户 | 承载两个正式客户的业务数据 |

`single_db_multi_company` 用于单体/演示/验收/受治理集团共享；`customer_production`
角色必须使用 `database_per_customer_tenant`，否则守卫 fail closed。

## 4. 与数据用途维度（customer/demo/test）的关系

- 策略决定“业务数据放在几个库”，数据用途决定“同一个库里哪些公司属于哪个用途域”。
- 二者正交：单库多公司依靠 `sc.tenant.company.registration.data_purpose` +
  公司维度共同隔离；每客户独立库依靠库边界隔离。
- 未注册公司的归属未知，按“未知归属不放行”处理，不因策略选择而放行。

## 5. 非目标

- 不新建平行权限引擎。
- 不在本文件重新定义数据库架构政策、模块所有权或契约边界。
- 不授权创建任何数据库；环境创建仍需按政策与独立授权执行。
