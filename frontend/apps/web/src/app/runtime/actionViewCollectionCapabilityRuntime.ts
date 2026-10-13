import { fileToBase64 } from '../../api/files';
import type { ApiDataImportContract } from '../../api/data';
import {
  ContractGapError,
  requireDeclaredBoolean,
  requireDeclaredText,
} from '../contract/contractGap';
import { importActionViewRecords } from './actionViewDataRuntime';

/**
 * The list surface publishes one declared action list
 * (`actionContract.surfacePolicies.collection_capabilities.actions`).  Each
 * declared action carries the facts a consumer must not invent for itself:
 *
 * - `scope` — `selection` actions operate on the chosen rows and belong to the
 *   selection bar; `collection` actions operate on the collection itself and are
 *   reachable with an empty selection (today: `import`).
 * - `intent` — the intent the backend executes the action through.
 *
 * This module is the single resolver for that declaration.  It routes a declared
 * action to its surface from the declaration and maps the declared intent onto an
 * executor this build actually has; an action whose intent this build cannot
 * execute stays visible and is reported unresolved instead of being guessed at
 * or silently dropped.
 */
export const SELECTION_SCOPE = 'selection';
export const COLLECTION_SCOPE = 'collection';

/** The layer that owes any declaration this surface finds missing. */
const DECLARATION_LAYER = 'P0:smart_core:contract_governance_list_surface|contract_governance_user_surface';

export type DeclaredCapability = {
  action: string;
  scope: string;
  intent: string;
  available: boolean;
};

export type CollectionCapabilities = { enabled: boolean; actions: DeclaredCapability[] };

export type SurfaceCapabilityAction = {
  key: string;
  action: string;
  scope: string;
  intent: string;
  executor: string;
  label: string;
  enabled: boolean;
  hint: string;
};

/**
 * What this client build can actually run, keyed by the *declared intent*.  This
 * is a client capability table, so it names executors rather than business
 * actions: a contract that declares a new action reaches the client through its
 * intent, and one whose intent this build cannot execute is reported unresolved.
 */
export const DECLARED_CAPABILITY_EXECUTORS: Record<string, string> = Object.freeze({
  'api.data': 'export_csv',
  'api.data.batch': 'batch_write',
  'api.data.unlink': 'unlink',
  'api.data.import': 'import_records',
});

export const CAPABILITY_LABELS: Record<string, [string, string]> = Object.freeze({
  import: ['collection_label_import', '批量导入'],
  export: ['batch_label_export', '导出所选'],
  delete: ['batch_label_delete', '批量删除'],
  activate: ['batch_label_activate', '批量激活'],
  archive: ['batch_label_archive', '批量归档'],
});

