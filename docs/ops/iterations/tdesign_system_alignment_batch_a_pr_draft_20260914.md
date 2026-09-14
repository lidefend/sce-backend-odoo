# Draft PR：统一 TDesign 共享排版、表面与章节导航

English: [tdesign_system_alignment_batch_a_pr_draft_20260914.en.md](tdesign_system_alignment_batch_a_pr_draft_20260914.en.md)

## Summary

本 PR 在现有契约体系和 TDesign 1.20.5 桥接上统一页面排版、控件文字、Card/章节表面和章节导航溢出表达，并让只读长值始终留在自己的字段槽位内。

不升级依赖，不改外壳、色板、P1 XML、业务章节/字段顺序、权限、动作、保存链或业务数据。

## User-visible improvements

- 列表、办理表单和只读详情共享清晰的页面标题、章节、正文和辅助文字层级。
- 长表单使用连续工作面，减少父卡/章节/子卡连续边框与阴影，同时保留表格、明细和浮层的功能边界。
- 章节导航的前后浏览按钮不覆盖末端标签，桌面、触屏和键盘均沿用公开按钮能力。
- 浏览到首尾时按钮不会因节点移除而丢失键盘焦点，并以公开 `aria-disabled` 状态表达边界。
- 合同长名称、无空格编号和关系名称在本字段内自然换行，不与相邻字段混叠。
- 日期、关系选择和文本域在复合表单中保持同一正文尺度、控件基线和字段边界。

## Architecture impact

- Formal Product Layer：P0 共享表现层；P4 聚焦守卫和交付证据。
- P0 仅消费既有 token、appearance、契约结构和 TDesign 公开 API；没有模型名、字段名、XML ID 或业务事实特判。
- P1/P2/P3 均未改变；三个代表页面没有专属 CSS。
- Blast radius 由收入合同层级列表、支出结算新建/查看和材料入库复合表单共同验证。

## Verification

- `make ci.local.iteration`：PASS，16 tests。
- form canvas、product page header、professional base field、canonical presenter、native section navigation、primitive/page-pattern 和严格类型检查：非零 PASS。
- 1088×791 产品样板及长值修复已完成用户截图复核。
- 候选 `b7f167b8873b0578850aee4e5b37fa3f082df7cd` 的 1440×960、390×844 明暗矩阵各 8 个样本均 `pass=true`、零写入、零错误；运行前后完整指纹逐字节一致。
- 1088×791、390×844 的正反向溢出浏览均验证首尾控制保持聚焦、连接且正确禁用；共享按钮状态由公开 prop 承接。
- 支出新建导航每组 5 个目标均唯一、完整可见且稳定避开吸顶区；只读详情逐个检查实际可见目标。
- 材料入库复合表单的日期、关系选择和文本域共 8 个适用控件在桌面/移动均无槽位或基线失败；未保存。
- 冻结准备、最终一次 Quick 与独立复核由最终 clean HEAD 的仓外 exact-head 证据记录，本草案不回填结果而改变候选。

## Evidence

- 报告：`docs/ops/iterations/tdesign_system_alignment_batch_a_20260914.md`
- 浅色矩阵：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-bound-light-b7f167b8/evidence-binding.json`
- 深色矩阵：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-bound-dark-b7f167b8/evidence-binding.json`
- 1088/390 焦点探针：`/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-section-browse-focus-b66f1640/summary.json`
- 首次浅色环境失败：`tdesign-alignment-final-light-1440-390-85b05110`，只作环境诊断，不冒充通过证据。

## Not included

- 保存、审批、权限、全角色、数据库、fixture、发布或部署验收。
- TDesign 升级、外壳/色板/活动页签、Dialog/Drawer 生命周期、低代码或新的模板引擎。
- `ScFormField` 帮助/错误关联；该项保留为独立 P0 交互批次。

## Risk and rollback

- 共享 CSS/组件影响面通过三类页面与复合表单控制；业务契约与写入链没有变化。
- 可按只读字段边界 → 导航 → 表面 → 排版逆序回退，无数据库回滚。

## Delivery status

`READY_FOR_REMOTE_DELIVERY_DECISION_AFTER_EXACT_HEAD_GATES`。远端 push、建 PR、Ready、合并、部署和发布均需独立授权；HEAD 漂移、冲突或新增阻断时停止。
