# G0 基线冻结附录（Custom Frontend Integration）

> 冻结日期：2026-09-03
> 冻结对象：本专题（`feature/custom-frontend-integration-v1`）的架构基线
> 冻结 SHA：`104b631471d9de8a19c0e4088078ee30ef06c1af`（main，PR #402 squash 合入点）
> 文档来源：`~/workspace/2026-08-05-21-27-25/2026-08-05-21-27-25`（2026-08-06 定稿，冲突审计为 0）
> 本文件地位：对 README.md（总控真相源）的 G0 落地附录；与 README 冲突时以 README 为准并立即修订本文件。

## 1. 冻结证据

- 远程 CI 门禁在冻结 SHA 上全绿（PR #402 合入时 12 项 checks pass）：`merge_policy_gate`、`professional_quality_gate`、`professional_authorization`、`frontend_release_gate`、`public_guard`、`public_guard_classify`、`python310_runtime_compatibility`、`release_candidate_gate`、`classify`。
- 本地门禁：`make pr.merge` 已于 PR #402 起硬性前置 `pr.merge.local_quick_gate`（完整 `ci.local.quick` 套件）。该门禁本身即是本专题 G 阶段「进入条件」的机械执行者。
- 冻结时工作树干净，main 与 origin/main 一致。

## 2. 计划定稿（2026-08-06）以来的基线增量

主仓库在计划定稿后合入了大量工作。以下增量直接影响本专题的假设，逐项核对：

| 增量 | 对本专题的影响 |
| --- | --- |
| 契约版本化 R6（8 域 + registry.yaml + lint 双向校验） | 计划第 5 节「统一契约扩展策略」可复用 registry 机制；新 capability key 建议走同一 registry |
| 契约结构指纹锁（contract_structure_fingerprint.json，CI 硬拦截） | 新增 capability 字段必须同步刷指纹（`make refresh.generated_reports`） |
| Native view 语义收口（PR #399/#401：h1/h2/h3 容器保留、many2one 关系控件、auth 词表） | 计划的「不改写 native form/tree 基础结构」约束已有实现载体；BOQ 树表应挂接该 renderer 而非另建 |
| R7 守卫注册表 + 退役机制（registry.yaml，孤儿守卫 review_by 2026-09-30） | 本专题新增守卫须登记；引用旧守卫前先查退役状态 |
| R9 后端套件 CI 化（backend_test_suite 夜间+手动） | G2 BOQ 审计的测试证据可挂靠该套件 |
| R10 测试债处置（后端原生权威 + 稀疏语义标注） | 计划「前端不解析 Odoo XML、不猜业务语义」的路径 B 已是既定实践 |
| pr.merge 本地门禁（PR #402） | 每个 G 阶段 PR 合入前强制过全套本地守卫——计划第 9 节验收门禁的执行保证 |

## 3. 冻结时点的前端基础设施事实（2026-09-03 核验）

- `frontend/packages/`：`design-tokens`、`schema`、`sdk`、`tools`、`ui` —— 与 README 第 4 节目标布局一致，无需新建。
- `frontend/apps/`：`web`、`mobile`、`mobile-harmony-shell` —— **注意**：计划第 6.9 节 Mobile 章节定稿时未知 `mobile-harmony-shell` 的存在；该章「不建第二套移动业务页面」约束在落地时须先审计 harmony shell 的当前职责与数据来源，再决定收口方式。
- `frontend/apps/web` 生产依赖仅 4 项（`@sc/ui`、`pinia`、`vue`、`vue-router`）：echarts/xlsx 均未引入——轨道 B「大依赖须 ADR」前提仍然成立。
- `project.boq.import.wizard` 及相关 action/view 存在于 `addons/smart_construction_core`（G2 审计目标确认在位）。
- capability 关键字（`visualization.chart`、`planning.gantt`、`ui.theme` 等）在仓库内尚无落点——专题未开始实施，与计划状态一致。

## 4. 文档导入说明

- `README.md`、`PLAN_CONFLICT_AUDIT.md` 原样导入，未修改任何内容（证据完整性）。
- 九专题 + 菜单治理正文从 `*/docs/*.md` 平移为 `topics/*.md`；原文内相对链接（如 `menu-governance/docs/TECH_DESIGN.md`）在仓库内不再指向实际路径，阅读时按 `topics/<topic>.md` 对应。
- 原型源码（各 `*-frontend/src`）、`demo/`、`.workbuddy/` **未导入**，仍留在仓外规划目录。它们是候选实现参考，逐文件选择迁移，禁止整目录复制（README 第 4 节）。
- 冲突扫描复核命令在仓库内路径下的等价形式：

```bash
cd docs/planning/custom-frontend-integration
rg -n 'surface_policies\.(theme|primary_color|logo_url)|"features"[[:space:]]*:|"type"[[:space:]]*:[[:space:]]*"chart"|"group_by"[[:space:]]*:|"view_type"[[:space:]]*:[[:space:]]*"gantt"|viewport=mobile' README.md topics/*.md
# 预期无输出（0 冲突证据）
```

## 5. G0 出口判定

- [x] SHA 可追溯：冻结 SHA `104b6314`，构建与门禁状态见第 1 节
- [x] 冲突扫描为 0：2026-08-06 审计结论 + 本附录第 4 节复核命令
- [x] 文档进入主仓库：本目录
- [x] 现状偏差已记录：第 2、3 节（特别是 mobile-harmony-shell 的审计义务）

**G0 完成。下一阶段 G1（现状/差距清单 + 环境无关验收框架）按 README 第 7 节顺序启动。**
