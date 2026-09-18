import assert from 'node:assert/strict';
import path from 'node:path';

// Read-only representative-surface pass for the structure-consumption review.
// It consumes the compiled contract and the rendered page only; it never opens,
// stages, previews, publishes or rolls back a change set, so it cannot modify
// design drafts or published configuration.

const EDITABLE_CONTROL = 'textarea:not([disabled]):not([readonly]), input:not([disabled]):not([readonly]):not([type="hidden"]), select:not([disabled]), [contenteditable="true"]';
// A delivered fact is user-fillable through two control shapes.  Besides a plain
// editing control there is the picker trigger: its inner input is `readonly` by
// construction, so the strict selector above counts it as zero even though the
// user drives it (measured on the tax-deduction create surface - activating the
// 开票日期 trigger opened the calendar panel and wrote the picked date back).
// The trigger only counts while its own root is not disabled and the input is
// not disabled, so a disabled or readonly presentation still measures zero and
// the readonly guard stays strict.
const PICKER_CONTROL = '[data-semantic-driver$="-picker"]:not(.t-is-disabled) input:not([disabled])';
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
    // Activating an entry is only usable if it delivers its section into the pinned
    // band, and the deliverable is direction-independent: a sweep that only walks the
    // entries in document order never exercises the reverse jump a reader makes from
    // the last section back to the first, nor an activation taken from a resting
    // position the entry itself did not produce.  Both are replayed here and measured
    // by the same rule.
    const measureEntry = async (index, phase) => {
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
           track_scroll_left: Math.round(document.querySelector('[data-form-section-navigation] .form-section-navigation__track')?.scrollLeft || 0),
           target: rect(value),
         };
       }, selector);
      return { viewport: `${viewport.width}x${viewport.height}`, viewport_height: viewport.height, phase, section, ...state };
    };
    const indices = [...Array(total).keys()];
    for (const index of indices) measured.push(await measureEntry(index, 'forward'));
    for (const index of [...indices].reverse()) measured.push(await measureEntry(index, 'reverse'));
    // A manual scroll moves the page without activating anything; the next entry
    // must still deliver its section into the pinned band from that resting position.
    await page.mouse.move(Math.round(viewport.width / 2), Math.round(viewport.height / 2));
    await page.mouse.wheel(0, 2400);
    await page.waitForTimeout(250);
    measured.push(await measureEntry(0, 'after-manual-scroll'));
    // The 章节导航 is itself a horizontal track: once the active entry is centred,
    // reaching a different entry means moving the track, so an entry that is off
    // the track is part of using the control.  The track is parked at its far edge
    // and then the first entry is taken, which is the reach the reader performs.
    await page.evaluate(() => {
      const track = document.querySelector('[data-form-section-navigation] .form-section-navigation__track');
      if (track) track.scrollLeft = track.scrollWidth;
    });
    await page.waitForTimeout(150);
    measured.push(await measureEntry(total - 1, 'after-track-scroll'));
    measured.push(await measureEntry(0, 'after-track-scroll'));
  }
  observations.sticky_layout = measured;
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.waitForTimeout(200);
  const covered = measured.filter((row) => (row.actions && row.nav
    ? Math.min(row.actions.bottom, row.nav.bottom) - Math.max(row.actions.top, row.nav.top) > 0
    : true));
  assert.deepEqual(covered.map((row) => `${row.viewport}:${row.phase || 'rest'}:${row.section}`), [],
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
  assert.deepEqual(behind.map((row) => `${row.viewport}:${row.phase || 'rest'}:${row.section}`), [],
    `${label}: the 章节导航 must stay below the command bar and above the revealed section`);
  return measured;
}

