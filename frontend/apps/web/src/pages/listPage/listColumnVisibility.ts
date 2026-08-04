export type ListColumnVisibilityOption = {
  name: string;
  defaultVisible?: boolean;
};

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
