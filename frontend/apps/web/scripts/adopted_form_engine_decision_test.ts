/**
 * Executable proof for FE-TPL-02: a real official form engine decides whether a
 * save happens.
 *
 * The chain under test is the shipped one:
 *
 *   buildContractFormRules -> real TDesign Form/FormItem -> validate()
 *     -> failedAdoptedFieldNames -> the adopted-section registry
 *     -> the save gate -> collectRequiredFieldValidation (engine coverage excluded)
 *
 * The engine is not a stub: the installed `tdesign-vue-next` build is mounted
 * through Vue's own renderer, the same harness `global_component_capability_test`
 * already uses. Only the write itself is a counter, and the file does not claim
 * a database write happened.
 *
 * What this proves that the browser journey cannot: the failure that stops the
 * save comes from the official engine's own return value, not from a source
 * ordering coincidence.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRenderer, defineComponent, h, nextTick, ref } from 'vue';

import {
  buildContractFormRules,
  failedAdoptedFieldNames,
} from '../src/components/template/contractFormValidationRules';
import { TDesignForm, TDesignFormItem } from '../src/components/design-system/tdesignPrimitiveBridge';
import { createStandardFormValidationRegistry } from '../src/pages/contractForm/standardFormCompositionRuntime';
import { collectRequiredFieldValidation } from '../src/pages/contractForm/saveRecordHelpers';
import type { FormSectionFieldSchema } from '../src/components/template/formSection.types';
import type { LayoutNode } from '../src/pages/contractForm/types';

let cases = 0;
const check = (actual: unknown, expected: unknown, label: string) => {
  assert.equal(actual, expected, label);
  cases += 1;
};
const checkDeep = (actual: unknown, expected: unknown, label: string) => {
  assert.deepEqual(actual, expected, label);
  cases += 1;
};

const locateSource = (relative: string) => {
  let dir = process.cwd();
  for (let depth = 0; depth < 4; depth += 1) {
    const candidate = path.join(dir, relative);
    if (fs.existsSync(candidate)) return candidate;
    dir = path.dirname(dir);
  }
  return '';
};
const readSource = (relative: string) => fs.readFileSync(locateSource(relative), 'utf8');

// ---------------------------------------------------------------------------
// Vue renderer harness: real components, no browser, no new test framework
// ---------------------------------------------------------------------------
type HostNode = {
  children: HostNode[];
  parent: HostNode | null;
  props: Record<string, unknown>;
  text?: string;
  type?: string;
};
const hostNode = (type?: string): HostNode => ({ children: [], parent: null, props: {}, type });
const renderer = createRenderer<HostNode, HostNode>({
  patchProp(node, key, _previous, value) {
    if (value === null || value === undefined) delete node.props[key];
    else node.props[key] = value;
  },
  insert(child, parent, anchor) {
    child.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index >= 0) parent.children.splice(index, 0, child);
    else parent.children.push(child);
  },
  remove(child) {
    if (!child.parent) return;
    const index = child.parent.children.indexOf(child);
    if (index >= 0) child.parent.children.splice(index, 1);
    child.parent = null;
  },
  createElement: (type) => hostNode(type),
  createText: (text) => ({ ...hostNode('text'), text }),
  createComment: (text) => ({ ...hostNode('comment'), text }),
  setText: (node, text) => { node.text = text; },
  setElementText: (node, text) => { node.text = text; },
  parentNode: (node) => node.parent,
  nextSibling(node) {
    if (!node.parent) return null;
    const index = node.parent.children.indexOf(node);
    return node.parent.children[index + 1] || null;
  },
  querySelector: () => null,
  setScopeId: () => {},
  cloneNode: (node) => ({ ...node, children: [...node.children], props: { ...node.props }, parent: null }),
  insertStaticContent: () => {
    const node = hostNode('static');
    return [node, node];
  },
});
(globalThis as unknown as Record<string, unknown>).document = {
  documentElement: { style: {}, setAttribute: () => {}, getAttribute: () => null },
};
(globalThis as unknown as Record<string, unknown>).window = {
  location: { href: 'http://localhost/', origin: 'http://localhost' },
};

// ---------------------------------------------------------------------------
// The shipped rule builder, on fields shaped like the contract produces
// ---------------------------------------------------------------------------
const field = (overrides: Partial<FormSectionFieldSchema>): FormSectionFieldSchema => ({
  key: String(overrides.name || 'field'),
  name: String(overrides.name || 'field'),
  label: String(overrides.label || '名称'),
  type: String(overrides.type || 'char'),
  required: false,
  readonly: false,
  ...overrides,
});

type Draft = Record<string, unknown>;

type SurfaceSpec = Partial<FormSectionFieldSchema> & { rendered?: boolean };
type SurfaceOptions = { rulesOnItems?: boolean };

/**
 * A section as the page really renders one: the page owns the field schemas and
 * replays them into the section on every change, so the rules handed to the
 * engine are rebuilt from the values currently on screen - the same reactivity
 * `FormSection.vue` gets from `props.fields`.
 *
 * `rendered: false` mirrors a position the section keeps as a fact but does not
 * mount a form item for: its rule still exists, yet the engine can only
 * evaluate positions it was actually asked to register.
 */
