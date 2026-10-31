# 61 · Guard Rule Reconciliation Matrix

## 规则 ↔ ADR-004 对照

| 规则 | ADR-004 条款 | 当前行为 | 需改造 | 目标语义 |
| --- | --- | --- | --- | --- |
| PC-001 | 业务组合权威：slots+fieldGroups+fieldOwnership | 仅 slots 非空即 PASS | 拆分业务/布局两层；同层唯一权威 | slots 为业务组合唯一权威；布局权威归 PC-011 |
| PC-002 | Identity 显式归属 | 仅 slot 存在 | 交叉验证 ownerSlotRef==slot:identity | Identity 主展示字段真正归属 identity slot |
| PC-003 | Business Section 归属 | 仅 slot+group 存在 | 验证业务字段的 slot+group 绑定 | 业务字段绑定 section slot+group |
| PC-004 | 唯一 primary owner | 死代码重复检测，PASS 仅代表非空 | 校验记录与引用有效性 | 每字段唯一且 ownerSlotRef/ownerGroupRef 可解析 |
| PC-005 | 辅助投影显式声明；role 以 Schema 为准 | `_text` 未定义；role 硬编码 | 修 `_text`；role 集合改为 Schema 驱动 | 合法重复投影不误判；无证据 NOT_VERIFIED |
| PC-006 | 分类语义 | class 白名单 | 无需 | 分类一致 |
| PC-007 | 正式页面禁止隐式 fallback | 无证据等级 | 引入证据等级（source/static/runtime） | formal+运行时 fallback=FAIL；仅源码=NOT_VERIFIED |
| PC-008 | 服务端最终授权；布尔声明非证明 | 非空即 PASS | 引入证据类型，拒绝声明式证据 | 仅独立权限证据可 PASS |
| PC-009 | 旧消费者实际消费链 | 非空即 PASS | 引入证据等级 | 仅真实旧消费者回归可 PASS |
| PC-010 | 历史节点稳定身份 | 非空即 PASS | 引入对照证据校验 | 迁移前后对照一致才 PASS |
| PC-011 | 布局一致性（新） | 不存在 | 新增（60 号文档设计） | 布局完整/引用有效/跨层一致，无映射 NOT_VERIFIED |

## Formal Page 准入条件覆盖检查

| 准入条件（57 号文档） | 覆盖规则 | 现状 |
| --- | --- | --- |
| slots 非空 | PC-001 | 部分覆盖 |
| ownership 覆盖全字段且唯一 | PC-004 | 弱覆盖（引用未校验） |
| 引用有效 | PC-002/003/004 | 未覆盖 |
| Identity 归属 | PC-002 | 弱覆盖 |
| Section 归属 | PC-003 | 弱覆盖 |
| 辅助投影显式 | PC-005 | 部分覆盖（有缺陷） |
| 无隐式 fallback | PC-007 | 部分覆盖 |
| 权限边界 | PC-008 | 弱覆盖 |
| 版本兼容 | PC-009 | 弱覆盖 |
| 历史身份稳定 | PC-010 | 弱覆盖 |
| 布局消费一致 | PC-011 | 未覆盖 |

结论：Formal 准入条件尚未被 Guard 完整覆盖；两层后端权威中布局层完全缺位。
