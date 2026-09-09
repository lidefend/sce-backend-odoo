# 前端层级工作区 C1 抽屉补验收口

日期：2026-09-09

状态：C1 补验本地候选通过；未执行发布、推送、PR 或合并

基线 HEAD：`297329088d4ff5547d9a6e5aa2febb0c0c99781f`

冻结候选 HEAD：`abda10891b1d0c3f8b2c3177bce7c2b91033429a`

## 1. 目标与边界

唯一目标是修复共享 `ScDrawer` 在窄屏 portal 浮层中的可见越界，并补齐层级范围抽屉的首次打开、关闭重开、视口切换与焦点恢复证据。

- Formal Product Layer：P0 通用浮层机制；P4 验证与本报告。
- Layer Target：Web `ScDrawer` 与受管候选层级旅程验证。
- Standard vs User-Specific：平台通用响应式和可访问性行为。
- Why Here：固定 420px/920px drawer token 被直接用于 TDesign portal，根文档 overflow 无法观察浮层自身越界。
- Why Not Elsewhere：无需修改收入合同、页面契约、业务状态、P1/P2/P3 配置或运行环境。
- Blast Radius：所有共享 `ScDrawer` 消费者的窄视口最大宽度、标题换行和 header actions 收缩；overlay/hierarchy 门禁及真实层级旅程证明约束。

## 2. 实现

- drawer 宽度使用 `min(正式宽度 token, 100vw)`，保留桌面 token 并限制窄屏 portal 浮层。
- 标题和说明允许按任意长文本换行；关闭动作区域不参与压缩。
- 候选浏览器断言直接检查 portal panel、dialog surface、标题、关闭按钮和首个树节点，而不再只检查根文档 overflow。
- 移动旅程依次验证首次打开、Escape 关闭与焦点恢复、重新打开、320↔390 打开态切换和恢复；断言等待进入动画稳定后采样。

## 3. 验证

冻结候选完整工作树指纹：`5a81936b3f6e1d8f1114afec37789181e9a47068651166950fb6952c611f3d5f`；scope manifest `211ad720e391b6088f1600bd80a3d8a5c844be60713dc08ac4416b87a48f6633`；7329 paths。

静态验证：

- `make verify.frontend.overlay_lifecycle.unit`：PASS，9 tests；overlay guard canonical=3、consumers=3、formal gaps=0。
- `make verify.frontend.hierarchical_worksheet.unit`：PASS，后端 18 tests、interaction 15 cases、domain assertions PASS。
- `make verify.frontend.typecheck.strict`：PASS。
- `make verify.frontend.style_system.guard`：PASS，hardcoded color refs 0。

真实浏览器：

| 场景 | 结果 |
| --- | --- |
| 320px 暗色首次/重开 | panel `0..320`；surface `16..304`；标题、关闭按钮、树节点均在视口内 |
| 320→390→320 打开态切换 | 三次边界断言均 PASS；标题 `收入合同履约结构` 未截断 |
| 390px 明色首次/重开 | panel `0..390`；surface `16..374`；全部内部关键元素可见 |
| 390→320→390 打开态切换 | 三次边界断言均 PASS |
| Escape | 关闭后焦点恢复到层级范围触发器 |
| 完整层级旅程 | 46→scope 1→query 0→恢复→record 15→返回状态保持继续 PASS |
| 证据完整性 | 两组 `mutationCount=0`、`errors=[]`、`failures=[]`、根 overflow 0 |

证据：

- `artifacts/playwright/frontend-c1-drawer-closure-dark-320/summary.json`
- `artifacts/playwright/frontend-c1-drawer-closure-light-390/summary.json`
- 同目录 `mobile-*-scope-drawer-open.png` 为打开态截图。

## 4. 风险与回滚

风险局限于共享 drawer 在窄视口从固定宽度变为视口上限；桌面仍使用原 token。可按提交边界回退 `5b2e78f2`（产品）及 `abda1089`（稳定边界断言）。

本批没有写配置或业务数据，没有修改 contract/schema、启动链、路由 authority、角色、数据库、fixture、profile 或端口。C1 补验已独立收口，可以进入 C2；正式 release gate 仍未运行，状态保持 `verification_pending`。
