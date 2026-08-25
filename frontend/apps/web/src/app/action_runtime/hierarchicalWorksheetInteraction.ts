type WorksheetKeyboardEvent = Pick<KeyboardEvent, 'key' | 'target' | 'currentTarget'>;

export function shouldOpenWorksheetRecordFromKeyboard(
  event: WorksheetKeyboardEvent,
  record: unknown,
): boolean {
  return event.key === 'Enter'
    && event.target === event.currentTarget
    && Boolean(record);
}
