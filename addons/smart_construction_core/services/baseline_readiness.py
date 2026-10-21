"""P1 read-only submission readiness, backed by native business checks."""
from odoo.exceptions import AccessError, UserError


SUPPORTED_MODELS = ("project.project", "payment.request")
SOURCE_AUTHORITIES = (
    "project.project._check_initiation_ready",
    "payment.request._check_submission_prerequisites",
    "payment.request._collect_payment_advisories",
    "payment.request._enforce_batch_funding_submit_gate",
    "ir.model.access", "ir.rule",
)


def build_readiness(env, model, record_id=None):
    if model not in SUPPORTED_MODELS:
        raise ValueError("Unsupported readiness model")
    if record_id is not None and (type(record_id) is not int or record_id <= 0):
        raise ValueError("record_id must be a positive integer")
    result = {"schema_version": "1.0", "model": model, "record_id": record_id,
              "status": "no_data", "reason_code": "RECORD_REQUIRED", "checks": [],
              "message": "请先保存或选择业务记录，再进行办理前检查。",
              "next_step": {"action": "select_record", "label": "选择业务记录"},
              "source_authorities": list(SOURCE_AUTHORITIES), "projection_only": True}
    record = env[model].browse(record_id) if record_id is not None else env[model]
    try:
        record.check_access_rights("read")
        if record_id is None:
            return result
        record.check_access_rule("read")
        if not record.exists():
            result["reason_code"] = "RECORD_NOT_FOUND"
            return result
        allowed = (record._has_initiation_submit_access() if model == "project.project"
                   else record._has_submit_access())
        if not allowed:
            raise AccessError("Submission capability required")
        checks = submission_checks(record)
        blocked = [row for row in checks if row["status"] == "blocked"]
        result.update(status="blocked" if blocked else "ready", checks=checks,
                      reason_code=blocked[0]["reason_code"] if blocked else "OK",
                      message=blocked[0]["message"] if blocked else "当前可提交；提示项及提交时的重新校验仍然适用。",
                      next_step={"action": "review_record" if blocked else "submit_record",
                                 "label": "处理阻塞原因" if blocked else "提交业务记录"})
    except AccessError:
        # Do not echo inaccessible business facts, field values or native rule details.
        result.update(status="forbidden", reason_code="PERMISSION_DENIED", checks=[],
                      message="当前账号无权查看或提交该记录。",
                      next_step={"action": "request_access", "label": "联系管理员核对业务权限"})
    return result


def payment_advisories(record, action, evaluation_cache=None):
    """Project native business refusals as hard blocks; never swallow access/errors."""
    try:
        return list(record._collect_payment_advisories(action, evaluation_cache=evaluation_cache) or [])
    except AccessError:
        raise
    except UserError as exc:
        return [{"reason_code": "NATIVE_PAYMENT_CHECK_BLOCKED", "message": str(exc),
                 "force_block_enabled": True,
                 "hints": ["请按上述原生业务检查结果修正记录。"]}]


def submission_checks(record, advisories=None):
    """Read-only business availability; caller retains capability and record authorization."""
    model = record._name
    checks = []
    prerequisite = (record._check_initiation_ready if model == "project.project"
                    else record._check_submission_prerequisites)
    try:
        prerequisite()
    except AccessError:
        raise
    except UserError as exc:
        checks.append({"key": "submission", "status": "blocked", "reason_code": "SUBMISSION_PREREQUISITES_BLOCKED",
                       "message": str(exc), "next_step": "请按上述原因补充或修正当前记录。"})
    else:
        checks.append({"key": "submission", "status": "ready", "reason_code": "OK",
                       "message": "提交基础条件检查通过。", "next_step": "提交时将再次检查当前数据。"})
    if model == "payment.request":
        cache = {}
        for item in (payment_advisories(record, "submit", evaluation_cache=cache) if advisories is None else advisories):
            checks.append({"key": item["reason_code"],
                           "status": "blocked" if item.get("force_block_enabled") else "warning",
                           "reason_code": item["reason_code"], "message": item.get("message", ""),
                           "next_step": "；".join(item.get("hints") or []) or item.get("message", "")})
        try:
            record.with_context(payment_soft_gate=True)._enforce_batch_funding_submit_gate(evaluation_cache=cache)
        except AccessError:
            raise
        except UserError as exc:
            checks.append({"key": "funding", "status": "blocked", "reason_code": "FUNDING_SUBMISSION_BLOCKED",
                           "message": str(exc), "next_step": "请核对项目资金基线、有效期间和可用额度。"})
    return checks


def readiness_display(record):
    """Native form presentation of the same projection, including unsaved records."""
    record_id = record.id if type(record.id) is int else None
    result = build_readiness(record.env, record._name, record_id)
    labels = {"ready": "可提交", "blocked": "待处理", "no_data": "暂无记录", "forbidden": "无权限"}
    lines = ["办理前检查：%s" % labels[result["status"]], result["message"]]
    for check in result["checks"]:
        if check["status"] != "ready":
            detail = check["message"]
            if check["next_step"] and check["next_step"] != detail:
                detail += " " + check["next_step"]
            if detail not in lines:
                lines.append(detail)
    lines.append("下一步：" + result["next_step"]["label"])
    return "\n".join(lines)
