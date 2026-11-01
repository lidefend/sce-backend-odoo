# 175 · BNVA-02B-01 · 原生 Group 映射规则

## 区分四个概念

| 概念 | 来源 | 语义 |
| --- | --- | --- |
| nativeIdentity | Odoo 原生 group `name` | 结构身份与节点定位 |
| businessSectionId | 配置 section `key` | 稳定业务分区身份 |
| businessRole | `semantic_role` / `group_role` | 业务语义角色 |
| sectionTitle | section `title` | 显示标题 |

## 规则

1. 原生 Group 名称不得直接等同于业务 Section ID。
2. 原生名称提供结构位置与节点身份；业务配置提供业务语义；二者经显式映射关联。
3. 字段位于某原生 Group，不自动满足 Formal 业务归属。
4. `native_semantic_surface`：原生 group 即 section，role 由 `group_role` 派生。
5. `entry_semantic_surface`：section 为业务声明；如字段来自原生 group，需在
   section 条目声明 `native_group`（字符串或列表）做显式映射。
6. 缺映射且无法由原生 group 唯一对应时，判 NOT_VERIFIED / ERROR，不得猜映射。

## 最小 Schema 扩展

仅在既有 section 条目上增加可选 `native_group` 键；不新增平行 Schema。

