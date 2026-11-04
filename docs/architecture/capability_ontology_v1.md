# SCE Capability Ontology & Definition v1（B0）

状态：CAP-01B 前置本体定义，待审查
上游：ARCH-DECISION-011（能力发布与产品发布分离）
对齐：`addons/smart_core/core/capability_maturity.py`（preview / standard 资格，不另造状态）

## 1. 正式定义

> 能力（Capability）是一个具有明确业务或技术目的、稳定身份、确定输入输出、可验证执行结果，
> 并且能够独立管理生命周期的最小可交付功能单元。

五个必要条件（任一不满足，不构成能力）：

1. 目的明确：解决一个确定的问题，可一句话描述。
2. 身份稳定：不依赖具体菜单、页面、模型名称；换 Provider 不必然改变身份。
3. 契约明确：输入、输出、约束和错误语义可描述。
4. 结果可验证：能证明执行成功或失败，有可复现证据。
5. 生命周期独立：可接入、验证、发布、升级、停用、退役。

## 2. 三层分类

| 层 | 名称 | 定义 | 归属 |
|---|---|---|---|
| L1 | Atomic Capability | 最小独立业务操作或技术功能 | 能力发布体系 |
| L2 | Composite Capability | 多个能力按明确依赖组合的可复用功能，有稳定身份但不重复实现底层逻辑 | 能力发布体系 |
| L3 | Work Scenario | 面向用户目标的完整工作过程，组织组合能力、页面和入口 | 产品发布体系 |

边界：L1/L2 属于 Capability，进入能力发布；L3 属于 Product Composition，进入产品发布。

## 3. 哪些不是能力

| 对象 | 是否独立构成能力 | 原因 |
|---|---|---|
| Odoo Model | 否 | 数据和业务执行载体 |
| Odoo Action | 否 | 导航或执行载体 |
| Intent | 不一定 | 需有独立功能语义 |
| 字段 | 否 | 能力的数据结构组成 |
| 页面 Scene | 否 | 用户交互呈现 |
| Menu | 否 | 入口 |
| API | 不一定 | 仅当有独立功能契约 |
| AI 模型 | 不一定 | 模型本身不等于可交付功能 |
| 工程计算服务 | 可以 | 满足定义与独立验证条件时 |

`project.project` 是模型；“创建项目”才可能是原子能力。一个原子能力可同时依赖 model、
intent handler、原生 action、多个校验规则，但它们是四个载体，不是四个业务能力。

## 4. 能力身份与 Provider 关系

| 对象 | 含义 |
|---|---|
| Capability Identity | 能力是什么，稳定身份（capability_key） |
| Provider Binding | 能力由什么实际执行（model/action/intent/service/api/ai） |
| Capability Qualification | 能力达到什么成熟度（preview/standard） |
| Capability Release | 能力是否正式发布、当前版本 |

身份独立于 Provider：换成微服务或 AI 实现，不必然改变能力身份；但 Provider 变化必须触发
依赖指纹与资格重新验证。

## 5. 组合与依赖规则

1. 组合能力通过依赖引用原子能力，不复制实现。
2. 组合能力契约 = 自身组合契约 + 依赖能力版本 + 兼容性约束 + 组合行为。
3. 组合能力成熟度必须验证依赖版本、兼容性和组合行为，不能把子能力资格简单相加。
4. 原子能力变更（版本/资格/退役）触发所有引用它的组合能力重新验证（DECISION-S2-04/06）。

## 6. 发布资格与证据要求

对齐 `capability_maturity.evaluate_maturity`，状态仅 preview / standard：

| 资格 | 要求 |
|---|---|
| preview | 通过 preview 版 criteria 的全部必测用例，receipt 绑定依赖指纹 |
| standard | 通过 standard 版 criteria（含 preview 全部用例），receipt + artifact 有效 |
| unreleased | 未通过任何资格评估 |
| retired | 已停用/退役，禁止新交付引用 |

