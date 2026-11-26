import { computed, type Ref } from 'vue';
import {
  COLLECTION_SCOPE,
  resolveSurfaceCapabilities,
  type CollectionCapabilities,
} from '../runtime/actionViewCollectionCapabilityRuntime';

type CollectionImportWizard = {
  open: (options: { model: string; context: Record<string, unknown>; buildIdempotencyKey: (file: File) => string })
    => Promise<import('../../api/data').ApiDataImportContract | null>;
};

type UseActionViewCollectionActionRuntimeOptions = {
  /** The contract's single declared action list; this surface reads its scope. */
  capabilities: Readonly<Ref<CollectionCapabilities>>;
  busy: Ref<boolean>;
  message: Ref<string>;
  importWizardRef: Readonly<Ref<CollectionImportWizard | null>>;
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
    options.busy.value = true;
    try {
      const wizard = options.importWizardRef.value;
      if (!wizard) throw new Error('原生导入向导尚未就绪');
      const result = await wizard.open({ model, context: options.resolveEffectiveRequestContext(),
        buildIdempotencyKey: file => options.buildIdempotencyKey('import', [], {
          file_name: file.name, file_size: file.size, file_last_modified: file.lastModified,
        }) });
      if (result) {
        options.message.value = options.text('collection_msg_import_done', `已导入 ${result.imported_count} 条记录`);
        await options.reload();
      }
    } catch (error) {
      options.message.value = error instanceof Error ? error.message : String(error);
    } finally { options.busy.value = false; }
  }

  return {
    collectionActions,
    handleCollectionAction,
  };
}
