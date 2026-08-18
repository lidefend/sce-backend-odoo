import type { Ref } from 'vue';
import {
  clearIntakeAutosavePayload,
  persistIntakeAutosavePayload,
  restoreIntakeAutosavePayload,
} from './intakeAutosave';

export function useIntakeAutosaveRuntime(options: {
  key: Ref<string>;
  hasRecord: Ref<unknown>;
  formData: Record<string, unknown>;
  fields: Ref<string[]>;
}) {
  const persist = () => {
    const key = options.key.value;
    if (!key || options.hasRecord.value) return;
    persistIntakeAutosavePayload(key, options.formData, options.fields.value);
  };
  const restore = () => {
    const key = options.key.value;
    if (!key || options.hasRecord.value) return;
    Object.entries(restoreIntakeAutosavePayload(key, options.fields.value)).forEach(([field, value]) => {
      options.formData[field] = value as never;
    });
  };
  const clear = () => {
    const key = options.key.value;
    if (!key) return;
    clearIntakeAutosavePayload(key);
  };
  return { persist, restore, clear };
}
