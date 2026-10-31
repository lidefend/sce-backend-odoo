# 47 · Project Action/View Differential Trace

| Item | 590 / 1776 | 652 / 944 |
| --- | --- | --- |
| V2 pageId | project.project.form | project.project.form |
| slots | 0 | 0 |
| fieldGroups | false | false |
| pageComposition | unclassified_historical | unclassified_historical |
| render profile | readonly | edit |
| native shell | true | true |

## Observation

两个入口共享 V2 pageId，slots/fieldGroups 状态一致。当前没有证据证明它们使用
不同的结构来源；但 render profile 不同，仍需分别验证最终布局节点。

