# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .source_authority import build_source_authority_contract

SOURCE_KIND = "smart_core_extension_loader"
SOURCE_AUTHORITIES = (
    "ir.config_parameter",
    "ir.module.module",
    "odoo.registry",
    "odoo.addons",
    "smart_core_register",
)
NO_BUSINESS_FACT_AUTHORITY = True
_REGISTRY_CONTEXT_ATTR = "_smart_core_extension_runtime_context"


class ExtensionConfigurationError(RuntimeError):
    code = "EXTENSION_CONFIGURATION_INVALID"

    def __init__(
        self,
        message: str,
        *,
        configured: tuple[str, ...] = (),
        missing: tuple[str, ...] = (),
        uninstalled: tuple[tuple[str, str], ...] = (),
    ):
        super().__init__(message)
        self.configured = configured
        self.missing = missing
        self.uninstalled = uninstalled

    def to_diagnostic(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "configured": list(self.configured),
            "missing": list(self.missing),
            "uninstalled": [
                {"module": module, "state": state}
                for module, state in self.uninstalled
            ],
        }


class ExtensionRuntimeError(RuntimeError):
    code = "EXTENSION_RUNTIME_INVALID"


@dataclass(frozen=True)
class ExtensionRuntimeContext:
    config_modules: tuple[str, ...]
    modules: tuple[str, ...]
    handlers: Mapping[str, type]
    lifecycle_transition: bool = False


def source_authority_contract():
    return build_source_authority_contract(
        kind=SOURCE_KIND,
        authorities=SOURCE_AUTHORITIES,
        no_business_fact_authority=NO_BUSINESS_FACT_AUTHORITY,
        runtime_carrier="odoo_registry_extension_context",
    )


def _parse_modules(raw: str):
    if not raw:
        return []
    return [item.strip() for item in str(raw).split(",") if str(item).strip()]


def unregister_extension_module(env, module_name: str) -> None:
    """Remove only this module's registration in Odoo's uninstall transaction.

    Called by native uninstall hooks; never commits or manages module states.
    Manual references to other uninstalled modules remain invalid configuration.
    """
    params = env["ir.config_parameter"].sudo()
    key = "sc.core.extension_modules"
    modules = _parse_modules(params.get_param(key) or "")
    if module_name in modules:
        params.set_param(key, ",".join(name for name in modules if name != module_name))


def _configured_extension_modules(env) -> tuple[str, ...]:
    try:
        raw = env["ir.config_parameter"].sudo().get_param("sc.core.extension_modules") or ""
    except Exception as exc:
        raise ExtensionConfigurationError(
            "extension configuration could not be read: %s" % (exc,)
        ) from exc
    return tuple(dict.fromkeys(_parse_modules(raw)))


def _installed_module_states(env, modules: tuple[str, ...]) -> dict[str, str]:
    if not modules:
        return {}
    try:
        model = env["ir.module.module"].sudo().with_context(active_test=False)
        rows = model.search_read(
            [("name", "in", list(modules))],
            ["name", "state"],
        )
    except Exception as exc:
        raise ExtensionConfigurationError(
            "installed module state could not be read: %s" % (exc,),
            configured=modules,
        ) from exc
    return {
        str(row.get("name") or "").strip(): str(row.get("state") or "").strip()
        for row in rows
        if str(row.get("name") or "").strip()
    }


