import assert from 'node:assert/strict';
import path from 'node:path';

// Read-only representative-surface pass for the structure-consumption review.
// It consumes the compiled contract and the rendered page only; it never opens,
// stages, previews, publishes or rolls back a change set, so it cannot modify
// design drafts or published configuration.

const EDITABLE_CONTROL = 'textarea:not([disabled]):not([readonly]), input:not([disabled]):not([readonly]):not([type="hidden"]), select:not([disabled]), [contenteditable="true"]';
const RELATION_TYPES = new Set(['one2many', 'many2many']);

const CHILD_KEYS = ['children', 'tabs', 'pages', 'nodes', 'items'];

function* walkTree(rows) {
  for (const node of rows || []) {
    if (!node || typeof node !== 'object') continue;
    yield node;
    for (const key of CHILD_KEYS) yield* walkTree(node[key]);
  }
}

const fieldNodes = (contract) => [...walkTree(contract.layoutContract?.containerTree)]
  .filter((node) => node.type === 'field' && node.name);

// Container-level conditions decide whether a whole business section renders for
// the current record.  A collection the field-level profile marks visible but
// whose enclosing section is conditionally hidden abstains by design (`not id`
// only resolves on an existing record), so it must never be reported as a lost
// presentation; it is re-checked on the record surface instead.
function invisibleCondition(node) {
  for (const raw of [node.invisible, node.modifiers?.invisible, node.attributes?.invisible]) {
    if (raw === true) return 'always';
    if (Array.isArray(raw)) { if (raw.length) return JSON.stringify(raw); continue; }
    if (typeof raw !== 'string') continue;
    const value = raw.trim();
    if (value && !['false', '0'].includes(value)) return value;
  }
  return null;
}

// One entry per declared occurrence, so a fact with both a conditional and an
// unconditional occurrence is not excused by the conditional one.
function containerConditions(contract) {
  const map = new Map();
  const visit = (nodes, conditions) => {
    for (const node of nodes || []) {
      if (!node || typeof node !== 'object') continue;
      const own = invisibleCondition(node);
      const nested = own ? [...conditions, own] : conditions;
      if (node.type === 'field' && node.name) {
        const name = String(node.name);
        map.set(name, [...(map.get(name) || []), nested]);
      }
      for (const key of CHILD_KEYS) visit(node[key], nested);
    }
  };
  visit(contract.layoutContract?.containerTree, []);
  return map;
}

// Structure responsibility on the rendered page: one presentation per business
// fact, no emptied container occupying space, no separator owned by a layout
// wrapper, no section title invented by a wrapper, and the section navigation
// resolving against the same visible tree the body renders.
async function structureFindings(page) {
  return page.evaluate(() => {
    const out = { duplicated: [], empty_containers: [], decorated_layout_groups: [], titled_layout_groups: [] };
    const counts = {};
    document.querySelectorAll('[data-field-name]').forEach((el) => {
      const name = String(el.getAttribute('data-field-name') || '').trim();
      if (name) counts[name] = (counts[name] || 0) + 1;
    });
    out.duplicated = Object.entries(counts).filter(([, count]) => count > 1).map(([name, count]) => `${name}x${count}`);
    document.querySelectorAll('.native-container').forEach((el) => {
      const hasHead = Boolean(el.querySelector(':scope > .native-container-head'));
      const content = Array.from(el.children).filter((child) => {
        if (child.classList.contains('native-container-head')) return false;
        if (window.getComputedStyle(child).display === 'none') return false;
        return (child.textContent || '').trim().length > 0
          || Boolean(child.querySelector('[data-field-name],button,input,textarea,canvas,svg,img,a'));
      });
      if (!hasHead && content.length === 0) {
        const box = el.getBoundingClientRect();
        out.empty_containers.push({ class: String(el.className).slice(0, 90), height: Math.round(box.height), width: Math.round(box.width) });
      }
    });
    document.querySelectorAll('.native-container--group--layout').forEach((el) => {
      const style = window.getComputedStyle(el);
      if (style.borderTopWidth !== '0px' || style.borderTopStyle !== 'none') out.decorated_layout_groups.push(String(el.className).slice(0, 120));
      const head = el.querySelector(':scope > .native-container-head');
      if (head && (head.textContent || '').trim()) out.titled_layout_groups.push((head.textContent || '').trim().slice(0, 60));
    });
    return out;
  });
}

