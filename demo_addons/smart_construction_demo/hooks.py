# -*- coding: utf-8 -*-
import os


ENVIRONMENT_ROLE = "platform_internal_demo"
DEMO_TENANT_KEY = "sc-demo-main"
DEMO_DATA_MODULE = "smart_construction_demo"
DEMO_COMPANY_NAME = "四川智汇某某建设集团有限公司"
# The demo tenant is a group, not a single legal entity.  The second company is
# a real operating subsidiary of the same tenant, never an acceptance fixture
# and never a visible "demo 2" label.
DEMO_COMPANY_SECOND_NAME = "四川智汇某某建设集团第二工程有限公司"
DEMO_COMPANY_SECOND_XMLID = "smart_construction_demo.demo_company_second"
# Group-level seats that must be able to switch into the subsidiary.  Project
# staff deliberately stay scoped to the main company so the demo shows a real
# multi-company boundary instead of giving everybody every company.
DEMO_COMPANY_SECOND_MEMBER_LOGINS = (
    "admin",
    "wutao",
    "demo_full",
    "demo_role_owner",
    "demo_role_executive",
    "fin_mgr",
    "fin1",
    "demo_finance",
    "demo_audit",
    "sc_demo_accounting_manager",
    "sc_demo_business_config",
    "sc_demo_operation",
)
DEMO_COMPANY_IDENTITY = {
    "email": "info@zhihui-construction.cn",
    "phone": "028-8601 2000",
    "website": "https://www.zhihui-construction.cn",
    "street": "天府大道中段 1388 号",
    "city": "成都",
    "zip": "610041",
}
DEMO_COMPANY_SECOND_IDENTITY = {
    "email": "gc2@zhihui-construction.cn",
    "phone": "028-8601 2100",
    "website": "https://www.zhihui-construction.cn",
    "street": "天府大道中段 1388 号",
    "city": "成都",
    "zip": "610041",
}
# The showcase deliberately uses one simple password for every seeded demo
# identity. Keeping it in the carrier, rather than only in the host secret,
# makes a rebuild or reseed reproduce the published demo login.
DEMO_USER_PASSWORD = "123456"
# Principals authored by the seed chain rather than by module XML. They still
# belong to the published demo surface, so every password hook and self-check
# has to include them explicitly.
DEMO_PRINCIPAL_LOGINS = (
    "wutao",
    "demo_full",
    "demo_pm",
    "demo_finance",
    "demo_cost",
    "demo_audit",
    "demo_readonly",
    "sc_test_admin",
)


def assert_demo_seed_principal(env):
    """Only the managed installation/shell principal may delegate demo actions."""
    from odoo import SUPERUSER_ID
    from odoo.exceptions import AccessError

    if env.uid != SUPERUSER_ID or not env.su:
        raise AccessError("DEMO_SEED_PRINCIPAL_REQUIRED")


def guard_demo_scope(env):
    db_name = str(env.cr.dbname or "").strip()
    if not (
        db_name in {"sc_demo", "sc_dev_demo"} or db_name.startswith("sc_demo_")
    ):
        raise RuntimeError("smart_construction_demo requires an authorized demo database")
    if os.environ.get("SC_ENVIRONMENT") != "demo":
        raise RuntimeError("smart_construction_demo requires SC_ENVIRONMENT=demo")
    if os.environ.get("SC_ALLOW_DEMO_DATA") != "1":
        raise RuntimeError("smart_construction_demo requires SC_ALLOW_DEMO_DATA=1")
    if not str(os.environ.get("SC_DEMO_USER_PASSWORD") or "").strip():
        raise RuntimeError("smart_construction_demo requires SC_DEMO_USER_PASSWORD")


def onboard_platform_data_space(env):
    """Onboard this demo database's main company as the demo data space.

    Owner ruling DEMO_IS_FIRST_ONBOARDED_COMPANY: in the demo role the
    environment main company IS the first onboarded business company, so demo
    seeding runs only after that company owns a registration instead of a
    technical-carrier marker. Re-runs are idempotent and the marketing/demo
    lane never manufactures its own registration.

    Onboarding is not complete with the registration row: the demo's operating
    identities must also be enrolled into the non-customer data realm, or the
    data space exists and nobody can read it. Identity enrollment is therefore
    part of this same idempotent act, never a per-user assembly in demo data.
    """
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    provisioning.declare_environment_role(env, ENVIRONMENT_ROLE)
    if not provisioning.onboarded_registrations(env, purpose="demo"):
        provisioning.onboard_environment_main_company(env, tenant_key=DEMO_TENANT_KEY)
    return provisioning.enroll_data_space_identities(env, purpose="demo")


