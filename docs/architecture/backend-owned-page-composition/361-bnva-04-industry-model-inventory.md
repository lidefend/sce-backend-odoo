# 361 · BNVA-04 Industry Model Inventory

## 口径修正

smart_construction_core 实际有 **277** 个 distinct ir.model（不是 04-01 写的 254）。
254 来自带名称前缀过滤的统计，遗漏了 tender.*（10）和部分 other（23）中的模型。
权威口径：`count(distinct ir_model where ir_model_data.module='smart_construction_core') = 277`。

前缀分布：sc.* 187、project.* 41、other 23、construction.* 10、tender.* 10、payment.* 6 = 277。

## 187 个 sc.* 按消费者分类（证据驱动）

| 分类 | 数量 | 证据 |
| --- | --- | --- |
| INDUSTRY_CORE / WORKFLOW | 50 | 有 menu + ui.business.config.contract |
| INDUSTRY_WORKFLOW | 69 | 有 menu，暂无 productized contract |
| HAS_ACTION_ONLY | 11 | 有 action，无 menu（多为价目/字典/行/汇总） |
| TECHNICAL_INFRASTRUCTURE | 57 | 无 action/menu/contract，且全部为 abstract/base 或 transient（mixin/基类/向导） |

57 个“无消费者”不是孤儿业务对象，而是抽象基类、mixin 和 TransientModel，属于技术基础设施。
