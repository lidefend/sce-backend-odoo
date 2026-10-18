# 路径命名空间 C 批验收脚本

`scripts/ops/path_ns_c_acceptance.py` 是可复跑的批量 C 入口验收脚本。它针对
运行中的入口执行五组断言，输出带 `expected` / `actual` / `status` 的 JSON，
任一断言失败即返回非 0。

## 用法

本机入口：

```bash
python3 scripts/ops/path_ns_c_acceptance.py \
  --base-url http://127.0.0.1:18081 \
  --report /tmp/path-ns-c-acceptance.json
```

远端入口（探针在目标主机上执行，`127.0.0.1` 指该主机自身，来源信息也读该主机的检出）：

```bash
python3 scripts/ops/path_ns_c_acceptance.py \
  --ssh-host sc-root \
  --repo /opt/projects/repos/sce-product-odoo \
  --expected-sha <40-hex> \
  --report /tmp/path-ns-c-acceptance.json
```

`--json-out` 与 `--report` 等价语义见脚本内参数；`--emit-json` 只打印 JSON，
供 SSH 管道消费。

## 断言分组

| 分组 | 条数 | 覆盖 |
| --- | --- | --- |
| `provenance` | 5 | 服务器 HEAD 与期望一致、工作树干净、服务器侧提交在历史中、双实例 `source_revision` 一致 |
| `entry_contract` | 7 | `/`→308 `/t/demo/`；无命名空间 `/api`→400；`X-Odoo-DB` 与 `?db=`→409；未知命名空间→404；两条入口各自绑定 `sc_demo` / `sc_platform_control` |
| `dual_entry_auth` | 5 | 同名 `admin` 在双入口各自登录成功、token 互不相同、各自入口可用 |
| `cross_namespace_replay` | 2 | demo token 调 platform、platform token 调 demo 均 401 |
| `session_logout` | 3 | demo 退出成功、demo token 失效、platform token 仍有效 |
| `company_boundary` | 1 | `company_id=999` → 403 `PERMISSION_DENIED` |

合计 23 条。

## 副作用与边界

- 仅对认证状态产生写入：登录建立会话、退出递增 `token_version`。不改业务数据。
- 不重启容器、不改配置、不改数据库结构。
- 脚本只读取被测入口，不修改仓库文件；报告由调用方指定路径。
