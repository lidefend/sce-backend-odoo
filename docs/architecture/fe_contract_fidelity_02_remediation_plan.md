# FE-CONTRACT-FIDELITY-02

## 前端契约忠实度系统性整改计划

### 0. 状态与授权边界

| 项目 | 值 |
| --- | --- |
| 状态 | `PLANNING_ONLY` |
| 架构负责人裁定 | 接受 `FE-CONTRACT-FIDELITY-01` 的 `NOT READY` 结论 |
| 审计 PR | #969 |
| 审计源 HEAD | `bd70df6171ec930ea866e2fdd7b525ca5bcd7573` |
| 审计合并提交 | `0f7dce48a360249ec46ee5b4f6ddc6466f4ad37e` |
| 规划基线 | `main@0f7dce48a360249ec46ee5b4f6ddc6466f4ad37e` |
| 产品源码修改 | 否 |
| 后端契约/ACL/工作流/数据库修改 | 否 |
| 产品修复授权 | 本计划经独立审查并由架构负责人批准后才生效 |

本文件只把审计事实转成整改计划。它不实现任何页面修复，不修改
`frontend/apps/web`、`frontend/packages/ui`、`addons/smart_core` 的产品行为，
也不创建第二套值运行时、Renderer、Registry、Bundle 或页面引擎。

### 1. 输入事实

已接受的审计矩阵包含：

| 结果 | 数量 |
| --- | ---: |
| 适用单元 | 140 |
| PASS | 92 |
| MISSING | 0 |
| LOST | 19 |
| ALTERED | 2 |
| INFERRED | 2 |
| DUPLICATED | 6 |
| NOT_APPLICABLE | 28 |
| NOT_VERIFIED | 19 |
| 已确认缺陷单元 | 29 |

`MISSING=0` 只说明存在消费入口。整改必须解决“入口存在但不忠实消费”的问题。
`NOT_VERIFIED` 不计为 PASS。只有声明、传输、前端解释和实际行为均有证据时才可改判。

本阶段保留并复用以下已经成立的边界，只做受影响回归：

- Contract V2 schema 解码；
- field modifiers、readonly、required；
- action status、target、reason 与执行器；
- canonical navigation 与 route authority；
- semantic registry；
- List aggregate currency identity；
- One2many relation、percentage 与 digits；
- 现有合同查询、ORM 写入和权限接口。

### 2. 目标架构

整改目标是建立一个固定分工，而不是建立一个更大的万能组件。

```text
后端权威声明
  -> Contract V2 / API 语义载体
  -> 唯一业务语义裁决
  -> 场景呈现适配
  -> Form / List / Kanban / One2many / Readonly / My Work / Page Block
```

四层责任如下：

| 层 | 必须负责 | 禁止承担 |
| --- | --- | --- |
| 后端契约 | 字段类型、componentKey、digits、currency、selection、unit、时区、关系身份、附件身份与角色、动作和反馈 | 页面视觉密度 |
| 语义裁决 | 判断业务值是什么、缺声明时 fail-closed、给出稳定语义结果 | 页面布局和视觉样式 |
| 传输载体 | 原样携带 raw value、字段描述和必要上下文 | 提前字符串化、丢失身份、补默认规则 |
| 表现组件 | 根据场景选择表单、列表、卡片、徽标、紧凑/完整展示 | 重新决定业务语义 |

唯一业务语义裁决继续由现有契约感知路径承担，以
`presentDeclaredBusinessValue()` 为起点。`formatDisplayValue()` 可以保留为底层
文本/原生兼容工具，但不得再成为与契约感知路径并列的业务语义权威。

页面可以有不同的信息密度，但相同的 field、componentKey、type、digits、currency、
unit、timezone、relation identity 和 attachment role 必须得到相同解释。

### 3. 语义传输载体

第二批需要一个显式传输载体，而不是在桥接层执行 `String(value)`。计划采用以下
形状作为候选，最终类型名和模块位置在实现审查时定稿：

