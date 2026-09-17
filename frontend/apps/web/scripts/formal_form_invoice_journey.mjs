import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs/promises';

// Bounded U-C4 G02 observations for the rebuilt native invoice form, called by
// the governed form loop before the shared designer journey.  Four formal
// entries (785 input, 786 output application, 787 output registration, 788
// prepaid tax) share model sc.invoice.registration and view 1651; two bypass
// actions (789 input tax report, 639 invoice general ledger) must keep
// resolving the same native form.  Read-only: no record writes, no
// configuration writes; the preview/publish/rollback lifecycle stays in the
// designer journey.  Navigation-wise 789 is entry-isolated from the
// reviewing admin (CONTEXTUAL_ROUTE for finance principals only) and 639 is
// a retired navigation entry — see CONTEXTUAL_BYPASS / RETIRED_NAVIGATION.

const FORMAL_IDS = [785, 787, 786, 788];
const BYPASS_IDS = [789, 639];
const ALWAYS_SECTIONS = ['办理主信息', '项目与往来单位', '发票与税务信息', '发票金额与税额', '办理信息', '办理说明'];
const PREPAID_SECTION = '预缴税信息';
const OUTPUT_SECTION = '销项业务信息';
const RETIRED_TITLES = ['发票标题', '受票方信息', '开票方信息', '本次开票信息', '开票详情', '发票实开详情'];
const PREPAID_INVISIBLE = "source_kind != 'prepaid_tax' and direction != 'prepaid'";
const OUTPUT_INVISIBLE = "source_kind not in ['output_invoice_tax'] and direction != 'output'";
const ANCHORS = ['invoice_main', 'invoice_project', 'invoice_tax_details', 'invoice_prepaid_tax',
  'invoice_amount', 'invoice_output_business', 'invoice_handling', 'invoice_notes', 'invoice_source_trace'];
const UNCONDITIONAL_ANCHORS = ['invoice_main', 'invoice_project', 'invoice_tax_details',
  'invoice_amount', 'invoice_handling', 'invoice_notes'];

// Entry-level create-profile field surface.  Entries that bind a business
// category through default_business_category_code inherit the seeded form
// policy (sc.business.category.form_policy_json): the advanced group is
// trimmed at the create profile (visible_profiles lack "create") and reappears
// at edit/readonly profiles, the办理 identity fields stay readonly, and the
// required set comes from the category required_fields_json.  785 and 639
// stay unbound and keep the full surface.  These tables mirror the seed in
// addons/smart_construction_core/data/business_category_seed.xml; asserting
// them here turns the entry field surface into an explicit guard instead of
// relying on the field union.
const CATEGORY_BINDING = {
  786: 'invoice.output.application',
  787: 'invoice.output.registration',
  788: 'invoice.prepaid_tax',
  789: 'invoice.input.report',
};
const CREATE_HIDDEN_ADVANCED = {
  'invoice.input.report': ['source_kind', 'direction', 'state', 'name', 'document_no', 'document_date',
    'invoice_state', 'kingdee_document_no', 'creator_name', 'created_time', 'legacy_source_table',
    'legacy_record_id', 'active'],
  'invoice.output.application': ['source_kind', 'direction', 'state', 'name', 'document_no', 'document_date',
    'invoice_state', 'push_result', 'kingdee_document_no', 'creator_name', 'created_time',
    'legacy_source_table', 'legacy_record_id', 'active'],
  'invoice.output.registration': ['source_kind', 'direction', 'state', 'name', 'document_no', 'document_date',
    'application_date', 'invoice_state', 'expected_receipt_date', 'applicant_name', 'push_result',
    'kingdee_document_no', 'creator_name', 'created_time', 'legacy_source_table', 'legacy_record_id', 'active'],
  'invoice.prepaid_tax': ['source_kind', 'direction', 'state', 'name', 'partner_id', 'contract_id',
    'document_no', 'document_date', 'kingdee_document_no', 'creator_name', 'created_time',
    'legacy_source_table', 'legacy_record_id', 'active'],
};
const CREATE_REQUIRED = {
  'invoice.output.application': ['project_id', 'partner_id', 'contract_id', 'invoice_date', 'amount_total'],
  'invoice.output.registration': ['project_id', 'partner_id', 'contract_id', 'invoice_no', 'invoice_date', 'amount_total'],
  'invoice.prepaid_tax': ['project_id', 'tax_certificate_no', 'invoice_date', 'amount_total'],
};
const CREATE_READONLY = ['business_category_id', 'invoice_content', 'operation_strategy'];

// The output business group carries exactly these four fields; when the
// create-profile policy trims all of them the rendered section collapses.
const OUTPUT_GROUP_FIELDS = ['push_result', 'kingdee_document_no', 'expected_receipt_date', 'applicant_name'];

