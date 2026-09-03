# G2 审计报告：既有 BOQ 导入能力（只读）

> 阶段：G2（审计既有 BOQ 导入能力）
> 审计基线：main@235a96d9（PR #404 合入点）
> 性质：静态只读审计，未做任何业务写入；证据为仓库内代码路径与行号。
> 范围：`project.boq.import.wizard`、`action_open_boq_import`、CSV/XLS/XLSX 解析、权限与错误语义、数据边界。
> 退出条件对照（计划第 7 节）：权限、格式、动作、失败语义和数据边界有证据 —— 见第 2–6 节，每项均附代码证据。

## 1. 审计对象与规模

| 对象 | 路径 | 规模 |
| --- | --- | --- |
| 导入向导 | `addons/smart_construction_core/wizard/project_boq_import_wizard.py` | 2171 行，TransientModel |
| 项目入口动作 | `addons/smart_construction_core/models/core/project_core.py:1548`（`action_open_boq_import`） | 方法体仅预填 `default_project_id` 后转发向导 action |
| 向导视图 | `views/core/project_boq_import_views.xml` | upload/preview/done 三态按钮 |
| 入口按钮 | `views/core/project_views.xml:124,217` | 项目表单 smart button + 列表按钮 |
| 既有测试 | `scripts/e2e/e2e_boq_import_fixed_data_preflight.py`、`scripts/verify/boq_baseline_browser_acceptance.mjs` | 预检 e2e + 浏览器基线验收 |

## 2. 权限（证据：security CSV + 记录规则 + 按钮组）

**模型 ACL**（`security/ir.model.access.csv:127-131`）：

| 模型 | 组 | 权限 |
| --- | --- | --- |
| project.boq.import.wizard | group_sc_cap_cost_manager | 1,1,1,1 |
| project.boq.import.wizard | group_sc_cap_cost_user | 1,1,1,1 |
| project.boq.import.batch | group_sc_cap_cost_manager | 1,1,1,1 |
| project.boq.import.batch | group_sc_cap_cost_user | 1,1,1,0 |
| project.boq.import.batch | group_sc_cap_project_read | 1,0,0,0 |

**记录规则**（`security/sc_record_rules.xml:2836-2859`）：boq.version / boq.import.batch 按「项目负责人 OR 项目关注者」域限制 cost_read/cost_user；cost_manager 全域（`[(1,'=',1)]`）。

**入口可见性**：两处入口按钮与向导 action `groups_id` 均限定 `group_sc_cap_cost_user` + `group_sc_cap_cost_manager`；cost_read 只读组**无**向导 ACL（导入是写操作，只读角色无法触发——符合最小权限）。

**结论**：权限分层完整（manager 全域 / user 项目范围 / read 只读且不可导入），无越权缺口。

## 3. 格式与解析（证据：wizard 源码）

| 格式 | 解析器 | 缺失依赖时的行为 |
| --- | --- | --- |
| CSV | 内置 `csv`，`_parse_csv_bytes` 逐级尝试 UTF-8 → GBK | 均失败 → `UserError("无法解码导入文件，请确认使用 UTF-8 或 GBK 编码。")` |
| XLSX | `openpyxl`（try-import 可选） | `UserError("服务器缺少 openpyxl…请安装依赖或改用 CSV。")` |
| XLS | `xlrd`（try-import 可选） | `UserError("服务器缺少 xlrd…")` |

- 依赖缺失是**显式中文 UserError 降级**，不是 ImportError 崩溃。
- 模板最低要求：至少含「清单名称」列（`_prepare_col_map`，wizard:1060）。
- 单位别名归一：`UOM_ALIAS_MAP`（㎡/m²/平米/平方米/平方 → m2 等）。
- 解析保留策略：结构标题行、页内小计、合计、费用计算明细**完整保留**（preview_* 计数字段区分 item/summary/heading/calculation_detail/skipped）。

## 4. 动作语义（证据：action_preflight / action_import）

**两段式（预检 → 导入），关键安全设计**：

