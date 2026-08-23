import { reactive, ref } from 'vue';
import type { ContractV2Snapshot } from '../../app/contracts/v2';
import type { BusyKind, SubmissionFeedback, UiStatus } from './types';

export function useContractFormPageState() {
  return {
    status: ref<UiStatus>('loading'),
    isComponentActive: ref(true),
    instanceRouteIdentity: ref(''),
    retainedRouteIdentity: ref(''),
    renderErrorMessage: ref(''),
    recordMissing: ref(false),
    errorMessage: ref(''),
    loadError: reactive<{ status: number | null; reason: string; trace: string }>({ status: null, reason: '', trace: '' }),
    validationErrors: ref<string[]>([]),
    submissionFeedback: ref<SubmissionFeedback>(null),
    formConflict: ref(false),
    showOne2manyErrors: ref(false),
    busyKind: ref<BusyKind>(null),
    activeContractMode: ref(''),
    formSettingsActiveTab: ref<'structure' | 'fields' | 'details' | 'actions'>('fields'),
    contractModeFeedback: ref(''),
    contract: ref<ContractV2Snapshot | null>(null),
    contractMeta: ref<Record<string, unknown> | null>(null),
  };
}
