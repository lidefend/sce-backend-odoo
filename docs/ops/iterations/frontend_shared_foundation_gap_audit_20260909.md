# 共享前端基础完整性审查

日期：2026-09-09  
状态：实施中；不是发布验收结论  
基线 HEAD：`d4b66a8eca180bc640bad31285bb80021381251c`

## 1. 范围与所有权

- Formal Product Layer：P0 平台通用前端表达与交互；P4 仅承载验证和报告。
- Layer Target：现有 design-system、canonical form renderer、relation/detail collection runtime、overlay lifecycle、collection/navigation patterns。
- Standard vs User-Specific：跨模型通用机制，不含行业字段语义、客户偏好或管理员配置。
- Why Here：缺口发生在已有契约到真实控件、错误目标、明细列和响应式表达的消费链。
- Why Not Elsewhere：不需要新建后端字段、业务规则或模型特例；契约未提供的分支失败关闭并登记依赖。
- Blast Radius：所有 ContractForm 关系字段与 one2many 明细；通过付款样板、一个可编辑表单样本和共享门禁证明收敛。

## 2. 基础能力缺口与优先级

| 优先级 | 可见问题 | 已有契约/状态依据 | 现有共享实现断点 | 最小修改归属 | 验收 |
| --- | --- | --- | --- | --- | --- |
| P0 | 同名、短标签或隐藏副本可导致错误误标和焦点偏移 | layout field code、required 结果、`data-field-name` | canonical 按错误文案包含标签匹配；错误摘要只携带字符串 | `canonicalFormRenderState`、表单校验状态、`ScErrorSummary`、可见控件定位 | 字段 code 精确投影；展开所在分区；不聚焦响应式隐藏节点；无结构化目标时聚焦摘要 |
| P0 | many2one 外层显示错误，真实 input 没有等价 ARIA 关联 | field required/invalid/describedBy | `ScRelationField` 没有消费现有 native projection 机制 | `ScRelationField` | 真实 input 具有 `aria-required/invalid/describedby`，辅助技术可读取错误 |
| P0 | 明细列标题丢失；手机表格拥挤且字段意义难辨识 | subview column label/type/required/readonly、row state | 桌面列没有显式 title；窄屏仍依赖宽表格 | 同一 `X2ManyRelationRenderer` | 桌面列名完整；320/390 按行展示同一数据与操作 authority；无业务字段特例 |
| P0 | 明细校验只到行级，控件无精确描述 | column required + row key + field code | `rowErrors` 不能建立 control/error id 关联 | one2many validation + relation adapter | 单元格错误不误标同名列；桌面/手机共享同一错误数据 |
| P1 | 契约允许明细行编辑时，many2one 列被前端类型策略一律只读 | 必须同时满足 subview `inline_edit=true`、列非只读、子模型 field contract `relation_entry.can_read=true` | 子模型描述加载函数已存在但未被调用；顶层关系缓存键无法表示“行×列” | 现有 relation runtime + relation adapter + `ScSelect` 搜索转发 | 缺任一 authority 均只读；行/父表 domain 生效；关键词查询不截断；失败不伪装空结果；不提交写入 |
| P1 | 明细桌面/手机控件标记重复，后续容易产生行为偏差 | 两种布局共享同一 row/column/authority/error | 两套 template 重复选择、输入和错误绑定 | 抽取明细单元格编辑器，不新建数据链 | 两种布局使用同一组件与事件，字段值和错误一致 |
| 已有基线 | drawer/dialog 边界、Escape 关闭与焦点恢复 | overlay lifecycle + token | 前序 C1/A2 已收口 | 本轮不重写，仅回归 | 320/390 浮层自身边界与关闭后焦点 |
| 已有基线 | 列表查询、分页、返回恢复；页面身份和外壳 | action/list route query + page identity | 前序 A1/B2/C1 已收口 | 本轮不重写，仅回归 | 付款集合和层级样本往返不回归 |

## 3. 实施顺序

1. 先完成字段错误身份、真实控件 ARIA 和可见焦点闭环。
2. 再完成明细列标题、单元格错误和窄屏表达，同时去除桌面/手机控件逻辑重复。
3. many2one 明细只在三重 authority 完整时启用，查询复用现有 relation runtime；契约缺失或加载失败保持只读。
4. 通过 Quick 和定向门禁后，在受管 local.dev 执行只读/未提交浏览器验收；付款为主样板，其他页面只证明共享机制。

## 4. 外部依赖与失败关闭

- 子模型 field contract 若缺少 relation model、`relation_entry` 或读权限，关联列保持只读并显示通用可理解原因；不根据列标题猜选项。
- 后端若只返回非结构化错误文案，前端保留并聚焦错误摘要，不猜字段身份。
- 行级 domain 中未被契约解析器支持的表达式登记为契约依赖，不在前端执行任意表达式。
- 本轮不包含业务保存、审批、支付、fixture、数据迁移或 release gate。