// Stored display copies of a fact that already has its canonical presenter on
// the same form (note, attachment_ids, creator_name, created_time).  They keep
// their model field, list columns and API consumers, but must never be
// projected into the form body: one business fact, one presentation.
const DERIVED_DISPLAY_COPIES = ['note_display', 'invoice_attachment_text', 'source_created_by', 'source_created_at'];

// Bypass navigation facts (verified on sc_dev_demo 2026-09-16 via system.init
// route_authority replay): 789 (进项税额上报) is a CONTEXTUAL_ROUTE granted to
// finance-role principals (source finance.invoice_input_report_contextual_
// route in the finance role surface); the reviewing admin account
// (sc_test_admin / system_admin) carries no such grant, so its direct route
// is denied — an entry-isolation fact asserted below rather than worked
// around, per review discipline (existing accounts only, no ad-hoc groups).
// The finance principal then provides the real DOM coverage for 789.
// 639 (发票总台账) rides menu 340 under menu_sc_invoice_management_group,
// deliberately deactivated by menu_product_finance_wave1.xml (P1 finance
// wave one), so no principal holds route authority for /a/639; its DOM
// routes are recorded as not_run_no_access while the contract-level
// assertions above still run.
const CONTEXTUAL_BYPASS = {
  789: { account: process.env.E2E_FINANCE_LOGIN || 'demo_role_finance' },
};
const RETIRED_NAVIGATION = {
  639: 'menu carrier 发票台账 (menu_sc_invoice_management_group) deactivated by '
    + 'menu_product_finance_wave1.xml (P1 finance wave one); no principal holds route authority for /a/639',
};

// The action context is a python-literal string; extract string-valued keys
// (the default_* entries are all plain strings).
function contextDefaults(raw) {
  const defaults = {};
  for (const match of String(raw || '').matchAll(/'([^']+)'\s*:\s*'([^']*)'/g)) defaults[match[1]] = match[2];
  return defaults;
}

function policySurface(actionId, defaults) {
  const code = defaults.default_business_category_code || null;
  const expected = CATEGORY_BINDING[actionId] || null;
  return { code, expected, hidden: new Set(CREATE_HIDDEN_ADVANCED[code] || []) };
}

// Mirrors the native view group conditions evaluated against record values.
function conditionalVisibility({ direction, source_kind }) {
  return {
    prepaid: source_kind === 'prepaid_tax' || direction === 'prepaid',
    output: source_kind === 'output_invoice_tax' || direction === 'output',
  };
}

function* walk(rows) {
  for (const node of rows || []) {
    if (!node || typeof node !== 'object') continue;
    yield node;
    for (const key of ['children', 'tabs', 'pages', 'nodes', 'items']) if (Array.isArray(node[key])) yield* walk(node[key]);
  }
}

function treeIndex(contractResult) {
  const nodes = [...walk(contractResult.layoutContract.containerTree)];
  const groups = new Map(nodes.filter((node) => node.type === 'group' && node.containerId).map((node) => [node.containerId, node]));
  const field = (name) => {
    const matches = nodes.filter((node) => node.type === 'field' && node.name === name);
    assert.equal(matches.length, 1, `expected single occurrence of ${name}`);
    return matches[0];
  };
  return { nodes, groups, field };
}

function widgetIndex(contractResult) {
  const byName = new Map();
  for (const row of contractResult.statusContract?.widgetStatus || []) {
    const name = String(row.widgetId || '').replace(/\.occ\.[0-9a-f]+$/, '');
    if (name) byName.set(name, row);
  }
  return byName;
}

// The create-profile surface is part of the contract: policy-hidden fields
// flip to visible:false/auth:none, category required fields are required, and
// the办理 identity fields stay readonly.  Fields absent from the view are
// skipped so the guard tolerates view-only fields.
function assertCreateSurfaceStatus(actionId, baseline, surface) {
  const widgets = widgetIndex(baseline);
  for (const name of surface.hidden) {
    const row = widgets.get(`field.${name}`);
    if (!row) continue;
    assert.equal(row.visible, false, `action ${actionId}: policy field ${name} must be hidden at create`);
    assert.equal(row.auth, 'none', `action ${actionId}: policy field ${name} must carry auth none at create`);
  }
  if (surface.code) {
    for (const name of CREATE_READONLY) {
      const row = widgets.get(`field.${name}`);
      if (!row) continue;
      assert.equal(row.readonly, true, `action ${actionId}: field ${name} must be readonly at create`);
    }
    for (const name of CREATE_REQUIRED[surface.code] || []) {
      const row = widgets.get(`field.${name}`);
      if (!row) continue;
      assert.equal(row.required, true, `action ${actionId}: category field ${name} must be required at create`);
    }
  }
  if (!surface.code) {
    const row = widgets.get('field.name');
    if (row) assert.equal(row.visible, true, `action ${actionId}: unbound entry must keep the full surface (name visible)`);
  }
}

