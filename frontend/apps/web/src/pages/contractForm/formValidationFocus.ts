import { parseBusinessErrorDisplayPosition, type BusinessErrorDisplayPosition } from '../../app/businessValidationError';
import {
  selectValidationPosition,
  type ValidationPositionCandidate,
  type ValidationPositionChoice,
} from './validationErrorPosition';

export type ValidationField = { kind: string; name: string; label: string };

/**
 * A local display target for focus.
 *
 * A string is the page-local display key carried by the error summary and by
 * the registered position attributes. The object form additionally carries the
 * occurrence that produced the value, which is preferred when it still resolves.
 * Neither form is business ownership: the business target stays in the error
 * state.
 */
export type ProductFormFocusTarget = string | { key?: string; sourceOccurrenceKey?: string };

export type ProductFormFocusResult = 'focused' | 'summary' | 'no-form';

const CONTROL_SELECTOR = 'input, select, textarea, button, [tabindex]';

function isVisible(element: HTMLElement) {
  const style = window.getComputedStyle(element);
  return style.display !== 'none' && style.visibility !== 'hidden' && element.getClientRects().length > 0;
}

function isControlUsable(control: HTMLElement) {
  if (control.getAttribute('aria-disabled') === 'true') return false;
  if (control.getAttribute('data-field-state') === 'readonly') return false;
  if (!('disabled' in control)) return true;
  const field = control as HTMLInputElement;
  return !field.disabled && !field.readOnly;
}

function isNativeDisabled(element: HTMLElement) {
  return 'disabled' in element && Boolean((element as HTMLInputElement).disabled);
}

function revealDisclosureAncestors(element: HTMLElement) {
  let parent = element.parentElement;
  while (parent) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
    parent = parent.parentElement;
  }
}

/**
 * Collapsed disclosure triggers that hide this element.
 *
 * A collapsed panel keeps its content in the DOM, so the error target exists but
 * is not reachable. Expanding is the existing mechanism for reachable-but-hidden
 * content; a target that is not mounted at all is not repaired by guessing.
 */
function collapsedDisclosureTriggers(element: HTMLElement): HTMLElement[] {
  const triggers: HTMLElement[] = [];
  let parent = element.parentElement;
  while (parent) {
    const trigger = parent.querySelector<HTMLElement>('[data-disclosure-trigger][aria-expanded="false"]');
    if (trigger && !triggers.includes(trigger)) triggers.push(trigger);
    parent = parent.parentElement;
  }
  return triggers;
}

function focusSummary(form: HTMLElement): ProductFormFocusResult {
  form.querySelector<HTMLElement>('[data-form-error-summary]')?.focus({ preventScroll: true });
  return 'summary';
}

function containersFor(form: HTMLElement, position: BusinessErrorDisplayPosition): { exact: HTMLElement[]; field: HTMLElement[] } {
  const exact = Array.from(form.querySelectorAll<HTMLElement>(`[data-validation-target="${CSS.escape(position.key)}"]`));
  // A collection container cannot identify a missing row/cell. Keep its error
  // in the summary rather than focusing a sibling row or an add-row control.
  const fallback = exact.length || position.rowKey || position.cellField
    ? []
    : Array.from(form.querySelectorAll<HTMLElement>(`[data-field-name="${CSS.escape(position.fieldCode)}"]`));
  return { exact, field: fallback };
}

function candidateFor(container: HTMLElement, key: string): { candidate: ValidationPositionCandidate; control: HTMLElement | null } {
  revealDisclosureAncestors(container);
  const control = container.matches(CONTROL_SELECTOR)
    ? container
    : container.querySelector<HTMLElement>(CONTROL_SELECTOR);
  const state = container.getAttribute('data-field-state') || (control ? control.getAttribute('data-field-state') : null);
  const declared = state === null ? undefined : state !== 'readonly';
  const visible = isVisible(container) && (!control || isVisible(control));
  const correctable = declared === false
    ? false
    : Boolean(control) && !isNativeDisabled(control as HTMLElement) && isControlUsable(control as HTMLElement);
  return {
    candidate: {
      key,
      occurrenceKey: String(container.getAttribute('data-field-key') || container.getAttribute('data-occurrence-key') || '').trim(),
      visible,
      correctable,
    },
    control: visible ? control : null,
  };
}

function choosePosition(
  containers: HTMLElement[],
  key: string,
  sourceOccurrenceKey: string,
): { choice: ValidationPositionChoice; element: HTMLElement | null } {
  const resolved = containers.map((container) => ({ container, ...candidateFor(container, key) }));
  const choice = selectValidationPosition(resolved.map((item) => item.candidate), { sourceOccurrenceKey });
  if (!choice.position) return { choice, element: null };
  const match = resolved.find((item) => item.candidate === choice.position);
  return { choice, element: match ? match.container : null };
}

function applyFocus(container: HTMLElement): ProductFormFocusResult {
  const candidates = container.matches(CONTROL_SELECTOR)
    ? [container]
    : Array.from(container.querySelectorAll<HTMLElement>(CONTROL_SELECTOR));
  const control = candidates.find((item) => isVisible(item) && !isNativeDisabled(item));
  const focusTarget = control || container;
  if (focusTarget === container && !container.hasAttribute('tabindex')) container.setAttribute('tabindex', '-1');
  focusTarget.focus({ preventScroll: true });
  container.scrollIntoView({ block: 'nearest', behavior: 'auto' });
  return 'focused';
}

function nextFrame(): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window.requestAnimationFrame === 'function') window.requestAnimationFrame(() => resolve());
    else setTimeout(resolve, 0);
  });
}

/**
 * Move focus to the position that can correct one business error.
 *
 * Selection order: a registered position carrying the same business key, then
 * the field's positions, and only those the user can actually correct. Errors
 * are never cleared here: an unresolved position keeps its error and falls back
 * to the form-level summary, which lists the same business ownership.
 */
export async function focusProductFormValidationError(
  target: ProductFormFocusTarget,
  fields: ValidationField[] = [],
): Promise<ProductFormFocusResult> {
  void fields;
  const form = document.querySelector<HTMLElement>('[data-product-page-mode="form"]');
  if (!form) return 'no-form';
  const key = String((typeof target === 'string' ? target : target?.key) || '').trim();
  const sourceOccurrenceKey = String(typeof target === 'string' ? '' : target?.sourceOccurrenceKey || '').trim();
  const position = parseBusinessErrorDisplayPosition(key);
  if (!position) return focusSummary(form);

  const first = containersFor(form, position);
  for (const group of [first.exact, first.field]) {
    if (!group.length) continue;
    const { choice, element } = choosePosition(group, position.key, sourceOccurrenceKey);
    if (choice.outcome === 'position' && element) return applyFocus(element);
  }

  // The position may exist but sit inside a collapsed disclosure. Expand the
  // existing disclosure triggers once, then resolve again on the settled DOM.
  const hidden = [...first.exact, ...first.field].flatMap((container) => collapsedDisclosureTriggers(container));
  if (hidden.length) {
    hidden.forEach((trigger) => trigger.click());
    await nextFrame();
    const retried = containersFor(form, position);
    for (const group of [retried.exact, retried.field]) {
      if (!group.length) continue;
      const { choice, element } = choosePosition(group, position.key, sourceOccurrenceKey);
      if (choice.outcome === 'position' && element) return applyFocus(element);
    }
  }

  return focusSummary(form);
}
