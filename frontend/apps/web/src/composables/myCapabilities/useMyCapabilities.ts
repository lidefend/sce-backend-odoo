import { computed, ref } from 'vue';
import type { UserCapabilityItem } from '../../api/productCapabilityCatalog';
import {
  isProductCapabilityCatalogGap,
  projectUserCapabilities,
} from '../../app/productCapabilityCatalogProjection';
import { useSessionStore } from '../../stores/session';

export function useMyCapabilities() {
  const session = useSessionStore();
  const loading = ref(false);
  const error = ref('');
  const gap = ref('');
  const emptyMessage = ref('');
  const capabilities = ref<UserCapabilityItem[]>([]);

  const byEntry = computed(() => {
    const map = new Map<string, UserCapabilityItem[]>();
    for (const row of capabilities.value) {
      const key = row.entry;
      const rows = map.get(key) || [];
      rows.push(row);
      map.set(key, rows);
    }
    return map;
  });

  async function load() {
    if (!session.token) return;
    loading.value = true;
    error.value = '';
    gap.value = '';
    try {
      await session.loadProductCapabilityCatalog();
      const surface = projectUserCapabilities(session.productCapabilityCatalog);
      capabilities.value = surface.items;
      emptyMessage.value = surface.empty_message;
    } catch (err) {
      capabilities.value = [];
      if (isProductCapabilityCatalogGap(err)) {
        gap.value = String(err.message || '');
      } else {
        error.value = '能力清单暂时无法加载，请稍后重试。';
      }
    } finally {
      loading.value = false;
    }
  }

  return {
    loading,
    error,
    gap,
    capabilities,
    emptyMessage,
    byEntry,
    load,
  };
}
