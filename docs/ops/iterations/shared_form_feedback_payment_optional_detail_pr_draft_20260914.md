# Draft PR：共享表单反馈与付款申请可选明细闭环

## Summary

本 PR 统一共享表单的标签、帮助、错误、只读语义和动态办理反馈，并按原生视图优先原则收敛表单结构权威。付款申请同时获得可选的“按明细填写”能力：无明细时直接填写申请金额；使用有效明细时，后端以明细合计作为申请金额权威。

不改审批权限、付款登记、会计写入或历史业务数值，不创建数据库/fixture，不为付款模型增加前端样式特判。

## User-visible improvements

- 帮助和错误关联到真实可操作控件；错误出现/解除时 `aria-describedby` 与 `aria-invalid` 同步更新。
- 普通只读值减少重复“只读”噪声；状态、金额、日期、关系及长文本保留各自展示语义。
- 页面级说明、动作阻断、字段错误和后续阶段条件按作用范围动态出现，不再全部作为章节或普通只读字段堆叠。
- 付款申请正文与导航消费同一棵原生优先章节树，内部布局组和辅助提示不会自动升级为一级导航。
- 申请金额位于可选明细之前；“按明细填写”默认折叠，展开后表格跨满业务区域，收起后不留边框或空白。
- 明细生效后申请金额随合计同步。空白/零金额行显式无效；历史不一致不会在打开、onchange 或无关保存时被静默修复。
- 删除最后一行有取消/确认，确认后保留最后合计；从结算单引入执行同币种校验并使用契约币种格式。
- 历史确认金额退出当前申请金额编辑区，在历史追溯中只读呈现；账户来源与账户完整度分别表达来源事实和完整状态。

## Architecture impact

- Formal Product Layer：P0 共享契约合成与渲染；P1 建设行业付款申请视图及金额规则；P4 聚焦 guard 和受管证据。
- 原生最终合成视图定义基础结构，配置仅提供受约束增强；冲突显式失败。正文和导航不再分别选择或推断结构。
- 共享控件沿用 TDesign 公开 API 与现有桥接，不依赖私有类名、固定节点顺序或重新实现官方组件。
- P1 后端保证金额权威、币种精度和提交约束；P0 仅提供即时显示、披露和确认交互。

## Verification

- `make ci.local.iteration`：PASS，16 tests。
- 共享控件、presenter、section navigation、detail collection 和严格类型检查：非零 PASS。
- X2Many adapter guard：4 个反例 PASS（2 个合法调用、2 个缺失/错误调用）。
- 后端金额规则：选择 4 个方法并实际执行 4 个方法，Odoo 统计 6 tests，失败/错误 0；币种及 onchange 修复另有非零 2 方法、1 方法 PASS；最终模型跨币种/权威名称搜索方法再次实际执行 1 个方法，框架统计 3 tests，失败/错误 0。统计次数不冒充独立业务用例数。
- `smart_construction_core` 受管增量升级、local.dev restart/health：PASS。
- 621 的 1088×791、390×844 初始折叠/展开/再次收起：PASS，零写入；展开宽度比 1，收起无内容节点。
- 当前候选 `16b68142af22be2811e59a3e1e5087e4f3383501` 上，现有专用付款 fixture：引入明细后保存、权威回读和刷新 PASS；取消删除保持行，确认删除后回读 0 行且金额保留；专用 reset PASS。来源绑定 S69 settlement/line XMLID，resolver 使用实际财务用户、公司、币种、项目和合同约束；中断路径由 `EXIT` trap 执行专用 reset。
- 621 与收入合同/结算共享反例在 1088×791、390×844 下 `pass=true`、零写入：显式只读空值不覆盖真实值，不进入编辑控件；未声明空值保持既有回退。
- 冻结准备、唯一一次 Quick 和独立复核由最终 clean HEAD 的仓外 exact-head 证据记录；不为回填结果修改候选。

## Evidence

- 迭代报告：[shared_form_feedback_payment_optional_detail_20260914.md](shared_form_feedback_payment_optional_detail_20260914.md)
- 结构权威决策：[native_first_form_structure_authority_v1.md](../../architecture/native_first_form_structure_authority_v1.md)
- 布局：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/shared-form-payment-621-optional-detail-states-1f96aac5/summary.json`
- 字段语义与共享反例：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/shared-form-semantic-fields-16b68142/summary.json`（绑定完整候选 `16b68142af22be2811e59a3e1e5087e4f3383501`）
- 真实闭环：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/payment-optional-detail-real-closure-16b68142/introduce-summary.json`、`remove-summary.json`（均绑定完整候选 `16b68142af22be2811e59a3e1e5087e4f3383501`）

## Boundaries

- 621 仅用于只读/未提交布局证据；真实写入仅使用登记的 demo fixture。
- 未执行付款审批、付款登记、会计写入、全角色、生产数据或完整读屏器体验。
- 历史金额差异只显示并阻止提交，不自动修数。
- 既有批准结算发票快照不一致不属于本 PR；最终专用付款旅程不依赖该历史快照，完整受管入口已通过并恢复登记 fixture。

## Risk and rollback

共享 P0 与金额 P1 影响面通过非零测试、621 只读样板及专用 fixture 闭环控制。回滚必须按依赖逆序：P4 旅程/guard → P0 可选集合与反馈消费 → P1 页面结构和金额权威；不能只撤一侧后继续交付。无需数据迁移回滚。

## Delivery status

`READY_FOR_FINAL_FREEZE_GATES`。完成生成证据预检后冻结 clean HEAD，只运行一次 Quick 并绑定独立复核。远端 push、PR、Ready、合并、部署和发布均不在当前授权范围。
