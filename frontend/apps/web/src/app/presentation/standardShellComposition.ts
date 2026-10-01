/**
 * Which routes render through the official application-shell composition.
 *
 * Presentation scope only. This decides *how* an already-authorized route is
 * framed by the application shell; it never decides which navigation entries
 * exist, which records are readable, which actions are allowed, or who may use
 * the page. Adoption is therefore never derived from business model names,
 * field labels, semantic roles, action IDs, menu IDs, company identity, or
 * renderer selection, and it is never an authorization input.
 *
 * The official source is the reference application shell `src/layouts/` of
 * `Tencent/tdesign-vue-next-starter`
 * (`aeed57076217f7777158b905f353d73585bad1c4`); it is a reference baseline, not
 * a dependency upgrade. The shell container driver is already the official
 * `t-layout` primitive (`ProductAppShell` -> `ScLayout`); this policy only makes
 * the *adoption scope* explicit so a route joins by declaring the adopted
 * layout, not by resembling one.
 *
 * A route that is not adopted keeps its previous presentation: it renders its
 * page component without the shell, exactly as before. An embedded relation
 * dialog keeps that previous presentation too, because the shell is
 * intentionally bypassed while the dialog owns the interaction.
 */

export type StandardShellCompositionId = 'official-standard-shell' | 'legacy-shell-surface';

export type StandardShellCompositionReason =
  | 'shell-layout-adopted'
  | 'not-a-shell-layout'
  | 'embedded-relation-dialog';

export type StandardShellCompositionDecision = {
  composition: StandardShellCompositionId;
  adopted: boolean;
  reason: StandardShellCompositionReason;
};

/**
 * Route layouts whose standard frame is served by the official composition.
 *
 * Every entry is a surface this project has verified against the official
 * composition. The shell surface never names a business model, so a route joins
 * by declaring an adopted layout and by carrying a page the shell already
 * frames.
 */
export const STANDARD_SHELL_COMPOSITION_LAYOUTS: readonly string[] = Object.freeze([
  'shell',
]);

export function resolveStandardShellComposition(input: {
  layout?: unknown;
  embeddedRelationDialog?: unknown;
}): StandardShellCompositionDecision {
  const layout = String(input?.layout ?? '').trim();
  if (!layout || !STANDARD_SHELL_COMPOSITION_LAYOUTS.includes(layout)) {
    return { composition: 'legacy-shell-surface', adopted: false, reason: 'not-a-shell-layout' };
  }
  if (input?.embeddedRelationDialog === true) {
    return { composition: 'legacy-shell-surface', adopted: false, reason: 'embedded-relation-dialog' };
  }
  return { composition: 'official-standard-shell', adopted: true, reason: 'shell-layout-adopted' };
}