class AdoptedSurface {
  readonly formRef = ref<{ validate: () => Promise<unknown> } | null>(null);
  readonly fields = ref<FormSectionFieldSchema[]>([]);
  draft: Draft = {};
  private readonly specs: SurfaceSpec[];
  private readonly options: SurfaceOptions;
  private readonly renderedNames = ref<Set<string>>(new Set<string>());
  private readonly app: { unmount: () => void };

  constructor(draft: Draft, specs: SurfaceSpec[], options: SurfaceOptions = {}) {
    this.draft = draft;
    this.specs = specs;
    this.options = options;
    this.renderedNames.value = new Set(
      specs.filter((spec) => spec.rendered !== false).map((spec) => String(spec.name)),
    );
    this.fields.value = this.materialize();
    const Root = defineComponent({
      setup: () => {
        return () => h(TDesignForm as never, {
          ref: this.formRef,
          data: draft,
          rules: buildContractFormRules(this.fields.value),
          showErrorMessage: false,
        }, () => {
          const itemRules = this.options.rulesOnItems
            ? buildContractFormRules(this.fields.value)
            : {};
          return this.renderedFields().map((item) => h(
            TDesignFormItem as never,
            {
              label: item.label,
              name: item.name,
              rules: itemRules[item.name],
              showErrorMessage: false,
            },
            () => h('input'),
          ));
        });
      },
    });
    const root = hostNode('root');
    this.app = renderer.createApp(Root as never) as unknown as { unmount: () => void };
    this.app.mount(root);
  }

  private materialize(): FormSectionFieldSchema[] {
    return this.specs.map((spec) => field({
      ...spec,
      inputValue: this.draft[String(spec.name)] as string | number | boolean | null,
    }));
  }

  private renderedFields(): FormSectionFieldSchema[] {
    return this.fields.value.filter((item) => this.renderedNames.value.has(String(item.name)));
  }

  /** Mirrors the shipped `validateAdoptedSection` in FormSection.vue. */
  async validateSection(): Promise<string[]> {
    const instance = this.formRef.value;
    if (!instance) {
      if (this.ruleFieldNames().length) {
        throw new Error('adopted form section has no engine instance for its declared rules');
      }
      return [];
    }
    const rejected = failedAdoptedFieldNames(await instance.validate());
    if (rejected === null) {
      throw new Error('adopted form engine returned an unrecognised validation result');
    }
    return rejected;
  }

  /** Mirrors the shipped `adoptedRuleFieldNames` in FormSection.vue. */
  ruleFieldNames(): string[] {
    const rules = buildContractFormRules(this.fields.value);
    return this.renderedFields()
      .map((item) => String(item.name || '').trim())
      .filter((name) => Boolean(name && rules[name]));
  }

  async setDraft(updater: (draft: Draft) => void): Promise<void> {
    updater(this.draft);
    this.fields.value = this.materialize();
    await nextTick();
  }

  /** Mirrors a section conditionally rendering (or not) one of its positions. */
  async setRendered(name: string, rendered: boolean): Promise<void> {
    const next = new Set(this.renderedNames.value);
    if (rendered) next.add(name);
    else next.delete(name);
    this.renderedNames.value = next;
    await nextTick();
  }

  unmount() { this.app.unmount(); }
}

