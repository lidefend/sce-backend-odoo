# 105 · BNVA-008~011 · 原生 Group → 业务结构映射设计

## 目标

fieldOwnership / slots / fieldGroups 统一由**原生字段位置**推导，删除字段名启发式；
identity 只来自显式声明。

## 映射规则

| Odoo 原生 | V2 业务 |
| --- | --- |
| sheet（顶层容器） | slot（默认一个，或由配置声明多个 section） |
| `<group name>` | group（稳定身份 = 原生 name） |
| `<field>` | FieldRef（归属其所在 group / sheet） |
| 配置 identity_fields | 仅标记 role=identity，不改变字段位置 |

## 原生 group → V2 group

原生 group name 保留为稳定身份，语义中文名作为 title：

```text
sc_project_information_identity      -> group:sc_project_information_identity（业务识别）
sc_project_information_entity        -> group:sc_project_information_entity
sc_project_information_contact       -> group:sc_project_information_contact
...
```

不强制把 11 个原生组压成 5 个自定义 slot；slot 仅作为 sheet 级容器，
除非业务配置显式声明 section。

## FieldOwnership 推导

```text
field X 出现在 <group name="G"> 内
  => ownerGroupRef = group:G
  => ownerSlotRef = 所在 sheet 的 slot
```

同一字段多次出现：首次出现所在 group 为 primary owner；其余为合法投影，
必须显式声明（否则 NOT_VERIFIED），不按字段名/类型/顺序自动选主。

## Identity（BNVA-010）

- 只接受配置 `identity_fields` 声明的字段为 identity。
- identity 的 group 仍由原生位置决定；若原生把 identity 字段放在
  `sc_project_information_identity` 组，则 V2 为 `group:sc_project_information_identity`。
- 不为了满足示例 Schema 而强行改名或改原生结构。

## 删除项（BNVA-011）

删除 `ui_contract_v2_form_structure.py` 中的字段名启发式清单：

- identity_fields 默认候选（name/document_no/invoice_no/...）
- relation_candidates
- term_fields
- amount_fields
- status_fields
- collaboration_fields
- detail_fields
- source_fields
- history_check_fields

保留：原生 group→field 映射、配置 identity_fields、slot/group 结构输出。

## 兼容与验证

- 五个已知页面 + PC-01/PC-02 结构身份不变。
- 前端旧消费者对 formStructureContract.slots/fieldGroups/fieldOwnership 的消费
  保持可用；slot 数量变化需在 BNVA-012~014 统一验证。
- Guard 校验 fieldOwnership 与原生结构一致，不再兜两套结构差异。