```ts
type ContractValueEnvelope = {
  field: {
    name: string;
    type: string;
    widget?: string;
    componentKey?: string;
    cellRole?: string;
    selection?: readonly (readonly [string, string])[];
    digits?: readonly [number, number];
    currencyField?: string;
    unit?: string;
    attachmentRole?: string;
  };
  rawValue: unknown;
  context?: {
    currency?: { id: number; label: string };
    timezone?: string;
  };
};
```

约束：

1. `rawValue` 保留后端原始类型，不因只读展示提前转成字符串。
2. 关系值必须至少保留记录 ID 和显示名称；仅有 ID 时按契约缺口停机。
3. 金额、百分比、时长和普通数值分别保留声明身份和精度。
4. 附件必须保留稳定附件身份、文件名、类型、来源记录及语义角色。
5. 时区必须来自当前用户的权威运行上下文，不从浏览器猜测。
6. 传输载体只传递事实，不执行格式化，更不得把展示文本写回 ORM。
7. 若现有 Contract V2 已有一部分字段，优先扩展既有描述符；不创建平行字段字典。

#### FCF-02-2 载体验收设计门

`ContractValueEnvelope` 只是候选形状，最终实现必须逐项通过以下审查条件：

| 条件 | 必须证明 |
| --- | --- |
| `CARRIER-01` | `rawValue` 保留后端原始类型，桥接层不提前字符串化、取整或重构事实 |
| `CARRIER-02` | field descriptor 保留全部适用 type、widget、componentKey、digits、currency、unit、selection 和 temporal 语义 |
| `CARRIER-03` | relation identity 同时具备可验证记录身份和权威显示名称；显示名称不能替代身份 |
| `CARRIER-04` | attachment identity、record ownership、role、authorized action 和 failure feedback 均有明确契约来源 |
| `CARRIER-05` | currency 与 timezone 来自权威运行上下文，不来自显示标签、进程 locale 或浏览器默认时区 |
| `CARRIER-06` | 展示值不得成为 ORM 写入值 |

Page Block 还必须单独证明 action target、permission result、disabled reason、
error reason code、message 和 trace identity 在桥接及最终表达中完整保留。

### 4. 契约缺口探测

以下七项必须先完成只读核查。已经存在的声明直接消费；确实缺失时登记为 P0
生产端缺口，另批修订，前端不得补默认值。

| ID | 待确认语义 | 已有线索 | 缺失时唯一正确动作 |
| --- | --- | --- | --- |
| `CFG-GAP-01` | 当前用户时区权威与传递 | login/profile、API 请求上下文和 Contract V2 locale 均有时区入口 | 明确唯一权威并在 P0 契约/请求上下文暴露 |
| `CFG-GAP-02` | Page Block 业务值载体 | 当前 block payload 主要使用松散 dataset | 增加显式 value/field/unit/action/feedback 声明，不在组件内猜 |
| `CFG-GAP-03` | My Work fact 身份 | 现有 fact 仅有 text/money/datetime role 与 money 数字精度 | 补齐 percentage、currency identity、selection/relation/duration 所需声明 |
| `CFG-GAP-04` | 附件身份与角色 | Contract V2 有 attachment zone，附件 API 有下载授权身份 | 统一稳定角色、附件 ID、记录归属与动作语义 |
| `CFG-GAP-05` | Page Block 动作与反馈 | 部分块有 action_key，反馈结构尚未形成统一声明 | 明确动作目标、权限原因、失败 reasonCode 与可见反馈 |
| `CFG-GAP-06` | Form 内嵌集合聚合适用性 | 审计将 Form 的 collection aggregate 标为未验证 | 若 Form 不承载该语义则登记 `NOT_APPLICABLE`，否则消费同一集合契约 |
| `CFG-GAP-07` | Dialog duration 语义 | 对话框可能承载 `float_time` 或其他 duration 输入 | 明确字段身份、单位、计算、输入投影、只读表达和 ORM 兼容写入值 |

缺口探测输出必须包含：声明位置、API 字段、前端消费者、实际运行回读、结论
`sufficient` / `contract_gap` / `not_applicable`。不得用文本存在代替运行行为。

缺口结论是机器门控，不是说明文字：

```text
sufficient ------------------------------+
                                        |
not_applicable -------------------------+--> dependent frontend batch
                                        |
contract_gap -> P0 producer remediation -+
                     |
                     +--> owning declaration
                          consumer decode
                          independent review
                          registered verification
                          |
                          +--> dependent frontend batch unlock
```

