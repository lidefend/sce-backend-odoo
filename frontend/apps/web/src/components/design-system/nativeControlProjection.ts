import type { Directive } from 'vue';

export interface NativeControlProjection {
  selector: 'input' | 'textarea';
  attributes: Record<string, string | boolean | undefined>;
}

function project(root: HTMLElement, binding: NativeControlProjection) {
  const control = root.matches(binding.selector) ? root : root.querySelector(binding.selector);
  if (!(control instanceof HTMLElement)) return;
  for (const [name, value] of Object.entries(binding.attributes)) {
    if (value === undefined || value === false || value === '') control.removeAttribute(name);
    else control.setAttribute(name, value === true ? '' : String(value));
  }
}

export const nativeControlProjection: Directive<HTMLElement, NativeControlProjection> = {
  mounted: project,
  updated: project,
};
