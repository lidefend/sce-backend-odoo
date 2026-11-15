# Odoo-Native Capability Explorer 只读 API 契约 v1

状态：后端只读 API 已实现，前端与写操作未实现

实现基线：`d176e2fd67fec87257114b207cec655ec8fa6e9d`

运行观测：`sc_demo@2571346af`

## 1. 分类验证结论

对 282 个原生业务入口的只读验证结果：

| 分类事实 | 数量 |
|---|---:|
| 业务领域由现有场景绑定权威确定 | 75 |
| 仅有中心、业务领域未确定 | 207 |
| 多场景歧义 | 0 |
| 原生一级中心可确定 | 282 |
| 技术可选 | 282 |

75 个权威分类来自现有 `sc.product.scenario.entry` 的 17 个场景：

| scene key | 入口数 |
|---|---:|
| `project.management` | 13 |
| `payment.capital` | 11 |
| `tax.management` | 9 |
| `contract.performance` | 7 |
| `administration.office` | 7 |
| `analytics.decision` | 6 |
| `accounting.management` | 3 |
| `cost.budget` | 3 |
| `labor.management` | 3 |
| `material.management` | 3 |
| `governance.organization` | 2 |
| `procurement.supplier` | 2 |
| `subcontract.management` | 2 |
| `equipment.management` | 1 |
| `quality.management` | 1 |
| `receipt.payment.ledger` | 1 |
| `safety.management` | 1 |

207 个未分类入口仍保留原生中心，例如项目中心 55、财务中心 54、合同中心 20、
报表中心 19、产品配置 17。中心只是浏览提示，不自动升级成业务领域。

## 2. 分类依据优先级

分类按以下顺序执行，低优先级证据不能覆盖高优先级事实：

| 优先级 | 证据 | 可回答的问题 | 结果 |
|---|---|---|---|
| 1 | `sc.product.scenario.entry` | 入口已经被哪个正式业务场景引用 | 可给出权威 `business_domain` |
| 2 | 当前产品发布策略 `group_key/group_label` | 入口属于哪个发布中心 | 只给出 `release_center` |
| 3 | 原生一级 Menu XMLID | Odoo 原生菜单属于哪个中心 | 给出稳定 `center_key` |
| 4 | 模型、View、ACL、Record Rule、模块 | 入口来自什么技术载体 | 只补充详情，不推断业务领域 |
| 5 | 无稳定证据 | 无法可靠判断 | `business_domain=unclassified` |

历史 63 项 UI registry、中文菜单名和模型名前缀不作为自动分类依据。

正式产品菜单策略中虽然存在更细的静态 `product_domain_label`，但当前 active
release snapshot 没有携带该字段，因此本版 API 不把它作为运行时分类事实。

## 3. Intent 审查与实现

现有 Intent 不复用：

- `capability.describe`：读取旧 `sc.capability`，不是 Odoo 原生发现。
- `capability.visibility.report`：同样基于旧 `sc.capability`。
- `product.configuration.capability.catalog`：描述配置工作台功能，不是平台能力浏览器。

已实现三个只读 Intent：

- `platform.capability.explorer.list`
- `platform.capability.explorer.detail`
- `platform.capability.explorer.diagnose`

名称表达的是平台能力浏览，不沿用“capability catalog”以免再次与产品配置功能混淆。

## 4. List 契约

请求：

```json
{
  "query": "合同",
  "filters": {
    "center_keys": [],
    "business_domain_keys": [],
    "scene_status": "unbound",
    "release_states": ["released"],
    "draft_selectable": true,
    "classification_confidence": ["center_only", "unclassified"]
  },
  "limit": 50,
  "offset": 0,
  "sort": "center_sequence:asc,label:asc,menu_xmlid:asc"
}
```

约束：

- `limit` 范围 `1..100`，默认 50。
- MVP 使用稳定 `offset` 分页，排序必须包含 `menu_xmlid` 作为最终 tie-breaker。
- List 与 Detail 都接受可选 `expected_catalog_token`；提供且与当前 token 不一致时
  返回 `409 CATALOG_STALE`，不得混用新旧目录。
