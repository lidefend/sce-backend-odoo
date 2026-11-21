# ARCH-CLOSE-01 Extension Lifecycle and Hook Authority v1

- Status: implemented, verification pending
- Layer: P0 platform extension mechanics with P1 provider ownership
- Scope: `smart_core` extension loading and dispatch, construction Core/Scene
  Hook ownership, and offline verification

## Decision

Odoo module installation is the authority for extension execution. The
`sc.core.extension_modules` parameter is enablement data only.

```text
effective extensions = installed modules intersect enabled extensions
```

Every enabled module must also be installed in the current database. A
configured but missing or non-installed module is an explicit
`EXTENSION_CONFIGURATION_INVALID` failure with a machine-readable diagnostic.
Installed modules that are not enabled do not contribute Handlers or Hooks.

## Registry lifecycle

Extension runtime state belongs to the current Odoo Registry. Platform base
Handlers remain in the process-level base catalog, while extension Handlers are
built into an immutable mapping stored on the Registry.

- A new Registry starts without another Registry's extension context.
- A configuration change on the same Registry rebuilds its extension context.
- Module installation, upgrade, or removal takes effect through Odoo Registry
  rebuild or process restart.
- Python import caching is not treated as runtime registration state.

Handler catalog lookup is lazy. This prevents
`extension_loader -> handler_registry -> handlers -> extension_loader` import
cycles during Odoo startup. Runtime consumers resolve extension module lists
through the Loader and do not reintroduce a global-or-package-level cache.

ARCH-CLOSE-01 does not introduce hot module reload or a second module lifecycle
manager. Odoo remains responsible for install, upgrade, unload, and Registry
lifecycle.

## Hook invocation modes

Every extension Hook invoked through the first-owner compatibility entrypoint
has one declared mode in `extension_hook_contracts.py`.

| Mode | Semantics |
| --- | --- |
| `single_owner` | At most one enabled provider; two providers fail explicitly |
| `ordered_merge` | A declared provider order and merge strategy apply |
| `run_all` | Every enabled provider executes through the run-all entrypoint |

Module configuration order no longer selects a winner for first-owner Hooks.
Undeclared Hooks fail. A `run_all` Hook cannot use the first-owner entrypoint,
and a non-`run_all` Hook cannot use the all-provider entrypoint.

## Core / Scene ownership

The four construction Core/Scene collisions are resolved as follows.

| Hook | Authority |
| --- | --- |
| `smart_core_identity_profile` | Core single owner |
| `smart_core_nav_scene_maps` | Explicit ordered merge; Scene Registry overrides Core compatibility maps |
| `smart_core_critical_scene_target_overrides` | Explicit set union of Core and Scene |
| `smart_core_critical_scene_target_route_overrides` | Explicit key update in Core then Scene order |

The Scene navigation consumer remains the real route for verifying that the
Scene Registry-derived mapping is reachable.

## Verification boundary

Offline checks cover installed/enabled resolution, Registry identity isolation,
configuration invalidation, immutable Handler mappings, Hook modes, duplicate
providers, merge order, and provider failures.

The governed lifecycle check clones the current bundle test template twice,
builds a separate Registry for each clone, and verifies different enablement
sets in the same process. It then uses Odoo's native module API to install,
upgrade, and uninstall `smart_owner_core`, reading back Handler presence after
each rebuild and after uninstall. Both temporary databases are dropped and
their absence is read back.

The ORM result guard selects the summary for the requested test database; nested
Registries created by the lifecycle test are not allowed to mask the real target
count.