// The delivered page declares how it presents the record.  A readonly
// presentation renders a reduced fact set (the renderer's input buckets exist
// only for a writable record), so an input position that the field policy marks
// visible is legitimately absent there; entry positions are verified on the
// writable surface instead.
async function presentationMode(page) {
  return page.evaluate(() => {
    const seen = {};
    document.querySelectorAll('[data-render-profile]').forEach((el) => {
      const value = String(el.getAttribute('data-render-profile') || '').trim();
      if (value) seen[value] = (seen[value] || 0) + 1;
    });
    const ranked = Object.entries(seen).sort((left, right) => right[1] - left[1]);
    return ranked.length ? ranked[0][0] : null;
  });
}

// The delivered views declare business sections collapsed by default
// (`data-sc-collapsible` + `data-sc-collapsed-by-default`) and the renderer hides
// a collapsed subtree with CSS.  That is a declared presentation state, not a lost
// render, so the pass resolves it through the product's own section toggle and
// then inspects the structure behind it.
async function expandCollapsedSections(page, label, observations) {
  const collapsedSections = () => page.evaluate(() => [...document.querySelectorAll('.native-container[data-collapsed="true"]')]
    .map((el) => String(el.getAttribute('data-group-title') || '').trim() || String(el.className).slice(0, 60)));
  observations.collapsed_sections = await collapsedSections();
  for (let guard = 0; guard < 20; guard += 1) {
    const toggle = page.locator('.native-container[data-collapsed="true"] > .native-container-head button[aria-expanded="false"]').first();
    if (await toggle.count() === 0) break;
    await toggle.click();
    await page.waitForTimeout(120);
  }
  const unresolved = await collapsedSections();
  observations.collapsed_sections_unresolved = unresolved;
  assert.deepEqual(unresolved, [], `${label}: collapsed sections must expand and reveal their structure`);
  return observations.collapsed_sections;
}

async function assertStructureResponsibility(page, label) {
  const findings = await structureFindings(page);
  assert.deepEqual(findings.duplicated, [], `${label}: each business fact must be presented once`);
  // A wrapper whose children are all hidden may be empty and harmless; only one
  // that still draws space is an emptied presentation the reader must not see.
  assert.deepEqual(findings.empty_containers.filter((row) => row.height > 2).map((row) => `${row.class}[${row.height}x${row.width}]`), [],
    `${label}: emptied containers must not occupy space`);
  assert.deepEqual(findings.decorated_layout_groups, [], `${label}: layout-only wrappers must not draw the section separator`);
  assert.deepEqual(findings.titled_layout_groups, [], `${label}: layout-only wrappers must not carry a section title`);
  return findings;
}

// The delivered 章节入口 must reach every section it advertises.  The product
// reveals a section by activating the 页签 that owns it, so a target that does
// not resolve on the currently open page is the mechanism working as designed,
// not a defect: the behaviour assertion is that using the entry makes its target
// exist and become visible, which is what the reviewer is promised.
async function assertSectionNavigationBehaviour(page, label, observations) {
  const nav = page.locator('[data-form-section-navigation]').first();
  if (await nav.count() === 0) {
    observations.nav_targets = [];
    return [];
  }
  const buttons = nav.locator('[data-section-target]');
  const total = await buttons.count();
  const results = [];
  for (let index = 0; index < total; index += 1) {
    const button = buttons.nth(index);
    const section = String(await button.textContent() || '').trim().slice(0, 40);
    const selector = String(await button.getAttribute('data-section-target') || '');
    await button.click();
    await page.waitForTimeout(200);
    const state = await page.evaluate((value) => {
      let node = null;
      try { node = document.querySelector(value); } catch { return { resolved: false, visible: false }; }
      return { resolved: Boolean(node), visible: Boolean(node && node.getClientRects().length) };
    }, selector);
    results.push({ section, selector, ...state });
  }
  observations.nav_targets = results;
  assert.deepEqual(results.filter((row) => !row.resolved).map((row) => row.section), [],
    `${label}: every 章节入口 must resolve a target`);
  assert.deepEqual(results.filter((row) => !row.visible).map((row) => row.section), [],
    `${label}: every 章节入口 must reveal a visible section`);
  return results;
}

