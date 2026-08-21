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

export function useContractV2ShadowDiagnostics(input: {
  store: Ref<ContractV2NormalizedStore | null>;
  legacyFields: () => Record<string, unknown>;
  nativeLayoutCount: () => number;
  layoutNodes: () => DiagnosticLayoutNode[];
}) {
  const fieldCodes = computed(() => Array.from(input.store.value?.widgetsByFieldCode.keys() || []));
  const valueSource = computed(() => resolveContractV2ValueSource(input.store.value));
  const missingLegacyFields = computed(() => fieldCodes.value.filter((fieldCode) => (
    !(fieldCode in input.legacyFields())
  )));
  const formStructureContract = computed(() => resolveContractV2FormStructureContract(input.store.value));

  return {
    v2ShadowStoreReady: computed(() => Boolean(input.store.value)),
    v2ShadowWidgetCount: computed(() => input.store.value?.widgetsById.size || 0),
    v2ShadowActionCount: computed(() => input.store.value?.actionsById.size || 0),
    v2ShadowButtonStatusCount: computed(() => input.store.value?.buttonStatusById.size || 0),
    v2ShadowFieldCodeCount: computed(() => fieldCodes.value.length),
    v2ShadowLegacyFieldOverlapCount: computed(() => fieldCodes.value.length - missingLegacyFields.value.length),
    v2ShadowLegacyFieldMissingPreview: computed(() => missingLegacyFields.value.slice(0, 8).join(',') || '-'),
    v2ShadowFormStructureContract: formStructureContract,
    v2ShadowFormStructureSlotCount: computed(() => {
      const slots = formStructureContract.value.slots;
      return Array.isArray(slots) ? slots.length : 0;
    }),
    v2ShadowLayoutSourceKind: computed(() => {
      if (resolveContractV2ContainerTree(input.store.value).length) return 'v2_store';
      return input.nativeLayoutCount() ? 'legacy_layout' : 'none';
    }),
    v2ShadowGlobalSourceKind: computed(() => (
      resolveContractV2GlobalStatus(input.store.value) ? 'v2_store' : 'legacy_resolver'
    )),
    v2ShadowSourceContextKind: computed(() => (
      Object.keys(resolveContractV2SourceContext(input.store.value)).length ? 'v2_store' : 'legacy_resolver'
    )),
    v2ShadowStatusFieldCount: computed(() => Object.keys(collectContractV2FieldStatusByCode(input.store.value)).length),
    v2ShadowValueSourceKind: computed(() => valueSource.value.kind),
    v2ShadowValueFieldCount: computed(() => fieldCodes.value.filter((fieldCode) => (
      Object.prototype.hasOwnProperty.call(valueSource.value.values, fieldCode)
    )).length),
    v2ShadowMainDataFieldCount: computed(() => fieldCodes.value.filter((fieldCode) => (
      Object.prototype.hasOwnProperty.call(resolveContractV2MainData(input.store.value), fieldCode)
    )).length),
    v2ShadowReadonlyValueCount: computed(() => input.layoutNodes().filter((node) => (
      node.kind === 'field'
      && node.readonly
      && Boolean(input.store.value?.widgetsByFieldCode.has(node.name))
      && Object.prototype.hasOwnProperty.call(valueSource.value.values, node.name)
    )).length),
  };
}