- `query` 只搜索服务端声明字段：label、menu XMLID、action XMLID、模型、中心、场景。
- 不接受任意 ORM domain、模型名或 SQL 排序。
- 分类候选超过一个时不能自动选择。

响应：

```json
{
  "meta": {
    "schema": "platform.capability.explorer.list.v1",
    "generated_at": "2026-11-15T00:00:00Z",
    "runtime_database": "sc_demo",
    "source_revision": "2571346afc8c69cea20e32fcba36082c949cf825",
    "catalog_token": "sha256:...",
    "language": {
      "code": "zh_CN"
    },
    "total": 282,
    "filtered_total": 207,
    "offset": 0,
    "limit": 50,
    "next_offset": 50,
    "has_more": true,
    "freshness": "request_time_projection"
  },
  "facets": {
    "centers": [],
    "business_domains": [],
    "scene_status": {"bound": 75, "unbound": 207},
    "release_states": {"released": 274, "unknown": 8},
    "classification_confidence": {
      "authoritative_scene_binding": 75,
      "center_only": 207,
      "unclassified": 0
    }
  },
  "rows": []
}
```

列表行：

```json
{
  "entry_ref": {
    "menu_xmlid": "smart_construction_core.menu_example",
    "action_xmlid": "smart_construction_core.action_example"
  },
  "label": "示例入口",
  "origin": {
    "module": "smart_construction_core",
    "model": "project.project"
  },
  "center": {
    "key": "smart_construction_core.menu_sc_project_center",
    "label": "项目中心"
  },
  "business_domain": {
    "key": null,
    "label": null,
    "confidence": "center_only",
    "reason_code": "NO_SCENE_BINDING"
  },
  "scene_usage": {
    "bound": false,
    "count": 0
  },
  "release_state": "released",
  "draft_eligibility": {
    "selectable": true,
    "blockers": []
  },
  "scene_assignment": {
    "assignable": true,
    "blockers": []
  },
  "product_qualification": {
    "preview": "not_verified",
    "standard": "not_verified"
  }
}
```

## 5. Detail 契约

请求使用稳定复合身份：

```json
{
  "entry_ref": {
    "menu_xmlid": "smart_construction_core.menu_example",
    "action_xmlid": "smart_construction_core.action_example"
  },
  "expected_catalog_token": "sha256:..."
}
```

`expected_catalog_token` 可选。若提供且当前 token 不同，返回 `409 CATALOG_STALE`，
避免前端把旧列表与新发展开结果混用。List 与 Detail 共用同一规则。

详情在列表字段基础上返回：

```json
{
  "native_facts": {
    "action_type": "ir.actions.act_window",
    "view_modes": ["tree", "form"],
    "field_count": 235,
    "view_count": 42,
    "acl": {
      "row_count": 10,
      "group_xmlids": []
    },
    "record_rule_count": 10,
    "module_version": "17.0.0.182",
    "module_dependencies": []
  },
  "scenario_usage": {
    "bound": true,
    "scenarios": []
  },
  "release": {
    "state": "released",
    "center": {}
  },
  "classification": {
    "source": "sc.product.scenario.entry",
    "candidates": []
  }
}
```

ACL 组和 Rule 只返回已授权摘要，不返回 Rule domain、用户列表或业务记录。

## 6. Diagnose 契约

主目录只返回具有稳定 Menu + Action XMLID 的入口。诊断还支持按
`menu_xmlid` 读取当前 Registry 中的入口，即使该入口没有 Action、Action
类型不支持或身份不完整，也不会因此进入可场景化主目录。

诊断返回可机器消费的原因码：

- `NATIVE_IDENTITY_INCOMPLETE`
- `MODULE_NOT_INSTALLED`
- `ACTION_NOT_FOUND`
- `ACTION_TYPE_UNSUPPORTED`
- `MENU_ACTION_MISMATCH`
- `MODEL_NOT_FOUND`
- `NO_SCENE_BINDING`
- `AMBIGUOUS_SCENE_BINDING`
- `ENTRY_NOT_RELEASED`
- `MATURITY_EVIDENCE_MISSING`
- `XMLID_INVALID`
- `XMLID_NOT_FOUND`
- `XMLID_AMBIGUOUS`
- `RELEASE_CENTER_AMBIGUOUS`