def resolve_extension_modules(
    env,
    configured: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Return enabled extensions that are installed in the current database."""
    configured = (
        tuple(configured)
        if configured is not None
        else _configured_extension_modules(env)
    )
    # Only Odoo's Registry can authorize construction-time filtering. Request
    # context and callers cannot opt out of the runtime authority check.
    allow_transition = not _registry_is_ready(_context_host(env))
    states = _installed_module_states(env, configured)
    missing = tuple(module for module in configured if module not in states)
    uninstalled = tuple(
        (module, states.get(module) or "unknown")
        for module in configured
        if module in states and states[module] != "installed"
    )
    if (missing or uninstalled) and not allow_transition:
        details = []
        if missing:
            details.append("missing=%s" % ",".join(missing))
        if uninstalled:
            details.append(
                "uninstalled=%s"
                % ",".join("%s:%s" % pair for pair in uninstalled)
            )
        raise ExtensionConfigurationError(
            "sc.core.extension_modules contains modules without installed authority (%s)"
            % "; ".join(details),
            configured=configured,
            missing=missing,
            uninstalled=uninstalled,
        )
    if allow_transition:
        return tuple(
            sorted(
                module for module in configured
                if states.get(module) == "installed"
                and module in getattr(env.registry, "_init_modules", ())
            )
        )
    return tuple(sorted(configured))


def _registry_is_ready(host) -> bool:
    """Odoo owns Registry construction; adapters run fully only after it is ready."""
    return bool(getattr(host, "ready", True))


def _build_handlers(env, modules: tuple[str, ...]) -> dict[str, type]:
    from .handler_registry import base_handlers

    handlers = base_handlers()
    owners = {intent: "smart_core" for intent in handlers}
    for module_name in sorted(modules):
        try:
            module = importlib.import_module("odoo.addons.%s" % module_name)
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension module import failed: %s (%s)" % (module_name, exc)
            ) from exc
        hook = getattr(module, "smart_core_register", None)
        if not callable(hook):
            continue
        before = dict(handlers)
        try:
            hook(handlers)
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension register hook failed: %s (%s)" % (module_name, exc)
            ) from exc
        removed = sorted(set(before) - set(handlers))
        if removed:
            raise ExtensionRuntimeError(
                "extension removed existing intents: %s (%s)"
                % (module_name, ",".join(removed))
            )
        for intent, handler in handlers.items():
            previous = before.get(intent)
            owner = owners.get(intent, "")
            if previous is not None and previous is not handler:
                raise ExtensionRuntimeError(
                    "duplicate intent registration: %s owned by %s and %s"
                    % (intent, owner or "<unknown>", module_name)
                )
            if intent not in before:
                owners[intent] = module_name
    return handlers


def _context_host(env):
    host = getattr(env, "registry", None)
    if host is None:
        raise ExtensionRuntimeError("extension runtime requires an Odoo Registry")
    return host


def extension_runtime_context(env) -> ExtensionRuntimeContext:
    """Return extension state owned by the current Odoo Registry.

    A new Registry starts with no extension context. Configuration changes on
    the same Registry replace the context keyed by the configured module order.
    Installed-module truth is read when the context is built; Odoo Registry
    rebuild is the lifecycle boundary for module install, upgrade and removal.
    """
    host = _context_host(env)
    config_modules = _configured_extension_modules(env)
    lifecycle_transition = not _registry_is_ready(host)
    cached = getattr(host, _REGISTRY_CONTEXT_ATTR, None)
    if (
        isinstance(cached, ExtensionRuntimeContext)
        and cached.config_modules == config_modules
        and not lifecycle_transition
        and not cached.lifecycle_transition
    ):
        return cached

    modules = resolve_extension_modules(
        env,
        config_modules,
    )
    context = ExtensionRuntimeContext(
        config_modules=config_modules,
        modules=modules,
        handlers=MappingProxyType(_build_handlers(env, modules)),
        lifecycle_transition=lifecycle_transition,
    )
    # The module graph advances within one Registry build. Never freeze a
    # partial set or carry it across Odoo's ready boundary.
    if not lifecycle_transition:
        setattr(host, _REGISTRY_CONTEXT_ATTR, context)
    return context


def clear_extension_runtime_context(env=None, *, registry=None) -> None:
    """Clear Registry-owned extension state for lifecycle tests and repair."""
    host = registry if registry is not None else _context_host(env)
    try:
        delattr(host, _REGISTRY_CONTEXT_ATTR)
    except AttributeError:
        pass


def load_extensions(env, registry=None):
    """Return current Registry handlers without mutating process-global state."""
    del registry
    return handlers_for_env(env)


def handlers_for_env(env) -> Mapping[str, type]:
    return extension_runtime_context(env).handlers


def iter_extension_modules(env):
    if env is None or getattr(env, "registry", None) is None:
        return []
    return sorted(extension_runtime_context(env).modules)


def run_extension_hooks(env, hook_name: str, *args, **kwargs):
    if env is None:
        return []
    from .extension_hook_contracts import contract_for

    try:
        contract = contract_for(hook_name)
    except KeyError as exc:
        raise ExtensionRuntimeError(
            "extension hook has no declared invocation contract: %s" % hook_name
        ) from exc
    if contract.mode != "run_all":
        raise ExtensionRuntimeError(
            "non-run_all hook cannot use the all-provider entrypoint: %s"
            % hook_name
        )
    providers = {}
    for module_name in iter_extension_modules(env):
        try:
            module = importlib.import_module("odoo.addons.%s" % module_name)
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension module import failed: %s (%s)" % (module_name, exc)
            ) from exc
        hook = getattr(module, hook_name, None)
        if callable(hook):
            providers[module_name] = hook
    modules = sorted(providers)
    final_providers = tuple(getattr(contract, "final_providers", ()))
    if (
        len(set(final_providers)) != len(final_providers)
        or not set(final_providers).issubset(contract.providers)
    ):
        raise ExtensionRuntimeError(
            "run_all hook final providers are invalid: %s (%s)"
            % (hook_name, ",".join(final_providers))
        )
    if contract.providers:
        unexpected = sorted(set(modules) - set(contract.providers))
        allow_undeclared = bool(getattr(contract, "allow_undeclared", False))
        if unexpected and not allow_undeclared:
            raise ExtensionRuntimeError(
                "run_all hook has undeclared providers: %s (%s)"
                % (hook_name, ",".join(unexpected))
            )
        modules = [
            module_name
            for module_name in contract.providers
            if module_name in modules and module_name not in final_providers
        ] + (unexpected if allow_undeclared else []) + [
            module_name
            for module_name in final_providers
            if module_name in modules
        ]
    results = []
    for module_name in modules:
        hook = providers[module_name]
        try:
            results.append((module_name, hook(*args, **kwargs)))
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension hook failed: %s.%s (%s)"
                % (module_name, hook_name, exc)
            ) from exc
    return results