const editableControls = (locator) => locator.locator(
  'textarea:not([disabled]):not([readonly]), input:not([disabled]):not([readonly]):not([type="hidden"]), select:not([disabled]), [contenteditable="true"]');

async function assertFormRendered(page, anchorField) {
  await page.locator(`[data-field-name="${anchorField}"]`).filter({ visible: true }).first().waitFor();
  const labels = await page.locator('[data-form-section-navigation]').locator('button').allTextContents();
  const bodyText = await page.locator('body').innerText();
  return { labels, bodyText };
}

// One business fact, one presentation: no field node may render twice and the
// stored display copies of facts already presented on the form must be absent.
async function assertSinglePresentation(page, label) {
  const duplicates = await page.evaluate(() => {
    const counts = {};
    document.querySelectorAll('[data-field-name]').forEach((el) => {
      const name = String(el.getAttribute('data-field-name') || '').trim();
      if (name) counts[name] = (counts[name] || 0) + 1;
    });
    return Object.entries(counts).filter(([, count]) => count > 1).map(([name, count]) => `${name}x${count}`);
  });
  assert.deepEqual(duplicates, [], `${label}: each business fact must be presented once`);
  for (const copy of DERIVED_DISPLAY_COPIES) {
    assert.equal(await page.locator(`[data-field-name="${copy}"]`).count(), 0,
      `${label}: derived display copy ${copy} must not render in the form body`);
  }
  assert.equal(await page.getByText('快捷筛选', { exact: true }).count(), 0,
    `${label}: record-list queries stay on the record list (action filter block leaked into the form)`);
  await assertStructureResponsibility(page, label);
}

// Structure responsibility on the rendered page: emptied containers never
// occupy space and layout-only groups never draw the section separator.
async function assertStructureResponsibility(page, label) {
  const findings = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.native-container').forEach((el) => {
      const contentChildren = Array.from(el.children).filter((child) => {
        if (child.classList.contains('native-container-head')) return false;
        if (window.getComputedStyle(child).display === 'none') return false;
        return (child.textContent || '').trim().length > 0
          || Boolean(child.querySelector('[data-field-name],button,input,textarea,canvas,svg,img,a'));
      });
      const hasTitle = Boolean(el.querySelector(':scope > .native-container-head'));
      if (!hasTitle && contentChildren.length === 0) {
        out.push(`empty-container:${el.className}|html:${(el.outerHTML || '').slice(0, 300)}`);
      }
    });
    return out;
  });
  assert.equal(findings.length, 0, `${label}: emptied containers must not occupy space\n${findings.join('\n')}`);
  const decoratedWrappers = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.native-container--group--layout').forEach((el) => {
      const style = window.getComputedStyle(el);
      if (style.borderTopWidth !== '0px' || style.borderTopStyle !== 'none') {
        out.push(el.className);
      }
    });
    return out;
  });
  assert.deepEqual(decoratedWrappers, [], `${label}: layout-only groups must not draw the section separator`);
}

// Rendered value occurrences of one fact: editable controls carry it in their
// value, read-only presenters in their text.
async function factOccurrences(page, text) {
  return page.evaluate((needle) => {
    let total = 0;
    document.querySelectorAll('input,textarea,div,span,p,td').forEach((el) => {
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        if ((el.value || '') === needle) total += 1;
        return;
      }
      if (el.children.length === 0 && (el.textContent || '').trim() === needle) total += 1;
    });
    return total;
  }, text);
}

