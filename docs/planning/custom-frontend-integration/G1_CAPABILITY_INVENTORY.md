# G1 能力现状/差距清单（CAPABILITY INVENTORY）

> 阶段：G1（建立现状/差距清单与环境无关验收）
> 基线 SHA：`b0cfa8ec41ab6b349b1d1d545fd03f59cc4c2a15`（G1 分支切点，origin/main 可追溯）
> 依据：本清单基于 main 基线真实代码扫描产出，不是计划文档照抄；计划文档见同目录 `README.md`。
> 机器可校验证据：`G1_BASELINE_EVIDENCE.json`（由 `scripts/verify/g1_acceptance_baseline_guard.py` 拥有，禁止人工编辑）。

## 1. 轨道定义（回顾）

- **轨道 A（既有能力接入/收敛）**：main 上已有实现或部分实现，目标是收敛到统一契约/设计系统，不引入新的大依赖。
- **轨道 B（新平台能力）**：main 上无实现，须先过 G5 ADR（依赖体积、首屏预算、安全边界评审）才能进入 G6 实现。

## 2. 十专题现状与差距

| 专题 | 轨道 | main 上的现状证据 | 差距（对照计划） | 目标阶段 |
| --- | --- | --- | --- | --- |
| design-system | A | `frontend/packages/design-tokens`（base/semantic.light/semantic.dark/pattern/component 五层 token + web/mini/mobile 三平台 + `token-authority.json` 单点真相源）；`frontend/packages/ui`；web 应用内 67 个 `Sc*` 设计系统组件 + `tdesignPrimitiveBridge.ts`/`primitiveAdapter.ts` 桥接层 | Token allowlist 守卫与硬编码颜色守卫的覆盖面待审计（README 9.1/9.2）；原型目录 44 个组件按契约逐文件准入迁移尚未开始 | G1 后持续收敛 |
| theme | A | design-tokens 亮/暗双语义层 + `dist/web/tokens.{light,dark}.css`；web 端 `styles/theme.ts` + `styles/tokens/*`（含 `tdesign-bridge.css`） | 品牌资产来源审计、主题切换无闪烁验收未建立 | G4 |
| boq | A | `addons/smart_construction_core/wizard/project_boq_import_wizard.py`、`project_task_from_boq_wizard.py`、`models/support/project_extend_boq.py`（既有导入向导与 BOQ 模型）；前端无专用 tree-grid | 权限/格式/动作/失败语义/数据边界只读审计未做；只读投影与 10k 行预算未建立 | G2→G3 |
| excel | B | 无。web 生产依赖仅 `@sc/ui/pinia/vue/vue-router` 四项，无 xlsx/SheetJS | 全部待 ADR（文件类型/大小、公式注入、权限裁剪、幂等、错误回执） | G5 |
| gantt | B | 无。无任何 gantt 依赖 | 全部待 ADR（依赖环、日历、冲突回滚、500 任务性能） | G5 |
| pdf | A+B | 后端存量：`views/projection/*_report_views.xml`、`product_report_contracts.xml` 等报表视图（Odoo QWeb 报表通道） | 前端 PDF job UI（模板沙箱、字体、分页、签章/水印权威、下载权限）无实现，待 ADR | G5 |
| editor | B | 仅一个只读 Html 字段：`models/support/mail_notification_product.py`（`sc_body` related readonly） | 富文本编辑器全量缺失：XSS、协议净化、粘贴、附件 ACL、版本冲突验收均未建立 | G5 |
| echarts/chart | B | 无。无 echarts 依赖 | 数据口径快照、空/错/慢、resize、打印、内存释放验收均未建立，待 ADR | G5 |
| mobile | A | `frontend/apps/mobile-harmony-shell`（ArkTS/HarmonyOS 工程：AppScope/entry/hvigor）；lite 契约 harmony h5 pilot 守卫族（compile/ui_renderer/runtime_mount） | `mobile-harmony-shell` 是计划定稿时未知的存量（G0 附录已标记）：职责、数据来源、与统一页面契约的关系须先审计，才谈 G4 收口 | G4 前置审计 |
| menu-governance | A | `docs/engineering_convergence/menu_governance/`（M0 基线→M4 收口全链文档 + `menu_capability_inventory.{json,md,schema.json}` + 治理范围 json） | 已闭环；后续仅随专题接入做增量治理 | 持续 |

