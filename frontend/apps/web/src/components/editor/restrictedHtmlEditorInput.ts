export function resolveRestrictedHtmlEditorInput(options: {
  disabled: boolean;
  html: unknown;
}): string | null {
  if (options.disabled) return null;
  return String(options.html ?? '');
}
