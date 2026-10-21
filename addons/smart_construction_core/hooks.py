# -*- coding: utf-8 -*-
import zlib
from odoo import SUPERUSER_ID, api


REQUIRED_CORE_TAXES = (
    ("销项VAT 9%", 9.0, "sale"),
    ("进项VAT 13%", 13.0, "purchase"),
)


def _tax_key(company_id, type_tax_use, name, amount, amount_type, price_include=False):
    raw = f"{company_id}|{type_tax_use}|{amount_type}|{amount}|{int(bool(price_include))}|{name}".encode("utf-8")
    return zlib.crc32(raw) & 0xFFFFFFFF


def _advisory_xact_lock(cr, key_int):
    cr.execute("SELECT pg_advisory_xact_lock(%s)", (int(key_int),))


def _find_or_create_tax(
    env,
    *,
    company,
    type_tax_use,
    name,
    amount,
    amount_type="percent",
    price_include=False,
    tax_group=None,
    country=None,
):
    """Idempotent tax getter with tx-level lock to avoid duplicate create under concurrency."""
    Tax = env["account.tax"].with_context(active_test=False).sudo()
    domain = [
        ("company_id", "=", company.id),
        ("type_tax_use", "=", type_tax_use),
        ("amount_type", "=", amount_type),
        ("amount", "=", amount),
        ("price_include", "=", bool(price_include)),
        ("name", "=", name),
    ]
    tax = Tax.search(domain, limit=1)
    if tax:
        return tax

    legacy_domain = [
        ("company_id", "=", company.id),
        ("type_tax_use", "=", type_tax_use),
        ("amount_type", "=", amount_type),
        ("amount", "=", amount),
        ("price_include", "=", bool(price_include)),
    ]
    legacy_tax = Tax.search(legacy_domain, order="active desc, id asc", limit=1)
    if legacy_tax:
        return legacy_tax

    lock_key = _tax_key(company.id, type_tax_use, name, amount, amount_type, price_include)
    _advisory_xact_lock(env.cr, lock_key)

    tax = Tax.search(domain, limit=1)
    if tax:
        return tax

    legacy_tax = Tax.search(legacy_domain, order="active desc, id asc", limit=1)
    if legacy_tax:
        return legacy_tax

    vals = {
        "name": name,
        "amount_type": amount_type,
        "amount": amount,
        "type_tax_use": type_tax_use,
        "price_include": bool(price_include),
        "company_id": company.id,
        "active": True,
    }
    if tax_group:
        vals["tax_group_id"] = tax_group.id
    if country:
        vals["country_id"] = country.id
    return Tax.create(vals)