export async function checkInvoiceDefaults({ page, scope, contract, out, report }) {
  const base = process.env.BASE_URL;
  report.stages.defaults = [];
  const byId = new Map(scope.entries.map((surface) => [surface.action_id, surface]));
  const formal = FORMAL_IDS.map((id) => byId.get(id));
  const bypass = BYPASS_IDS.map((id) => byId.get(id));
  assert(formal.every(Boolean) && bypass.every(Boolean), 'expected six registered invoice surfaces');
  assert.equal(formal.every((surface) => surface.model === 'sc.invoice.registration'), true);

  for (const surface of formal) {
    const defaults = contextDefaults(surface.action_context);
    assert.equal(defaults.default_direction, { 785: 'input', 786: 'output', 787: 'output', 788: 'prepaid' }[surface.action_id],
      `action ${surface.action_id} context must carry its direction default`);
    const policy = policySurface(surface.action_id, defaults);
    assert.equal(policy.code, policy.expected,
      `action ${surface.action_id}: business category binding mismatch (got ${policy.code})`);
    const expected = conditionalVisibility({ direction: defaults.default_direction, source_kind: defaults.default_source_kind });

    // 1. Contract gate: authority is stated explicitly (no fallback), the
    // legacy structure is fully retired, the conditional group rules survive
    // on the final tree, and the create-profile entry surface matches the
    // seeded business-category policy.
    const baseline = await contract(surface);
    const source = baseline.formStructureContract.sourceAuthority.governance_source;
    assert.ok('formStructureAuthority' in source, `action ${surface.action_id}: authority key must exist`);
    assert.equal(source.formStructureAuthority, 'native_authority');
    assert.ok('formPresentationMode' in source, `action ${surface.action_id}: presentation mode key must exist`);
    assert.equal(source.formPresentationMode, 'task');
    assert.deepEqual(source.compatibilityDependencies, []);
    assert.deepEqual(source.configuredSections, []);
    assert.equal(source.resolvedActionId, surface.action_id);
    assert.equal(source.resolvedViewId, surface.view_id);
    assert(JSON.stringify(baseline.layoutContract).includes('data-sc-anchor'), 'runtime native view is stale: section anchors missing');
    const { groups, field, nodes } = treeIndex(baseline);
    for (const anchor of ANCHORS) assert(groups.has(anchor), `action ${surface.action_id}: anchor ${anchor} missing`);
    assert.equal(groups.get('invoice_prepaid_tax').attributes.invisible, PREPAID_INVISIBLE);
    assert.equal(groups.get('invoice_output_business').attributes.invisible, OUTPUT_INVISIBLE);
    for (const anchor of UNCONDITIONAL_ANCHORS) {
      assert.ok(!('invisible' in (groups.get(anchor).attributes || {})), `action ${surface.action_id}: ${anchor} must stay unconditional`);
    }
    assert.equal(field('name').modifiers.readonly, true);
    assert.equal(field('invoice_flow_label').modifiers.readonly, true);
    for (const copy of DERIVED_DISPLAY_COPIES) {
      assert.equal(nodes.filter((node) => node.type === 'field' && node.name === copy).length, 0,
        `action ${surface.action_id}: derived display copy ${copy} must not be a form field (single presentation)`);
    }
    assert.equal(field('document_date').modifiers.required, true);
    assert.ok(!field('note').modifiers?.readonly, 'note must stay editable');
    assert.ok(!field('partner_id').modifiers?.readonly, 'partner_id must stay editable');
    assertCreateSurfaceStatus(surface.action_id, baseline, policy);
    await fs.writeFile(path.join(out, `contract-${surface.action_id}.json`), JSON.stringify(baseline, null, 2));

    // 2. The formal action collection is reachable before its create/record routes.
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto(`${base}/a/${surface.action_id}?menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle');
    assert(!page.url().includes('/login'));
    const listText = await page.locator('body').innerText();
    assert(!/无权访问|没有访问权限|加载失败/.test(listText), listText.slice(-2000));
    await page.screenshot({ path: path.join(out, `entry-${surface.action_id}.png`), fullPage: true });

    // 3. New record: conditional groups evaluate from the action-context
    // defaults, the create-profile entry surface reaches the DOM, and the
    // required/readonly markers land on the rendered controls.
    await page.goto(`${base}/f/${surface.model}/new?action_id=${surface.action_id}&menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
    const rendered = await assertFormRendered(page, 'note');
    for (const title of ALWAYS_SECTIONS) assert(rendered.labels.includes(title), `action ${surface.action_id}: nav missing ${title}`);
    for (const title of RETIRED_TITLES) assert(!rendered.labels.some((label) => label.includes(title)), `action ${surface.action_id}: retired section ${title} leaked`);
    assert.equal(rendered.labels.includes(PREPAID_SECTION), expected.prepaid,
      `action ${surface.action_id}: prepaid section visibility mismatch (${JSON.stringify(expected)})`);
    const outputSectionVisible = expected.output && OUTPUT_GROUP_FIELDS.some((name) => !policy.hidden.has(name));
    assert.equal(rendered.labels.includes(OUTPUT_SECTION), outputSectionVisible,
      `action ${surface.action_id}: output business section visibility mismatch (${JSON.stringify(expected)}, hidden=${OUTPUT_GROUP_FIELDS.filter((name) => policy.hidden.has(name)).length})`);
    assert.equal(await page.locator('[data-field-name="tax_type"]').filter({ visible: true }).count() > 0, expected.prepaid,
      `action ${surface.action_id}: tax_type DOM visibility mismatch`);
    assert.equal(await page.locator('[data-field-name="applicant_name"]').filter({ visible: true }).count() > 0,
      expected.output && !policy.hidden.has('applicant_name'),
      `action ${surface.action_id}: applicant_name DOM visibility mismatch (conditional + create-profile surface)`);
    assert.equal(await page.locator('[data-field-name="name"]').filter({ visible: true }).count() > 0, !policy.hidden.has('name'),
      `action ${surface.action_id}: name DOM visibility mismatch vs create-profile surface`);
    assert.equal(await page.locator('[data-field-name="document_date"]').filter({ visible: true }).count() > 0, !policy.hidden.has('document_date'),
      `action ${surface.action_id}: document_date DOM visibility mismatch vs create-profile surface`);
    if (!policy.hidden.has('document_date')) {
      // required marker reaches the rendered control (aria/data/native signals)
      const requiredSignals = await page.locator('[data-field-name="document_date"]')
        .locator('[aria-required="true"], [data-required], [required]').count();
      assert(requiredSignals > 0, `action ${surface.action_id}: document_date required marker missing in DOM`);
    }
    // readonly fields carry no enabled editable control; the editable note does
    assert.equal(await editableControls(page.locator('[data-field-name="invoice_flow_label"]').filter({ visible: true }).first()).count(), 0,
      `action ${surface.action_id}: readonly invoice_flow_label exposes an editable control`);
    await assertSinglePresentation(page, `action ${surface.action_id} create`);
    if (!policy.hidden.has('name')) {
      assert.equal(await editableControls(page.locator('[data-field-name="name"]').filter({ visible: true }).first()).count(), 0,
        `action ${surface.action_id}: readonly name exposes an editable control`);
    } else {
      const category = page.locator('[data-field-name="business_category_id"]').filter({ visible: true }).first();
      await category.waitFor();
      assert.equal(await editableControls(category).count(), 0,
        `action ${surface.action_id}: readonly business_category_id exposes an editable control`);
    }
    assert(await editableControls(page.locator('[data-field-name="note"]').filter({ visible: true }).first()).count() > 0,
      `action ${surface.action_id}: editable note has no editable control`);
    await page.screenshot({ path: path.join(out, `new-${surface.action_id}.png`), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      `action ${surface.action_id}: horizontal overflow at 390px`);
    await page.screenshot({ path: path.join(out, `new-${surface.action_id}-narrow.png`), fullPage: false });
    await page.setViewportSize({ width: 1440, height: 960 });
    report.stages.defaults.push({ action: surface.action_id, state: 'create', viewport: [1440, 390],
      source, conditional: expected, category: policy.code || 'unbound',
      create_surface: policy.code ? { hidden: policy.hidden.size, required: (CREATE_REQUIRED[policy.code] || []).length } : 'full',
      navigation: rendered.labels, status: 'passed', url: page.url() });

    // 4. Readonly sample: record-driven conditional evaluation plus the legacy
    // migration tab.  Readonly record pages apply the empty-value projection
    // (canonicalNativeFormBridge readonlyFactIsPresentable): fields with no
    // value and no action drop out and their group collapses, so a conditional
    // section appears only when its record data is non-empty.  The assertions
    // are therefore directional: a shown section must satisfy its condition;
    // tax_type (prepaid-only) follows the same rule.
    if (surface.samples?.length) {
      const sample = surface.samples[0];
      const sampleExpected = conditionalVisibility({ direction: sample.direction, source_kind: sample.source_kind });
      await page.goto(`${base}/f/${surface.model}/${sample.id}?action_id=${surface.action_id}&menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
      const sampleRendered = await assertFormRendered(page, 'name');
      for (const title of ALWAYS_SECTIONS) assert(sampleRendered.labels.includes(title), `action ${surface.action_id}: sample nav missing ${title}`);
      for (const title of RETIRED_TITLES) assert(!sampleRendered.labels.some((label) => label.includes(title)), `action ${surface.action_id}: retired section ${title} leaked on sample`);
      if (sampleRendered.labels.includes(PREPAID_SECTION)) {
        assert(sampleExpected.prepaid, `action ${surface.action_id}: prepaid section shown although record is not prepaid`);
      }
      if (sampleRendered.labels.includes(OUTPUT_SECTION)) {
        assert(sampleExpected.output, `action ${surface.action_id}: output business section shown although record is not output`);
      }
      assert.equal(await page.locator('[data-field-name="tax_type"]').filter({ visible: true }).count() > 0, sampleExpected.prepaid,
        `action ${surface.action_id}: sample tax_type DOM visibility mismatch`);
      if (await page.locator('[data-field-name="applicant_name"]').filter({ visible: true }).count() > 0) {
        assert(sampleExpected.output, `action ${surface.action_id}: applicant_name shown although record is not output`);
      }
      assert.equal(await page.locator('[data-section-tab="红冲关联"]').count(), 0,
        `action ${surface.action_id}: red-flush tab must stay hidden without red-flush data`);
      await assertSinglePresentation(page, `action ${surface.action_id} record ${sample.id}`);
      if (sample.note) {
        // The record page used to render the stored copy next to the canonical
        // field, so the same note text appeared twice.
        assert.equal(await factOccurrences(page, sample.note), 1,
          `action ${surface.action_id}: the same note text must render exactly once on the record page`);
      }
      const presentation = { note_presentation: sample.note ? 'single' : 'empty' };
      if (sample.source_origin === 'legacy') {
        const migrationTab = page.locator('[data-section-tab="迁移来源"]').filter({ visible: true }).first();
        await migrationTab.waitFor();
        await migrationTab.click();
        // The migration page renders legacy facts.  legacy_partner_name is a
        // view-owned field with a record value; legacy_source_table and
        // legacy_record_id are category-policy readonly-profile fields and the
        // record page resolves an edit-profile contract, so only the
        // value-bearing unrestricted legacy fact is asserted in the DOM.
        await page.locator('[data-field-name="legacy_partner_name"]').filter({ visible: true }).first().waitFor();
        await page.screenshot({ path: path.join(out, `sample-${surface.action_id}-legacy-source.png`), fullPage: false });
        report.stages.defaults.push({ action: surface.action_id, record: sample.id, state: 'readonly',
          conditional: sampleExpected, source_origin: 'legacy', migration_tab: 'visible',
          legacy_fact: 'legacy_partner_name', navigation: sampleRendered.labels, ...presentation,
          status: 'passed', url: page.url() });
      } else {
        assert.equal(await page.locator('[data-section-tab="迁移来源"]').count(), 0,
          `action ${surface.action_id}: migration tab must stay hidden for non-legacy records`);
        await page.screenshot({ path: path.join(out, `sample-${surface.action_id}.png`), fullPage: false });
        report.stages.defaults.push({ action: surface.action_id, record: sample.id, state: 'readonly',
          conditional: sampleExpected, source_origin: sample.source_origin || 'unspecified',
          migration_tab: 'hidden', navigation: sampleRendered.labels, ...presentation,
          status: 'passed', url: page.url() });
      }
    } else {
      report.stages.defaults.push({ action: surface.action_id, state: 'readonly', status: 'not_run_no_sample',
        reason: 'no record matches this action domain in sc_dev_demo' });
    }
  }

  // 5. Bypass counter-examples: the two non-converted actions resolve the same
  // native form in workspace mode with no legacy section projection.  789
  // carries the input-report category binding (trimmed create surface), 639
  // stays unbound (full surface, no direction defaults).  Navigation-wise:
  // 789 is entry-isolated from the reviewing admin but reachable for a
  // finance-role principal (CONTEXTUAL_ROUTE), 639 is a retired navigation
  // entry (deactivated menu group) and must stay denied for every principal.
  for (const surface of bypass) {
    const defaults = contextDefaults(surface.action_context);
    const policy = policySurface(surface.action_id, defaults);
    assert.equal(policy.code, policy.expected,
      `bypass ${surface.action_id}: business category binding mismatch (got ${policy.code})`);
    const expected = conditionalVisibility({ direction: defaults.default_direction, source_kind: defaults.default_source_kind });
    const baseline = await contract(surface);
    const source = baseline.formStructureContract.sourceAuthority.governance_source;
    assert.ok('formStructureAuthority' in source, `bypass ${surface.action_id}: authority key must exist`);
    assert.equal(source.formStructureAuthority, 'native_authority');
    assert.ok('formPresentationMode' in source, `bypass ${surface.action_id}: presentation mode key must exist`);
    assert.equal(source.formPresentationMode, 'workspace');
    assert.deepEqual(source.configuredSections, []);
    assert.deepEqual(source.compatibilityDependencies, []);
    assert.equal(source.resolvedActionId, surface.action_id);
    assertCreateSurfaceStatus(surface.action_id, baseline, policy);
    await fs.writeFile(path.join(out, `contract-${surface.action_id}.json`), JSON.stringify(baseline, null, 2));

    // Shared DOM assertions for any authorized principal.
    const assertBypassDom = async (pg) => {
      await pg.setViewportSize({ width: 1440, height: 960 });
      await pg.goto(`${base}/a/${surface.action_id}?menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
      await pg.waitForLoadState('networkidle');
      assert(!pg.url().includes('/login'), `bypass ${surface.action_id}: session lost`);
      const listText = await pg.locator('body').innerText();
      assert(!/加载失败/.test(listText), `bypass ${surface.action_id}: list route failed to load ${listText.slice(-500)}`);
      assert(!/无权访问|没有访问权限/.test(listText), `bypass ${surface.action_id}: unexpected access denial ${listText.slice(-2000)}`);
      await pg.screenshot({ path: path.join(out, `entry-${surface.action_id}.png`), fullPage: true });
      await pg.goto(`${base}/f/${surface.model}/new?action_id=${surface.action_id}&menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
      await assertFormRendered(pg, 'note');
      for (const name of ['partner_id', 'amount_total', 'attachment_ids']) {
        if (policy.hidden.has(name)) continue;
        assert(await pg.locator(`[data-field-name="${name}"]`).filter({ visible: true }).first().isVisible(),
          `bypass ${surface.action_id}: ${name} not visible`);
      }
      assert.equal(await pg.locator('[data-field-name="name"]').filter({ visible: true }).count() > 0, !policy.hidden.has('name'),
        `bypass ${surface.action_id}: name DOM visibility mismatch vs create-profile surface`);
      assert.equal(await pg.locator('[data-field-name="tax_type"]').filter({ visible: true }).count() > 0, expected.prepaid,
        `bypass ${surface.action_id}: tax_type DOM visibility mismatch`);
      assert.equal(await pg.locator('[data-field-name="applicant_name"]').filter({ visible: true }).count() > 0,
        expected.output && !policy.hidden.has('applicant_name'),
        `bypass ${surface.action_id}: applicant_name DOM visibility mismatch`);
      const bodyText = await pg.locator('body').innerText();
      for (const title of RETIRED_TITLES) assert(!bodyText.includes(title), `bypass ${surface.action_id}: retired section ${title} leaked`);
      await assertSinglePresentation(pg, `bypass ${surface.action_id} create`);
      await pg.screenshot({ path: path.join(out, `new-${surface.action_id}.png`), fullPage: true });
      await pg.setViewportSize({ width: 390, height: 844 });
      await pg.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert(await pg.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
        `bypass ${surface.action_id}: horizontal overflow at 390px`);
      await pg.screenshot({ path: path.join(out, `new-${surface.action_id}-narrow.png`), fullPage: false });
    };

    const contextual = CONTEXTUAL_BYPASS[surface.action_id];
    if (contextual) {
      // (a) Entry isolation: the reviewing admin has no contextual grant for
      // this route, so direct navigation is denied for that principal.
      await page.setViewportSize({ width: 1440, height: 960 });
      await page.goto(`${base}/a/${surface.action_id}?menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      assert(!page.url().includes('/login'), `bypass ${surface.action_id}: session lost`);
      assert(page.url().includes('/access-denied'),
        `bypass ${surface.action_id}: expected NAVIGATION_AUTHORITY_DENIED entry isolation for the reviewing admin`);
      await page.screenshot({ path: path.join(out, `entry-${surface.action_id}-admin-denied.png`), fullPage: true });
      report.stages.defaults.push({ action: surface.action_id, bypass: true, state: 'list',
        account: scope.login, status: 'denied_for_account',
        reason: 'reviewing admin (system_admin route authority) carries no contextual grant for this route; entry isolation asserted',
        url: page.url() });

      // (b) Real DOM coverage through an existing authorized finance-role
      // principal (CONTEXTUAL_ROUTE), per review discipline.
      const password = process.env.E2E_FINANCE_PASSWORD || process.env.E2E_PASSWORD;
      assert(password, 'bypass 789: finance account password missing (E2E_FINANCE_PASSWORD/E2E_PASSWORD)');
      const browser = page.context().browser();
      const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
      const financePage = await context.newPage();
      // This surface runs in its own browser context, which the owning runner does not
      // instrument and which is closed before the run-level failure capture executes.
      // Attribute a break here from this surface's own URL, DOM, page errors and failed
      // requests instead of inferring it from the opener page.
      const financeSignals = { pageerrors: [], console: [], failed_requests: [] };
      financePage.on('pageerror', (error) => financeSignals.pageerrors.push(String(error.message).slice(0, 300)));
      financePage.on('console', (message) => {
        if (message.type() === 'error' && financeSignals.console.length < 20) financeSignals.console.push(String(message.text()).slice(0, 300));
      });
      financePage.on('requestfailed', (request) => {
        if (financeSignals.failed_requests.length < 20) financeSignals.failed_requests.push({ path: new URL(request.url()).pathname, error: request.failure()?.errorText });
      });
      // Two different facts can hide the anchor field: the page never finished loading
      // (transport), or the field is legitimately not rendered / hidden for this principal.
      // Collapsing both into one locator timeout is what made the earlier failure
      // unattributable, so classify them explicitly and keep transport evidence separate.
      const noteVisibility = async (pg) => {
        const probe = await pg.evaluate(() => {
          const nodes = [...document.querySelectorAll('[data-field-name="note"]')];
          const app = document.querySelector('#app');
          return {
            app_shell_children: app ? app.children.length : 0,
            body_text_length: (document.body?.innerText || '').length,
            note_nodes: nodes.length,
            note_visible_nodes: nodes.filter((node) => node.getClientRects().length > 0).length,
            field_nodes: document.querySelectorAll('[data-field-name]').length,
            section_nav_items: document.querySelectorAll('[data-form-section-navigation] button').length,
          };
        }).catch(() => null);
        const bodyText = await pg.locator('body').innerText().catch(() => '');
        const failed = /加载失败|无权访问|没有访问权限/.test(bodyText);
        const loaded = Boolean(probe && probe.app_shell_children > 0 && !failed);
        const verdict = !loaded ? 'page_not_loaded'
          : !probe.note_nodes ? 'field_not_rendered'
          : !probe.note_visible_nodes ? 'field_rendered_hidden' : 'field_visible';
        return { url: pg.url(), loaded, verdict, ...(probe || {}), body_text: bodyText.slice(0, 600) };
      };
      try {
        await financePage.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 15000 });
        const inputs = financePage.locator('input');
        await inputs.nth(0).fill(contextual.account);
        await inputs.nth(1).fill(password);
        if (await inputs.count() > 2 && await inputs.nth(2).isEnabled()) await inputs.nth(2).fill(scope.database);
        await financePage.getByRole('button', { name: /^登录$/ }).click();
        await financePage.waitForURL((target) => !target.pathname.includes('/login'), { timeout: 30000 });
        await assertBypassDom(financePage);
        // Recorded after the assertion so a passing run states the field was actually
        // visible, instead of reporting the pre-render state as if it were the verdict.
        report.note_visibility = { action: surface.action_id, account: contextual.account,
          at: 'after_assertion', ...(await noteVisibility(financePage)), transport: financeSignals };
        report.stages.defaults.push({ action: surface.action_id, bypass: true, state: 'create', viewport: [1440, 390],
          account: contextual.account, route_kind: 'CONTEXTUAL_ROUTE', source, conditional: expected,
          category: policy.code || 'unbound', status: 'passed', url: financePage.url() });
      } catch (error) {
        report.note_visibility = { action: surface.action_id, account: contextual.account,
          at: 'assertion_failure', ...(await noteVisibility(financePage)), transport: financeSignals };
        const dom = await financePage.content().catch(() => '');
        await fs.writeFile(path.join(out, `failure-${surface.action_id}-finance-dom.html`), dom).catch(() => {});
        await financePage.screenshot({ path: path.join(out, `failure-${surface.action_id}-finance.png`), fullPage: true }).catch(() => {});
        report.bypass_surface_failure = { action: surface.action_id, account: contextual.account,
          url: financePage.url(), ready_state: await financePage.evaluate(() => document.readyState).catch(() => null),
          body_text: (await financePage.locator('body').innerText().catch(() => '')).slice(0, 2000),
          field_nodes: fields, dom_length: dom.length, signals: financeSignals,
          assertion: String(error?.message || error).slice(0, 500) };
        throw error;
      } finally {
        await context.close();
      }
      continue;
    }

    const retired = RETIRED_NAVIGATION[surface.action_id];
    if (retired) {
      // Retired navigation entry: denied for every principal by design.
      await page.setViewportSize({ width: 1440, height: 960 });
      await page.goto(`${base}/a/${surface.action_id}?menu_id=${surface.menu_id}`, { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle');
      assert(!page.url().includes('/login'), `bypass ${surface.action_id}: session lost`);
      const denied = page.url().includes('/access-denied')
        || /无权访问|没有访问权限/.test(await page.locator('body').innerText());
      assert(denied, `bypass ${surface.action_id}: retired navigation entry must stay denied`);
      await page.screenshot({ path: path.join(out, `entry-${surface.action_id}-denied.png`), fullPage: true });
      report.stages.defaults.push({ action: surface.action_id, bypass: true, state: 'list',
        status: 'not_run_no_access', reason: retired,
        contract_coverage: 'workspace authority + create-profile surface asserted via contract replay',
        category: policy.code || 'unbound', url: page.url() });
      continue;
    }

    // Undocumented bypass surface: full DOM coverage on the reviewing account.
    await assertBypassDom(page);
    report.stages.defaults.push({ action: surface.action_id, bypass: true, state: 'create', viewport: [1440, 390],
      source, conditional: expected, category: policy.code || 'unbound', status: 'passed', url: page.url() });
  }
}
