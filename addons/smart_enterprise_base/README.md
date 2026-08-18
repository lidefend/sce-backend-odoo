# smart_enterprise_base — 非安装契约桩（Test Fixture / Contract Stub）

> 2026-08-18 产品化审计（PRODUCTIZATION-AUDIT-001）曾将其判定为
> "不可安装残留"，经引用排查复核后修正定性，详见工作空间
> `docs/engineering/sce-backend-odoo-productization-audit.md` 的 R4 修订注记。

## 它是什么

本目录**故意**不是可安装 Odoo 模块：

- 无 `__manifest__.py`、无 `__init__.py` —— Odoo 安装器跳过它
- 仅含 `core_extension.py`，实现 smart_core 扩展点约定函数
  （`smart_core_extend_system_init` / `get_intent_handler_contributions`）

## 为什么存在

`addons/smart_construction_scene/tests/test_action_only_scene_semantic_supply.py`
通过 `sys.modules` 注入包路径并按文件路径加载本模块（见该文件
`enterprise_base_pkg` / `enterprise_base_core_extension` 相关行），模拟
"外部第三方扩展模块挂到 smart_core 扩展点" 的场景，用于验证：

- 企业开通引导（enterprise enablement）mainline 步骤的 scene/route 投射
- 扩展点对未注册 XMLID（`smart_enterprise_base.menu_*` / `action_*`）的
  容错降级

## 硬约束

- **禁止**给本目录补 `__manifest__.py` 或加入 Dockerfile COPY 白名单——
  它必须保持不可安装，否则会污染生产模块边界
- 修改 `core_extension.py` 的函数签名前，先跑
  `addons/smart_construction_scene/tests/test_action_only_scene_semantic_supply.py`
