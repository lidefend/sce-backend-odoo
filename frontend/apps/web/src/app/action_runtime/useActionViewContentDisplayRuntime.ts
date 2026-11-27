import { computed, type Ref } from 'vue';
import { resolveDeclaredKanbanTitleField } from '../runtime/actionViewKanbanTitleField';

type Dict = Record<string, unknown>;

type UseActionViewContentDisplayRuntimeOptions = {
  strictProjectionContract: Ref<Dict>;
  mapProjectionMetricItems: (items: unknown, fallbackPrefix: string) => Array<Record<string, unknown>>;
  kanbanTitleFieldHint: Ref<string>;
  kanbanFields: Ref<string[]>;
};

export function useActionViewContentDisplayRuntime(options: UseActionViewContentDisplayRuntimeOptions) {
  const ledgerOverviewItems = computed(() => {
    return options.mapProjectionMetricItems(options.strictProjectionContract.value.overview_strip, 'overview');
  });

  const listSummaryItems = computed(() => {
    return options.mapProjectionMetricItems(options.strictProjectionContract.value.summary_items, 'summary');
  });

  const kanbanTitleField = computed(() => resolveDeclaredKanbanTitleField(
    options.kanbanTitleFieldHint.value,
    options.kanbanFields.value,
  ));

  return {
    ledgerOverviewItems,
    listSummaryItems,
    kanbanTitleField,
  };
}