function asDict(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

/**
 * Read the declared action list.  The declaration is the only source: a payload
 * that publishes a collection policy without it is a contract defect, and the
 * surface stops instead of rebuilding the declaration on the client.  A client
 * rebuild could only tag every action as selection-scope, so it would silently
 * drop the collection-scope actions the contract declared.
 */
export function resolveDeclaredCapabilities(surfacePolicies: unknown): CollectionCapabilities {
  const policies = asDict(surfacePolicies);
  if (!('collection_capabilities' in policies)) {
    if (declaresCollectionPolicy(policies)) {
      throw new ContractGapError(
        {
          kind: 'contract_defect',
          missing: 'actionContract.surfacePolicies.collection_capabilities',
          requiredDeclarationLayer: DECLARATION_LAYER,
        },
        '契约声明了集合面策略却没有声明 collection_capabilities：前端不重建动作声明，等待声明层补齐',
      );
    }
    return { enabled: false, actions: [] };
  }
  const raw = asDict(policies.collection_capabilities);
  const enabled = requireDeclaredBoolean(raw.enabled, {
    missing: 'actionContract.surfacePolicies.collection_capabilities.enabled',
    requiredDeclarationLayer: DECLARATION_LAYER,
  });
  if (!Array.isArray(raw.actions)) {
    throw new ContractGapError(
      {
        kind: 'contract_defect',
        missing: 'actionContract.surfacePolicies.collection_capabilities.actions',
        requiredDeclarationLayer: DECLARATION_LAYER,
      },
      '契约声明了 collection_capabilities 却没有声明 actions 数组：合法的空集合必须显式声明为 []，前端不代声明层补空表',
    );
  }
  // A declared entry is consumed whole or not at all.  Skipping an entry that
  // omits `action`/`scope` used to drop a business action silently, which is
  // indistinguishable from a contract that never declared it.
  const actions = raw.actions.map((row, index) => {
    const path = `actionContract.surfacePolicies.collection_capabilities.actions[${index}]`;
    const entry = asDict(row);
    const action = asText(entry.action).toLowerCase();
    if (!action) {
      throw new ContractGapError(
        {
          kind: 'contract_defect',
          missing: `${path}.action`,
          requiredDeclarationLayer: DECLARATION_LAYER,
        },
        '契约声明了集合动作条目却没有声明 action：前端不静默丢弃该动作，等待声明层补齐',
      );
    }
    const scope = asText(entry.scope).toLowerCase();
    if (scope !== SELECTION_SCOPE && scope !== COLLECTION_SCOPE) {
      throw new ContractGapError(
        {
          kind: 'contract_defect',
          missing: `${path}.scope`,
          requiredDeclarationLayer: DECLARATION_LAYER,
        },
        `契约声明的集合动作 ${action} 缺少合法 scope（${SELECTION_SCOPE}|${COLLECTION_SCOPE}）：前端不猜测动作归属面`,
      );
    }
    return {
      action,
      scope,
      intent: requireDeclaredText(entry.intent, {
        missing: `${path}.intent`,
        requiredDeclarationLayer: DECLARATION_LAYER,
      }),
      available: requireDeclaredBoolean(entry.available, {
        missing: `${path}.available`,
        requiredDeclarationLayer: DECLARATION_LAYER,
      }),
    } satisfies DeclaredCapability;
  });
  return { enabled, actions };
}

/** Does this payload publish a collection policy that must carry a declaration? */
function declaresCollectionPolicy(policies: Record<string, unknown>): boolean {
  return ['batch_policy', 'selection_policy'].some(
    (key) => Object.keys(asDict(policies[key])).length > 0,
  );
}

/**
 * The declared selection capability (`surfacePolicies.selection_policy.enabled`),
 * consumed verbatim.  Selection is a business capability: a payload that
 * publishes surface policies without it is a contract defect, and a payload that
 * publishes no surface policy declares no collection surface at all.
 */
export function resolveDeclaredSelectionCapability(surfacePolicies: unknown): boolean {
  const policies = asDict(surfacePolicies);
  if (!('selection_policy' in policies)) {
    if (declaresCollectionPolicy(policies)) {
      throw new ContractGapError(
        {
          kind: 'contract_defect',
          missing: 'actionContract.surfacePolicies.selection_policy',
          requiredDeclarationLayer: DECLARATION_LAYER,
        },
        '契约声明了集合面策略却没有声明 selection_policy：前端不补默认能力，等待声明层补齐',
      );
    }
    return false;
  }
  return requireDeclaredBoolean(asDict(policies.selection_policy).enabled, {
    missing: 'actionContract.surfacePolicies.selection_policy.enabled',
    requiredDeclarationLayer: DECLARATION_LAYER,
  });
}

/** The declared actions of one scope, resolved against this build's executors. */
export function resolveSurfaceCapabilities(
  capabilities: CollectionCapabilities | null | undefined,
  scope: string,
  text: (key: string, fallback: string) => string,
): SurfaceCapabilityAction[] {
  const rows = Array.isArray(capabilities?.actions) ? capabilities!.actions : [];
  return rows
    .filter((entry) => entry.scope === scope)
    .map((entry) => {
      const executor = asText(DECLARED_CAPABILITY_EXECUTORS[entry.intent]);
      const declared = entry.available;
      const executable = Boolean(entry.intent && executor);
      const [labelKey, labelFallback] = CAPABILITY_LABELS[entry.action] || ['', ''];
      const enabled = declared && executable;
      return {
        key: `${scope === SELECTION_SCOPE ? 'batch' : 'collection'}:${entry.action}`,
        action: entry.action,
        scope: entry.scope,
        intent: entry.intent,
        executor,
        label: labelKey ? text(labelKey, labelFallback) : entry.action,
        enabled,
        hint: enabled
          ? ''
          : declared
            ? text('capability_hint_execution_unresolved', '该操作未声明执行方式，暂不可用')
            : text('capability_hint_unavailable', '当前状态下该操作不可用'),
      };
    });
}

export type CollectionImportSummary = {
  fileName: string;
  rowCount: number;
  mappedFieldCount: number;
};

/** Open the platform file picker; returns null when the user cancels. */
export function pickImportFile(accept = '.csv,.xls,.xlsx,.ods'): Promise<File | null> {
  if (typeof document === 'undefined') return Promise.resolve(null);
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.style.display = 'none';
    input.addEventListener('change', () => {
      const file = input.files && input.files[0] ? input.files[0] : null;
      input.remove();
      resolve(file);
    });
    input.addEventListener('cancel', () => {
      input.remove();
      resolve(null);
    });
    document.body.appendChild(input);
    input.click();
  });
}