// ---------------------------------------------------------------------------
// The shipped save gate, with a counted write instead of a real one
// ---------------------------------------------------------------------------
function createSaveGate(options: {
  model: string;
  registry: ReturnType<typeof createStandardFormValidationRegistry>;
  expectedRequired: string[];
  layoutNodes: LayoutNode[];
  draft: Draft;
  isWritableFieldVisible?: (name: string) => boolean;
}) {
  let writes = 0;
  const isVisible = options.isWritableFieldVisible || (() => true);
  return {
    get writes() { return writes; },
    async attempt(): Promise<boolean> {
      if (!options.registry.adopted.value) {
        writes += 1;
        return true;
      }
      const outcome = await options.registry.validateAdoptedFields();
      const covered = outcome.ok ? outcome.coveredFieldNames : [];
      const coverageMissing = options.expectedRequired.length > 0 && covered.length === 0;
      if (!outcome.ok || coverageMissing) return false;
      if (outcome.fieldNames.length) return false;
      const precheck = collectRequiredFieldValidation({
        excludedFieldNames: covered,
        formData: options.draft,
        isWritableFieldVisible: isVisible,
        layoutNodes: options.layoutNodes,
        model: options.model,
        normalizeFieldValue: (_name, value) => value,
        recordId: null,
        values: options.draft,
      });
      if (precheck.messages.length) return false;
      writes += 1;
      return true;
    },
  };
}

const fieldNode = (name: string, label: string, required = true): LayoutNode => ({
  key: name,
  kind: 'field',
  name,
  label,
  readonly: false,
  required,
  descriptor: { name, string: label, required, readonly: false, ttype: 'char' } as LayoutNode['descriptor'],
});

// ---------------------------------------------------------------------------
// Part 1 — a real engine failure stops the write, a real pass allows exactly one
// ---------------------------------------------------------------------------
const draft: Draft = { name: '', amount_total: '123456' };
const surface = new AdoptedSurface(draft, [
  { name: 'name', label: '项目名称', required: true },
  { name: 'amount_total', label: '合同金额', required: true, type: 'monetary' },
]);
surface.draft = draft;

const registry = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
check(registry.adopted.value, true, 'the adopted scope is the same policy the page uses');
registry.register({ sectionId: 'section-1', ruleFieldNames: () => surface.ruleFieldNames(), validate: () => surface.validateSection() });

const layoutNodes = [fieldNode('name', '项目名称'), fieldNode('amount_total', '合同金额')];
const gate = createSaveGate({
  draft,
  expectedRequired: ['name', 'amount_total'],
  layoutNodes,
  model: 'project.project',
  registry,
});

const firstAttempt = await gate.attempt();
check(firstAttempt, false, 'an empty required position must not reach the write');
check(gate.writes, 0, 'the real engine failure performs zero writes');

const rawRejection = await surface.formRef.value!.validate() as Record<string, unknown>;
checkDeep(Object.keys(rawRejection), ['name'], 'the official engine rejects exactly the empty position');
checkDeep(
  failedAdoptedFieldNames(rawRejection),
  ['name'],
  'the shipped reader turns the engine result into the business field code',
);
checkDeep(
  failedAdoptedFieldNames(true),
  [],
  'the engine answering true means nothing failed',
);
check(
  failedAdoptedFieldNames(undefined) === null,
  true,
  'an absent engine result is not evidence of a pass',
);
check(
  failedAdoptedFieldNames(null) === null,
  true,
  'a null engine result is not evidence of a pass',
);
checkDeep(
  failedAdoptedFieldNames({}),
  [],
  'an engine answering with an empty rejection set is a real pass',
);

await surface.setDraft((current) => { current.name = 'FE-TPL-02 引擎判定'; });
const outcome = await registry.validateAdoptedFields();
check(outcome.ok, true, 'the registry reports ok once the engine can answer');
checkDeep(outcome.fieldNames, [], 'a corrected field leaves no rejected code');
checkDeep(
  outcome.coveredFieldNames,
  ['name', 'amount_total'],
  'the registry reports exactly the positions the engine evaluated',
);

const secondAttempt = await gate.attempt();
check(secondAttempt, true, 'the corrected form may be written');
check(gate.writes, 1, 'exactly one write follows one successful validation');
check(gate.writes, 1, 'a second gate call is not a second write for the same attempt');

