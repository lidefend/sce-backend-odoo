# Product View Capability Ledger Contract V1

## 1. Purpose and boundary

This contract defines atom-level evidence from an Odoo native-view occurrence to frontend interaction. It measures how much native-view capability the product contract actually carries. It is a P4 evidence and gate mechanism measuring the generic P0 `smart_core` contract pipeline; it does not introduce business semantics or move industry or customer rules into the platform kernel.

This phase defines measurement facts only. The ledger and its reason codes are not runtime behavior authority and must not be used by the frontend to infer missing semantics.

## 2. Authoritative runtime identity

Every ledger binds the full candidate fingerprint, database architecture policy hash, module set, user, company, language, and group profile. Runtime identity is fixed to `local.clean` / `sc-local-clean` / `sc_clean` / `^sc_clean$`; manually assembled Compose, database, or credential commands cannot satisfy the gate.

## 3. Capability atoms and evidence chain

A capability atom represents one locatable native-view occurrence, not a deduplicated field or button name. `atom_id` must distinguish repeated fields, repeated buttons, inheritance contributors, and nested subviews.

The evidence chain records `native`, `normalized`, `semantic`, and `frontend` stages. The frontend stage explicitly binds the canonical atom, compatibility projection, consumer symbol, renderer, and interaction symbol. `source_authority` is mandatory; behavior determined by multiple sources without one declared authority cannot be ready.

## 4. Terminal-state rules

Every native capability atom has exactly one terminal state:

- `ready`: normalized, semantic, frontend-consumption, and interaction evidence is complete, without semantic guessing or undeclared override.
- `fallback`: an explicit, governed, traceable degradation path exists but does not fully preserve the native capability.
- `unsupported`: no usable carrier or renderer exists, or the capability is explicitly rejected.

A `ready` atom has an empty `reason_code`; `fallback` and `unsupported` atoms reference the reason-code registry. Unknown state, silent deletion, and unclassified loss are invalid.

The static presence of a field, parser node, or renderer proves carrier presence only, not end-to-end readiness. Dynamic modifiers, permissions, record context, and interaction behavior require governed runtime evidence; without it, the atom is at best `fallback`.

## 5. Zero-silent-loss gate

The guard recomputes all content and manifest hashes and verifies authority identity, summary counts, contract references, parent-child surface relationships, the native contribution graph, and reason codes. A native capability without a terminal state, with broken evidence, mismatched hashes or counts, or an unknown reason code increments `silent_loss_count` and fails the gate.

Acceptance requires native occurrence count to equal `ready + fallback + unsupported`, `silent_loss_count` to be zero, every non-ready atom to have a registered reason and executable exit condition, and all evidence to bind the same frozen candidate fingerprint.

The reason-code authority is `contracts/product/native-view-capability-reason-codes-v1.yaml`; the structural constraint is `contracts/schemas/product-view-capability-ledger-v1.yaml`.