`contract_gap` 在 P0 声明、消费解码、独立审查及验证完成之前，禁止通过前端默认值
或临时兼容规则解锁。`FCF-02-1` 不依赖任何缺口探测，可以独立先行。

### 5. 整改批次

#### FCF-02-1：统一业务语义解释权

覆盖：`FCF-07`、`FCF-08`、`FCF-01`、`FCF-06`。

目标：

- 契约字段进入 `FieldValue`、`ProfessionalBaseFieldControl`、FormSection、
  Hierarchy 和 Kanban fallback 时保留完整字段描述与 `componentKey`。
- 契约感知路径成为业务语义裁决权威。
- `formatDisplayValue()` 不再独立决定 selection、relation、status、percentage、
  duration 等契约语义。
- List 未知 selection 不得显示原始存储 key，进入显式契约缺口状态。
- List/Kanban relation 保持记录身份，禁止裸露 ID。
- Kanban 标题回退携带声明的字段描述。

最小文件候选：

- `frontend/apps/web/src/app/presentation/businessValuePresentation.ts`
- `frontend/apps/web/src/utils/display.ts`
- `frontend/apps/web/src/components/FieldValue.vue`
- `frontend/apps/web/src/components/professional-fields/ProfessionalBaseFieldControl.vue`
- `frontend/apps/web/src/components/template/FormSection.vue`
- `frontend/apps/web/src/components/action/HierarchyPlanner.vue`
- `frontend/apps/web/src/components/action/HierarchyBrowser.vue`
- `frontend/apps/web/src/pages/KanbanPage.vue`
- `frontend/apps/web/src/pages/ListPage.vue`
- `frontend/apps/web/src/pages/listPage/listCellPresentation.ts`

验收：

- 未知 selection 的组件测试产生 `ContractGapError` 或等价可见停机态，绝不显示 raw key。
- relation tuple、object 和纯 ID 的边界测试证明只有带身份的记录能显示。
- percentage、duration、status 和 money 的 `componentKey` 传递测试。
- 空值、零值、负值、布尔值和未知值反例。
- List、Kanban、Form、Readonly 组件浏览器回归，1440/390 无横向溢出。
- One2many 的关系、精度、行身份、dirtyFields、onchange 和保存 payload 回归不变。

退出条件：

四项发现全部关闭；旧解释器中的所有生产旁路均被删除、登记为合法底层工具，或有
明确的 `NOT_APPLICABLE` 证据。不得为了统一 UI 把所有场景合并成单一组件。

#### FCF-02-2：恢复业务语义传递完整性

覆盖：`FCF-02`、`FCF-03`，并承接 `CFG-GAP-02`、`CFG-GAP-04`、`CFG-GAP-05`。

目标：

- Readonly Collection 桥接停止把记录字段提前字符串化。
- Normalized collection adapter 接收并传递业务值载体。
- Page Block metric、progress、summary、table 消费统一值载体。
- relation、selection、money、percentage、temporal、duration、empty/zero、attachment
  在桥接后仍可被最终 Renderer 判断。
- Page Block 动作与失败反馈消费后端声明，不由块组件猜。

最小文件候选：

- `frontend/apps/web/src/app/renderers/sceneReadonlyCollectionBridge.ts`
- `frontend/packages/ui/src/contracts/normalizedCollectionAdapter.ts`
- `frontend/packages/ui/src/contracts/sceneObjectPage.ts`
- `frontend/apps/web/src/components/scene/SceneBlocksRenderer.vue`
- `frontend/apps/web/src/components/page/blocks/BlockMetricRow.vue`
- `frontend/apps/web/src/components/page/blocks/BlockRecordSummary.vue`
- `frontend/apps/web/src/components/page/blocks/BlockRecordTable.vue`
- 视缺口结论增加的 P0 契约 producer/consumer 文件

验收：

- 同一记录业务值经 Readonly Collection 和标准 Field Renderer 得到相同语义。
- `[id, "名称"]`、对象、attachment ref、selection、money、percentage、datetime
  和 duration 不被字符串化丢失。