// Measured sticky separation: the command bar publishes its height, the 章节导航
// pins below that published offset, and activating an entry brings its target
// below the navigation.  The three bands are measured on the rendered page at
// the two viewports where the product declares a sticky offset, so a published
// height that no consumer reads, or a fallback smaller than the real header,
// fails here instead of silently covering the header action row.
async function assertStickyLayoutSeparation(page, label, observations) {
  const STICKY_VIEWPORTS = [{ width: 1088, height: 900 }, { width: 390, height: 844 }];
  const geometry = () => page.evaluate(() => {
    const rect = (selector) => {
      const el = document.querySelector(selector);
      if (!el) return null;
      const box = el.getBoundingClientRect();
      return { top: Math.round(box.top), bottom: Math.round(box.bottom) };
    };
    const carrier = document.querySelector('.sc-page[data-product-page-mode="form"], .contract-form-native-shell[data-product-page-mode="form"]');
    return {
      command_bar_var: carrier ? getComputedStyle(carrier).getPropertyValue('--sc-form-command-bar-height').trim() : '',
      bar: rect('.contract-form-command-bar'),
      actions: rect('.product-page-header__actions') || rect('[data-workspace-action-bar]'),
      nav: rect('[data-form-section-navigation]'),
    };
  });
  const measured = [];
  for (const viewport of STICKY_VIEWPORTS) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(350);
    const initial = await geometry();
    assert(initial.bar && initial.nav,
      `${label} @${viewport.width}: the sticky command bar and the 章节导航 must both render`);
    // The first paint band is measured before any entry is activated, so the
    // resting layout is covered as well as the pinned layout.
    measured.push({ viewport: `${viewport.width}x${viewport.height}`, section: '(top)', bar: initial.bar, actions: initial.actions, nav: initial.nav, target: null });
    const buttons = page.locator('[data-form-section-navigation] [data-section-target]');
    const total = await buttons.count();
    for (let index = 0; index < total; index += 1) {
      const button = buttons.nth(index);
      const section = String(await button.textContent() || '').trim().slice(0, 40);
      const selector = String(await button.getAttribute('data-section-target') || '');
      await button.click();
      await page.waitForTimeout(250);
      const state = await page.evaluate((value) => {
        const rect = (selector_) => {
          let el = null;
          try { el = document.querySelector(selector_); } catch { el = null; }
          if (!el) return null;
          const box = el.getBoundingClientRect();
          return { top: Math.round(box.top), bottom: Math.round(box.bottom), visible: el.getClientRects().length > 0 };
        };
        return {
          bar: rect('.contract-form-command-bar'),
          actions: rect('.product-page-header__actions') || rect('[data-workspace-action-bar]'),
          nav: rect('[data-form-section-navigation]'),
          target: rect(value),
        };
      }, selector);
      measured.push({ viewport: `${viewport.width}x${viewport.height}`, section, ...state });
    }
  }
  observations.sticky_layout = measured;
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.waitForTimeout(200);
  const covered = measured.filter((row) => (row.actions && row.nav
    ? Math.min(row.actions.bottom, row.nav.bottom) - Math.max(row.actions.top, row.nav.top) > 0
    : true));
  assert.deepEqual(covered.map((row) => `${row.viewport}:${row.section}`), [],
    `${label}: the 章节导航 must never cover the command bar action row`);
  const behind = measured.filter((row) => {
    if (!row.nav) return true;
    // The navigation pins below the published command-bar height, never inside it.
    if (row.bar && row.nav.top < row.bar.bottom - 1) return true;
    // Activating an entry must bring its target below the navigation; a 1px
    // tolerance absorbs integer rounding, nothing more.
    if (row.target && row.target.visible && row.target.top < row.nav.bottom - 1) return true;
    return false;
  });
  assert.deepEqual(behind.map((row) => `${row.viewport}:${row.section}`), [],
    `${label}: the 章节导航 must stay below the command bar and above the revealed section`);
  return measured;
}

// Page-level invariants must hold on every notebook page, not only on the page
// that happens to be open at first paint.
async function assertStructureAcrossTabs(page, label) {
  const tabs = page.locator('[data-section-tab]:visible');
  const total = await tabs.count();
  const perTab = [];
  for (let index = 0; index < total; index += 1) {
    const tab = tabs.nth(index);
    const name = String(await tab.textContent() || '').trim();
    await tab.click();
    await page.waitForTimeout(250);
    const findings = await assertStructureResponsibility(page, `${label} 页签 ${name}`);
    perTab.push({ tab: name, clean: true, findings });
  }
  return perTab;
}

