import type { Ref } from 'vue';
import type { ContractV2NormalizedStore } from '../contracts/v2';
import { loadActionContractStore } from '../../api/contract';
import { intentRequest } from '../../api/intents';
import { saveActionViewSearchFavorite } from './actionViewDataRuntime';
import {
  settleSavedSearchDeletion,
  settleSavedSearchSubmission,
  type SavedSearchDeleteAction,
} from './savedSearchSubmission';

type ReadRef<T> = { readonly value: T };

type SavedFilterChip = {
  key?: string;
  deleteAction?: SavedSearchDeleteAction | null;
};

type FavoriteCapabilities = {
  favoriteSaveEnabled?: boolean;
  favoriteSharedEnabled?: boolean;
};

type FavoritePayload = { name: string; isDefault?: boolean; isShared?: boolean };

export function useActionViewFavoriteRuntime(options: {
  actionId: ReadRef<number>;
  actionContract: Ref<ContractV2NormalizedStore | null>;
  sceneKey: ReadRef<string>;
  menuId: ReadRef<number>;
  activeSavedFilterKey: ReadRef<string>;
  resolvedModelRef: ReadRef<string>;
  model: ReadRef<string>;
  sortValue: ReadRef<string>;
  customSearchCapabilities: ReadRef<FavoriteCapabilities>;
  contractSavedFilterChips: ReadRef<SavedFilterChip[]>;
  clearSavedFilter: () => void;
  requestLoadPage: () => Promise<void> | void;
  resolveEffectiveFilterDomain: () => unknown[];
  resolveEffectiveRequestContext: () => Record<string, unknown>;
}) {
  async function reloadContract(sourceActionId: number, sourceContract: unknown): Promise<void> {
    if (options.actionId.value !== sourceActionId || options.actionContract.value !== sourceContract) return;
    const refreshed = await loadActionContractStore(sourceActionId, {
      sceneKey: options.sceneKey.value || undefined,
      menuId: options.menuId.value || undefined,
    });
    if (options.actionId.value !== sourceActionId || options.actionContract.value !== sourceContract) return;
    options.actionContract.value = refreshed;
    await options.requestLoadPage();
  }

  async function handleDeleteFavorite(id: number) {
    const chip = options.contractSavedFilterChips.value.find((row) => row?.deleteAction?.params.filter_id === id);
    const action = chip?.deleteAction;
    if (!action) return { deleted: false, message: '当前页面未允许删除此收藏，请刷新后重试。' };
    const sourceActionId = options.actionId.value;
    const sourceContract = options.actionContract.value;
    return settleSavedSearchDeletion(async () => {
      const result = await intentRequest<{ deleted: boolean; id: number }>({ intent: action.intent, params: action.params });
      if (result.deleted !== true || result.id !== id) throw new Error('SAVED_SEARCH_DELETE_OUTCOME_MISMATCH');
    }, async () => {
      if (options.actionId.value !== sourceActionId || options.actionContract.value !== sourceContract) return;
      if (options.activeSavedFilterKey.value === chip?.key) options.clearSavedFilter();
      await reloadContract(sourceActionId, sourceContract);
    });
  }

  async function handleSaveFavorite(payload: FavoritePayload) {
    const targetModel = String(options.resolvedModelRef.value || options.model.value || '').trim();
    const name = String(payload.name || '').trim();
    if (!targetModel || !name || !options.customSearchCapabilities.value.favoriteSaveEnabled) return { saved: false, message: '当前页面不允许保存收藏' };
    const sourceActionId = options.actionId.value;
    const sourceContract = options.actionContract.value;
    return settleSavedSearchSubmission(() => saveActionViewSearchFavorite({
      model: targetModel,
      name,
      domain: options.resolveEffectiveFilterDomain(),
      context: options.resolveEffectiveRequestContext(),
      order: options.sortValue.value,
      action_id: options.actionId.value,
      is_default: payload.isDefault === true,
      is_shared: payload.isShared === true && options.customSearchCapabilities.value.favoriteSharedEnabled === true,
    }), async () => {
      if (options.actionId.value !== sourceActionId || options.actionContract.value !== sourceContract) return;
      await reloadContract(sourceActionId, sourceContract);
    });
  }

  return { handleDeleteFavorite, handleSaveFavorite };
}
