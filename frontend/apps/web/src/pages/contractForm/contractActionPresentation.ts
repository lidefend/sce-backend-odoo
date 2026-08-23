import type { ContractV2ButtonStatus } from '../../app/contracts/v2/types';
import { detectObjectMethodFromActionKey, normalizeActionKind, parseMaybeJsonRecord, toPositiveInt } from '../../app/contractRuntime';
import { normalizeSceneActionProtocol } from '../../app/sceneActionProtocol';
import {
  normalizeActionLabel,
  normalizeActionSafety,
  normalizeRequiredParams,
  resolveV2ButtonStatus,
} from './actionContract';
import type { ContractAction } from './types';

export function buildContractFormActions(params: {
  model: string;
  recordId: number;
  renderProfile: 'create' | 'edit' | 'readonly';
  sceneReadyActions: Array<Record<string, unknown>>;
  v2ButtonStatus: Record<string, ContractV2ButtonStatus>;
  v2ActionRuleList: Array<Record<string, unknown>>;
  evaluateNativeActionVisibility: (row: Record<string, unknown>) => boolean;
  isTierValidationActionHidden: (methodName: string) => boolean;
}): ContractAction[] {
  const mapSceneReadyAction = (row: Record<string, unknown>): ContractAction | null => {
    const protocol = normalizeSceneActionProtocol(row);
    const key = String(row.key || '').trim();
    if (!key) return null;
    const target = parseMaybeJsonRecord(row.target);
    const intent = String(row.intent || '').trim().toLowerCase();
    const presentation = parseMaybeJsonRecord(row.presentation);
    const presentationTier = String(presentation.tier || row.tier || '').trim().toLowerCase();
    const placement = String(row.placement || 'header').trim().toLowerCase();
    const actionId = toPositiveInt(target.action_id) ?? toPositiveInt(target.ref);
    const hasOpenTarget = Boolean(actionId || String(target.url || '').trim() || String(target.route || '').trim());
    const kind = hasOpenTarget || intent === 'ui.contract' ? 'open' : 'object';
    const requiresSavedRecord = ['object', 'server', 'mutation'].includes(kind) && !params.recordId;
    return {
      key,
      authorityActionId: '',
      backendIdentity: String(row.backendIdentity || row.backend_identity || '').trim() || undefined,
      label: String(row.label || key),
      kind,
      level: placement,
      selection: 'none',
      actionId,
      methodName: detectObjectMethodFromActionKey(key, String(target.method || '').trim()),
      serverActionId: null,
      serverActionXmlId: '',
      targetModel: String(target.model || params.model || '').trim(),
      context: parseMaybeJsonRecord(target.context_raw),
      domainRaw: String(target.domain_raw || '').trim(),
      target: String(target.target || '').trim(),
      url: String(target.url || target.route || '').trim(),
      enabled: !requiresSavedRecord,
      authorizationAllowed: true,
      requiresSavedRecord,
      hint: requiresSavedRecord ? 'requires record id' : '',
      intent,
      semantic: presentationTier === 'primary' ? 'primary_action' : presentationTier === 'secondary' ? 'secondary_action' : '',
      sourceWidgetId: String(row.sourceWidgetId || row.source_widget_id || '').trim(),
      clientMode: String(target.mode || target.client_mode || row.clientMode || row.client_mode || '').trim(),
      visibleProfiles: ['create', 'edit', 'readonly'],
      requiredParams: normalizeRequiredParams(row.required_params),
      requiresReason: row.requires_reason === true,
      presentationTier,
      destructive: presentation.semantic === 'destructive',
      requiresConfirmation: presentation.requires_confirmation === true,
      actionSafety: normalizeActionSafety(row.action_safety),
      mutation: protocol?.mutation,
      refreshPolicy: protocol?.refresh_policy,
    };
  };

  const merged: Array<Record<string, unknown>> = [];
  (params.v2ActionRuleList || []).forEach((raw) => {
      if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return;
      const row = raw as Record<string, unknown>;
      const sourceWidgetId = String(row.sourceWidgetId || row.source_widget_id || '').trim();
      const targetScope = String(row.targetScope || row.target_scope || '').trim().toLowerCase();
      const triggerType = String(row.triggerType || row.trigger_type || '').trim();
      if (triggerType && triggerType !== 'click') return;
      const key = String(row.actionKey || row.key || row.actionId || '').trim();
      if (!key) return;
      const target = parseMaybeJsonRecord(row.target);
      const button = parseMaybeJsonRecord(row.button);
      const clientMode = String(target.mode || target.client_mode || '').trim();
      const buttonName = String(button.name || button.method || '').trim();
      // V2 targetScope describes the action's mutation/navigation scope, not
      // a visual body slot.  A page-scoped action emitted from page.root is a
      // page-header action; widget/container/dataSource/runtime scopes are not.
      const isHeaderAction = sourceWidgetId === 'page.header'
        || (sourceWidgetId === 'page.root' && ['header', 'page'].includes(targetScope));
      const isFooterAction = targetScope === 'footer';
      const nativeIdentity = parseMaybeJsonRecord(row.nativeIdentity || row.native_identity);
      const canonicalRegion = String(nativeIdentity.canonical_region || nativeIdentity.canonicalRegion || '').trim().toLowerCase();
      const level = isFooterAction
        ? 'footer'
        : isHeaderAction
          ? 'header'
          : canonicalRegion === 'stat_buttons'
            ? 'smart'
            : 'body';
      const buttonType = String(button.type || button.buttonType || '').trim();
      merged.push({
        key,
        authorityActionId: String(row.actionId || row.action_id || '').trim(),
        backendIdentity: String(row.backendIdentity || row.backend_identity || '').trim() || undefined,
        label: String(row.label || key).trim() || key,
        kind: buttonType === 'server' || buttonType === 'server_action' ? 'server' : buttonName ? 'object' : clientMode ? 'client' : 'open',
        intent: String(row.intent || '').trim(),
        level,
        selection: 'none',
        sourceWidgetId,
        target,
        target_model: String(target.model || '').trim(),
        payload: {
          method: buttonName,
          type: buttonType,
          server_action_id: button.server_action_id ?? button.serverActionId,
          xml_id: button.xml_id ?? button.xmlId,
          action_id: target.action_id,
          ref: target.ref,
          url: target.url || target.route,
          target: target.target,
          mode: clientMode,
          client_mode: clientMode,
          domain_raw: target.domain_raw,
          context_raw: target.context_raw,
        },
        visible: row.visible,
        allowed: row.allowed,
        enabled: row.enabled,
        disabled: row.disabled,
        modifiers: row.modifiers,
        invisible: row.invisible,
        visible_profiles: Array.isArray(row.visibleProfiles)
          ? row.visibleProfiles
          : Array.isArray(row.visible_profiles)
            ? row.visible_profiles
          : ['create', 'edit', 'readonly'],
        presentation: row.presentation,
        action_safety: row.actionSafety ?? row.action_safety,
        refresh_policy: row.refreshPolicy ?? row.refresh_policy,
      });
  });
  merged.push(...params.sceneReadyActions);

  const dedup = new Set<string>();
  const out: ContractAction[] = [];
  for (const row of merged) {
    if (params.sceneReadyActions.includes(row) || (params.sceneReadyActions.length && !String(row.key || '').trim())) {
      const mapped = mapSceneReadyAction(row);
      if (!mapped || dedup.has(mapped.key)) continue;
      const status = resolveV2ButtonStatus(mapped.key, params.v2ButtonStatus);
      if (status?.visible === false) continue;
      if (status?.disabled === true) {
        mapped.enabled = false;
        mapped.authorizationAllowed = false;
        mapped.hint = status.reasonCode || mapped.hint || 'disabled_by_status_contract';
      }
      dedup.add(mapped.key);
      out.push(mapped);
      continue;
    }
    const rowLabel = normalizeActionLabel(row.label);
    const keyBase = String(row.key || row.name || rowLabel || '').trim();
    const key = dedup.has(keyBase) && rowLabel ? `${keyBase}:${rowLabel}` : keyBase;
    if (!key || dedup.has(key)) continue;
    dedup.add(key);
    const payload = parseMaybeJsonRecord(row.payload);
    const protocol = normalizeSceneActionProtocol(row);
    const targetRaw = parseMaybeJsonRecord(row.target);
    const effectiveKind = protocol?.mutation ? 'mutation' : normalizeActionKind(row.kind);
    const level = String(row.level || 'body').trim().toLowerCase();
    const actionId = toPositiveInt(payload.action_id) ?? toPositiveInt(payload.ref) ?? toPositiveInt(row.actionId) ?? toPositiveInt(row.action_id);
    const methodName = detectObjectMethodFromActionKey(key, String(payload.method || row.method || '').trim());
    if (params.isTierValidationActionHidden(methodName)) continue;
    const selectionRaw = String(row.selection || 'none').trim().toLowerCase();
    const selection = selectionRaw === 'single' || selectionRaw === 'multi' ? selectionRaw : 'none';
    const visibleProfiles = (Array.isArray(row.visible_profiles) ? row.visible_profiles : ['create', 'edit'])
      .map((item) => String(item || '').trim().toLowerCase())
      .filter((item): item is 'create' | 'edit' | 'readonly' => ['create', 'edit', 'readonly'].includes(item));
    const requiredParams = normalizeRequiredParams(row.required_params);
    const presentation = parseMaybeJsonRecord(row.presentation);
    const presentationTier = String(presentation.tier || '').trim().toLowerCase();
    const presentationSemantic = String(presentation.semantic || '').trim();
    if (row.visible === false || row.invisible === true || !params.evaluateNativeActionVisibility(row)) continue;
    const status = resolveV2ButtonStatus(key, params.v2ButtonStatus);
    if (status?.visible === false) continue;
    const contractAllowed = typeof row.allowed === 'boolean' ? row.allowed : true;
    const contractEnabled = typeof row.enabled === 'boolean' ? row.enabled : true;
    const contractDisabled = row.disabled === true;
    const needRecord = ['object', 'server', 'mutation'].includes(effectiveKind) || ['row', 'smart'].includes(level);
    const authorizationAllowed = contractAllowed && contractEnabled && !contractDisabled
      && status?.disabled !== true;
    const requiresSavedRecord = needRecord && !params.recordId;
    const enabled = authorizationAllowed && !requiresSavedRecord;
    out.push({
      key,
      authorityActionId: String(row.authorityActionId || row.actionId || row.action_id || '').trim(),
      backendIdentity: String(row.backendIdentity || row.backend_identity || '').trim() || undefined,
      label: normalizeActionLabel(row.label, key),
      kind: effectiveKind,
      level,
      selection,
      actionId,
      methodName,
      serverActionId: toPositiveInt(payload.server_action_id || payload.serverActionId),
      serverActionXmlId: String(payload.xml_id || payload.xmlId || '').trim(),
      targetModel: String(row.target_model || row.model || params.model || '').trim(),
      context: parseMaybeJsonRecord(payload.context_raw),
      domainRaw: String(payload.domain_raw || '').trim(),
      target: String(payload.target || row.target || '').trim(),
      url: String(payload.url || row.url || '').trim(),
      enabled,
      authorizationAllowed,
      requiresSavedRecord,
      hint: status?.disabled === true
        ? status.reasonCode || 'disabled_by_status_contract'
        : needRecord && !params.recordId
          ? 'requires record id'
          : contractAllowed
            ? String(row.warning_message || '').trim()
            : String(row.blocked_message || row.reason || row.reason_code || '').trim(),
      intent: String(row.intent || '').trim(),
      semantic: presentationSemantic,
      sourceWidgetId: String(row.sourceWidgetId || row.source_widget_id || '').trim(),
      clientMode: String(targetRaw.mode || targetRaw.client_mode || row.clientMode || row.client_mode || '').trim(),
      visibleProfiles,
      requiredParams,
      requiresReason: row.requires_reason === true || requiredParams.includes('reason'),
      presentationTier,
      destructive: presentation.semantic === 'destructive',
      requiresConfirmation: presentation.requires_confirmation === true,
      actionSafety: normalizeActionSafety(row.action_safety),
      mutation: protocol?.mutation,
      refreshPolicy: protocol?.refresh_policy,
    });
  }
  const tierOrder: Record<string, number> = { primary: 0, secondary: 1, overflow: 2 };
  return out.sort((a, b) => (tierOrder[a.presentationTier || ''] ?? 3) - (tierOrder[b.presentationTier || ''] ?? 3)
    || a.level.localeCompare(b.level) || a.label.localeCompare(b.label, 'zh-CN'))
    .filter((item) => (!item.visibleProfiles.length || item.visibleProfiles.includes(params.renderProfile)) && item.selection === 'none' && item.level !== 'toolbar');
}
