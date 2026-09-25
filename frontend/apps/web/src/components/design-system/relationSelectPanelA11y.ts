/**
 * ARIA projection for the official TDesign Select candidate panel.
 *
 * Official-capability gap (tdesign-vue-next@1.20.5): the `Select` panel renders
 * `<li class="t-select-option">` rows without `role="option"`/`aria-selected`
 * and the option list carries no listbox role, while the public API exposes no
 * slot for the option rows. Assistive technology therefore cannot announce the
 * candidate list or the active option.
 *
 * This module projects only the missing semantics onto the official DOM. It owns
 * no interaction: keyboard navigation, focus, selection and popup lifecycle stay
 * with the official component; the projection mirrors the component's own state
 * (hovered row, selected value) into ARIA attributes and stable automation hooks.
 * Remove it once the official Select exposes option roles or an option-row slot.
 */

export interface RelationSelectPanelA11ySource {
  panelId: () => string;
  activeValue: () => string;
  optionValues: () => readonly string[];
}

const OPTION_SELECTOR = 'li.t-select-option';
const OPTION_LIST_SELECTOR = 'ul.t-select__list';
const OPTION_HOVER_CLASS = 't-select-option__hover';

function apply(panel: HTMLElement, input: HTMLElement | null, source: RelationSelectPanelA11ySource): void {
  const panelId = source.panelId();
  panel.setAttribute('id', panelId);
  const list = panel.querySelector(OPTION_LIST_SELECTOR);
  if (list instanceof HTMLElement) list.setAttribute('role', 'listbox');
  const activeValue = source.activeValue();
  const optionValues = source.optionValues();
  const rows = Array.from(panel.querySelectorAll<HTMLElement>(OPTION_SELECTOR));
  // The official panel renders rows in option order, so the projected value is
  // only trusted while both counts agree (skips virtual-scroll windows).
  const aligned = rows.length === optionValues.length;
  let activeId = '';
  rows.forEach((row, index) => {
    const optionId = `${panelId}-option-${index}`;
    const optionValue = aligned ? optionValues[index] : undefined;
    row.setAttribute('role', 'option');
    row.setAttribute('id', optionId);
    if (optionValue === undefined) row.removeAttribute('data-relation-option-value');
    else row.setAttribute('data-relation-option-value', String(optionValue));
    row.setAttribute('aria-selected', optionValue !== undefined && String(optionValue) === activeValue ? 'true' : 'false');
    if (row.classList.contains(OPTION_HOVER_CLASS)) activeId = optionId;
  });
  if (!(input instanceof HTMLElement)) return;
  if (activeId) input.setAttribute('aria-activedescendant', activeId);
  else input.removeAttribute('aria-activedescendant');
}

export function observeRelationSelectPanelA11y(
  panel: HTMLElement,
  input: HTMLElement | null,
  source: RelationSelectPanelA11ySource,
): () => void {
  const sync = () => apply(panel, input, source);
  sync();
  if (typeof MutationObserver !== 'function') return () => {};
  // Only class/child mutations can change the active row, so the projection
  // never reacts to its own attribute writes.
  const observer = new MutationObserver(() => sync());
  observer.observe(panel, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
  return () => observer.disconnect();
}

let relationFieldInstanceSequence = 0;

export function nextRelationSelectPanelInstanceId(): string {
  relationFieldInstanceSequence += 1;
  return `sc-relation-field-${relationFieldInstanceSequence}`;
}
