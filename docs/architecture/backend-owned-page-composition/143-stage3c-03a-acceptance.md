# 143 · BNVA-019 Stage 3C-03A · 验收

## 裁定

READY

## 回答

1. Assembler 当前承担 —— 契约归一、布局归一、业务结构投影应用、pageComposition、
   最终组装；不再解析原生视图。
2. 重复业务推导 —— 已无「从 arch 重推导」；仅剩旧启发式 ownership 兜底（仅旧路径）。
3. 应迁移到 Adapter —— 容器语义名称启发式、旧 ownership 兜底。
4. 必须留在 Assembler —— 契约归一与最终组装。
5. 兼容性依赖 —— 旧启发式页面依赖 `_page_composition_contract` 兜底，不能直接删。
6. 3C-03B 最小范围 —— 迁移容器语义标准化到 Layout Adapter，暂缓 ownership 兜底。
7. 是否具备进入 03B —— 具备。

