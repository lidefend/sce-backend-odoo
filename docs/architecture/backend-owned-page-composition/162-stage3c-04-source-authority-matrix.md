# 162 · BNVA-019 Stage 3C-04 · 原生事实来源矩阵

## Form 主 arch（共享，请求级一次）

| 事实 | 唯一入口 | 说明 |
| --- | --- | --- |
| get_view | `native_view_projection.project_native_view`（:185） | carrier 命中则跳过 |
| fields_get | `project_native_view`（:191） | 当前用户 env，非 sudo |
| etree.fromstring | `project_native_view`（:189） | 解析根缓存为 `_arch_root` |
| Canonical Model | `NativeView`（`native_view_projection.py:73`） | 一次遍历一次构建 |

## 合法独立解析（非重复）

| 范围 | 入口 | 依据 |
| --- | --- | --- |
| tree/kanban/pivot | `view_Parser/parsers Kanban Pivot Graph.py` | 独立视图类型 |
| calendar/gantt/activity | `view_Parser/parsers_Calendar_Gantt Activity.py` | 独立视图类型 |
| search | `app_search_config.py` | 独立视图类型 |
| 内联 x2many 子视图 | `parsers Tree Form.py:1551/1572` | 子视图独立 arch |
| onchange spec | `native_onchange_spec.py` | 02B 裁定保留独立 |
| draft feedback | `draft_feedback.py` | 02B 裁定保留独立 |
| node validation | `node_component_validation.py` | 独立视图身份校验 |

## 权限上下文

- Form 主 arch 的 get_view / fields_get 均使用当前用户 env；无 sudo 补全。
- carrier 绑定 uid / su / company-lang-tz context digest；跨用户/公司/请求不共享。

