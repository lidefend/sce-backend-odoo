# 前端交付 readiness v1

## 当前结论

首批交付范围冻结为 70 个权威导航叶节点：finance 42、project member 9、PM 14、owner 5。70/70 在 1440×900 可达且页面身份通过。该结论只适用于 `sc_frontend_acceptance` 的公司 A/B、Project A 和冻结角色范围，不扩张为全业务或生产规模承诺。

**证据缺口（2026-09-28 核对）**：本轮沿引用回查归档，无法支持「J02–J11 已分别覆盖公司/角色隔离、权限拒绝、资金关系链、合法操作、My Work、表单审批、错误恢复、390px 键盘路径和异步乱序」这一整体结论。`artifacts/frontend-page-identity/journeys.json` 中 J01–J08 对每个角色均为 `NOT_ASSESSED`（备注「surface巡检不执行写操作，需专门旅程脚本复核」）；`artifacts/frontend-delivery-hardening/report.json` 只记录 `J09`／`J10` 为 PASS，无 J02–J08／J11 结论；`artifacts/frontend-page-identity/accessibility-report.json` 为 `status=N/A`。待补验的最小范围见文末「FE-B06 交付证据」的缺口条目。

## 可交付能力

- finance：My Work、合同—结算—付款详情、付款申请新建/保存/提交、公司 A/B 隔离和结果回看有真实证据。
- project member：仅 Project A 范围、敏感导航排除、敏感 action/menu/record 明确拒绝且无标题/金额泄露。
- PM/owner：冻结的 14/5 个合法叶节点保持可达；PM 以正式权限验证 Project A—合同—结算详情，owner 不扩张职责。
- executive：仅作为正式付款审批旅程角色，提交后审批和待办迁移有真实证据，不计入 70 个导航分母。

## 不宜直接承诺的能力

- My Work 扩展到付款申请以外的对象。
- finance 获得 Project A 主表 action 权限，或 project member 获得财务事实。
- 没有可靠审计参与证据时展示“最近完成”。
- 生产数据规模、弱网和非验收硬件上的绝对性能保证。

## 首批用户前置条件

1. 使用冻结 fixture 和正式角色运行 J02–J11，不跳过权限与错误检查。
2. 以 `artifacts/frontend-delivery-hardening/` 中的性能、无障碍、响应式和错误恢复报告作为试点判定输入。
3. 生产发布前另行验证真实部署资源、数据库规模、备份恢复和监控，不把本地验收数值外推为生产 SLA。

## FE-B06 交付证据

- 代表表面：**证据缺口**。`artifacts/frontend-delivery-hardening/responsive.json`（候选 `b214aba6`）的 `viewports`／`pages` 均为空数组，`horizontal_overflow=0` 来自空样本，不能支撑「17 表面 × 68 组合」。需按代表表面重跑响应式采集后才能声明。
- 无障碍：**证据缺口**。`artifacts/frontend-delivery-hardening/accessibility.json`（候选 `b214aba6`）为 `result=NOT_RUN`、`scans=[]`；`violations/critical/serious` 为 0 属未扫描的默认值，不能支撑「扫描 18 个桌面表面、阻断为 0」。J10 键盘路径另见 `report.json`（该文件仅记录 J09／J10 为 PASS）。
- 恢复：真实记录读取分别注入网络断开、409 和 401；Retry、获取最新数据和安全登录回退通过，登录 URL 不携带旧敏感详情 redirect。
- 异步隔离：请求 epoch 阻止迟到的公司、角色和详情响应覆盖当前页面；J11 最终只显示最后选择的公司 B，logout 后 project member 不出现 finance 数据。
- 性能：**证据缺口，原引用不成立**。本条此前引用的登录 1382/1612ms、My Work 942/947ms、付款详情 1970/2051ms、结算详情 1965/1989ms、付款执行 1463/1466ms、表单 1411/1418ms、公司切换 849/1516ms，在 `artifacts/frontend-delivery-hardening/` 任何归档中都找不到来源。被引用的 `performance.json`（候选 `b214aba6`，2026-09-10T16:36:54Z）实际为 `result=FAIL`、`scenarios={}`（空）；同候选的 `performance-probe.json` 虽为 `result=PASS`，但其 7 个场景中位数为 login 2632、my_work 279、payment_detail 263、settlement_detail 324、execution_detail 311、form_open 1445、company_switch 2107ms，**与本条引用的数字无一致项**；`report.json` 同为 `pass=false`。因此「逐指标门禁通过」与上述中位数均无归档支撑。需在当前候选重跑性能采集并归档后才能声明；不得把候选 `b214aba6` 的 FAIL／空结果写成当前候选失败，也不得把旧数字沿用为当前候选通过。

**待补验的最小范围**（证据缺口，未通过即不得声明）：当前候选上的性能采集（7 场景中位数＋最慢值，与预算文件比对）、无障碍扫描（`scans` 非空）、响应式采集（`viewports`／`pages` 非空）、以及 J02–J08／J11 旅程的专门脚本结果。这些不受 WEB-FIX-01／WEB-FIX-02 影响的部分可按输入变化复用旧证据，但引用范围必须与旧候选一致。
