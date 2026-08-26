import assert from 'node:assert/strict';
import { resolveActivityTabKeyboardIndex } from '../src/components/product-shell/activityPageTabKeyboard.ts';

assert.equal(resolveActivityTabKeyboardIndex({ key: 'ArrowRight', currentIndex: 0, count: 3 }), 1);
assert.equal(resolveActivityTabKeyboardIndex({ key: 'ArrowRight', currentIndex: 2, count: 3 }), 0);
assert.equal(resolveActivityTabKeyboardIndex({ key: 'ArrowLeft', currentIndex: 0, count: 3 }), 2);
assert.equal(resolveActivityTabKeyboardIndex({ key: 'Home', currentIndex: 2, count: 3 }), 0);
assert.equal(resolveActivityTabKeyboardIndex({ key: 'End', currentIndex: 0, count: 3 }), 2);
assert.equal(resolveActivityTabKeyboardIndex({ key: 'Enter', currentIndex: 0, count: 3 }), null);
assert.equal(resolveActivityTabKeyboardIndex({ key: 'ArrowRight', currentIndex: -1, count: 3 }), null);
assert.equal(resolveActivityTabKeyboardIndex({ key: 'ArrowRight', currentIndex: 0, count: 0 }), null);

console.log('[activity_page_tab_keyboard_test] PASS cases=8');
