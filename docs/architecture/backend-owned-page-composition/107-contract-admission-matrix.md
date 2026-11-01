# 107 · BNVA-019-02 · 信息准入与排除规则

> 目标：冻结 Native → V2 Contract 的信息准入边界，防止下游重新推导已确定的事实。

## 1. 四层单向依赖

```text
L0 Native Source Facts      Odoo 返回什么就忠实记录什么
        ↓
L1 Canonical Projection     消除格式差异，保留结构身份 / 层级 / occurrence
        ↓
L2 Contract Admission       按契约职责选择输出，只补明确声明的业务语义
        ↓
L3 Consumer Projection      生成页面结构 / 字段描述 / 记录数据 / 权限 / 操作契约
```

下游模块不得重新读取原始 arch 后重新决定业务字段归属。

## 2. 必须进入契约的信息

| 信息 | 来源 | 契约位置 | 处理 |
| --- | --- | --- | --- |
| Model / Action / View | Odoo | contract identity | 原样保留 |
| 容器层级 | 原生 arch | containerTree | 保留 |
| 容器名称 | group/page | containerTree | 保留原生身份 |
| 字段名称 | field 节点 | FieldRef | 保留 |
| 字段出现次数 | field 节点 | occurrence | 不得去重丢失 |
| 字段所在容器 | 原生 arch | 结构映射 | 保留 |
| 原生字段类型 | fields_get | Field Descriptor | 保留 |
| Label | arch + fields_get | Field Descriptor | 按优先级合并 |
| widget / placeholder | field 属性 | Field Descriptor | 保留 |
| 原始 modifiers | 原生 arch | Modifier Contract | 原样保留 |
| 关系目标模型 | 字段描述符 | Relation Descriptor | 保留 |
| subview | 关系字段内部 arch | Relation Contract | 保留 |

## 3. 有条件进入的信息

| 信息 | 进入条件 | 处理 |
| --- | --- | --- |
| 原生 group | 是有效结构容器 | 作为 group 身份 |
| Sheet | 是业务表单容器 | slot 候选 |
| Notebook / Page | 存在实际页面结构 | 保留层级 |
| Identity | 有显式业务声明 | 标记语义角色 |
| Section 语义 | 有明确声明 | 不按名称猜测 |
| FieldOwnership | 归属证据完整 | 唯一 primary owner |
| readonly/required/invisible | 有原始表达式 | 保留表达式，运行时求值 |
| groups | 有可见性约束 | 保留适用范围，不替代 ACL |
| technical field | 被表达式依赖 | 保留技术依赖，不作业务展示 |

## 4. 不直接进入页面结构契约的信息

| 信息 | 应归属 |
| --- | --- |
| 完整 ORM Python 对象 | 内部执行层 |
| 数据库记录全部字段值 | Record Data Contract |
| ACL 原始规则 | 权限服务 |
| Record Rules 原始 domain | 权限服务 |
| 超级用户环境 | 服务端执行上下文 |
| 原始 XML 字符串副本 | 内部审计与来源追踪 |
| 临时解析对象 | Canonical Projection 内部 |
| 未声明业务字段分类 | 不允许生成 |
| 字段名猜出的 Identity | 不允许生成 |
| 前端组件样式默认值 | Presentation Contract |
| 纯技术调试信息 | Diagnostic Contract |

## 5. 五个容易分叉的边界

### A · View 中出现 ≠ 进入 mainData

```text
NativeFieldOccurrences
  ├── ViewField          原生视图声明字段
  ├── BusinessField      业务归属 → fieldOwnership
  ├── HydrationField     首屏记录值 → mainData
  ├── TechnicalDependency 表达式依赖 → modifier evaluation
  └── RelationField      关系导航 → relation descriptor
```

### B · 原生 Group 身份与业务角色分离

```text
nativeIdentity = "sc_project_information_responsible"
businessRole   = "context"
title          = "责任信息"
```

不允许 `if "responsible" in group_name: return "context"` 作为正式语义权威。

### C · Modifiers 保留原始表达式

后端只提供原始表达式和（可选的）静态字面量解析；记录/context/uid 相关表达式
由前端按运行时上下文求值，不用空上下文误算成 false/null。

### D · 权限不能因进入契约被重新授权

契约只表达服务端授权结果，不能成为新的授权系统；不允许 sudo 补全普通用户视图。

### E · 布局不决定业务归属

containerTree / slots / fieldGroups / fieldOwnership / Renderer 各司其职，
通过稳定身份相互引用，不互相替代。

## 6. 准入策略（内部模型）

```text
NATIVE_STRUCTURE   = container_identity, container_hierarchy,
                    field_occurrences, native_locator
FIELD_DESCRIPTOR   = field_code, field_type, label, widget,
                    placeholder, relation, modifiers_raw
BUSINESS_SEMANTICS = identity, section, field_ownership, display_role
FORBIDDEN_INFERENCE = identity_from_field_name,
                      business_role_from_orm_type,
                      primary_owner_from_occurrence_order,
                      permission_from_frontend_visibility
```

可测试准入规则：原生结构有统一来源；业务语义有明确声明；不合规字段不静默补齐；
不同契约只消费所需信息；所有转换可追溯；下游不重解释已确定事实。

