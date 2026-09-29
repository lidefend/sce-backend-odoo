/** Page-type adoption and explicit detail-extension boundaries. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import {
  resolveStandardListComposition,
} from '../src/app/presentation/standardListComposition';
import {
  resolveStandardDetailComposition,
  resolveStandardDetailSection,
} from '../src/app/presentation/standardDetailComposition';
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
}
check(resolveStandardDetailComposition({ pageType: 'record-detail', reason: 'contract-readonly-record-view' }).adopted, true, 'readonly contract detail adopts');
for (const renderProfile of ['create', 'edit', '', undefined]) {
  const decision = resolveStandardPageType({ viewType: 'form', layoutType: 'form', renderProfile });
  check(resolveStandardDetailComposition(decision).reason, 'contract-view-not-classified', 'an editable form is not a readonly detail');
}
check(resolveStandardDetailComposition(resolveStandardPageType({ viewType: 'worksheet', renderProfile: 'readonly' })).adopted, false, 'dedicated workspace is not a generic detail');
const facts = { adopted: true, configurationMode: false, readonlyFacts: true, fields: [{ type: 'char', dedicatedControl: false }] };
check(resolveStandardDetailSection(facts).adopted, true, 'scalar facts use descriptions');
for (const type of ['one2many', 'many2many', 'binary', 'json', 'unknown']) {
  check(resolveStandardDetailSection({ ...facts, fields: [...facts.fields, { type, dedicatedControl: false }] }).adopted, false, 'mixed section preserves specialized control: ' + type);
}
check(resolveStandardDetailSection({ ...facts, fields: [{ type: 'char', dedicatedControl: true }] }).reason, 'dedicated-control-extension', 'custom widget cannot degrade to text');
check(resolveStandardDetailSection({ ...facts, configurationMode: true }).reason, 'configuration-editor', 'designer keeps editable field bindings');
check(resolveStandardDetailSection({ ...facts, readonlyFacts: false }).adopted, false, 'editable facts keep controls');
check(resolveStandardDetailSection({ ...facts, fields: [] }).adopted, false, 'empty section does not claim coverage');

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
check(listPageSource.includes('<ProductListSurface v-else-if="status === \'empty\'">'), true, 'empty results retain the same official composition');

const headerSource = readSource('frontend/apps/web/src/components/product-list/ProductListHeader.vue');
check(headerSource.includes('<template #suffix>'), true, 'the official query row renders a search affordance inside the search input');
check(headerSource.includes('<ScIcon name="search"'), true, 'the official query row search affordance is the search icon');
check(headerSource.includes("data-list-query-action-bar"), true, 'the query row keeps its stable runtime identity');
check(headerSource.includes('sc-product-page-toolbar'), true, 'the query row keeps its product page region identity');

// ---------------------------------------------------------------------------
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
check(formSectionSource.includes("standardDetailComposition?.adopted.value === true"), true, 'only an adopted detail decision converts the facts layout');
check(formSectionSource.includes('data-detail-facts="official-standard-detail"'), true, 'the adopted readonly facts are identifiable at runtime');
check(formSectionSource.includes(':bordered="false"'), true, 'the adopted readonly facts use the official unbordered card');
check(formSectionSource.includes(':items="displayFields"'), true, 'the adopted readonly facts are driven by the contract field facts, not sample data');
check(formSectionSource.includes('v-else :class="[\'template-form-section-grid\''), true, 'an unadopted section keeps the grid it had, so no surface renders two layouts');
check(formSectionSource.includes("from '../design-system/ScDescriptions.vue'"), true, 'the adopted readonly facts use the project primitive, not the vendor component');
check(formSectionSource.includes('readonly-relation-label'), true, 'the adopted readonly facts keep the authorized relation entry');
check(formSectionSource.includes("'sc.general.contract'"), false, 'the section must not name a business model');
check(formSectionSource.includes("'project.project'"), false, 'the section must not name a business model');

const descriptionsSource = readSource('frontend/apps/web/src/components/design-system/ScDescriptions.vue');
check(descriptionsSource.includes('semanticPrimitiveIdentity(\'ScDescriptions\')'), true, 'the descriptions primitive keeps its project identity');
check(descriptionsSource.includes('TDesignDescriptionsItem'), true, 'the descriptions primitive is the official implementation');

console.log(`[standard_collection_composition_test] PASS cases=${cases} scope=page-types`);
