# 57 · Formal Page Composition Entry Criteria

## 定义

Formal Page 是经 Backend-Owned Page Composition v1 认定具备正式交付资格的页面：
后端契约完整表达业务组合与布局，前端只消费契约，且权限边界独立、可证明。

## 准入条件（不可协商）

1. `formStructureContract.slots` 存在且非空。
2. `fieldOwnership` 覆盖所有主展示字段，且每字段仅一条记录。
3. 所有 `fieldRef` / `ownerSlotRef` / `ownerGroupRef` 引用有效。
4. Identity 字段归属 `slot:identity`，由 slots 显式声明，不由字段名推断。
5. Business Section 字段归属明确的 slot + group。
6. 辅助投影（只读摘要 / 关联引用 / 明细引用）由 slot 显式声明。
7. 不依赖隐式 Legacy fallback（coreFieldNames / advancedFieldNames /
   buildLegacyLayoutNodes）。
8. 服务端权限边界未改变，且存在独立权限证据（不得仅凭
   permissionSemanticsPreserved=true）。
9. 版本兼容有证据（旧消费者回归、action/view 无配置串用）。
10. 历史低代码节点身份稳定（有迁移前后对照证据）。
11. 布局消费有证据：Renderer 消费 `layoutContract.containerTree`，且
    slots ↔ containerTree 映射一致（待 PC-011 建立）。

## 证据充分性要求

- 结构、布局、消费链必须达到 SOURCE_VERIFIED 或 RUNTIME_VERIFIED。
- fallback、权限、旧消费者、历史身份若无法取得证据，保持 NOT_VERIFIED，
  不得转 PASS。
- 任何一条不可协商条件未满足，页面不得进入 Formal。

## 成熟度 ≠ 准入

- 页面能渲染 ≠ Formal。
- slots 完整 ≠ Formal（还需 ownership / 权限 / 版本 / 历史身份 / 布局一致性）。
- containerTree 存在 ≠ 业务组合完整。
- fieldGroups 存在 ≠ 参与渲染。

## 五个已知样本当前判定

| 页面 | 业务组合 | 布局 | 主归属 | 判定 |
| --- | --- | --- | --- | --- |
| project.project 590/1776 | slots=0, groups=false | containerTree 存在 | 缺失 | 未准入 |
| project.project 652/944 | slots=0, groups=false | containerTree 存在 | 缺失 | 未准入 |
| payment.request 649/1773 | slots=9, groups=true | containerTree 存在 | 缺失 | 未准入（最接近，缺 ownership） |
| sc.payment.execution 709/1658 | slots=0, groups=true | containerTree 存在 | 缺失 | 未准入 |
| sc.receipt.income 708/1655 | 无 V2 Contract | 无证据 | 缺失 | NOT_VERIFIED |

## 结论

当前没有任何页面满足 Formal 准入。五个样本均不得进入迁移准备；不得为获得全绿
结果修改样本配置。
