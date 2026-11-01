# 187 · BNVA-02B-02B · 验收

## 七个裁定

1. 结构校验进入发布入口：是（`_append_published_version` 新版本路径）。
2. Formal 失败关闭：是（无 legacy 声明的 ERROR 阻断）。
3. Legacy Compatible 明确范围：是（5 个必填键）。
4. Unclassified Historical 保持未分类：是（NOT_VERIFIED 不自动 Formal）。
5. 版本与校验摘要绑定：gate 存入 `snapshot_json._publication_gate`。
6. 历史配置保持兼容：未变更重发不阻断；restore 剔除 gate。
7. 具备进入 02B-02C：是——门禁与兼容通道已就绪，可逐项治理历史配置。

