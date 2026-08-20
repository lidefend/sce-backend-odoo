# 产品视图能力台账契约 V1

[English version](product_view_capability_ledger_v1.en.md)

## 1. 目的与边界

本契约定义从 Odoo 原生视图到前端交互的逐能力原子证据链，用于回答“产品契约实际承载了多少原生视图能力”。它属于 P4 证据与门禁机制，测量对象是 P0 `smart_core` 的通用契约链路，不改变业务语义，也不把行业或客户规则放入平台内核。

本阶段只定义测量事实。台账和原因码不是运行时行为来源，不得被前端用于推导缺失语义。

## 2. 权威运行身份

每份台账必须绑定既有 `codex_complete_worktree_fingerprint/v1` 完整候选指纹、Git HEAD、基线 SHA、范围清单哈希，以及数据库架构政策、正式菜单政策、原因码注册表、视图结构基线、模块版本集合、用户、公司、语言和权限组。运行身份固定为 `local.clean` / `sc-local-clean` / `sc_clean` / `^sc_clean$` 且 `demo_data=false`，不得使用 Git commit SHA 代替完整指纹，也不得使用手工拼装的 Compose、数据库或凭据代替。

## 3. 能力原子与证据链

一个能力原子代表原生视图中一个可定位的实际出现，而不是去重后的字段名或按钮名。`occurrence_index` 是同一父节点下相同基础 locator 的一基序号；每个 atom 本身只代表一次出现。`atom_id` 不包含 value hash，必须能稳定区分重复字段、重复按钮、继承贡献和嵌套子视图。

证据链依次记录 `native`、`normalized`、`semantic` 和 `frontend`。前端阶段必须明确绑定规范原子、兼容投影、消费符号、渲染器和交互符号。`source_authority` 必须显式声明；多个来源共同决定行为但没有唯一权威时，不能判定为就绪。

## 4. 终态规则

每个原生能力原子必须且只能获得一个终态：

- `ready`：规范化、语义、前端消费和交互证据完整，且不存在语义猜测或未声明覆盖。
- `fallback`：存在明确、受治理、可追踪的降级路径，但未完整承载原生能力。
- `unsupported`：没有可用载体或渲染器，或者能力被明确拒绝。

`ready` 的 `reason_code` 必须为空，且三层载体均为 `present`、计数非零、哈希可复算、前端来源唯一并具有非空消费/渲染/交互符号；`fallback` 和 `unsupported` 必须引用状态与首个损失阶段相符的注册原因码。`gate_effect=silent_loss` 的原因不能形成可发布台账。未知、静默删除和无法分类不是合法终态。

静态存在一个字段、解析器节点或渲染器，只能证明载体存在，不能证明端到端就绪。动态修饰符、权限判断、记录上下文和交互行为必须绑定受治理的运行证据；未执行时至少为 `fallback`。

## 5. 无静默损失门禁

哈希输入使用 UTF-8 canonical JSON：对象键排序、无无意义空白、Unicode 不转义；`manifest_sha256` 覆盖除自身外的完整台账。守卫必须复算全部内容哈希和清单哈希，核对权威身份、汇总守恒、唯一 `contract_ref`/`atom_id`、`menu_xmlid::canonical_view_type` 关系、来源贡献图及原因码。`list` 仅作为输入别名并规范为 `tree`，不得出现在台账中。

`evidence_refs` 固定包含仓库相对路径、文件 SHA、候选指纹、阶段和可解析 selector。守卫必须证明文件存在、内容哈希一致、候选同源且 selector 能定位事实。任何原生能力没有终态、证据断链、哈希不符、汇总不符或原因码未知，都计入 silent loss 并使门禁失败。

验收要求原生能力出现数等于 `ready + fallback + unsupported`，`silent_loss_count` 等于零，每个非就绪原子都有注册原因和可执行退出条件，并且全部证据绑定同一冻结候选指纹。

原因码权威文件为 `contracts/product/native-view-capability-reason-codes-v1.yaml`，taxonomy 为 `contracts/product/native-view-capability-taxonomy-v1.yaml`，结构约束为 `contracts/schemas/product-view-capability-ledger-v1.yaml` 和 `contracts/schemas/native-view-capability-reason-codes-v1.yaml`。Schema 只能表达局部约束；跨文件引用、唯一性、守恒、原因码阶段匹配和哈希复算必须由 fail-closed 守卫执行。