1. `action_preflight`（wizard:141）：`with_context(boq_import_preflight=True)` 解析**无业务写入**，并把 `sha256(文件字节流)` 冻结到 `preview_digest`。
2. `action_import`（wizard:241）五重前置校验，任一失败即拒绝：
   - 文件存在；state=preview 且有 digest；**digest 重算一致**（防止预检后换文件）；
   - **P0_BOQ_FROZEN 守卫**：项目进入结算/支付关键节点（`is_boq_frozen()`）时拒绝导入新版本；
   - 版本号在「同项目 × 同清单来源」下唯一。
3. 写入：`project.boq.version`（独立草稿版本，**不覆盖已发布清单**）+ `project.boq.import.batch`（含结构化预检快照，schema `sc.boq.import.preview.v1`：行数/项数/汇总/警告/金额/诊断）+ `project.boq.line` 分批（BATCH_CREATE_SIZE=500）。
4. 行级 `boq_category` 分组决定层级导入策略（_create_rows 内 grouped）。

**结论**：动作语义成熟——预检无副作用、digest 绑定、冻结守卫、版本唯一性、批写入。G3 只读投影可直接消费 batch 的 `preview_payload` 结构化快照。

## 5. 失败语义（证据：全部 UserError 文案）

- 全部失败为**中文可操作提示**：「请先上传导入文件」「请先执行预检，再确认导入」「文件已发生变化，请重新执行预检」「同一项目和清单来源下已存在该版本号，请使用新的版本号」「未找到可导入的清单数据：…（含原因说明）」。
- 业务守卫走 `state_guard.raise_guard`（`models/support/state_guard.py`）：结构化前缀 `[SC_GUARD:P0_BOQ_FROZEN]` + 对象 + 拒绝动作 + 原因列表 + 建议列表——**前端可解析的稳定错误协议**。
- 记录日志：`_logger` 存在但仅用于诊断；无静默吞错路径（所有 raise 路径均带用户可见文案）。

## 6. 数据边界（证据：写入模型清单）

| 写入模型 | 边界评估 |
| --- | --- |
| project.boq.version | 草稿版本独立，不覆盖已发布；记录规则限项目范围 ✅ |
| project.boq.import.batch | 导入批次 + 预检快照；cost_user 可写、项目范围 ✅ |
| project.boq.line | 500 行分批；version_id/import_batch_id 关联 ✅ |
| **uom.uom（计量单位）** | ⚠️ 单位不存在时**自动创建**（`_default_uom_category` 用 `sudo()` 兜底取类别）——uom.uom 是**跨项目/跨公司共享主数据**，导入文件可静默扩充全局单位表 |

**风险登记（G3 输入）**：

1. **R-G2-01（中）**：uom 自动创建无白名单约束——恶意/低质量导入文件可膨胀全局单位表。缓解现状：自动创建的单位会写入导入日志（wizard:357-358「自动创建计量单位」清单，事后可审计）；G3 闭环建议升级为：单位映射白名单 + 未知单位进预检警告（而非静默创建）。
2. **R-G2-02（低）**：`_default_uom_category` 的 `sudo().search([], limit=1)` 在标准类别缺失时取任意类别——确定性不足，建议固定 xmlid。
3. **R-G2-03（信息）**：P0_BOQ_FROZEN 守卫错误必须原样透传到 G3 前端（结构化 `[SC_GUARD:*]` 前缀可解析出原因/建议），不得被前端降级为笼统「导入失败」。
4. **R-G2-04（信息）**：digest 绑定设计（预检→导入文件一致性）应在 G3 前端流程中原样保留（上传→预检→确认的文件不可中途替换）。

## 7. 结论与 G3 建议

既有 BOQ 导入能力的权限、格式、动作、失败语义、数据边界**全部有代码级证据**，G2 退出条件达成。能力成熟度高于计划假设（计划按「最小可用」预估，实际已有预检快照/冻结守卫/版本治理）。

**G3（BOQ 最小真实闭环）设计输入**：
- 后端事实源：`project.boq.import.batch.preview_payload`（schema sc.boq.import.preview.v1）+ boq.version 草稿链
- 前端只读投影：消费 preview_payload 的结构化字段渲染预检结果（行数/项数/警告/金额），无需重新解析文件
- 写路径：沿用两段式 + digest 绑定 + [SC_GUARD:*] 错误透传
- 须先处置 R-G2-01（单位白名单）再开写路径
