# 176 · BNVA-02B-01 · 配置发布完整性门禁

## 现状

`_check_contract_json` / `_runtime_contract_validation` /
`role_form_structure_violations` 都不校验 Section.fields 完整性、Identity 声明、
fieldOwnership 完整性与原生 Group 映射。发布流程只管理版本与摘要。published
不能证明结构完整。

## 门禁规则（在发布前执行）

| 检查 | 级别 |
| --- | --- |
| Section 缺少 fields / fields 为空 | ERROR |
| fieldRef 无效 | ERROR |
| 同一字段重复归属 | ERROR |
| primary owner 缺失 | ERROR |
| ownerSlotRef 无效 | ERROR |
| ownerGroupRef 无效 | ERROR |
| Identity 未声明 | ERROR |
| 原生 Group 映射缺失（需要时） | ERROR |
| published 配置缺正式结构 | ERROR |
| 历史兼容占位 | WARNING（需显式 compatibility 标记） |
| 证据不足 | NOT_VERIFIED |

配置存在或 published 不自动证明结构完整。门禁实现留待 02B-02，本轮只定规则。

