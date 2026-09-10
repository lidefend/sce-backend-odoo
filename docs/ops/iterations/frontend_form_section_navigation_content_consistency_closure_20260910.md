# 表单章节导航内容一致性收口（2026-09-10）

## 结论

本批已完成并可冻结。导航名称现在绑定实际可见章节，不再由字段级 `semanticRole` 命中任意字段。关系字段、业务明细集合、附件与审计时间线的导航身份已分开。

Formal Product Layer 为 P0 通用前端 renderer，P4 仅承载守卫与只读浏览器证据。未修改契约、字段、权限、业务动作、隐藏章节或响应式容器基线。

## 候选身份

- 分支：`feature/form-page-structure-professionalization-v1`
- baseline：`2d5870009f08e6850e03e79a2fae2823bb152813`
- 最终候选：`dd98a5f0caf7fb052ffee012cccf73eed9d66475`
- 完整指纹：`933a4bc22371bb4647fe1615f2b6ba04d7fb265da3c0484a8a011997b2cb072f`
- 指纹路径：`artifacts/fingerprints/form_section_navigation_content_candidate_dd98a5f0.json`
- 路径数：7358

## 实现收口

- workspace 表单只从节点级语义产生普通章节入口，字段语义不再上升为章节身份。
- task 表单的概览、办理提示、基本信息和辅助区绑定实际 floorplan 容器；关系入口绑定实际 O2M/M2M 字段容器。
- 多个明细集合保留契约现有标签与 widget 身份；不使用页面模型名或字段名推测标题。
- many2one 关系字段不产生明细入口；附件依据现有组件解析和正式 relation descriptor 排除。
- “历史审计”只在实际 audit event 时间线存在时显示；普通录入人字段不会生成审计入口。
- 激活后按实际页头和导航边界校正落点，保证目标标题不被吸顶区遮挡。

## 验证证据

- `make verify.frontend.quick.gate`：PASS，包含新增 `native_section_navigation_test` 内容身份用例。
- 定向单元：字段级 relation/audit 角色不产生章节；隐藏节点不产生入口；多集合标题/身份不串位；附件组件与 descriptor 均不进入业务明细导航。
- 明色：`artifacts/local_dev_candidate/form_section_navigation_content/final_pass_light_1440_390/summary.json`，1440/390 共 8 个页面视口，32/32 导航内容断言 PASS。
- 暗色：`artifacts/local_dev_candidate/form_section_navigation_content/final_pass_dark_1088_320/summary.json`，1088/320 共 8 个页面视口，32/32 导航内容断言 PASS。
- 两组运行共 48 张首屏/中段/底部截图，mutationCount=0，errors/failures 为空。响应式容器、导航内部滚动和关系弹层边界检查仍为 PASS。

实际导航结果：

- 材料入库新建：“入库明细”定位到对应明细集合，附件不出现在明细导航中。
- 收入合同详情/新建：“合同明细”定位到对应集合。详情页有真实审计时间线，新建页不显示“历史审计”。
- 付款详情：当只读明细无可呈现内容时不生成空导航入口；实际审计时间线仍可到达。

## 边界与后续

本批不证明真实业务写入、多角色、acceptance、release 或生产发布。未执行 module upgrade、fixture reset、数据库操作、push、PR、merge 或 release。

响应式容器批次保持已冻结，本批没有重开美化。表单表达阶段已具备退出条件，等待独立审查后进入 PR 交付包整理。
