import { strict as assert } from 'node:assert';
import { shouldOpenWorksheetRecordFromKeyboard } from '../src/app/action_runtime/hierarchicalWorksheetInteraction';

const row = {} as EventTarget;
const expander = {} as EventTarget;
const record = { id: 7 };

assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: 'Enter', target: row, currentTarget: row }, record), true);
assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: 'Enter', target: expander, currentTarget: row }, record), false);
assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: 'Enter', target: row, currentTarget: row }, null), false);
assert.equal(shouldOpenWorksheetRecordFromKeyboard({ key: ' ', target: row, currentTarget: row }, record), false);

console.log('[hierarchical_worksheet_interaction_test] PASS cases=4');