### 2.1 轨道汇总

- **轨道 A 共 6 项**：design-system、theme、boq、pdf（后端通道存量）、mobile、menu-governance。
- **轨道 B 共 5 项**：echarts/chart、excel、gantt、editor、pdf（前端 job UI 部分）。pdf 跨双轨：后端报表通道是存量（A），前端 job UI 是新增（B）。
- **结论**：轨道 B 五项在 main 上零实现，G5 ADR 前不得引入任何对应依赖（当前 web 生产依赖 4 项，前提仍然成立）。

## 3. 验收资产盘点（环境无关验收框架现状）

| 资产 | 路径 | 状态 | 说明 |
| --- | --- | --- | --- |
| 四环境配置 | `config/frontend/acceptance_environments_v1.json` | ✅ 存量，指纹已冻结 | local/test/daily/production 四 profile；地址发现走环境变量（`ACCEPTANCE_BASE_URL` 等），无硬编码服务器/端口/账号；写入策略分级（local 允许夹具写、daily 默认只读、production 仅安全冒烟） |
| 验收工具矩阵 | `config/frontend/acceptance_tool_matrix_v1.json` | ✅ 存量，指纹已冻结 | 9 类工具 × profile × 操作类型映射 |
| 证据契约 Schema | `config/frontend/acceptance_evidence_contract_v1.schema.json` | ✅ 本次新增 | 冻结 README 第 12 节浏览器证据 11 项必填字段 + 跨环境复用禁令 |
| G1 基线证据 | `docs/planning/custom-frontend-integration/G1_BASELINE_EVIDENCE.json` | ✅ 本次新增 | 绑定基线 SHA + 三资产 sha256 指纹 + 工具链版本；守卫重算指纹即验证可复现性 |
| 基线守卫 | `scripts/verify/g1_acceptance_baseline_guard.py` | ✅ 本次新增 | make 目标 `verify.g1.acceptance.baseline`；校验结构/SHA 可追溯/指纹重算/四环境齐全/契约字段覆盖 |
| 既有环境守卫 | `verify.frontend.acceptance.environment.guard` 等 | ✅ 存量 | 环境 source guard、runtime profile、daily env guard（针对既有验收场景，与本框架互补） |

## 4. G1 差距结论（G2+ 输入）

1. **四环境配置化：已达成。** 存量 `acceptance_environments_v1.json` 与计划第 12 节矩阵逐项对齐（地址发现/认证/数据夹具/写入策略/SHA 证明字段齐备），本轮补齐证据契约后整套资产纳入指纹冻结。
2. **基线证据可复现：已达成。** `g1_acceptance_baseline_guard.py` 重算资产 sha256 与基线 SHA 祖先校验，本地与 CI 同一套逻辑；任何环境配置变更都会导致指纹漂移被拦截，必须显式 `--write` 重冻结并随 PR 评审。
3. **进入 G2 的前置条件**：本清单 + 基线证据合入 main；G2 对 `project.boq.import.wizard` / `action_open_boq_import` 的只读审计以本清单第 2 节 boq 行的现状证据为起点。
4. **风险提示**：`mobile-harmony-shell` 审计必须先于 G4 任何 Mobile 收口动作（G0 附录遗留项）。

## 5. 验收命令

```bash
make verify.g1.acceptance.baseline            # 结构+指纹+四环境+SHA 可追溯校验
python3 scripts/verify/g1_acceptance_baseline_guard.py --write   # 仅环境配置变更后重冻结
```

守卫已接入 `ci.local.quick`，经 `make pr.merge` 合流门禁强制执行。
