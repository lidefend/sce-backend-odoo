import { computed, type Ref } from 'vue';
import {
  COLLECTION_SCOPE,
  executeActionViewCollectionImport,
  pickImportFile,
  resolveSurfaceCapabilities,
  type CollectionCapabilities,
  type CollectionImportSummary,
} from '../runtime/actionViewCollectionCapabilityRuntime';

type CollectionConfirmation = {
  confirm: (options: { actionLabel: string; message: string }) => Promise<boolean>;
};

type UseActionViewCollectionActionRuntimeOptions = {
  /** The contract's single declared action list; this surface reads its scope. */
  capabilities: Readonly<Ref<CollectionCapabilities>>;
  busy: Ref<boolean>;
  message: Ref<string>;
  confirmationRef: Readonly<Ref<CollectionConfirmation | null>>;
  text: (key: string, fallback: string) => string;
  resolveTargetModel: () => string;
  resolveEffectiveRequestContext: () => Record<string, unknown>;
  buildIdempotencyKey: (action: string, ids: number[], extra: Record<string, unknown>) => string;
  reload: () => Promise<unknown>;
};

/**
 * The collection surface of a collection: the actions the contract declares with
 * the `collection` scope, which are reachable without a row selection (today:
 * import).
 *
 * This runtime routes each declared action from its declared scope and looks up
 * the executor for its declared intent. It never decides that an action exists,
 * which surface it belongs to, or whether a business rule allows it.
 */
export function useActionViewCollectionActionRuntime(
  options: UseActionViewCollectionActionRuntimeOptions,
) {
  const collectionActions = computed(() =>
    resolveSurfaceCapabilities(options.capabilities.value, COLLECTION_SCOPE, options.text),
  );

  function handleCollectionAction(key: string) {
    const action = key.startsWith('collection:') ? key.slice('collection:'.length) : '';
    if (!action) return;
    const declaration = collectionActions.value.find((row) => row.action === action);
    if (!declaration || !declaration.enabled) {
      options.message.value = declaration?.hint
        || options.text('capability_hint_execution_unresolved', '该操作未声明执行方式，暂不可用');
      return;
    }
    if (declaration.executor === 'import_records') {
      void runImport();
    }
  }

  async function runImport() {
    const model = options.resolveTargetModel();
    if (!model) {
      options.message.value = options.text('collection_msg_missing_model', '当前场景无法确定业务对象，暂不能导入');
      return;
    }
    const file = await pickImportFile();
    if (!file) return;
    const idempotencyKey = options.buildIdempotencyKey('import', [], {
      file_name: file.name,
      file_size: file.size,
      file_last_modified: file.lastModified,
    });
    await executeActionViewCollectionImport({
      model,
      file,
      context: options.resolveEffectiveRequestContext(),
      idempotencyKey,
      text: options.text,
      setBusy: (busy) => { options.busy.value = busy; },
      confirm: (summary: CollectionImportSummary) => {
        const confirmation = options.confirmationRef.value;
        if (!confirmation) return Promise.resolve(false);
        const message = options.text(
          'collection_confirm_import',
          `将导入文件 ${summary.fileName}，共 ${summary.rowCount} 行、匹配 ${summary.mappedFieldCount} 个字段，确认执行？`,
        );
        return confirmation.confirm({ actionLabel: options.text('collection_label_import', '批量导入'), message });
      },
      onSuccess: async (result) => {
        options.message.value = options.text(
          'collection_msg_import_done',
          `已导入 ${Number(result?.imported_count || 0)} 条记录`,
        );
        await options.reload();
      },
      onFailure: (message) => { options.message.value = message; },
    });
  }

  return {
    collectionActions,
    handleCollectionAction,
  };
}
