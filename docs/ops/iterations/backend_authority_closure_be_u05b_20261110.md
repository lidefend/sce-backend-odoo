# BE-U05B Project Finalize Migration

状态：本地批次验收完成；待 U01-U05 累计独立只读复审。主线集成、部署和浏览器审批旅程未执行。候选位于
`codex/be-u05-page-declaration-authority-20261110`，基线为
BE-U05 partner 切片 `f1b9c5997a298d6a8a160c519831167c644ba644`。

## 目标

项目原生表单已经声明责任矩阵、项目负责人、项目经理、协作者和分组结构。本切片删除
finalize 对非显式项目表单的：

- 节点修剪与字段标签覆盖；
- 组件注册扩展；
- 责任/协作组追加。

页面结构由 P1 原生视图声明和 P0 统一编排消费，finalize 不再成为第二处页面定义者。

## 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.backend.authority_closure.unit` | PASS，7 tests；G05 项目重定义调用已消失 |
| `make verify.frontend.dev.incremental.unit` | PASS，109 tests；finalize 同时路由 partner/project 两个精确目标 |
| `make verify.page.project_finalize.authority.orm` | PASS，1 test；layout/status 前后完全一致 |
| `make verify.page.finalize.authority.orm` | PASS，1 test；声明变化改变 hidden 集合，native-only pass 不执行旧 partner override |
| `make ci.local.iteration` | PASS，affected targets=6；partner 与 project ORM 各 1/1 |

两次 ORM 失败均为测试断言边界错误：第一次要求整个契约对象不变，但 finalize 合法补充了独立的
`workflowContract`；第二次把初始 `widgetStatus` 期望集合漏写了 `partner_id`。测试改为比较
layout/status 不变后重跑通过。产品代码未因测试失败放宽页面规则。

`project.project` 原生视图继续拥有负责人、经理、责任矩阵、协作、标签和分组结构；finalize 的
项目 fallback 修剪、重标、组件注册扩展和职责区追加已全部移除。`execute_button` 执行重验未变。

## 可达性与职责结论

- `_apply_partner_form_surface_governance` 与 `_apply_project_ledger_form_surface_governance` 均未标记
  `native_authority_safe`，目标原生视图权威路径不会执行其结构修改。
- 两者仍保留为明确非原生兼容路径；本批没有宣称删除这些兼容入口。
- 原生路径的 partner 隐藏来自发布态 sparse field policy；临时声明对照使 `country_id` 退出 hidden 集合，
  证明最终结果随声明变化。
- project native-only pass 不重标字段、不隐藏 `user_id`、不追加职责区。

覆盖限制：完整 `core_extension_v2_finalize` tag 中依赖既有项目数据的历史用例在无 demo 一次性库中
没有运行；精确 1/1 结果不冒充整个页面测试集通过。

提交钩子刷新了复杂度预算与拆分队列；差异只反映 finalize 代码缩减，已纳入本批范围。

## 回退

回退本切片提交即可；不改变 schema、ACL、动作执行或部署数据。
