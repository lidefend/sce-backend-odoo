export function fieldRequiresServerOnchange(rules: Array<Record<string, unknown>>, fieldName: string) {
  return rules.some((rule) => {
    const source = String(rule.sourceWidgetId || rule.source_widget_id || '').trim();
    const trigger = String(rule.triggerType || rule.trigger_type || '').trim().toLowerCase();
    const dispatch = String(rule.dispatchMode || rule.dispatch_mode || '').trim().toLowerCase();
    return source === `field.${fieldName}`
      && ['change', 'select', 'blur'].includes(trigger)
      && dispatch.startsWith('server');
  });
}