def guard_demo_data_space(env):
    """A demo database seeds only against a retired bootstrap marker."""
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    onboard_platform_data_space(env)
    provisioning.assert_business_data_space_ready(env, purpose="demo")
    provisioning.assert_data_space_identities_enrolled(env, purpose="demo")
    carriers = provisioning.bootstrap_company_ids(env)
    if carriers:
        raise RuntimeError(
            "smart_construction_demo requires a retired bootstrap marker, still: %s"
            % (carriers,)
        )


def apply_demo_company_identity(env):
    """Give the demo's main company its published identity, idempotently.

    The company name is part of the published surface, so a rebuilt or upgraded
    demo must never fall back to "My Company" or an old "Demo演示公司" label.
    Country, contact and website values are converged in the same act because a
    Chinese construction group with an empty/US identity is visibly incomplete.
    """
    company = env.ref("base.main_company")
    country = env.ref("base.cn", raise_if_not_found=False)
    country_id = getattr(country, "id", False)
    values = {"name": DEMO_COMPANY_NAME, **DEMO_COMPANY_IDENTITY}
    if country_id:
        values["country_id"] = country_id
    patch = _changed_values(company, values)
    if patch:
        company.write(patch)
    partner = company.partner_id
    partner_values = {"name": DEMO_COMPANY_NAME, **DEMO_COMPANY_IDENTITY}
    if country_id:
        partner_values["country_id"] = country_id
    partner_patch = _changed_values(partner, partner_values)
    if partner_patch:
        partner.write(partner_patch)
    return company


def _changed_values(record, values):
    """Return only the fields a record can carry and that still differ.

    Comparing a many2one recordset with an integer id would always look
    different, so the current value is reduced to its id first.  Fields the
    record does not implement are skipped, which keeps the function usable with
    the lightweight fakes in the offline tests.
    """
    patch = {}
    for field, value in values.items():
        if not hasattr(record, field):
            continue
        current = getattr(record, field)
        if hasattr(current, "id"):
            current = current.id
        if current != value:
            patch[field] = value
    return patch


def _find_or_create_second_company(env):
    """Resolve the second demo company by stable XMLID, never by hardcoded id."""
    Company = env["res.company"].sudo()
    Data = env["ir.model.data"].sudo()
    xmlid = Data.search([
        ("module", "=", DEMO_DATA_MODULE),
        ("name", "=", "demo_company_second"),
        ("model", "=", "res.company"),
    ], limit=1)
    company = Company.browse()
    if xmlid:
        company = Company.browse(xmlid.res_id).exists()
        if not company:
            xmlid.unlink()
            xmlid = Data.browse()
    if not company:
        matches = Company.search([("name", "=", DEMO_COMPANY_SECOND_NAME)])
        if len(matches) > 1:
            raise RuntimeError(
                "DEMO_COMPANY_SECOND_NAME_AMBIGUOUS:%s:%s"
                % (DEMO_COMPANY_SECOND_NAME, len(matches))
            )
        company = matches
    if not company:
        vals = {
            "name": DEMO_COMPANY_SECOND_NAME,
            "parent_id": env.ref("base.main_company").id,
        }
        currency = env.ref("base.CNY", raise_if_not_found=False)
        if currency:
            vals["currency_id"] = currency.id
        country = env.ref("base.cn", raise_if_not_found=False)
        if country:
            vals["country_id"] = country.id
        company = Company.create(vals)
    if not xmlid:
        Data.create({
            "module": DEMO_DATA_MODULE,
            "name": "demo_company_second",
            "model": "res.company",
            "res_id": company.id,
            "noupdate": True,
        })
    return company


