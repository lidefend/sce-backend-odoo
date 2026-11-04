# C1 最小验证范围（CAP-01C 统一基线）

状态：设计冻结
原则：只验证“原子能力承诺结果”与“契约化成果一致性”，不重复验证 Odoo 原生机制。

## 1. 直接信任、不重复测试

- Odoo ORM / 数据库 / 事务
- Model / Action / View 原生注册
- ACL / Record Rules 底层实现
- 字段与关系机制
- 模块安装 / 升级生命周期

## 2. 只验证 SCE 新增语义

| 能力承诺 | 验证点 | 对应测试 |
|---|---|---|
| 接受约定输入 | handler 白名单 + name 必填 | test_01 / test_04 |
| 创建项目 | 返回真实项目记录（契约形态） | test_01 |
| 应用默认值 | normalize_create_vals 默认 manager/phase/lifecycle | test_02 |
| 条件性初始化 | 任务根节点 + 消息 + 不重复 | test_03 / test_03b |
| 错误语义 | MISSING_PARAMS / PERMISSION_DENIED / BUSINESS_RULE_FAILED 映射 | test_04 / test_05 / test_06 |
| 依赖 Provider | handler → service → model 执行链一致 | test_01 隐含 |

## 3. 与统一认证流水线对齐

```text
能力身份 -> 能力承诺 -> 能力契约 -> 实际 Provider -> 承诺结果验证 -> 契约一致性验证 -> 指纹与证据 -> Preview/Standard
```

组合能力在此基础上增加依赖资格与组合结果验证。
