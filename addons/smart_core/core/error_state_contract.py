"""P0 public error presentation. Contains no tenant or authorization facts."""
from copy import deepcopy


def build_error_state_contract():
    def state(kind, statuses, reasons, title, message, action, label, path=None):
        return dict(kind=kind, statuses=statuses, reasons=reasons, title=title,
                    message=message, action=dict(kind=action, label=label, path=path))

    return deepcopy({
        "schema_version": "1.0.0",
        "source": "smart_core.error_state_contract",
        "default_kind": "unknown",
        "states": [
            state("session", [401], ["SESSION_EXPIRED", "TOKEN_EXPIRED"], "登录已失效", "为保护业务数据，请重新登录后继续。", "route", "重新登录", "/login"),
            state("permission", [403], ["ACCESS_DENIED", "FORBIDDEN", "PERMISSION_DENIED"], "无权访问", "当前账号无权访问此内容，请返回已授权的工作区。", "route", "返回安全页面", "/"),
            state("missing", [404], ["RECORD_NOT_FOUND", "NOT_FOUND", "MISSING_RECORD"], "记录不存在", "该记录可能已被删除，或链接已经失效。", "route", "返回安全页面", "/"),
            state("conflict", [409], ["CONFLICT", "STALE", "VERSION_CONFLICT"], "数据已发生变化", "其他操作已更新这条数据，请获取最新版本后继续。", "retry", "获取最新数据"),
            state("validation", [422], ["VALIDATION", "BUSINESS_RULE"], "请检查业务信息", "部分内容不符合业务要求，请检查后重试。", "none", "检查业务信息"),
            state("network", [0], ["NETWORK", "TIMEOUT", "FETCH_FAILED"], "网络连接异常", "暂时无法连接服务，请检查网络后重试。", "retry", "重试"),
            state("server", list(range(500, 600)), [], "服务暂时不可用", "服务当前无法完成请求，请稍后重试。", "retry", "重试"),
            state("unknown", [], [], "操作未完成", "请求未能完成，请返回安全页面。", "route", "返回安全页面", "/"),
        ],
    })