def apply_demo_company_secondary(env):
    """Create or converge the demo group's second operating company.

    The company is a child of the environment main company, uses the same CNY
    currency and the Chinese country record, and is found through its stable
    XMLID.  Re-running the seed or rebuilding the demo therefore converges the
    same row instead of creating a duplicate company.
    """
    company = _find_or_create_second_company(env)
    main = env.ref("base.main_company")
    currency = env.ref("base.CNY", raise_if_not_found=False)
    country = env.ref("base.cn", raise_if_not_found=False)
    values = {
        "name": DEMO_COMPANY_SECOND_NAME,
        "parent_id": main.id,
        **DEMO_COMPANY_SECOND_IDENTITY,
    }
    if currency:
        values["currency_id"] = currency.id
    if country:
        values["country_id"] = country.id
    patch = _changed_values(company, values)
    if patch:
        company.write(patch)
    partner = company.partner_id
    partner_values = {"name": DEMO_COMPANY_SECOND_NAME, **DEMO_COMPANY_SECOND_IDENTITY}
    if country:
        partner_values["country_id"] = country.id
    partner_patch = _changed_values(partner, partner_values)
    if partner_patch:
        partner.write(partner_patch)
    return company


def register_demo_company_secondary(env, company):
    """Register the second company as a demo data space, idempotently.

    ``_sc_data_company_ids`` only returns companies with an active registration,
    so an unregistered second company would switch to an empty surface and any
    row created there would be invisible.  Registration is the platform's
    ownership anchor, not a demo shortcut, and it stays under the same tenant
    key as the main company.
    """
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    Registrations = env["sc.tenant.company.registration"].sudo().with_context(
        active_test=False
    )
    if Registrations.search_count([("company_id", "=", company.id)]):
        return False
    if not getattr(env, "su", False):
        raise RuntimeError("DEMO_COMPANY_SECOND_REGISTRATION_REQUIRES_SYSTEM_PRINCIPAL")
    provisioning.adopt_business_company(
        env,
        tenant_key=DEMO_TENANT_KEY,
        purpose="demo",
        company_id=company.id,
    )
    return True


def demo_user_records(env):
    """Every user owned by the demo module or named as a demo principal.

    ``demo_full`` and the role seats are authored by the seed chain instead of
    XML, so selecting only ``ir.model.data`` rows would leave them on an older
    password after a reseed or rebuild.
    """
    Users = env["res.users"].sudo().with_context(active_test=False)
    rows = env["ir.model.data"].sudo().search(
        [("module", "=", DEMO_DATA_MODULE), ("model", "=", "res.users")]
    )
    users = Users.browse([row.res_id for row in rows.exists()]).exists()
    for login in DEMO_PRINCIPAL_LOGINS:
        users |= Users.search([("login", "=", login)], limit=1)
    return users.exists()


DEMO_ADMIN_LOGIN = "admin"


def demo_admin_record(env):
    """The published demo admin login, or ``None`` when that login was renamed.

    ``admin`` is ``base.user_admin``: the demo module owns no XML record for it,
    so ``demo_user_records`` never selected it and a rebuild from
    ``--without-demo=all`` kept whatever ``base`` created. It is still part of
    the published demo surface, so the password hook and the seed self-check
    name it through this one accessor instead of widening the module's XML
    ownership.
    """
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    if not admin or admin.login != DEMO_ADMIN_LOGIN:
        return None
    return admin


def apply_demo_admin_password(env):
    """Give the published demo admin login the showcase password.

    ``guard_demo_scope`` runs first and refuses every database that is not a
    demo duty, so this write can never reach the platform duty's admin login.
    A renamed ``base.user_admin`` is left alone rather than rewritten, so the
    hook never turns an operator's login change into a published credential.
    """
    guard_demo_scope(env)
    admin = demo_admin_record(env)
    if admin is None:
        return None
    if admin.login != DEMO_ADMIN_LOGIN:
        return None
    admin.sudo().write({"password": DEMO_USER_PASSWORD})
    return admin


def apply_demo_user_passwords(env):
    guard_demo_scope(env)
    guard_demo_data_space(env)
    users = demo_user_records(env)
    if users:
        users.write({"password": DEMO_USER_PASSWORD})
    apply_demo_admin_password(env)


def pre_init_hook(env):
    guard_demo_scope(env)
    guard_demo_data_space(env)


def post_init_hook(env):
    apply_demo_company_identity(env)
    apply_demo_user_passwords(env)
