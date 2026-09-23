/**
 * Executable proof for the collaboration region authority.
 *
 * The collaboration region is visible when the runtime capability is on, or when
 * a subordinate node is a collaboration surface kind and collaboration is not
 * suppressed.  That rule is stated once, in `contractRuntimeVm.ts`; this test
 * executes the real module so the rule cannot be retired by rearranging tokens:
 * an inverted predicate, an emptied kind list, a dead `||` operand or a dropped
 * suppression gate each changes at least one expectation below.
 *
 * The tables run twice: once under node, and once with browser globals installed.
 * A rule that is live under node and inert in the browser is a different rule, and
 * the second pass is what makes that visible here instead of in the product.
 */
import assert from 'node:assert/strict';
import {
  COLLABORATION_SURFACE_KINDS,
  hasCollaborationNode,
  isCollaborationSurfaceKind,
  resolveCollaborationVisibility,
} from '../src/pages/contractForm/contractRuntimeVm';

const declaredKinds = COLLABORATION_SURFACE_KINDS as readonly string[];
const node = (kind: unknown) => ({ kind });

const kindCases: Array<[unknown, boolean]> = [
  ['chatter', true],
  ['activity', true],
  ['CHATTER', true],
  ['Activity', true],
  [' chatter ', true],
  ['note', false],
  ['audit', false],
  ['', false],
  ['  ', false],
  [0, false],
  [null, false],
  [undefined, false],
  [{}, false],
];

const nodeCases: Array<[Array<{ kind?: unknown }> | null | undefined, boolean]> = [
  [[], false],
  [undefined, false],
  [null, false],
  [[node('note')], false],
  [[node(undefined)], false],
  [[node('chatter')], true],
  [[node('note'), node('activity')], true],
  [[node('note'), node('audit')], false],
  [[node('ACTIVITY')], true],
];

const visibilityCases: Array<[unknown, boolean | undefined, Array<{ kind?: unknown }>, boolean]> = [
  [true, false, [], true],
  [true, true, [], true],
  [true, true, [node('chatter')], true],
  [false, false, [], false],
  [false, true, [], false],
  [false, false, [node('chatter')], true],
  [false, true, [node('chatter')], false],
  [false, false, [node('activity')], true],
  [false, true, [node('activity')], false],
  [false, false, [node('note')], false],
  [false, false, [node('note'), node('activity')], true],
  [false, true, [node('note'), node('chatter')], false],
  [undefined, false, [node('chatter')], true],
  [undefined, true, [node('chatter')], false],
  [0, false, [node('chatter')], true],
  ['', false, [node('chatter')], true],
  [false, undefined, [node('chatter')], true],
  [false, false, [node('CHATTER')], true],
  [false, false, [node(' chatter ')], true],
  [false, false, [node('')], false],
  ['', true, [], false],
  [0, true, [], false],
  ['yes', true, [], true],
  [1, true, [], true],
  [false, true, [node('note')], false],
];

