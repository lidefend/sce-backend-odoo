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


def _configured_extension_modules(env) -> tuple[str, ...]:
    try:
        raw = env["ir.config_parameter"].sudo().get_param("sc.core.extension_modules") or ""
    except Exception as exc:
        raise ExtensionConfigurationError(
            "extension configuration could not be read: %s" % (exc,)
        ) from exc
    modules = _parse_modules(raw)
    try:
        context_modules = _parse_modules(
            str((env.context or {}).get("sc.core.extension_modules") or "")
        )
    except Exception:
        context_modules = []
    for module in context_modules:
        if module not in modules:
            modules.append(module)
    return tuple(dict.fromkeys(modules))


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
    states = _installed_module_states(env, configured)
    missing = tuple(module for module in configured if module not in states)
    uninstalled = tuple(
        (module, states.get(module) or "unknown")
        for module in configured
        if module in states and states[module] != "installed"
    )
    if missing or uninstalled:
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
    return configured


def _build_handlers(env, modules: tuple[str, ...]) -> dict[str, type]:
    from .handler_registry import base_handlers

    handlers = base_handlers()
    for module_name in modules:
        try:
            module = importlib.import_module("odoo.addons.%s" % module_name)
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension module import failed: %s (%s)" % (module_name, exc)
            ) from exc
        hook = getattr(module, "smart_core_register", None)
        if not callable(hook):
            continue
        try:
            hook(handlers)
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension register hook failed: %s (%s)" % (module_name, exc)
            ) from exc
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
    cached = getattr(host, _REGISTRY_CONTEXT_ATTR, None)
    if (
        isinstance(cached, ExtensionRuntimeContext)
        and cached.config_modules == config_modules
    ):
        return cached

    modules = resolve_extension_modules(env, config_modules)
    context = ExtensionRuntimeContext(
        config_modules=config_modules,
        modules=modules,
        handlers=MappingProxyType(_build_handlers(env, modules)),
    )
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
    return list(extension_runtime_context(env).modules)


def run_extension_hooks(env, hook_name: str, *args, **kwargs):
    if env is None:
        return
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
    for module_name in iter_extension_modules(env):
        try:
            module = importlib.import_module("odoo.addons.%s" % module_name)
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension module import failed: %s (%s)" % (module_name, exc)
            ) from exc
        hook = getattr(module, hook_name, None)
        if not callable(hook):
            continue
        try:
            hook(*args, **kwargs)
        except Exception as exc:
            raise ExtensionRuntimeError(
                "extension hook failed: %s.%s (%s)"
                % (module_name, hook_name, exc)
            ) from exc