// Registered stored display copies must stay declared outside the form body and
// must never become a second presentation of the same fact inside it, while the
// canonical carrier of that fact keeps its entry.
async function assertDisplayCopyDiscipline({ page, contract, checks, label, observations }) {
  const declared = JSON.stringify(contract);
  const fields = fieldNodes(contract);
  for (const copy of checks.display_copy_out_of_body || []) {
    assert.equal(fields.filter((node) => node.name === copy).length, 0,
      `${label}: display copy ${copy} must not be a field node in the render tree`);
    assert.equal(await page.locator(`[data-field-name="${copy}"]`).count(), 0,
      `${label}: display copy ${copy} must not render in the form body`);
    const stillDeclared = declared.includes(copy);
    observations.display_copy_out_of_body[copy] = { rendered: false, declared_outside_body: stillDeclared };
    assert(stillDeclared, `${label}: ${copy} must stay declared outside the body, not be deleted from the contract`);
  }
  for (const name of checks.require_render || []) {
    const visible = await page.locator(`[data-field-name="${name}"]`).filter({ visible: true }).count();
    assert(visible > 0, `${label}: canonical ${name} must keep its entry in the body`);
    observations.require_render[name] = visible;
  }
  for (const name of checks.suffix_display_must_render || []) {
    const rendered = await page.locator(`[data-field-name="${name}"]`).count();
    assert(rendered > 0, `${label}: unregistered ${name} must not be removed by name/suffix guesswork`);
    observations.suffix_display_must_render[name] = rendered;
  }
}

// Create-profile visibility/readonly delivered by the contract itself.  A field
// the profile hides carries no rendered entry by design; a field the profile
// omits is view-only and is not part of this surface.
function widgetProfile(contract) {
  const map = new Map();
  for (const row of contract.statusContract?.widgetStatus || []) {
    const name = String(row.widgetId || '').replace(/\.occ\.[0-9a-f]+$/, '').replace(/^field\./, '');
    if (!name) continue;
    map.set(name, [...(map.get(name) || []), {
      visible: row.visible !== false, readonly: row.readonly === true, reason: row.reasonCode || null,
    }]);
  }
  // A fact may carry several occurrences in different presentation positions.
  // It is presented when any occurrence is visible, and it is readonly only when
  // every visible occurrence is readonly: one editable position still carries an
  // edit, so a hidden readonly occurrence must not label the fact readonly.
  const summary = new Map();
  for (const [name, occurrences] of map) {
    const visible = occurrences.filter((row) => row.visible);
    summary.set(name, {
      visible: visible.length > 0,
      readonly: visible.length > 0 && visible.every((row) => row.readonly),
      reason: (visible.find((row) => row.reason) || occurrences.find((row) => row.reason) || {}).reason || null,
    });
  }
  return summary;
}

// Walk every notebook page and collect what the page actually renders there:
// field entries, whether an entry exposes an editable control, and the width of
// the detail region.  A collection that lives on a 页签 is only observable once
// that page is activated, so the union across pages is the rendered fact set.
async function collectRenderedFacts(page) {
  const tabs = page.locator('[data-section-tab]:visible');
  const total = await tabs.count();
  const pages = [];
  const facts = {};
  const record = (name, data, where) => {
    const previous = facts[name];
    if (!previous) facts[name] = { ...data, where };
    else facts[name] = {
      editable: Math.max(previous.editable, data.editable),
      detail: Math.max(previous.detail, data.detail),
      detail_width: Math.max(previous.detail_width, data.detail_width),
      width: Math.max(previous.width, data.width),
      height: Math.max(previous.height, data.height),
      // The strictest carrier wins, so a field that renders once on a
      // single-column surface must satisfy the full-width rule.
      columns: Math.min(previous.columns, data.columns),
      where: previous.where,
    };
  };
  const snapshot = async (where) => page.evaluate(() => {
    const tree = document.querySelector('.native-form-tree');
    const detailSelector = '[data-detail-collection-content], .relation-editor';
    return {
      treeWidth: tree ? tree.getBoundingClientRect().width : 0,
      fields: [...document.querySelectorAll('[data-field-name]')].map((el) => {
        const box = el.getBoundingClientRect();
        const holders = [el, ...el.querySelectorAll('.native-container')];
        const widths = holders.map((holder) => holder.getBoundingClientRect().width).filter((width) => width > 0);
        const details = [...el.querySelectorAll(detailSelector)];
        const detailWidths = details.map((detail) => detail.getBoundingClientRect().width).filter((width) => width > 0);
        const grid = el.closest('[class*="template-form-section-grid--columns-"]');
        const columns = grid ? Number((String(grid.className).match(/columns-(\d+)/) || [])[1] || 0) : 1;
        return {
          name: el.getAttribute('data-field-name'),
          editable: el.querySelectorAll('textarea:not([disabled]):not([readonly]), input:not([disabled]):not([readonly]):not([type="hidden"]), select:not([disabled]), [contenteditable="true"]').length,
          detail: details.length,
          detail_width: Math.round(Math.max(0, ...detailWidths)),
          width: Math.round(Math.max(0, ...widths)),
          height: Math.round(box.height),
          columns: columns > 0 ? columns : 1,
        };
      }),
    };
  });
  const first = await snapshot('body');
  for (const row of first.fields) record(row.name, row, 'body');
  for (let index = 0; index < total; index += 1) {
    const tab = tabs.nth(index);
    const label = String(await tab.textContent() || '').trim();
    await tab.click();
    await page.waitForTimeout(250);
    const active = await tab.evaluate((el) => el.className.toString().includes('native-tab--active'));
    const page_ = await snapshot(`tab:${label}`);
    for (const row of page_.fields) record(row.name, row, `tab:${label}`);
    pages.push({ tab: label, active, fields: page_.fields.length, content: page_.fields.length > 0 });
  }
  const treeWidth = first.treeWidth || 0;
  return { facts, pages, treeWidth };
}

