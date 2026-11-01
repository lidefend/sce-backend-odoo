# 177 · BNVA-02B-01 · 验收

## 七个裁定

1. Section.fields 唯一表达：`views.form.sections[]`（key + title + fields）。
2. Identity：`views.form.identity_fields` 显式声明。
3. FieldOwnership：既有 `field:<code>` → ownerSlotRef/ownerGroupRef，唯一主归属。
4. 原生 Group 映射：section 可选 `native_group` 键显式映射。
5. 发布准入：ERROR/WARNING/NOT_VERIFIED 三级，published ≠ 完整。
6. Schema 扩展必要性：仅新增可选 `native_group`，不新增平行 Schema。
7. 具备进入 02B-02 条件：是，需先固化发布门禁实现点。

## 约束

本轮仅设计与反向验证，未改产品代码、未改配置、未改公开 V2 Contract。

