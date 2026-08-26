import type { Ref } from 'vue';
import type { SceneListProfile } from '../resolvers/sceneRegistry';
import { resolveCollectionStatusPresentation } from '../presentation/collectionStatusPresentation';

type ListColumnMetricOption = {
  name: string;
  selection?: Array<{ value: string; label: string }>;
  toneByValue?: Record<string, string>;
};

export function useActionViewCollectionMetricRuntime(options: {
  listProfile: Ref<SceneListProfile | null>;
  listColumnOptions: Ref<ListColumnMetricOption[]>;
}) {
  function metricFields() {
    const fields = Array.isArray(options.listProfile.value?.metric_fields)
      ? options.listProfile.value?.metric_fields || []
      : [];
    return fields.map((item) => String(item || '').trim()).filter(Boolean);
  }

  function resolveCollectionStateCell(row: Record<string, unknown>) {
    const statusField = String(options.listProfile.value?.status_field || '').trim();
    if (!statusField) return { text: '', tone: 'neutral' };
    const column = options.listColumnOptions.value.find((item) => item.name === statusField);
    const status = resolveCollectionStatusPresentation({
      value: row[statusField],
      selection: column?.selection,
      toneByValue: column?.toneByValue,
    });
    return {
      text: status.label,
      tone: status.tone,
    };
  }

  function resolveCollectionAmount(row: Record<string, unknown>) {
    for (const field of metricFields()) {
      const candidate = row[field];
      const amount = Number(candidate);
      if (Number.isFinite(amount) && amount > 0) return amount;
    }
    return 0;
  }

  function isCompletedState(_stateText: string, tone: string) {
    return tone === 'success';
  }

  return {
    metricFields,
    resolveCollectionStateCell,
    resolveCollectionAmount,
    isCompletedState,
  };
}
