# Frontend Form Information Architecture Audit v1

## Decision

The form platform has strong contract generation, unified rendering, responsive layout, status/action handling and configuration support. It does not yet provide a mature business-document presentation model.

- Technical structure maturity: `8.2/10`.
- Business information architecture maturity: `4.7/10`.
- Formal product form baseline: `not accepted yet`.
- Reuse: unified page contract, field metadata, state/actions, responsive containers, design tokens, attachments and collaboration.
- Upgrade: ordinary-user filtering, entry-specific summary, readonly projection, section semantics, evidence/narrative composition and role/mode differentiation.

## Evidence

The reproducible static audit is:

```bash
python3 scripts/verify/form_information_architecture_audit.py
```

It inspected 77 product-release contracts that declare `entry_semantic_surface`, fields and sections:

| Metric | Result |
|---|---:|
| P0 | 73 |
| P1 | 4 |
| PASS | 0 |
| Visible technical/trace field occurrences | 407 |
| Entries with ordinary trace/system sections | 70 |
| Entries with a generic first section | 57 |
| Entries mixing attachments and long text | 65 |
| Entries without a first-class attachment area | 8 |

The isolated browser fixture produced 18 screenshots for six states across `1440x900`, `1280x800` and `390x844`. The sampled contract, payment request and settlement pages expose 13, 16 and 14 section-navigation items respectively. Readonly mode reuses the editable field tree and displays many optional empty values instead of projecting a concise business document.

## Root Causes

1. The ordinary-user surface has no fail-closed semantic boundary for system, migration and audit fields.
2. Readonly mode changes editability but does not receive a dedicated information projection.
3. Entry semantics do not control the first-screen summary strongly enough.
4. Section count and abstraction levels are not budgeted.
5. Attachments and narrative text are treated as adjacent generic fields rather than different business capabilities.
6. Existing gates prove structural presence and operability, not product-level information quality.

## Target Contract Extension

Extend the existing unified page contract; do not create a second page protocol:

- `sectionKind`: `summary | facts | details | narrative | evidence | workflow | audit`.
- `fieldRole`: `identity | context | decision | detail | narrative | evidence | workflow | system`.
- `audience`: standard role set.
- `renderProfiles`: `create | edit | readonly`.
- `emptyValuePolicy`: `show | hide | collapse_section`.
- `readPriority`: readonly summary/body ordering.
- `attachmentCategory`: evidence category and requirement.
- `surface`: `header | body | drawer | audit_only`.

## Delivery Sequence

1. Freeze the current contract and browser evidence.
2. Add the P0 semantic contract and fail-closed ordinary-user filtering.
3. Add a backend readonly projection and document-style readonly renderer.
4. Productize six high-impact P1 recipes: construction contract, payment request, settlement, expense claim, invoice and project.
5. Separate evidence/attachments from narrative text.
6. Migrate all 77 contracts and validate role, mode and five-viewport matrices.

## Acceptance

- Ordinary handler technical/migration fields: `0`.
- Ordinary handler source/system sections: `0`.
- Summary facts: `4–8`; total first-screen business fields: at most `12`.
- Major sections: normally `4–7`.
- Create, edit and readonly have provably different projections.
- Optional empty readonly fields do not occupy space by default.
- Narrative and attachments are separate semantic sections.
- Attachments are first-class categorized evidence.
- The first business-theme section is reachable in the initial 390px viewport without horizontal overflow.
- Permissions, routes, APIs and business facts do not drift during presentation changes.
- New assertions are part of the formal frontend release gate.

The next implementation step should be the platform contract and readonly projection, followed by three real end-to-end samples: construction contract, payment request and settlement. CSS-only page-by-page tuning should stop until those foundations are in place.
