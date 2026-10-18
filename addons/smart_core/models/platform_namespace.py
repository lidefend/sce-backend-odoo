# -*- coding: utf-8 -*-
"""Immutable namespace identity (ADR-007 batch C).

A namespace is a governed fact: an immutable ``namespace_id`` binds one
database and one duty, and every path alias is only a renameable pointer to it.
The registry never infers a namespace from whichever database a request reached.
"""

from __future__ import annotations

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..security.namespace_errors import (
    NamespaceAmbiguous,
    NamespaceConflict,
    NamespaceSuspended,
    UnknownNamespace,
)

NAMESPACE_ID_PATTERN = re.compile(r"^ns_[0-9a-f]{12}$")
ALIAS_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

AUDIENCE_PLATFORM = "platform-admin"
AUDIENCE_TENANT = "tenant"

LIFECYCLE_STATES = (
    ("declared", "已声明"),
    ("provisioned", "已分配"),
    ("active", "运行中"),
    ("suspended", "已暂停"),
    ("retired", "已退役"),
)


class ScPlatformNamespace(models.Model):
    _name = "sc.platform.namespace"
    _description = "Platform Namespace Identity"
    _order = "namespace_id"

    namespace_id = fields.Char(
        string="命名空间",
        required=True,
        index=True,
        readonly=True,
        copy=False,
    )
    display_name = fields.Char(string="租户名称", required=True)
    lifecycle_state = fields.Selection(
        LIFECYCLE_STATES,
        string="生命周期",
        default="declared",
        required=True,
        index=True,
    )
    # The physical database is an internal binding fact.  It is deliberately
    # kept out of every list/form projection: the platform administrator works
    # with the logical namespace identity, not the storage name behind it.
    database_name = fields.Char(
        string="物理库（内部）",
        required=True,
        index=True,
    )
    duty_key = fields.Char(string="职责标识", required=True, index=True)
    audience = fields.Selection(
        [(AUDIENCE_PLATFORM, "平台管理"), (AUDIENCE_TENANT, "租户")],
        string="职责域",
        default=AUDIENCE_TENANT,
        required=True,
    )
    primary_alias = fields.Char(
        string="入口别名",
        compute="_compute_primary_alias",
    )
    alias_ids = fields.One2many(
        "sc.platform.namespace.alias",
        "namespace_id",
        string="路径别名",
        readonly=True,
    )

    @api.depends(
        "alias_ids.alias",
        "alias_ids.alias_kind",
        "alias_ids.is_primary",
        "alias_ids.retired_at",
    )
    def _compute_primary_alias(self):
        for record in self:
            aliases = record.alias_ids.filtered(
                lambda row: row.alias_kind == "path" and not row.retired_at
            )
            primary = aliases.filtered("is_primary")[:1] or aliases[:1]
            record.primary_alias = primary.alias or ""

    _sql_constraints = [
        (
            "platform_namespace_id_uniq",
            "unique(namespace_id)",
            "A namespace identity is registered exactly once.",
        ),
        (
            "platform_namespace_database_uniq",
            "unique(database_name)",
            "A governed database carries exactly one namespace.",
        ),
    ]

    @api.constrains("namespace_id")
    def _check_namespace_id(self):
        for record in self:
            value = str(record.namespace_id or "")
            if not NAMESPACE_ID_PATTERN.match(value):
                raise ValidationError("namespace_id must look like ns_<12 lowercase hex>")

    @api.constrains("database_name", "duty_key")
    def _check_database_declaration(self):
        for record in self:
            database = str(record.database_name or "").strip()
            duty_key = str(record.duty_key or "").strip()
            if not database or not duty_key:
                raise ValidationError("namespace requires a database and a duty")
            registration = self.env["sc.platform.database.registration"].sudo().search(
                [("db_name", "=", database)], limit=1
            )
            if registration and registration.lifecycle_state == "retired":
                raise ValidationError("namespace cannot bind a retired database registration")

    def write(self, vals):
        if "namespace_id" in vals:
            for record in self:
                if str(vals.get("namespace_id") or "") != str(record.namespace_id or ""):
                    raise ValidationError("namespace_id is immutable once created")
        return super().write(vals)

    def assert_active(self):
        self.ensure_one()
        if self.lifecycle_state != "active":
            raise NamespaceSuspended(
                "namespace %s is %s" % (self.namespace_id, self.lifecycle_state)
            )
        return True

    @api.model
    def resolve_alias(self, alias, kind="path"):
        """Resolve one alias to its namespace record, or fail closed."""

        token = str(alias or "").strip()
        if not token:
            raise UnknownNamespace("empty namespace alias")
        rows = self.sudo().search(
            [
                ("alias_ids.alias", "=", token),
                ("alias_ids.alias_kind", "=", kind),
                ("alias_ids.retired_at", "=", False),
            ]
        )
        if len(rows) > 1:
            raise NamespaceConflict("alias %s resolves to %s namespaces" % (token, len(rows)))
        if not rows:
            raise UnknownNamespace("unknown namespace alias: %s" % token)
        rows.assert_active()
        return rows

    @api.model
    def resolve_for_database(self, database):
        """Resolve the namespace an instance is bound to (internal callers)."""

        name = str(database or "").strip()
        if not name:
            raise UnknownNamespace("empty database")
        rows = self.sudo().search([("database_name", "=", name)])
        if len(rows) > 1:
            raise NamespaceAmbiguous(
                "database %s declares %s namespaces" % (name, len(rows))
            )
        if not rows:
            raise UnknownNamespace("database %s declares no namespace" % name)
        rows.assert_active()
        return rows


class ScPlatformNamespaceAlias(models.Model):
    _name = "sc.platform.namespace.alias"
    _description = "Platform Namespace Alias"
    _order = "alias"

    alias = fields.Char(string="别名", required=True, index=True)
    alias_kind = fields.Selection(
        [("path", "路径前缀"), ("subdomain", "子域")],
        string="别名类型",
        default="path",
        required=True,
        index=True,
    )
    namespace_id = fields.Many2one(
        "sc.platform.namespace",
        string="命名空间",
        required=True,
        ondelete="cascade",
        index=True,
    )
    is_primary = fields.Boolean(string="主别名", default=False)
    retired_at = fields.Datetime(string="退役时间", readonly=True)

    _sql_constraints = [
        (
            "platform_namespace_alias_kind_uniq",
            "unique(alias, alias_kind)",
            "An alias is assigned to exactly one namespace per kind.",
        ),
    ]

    @api.constrains("alias")
    def _check_alias(self):
        for record in self:
            if not ALIAS_PATTERN.match(str(record.alias or "")):
                raise ValidationError("alias must match ^[a-z0-9][a-z0-9-]{0,62}$")
