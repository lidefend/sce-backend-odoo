type WorksheetKeyboardEvent = Pick<KeyboardEvent, 'key' | 'target' | 'currentTarget'>;

export type WorksheetResizeAxis = 'navigation' | 'detail';

export type WorksheetResizeResult = {
  handled: boolean;
  value: number;
};

const RESIZE_BOUNDS: Record<WorksheetResizeAxis, { min: number; max: number }> = {
  navigation: { min: 200, max: 480 },
  detail: { min: 140, max: 420 },
};

export function clampWorksheetPaneSize(axis: WorksheetResizeAxis, value: number): number {
  const bounds = RESIZE_BOUNDS[axis];
  return Math.max(bounds.min, Math.min(bounds.max, Math.round(value)));
}

export function resizeWorksheetPaneFromKeyboard(
  axis: WorksheetResizeAxis,
  current: number,
  key: string,
  step = 16,
): WorksheetResizeResult {
  const bounds = RESIZE_BOUNDS[axis];
  if (key === 'Home') return { handled: true, value: bounds.min };
  if (key === 'End') return { handled: true, value: bounds.max };
  const delta = axis === 'navigation'
    ? (key === 'ArrowLeft' ? -step : key === 'ArrowRight' ? step : 0)
    : (key === 'ArrowDown' ? -step : key === 'ArrowUp' ? step : 0);
  return delta
    ? { handled: true, value: clampWorksheetPaneSize(axis, current + delta) }
    : { handled: false, value: current };
}

export function resolveVisibleWorksheetRecordId(
  visibleRecordIds: number[],
  selectedRecordId: number | null,
): number | null {
  if (selectedRecordId && visibleRecordIds.includes(selectedRecordId)) return selectedRecordId;
  return visibleRecordIds[0] || null;
}

export function shouldOpenWorksheetRecordFromKeyboard(
  event: WorksheetKeyboardEvent,
  record: unknown,
): boolean {
  return event.key === 'Enter'
    && event.target === event.currentTarget
    && Boolean(record);
}
