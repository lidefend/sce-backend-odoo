# 277 · BNVA-02C-02E-P4-02A · 安装失败根因

## 根因模块

`hr`（Odoo 官方标准模块，技术名 `hr`）。

## 位置

`/usr/lib/python3/dist-packages/odoo/addons/hr/README.md`（非 `__manifest__.py`；
`hr` 的 manifest 无 `description` 键，Odoo 回退读取 README）。

## 错误

README 第 48–49 行：

```text
Time Off Management        (19 字符)
-----------------          (17 连字符，短 2)
```

docutils 报 “Title underline too short: Time Off Management”，并伴随 “Unexpected
indentation”（ERROR/3，致命）导致 `-i sc_norm_engine` 退出 255。

## 结论

这是 Odoo 官方 `hr` 模块 README 的文档格式缺陷（Markdown 标题下划线过短），不是
本轮配置改动（identity_fields/section key）引入。

