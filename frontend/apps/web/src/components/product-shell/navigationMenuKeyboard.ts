/** Dispatch keyboard activation to the control TDesign registered for a submenu. */
export function activateNavigationMenuFromKeyboard(
  event: Pick<KeyboardEvent, 'currentTarget'>,
): void {
  const root = event.currentTarget;
  if (!(root instanceof HTMLElement)) return;
  const activationTarget = root.querySelector<HTMLElement>('[data-navigation-toggle="submenu"]') || root;
  activationTarget.click();
}
