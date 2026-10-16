"""ORM glue for the narrow signed-payload import operator lifecycle.

The decisions live in ``tenant_payload_operator_policy``; this module only
turns them into ORM writes.  It exists because the owner ruled that the
*platform* owns the operator's account lifecycle and the customer module must
not create platform operators, so no ops script may be the long-term source of
this behaviour.

Everything here is deliberately narrow:

* the account carries only ``base.group_user`` plus the importer group, never
  an administrator group, and it is created without an interactive password;
* re-running the provision on the account this mechanism created is a no-op;
  an account that merely shares the declared external id or login is refused
  rather than taken over;
* the only group this mechanism ever adds is the narrow importer group, and the
  change is asserted to be the *only* membership change;
* revoking removes the permission and keeps the account, its external id and
  the audit association.
"""

from __future__ import annotations

from odoo import SUPERUSER_ID, Command, fields
from odoo.exceptions import AccessError, UserError

from odoo.addons.smart_core.security import tenant_payload_operator_policy as policy


class TenantPayloadOperatorError(UserError):
    """The mechanism refuses to continue rather than guess a fact."""


def _fail(rule: str) -> None:
    raise TenantPayloadOperatorError(rule)


def _assert_governed_principal(env) -> None:
    """Only the governed platform maintenance principal may write the lifecycle.

    The lifecycle is a platform mechanism, so its writes are reachable from the
    maintenance principal and from nowhere else; a business or portal user may
    never provision, grant to or revoke from a service identity.
    """
    try:
        env["sc.platform.database.registration"]._assert_governance_principal()
    except AccessError:
        raise


def _xmlid_to_record(env, xmlid: str):
    return env.ref(xmlid, raise_if_not_found=False)


def _group_xmlids(env, group_ids) -> list[str]:
    if not group_ids:
        return []
    rows = env["ir.model.data"].sudo().search(
        [("model", "=", "res.groups"), ("res_id", "in", sorted(group_ids))]
    )
    by_id: dict[int, list[str]] = {}
    for row in rows:
        by_id.setdefault(row.res_id, []).append("%s.%s" % (row.module, row.name))
    if any(len(by_id.get(group_id, ())) != 1 for group_id in group_ids):
        _fail("TPO_GROUP_XMLID_NOT_UNIQUE")
    return sorted(by_id[group_id][0] for group_id in group_ids)


def _group_closure_xmlids(env, group_ids) -> list[str]:
    """The transitive implied closure of the given groups, as xmlids.

    Odoo completes an account's membership with the implied groups of the
    groups it is created with, so "the identity this mechanism may reuse" is
    the required groups *plus* the platform's own closure of them, and nothing
    else.  Reading the closure instead of hard-coding it keeps the mechanism
    independent of which modules happen to imply a group in a given tenant.
    """
    if not group_ids:
        return []
    groups = env["res.groups"].sudo().browse(sorted(set(group_ids)))
    return _group_xmlids(env, (groups | groups.trans_implied_ids).ids)


def _has_stored_password(env, user) -> bool:
    """Read the credential fact, not a cached attribute.

    The operator is reachable only through the governed maintenance entry, so a
    stored password would be an unreviewed second channel.  Whether one exists
    is a database fact, so it is read as one.
    """
    env.cr.execute("SELECT COALESCE(password, '') FROM res_users WHERE id = %s", (user.id,))
    row = env.cr.fetchone()
    return bool(row and str(row[0] or "").strip())


def _has_native_api_keys(env, user) -> bool:
    env.cr.execute(
        "SELECT COUNT(*) FROM res_users_apikeys WHERE user_id = %s", (user.id,)
    )
    row = env.cr.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def read_operator(env, *, identity_xmlid: str) -> dict:
    """Every fact the lifecycle asserts, read from the current state."""
    record = _xmlid_to_record(env, identity_xmlid)
    report = {
        "schema_version": policy.SCHEMA_VERSION,
        "mode": "read_only",
        "writes": 0,
        "database": env.cr.dbname,
        "identity_key": identity_xmlid,
        "operator": None,
        "importer_group_member_count": 0,
    }
    importer = _xmlid_to_record(env, policy.IMPORTER_GROUP_XMLID)
    if importer:
        report["importer_group_member_count"] = len(importer.users)
        report["importer_implied_xmlids"] = _group_xmlids(env, importer.implied_ids.ids)
    required_group = _xmlid_to_record(env, policy.INTERNAL_USER_GROUP_XMLID)
    if required_group:
        report["required_group_closure_xmlids"] = _group_closure_xmlids(
            env, [required_group.id]
        )
    if not record or record._name != "res.users":
        return report
    user = record
    report["operator"] = {
        "id": user.id,
        # The external id the record was resolved by is itself a fact the
        # lifecycle asserts: the idempotency check compares it, and a report
        # that omitted it could not be compared with the declaration.
        "xmlid": identity_xmlid,
        "login": user.login,
        "name": user.name,
        "active": bool(user.active),
        "share": bool(user.share),
        "company_ids": sorted(user.company_ids.ids),
        "group_xmlids": _group_xmlids(env, user.groups_id.ids),
        "is_importer": bool(importer and importer.id in user.groups_id.ids),
        "is_data_operator": bool(
            (data_operator := _xmlid_to_record(env, policy.DATA_OPERATOR_GROUP_XMLID))
            and data_operator.id in user.groups_id.ids
        ),
        "has_stored_password": _has_stored_password(env, user),
        "has_native_api_keys": _has_native_api_keys(env, user),
    }
    return report


