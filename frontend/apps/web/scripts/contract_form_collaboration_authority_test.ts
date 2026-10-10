/**
 * Executable proof for the collaboration region authority.
 *
 * The collaboration region renders when, and only when, the contract declares it
 * and the dispatch context does not suppress it.  The declaration read is stated
 * once, in `contractRuntimeVm.ts`; this test executes the real module so the rule
 * cannot be retired by rearranging tokens: a read that cannot refuse a contract
 * that declares no region, or that accepts a surface of any content kind, changes
 * at least one expectation below.
 *
 * The tables run twice: once under node, and once with browser globals installed.
 * A rule that is live under node and inert in the browser is a different rule, and
 * the second pass is what makes that visible here instead of in the product.
 */
import assert from 'node:assert/strict';
import type { ContractV2FormStructureSurface } from '../src/app/contracts/v2/types';
import {
  COLLABORATION_SURFACE_KINDS,
  declaredCollaborationSurface,
  isCollaborationSurfaceKind,
} from '../src/pages/contractForm/contractRuntimeVm';

const declaredKinds = COLLABORATION_SURFACE_KINDS as readonly string[];

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

/** A declared surface.  `contentKind` is deliberately loose so the table can spell
 *  a wrong kind; the authority is the only thing that may interpret it. */
const surface = (contentKind: unknown, title = ''): ContractV2FormStructureSurface => ({
  surface: `surface-${title}`,
  title,
  role: 'activity',
  contentKind: contentKind as ContractV2FormStructureSurface['contentKind'],
  sourceIdentity: `source-${title}`,
});

const first = surface('collaboration-panel', 'first');
const second = surface('collaboration-panel', 'second');
const auditTimeline = surface('audit-timeline', 'audit');

type Surfaces = Parameters<typeof declaredCollaborationSurface>[0];
const asSurfaces = (value: unknown): Surfaces => value as Surfaces;

/**
 * The declaration read: `undefined` (the contract cannot declare regions at all)
 * and `[]` (it declares none) both yield no region; anything that is not a list is
 * not a declaration; only a `collaboration-panel` surface is a region, matched
 * exactly; and the first declared one wins - the read returns the declared object
 * itself, not a copy or a re-derived shape.
 */
const declarationCases: Array<[unknown, unknown]> = [
  [undefined, null],
  [null, null],
  [[], null],
  ['collaboration-panel', null],
  [42, null],
  [{}, null],
  [[auditTimeline], null],
  [[surface('CHATTER')], null],
  [[surface(undefined)], null],
  [[surface('')], null],
  [[first], first],
  [[auditTimeline, first], first],
  [[first, second], first],
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
  // is a failure rather than a pass: the predicate is typed `boolean`, and a
  // weakened return contract must not survive the proof.
  for (const [kind, expected] of kindCases) {
    assert.strictEqual(
      isCollaborationSurfaceKind(kind),
      expected,
      `kind ${JSON.stringify(kind) ?? 'undefined'}${where}`,
    );
  }

  // 3. Declaration read truth table.  `deepStrictEqual` because the returned value
  // is the declared surface itself: a copy with the same fields is a different
  // authority than the declaration.
  for (const [surfaces, expected] of declarationCases) {
    assert.deepStrictEqual(
      declaredCollaborationSurface(asSurfaces(surfaces)),
      expected,
      `surfaces ${JSON.stringify(surfaces) ?? 'undefined'}${where}`,
    );
  }

  // 4. The declaration is the only input, and the refusal is load-bearing: a
  // contract that cannot declare regions yields no region even though its runtime
  // data or capabilities might suggest one.
  assert.strictEqual(
    declaredCollaborationSurface(asSurfaces([auditTimeline, first])),
    first,
    `an audit-only prefix must not shadow the declared collaboration region${where}`,
  );
  assert.strictEqual(
    declaredCollaborationSurface(asSurfaces([first, second])),
    first,
    `the first declared collaboration region is the one published${where}`,
  );
  assert.strictEqual(
    declaredCollaborationSurface(asSurfaces('collaboration-panel')),
    null,
    `a content kind is not a declaration list${where}`,
  );
}

runTables('node');

// 5. The same tables with the browser globals present, so a rule that is gated on
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

const totalCases = (kindCases.length + declarationCases.length + 3) * 2;
console.log(`[contract_form_collaboration_authority] PASS cases=${totalCases}`);
