# 93 · PC-007 Frontend Shadow Contraction

## 收缩点

`frontend/apps/web/src/pages/contractForm/useRecordFormFieldSchemas.ts:106`：

```ts
const layoutNodes = computed(() => buildLegacyLayoutNodes({ ... }));
```

`layoutNodes` 是 legacy 布局，被两类消费者使用：

1. shadow 诊断（`useContractV2ShadowDiagnostics.ts`）：统计与 V2 的字段重叠。
2. legacy FormSection 渲染（部分可见）。

## 观测事实（正式入口 View 1776）

```text
legacyFormSection 总数 22，可见 5，隐藏 17
nativeTree 总数 23，可见 5
```

可见的 5 个 legacy 节点与 native 树是并行影子，不是主结构；主组合是
official-standard-form。

## 收缩原则

1. 不得简单 `return []`——那会同时抹掉 shadow 诊断，隐藏 79 个 overlap 这一
   真实迁移信号，违反“Shadow 不隐藏真实问题”。
2. 正确收缩是：formal 页面不再用 legacy `layoutNodes` 作为渲染输入（可见
   legacy 归零），但保留 shadow 诊断的 overlap 统计，直到 overlap 归零。
3. 需要把“渲染用 legacy 布局”与“诊断用 legacy 布局”分离，而不是共用一个
   `layoutNodes`。

## 最小实施

- 给 legacy 渲染路径加 page-class 门控：`pageComposition.class === 'formal'`
  时，渲染侧不消费 `layoutNodes`，但诊断侧继续计算 overlap。
- 门控点从 `v2ContractStore.snapshot.pageComposition.class` 读取，与后端
  assembler 的 `formal` 分类一致。
- 需要前端重建（Vue）并跑浏览器复核，确认可见 legacy 归零、overlap 仍可读。

## 已实施

`useRecordFormFieldSchemas.ts` 的 `layoutNodes` computed 已加 formal 门控：

```ts
const pageClass = String((context.v2ContractStore.value as any)?.snapshot?.pageComposition?.class || '').trim();
if (pageClass === 'formal') return [];
```

- 79 overlap 诊断依赖 `formFields`（V2 字段映射），不依赖 `layoutNodes`，
  故门控不隐藏 overlap。
- 前端 Vite 服务 200、无编译错误；View 944（legacy）不受影响。
- DOM 级复核（View 1776 可见 legacy 归零）需经 项目中心 → 项目台账 → 打开项目
  的真实菜单路径，尚未完成自动化。

## 边界

这是 Phase 5 Legacy 收缩的前端部分；不改权限、不改业务配置、不改后端结构。
shadow 诊断保留到 overlap 归零后整体退役。
