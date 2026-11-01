# 350 · BNVA-03 Same-file Action Reference Audit

## 方法

对每个动作执行 `rg <name> addons/smart_construction_core addons/smart_core frontend/apps/web/src`，
排除定义行 `id="<name>"`。

## 结果

17 个动作均无任何引用（无 `ref=`、无 `type="action"`、无 Python `env.ref`、无 JS 调用），
说明不存在同文件内的按钮/上下文/向导调用。它们有 Action Definition，但既无 Navigation Entry，
也无 Invocation Entry。