诊断结果必须分栏。顶层兼容字段可保留，但不得把不同栏位互相推导：

```json
{
  "native_valid": true,
  "draft_selectable": true,
  "scene_assignable": true,
  "entry_published": true,
  "preview_qualified": "not_verified",
  "standard_qualified": "not_verified",
  "blockers": []
}
```

- `draft_selectable` 只表示原生 Menu/Action/模型事实允许进入场景草稿。
- `scene_assignable` 只表示场景事实提供者可接受引用，不表示场景或产品已经合格。
- `preview_qualified` 与 `standard_qualified` 必须来自各自资格事实；默认是
  `not_verified`，不能由入口发布状态或技术可选状态推导。
- 入口发布状态单独返回，Release 状态不能代表成熟度。

## 7. 权限模型

查询必须由后端授权，不能依赖前端隐藏：

- 当前实例目录：`user_is_tenant_config_admin(user)` 或平台控制管理员。
- 跨实例全局目录：只允许具有平台控制实例身份、平台管理员组和
  `platform-admin` audience 的 `user_is_platform_control_admin(user)`。
- 查询自身不得因为使用 `sudo()` 读取菜单、ACL 或 Rule 元数据，就绕过上面的入口授权。
- tenant 查询只能返回当前数据库身份；没有目标 tenant 注册和授权时不得跨库。
- ACL 组、Rule 数量和模块依赖属于安全元数据，只向通过上述谓词的管理员返回；
  普通业务用户不调用该 Intent。
- 目录查询不等于业务记录读取权限，不返回模型业务行。
- Explorer 的租户查询不得打开其他数据库 Registry，也不得在其他数据库创建
  `SUPERUSER_ID` 环境。平台发布库与当前库不一致时，Release authority 必须返回
  `PLATFORM_RELEASE_DB_ISOLATED`，入口状态保持 `unknown`。
- 只有当前运行库就是平台发布库时，平台控制实例才通过现有平台发布服务读取
  Release Snapshot。

未来若需要“平台能力运营员”与“平台系统管理员”分离，应新增独立 P0 权限；本轮不实现。

## 8. 数据新鲜度与缓存

MVP 不持久化发现结果：

- 每次查询从当前 Odoo registry 和数据库实时投影。
- `generated_at` 表示本次投影时间。
- `catalog_token` 覆盖当前数据库、语言环境、安装模块及依赖、Menu/Action 身份和
  Action 目标、Menu 层级与顺序、模型和字段、View 关联、ACL、Record Rule、
  场景绑定、发布状态、发布中心、资格事实、活动发布快照身份、
  `scene_authority_available`、`release_authority_available`、Provider 状态、
  root/fallback 诊断、XMLID 歧义、Release Center conflicts 和候选 Menu 诊断事实。
- List、Detail 与 Diagnose 必须在同一请求内绑定同一 token；不能只让 Detail 校验 token。
- 不建立跨请求能力缓存；如需请求内 memo，只能按当前 cursor/instance 隔离。
- 模块升级、菜单/动作修改、场景绑定和发布快照变化必须自然反映到下一次查询。
- XMLID 多重映射不得任意选择；无法形成唯一 Menu/Action 身份时 fail-closed。

## 9. 性能边界

- 原生入口继续复用 `RuntimeCapabilityCatalogService`。
- Menu、Action、Group 的 XMLID 使用批量预取，禁止逐入口调用 `get_external_id()`。
- 模块、模型、字段、View、ACL、Record Rule 按本次目录涉及的身份批量读取。
- List 只返回轻量行；Detail 才构造 View/ACL/Rule/组等技术摘要。
- Diagnose 复用同一次完整投影，不另起一套发现逻辑。
- 每次响应记录 SQL 数、原生投影、元数据、贡献、总投影和序列化耗时。
- 请求结束即释放，不建立跨请求持久化缓存。

## 10. 本轮不做

- 不新增 ORM 表。
- 不实现前端页面。
- 不实现“加入场景草稿”写操作。
- 不计算或补发 Preview/Standard 资格。
- 不修改现有业务模型、ACL、Record Rule、场景数据或发布状态。
- 不修改、推送或合并 PR #888 及本分支之外的发布对象。
