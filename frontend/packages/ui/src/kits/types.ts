import type { Component } from 'vue';

export type SceneUiKitId = 'sc-native' | 'tdesign-modern' | 'ui5-horizon';
export type SceneUiDensity = 'compact' | 'cozy';
export type SceneComponentModel = 'native' | 'vue' | 'web-components';
export type ScenePrimitiveId =
  | 'alert'
  | 'button'
  | 'date'
  | 'drawer'
  | 'input'
  | 'select'
  | 'table'
  | 'tab-panel'
  | 'tabs'
  | 'textarea';

export interface SceneUiDriverRuntime {
  id: SceneUiKitId;
  componentModel: SceneComponentModel;
  components: Partial<Record<ScenePrimitiveId, Component>>;
  ensurePrimitive?: (primitive: ScenePrimitiveId) => Promise<void>;
}

export interface SceneUiKitDescriptor {
  id: SceneUiKitId;
  label: string;
  vendor: string;
  capabilities: readonly string[];
}

export const SCENE_UI_KITS: Record<SceneUiKitId, SceneUiKitDescriptor> = {
  'sc-native': {
    id: 'sc-native',
    label: '现有基础组件',
    vendor: 'SC',
    capabilities: ['page-frame', 'button', 'input', 'select', 'date', 'textarea', 'tabs', 'alert', 'table', 'drawer'],
  },
  'tdesign-modern': {
    id: 'tdesign-modern',
    label: '现代商务',
    vendor: 'TDesign Vue Next',
    capabilities: ['page-frame', 'button', 'input', 'select', 'date', 'textarea', 'tabs', 'alert', 'table', 'drawer'],
  },
  'ui5-horizon': {
    id: 'ui5-horizon',
    label: '专业流程',
    vendor: 'SAP UI5 Web Components',
    capabilities: ['page-frame', 'button', 'input', 'select', 'date', 'textarea', 'tabs', 'alert', 'table', 'drawer'],
  },
};
