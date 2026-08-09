# Action Surface Renderer Registry v1

## 目标

所有集合页面必须遵循同一条链路：

`Odoo native view -> backend normalized contract -> collection presentation semantic -> renderer registry -> renderer host -> shared design components`

`ActionView` 不得按模型、菜单、XML ID、行业名称或专用组件写渲染分支。

## 注册模型

每个渲染语义必须登记：

- `semantic`：后端契约给出的稳定语义；
- `requestedRendererKey`：该语义最终应使用的正式渲染器；
- `activeRendererKey`：当前实际执行的渲染器；
- `status`：`ready / fallback / unsupported`；
- `outlet`：由标准集合面或注册组件承载；
- `reasonCode`：降级或不支持时的稳定原因码。

当前 ready：`table`、`card`、`workflow_board`、`hierarchy_browser`。

当前纳入架构但尚未实现：`pivot`、`graph`、`calendar`、`gantt`、`activity`、`dashboard`。它们必须登记为 `fallback`，统一使用 `core.readable_records`，直到各自正式渲染器具备契约测试和浏览器验收后切换为 `ready`。

## 硬约束

1. 未注册语义必须以 `ACTION_SURFACE_RENDERER_NOT_REGISTERED` 失败关闭。
2. 专用渲染组件只能进入集中组件映射，`ActionView` 不得直接导入。
3. 渲染组件只接收契约、标准数据源、导航和动作适配；不得读取模型名、XML ID、菜单文案推断业务结构。
4. 新增复杂视图时必须更新注册表、组件映射、契约 schema、单元测试和浏览器验收。
5. `fallback` 是显式产品状态，不得伪装成 `ready`，也不得改变后端业务事实。
6. 页面和业务 block 不得直接创建原生 `<table>`；表格结构统一由 `ScDataTable` 基础组件承载。

## 演进方式

实现某个复杂视图时，仅把该语义的 `activeRendererKey` 指向新增通用组件，并将 `status` 改为 `ready`。页面入口、导航、模型视图和权限链路保持不变。
