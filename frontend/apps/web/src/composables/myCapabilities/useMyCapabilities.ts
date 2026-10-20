import { computed, ref } from 'vue';
import type { ProductCapabilityItem } from '../../api/productCapabilityCatalog';
import {
  isProductCapabilityCatalogGap,
  projectCapabilities,
} from '../../app/productCapabilityCatalogProjection';
import { useSessionStore } from '../../stores/session';

export function useMyCapabilities() {
  const session = useSessionStore();
  const loading = ref(false);
  const error = ref('');
  const gap = ref('');
  const capabilities = ref<ProductCapabilityItem[]>([]);

  const byEntry = computed(() => {
    const map = new Map<string, ProductCapabilityItem[]>();
    for (const row of capabilities.value) {
      const key = row.entry || row.audience || 'other';
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
      capabilities.value = projectCapabilities(session.productCapabilityCatalog);
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
    byEntry,
    load,
  };
}
