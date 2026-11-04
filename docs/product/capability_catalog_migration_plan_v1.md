# Capability Catalog Migration Plan v1（CAP-01B · B5）

状态：候选方案，待架构复核；正式目录不修改

## 1. 迁移目标

从三套历史资产（`capability_catalog_v1.json` 42 条、`product_capability_matrix_v2.md` 63 条、
`product_menu_source.json` 131 条产品入口）收敛到一份“候选能力目录”，再经 CAP-01C 评估后形成正式目录。

## 2. 迁移步骤

1. 以 63 条矩阵为主集合，42 条目录为子集（42 ⊆ 63）。
2. 131 条产品菜单入口整体不迁入能力目录，保留在产品发布层。
3. 按 B2 分类执行：keep 12、defer 24、exclude 27。
4. keep 项直接进入候选目录；defer 项标记 `status=candidate_unverified`；exclude 项不进入。
5. 改名项建立兼容别名（本轮暂无改名，保留原 key）。
6. 不补发资格：所有候选 `qualification=unreleased`，待 CAP-01C。

## 3. 兼容映射

本阶段不删除任何旧 key；旧目录与矩阵保留为历史候选记录，新候选目录通过
`source_ref`（旧 key）回溯。未来正式目录发布后，旧文件标记为 historical，不直接删除。

## 4. 回退

候选目录为新增只读产物；正式目录、`product_menu_source.json`、能力资格均不变。
回退即删除候选目录文件，不影响任何产品运行。
