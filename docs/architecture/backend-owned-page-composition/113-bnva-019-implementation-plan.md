# 113 · BNVA-019-08 · 正式实施顺序与兼容策略

> 目标：在冻结信息准入边界后，给出不改变行为的最小实施顺序。

## 1. Native-to-Contract Authority Principle

原生事实只采集一次，业务语义只声明一次，契约只投影一次，前端只消费一次。

- Odoo 负责原生事实。
- Native Projection 负责忠实规范化。
- 业务配置负责明确语义。
- Contract Assembler 负责准入和投影。
- Vue Renderer 负责表现。
- Guard 负责验证各层没有越权或分叉。

## 2. 实施顺序

| 阶段 | 内容 | 风险 |
| --- | --- | --- |
| 1 | 补齐 Canonical AST（div / 深层嵌套容器），仍只作内部投影 | 低 |
| 2 | 建立 ContractAdmissionPolicy（内部可测试规则） | 低 |
| 3 | 用 Canonical AST 统一 view_Parser 的 arch 解析入口 | 中 |
| 4 | 收缩旧字段名启发式（保留 selected-authority / fallback 路径） | 中 |
| 5 | 收敛 modifiers / 字段元数据投影 | 中 |
| 6 | 建立两个不同权限角色的运行时对照测试 | 高（安全） |
| 7 | 职责边界迁移（ui_contract_v2 / page_assembler / assembler） | 高 |

## 3. 兼容策略

- 五个已知页面 + PC-01/PC-02 的结构身份、字段出现次数、权限投影不变。
- 旧消费者对 slots / fieldGroups / fieldOwnership 的消费保持可用。
- `structureAuthority` 的 `container_tree` / `native_form_slots` /
  `task_sections` 语义不改变。
- 每次收敛都用精确 HEAD Quick + 定向单测 + Guard 验证。

## 4. 禁止事项

- 不新增平行公开 Schema。
- 不把业务语义硬编码进平台内核。
- 不用 sudo 补全普通用户视图。
- 不把大文件机械拆分当作收敛完成。
- 不追求把 Odoo 所有原生属性都塞进 V2（最小充分契约）。

