# 70 · PC-001～PC-011 Validation Matrix

| 规则 | 检查 | PASS 条件 | FAIL 条件 | NOT_VERIFIED 条件 | 测试 |
| --- | --- | --- | --- | --- | --- |
| PC-001 | 两层权威 | slots 与 containerTree 均声明 | 无 | 任一层缺失 | PC001Tests |
| PC-002 | Identity | identity slot + identity 字段归属且引用有效 | identity 字段引用无效 | 无 identity slot / 无绑定字段 | PC002Tests |
| PC-003 | Section | 业务 slot + groups + 业务字段绑定有效 slot+group | 业务字段引用无效 | 缺业务 slot / groups / 绑定 | PC003Tests |
| PC-004 | Ownership | 唯一且引用有效 | 重复 key / 引用失效 | 未声明 / 无 slot 证据 | PC004Tests |
| PC-005 | 投影 | 单 slot 或唯一主归属 | 非法 fieldRefs / 多主入口 | 缺 role Schema / 辅助语义未证 | PC005Tests |
| PC-006 | 分类 | class 在四类内 | class 非法 | 无 | 现有 |
| PC-007 | Fallback | 无运行时 fallback（非 formal） | formal + 运行时 fallback | 仅源码/静态 / 无证据 | PC007Tests |
| PC-008 | 权限 | 充分权限证据（type + coverage） | 无 | 无证据 / 证据不充分 | PC008To010Tests |
| PC-009 | 版本兼容 | 旧消费者回归证据 | 无 | 无证据 | PC008To010Tests |
| PC-010 | 历史身份 | before/after 映射证据 | 无 | 无证据 | PC008To010Tests |
| PC-011 | 布局完整性 | 结构完整 + 映射一致 | 悬空引用 / 归属冲突 / 映射失效 | 无映射 / 无 containerTree | PC011Tests |

## 规则级证据充分性

| 规则 | 允许 evidence_type | 必须 coverage |
| --- | --- | --- |
| PC-007 | RUNTIME_OBSERVATION（grade=RUNTIME_VERIFIED） | — |
| PC-008 | TEST_EXECUTION / RUNTIME_OBSERVATION | server_permission_mechanism, authorized_access, unauthorized_denied |
| PC-009 | TEST_EXECUTION | old_consumer_regression |
| PC-010 | HISTORICAL_REFERENCE | before_after_mapping |