def _declared_block_company(env, declared: dict):
    company = _xmlid_to_record(env, declared["company_xmlid"])
    if not company or company._name != "res.company":
        _fail("TPO_DECLARED_COMPANY_NOT_RESOLVED")
    return company


def provision(env, *, declaration: dict, authorization: dict) -> dict:
    """Create or reuse the declared service identity, idempotently.

    The approval is verified before anything is created, and it is verified
    from the passed facts rather than from the declaration: a declaration
    written by the side that wants the permission can never authorize itself.
    """
    _assert_governed_principal(env)
    declared = policy.validate_declaration(declaration)
    company = _declared_block_company(env, declared)
    facts = authorization if isinstance(authorization, dict) else {}
    approval = policy.validate_authorization(
        authorization,
        # The expectations come from the database that is being written, not
        # from the approval payload or the declaration, so neither side can
        # widen its own scope by describing it differently.
        db_name=env.cr.dbname,
        tenant_key=str(
            env["ir.config_parameter"].sudo().get_param("sc.tenant.bound_tenant_key", "") or ""
        ),
        identity_key=declared["identity_key"],
        subject_checksum=facts.get("subject_checksum"),
        now=fields.Datetime.to_string(fields.Datetime.now()),
        action="provision",
    )
    if company != env.company:
        # A service identity may only ever be scoped to the tenant database's
        # own company; a declaration that names another company is a different
        # authorization and is refused rather than narrowed silently.
        _fail("TPO_DECLARED_COMPANY_NOT_TENANT_COMPANY")
    plan = policy.plan_account_creation(declared=declared, company_ids=[company.id])
    internal = _xmlid_to_record(env, policy.INTERNAL_USER_GROUP_XMLID)
    if not internal:
        _fail("TPO_INTERNAL_USER_GROUP_MISSING")
    users = env["res.users"].sudo().with_context(active_test=False)
    existing = _xmlid_to_record(env, declared["identity_key"])
    created = False
    if existing:
        if existing._name != "res.users":
            _fail("TPO_IDENTITY_XMLID_ALREADY_TAKEN")
        if not policy.account_identity_matches(
            existing=read_operator(env, identity_xmlid=declared["identity_key"])["operator"],
            declared={
                "identity_key": declared["identity_key"],
                "login": declared["login"],
                "company_ids": [company.id],
                "expected_account_groups": declared["expected_account_groups"],
                # The reusable identity also carries whatever Odoo materialises
                # from the required groups; any other membership is a widened
                # identity and is refused, never adopted.
                "expected_implied_account_groups": _group_closure_xmlids(
                    env, [internal.id]
                ),
                "forbidden_account_groups": declared["forbidden_account_groups"],
            },
        ):
            # Same external id, different identity: refuse, never take over.
            _fail("TPO_EXISTING_IDENTITY_MISMATCH")
        user = existing
    else:
        taken = users.search([("login", "=", declared["login"])], limit=1)
        if taken:
            # A different account already owns the declared login; adopting it
            # would hand the grant to whatever that account already is.
            _fail("TPO_LOGIN_ALREADY_OWNED")
        user = users.with_context(no_reset_password=True).create(
            {
                "name": declared["name"],
                "login": declared["login"],
                "company_id": company.id,
                "company_ids": [Command.set([company.id])],
                "groups_id": [Command.set([internal.id])],
                "active": True,
            }
        )
        module, name = declared["identity_key"].split(".", 1)
        env["ir.model.data"].sudo().create(
            {
                "module": module,
                "name": name,
                "model": "res.users",
                "res_id": user.id,
                "noupdate": True,
            }
        )
        created = True
    readback = read_operator(env, identity_xmlid=declared["identity_key"])
    operator = readback["operator"] or {}
    if operator.get("has_native_api_keys"):
        # A machine credential would be a second, unreviewed channel; the
        # governed credential framework owns those and must issue them
        # explicitly, so the lifecycle never leaves a stray key behind.
        _fail("TPO_OPERATOR_HAS_UNMANAGED_API_KEY")
    readback["mode"] = "provision"
    # The readback part of this report wrote nothing; the lifecycle part did.
    readback["writes"] = 1 if created else 0
    readback["created"] = created
    readback["plan"] = plan
    readback["authorization"] = approval
    readback["interactive_login_capable"] = bool(operator.get("has_stored_password"))
    return readback


