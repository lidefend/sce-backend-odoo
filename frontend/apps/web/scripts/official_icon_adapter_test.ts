import assert from 'node:assert/strict';
import { SC_ICON_COMPONENTS, SC_ICON_NAMES, resolveScIconComponent } from '../src/components/design-system/scIcon';

assert.equal(new Set(SC_ICON_NAMES).size, SC_ICON_NAMES.length, 'semantic icon names must be unique');
assert.deepEqual(Object.keys(SC_ICON_COMPONENTS).sort(), [...SC_ICON_NAMES].sort(), 'every semantic name must map exactly once');

for (const name of SC_ICON_NAMES) {
  const component = resolveScIconComponent(name) as { name?: string };
  assert.equal(component, SC_ICON_COMPONENTS[name], `${name} must resolve through the public map`);
  assert.match(String(component.name || ''), /Icon$/, `${name} must resolve to an official icon component`);
}

assert.equal((resolveScIconComponent('star') as { name?: string }).name, 'StarFilledIcon');
assert.equal((resolveScIconComponent('star-outline') as { name?: string }).name, 'StarIcon');
assert.equal((resolveScIconComponent('construction') as { name?: string }).name, 'ToolsIcon');

console.log(`[official_icon_adapter_test] PASS semantic=${SC_ICON_NAMES.length} source=tdesign-icons-vue-next`);
