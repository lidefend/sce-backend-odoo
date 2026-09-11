export type NativeBusinessSectionNode = {
  kind?: unknown;
  type?: unknown;
  containerType?: unknown;
  title?: unknown;
  string?: unknown;
  label?: unknown;
  visible?: unknown;
  attributes?: Readonly<Record<string, unknown>>;
};

export type NativeBusinessSectionIdentity = {
  anchor: string;
  label: string;
};

function text(value: unknown): string {
  return String(value ?? '').trim();
}

function nodeKind(node: NativeBusinessSectionNode): string {
  return text(node.kind || node.type || node.containerType).toLowerCase();
}

function readableTitle(value: unknown): string {
  const title = text(value);
  if (!title) return '';
  if (['group', 'page', 'notebook', 'sheet', 'container', 'header', 'footer'].includes(title.toLowerCase())) return '';
  if (/^[a-z][a-z0-9_:. -]*$/i.test(title) && /[_:.]/.test(title)) return '';
  return title;
}

/**
 * Explicit native-view opt-in for a visible business section.
 *
 * A plain XML `string` remains layout metadata and is not enough to create a
 * heading or navigation entry. This preserves the existing hidden-group
 * policy while allowing a released view to identify a real business section
 * through its stable `data-sc-anchor`.
 */
export function nativeBusinessSectionIdentity(
  node: NativeBusinessSectionNode | null | undefined,
): NativeBusinessSectionIdentity | null {
  if (!node || node.visible === false || nodeKind(node) !== 'group') return null;
  const anchor = text(node.attributes?.['data-sc-anchor']);
  const label = readableTitle(node.title || node.string || node.label);
  return anchor && label ? { anchor, label } : null;
}
