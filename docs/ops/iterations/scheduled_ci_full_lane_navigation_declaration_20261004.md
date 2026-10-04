# 定时 CI full 车道：finance 导航声明补齐（P1 审计清单对齐）

## 1. 结论

`frontend_release_gate` 的 **full** 车道（schedule / workflow_dispatch 才启用）自 2026-09-19 起持续红灯。
上一批 `CI-SCHEDULED-FULL-LANE-RECOVERY-B`（PR #559，squash `4f55eed2`）修好了三处守卫缺陷，
但在合并后的 full 车道复跑（run `37174497207`）中证明：守卫现已全绿，**真正的剩余阻断**是浏览器
页面身份审计 `verify.frontend.page_identity.browser` 的导航对账失败——

```
[frontend-surface-audit] { "pass": false, "surfaces": 28, "failed": 0, "failures": [] }
frontend-release-audit report.json → blocking_failures:
  NAVIGATION_NOT_AUTHORITATIVE_TOTAL
  EVIDENCE_INVALID:.../frontend-delivery-hardening/report.json (被前一条短路，未生成)
  EVIDENCE_INVALID:.../frontend-delivery-hardening/accessibility.json (同上)
```

即：**没有任何一个页面失败**（`failed: 0`），失败来自“声明面 ≠ 运行时面”。

## 2. 根因（证据绑定）

`frontend_product_maturity_audit.mjs` 用 `compareNavigation()` 对账：
期望面取 `config/frontend/authoritative_navigation.json` 的**每角色 `browser_leaf_keys`**，
实际面取该角色在验收 fixture 里**真实可见**的菜单叶子。

运行时报告（`frontend-page-identity/navigation-report.json`）：

| 角色 | expected | actual | 结论 |
| --- | --- | --- | --- |
| finance | 13 | **15** | FAIL，多出 2 个未声明叶子 |
| project_a_member | 4 | 4 | PASS |
| pm | 7 | 7 | PASS |
| owner | 2 | 2 | PASS |
| 合计 | 26 | **28** | FAIL |

多出的两个叶子：

- `smart_construction_core.menu_sc_product_current_account_v1|smart_construction_core.action_sc_product_current_account_v1|sc.current.account.workspace`
- `smart_construction_core.menu_sc_product_company_project_refund_v1|smart_construction_core.action_sc_product_company_project_refund_v1|sc.company.project.refund.workspace`

两者都是**后端已正式发布**的 finance 主菜单：

- `addons/smart_construction_core/core_extension_policy_maps.py` 中
  `ROLE_SURFACE_OVERRIDES["finance"]["primary_menu_xmlids"]` 明确包含这两条；PR #497（`cefeff1f`）的
  提交说明写明这是「按入口自身声明的持组对齐角色导航面」，属**既有授权路径**，未改 ACL、未新增机制。
- 二者同时出现在同文件的 finance `leaf_keys`（45 条）中；`frontend_release_navigation_policy_guard`
  要求 `leaf_keys == 角色发布面`，故 `leaf_keys` 侧是权威且已对齐。
- 与定时车道由绿转红的时点完全一致：09-18 绿（head `26d254ad`）→ 09-19 红（head `4b4a47fe`），
  中间正是 PR #497（`cefeff1f`）。随后 09-23 的基线对齐批次（`bc98f5e6`）只把 finance `leaf_keys`
  从 43 补到 45，**遗漏了 `browser_leaf_keys`**（仍为 13），从此 full 车道的浏览器对账持续红灯。

既有先例同向：`docs/ops/iterations/frontend_gate_baseline_alignment_20260922.md` 明确
「后端发布面本身是权威，前端清单才是滞后项」，并以补齐前端清单收口同类红灯。

## 3. 变更（P1 审计清单，单点）

`config/frontend/authoritative_navigation.json`：finance 角色的**审计视角**登记补齐。

