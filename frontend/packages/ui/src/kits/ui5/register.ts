import './bootstrap';
import '@ui5/webcomponents/dist/Button.js';
import '@ui5/webcomponents/dist/DatePicker.js';
import '@ui5/webcomponents/dist/Input.js';
import '@ui5/webcomponents/dist/Option.js';
import '@ui5/webcomponents/dist/Select.js';
import '@ui5/webcomponents/dist/Tab.js';
import '@ui5/webcomponents/dist/TabContainer.js';
import '@ui5/webcomponents/dist/TextArea.js';
import '@ui5/webcomponents-fiori/dist/DynamicPage.js';
import '@ui5/webcomponents-fiori/dist/DynamicPageHeader.js';
import '@ui5/webcomponents-fiori/dist/DynamicPageTitle.js';
import type { ScenePrimitiveId, SceneUiDriverRuntime } from '../types';

const enterpriseLoaders: Partial<Record<ScenePrimitiveId, () => Promise<unknown>>> = {
  alert: () => import('./primitives/alert'),
  drawer: () => import('./primitives/drawer'),
  table: () => import('./primitives/table'),
};
const enterpriseCache = new Map<ScenePrimitiveId, Promise<unknown>>();

async function ensurePrimitive(primitive: ScenePrimitiveId): Promise<void> {
  const loader = enterpriseLoaders[primitive];
  if (!loader) return;
  let pending = enterpriseCache.get(primitive);
  if (!pending) {
    pending = loader();
    enterpriseCache.set(primitive, pending);
  }
  await pending;
}

export const ui5Runtime: SceneUiDriverRuntime = {
  id: 'ui5-horizon',
  componentModel: 'web-components',
  components: {},
  ensurePrimitive,
};
