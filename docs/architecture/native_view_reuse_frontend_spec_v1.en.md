# Native-View-Reuse Driven Frontend Page Design Spec v1

## 1. Objective

This spec standardizes how frontend pages are built in this repo:

`Odoo native views define base structure -> backend normalizes and lifts semantics -> frontend renders from unified contracts -> scene/product layer adds enhancements.`

Scope:
- Odoo backend view parsing
- frontend generic renderers
- scene orchestration
- product enhancement layer

## 2. Core Principles

1. **Native structure first**: if native view already defines field/group/notebook/header/chatter/x2many/modifiers, frontend must not redefine it.
2. **Backend interpretation first**: frontend must not parse XML or infer business semantics.
3. **Generic renderer first**: prioritize shared renderers over page-level hardcoding.
4. **Explicit interaction authority**: native facts declare purpose, association and trigger for risk/AI/next-action guidance. A zone/block or task/risk role never authorizes permanent body tutorials or inference from readonly/nonempty fields. Native field help uses official interactive help; action risks use the declared action trigger. Field errors, operation results and contract-gap states retain their distinct sources.
5. **Consistency first**: Odoo backend and custom frontend must keep consistent semantics, permission outcomes, and status meaning.

## 3. Four-Layer Page Model

1) **Native View Layer**: raw Odoo view facts.
2) **Normalized Structure Layer**: standardized machine-consumable structure.
3) **Semantic Page Layer**: `zone + block` semantics for rendering.
4) **Product Orchestration Layer**: scene/role-specific composition without breaking base semantics.

Recommended zones:
- `header_zone`, `summary_zone`, `detail_zone`, `relation_zone`
- `action_zone`, `collaboration_zone`, `insight_zone`, `attachment_zone`

Recommended blocks:
- `title_block`, `status_block`, `action_bar_block`, `field_group_block`
- `notebook_block`, `relation_table_block`, `stat_button_block`
- `chatter_block`, `attachment_block`, `risk_alert_block`
- `ai_recommendation_block`, `next_action_block`

## 4. Mandatory Delivery Flow

1. Check native view carrying capability first.
2. If UI is insufficient, improve backend semantic output first.
3. Frontend consumes only semantic contracts (`page/zones/blocks/fields/actions/permissions`).
4. Page-level special cases are allowed only for high-value scenarios with explicit rationale.

## 5. Backend Responsibilities

Backend must output:
- base view definition
- structured page contract
- field modifiers
- executable actions
- permission/status interpretation with reason codes

Backend must not:
- dump raw XML and delegate semantic interpretation to frontend
- return only fields + records while omitting structure
- maintain multiple conflicting structure sources for one page

## 6. Frontend Responsibilities

Frontend is responsible for:
- structural rendering
- component mapping
- interaction and feedback
- form input management
- submit/refresh lifecycle
- extension slot rendering

Frontend must not:
- parse Odoo XML
- infer permissions/action availability
- rebuild business partitioning by guesswork
- override native semantic order with ad-hoc field order

## 7. Governance

### New page checklist
1. Is native view sufficient for base layout?
2. Is backend semantic output complete?
3. Is this requirement generic rendering or product enhancement?
4. Is a page special-case truly necessary?
5. Will this break renderer consistency?

### Implementation priority
1. Backend parsing/normalization
2. Frontend generic renderers
3. Semantic orchestration
4. Product enhancement
5. Page special-cases

## 8. Enforced Rule for Future Iterations

From this spec onward:
- New page work must start with native-carrying assessment.
- Structure gaps must be fixed in backend semantic output first.
- Frontend page structure must be contract-driven.
- Any page special-case must include entry criteria and exit criteria in iteration notes.

## 9. One-Line Policy

Native Odoo views define the base page structure, backend provides unified semantics, frontend renders generically, and high-value scenes receive product enhancements.


## Effective runtime structure (2026-09-16)

Native views provide the complete default baseline, not the exclusive layout authoring source. The backend composes authorized industry defaults, customer preferences and administrator configuration, validates business and security constraints, and emits one effective tree shared by content, navigation and preview. Restrictions on rewriting native structure prohibit client-side reinterpretation and duplicate defaults, not legitimate low-code layout configuration. See `native_first_form_structure_authority_v1.md` for identity, conflict and lifecycle rules.

## View, layout and authorization ownership (2026-10-13)

The model base/default view, action-selected view and permission-projected runtime view are distinct stages. The action-selected view defines the entry baseline. P1/P2 defaults and authorized P3 configuration compose one final layout; roles authorize editing and operation but do not select templates, sections, ordering or widths. Permission clipping may hide content or restrict actions/editability without regrouping or recalculating remaining business spans. Effective readonly and edit modes must be compared separately.

P0 declares the supported layout properties, legal values, stable node/occurrence identity and composition rules. Low-code configures authorized grouping, order, tabs, columns, spans and supported presentation options, never arbitrary DOM, CSS or executable code. The final contract includes effective structure and source/configuration provenance; frontend components only render it. Missing, illegal, conflicting or unsupported effective declarations fail closed. Only registered rendering/transport mechanism constants may be client-owned; absence never licenses product defaults or clamping. An adopter need not consume every capability, but active page requirements cannot be silently ignored.

Equal field-grid tracks accept integer divisors of 24 (1,2,3,4,6,8,12,24). P0 resolves an omitted native column count to 2; explicit invalid declarations never fall back. A native field node and its same-occurrence widget use the same parent span. Only an explicitly declared field node whose outer host already consumes that span uses the registered singleton content mapping (columns=1/span=24) internally. Grouped fields retain their individual declared spans. This mapping does not depend on role or visible field count. Responsive folding validates the declaration before applying registered visual rules.

Evidence must bind declaration, consumer and actual behavior, retain occurrence/parent/order/width identities and separate permissions. Schema or selector presence alone is not acceptance.
