# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request

from odoo.addons.smart_core.utils.product_release import runtime_release_identity
from odoo.addons.smart_core.security.namespace_resolver import resolve_entry


class RuntimeVersionController(http.Controller):
    @http.route(
        "/api/runtime-version",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def runtime_version(self, **_params):
        payload = runtime_release_identity(request.env.cr.dbname)
        # Batch C: the guard already refused a request without a valid entry
        # stamp (ir.http._pre_dispatch).  The payload names the namespace that
        # selected this database so acceptance can bind the answer to the path.
        httprequest = getattr(request, "httprequest", None)
        headers = dict(getattr(httprequest, "headers", None) or {})
        namespace = resolve_entry(request.env, headers)
        payload = {
            **payload,
            "namespace_id": namespace.namespace_id,
            "namespace_alias": namespace.alias,
            "audience": namespace.audience,
        }
        return request.make_response(
            json.dumps(payload, ensure_ascii=False),
            headers=[("Content-Type", "application/json; charset=utf-8")],
            status=200,
        )
