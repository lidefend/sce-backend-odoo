# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from odoo import fields, http
from odoo.exceptions import AccessDenied
from odoo.http import request

from odoo.addons.smart_core.security.auth import get_user_from_token
from odoo.addons.smart_core.security.platform_admin import user_is_platform_control_admin
from odoo.addons.smart_core.core.trace import get_trace_id

CONTRACT_VERSION = "v1"


def _server_time() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_response(payload: dict[str, Any], status: int = 200):
    return request.make_response(
        json.dumps(payload, ensure_ascii=False, default=str),
        headers=[("Content-Type", "application/json; charset=utf-8")],
        status=status,
    )


def _ok(data: Any, status: int = 200):
    trace_id = get_trace_id(request.httprequest.headers)
    return _json_response(
        {
            "ok": True,
            "contract_version": CONTRACT_VERSION,
            "server_time": _server_time(),
            "trace_id": trace_id,
            "warnings": [],
            "data": data,
        },
        status=status,
    )


def _fail(code: str, message: str, *, details: dict[str, Any] | None = None, http_status: int = 400):
    trace_id = get_trace_id(request.httprequest.headers)
    return _json_response(
        {
            "ok": False,
            "contract_version": CONTRACT_VERSION,
            "server_time": _server_time(),
            "trace_id": trace_id,
            "warnings": [],
            "error": {
                "code": str(code),
                "message": message,
                "details": details or {},
                "trace_id": trace_id,
            },
        },
        status=http_status,
    )


def _fail_from_exception(exc: Exception, http_status: int = 500):
    return _fail(
        "SERVER_ERROR",
        "Internal server error",
        details={"error": str(exc)},
        http_status=http_status,
    )


def _platform_env():
    user = get_user_from_token()
    if not user_is_platform_control_admin(user):
        raise AccessDenied("insufficient permissions")
    return user, request.env(user=user)