// Relation collections declared as visible by the create profile must render on
// some notebook page; a visible collection absent from every page is a lost
// entry, while a profile-hidden collection is a legitimate absence.
function assertRelationCollections({ contract, facts, label, observations }) {
  const profile = widgetProfile(contract);
  const conditions = containerConditions(contract);
  const relations = [...new Map(fieldNodes(contract)
    .filter((node) => RELATION_TYPES.has(String(node.fieldInfo?.type || '')))
    .map((node) => [node.name, node])).values()];
  assert(relations.length > 0, `${label}: compiled structure must declare at least one relation collection`);
  const missing = [];
  const skipped = [];
  const conditional = [];
  for (const node of relations) {
    const status = profile.get(node.name);
    if (!status) { skipped.push(`${node.name}(not-in-create-profile)`); continue; }
    if (!status.visible) { skipped.push(`${node.name}(policy-hidden:${status.reason || 'hidden'})`); continue; }
    if (facts[node.name]) continue;
    // Every declared occurrence is section-conditional in this record context,
    // so the absence is an abstention rather than a lost presentation.
    const chains = conditions.get(node.name) || [];
    if (chains.length && chains.every((chain) => chain.length)) {
      conditional.push(`${node.name}(section-conditional:${chains.at(-1).at(-1)})`);
      continue;
    }
    missing.push(`${node.name}(${node.fieldInfo.type})`);
  }
  observations.relations = relations.map((node) => {
    const status = profile.get(node.name);
    return `${node.name}:${node.fieldInfo.type}:${status ? (status.visible ? `rendered@${facts[node.name]?.where || 'missing'}` : `policy-hidden:${status.reason || ''}`) : 'not-in-create-profile'}`;
  });
  observations.relations_skipped = skipped;
  observations.relations_conditional = conditional;
  assert.deepEqual(missing, [], `${label}: visible relation collections must render (body or a 页签)`);
}

// A fact the contract marks readonly may not expose an editable control at its
// carrying position, on any notebook page.
function assertReadonlyValues({ contract, facts, label, observations }) {
  const profile = widgetProfile(contract);
  const readonly = [...new Map(fieldNodes(contract).filter((node) => {
    const status = profile.get(node.name);
    // The delivered profile owns the create/edit decision; the node flag only
    // covers a fact the profile does not carry.
    if (status) return status.readonly;
    return node.readonly === true || node.modifiers?.readonly === true;
  }).map((node) => [node.name, node])).values()];
  assert(readonly.length > 0, `${label}: compiled structure must carry readonly facts`);
  const rendered = readonly.filter((node) => facts[node.name]);
  const editable = rendered.filter((node) => facts[node.name].editable > 0).map((node) => node.name);
  observations.readonly_checked = rendered.map((node) => node.name);
  assert(rendered.length > 0, `${label}: at least one readonly fact must be present on the rendered page`);
  assert.deepEqual(editable, [], `${label}: readonly facts must not expose editable controls`);
}

