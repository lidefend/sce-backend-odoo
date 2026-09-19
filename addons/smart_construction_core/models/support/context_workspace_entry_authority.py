# -*- coding: utf-8 -*-
"""Entry authority for the context dispatch workspaces.

A dispatch workspace only collects the project/counterparty context and hands it
over to a formal document.  The formal document is opened through an Odoo window
action, and the client pairs that action with the menu that authorizes it for the
current principal: a returned action without that pairing is not a route the
principal may open, so the client fails closed instead of guessing.

The three U-C4 G08 workspaces therefore hand back, on every dispatch carrier, the
menu the current principal's route authority already contains for that action.  A
carrier whose target is outside the principal's route authority fails closed with
a business message instead of navigating the user into a navigation denial.

The route authority is the same contract the client enforces, and it is derived
from configuration - the released product surface and the role surface - so a
principal that is granted the entry reaches the formal document without a code
change, and one that is not gets an actionable message.
"""
from datetime import date, datetime

from odoo import _, fields, models
from odoo.exceptions import UserError

# Buckets the client accepts as navigable routes, in client order.
_ROUTE_AUTHORITY_BUCKETS = (
    "primary_actions",
    "role_home_actions",
    "contextual_actions",
    "admin_actions",
    "menu_containers",
)


class ScContextWorkspaceEntryAuthority(models.AbstractModel):
    _name = "sc.context.workspace.entry.authority"
    _description = "上下文办理工作台正式入口授权"

    # A model without `_rec_name` labels every record `<model>,<id>`, and the
    # record surfaces show that verbatim in the tab, the header subtitle and the
    # breadcrumb.  A dispatch context is an operator-facing record, so each entry
    # states its own readable name and the client keeps reading the standard
    # display-name field (`display_name`/`name`) with no model special case.
    name = fields.Char(
        string="记录名称",
        compute="_compute_sc_context_name",
        help="办理工作台记录的显示名称，由入口标题与已选择的办理上下文组成。",
    )
    _rec_name = "name"

    def _sc_readable_context_name(self):
        """Return the entry's readable record name."""
        self.ensure_one()
        return str(self._description or self._name or "").strip()

    def _compute_sc_context_name(self):
        for record in self:
            record.name = record._sc_readable_context_name()

    def _sc_join_context_name(self, project, counterparty):
        """Join the entry title with the context the operator already chose."""
        parts = [str(self._description or self._name or "").strip()]
        for record in (project, counterparty):
            label = str(getattr(record, "display_name", "") or "").strip()
            if label:
                parts.append(label)
        return " · ".join(part for part in parts if part)

    def name_get(self):
        """Keep the legacy display-name entry point consistent with `name`."""
        return [(record.id, record.name or record._sc_readable_context_name()) for record in self]

    def _sc_route_authority(self):
        """Return the route authority entries the current principal may open."""
        from odoo.addons.smart_core.delivery.delivery_engine import DeliveryEngine
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver

        resolver = IdentityResolver(self.env)
        role_surface = resolver.build_role_surface(
            resolver.user_group_xmlids(self.env.user),
            [],
            {"workspace.home"},
        )
        payload = DeliveryEngine(self.env).build(data={"role_surface": role_surface})
        authority = payload.get("route_authority")
        if not isinstance(authority, dict):
            return []
        entries = []
        for bucket in _ROUTE_AUTHORITY_BUCKETS:
            for entry in authority.get(bucket) or []:
                if isinstance(entry, dict):
                    entries.append(entry)
        return entries

    def _sc_entry_menu_ids(self, action_id, model_name=""):
        """Return every route menu the principal's authority offers for the action.

        Only routes the client itself pairs with the action are returned, so a
        menu listed here is one the principal can open.  Product and role
        configuration change the route authority and the carriers follow without
        a code change.
        """
        normalized_action_id = int(action_id or 0)
        if not normalized_action_id:
            return []
        normalized_model = str(model_name or "").strip()
        menus = set()
        for entry in self._sc_route_authority():
            if int(entry.get("action_id") or 0) != normalized_action_id:
                continue
            entry_model = str(entry.get("model") or "").strip()
            if normalized_model and entry_model and entry_model != normalized_model:
                continue
            requirements = entry.get("context_requirements")
            if isinstance(requirements, dict):
                required_query = [
                    str(key or "").strip()
                    for key in requirements.get("required_query") or []
                    if str(key or "").strip()
                ]
                if required_query:
                    # The client re-validates these against the route query,
                    # which a button dispatch does not populate, so the entry is
                    # not dispatchable from here.
                    continue
            menu_id = int(entry.get("menu_id") or 0)
            if menu_id:
                menus.add(menu_id)
        return sorted(menus)

    def _sc_entry_menu_id(self, action_id, model_name="", label=""):
        """Return the single route menu for ``action_id``, ``0`` when there is none.

        A carrier is pinned to exactly one menu.  When the principal's authority
        offers more than one candidate, picking one arbitrarily would send the
        operator into an entry the product never chose, so the dispatch fails
        closed with a business message instead.
        """
        menus = self._sc_entry_menu_ids(action_id, model_name)
        if len(menus) == 1:
            return menus[0]
        if len(menus) > 1:
            raise UserError(
                _("当前账号在“%s”下有多个可打开入口，无法确定要派发到哪一个；请联系管理员收敛发布范围后办理。")
                % (label or "")
            )
        return 0

    def _sc_literal_context(self, context):
        """Return ``context`` with values that survive a Python-literal round-trip.

        A dispatch carrier reaches the client as a window action, and the
        gateway transports ``action.context`` as a Python literal
        (``execute_button._query_literal`` -> ``repr``).  A ``date``/``datetime``
        object reprs as ``datetime.date(2026, 9, 19)``, which neither the client
        route parser nor the list gateway can read, so the whole context is
        rejected and the formal document would open without the project and
        counterparty the operator just chose.  Date-like values therefore travel
        as ISO strings.
        """
        if not isinstance(context, dict):
            return {}
        literal = {}
        for key, value in context.items():
            if isinstance(value, datetime):
                literal[key] = fields.Datetime.to_string(value)
            elif isinstance(value, date):
                literal[key] = fields.Date.to_string(value)
            else:
                literal[key] = value
        return literal

    def _sc_pin_entry_authority(self, action, *, label):
        """Bind a returned window action to the menu the principal may open.

        ``action`` is the window-action payload the carrier is about to return.
        Fails closed with a business message when the principal's route authority
        carries no entry for the target, because the client cannot open an action
        the principal has no authorized route for.
        """
        if not isinstance(action, dict) or not action:
            raise UserError(_("正式办理入口不存在，请检查产品配置。"))
        if isinstance(action.get("context"), dict):
            action["context"] = self._sc_literal_context(action["context"])
        menu_id = self._sc_entry_menu_id(
            action.get("id") or action.get("action_id"),
            action.get("res_model"),
            label=label,
        )
        if not menu_id:
            raise UserError(
                _("当前账号的角色范围未包含“%s”的正式入口，请联系管理员确认角色与发布范围后办理。") % label
            )
        action["menu_id"] = menu_id
        return action
