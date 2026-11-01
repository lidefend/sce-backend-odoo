# 174 · BNVA-02B-01 · FieldOwnership 准入规则

## 结构

沿用既有 `fieldOwnership`：`field:<code>` → `{ownerSlotRef, ownerGroupRef}`。
不新增 displayRole；不在 ownership 里放第二归属。

## 准入规则

| 规则 | 判定 |
| --- | --- |
| fieldRef 存在 | 字段必须在某 Section.fields 中 |
| ownerSlotRef 有效 | 指向已声明 slot |
| ownerGroupRef 有效 | 指向已声明 group |
| primary owner 唯一 | 一个业务字段只有一个主归属 |
| 合法辅助投影 | 跨 Section 重复字段需显式声明，不自动选择首次出现 |
| 不允许多主编辑入口 | 重复 primary 判 ERROR |

由 Business Adapter 从配置 Section 投影生成；不得按字段名/类型/顺序推断主归属。
未归属业务字段不得隐式补齐（延续 BNVA-019 3C-03C-02B）。

