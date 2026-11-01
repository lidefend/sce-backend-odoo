# 209 · BNVA-02B-02C-02B-01 · 种子版本身份

## 稳定身份（不依赖 payload source）

| 字段 | 来源 |
| --- | --- |
| module | XML 所属模块 |
| external_id | ir.model.data External ID |
| model | 目标模型 |
| configuration_scope | view_type/action/view/role/company 归一化 |
| seed_version | 模块版本或显式 seed_version |
| migration_id | hash(external_id + seed_version + target_digest) |
| source_definition_digest | 当前已发布定义摘要 |
| target_definition_digest | 目标 XML 定义摘要 |

不得仅凭 payload 中的 `source` 字段识别所有权；external_id + module 才是锚。

