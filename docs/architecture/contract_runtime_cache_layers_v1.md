# 契约运行时缓存分层 v1

日期：2026-10-17
正式产品层：P0
架构层：L1（契约运行时）
运行归属：`smart_core`

## 1. 权威结论

运行时契约只有一条权威链：**动态计算**。缓存是它的加速载体，不是产品事实来源；任何缓存层都不得保存或推断记录事实、权限裁决、业务动作、状态语义或可见性。

四层职责固定如下：

| 层 | 载体 | 允许保存 | 禁止保存 | 键与失效 |
| --- | --- | --- | --- | --- |
| L0 动态计算 | 装配/投影管线（未命中时） | 不保存；本次请求内计算记录覆盖、权限/entitlement、业务动作、策略、修饰符、状态、seal 与终端裁剪 | 不缓存任何结果 | `record_id`/create/preview 请求每请求执行；record-free 未命中也执行，命中则只复用受 §1 三项身份约束的 L1 已装配结果 |
| L1 后端进程热缓存 | `LoadContractResponseCache`（`addons/smart_core/utils/load_contract_response_cache.py`） | ① record-independent 源投影；② **仅 record-free 请求**的已装配契约 | 带 `record_id`/create/preview 的已装配契约 | `cache_key` + `source_token` + 缓存版本 + client/profile/limit 门控；TTL 是第二道边界，不是权限边界 |
| L2 后端持久资产 | `ui_base_contract_asset_repository`（`contract_kind=runtime_source`） | 仅源投影（`ui_data` + 身份化 `ui_meta`） | 已装配契约、record-bound 契约、权限裁决 | `scene_key`（cache_key）+ `role_code` + `company_id` + `asset_version`（source_token）；token 变更即不可达 |
| L3 前端缓存 | `frontend/apps/web/src/app/contracts/v2/client.ts` 的 `createContractCache` | 仅无 `recordId`、无 `previewToken` 的 create 契约 | 编辑/只读记录契约、预览契约、任意后端未声明可复用的契约 | `sessionDb` + `token` + `contextEpoch` + 完整 params；30s TTL；写入受后端 `runtimeContract.cachePolicy` 门控 |

**结论**：`record_id` 请求永远走 L0。它可以*读*L1/L2 的源投影，但不得读写已装配契约；这正是“复用静态结构、逐请求计算记录与权限”的机制化表达。

**命中路径不是逐请求重算**：record-free 已装配命中后，handler 直接复用缓存中的
`source_contract` / `contract`，只执行 runtime seal 并返回。它**不**重新执行
entitlement、字段/业务策略、动作、modifier/status 或 trim。seal 只刷新
request/trace 身份与完整性摘要，**不是授权检查**。因此命中有效性完全由下面三件事
共同保证，任何一项缺失都不得宣称“权限逐请求重算”：

1. `cache_key` 绑定 principal：`uid` + 用户组集合摘要 + 公司 + allowed companies +
   lang/tz + model/view types + 语义化 params；
2. `source_token` 绑定权威：视图、字段、动作、菜单、`ir.model.access`、`ir.rule`、
   `res.users.write_date`、`ir.module.module`、app 配置、业务配置契约的
   `definition_sha256/version_no/status`、字段策略定义集与角色组、代码内容摘要；
3. `ASSEMBLED_CONTRACT_CACHE_VERSION` + client/profile/limit 门控 + 30 s TTL。

角色撤销会使 `cache_key` 的组摘要和 `source_token` 的 `res.users.write_date` 同时
移动；策略变化会使 `source_token` 移动。两者都会让旧条目不可达，见 §5.2 的运行时
反例。TTL 只覆盖未被权威行表达的输入，不能替代上述身份。

L3 的 create 契约包含权限投影。同 token 下的服务端角色变更不会旋转 `contextEpoch`，因此缓存最多陈旧 30 s。这是已声明的**有界降级**，不是权限边界：后端写操作与记录读取仍逐请求授权；最终 seal 只刷新身份与摘要，不是授权。

## 2. 数据流

```text
请求(record_id?)
  → L1/L2 源投影（record-independent，按 source_token 失效）
  → [仅 record_id] PageAssembler.apply_runtime_record_overlay（L0）
  → 路由注入：业务类别、关系契约、动作窗口、协作、记录快照（L0）
  → assemble_unified_page_contract_v2（L0，内部 seal 算 source/contract 摘要）
  → 权限与字段策略、扩展归一化、modifier/status（L0）
  → trim_unified_page_contract_v2（L0，顶层一次深拷贝，子树原地裁剪）
  → [仅 record-free] 写 L1 已装配契约（含语义摘要 memo）
  → 运行时 seal（L0，复用装配期 sourceSha256，重算 contractSha256）
  → 响应
```

record-free 已装配命中走的是另一条短路径：

```text
请求(record-free)
  → cache_key + source_token + version/gate 命中
  → 复用 _assembled_v2.contract / source_contract（LOAN，只读）
  → runtime seal（刷新 request/trace 与 contractSha256）
  → 响应
  （跳过 entitlement / 字段与业务策略 / 动作 / modifier / trim）
```