- 附件普通整数、文本中的 URL、真正附件引用三类边界不互相误判。
- Page Block 缺 value/unit/field/action 声明时 fail-closed 并展示明确契约缺口。
- Page Block action target、permission result、disabled reason、error reasonCode、
  message 和 trace identity 在桥接后仍可验证。
- relation identity、attachment identity/ownership/role/action/feedback、currency、
  timezone 和 raw value 满足第 3 节 `CARRIER-01..06`。
- 真实组件浏览器覆盖 1440/390；只读页面不产生额外写请求。

退出条件：

字段语义在桥接层不再丢失；如果某些语义确实不在后端 payload 中，必须由独立 P0
契约缺口批次补齐后才继续，不得在前端恢复“看起来合理”的显示。

#### FCF-02-3：移除前端自造业务规则

覆盖：`FCF-04`、`FCF-05`，并承接 `CFG-GAP-03`。

目标：

- Progress Summary 不再在缺 unit 时补 `%`。
- Progress Summary 不再自行夹取或取整后端业务值。
- My Work 不再在缺 digits 时补两位小数。
- My Work 消费已声明的 percentage、currency、selection、relation 和 duration 身份。
- 预算、进度或状态的计算留在后端；前端只解释返回事实。

最小文件候选：

- `frontend/apps/web/src/components/page/blocks/BlockProgressSummary.vue`
- `frontend/apps/web/src/app/presentation/productMyWorkPresentation.ts`
- `frontend/apps/web/src/api/myWork.ts`
- 视缺口结论增加的 `smart_core` 或工作项事实 P0 producer/consumer 文件

验收：

- unit 缺失、precision 缺失、percentage 缺失和 currency 缺失均 fail-closed。
- 零、负数、超 100 的原始事实不被前端改写；是否合法由契约/后端决定。
- 小数业务事实不得因缺少声明而被隐式取整；只有已声明呈现精度可以影响显示文本，
  原始事实和 ORM 写入值保持不变。
- 同一金额在 My Work、List、Form 和 One2many 使用同一币种和精度。
- My Work 百分比显示为业务百分比，不显示裸数字字符串。
- 现有动作、排序、字段分组和目标路由回归不变。

退出条件：

所有前端默认业务值已删除；缺声明时有明确缺口回执或可见停机态。

#### FCF-02-4：关闭全部 NOT_VERIFIED

覆盖：本计划第 6 节的 19 个矩阵单元。

目标：

- 对每个单元完成“契约声明 -> API 解码 -> 前端消费 -> 实际行为”证据。
- 改判只能是 `PASS`、新缺陷、`NOT_APPLICABLE` 或仍为 `NOT_VERIFIED`。
- 不使用静态结论替代用户时区、附件授权、Page Block 和 My Work 的运行事实。

本批不是重跑全站随机回归，而是按语义和受影响表面执行最小证据集。可从早期批次
并行开展只读探测，但只有前置实现稳定后才冻结最终结论。

退出条件：

- `NOT_VERIFIED=0`；
- 新发现缺陷均有责任层和关闭批次；
- 已通过边界没有被重新实现；
- 最终复审重新计算矩阵，不用“抽样覆盖率”替代全量清单。

#### FCF-02-5：最终交付资格复审

只有以下条件全部满足才可提出 `CONTRACT FIDELITY READY`：

1. `FCF-01` 至 `FCF-08` 全部关闭。
2. 原 19 个 `NOT_VERIFIED` 全部闭合。
3. 矩阵中不再有未解释的 LOST、ALTERED、INFERRED、DUPLICATED。
4. Contract Fidelity Guard 全规则为 enforce。
5. 同一业务值跨页面语义一致。
6. 精确 HEAD 的 lint、strict typecheck、单元测试、生产构建和受影响浏览器证据通过。
7. 当前 HEAD 的远端四项必需检查通过。
8. 独立复审确认声明、消费和实际行为三段闭环。

### 6. NOT_VERIFIED 闭合矩阵

