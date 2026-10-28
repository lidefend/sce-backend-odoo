# FEPC-13I-I1a：声明与 occurrence 编译

状态：已按所有者最新指令暂停，转入 FEPC-13M。仅留下前置核对；未修改 schema、编译器或任何产品代码。以下组织方案为暂停前观察，不是当前推荐实施路径。

基线：`e0ce73b47b800da181a224913937720d9c5d77ba`。GitHub main 与本地一致、初始工作区干净；FEPC-13I-00 的 16 项源文件 SHA-256 全部匹配。复用 FEPC-13D/R1 与 FEPC-13R，不访问 Demo。

归属：P0 smart_core 通用声明/编译；测试入口为 P4。不是行业特例或前端推断，不修改业务数据。

## 版本资产前置核查

当前 schema、enum registry、`contract_schema_declaration_sync.py` 与 `contract_lifecycle.py` 是单一版本绑定。现有 schema 生命周期定义固定当前版本；修改该文件即改变旧响应的 schemaSha256。不能把扩大原文件校验范围当成旧协议字节不变。

最小组织方案：原 schema/注册表/生成链保持不动，在同一协议目录下使用独立版本资产。新资产仅用于显式版本的离线校验，不接入 assembler 或 seal；后续 I1b 才负责选择器。新旧资产均应具备独立固定指纹，不能通过修改旧 additionalProperties 实现兼容。

验收仍需证明：严格声明、唯一绑定、布局变更失效、来源与权限、旧输出不变。当前这些新测试为 not_run，不代表已具备实现支持。
