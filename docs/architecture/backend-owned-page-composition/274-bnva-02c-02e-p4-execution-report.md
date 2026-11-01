# 274 · BNVA-02C-02E-P4 · 执行报告（失败，停止）

## P4-01 凭证重建 — 成功

`make local.clean.rebuild` 已生成 `.env.local.clean`（mode=600），未输出任何明文。
只删除/重建了 `sc_local_clean_db_data / redis_data / odoo_data` 三个卷，未触碰其他环境。

## P4-02 全新安装 — 失败

模块安装 `-i sc_norm_engine --without-demo=all` 失败（Error 255），错误为模块描述
reST 解析错误：

```text
<string>:38: (ERROR/3) Unexpected indentation.
<string>:49: (WARNING/2) Title underline too short.  "Time Off Management"
```

## 失败分类

`environment_defect / baseline_evidence_defect`：安装链中某模块（“Time Off
Management”，疑似 Odoo 标准 hr_holidays 或 OCA 模块）的 `__manifest__.py`
`description` 存在 malformed reST，docutils 解析失败导致安装中断。

与本轮配置改动无关（本轮只改 XML 数据文件 identity_fields / section key，不在
模块 manifest 解析路径）。

## 当前状态

- `.env.local.clean` 已生成（600 权限）。
- `sc_clean` 数据库为空（全新，未完成安装）。
- 容器：db/redis 运行，odoo 未启动（安装失败）。

## 停止

需先定位并修复安装链中“Time Off Management”模块描述，或调整安装模块集，再重跑
受管重建。不自行扩大修复范围。

