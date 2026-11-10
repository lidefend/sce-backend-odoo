# BE-U05C Review Remediation

状态：本地复审整改完成。基线为独立复审 REQUEST_CHANGES 的 `8a35c7718…`。

本批关闭两项 S1：

- 未知/遗留能力行不再默认成为业务能力；
- 页面声明对照进入真实 `UiContractV2Handler` 最终契约。

## 验证

| 检查 | 结果 |
| --- | --- |
| `make verify.capability.identity_boundary.unit` | PASS，6 tests |
| `make verify.page.finalize.authority.orm` | PASS，1 test；最终 `UiContractV2Handler` 契约随 action/view 声明变化 |
| `make verify.page.project_finalize.authority.orm` | PASS，1 test |
| `make verify.backend.authority_closure.unit` | PASS，7 tests |
| `make verify.frontend.dev.incremental.unit` | PASS，109 tests |
| `make ci.local.iteration` | PASS，affected targets=4；两个页面 ORM 各 1/1 |

能力身份整改：

- `construction.menu.*`、`catalog.menu.*` 无论是否缺字段，强制归为入口别名；
- 未知且无显式身份的行归为 `unclassified_capability`；
- 只有显式 `identity_kind=business_capability` 且布尔值为真才成为业务能力；
- 运行 payload 是否存在不再使未知键自动升级为业务能力。

页面整改：

- partner 临时 action/view 声明隐藏原生确实渲染的 `category_id`；
- 最终契约中该字段消失；
- 撤销临时声明后最终契约恢复该字段；
- 证明声明通过真实 `UiContractV2Handler` 决定最终结果，而非仅改变中间 resolver 集合。

提交钩子刷新了复杂度预算，已纳入本批生成证据范围。

## 回退

回退 remediation 提交即可。
