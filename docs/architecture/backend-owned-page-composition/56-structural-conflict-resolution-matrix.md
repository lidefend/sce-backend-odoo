# 56 · Structural Conflict Resolution Matrix

## 状态语义

- Formal 允许 / 不允许：能否被认定为正式产品页面。
- Legacy Compatible 允许 / 不允许：能否被认定为显式兼容页面。
- Guard 预期：当前 Guard 或建议规则（PC-011）的预期结果。
- 阻断迁移：是否阻断向 Formal 的迁移。
- 人工确认：是否需要人工裁定。

## 矩阵

| # | 场景 | Formal | Legacy Compatible | Guard 预期 | 阻断迁移 | 人工确认 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | slots 完整 + containerTree 完整 | 允许（需 ownership 完整、引用有效、无隐式 fallback、权限边界不变，且 slots↔containerTree 映射有证据） | 不适用 | PC-001 PASS；PC-011 NOT_VERIFIED（未实现） | 否 | 是（映射证据需复核） |
| 2 | slots 完整 + containerTree 缺失 | 允许（业务组合完整；渲染若需布局则 fail-closed，不得前端自造） | 不适用 | PC-001 PASS；布局缺失需 PC-011 报告 | 否 | 是（确认 Renderer 布局路径） |
| 3 | slots 缺失 + containerTree 完整 | 不允许（业务组合未声明） | 允许（仅当显式 `legacyCompatible=true`；否则 unclassified_historical） | PC-001 NOT_VERIFIED → 应为 FAIL（对 Formal） | 是 | 是（补 slots 或显式兼容标记） |
| 4 | slots 与 containerTree 区域不一致 | 不允许 | 允许（显式兼容 + WARNING） | PC-011 FAIL（确认不一致后） | 是 | 是 |
| 5 | fieldGroups 存在但 slots 为空 | 不允许 | 允许（显式兼容 + WARNING） | PC-001 NOT_VERIFIED；PC-003 NOT_VERIFIED | 是 | 是 |
| 6 | fieldOwnership 存在但引用失效 | 不允许（incomplete） | 允许（显式兼容 + WARNING） | PC-002/PC-003/PC-004 FAIL（无效引用） | 是 | 是 |
| 7 | 字段出现在多个容器（containerTree） | 允许（仅当字段主归属唯一且重复展示被显式声明） | 允许（显式兼容 + WARNING） | PC-011 需区分合法重复与第二主入口 | 否（歧义未消除时阻断） | 是（歧义场景） |
| 8 | 唯一 primary owner + 只读摘要投影 | 允许（辅助投影由 slot role 显式声明） | 不适用 | PC-005 PASS（语义被证明后）；当前保守为 NOT_VERIFIED | 否 | 否（role 为 Schema 合法集合内） |
| 9 | 多 Action 共用模型、不同 View | 允许（按 model+action_id+view_id 独立评估） | 允许（独立评估） | 每个 action/view 独立判定，不得合并 | 否（各入口独立满足准入） | 否 |
| 10 | 历史页面仍依赖 Legacy fallback | 不允许（正式页面禁止隐式补齐） | 允许（显式兼容 + WARNING） | PC-007：Formal+fallback=FAIL；Legacy+fallback=WARNING；运行消费未证明=NOT_VERIFIED | 是 | 是 |

## 结论

- 场景 3、4、5、6、10 是当前五个已知样本主要落入的高风险类别。
- 场景 7、8 依赖“辅助 role 合法集合以真实 Schema 定义为准”，Guard 不得自行
  扩大或缩小该集合（对齐 4D-01 结论）。
- 场景 9 强调页面身份必须到 Action/View 粒度，不得按 Model 汇总。
