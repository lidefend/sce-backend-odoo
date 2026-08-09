import assert from 'node:assert/strict';
import {
  ACTION_SURFACE_RENDERER_REGISTRY,
  registeredActionSurfaceSemantics,
  resolveActionSurfaceRenderer,
} from '../src/app/renderers/actionSurfaceRendererRegistry';
import { resolveActionCollectionPresentation } from '../src/app/contracts/actionViewSurfaceContract';

const readySemantics = ['table', 'card', 'workflow_board', 'hierarchy_browser'];
const plannedSemantics = ['pivot', 'graph', 'calendar', 'gantt', 'activity', 'dashboard'];

assert.deepEqual(registeredActionSurfaceSemantics().sort(), [...readySemantics, ...plannedSemantics].sort());
readySemantics.forEach((semantic) => assert.equal(ACTION_SURFACE_RENDERER_REGISTRY[semantic]?.status, 'ready'));
plannedSemantics.forEach((semantic) => {
  const registration = ACTION_SURFACE_RENDERER_REGISTRY[semantic];
  assert.equal(registration?.status, 'fallback');
  assert.equal(registration?.activeRendererKey, 'core.readable_records');
  const presentation = resolveActionCollectionPresentation({ views: { [semantic]: { fields: ['id', 'name'] } } }, semantic);
  assert.equal(presentation.semantic, semantic);
  assert.equal(resolveActionSurfaceRenderer(presentation, semantic).requestedRendererKey, `core.${semantic}`);
});

const hierarchy = resolveActionSurfaceRenderer({
  semantic: 'hierarchy_browser', label: 'Hierarchy', groupField: '', groupedLanes: false, config: { tree: {} },
}, 'tree');
assert.equal(hierarchy.activeRendererKey, 'core.hierarchy_browser');
assert.equal(hierarchy.outlet, 'component');
assert.deepEqual(hierarchy.config, { tree: {} });

const unsupported = resolveActionSurfaceRenderer({
  semantic: 'unknown' as never, label: '', groupField: '', groupedLanes: false, config: {},
}, 'unknown');
assert.equal(unsupported.status, 'unsupported');
assert.equal(unsupported.activeRendererKey, 'core.unsupported');
assert.equal(unsupported.reasonCode, 'ACTION_SURFACE_RENDERER_NOT_REGISTERED');

console.log('[action-surface-renderer-registry] PASS');
