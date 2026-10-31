# 12 · Integrity Guard Rule Matrix

| Rule | Check | Expected | Status |
| --- | --- | --- | --- |
| PC-001 | 页面结构来源 | 唯一权威来源 | NOT_VERIFIED |
| PC-002 | Identity 主展示归属 | 明确归属 identity slot | NOT_VERIFIED |
| PC-003 | Business Section 归属 | 明确 slot + group | NOT_VERIFIED |
| PC-004 | Ownership primary 唯一 | 每字段唯一 owner | PASS（assembler V4） |
| PC-005 | 重复投影 | 只读摘要与主编辑不冲突 | NOT_VERIFIED（V7 未完整） |
| PC-006 | Legacy 分类 | Formal / Legacy Compatible / Unclassified | PASS（3B-2） |
| PC-007 | Fallback | 正式页面禁止隐式补齐 | NOT_VERIFIED |
| PC-008 | 权限边界 | 服务端权限不变 | NOT_VERIFIED（布尔声明不足以证明） |
| PC-009 | Schema 版本兼容 | 旧消费者兼容 | NOT_VERIFIED |
| PC-010 | 历史节点身份 | 低代码绑定稳定 | NOT_VERIFIED |

状态语义：

- PASS：已有可执行证据。
- FAIL：已发现缺陷。
- WARNING：条件性通过。
- NOT_VERIFIED：缺少证据，不得当作 PASS。
- NOT_APPLICABLE：不适用。

