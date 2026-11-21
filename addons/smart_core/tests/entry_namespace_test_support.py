"""Shared entry-namespace setup for smart_core HTTP and platform tests."""

import hashlib


TEST_ENTRY_SECRET = "smart-core-entry-test-secret"
TEST_ROUTE_VERSION = "smart-core-entry-test-v1"


def configure_test_entry_namespace(
    env,
    *,
    alias,
    audience,
    duty_key,
    platform_control=False,
):
    """Bind this disposable test database to one governed entry namespace."""
    database = str(env.cr.dbname)
    Namespace = env["sc.platform.namespace"].sudo()
    namespace = Namespace.search([("database_name", "=", database)], limit=1)
    values = {
        "display_name": "smart_core test entry",
        "lifecycle_state": "active",
        "database_name": database,
        "duty_key": duty_key,
        "audience": audience,
    }
    if namespace:
        namespace.write(values)
    else:
        namespace = Namespace.create({
            "namespace_id": "ns_" + hashlib.sha256(
                database.encode("utf-8")
            ).hexdigest()[:12],
            **values,
        })

    Alias = env["sc.platform.namespace.alias"].sudo()
    namespace_alias = Alias.search([
        ("alias", "=", alias),
        ("alias_kind", "=", "path"),
    ], limit=1)
    alias_values = {
        "namespace_id": namespace.id,
        "is_primary": True,
    }
    if namespace_alias:
        namespace_alias.write(alias_values)
    else:
        Alias.create({
            "alias": alias,
            "alias_kind": "path",
            **alias_values,
        })

    params = env["ir.config_parameter"].sudo()
    params.set_param("sc.entry.shared_secret", TEST_ENTRY_SECRET)
    params.set_param("sc.entry.route_version", TEST_ROUTE_VERSION)
    if platform_control:
        params.set_param("sc.platform.control_db", database)
    return {
        "X-SC-Namespace": alias,
        "X-SC-Audience": audience,
        "X-SC-Route-Version": TEST_ROUTE_VERSION,
        "X-SC-Entry-Secret": TEST_ENTRY_SECRET,
    }
