#!/usr/bin/env node
import assert from 'node:assert/strict';

import {
  appPathname,
  assertDateSelection,
  assertExpectedProjectRecord,
  projectRecordTarget,
  targetInitiationDate,
} from './local_dev_project_profile_write_contract.mjs';

let cases = 0;
const check = (actual, expected, label) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};
const rejects = (run, pattern, label) => {
  assert.throws(run, pattern, label);
  cases += 1;
};

check(appPathname('http://example.invalid/t/demo/f/project.project/1053'), '/f/project.project/1053',
  'the app pathname strips the tenant namespace');
check(projectRecordTarget('http://example.invalid/t/demo/r/project.project/1053'),
  { surface: 'r', projectId: 1053 }, 'the exact delivered record target is parsed');
check(projectRecordTarget('http://example.invalid/t/demo/f/res.partner/1053'), null,
  'another model is not treated as a project target');
check(assertExpectedProjectRecord('http://example.invalid/t/demo/f/project.project/1053', 1053),
  { surface: 'f', projectId: 1053 }, 'the expected project identity is accepted');
rejects(
  () => assertExpectedProjectRecord('http://example.invalid/t/demo/r/project.project/999', 1053),
  /opened project 999, expected 1053/,
  'the home entry cannot silently open another project',
);

check(targetInitiationDate('2026-11-13', 10), '2026-11-10',
  'the target date is a full different date');
check(targetInitiationDate('2026-11-10', 10), '2026-11-11',
  'the target date moves when the preferred day equals the original');
check(targetInitiationDate('', 31, new Date(2026, 1, 1)), '2026-02-28',
  'the target date stays inside the selected month');

assertDateSelection({
  before: '2026-11-13',
  target: '2026-11-10',
  after: '2026-11-10',
  writeValue: '2026-11-10',
});
cases += 1;
rejects(
  () => assertDateSelection({
    before: '2026-11-13',
    target: '2026-11-10',
    after: '2026-11-13',
    writeValue: '2026-11-10',
  }),
  /did not become 2026-11-10/,
  'an unchanged date control fails even when readback equals the old value',
);
rejects(
  () => assertDateSelection({
    before: '2026-11-13',
    target: '2026-11-10',
    after: '2026-11-10',
    writeValue: '',
  }),
  /date write value/,
  'a missing date write value fails',
);

console.log(`[local_dev_project_profile_write_contract_test] PASS cases=${cases}`);
