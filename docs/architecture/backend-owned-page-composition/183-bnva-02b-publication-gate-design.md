# 183 · BNVA-02B-02B · 发布门禁设计

## 接入点

单点发布入口 `_append_published_version`：仅在创建新版本路径执行门禁；未变更的
重发（definition_sha256 一致）不阻断，保护历史配置。

## 门禁判定（`publication_gate`）

| verdict | 条件 |
| --- | --- |
| blocked | 非法引用，或结构不完整且未声明 Legacy Compatible |
| formal | 无 ERROR 且无 NOT_VERIFIED |
| legacy_compatible | 显式完整兼容声明覆盖非阻断缺口 |
| unclassified_historical | 无 ERROR 但有 NOT_VERIFIED，可发布但非 Formal |

## 非法引用（对 Legacy 也阻断）

SECTION_INVALID / SECTION_FIELD_INVALID / IDENTITY_FIELD_INVALID /
NATIVE_GROUP_UNRESOLVED。

## 绑定

gate 结果存入版本 `snapshot_json._publication_gate`，随版本不可变；restore 时剔除。
payload_sha256 / definition_sha256 仍来自 contract_json / definition_payload，不变。

