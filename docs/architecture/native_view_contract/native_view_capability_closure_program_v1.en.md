# Native View Contract Capability Closure Program v1

[中文](native_view_capability_closure_program_v1.md)

## 1. Objective

This program advances the platform from "native views can be parsed" to
"formal-product native capabilities are carried by the contract and generic
frontend end to end."

The single product result is that every native-view capability in the formal
product is traceable to a normalized contract and renderer outcome. A
capability that cannot be carried must fail closed with a stable reason code.

## 2. Product boundary

- Formal Product Layer: P0 platform kernel product.
- Supporting Layer: P4 contract export, evidence and gate tooling.
- Layer Target: the `smart_core` native-view contract pipeline, the generic
  frontend renderer registry and product-level contract gates.
- P1 is unchanged: no construction model, state, field meaning or standard
  workflow changes.
- P2 and P3 are unchanged: no customer preference or administrator runtime
  configuration result is embedded here.
- The frontend never infers business meaning from a model, menu, XML ID, role,
  label or route.

## 3. Unit of evaluation

Whether a page opens is not capability-coverage evidence. The minimum unit is
a capability atom:

```text
native capability atom
-> normalized contract atom
-> semantic contract atom
-> renderer capability
-> interaction capability
-> verification evidence
```

Capability atoms include structure, fields, modifiers, actions, collection
views and permission verdicts.

## 4. Batch roadmap

| Batch | Single objective | Exit criterion |
| --- | --- | --- |
| Q0 | Bootstrap the topic branch and freeze boundaries | Exact main baseline, independent worktree, goal and rollback boundary |
| Q1 | Build the formal-product capability-loss ledger | Every surface and atom has a terminal status; no silent loss |
| Q2 | Close modifiers, actions and permissions | Modifiers evaluate, actions are adjudicated and every denial has a reason code |
| Q3 | Close form/tree/search/kanban semantics | The main path has no model/page special cases and has structural and interaction evidence |
| Q4 | Close pivot/graph/activity renderers | Advanced views leave readable fallback through independently accepted renderer batches |
| Q5 | Establish the widget registry and release gate | Every widget is ready/fallback/unsupported and regressions block release |

## 5. Q1 ledger contract

Every row identifies the formal surface, capability key, native count, status at
each pipeline layer, stable reason code and evidence references.

Allowed terminal statuses are `ready`, `fallback` and `unsupported`. Unknown,
missing and reasonless fallback states are forbidden.

## 6. Governance and environment

- Reuse only `local.clean`: project `sc-local-clean`, database `sc_clean`,
  dbfilter `^sc_clean$`.
- Do not create a Compose project, database, port, volume, credential, fixture
  system or runtime profile.
- Serialize shared database writes, module upgrades and formal runtime
  acceptance.
- Bind each batch to a complete tracked, staged and untracked fingerprint.
- Treat zero collected tests as failure.
- Report code, contract, gate and frontend behavior independently.

## 7. Completion criteria

- Exact and conflict-free formal-menu-policy coverage.
- A terminal status for every native capability atom.
- Zero silent capability loss.
- Stable reason codes for every fallback and unsupported outcome.
- One canonical runtime shape for `native_view` and `semantic_page`.
- Frontend component selection driven only by formal contract semantics.
- Clean-install, targeted-test, contract-drift and user-journey evidence bound
  to the same complete candidate fingerprint.
