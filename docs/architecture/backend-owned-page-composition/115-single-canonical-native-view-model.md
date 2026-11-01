# 115 · BNVA-019 Stage 3 架构调整 · Single Canonical Native View Model

> 目标：用「统一原生视图模型 + 多个职责独立适配器」取代原定的双投影共享 root。
> 本轮为架构裁定（只读），据此再实施 Stage 3A / 3B / 3C。

## 1. 为什么调整

此前把「职责独立」误实现成了「结构解析独立」：NCP 与 LDP 各自
`get_view()`、各自 `etree.fromstring()`、各自遍历，再各自维护结构身份。
职责边界是对的，但两套解析管线不是唯一解，且会持续产生第三条结构管线。

裁定：统一的是**内部事实模型**，不是合并业务职责。

## 2. 三种方案比较

| 维度 | 完全双投影 | 完全合并 | 统一模型 + 多适配器（推荐） |
| --- | --- | --- | --- |
| arch 解析 | 两次 | 一次 | 一次 |
| 内部结构模型 | 两套 | 一套 | 一套 |
| 业务/布局职责 | 分离 | 易混合 | 分离 |
| 维护成本 | 较高 | 易成巨型模块 | 较低 |
| 前端兼容 | 较好 | 需谨慎 | 较好 |
| 扩展其他 View 类型 | 两套适配 | 易耦合 | 独立扩展 |
| 长期演进 | 一般 | 有风险 | 最优 |

推荐：**Single Canonical Native View Model**。

## 3. 目标架构

```text
Odoo Native Kernel
  get_view() + fields_get() + 当前用户权限上下文
        ↓
Native View Parser
  一次 XML 解析、一次遍历、保留完整节点身份
        ↓
Canonical Native View Model
  Container Tree / Field Occurrences / Native Attributes /
  Modifiers / Field Metadata / Provenance / Relation / Subview
  （不含猜测的业务语义，也不含前端表现决策）
        ↓
  ┌─────────────────────┬────────────────────────────┐
  │ Business Structure  │ Layout Adapter             │
  │ Adapter             │  containerTree / columns / │
  │ slots / fieldGroups │  widgets / toolbar / search│
  │ fieldOwnership /    │                            │
  │ Identity            │                            │
  └──────────┬──────────┴─────────────┬──────────────┘
             ↓                        ↓
     formStructureContract      layoutContract
```

## 4. 统一模型内容（只采集一次）

| 原生事实 | 统一模型表达 |
| --- | --- |
| form / sheet / group | NativeContainer |
| notebook / page / div / header | NativeContainer |
| field 节点 | NativeFieldOccurrence |
| 重复字段 | occurrence_index |
| 字段所属容器 | container_ref |
| 原始属性 | native_attributes |
| modifiers | modifiers_raw |
| fields_get 元数据 | field_metadata |
| relation | relation_descriptor |
| 原始节点位置 | native_locator |
| 来源身份 | provenance |

当前 `native_view_projection.NativeView` 已覆盖大部分；缺口是
`native_attributes`（除 modifiers 之外的 attrs）与显式 `relation_descriptor`
尚未独立承载，需要在 Stage 3A 补齐，不改变现有 V2 输出。

## 5. 仍由独立适配器负责（不进统一模型）

| 内容 | 责任方 |
| --- | --- |
| Identity 业务语义 | 业务配置 |
| Section 语义 | 业务配置 |
| FieldOwnership | Business Structure Adapter |
| columns | Layout Adapter |
| widget | Layout Adapter |
| toolbar | Action / Layout Adapter |
| search | Search Contract |
| 权限结果 | Odoo 服务端 |

`NativeContainer` 存在不等于它是业务 Section；`NativeFieldOccurrence` 存在
不等于它进入 mainData。

## 6. 文件职责调整

| 文件 | 目标职责 |
| --- | --- |
| `native_view_projection.py` | 统一 Parser + Canonical Model |
| `view_Parser/base.py` | 消费统一模型，保留旧接口兼容 |
| `view_Parser/contract_Parser.py` | Layout Adapter |
| `ui_contract_v2_form_structure.py` | Business Structure Adapter |
| `form_structure_authority.py` | 只解析明确业务语义声明 |
| `unified_page_contract_v2_assembler.py` | 最终契约组装，不重新解析视图 |
| `ui_contract_v2.py` | 请求编排，不再承担多套解析逻辑 |

## 7. 两个必须修正的设计点

1. 不得让第一次出现的字段自动成为 primary owner。统一模型保留全部
   occurrence；Business Structure Adapter 只在唯一归属明确后生成 ownership。
2. 权限上下文必须在原生解析入口确定。当前用户的 `get_view()` 结果才是该用户
   的结构事实，不允许把 sudo 视图与普通用户视图混入同一模型。

## 8. 实施三步

- Stage 3A · 模型设计：确定 Canonical Model 完整字段、身份、权限、生命周期；
  补 `native_attributes` / `relation_descriptor`，不改 V2 输出。
- Stage 3B · 统一解析：单一解析入口，两个适配器消费同一模型。
- Stage 3C · 消费者收敛：移除重复 XML 解析与重复遍历，保持 V2 Contract 输出
  兼容，移除旧 NCP/LDP 双解析。

## 9. 约束

- 不重新实现 Odoo 视图系统，只规范化原生结构。
- 一次 `get_view()`、一次 `etree.fromstring()`、一次遍历。
- 不新增公开 Schema；Canonical Model 是内部结构。
- 每次收敛用精确 HEAD Quick + 定向单测 + 权限对照验证。

