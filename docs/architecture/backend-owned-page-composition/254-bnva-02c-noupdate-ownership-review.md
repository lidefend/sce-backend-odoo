# 254 · BNVA-02C-02B-01 · 32 个 noupdate=1 文件更新所有权复检

## 复检口径

noupdate=1 不是永久冻结；仅改变模块升级时数据重应用行为。首次发布时产品默认
业务结构应随产品版本演进。

## 初步分档（只建议，不回改）

| 档 | 文件特征 | 建议 |
| --- | --- | --- |
| 基础技术/系统配置 | data_permission / mail_notification / policy_document / product_system_settings / product_numbering_rule 等 | 保持 noupdate=1 |
| 产品默认业务结构 | *_form_productization（native_semantic_surface / identity_fields）/ view_orchestration_contract_data | 可能需随版本演进 → 复检 |
| 需受控升级 | 含 identity_fields 且身份定义会随产品演进 | 版本化代码模板 |

结论：32 个文件不能全部视为永久冻结；具体分档需产品负责人按业务演进确认，
本轮不回滚。

