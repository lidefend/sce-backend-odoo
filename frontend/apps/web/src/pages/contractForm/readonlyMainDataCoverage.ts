export function readonlyMainDataCoversFields(input: {
  renderProfile: string;
  fieldNames: string[];
  mainData: Record<string, unknown>;
}): boolean {
  if (input.renderProfile !== 'readonly' || input.fieldNames.length === 0) return false;
  return input.fieldNames.every((name) => Object.prototype.hasOwnProperty.call(input.mainData, name));
}
