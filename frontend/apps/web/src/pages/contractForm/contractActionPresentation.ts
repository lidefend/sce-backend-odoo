import type { ContractV2ButtonStatus } from '../../app/contracts/v2/types';
import { routeAuthorityContextAllowed, type RouteAuthorityEntry } from '../../app/routeAuthority';
import { detectObjectMethodFromActionKey, normalizeActionKind, parseMaybeJsonRecord, toPositiveInt } from '../../app/contractRuntime';
import { normalizeSceneActionProtocol } from '../../app/sceneActionProtocol';
import {
  normalizeActionLabel,
  normalizeActionSafety,
  normalizeRequiredParams,
  resolveV2ButtonStatus,
} from './actionContract';
import type { ContractAction } from './types';
import { nativeActionOccurrenceKey } from './nativeActionIdentity';

export type AuthorizedWindowActionTarget = { actionId: number; menuId: number };

export function resolveContractActionForNativeOccurrence(
  actions: ContractAction[],
  row: Record<string, unknown>,
): ContractAction | null {
  const nativeAction = parseMaybeJsonRecord(row.action);
  const backendIdentity = String(
    nativeAction.backendIdentity || nativeAction.backend_identity
    || row.backendIdentity || row.backend_identity || '',
  ).trim();
  const authorityActionId = String(
    nativeAction.actionId || nativeAction.action_id || row.actionId || row.action_id || '',
  ).trim();
  const occurrenceKey = nativeActionOccurrenceKey(
    nativeAction.nativeIdentity || nativeAction.native_identity
    || row.nativeIdentity || row.native_identity,
  );
  if (!backendIdentity && !authorityActionId && !occurrenceKey) return null;
  const candidates = actions.filter((candidate) => (
    (!backendIdentity || candidate.backendIdentity === backendIdentity)
    && (!authorityActionId || candidate.authorityActionId === authorityActionId)
    && (!occurrenceKey || nativeActionOccurrenceKey(candidate.nativeIdentity) === occurrenceKey)
  ));
  return candidates.length === 1 ? candidates[0] : null;
}

export function resolveAuthorizedWindowActionTarget(
  entries: RouteAuthorityEntry[],
  requested: { actionId: number | null; actionReference: string; menuId: number | null },
  context: { query: Record<string, unknown>; companyId?: number | null; selectedRecordId?: number | null },
): AuthorizedWindowActionTarget | null {
  const referenceIsNumeric = Boolean(toPositiveInt(requested.actionReference));
  const candidates = entries.filter((entry) => {
    const actionId = toPositiveInt(entry.action_id);
    const menuId = toPositiveInt(entry.menu_id) || 0;
    if (!actionId) return false;
    if (requested.actionId && actionId !== requested.actionId) return false;
    if (!referenceIsNumeric && requested.actionReference
      && String(entry.action_xmlid || '').trim() !== requested.actionReference) return false;
    if (requested.menuId && menuId !== requested.menuId) return false;
    return routeAuthorityContextAllowed(entry, context.query, context);
  });
  const pairs = new Map<string, AuthorizedWindowActionTarget>();
  candidates.forEach((entry) => {
    const pair = { actionId: toPositiveInt(entry.action_id) as number, menuId: toPositiveInt(entry.menu_id) || 0 };
    pairs.set(`${pair.menuId}:${pair.actionId}`, pair);
  });
  return pairs.size === 1 ? [...pairs.values()][0] : null;
}

