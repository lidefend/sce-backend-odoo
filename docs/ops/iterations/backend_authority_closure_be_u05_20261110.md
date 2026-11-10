# BE-U05 Page Declaration Authority

状态：partner 切片本地验收完成；项目 fallback 尚未迁移，G05 仍为部分收口。候选分支
`codex/be-u05-page-declaration-authority-20261110`，基线为
BE-U04 候选 `11986acb3d3b4ee677149f05c28d6dbe63c245a5`。

## 目标

先把已确认的 `res.partner` 页面差异从 finalize 后置代码迁入发布态页面声明：

- `country_id`、`user_id` 由 `ui.business.config.contract` 的 sparse field policy 隐藏；
- `smart_core_finalize_unified_page_contract_v2()` 不再识别并修改这两个字段；
- 项目表单 fallback 的修剪、标签和职责区追加仍留待同卡后续，不把本切片称为 finalize 完全退役。

## 层与范围

- `Formal Product Layer`：P1 行业标准，支撑 P0 页面编排。
- `Layer Target`：partner 表单声明与 finalize 边界。
- `Module`：`smart_construction_core`。

## 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.backend.authority_closure.unit` | PASS，7 tests；finalize 禁止伙伴字段隐藏 token，声明记录存在 |
| `make verify.frontend.dev.incremental.unit` | PASS，109 tests；U05 路径有专属目标 |
| `make verify.page.finalize.authority.orm` | PASS，1 test；声明隐藏字段且 finalize 对 partner form 返回 None |
| `make ci.local.iteration` | PASS，affected targets=5；一次性 `sc_test` 精确用例重验 1/1 |

首次 ORM 在数据加载阶段失败：contract JSON 使用 JSON 小写 `false`，而 Odoo `eval` 要求 Python
`False`，属于页面声明语法错误。第二次完整 tag 中新增用例通过，但同 tag 的其他历史用例依赖项目数据，
在无 demo 的一次性库中不具备独立运行前提；入口改为精确选择新增测试方法后 1/1 通过。原始日志保留。

覆盖限制：本次只迁移 `res.partner` 的 `country_id`/`user_id` 稀疏隐藏。项目表单 fallback 的
字段修剪、标签修改和职责区追加仍在 finalize 中，G05 不得标为完全关闭；`execute_button` 执行重验
未改动。

提交钩子刷新了复杂度预算与拆分队列；差异只反映 finalize 代码缩减和入口规模，已纳入本批范围。

## 回退

回退本切片提交即可；contract XML 通过模块升级重放，不改 schema 或部署数据。