- `browser_expected_count`：13 → **15**
- `browser_leaf_keys`：按字典序插入上述两条（保持有序）
- 其余角色、`leaf_keys`、`source`、后端 `ROLE_SURFACE_OVERRIDES` **均不改**

`Formal Product Layer`：P1（施工行业标准产品的角色发布面声明）；`Layer Target`：前端权威导航审计清单。
`Standard vs User-Specific`：平台/行业标准的角色发布面登记，不含客户偏好。
`Why Here`：审计对账的权威就是这份清单。`Why Not Elsewhere`：后端发布面是权威、不得为迁就前端而改；
运行时可见性由菜单持组与 ACL 决定，不得为对齐数字而削减入口。
`Blast Radius`：仅影响 `frontend_release_gate` full 车道的浏览器对账期望值与
`verify.frontend.release_navigation_policy.guard` 的自洽检查；不改前端渲染、契约 schema、字段权限、
状态动作或业务取值。`Rollback`：`git revert`（纯声明，可逆，无数据/模式迁移）。

## 4. 未放宽的证明

- 期望面**只增不减**：没有任何已声明叶子被删除；15 条中 13 条原样保留。
- 对账仍是**精确相等**（`frontend_navigation_audit.mjs` 要求
  `expected_count == actual_count == matched_count` 且 `missing/unexpected/duplicate/invalid` 全空），
  新增的两条也必须真实可导航并通过身份断言，否则依旧 FAIL。
- `frontend_release_navigation_policy_guard.py` 的 `browser_leaf_keys ⊆ leaf_keys` 子集约束未改，
  且新增项来自 `ROLE_SURFACE_OVERRIDES["finance"]["primary_menu_xmlids"]`。
- `frontend_release_audit.py` 仍以 `browser_expected_count` 强校验报告中的
  `total.expected_count == total.actual_count == total.matched_count`。

## 5. 独立车道：`backend_test_suite`（单列，不泛化）

schedule run `37158252861`（10-03）等在 `Build images and start database` 失败：

```
failed to create network sc-suite-<id>_default:
  Error response from daemon: all predefined address pools have been fully subnetted
```

测试**根本没有执行**（`Run backend test suite per module` 被 skip）。宿主即 self-hosted runner
（`wsl-sce-runner-01`，`/home/lidefend/actions-runner`）。实测两段默认地址池均已占满：
`172.17.0.0/12` 的 14 个 /16 槽位与 `192.168.0.0/16` 的 16 个 /20 槽位。

按既有受管原则**不使用** `docker system/volume/network prune`（仓库测试明确禁止），
仅删除 **零挂载**（`Containers` 数为 0）的孤儿网络 11 个，未触碰任何有挂载的网络、容器、卷：

`sc-p204-33ddd6a-attempt2-net`、`sc-p204-33ddd6a-clean-net`、`sc-production-blocker-matrix_default`、
`sc-production-candidate_default`、`sc-tenant-rc-deploy01ar_default`、
`sc-core035-s07a-20260727035410-acab0f53_default`、`sc-field-arch-p003r_default`、
`sc-backend-odoo_default`、`sc-p204-075-init-net`、`sc-p204-33ddd6a-upgrade-net`、
`sc-locked-p002r-runtimeclosure83_default`（日志 `/tmp/runner_net_reclaim_20261004T033756Z.log`）。

复跑证据：单模块 `sc_norm_engine` 派发 `37174639058` → `Build images and start database` 与
`Run backend test suite per module` 均 **success**。完整车道 `37174945333` 结果见 §7。

历史留痕（10-01）另有 `smart_construction_core` 的长期真实红（`25 failed, 35 error(s) of 471 tests`），
本轮不据此宣称环境全局通过。

## 6. 定向验证（本批，L1/L2）

（结果随本轮执行同步填写。）

## 7. 远端证据

（合并与 full 车道复跑结果随本轮执行同步填写。）
