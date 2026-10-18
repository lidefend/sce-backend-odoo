# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from odoo import api, fields, models

from ..security.platform_admin import (
    declared_platform_control_dbname,
    is_declared_platform_control_database,
)

_logger = logging.getLogger(__name__)

ENTRY_KIND_TENANT = "tenant"
ENTRY_KIND_PLATFORM_ADMIN = "platform_admin"


def normalize_entry_kind(entry_kind, current_db: str, env=None) -> str:
    """Keep ``platform_admin`` confined to the declared platform instance.

    A tenant database may still hold a legacy row labelled ``platform_admin``;
    the runtime projection must not repeat that label.  ADR-007 D6 binds the
    responsibility to the instance, so the label degrades to ``tenant``
    whenever the current database is not the declared platform-control one.
    """

    kind = str(entry_kind or "").strip() or ENTRY_KIND_TENANT
    if kind == ENTRY_KIND_PLATFORM_ADMIN and not is_declared_platform_control_database(current_db, env):
        return ENTRY_KIND_TENANT
    return kind


class ScLoginRoute(models.Model):
    _name = "sc.login.route"
    _description = "SC Unified Login Route"
    _order = "sequence, id"

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    login = fields.Char(required=True, index=True)
    target_db = fields.Char(required=True, index=True)
    entry_kind = fields.Selection(
        [("tenant", "Tenant"), ("platform_admin", "Platform Admin")],
        default="tenant",
        required=True,
        index=True,
    )
    product_key = fields.Char(default="platform")
    label = fields.Char()
    note = fields.Text()

    _sql_constraints = [
        ("sc_login_route_login_uniq", "unique(login)", "Login route must be unique per login."),
    ]

    @api.model
    def ensure_platform_default_login_routes(self):
        """Seed platform-admin routes only inside the declared platform instance.

        Tenant databases must never grow a ``platform_admin`` route just
        because they installed ``smart_core``.
        """

        current_db = ""
        try:
            current_db = str(self.env.cr.dbname or "").strip()
        except Exception:
            current_db = ""
        if not is_declared_platform_control_database(current_db, self.env):
            _logger.info(
                "sc.login.route: skipping platform default routes on %s; declared platform control db is %s",
                current_db or "<unknown>",
                declared_platform_control_dbname(self.env),
            )
            return False
        raw_logins = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sc.login.platform_admin_logins", "admin")
        )
        for login in [item.strip() for item in str(raw_logins or "").split(",") if item.strip()]:
            route = self.sudo().search([("login", "=", login)], limit=1)
            vals = {
                "login": login,
                "target_db": current_db,
                "entry_kind": "platform_admin",
                "product_key": "platform",
                "label": "Platform Admin",
                "active": True,
            }
            if route:
                route.sudo().write({key: vals[key] for key in ("target_db", "entry_kind", "product_key", "label", "active")})
            elif current_db:
                self.sudo().create(vals)
        return True

    def to_runtime_dict(self, current_db: str | None = None) -> dict:
        self.ensure_one()
        entry_kind = (self.entry_kind or "").strip()
        if current_db is not None:
            entry_kind = normalize_entry_kind(entry_kind, current_db, self.env)
        return {
            "login": (self.login or "").strip(),
            "target_db": (self.target_db or "").strip(),
            "entry_kind": entry_kind,
            "product_key": (self.product_key or "").strip(),
            "label": (self.label or "").strip(),
        }
