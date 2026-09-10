# 共享表单响应式容器与阅读宽度收口（2026-09-10）

## 1. 结论

本批已关闭 320px 合同新建页的内部横向溢出，并把验证从根文档宽度扩展到实际容器、章节栏、字段、控件和公开语义弹层。四个代表样本在 1440/1088/390/320、明暗主题的最终只读候选均通过；当前状态为等待产品复核，不据此宣布全部表单或全系统验收完成。

## 2. 边界与实现

- Formal Product Layer：P0 平台通用前端 renderer；P4 只承载守卫、浏览器测量和记录。
- Layer Target：`frontend/apps/web` 的 native 表单收缩链、共享章节导航和移动字段对齐。
- Standard vs User-Specific：平台机制。容器收缩、滚动归属和控件边界不属于施工行业事实、客户偏好或低代码配置。
- Why Here：缺陷由 grid item 的固有 `min-width:auto` 沿 native page、导航和表单树传播，必须由共享 renderer 统一解决。
- Why Not Elsewhere：没有修改契约、字段、权限、动作、金额口径或隐藏章节；没有用 `overflow:hidden` 掩盖；没有把修复放入业务模块或 P4 工具。
- Blast Radius：contract-driven task form 与 native workspace form 的外层收缩、章节导航轨道、嵌套分组内边距及浏览器边界证据。

产品实现：

- native page、driver host、form tree、辅助区与协作区统一声明 `width/max-width:100%`、`min-width:0` 和 `border-box`，切断固有最小宽度向外扩张。
- 章节导航外壳严格继承正文宽度且不裁切；只有内部 track 使用 `overflow-x:auto`。每个入口滚入轨道可视区后再定位章节。
- 移动端 header 与普通分组使用同一内边线；嵌套 group 不再逐层增加左右缩进。
- 原后端隐藏章节继续隐藏；合同金额语义限制与 `smart_construction_demo` 目录问题继续独立登记。

## 3. 缺陷复现与关闭

基线 `7be995af2b87c4d384464decc3db23571859feba`，完整指纹 `0debfd8efd778e42269d0a21061ec9bf458eab9bd9b7755c9853e0b347bc50f5`（7355 paths）。在旧候选 `d0ede53f67d5d5b00eb3dae7bc7cf9a24e2d4bfb` 上，收入合同新建 320px 暗色复现为：

- 正文 owner：x=25..280，clientWidth=255。
- native page：x=25..337，width/scrollWidth=312，`min-width:auto`，向右超出 57px。
- 章节导航和 form tree 继承 312px；根文档仍为 320px，证明根级 `scrollWidth` 指标会漏报。

最终候选 `04c774035e241eb82343f37ceac951fcd8c79d97`，完整指纹 `67bd65ed22559dfcdccf0b2c8e779463f8e7916a547a210b700f70db1a879089`（7356 paths）：

- 320px 合同新建 native page 为 x=25..280，clientWidth=scrollWidth=255。
- 导航外壳为 x=25..280、255px；track 为 clientWidth=255、scrollWidth=312、`overflow-x:auto`，超宽仅存在于获准滚动的内部轨道。
- 实际关系控件为 x=38..267；真实打开的公开 `role=listbox` 弹层同为 x=38..267，完整落在 320px 视口内。
- 末项导航滚动后完整可见，定位目标位于吸顶区域下方。

## 4. 验证

- `make verify.frontend.quick.gate`：最终候选 HEAD PASS，包含 strict typecheck、静态 build、官方组件接入、form canvas、renderer、relation、overlay、theme 与生成清单门禁；所有测试入口均为非零。
- `python3 -m unittest scripts.verify.test_local_dev_candidate_frontend`：9 tests PASS。
- 浏览器 final light：1440×960 / 390×844，4 个样本 × 2 viewport 全部 PASS。
- 浏览器 final dark：1088×960 / 320×844，4 个样本 × 2 viewport 全部 PASS。
- 两份最终摘要合计 16 个路由视口、48 张首屏/中段/底部截图、756 个内部边界、8 次真实弹层边界、76 次章节定位；`mutationCount=0`、`errors=[]`、`failures=[]`。
- 材料桌面首屏同时看到明细标题和添加入口；合同详情桌面为比较表、移动为标题卡；允许横向滚动的导航轨道/明细表格单独分类。
- 人工复核确认 320 合同新建控件右边框完整、付款关键金额与材料明细入口无回归、暗色和明色中底部内容可读。

## 5. 证据索引

- before：`artifacts/playwright/form-responsive-width-before-d0ede53f/summary.json`
- targeted final：`artifacts/playwright/form-responsive-width-targeted-507dbb3e/summary.json`
- final light：`artifacts/playwright/form-responsive-width-final-light-1440-390-04c77403/summary.json`
- final dark：`artifacts/playwright/form-responsive-width-final-dark-1088-320-04c77403/summary.json`
- final fingerprint：`artifacts/fingerprints/form_responsive_width_candidate_04c77403.json`

历史失败不作为通过证据：一次暗色桌面详情在关系数据水合前采样，随后同次移动样本已出现卡片。验证器现按显式 comparison 开关等待桌面表格/移动卡片后再截图，最终 exact-head 两套矩阵均通过。

## 6. 风险、回滚与后续

- 结论限于四个代表样本的本地只读候选，不覆盖真实保存、多角色、旧版本升级、acceptance 或发布。
- P0 产品回滚：在受管修复分支回退 `e5085e42`；无需契约、数据库或 fixture 回滚。P4 守卫、清单和报告可独立回退。
- 当前版本验收环境恢复与旧版本升级兼容仍是两个独立 P4 任务；本批未执行二者。
- 当前状态：响应式闭环完成，等待产品复核是否冻结表单表达成果。未恢复键盘/查询专题，未追加泛化美化任务。
