import assert from 'node:assert/strict';
import { activateNavigationMenuFromKeyboard } from '../src/components/product-shell/navigationMenuKeyboard';

class KeyboardTarget {
  clicks = 0;
  toggle: KeyboardTarget | null;

  constructor(toggle: KeyboardTarget | null = null) {
    this.toggle = toggle;
  }

  querySelector(selector: string): Element | null {
    assert.equal(selector, '[data-navigation-toggle="submenu"]');
    return this.toggle as unknown as Element | null;
  }

  click(): void {
    this.clicks += 1;
  }
}

Object.defineProperty(globalThis, 'HTMLElement', {
  configurable: true,
  value: KeyboardTarget,
});

for (const key of ['Enter', ' ']) {
  const toggle = new KeyboardTarget();
  const submenu = new KeyboardTarget(toggle);
  activateNavigationMenuFromKeyboard({
    key,
    currentTarget: submenu as unknown as EventTarget,
  } as unknown as KeyboardEvent);
  assert.equal(toggle.clicks, 1, `${key} activates the registered submenu toggle`);
  assert.equal(submenu.clicks, 0, `${key} does not click the submenu list item`);

  const leaf = new KeyboardTarget();
  activateNavigationMenuFromKeyboard({
    key,
    currentTarget: leaf as unknown as EventTarget,
  } as unknown as KeyboardEvent);
  assert.equal(leaf.clicks, 1, `${key} activates a leaf menu item`);
}

console.log('[navigation_menu_keyboard_test] PASS cases=4');
