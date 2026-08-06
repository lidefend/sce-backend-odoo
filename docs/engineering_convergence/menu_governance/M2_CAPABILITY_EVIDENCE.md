# M2：能力、权限、菜单、action、路由证据框架

## 已完成的静态链

生成资产账逐项保留：

```text
menu XML ID → 声明/patch 来源 → parent XML ID
→ group XML ID → action XML ID → action 类型/res_model
→ 静态引用状态
```

这条链只能证明源码声明和本模块内引用，不能证明当前用户可见、记录权限充分、页面可加载或 URL 可达。`capability_key`、角色和运行时字段因此保持未决。

## 后续受控采样契约

运行时采样只有同时满足下列条件才可启动：

1. 从环境变量或受控配置取得 base URL、数据库别名和身份引用；禁止写入账号、密码、固定 action/menu ID。
2. 数据库为只读验收角色或事务回滚夹具，不执行提交、审批、删除、配置保存。
3. 端口、服务、浏览器 profile 和证据目录持有独占租约；与其他专题零共享。
4. 服务端运行 SHA 与本报告精确 SHA 一致。
5. 角色、公司与菜单 contract 在同一会话采样，并记录时间、工具版本、响应摘要和脱敏状态。

## 结构化证据单元

每个未来证据单元至少包含：

| 字段 | 含义 |
| --- | --- |
| `product_sha` | 服务端精确提交 |
| `environment_ref` | 不含凭证的环境标识 |
| `dataset_ref` | 可重放的非敏感数据集标识 |
| `role_ref` / `company_ref` | 角色及公司语义引用 |
| `menu_xmlid` / `action_xmlid` | 静态资产键 |
| `capability_key` | 经产品确认的能力键 |
| `runtime_visible` | 运行态最终导航事实 |
| `permission_consistent` | 菜单可见性与 action 权限一致性 |
| `route` / `http_status` | 真实路由和结果 |
| `title` / `active_menu` | 页面身份一致性 |
| `evidence_sha256` | 原始脱敏证据摘要 |

## 标杆与角色任务证据

营销页只登记“能力分类启示”，不得用来证明真实导航层级。后续每条标杆观察必须记录官方来源、采样日期、产品/页面、可见角色、观察、不适用理由和证据引用。BOSS/PUMA 真实会话与外部成熟产品参考必须分栏，不得互相冒充。

角色任务证据优先使用脱敏日志和真实任务频率；没有事实前，不以开发者主观判断填写 `audience_roles` 或把高频动作提升为全局菜单。