def ensure_core_taxes(env_or_cr, registry=None):
    """Guarantee税组与税率存在，即便被意外删除也能自愈."""
    if registry:
        env = api.Environment(env_or_cr, SUPERUSER_ID, {})
    else:
        env = env_or_cr
    company = env.ref("base.main_company")
    country = env.ref("base.cn", raise_if_not_found=False)

    tax_group_vals = {
        "name": "增值税",
        "sequence": 10,
        "company_id": company.id,
    }
    if country:
        tax_group_vals["country_id"] = country.id
    tax_group = (
        env["account.tax.group"]
        .sudo()
        .with_context(active_test=False)
        .search(
            [
                ("name", "=", tax_group_vals["name"]),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
    )
    if not tax_group:
        tax_group = env["account.tax.group"].sudo().create(tax_group_vals)

    # Neutral contract reference rates belong to smart_construction_seed.
    # Core owns only the two operational sale/purchase defaults below.
    tax_defs = list(REQUIRED_CORE_TAXES)
    for name, amount, tax_use in tax_defs:
        tax = _find_or_create_tax(
            env,
            company=company,
            type_tax_use=tax_use,
            name=name,
            amount=amount,
            amount_type="percent",
            price_include=False,
            tax_group=tax_group,
            country=country,
        )


def post_init_hook(env):
    """Install-time hook to ensure core taxes are present."""
    ensure_core_taxes(env)
    _ensure_signup_defaults(env)
    _ensure_chinese_translations(env)


def _ensure_chinese_translations(env):
    """Ensure zh_CN language is active and translations are loaded.

    Odoo's base module ships complete zh_CN translations (including
    res.partner.industry), but they are not automatically loaded into
    the database unless the language is explicitly installed/updated.
    This function activates zh_CN and forces a translation reload so
    that all translatable fields (industry names, selection labels, etc.)
    display correctly in Chinese.

    Idempotent: uses ir.config_parameter to track whether translations
    have been loaded for the current base module version.
    """
    ICP = env["ir.config_parameter"].sudo()
    Lang = env["res.lang"].sudo()
    Module = env["ir.module.module"].sudo()

    # Activate zh_CN if not already active
    zh_cn = Lang.search([("code", "=", "zh_CN")], limit=1)
    if zh_cn and not zh_cn.active:
        zh_cn.write({"active": True})
    elif not zh_cn:
        # Language record doesn't exist yet; activate via the standard
        # Odoo language installation wizard
        Lang._activate_lang("zh_CN")

    # Check if translations have already been loaded for the current base version
    base_module = Module.search([("name", "=", "base")], limit=1)
    base_version = base_module.latest_version if base_module else "unknown"
    loaded_version = ICP.get_param("sc.i18n.zh_cn.loaded_for_base_version", "")

    if loaded_version == base_version:
        return

    # Force reload of zh_CN translations for all installed modules
    # This is equivalent to running: odoo -d <db> -u all --i18n-overwrite
    # but scoped to zh_CN only
    installed_modules = Module.search([("state", "=", "installed")])
    for module in installed_modules:
        try:
            module._update_translations("zh_CN")
        except Exception:
            # Individual module translation failures should not block
            # the overall initialization; log and continue
            pass

    # Record that translations have been loaded
    ICP.set_param("sc.i18n.zh_cn.loaded_for_base_version", base_version)


def _ensure_cny_company_currency(env):
    """The business product is RMB-only for users; keep company defaults aligned."""
    env["res.company"]._sc_ensure_cny_currency()


def _archive_default_project_stages(env):
    """Archive Odoo default project stages to keep lifecycle stages canonical."""
    Stage = env["project.project.stage"].sudo()
    builtin_names = [
        "To Do",
        "In Progress",
        "Done",
        "Canceled",
        "Cancelled",
        "New",
    ]
    for name in builtin_names:
        stages = Stage.search([("name", "ilike", name), ("active", "=", True)])
        if stages:
            stages.write({"active": False})


def _ensure_signup_defaults(env):
    """Seed signup defaults once; never override explicit operator config."""
    ICP = env["ir.config_parameter"].sudo()
    if not ICP.get_param("sc.signup.mode"):
        login_env = ICP.get_param("sc.login.env", "prod")
        mode = "invite" if login_env in ("prod", "production") else "open"
        ICP.set_param("sc.signup.mode", mode)

    if ICP.get_param("sc.signup.require_email_verify") in (None, False, ""):
        ICP.set_param("sc.signup.require_email_verify", "true")
    if ICP.get_param("sc.signup.default_group_xmlids") in (None, False, ""):
        ICP.set_param("sc.signup.default_group_xmlids", "base.group_portal")
    if ICP.get_param("sc.signup.domain_whitelist") in (None, False):
        ICP.set_param("sc.signup.domain_whitelist", "")
    if ICP.get_param("sc.signup.recaptcha.mode") in (None, False, ""):
        ICP.set_param("sc.signup.recaptcha.mode", "soft")
    if ICP.get_param("sc.signup.token_expiration_hours") in (None, False, ""):
        ICP.set_param("sc.signup.token_expiration_hours", "24")
    if ICP.get_param("sc.signup.ratelimit.window_sec") in (None, False, ""):
        ICP.set_param("sc.signup.ratelimit.window_sec", "60")
    if ICP.get_param("sc.signup.ratelimit.max_per_ip") in (None, False, ""):
        ICP.set_param("sc.signup.ratelimit.max_per_ip", "3")
    if ICP.get_param("sc.signup.ratelimit.max_per_email") in (None, False, ""):
        ICP.set_param("sc.signup.ratelimit.max_per_email", "2")
    if ICP.get_param("sc.signup.ratelimit.gc_days") in (None, False, ""):
        ICP.set_param("sc.signup.ratelimit.gc_days", "7")
    if ICP.get_param("sc.password_recovery.self_service_enabled") in (None, False, ""):
        ICP.set_param("sc.password_recovery.self_service_enabled", "false")
