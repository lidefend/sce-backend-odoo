# Product View Capability Ledger Contract V1

[中文版](product_view_capability_ledger_v1.md)

## 1. Purpose and boundary

This contract defines atom-level evidence from an Odoo native-view occurrence to frontend interaction. It measures how much native-view capability the product contract actually carries. It is a P4 evidence and gate mechanism measuring the generic P0 `smart_core` contract pipeline; it does not introduce business semantics or move industry or customer rules into the platform kernel.

This phase defines measurement facts only. The ledger and its reason codes are not runtime behavior authority and must not be used by the frontend to infer missing semantics.

## 2. Authoritative runtime identity

Every ledger binds the existing `codex_complete_worktree_fingerprint/v1` complete candidate fingerprint, Git HEAD, baseline SHA, scope-manifest hash, database architecture policy, formal-menu policy, reason registry, view-structure baseline, versioned module set, user, company, language, and group profile. Runtime identity is fixed to `local.clean` / `sc-local-clean` / `sc_clean` / `^sc_clean$` with `demo_data=false`. A Git commit SHA alone is not the complete fingerprint, and manually assembled Compose, database, or credential commands cannot satisfy the gate. To remove self-reference, the complete fingerprint may exclude only the exact `contracts/generated/product_view_structure_contract.json` file; the excluded path and reason are themselves part of the canonical digest, and directory, wildcard, or mutable exclusions are forbidden.

The evidence-carrier commit created after generation may place current HEAD after the ledger's source HEAD. The guard must recompute the source digest from the current complete scope entries, prove that source HEAD is an ancestor of current HEAD, and require an identical scope hash. Baseline-to-independent-export comparison normalizes only source/current HEAD, its fingerprint digest, and the derived manifest hash; no other authority, structure, or runtime fact may be normalized.

## 3. Capability atoms and evidence chain

A capability atom represents one locatable native-view occurrence, not a deduplicated field or button name. `occurrence_index` is the one-based ordinal among equal base locators under one parent; one atom represents exactly one occurrence. `atom_id` excludes the value hash and distinguishes repeated fields, repeated buttons, inheritance contributors, and nested subviews.

The evidence chain records `native`, `normalized`, `semantic`, and `frontend` stages. The frontend stage explicitly binds the canonical atom, compatibility projection, consumer symbol, renderer, and interaction symbol. `source_authority` is mandatory; behavior determined by multiple sources without one declared authority cannot be ready.

This repository's runtime authority is Odoo 17. The user-visible resolved arch comes from public `get_view()`; `_get_view()` may support provenance evidence but must not replace the final structure. When no database `ir.ui.view` exists and Odoo calls `_get_default_<view_type>_view()`, `get_view()["id"]` is legitimately `False`. The ledger records `synthetic_default_view` and the model implementation symbol without inventing a database-view identity. Odoo 17 uses `tree` as the fact-layer canonical type; `list` is a client projection only.

## 4. Terminal-state rules

Every native capability atom has exactly one terminal state:

- `ready`: normalized, semantic, frontend-consumption, and interaction evidence is complete, without semantic guessing or undeclared override.
- `fallback`: an explicit, governed, traceable degradation path exists but does not fully preserve the native capability.
- `unsupported`: no usable carrier or renderer exists, or the capability is explicitly rejected.

A `ready` atom has an empty `reason_code`, all three carrier stages present with non-zero counts and recomputable hashes, and one frontend source with non-empty consumer, renderer, and interaction symbols. `fallback` and `unsupported` reference a registered reason whose status and first-loss stage match the atom. A reason with `gate_effect=silent_loss` cannot produce a publishable ledger. Unknown state, silent deletion, and unclassified loss are invalid.

The static presence of a field, parser node, or renderer proves carrier presence only, not end-to-end readiness. Dynamic modifiers, permissions, record context, and interaction behavior require governed runtime evidence; without it, the atom is at best `fallback`.

## 5. Zero-silent-loss gate

Hash input is UTF-8 canonical JSON with sorted object keys, no insignificant whitespace, and unescaped Unicode. `manifest_sha256` covers the complete ledger except itself. The guard recomputes all hashes and verifies authority identity, conservation totals, unique `contract_ref`/`atom_id`, the `menu_xmlid::canonical_view_type` relation, the native contribution graph, and reason codes. `list` is only an input alias and is canonicalized to `tree`; it is invalid in a ledger.

Each `evidence_refs` item contains a repository-relative path, file SHA, candidate fingerprint, stage, and resolvable selector. The guard proves that the file exists, its hash matches, its candidate is identical, and the selector locates the claimed fact. Broken evidence, mismatched hashes or totals, and unknown reasons are silent loss and fail the gate.

Acceptance requires native occurrence count to equal `ready + fallback + unsupported`, `silent_loss_count` to be zero, every non-ready atom to have a registered reason and executable exit condition, and all evidence to bind the same frozen candidate fingerprint.

The reason-code authority is `contracts/product/native-view-capability-reason-codes-v1.yaml`, the taxonomy is `contracts/product/native-view-capability-taxonomy-v1.yaml`, and structural constraints are `contracts/schemas/product-view-capability-ledger-v1.yaml` and `contracts/schemas/native-view-capability-reason-codes-v1.yaml`. Schema expresses local constraints only; the fail-closed guard enforces cross-file references, uniqueness, conservation, reason-stage matching, and hash recomputation.

## 6. Classification and correlation rules

Git commit identity uses a 40-character `git_oid`; content and manifest identity use 64-character SHA256. They are not interchangeable. Every resolved node and every governed attribute is a native candidate and must match exactly one machine-taxonomy rule or one explicit exclusion. Conservation is `native_candidate_count = classified_atom_count + excluded_native_count + unclassified_native_count + ambiguous_native_count`; unclassified, ambiguous, and silent-loss counts must be zero.

The current structure baseline proves the resolved view but not the exact contributor that originated each node. When origin is not proven, `origin_status=unproven`, `origin_view_ref` is empty, and the earliest-loss reason applies; inventing the root view as origin is forbidden. Reason priority is fixed as `native -> normalized -> semantic -> frontend -> interaction`.

Formal carriers are generated in the same candidate and `sc_clean` runtime and must exactly match `contract_ref/menu/action/model/view_type/view_ref/resolved_arch_sha256`. Legacy semantic samples and `model + view_type` similarity are not product evidence. Evidence selectors are limited to `json-pointer:/...` and `symbol:...`; paths remain under governed roots, file hashes and candidate fingerprints match, and selectors resolve.