| ID | 表面 / 语义 | 必需探测 | 允许的关闭结果 |
| --- | --- | --- | --- |
| `NV-01` | Form / timezone | 用户时区来源、请求上下文、datetime 输入与只读表达 | PASS、缺陷或契约缺口 |
| `NV-02` | Form / collection aggregate | Form 是否承载内嵌集合与聚合 | PASS 或 NOT_APPLICABLE |
| `NV-03` | List / timezone | list API context、日期列和跨时区回读 | PASS 或缺陷 |
| `NV-04` | Kanban / timezone | 卡片时间 facts 与用户时区 | PASS 或缺陷 |
| `NV-05` | One2many / timezone | 明细 datetime 只读显示与编辑输入 | PASS 或缺陷 |
| `NV-06` | One2many / attachments | 行附件身份、角色、预览、下载 | PASS 或契约缺口 |
| `NV-07` | My Work / selection | state/status 标签、未知值处理 | PASS 或缺陷 |
| `NV-08` | My Work / relation | 项目、往来方、经办记录身份 | PASS 或契约缺口 |
| `NV-09` | My Work / timezone | 创建/更新时间与用户时区 | PASS 或契约缺口 |
| `NV-10` | My Work / duration | duration fact 身份和计算规则 | PASS 或契约缺口 |
| `NV-11` | My Work / attachments | 附件 fact、身份、授权动作；由 `CFG-GAP-04` 唯一负责 | PASS 或契约缺口 |
| `NV-12` | Page Block / action reason | action target、授权、disabled reason | PASS 或契约缺口 |
| `NV-13` | Page Block / feedback | 错误 reasonCode、message、traceId 和可见表达 | PASS 或契约缺口 |
| `NV-14` | Dialog / timezone | 对话框中的 datetime 输入和回显 | PASS 或缺陷 |
| `NV-15` | Dialog / duration | 时长输入、显示与写入；由独立 `CFG-GAP-07` 负责 | PASS 或契约缺口 |
| `NV-16` | Dialog / attachments | 附件选择、稳定身份、失败反馈 | PASS 或契约缺口 |
| `NV-17` | Native Contract Runtime / timezone | locale/context 解码和所有 native temporal consumer | PASS 或缺陷 |
| `NV-18` | Native Contract Runtime / attachments | attachment zone、字段关系、动作声明 | PASS 或契约缺口 |
| `NV-19` | Shared interpreters / timezone | 共享时间工具是否消费权威时区 | PASS 或缺陷 |

跨环境证据要求：

- 业务记录通过稳定业务键、动作身份或 fixture alias 定位，不把数据库自增 ID 写进测试。
- 货币、公司、角色和记录身份在运行时回读并记录为证据，不跨环境复用数值身份。
- 日期时间测试固定输入、用户时区和预期输出，浏览器宿主机时区不得改变结论。
- 附件测试通过已登记授权接口读取，不绕过 ACL，不创建新的上传/下载权限。

### 7. 依赖关系

```text
Plan approval
  |
  +--> FCF-02-1 authority (independent)
  |
  +--> CFG-GAP-01..07 read-only probes
         |
         +-- sufficient / not_applicable --> dependent batch
         |
         +-- contract_gap --> P0 producer remediation
                                  |
                                  +--> producer declaration
                                       consumer decode
                                       independent review
                                       registered verification
                                       |
                                       +--> dependent batch unlock

FCF-02-1 + CFG-GAP-02/04/05 --> FCF-02-2 semantic transport
FCF-02-1 + FCF-02-2 + CFG-GAP-03 --> FCF-02-3 remove invented rules
FCF-02-1/02/03 + CFG-GAP-01..07 --> FCF-02-4 close NOT_VERIFIED
FCF-02-4 --> FCF-02-5 readiness review
```

依赖规则：

- `FCF-02-1` 可直接启动，但必须为后续载体定义唯一裁决接口。
- `FCF-02-2` 依赖对应契约缺口结论；不能先用前端默认值让页面通过。
- `FCF-02-3` 依赖 `FCF-02-1` 的权威和 `FCF-02-2` 的载体，避免再次出现局部格式化器。
- `CFG-GAP-03` 仅负责 My Work fact identity，不负责 Dialog duration。
- `CFG-GAP-04` 是 My Work、One2many、Dialog 和 Native Runtime 附件语义的唯一附件责任探测。
- `CFG-GAP-07` 独立负责 Dialog duration，不得借用 My Work fact identity。
- `FCF-02-4` 的静态核查可并行，最终运行证据必须在产品实现稳定后采集。
- 各批可形成独立 PR；不得并行修改同一批共享文件并把依赖顺序倒置。

