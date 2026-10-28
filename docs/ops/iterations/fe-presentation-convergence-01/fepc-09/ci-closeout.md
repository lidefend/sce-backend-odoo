# PR759 CI与证据范围收敛

失败HEAD：`1214b9ce88c42875436a71340f7dd6d2eea3a126`；[真实失败日志](https://github.com/lidefend/sce-backend-odoo/actions/runs/40663244489/job/122731373214)。版本守卫将11个证据文件的历史观测判为重复发布声明，专业质量失败导致合并门禁失败。公开范围与前端门禁已通过，不能因此忽略质量失败。

用户明确批准P4修复及证据精简。处理范围：一份历史运行身份投影的精确路径+完整内容SHA256登记；原始证据归档；发布守卫反例测试。无产品、工作流、VERSION、权限、数据或运行时改变。不使用目录/通配符豁免，不把历史值替换为当前VERSION，不隐藏真实失败。

历史身份投影包含观测时间、服务revision、构建指纹、原始文件摘要及不可变提交。其完整摘要被守卫锁定，任一内容变化都失效；即使将版本改成不再匹配当前VERSION，独立完整性检查也仍拒绝。缺文件、CRLF变化、追加声明、换路径均有回归覆盖。

47个原件已保存至本地.git/codex-recovery/FEPC-09/pr-scope-closeout并逐个回读哈希；原始提交仍是当前分支祖先，GitHub固定链接可查，不强推不重写历史。最终树只保留审阅所需的投影和截图；原始探针和失败未丢弃。

定向验证及最终身份/CI结果在当前run与PR更新记录中维护；本文件不预先宣称远端通过。FEPC-10实施与审计PR分开，其他候选未授权实施。

本地已通过 `make verify.product.release.version`（17项release测试、版本守卫、10项package测试）、`make ci.local.iteration`、`make ci.delivery.freeze.prepare`。47原件归档/Git对象哈希与最终Markdown链接、JSON均通过。原validation.json记录首次审计时的检查，不伪装为当前完整交付结果。
