# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api, models, fields, tools


class ResUsers(models.Model):
    _inherit = "res.users"
    SOURCE_KIND = "odoo_auth_session_extension"
    SOURCE_AUTHORITIES = ("res.users",)
    NO_BUSINESS_FACT_AUTHORITY = True

    token_version = fields.Integer(default=0)

    # Membership in these groups is an *audience* classification ("who the
    # user is"), not a capability ("what the user may do"). Odoo core derives
    # ``res.users._is_public``/``_is_portal``, ``res.partner.is_public`` and
    # the mail channel-membership guard from them, so their real value must
    # never be replaced by the superuser pass-through below.
    AUDIENCE_GROUP_XMLIDS = frozenset({"base.group_public", "base.group_portal"})

    @api.model
    @tools.ormcache("self._uid", "group_ext_id")
    def _has_group(self, group_ext_id):
        # R10-v2: this Odoo build's has_group has no superuser pass-through,
        # while every SC capability guard assumes "superuser can act".
        # Restore the Odoo ACL semantics here so superuser-driven flows
        # (tests, scripts, shell) are not denied by group membership checks.
        # Audience markers are excluded: fabricating superuser membership there
        # would make OdooBot (uid 1) look like a public/portal user and trip
        # core constraints such as ``discuss_channel_member``.
        if self._uid == SUPERUSER_ID and group_ext_id not in self.AUDIENCE_GROUP_XMLIDS:
            return True
        return super()._has_group(group_ext_id)

    def write(self, vals):
        if self.env.context.get("sc_skip_token_epoch_bump"):
            return super().write(vals)

        security_fields = {"active", "company_id", "company_ids", "groups_id", "login", "password"}
        must_invalidate = bool(security_fields.intersection(vals)) and "token_version" not in vals
        result = super().write(vals)
        if must_invalidate:
            for user in self.exists():
                user.with_context(sc_skip_token_epoch_bump=True).write(
                    {"token_version": int(user.token_version or 0) + 1}
                )
        return result

    def source_authority_contract(self):
        return {
            "kind": self.SOURCE_KIND,
            "authorities": list(self.SOURCE_AUTHORITIES),
            "projection_only": True,
            "write_proxy": True,
            "no_business_fact_authority": self.NO_BUSINESS_FACT_AUTHORITY,
            "runtime_carrier": self._name,
        }
