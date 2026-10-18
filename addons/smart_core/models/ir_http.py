# -*- coding: utf-8 -*-
"""Entry guard hook: resolve the path namespace before any controller runs.

Raising is the only reliable short-circuit in ``_pre_dispatch`` (Odoo ignores
its return value), so a namespace rejection becomes a stable JSON HTTP error
instead of the controller's own response or a 500.
"""

import json

from odoo import models
from odoo.http import request
from werkzeug.exceptions import HTTPException

from ..security.entry_guard import enforce_entry_namespace, namespace_error_body
from ..security.namespace_errors import NamespaceError


class NamespaceRejection(HTTPException):
    """A namespace rejection rendered as stable JSON with its own status."""

    def __init__(self, status: int, body: dict):
        super().__init__(description=json.dumps(body, ensure_ascii=False))
        self.code = int(status)
        self.body = body

    def get_body(self, environ=None, scope=None):
        return json.dumps(self.body, ensure_ascii=False)

    def get_headers(self, environ=None, scope=None):
        return [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Cache-Control", "no-store"),
        ]


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def _pre_dispatch(self, rule, args):
        try:
            enforce_entry_namespace(
                request.env,
                request.httprequest.path,
                request.httprequest.headers,
            )
        except NamespaceError as exc:
            raise NamespaceRejection(exc.http_status, namespace_error_body(exc))
        return super()._pre_dispatch(rule, args)
