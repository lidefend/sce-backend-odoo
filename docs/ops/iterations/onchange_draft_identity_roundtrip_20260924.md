# onchange 回填必须绑定它所依据的草稿（2026-09-24）

本记录只收口一个共享缺陷：onchange 响应是**派生**结果，却被回填到当时的任意草稿上。
未扩大为字段策略、保存链或关系控件改动；关系控件收敛与结算工作表修复各有独立记录。

## 层与边界声明

- Formal Product Layer：P0 平台通用产品。表单草稿身份与派生回填顺序是平台机制。
- Layer Target：`frontend/apps/web/src/pages/contractForm/`（`useRecordFormState` 及其纯函数模块）。
- Module：前端 web app 通用表单运行时。
- Standard vs User-Specific：平台通用规则；不对合同、结算或任何模型加特例。
- Why Here：草稿与请求的对应关系只存在于表单运行时；契约与后端不掌握"用户此刻输入了什么"。
- Why Not Elsewhere：不在后端做去抖或丢弃，不在页面层给单个模型打补丁，不用定时器掩盖顺序问题。
- Blast Radius：所有经 `useRecordFormState` 的 onchange 回填路径（合同表单为首个消费者）。

## 根因

`onchange` 响应由**较早**的草稿算出，但原实现把返回内容原样写入**当前**表单数据：

1. 被取代的响应（用户已发出更新的一次编辑）后到，把计算字段回退成旧答案；
2. 响应覆盖用户在请求发出**之后**才输入的字段（服务端是按它收到的值作答的）；
3. 响应跨越记录切换仍在途，被写到**下一条记录**的表单数据上。

三者同一根因：响应没有携带"它属于哪个记录、第几次请求、依据哪份草稿"。

## 修改文件

| 文件 | 作用 |
|---|---|
| `frontend/apps/web/src/pages/contractForm/onchangeRoundtripIdentity.ts`（新增） | 纯函数：记录键、请求票据、草稿快照、响应/字段是否仍适用、应用计划 |
| `frontend/apps/web/src/pages/contractForm/useRecordFormState.ts` | 发请求时生成票据与快照，只应用 `plan.patch`，整份响应被丢弃时直接返回 |
| `frontend/apps/web/scripts/onchange_roundtrip_race_test.mjs`（新增） | 以真实组合式闭包 + 假传输手控响应顺序，验证三种竞态 |
| `scripts/verify/onchange_roundtrip_guard.py` | 增加必需标记，并把 `Object.entries(patch)` 列为**禁止**标记 |
| `make/frontend.mk` | `verify.frontend.onchange_roundtrip.guard` 同时运行竞态测试 |

判定规则：记录键不一致或票据被取代 → 整份响应丢弃；同一响应内，本地可比值在请求之后已移动的字段 → 逐字段丢弃。

## 定向验证

- `make verify.frontend.onchange_roundtrip.guard`：竞态测试 PASS（checks=4），守卫 `[OK]`。
- 非永真证据（两次）：暂存两个源文件后，竞态测试失败并报
  `actual: 'from-first', expected: 'from-second'`（旧答案覆盖新草稿）；守卫报出全部 6 个新增标记缺失且禁止标记存在。
- 同时 PASS：`verify.frontend.onchange_contract_schema.guard`、`verify.frontend.onchange_line_patch.guard`、
  `verify.frontend.create_record_user_journey.unit`（checkpoints=defaults,single-flight-save,reopen,edit,submit,refresh）、
  `verify.frontend.typecheck.strict`、`verify.frontend.lint.src`（0 error，39 项既有 warning，新增文件无 warning）、`make ci.local.iteration`。
- `vue-tsc` 结论保持"31 项既有错误、未新增"，不等于类型检查通过。

## 状态与边界

- 本地提交，未推送、未合并；未在真实浏览器复验该竞态（无受控的超时/乱序注入手段），不宣称浏览器通过。
- 已核实与本次改动无关、在纯净 main 上同样失败的既有项：`verify.frontend.no_new_any_guard`
  （`useBusinessConfigRemediationLifecycle.ts` 等 3 个文件 any 计数超基线）；该守卫只属于
  `verify.frontend.suggested_action.all`，不在任何 Gitee 必需门禁内。

## 普通保存回归（浏览器，注册验收通道，2026-09-24 补充）

竞态证据仍是组合式闭包测试；本节补的是**普通保存路径**的真实浏览器证据，两者分开报告，互不替代。
入口用注册的 `make acceptance.frontend.core_record_form.journeys`（受管 acceptance profile：
`sc_fe-r2-p1-01` / `sc_frontend_acceptance` / 5175，前端由当前工作树 `dist-release` 构建，
夹具在 EXIT 时重置），不新建夹具系统。

改动文件：`scripts/verify/frontend_core_record_form_journeys.mjs`

- 新增 J14：对 `sc.general.contract` 保存注入一次传输层失败（`route.fulfill` 500，请求未到服务端），
  断言失败提示出现、**草稿仍在输入框中**；撤掉注入后**不重新输入**直接重试保存，刷新回读必须等于该草稿；
  最后把记录改回进入时的值并再次回读，完成清理。
- 修正 J12 的过时定位：返回动作按当前权威的 `[data-form-secondary-action="return-list"]` 定位，
  不再依赖会随文案变化的可访问名 `返回列表`（当前文案为 `返回`）。断言强度未降低，只是换成产品自声明身份。

浏览器结果：

| 项 | 结果 |
|---|---|
| J12 修改→保存→刷新回读（`fixture_role_contract_operator`） | PASS（`dirty_guard`/`cancel_retains_input`/`save_and_reload` 均 true） |
| J14 保存失败保草稿 | PASS，`failure_retains_draft=true`，失败提示文本 `injected save failure` |
| J14 重试成功（未重新输入）+ 权威回读 | PASS，`retry_persists_without_retyping=true` |
| J14 清理回读 | PASS，`restored_to_authority=true`；DB 复核 `sc_general_contract(10)='FE-A General Contract'`，`like '%J14%' or '%J12%'` 计数 0 |
| J14 注入确实命中保存请求 | 唯一 1 条 500：`intent=api.data, op=write, model=sc.general.contract, ids=[10]` |
| 运行期错误 | `console=[]`、`pageerror=[]`；`unexpectedHttp` 仅上述被注入的一条（J14 主动断言） |

已知既有缺陷（本次未修改，也不因它调整断言）：J13 第一步在付款申请新建页清空金额后点“保存草稿”，
期望出现必填校验汇总 `请检查以下内容`；当前产品允许该草稿保存（状态草稿、金额 0.00，办理前置条件里才提示
“金额必须大于 0”），因此该断言必然超时失败。旁证：acceptance 库存在 2026-08-24 由同一路径产生的
`PRQ2600326`（金额 0.00），说明该分歧早于本次改动。J13 属移动端冲突保留用例，与本次 onchange 缺陷无关；
是否收紧产品“草稿金额”语义需产品决定，本记录只登记，不擅自改产品规则。