证据要求（不可伪造）：
- `maturity_fingerprint` = f(capability_key, dependencies, criteria)
- receipt 绑定 capability + 依赖指纹 + artifact 执行用例（pass/fail/error/skip）
- 过期、失败、跳过、重复证据一律拒绝

## 7. 正例 / 反例 / 边界案例

| 类型 | 案例 | 判定 |
|---|---|---|
| 正例 | 创建项目 | Atomic：明确目的、可验证、独立生命周期 |
| 正例 | 项目成本分析 | Composite：组合查询/成本计算等原子能力 |
| 正例 | 完成合同审批 | Work Scenario（L3，产品组合） |
| 反例 | `project.project` 模型 | 载体，非能力 |
| 反例 | `action_project_initiation` | 执行载体，非能力身份 |
| 反例 | `menu_sc_project_project` | 入口，非能力 |
| 边界 | `project.dashboard.enter`（intent） | 需有独立功能语义与契约才可作原子能力 |
| 边界 | 工程图纸识别 AI 服务 | 有独立契约与验证时可为原子能力 |

## 8. 对现有 42 / 63 条资产的抽样分类验证

| 现有 capability_key | 本体分类 | 说明 |
|---|---|---|
| `project.initiation.enter` | Atomic（项目立项） | 满足五条件，身份可稳定 |
| `project.list.open` | Atomic（项目查询/列表） | 满足五条件 |
| `project.structure.manage` | 待定（更接近入口而非原子业务操作） | 需补契约与可验证结果 |
| `construction.plan.manage` | Composite（计划管理） | 依赖多个原子操作 |
| `project.dashboard.enter` | 边界（进入驾驶舱是入口语义，非完整业务操作） | 需判定是否独立功能 |
| `product_menu_source.json` 的 `capability_key=None` 条目 | 非能力（产品菜单入口） | 应排除出能力目录，归产品入口 |

抽样结论：现有 42/63 条资产混入了入口、页面和载体，不能直接作为能力目录；需按本体定义
重新分类后，CAP-01C 才能生成真实资格与证据。

## 9. 四个关键边界（B0 审查重点）

### 9.1 最小能力边界

“项目创建 / 项目查询 / 项目更新”是否各为独立原子能力，判据是五条件，不是按钮数量或模型数量：

- 三者共享 `project.project` 模型，但目的不同、输入输出不同、验证结果不同 → 三个原子能力。
- 不能因共享模型合并为一个“项目管理”原子能力。
- 也不能因存在三个入口就机械拆成三个；只有各自满足“独立契约 + 可验证结果”才成立。

### 9.2 组合能力 vs 工作场景编排

组合能力（L2）与工作场景（L3）的判据：

- 组合能力：自身有稳定身份、可复用、可独立发布与验证（如“项目成本分析”=项目读取+合同读取+
  成本读取+成本计算，有明确的组合契约和可验证产出）。
- 工作场景：面向某个用户目标的一次完整过程编排，依赖入口/页面/角色/步骤，不独立发布为能力。
- 若一组能力只被一个场景按固定步骤使用、无独立复用和验证价值，则不提升为组合能力，保持为场景编排。

### 9.3 能力身份与成熟度资格解耦

- 能力身份存在 ≠ 已发布。
- 能力可被识别 ≠ 可被产品引用。
- 未发布能力可作为候选资产登记（身份 + Provider + 契约），但不得进入正式产品交付引用。
- 身份、契约化、资格（preview/standard）、发布是四个独立状态，不互相绑定。

### 9.4 能力与产品生命周期解耦

- 一个原子能力可被多个组合能力使用，一个组合能力可被多个工作场景使用。
- 某个产品停用/退役，不得误退役仍被其他产品引用的能力；能力退役必须确认无存活引用。
- 能力退役由“引用闭合检查”驱动，不由任何单一产品发布状态驱动。