/** Run every table.  `environment` only labels the failure messages. */
function runTables(environment: string): void {
  const where = ` [${environment}]`;

  // 1. The declared kind list is consumed by the predicate, and is monotone.
  for (const kind of declaredKinds) {
    assert.strictEqual(
      isCollaborationSurfaceKind(kind),
      true,
      `declared kind must be accepted: ${kind}${where}`,
    );
  }
  for (const kind of ['chatter', 'activity']) {
    assert.strictEqual(
      declaredKinds.includes(kind),
      true,
      `declared kind must stay declared: ${kind}${where}`,
    );
  }

  // 2. Kind predicate truth table (case- and whitespace-insensitive).  Every
  // expectation is compared with `strictEqual`, so a truthy-but-not-boolean return
  // is a failure rather than a pass: the authorities are typed `boolean`, and a
  // weakened return contract must not survive the proof.
  for (const [kind, expected] of kindCases) {
    assert.strictEqual(
      isCollaborationSurfaceKind(kind),
      expected,
      `kind ${JSON.stringify(kind) ?? 'undefined'}${where}`,
    );
  }

  // 3. Node authority is an existential test over the subordinate zone.
  for (const [nodes, expected] of nodeCases) {
    assert.strictEqual(
      hasCollaborationNode(nodes),
      expected,
      `nodes ${JSON.stringify(nodes) ?? 'undefined'}${where}`,
    );
  }

  // 4. Visibility truth table: capability OR (not suppressed AND node authority).
  for (const [capability, suppressed, nodes, expected] of visibilityCases) {
    assert.strictEqual(
      resolveCollaborationVisibility({ capability, suppressed, nodes }),
      expected,
      `capability=${String(capability)} suppressed=${String(suppressed)} `
        + `nodes=${JSON.stringify(nodes)}${where}`,
    );
  }

  // 5. Both operands are load-bearing, and the capability is an alternative.
  assert.strictEqual(
    resolveCollaborationVisibility({ capability: false, suppressed: false, nodes: [node('chatter')] }),
    true,
    `the node authority must be able to switch the region on without the capability${where}`,
  );
  assert.strictEqual(
    resolveCollaborationVisibility({ capability: false, suppressed: true, nodes: [node('chatter')] }),
    false,
    `suppression must be able to gate the node authority${where}`,
  );
  assert.strictEqual(
    resolveCollaborationVisibility({ capability: true, suppressed: true, nodes: [] }),
    true,
    `the capability is an alternative to the node authority, not a condition on it${where}`,
  );
  assert.strictEqual(
    hasCollaborationNode([node('note')]),
    false,
    `a non-collaboration subordinate node must not switch the region on${where}`,
  );
}

runTables('node');

// 6. The same tables with the browser globals present, so a rule that is gated on
//    `window`/`document`/`navigator`/`self` fails here - under node such a branch
//    is inert, which is exactly how an environment-gated rule used to pass both
//    this proof and the wiring guard while the region never rendered.
const browserGlobals: Array<[string, unknown]> = [
  ['window', globalThis],
  ['document', {}],
  ['navigator', {}],
  ['self', globalThis],
];
const browserGlobalScope = globalThis as unknown as Record<string, unknown>;
const previousBrowserGlobals = new Map<string, PropertyDescriptor | undefined>();
for (const [key, value] of browserGlobals) {
  previousBrowserGlobals.set(key, Object.getOwnPropertyDescriptor(browserGlobalScope, key));
  try {
    Object.defineProperty(browserGlobalScope, key, { value, writable: true, configurable: true });
  } catch {
    // A host-defined global that cannot be redefined (`node` 22 exposes `navigator`
    // as a lazy getter) is already present, which is the condition this pass needs.
    // Presence is asserted below rather than assumed here.
  }
}
let browserDomainPassed = false;
try {
  for (const [key] of browserGlobals) {
    assert.notStrictEqual(
      browserGlobalScope[key],
      undefined,
      `the browser-domain pass must run with ${key} present`,
    );
  }
  runTables('browser globals present');
  browserDomainPassed = true;
} finally {
  for (const [key, descriptor] of previousBrowserGlobals) {
    if (descriptor === undefined) {
      delete browserGlobalScope[key];
    } else {
      Object.defineProperty(browserGlobalScope, key, descriptor);
    }
  }
}
assert.strictEqual(browserDomainPassed, true, 'the browser-domain pass must run to completion');
for (const [key] of browserGlobals) {
  const descriptor = previousBrowserGlobals.get(key);
  assert.deepStrictEqual(
    Object.getOwnPropertyDescriptor(browserGlobalScope, key),
    descriptor,
    `the browser-domain pass must restore the ${key} global`,
  );
}

const totalCases = (kindCases.length + nodeCases.length + visibilityCases.length + 4) * 2;
console.log(`[contract_form_collaboration_authority] PASS cases=${totalCases}`);
