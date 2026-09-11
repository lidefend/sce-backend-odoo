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

export type NativeBusinessSectionMatch<T extends NativeBusinessSectionNode> = {
  node: T;
  identity: NativeBusinessSectionIdentity;
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

/**
 * Collect business sections from the non-notebook, visible form body.
 *
 * Hidden ancestors terminate traversal and notebook descendants stay owned by
 * tab navigation. Both the renderer mode switch and section navigation consume
 * this function so an out-of-scope anchor cannot activate only one of them.
 */
export function collectNativeBusinessSections<T extends NativeBusinessSectionNode>(
  nodes: readonly T[],
  options: {
    childrenOf: (node: T) => readonly T[];
    isVisible?: (node: T) => boolean;
  },
): NativeBusinessSectionMatch<T>[] {
  const matches: NativeBusinessSectionMatch<T>[] = [];
  const isVisible = options.isVisible || ((node: T) => node.visible !== false);

  function visit(node: T, insideNotebook = false) {
    if (!isVisible(node)) return;
    const kind = nodeKind(node);
    const identity = insideNotebook ? null : nativeBusinessSectionIdentity(node);
    if (identity) matches.push({ node, identity });
    options.childrenOf(node).forEach((child) => visit(child, insideNotebook || kind === 'notebook'));
  }

  nodes.forEach((node) => visit(node));
  return matches;
}