这条短路径的正确性前提是 §1 的三项身份；它不是“命中后再授权”。

前端 `loadModelContractV2` 只在 `renderProfile === 'create' && !recordId && !previewToken` 时进入 L3；其余请求直接走后端。

## 3. 不变量（fail-closed）

以下不变量由静态结构和非零验证共同强制。I1-I9 由
`make verify.unified_page_contract.v2.assembler` 静态强制；I10 的字段绑定由同一静态
守卫强制，“旧条目必须不可达”由 48 项缓存单测（含角色撤销、ACL/规则/用户行变化、
业务策略定义变化）及 §5.2 的受管运行时探针证明。违反即失败：

1. **I1 记录不入缓存**：handler 不得出现 `get_record_assembled` / `put_record_generated`；已装配读写的门控表达式必须分别保持 `not runtime_record_id and (not is_create_request)` 与 `not runtime_record_id and (not is_create_request) and cache_key and source_token`。
2. **I2 记录覆盖逐请求**：`apply_runtime_record_overlay(` 必须存在于 handler 的装配路径。
3. **I3 持久层只存源**：`ui_base_contract_asset_repository` 不得出现 `_assembled_v2` 或 `contract_v2`。
4. **I4 前端只缓存 record-free create**：三个门控标记必须同时存在；缓存键必须绑定 `sessionDb`、`token`、`contextEpoch`。
5. **I5 版本与代码绑定**：`ASSEMBLED_CONTRACT_CACHE_VERSION` 与装配输入代码摘要 `ASSEMBLED_CACHE_INPUTS_SHA256` 必须同步重钉；任何装配输入变化都必须 bump 版本。
6. **I6 装配期不重复全图哈希**：`_base_contract` 不得为占位 meta 调用 `_fingerprint(source_payload)`；占位值必须来自稳定页面身份，最终 identity 由 seal 生成。
7. **I7 裁剪所有权**：`trim_unified_page_contract_v2` 在顶层做唯一一次 `deepcopy`；`_trim_container` / `_trim_widget` 只允许原地裁剪该副本，不得再次逐节点复制。
8. **I8 传输身份剥离是 copy-on-write**：`strip_request_transport_identity` 对无传输字段的子树返回原对象；任何要修改返回值的调用方必须自行复制（`contract_semantic_payload` 已显式复制顶层）。
9. **I9 命中路径不伪装成重算**：record-free 已装配命中分支必须在 entitlement、字段/业务策略、动作、modifier/status、trim 之前返回；守卫同时要求该分支只做 runtime seal 并 return，禁止这些投影调用出现在分支内；文档与验收不得把 seal 描述为权限或策略重算。
10. **I10 身份必须覆盖角色与策略**：`build_projection_cache_key` 必须包含用户组摘要；`build_projection_source_token` 必须包含 ACL、规则、用户行、字段策略定义集和业务配置契约定义。守卫钉住这些声明载体；角色撤销或策略定义变化后旧条目不可达由非零单测与运行时探针证明。

## 4. 失效矩阵

| 变化 | L1 源投影 | L1 已装配 | L2 持久源 | L3 前端 create |
| --- | --- | --- | --- | --- |
| `source_token` 变化 | 立即失效 | 立即失效 | 立即不可达 | 不适用（key 含 params/epoch） |
| 装配输入代码变化 | 保留 | 版本不符即失效 | 保留 | TTL 内可能命中，故必须 bump 版本 |
| 用户角色/权限变化 | key 含组摘要；token 含 ACL/规则/用户行，旧条目不可达 | **旧条目不可达**（key 的组摘要与 token 的 `res.users.write_date` 同时移动；命中路径不重算权限，seal 不是授权） | 角色 code 不同即不可达 | key 含 token/epoch；**不覆盖**同 token 下的服务端角色变更，30 s TTL 内可有界陈旧 |
| 业务策略定义变化 | token 含 `definition_sha256/version_no/status` 或字段策略定义集，旧条目不可达 | **旧条目不可达**（命中路径不重算策略） | token 不同即不可达 | 不适用 |
| 公司变化 | key 含公司 | 同上 | 公司不同即不可达 | key 含 context epoch |
| 记录字段/关联记录变化 | 不相关 | **不得复用**（record-free only） | 不相关 | 不适用 |
| 上下文变化 | key 含 context | 同上 | 同上 | key 含 context epoch + params |

## 5. 本轮实测（P4 诊断，不冻结）

### 5.1 记录表单热路径

无插桩探针：`make local.dev.runtime.record_form.probe`，场景 `payment.request`
记录表单、`role_finance`、同一记录热重复 6 次；列表作为对照。

**统计口径修正**：旧探针的 `_stats` 用 `values[len // 2]`，六样本时取第 4 个值，
不是中位数；`p95` 用 nearest-rank，六样本时等于窗口最大值。现在中位数取偶数样本
中间两项均值，并显式输出 `p95_equals_max=true` / `p95_interpretation=window_max_observation`。