// ---------------------------------------------------------------------------
// Part 2 — an unreadable engine result and a missing engine both fail closed
// ---------------------------------------------------------------------------
const muteSurface = new AdoptedSurface({ name: 'x' }, [{ name: 'name', label: '项目名称', required: true }]);
const muteRegistry = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
muteRegistry.register({
  sectionId: 'mute',
  ruleFieldNames: () => ['name'],
  validate: async () => {
    const rejected = failedAdoptedFieldNames(undefined);
    if (rejected === null) throw new Error('engine returned an unrecognised validation result');
    return rejected;
  },
});
const muteGate = createSaveGate({
  draft: { name: 'x' },
  expectedRequired: ['name'],
  layoutNodes: [fieldNode('name', '项目名称')],
  model: 'project.project',
  registry: muteRegistry,
});
check(await muteGate.attempt(), false, 'a section that cannot read its engine result blocks the write');
check(muteGate.writes, 0, 'an unreadable engine result performs zero writes');
muteSurface.unmount();

const throwing = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
throwing.register({
  sectionId: 'no-engine',
  ruleFieldNames: () => ['name'],
  validate: async () => {
    throw new Error('adopted form section has no engine instance for its declared rules');
  },
});
const throwingGate = createSaveGate({
  draft: { name: 'x' },
  expectedRequired: ['name'],
  layoutNodes: [fieldNode('name', '项目名称')],
  model: 'project.project',
  registry: throwing,
});
check(await throwingGate.attempt(), false, 'a section without an engine cannot allow the write');
check(throwingGate.writes, 0, 'a missing engine performs zero writes');

// ---------------------------------------------------------------------------
// Part 3 — boundaries A / B / C
// ---------------------------------------------------------------------------
const unadoptedRegistry = createStandardFormValidationRegistry(() => ({ pageType: 'specialized', reason: 'contract-view-not-classified' } as const));
unadoptedRegistry.register({ sectionId: 'x', ruleFieldNames: () => ['name'], validate: async () => ['name'] });
const unadoptedGate = createSaveGate({
  draft: { name: '' },
  expectedRequired: [],
  layoutNodes: [fieldNode('name', '名称', false)],
  model: 'payment.request',
  registry: unadoptedRegistry,
});
check(await unadoptedGate.attempt(), true, 'A: a surface outside the scope keeps its pre-existing path');
check(unadoptedGate.writes, 1, 'A: an unadopted surface is never forced through an absent gate');

const emptyContract = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
const emptyGate = createSaveGate({
  draft: {},
  expectedRequired: [],
  layoutNodes: [],
  model: 'project.project',
  registry: emptyContract,
});
check(await emptyGate.attempt(), true, 'C: a contract with no required position is a legal empty set, not a failure');
check(emptyGate.writes, 1, 'C: the legal empty set writes once');

const uncovered = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
const uncoveredGate = createSaveGate({
  draft: { name: 'ok' },
  expectedRequired: ['name'],
  layoutNodes: [fieldNode('name', '项目名称')],
  model: 'project.project',
  registry: uncovered,
});
check(await uncoveredGate.attempt(), false, 'B: an adopted surface with required positions and no registered section blocks the write');
check(uncoveredGate.writes, 0, 'B: a missing registration performs zero writes');

// ---------------------------------------------------------------------------
// Part 4 — one save, one generic authority for the covered positions
// ---------------------------------------------------------------------------
const rejectedCodes = (result: ReturnType<typeof collectRequiredFieldValidation>) => (
  Object.values(result.fieldErrors).map((error) => error.target.fieldCode)
);
const coveredNames = ['name', 'amount_total'];
const uncoveredNodes = [
  fieldNode('name', '项目名称'),
  fieldNode('amount_total', '合同金额'),
  fieldNode('location', '项目地点'),
];
const sharedPrecheck = collectRequiredFieldValidation({
  excludedFieldNames: coveredNames,
  formData: { name: '', amount_total: '', location: '' },
  isWritableFieldVisible: () => true,
  layoutNodes: uncoveredNodes,
  model: 'project.project',
  normalizeFieldValue: (_name, value) => value,
  recordId: null,
  values: { name: '', amount_total: '', location: '' },
});
checkDeep(
  rejectedCodes(sharedPrecheck),
  ['location'],
  'the page precheck still decides exactly the positions the engine did not cover',
);
check(
  Object.keys(sharedPrecheck.fieldErrors)[0],
  'location',
  'a precheck rejection keeps the shared store key, so both producers land on one error position',
);
check(
  sharedPrecheck.messages.length === 1 && sharedPrecheck.messages[0].includes('项目地点'),
  true,
  'the uncovered position keeps the shared summary message shape',
);
checkDeep(
  coveredNames.filter((name) => rejectedCodes(sharedPrecheck).includes(name)),
  [],
  'no engine-covered position is independently re-decided by the page precheck',
);

