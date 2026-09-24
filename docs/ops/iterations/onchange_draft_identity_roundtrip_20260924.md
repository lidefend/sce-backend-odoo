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
