# 205 · BNVA-02B-02C-02A · 最终裁定

1. 应 noupdate=1 的种子：不可变默认 + 生成基线（共约 18 + 稳定默认集合）。
2. 必须受控升级的种子：entry_semantic_surface / native_semantic_surface 结构模板。
3. 是否需要独立 migration runner：是，复用版本快照 + change_set，不新增平行 Schema。
4. 用户覆盖免于代码升级影响：已成立（tenant_lowcoding 独立公司级配置，不参与种子迁移）。
5. 多条 active 治理：不唯一约束，增加同精确作用域重复的追溯诊断。
6. 具备进入 02C-02B：是——按分类先建立受控迁移机制，再切换 noupdate。

## 约束

本轮只读设计；未修改 XML/noupdate/配置/升级逻辑，未执行生产升级。

