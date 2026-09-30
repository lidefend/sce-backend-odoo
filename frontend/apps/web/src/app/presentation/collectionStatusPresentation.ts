import { FIELD_VALUE_EMPTY_TEXT } from '../../utils/fieldSemantics.ts';

export type CollectionStatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

export type CollectionStatusDescriptor = {
  value: string;
  label: string;
  tone: CollectionStatusTone;
};

/**
 * Status badge colour is a presentation decision, so the palette lives here, in
 * the frontend presentation layer, and never in the business contract.  The
 * contract supplies the authoritative status value plus its business label; it
 * does not carry a colour, a theme name or any other design token.
 *
 * The policy is keyed by the authoritative state value (a platform-wide status
 * vocabulary), never by a display label, so a translated or renamed label can
 * never change how a record is coloured.
 *
 * Basis for each entry:
 * - the tones already in effect for the shared lifecycle vocabulary
 *   (draft/submit/approve/approved/in_progress/paused/done/closing/warranty/
 *   closed);
 * - the reference product renders the payment approval stage 审批中 as a
 *   warning badge and the approved stage 审核通过 as a success badge.
 *
 * A state absent from this policy keeps the design-system default badge.  That
 * covers cancel/cancelled and rejected, which the construction native views
 * also de-emphasise (decoration-muted) rather than flag as an error.
 */
const STATUS_TONE_POLICY: Record<string, CollectionStatusTone> = {
  // Shared lifecycle vocabulary (the tones already in effect for projects,
  // tasks, payment requests and material plans).
  draft: 'neutral',
  submit: 'warning',
  approve: 'warning',
  approved: 'success',
  in_progress: 'info',
  paused: 'warning',
  done: 'success',
  closing: 'warning',
  warranty: 'info',
  closed: 'neutral',
  // Generic progress and risk vocabulary this web app already colours.
  open: 'info',
  active: 'info',
  pending: 'warning',
  to_do: 'warning',
  todo: 'warning',
  unpaid: 'warning',
  warning: 'warning',
  blocked: 'danger',
  overdue: 'danger',
  risk: 'danger',
  high_risk: 'danger',
  rejected: 'danger',
  cancel: 'danger',
  cancelled: 'danger',
  paid: 'success',
  completed: 'success',
  normal: 'success',
  archived: 'neutral',
  new: 'neutral',
};

const TONES = new Set<CollectionStatusTone>(['neutral', 'info', 'success', 'warning', 'danger']);

function text(value: unknown): string {
  if (Array.isArray(value)) {
    if (value.length > 1 && value[1] !== null && value[1] !== undefined) return String(value[1]).trim();
    if (value.length) return String(value[0] ?? '').trim();
  }
  return String(value ?? '').trim();
}

function authorityKey(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] ?? '').trim();
  return String(value ?? '').trim();
}

export function resolveStatusTone(value: unknown): CollectionStatusTone {
  const key = authorityKey(value).toLowerCase();
  const tone = key ? STATUS_TONE_POLICY[key] : undefined;
  return tone && TONES.has(tone) ? tone : 'neutral';
}

export function resolveCollectionStatusPresentation(input: {
  value: unknown;
  selection?: Array<{ value: string; label: string }>;
}): CollectionStatusDescriptor {
  const value = authorityKey(input.value);
  const label = input.selection?.find((item) => item.value === value)?.label || text(input.value) || FIELD_VALUE_EMPTY_TEXT;
  return {
    value,
    label,
    tone: resolveStatusTone(input.value),
  };
}