function importMessage(summary: ApiDataImportContract, limit = 3): string {
  const messages = Array.isArray(summary?.messages) ? summary.messages : [];
  return messages
    .slice(0, limit)
    .map((row) => String(row?.message || '').trim())
    .filter(Boolean)
    .join('；');
}

/**
 * The declared collection-scope import: read the file, let the backend kernel
 * match columns to fields and validate every row without writing, confirm with
 * the user, then execute the same mapping once.
 */
export async function executeActionViewCollectionImport(options: {
  model: string;
  file: File;
  context: Record<string, unknown>;
  idempotencyKey: string;
  text: (key: string, fallback: string) => string;
  setBusy: (busy: boolean) => void;
  confirm: (summary: CollectionImportSummary) => Promise<boolean>;
  onSuccess: (result: ApiDataImportContract) => void | Promise<void>;
  onFailure: (message: string) => void;
}): Promise<void> {
  options.setBusy(true);
  try {
    const { data: fileBase64, mimetype } = await fileToBase64(options.file);
    const request = {
      model: options.model,
      fileName: options.file.name,
      fileBase64,
      fileType: mimetype,
      context: options.context,
      idempotencyKey: options.idempotencyKey,
    };
    const preview = await importActionViewRecords({ ...request, dryRun: true });
    if (Number(preview?.error_count || 0) > 0) {
      const detail = importMessage(preview);
      options.onFailure(
        detail
          ? options.text('collection_msg_import_invalid', `导入预校验未通过：${detail}`)
          : options.text('collection_msg_import_invalid_plain', '导入预校验未通过，请检查文件内容'),
      );
      return;
    }
    const mapping = Array.isArray(preview?.mapping) ? preview.mapping : [];
    const summary: CollectionImportSummary = {
      fileName: options.file.name,
      rowCount: Number(preview?.file_length || 0),
      mappedFieldCount: mapping.filter(Boolean).length,
    };
    if (!await options.confirm(summary)) return;
    const result = await importActionViewRecords({
      ...request,
      fields: mapping,
      columns: Array.isArray(preview?.headers) ? preview.headers : [],
      dryRun: false,
    });
    await options.onSuccess(result);
  } catch (err) {
    const message = err instanceof Error && err.message
      ? err.message
      : options.text('collection_msg_import_failed', '导入失败，请稍后重试');
    options.onFailure(message);
  } finally {
    options.setBusy(false);
  }
}
