# 共享表单字段网格与对齐收口

日期：2026-09-10  
状态：`verification_pending`

## 范围与边界

- Formal Product Layer：P0 通用前端；P4 仅承载守卫、几何测量与截图。
- Layer Target：`frontend/apps/web` 的通用字段槽位、控件外框、native group 网格与查看态行盒。
- Module：共享表单渲染器、professional field controls 与 design-system adapter。
- Why Here：字段槽位宽度、控件投影和组缩进属于通用渲染机制，不属于合同、材料或付款业务语义。
- Why Not Elsewhere：未改契约、schema、字段、权限、动作、业务值或低代码配置；未按模型名或字段名推断重要性。
- 保留故意隐藏的后台章节标题，也保留前批已通过的章节导航和响应式容器。
- 未写数据库，未运行 fixture、acceptance、module upgrade、release，也未执行远程写入。

## 实现结果

1. `ProfessionalBaseFieldControl` 移除叠加在官方输入适配器外层的 8px 横向 padding；text、relation、date、number、textarea 均消费完整字段槽位。
2. `ScDateField` 公开语义根与共享选择、数字、文本域适配器统一为 `width: 100%`。
3. money、percentage、duration 的单位使用现有 `ScInput` suffix 插槽，不再以外部兄弟节点挤占输入框宽度；legacy monetary 路径同步使用同一公开插槽。
4. desktop native group 清除无意的 32px 横向递增缩进，移动端保留既有统一 gutter；章节标题与字段组消费同一列线。
5. 查看态的 business value、field row 与 compact readonly fact 使用稳定 22px 行盒，消除状态值与同排普通文本的 3px 顶部偏差。
6. 验证只测项目公开的 `data-semantic-component` 根，不依赖 TDesign 内部 DOM；detail collection 与允许横向比较的表格单独分类。

## 前后测量

测量对象为可见控件公开根的边界，容差 1px。

| 收入合同新建，1440px | 修复前 | 修复后 |
|---|---:|---:|
| 合同标题 `subject` 相对槽位左右缩进 | 8px / 8px | 0px / 0px |
| 工程类别 `engineering_category_text` 相对槽位左右缩进 | 8px / 8px | 0px / 0px |
| 业务分类 `business_category_id` 相对槽位左右缩进 | 0px / 0px | 0px / 0px |
| 项目名称 `project_id` 相对槽位左右缩进 | 0px / 0px | 0px / 0px |
| native group 跨组左右边界 spread | 32px / 32px | 0px / 0px |

最终收入合同新建在 1440、1088、390、320 下每个视口均测得 24 个可编辑控件，frame failure 为 0、row baseline failure 为 0、强制跨组 grid spread 为 0px。付款查看态最初复现状态值比同排文本低 3px；最终桌面与移动均为 0 个 row baseline failure。

## 证据索引

- 修复前候选：`3371fc95902bfe82bf59b5dfd0643f02b8b4118a`
- 浏览器产品候选：`d43e9e75d70535c2093ec9ae0ce10f82fe5324bc`
- 已验证实现与 inventory HEAD：`32b94b8cc9dac4a9d0656b0bfe4e97e43caef8dd`
- 完整已验证指纹：`233948900bef0804ee7b9f35c876b04c015043d186f3686f9916310aea2c44ee`，7360 paths。
- 修复前测量与参考线：`artifacts/local_dev_candidate/form_field_grid_alignment/before_guided_light_1440_390/summary.json`
- 最终明色：`artifacts/local_dev_candidate/form_field_grid_alignment/final_pass_light_1440_390/summary.json`
- 最终暗色：`artifacts/local_dev_candidate/form_field_grid_alignment/final_pass_dark_1088_320/summary.json`
- 两组最终摘要均为 `pass=true`、8 个路由视口、`mutationCount=0`、errors/failures empty；合计 16 个路由视口与 64 张首屏、中段、底部、对齐参考线截图。
- 浏览器候选之后仅刷新四份派生 inventory JSON；产品树未变化。最终 `make verify.frontend.quick.gate` PASS，官方设计清单为 internal vendor selector 0、visual literal gap 0、unknown token override 0。

## 结论

本批实现与本地证据已完成，候选服务已停止。结论仅覆盖四个代表表单的共享字段网格、控件外框和行基线，不宣称全业务、真实写入、多角色、acceptance 或 release 通过。状态保持 `verification_pending`，等待独立复核决定是否退出表单表达阶段。
