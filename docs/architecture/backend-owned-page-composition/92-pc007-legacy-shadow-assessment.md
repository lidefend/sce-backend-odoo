# 92 · PC-007 Legacy Shadow Assessment

## 结论

PC-007 FAIL 是真实的迁移就绪信号，不是 Guard 误报。

## 机制

`useContractV2ShadowDiagnostics.ts` 在正式页面以 shadow 方式并行运行
`buildLegacyLayoutNodes`，渲染 legacy 布局并统计与 V2 的字段重叠。主组合已由
`standardFormComposition` 决定为 official-standard-form，但 shadow 仍是运行时
对 legacy 的消费。

## 两个入口的区分

- View 1776（Action 590，项目概览）：V2 结构完整（11 组 / 33 归属 / 5 slots），
  主组合 official-standard-form；shadow 曾观测到 79 个字段重叠。
- View 944（标准 project.form，`/f/project.project/1` 解析到它）：仍走
  legacy-form-section（无 V2 结构），shadow overlap=0。

两者不可合并为同一页面：590/1776 是 formal 结构入口，652/944 是历史结构入口。

## 收缩路径

1. shadow 的使命是跟踪 overlap 收敛，当 V2 完全覆盖 legacy 字段时退役。
2. 当前 formal 入口仍有 79 个 overlap，说明 V2 结构尚未覆盖全部 legacy 字段。
3. 收缩动作 = 对 formal 页面关闭 shadow 渲染（或 overlap 归零后整体退役）。

## 工作清单

79 个重叠字段需从 View 1776 的正式入口（菜单/Action 590）实际渲染时枚举，
`/f/project.project/1` 会解析到 View 944，不能用于该清单。

## 边界

这是 Phase 5 Legacy 收缩的前置工作；不改变权限、不改业务配置；shadow 作为
迁移诊断保留到 overlap 归零。
