# 200 · BNVA-02B-02C-02A · 种子升级分类

## 全量

- 145 条 `ui.business.config.contract` 记录，49 个 XML 文件。
- noupdate 分布：noupdate=0 文件 28 个（109 条）、default 文件 16 个（18 条）、
  noupdate=1 文件 4 个（18 条）。Odoo 中 default 等价 noupdate=0。
- 因此升级会被重写的记录共 127 条，仅 18 条（generated baseline + 少数模板）保留。

## 分类

| 类别 | 典型文件 | 记录数 | 建议 |
| --- | --- | --- | --- |
| A IMMUTABLE_CODE_SEED | form_productization_contract.xml（稳定默认） | 多数 | noupdate=1 |
| B VERSIONED_CODE_TEMPLATE | view_orchestration_form_section_contract_data.xml（entry sections） | ~40 | 受控迁移 |
| C GENERATED_BASELINE | view_orchestration_contract_generated_data.xml | 18 | noupdate=1 + 明确生成器 |
| D USER_OWNED | 运行时 lowcode（非 XML） | — | 不受 XML 覆盖 |
| E RETIRED | receipt（active=False）、payment_request（空占位） | 2 | 保留追溯，不自动恢复 |

## 判定原则

不可变默认与生成基线走 noupdate=1；需要随产品演进的结构模板走受控迁移，不用
noupdate=0 隐式重写。

