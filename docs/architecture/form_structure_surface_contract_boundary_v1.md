# Form Structure Surface Contract Boundary v1

## Purpose

`协作记录` and `历史审计` used to be invented by the renderer: the labels,
the region identity and the visibility rule lived in frontend files, and the
audit region appeared whenever runtime timeline data happened to exist.  That
produced two nav entries for one region, a task-mode layout that differed from
the workspace-mode layout, and a region that a user without the audit role could
still see.

This note fixes where a non-field page region is declared, and under which
authority it becomes visible.  It refines `contract_authority_hierarchy_v1.md`
and `app_shell_vs_page_scene_contract_v1.md`; it does not replace either.

## Layer boundaries (server side)

| Layer | Carrier | Owns | Must not own |
| --- | --- | --- | --- |
| Scene / navigation | `scene_ready_contract`, `system.init.nav`, `scene_catalog_v2.json` | which menu, action and scene identity the current user may open | page body structure, field layout, region titles |
| Page contract | `ui.contract.v2` snapshot | runtime page projection for one (scene, action, model, view, record, role, company, lang) | navigation authority, ORM write authority |
| Layout authority | `layoutContract` (container tree, zones, widget placement) | where Odoo view elements are placed, projected from the native view | regions that are not Odoo view elements |
| Status / action / data | `statusContract`, `actionContract`, `dataContract` | final permission status, runtime actions, data sources | page region declaration |
| Semantic structure | `formStructureContract` (`projection_only`, `no_business_fact_authority`) | declared form structure: slots, field roles, and **declared surfaces** | layout placement, ORM facts, menu exposure |
| Role / capability authority | `res.groups` + published capability registry (`system.init.capabilities`) | which role may use which capability | per-page region wording or DOM |

`scene_key` participates in `ui.contract.v2` only as a binding/authorization
check (`_validate_scene_action_binding`) and as an entry identity.  For
`source_type=ui.contract` the scene is **not** the page body authority, so a
region must not be declared in, or derived from, the scene registry.  The only
contract source that *is* scene-shaped is `source_type=scene_contract`, which
serves scene summary blocks, not business record pages.

## Where a surface belongs

A surface (for example the collaboration region) is a declared page region that
is **not** an Odoo view element.  It therefore cannot live in `layoutContract`:
that contract is the native view projection, and `container_tree_authority`
explicitly forbids independent structural membership there.  It is declared in
`formStructureContract.surfaces`, next to `slots`, because both describe
declared structure rather than placement or business facts.

Declaration shape (per surface):

- `surface`, `title`, `role`, `contentKind`, `sourceIdentity` — region identity.
- `capabilities` — which model-declared sub-capabilities the region carries
  (timeline / remarks / attachments).
- `audit` — the role-gated sub-declaration: `title`, `contentKind`,
  `sourceIdentity` and `authorization`.

`authorization` is resolved on the backend for the requesting identity and
publishes the same vocabulary the capability registry already publishes
(`allow` / `deny` / `pending` / `coming_soon`), plus the required roles and
groups as evidence.  A gated region is rendered only when
`authorization.state === 'allow'`.

## Visibility rule (one rule, one direction)

```
visible = contract declares the surface
          AND (surface has no audit sub-declaration OR audit.authorization.state == 'allow')
          AND no other declared governance rule suppresses it
```

Runtime data is never a visibility authority: audit events present but no
authorization must not show the region, and audit events absent but authorized
must still show the region (with its own empty state).  This removes the
"captured before the timeline was ready" theme/viewport dependent rendering.

## Ownership

- `smart_core` owns the generic mechanism: it composes the declared surface list
  into `formStructureContract`, normalizes it, and falls back to the model
  capability when no product policy is registered.  It must not name a
  product capability key.
- `smart_construction_core` (industry standard product) owns the policy: which
  surfaces a construction form publishes, their titles, and which capability
  gates the audit sub-region.  It resolves the entitlement from the same
  capability registry that publishes `system.init.capabilities`, so a gated
  region and the capability matrix cannot drift apart.
- The renderer owns nothing but consumption: it maps declared surfaces to
  navigation entries and renders the declared region.  It must not hardcode a
  region label, region identity or visibility predicate.

## Verification

- `make verify.frontend.form_structure_surface_contract.unit` — declaration
  consumption and the role gate, negative-first.
- `make verify.frontend.form_structure_contract_projection.unit` — projection
  matrix still consistent.
- `make verify.contract.project_ledger_entry_carrier.orm` — runtime carrier unchanged.
