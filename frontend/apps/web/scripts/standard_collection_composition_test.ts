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
// Part 1/2 — existing page responsibilities select the shared composition.
check(resolveStandardListComposition({ pageType: 'standard-query-list' }).adopted, true, 'all ordinary query lists adopt without a model whitelist');
for (const pageType of ['', 'worksheet', 'hierarchy', 'kanban', undefined]) {
  check(resolveStandardListComposition({ pageType }).adopted, false, 'specialized lists remain explicit exceptions');
}
check(resolveStandardDetailComposition({ pageType: 'contract-record-detail', renderProfile: 'readonly' }).adopted, true, 'readonly contract detail adopts');
for (const renderProfile of ['create', 'edit', '', undefined]) {
  check(resolveStandardDetailComposition({ pageType: 'contract-record-detail', renderProfile }).reason, 'not-a-readonly-profile', 'detail does not confer readonly state');
}
check(resolveStandardDetailComposition({ pageType: 'worksheet', renderProfile: 'readonly' }).adopted, false, 'dedicated workspace is not a generic detail');
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

// ---------------------------------------------------------------------------
// Part 4 — the shipped surfaces really render the adopted composition
// ---------------------------------------------------------------------------
const listPageSource = readSource('frontend/apps/web/src/pages/ListPage.vue');
check(listPageSource.includes("resolveStandardListComposition({ pageType: 'standard-query-list' })"), true, 'the list page resolves adoption from the contract model, not a renderer choice');
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
check(detailRuntimeSource.includes('resolveStandardDetailComposition({'), true, 'the runtime resolves the one pure detail policy');
check(detailRuntimeSource.includes('provide(StandardDetailCompositionKey, runtime)'), true, 'the page provides one decision for the sections to read');
check(detailRuntimeSource.includes('inject(StandardDetailCompositionKey, null)'), true, 'a surface with no provider keeps its previous composition');
check(/from\s+['"]vue['"]/.test(detailRuntimeSource), true, 'the runtime is a Vue-layer module');
check(/from\s+['"]tdesign-vue-next['"]/.test(detailRuntimeSource), false, 'the runtime must not import the component library');

const contractPageSource = readSource('frontend/apps/web/src/pages/ContractFormPage.vue');
check(contractPageSource.includes("createStandardDetailCompositionRuntime(() => 'contract-record-detail', () => renderProfile.value)"), true, 'the record page resolves detail adoption from its own model and render profile');
check(contractPageSource.includes(':data-detail-composition="standardDetailComposition.decision.value.composition"'), true, 'the record page publishes the detail composition it used');
check(contractPageSource.includes(':data-detail-composition-reason="standardDetailComposition.decision.value.reason"'), true, 'the record page publishes why it chose it');

// ---------------------------------------------------------------------------
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
