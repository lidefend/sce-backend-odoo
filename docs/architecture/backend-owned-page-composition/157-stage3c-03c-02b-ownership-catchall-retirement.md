# 157 · BNVA-019 Stage 3C-03C-02B · 旧 Ownership Catch-all 退出

## 裁定

删除 `_page_composition_contract` 中把未归属 widget 字段自动补入
`slot:primary_facts / group:other_facts` 的 catch-all。

## 变更

- `addons/smart_core/core/unified_page_contract_v2_assembler.py`
  - 删除 catch-all 补充块及 `record_catch_all` 调用。
  - 未归属字段不再自动获得 primary owner。
  - 缺失归属时保留 `PAGE_COMPOSITION_FIELD_OWNERSHIP_MISSING`（V10）诊断。

## 保持不变

- 已有明确 `fieldOwnership` 不被覆盖。
- 正常 Native 路径与 Explicit Ownership 页面不触发该 catch-all。
- 前端消费者兼容路径不变。

## 全仓核验

搜索 `primary_facts` / `other_facts` / `fieldOwnership` / `DEFAULT` 确认无其他
模块重新生成同类默认归属。残留引用均为：

- shadow 观测计数（仅检测，不生成）。
- legacy 角色归一化映射（只读输入）。
- 旧测试 fixture 与前端 legacy 归一化映射。

