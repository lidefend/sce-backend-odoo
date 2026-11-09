# FE-SYSTEMIC-CONVERGENCE M3：内联样式分类与收敛

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: generic frontend inline-style ownership and rendering mechanics
- Module: shared pages, renderers and design-system adapters
- Contract V2, ACL, backend semantics, database and deployment are excluded

## Baseline Correction

The original audit counted the substring `style="` and therefore included
Vue dynamic bindings and component style props. A literal static `style="..."`
search currently returns zero files.

Current exact inventory:

| Category | Files | Occurrences | Meaning |
| --- | ---: | ---: | --- |
| Vue `:style` bindings | 25 | 89 | Dynamic runtime style expressions |
| Component styling props | 8 files, including 7 outside the `:style` set | 9 | Explicit `layout-style`, `body-style`, `overlay-style` or forwarded `style` API |
| Literal static inline style attributes | 0 | 0 | No literal CSS text embedded in Vue templates |

The M3 acceptance therefore uses ownership rather than a blended raw substring
count: literal static styling must stay zero, and every retained dynamic style
must have one registered rendering-mechanism owner.

## Audit

All retained mechanisms are registered in
`docs/architecture/inline_style_allowlist.json`:

| Mechanism | Files | Ownership |
| --- | ---: | --- |
| Contract section order | 15 | `frontend.page_contract` |
| Resizable workspace geometry | 2 | `frontend.hierarchy_renderer` |
| Render-tree indentation | 3 | `frontend.hierarchy_renderer` |
| Declarative column geometry | 4 | `frontend.collection` |
| Declared native form layout | 1 | `frontend.native_form_renderer` |
| Contract grid span | 1 | `frontend.contract_renderer` |
| Contract visual color | 1 | `frontend.professional_fields` |
| Data visualization width | 1 | `frontend.analysis` |
| Component style API | 2 | `frontend.design_system` |

Product consumers removed the following non-semantic inline expressions:

- `ScCard`: body/header styles moved to `data-appearance` CSS.
- `ScPanel`: body padding moved to `data-tone` CSS.
- `ScDialog`: dimensions moved to `sc-dialog--default|wide` CSS.
- `NativeWeightedRelationDisplay`: overlay object moved to a named overlay class.
- `X2ManyRelationRenderer`: readonly overlay object moved to a named overlay class.
- `HierarchyPlanner`: static header grid moved to `ProductListHeader` layout mode.

Exact counts:

| Metric | Before | After |
| --- | ---: | ---: |
| Raw `style=` substring files | 32 | 26 |
| Raw `style=` substring occurrences | 98 | 91 |
| Literal static inline style attributes | 0 | 0 |
| Registered mechanism owners | absent | 9 |
| Unregistered template/script style sites | unaudited | 0 |

## Validation

- Inline-style guard unit tests: 6 passed.
- `make verify.frontend.style_system.guard`: PASS.
- Registered inline-style mechanism files: 28.
- `make verify.frontend.dev.incremental.unit`: 103 passed.
- `make verify.frontend.page_pattern_reference_parity.unit`: 16 passed.
- `make ci.local.iteration`: PASS on the declared dirty scope, 13 targets.
- `make verify.frontend.node_component.component`: 36 and 42 cases passed.
- `make verify.frontend.overlay_lifecycle.browser`: PASS.
- `make verify.frontend.professional_relation_field.unit`: PASS, including
  18 model cases, 40 guard tests and relation entry/authority assertions.

Receipt:
`.runtime/frontend-dev-validation/executions/20261109T195656Z-4002557-438242662/receipt.json`.

## Result

Pending commit, clean-HEAD iteration and 1440/390 browser review.