// The 章节导航 is itself a horizontal track, so reaching an entry means moving
// the track - and a reader who moves it has positioned a control under their own
// finger.  Automatic follow that slides the track while the reader is between
// positioning an entry and pressing it turns a pressable entry into a moving
// target: the press lands on a different section or on nothing at all, while the
// highlight keeps showing the section the reader never chose.  The battery below
// replays that sequence with real pointer input.  The entry is pressed where it
// currently is - never scrolled into view by the driver first, which is what
// makes a broken track still look green - and the delivered state is measured in
// one stable state: the entry under the press point, the pressed section, the
// highlight, the three bands and the track offset.
async function assertSectionNavigationPressStability(page, label, observations) {
  const VIEWPORTS = [{ width: 390, height: 844 }, { width: 1088, height: 900 }];
  const rows = [];

  const readState = () => page.evaluate(() => {
    const rect = (selector) => {
      const el = document.querySelector(selector);
      if (!el) return null;
      const box = el.getBoundingClientRect();
      return { top: Math.round(box.top), bottom: Math.round(box.bottom), left: Math.round(box.left), right: Math.round(box.right) };
    };
    const nav = document.querySelector('[data-form-section-navigation]');
    const track = nav ? nav.querySelector('.form-section-navigation__track') : null;
    return {
      active: nav ? (nav.querySelector('[aria-current="location"]')?.textContent || '').trim() : '',
      actions: rect('.product-page-header__actions') || rect('[data-workspace-action-bar]'),
      nav: rect('[data-form-section-navigation]'),
      target: null,
      track: track ? { ...rect('.form-section-navigation__track'), scroll_left: Math.round(track.scrollLeft),
        scroll_width: track.scrollWidth, client_width: track.clientWidth } : null,
    };
  });

  // The press point is the middle of the part of the entry the track actually
  // shows: an entry the control advertises but keeps outside the track window is
  // not pressable, and that is the fact this returns.
  const entryBox = (text) => page.evaluate((value) => {
    const entry = [...document.querySelectorAll('[data-form-section-navigation] [data-section-target]')]
      .find((node) => (node.textContent || '').trim() === value);
    if (!entry) return null;
    const box = entry.getBoundingClientRect();
    const track = entry.closest('.form-section-navigation__track');
    const trackBox = track ? track.getBoundingClientRect() : null;
    const window_ = trackBox || box;
    const visibleLeft = Math.max(box.left, window_.left);
    const visibleRight = Math.min(box.right, window_.right);
    return {
      left: Math.round(box.left), right: Math.round(box.right), y: Math.round(box.top + box.height / 2),
      visible_width: Math.round(visibleRight - visibleLeft),
      fully_inside_track: trackBox ? box.left >= trackBox.left - 1 && box.right <= trackBox.right + 1 : true,
      press_x: Math.round((visibleLeft + visibleRight) / 2),
      press_y: Math.round(box.top + box.height / 2),
    };
  }, text);

  const underPressPoint = (x, y) => page.evaluate(({ px, py }) => {
    const el = document.elementFromPoint(px, py);
    const entry = el && el.closest ? el.closest('[data-section-link]') : null;
    return entry ? (entry.textContent || '').trim() : null;
  }, { px: x, py: y });

  const pressPoint = async (x, y) => {
    await page.mouse.move(x, y);
    await page.waitForTimeout(120);
    await page.mouse.down();
    await page.waitForTimeout(70);
    await page.mouse.up();
    await page.waitForTimeout(400);
  };

  const pressPublishedControl = async (ariaLabel) => {
    const box = await page.evaluate((name) => {
      const control = [...document.querySelectorAll('[data-form-section-navigation] .form-section-navigation__scroll-control')]
        .find((node) => node.getAttribute('aria-label') === name);
      if (!control || control.getAttribute('aria-disabled') === 'true') return null;
      const rect = control.getBoundingClientRect();
      return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
    }, ariaLabel);
    if (!box) return false;
    await pressPoint(box.x, box.y);
    return true;
  };

  const bodyScroll = async (viewport, deltaY) => {
    await page.mouse.move(Math.round(viewport.width / 2), Math.round(viewport.height * 0.7));
    await page.mouse.wheel(0, deltaY);
    await page.waitForTimeout(600);
  };

  // The body scroll of a reader who is holding a control with another finger:
  // the wheel is delivered where the pointer already is, so the press stays on
  // the entry it started on.
  const scrollBodyWithoutMovingPointer = async (deltaY) => {
    await page.mouse.wheel(0, deltaY);
    await page.waitForTimeout(600);
  };

  // The track is a horizontal control: moving it is done with the published
  // browse controls, which is the reach the reader performs.
  const revealInTrack = async (text, direction) => {
    for (let attempt = 0; attempt < 8; attempt += 1) {
      const box = await entryBox(text);
      if (box && box.fully_inside_track && box.visible_width > 8) return box;
      const moved = await pressPublishedControl(direction === 1 ? '向后浏览表单章节' : '向前浏览表单章节');
      if (!moved) break;
    }
    return entryBox(text);
  };

  const measureEntry = async () => readState();

  const assertPressed = async (record, entry, viewport) => {
    const state = await measureEntry();
    const active = state.active;
    if (active !== entry) {
      rows.push({ ...record, viewport: `${viewport.width}x${viewport.height}`, status: 'wrong_section',
        pressed: entry, delivered_active: active, actions: state.actions, nav: state.nav,
        track: state.track, target: null });
      return false;
    }
    const target = await page.evaluate((value) => {
      const el = document.querySelector(value);
      if (!el || !el.getClientRects().length) return null;
      const box = el.getBoundingClientRect();
      return { top: Math.round(box.top), bottom: Math.round(box.bottom), visible: true };
    }, record.selector);
    rows.push({ ...record, viewport: `${viewport.width}x${viewport.height}`, status: 'pressed',
      pressed: entry, delivered_active: active, actions: state.actions, nav: state.nav,
      track: state.track, target });
    return true;
  };

  for (const viewport of VIEWPORTS) {
    await page.setViewportSize(viewport);
    await page.waitForTimeout(350);
    const initial = await readState();
    if (!initial.track || initial.track.scroll_width <= initial.track.client_width + 2) {
      rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'not_applicable',
        reason: initial.track ? 'track_does_not_overflow' : 'no_section_navigation' });
      continue;
    }
    const vp = `${viewport.width}x${viewport.height}`;
    const entryNames = await page.evaluate(() => [...document.querySelectorAll('[data-form-section-navigation] [data-section-target]')]
      .map((node) => (node.textContent || '').trim()));
    const first = entryNames[0];
    const last = entryNames[entryNames.length - 1];

    // 1. A resting state that is not the first entry: scrolling the body is what
    //    the reader does before reaching for the track.
    await bodyScroll(viewport, 2600);
    const selectorFor = async (text) => page.evaluate((value) => {
      const entry = [...document.querySelectorAll('[data-form-section-navigation] [data-section-target]')]
        .find((node) => (node.textContent || '').trim() === value);
      return entry ? entry.getAttribute('data-section-target') : '';
    }, text);

    // 2. First entry brought into the track, pressed where it is.
    const firstBox = await revealInTrack(first, -1);
    if (!firstBox || !firstBox.fully_inside_track) {
      rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_reachable',
        entry: first, box: firstBox, reason: 'first entry stays outside the track window after the published browse control' });
    } else {
      const under = await underPressPoint(firstBox.press_x, firstBox.press_y);
      if (under !== first) {
        rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_under_press_point',
          entry: first, under, box: firstBox });
      } else {
        await pressPoint(firstBox.press_x, firstBox.press_y);
        await assertPressed({ step: 'first_entry_in_view', selector: await selectorFor(first) }, first, viewport);
      }
    }

    // 3. The reader positions the track, then scrolls the body before pressing.
    //    The entry the reader is about to press must not move in between; this is
    //    the exact regression: the highlight follows the body, the track does not.
    const positionedAt = await bodyScroll(viewport, 2600).then(() => revealInTrack(first, -1));
    const beforeScroll = positionedAt ? { box: positionedAt, under: await underPressPoint(positionedAt.press_x, positionedAt.press_y) } : null;
    if (!beforeScroll || !beforeScroll.box || !beforeScroll.box.fully_inside_track) {
      rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_reachable',
        entry: first, box: beforeScroll && beforeScroll.box, reason: 'positioned entry stays outside the track window' });
    } else {
      await bodyScroll(viewport, -420);
      const afterScroll = await entryBox(first);
      const heldState = await readState();
      const stable = afterScroll && afterScroll.left === beforeScroll.box.left
        && (await underPressPoint(afterScroll.press_x, afterScroll.press_y)) === first;
      if (!stable) {
        rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_moved_under_finger',
          entry: first, before: beforeScroll.box, after: afterScroll, track: heldState.track,
          active_after_body_scroll: heldState.active });
      } else {
        await pressPoint(afterScroll.press_x, afterScroll.press_y);
        await assertPressed({ step: 'pressed_after_body_scroll', selector: await selectorFor(first) }, first, viewport);
      }
    }

    // 4. Last entry, then back to the first: the reverse jump the reader makes
    //    after inspecting the end of a long form.
    const lastBox = await revealInTrack(last, 1);
    if (lastBox && lastBox.fully_inside_track && (await underPressPoint(lastBox.press_x, lastBox.press_y)) === last) {
      await pressPoint(lastBox.press_x, lastBox.press_y);
      await assertPressed({ step: 'last_entry_in_view', selector: await selectorFor(last) }, last, viewport);
    } else {
      rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_reachable', entry: last, box: lastBox });
    }
    const backBox = await revealInTrack(first, -1);
    if (backBox && backBox.fully_inside_track && (await underPressPoint(backBox.press_x, backBox.press_y)) === first) {
      await pressPoint(backBox.press_x, backBox.press_y);
      await assertPressed({ step: 'last_then_first', selector: await selectorFor(first) }, first, viewport);
    } else {
      rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_reachable', entry: first, box: backBox });
    }
    // 5. First entry, then the last one: the forward reach from the pinned band.
    const forwardBox = await revealInTrack(last, 1);
    if (forwardBox && forwardBox.fully_inside_track && (await underPressPoint(forwardBox.press_x, forwardBox.press_y)) === last) {
      await pressPoint(forwardBox.press_x, forwardBox.press_y);
      await assertPressed({ step: 'first_then_last', selector: await selectorFor(last) }, last, viewport);
    } else {
      rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_reachable', entry: last, box: forwardBox });
    }

    // 6. The press and the body scroll overlap: the reader holds an entry with one
    //    finger while the body keeps moving (a second finger, or inertia).  The
    //    automatic follow keeps the highlight readable while the body scrolls, but
    //    it must not slide the track during a press - the entry would leave the
    //    finger and the release would be delivered to a neighbour or to the track
    //    itself.  The scroll is applied with the pointer left on the entry: moving
    //    the pointer before the release is a drag, and a release off a control
    //    cancels its activation in every browser, so a harness that moved the
    //    pointer first would measure itself instead of the control.  The case is
    //    only live when the body scroll really does move the followed section.
    const raceBox = await revealInTrack(last, 1);
    const raceArmed = raceBox && raceBox.fully_inside_track
      && (await underPressPoint(raceBox.press_x, raceBox.press_y)) === last;
    if (!raceArmed) {
      rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_reachable', entry: last, box: raceBox });
    } else {
      const beforePress = await readState();
      const activeBeforePress = beforePress.active;
      const trackBeforePress = beforePress.track;
      await page.mouse.move(raceBox.press_x, raceBox.press_y);
      await page.waitForTimeout(120);
      await page.mouse.down();
      await page.waitForTimeout(70);
      await scrollBodyWithoutMovingPointer(-420);
      const heldBox = await entryBox(last);
      const duringPress = await readState();
      const underHeldPress = await underPressPoint(raceBox.press_x, raceBox.press_y);
      const trackSlid = Boolean(trackBeforePress && duringPress.track
        && trackBeforePress.scroll_left !== duringPress.track.scroll_left);
      await page.mouse.up();
      await page.waitForTimeout(400);
      if (duringPress.active === activeBeforePress) {
        rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'not_applicable', step: 'pressed_while_body_scrolled',
          entry: last, box: raceBox, reason: 'the body scroll did not move the followed section' });
      } else if (trackSlid || !heldBox || heldBox.left !== raceBox.left || underHeldPress !== last) {
        rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_moved_under_press',
          step: 'pressed_while_body_scrolled', entry: last, before: raceBox, after: heldBox,
          under_press_point: underHeldPress, track_slid: trackSlid,
          track_before: trackBeforePress, track_during: duringPress.track,
          active_after_body_scroll: duringPress.active });
      } else {
        await assertPressed({ step: 'pressed_while_body_scrolled', selector: await selectorFor(last) }, last, viewport);
      }

      // 6b. Negative control for the delivery above: the same press, released
      //     after the pointer was deliberately taken off the entry, must activate
      //     nothing.  Without it, "the pressed entry was delivered" could be
      //     produced by the press itself instead of by the release landing on the
      //     entry.  The control carries its own verdict, so it is neither exempted
      //     from the failure list nor counted as a delivered section.
      const controlBox = await revealInTrack(first, -1);
      if (controlBox && controlBox.fully_inside_track
        && (await underPressPoint(controlBox.press_x, controlBox.press_y)) === first) {
        const activeBeforeControl = (await readState()).active;
        await page.mouse.move(controlBox.press_x, controlBox.press_y);
        await page.waitForTimeout(120);
        await page.mouse.down();
        await page.waitForTimeout(70);
        const releaseX = Math.round(viewport.width / 2);
        const releaseY = Math.round(viewport.height * 0.7);
        await page.mouse.move(releaseX, releaseY);
        await page.waitForTimeout(120);
        // The arming fact is where the pointer is when the release happens, not
        // where the entry is: a hit test at the entry's own coordinates would
        // report the entry even though the pointer had already left it.
        const underRelease = await underPressPoint(releaseX, releaseY);
        await page.mouse.up();
        await page.waitForTimeout(400);
        const controlState = await readState();
        const controlArmed = underRelease !== first;
        rows.push({ viewport: `${viewport.width}x${viewport.height}`,
          status: !controlArmed ? 'control_not_armed'
            : controlState.active === activeBeforeControl ? 'control' : 'activation_survived_a_cancelled_press',
          step: 'release_off_entry_activates_nothing', pressed: first,
          active_when_held: activeBeforeControl, delivered_active: controlState.active,
          release_point: { x: releaseX, y: releaseY, under: underRelease },
          entry_still_under_its_own_point: await underPressPoint(controlBox.press_x, controlBox.press_y),
          actions: controlState.actions,
          nav: controlState.nav, track: controlState.track, target: null });
      } else {
        rows.push({ viewport: `${viewport.width}x${viewport.height}`, status: 'entry_not_reachable',
          step: 'release_off_entry_activates_nothing', entry: first, box: controlBox });
      }
    }

    // 7. Auto-reveal path.  An entry the track keeps outside its window cannot be
    //    pressed where it is, so an automation first scrolls it into view and then
    //    presses it.  The press point has to be read *after* that reveal: the point
    //    the entry had while it was hidden now belongs to whichever entry sits
    //    there, so a press sent to it activates a neighbour and takes the reader to
    //    a section they did not choose.  The hidden point and what is under it are
    //    measured and reported, so that hazard is visible instead of assumed away.
    const hideFirst = async () => {
      for (let attempt = 0; attempt < 8; attempt += 1) {
        const box = await entryBox(first);
        if (box && box.visible_width <= 0) return box;
        if (!(await pressPublishedControl('向后浏览表单章节'))) break;
      }
      return entryBox(first);
    };
    const hiddenBox = await hideFirst();
    if (!hiddenBox) {
      rows.push({ viewport: vp, status: 'entry_not_reachable', entry: first, box: null, step: 'auto_reveal_press' });
    } else if (hiddenBox.fully_inside_track || hiddenBox.visible_width > 0) {
      rows.push({ viewport: vp, status: 'not_applicable', entry: first, box: hiddenBox, step: 'auto_reveal_press',
        reason: 'the track already shows part of the first entry, so there is nothing to auto-reveal' });
    } else {
      const hiddenPoint = { x: hiddenBox.press_x, y: hiddenBox.press_y };
      const underHiddenPoint = await underPressPoint(hiddenPoint.x, hiddenPoint.y);
      await page.locator('[data-form-section-navigation] [data-section-link]').filter({ hasText: first }).first()
        .scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      const revealedBox = await entryBox(first);
      // What a press sent to the point the entry had while it was hidden would
      // now hit: the entry itself, a neighbouring entry, or nothing.
      const stalePointAfterReveal = await underPressPoint(hiddenPoint.x, hiddenPoint.y);
      if (!revealedBox || !revealedBox.fully_inside_track) {
        rows.push({ viewport: vp, status: 'entry_not_reachable', entry: first, box: revealedBox, step: 'auto_reveal_press',
          reason: 'the entry is still outside the track window after the automation scrolled it into view' });
      } else {
        await pressPoint(revealedBox.press_x, revealedBox.press_y);
        await assertPressed({ step: 'auto_reveal_press', selector: await selectorFor(first),
          hidden_point: hiddenPoint, under_hidden_point: underHiddenPoint,
          stale_point_after_reveal: stalePointAfterReveal, revealed_left: revealedBox.left }, first, viewport);
      }
    }

    // 8. Keyboard path.  The published navigation is reachable without a pointer:
    //    Tab moves focus out of the published browse control into the entries and
    //    Enter activates the focused entry, which must deliver the same section and
    //    the same below-the-pinned-band target as a press.  Enter is only sent while
    //    a section entry holds focus, so a run that never reaches the track cannot
    //    send it into a form control.
    await hideFirst();
    const focusStart = await page.evaluate(() => {
      const control = [...document.querySelectorAll('[data-form-section-navigation] .form-section-navigation__scroll-control')]
        .find((node) => node.getAttribute('aria-label') === '向前浏览表单章节');
      if (!control) return false;
      control.focus();
      return true;
    });
    let focusedEntry = null;
    let tabPresses = 0;
    for (; focusStart && tabPresses < 6; ) {
      await page.keyboard.press('Tab');
      tabPresses += 1;
      await page.waitForTimeout(80);
      focusedEntry = await page.evaluate(() => {
        const el = document.activeElement;
        const link = el && el.closest ? el.closest('[data-section-link]') : null;
        return link ? (link.textContent || '').trim() : null;
      });
      if (focusedEntry) break;
    }
    const focusState = await readState();
    if (!focusStart || focusedEntry !== first) {
      rows.push({ viewport: vp, status: 'keyboard_focus_not_reached', step: 'keyboard_activation',
        entry: first, focused: focusedEntry, tabs_to_focus: tabPresses, track: focusState.track,
        reason: 'Tab did not move focus onto the first section entry from the published browse control' });
    } else {
      await page.keyboard.press('Enter');
      await page.waitForTimeout(400);
      await assertPressed({ step: 'keyboard_activation', selector: await selectorFor(first),
        focused_entry: focusedEntry, tabs_to_focus: tabPresses, track_at_focus: focusState.track }, first, viewport);
    }
  }
  observations.section_navigation_press = rows;
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.waitForTimeout(200);
  // 'control' rows carry their own verdict (a cancelled press that activated
  // nothing); they assert a behaviour but deliver no section, so they are
  // neither failures nor delivery evidence.
  const failed = rows.filter((row) => !['pressed', 'not_applicable', 'control'].includes(row.status));
  assert.deepEqual(failed.map((row) => `${row.viewport}:${row.step || row.status}:${row.entry || row.pressed || ''}`), [],
    `${label}: an entry positioned under the reader's finger must stay there and deliver its section`);
  const delivered = rows.filter((row) => row.status === 'pressed');
  const behind = delivered.filter((row) => (!row.nav || !row.target
    || row.target.top < row.nav.bottom - 1));
  assert.deepEqual(behind.map((row) => `${row.viewport}:${row.step}`), [],
    `${label}: a pressed 章节入口 must deliver its target below the pinned navigation`);
  return rows;
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
async function assertDisplayCopyDiscipline({ page, contract, checks, label, observations, writable }) {
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
    // "Keeps its entry in the body" is asserted against the contract for every
    // surface: the canonical field must stay a node of the render tree the page
    // consumes.  The rendered entry is asserted on the writable surface, where
    // the reader needs the control.  The readonly presentation runs a separate
    // shared omission rule (an empty readonly fact is dropped unless it is a
    // detail collection), so an absent DOM entry there is recorded with its
    // owning rule instead of being reported as a lost fact or silently passed.
    assert(fields.filter((node) => node.name === name).length > 0,
      `${label}: canonical ${name} must stay a node of the render tree`);
    const rendered = await page.locator(`[data-field-name="${name}"]`).count();
    const visible = await page.locator(`[data-field-name="${name}"]`).filter({ visible: true }).count();
    observations.require_render[name] = { rendered, visible, writable: Boolean(writable) };
    if (writable) {
      assert(rendered > 0 && visible > 0,
        `${label}: canonical ${name} must keep a usable entry on the writable surface (dom=${rendered} visible=${visible})`);
    } else if (rendered === 0) {
      observations.readonly_fact_omitted = [
        ...(observations.readonly_fact_omitted || []),
        {
          name,
          rule: 'readonlyFactIsPresentable omits an empty readonly field unless it is a one2many detail collection',
          surface: 'readonly-presentation',
        },
      ];
    }
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
      visible: row.visible !== false, readonly: row.readonly === true,
      required: row.required === true, reason: row.reasonCode || null,
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
      // The delivered policy owns the required marker too: one occurrence that
      // asks for the fact is enough to make the record unfinishable without it.
      required: visible.some((row) => row.required),
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
      picker: Math.max(previous.picker, data.picker),
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
  // The selectors are passed in so the measured page and the assertion share one
  // definition; nothing here is re-declared as a literal inside the browser.
  const snapshot = async (where) => page.evaluate((selectors) => {
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
          editable: el.querySelectorAll(selectors.editable).length,
          picker: el.querySelectorAll(selectors.picker).length,
          detail: details.length,
          detail_width: Math.round(Math.max(0, ...detailWidths)),
          width: Math.round(Math.max(0, ...widths)),
          height: Math.round(box.height),
          columns: columns > 0 ? columns : 1,
        };
      }),
    };
  }, { editable: EDITABLE_CONTROL, picker: PICKER_CONTROL });
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
  // Either delivered shape would let the user write a fact the profile declares
  // read-only, so both the plain control and the picker trigger must be absent.
  const writable = rendered
    .filter((node) => facts[node.name].editable > 0 || facts[node.name].picker > 0)
    .map((node) => node.name);
  observations.readonly_checked = rendered.map((node) => node.name);
  assert(rendered.length > 0, `${label}: at least one readonly fact must be present on the rendered page`);
  assert.deepEqual(writable, [], `${label}: readonly facts must not expose editable controls`);
}

