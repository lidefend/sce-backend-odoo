import type { BusinessAction, Dictionary } from "@/types/contracts";

const EXECUTE_BUTTON_INTENTS = new Set([
  "",
  "execute",
  "button.execute",
  "execute_button",
]);

export function usesExecuteButtonIntent(
  intent: unknown,
  button: Dictionary | null | undefined,
): boolean {
  if (!button || typeof button !== "object" || Array.isArray(button))
    return false;
  if (!Object.keys(button).length) return false;
  return EXECUTE_BUTTON_INTENTS.has(String(intent || "").trim().toLowerCase());
}

export function isInlineBusinessAction(action: BusinessAction): boolean {
  // A target describes where an action navigates, not how it is presented.
  // Only an explicit inline tier may create an embedded tab in a record form.
  return action.presentationTier === "inline";
}

export function isConfigurationBusinessAction(
  action: BusinessAction,
  options: { isPlatformAdmin?: boolean } = {},
): boolean {
  if (options.isPlatformAdmin === false) return false;
  if (action.presentationTier === "configuration") return true;
  const intent = String(action.intent || "").trim().toLowerCase();
  return [
    "ui.local_mode",
    "ui.form_field_configuration",
    "ui.form_custom_field.create",
    "ui.business_config.lowcode.apply",
  ].includes(intent);
}

export interface ActionResolutionOptions {
  nativeTree?: boolean;
  intakeMode?: boolean;
}

function sourceWidgetId(action: BusinessAction): string {
  return String(action.sourceWidgetId || "").trim().toLowerCase();
}

function targetScope(action: BusinessAction): string {
  return String(action.targetScope || "").trim().toLowerCase();
}

/**
 * Native form trees render their own body buttons. The remaining action bar
 * must therefore be limited to the page header surface, matching web.
 */
export function isNativeFormHeaderAction(action: BusinessAction): boolean {
  const source = sourceWidgetId(action);
  return source === "page.header"
    || (source === "page.root" && ["header", "page"].includes(targetScope(action)));
}

export function isNativeRowAction(action: BusinessAction): boolean {
  return sourceWidgetId(action) === "page.row" || action.triggerType === "row_click";
}

export function groupRecordBusinessActions(
  actions: BusinessAction[],
  options: { isPlatformAdmin?: boolean } = {},
) {
  const inline = actions.filter(isInlineBusinessAction);
  const configuration = actions.filter((action) => isConfigurationBusinessAction(action, options));
  const configurationKeys = new Set(
    actions
      .filter((action) => isConfigurationBusinessAction(action, { isPlatformAdmin: true }))
      .map((action) => action.key),
  );
  const commands = actions.filter(
    (action) => !inline.includes(action) && !configurationKeys.has(action.key),
  );
  const primary = commands.find((action) => action.presentationTier === "primary");
  const directCandidates = commands.filter(
    (action) => action !== primary && action.presentationTier === "secondary",
  );
  const direct = [...(primary ? [primary] : []), ...directCandidates].slice(0, 3);
  const directKeys = new Set(direct.map((action) => action.key));
  return {
    inline,
    direct,
    overflow: commands.filter((action) => !directKeys.has(action.key)),
    configuration,
  };
}
