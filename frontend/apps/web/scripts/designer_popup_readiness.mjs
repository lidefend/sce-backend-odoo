// Readiness classification for the business popup the designer journey asserts against.
//
// A break on that page used to surface only as a locator timeout, which cannot tell
// apart: a page that never arrived, a route the product denied, a shell that mounted
// while its record request was still in flight, and a mounted page whose label is
// genuinely absent. The classification below separates those facts so the run reports
// which one it observed instead of guessing from the opener's signals.
//
// Denial is a *route* fact. The shell renders menu chrome that may legitimately contain
// the denial wording for entries the current principal may not open, so body text is
// never used to classify a mounted page as denied.
export function resolvePopupReadiness({ state, url, entryModel = null, closed = false }) {
  let path = '';
  try { path = new URL(String(url || '')).pathname; } catch { path = ''; }
  const routeDenied = /\/login$|\/access-denied/.test(path);
  const shellMounted = Boolean(state && state.app_mounted);
  const verdict = !state ? 'popup_unreachable'
    : routeDenied ? 'popup_route_denied'
      : !shellMounted ? 'popup_shell_not_mounted'
        : state.loading_title ? 'popup_still_loading' : 'popup_ready_for_assertion';
  return {
    verdict,
    path,
    route_denied: routeDenied,
    shell_mounted: shellMounted,
    route_matches_entry: Boolean(entryModel) && path.includes(`/f/${entryModel}/`),
    // Only proven failure states may interrupt the journey: a route the product denied,
    // or a popup the product actually closed. A page whose state simply could not be read
    // yet is still an observation - a transient evaluate failure during navigation must
    // not fail a run that the strict label assertion below would have passed.
    blocking: verdict === 'popup_route_denied' || (verdict === 'popup_unreachable' && Boolean(closed)),
  };
}
