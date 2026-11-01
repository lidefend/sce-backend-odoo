# 398 · BNVA-04-06B Acceptance

## 结论

sc.tax.certificate.registration 原生 View 声明修正完成，改动最小且精确：

- 删除 tree 两个 `source_created_*` 可选列。
- 删除 form 整个「录入来源」group（仅含这两个孤儿字段）。

静态验证全部 PASS，未触及其他任何层或模型。

## 兄弟模型风险

sc.tax.deduction.registration 同类问题已登记，不在本轮修改，后续专项处理。

## 下一轮

BNVA-04-06C：双页面静态回归（XML / Contract / Assembler / Guard / 字段投影统一复核）。

完成后停止，等待统一调度。