const unpacked = collectRequiredFieldValidation({
  formData: { name: '' },
  isWritableFieldVisible: () => true,
  layoutNodes: [fieldNode('name', '项目名称')],
  model: 'project.project',
  normalizeFieldValue: (_name, value) => value,
  recordId: null,
  values: { name: '' },
});
checkDeep(rejectedCodes(unpacked), ['name'], 'without an adopted engine the precheck keeps its full authority');

// ---------------------------------------------------------------------------
// Part 5 — sections aggregate: one failure stops the save, all passes write once
// ---------------------------------------------------------------------------
const aggregateDraft: Draft = { name: '', amount_total: '100', note: '' };
const nameSection = new AdoptedSurface(aggregateDraft, [{ name: 'name', label: '项目名称', required: true }]);
const noteSection = new AdoptedSurface(aggregateDraft, [{ name: 'note', label: '备注', required: true, type: 'text' }]);
const aggregateRegistry = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
aggregateRegistry.register({
  sectionId: 'name-section',
  ruleFieldNames: () => nameSection.ruleFieldNames(),
  validate: () => nameSection.validateSection(),
});
aggregateRegistry.register({
  sectionId: 'note-section',
  ruleFieldNames: () => noteSection.ruleFieldNames(),
  validate: () => noteSection.validateSection(),
});
const aggregateGate = createSaveGate({
  draft: aggregateDraft,
  expectedRequired: ['name', 'note'],
  layoutNodes: [fieldNode('name', '项目名称'), fieldNode('note', '备注')],
  model: 'project.project',
  registry: aggregateRegistry,
});
check(await aggregateGate.attempt(), false, 'one failing section stops the whole save');
check(aggregateGate.writes, 0, 'a sibling section reporting a pass cannot rescue the write');
const aggregateOutcome = await aggregateRegistry.validateAdoptedFields();
checkDeep(
  aggregateOutcome.fieldNames,
  ['name', 'note'],
  'every failing applicable section reports together instead of the save discovering them one at a time',
);

await nameSection.setDraft((current) => { current.name = '已填写'; });
check(await aggregateGate.attempt(), false, 'correcting one section does not save while a sibling still fails');
check(aggregateGate.writes, 0, 'a partially corrected form still performs zero writes');

await noteSection.setDraft((current) => { current.note = '备注内容'; });
check(await aggregateGate.attempt(), true, 'the save proceeds once every applicable section passes');
check(aggregateGate.writes, 1, 'all-passing sections enter the save chain exactly once, not once per section');
nameSection.unmount();
noteSection.unmount();

// ---------------------------------------------------------------------------
// Part 6 — a position the section does not mount is never treated as passing
// ---------------------------------------------------------------------------
const hiddenDraft: Draft = { title: '有值', summary: '' };
const hiddenSurface = new AdoptedSurface(hiddenDraft, [
  { name: 'title', label: '标题', required: true },
  { name: 'summary', label: '摘要', required: true, type: 'text', rendered: false },
]);
checkDeep(
  hiddenSurface.ruleFieldNames(),
  ['title'],
  'a position with no form item is not reported as engine-covered',
);
const hiddenRegistry = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
hiddenRegistry.register({
  sectionId: 'hidden-section',
  ruleFieldNames: () => hiddenSurface.ruleFieldNames(),
  validate: () => hiddenSurface.validateSection(),
});
const hiddenGate = createSaveGate({
  draft: hiddenDraft,
  expectedRequired: ['title', 'summary'],
  layoutNodes: [fieldNode('title', '标题'), fieldNode('summary', '摘要')],
  model: 'project.project',
  registry: hiddenRegistry,
});
const hiddenOutcome = await hiddenRegistry.validateAdoptedFields();
checkDeep(hiddenOutcome.fieldNames, [], 'the engine answers only for the position it really evaluated');
check(await hiddenGate.attempt(), false, 'an unmounted but applicable required position is not treated as passing');
check(hiddenGate.writes, 0, 'the position the engine could not cover still blocks the write');

