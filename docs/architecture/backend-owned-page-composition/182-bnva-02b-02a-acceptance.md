# 182 · BNVA-02B-02A · 验收

## 七个裁定

1. 复用现有校验入口：是（`_runtime_contract_validation` 附加 shadow 诊断）。
2. Section.fields 完整验证：是（KEY/TITLE/FIELDS_EMPTY/FIELD_INVALID）。
3. Identity 显式验证：是（MISSING/FIELD_INVALID/NOT_IN_SECTION）。
4. Ownership 唯一验证：以跨 section 重复字段 WARNING 覆盖主归属歧义。
5. native_group 映射：ERROR（模型提供时）/ NOT_VERIFIED（缺模型）。
6. 五样本出现预期诊断：是。
7. 具备进入 02B-02B：是，需把诊断接入发布门禁并实现历史兼容 WARNING 通道。

## 约束

未修改业务配置、未改公开 V2 Schema、未改变发布阻断、未迁移/删除历史配置。

