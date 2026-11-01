# 247 · BNVA-02C-02A-R · 产品默认配置与用户覆盖关系

沿用 ARCH-DECISION-005 + Copy-on-Write 研究：

- 产品默认：`product_release` 种子（company_id=False）。
- 用户覆盖：`lowcode` 公司级配置（tenant_lowcoding layer=40 覆盖 product layer=20）。
- 运行时：Resolver 合并，标量 last-wins、列表追加、隐藏并集。
- 撤销覆盖 = 停用/删除覆盖，回落产品默认。

产品升级演进产品默认；用户覆盖独立；两者不互相写入。

