# 91 · Field Ownership Runtime Closure

## 状态

fieldOwnership 已端到端闭环，590/1776 结构侧五项 Guard 规则 PASS。

## 运行时结果（590/1776 表单契约）

```text
containerTree group 节点 = 11（原生 sc_project_information_* 命名组已保留）
fieldOwnership          = 33 条
pageComposition.class   = formal（assembler 无诊断）
```

## Guard 结果

```text
overall: FAIL
PC-001 PASS    PC-002 PASS    PC-003 PASS
PC-004 PASS    PC-005 NOT_VERIFIED    PC-006 PASS
PC-007 FAIL    PC-008 NOT_VERIFIED    PC-009 NOT_VERIFIED
PC-010 NOT_VERIFIED  PC-011 NOT_VERIFIED
```

## 已收敛的架构口径

- 原生 `<group>` 是权限/可见性载体；`groups` 属性只在 `_runtime_filter`
  投影可见性，ownership 不读取。
- `role` 降级为业务语义标签，不承载权限。
- `fieldOwnership` 是独立业务组合声明，唯一主归属 = ownerSlotRef +
  ownerGroupRef。
- identity 在运行时由 `group:identity` 表达（选项 A 约定），Guard 已对齐。

## 关键实现点

- `_normalize_native_layout_nodes` 从 `attributes.name` 读取 group 身份，
  使 11 个原生组名进入 containerId。
- `derive_field_ownership` 从 field_roles 派生 33 条唯一主归属。
- assembler 的 group 解析同时读 formStructureContract slots[].groups[].name。
- Guard 的 PC-002/003/004 对齐 `group:identity` 与 slot groups 约定。

## 剩余

- PC-005：辅助投影语义未显式声明，保守 NOT_VERIFIED。
- PC-007：formal 页面仍有运行时 legacy shadow，需 Phase 5 收缩。
- PC-008～011：证据缺失（权限双样本、旧消费者回归、历史身份、映射）。
