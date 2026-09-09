import { strict as assert } from 'node:assert';
import {
  clampWorksheetPaneSize,
  resizeWorksheetPaneFromKeyboard,
  resolveVisibleWorksheetRecordId,
  shouldOpenWorksheetRecordFromKeyboard,
} from '../src/app/action_runtime/hierarchicalWorksheetInteraction';

const row = {} as EventTarget;
const expander = {} as EventTarget;
const record = { id: 7 };

assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: 'Enter', target: row, currentTarget: row }, record), true);
assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: 'Enter', target: expander, currentTarget: row }, record), false);
assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: 'Enter', target: row, currentTarget: row }, null), false);
assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: ' ', target: row, currentTarget: row }, record), false);

assert.deepEqual(resizeWorksheetPaneFromKeyboard('navigation', 260, 'ArrowRight'), { handled: true, value: 276 });
assert.deepEqual(resizeWorksheetPaneFromKeyboard('navigation', 200, 'ArrowLeft'), { handled: true, value: 200 });
assert.deepEqual(resizeWorksheetPaneFromKeyboard('navigation', 260, 'Home'), { handled: true, value: 200 });
assert.deepEqual(resizeWorksheetPaneFromKeyboard('detail', 210, 'ArrowUp'), { handled: true, value: 226 });
assert.deepEqual(resizeWorksheetPaneFromKeyboard('detail', 210, 'ArrowDown'), { handled: true, value: 194 });
assert.deepEqual(resizeWorksheetPaneFromKeyboard('detail', 210, 'End'), { handled: true, value: 420 });
assert.deepEqual(resizeWorksheetPaneFromKeyboard('detail', 210, 'Enter'), { handled: false, value: 210 });
assert.equal(clampWorksheetPaneSize('detail', 999), 420);

assert.equal(resolveVisibleWorksheetRecordId([7, 8], 8), 8);
assert.equal(resolveVisibleWorksheetRecordId([7, 8], 9), 7);
assert.equal(resolveVisibleWorksheetRecordId([], 8), null);

console.log('[hierarchical_worksheet_interaction_test] PASS cases=15');
