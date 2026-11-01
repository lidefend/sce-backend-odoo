# 395 · BNVA-04 Tax Certificate Field Ownership Adjudication

## 分类裁定

**VIEW_DECLARATION_CORRECTION**

## 排除理由

- SHARED_PROTOCOL_REUSE：不成立。`sc.formal.display.copy.sources` 是排除协议，不提供字段；
  且 tax.certificate 未接入协议、未登记任何 `source_created_*`。
- MIXIN_EXTENSION：不成立。仓库不存在声明 `source_created_by` / `source_created_at` 的公共
  Mixin；这两个字段在 4 个模型上是逐模型声明的计算存储字段，tax.certificate 没有可继承的现成载体。
- NOT_VERIFIED：不成立。模型声明、视图引用、协议定义、全仓库字段声明均已取证。

## 根因

sc.tax.certificate.registration 的原生 tree/form 复制了兄弟财务模型的「录入来源 / 录入人 /
录入时间」展示字段引用，但：

1. 本模型未声明这两个展示字段；
2. 本模型没有 `creator_name` / `created_time` 规范来源；
3. 本模型没有迁移来源（`source_origin` / `legacy_*`）业务概念。

## 最小修复建议（本轮不执行）

修正原生视图声明，删除 sc.tax.certificate.registration 中的孤儿字段引用：

- tree 删除 `source_created_by`、`source_created_at` 两个 `optional="hide"` 列；
- form 删除整个「录入来源」group（该模型无迁移来源概念，组内无任何可保留字段）。

不新增字段、不改 Mixin、不改 Python 模型、不改 Contract、不改 Schema、不改 Renderer、不改 ACL。

## 影响范围

- 仅 `addons/smart_construction_core/views/core/tax_certificate_registration_views.xml`。
- 运行时表单/列表字段解析恢复正常；契约与权限权威不变。
- 修复后需复跑 XML/Contract/Assembler/Guard，再进入 04-06D 运行时验证。

## 兄弟模型提示（本批范围外）

sc.tax.deduction.registration 的「迁移来源」页同样引用了未声明的裸 `source_created_by` /
`source_created_at`（其规范来源 `creator_name` / `created_time` 已存在，展示副本应为
`deduction_bill_source_created_by/at`）。属同一缺陷类，建议后续单独裁定，不在本轮处理。
