import { intentRequestRaw } from './intents';
import { ApiError } from './client';
import { extractLiteContractFromIntentBody } from '../app/runtime/unifiedPageContractLitePilot';
import type { UnifiedPageContractLite } from '../app/contracts/unifiedPageContractLite';
import { LITE_PREVIEW_LEGACY_FALLBACK_MODE } from '../app/contracts/unifiedPageContractLiteCompat';
import type { UnifiedPageContractV2 } from '../app/contracts/unifiedPageContractV2';
import { loadActionContractV2, loadModelContractV2 } from '../app/contracts/v2/client';

type LoadActionContractOptions = {
  sceneKey?: string | null;
  viewId?: number | null;
  menuId?: number | null;
  viewType?: 'form' | 'tree' | 'list' | 'kanban' | 'pivot' | 'graph' | 'calendar' | 'gantt' | 'activity' | 'dashboard' | null;
  recordId?: number | null;
  renderProfile?: 'create' | 'edit' | 'readonly' | null;
  surface?: 'user' | 'native' | 'hud' | null;
  sourceMode?: string | null;
  context?: Record<string, unknown> | null;
  contextRaw?: string | null;
  previewToken?: string | null;
  previewRoleKey?: string | null;
};

type LoadModelContractOptions = LoadActionContractOptions & {
  actionId?: number | null;
  viewType?: 'form' | 'tree' | 'kanban';
};


export async function loadActionUnifiedPageContractV2(actionId: number, options?: LoadActionContractOptions): Promise<UnifiedPageContractV2> {
  const result = await loadActionContractV2(actionId, options);
  return result.snapshot as unknown as UnifiedPageContractV2;
}

function rethrowContractError(err: unknown, context: { op: 'action_open' | 'model'; model?: string; actionId?: number }): never {
  if (!(err instanceof ApiError)) {
    throw err;
  }
  const message = String(err.message || '').trim();
  const isNativeBlocked = err.status === 410 && message.includes('native ui.contract op is disabled');
  if (!isNativeBlocked) {
    throw err;
  }
  const subject = context.op === 'action_open'
    ? `action_id=${Number(context.actionId || 0)}`
    : `model=${String(context.model || '').trim() || '-'}`;
  throw new ApiError(
    `ui.contract blocked by delivery policy (${subject}); switch to scene-ready scene route (/s/:sceneKey)`,
    err.status,
    err.traceId,
    {
      reasonCode: 'UI_CONTRACT_NATIVE_BLOCKED',
      kind: 'contract',
      hint: 'Prefer Scene-ready contract path: system.init -> scene registry -> /s/:sceneKey',
      errorCategory: err.errorCategory,
      retryable: false,
      suggestedAction: 'open_scene_route',
      details: {
        blocked_op: context.op,
        blocked_subject: subject,
      },
    },
  );
}

export async function loadActionContractStore(actionId: number, options?: LoadActionContractOptions) {
  try {
    const result = await loadActionContractV2(actionId, options);
    return result.store;
  } catch (err) {
    rethrowContractError(err, { op: 'action_open', actionId });
  }
}

export async function loadModelUnifiedPageContractV2(model: string, options?: LoadModelContractOptions): Promise<UnifiedPageContractV2> {
  const result = await loadModelContractV2(model, { ...options, viewType: options?.viewType || 'form' });
  return result.snapshot as unknown as UnifiedPageContractV2;
}

export async function loadModelLitePreviewContract(model: string, options?: LoadModelContractOptions): Promise<UnifiedPageContractLite | null> {
  const viewType = options?.viewType || 'tree';
  const result = await intentRequestRaw<Record<string, unknown>>({
    intent: 'load_contract',
    params: {
      model: String(model || '').trim(),
      view_type: viewType,
      include: 'all',
      contractMode: 'lite_preview',
      contractVersion: '2.0.0',
      entryPoint: 'load_contract',
      clientType: 'web_pc',
      fallbackMode: LITE_PREVIEW_LEGACY_FALLBACK_MODE,
      traceId: `lite-frontend-pilot-${String(model || '').trim() || 'model'}-${viewType}`,
    },
  });
  return extractLiteContractFromIntentBody(result.rawBody);
}
