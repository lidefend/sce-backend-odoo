export type ListColumnVisibilityOption = {
  name: string;
  defaultVisible?: boolean;
};

export type ListColumnSelectionReason =
  | 'critical_contract'
  | 'explicit_visible'
  | 'responsive_budget'
  | 'explicit_hidden'
  | 'default_hidden'
  | 'responsive_capacity';

export type ListColumnSelectionTrace = {
  field: string;
  visible: boolean;
  reasonCode: ListColumnSelectionReason;
};

export function resolveResponsiveListColumns(options: {
  enabledColumns: string[];
  orderedColumns: string[];
  criticalColumns?: string[];
  defaultVisibility?: Record<string, boolean>;
  visibility?: Record<string, boolean>;
  responsiveCandidates?: string[];
  capacity?: number;
}) {
  const enabled = new Set(options.enabledColumns);
  const ordered = options.orderedColumns.filter((field, index, rows) => enabled.has(field) && rows.indexOf(field) === index);
  const visibility = options.visibility || {};
  const defaults = options.defaultVisibility || {};
  const critical = new Set((options.criticalColumns || []).filter((field) => enabled.has(field)));
  const explicitVisible = new Set(ordered.filter((field) => visibility[field] === true));
  const candidates = new Set((options.responsiveCandidates || ordered).filter((field) => enabled.has(field)));
  const required = new Set([...critical, ...explicitVisible]);
  const capacity = Math.max(1, Number(options.capacity || ordered.length || 1));
  const selected = new Set<string>();

  for (const field of ordered) {
    if (required.has(field)) selected.add(field);
  }
  for (const field of ordered) {
    if (selected.size >= capacity && !required.has(field)) continue;
    if (candidates.has(field)) selected.add(field);
  }

  const trace: ListColumnSelectionTrace[] = options.orderedColumns.map((field) => {
    if (visibility[field] === false) return { field, visible: false, reasonCode: 'explicit_hidden' };
    if (!enabled.has(field)) return { field, visible: false, reasonCode: 'default_hidden' };
    if (critical.has(field)) return { field, visible: true, reasonCode: 'critical_contract' };
    if (explicitVisible.has(field)) return { field, visible: true, reasonCode: 'explicit_visible' };
    if (selected.has(field)) return { field, visible: true, reasonCode: 'responsive_budget' };
    return { field, visible: false, reasonCode: 'responsive_capacity' };
  });
  return {
    visibleColumns: ordered.filter((field) => selected.has(field)),
    trace,
    requiresOverflow: selected.size > capacity,
  };
}

export function resolveEnabledListColumns(
  columns: ListColumnVisibilityOption[],
  fallbackColumns: string[],
  visibility: Record<string, boolean> = {},
) {
  const source = columns.length ? columns.map((column) => column.name) : fallbackColumns;
  const defaults = new Map(columns.map((column) => [column.name, column.defaultVisible !== false]));
  const enabled = source.filter((name) => {
    if (Object.prototype.hasOwnProperty.call(visibility, name)) return visibility[name] === true;
    return defaults.get(name) !== false;
  });
  return enabled.length ? enabled : source.slice(0, 1);
}

export function prioritizeExplicitlyEnabledListColumns(
  fields: string[],
  defaultVisibility: Record<string, boolean>,
  visibility: Record<string, boolean> = {},
) {
  return fields
    .map((field, index) => ({
      field,
      index,
      explicitlyEnabled: visibility[field] === true && defaultVisibility[field] === false,
    }))
    .sort((left, right) => Number(right.explicitlyEnabled) - Number(left.explicitlyEnabled) || left.index - right.index)
    .map((item) => item.field);
}
