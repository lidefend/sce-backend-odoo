# 项目专项抵扣 V1

日期：2026-08-12

## 产品边界

项目专项抵扣不是新的税务事实模型。它与普通税额抵扣共同使用
`sc.tax.deduction.registration`，由后端字段 `deduction_scope` 和业务分类共同确定办理口径：

- 普通抵扣：`general` / `tax.deduction.registration`；
- 项目专项抵扣：`project_special` / `tax.deduction.project_special`。

两个入口的 domain 和默认值互斥；范围与分类不一致时模型拒绝保存。前端只渲染 action
契约，不能推断或切换事实口径。

## 数据与下游

既有抵扣数据统一归为普通抵扣，不改变历史认知。项目专项抵扣仍生成
`sc.finance.business.fact`，进入项目税务摘要和项目资金总览；其 `balance_effect` 保持为
零，不进入现金收付款、往来款或保证金余额。

## 发布判定

本能力达到 `RELEASED_FOUNDATION`。范围、分类、菜单 action、表单契约和非现金税务投影
已形成闭环。后续扩充专项类型时应增加受治理字典，不得增加平行抵扣模型。
