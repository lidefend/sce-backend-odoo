/** Contiguous rendering batches preserve native order and shared field columns.
 * These are renderer iterations, never configuration nodes or a second tree.
 */
export function nativeChildSegments<T>(nodes: readonly T[], typeOf: (node: T) => string) {
  const segments: Array<{ kind: string; nodes: T[] }> = [];
  for (const node of nodes) {
    const type = typeOf(node);
    const kind = ['field', 'button', 'widget'].includes(type) ? type : 'container';
    const previous = segments[segments.length - 1];
    if (previous?.kind === kind) previous.nodes.push(node);
    else segments.push({ kind, nodes: [node] });
  }
  return segments;
}

/** Declared layout container vocabulary: the contract declares these on a
 * container's presentation facet to say the container itself arranges its
 * declared children (flex row / grid row). */
export const DECLARED_LAYOUT_CONTAINER_TOKENS = ['row', 'd-flex', 'd-inline-flex'];

export function isDeclaredLayoutContainerToken(tokens: readonly string[]) {
  return tokens.some((token) => DECLARED_LAYOUT_CONTAINER_TOKENS.includes(token));
}

/**
 * Declared layout container children: the container declares how its declared
 * children are arranged, so each declared child renders as its own layout item
 * in declared order.  Batching contiguous fields into one shared segment would
 * insert a renderer-invented grid between the container and its declared
 * children, which is exactly what replaced the declared layout.
 */
export function declaredLayoutChildSegments<T>(nodes: readonly T[], typeOf: (node: T) => string) {
  return nodes.map((node) => {
    const type = typeOf(node);
    return { kind: ['field', 'button', 'widget'].includes(type) ? type : 'container', nodes: [node] };
  });
}
