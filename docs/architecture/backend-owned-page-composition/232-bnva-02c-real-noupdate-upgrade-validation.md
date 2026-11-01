# 232 · BNVA-02B-02C-02C-01 · 真实 noupdate 升级验证

## 状态

`not_run`：local.test 的 Odoo 应用容器未运行（仅 db/redis 运行）。真实 `-u`
升级（尤其 noupdate=0→1 的既有库升级）未执行。

## 待执行步骤（已准备）

1. 升级前代码安装模块。2. 建租户覆盖。3. 记录摘要。4. 当前代码 `-u` 升级。
5. 核验 32 个 noupdate=1。6. 核验 VERSIONED。7. 重复升级。8. 核验 ir.model.data。
9. 核验覆盖。10. 核验 Resolver。

必须覆盖“旧 noupdate=0 库升级到新 noupdate=1”场景，不只全新安装。

