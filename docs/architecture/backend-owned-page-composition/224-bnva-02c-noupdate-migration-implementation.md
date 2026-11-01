# 224 · BNVA-02B-02C-02B-03B · noupdate 迁移实施

## 分类结果（脚本判定）

- IMMUTABLE_CODE_SEED：32 个文件（native_semantic_surface / native_authority /
  identity_fields，无 entry_semantic_surface）→ 已改 `noupdate="1"`。
- VERSIONED_CODE_TEMPLATE：16 个文件（含 entry_semantic_surface sections）→ 保留。
- GENERATED_BASELINE：1 个文件（view_orchestration_contract_generated_data）→ 已 noupdate=1。

## 变更

32 个 IMMUTABLE XML 根标签 `<odoo>` → `<odoo noupdate="1">`；XML 全部可解析，
`git diff --check` 通过。

## 关键发现

15 个 `*_form_productization_contract.xml` 实际是 entry_semantic_surface（title-only
sections），归为 VERSIONED，不能简单冻结；留待 03C 经 Runner 补 fields 或转 Legacy。

