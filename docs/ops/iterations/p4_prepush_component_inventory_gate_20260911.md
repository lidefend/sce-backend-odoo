# P4 推送前组件清单门禁

## 1. 本轮变更

- 目标：让新增前端源文件引起的组件接管清单摘要变化在远端写入前被发现，不再等待 `frontend_release_gate` 报错。
- 完成：`ci.local.quick.run` 消费既有非零组件清单守卫；`pr.push` 在首次远端访问前同时刷新通用报告和组件接管清单，任何确定性变化都会令工作区变脏并零 push 退出；清单保持不变时继续运行生成报告守卫和组件清单守卫。
- 未完成：本批不改变其他清单的登记方式，不重构生成报告框架，也不处理产品、契约、数据库、fixture、acceptance 或发布。

## 2. 影响范围

- Formal Product Layer：P4 ops delivery tool。
- Layer Target：受管本地 Quick 与 `pr.push` 推送前生成证据链。
- Module：`make/ci.mk`、`scripts/ops/git_safe_push.sh`、既有组件清单生成器测试。
- Standard vs User-Specific：全仓交付治理机制。
- Why Here：#463 首个 HEAD 的本地 Quick 通过，但组件清单摘要陈旧，直到远端前端门禁才失败，证明本地交付入口覆盖不完整。
- Why Not Elsewhere：不应靠业务分支人工记忆刷新，不应降低远端门禁，也不应修改组件或渲染逻辑掩盖证据差异。
- Blast Radius：本地 Quick 增加 7 项既有清单测试；每次受管 push 增加一次确定性刷新和一次清单校验。没有运行态、schema、业务数据或发布影响。

## 3. 失败前置与实现

- 修复前反例：扩展 `git_safe_push.sh --self-test` 后非零失败；日志显示只调用 `refresh.generated_reports` 与 `ci.generated_reports.guard`，随后发生一次模拟 GitHub push，未调用组件清单入口。
- 修复后：模拟组件清单刷新产生 tracked 变化时，入口在远端探测和 push 前停止；正常路径必须经过 `verify.frontend.component_driver_takeover.unit` 才允许一次模拟 push。
- 生成器反例：临时前端源目录新增 `.ts` 文件后，`sources()` 数量增加且 `inputDigest` 必然变化，测试结束自动清理临时目录。

## 4. 验证

- `bash scripts/ops/git_safe_push.sh --self-test`：PASS，13 个隔离场景，真实远端写入为 0。
- `python3 -m unittest scripts.audit.test_generate_frontend_component_driver_takeover_inventory`：PASS，7 项。
- `make verify.frontend.component_driver_takeover.unit`：PASS，7 项；`required=35`、`missing=0`、`bridge_only=0`、`raw=0`。
- `git diff --check`：PASS。
- 最终 exact-head `make ci.local.quick`：待最终提交后执行；浏览器、contract snapshot、数据库、fixture、模块升级和发布验收不适用于本批。

## 5. 风险与回滚

- 风险：Quick 和 push 会多执行一次轻量组件清单生成计算；这是有意的前移失败成本，不引入网络或运行态依赖。
- 风险：刷新检测到真实变化时 `pr.push` 会停止，需要审阅并提交清单后重试；该 fail-closed 行为正是本批目标。
- 回滚：回退本批 P4 提交即可；没有数据库、容器、契约或产品回滚步骤。

## 6. 下一步

- 完成本地提交与 exact-head Quick 后进入独立复核及 PR 授权。
- 不将收入合同、controller checkpoint 或历史分支治理并入本批。