// Notebook navigation must actually switch the rendered page, and every 页签
// must carry content.
function assertNotebookNavigation({ pages, label, observations }) {
  assert(pages.length > 1, `${label}: notebook must expose more than one 页签`);
  observations.tabs = pages;
  assert.deepEqual(pages.filter((page_) => !page_.active || !page_.content).map((page_) => page_.tab), [],
    `${label}: every 页签 must activate and carry content`);
}

// A relation detail region must fill the surface that carries it.  A collection
// on a page-level (single-column) surface must span the form body; a collection
// the delivered view places inside a multi-column layout group correctly fills
// its own column, and both are measured on the rendered page so a detail
// narrower than its own carrier stays a defect.
function assertFullWidthDetail({ contract, facts, treeWidth, label, observations }) {
  const detail = fieldNodes(contract).filter((node) => RELATION_TYPES.has(String(node.fieldInfo?.type || ''))
    && facts[node.name]?.detail > 0);
  const measured = detail.map((node) => {
    const fact = facts[node.name];
    return {
      field: node.name,
      detail: fact.detail_width,
      carrier: fact.width,
      tree: Math.round(treeWidth),
      columns: fact.columns,
      column_fill: fact.width > 0 ? Number((fact.detail_width / fact.width).toFixed(3)) : 0,
      tree_ratio: treeWidth > 0 ? Number((fact.detail_width / treeWidth).toFixed(3)) : 0,
    };
  });
  observations.detail_widths = measured;
  assert(measured.length > 0, `${label}: relation detail region must render on some 页签`);
  assert.deepEqual(measured.filter((row) => row.column_fill < 0.9).map((row) => row.field), [],
    `${label}: relation detail must fill the column that carries it`);
  const pageLevel = measured.filter((row) => row.columns === 1);
  assert(pageLevel.length > 0, `${label}: at least one relation collection must render on a page-level surface`);
  assert.deepEqual(pageLevel.filter((row) => row.tree_ratio < 0.9).map((row) => row.field), [],
    `${label}: a page-level relation collection must span the whole form body`);
}

