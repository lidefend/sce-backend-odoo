import assert from 'node:assert/strict';
import {
  activateWorkflowReasonTrigger,
  type WorkflowReasonKeyboardEvent,
} from '../src/pages/contractForm/workflowReasonTrigger';

function event(key: string, options: { sameTarget?: boolean; htmlTarget?: boolean } = {}) {
  let prevented = 0;
  let clicks = 0;
  const trigger = options.htmlTarget
    ? { click: () => { clicks += 1; } }
    : {};
  const currentTarget = trigger;
  const target = options.sameTarget === false ? {} : currentTarget;
  const keyboard = {
    key,
    currentTarget,
    target,
    preventDefault: () => { prevented += 1; },
  } as unknown as WorkflowReasonKeyboardEvent;
  activateWorkflowReasonTrigger(keyboard);
  return { prevented, clicks };
}

assert.deepEqual(event('Enter', { htmlTarget: true }), { prevented: 1, clicks: 1 });
assert.deepEqual(event(' ', { htmlTarget: true }), { prevented: 1, clicks: 1 });
assert.deepEqual(event('Tab', { htmlTarget: true }), { prevented: 0, clicks: 0 });
assert.deepEqual(event('Enter', { htmlTarget: true, sameTarget: false }), { prevented: 0, clicks: 0 });

console.log('[workflow_reason_trigger_test] PASS cases=4');
