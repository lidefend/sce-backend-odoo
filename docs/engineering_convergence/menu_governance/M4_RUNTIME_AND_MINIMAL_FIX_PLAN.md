# M4：运行时准入与最小修复计划（生成文件）

> 由 `scripts/verify/menu_governance_inventory.py` 生成，禁止人工修改。

## 当前裁决

- 状态：`BLOCKED_ON_RUNTIME_EVIDENCE`
- 冻结资产：22
- 重复 `<menuitem>`：16
- 技术/临时命名：4
- 第四级路径：2
- 菜单 XML 修改：否
- 数据库写入：否
- 浏览器/运行时事实声明：否

## 资源准入

- `18094` 属于当前列表专题，缺少独占租约，拒绝使用。
- `8070/18081` 的挂载源码 SHA 与冻结基线不同，且运行时身份端点缺失，拒绝作为证据。
- 后续依赖 env-portability 提供数据库、服务、浏览器 profile 和证据目录的统一独占租约。

## 最小修复边界

- 16 个重复声明仅允许改为显式 `ir.ui.menu` patch 或在运行时等价证明后移除后置重声明；不得重建 XML ID。
- 4 个命名候选仅改变 `name`，不改变 action、groups、sequence 或权限。
- 2 个第四级候选仅改变 parent，使业务深度回到三级；空容器的后续处置另行评审。
- 所有候选在运行时角色、路由、页面身份和兼容证据完成前均保持 `not_applied_runtime_evidence_required`。
