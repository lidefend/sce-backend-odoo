# 表单表达阶段交付收口包

日期：2026-09-10
状态：`READY_FOR_DRAFT_PR_AUTHORIZATION`

## 1. 阶段结论

表单表达开发阶段已完成，并通过源码与留存证据独立复核，可以进入 draft PR。该结论只覆盖通用前端表单结构、响应式容器、章节导航、字段对齐、共享页面职责与全局组件配置；不代表全系统业务验收、merge-ready 或 release-ready。

本次交付整理没有重新启动浏览器或重跑产品测试，也没有修改产品代码。官方图标资源采用留在后续独立批次。

## 2. PR 身份与完整差异

| 身份 | SHA | 说明 |
|---|---|---|
| 权威远端 | `origin=https://github.com/lidefend/sce-backend-odoo.git` | `git fetch --prune origin` 后核对 |
| 目标主线 | `origin/main` = `3c3c7bdef2dac3dfdfa06488c7e731ce1e565ce9` | 与本地 `main` 一致 |
| 共同基线 | `3c3c7bdef2dac3dfdfa06488c7e731ce1e565ce9` | `merge-base(origin/main, HEAD)` |
| 独立复核产品/证据候选 | `c442f731adb6cd23e3adc77811c1c895f137a5fe` | 浏览器补证与产品实现的最后候选 |
| 交付整理前 HEAD | `fc7433b6284d539d9486a551ca635771f00071af` | 相对候选仅目标记录和报告 |
| PR exact head | 创建前重新读取 | 不在草稿中预填尚未产生的提交 SHA |

交付整理前完整范围为 73 commits、72 paths、3207 insertions、571 deletions。本交付提交新增本文件和 PR 草稿；纳入后完整范围为 74 commits、74 paths，已只读复核。push/create 前仍须重新核对，若不一致则停止发布。

### 提交拓扑

| 范围 | 提交数 | 净路径数 | 主要内容 |
|---|---:|---:|---|
| `3c3c7bde…f1943462` | 8 | 21 | 共享表单结构、语义章节与首轮证据 |
| `f1943462…7be995af` | 16 | 23 | 视觉层级、首屏效率与章节导航 |
| `7be995af…2d587000` | 9 | 12 | 响应式容器、控件/弹层边界 |
| `2d587000…464c155d` | 14 | 22 | 导航名称、稳定目标与内容一致性 |
| `464c155d…fe22402e` | 18 | 17 | 字段外框、跨组列线和只读行基线 |
| `fe22402e…c442f731` | 7 | 36 | 根级官方能力、页头/正文职责、明细/协作层次及补证 |
| `c442f731…fc7433b6` | 1 | 2 | 独立复核前的目标记录和阶段报告 |

### 路径分类

| 类别 | 路径数 | 内容与审查重点 |
|---|---:|---|
| 产品前端 | 36 | `frontend/apps/web/src/**` 与 `frontend/packages/ui/src/primitives.ts`；审查结构、响应式、导航、字段几何、根 Provider 与生命周期 |
| 验证工具 | 18 | `frontend/apps/web/scripts/**`、`scripts/audit/**`、`scripts/verify/**`、`make/frontend.mk`；审查断言非零、定位器作用域和公开组件边界 |
| 生成清单 | 5 | `docs/frontend_productization/rendering-detail/*.json`；审查输入摘要与零缺口条件 |
| 治理文档 | 13（整理前）/15（交付后） | `.agent/goals/**`、阶段报告、上下文日志和本交付包/PR 草稿 |
| 未分类 | 0 | 所有净路径均已归类 |

全差异没有 `addons/`、`contracts/`、数据库/fixture、acceptance 环境恢复、Compose/profile、发布脚本或图标资源。没有 contract/schema、权限、业务动作、金额口径、隐藏章节或业务数据改动。

## 3. 产品交付范围

- 统一查看态与录入态骨架：身份/状态/操作归页头，正文、关系明细、辅助信息和协作记录形成稳定层次。
- 材料入库明细前置且保留单据附件与协作附件的不同归属；收入合同桌面明细支持横向比较。
- 修复 320/390 下多层表单、字段组、真实控件和章节导航的内部超宽；只允许明细表格在声明区域横向浏览。
- 导航绑定实际可见章节的稳定身份，关系字段和录入人不再冒充“关系明细”或“历史审计”；故意隐藏的章节保持隐藏。
- 文本、关系、日期、金额和多行控件共享字段槽位与跨组列线；查看态与录入态行基线一致。
- 根级接入 TDesign 1.20.5 公开 ConfigProvider；主题/减少动画监听拥有明确的启动、卸载、重新挂载与 HMR 生命周期。
- 页头内部布局归共享组件，frame、pattern、正文、明细和协作区的背景、边界、间距责任分离；没有继续通过页面深层选择器修补共享组件内部。

