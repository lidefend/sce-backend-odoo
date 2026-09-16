import type { ContractV2Container } from '../../app/contracts/v2/types';

export type BoundPatch = {
  target: string;
  expected: { type: string; name: string | null; occurrence_index: number };
  set?: { label?: string; visible?: boolean };
  order?: string[];
  group?: { key: string; label: string; members: string[] };
};
export function boundNodes(tree: ContractV2Container[]) {
  const rows: Array<{ node: ContractV2Container; parent?: ContractV2Container }> = [];
  const visit = (nodes: ContractV2Container[], parent?: ContractV2Container) => {
    for (const node of nodes) {
      if (node.nativeLocator) rows.push({ node, parent });
      visit(node.children || [], node);
    }
  };
  visit(tree);
  return rows;
}
export function bindNode(node: ContractV2Container): BoundPatch {
  if (!node.nativeLocator || !node.occurrenceIndex) throw new Error('配置目标缺少稳定身份，请刷新页面');
  return { target: node.nativeLocator, expected: { type: node.type || node.containerType,
    name: node.name ?? null, occurrence_index: node.occurrenceIndex } };
}
export function editBoundField(patches: BoundPatch[], node: ContractV2Container, values: NonNullable<BoundPatch['set']>) {
  const next = JSON.parse(JSON.stringify(patches)) as BoundPatch[];
  const index = next.findIndex((patch) => patch.target === node.nativeLocator);
  if (index < 0) next.push({ ...bindNode(node), set: values });
  else next[index] = { ...next[index], set: { ...next[index].set, ...values } };
  return next;
}
export function orderBoundField(patches: BoundPatch[], parent: ContractV2Container, node: ContractV2Container, delta: number) {
  if (parent.nativeLocator?.includes('/configuration-group:')) throw new Error('请在原分组中调整顺序后再设置新分组');
  const next = JSON.parse(JSON.stringify(patches)) as BoundPatch[];
  const patch = next.find((row) => row.target === parent.nativeLocator) || bindNode(parent);
  const order = [...(patch.order || parent.children.map((child) => child.nativeLocator || ''))];
  if (order.some((identity) => !identity || identity.includes('/configuration-group:'))) throw new Error('此区域包含独立配置分组，当前不支持跨组排序');
  const index = order.indexOf(node.nativeLocator || '');
  if (index < 0 || index + delta < 0 || index + delta >= order.length) return next;
  [order[index], order[index + delta]] = [order[index + delta], order[index]];
  patch.order = order;
  if (!next.includes(patch)) next.push(patch);
  return next;
}
export function groupBoundField(patches: BoundPatch[], parent: ContractV2Container, node: ContractV2Container, label: string) {
  if (!label.trim()) throw new Error('请填写分组名称');
  if (parent.nativeLocator?.includes('/configuration-group:')) throw new Error('当前字段已在配置分组中，请先回滚该配置再重新分组');
  const next = JSON.parse(JSON.stringify(patches)) as BoundPatch[];
  const patch = next.find((row) => row.target === parent.nativeLocator) || bindNode(parent);
  if (patch.group && patch.group.label !== label.trim()) throw new Error('同一区域当前仅支持一个新增分组，请使用已有分组名称');
  patch.group = { key: patch.group?.key || 'designer', label: label.trim(),
    members: [...new Set([...(patch.group?.members || []), node.nativeLocator!])] };
  if (!next.includes(patch)) next.push(patch);
  return next;
}

/** Summarize the same stable-node patches sent to the compiler. No second layout. */
export function summarizeBoundPatches(tree: ContractV2Container[], patches: BoundPatch[]): string[] {
  const nodes = new Map(boundNodes(tree).map(({ node }) => [node.nativeLocator!, node]));
  const name = (id: string) => {
    const node = nodes.get(id);
    return node ? `${node.label || node.title || node.name || '区域'}（${node.name || '分组'} · ${node.occurrenceIndex}）` : `失效目标：${id}`;
  };
  const lines: string[] = [];
  for (const patch of patches) {
    if (patch.set?.label !== undefined && patch.set.label !== (nodes.get(patch.target)?.label || nodes.get(patch.target)?.name)) lines.push(`标签：${name(patch.target)} → ${patch.set.label}`);
    if (patch.set?.visible !== undefined) lines.push(`显隐：${name(patch.target)} → ${patch.set.visible ? '显示（遵循业务约束）' : '隐藏'}`);
    if (patch.order) lines.push(`顺序：${name(patch.target)}：${patch.order.map(name).join(' → ')}`);
    if (patch.group) lines.push(`分组：${patch.group.label} ← ${patch.group.members.map(name).join('、')}`);
  }
  return lines;
}
