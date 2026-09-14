import type { Directive, DirectiveBinding } from 'vue';

export interface NativeControlProjection {
  selector: 'input' | 'textarea' | '.t-table__content';
  attributes: Record<string, string | number | boolean | undefined>;
}

export function nativeControlAttributeValue(
  name: string,
  value: string | number | boolean | undefined,
): string | null {
  if (value === undefined || value === false || value === '') return null;
  if (value === true) return name.startsWith('aria-') ? 'true' : '';
  return String(value);
}

function project(root: HTMLElement, binding: DirectiveBinding<NativeControlProjection>) {
  const control = root.matches(binding.value.selector) ? root : root.querySelector(binding.value.selector);
  if (!(control instanceof HTMLElement)) return;
  for (const [name, value] of Object.entries(binding.value.attributes)) {
    const attributeValue = nativeControlAttributeValue(name, value);
    if (attributeValue === null) control.removeAttribute(name);
    else control.setAttribute(name, attributeValue);
  }
}

export const nativeControlProjection: Directive<HTMLElement, NativeControlProjection> = {
  mounted: project,
  updated: project,
};
