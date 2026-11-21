# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import inspect
from copy import deepcopy
from typing import Any

from odoo.addons.smart_core.core.extension_hook_contracts import (
    contract_for,
)

SOURCE_KIND = "smart_core_extension_hook_resolver"
SOURCE_AUTHORITIES = (
    "ir.config_parameter",
    "ir.module.module",
    "odoo.registry",
    "extension_hook_contracts",
    "odoo.addons",
)
NO_BUSINESS_FACT_AUTHORITY = True


class ExtensionHookAuthorityError(RuntimeError):
    code = "EXTENSION_HOOK_AUTHORITY_INVALID"


def source_authority_contract() -> dict:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "rebuildable": True,
        "no_business_fact_authority": NO_BUSINESS_FACT_AUTHORITY,
        "runtime_carrier": "registry_extension_hooks",
    }


def _extension_modules(env) -> tuple[str, ...]:
    if env is None or getattr(env, "registry", None) is None:
        return ()
    from odoo.addons.smart_core.core.extension_loader import (
        extension_runtime_context,
    )

    return extension_runtime_context(env).modules


def _hook_providers(env, hook_name: str):
    providers = []
    for module_name in _extension_modules(env):
        try:
            module = importlib.import_module("odoo.addons.%s" % module_name)
        except Exception as exc:
            raise ExtensionHookAuthorityError(
                "hook provider import failed: %s.%s (%s)"
                % (module_name, hook_name, exc)
            ) from exc
        hook = getattr(module, hook_name, None)
        if callable(hook):
            providers.append((module_name, hook))
    return providers


def _call_provider(provider_name, hook, args, kwargs):
    del provider_name
    try:
        return hook(*args, **kwargs)
    except Exception as exc:
        raise ExtensionHookAuthorityError(
            "extension hook failed: %s (%s)" % (hook.__module__, exc)
        ) from exc


def _call_compatible_provider(provider_name, hook, args, optional_kwargs):
    call_kwargs = dict(optional_kwargs or {})
    try:
        signature = inspect.signature(hook)
    except (TypeError, ValueError):
        signature = None
    if signature is not None:
        try:
            signature.bind(*args, **call_kwargs)
        except TypeError:
            call_kwargs = {}
            try:
                signature.bind(*args)
            except TypeError:
                raise ExtensionHookAuthorityError(
                    "extension hook signature is incompatible: %s.%s"
                    % (provider_name, hook.__name__)
                )
    try:
        return True, hook(*args, **call_kwargs)
    except Exception as exc:
        raise ExtensionHookAuthorityError(
            "extension hook failed: %s (%s)" % (hook.__module__, exc)
        ) from exc


def _merge_values(values: list[Any], strategy: str):
    if not values:
        return None
    if strategy == "set_union":
        merged = set()
        for value in values:
            if isinstance(value, (list, tuple, set)):
                merged.update(value)
            else:
                raise ExtensionHookAuthorityError(
                    "set_union hook returned %s" % type(value).__name__
                )
        return merged
    if strategy == "dict_update":
        merged = {}
        for value in values:
            if not isinstance(value, dict):
                raise ExtensionHookAuthorityError(
                    "dict_update hook returned %s" % type(value).__name__
                )
            merged.update(deepcopy(value))
        return merged
    if strategy == "deep_dict":
        merged = {}
        for value in values:
            if not isinstance(value, dict):
                raise ExtensionHookAuthorityError(
                    "deep_dict hook returned %s" % type(value).__name__
                )
            merged = _deep_merge_dict(merged, value)
        return merged
    if strategy == "list_extend":
        merged = []
        for value in values:
            if not isinstance(value, (list, tuple)):
                raise ExtensionHookAuthorityError(
                    "list_extend hook returned %s" % type(value).__name__
                )
            merged.extend(deepcopy(list(value)))
        return merged
    raise ExtensionHookAuthorityError("unknown hook merge strategy: %s" % strategy)


def _deep_merge_dict(left: dict, right: dict) -> dict:
    merged = deepcopy(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _resolve_contract(env, hook_name: str):
    try:
        contract = contract_for(hook_name)
    except KeyError as exc:
        raise ExtensionHookAuthorityError(
            "extension hook has no declared invocation contract: %s" % hook_name
        ) from exc
    if contract.mode == "run_all":
        raise ExtensionHookAuthorityError(
            "run_all hook must use the run-all entrypoint: %s" % hook_name
        )
    providers = _hook_providers(env, hook_name)
    provider_by_name = dict(providers)
    if contract.mode == "single_owner":
        if len(providers) > 1:
            raise ExtensionHookAuthorityError(
                "single_owner hook has multiple providers: %s (%s)"
                % (hook_name, ",".join(name for name, _hook in providers))
            )
        return contract, providers
    if contract.mode == "ordered_merge":
        unexpected = sorted(set(provider_by_name) - set(contract.providers))
        if unexpected:
            raise ExtensionHookAuthorityError(
                "ordered_merge hook has undeclared providers: %s (%s)"
                % (hook_name, ",".join(unexpected))
            )
        ordered = [
            (module_name, provider_by_name[module_name])
            for module_name in contract.providers
            if module_name in provider_by_name
        ]
        return contract, ordered
    raise ExtensionHookAuthorityError(
        "unsupported hook contract mode: %s" % contract.mode
    )


def call_extension_hook_first(env, hook_name: str, *args, **kwargs) -> Any:
    """Resolve a hook through its declared contract.

    The historical function name is retained for call-site compatibility.
    Invocation is no longer decided by module configuration order.
    """
    contract, providers = _resolve_contract(env, hook_name)
    if contract.mode == "single_owner":
        if not providers:
            return None
        module_name, hook = providers[0]
        return _call_provider(module_name, hook, args, kwargs)
    values = []
    for module_name, hook in providers:
        value = _call_provider(module_name, hook, args, kwargs)
        if value is not None:
            values.append(value)
    return _merge_values(values, contract.merge)


def call_extension_hook_first_compatible(
    env,
    hook_name: str,
    *args,
    optional_kwargs: dict[str, Any] | None = None,
) -> Any:
    contract, providers = _resolve_contract(env, hook_name)
    values = []
    for module_name, hook in providers:
        accepted, value = _call_compatible_provider(
            module_name,
            hook,
            args,
            optional_kwargs,
        )
        if not accepted or value is None:
            continue
        if contract.mode == "single_owner":
            return value
        values.append(value)
    if contract.mode == "single_owner":
        return None
    return _merge_values(values, contract.merge)