// A required fact must be fillable on the surface that requires it.  The
// delivered profile owns the decision: a fact it leaves authorable cannot also
// be required-without-a-control, because the user would then have no way to
// complete the record.  A required fact the profile itself marks read-only is a
// different question - its value has to arrive from a default or another
// carrier - so it is recorded with its exact declaration instead of being
// conflated with this defect.
function assertRequiredFactsAreFillable({ contract, facts, label, observations }) {
  const profile = widgetProfile(contract);
  const required = [...new Map(fieldNodes(contract).filter((node) => {
    const status = profile.get(node.name);
    if (status) return status.required === true && status.visible !== false;
    return node.fieldInfo?.required === true;
  }).map((node) => [node.name, node])).values()];
  assert(required.length > 0, `${label}: the compiled create profile must carry required facts`);
  const rows = required.map((node) => {
    const status = profile.get(node.name) || {};
    const fact = facts[node.name];
    return {
      name: node.name,
      policy_readonly: status.readonly === true,
      body_readonly: node.readonly === true || node.modifiers?.readonly === true,
      rendered: Boolean(fact),
      editable: fact ? fact.editable : 0,
      picker: fact ? fact.picker : 0,
      fillable: fact ? fact.editable + fact.picker : 0,
    };
  });
  observations.required_facts = rows;
  observations.required_facts_not_rendered = rows.filter((row) => !row.rendered).map((row) => row.name);
  observations.required_facts_without_control = rows
    .filter((row) => row.rendered && row.fillable === 0)
    .map((row) => `${row.name}:policy_readonly=${row.policy_readonly}:body_readonly=${row.body_readonly}`);
  const contradiction = rows
    .filter((row) => row.rendered && !row.policy_readonly && row.fillable === 0)
    .map((row) => row.name);
  assert.deepEqual(
    contradiction, [],
    `${label}: the delivered profile leaves these required facts authorable but renders no control for them`,
  );
  // A fact counted through its picker trigger only is returned so the caller can
  // prove that trigger is reachable on the delivered page instead of trusting
  // the selector.
  return { pickerBacked: rows.filter((row) => row.fillable > 0 && row.editable === 0).map((row) => row.name) };
}

