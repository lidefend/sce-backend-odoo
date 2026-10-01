import type { RelationActionOrigin } from '@sc/schema';

// Transport navigation provenance; the backend must revalidate every field.
export function relationActionOrigin(query: Record<string, unknown>): RelationActionOrigin | undefined {
  if (!query.return_record_id) return undefined;
  return {
    model: String(query.return_model || ''),
    record_id: Number(query.return_record_id),
    field: String(query.return_field || ''),
    action_id: Number(query.return_action_id || 0),
    menu_id: Number(query.return_menu_id || 0),
  };
}
