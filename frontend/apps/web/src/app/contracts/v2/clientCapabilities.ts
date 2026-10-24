/**
 * Delivery capabilities implemented by this web client.
 *
 * These are transport/protocol declarations, not product semantics. Contract
 * requests and server-side configuration verification must consume the same
 * declaration so a preview cannot silently drop a component the actual client
 * already supports.
 */
export const CONTRACT_V2_CLIENT_CAPABILITIES = [
  'container_tree.v2',
  'data_source.v2',
  'action_rule.v2',
  'relation_entry.v2',
  'status_contract.v2',
  'form_layout.children_owner.v1',
  'form.feedback.message.v1',
  'form.feedback.draft.v1',
  'form.navigation.anchor.v1',
] as const;
