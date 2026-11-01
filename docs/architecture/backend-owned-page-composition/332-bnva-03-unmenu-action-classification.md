# 332 · BNVA-03 Unmenu Action Classification

233 个无菜单 act_window 全都有 xmlid，无匿名 action。

| 分类 | 数量 |
| --- | --- |
| CONTEXT_ACTION（binding_model_id 绑定） | 31 |
| WIZARD_ACTION | 11 |
| REPORT_ACTION | 9 |
| EMBEDDED_ACTION | 3 |
| NAMED_NEEDS_CALLER_ANALYSIS（待调用方分析） | 179 |

179 项需进一步检查按钮/服务端动作/其他 action 引用，确认是内嵌入口还是真正孤立候选。
