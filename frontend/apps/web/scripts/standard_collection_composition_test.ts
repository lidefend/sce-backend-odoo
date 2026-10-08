/** Page-type adoption and explicit detail-extension boundaries. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import {
  resolveStandardListComposition,
} from '../src/app/presentation/standardListComposition';
import {
  resolveStandardDetailComposition,
  resolveStandardDetailFactLayout,
  resolveStandardDetailSection,
} from '../src/app/presentation/standardDetailComposition';
import {
  resolveStandardFormComposition,
} from '../src/app/presentation/standardFormComposition';
import { resolveStandardPageType } from '../src/app/presentation/standardPageType';
import {
  DECLARED_BATCH_EXECUTORS,
  resolveSelectionActions,
} from '../src/app/runtime/actionViewSelectionExportRuntime';

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

const OFFICIAL_REFERENCE = 'aeed57076217f7777158b905f353d73585bad1c4';

// ---------------------------------------------------------------------------
// Part 1 — the effective contract declares what a page is; the compositions
// follow that declaration and never a model name, a route or a caption.
checkDeep(resolveStandardPageType({ viewType: 'list', layoutType: 'table' }), { pageType: 'query-list', reason: 'contract-collection-view' }, 'a declared collection view is a query list');
checkDeep(resolveStandardPageType({ viewType: 'tree', layoutType: 'tree' }), { pageType: 'query-list', reason: 'contract-collection-view' }, 'the backend tree token is a collection view');
checkDeep(resolveStandardPageType({ viewType: 'form', layoutType: 'form' }), { pageType: 'record-form', reason: 'contract-record-view' }, 'a declared form view is a record form');
checkDeep(resolveStandardPageType({ viewType: 'form', layoutType: 'form', renderProfile: 'readonly' }), { pageType: 'record-detail', reason: 'contract-readonly-record-view' }, 'an authorization-driven readonly form is a record detail');
checkDeep(resolveStandardPageType({ viewType: 'list', layoutType: 'form' }), { pageType: 'specialized', reason: 'contract-view-conflict' }, 'disagreeing declarations are reported, not silently chosen between');
checkDeep(resolveStandardPageType({ viewType: 'form', layoutType: 'table' }), { pageType: 'specialized', reason: 'contract-view-conflict' }, 'a record view with a collection layout is a conflict, not a form');
checkDeep(resolveStandardPageType({ viewType: 'pivot' }), { pageType: 'specialized', reason: 'contract-view-not-classified' }, 'a view the contract does not classify is not upgraded by resemblance');
checkDeep(resolveStandardPageType({}), { pageType: 'specialized', reason: 'contract-view-not-classified' }, 'an undeclared view is not guessed into a standard composition');

// ---------------------------------------------------------------------------
// Part 2 — existing page responsibilities select the shared composition.
check(resolveStandardListComposition({ pageType: 'query-list', reason: 'contract-collection-view' }).adopted, true, 'all ordinary query lists adopt without a model whitelist');
for (const decision of [
  { pageType: 'specialized', reason: 'contract-view-not-classified' },
  { pageType: 'record-form', reason: 'contract-record-view' },
  { pageType: 'record-detail', reason: 'contract-readonly-record-view' },
  undefined,
] as Array<{ pageType: 'specialized' | 'record-form' | 'record-detail'; reason: string } | undefined>) {
  check(resolveStandardListComposition(decision as never).adopted, false, 'a surface the contract did not declare a collection stays an explicit exception');
  check(
    resolveStandardListComposition(decision as never).reason,
    decision?.reason ?? 'contract-view-not-classified',
    'a non-adopted list keeps the contract reason it was handed instead of inventing one',
  );
}
checkDeep(resolveStandardDetailComposition({ pageType: 'record-detail', reason: 'contract-readonly-record-view' }), { composition: 'official-standard-detail', adopted: true, reason: 'contract-readonly-record-view' }, 'readonly contract detail adopts');
for (const renderProfile of ['create', 'edit', '', undefined]) {
  const decision = resolveStandardPageType({ viewType: 'form', layoutType: 'form', renderProfile });
  checkDeep(resolveStandardDetailComposition(decision), { composition: 'official-standard-detail', adopted: false, reason: 'contract-record-view' }, 'an editable form is not a readonly detail and keeps the contract reason');
}
checkDeep(resolveStandardDetailComposition(resolveStandardPageType({ viewType: 'worksheet', renderProfile: 'readonly' })), { composition: 'official-standard-detail', adopted: false, reason: 'contract-view-not-classified' }, 'dedicated workspace is not a generic detail');
checkDeep(resolveStandardDetailComposition(resolveStandardPageType({ viewType: 'form', layoutType: 'table', renderProfile: 'readonly' })), { composition: 'official-standard-detail', adopted: false, reason: 'contract-view-conflict' }, 'a conflicting declaration is reported instead of adopting a detail');
checkDeep(resolveStandardDetailComposition(undefined as never), { composition: 'official-standard-detail', adopted: false, reason: 'contract-view-not-classified' }, 'a page with no contract decision reports the missing classification rather than guessing one');
checkDeep(
  resolveStandardFormComposition({ pageType: 'record-detail', reason: 'contract-readonly-record-view' }),
  { composition: 'legacy-form-section', adopted: false, reason: 'contract-readonly-record-view' },
  'the form composition keeps the real second renderer it names, so the two policies stay distinguishable, and reports the contract reason it was given',
);
checkDeep(
  resolveStandardFormComposition({ pageType: 'specialized', reason: 'contract-view-conflict' }),
  { composition: 'legacy-form-section', adopted: false, reason: 'contract-view-conflict' },
  'a conflicting declaration is reported as a conflict rather than as an unclassified page',
);
// Every composition decision reports the contract's own classification reason.
// A record page that is not a query list is a classified page, so its list
// reason must not claim the contract said nothing.
checkDeep(
  resolveStandardListComposition({ pageType: 'record-form', reason: 'contract-record-view' } as never),
  { composition: 'official-standard-list', adopted: false, reason: 'contract-record-view' },
  'a page the contract declared a record form keeps that reason when the list surface does not adopt it',
);
checkDeep(
  resolveStandardListComposition({ pageType: 'record-detail', reason: 'contract-readonly-record-view' } as never),
  { composition: 'official-standard-list', adopted: false, reason: 'contract-readonly-record-view' },
  'a readonly record keeps its reason when the list surface does not adopt it',
);
checkDeep(
  resolveStandardListComposition({ pageType: 'specialized', reason: 'contract-view-conflict' } as never),
  { composition: 'official-standard-list', adopted: false, reason: 'contract-view-conflict' },
  'a conflicting declaration stays reported as a conflict for the list surface too',
);
const facts = { adopted: true, configurationMode: false, readonlyFacts: true, fields: [{ type: 'char', dedicatedControl: false }] };
const detailPolicySource = readSource('frontend/apps/web/src/app/presentation/standardDetailComposition.ts');
check(/'legacy-detail-surface'/.test(detailPolicySource), false, 'the detail policy must not name a renderer the project does not ship, because adoption is the only thing the answer carries');
check(/\|\s*'/.test(detailPolicySource.split('StandardDetailCompositionId =')[1]?.split(';')[0] ?? ''), false, 'the detail composition id stays single-valued while there is one detail surface');
check(resolveStandardDetailSection(facts).adopted, true, 'scalar facts use descriptions');
for (const type of ['one2many', 'many2many', 'binary', 'json', 'unknown']) {
  check(resolveStandardDetailSection({ ...facts, fields: [...facts.fields, { type, dedicatedControl: false }] }).adopted, false, 'mixed section preserves specialized control: ' + type);
}
check(resolveStandardDetailSection({ ...facts, fields: [{ type: 'char', dedicatedControl: true }] }).reason, 'dedicated-control-extension', 'custom widget cannot degrade to text');
check(resolveStandardDetailSection({ ...facts, configurationMode: true }).reason, 'configuration-editor', 'designer keeps editable field bindings');
check(resolveStandardDetailSection({ ...facts, readonlyFacts: false }).adopted, false, 'editable facts keep controls');
check(resolveStandardDetailSection({ ...facts, fields: [] }).adopted, false, 'empty section does not claim coverage');

// The page-level half: a readonly record the contract declared, and an
// editable record form, must reach opposite answers from the same section.
const readonlyRecordDecision = resolveStandardDetailComposition(
  resolveStandardPageType({ viewType: 'form', layoutType: 'form', renderProfile: 'readonly' }),
);
const editableRecordDecision = resolveStandardDetailComposition(
  resolveStandardPageType({ viewType: 'form', layoutType: 'form', renderProfile: 'edit' }),
);
const readonlySection = { configurationMode: false, readonlyFacts: true, fields: [{ type: 'char', dedicatedControl: false }] };
check(readonlyRecordDecision.adopted, true, 'the contract-declared readonly record adopts the official detail composition');
check(editableRecordDecision.adopted, false, 'an editable record form does not adopt the readonly detail composition');
check(
  resolveStandardDetailFactLayout(readonlyRecordDecision, readonlySection).adopted,
  true,
  'a readonly record the contract declares renders its scalar section as official detail facts, without also demanding the form composition the same contract cannot declare at the same time',
);
check(
  resolveStandardDetailFactLayout(editableRecordDecision, readonlySection).reason,
  'outside-standard-detail',
  'an editable record form keeps its controls instead of converting them to facts',
);
check(
  resolveStandardDetailFactLayout(resolveStandardDetailComposition(resolveStandardPageType({ viewType: 'list', layoutType: 'table' })), readonlySection).reason,
  'outside-standard-detail',
  'a collection page is not a readonly record, so its sections never claim the detail layout',
);
check(
  resolveStandardDetailFactLayout(null, readonlySection).reason,
  'outside-standard-detail',
  'a section outside a page that provides the decision keeps the composition it had',
);
check(
  resolveStandardDetailFactLayout(readonlyRecordDecision, { ...readonlySection, readonlyFacts: false }).reason,
  'editable-section',
  'the page adoption alone does not convert an editable section into facts',
);
check(
  resolveStandardDetailFactLayout(readonlyRecordDecision, { ...readonlySection, configurationMode: true }).reason,
  'configuration-editor',
  'the designer keeps editable field bindings even on a readonly record',
);
check(
  resolveStandardDetailFactLayout(readonlyRecordDecision, { ...readonlySection, fields: [{ type: 'one2many', dedicatedControl: false }] }).reason,
  'relation-collection-extension',
  'a relation collection on a readonly record stays a dedicated control rather than being folded into facts',
);

// ---------------------------------------------------------------------------
// Part 3 — the policies stay pure presentation scope
// ---------------------------------------------------------------------------
for (const relative of [
  'frontend/apps/web/src/app/presentation/standardListComposition.ts',
  'frontend/apps/web/src/app/presentation/standardDetailComposition.ts',
]) {
  const source = readSource(relative);
  const name = path.basename(relative);
  check(source.includes(`from 'vue'`), false, `${name} must not import Vue`);
  check(source.includes('document.'), false, `${name} must not touch the DOM`);
  check(source.includes('window.'), false, `${name} must not touch the window`);
  check(/from\s+['"]tdesign-vue-next['"]/.test(source), false, `${name} must not import the component library`);
  check(source.includes(OFFICIAL_REFERENCE), true, `${name} records the official reference snapshot`);
}

const pageTypeSource = readSource('frontend/apps/web/src/app/presentation/standardPageType.ts');
check(pageTypeSource.includes(`from 'vue'`), false, 'standardPageType must not import Vue');
check(pageTypeSource.includes('document.'), false, 'standardPageType must not touch the DOM');
check(pageTypeSource.includes('window.'), false, 'standardPageType must not touch the window');
check(/from\s+['"]tdesign-vue-next['"]/.test(pageTypeSource), false, 'standardPageType must not import the component library');
check(pageTypeSource.includes('pageInfo'), true, 'standardPageType reads the contract declared page info');

// ---------------------------------------------------------------------------
// Part 4 — the shipped surfaces really render the adopted composition
// ---------------------------------------------------------------------------
const listPageSource = readSource('frontend/apps/web/src/pages/ListPage.vue');
check(listPageSource.includes('resolveStandardListComposition('), true, 'the list page resolves adoption from the contract-derived page type');
check(listPageSource.includes('props.contractPageType'), true, 'the list page takes the contract-derived page type as an input instead of guessing one');
check(listPageSource.includes('standard-query-list'), false, 'the list page must not name a page-type token of its own');
check(listPageSource.includes(':data-list-composition="listComposition.composition"'), true, 'the list page publishes the composition it used');
check(listPageSource.includes(':data-list-composition-reason="listComposition.reason"'), true, 'the list page publishes why it chose it');
check(listPageSource.includes('<ProductListSurface>'), true, 'the list page routes the surface through the official container');
check(listPageSource.includes("'project.project'"), false, 'the list page must not name a business model');
check(listPageSource.includes("'sc.general.contract'"), false, 'the list page must not name a business model');

const surfaceSource = readSource('frontend/apps/web/src/components/product-list/ProductListSurface.vue');
check(surfaceSource.includes('data-list-card-container="official"'), true, 'the official list card container is identifiable at runtime');
check(surfaceSource.includes(':bordered="false"'), true, 'the official list card is unbordered, as the reference page declares');
check(surfaceSource.includes("appearance=\"table\""), true, 'the official list card uses the table surface appearance');
check(surfaceSource.includes(':deep(.t-'), false, 'the official list card adds no selector of its own onto the vendor internals');
check(surfaceSource.includes('appearance="table"'), true, 'the zero body padding comes from the primitive appearance, not a vendor override');
check(surfaceSource.includes('<slot v-else />'), false, 'standard list no longer has a legacy pass-through path');
// The empty branch is declared by the page status and must render through the
// same official container as the populated branch: an empty result set is a
// state of the query list, not a different page type.
const emptyBranchStart = listPageSource.indexOf("status === 'empty'");
const populatedBranchStart = listPageSource.indexOf('<template v-else>');
const emptyBranch = emptyBranchStart >= 0 && populatedBranchStart > emptyBranchStart
  ? listPageSource.slice(emptyBranchStart, populatedBranchStart)
  : '';
check(emptyBranch.includes('<ProductListSurface>'), true, 'empty results retain the same official composition');
check((listPageSource.match(/<ProductListSurface>/g) || []).length, 2, 'empty and populated results both route through the official list container');

const headerSource = readSource('frontend/apps/web/src/components/product-list/ProductListHeader.vue');
check(headerSource.includes('<template #suffix>'), true, 'the official query row renders a search affordance inside the search input');
check(headerSource.includes('<ScIcon name="search"'), true, 'the official query row search affordance is the search icon');
check(headerSource.includes("data-list-query-action-bar"), true, 'the query row keeps its stable runtime identity');
check(headerSource.includes('sc-product-page-toolbar'), true, 'the query row keeps its product page region identity');

// ---------------------------------------------------------------------------
const actionViewSource = readSource('frontend/apps/web/src/views/ActionView.vue');
const surfaceHeaderSource = readSource('frontend/apps/web/src/components/product-list/ListSurfaceHeader.vue');
check(listPageSource.includes('<ScPage'), false, 'embedded list cannot create a second canvas');
check(actionViewSource.includes('<ScPage'), true, 'routed ActionView owns the single canvas');
check(actionViewSource.includes('padding-inline: 0;'), false, 'no nested-gutter compensation remains');
check((listPageSource.match(/#leading/g) || []).length, 2, 'empty and populated headers both forward operations');
check(surfaceHeaderSource.includes('v-if="!contextual"'), false, 'selection never replaces query or column settings');
check(surfaceHeaderSource.includes('<slot name="contextual" />'), true, 'batch actions retain their slot');
check(actionViewSource.includes('v-if="!standardListOperationsInCard" #actions'), true, 'standard list operations have one active location');
check(surfaceSource.includes('padding: 32px'), true, 'official list card outer padding is explicit');
const densitySource = readSource('frontend/apps/web/src/styles/tokens/pattern.css');
check(densitySource.includes("[data-list-card-container='official']"), true, 'density belongs to the actual list surface');
check(densitySource.includes('.page.sc-product-workspace-stack {'), false, 'workspace does not inherit list density');
const patternsSource = readSource('frontend/apps/web/src/styles/product-patterns.css');
check(patternsSource.includes('.sc-product-workspace-stack :is(table, .data-table, .list-table)'), false, 'workspace tables do not inherit list header weight');

// Part 5 — the detail decision is provided once per page and read by sections
// ---------------------------------------------------------------------------
const detailRuntimePath = 'frontend/apps/web/src/pages/contractForm/standardDetailCompositionRuntime.ts';
const detailRuntimeSource = readSource(detailRuntimePath);
check(detailRuntimeSource.includes('resolveStandardDetailComposition('), true, 'the runtime resolves the one pure detail policy from the contract-derived page type');
check(detailRuntimeSource.includes('contractPageType: () => StandardPageTypeDecision'), true, 'the runtime takes the contract-derived page type as an input');
check(detailRuntimeSource.includes('provide(StandardDetailCompositionKey, runtime)'), true, 'the page provides one decision for the sections to read');
check(detailRuntimeSource.includes('inject(StandardDetailCompositionKey, null)'), true, 'a surface with no provider keeps its previous composition');
check(/from\s+['"]vue['"]/.test(detailRuntimeSource), true, 'the runtime is a Vue-layer module');
check(/from\s+['"]tdesign-vue-next['"]/.test(detailRuntimeSource), false, 'the runtime must not import the component library');

const contractPageSource = readSource('frontend/apps/web/src/pages/ContractFormPage.vue');
check(contractPageSource.includes('createStandardDetailCompositionRuntime(() => contractPageType.value)'), true, 'the record page resolves detail adoption from its own contract-derived page type');
check(contractPageSource.includes(':data-detail-composition="standardDetailComposition.decision.value.composition"'), true, 'the record page publishes the detail composition it used');
check(contractPageSource.includes(':data-detail-composition-reason="standardDetailComposition.decision.value.reason"'), true, 'the record page publishes why it chose it');

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Part 6a — the contract declares which batch actions exist and how each one
// executes.  The client maps a declared intent onto an executor it can run; it
// never decides the set of batch actions and never hides a declared one.
// ---------------------------------------------------------------------------
const batchText = (_key: string, fallback: string) => fallback;
const batchDeclaration = (over: Record<string, unknown> = {}) => ({
  intents: {} as Record<string, string>,
  deleteMode: 'none',
  activeField: '',
  ...over,
});
checkDeep(
  resolveSelectionActions(
    ['export', 'archive', 'activate', 'delete'],
    batchDeclaration({
      intents: { export: 'api.data', archive: 'api.data.batch', activate: 'api.data.batch', delete: 'api.data.unlink' },
      deleteMode: 'unlink',
      activeField: 'active',
    }),
    batchText,
  ).map((row) => [row.key, row.enabled]),
  [['batch:export', true], ['batch:archive', true], ['batch:activate', true], ['batch:delete', true]],
  'every action the contract declares is offered and executes through its declared intent',
);
checkDeep(
  resolveSelectionActions(
    ['export', 'delete'],
    batchDeclaration({ intents: { export: 'api.data', delete: 'api.data.unlink' }, deleteMode: 'none' }),
    batchText,
  ).map((row) => [row.key, row.enabled, row.hint !== '']),
  [['batch:export', true, false], ['batch:delete', false, true]],
  'a declared action the declared policy forbids stays visible but disabled',
);
checkDeep(
  resolveSelectionActions(
    ['export', 'purge'],
    batchDeclaration({ intents: { export: 'api.data' } }),
    batchText,
  ).map((row) => [row.key, row.enabled, row.hint !== '']),
  [['batch:export', true, false], ['batch:purge', false, true]],
  'a declared action the contract gives no execution intent is reported unresolved, not silently dropped',
);
check(
  resolveSelectionActions(['export'], batchDeclaration(), batchText)[0].enabled,
  false,
  'an undeclared execution never becomes enabled by a familiar action name',
);
check(
  Object.entries(DECLARED_BATCH_EXECUTORS).every(([intent, executor]) => intent.startsWith('api.') && Boolean(executor)),
  true,
  'the client capability table is keyed by declared intent, so a new business action reaches the client without a client change',
);

// Part 6 — the shipped readonly section really renders the adopted composition
// ---------------------------------------------------------------------------
const formSectionSource = readSource('frontend/apps/web/src/components/template/FormSection.vue');
check(formSectionSource.includes("useOptionalStandardDetailComposition()"), true, 'the readonly section reads the page-provided detail decision');
check(formSectionSource.includes('resolveStandardDetailFactLayout('), true, 'the facts layout is decided by the shared detail-fact resolver, not by an inline component condition');
check(
  formSectionSource.includes('standardDetailComposition?.adopted.value === true && adoptedComposition.value'),
  false,
  'the facts layout is never gated on the form composition being adopted: a contract classifies a page as a record form or a record detail, so conjoining the two leaves the layout unreachable on every page',
);
check(
  /resolveStandardDetailFactLayout\(\s*standardDetailComposition\?\.decision\.value/
    .test(formSectionSource),
  true,
  'the section feeds the resolver the page-level detail decision it was provided, not a locally re-derived page type',
);
check(formSectionSource.includes('data-detail-facts="official-standard-detail"'), true, 'the adopted readonly facts are identifiable at runtime');
check(formSectionSource.includes(':bordered="false"'), true, 'the adopted readonly facts use the official unbordered card');
check(formSectionSource.includes(':items="segment.fields"'), true, 'the adopted readonly facts are driven by the contract field facts, not sample data');
check(formSectionSource.includes('v-else :class="[\'template-form-section-grid\''), true, 'an unadopted section keeps the grid it had, so no surface renders two layouts');
check(formSectionSource.includes("from '../design-system/ScDescriptions.vue'"), true, 'the adopted readonly facts use the project primitive, not the vendor component');
check(formSectionSource.includes('readonly-relation-label'), true, 'the adopted readonly facts keep the authorized relation entry');
check(formSectionSource.includes("'sc.general.contract'"), false, 'the section must not name a business model');
check(formSectionSource.includes("'project.project'"), false, 'the section must not name a business model');

const descriptionsSource = readSource('frontend/apps/web/src/components/design-system/ScDescriptions.vue');
check(descriptionsSource.includes('semanticPrimitiveIdentity(\'ScDescriptions\')'), true, 'the descriptions primitive keeps its project identity');
check(descriptionsSource.includes('TDesignDescriptionsItem'), true, 'the descriptions primitive is the official implementation');

console.log(`[standard_collection_composition_test] PASS cases=${cases} scope=page-types`);
