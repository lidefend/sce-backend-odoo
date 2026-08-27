# Page Pattern Reference Contract Gaps v1

This ledger records reference details that cannot be implemented safely from the current authoritative payload. They are not permission to infer values in the frontend.

## P0 contract gaps

- Global search: the reference shell exposes a global search control, while the current payload only authorizes navigation filtering. A future capability must identify search domain, target route, result identity, and authority.
- Contextual detail drawer: the current record-entry contract expresses record intent and route disposition, but does not explicitly authorize `standalone_page | contextual_drawer`. Existing `/r` and `/f` semantics must not be reinterpreted by appearance.
- Record actions: copy, delete, disabled reason, and explicit labelled detail actions are not consistently projected for every model/action pair.
- Readonly section metadata: the reference displays section item counts. Contract V2 currently carries nodes and container structure but no authoritative displayed item-count presentation.

## P1/P2 product gaps

- Saved-search favorites need ownership and mutation capability before the favorite control can be universal.
- The Shell needs a formal user-facing release/version identity if the reference footer version is required.
- Authentication must declare credential-retention policy before a remember-account option stores any identifier.

## Evidence gaps

- No authenticated 390px screenshot exists for the reference implementation. Candidate mobile safety can be proven, but mobile visual parity cannot be claimed until the reference evidence is captured.

## Fail-closed rules

- Missing capability hides or disables the control; query parameters never create authority.
- No model, action, menu, field label, or Chinese-text special case may substitute for a missing contract field.
- A legacy route cannot silently become drawer authority.
- Visual similarity cannot override readonly/edit, action, mutation, or record-level permission decisions.
