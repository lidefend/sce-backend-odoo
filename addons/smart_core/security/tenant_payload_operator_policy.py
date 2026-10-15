"""Pure decision rules for the narrow signed-payload import operator.

Owner ruling (2026-10-15): the unified onboarding mechanism owns the import
operator's account lifecycle, and the customer module must not create platform
operators.  The platform product therefore owns two things and nothing else:

* a *declaration* contract -- the duty declaration carries the tenant
  difference (which identity, which login, which company, which authority),
  so the mechanism never learns a tenant name from code;
* an *authorization binding* -- a list of facts the approver signed off on,
  which the mechanism refuses to act without.

The rules are deliberately kept free of ``odoo`` imports, exactly like
``database_governance.py``, so a pure decision test can load this module
directly and the expensive ORM layer stays thin.

Three refusals are the whole point of this module, and none of them may be
relaxed to make a check pass:

* a service identity is never bound to an administrator group;
* an existing account whose identity does not match the declaration is never
  taken over;
* the authorization facts are never inferred from the declaration -- a missing
  or mismatched approval is a stop, because the declaration is written by the
  same side that would benefit from it.
"""

from __future__ import annotations

import re

SCHEMA_VERSION = "tenant_payload_operator.v1"

#: The existing maintenance capability a historical payload import runs under.
#: The import *is* a governed data migration, so it reuses that vocabulary
#: instead of inventing a parallel one.
IMPORT_CAPABILITY = "migrate"

IMPORTER_GROUP_XMLID = "smart_core.group_smart_core_tenant_payload_importer"
INTERNAL_USER_GROUP_XMLID = "base.group_user"
DATA_OPERATOR_GROUP_XMLID = "smart_core.group_smart_core_data_operator"

#: An import operator is an ordinary internal principal plus the narrow
#: importer group.  Nothing else may be added by this mechanism.
REQUIRED_ACCOUNT_GROUPS = (INTERNAL_USER_GROUP_XMLID,)
FORBIDDEN_ACCOUNT_GROUPS = (
    "base.group_system",
    "base.group_erp_manager",
    "base.group_allow_export",
    "smart_core.group_smart_core_admin",
    "smart_core.group_smart_core_security_admin",
    "smart_core.group_smart_core_business_config_admin",
    DATA_OPERATOR_GROUP_XMLID,
)

#: Groups this mechanism may ever add, and the only one it adds.
GRANTABLE_GROUP_XMLIDS = (IMPORTER_GROUP_XMLID,)

