# 128 · BNVA-019 Stage 3C-01 · 验收

## 裁定

READY_WITH_CONSTRAINTS

## 回答八个问题

1. 还有多少真正重复的原生解析 —— Form 主 arch 已收敛为 1 次；剩余为不同视图类型
   与子视图的合法解析，以及 fallback/onchange/draft/validation 的独立用途。
2. 还有多少独立结构事实来源 —— 两个投影（Canonical Model + Layout DOM）是设计内
   的职责分离；真正的「重复事实」是 fallback 与特定用途 arch 直读。
3. 哪些旧 Parser 可安全迁移 —— fallback / onchange / draft / validation。
4. 哪些解析必须保留 —— tree/kanban/search/子视图等独立 arch。
5. 请求缓存是否生命周期安全 —— 否；`id(cursor)` 复用风险未消除，需 3C-02 落地
   显式 request-scoped carrier。
6. Stage 3C-02 是否具备启动条件 —— 具备，但第一项必须先修复缓存生命周期。

## 约束

- 本轮只读，未删除旧 Parser，未改公开 Schema / 业务 / 权限 / 前端。
- 缓存有界 LRU 保留，不扩大容量掩盖生命周期问题。