### 8. Contract Fidelity Guard

Guard 是现有治理体系中的 P4 静态/测试门禁，不是产品运行时。

计划入口：

- `make verify.frontend.contract_fidelity.guard`
- `scripts/verify/frontend_contract_fidelity_guard.py`
- `docs/architecture/fe_contract_fidelity_02/guard_catalog.json`
- 回归矩阵：`docs/audit/fe_contract_fidelity_01/matrix.json`

当前阶段的规划一致性由独立 P4 门禁锁定：

- `make verify.frontend.contract_fidelity.plan.unit`
- `scripts/verify/contract_fidelity_plan_guard.py`
- `scripts/verify/test_contract_fidelity_plan_guard.py`

该门禁只验证规划文件的矩阵映射、依赖 DAG、Guard 目录和载体条件，不是已经实现的
Contract Fidelity Guard，也不声称产品行为通过。

规则分层：

| 层 | Guard 能力 |
| --- | --- |
| 类型层 | 契约字段只通过保留 field/rawValue/context 的载体进入适配器 |
| 静态层 | 扫描桥接层无声明字符串化、raw selection fallback、默认 precision/unit |
| 行为层 | 反例组件测试证明未知值、混合币种、缺精度、缺单位和附件边界 |
| 契约层 | componentKey、digits、currency、unit、timezone、attachment role 的 producer/consumer 对齐 |
| 证据层 | 矩阵单元绑定真实源码、定向测试和必要的浏览器/API 回读 |

其中 `CFG-003` 明确禁止前端夹取、取整或改写原始业务事实。`CFG-011` 单独覆盖
Page Block 的 action target、permission result、disabled reason、error reasonCode、
message 和 trace identity。

Guard 不覆盖或声称替代以下事项：

- 后端 ORM 正确性；
- ACL 或动作真实授权；
- 用户时区跨环境运行事实；
- 附件下载授权；
- 完整业务旅程；
- 生产部署和用户验收。

### 9. 每批通用验收门槛

每个整改候选必须记录：

1. 精确 base、branch、HEAD、tree 和 owned file scope。
2. Formal Product Layer、Layer Target、Module、Standard vs User-Specific、
   Why Here / Why Not Elsewhere、Blast Radius。
3. 受影响既有测试族和新增反例；零测试不算通过。
4. `make ci.local.iteration` 的真实非零结果。
5. 前端 lint、strict typecheck、生产构建。
6. 受影响的真实组件/页面测试；视行为覆盖 1440 与 390。
7. 原通过边界的回归证据。
8. 精确 HEAD 远端四项必需检查。
9. 独立审查与 clean worktree。
10. 失败分类为产品、契约、基线证据、环境或验证工具缺陷，不能混写为 PASS。

真实业务样板优先覆盖：

- 项目台账；
- 收入合同；
- 付款申请；
- 我的工作。

样板选择不是业务语义特判。测试只通过这些页面证明相同的公共解释能力。

### 10. 非目标

- 视觉美化、品牌重设计或局部交互润色；
- 新增业务模块、页面引擎或通用组件平台；
- 修改行业或客户业务规则；
- 后端模型、ACL、工作流、状态机和持久数据迁移；
- 重新实现已经通过的 Contract V2、navigation、action、List aggregate currency
  和 One2many precision/relation；
- 用浏览器选择器、DOM 字样或测试数量代替语义证据；
- 在缺少契约时补一个前端默认值并宣称兼容。

### 11. 审查结论与下一步

本计划请求的裁定只有一项：

> 是否批准按 FCF-02-1 至 FCF-02-5 的能力边界与依赖顺序进入系统性整改。

批准后，执行器仍需先完成对应批次的只读契约核查和验证计划；本文件不构成产品修复
授权、不构成后端契约修改授权，也不代表任何页面已经通过契约忠实度验收。