// A trigger counted as fillable must be reachable, the same way a plain control
// would be: visible and able to take focus.  This keeps the widened selector
// from becoming a blanket exemption for a hidden or inert control.
async function assertPickerTriggersAreReachable({ page, names, label, observations }) {
  observations.picker_backed_required_facts = names;
  for (const name of names) {
    const trigger = page
      .locator(`[data-field-name="${name}"] [data-semantic-driver$="-picker"]:not(.t-is-disabled) input:not([disabled])`)
      .first();
    assert.equal(await trigger.count(), 1, `${label}: ${name} is required and authorable but exposes no picker trigger`);
    assert.equal(await trigger.isVisible(), true, `${label}: ${name} is required and authorable but its picker trigger is not visible`);
    await trigger.focus();
    assert.equal(await trigger.evaluate((el) => document.activeElement === el), true,
      `${label}: ${name} is required and authorable but its picker trigger cannot take focus`);
  }
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

// The empty collection surface and the create entry describe one capability.
// A surface the user can create on must never present the read-only copy that
// claims the account has no create right, because the entry control the user
// can see still opens the create form.  Read-only: the list route is opened and
// read, no record is written.
async function assertEmptyListSurface({ page, surface, base }) {
  const url = `${base}/a/${surface.action_id}?menu_id=${surface.menu_id}`;
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  if (page.url().includes('/access-denied')) {
    return {
      status: 'blocked',
      reason: new URL(page.url()).searchParams.get('reason') || 'NAVIGATION_AUTHORITY_DENIED',
      url: page.url(),
    };
  }
  await page.locator('[data-semantic-component="ActionView"]').first().waitFor({ state: 'attached', timeout: 45000 });
  // Readiness: the delivered page publishes its own collection state.  An empty
  // state that resolves before the entry controls settle would report a copy
  // difference that is only a loading order, so wait for a settled state first.
  await page.waitForFunction(() => {
    const root = document.querySelector('[data-semantic-component="ActionView"]');
    const state = root && root.getAttribute('data-collection-state');
    return Boolean(state) && state !== 'loading';
  }, null, { timeout: 45000 });
  const observed = await page.evaluate(() => {
    const root = document.querySelector('[data-semantic-component="ActionView"]');
    const empty = document.querySelector('[data-collection-state="empty"] [data-semantic-component="ScEmptyState"]');
    const actionBar = document.querySelector('[data-workspace-action-bar]');
    const buttons = actionBar ? [...actionBar.querySelectorAll('button')] : [];
    const create = buttons.find((button) => (button.textContent || '').includes('新建')) || null;
    const text = (node) => (node ? (node.textContent || '').replace(/\s+/g, ' ').trim() : null);
    return {
      collection_state: (root && root.getAttribute('data-collection-state')) || '',
      empty_state_text: text(empty),
      create_entry_text: text(create),
      create_entry_available: Boolean(create) && !create.disabled,
    };
  });
  const result = { url: page.url(), ...observed };
  if (!observed.empty_state_text) {
    // The list carries rows: the empty-copy rule does not apply on this surface.
    return { ...result, status: 'not_applicable', reason: 'the collection is not empty' };
  }
  if (observed.create_entry_available) {
    assert.ok(
      !observed.empty_state_text.includes('没有新建权限'),
      `${surface.action_id}: the empty surface claims the account cannot create while the create entry is available`,
    );
  } else {
    // The reverse direction: without a create entry the surface must not invite
    // the user to create one, which would promise an action the page cannot run.
    assert.ok(
      !observed.empty_state_text.includes('可以先新建一条业务记录'),
      `${surface.action_id}: the empty surface invites the user to create while no create entry is available`,
    );
  }
  return { ...result, status: 'passed' };
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
    // The empty-collection copy is checked on the list route the entry actually
    // opens, before the form routes, so the entry capability and the copy the
    // user reads are observed on the same delivered page.
    if (checks.empty_list_state) {
      surfaceReport.list_surface = await assertEmptyListSurface({ page, surface, base });
    }
    for (const route of routes) {
      const label = `${scope.topic} action ${surface.action_id} ${route.kind}`;
      // Declared outside the attempt so a failure raised before the first
      // assertion still reaches the failure record below.
      const observations = { display_copy_out_of_body: {}, require_render: {}, suffix_display_must_render: {} };
      let findings = null;
      try {
        const compiled = await contract(surface, {
          render_profile: route.profile,
          ...(route.record_id ? { record_id: route.record_id } : {}),
        });
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
        findings = await assertStructureResponsibility(page, label);
        await assertDisplayCopyDiscipline({ page, contract: compiled, checks, label, observations, writable });
        const rendered = await collectRenderedFacts(page);
        if (writable && checks.relations) assertRelationCollections({ contract: compiled, facts: rendered.facts, label, observations });
        if (!writable) {
          // Record the reduction instead of asserting a writable-position rule the
          // readonly presentation does not carry.
          observations.relations_not_applicable = 'readonly-presentation';
          observations.note = 'readonly presentation renders a reduced fact set; input positions are verified on the writable surface';
        }
        if (checks.readonly_values) assertReadonlyValues({ contract: compiled, facts: rendered.facts, label, observations });
        if (writable && checks.required_fillable) {
          const { pickerBacked } = assertRequiredFactsAreFillable({ contract: compiled, facts: rendered.facts, label, observations });
          await assertPickerTriggersAreReachable({ page, names: pickerBacked, label, observations });
        }
        if (writable && checks.notebook) assertNotebookNavigation({ pages: rendered.pages, label, observations });
        if (writable && checks.full_width_detail) assertFullWidthDetail({ contract: compiled, facts: rendered.facts, treeWidth: rendered.treeWidth, label, observations });
        observations.tab_structure = await assertStructureAcrossTabs(page, label);
        if (checks.section_navigation) await assertSectionNavigationBehaviour(page, label, observations);
        if (checks.section_navigation) await assertStickyLayoutSeparation(page, label, observations);
        if (checks.section_navigation) await assertSectionNavigationPressStability(page, label, observations);
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
      } catch (error) {
        // An assertion that names a fact is not yet an attribution.  Keep the
        // page the fact was measured on, the measurements taken up to the
        // failure and a bounded DOM excerpt of the region the renderer
        // produced, so the failure can be attributed instead of guessed at.
        // Bounded and redacted: no credentials or tokens are recorded.
        const dom = await page.evaluate(() => {
          const tree = document.querySelector('.native-form-tree');
          return tree ? tree.outerHTML.slice(0, 20000) : '';
        }).catch(() => '');
        surfaceReport.routes.push({
          kind: route.kind, url: page.url(), status: 'failed',
          error: String((error && error.message) || error).slice(0, 600),
          findings, observations, dom_excerpt: dom,
        });
        surfaceReport.status = 'failed';
        surfaceReport.url = page.url();
        await page.screenshot({
          path: path.join(out, `representative-${scope.topic}-${surface.action_id}-${route.kind}-failure.png`),
          fullPage: true,
        }).catch(() => {});
        throw error;
      }
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
