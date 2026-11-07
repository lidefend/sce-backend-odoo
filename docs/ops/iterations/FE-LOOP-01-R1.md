# FE-LOOP-01-R1 验证闭环边界修复

## 身份与边界

- 基线：`07edc93db10381806f80ffe5db4995306153a456`
- 分支：`fix/fe-loop-01-r1-boundary-20261107`
- Formal Product Layer：P4
- Layer Target：前端增量执行 fail-closed 与共享 UI 静态验证覆盖

本批不修改 PR #834，不启动 FE-RENDERER-02，不执行浏览器验收、候选构建、部署或合并。

## 评审发现

1. 纯未映射源码变更先被标为 `blocked`，随后零目标分支将其覆盖为 `not_run` 并返回 0。
2. 共享 UI TS/Vue 被规划为基础源码，但现有 web ESLint/严格 TypeScript 工程没有完整覆盖该包，
   且扩展名列表包含当前命令未扫描的 `.tsx`。

## 修复与验证

### 1. 纯未映射路径 fail-closed

- 先处理 `blocked`，再处理零目标 `not_run`，避免后者覆盖前者。
- `addons/smart_core/models/example.py` 实跑结果：`BLOCKED`，退出码 2。
- 纯文档路径实跑结果：`NOT_RUN`，`verificationPassed=false`，未执行目标为 0。
- 新增 executor 回归测试，覆盖 requiredTargets 为空的纯未映射路径。

### 2. 共享 UI 包真实基础覆盖

- 新增 `frontend/packages/ui/tsconfig.json`，strict 模式全量包含 `src/**/*.ts`、
  `src/**/*.tsx`、`src/**/*.vue`。
- 新增 `frontend/packages/ui/src/css-modules.d.ts`，为 TDesign CSS side-effect import
  提供类型边界。
- `verify.frontend.lint.src` 现在依赖 `verify.frontend.ui.lint`，后者使用同一 ESLint 配置扫描
  共享 UI 的 `.ts/.tsx/.vue`。
- `verify.frontend.typecheck.strict` 现在依赖 `verify.frontend.ui.typecheck.strict`，后者运行
  shared UI 独立 strict 工程。
- Web `lint:src` 正式支持 `.ts/.tsx/.vue`。
- `SceneReviewPanel.vue` 移除了未使用的 `props` 绑定，使共享 UI lint 达到 0 error。

### 3. 执行验证

- Shared UI lint：PASS，0 error、3 个既有 warning。
- Shared UI strict typecheck：PASS。
- 临时 Web 与 Shared UI `.tsx` 探针：基础 lint 与 strict typecheck 均 PASS；探针已删除，
  不进入候选。
- `make ci.local.iteration`：执行 8 个目标全部 PASS。
  - run context：56 tests
  - incremental planner/executor：67 tests
  - page-pattern parity：15 + 13 tests
  - primitive adapter：41 tests
  - publish preflight contract：18 isolated push scenarios + 6 tests
  - lint 与 strict typecheck：PASS
- 最终执行回执：
  `.runtime/frontend-dev-validation/executions/20261107T112513Z-552260-441686588/receipt.json`

### 4. Review-only publication

PR #835 在本轮评审到达前已经按上一轮授权合并，因此无法再向 #835 推送新 HEAD。
为遵守本轮“不合并”，新增 `PR_PUBLISH_MODE=review`：

- 仍要求 clean、精确 `EXPECTED_HEAD`、完整 `ci.local.iteration` 和生成证据预检。
- 仅允许合并期运行时证据保持 pending，供独立评审使用。
- 默认 `PR_PUBLISH_MODE=merge` 继续要求 `--stage merge --require-ready`，没有放宽合并门禁。

受管 `list_surface_structure` 尝试未形成通过证据：当前验收后端绑定在未合并的
`ac7a858fd`，其 `addons` 树与当前 main 基线不同，入口在任何浏览器断言前退出。
归类为 `environment_defect`；本轮不伪造复用、不重写证据，也不以该失败声称产品通过。

两处评审阻断均已关闭。本批不合并。
