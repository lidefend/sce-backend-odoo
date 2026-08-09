import type { Component } from 'vue';
import HierarchyBrowser from './HierarchyBrowser.vue';
import HierarchicalWorksheet from './HierarchicalWorksheet.vue';
import UnsupportedActionSurface from './UnsupportedActionSurface.vue';

export const ACTION_SURFACE_RENDERER_COMPONENTS: Readonly<Record<string, Component>> = Object.freeze({
  'core.hierarchy_browser': HierarchyBrowser,
  'core.hierarchical_worksheet': HierarchicalWorksheet,
  'core.unsupported': UnsupportedActionSurface,
});