class PlatformOpsController(http.Controller):
    @http.route("/api/ops/tenants", type="http", auth="public", methods=["GET"], csrf=False)
    def tenants(self, **params):
        """Return the registered tenant namespaces, not the local companies.

        A company row in the platform-control database is not a tenant: the
        platform instance may hold no customer company at all, and a tenant
        database usually holds several companies.  The tenant registry is the
        namespaces declared with the ``tenant`` audience, joined to the
        governed database registration and to the explicit tenant-company
        registration when (and only when) one exists.  Billing data is emitted
        only for a namespace that resolves to a registered company.
        """
        try:
            _user, env = _platform_env()
            Namespace = env.get("sc.platform.namespace")
            if Namespace is None:
                return _fail("SERVER_ERROR", "namespace registry unavailable", http_status=500)
            Registration = env.get("sc.platform.database.registration")
            CompanyRegistration = env.get("sc.tenant.company.registration")
            Entitlement = env.get("sc.entitlement")
            Usage = env.get("sc.usage.counter")
            Subscription = env.get("sc.subscription")

            namespaces = Namespace.sudo().search(
                [("audience", "=", "tenant"), ("lifecycle_state", "!=", "retired")],
                order="namespace_id",
            )
            data = []
            for namespace in namespaces:
                registration = None
                if Registration is not None:
                    registration = Registration.sudo().search(
                        [("db_name", "=", namespace.database_name)], limit=1
                    )
                tenant_key = registration.tenant_key if registration else None
                company = None
                if CompanyRegistration is not None and tenant_key:
                    company_registration = CompanyRegistration.sudo().search(
                        [("tenant_key", "=", tenant_key), ("active", "=", True)], limit=1
                    )
                    company = company_registration.company_id or None

                plan_code = None
                flags = {}
                limits = {}
                usage = {}
                subscription_state = None
                if company is not None:
                    if Entitlement is not None:
                        entitlement = Entitlement.get_effective(company)
                        plan_code = entitlement.plan_id.code if entitlement.plan_id else None
                        flags = entitlement.effective_flags_json or {}
                        limits = entitlement.effective_limits_json or {}
                    usage = Usage.get_usage_map(company) if Usage is not None else {}
                    if Subscription is not None:
                        subscription = Subscription.search(
                            [("company_id", "=", company.id)],
                            order="start_date desc, id desc",
                            limit=1,
                        )
                        subscription_state = subscription.state if subscription else None

                primary_alias = namespace.alias_ids.filtered(
                    lambda alias: not alias.retired_at and alias.is_primary
                )[:1] or namespace.alias_ids.filtered(lambda alias: not alias.retired_at)[:1]
                alias = primary_alias.alias if primary_alias else None
                data.append({
                    "namespace_id": namespace.namespace_id,
                    "tenant_name": namespace.display_name,
                    "lifecycle_state": namespace.lifecycle_state,
                    "audience": namespace.audience,
                    "alias": alias,
                    "path_prefix": ("/t/%s" % alias) if alias else None,
                    "tenant_key": tenant_key,
                    "company_id": company.id if company is not None else None,
                    "company_name": company.name if company is not None else None,
                    "billing_bound": bool(company is not None),
                    "plan_code": plan_code,
                    "flags": flags,
                    "limits": limits,
                    "usage": usage,
                    "subscription_state": subscription_state,
                })
            return _ok({"tenants": data, "count": len(data)}, status=200)
        except AccessDenied as exc:
            return _fail("PERMISSION_DENIED", str(exc), http_status=403)
        except Exception as exc:
            return _fail_from_exception(exc, http_status=500)

    @http.route("/api/ops/subscription/set", type="http", auth="public", methods=["POST"], csrf=False)
    def set_subscription(self, **params):
        try:
            _user, env = _platform_env()
            body = request.httprequest.get_json(force=True, silent=True) or {}
            company_id = body.get("company_id")
            plan_code = body.get("plan_code") or "default"
            state = body.get("state") or "active"
            if not company_id:
                return _fail("BAD_REQUEST", "company_id required", http_status=400)
            Plan = env["sc.subscription.plan"].sudo()
            plan = Plan.search([("code", "=", plan_code)], limit=1)
            if not plan:
                return _fail("BAD_REQUEST", "plan_code not found", http_status=400)
            Subscription = env["sc.subscription"].sudo()
            sub = Subscription.search([("company_id", "=", company_id)], limit=1)
            vals = {
                "company_id": company_id,
                "plan_id": plan.id,
                "state": state,
                "is_trial": state == "trial",
                "start_date": fields.Date.context_today(env.user),
            }
            if sub:
                sub.write(vals)
            else:
                sub = Subscription.create(vals)
            return _ok({"subscription_id": sub.id}, status=200)
        except AccessDenied as exc:
            return _fail("PERMISSION_DENIED", str(exc), http_status=403)
        except Exception as exc:
            return _fail_from_exception(exc, http_status=500)

    @http.route("/api/ops/job/status", type="http", auth="public", methods=["GET"], csrf=False)
    def job_status(self, **params):
        try:
            _user, env = _platform_env()
            job_id = params.get("job_id")
            if not job_id:
                try:
                    limit = int(params.get("limit") or 20)
                except (TypeError, ValueError):
                    return _fail("BAD_REQUEST", "limit must be an integer", http_status=400)
                limit = max(1, min(limit, 100))
                jobs = env["sc.ops.job"].sudo().search(
                    [], order="started_at desc, id desc", limit=limit
                )
                return _ok(
                    {
                        "jobs": [self._serialize_job(job) for job in jobs],
                        "count": len(jobs),
                        "limit": limit,
                    },
                    status=200,
                )
            try:
                job_pk = int(job_id)
            except (TypeError, ValueError):
                return _fail("BAD_REQUEST", "job_id must be an integer", http_status=400)
            job = env["sc.ops.job"].sudo().browse(job_pk)
            if not job.exists():
                return _fail("NOT_FOUND", "job not found", http_status=404)
            return _ok(self._serialize_job(job), status=200)
        except AccessDenied as exc:
            return _fail("PERMISSION_DENIED", str(exc), http_status=403)
        except Exception as exc:
            return _fail_from_exception(exc, http_status=500)

    @staticmethod
    def _serialize_job(job):
        return {
            "job_id": job.id,
            "name": job.name,
            "job_type": job.job_type,
            "status": job.status,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "result": job.result_json or {},
            "error": job.error_message or "",
        }
