# 120 · BNVA-019 Stage 3B · 适配器接入报告

## 接入关系

| Adapter | 入口 | 共享 L0 方式 |
| --- | --- | --- |
| Layout Adapter (LDP) | `app_view_config._safe_get_view_data` | 解析后 `store_parsed_view` |
| Business Structure Adapter (NCP) | `project_native_view` | `fetch_parsed_view` 复用 |

两个 Adapter 仍各自遍历统一模型/解析根，职责不同；共享的是「解析一次」的 L0 事实，
不是共享业务处理逻辑。

## 隔离

- NCP 不输出 columns / widget / toolbar / search。
- LDP 不输出 fieldOwnership / identity / businessRole / fieldGroups。
- 请求缓存按 cursor + uid + context 隔离，普通用户不消费 sudo 视图。

