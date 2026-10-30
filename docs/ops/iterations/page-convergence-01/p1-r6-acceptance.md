# PAGE-CONVERGENCE-01 / P1-R6 · 页头三视口真实 DOM 验收

结论：P1 页头身份区去重已通过真实 DOM 验收，三视口全部 PASS，P1 正式关闭。

## 一、运行身份

- 分支：`feature/page-convergence-01`
- HEAD：`d363c01ee0f71cae686da42dbc574bdfbf4d8028`
- 本地受管库：`sc_dev_demo`（`127.0.0.1:18081` 的 `/t/demo` 入口路由到它；`sc_demo` 是远程日常
  服务器库，不参与本轮本地验收）
- 数据库 UUID：`551b2b2e-cba4-11f1-82d4-2ae01a997ff0`
- 服务进程：`2026-10-30T07:58:40Z` 启动（升级后新进程）
- 服务 SHA：`d363c01ee…`（后端从 `/mnt/source-addons` 工作树挂载服务）
- 前端：vite 开发源（`127.0.0.1:5174`，entry namespace `demo`），分支前端与 main 无差异
- 页面身份：action 590「项目台账」、form view 1769、record 21（城北新区安置房项目，在建阶段）、
  账号 pm1（uid 8）、company 1

## 二、三视口验收结果

| 检查项 | 1440 | 1024 | 390 |
| --- | --- | --- | --- |
| 唯一项目主标题（h1 数量=1） | PASS | PASS | PASS |
| ProductPageHeader 主标题 | PASS | PASS | PASS |
| 页头无 name 字段 | PASS | PASS | PASS |
| 页头无 operation_strategy 字段 | PASS | PASS | PASS |
| 页头含 business_nature | PASS | PASS | PASS |
| 项目身份组保留 name | PASS | PASS | PASS |
| 业务主体与项目属性组保留 operation_strategy | PASS | PASS | PASS |
| 全页「经营方式」出现次数 | 1 | 1 | 1 |
| 全页「项目名称」标签出现次数 | 1 | 1 | 1 |
| 无横向溢出 | PASS | PASS | PASS |

页头字段节点（三视口一致）：`project_code / business_nature / user_id / manager_id / owner_id /
project_type_id / write_date`，与后端新契约完全一致。

## 三、DOM 关键事实

- `h1` 三视口均唯一，文本为项目名「城北新区安置房项目（在建阶段）」，即 ProductPageHeader 主标题。
- `sc-project-overview__header` 无 `sc-project-title`，无「项目名称」标签，无「经营方式」字段。
- 「项目名称」标签只在「项目身份」分组出现 1 次。
- 「经营方式」字段只在「业务主体与项目属性」分组出现 1 次。
- 控制台错误：0。
- 操作区：返回 / 更多操作 / 项目设置 均可见未禁用，未挤压主标题。
- 几何：1440 h1 `w=705 h=32`；1024 h1 `w=305 h=64`（合理换行）；390 h1 `w=351 h=32`，均无溢出。

## 四、证据

- `.runtime/page-convergence-01/p1-r6/p1-r6-runtime-identity.json`
- `.runtime/page-convergence-01/p1-r6/p1-r6-dom-1440.json`
- `.runtime/page-convergence-01/p1-r6/p1-r6-dom-1024.json`
- `.runtime/page-convergence-01/p1-r6/p1-r6-dom-390.json`
- 截图：`.runtime/page-convergence-01/p1-r6/p1-r6-{1440,1024,390}.png`

## 五、P1 关闭判定

P1 页头身份区达到最终通过标准。根因（升级后服务进程未加载新代码）已定位并随进程重启消除；
资产匹配与 source token 失效机制经 P1-R5 验证工作正常，不删除历史资产、不修改匹配算法、不扩大缓存清理。

下一步进入 P2：六组基本信息专业化布局。

## 六、模块升级后的运行时验收顺序（固化为工程标准）

1. 升级前生成配对快照。
2. 执行受管模块升级。
3. 确认数据库视图已更新。
4. 重启或通过受管方式确认 Odoo 进程加载新代码。
5. 重新读取运行时源码指纹和契约身份。
6. 最后执行浏览器验收。

数据库升级成功不等于运行时升级完成；配置发布、契约编译、持久化资产与运行时进程是四个不同生命周期。
