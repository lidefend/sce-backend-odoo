/**
 * Executable proof for FE-TPL-04 (application shell): the official shell
 * composition is adopted by an explicit, layout-scoped presentation policy, the
 * shell gate really consumes it, and the shell's own style layer no longer
 * carries the component-local alias block it used to declare.
 *
 * Three things are proved that a screenshot cannot:
 *
 *   1. the adoption decision is an explicit layout list, so a route joins by
 *      declaring an adopted layout — the gate never names a business model,
 *      menu, action, role or company;
 *   2. the shell gate and its published identity come from one pure decision,
 *      so they cannot drift apart;
 *   3. the shell style layer consumes canonical tokens instead of declaring its
 *      own `--ink/--muted/--panel/--layout-divider` aliases, while every
 *      capability the shell had (panel modes, sidebar, topbar, touch targets)
 *      stays.
 *
 * The policy module is pure: no Vue, no DOM, no TDesign. The structural checks
 * read the shipped sources, so the test fails if the wiring is reverted while
 * the policy still reports "adopted".
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import {
  STANDARD_SHELL_COMPOSITION_LAYOUTS,
  resolveStandardShellComposition,
} from '../src/app/presentation/standardShellComposition';

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
// Part 1 — the shell adoption policy is an explicit, layout-scoped list
// ---------------------------------------------------------------------------
checkDeep(
  resolveStandardShellComposition({ layout: 'shell' }),
  { composition: 'official-standard-shell', adopted: true, reason: 'shell-layout-adopted' },
  'an adopted layout resolves to the official shell composition',
);
checkDeep(
  resolveStandardShellComposition({ layout: 'shell', embeddedRelationDialog: false }),
  { composition: 'official-standard-shell', adopted: true, reason: 'shell-layout-adopted' },
  'an explicit non-dialog route still adopts the shell',
);
checkDeep(
  resolveStandardShellComposition({ layout: 'shell', embeddedRelationDialog: true }),
  { composition: 'legacy-shell-surface', adopted: false, reason: 'embedded-relation-dialog' },
  'an embedded relation dialog keeps its previous composition',
);
checkDeep(
  resolveStandardShellComposition({ layout: 'blank' }),
  { composition: 'legacy-shell-surface', adopted: false, reason: 'not-a-shell-layout' },
  'an unverified layout keeps its previous composition',
);
checkDeep(
  resolveStandardShellComposition({}),
  { composition: 'legacy-shell-surface', adopted: false, reason: 'not-a-shell-layout' },
  'an absent layout never adopts by accident',
);
checkDeep(
  resolveStandardShellComposition({ layout: undefined }),
  { composition: 'legacy-shell-surface', adopted: false, reason: 'not-a-shell-layout' },
  'a missing layout never adopts by accident',
);
checkDeep(
  resolveStandardShellComposition({ layout: '  shell  ' }),
  { composition: 'official-standard-shell', adopted: true, reason: 'shell-layout-adopted' },
  'the decision is insensitive to surrounding whitespace',
);
checkDeep(
  resolveStandardShellComposition({ layout: 'SHELL' }),
  { composition: 'legacy-shell-surface', adopted: false, reason: 'not-a-shell-layout' },
  'adoption is an exact layout identity, not a case-folded label guess',
);
checkDeep(
  resolveStandardShellComposition({ layout: 'shell', embeddedRelationDialog: 'true' }),
  { composition: 'official-standard-shell', adopted: true, reason: 'shell-layout-adopted' },
  'a dialog hint that is not the boolean true never bypasses the shell',
);
check(Object.isFrozen(STANDARD_SHELL_COMPOSITION_LAYOUTS), true, 'the adopted layout list is immutable');
checkDeep(
  [...STANDARD_SHELL_COMPOSITION_LAYOUTS],
  ['shell'],
  'the adopted layout list stays the explicit verified scope',
);

// ---------------------------------------------------------------------------
// Part 2 — the policy stays pure presentation scope
// ---------------------------------------------------------------------------
const policyPath = 'frontend/apps/web/src/app/presentation/standardShellComposition.ts';
const policySource = readSource(policyPath);
check(policySource.includes("from 'vue'"), false, 'the shell policy must not import Vue');
check(policySource.includes('document.'), false, 'the shell policy must not touch the DOM');
check(policySource.includes('window.'), false, 'the shell policy must not touch the window');
check(/from\s+['"]tdesign-vue-next['"]/.test(policySource), false, 'the shell policy must not import the component library');
check(policySource.includes(OFFICIAL_REFERENCE), true, 'the shell policy records the official reference snapshot');
check(policySource.includes("'project.project'"), false, 'the shell policy must not name a business model');
check(policySource.includes("'sc.general.contract'"), false, 'the shell policy must not name a business model');
check(/menu_\d+|action_\d+/.test(policySource), false, 'the shell policy must not name a menu or action');

// ---------------------------------------------------------------------------
// Part 3 — the shipped shell gate really consumes the policy
// ---------------------------------------------------------------------------
const appSource = readSource('frontend/apps/web/src/App.vue');
check(
  appSource.includes("import { resolveStandardShellComposition } from './app/presentation/standardShellComposition';"),
  true,
  'the application root imports the one pure shell policy',
);
check(
  appSource.includes('const shellComposition = computed('),
  true,
  'the application root resolves the shell decision once',
);
check(
  appSource.includes('const shellComposition = computed(() => resolveStandardShellComposition({'),
  true,
  'the shell decision is the pure policy, not an inline comparison',
);
check(
  appSource.includes('v-if="shellComposition.adopted"'),
  true,
  'the shell gate is decided by the policy decision',
);
check(
  appSource.includes("route.meta?.layout === 'shell'"),
  false,
  'the shell gate no longer decides adoption inline',
);
check(
  appSource.includes(':data-shell-composition="shellComposition.composition"'),
  true,
  'the application root publishes the composition it used',
);
check(
  appSource.includes(':data-shell-composition-reason="shellComposition.reason"'),
  true,
  'the application root publishes why it chose it',
);
check(appSource.includes("'project.project'"), false, 'the application root must not name a business model');
check(appSource.includes("'sc.general.contract'"), false, 'the application root must not name a business model');

// ---------------------------------------------------------------------------
// Part 4 — the shell style layer consumes canonical tokens, not local aliases
// ---------------------------------------------------------------------------
const shellCss = readSource('frontend/apps/web/src/layouts/AppShell.css');
for (const localAlias of ['--surface:', '--ink:', '--muted:', '--accent:', '--panel:', '--layout-divider:']) {
  check(shellCss.includes(localAlias), false, `the shell no longer declares its local alias ${localAlias}`);
}
for (const localUse of ['var(--ink)', 'var(--muted)', 'var(--accent)', 'var(--panel)', 'var(--layout-divider)']) {
  check(shellCss.includes(localUse), false, `the shell no longer consumes its local alias ${localUse}`);
}
check(shellCss.includes('color: var(--sc-semantic-text-primary)'), true, 'the shell text color is the canonical semantic token');
check(shellCss.includes('color: var(--sc-semantic-text-secondary)'), true, 'the shell muted text color is the canonical semantic token');
check(shellCss.includes('background: var(--sc-semantic-surface-panel)'), true, 'the shell panel surface is the canonical semantic token');
check(shellCss.includes('var(--sc-semantic-border-default)'), true, 'the shell dividers are the canonical semantic token');
check(shellCss.includes('var(--sc-touch-target-min)'), true, 'the shell touch targets use the shared touch-target contract');
check(shellCss.includes('width: 44px;'), false, 'the shell no longer hardcodes the touch-target size');
// The shell keeps a viewport-offset calculation so its floating surfaces clamp
// to narrow viewports. The clamp is the invariant; the concrete size step is a
// design-token decision the shell does not own, so it is not pinned here.
check(
  /width:\s*min\([^,;{}]+,\s*calc\(\s*100vw\s*-\s*[^)]+\)\s*\)/.test(shellCss),
  true,
  'the shell keeps its viewport-offset calculation',
);

// Capability markers the shell must keep: the adoption is presentation-only.
for (const kept of [
  '.workspace-activity-rail',
  '.workspace-scope-panel',
  '.published-apps',
  '.activity-tab',
  '.topbar--minimal',
]) {
  check(shellCss.includes(kept), true, `the shell keeps its ${kept} capability`);
}
check(shellCss.includes('inline-size: var(--sc-shell-sidebar-width)'), true, 'the desktop sidebar keeps its public width contract');
check(shellCss.includes('min-height: var(--sc-shell-topbar-height)'), true, 'the topbar keeps its shared height contract');

// ---------------------------------------------------------------------------
// Part 5 — the shell component keeps its runtime identity and panel modes
// ---------------------------------------------------------------------------
const shellVue = readSource('frontend/apps/web/src/layouts/AppShell.vue');
check(shellVue.includes('<ProductAppShell'), true, 'the shell renders through the official layout driver wrapper');
check(shellVue.includes(':data-layout-kind="activeLayout.kind"'), true, 'the shell publishes its layout kind');
check(shellVue.includes(':data-sidebar-mode="activeLayout.sidebar"'), true, 'the shell publishes its sidebar mode');
check(shellVue.includes(':data-header-mode="activeLayout.header"'), true, 'the shell publishes its header mode');
check(shellVue.includes("workspacePanelMode === 'catalog'"), true, 'the published-apps panel mode is kept');
check(shellVue.includes("workspacePanelMode === 'navigation'"), true, 'the business navigation panel mode is kept');
check(shellVue.includes("workspacePanelMode === 'company'"), true, 'the company panel mode is kept');
check(shellVue.includes("workspacePanelMode === 'record'"), true, 'the record-context panel mode is kept');
check(shellVue.includes("'project.project'"), false, 'the shell must not name a business model');
check(shellVue.includes("'sc.general.contract'"), false, 'the shell must not name a business model');

// ---------------------------------------------------------------------------
// Part 6 — the shell dimension aliases stay declared and honestly consumed
// ---------------------------------------------------------------------------
const patternCss = readSource('frontend/apps/web/src/styles/tokens/pattern.css');
for (const declared of [
  '--sc-shell-topbar-height:',
  '--sc-shell-sidebar-collapsed-width:',
  '--sc-shell-navigation-item-height:',
  '--sc-shell-page-gutter:',
]) {
  check(patternCss.includes(declared), true, `the shell alias stays declared: ${declared}`);
}
// The official shell composition consumes both shell dimensions: the header band
// (`--td-comp-size-xxxl` equivalent) and the compact rail (the official 64px
// `t-menu` collapsed width). They must be real consumers in the shell style.
for (const consumed of ['var(--sc-shell-topbar-height)', 'var(--sc-shell-sidebar-collapsed-width)']) {
  check(
    shellCss.includes(consumed) || shellVue.includes(consumed),
    true,
    `the adopted shell consumes the shared shell dimension ${consumed}`,
  );
}
// The remaining aliases are still reserved: adopting them requires a real
// consumer, not a placeholder reference.
for (const reserved of ['var(--sc-shell-navigation-item-height)', 'var(--sc-shell-page-gutter)']) {
  check(
    shellCss.includes(reserved) || shellVue.includes(reserved),
    false,
    `no shell surface fabricates a consumer for the reserved alias ${reserved}`,
  );
}

console.log(`[standard_shell_composition_test] PASS cases=${cases} layouts=${STANDARD_SHELL_COMPOSITION_LAYOUTS.length}`);
