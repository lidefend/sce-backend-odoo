# 207 · BNVA-02D · Copy-on-Write / Overlay 研究

## 当前机制（`resolve_form_structure_governance`）

运行时按 apply_order 迭代所有匹配配置并合并，不是整文档替换：

- 标量键（composition_mode / form_structure_authority / form_presentation_mode /
  field_labels / field_semantic_roles / group_columns / group_visibility）：
  后者覆盖前者（last-wins）。
- 列表键（field_names / identity_fields / section_titles / field_groups /
  configured_sections）：追加去重（append，无 replace）。
- 隐藏（hidden_field_names）：并集（用户用 `visible=False` 抑制种子字段，而非删除）。

## 结论

当前已是“部分 Overlay”：用户覆盖可以是部分 payload（只声明要定制的键），合并到
种子之上；但没有显式 replace 语义，列表只能追加+隐藏，不能移除种子字段。

## 建议

- 不引入第三套配置表达。
- 短期沿用现有“部分 payload + 合并 + 隐藏”的 Overlay 语义，明确每个键的
  append / last-wins / hidden 规则。
- 仅当出现“必须从种子移除某字段/分区”的真实缺口时，再考虑给列表键增加显式
  `replace: true` 或 `remove` 标记，并作为 `contract_json` 的最小扩展。
- 用户撤销覆盖 = 删除/停用用户覆盖记录，自动回落到产品默认（天然 Copy-on-Write
  撤销语义），无需额外机制。

