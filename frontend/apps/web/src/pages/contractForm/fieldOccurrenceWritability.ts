import type { CanonicalFormNode, CanonicalFormRenderModel } from '../../app/presentation/canonicalFormRenderModel';
import type { LayoutNode } from './types';

/**
 * Occurrence-scoped writability for user field edits.
 *
 * One field code can be rendered at several positions on the same form: a
 * summary occurrence that is read-only, a detail occurrence that is editable,
 * repeated native occurrences of the same field, and so on. A user edit event
 * therefore carries the identity of the occurrence that emitted it, and the
 * decision to accept the edit must be taken for that occurrence alone.
 *
 * Aggregating the answer over every position that shares the field name ("some
 * occurrence is writable, so accept") lets a read-only position write the draft
 * through an editable sibling. That aggregate is never used for a keyed event;
 * an identity the contract cannot resolve is rejected instead of being
 * normalised into "find a writable position".
 */
export type FieldOccurrence = {
  /** Occurrence identity emitted by the control: canonical widgetId / layout key. */
  key: string;
  /** Field code this occurrence renders. */
  name: string;
  readonly: boolean;
  disabled: boolean;
};

export type FieldOccurrenceDecision = 'writable' | 'blocked' | 'unresolved';

export type FieldOccurrenceSources = {
  /** Contract-declared occurrences: page/record/container/slot/status conditions. */
  canonical: readonly FieldOccurrence[];
  /** Rendered native positions: descriptor, occurrence modifiers and rights. */
  layout: readonly FieldOccurrence[];
};

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function flattenCanonicalNode(node: CanonicalFormNode, out: FieldOccurrence[]): void {
  node.fields.forEach((field) => {
    out.push({
      key: text(field.widgetId),
      name: text(field.fieldCode),
      readonly: field.readonly === true,
      disabled: field.disabled === true,
    });
  });
  node.children.forEach((child) => flattenCanonicalNode(child, out));
}

export function collectCanonicalFieldOccurrences(model: CanonicalFormRenderModel | null | undefined): FieldOccurrence[] {
  if (!model) return [];
  const out: FieldOccurrence[] = [];
  [...model.zones.primary, ...model.zones.subordinate].forEach((node) => flattenCanonicalNode(node, out));
  return out.filter((occurrence) => occurrence.key && occurrence.name);
}

export function collectLayoutFieldOccurrences(nodes: readonly LayoutNode[] | null | undefined): FieldOccurrence[] {
  return (nodes || [])
    .filter((node) => node.kind === 'field' && text(node.key) && text(node.name))
    .map((node) => ({
      key: text(node.key),
      name: text(node.name),
      readonly: node.readonly === true,
      disabled: false,
    }));
}

/**
 * Resolve the writability of one occurrence identity.
 *
 * The contract decides first, because it also carries the page, record and
 * container editability conditions; the rendered position decides when the
 * contract does not name that position (compatibility layouts). A key that no
 * source knows, or that resolves to a different field, is `unresolved`.
 */
export function resolveFormOccurrenceDecision(
  sources: FieldOccurrenceSources,
  name: string,
  occurrenceKey: string,
): FieldOccurrenceDecision {
  const fieldName = text(name);
  const key = text(occurrenceKey);
  if (!fieldName || !key) return 'unresolved';
  for (const occurrences of [sources.canonical, sources.layout]) {
    const matches = occurrences.filter((occurrence) => occurrence.key === key);
    if (!matches.length) continue;
    // The position must belong to the field the event declared. A key that
    // names an occurrence of another field is a mismatched identity, not a
    // reason to look for a different position.
    if (matches.some((occurrence) => occurrence.name !== fieldName)) return 'unresolved';
    const editability = new Set(matches.map((occurrence) => occurrence.readonly || occurrence.disabled));
    // Duplicate keys that disagree describe an ambiguous identity.
    if (editability.size !== 1) return 'unresolved';
    return editability.has(true) ? 'blocked' : 'writable';
  }
  return 'unresolved';
}

/**
 * The decision function the page hands to the record-form runtime. It is
 * created here, not inline in the page, so the exact function under test is the
 * exact function production uses.
 */
export function createFormOccurrenceDecision(
  sources: () => FieldOccurrenceSources,
): (name: string, occurrenceKey: string) => FieldOccurrenceDecision {
  return (name, occurrenceKey) => resolveFormOccurrenceDecision(sources(), name, occurrenceKey);
}

/**
 * Name-only aggregate kept for callers that have no occurrence identity: the
 * native companions of a rendered control (a date range's hidden end field, a
 * favourite toggle) and the relation hooks that read a field as a whole.
 */
export function resolveNamedFieldWritable(
  occurrences: readonly FieldOccurrence[],
  name: string,
): boolean | undefined {
  const fieldName = text(name);
  if (!fieldName) return undefined;
  const matches = occurrences.filter((occurrence) => occurrence.name === fieldName);
  if (!matches.length) return undefined;
  return matches.some((occurrence) => !occurrence.readonly && !occurrence.disabled);
}