def assert_import_operator(env, *, identity_xmlid: str) -> dict:
    """Fail closed unless the declared identity may run a signed import."""
    readback = read_operator(env, identity_xmlid=identity_xmlid)
    operator = readback["operator"] or {}
    if not operator:
        _fail("TPO_OPERATOR_NOT_PROVISIONED")
    if operator.get("is_data_operator"):
        _fail("TPO_OPERATOR_IS_DATA_OPERATOR")
    if readback.get("importer_implied_xmlids"):
        _fail("TPO_IMPORTER_GROUP_IMPLIED_CLOSURE")
    if operator.get("has_stored_password"):
        _fail("TPO_OPERATOR_HAS_INTERACTIVE_CREDENTIAL")
    forbidden = set(operator.get("group_xmlids") or ()) & set(policy.FORBIDDEN_ACCOUNT_GROUPS)
    if forbidden:
        _fail("TPO_OPERATOR_HOLDS_FORBIDDEN_GROUP")
    return readback


def grant_import_scope(env, *, identity_xmlid: str, authorization: dict) -> dict:
    """Add the single narrow importer grant, with the contract's assertions.

    The grant is a maintenance operation in its own right, so it carries its own
    approval check: an access that authorized creating the identity is not read
    here as also authorizing the permission grant.
    """
    _assert_governed_principal(env)
    facts = authorization if isinstance(authorization, dict) else {}
    policy.validate_authorization(
        authorization,
        # The expectations come from the database being written, never from the
        # approval payload that wants the permission.
        db_name=env.cr.dbname,
        tenant_key=str(
            env["ir.config_parameter"].sudo().get_param("sc.tenant.bound_tenant_key", "") or ""
        ),
        identity_key=identity_xmlid,
        subject_checksum=facts.get("subject_checksum"),
        now=fields.Datetime.to_string(fields.Datetime.now()),
        action="grant",
    )
    before = assert_import_operator(env, identity_xmlid=identity_xmlid)
    importer = _xmlid_to_record(env, policy.IMPORTER_GROUP_XMLID)
    if not importer or importer._name != "res.groups":
        _fail("TPO_IMPORTER_GROUP_MISSING")
    user = _xmlid_to_record(env, identity_xmlid)
    if user.id == SUPERUSER_ID:
        _fail("TPO_SUPERUSER_TARGET_FORBIDDEN")
    groups_before = set(user.groups_id.ids)
    already = importer.id in groups_before
    if not already:
        user.write({"groups_id": [Command.link(importer.id)]})
        added = set(user.groups_id.ids) - groups_before
        if added != {importer.id}:
            _fail("TPO_GRANT_UNRELATED_MEMBERSHIP_CHANGED")
    groups_after = set(user.groups_id.ids)
    after = assert_import_operator(env, identity_xmlid=identity_xmlid)
    if not (after["operator"] or {}).get("is_importer"):
        _fail("TPO_GRANT_POSTCONDITION_FAILED")
    after["mode"] = "grant"
    after["writes"] = 0 if already else 1
    after["changed"] = not already
    after["granted_group_xmlid"] = policy.IMPORTER_GROUP_XMLID
    after["membership_before"] = len(groups_before)
    after["membership_after"] = len(groups_after)
    before["mode"] = "read_only"
    return {"before": before, "after": after}


def revoke_import_scope(env, *, identity_xmlid: str) -> dict:
    """Remove the permission, keep the account and its audit association."""
    _assert_governed_principal(env)
    readback = read_operator(env, identity_xmlid=identity_xmlid)
    user = _xmlid_to_record(env, identity_xmlid)
    if not user or user._name != "res.users":
        _fail("TPO_OPERATOR_NOT_PROVISIONED")
    importer = _xmlid_to_record(env, policy.IMPORTER_GROUP_XMLID)
    if not importer:
        _fail("TPO_IMPORTER_GROUP_MISSING")
    if importer.id not in user.groups_id.ids:
        readback["mode"] = "revoke"
        readback["writes"] = 0
        readback["changed"] = False
        return readback
    groups_before = set(user.groups_id.ids)
    # The res.users write bumps token_version, which invalidates every issued
    # session for this principal before the next one can act.
    user.write({"groups_id": [Command.unlink(importer.id)]})
    groups_after = set(user.groups_id.ids)
    if groups_before - groups_after != {importer.id}:
        _fail("TPO_REVOKE_UNRELATED_MEMBERSHIP_CHANGED")
    after = read_operator(env, identity_xmlid=identity_xmlid)
    if (after["operator"] or {}).get("is_importer"):
        _fail("TPO_REVOKE_POSTCONDITION_FAILED")
    after["mode"] = "revoke"
    after["writes"] = 1
    after["changed"] = True
    after["revoked_group_xmlid"] = policy.IMPORTER_GROUP_XMLID
    return after
