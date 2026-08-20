# Product View Contract Carriers V1

Chinese version: [产品视图契约载体 V1](product_view_contract_carriers_v1.md)

## Role

This contract is a P4 evidence asset containing normalized and semantic carriers from the final `LoadContractHandler` response for every formal product view. It is not runtime authority and must never infer, repair, or default a missing capability.

## Capture boundary

- Only governed `local.clean` is allowed: `sc-local-clean` / `sc_clean` / `^sc_clean$` / `demo_data=false`.
- Requests use `include=all` and `force_refresh=true` to prevent carrier-free 304 responses.
- Capture fails closed when runtime registers an `app.contract.service` whose read-only behavior is not proven by this repository.
- Capture uses a dedicated database cursor with both session and transaction read-only settings, then rolls back and restores the connection default. This guarantees database write rejection; it does not claim to intercept unregistered external side effects.
- `tree` is the canonical Odoo 17 type; the handler is never called with `list`.
- Capture consumes only `artifacts/contract/product_view_structure_candidate.json` exported and gated under the same candidate fingerprint; a historical tracked baseline is not a substitute.
- Database views bind the runtime record through `context.requested_view_id`; synthetic defaults must not fabricate that ID.

## Carrier rules

- Normalized evidence comes only from final-response `/data/views/<type>` and, for search, `/data/search`.
- `/data/native_view/*` is an alias projection and is never counted again.
- Semantic evidence comes only from `/data/semantic_page` with `version=v1` and `source=load_contract`.
- Values are SHA-256 hashed as key-sorted compact UTF-8 JSON while preserving array order.
- Artifact selectors are resolvable RFC 6901 JSON Pointers.
- Every surface binds the structure baseline `contract_ref`, `view_ref`, and all three structure hashes.
- The stable selector uses only cross-database stable fields and runtime authority; numeric `menu_id`, `action_id`, and `requested_view_id` are excluded.

## Failure policy

Handler errors, 304 responses, missing normalized carriers, incomplete surface coverage, and identity or hash drift cause a non-zero exporter or guard result. Missing semantic evidence may be recorded as `normalized_only`, but it must not be inferred as present.

Schema: `contracts/schemas/product-view-contract-carriers-v1.yaml`.
