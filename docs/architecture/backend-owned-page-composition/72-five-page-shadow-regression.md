# 72 · Five-Page Shadow Regression（4G-02C）

## 说明

Action 590 使用真实捕获样例；其余四页按 4E/4F 已记录的结构事实重建，未伪造
任何 VERIFIED 证据。这是影子验证，不改变任何页面运行行为。

## 结果矩阵

| 页面 | overall | PC-001 | PC-002 | PC-003 | PC-004 | PC-005 | PC-006 | PC-007 | PC-008 | PC-009 | PC-010 | PC-011 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| project.project 590/1776 | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PASS | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| project.project 652/944 | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PASS | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| payment.request 649/1773 | NOT_VERIFIED | PASS | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PASS | PASS | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| sc.payment.execution 709/1658 | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PASS | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |
| sc.receipt.income 708/1655 | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | PASS | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED | NOT_VERIFIED |

## 分析

- 无页面误判为 PASS / Formal。
- 无页面因 Guard 规则产生虚假 FAIL。
- payment.request 的 PC-001 / PC-005 PASS 正确反映“业务组合与布局已声明、且
  无重复主入口”，但 PC-002～PC-004 仍 NOT_VERIFIED（ownership 缺失），因此
  整体 NOT_VERIFIED，不具备迁移条件。
- sc.payment.execution slots=0：PC-001 NOT_VERIFIED，containerTree 未替代 slots。
- sc.receipt.income 无契约：全部结构规则 NOT_VERIFIED，仅 PC-006 PASS。

## 结论

Guard 能区分“结构已声明”与“归属/权限/兼容/历史身份未验证”，没有为获得全绿而
降低标准。
