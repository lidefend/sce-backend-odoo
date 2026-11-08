# FE-RENDERER-02C-01-R2C：空值状态契约校验

## 批次边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：状态声明校验与空值表达顺序。
- Module：`businessValuePresentation`、业务语义测试和静态守卫。
- Baseline：`22e3b34af2198436e414deed13c25f8ec01780c2`。
- PR：#840，仅更新候选，不合并、不部署。

## 审查结论

当前 `presentDeclaredBusinessValue` 先判断 value 是否为空，再进入 status 类型与 selection
校验。这样当前记录值为 `null` 时，缺失状态类型或缺失 selection 投影会直接返回空值，
把契约缺陷掩盖为正常无数据。

正确顺序是：

1. 解析字段业务种类。
2. 若声明为 status，验证 `selection|char` 类型身份。
3. selection-backed status 验证有效 selection 投影。
4. 最后判断当前记录值是否为空并返回统一空值表达。

## 验收

- 未声明类型的 status，`value=null`：`ContractGapError`。
- selection 类型缺少 selection，`value=null`：`ContractGapError`。
- 合法 selection，`value=null`：返回平台统一空值表达。
- 合法 char-status 继续可用。
- 静态守卫固定“声明校验先于空值返回”。
- 业务语义、BOQ、Lint、Strict Typecheck 和真实 `ci.local.iteration` 非零通过。

## 执行结果

- 业务语义：PASS，`money=6 status=20 temporal=4 empty=3`。
- 静态守卫：PASS，12 tests；把 status 契约解析移到空值返回之后会被拒绝。
- BOQ：PASS，只读投影 22 checks、请求模型 27 checks。
- Lint：PASS，0 errors，仅保留既有 warning。
- Strict Typecheck：PASS。
- `ci.local.iteration`：PASS，5/5 targets 实际执行，无 blocked/not-run/unmapped。
- `ci.delivery.freeze.prepare`：PASS；仅组件接管清单的输入 digest 随共享表达源码更新。

Receipt：
`.runtime/frontend-dev-validation/executions/20261108T012139Z-532938-605217410/receipt.json`

## 未覆盖

- 不修改金额、日期、Kanban、审批、验收 fixture 或行业 Renderer。
- 本次只改变共享状态声明校验顺序，不重跑既有浏览器证据；若影响分析或远端门禁显示
  实际页面输入受影响，再按受影响集合补验。
- 不触碰 PR #834，不部署、不合并。
