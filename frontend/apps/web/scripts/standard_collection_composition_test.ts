/**
 * Executable proof for FE-TPL-03: the official list and readonly detail
 * compositions are adopted by an explicit, model-scoped presentation policy,
 * and the shipped surfaces really render them.
 *
 * Two things are proved that a screenshot cannot:
 *
 *   1. the adoption decision is an explicit pilot list, so a business model
 *      joins by being listed there and by carrying a contract the composition
 *      already understands — the call sites never name a model;
 *   2. outside the adopted scope the surfaces keep their previous composition,
 *      so a list or a record never renders through two competing containers.
 *
 * The policy modules are pure: no Vue, no DOM, no TDesign. The structural
 * checks read the shipped sources, so the test fails if the wiring is reverted
 * while the policy still reports "adopted".
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import {
  STANDARD_LIST_COMPOSITION_PILOT_MODELS,
  resolveStandardListComposition,
} from '../src/app/presentation/standardListComposition';
import {
  STANDARD_DETAIL_COMPOSITION_PILOT_MODELS,
  resolveStandardDetailComposition,
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
// Part 1 — the list adoption policy is an explicit, model-scoped pilot list
// ---------------------------------------------------------------------------
checkDeep(
  resolveStandardListComposition({ model: 'project.project' }),
  { composition: 'official-standard-list', adopted: true, reason: 'pilot-model-adopted' },
  'an adopted list resolves to the official composition',
);
checkDeep(
  resolveStandardListComposition({ model: 'sc.general.contract' }),
  { composition: 'official-standard-list', adopted: true, reason: 'pilot-model-adopted' },
  'a second business model reuses the same composition, not a second implementation',
);
checkDeep(
  resolveStandardListComposition({ model: 'payment.request' }),
  { composition: 'official-standard-list', adopted: true, reason: 'pilot-model-adopted' },
  'the payment-request list joins the same composition, so one business flow does not run two list implementations',
);
checkDeep(
  resolveStandardListComposition({ model: 'res.partner' }),
  { composition: 'legacy-list-surface', adopted: false, reason: 'outside-pilot-scope' },
  'an unverified list keeps its previous composition',
);
checkDeep(
  resolveStandardListComposition({ model: '  sc.general.contract  ' }),
  { composition: 'official-standard-list', adopted: true, reason: 'pilot-model-adopted' },
  'the decision is insensitive to surrounding whitespace',
);
checkDeep(
  resolveStandardListComposition({ model: '' }),
  { composition: 'legacy-list-surface', adopted: false, reason: 'outside-pilot-scope' },
  'an unknown model never adopts by accident',
);
checkDeep(
  resolveStandardListComposition({}),
  { composition: 'legacy-list-surface', adopted: false, reason: 'outside-pilot-scope' },
  'an absent model never adopts by accident',
);
checkDeep(
  resolveStandardListComposition({ model: undefined }),
  { composition: 'legacy-list-surface', adopted: false, reason: 'outside-pilot-scope' },
  'a missing model never adopts by accident',
);
checkDeep(
  resolveStandardListComposition({ model: 'PROJECT.PROJECT' }),
  { composition: 'legacy-list-surface', adopted: false, reason: 'outside-pilot-scope' },
  'adoption is an exact model identity, not a case-folded label guess',
);
check(Object.isFrozen(STANDARD_LIST_COMPOSITION_PILOT_MODELS), true, 'the pilot list is immutable');
checkDeep(
  [...STANDARD_LIST_COMPOSITION_PILOT_MODELS],
  ['project.project', 'sc.general.contract', 'payment.request'],
  'the pilot list stays the explicit verified scope',
);

// ---------------------------------------------------------------------------
// Part 2 — only the readonly profile adopts the official detail composition
// ---------------------------------------------------------------------------
checkDeep(
  resolveStandardDetailComposition({ model: 'sc.general.contract', renderProfile: 'readonly' }),
  { composition: 'official-standard-detail', adopted: true, reason: 'pilot-model-adopted' },
  'an adopted readonly record resolves to the official detail composition',
);
checkDeep(
  resolveStandardDetailComposition({ model: 'sc.general.contract', renderProfile: 'edit' }),
  { composition: 'legacy-detail-surface', adopted: false, reason: 'not-a-readonly-profile' },
  'an editable surface keeps its previous composition',
);
checkDeep(
  resolveStandardDetailComposition({ model: 'sc.general.contract', renderProfile: 'create' }),
  { composition: 'legacy-detail-surface', adopted: false, reason: 'not-a-readonly-profile' },
  'the official detail page has no create state, so create keeps its previous composition',
);
checkDeep(
  resolveStandardDetailComposition({ model: 'sc.general.contract' }),
  { composition: 'legacy-detail-surface', adopted: false, reason: 'not-a-readonly-profile' },
  'an undeclared render profile is not treated as readonly',
);
checkDeep(
  resolveStandardDetailComposition({ model: 'project.project', renderProfile: 'readonly' }),
  { composition: 'legacy-detail-surface', adopted: false, reason: 'outside-pilot-scope' },
  'a readonly record outside the pilot scope keeps its previous composition',
);
checkDeep(
  resolveStandardDetailComposition({ model: '', renderProfile: 'readonly' }),
  { composition: 'legacy-detail-surface', adopted: false, reason: 'outside-pilot-scope' },
  'an unknown readonly record never adopts by accident',
);
check(Object.isFrozen(STANDARD_DETAIL_COMPOSITION_PILOT_MODELS), true, 'the detail pilot list is immutable');
checkDeep(
  [...STANDARD_DETAIL_COMPOSITION_PILOT_MODELS],
  ['sc.general.contract'],
  'the detail pilot list stays the explicit verified scope',
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

// ---------------------------------------------------------------------------
// Part 4 — the shipped surfaces really render the adopted composition
// ---------------------------------------------------------------------------
const listPageSource = readSource('frontend/apps/web/src/pages/ListPage.vue');
check(listPageSource.includes('resolveStandardListComposition({ model: props.model })'), true, 'the list page resolves adoption from the contract model, not a renderer choice');
check(listPageSource.includes(':data-list-composition="listComposition.composition"'), true, 'the list page publishes the composition it used');
check(listPageSource.includes(':data-list-composition-reason="listComposition.reason"'), true, 'the list page publishes why it chose it');
check(listPageSource.includes('<ProductListSurface :adopted="listComposition.adopted">'), true, 'the list page routes the surface through the official container');
check(listPageSource.includes("'project.project'"), false, 'the list page must not name a business model');
check(listPageSource.includes("'sc.general.contract'"), false, 'the list page must not name a business model');

const surfaceSource = readSource('frontend/apps/web/src/components/product-list/ProductListSurface.vue');
check(surfaceSource.includes('data-list-card-container="official"'), true, 'the official list card container is identifiable at runtime');
check(surfaceSource.includes(':bordered="false"'), true, 'the official list card is unbordered, as the reference page declares');
check(surfaceSource.includes("appearance=\"table\""), true, 'the official list card uses the table surface appearance');
check(surfaceSource.includes(':deep(.t-'), false, 'the official list card adds no selector of its own onto the vendor internals');
check(surfaceSource.includes('appearance="table"'), true, 'the zero body padding comes from the primitive appearance, not a vendor override');
check(surfaceSource.includes('<slot v-else />'), true, 'outside the adopted scope the surface is passed through unchanged');

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
check(contractPageSource.includes("createStandardDetailCompositionRuntime(() => model.value, () => renderProfile.value)"), true, 'the record page resolves detail adoption from its own model and render profile');
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

console.log(`[standard_collection_composition_test] PASS cases=${cases} lists=${STANDARD_LIST_COMPOSITION_PILOT_MODELS.length} details=${STANDARD_DETAIL_COMPOSITION_PILOT_MODELS.length}`);