## 4. 产品候选与补证候选不能合并计数

| 证据组 | 候选 | 覆盖 | 正确表述 |
|---|---|---|---|
| 联合页面矩阵 | `07758bd72c11e41157b3125b4d314ba7874c606b` | `artifacts/playwright/global-component-expression-final-pass-light-1440-390-07758bd7/summary.json` 与 dark 1088/320 对应摘要；9 类页面、桌面/移动共 36 个样本 | 原产品/表达矩阵通过；不是在 `c442f731` 上重跑 |
| 全局能力与诊断补证 | `c442f731adb6cd23e3adc77811c1c895f137a5fe` | system 1088/320；登录/嵌入主题、材料关系数据前提、材料集合查询、合同层级查询共 8 个样本 | 补证范围通过；不是完整 36 页矩阵 |

`07758bd7…c442f731` 共 3 commits、15 paths：4 个产品运行时路径、5 个验证路径、3 个生成清单和3个治理文档。产品变化仅是应用根主题生命周期归口及 TDesign 动画普通态显式恢复；原 36 样本对页面结构、字段几何和四视口表达仍有效，新增 8 样本专门覆盖被该变化影响的登录/嵌入主题和三项诊断。不得写成“最终候选 44 个样本全部重跑”。

## 5. 验证与独立复核

| 结论 | 证据 | 状态 |
|---|---|---|
| 字段对齐基线 | 原 24 个控件、跨组 spread 0px、付款只读行基线 | PASS |
| 官方组件与生成清单 | Frontend Quick、严格类型、production build、官方设计 inventory | PASS；内部 selector、未知 token、literal、orphan 均为 0 |
| 真实 Provider 动态传播 | 31 项组件测试；普通/异步/Teleport、局部覆盖、普通→减少→普通 | PASS |
| 生命周期 | 路由不重复注册；卸载、重挂载及 HMR dispose | PASS |
| 原页面矩阵 | `artifacts/playwright/global-component-expression-final-pass-light-1440-390-07758bd7/summary.json`、`artifacts/playwright/global-component-expression-final-pass-dark-1088-320-07758bd7/summary.json` | 36 samples PASS；mutation/errors/failures 0 |
| 补证矩阵 | `artifacts/playwright/global-capability-exit-system-1088-320-c442f731/summary.json` | 8 samples PASS；mutation/errors/failures 0 |
| 独立复核 | 源码与以上留存证据只读复核 | PASS；未重启浏览器、未重跑测试 |

补证候选完整指纹：`93bca159a932f41910a5eb3525a4c781b91a684d85af1362269605a4263571dd`，7366 paths，文件 `artifacts/fingerprints/global_component_capability_exit_candidate_c442f731.json`。

## 6. PR/CI 状态

- `make pr.status`：当前分支没有关联 PR，当前账户没有开放 PR。
- `ci_risk_classifier.py`：`lane=HIGH_RISK`、`frontend_full_required=true`、`frontend_mode=full`、`professional_mode=full`、`backend_changed=true`，原因是 `high_risk_path` 与 `unknown_path_fail_closed`。
- 实际净路径没有后端产品文件；`backend_changed=true` 是分类器的 fail-closed 路由结果，不能改写或手工降级。
- draft PR 创建后应等待 exact-head `public_guard`、`professional_quality_gate`、`frontend_release_gate`、`merge_policy_gate`。当前全部为 `not_run`，不得预填通过。
- `release_candidate_gate` 属于后续发布资格，与本次 draft PR 和合并资格分开。

## 7. 未覆盖、风险与回滚

- 未覆盖：多角色、真实保存/审批、非空权威材料关系数据集选择、acceptance、旧版本升级兼容、PR CI、发布验收。
- 风险：73+ 提交且涉及共享 form renderer、theme root 和验证工具，必须按产品前端、验证工具、生成清单、治理文档四组审查，不能只看最后补证提交。
- 产品整体回滚边界为共同基线 `3c3c7bde…`；各阶段可按表单结构、视觉层级、响应式、导航一致性、字段对齐、全局能力的提交边界逆序回退。
- 本次交付整理只新增/更新 P4 文档，可独立回退，不需要数据库、fixture、容器或契约回滚。

## 8. 下一步

唯一下一步是审阅本地 PR 草稿并单独授权 push/create。获得授权后重新核对 `origin/main`、clean HEAD 与完整差异，只能使用 `make pr.push` 和 `make pr.create`。推送、创建 PR、转 ready、合并和发布仍是不同授权与门禁阶段。