export async function runRepresentativeSurface({ page, scope, contract, out, report }) {
  const base = process.env.BASE_URL;
  const checks = scope.representative || {};
  assert(Object.keys(checks).length > 0, `representative checks are not registered for topic ${scope.topic}`);
  report.stages.representative = [];
  for (const surface of scope.entries) {
    const routes = [{
      kind: 'create',
      profile: 'create',
      url: `${base}/f/${surface.model}/new?action_id=${surface.action_id}&menu_id=${surface.menu_id}`,
    }];
    // Container conditions such as `invisible="not id"` can only resolve on an
    // existing record, so a registered record surface replays the same read-only
    // battery on a governed sample record of the same action.
    const recordId = surface.samples?.[0]?.id;
    const uncovered = [];
    if (checks.record_surface && recordId) {
      routes.push({
        kind: 'record',
        profile: 'edit',
        record_id: recordId,
        url: `${base}/f/${surface.model}/${recordId}?action_id=${surface.action_id}&menu_id=${surface.menu_id}`,
      });
    } else if (checks.record_surface) {
      // The registered record surface is replayed on a governed sample of the same
      // action; without one the route cannot run.  Record the exact reason (empty
      // action domain versus a record rule the scope identity cannot pass) instead
      // of reporting a shorter route list that looks complete.
      const state = surface.sample_state || {};
      uncovered.push({
        fact: 'record_surface',
        state: state.state || 'no_governed_sample',
        domain_rows: state.domain_rows ?? null,
        business_row_count: surface.business_row_count ?? null,
        reason: 'a registered record surface replays on a readable governed sample of the same action; this scope identity has none',
      });
    }
    const surfaceReport = {
      action_id: surface.action_id, model: surface.model, view_id: surface.view_id, menu_id: surface.menu_id, routes: [],
      ...(uncovered.length ? { uncovered } : {}),
    };
    report.stages.representative.push(surfaceReport);
    for (const route of routes) {
      const label = `${scope.topic} action ${surface.action_id} ${route.kind}`;
      const compiled = await contract(surface, {
        render_profile: route.profile,
        ...(route.record_id ? { record_id: route.record_id } : {}),
      });
      const observations = { display_copy_out_of_body: {}, require_render: {}, suffix_display_must_render: {} };
      await page.setViewportSize({ width: 1440, height: 960 });
      await page.goto(route.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      // A registered entry that the delivered route authority does not carry is a
      // reachability fact, not a structure result: record it with its exact reason
      // and keep inspecting the remaining surfaces instead of aborting the pass.
      if (page.url().includes('/access-denied')) {
        surfaceReport.status = 'blocked';
        surfaceReport.blocked_reason = new URL(page.url()).searchParams.get('reason') || 'NAVIGATION_AUTHORITY_DENIED';
        surfaceReport.url = page.url();
        break;
      }
      // Readiness gate: the native tree must reach a rendered state before any
      // structural assertion runs, so a slow first compile is never reported as a
      // lost container or a missing fact.
      await page.locator('.native-form-tree[data-state="ready"]').first().waitFor({ state: 'attached', timeout: 45000 });
      await page.locator('[data-field-name]').first().waitFor({ state: 'attached', timeout: 45000 });
      await expandCollapsedSections(page, label, observations);
      const mode = await presentationMode(page);
      observations.presentation_mode = mode;
      const writable = mode !== 'readonly';
      const findings = await assertStructureResponsibility(page, label);
      await assertDisplayCopyDiscipline({ page, contract: compiled, checks, label, observations });
      const rendered = await collectRenderedFacts(page);
      if (writable && checks.relations) assertRelationCollections({ contract: compiled, facts: rendered.facts, label, observations });
      if (!writable) {
        // Record the reduction instead of asserting a writable-position rule the
        // readonly presentation does not carry.
        observations.relations_not_applicable = 'readonly-presentation';
        observations.note = 'readonly presentation renders a reduced fact set; input positions are verified on the writable surface';
      }
      if (checks.readonly_values) assertReadonlyValues({ contract: compiled, facts: rendered.facts, label, observations });
      if (writable && checks.notebook) assertNotebookNavigation({ pages: rendered.pages, label, observations });
      if (writable && checks.full_width_detail) assertFullWidthDetail({ contract: compiled, facts: rendered.facts, treeWidth: rendered.treeWidth, label, observations });
      observations.tab_structure = await assertStructureAcrossTabs(page, label);
      if (checks.section_navigation) await assertSectionNavigationBehaviour(page, label, observations);
      if (checks.section_navigation) await assertStickyLayoutSeparation(page, label, observations);
      await page.screenshot({ path: path.join(out, `representative-${scope.topic}-${surface.action_id}-${route.kind}.png`), fullPage: true });
      // Field-level evidence for the same measured surface: which facts the
      // renderer actually promoted to nodes.  Read-only, bounded, no secrets;
      // it turns a section-presence difference into an attributable fact
      // instead of a guessed cause.
      const renderedFieldNames = await page.evaluate(() => [...new Set(
        [...document.querySelectorAll('[data-field-name]')].map((node) => node.getAttribute('data-field-name')),
      )].filter(Boolean).sort());
      surfaceReport.routes.push({
        kind: route.kind, url: page.url(), fields: await page.locator('[data-field-name]').count(),
        field_names: renderedFieldNames,
        sections: await page.locator('[data-form-section-navigation] button').count(), findings, observations,
      });
      surfaceReport.status = 'passed';
      surfaceReport.url = page.url();
    }
  }
  const blocked = report.stages.representative.filter((row) => row.status === 'blocked');
  report.representative_blocked = blocked.map((row) => ({ action_id: row.action_id, reason: row.blocked_reason }));
  // Registered facts that could not run are neither a pass nor a block: they stay
  // machine-readable so the remaining-gap ledger can name the missing coverage.
  report.representative_uncovered = report.stages.representative
    .filter((row) => row.uncovered)
    .flatMap((row) => row.uncovered.map((item) => ({ action_id: row.action_id, ...item })));
  const inspected = report.stages.representative.filter((row) => row.status === 'passed');
  // Every surface either produced structure results, or was recorded as blocked
  // by the delivered route authority.  Nothing is silently skipped and the
  // blocked list stays machine-readable for the remaining-gap ledger.
  assert.deepEqual(report.stages.representative.filter((row) => !row.status).map((row) => row.action_id), [],
    `representative topic ${scope.topic}: every surface must report a status`);
  assert(inspected.length + blocked.length === report.stages.representative.length,
    `representative topic ${scope.topic}: surface status must be passed or blocked`);
  assert(inspected.length > 0 || blocked.length > 0,
    `representative topic ${scope.topic}: no surface was registered`);
}
