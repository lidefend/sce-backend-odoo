import { computed, reactive, ref } from 'vue';
import {
  fetchProductSystemParameterCatalog,
  previewProductSystemParameter,
  publishProductSystemParameter,
  rollbackProductSystemParameter,
  type ProductSystemParameter,
  type ProductSystemParameterChange,
  type ProductSystemParameterMutationResult,
} from '../../api/productSystemParameter';
import {
  isProductSystemParameterGap,
  projectChangeRecord,
  projectImpactPreview,
  projectSystemParameterCatalog,
} from '../../app/productSystemParameterProjection';
import { useSessionStore } from '../../stores/session';

type Category = { key: string; label: string };

export function useSystemParameterCatalog() {
  const session = useSessionStore();
  const loading = ref(false);
  const error = ref('');
  const gap = ref('');
  const categories = ref<Category[]>([]);
  const parameters = ref<ProductSystemParameter[]>([]);
  const previewLoading = ref(false);
  const preview = ref<ReturnType<typeof projectImpactPreview> | null>(null);
  const previewError = ref('');
  const publishing = ref(false);
  const mutationError = ref('');
  const changes = ref<ProductSystemParameterChange[]>([]);
  const pendingValues = reactive(new Map<string, unknown>());
  let previewRevision = 0;

  function invalidatePreview() {
    previewRevision += 1;
    preview.value = null;
    previewError.value = '';
    previewLoading.value = false;
  }

  function currentValueFor(parameter: ProductSystemParameter): unknown {
    return pendingValues.has(parameter.key)
      ? pendingValues.get(parameter.key)
      : parameter.current_value ?? parameter.default;
  }

  function setValue(parameter: ProductSystemParameter, value: string) {
    pendingValues.set(parameter.key, value);
    invalidatePreview();
  }

  const byCategory = computed(() => {
    const map = new Map<string, ProductSystemParameter[]>();
    for (const parameter of parameters.value) {
      const rows = map.get(parameter.category) || [];
      rows.push(parameter);
      map.set(parameter.category, rows);
    }
    return map;
  });

  async function load() {
    if (!session.token) return;
    pendingValues.clear();
    invalidatePreview();
    loading.value = true;
    error.value = '';
    gap.value = '';
    try {
      const result = await fetchProductSystemParameterCatalog();
      const projected = projectSystemParameterCatalog(result);
      categories.value = projected.categories;
      parameters.value = projected.parameters;
    } catch (err) {
      parameters.value = [];
      categories.value = [];
      if (isProductSystemParameterGap(err)) {
        gap.value = String(err.message || '');
      } else {
        error.value = '系统参数目录暂时无法加载，请稍后重试。';
      }
    } finally {
      loading.value = false;
    }
  }

  async function previewFor(parameterKey: string, proposedValue: unknown) {
    const revision = ++previewRevision;
    previewLoading.value = true;
    previewError.value = '';
    preview.value = null;
    try {
      const result = await previewProductSystemParameter(parameterKey, proposedValue);
      if (revision !== previewRevision) return;
      preview.value = projectImpactPreview(result);
    } catch (err) {
      if (revision !== previewRevision) return;
      preview.value = null;
      previewError.value = isProductSystemParameterGap(err)
        ? String(err.message || '')
        : '影响预览暂时无法加载，请稍后重试。';
    } finally {
      if (revision === previewRevision) previewLoading.value = false;
    }
  }

  async function publish(parameterKey: string, proposedValue: unknown, reason: string) {
    publishing.value = true;
    mutationError.value = '';
    try {
      const result = await publishProductSystemParameter({
        parameter_key: parameterKey,
        proposed_value: proposedValue,
        change_reason: reason,
      });
      applyMutationResult(result);
      await load();
    } catch (err) {
      mutationError.value = isProductSystemParameterGap(err)
        ? String(err.message || '')
        : '参数发布失败，请稍后重试。';
    } finally {
      publishing.value = false;
    }
  }

  async function rollback(changeId: number) {
    publishing.value = true;
    mutationError.value = '';
    try {
      const result = await rollbackProductSystemParameter(changeId);
      applyMutationResult(result);
      await load();
    } catch (err) {
      mutationError.value = isProductSystemParameterGap(err)
        ? String(err.message || '')
        : '参数回滚失败，请稍后重试。';
    } finally {
      publishing.value = false;
    }
  }

  function applyMutationResult(result: ProductSystemParameterMutationResult) {
    try {
      const change = projectChangeRecord(result.change);
      changes.value = [change, ...changes.value.filter((row) => row.id !== change.id)].slice(0, 8);
      preview.value = null;
    } catch (err) {
      if (isProductSystemParameterGap(err)) mutationError.value = String(err.message || '');
    }
  }

  return {
    loading,
    error,
    gap,
    categories,
    parameters,
    byCategory,
    previewLoading,
    preview,
    previewError,
    publishing,
    mutationError,
    changes,
    currentValueFor,
    setValue,
    load,
    previewFor,
    publish,
    rollback,
  };
}
