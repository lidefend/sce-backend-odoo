import type { ContractV2ActionRule, ContractV2ButtonStatus, ContractV2Dictionary } from '../contracts/v2/types';
import { normalizeActionKind, parseMaybeJsonRecord } from '../contractRuntime';
import { normalizeSceneActionProtocol } from '../sceneActionProtocol';

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function asDict(value: unknown): ContractV2Dictionary {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as ContractV2Dictionary : {};
}

export type ActionRuleExecutionShape = {
  kind: string;
  level: string;
  effectiveKind: string;
  methodName: string;
  buttonType: string;
  requiresPersistedRecord: boolean;
};

/**
 * Single source of truth for how one declared contract action is executed.
 *
 * Presentation (visible/enabled) and the executable adapter list are two
 * consumers of the same declaration.  When they derive the execution shape
 * independently they can disagree, which either promises an action no adapter
 * can run or hides one that can run.  Both must resolve the shape here.
 */
export function resolveActionExecutionShape(row: Record<string, unknown>): ActionRuleExecutionShape {
  const sourceWidgetId = text(row.sourceWidgetId || row.source_widget_id);
  const targetScope = text(row.targetScope || row.target_scope).toLowerCase();
  const target = parseMaybeJsonRecord(row.target);
  const button = parseMaybeJsonRecord(row.button);
  const clientMode = text(target.mode || target.client_mode);
  const buttonName = text(button.name || button.method);
  const buttonType = text(button.type || button.buttonType);
  const intent = text(row.intent);
  // V2 targetScope describes the action's mutation/navigation scope, not a
  // visual body slot.  A page-scoped action emitted from page.root is a
  // page-header action; widget/container/dataSource/runtime scopes are not.
  const isHeaderAction = sourceWidgetId === 'page.header'
    || (sourceWidgetId === 'page.root' && ['header', 'page'].includes(targetScope));
  const isFooterAction = targetScope === 'footer';
  const nativeIdentity = parseMaybeJsonRecord(row.nativeIdentity || row.native_identity);
  const canonicalRegion = text(nativeIdentity.canonical_region || nativeIdentity.canonicalRegion).toLowerCase();
  const level = isFooterAction
    ? 'footer'
    : isHeaderAction
      ? 'header'
      : canonicalRegion === 'stat_buttons'
        ? 'smart'
        : 'body';
  const kind = ['ui.local_mode', 'ui.mode'].includes(intent)
    ? 'client'
    : buttonType === 'server' || buttonType === 'server_action'
      ? 'server'
      : buttonType === 'action'
        ? 'action'
        : buttonName
          ? 'object'
          : clientMode
            ? 'client'
            : 'open';
  const protocol = normalizeSceneActionProtocol({
    ...row,
    id: text(row.id || row.key || row.actionKey || row.actionId),
  });
  const effectiveKind = protocol?.mutation ? 'mutation' : normalizeActionKind(kind);
  return {
    kind,
    level,
    effectiveKind,
    methodName: buttonName,
    buttonType,
    // A declared record action cannot run against a record that does not exist
    // yet; the platform persists the draft first and only then executes it.
    requiresPersistedRecord: ['object', 'server', 'action', 'mutation'].includes(effectiveKind)
      || ['row', 'smart'].includes(level),
  };
}

export function actionRequiresPersistedRecord(action: ContractV2ActionRule): boolean {
  return resolveActionExecutionShape(action as unknown as Record<string, unknown>).requiresPersistedRecord;
}

/**
 * A status the producer resolved against the state it saw at fetch time.  It may
 * only be deferred to the declared modifier when the modifier references fields
 * that are present in the live values, so an unresolvable dependency still
 * fails closed.  Authority reasons (ACTION_NOT_ALLOWED, field/ACL policy, …)
 * are never deferred.
 */
export const STATE_DERIVED_STATUS_REASONS: ReadonlySet<string> = new Set([
  'ACTION_NOT_VISIBLE_IN_STATE',
  'ACTION_VISIBILITY_UNRESOLVED',
]);

export function declaredVisibilityModifier(action: ContractV2ActionRule): unknown {
  const visibleAttrs = asDict(action.visible?.attrs);
  if (Object.prototype.hasOwnProperty.call(action.modifiers || {}, 'invisible')) {
    return action.modifiers?.invisible;
  }
  if (Object.prototype.hasOwnProperty.call(visibleAttrs, 'invisible')) {
    return visibleAttrs.invisible;
  }
  return action.invisible;
}

function collectModifierFields(value: unknown, fields: Set<string>): void {
  if (Array.isArray(value)) {
    value.forEach((entry) => collectModifierFields(entry, fields));
    return;
  }
  if (!value || typeof value !== 'object') return;
  const row = value as Record<string, unknown>;
  const field = text(row.field);
  if (field) fields.add(field);
  const valueField = text(row.value_field) || text(row.valueField);
  if (valueField) fields.add(valueField);
  collectModifierFields(row.expr, fields);
  collectModifierFields(row.exprs, fields);
}

export function declaredModifierDependenciesResolved(modifier: unknown, values: ContractV2Dictionary): boolean {
  if (!modifier || typeof modifier !== 'object') return false;
  const fields = new Set<string>();
  collectModifierFields(modifier, fields);
  if (!fields.size) return false;
  for (const field of fields) {
    if (!Object.prototype.hasOwnProperty.call(values, field)) return false;
  }
  return true;
}

export function resolveStateDerivedStatus(
  action: ContractV2ActionRule,
  status: ContractV2ButtonStatus | undefined,
  values: ContractV2Dictionary,
): boolean {
  if (status?.visible !== false) return false;
  if (!STATE_DERIVED_STATUS_REASONS.has(text(status?.reasonCode))) return false;
  return declaredModifierDependenciesResolved(declaredVisibilityModifier(action), values);
}
