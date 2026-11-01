# 345 · BNVA-03 Action Invocation Chain Matrix

## 方法

- 第一轮：按 xmlid 名称扫描 Python / XML / TS / QWeb 引用文件。
- 限制：grep 只能区分“跨文件引用”与“同文件定义+引用”，不能把同文件内的按钮引用拆出来，
  因此单文件动作需第二轮上下文核对。

## 结论

跨文件引用 45 个可判定为有调用方；单文件 134 个不能仅凭 grep 判为孤立，需同文件引用核对。