**已有样本复算（不重跑）**：

| 指标 | 基线 | 本轮 | 变化 |
| --- | ---: | ---: | ---: |
| 记录表单热中位（正确中位数） | 697.437 ms | 483.499 ms | −30.7% |
| 记录表单窗口最大值 | 796.509 ms | 540.022 ms | −32.2%（仅本次窗口观察） |

**修正语义过滤后的同探针 A/B（新窗口）**：

| 指标 | 基线 | 本轮 | 变化 |
| --- | ---: | ---: | ---: |
| 记录表单首次 dispatch | 2669.028 ms | 2513.162 ms | −5.8% |
| 记录表单热中位 | 688.528 ms | 501.288 ms | −27.2% |
| 记录表单窗口最大值 | 711.902 ms | 551.859 ms | −22.5%（仅本次窗口观察） |
| `v2_source_assembly` 热中位 | 130.0 ms | 121.5 ms | −6.5% |
| `post_trim` 热中位 | 84.5 ms | 21.0 ms | −75.1% |
| `post_runtime_seal` 热中位 | 140.5 ms | 38.5 ms | −72.6% |
| `v2_projection_and_seal` 热中位 | 651.5 ms | 405.0 ms | −37.8% |
| 列表热中位 | 14.396 ms | 14.304 ms | 持平（对照） |

**语义等值（修正后）**：旧过滤器按字段名在任意深度删除 `timing`，会把真实业务字段
`data.business.timing.deadline` 也删掉，因此旧的“完整响应等价”结论已撤回。新过滤器
只豁免 10 条已登记精确路径（顶层 `meta.elapsed_ms`、`meta.projection_cache`、
`data.meta` 的四个 request/trace 身份键、两个 contract `context` 容器中的
`trace_id`/`request_id`）。修正后：

- 基线与本轮过滤后完整 SHA-256 均为 `ff6db9d1bdd3beb9…`；
- 契约自身 `contractSha256` 均为 `1673cb0b2f037845…`；
- 按顶层/二级 section 比较，全部摘要相同；
- 两次热响应的差异路径只有 `meta.elapsed_ms` 与 `meta.projection_cache.stages_ms.*`，
  没有任何业务子树。

反例已固化为非零单测：`data.business.timing.deadline` 从 1 改成 2 必须产生不同语义
摘要；未登记的 `context.trace_id` 必须保留。见
`scripts/verify/test_local_dev_runtime_record_form_probe.py`（9 项）。

证据：`artifacts/main-scheduled-ci-closeout-20261016/sce-r14-record-form-{baseline,after}-precise-semantic.log`。
`sce-r13-*` 日志仍是计时证据，但其语义摘要使用了过宽过滤，**不得**再作为等价证明。

### 5.2 缓存身份失效运行时验证

探针：`make local.dev.runtime.projection_cache_identity.probe`。在
`sc-local-dev/sc_dev_demo` 上对声明 principal `role_finance`（uid 45）执行：

| 场景 | 写入（savepoint 内） | 结果 |
| --- | --- | --- |
| 角色撤销 | 移除组 128 `smart_construction_core.group_sc_role_finance_manager` | `cache_key` 变化、`source_token` 变化 |
| 策略变化 | 草稿业务配置契约 id 27（`construction.contract`）`priority` +1 | `source_token` 变化 |
| 回滚恢复 | 两个 savepoint 都回滚 | key/token/组集合全部回到基线 |

commit 被拒绝；两次回滚后重新计算的身份与基线逐字节一致。证据：
`artifacts/main-scheduled-ci-closeout-20261016/sce-r14-projection-cache-identity.log`。

这证明的是“旧条目不可达”，不是“命中后重新授权”。record-free 命中仍然跳过
entitlement/policy/action/modifier/trim，这是已声明的设计边界。

## 6. 新增缓存的决策清单

任何新缓存必须逐项回答；任一答不上来就不得加入：

1. 保存的是**记录无关事实**吗？含 `record_id`、preview、权限裁决或业务动作即拒绝。
2. 键是否覆盖所有权威输入（source token、角色、公司、上下文、client/profile、代码版本）？
3. 失效是否由权威 token/版本驱动，而不是 TTL 或 `write_date` 猜测？
4. 命中后跳过了哪些投影？它们是否都由缓存键与失效 token 保证有效（record-free 命中不重算记录覆盖、权限/策略、动作与 trim；seal 不是授权）？
5. 是否有静态门禁 + 非零测试 + 语义等值证据？

## 7. 边界与未声称

- 本轮不冻结、不 `ci.local.quick`、不推送、不合并、不部署，不宣称批次验收或产品交付完成。
- 首次打开（首次契约约 1.74 s、首次 `system.init` 约 1.75 s）与真实页面端到端等待仍未关闭。
- gen-2 GC 长尾仍未证明消除；本轮只声明上述记录表单热路径的阶段收益与语义等值。
- 不恢复 record 级整装配缓存；不得用 `write_date`、TTL 或前端 key 代替运行时权限与关联记录事实。
