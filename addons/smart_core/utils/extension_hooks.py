# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import inspect
from typing import Any, List

SOURCE_KIND = "smart_core_extension_hook_resolver"
SOURCE_AUTHORITIES = ("ir.config_parameter", "odoo.addons", "extension_hook")
NO_BUSINESS_FACT_AUTHORITY = True


def source_authority_contract() -> dict:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "rebuildable": True,
        "no_business_fact_authority": NO_BUSINESS_FACT_AUTHORITY,
        "runtime_carrier": "extension_hooks",
    }


def _parse_extension_modules(raw: str) -> List[str]:
    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if str(item).strip()]


def iter_extension_modules(env) -> List[str]:
    try:
        raw = env["ir.config_parameter"].sudo().get_param("sc.core.extension_modules") or ""
    except Exception:
        return []
    return _parse_extension_modules(raw)


def call_extension_hook_first(env, hook_name: str, *args, **kwargs) -> Any:
    for module_name in iter_extension_modules(env):
        try:
            module = importlib.import_module(f"odoo.addons.{module_name}")
        except Exception:
            continue
        hook = getattr(module, hook_name, None)
        if callable(hook):
            try:
                result = hook(*args, **kwargs)
            except Exception:
                continue
            if result is not None:
                return result
    return None


def call_extension_hook_first_compatible(
    env,
    hook_name: str,
    *args,
    optional_kwargs: dict[str, Any] | None = None,
) -> Any:
    """Call the first provider that can bind the optional keyword signature.

    Provider order and an intentional empty result remain authoritative. Signature
    adaptation happens before invocation, so a TypeError raised inside a provider
    is not mistaken for an unsupported keyword and retried.
    """
    optional_kwargs = optional_kwargs if isinstance(optional_kwargs, dict) else {}
    for module_name in iter_extension_modules(env):
        try:
            module = importlib.import_module(f"odoo.addons.{module_name}")
        except Exception:
            continue
        hook = getattr(module, hook_name, None)
        if not callable(hook):
            continue
        try:
            signature = inspect.signature(hook)
        except (TypeError, ValueError):
            signature = None
        call_kwargs = dict(optional_kwargs)
        if signature is not None:
            try:
                signature.bind(*args, **call_kwargs)
            except TypeError:
                call_kwargs = {}
                try:
                    signature.bind(*args)
                except TypeError:
                    continue
        try:
            result = hook(*args, **call_kwargs)
        except Exception:
            continue
        if result is not None:
            return result
    return None
