"""Product-neutral, immutable data-space purpose vocabulary.

The persisted authority is sc.tenant.company.registration. Neither a database
name nor a fixture XMLID establishes authorization.
"""

CUSTOMER_PURPOSE = "customer"
NON_CUSTOMER_PURPOSES = ("demo", "test")
DATA_PURPOSES = (CUSTOMER_PURPOSE, *NON_CUSTOMER_PURPOSES)
NON_CUSTOMER_DATA_USER_GROUP = "smart_core.group_smart_core_non_customer_data_user"


def principal_data_purposes(*, platform_admin, non_customer_user):
    """A non-customer identity never also receives the customer data realm."""
    if platform_admin or non_customer_user:
        return NON_CUSTOMER_PURPOSES
    return (CUSTOMER_PURPOSE,)


def validate_customer_registration(values):
    """The signed customer importer cannot manufacture a non-customer scope."""
    if values.get("data_purpose", CUSTOMER_PURPOSE) != CUSTOMER_PURPOSE:
        raise ValueError("DATA_SPACE_CUSTOMER_IMPORT_PURPOSE_REQUIRED")


def validate_non_customer_creation(*, uid, superuser_id, su, purpose, tenant_key):
    # sudo() preserves uid: a product administrator invoking an elevated
    # internal service is not the governed superuser maintenance principal.
    if uid != superuser_id or not su:
        raise PermissionError("DATA_SPACE_MAINTENANCE_PRINCIPAL_REQUIRED")
    if purpose not in NON_CUSTOMER_PURPOSES:
        raise ValueError("DATA_SPACE_NON_CUSTOMER_PURPOSE_REQUIRED")
    if not isinstance(tenant_key, str) or not tenant_key.strip():
        raise ValueError("DATA_SPACE_TENANT_KEY_REQUIRED")


def registration_scope_domain(company_ids, purposes):
    """Empty company authorization remains empty; unknown data is never public."""
    return [
        ("active", "=", True),
        ("data_purpose", "in", list(purposes)),
        ("company_id", "in", list(company_ids)),
        ("company_id.is_platform_bootstrap_company", "=", False),
    ]
