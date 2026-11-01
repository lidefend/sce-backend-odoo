# 100 · BNVA-01 · Backend Native View Authority Optimization

## 目标

让 Odoo 原生视图成为页面结构事实的唯一输入：后端契约只做规范化投影和补充
明确声明的业务语义，不再用字段名启发式独立猜测第二套页面结构。

依据：`99-odoo-native-leverage-research.md`。

## 目标架构

```text
Odoo 原生权威: Action / View / get_view() / fields metadata
        ↓
Native View Canonical Projection: 合并视图解析、结构身份、字段位置、modifiers、来源追踪
        ↓
Business Semantic Enrichment: 只补充原生视图无法表达的明确业务语义，不推测字段归属
        ↓
V2 Contract Assembler: 统一输出 containerTree / slots / fieldGroups / fieldOwnership
        ↓
Vue Contract Renderer: 消费契约，不再推导业务结构
```

独立约束：ACL、Record Rules、字段 groups、服务端权限仍由 Odoo 决定。

核心区别：

- 原生视图决定字段实际出现在哪里。
- 业务配置可明确声明某区域的业务身份。
- 前端不再按字段名猜业务分组。
- Guard 验证结构一致性，不替两套结构差异兜底。

## 批次与任务

### Batch 0 · 现有后端能力审计（只读，优先级最高）

- BNVA-001 Odoo View API 能力审计 → API 能力矩阵
- BNVA-002 Arch 解析重复审计 → 解析重复矩阵
- BNVA-003 Modifiers 重复处理审计 → Modifiers 权威报告

重点：get_view / fields_view_get / fields_get 实际返回与生命周期；合并视图是否已含
继承结果；不同用户/组返回差异；invisible/readonly/required 的实际求值；fields 与
arch string 的优先级差异。按 Odoo 17 实际运行版本核实，不能仅凭“API 返回 modifiers”
就认定所有动态表达式已求值。

### Batch 1 · 统一 Native View Projection（P0）

- BNVA-004 统一视图解析入口
- BNVA-005 Canonical AST
- BNVA-006 字段身份与位置（container_ref / occurrence_index / native_locator）
- BNVA-007 原生属性投影（modifiers / 字段元数据 / 权限属性）

Canonical AST 内部模型（不新增平行公开 Schema）：

```text
NativeView
  identity(model, action_id, view_id, view_type)
  containers[](id, native_name, native_type, parent_ref, children[])
  fields[](field_code, occurrence_index, container_ref, native_locator, modifiers, field_metadata)
  provenance(source_view_id, inherited_view_chain, runtime_context)
```

设计要求：原生节点身份不丢失；同字段多次出现保留多个 occurrence；容器层级完整；
未命名容器不靠临时数组下标冒充稳定身份；权限裁剪后结构与当前用户一致。

### Batch 2 · 消除业务结构双轨（P1，本专项核心）

- BNVA-008 原生 Group 身份映射
- BNVA-009 FieldOwnership 生产者重构（从原生字段实际位置产生唯一主归属）
- BNVA-010 Identity 显式声明（只接受业务配置明确声明的身份字段）
- BNVA-011 删除 identity/relation/term/amount 等字段名启发式

设计决定：原生 group 是业务结构映射的基础，但**不直接把所有原生 group 等同于业务 slot**。

| Odoo 原生结构 | V2 业务结构 |
| --- | --- |
| Sheet 下明确业务容器 | Slot 候选 |
| 嵌套 Group | Group 候选 |
| Field 节点 | FieldRef |
| 原生 group name | 稳定身份来源 |
| 明确业务语义声明 | Identity / Section 语义 |

重复字段规则：主编辑入口唯一 primary owner；只读摘要/关联引用必须显式声明；不得靠
字段名、类型或出现顺序自动选主归属。无稳定名称的原生 Group 先标记补身份，不得默默
生成不稳定引用。identity 可为 `slot:primary_facts / group:identity`，以
ARCH-DECISION-004 为准。

### Batch 3 · 瘦身 V2 Assembler（P1）

- BNVA-012 Assembler 输入统一（用 Canonical AST）
- BNVA-013 Contract 组装去重
- BNVA-014 结构一致性验证（containerTree / slots / fieldGroups / fieldOwnership）

目标：containerTree 不猜业务语义；slots 不独立猜字段归属；fieldOwnership 不重新
分类字段；pageComposition 只负责分类与诊断；Assembler 不承担权限决策。不能只把大文件
拆成小文件就宣布完成。

### Batch 4 · 原生能力重复实现收敛（P2）

- BNVA-015 Modifiers 收敛（复用 Odoo 计算结果，保留必要的运行时表达式处理）
- BNVA-016 字段元数据收敛（减少重复 fields_get 与 XML label 回填）
- BNVA-017 权限投影核验（解析/过滤/输出不绕过原生权限）

特别约束：get_view() 已按用户裁剪时，不得用超级用户取完整视图再混入普通用户契约。

### Batch 5 · 专项回归与收口（P2）

- BNVA-018 全链路回归：五个已知页面 + PC-01/PC-02 样板。

验收：结构身份稳定；多次字段出现不丢失；Action/View 不串用；不同用户权限投影正确；
modifiers 语义不变；fieldOwnership 与原生结构一致；旧消费者兼容；页面样式与业务操作
不回归。

## 实施顺序与依赖

P0 先确定原生事实（BNVA-001~003，不碰代码）→ P0 统一结构表示（004~007）→
P1 统一业务结构来源（008~011）→ P1 Assembler 收敛（012~014）→
P2 重复实现收敛（015~017）→ P2 全链路验收（018）。

## 重点文件

- `form_structure_authority.py` → 业务语义声明解析入口
- `ui_contract_v2_form_structure.py` → 原生结构投影
- `ui_contract_v2.py` → 收敛重复富化
- `unified_page_contract_v2_assembler.py` → 统一结构输出

## 状态

已立项；Batch 0（BNVA-001~003）只读审计待执行，暂不修改代码。
