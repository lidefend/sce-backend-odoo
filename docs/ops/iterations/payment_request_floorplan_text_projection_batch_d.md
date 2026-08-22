# 付款申请黄金页面 Batch-D：语义区文本去重

## 边界与结果

- Formal Product Layer：P0 通用 Product Floorplan 投影。
- Layer Target：`canonicalFormFloorplan.ts`，不修改契约、领域字段或 UI kit。
- Why Here：无语义角色的 Native 静态说明此前随祖先节点同时进入 task/risk 投影，形成重复产品文案。
- Why Not Elsewhere：不删除后端事实，不按付款申请模型或中文内容过滤。
- Blast Radius：所有 semantic readonly Floorplan；只有与目标角色匹配的节点文本可进入该语义区，字段身份和值保持不变。

## 验证

- canonical presenter：PASS，52 cases；新增跨 task/risk 的未分配静态文本不重复断言。
- scene component bridge：PASS，38 cases；guard PASS，63 checks。
- strict typecheck 与 `make local.dev.frontend`：PASS。
- `make verify.local.dev.payment_request.floorplan.readonly`：PASS；10 个语义区、无伪主动作、390px overflow=0、第二模型复用及业务指纹不变。
- 最终桌面截图确认账户静态说明不再重复，权威阻断原因和下一步事实仍保留。
