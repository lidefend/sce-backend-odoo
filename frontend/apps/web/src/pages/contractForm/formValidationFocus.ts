export type ValidationField = { kind: string; name: string; label: string };

function isVisible(element: HTMLElement) {
  const style = window.getComputedStyle(element);
  return style.display !== 'none' && style.visibility !== 'hidden' && element.getClientRects().length > 0;
}

function revealDisclosureAncestors(element: HTMLElement) {
  let parent = element.parentElement;
  while (parent) {
    if (parent instanceof HTMLDetailsElement) parent.open = true;
    parent = parent.parentElement;
  }
}

export function focusProductFormValidationError(fieldName: string, fields: ValidationField[]) {
  void fields;
  const form = document.querySelector<HTMLElement>('[data-product-page-mode="form"]');
  if (!form) return;
  const normalized = String(fieldName || '').trim();
  if (!normalized) {
    form.querySelector<HTMLElement>('[data-form-error-summary]')?.focus({ preventScroll: true });
    return;
  }
  const exactTargets = Array.from(form.querySelectorAll<HTMLElement>(`[data-validation-target="${CSS.escape(normalized)}"]`));
  const containers = exactTargets.length
    ? exactTargets
    : Array.from(form.querySelectorAll<HTMLElement>(`[data-field-name="${CSS.escape(normalized)}"]`));
  for (const container of containers) {
    revealDisclosureAncestors(container);
    const controls = container.matches('input, select, textarea, button, [tabindex]')
      ? [container]
      : Array.from(container.querySelectorAll<HTMLElement>('input, select, textarea, button, [tabindex]'));
    const control = controls.find(isVisible);
    if (!control || !isVisible(container)) continue;
    control.focus({ preventScroll: true });
    container.scrollIntoView({ block: 'nearest', behavior: 'auto' });
    return;
  }
}
