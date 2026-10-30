# PAGE-CONVERGENCE-01 / P3 · 四张概览卡片专业化收敛

结论：四卡已统一为「业务类别标题 → 核心指标/明确不可用状态 → 单位 → 操作入口」的同一套
视觉语法，同时严格保持业务事实边界，四视口无横向溢出、无伪造数值。

## 一、设计决策

四卡由原生视图声明语义 token，渲染器在自身 scoped 作用域内拥有视觉输出。不引入 Vue 专属
卡片组件，不新增全局 CSS / 全局媒体查询 / 第二套卡片协议。

### 层级声明

- Formal Product Layer：P1（建筑行业标准产品的概览卡区块）
- Layer Target：`smart_construction_core` 原生视图 `project_overview_views.xml` +
  `NativeFormTreeRenderer` 的 scoped 视觉输出
- Standard vs User-Specific：Standard（四卡统一视觉语言，业务指标各自表达）
- Why Here：原生视图声明卡片结构，渲染器拥有其视觉输出（与既有 `sc-project-stage` /
  `sc-project-next` 同模式）
- Why Not Elsewhere：不改 P0 契约组装器/解析器、不改结果 B、不改业务计算/ACL
- Blast Radius：仅四卡区块的语义 token 与 scoped 样式；四视口 DOM 验证证明收敛

## 二、四层视觉语法

| 层级 | 表达 | token |
| --- | --- | --- |
| 1 | 业务类别标题 | `sc-project-card__title` |
| 2 | 核心指标或明确不可用状态 | `sc-project-card__value` / `sc-project-card__empty` |
| 3 | 单位 | `sc-project-card__unit` |
| 4 | 辅助说明 / 合法操作入口 | `sc-project-card__action` |

统一规则：标题用 body-small + semibold + 次级色（不压过数值）；数值用 title-large + bold；
单位用 body-small + 次级色并与数值基线对齐；空态用 body-small + 次级色并保留准确说明。

## 三、数据边界（严格保持）

- `sc_project_contract_entry_available`：按真实权限事实呈现（pm1 无合同列表入口 → 显示
  「当前账号的发布范围未提供项目合同列表入口」，不渲染「查看合同」按钮）。
- 成本/财务/项目任务：继续显示「数据暂不可用」，不伪造 0，不把契约缺失解释为业务为空。
- 结果 B 文件、`sc_overview_*_count` 业务计算、ACL/record rule 均未修改。

## 四、交互职责

仅原本具有真实业务跳转的卡片保留可点击行为：成本（查看成本）、财务（查看财务）、项目任务
（查看任务）。合同卡片在无入口权限时不渲染按钮，不产生无效导航。

## 五、四视口验收

| 检查项 | 1440 | 1024 | 768 | 390 |
| --- | --- | --- | --- | --- |
| 四卡渲染 | 4/行 | 4/行 | 2×2 | 单列 |
| 卡片间距统一 | 12px | 12px | 12px | 纵向 |
| 合同权限空态保留 | PASS | PASS | PASS | PASS |
| 三卡「数据暂不可用」 | PASS | PASS | PASS | PASS |
| 伪造 0 份 | 0 | 0 | 0 | 0 |
| 无横向溢出 | PASS | PASS | PASS | PASS |
| 控制台错误 | 0 | 0 | 0 | 0 |

合同卡在无入口权限时无操作按钮，高度随内容自然缩短（内容协调，不强制空白填充）。
