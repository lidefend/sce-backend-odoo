import type { Directive, DirectiveBinding } from 'vue';

export interface NativeControlProjection {
  selector: 'input' | 'textarea';
  attributes: Record<string, string | number | boolean | undefined>;
}

function project(root: HTMLElement, binding: DirectiveBinding<NativeControlProjection>) {
  const control = root.matches(binding.value.selector) ? root : root.querySelector(binding.value.selector);
  if (!(control instanceof HTMLElement)) return;
  for (const [name, value] of Object.entries(binding.value.attributes)) {
    if (value === undefined || value === false || value === '') control.removeAttribute(name);
    else control.setAttribute(name, value === true ? '' : String(value));
  }
}

export const nativeControlProjection: Directive<HTMLElement, NativeControlProjection> = {
  mounted: project,
  updated: project,
};
