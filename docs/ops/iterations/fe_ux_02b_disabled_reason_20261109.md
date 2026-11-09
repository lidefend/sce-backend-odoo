# FE-UX-02-B：禁用操作原因一致性

## 批次边界

- Formal Product Layer：P0 platform kernel product。
- Layer Target：前端工作流禁用操作的原因表达与激活。
- Module：`CanonicalActionBar`、`ContractFormProductHeader` 和共享工作流原因交互。
- Standard vs User-Specific：平台工程标准。
- Why Here：后端契约已经声明动作可用性和原因；前端只负责把该原因通过既有
  `ScPopover`、设计 Token 和标准交互暴露给鼠标、触摸、键盘及辅助技术。
- Why Not Elsewhere：不修改 Contract V2、权限、状态转换、行业规则、客户偏好或低代码配置；
  前端不得重新判断动作是否可用。
- Blast Radius：仅影响工作流动作栏与表单页头的禁用原因表达、共享键盘激活规则及专项测试。

## 当前事实

- `workflowDisabledReason` 已从 `reasonMessage`、`reasonCode` 和通用 fail-closed 文案得到
  唯一展示原因。
- `ContractFormProductHeader` 已把禁用原因投影为可聚焦触发器，并使用 `ScPopover` 表达。
- `CanonicalActionBar` 的直接动作仍只有 `title` 与 `data-disabled-reason`，键盘和触摸用户
  不能可靠打开原因。
- `ScDropdown` 的 overflow disabled item 已使用同一个 `ScPopover` + 可聚焦触发器模式。

## 目标

1. 让 `CanonicalActionBar` 的禁用直接动作使用与页头一致的可访问原因触发器。
2. 让两个消费者复用同一 Enter/Space 激活规则，避免行为漂移。
3. 证明打开原因不会执行动作，1440 与 390 视口均无布局和运行时回归。

## 排除

- Contract V2、ACL、权限和业务状态转换。
- 新增组件、Renderer Runtime 或 Registry。
- 修改后端原因文本或其计算规则。
- FE-UX-02-C、FE-UX-02-D、部署和合并。

## 执行记录

### 基线

- Branch：`fix/fe-ux-02b-disabled-reason-20261109`
- Base：`main@2d1614aacc44967061fd7e6259e26ffc830127df`
- 初始工作树：CLEAN
- 已合并 main 的 vendor-coupling guard 把
  `scene_primitive_selection_test.mjs` 的 2 个 TDesign 内部选择器报告为基线 0 的新增命中。
  该文件在 main 与本分支一致；最小 P4 修复只把测试改用公开角色和 `ScDateField` 语义表面，
  不提高 vendor 选择器基线。

### 验证计划

- `verify.frontend.professional_workflow.unit`
- `verify.frontend.native_form_action_presentation.browser`
- `verify.frontend.product_page_header.unit`
- `verify.frontend.form_header_action_primitives.unit`
- `verify.frontend.style_system.guard`
- `verify.frontend.lint.src`
- `verify.frontend.typecheck.strict`
- `verify.frontend.build`
- `make ci.local.iteration`

### 定向验证

- `verify.frontend.professional_workflow.unit`
  - workflow presenter：12 cases PASS。
  - 共享键盘激活：4 cases PASS。
  - workflow guard：10 tests PASS。
- `verify.frontend.native_form_action_presentation.browser`
  - 既有 NativeFormTreeRenderer：1440/390 PASS，0 console errors。
  - 新 CanonicalActionBar/ScPopover/SceneButton：2 视口、26 项受控断言 PASS。
  - 1440 鼠标与 390 触摸均能打开原因。
  - Enter/Space 打开原因，焦点环为 2px solid，Space 不滚动页面。
  - 禁用动作事件 0 次，启用动作事件 1 次。
  - document width 不超过 viewport，browser errors 为 0。
- `verify.frontend.playwright_vendor_coupling.guard`
  - vendor selector total 从登记 109 降至 103，未提高基线。
- `verify.frontend.scene_primitive_contract.behavior`
  - adapter、collection、selection 和 text controls 浏览器检查全部 PASS。
- `verify.frontend.product_page_header.unit`
  - readonly header 34 checks、model 28 cases、adapter entries=4/axes=15、
    page-header guard 75 tests PASS。
- `verify.frontend.form_header_action_primitives.unit`：9 tests + guard PASS。
- `verify.frontend.style_system.guard`：PASS。
- `verify.frontend.lint.src`：0 errors。
- `verify.frontend.typecheck.strict`：PASS。
- `verify.frontend.build`：PASS。
- `verify.agent.ledger.unit`：18 tests + guard PASS。
- `verify.frontend.dev.incremental.unit`：89 tests PASS。

### 首次 `ci.local.iteration` 诊断

- 首轮在未提交候选上报告 `frontend_presentation` /
  `list_surface_structure: uncommitted suite inputs changed`，属于阶段身份条件，不是产品失败。
- 同时 `verification-lane-coverage` 拒绝新增独立 browser target。
- 恢复动作：把新 Chromium 用例并入既有
  `verify.frontend.native_form_action_presentation.browser`，不新增验证面；
  `audit.verification.lane_coverage.check` 随后 PASS。
- 下一轮在 clean 提交上执行 `make ci.local.iteration`。

### 状态

- 实现：IN_PROGRESS
- 真实浏览器验收：PASS（组件级 1440/390）
- PR：NOT_CREATED
- 合并、部署：未执行
