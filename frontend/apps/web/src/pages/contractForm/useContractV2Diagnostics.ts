import { computed, type Ref } from 'vue';
import {
  collectContractV2FieldStatusByCode,
  resolveContractV2ContainerTree,
  resolveContractV2FormStructureContract,
  resolveContractV2GlobalStatus,
  resolveContractV2MainData,
  resolveContractV2SourceContext,
  resolveContractV2ValueSource,
  type ContractV2NormalizedStore,
} from '../../app/contracts/v2';

type DiagnosticLayoutNode = { kind: string; name: string; readonly: boolean };

export function useContractV2Diagnostics(input: {
  store: Ref<ContractV2NormalizedStore | null>;
  nativeLayoutCount: () => number;
  layoutNodes: () => DiagnosticLayoutNode[];
}) {
  const fieldCodes = computed(() => Array.from(input.store.value?.widgetsByFieldCode.keys() || []));
  const valueSource = computed(() => resolveContractV2ValueSource(input.store.value));
  const formStructureContract = computed(() => resolveContractV2FormStructureContract(input.store.value));

  return {
    formV2StoreReady: computed(() => Boolean(input.store.value)),
    formV2WidgetCount: computed(() => input.store.value?.widgetsById.size || 0),
    formV2ActionCount: computed(() => input.store.value?.actionsById.size || 0),
    formV2ButtonStatusCount: computed(() => input.store.value?.buttonStatusById.size || 0),
    formV2FieldCodeCount: computed(() => fieldCodes.value.length),
    formV2DescriptorCount: computed(() => fieldCodes.value.length),
    formV2AuthorityIssuePreview: computed(() => '-'),
    formV2FormStructureContract: formStructureContract,
    formV2FormStructureSlotCount: computed(() => {
      const slots = formStructureContract.value.slots;
      return Array.isArray(slots) ? slots.length : 0;
    }),
    formV2LayoutSourceKind: computed(() => {
      if (resolveContractV2ContainerTree(input.store.value).length) return 'v2_store';
      return input.nativeLayoutCount() ? 'v2_native_layout' : 'none';
    }),
    formV2GlobalSourceKind: computed(() => (
      resolveContractV2GlobalStatus(input.store.value) ? 'v2_store' : 'none'
    )),
    formV2SourceContextKind: computed(() => (
      Object.keys(resolveContractV2SourceContext(input.store.value)).length ? 'v2_store' : 'none'
    )),
    formV2StatusFieldCount: computed(() => Object.keys(collectContractV2FieldStatusByCode(input.store.value)).length),
    formV2ValueSourceKind: computed(() => valueSource.value.kind),
    formV2ValueFieldCount: computed(() => fieldCodes.value.filter((fieldCode) => (
      Object.prototype.hasOwnProperty.call(valueSource.value.values, fieldCode)
    )).length),
    formV2MainDataFieldCount: computed(() => fieldCodes.value.filter((fieldCode) => (
      Object.prototype.hasOwnProperty.call(resolveContractV2MainData(input.store.value), fieldCode)
    )).length),
    formV2ReadonlyValueCount: computed(() => input.layoutNodes().filter((node) => (
      node.kind === 'field'
      && node.readonly
      && Boolean(input.store.value?.widgetsByFieldCode.has(node.name))
      && Object.prototype.hasOwnProperty.call(valueSource.value.values, node.name)
    )).length),
  };
}
