# Professional Relation Lifecycle v1

Phase 8D establishes one generic lifecycle authority for relation search, create, cancel, and successful return settlement.

- Child and parent forms share one typed message identity: nonce, parent model, relation model, and parent field.
- Origin, iframe source, lifecycle identity, and record identity must all match before settlement.
- Successful creation backfills once and closes search/create layers once.
- Cancellation closes only the create layer and restores the preserved search context when declared.
- Parent draft state and URL remain outside the child lifecycle and are never reset by settlement.
- No model, action, menu, route, label, or industry special case is permitted.
