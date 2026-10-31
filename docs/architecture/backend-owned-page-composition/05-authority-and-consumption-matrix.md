# 05 · Authority and Consumption Matrix

## Mechanisms

| 机制 | 数据来源 | 职责 | 是否决定结构 | 是否被前端消费 |
| --- | --- | --- | --- | --- |
| formStructureContract | 后端 V2 | 页面结构 | 部分 | 是 |
| field_groups | 后端 V2（本页空） | 字段分组 | 否（本页） | 可选 |
| page_orchestration | 后端组装 | 页面区域 | 未进入本页 | 否 |
| coreFieldNames | 前端语义派生 | 默认字段 | 可能 | 是 |
| advancedFieldNames | 前端语义派生 | 默认字段 | 可能 | 是 |
| Legacy fallback | 前端布局函数 | 补齐字段 | 是 | 是 |

## B1 field ownership case

| 字段 | V2 声明 | 页头投影 | Detail 投影 | 重复责任 |
| --- | --- | --- | --- | --- |
| project_code | 未明确 | 是 | 是 | 是 |
| user_id | 未明确 | 是 | 是 | 是 |
| manager_id | 未明确 | 是 | 是 | 是 |

## Conclusion

当前没有一个机制在 Action 590 上明确字段主展示职责；前端 Legacy fallback
成为事实上的第二权威来源。