await hiddenSurface.setRendered('summary', true);
const shownOutcome = await hiddenRegistry.validateAdoptedFields();
checkDeep(shownOutcome.coveredFieldNames, ['title', 'summary'], 'a position that becomes visible enters the engine scope');
checkDeep(shownOutcome.fieldNames, ['summary'], 'the newly visible empty position is now rejected by the engine itself');
check(await hiddenGate.attempt(), false, 'the newly visible empty position still blocks the write');
check(hiddenGate.writes, 0, 'a scope change never turns a failing position into a passing one');

await hiddenSurface.setDraft((current) => { current.summary = '摘要正文'; });
check(await hiddenGate.attempt(), true, 'the corrected, now-covered position may be written');
check(hiddenGate.writes, 1, 'the covered position enters the save chain once');

await hiddenSurface.setDraft((current) => { current.summary = ''; });
await hiddenSurface.setRendered('summary', false);
const hiddenAgain = await hiddenRegistry.validateAdoptedFields();
checkDeep(hiddenAgain.coveredFieldNames, ['title'], 'a position that leaves the surface leaves the engine scope again');
checkDeep(hiddenAgain.fieldNames, [], 'the engine stops answering for a position it no longer renders');
check(await hiddenGate.attempt(), false, 'the emptied position returns to the precheck instead of silently passing');
check(hiddenGate.writes, 1, 'no further write follows a position that left the engine scope while empty');
hiddenSurface.unmount();

// ---------------------------------------------------------------------------
// Part 7 — one logical error, two display positions, still one rejection
// ---------------------------------------------------------------------------
const duplicateDraft: Draft = { name: '' };
const duplicateSurface = new AdoptedSurface(duplicateDraft, [
  { name: 'name', label: '项目名称', required: true },
  { name: 'name', label: '项目名称', required: true },
]);
checkDeep(
  duplicateSurface.ruleFieldNames(),
  ['name', 'name'],
  'two display positions of one business field are both handed to the engine',
);
const duplicateRegistry = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
duplicateRegistry.register({
  sectionId: 'duplicate-section',
  ruleFieldNames: () => duplicateSurface.ruleFieldNames(),
  validate: () => duplicateSurface.validateSection(),
});
const duplicateOutcome = await duplicateRegistry.validateAdoptedFields();
checkDeep(duplicateOutcome.fieldNames, ['name'], 'two display positions of one logical error produce one rejection');
checkDeep(
  duplicateOutcome.coveredFieldNames,
  ['name'],
  'the repeated position is covered once, so the precheck never double-decides it',
);
duplicateSurface.unmount();

// ---------------------------------------------------------------------------
// Part 8 — the same rule declared at two levels is still one authority
// ---------------------------------------------------------------------------
const doubleDraft: Draft = { name: '' };
const doubleSurface = new AdoptedSurface(
  doubleDraft,
  [{ name: 'name', label: '项目名称', required: true }],
  { rulesOnItems: true },
);
const doubleRegistry = createStandardFormValidationRegistry(() => ({ pageType: 'record-form', reason: 'contract-record-view' } as const));
doubleRegistry.register({
  sectionId: 'double-section',
  ruleFieldNames: () => doubleSurface.ruleFieldNames(),
  validate: () => doubleSurface.validateSection(),
});
const doubleGate = createSaveGate({
  draft: doubleDraft,
  expectedRequired: ['name'],
  layoutNodes: [fieldNode('name', '项目名称')],
  model: 'project.project',
  registry: doubleRegistry,
});
const doubleRejection = await doubleSurface.formRef.value!.validate() as Record<string, unknown>;
checkDeep(
  Object.keys(doubleRejection),
  ['name'],
  'declaring the same rule on the form and on its item still yields one rejection, not two',
);
check(
  (doubleRejection.name as unknown[]).length,
  1,
  'the position is rejected once, so the error layer cannot show two contradicting messages',
);
const doubleOutcome = await doubleRegistry.validateAdoptedFields();
checkDeep(doubleOutcome.fieldNames, ['name'], 'the duplicate declaration still yields one business code');
checkDeep(doubleOutcome.coveredFieldNames, ['name'], 'the position is covered once, never twice');
check(await doubleGate.attempt(), false, 'the doubly declared rule still blocks the write');
check(doubleGate.writes, 0, 'no write follows a doubly declared failing rule');
await doubleSurface.setDraft((current) => { current.name = '已填写'; });
check(await doubleGate.attempt(), true, 'the corrected position still saves once');
check(doubleGate.writes, 1, 'a doubly declared rule does not cause a second save');
doubleSurface.unmount();