export function buildContractFormActions(params: {
  model: string;
  recordId: number;
  renderProfile: 'create' | 'edit' | 'readonly';
  sceneReadyActions: Array<Record<string, unknown>>;
  v2ButtonStatus: Record<string, ContractV2ButtonStatus>;
  v2ActionRuleList: Array<Record<string, unknown>>;
  resolveActionReference?: (requested: { actionId: number | null; actionReference: string; menuId: number | null }) => AuthorizedWindowActionTarget | null;
}): ContractAction[] {
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
        nativeIdentity,
        label: String(row.label || key).trim() || key,
        kind: buttonType === 'server' || buttonType === 'server_action'
          ? 'server'
          : buttonType === 'action'
            ? 'action'
            : buttonName
              ? 'object'
              : clientMode
                ? 'client'
                : 'open',
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
          ref: target.ref || target.action_ref || target.xml_id || target.xmlid,
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
        entitlementEvaluated: row.entitlementEvaluated ?? row.entitlement_evaluated,
      });
  });

  // Scene rows are presentation hints, never executable authority.  A V2 row
  // is the only source allowed to enter the form action bar.
  const identityCounts = new Map<string, number>();
  const actionIdCounts = new Map<string, number>();
  merged.forEach((row) => {
    const identity = String(row.backendIdentity || row.backend_identity || '').trim();
    const actionId = String(row.authorityActionId || row.actionId || row.action_id || '').trim();
    if (identity) identityCounts.set(identity, (identityCounts.get(identity) || 0) + 1);
    if (actionId) actionIdCounts.set(actionId, (actionIdCounts.get(actionId) || 0) + 1);
  });

  const dedup = new Set<string>();
  const out: ContractAction[] = [];
  for (const row of merged) {
    const authorityActionId = String(row.authorityActionId || row.actionId || row.action_id || '').trim();
    const backendIdentity = String(row.backendIdentity || row.backend_identity || '').trim();
    const sourceWidgetId = String(row.sourceWidgetId || row.source_widget_id || '').trim();
    if (!authorityActionId || !backendIdentity || !sourceWidgetId) continue;
    if (identityCounts.get(backendIdentity) !== 1 || actionIdCounts.get(authorityActionId) !== 1) continue;
    if (
      typeof row.allowed !== 'boolean'
      || typeof row.enabled !== 'boolean'
      || typeof row.disabled !== 'boolean'
      || row.entitlementEvaluated !== true
    ) continue;
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
    const actionReference = String(payload.ref || '').trim();
    const requestedActionId = toPositiveInt(payload.action_id)
      ?? toPositiveInt(actionReference)
      ?? toPositiveInt(row.actionId)
      ?? toPositiveInt(row.action_id);
    const requestedMenuId = toPositiveInt(targetRaw.menu_id || targetRaw.menuId);
    const hasWindowActionSelector = Boolean(requestedActionId || actionReference || requestedMenuId);
    const authorizedWindowTarget = effectiveKind === 'open' && hasWindowActionSelector && params.resolveActionReference
      ? params.resolveActionReference({ actionId: requestedActionId, actionReference, menuId: requestedMenuId })
      : null;
    const requiresAuthorizedResolution = Boolean(params.resolveActionReference && hasWindowActionSelector);
    const actionId = authorizedWindowTarget?.actionId ?? (requiresAuthorizedResolution ? null : requestedActionId);
    const menuId = authorizedWindowTarget?.menuId ?? (requiresAuthorizedResolution ? null : requestedMenuId);
    const openUrl = String(payload.url || row.url || '').trim();
    if (effectiveKind === 'open' && !actionId && !openUrl) continue;
    const methodName = detectObjectMethodFromActionKey(key, String(payload.method || row.method || '').trim());
    const selectionRaw = String(row.selection || 'none').trim().toLowerCase();
    const selection = selectionRaw === 'single' || selectionRaw === 'multi' ? selectionRaw : 'none';
    const visibleProfiles = (Array.isArray(row.visible_profiles) ? row.visible_profiles : ['create', 'edit'])
      .map((item) => String(item || '').trim().toLowerCase())
      .filter((item): item is 'create' | 'edit' | 'readonly' => ['create', 'edit', 'readonly'].includes(item));
    const requiredParams = normalizeRequiredParams(row.required_params);
    const presentation = parseMaybeJsonRecord(row.presentation);
    const presentationTier = String(presentation.tier || '').trim().toLowerCase();
    const presentationSemantic = String(presentation.semantic || '').trim();
    if (row.visible === false || row.invisible === true) continue;
    const statuses = [...new Set(Object.values(params.v2ButtonStatus))];
    const identityStatuses = statuses.filter((candidate) => (
      String(candidate?.backendIdentity || '').trim() === backendIdentity
    ));
    const status = identityStatuses.length === 1
      ? identityStatuses[0]
      : identityStatuses.length > 1
        ? undefined
        : resolveV2ButtonStatus(key, params.v2ButtonStatus);
    if (!status || typeof status.visible !== 'boolean' || typeof status.disabled !== 'boolean') continue;
    if (status?.backendIdentity && status.backendIdentity !== backendIdentity) continue;
    if (status.visible === false) continue;
    const contractAllowed = row.allowed === true;
    const contractEnabled = row.enabled === true;
    const contractDisabled = row.disabled === true;
    const needRecord = ['object', 'server', 'action', 'mutation'].includes(effectiveKind) || ['row', 'smart'].includes(level);
    const authorizationAllowed = contractAllowed && contractEnabled && !contractDisabled
      && status.disabled !== true;
    const requiresSavedRecord = needRecord && !params.recordId;
    const enabled = authorizationAllowed && !requiresSavedRecord;
    out.push({
      key,
      authorityActionId,
      backendIdentity,
      nativeIdentity: parseMaybeJsonRecord(row.nativeIdentity || row.native_identity),
      label: normalizeActionLabel(row.label, key),
      kind: effectiveKind,
      level,
      selection,
      actionId,
      menuId,
      methodName,
      serverActionId: toPositiveInt(payload.server_action_id || payload.serverActionId),
      serverActionXmlId: String(payload.xml_id || payload.xmlId || '').trim(),
      // A type=action button is authorised against the current source record;
      // target.model names the window destination (often a transient wizard),
      // not the record whose Contract V2 authority is being executed.
      targetModel: effectiveKind === 'action'
        ? params.model
        : String(row.target_model || row.model || params.model || '').trim(),
      context: parseMaybeJsonRecord(payload.context_raw),
      domainRaw: String(payload.domain_raw || '').trim(),
      target: String(payload.target || targetRaw.target || '').trim(),
      url: openUrl,
      enabled,
      authorizationAllowed,
      requiresSavedRecord,
      hint: status.disabled === true
        ? status.reasonCode || 'disabled_by_status_contract'
        : needRecord && !params.recordId
          ? 'requires record id'
          : contractAllowed
            ? String(row.warning_message || '').trim()
            : String(row.blocked_message || row.reason || row.reason_code || '').trim(),
      intent: String(row.intent || '').trim(),
      semantic: presentationSemantic,
      sourceWidgetId,
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