XMLID = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
LOGIN = re.compile(r"^[a-z][a-z0-9_.-]{2,62}$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class OperatorPolicyError(ValueError):
    """A stop: the mechanism refuses to continue rather than guess a fact."""


def _fail(rule: str) -> None:
    raise OperatorPolicyError(rule)


def _text(value) -> str:
    return str(value or "").strip()


def _xmlid_list(block: dict, key: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    values = block.get(key)
    if values is None and allow_empty:
        return ()
    if not isinstance(values, list) or (not values and not allow_empty):
        _fail("DECLARATION_%s_INVALID" % key.upper())
    for value in values:
        if not isinstance(value, str) or not XMLID.fullmatch(value.strip()):
            _fail("DECLARATION_%s_INVALID" % key.upper())
    normalized = tuple(sorted(set(value.strip() for value in values)))
    if len(normalized) != len(values):
        _fail("DECLARATION_%s_INVALID" % key.upper())
    return normalized


def validate_declaration(block) -> dict:
    """Normalize one duty's ``payload_operator`` declaration.

    The declaration is the *only* place a tenant difference may live: the
    mechanism reads the identity, the login, the company and the authority from
    here and carries no tenant name of its own.
    """
    if not isinstance(block, dict):
        _fail("DECLARATION_MISSING")
    allowed_carriers = ("unified_onboarding_service_identity",)
    if _text(block.get("carrier")) not in allowed_carriers:
        _fail("DECLARATION_CARRIER_UNSUPPORTED")
    identity_key = _text(block.get("identity_key"))
    if not XMLID.fullmatch(identity_key):
        _fail("DECLARATION_IDENTITY_KEY_INVALID")
    declared_module = identity_key.split(".", 1)[0]
    if declared_module == "base":
        # A mechanism that may bind itself to a core account can silently take
        # over an administrator; the identity must be owned by the mechanism.
        _fail("DECLARATION_IDENTITY_MODULE_FORBIDDEN")
    login = _text(block.get("login"))
    if not LOGIN.fullmatch(login):
        _fail("DECLARATION_LOGIN_INVALID")
    name = _text(block.get("name"))
    if not name:
        _fail("DECLARATION_NAME_MISSING")
    company_xmlid = _text(block.get("company_xmlid"))
    if not company_xmlid:
        # The company the operator may act for is part of what the approver
        # signs off on, so it is declared, never defaulted to "whatever company
        # happens to be first".
        _fail("DECLARATION_COMPANY_XMLID_MISSING")
    if not XMLID.fullmatch(company_xmlid):
        _fail("DECLARATION_COMPANY_XMLID_INVALID")
    authorization_basis = _text(block.get("authorization_basis"))
    if not authorization_basis:
        _fail("DECLARATION_AUTHORIZATION_BASIS_MISSING")
    groups = _xmlid_list(block, "expected_account_groups")
    if groups != tuple(sorted(REQUIRED_ACCOUNT_GROUPS)):
        _fail("DECLARATION_ACCOUNT_GROUPS_NOT_MINIMAL")
    forbidden = set(_xmlid_list(block, "forbidden_account_groups", allow_empty=True))
    if forbidden != set(FORBIDDEN_ACCOUNT_GROUPS):
        _fail("DECLARATION_FORBIDDEN_GROUPS_INCOMPLETE")
    if set(groups) & forbidden:
        _fail("DECLARATION_ACCOUNT_GROUPS_CONFLICT")
    capability = _text(block.get("import_capability"))
    if not capability:
        _fail("DECLARATION_IMPORT_CAPABILITY_MISSING")
    if capability != IMPORT_CAPABILITY:
        _fail("DECLARATION_IMPORT_CAPABILITY_INVALID")
    return {
        "carrier": _text(block.get("carrier")),
        "identity_key": identity_key,
        "login": login,
        "name": name,
        "company_xmlid": company_xmlid,
        "authorization_basis": authorization_basis,
        "import_capability": capability,
        "expected_account_groups": list(groups),
        "forbidden_account_groups": list(forbidden),
        "grantable_group_xmlids": list(GRANTABLE_GROUP_XMLIDS),
    }


def account_identity_matches(*, existing: dict, declared: dict) -> bool:
    """Whether an existing account may be reused instead of taken over.

    Idempotency and takeover are the same question asked twice: re-running the
    provision on the account it created must be a no-op, while an account that
    merely shares the declared login or external id must be refused.  Both are
    answered by comparing the *whole* identity, never the login alone.
    """
    if not isinstance(existing, dict) or not isinstance(declared, dict):
        _fail("IDENTITY_COMPARISON_INVALID")
    if _text(existing.get("xmlid")) != _text(declared.get("identity_key")):
        return False
    if _text(existing.get("login")) != _text(declared.get("login")):
        return False
    if existing.get("active") is not True:
        return False
    if bool(existing.get("share")):
        return False
    if bool(existing.get("has_stored_password")):
        # The operator is reachable only through the governed maintenance
        # entry; an interactive password is an unreviewed second channel.
        return False
    company_ids = tuple(sorted(int(value) for value in (existing.get("company_ids") or ())))
    if company_ids != tuple(sorted(int(value) for value in (declared.get("company_ids") or ()))):
        return False
    # Odoo completes an account's membership with the *transitive implied
    # closure* of the groups it is created with (``UsersImplied.create``), so
    # the reusable identity is the required groups plus the platform's own
    # closure of them -- and nothing else.  The closure is environment
    # knowledge, so the caller supplies it; leaving it out means "the required
    # groups only", which stays the strict reading.
    groups = set(existing.get("group_xmlids") or ())
    required = set(declared.get("expected_account_groups") or ())
    implied = set(declared.get("expected_implied_account_groups") or ())
    if required - groups:
        return False
    if groups - (required | implied):
        # A membership this mechanism never grants appeared: that is a widened
        # identity, not the one the declaration describes, so it is refused
        # rather than taken over.
        return False
    if groups & set(declared.get("forbidden_account_groups") or ()):
        return False
    return True


def validate_authorization(
    authorization,
    *,
    db_name: str,
    tenant_key: str,
    identity_key: str,
    subject_checksum,
    now,
    action: str,
) -> dict:
    """Refuse to act without an independent, in-window approval.

    The approval record lives where the platform is the authority over the
    fact (the platform control database) and binds the target tenant, the
    database, the operator, the permission scope, the subject digest and the
    validity window.  This function only *checks* those facts; it never
    derives them from the declaration and never invents a value.

    ``action`` is the operation this caller is about to execute and is a
    required argument: the caller must state what it is about to do before the
    approval can be read.  The approval must name that operation, because a
    capability is not a grant -- an access that authorizes one operation can
    never be read as authorizing another.
    """
    if not isinstance(authorization, dict):
        _fail("AUTHORIZATION_MISSING")
    expected = {
        "db_name": _text(db_name),
        "tenant_key": _text(tenant_key),
        "operator_identity_key": _text(identity_key),
        "capability": IMPORT_CAPABILITY,
        "state": "approved",
    }
    for key, value in expected.items():
        if not value:
            _fail("AUTHORIZATION_FACT_MISSING:%s" % key)
        if _text(authorization.get(key)) != value:
            _fail("AUTHORIZATION_FACT_MISMATCH:%s" % key)
    # The digest is *recorded*, not compared against an expectation: binding it
    # to the payload being imported is the caller's duty, and comparing it here
    # against a value the same caller supplied would check nothing.
    digest = _text(subject_checksum)
    if not SHA256_HEX.fullmatch(digest):
        _fail("AUTHORIZATION_SUBJECT_CHECKSUM_INVALID")
    approver = _text(authorization.get("approved_by"))
    if not approver:
        # Never fabricate an approval identity; an empty approver is a stop.
        _fail("AUTHORIZATION_APPROVER_MISSING")
    requested_by = _text(authorization.get("requested_by"))
    if requested_by and requested_by == approver:
        _fail("AUTHORIZATION_APPROVER_NOT_INDEPENDENT")
    valid_from = _text(authorization.get("valid_from"))
    valid_until = _text(authorization.get("valid_until"))
    if not valid_from or not valid_until:
        _fail("AUTHORIZATION_VALIDITY_MISSING")
    current = _text(now)
    if not (valid_from <= current < valid_until):
        _fail("AUTHORIZATION_OUT_OF_WINDOW")
    access_id = authorization.get("access_id")
    if not isinstance(access_id, int) or isinstance(access_id, bool) or access_id <= 0:
        _fail("AUTHORIZATION_ACCESS_ID_INVALID")
    operations = authorization.get("authorized_operations")
    if not isinstance(operations, list) or not all(
        isinstance(item, str) for item in operations
    ):
        _fail("AUTHORIZATION_OPERATIONS_MISSING")
    covered = [item for item in operations if item]
    if not covered:
        _fail("AUTHORIZATION_OPERATIONS_MISSING")
    requested = _text(action)
    if not requested:
        _fail("AUTHORIZATION_ACTION_MISSING")
    if requested not in covered:
        _fail("AUTHORIZATION_OPERATION_NOT_COVERED:%s" % requested)
    return {
        "access_id": access_id,
        "db_name": expected["db_name"],
        "tenant_key": expected["tenant_key"],
        "operator_identity_key": expected["operator_identity_key"],
        "capability": expected["capability"],
        "subject_checksum": digest,
        "approved_by": approver,
        "requested_by": requested_by,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "authorized_operations": covered,
    }


def plan_account_creation(*, declared: dict, company_ids) -> dict:
    """The account this mechanism may create, as a reviewable plan."""
    company_scope = tuple(sorted({int(value) for value in (company_ids or ())}))
    if len(company_scope) != 1:
        # The operator exists to serve one tenant; a wider company scope is a
        # different authorization and must not be created silently.
        _fail("ACCOUNT_COMPANY_SCOPE_NOT_SINGLE")
    if not declared.get("identity_key") or not declared.get("login"):
        _fail("DECLARATION_MISSING")
    return {
        "schema_version": SCHEMA_VERSION,
        "identity_key": declared["identity_key"],
        "login": declared["login"],
        "name": declared["name"],
        "share": False,
        "active": True,
        "usable_password": False,
        "interactive_login": False,
        "company_ids": list(company_scope),
        "group_xmlids": list(REQUIRED_ACCOUNT_GROUPS),
        "grantable_group_xmlids": list(GRANTABLE_GROUP_XMLIDS),
        "forbidden_group_xmlids": list(FORBIDDEN_ACCOUNT_GROUPS),
    }
