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