// ---------------------------------------------------------------------------
// Part 8 — the shipped call sites are the ones under test
// ---------------------------------------------------------------------------
const sectionSource = readSource('frontend/apps/web/src/components/template/FormSection.vue');
check(sectionSource.includes('adoptedRuleFieldNames'), true, 'the section reports the positions it really hands to the engine');
check(sectionSource.includes('failedAdoptedFieldNames(await instance.validate())'), true, 'the section reads the engine result through the shipped reader');
const rulesSource = readSource('frontend/apps/web/src/components/template/contractFormValidationRules.ts');
check(rulesSource.includes('): string[] | null {'), true, 'the reader distinguishes "cannot read" from "nothing failed"');
const actionsSource = readSource('frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts');
check(actionsSource.includes('await validate()'), true, 'the save gate awaits the engine before it decides');
check(actionsSource.includes('coverageMissing'), true, 'the save gate separates a legal empty set from a missing registration');

// ---------------------------------------------------------------------------
// Part 9 - the engine keeps its own per-item error, and a record change must
// re-create the tree rather than trust that the page's error store is clean
// ---------------------------------------------------------------------------
const renderedText = (node: HostNode): string[] => [
  ...(node.text ? [node.text] : []),
  ...node.children.flatMap((child) => renderedText(child)),
];
{
  const staleMessage = '项目名称不能为空';
  const revision = ref(0);
  const nameDraft = { name: '' };
  const engineInstances: Array<{ validate: () => Promise<unknown> }> = [];
  const messageRule = [{ required: true, message: staleMessage }];
  const KeyedSurface = defineComponent({
    setup() {
      return () => h(
        TDesignForm as never,
        {
          // Exactly what the page does when the record identity changes:
          // ContractFormNativeCanvas keys the form tree by
          // nativeLayoutVisibilityRevision, which useRecordPageLifecycle bumps
          // on every record load. Nothing calls clearValidate here.
          key: `record-${revision.value}`,
          ref: (instance: unknown) => { if (instance) engineInstances.push(instance as { validate: () => Promise<unknown> }); },
          data: nameDraft,
          rules: { name: messageRule },
          showErrorMessage: true,
        },
        () => [
          h(TDesignFormItem as never, { label: '项目名称', name: 'name', rules: messageRule }, () => h('input')),
        ],
      );
    },
  });
  const keyedRoot = hostNode('root');
  const keyedApp = renderer.createApp(KeyedSurface as never) as unknown as { unmount: () => void };
  keyedApp.mount(keyedRoot);
  await nextTick();

  const engineBefore = engineInstances[engineInstances.length - 1];
  const rejection = await engineBefore.validate() as Record<string, unknown>;
  await nextTick();
  checkDeep(Object.keys(rejection), ['name'], 'G: the engine marks the empty position on its own form item');
  check(
    renderedText(keyedRoot).filter((text) => text.includes(staleMessage)).length,
    1,
    'G: the official engine renders its rejection inside the form item, not only in the page error store',
  );

  revision.value += 1;
  await nextTick();
  await nextTick();
  check(engineInstances.length, 2, 'G: a record identity change mounts a fresh adopted form tree');
  check(
    renderedText(keyedRoot).filter((text) => text.includes(staleMessage)).length,
    0,
    'G: the previous record\'s engine error cannot survive onto the new record once the tree is re-created',
  );

  const engineAfter = engineInstances[engineInstances.length - 1];
  check(engineAfter === engineBefore, false, 'G: the new record is validated by a new engine instance, not the old one');
  keyedApp.unmount();
}

// The page really does re-key the adopted form tree on every record load; the
// experiment above is only meaningful together with this shipped wiring.
const canvasSource = readSource('frontend/apps/web/src/pages/contractForm/ContractFormNativeCanvas.vue');
check(
  canvasSource.includes(':key="layoutVisibilityRevision"'),
  true,
  'G: the canvas keys the adopted form tree by the layout revision',
);
const lifecycleSource = readSource('frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts');
check(
  lifecycleSource.split('nativeLayoutVisibilityRevision.value += 1;').length - 1,
  2,
  'G: every loaded record bumps that revision, so both create and edit loads re-create the tree',
);

surface.unmount();

console.log(`[adopted_form_engine_decision_test] PASS cases=${cases} engine=real-tdesign-vue-next writes=counted`);
