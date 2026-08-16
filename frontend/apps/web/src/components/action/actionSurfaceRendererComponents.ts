import { defineAsyncComponent, type Component } from 'vue';
import HierarchyBrowser from './HierarchyBrowser.vue';
import HierarchyPlanner from './HierarchyPlanner.vue';
import HierarchicalWorksheet from './HierarchicalWorksheet.vue';
import UnsupportedActionSurface from './UnsupportedActionSurface.vue';

export const ACTION_SURFACE_RENDERER_COMPONENTS: Readonly<Record<string, Component>> = Object.freeze({
  'core.scene_collection': defineAsyncComponent(() => import('./SceneReadonlyCollectionRenderer.vue')),
  'core.hierarchy_browser': HierarchyBrowser,
  'core.hierarchy_planner': HierarchyPlanner,
  'core.hierarchical_worksheet': HierarchicalWorksheet,
  'core.unsupported': UnsupportedActionSurface,
});
