const SYSTEM_INIT_INTENT = 'system.init';

function navigationFromPayload(payload) {
  const data = payload?.result || payload?.data || payload || {};
  return Array.isArray(data?.navigation?.nav) ? data.navigation.nav : [];
}

function navigationTarget(node) {
  const meta = node.meta && typeof node.meta === 'object' ? node.meta : {};
  const entryTarget = node.entry_target && typeof node.entry_target === 'object'
    ? node.entry_target
    : meta.entry_target && typeof meta.entry_target === 'object'
      ? meta.entry_target
      : {};
  const canonical = node.canonical_navigation && typeof node.canonical_navigation === 'object'
    ? node.canonical_navigation
    : {};
  return {
    action_id: Number(node.action_id || node.actionId || node.action || meta.action_id || meta.actionId || 0),
    menu_id: Number(node.menu_id || node.menuId || meta.menu_id || meta.menuId || 0),
    route: String(
      node.route
      || meta.route
      || entryTarget.route
      || canonical.route
      || '',
    ).trim(),
    scene_key: String(node.scene_key || meta.scene_key || entryTarget.scene_key || '').trim(),
    entry_target: entryTarget,
    entry_target_type: String(entryTarget.type || '').trim(),
    action_xmlid: String(node.action_xmlid || meta.action_xmlid || '').trim(),
    menu_xmlid: String(node.menu_xmlid || node.xmlid || meta.menu_xmlid || '').trim(),
  };
}

export function findReleasedNavigationTarget(nav, actionXmlid) {
  const pending = Array.isArray(nav) ? [...nav] : [];
  while (pending.length) {
    const node = pending.shift();
    if (!node || typeof node !== 'object') continue;
    const target = navigationTarget(node);
    if (target.action_xmlid === actionXmlid) {
      if (target.action_id > 0 && target.menu_id > 0) return target;
    }
    if (Array.isArray(node.children)) pending.push(...node.children);
  }
  return null;
}

export function findReleasedNavigationTargetById(nav, actionId, menuId) {
  const expectedActionId = Number(actionId || 0);
  const expectedMenuId = Number(menuId || 0);
  if (expectedActionId <= 0 || expectedMenuId <= 0) return null;
  const pending = Array.isArray(nav) ? [...nav] : [];
  while (pending.length) {
    const node = pending.shift();
    if (!node || typeof node !== 'object') continue;
    const target = navigationTarget(node);
    if (target.action_id === expectedActionId && target.menu_id === expectedMenuId) {
      return target;
    }
    if (Array.isArray(node.children)) pending.push(...node.children);
  }
  return null;
}

export function findReleasedNavigationTargetByMenuXmlid(nav, menuXmlid, actionXmlid = '') {
  const expectedMenuXmlid = String(menuXmlid || '');
  const expectedActionXmlid = String(actionXmlid || '');
  if (!expectedMenuXmlid) return null;
  const pending = Array.isArray(nav) ? [...nav] : [];
  while (pending.length) {
    const node = pending.shift();
    if (!node || typeof node !== 'object') continue;
    const target = navigationTarget(node);
    if (
      target.menu_xmlid === expectedMenuXmlid
      && (!expectedActionXmlid || target.action_xmlid === expectedActionXmlid)
    ) {
      const hasActionIdentity = target.action_id > 0 && target.menu_id > 0;
      const hasSceneIdentity = target.action_id === 0 && target.menu_id > 0 && Boolean(target.route);
      if (hasActionIdentity || hasSceneIdentity) return target;
    }
    if (Array.isArray(node.children)) pending.push(...node.children);
  }
  return null;
}

export function captureReleasedNavigation(page) {
  let current = [];
  let currentPayload = {};
  page.on('response', async (response) => {
    if (!response.url().includes('/api/v1/intent')) return;
    try {
      const request = JSON.parse(response.request().postData() || '{}');
      if (request?.intent !== SYSTEM_INIT_INTENT || response.status() >= 400) return;
      const payload = await response.json();
      const nav = navigationFromPayload(payload);
      if (nav.length) {
        current = nav;
        currentPayload = payload?.result || payload?.data || payload || {};
      }
    } catch {}
  });
  return {
    nav: () => current,
    payload: () => currentPayload,
    async target(actionXmlid, timeoutMs = 45000) {
      const started = Date.now();
      while (Date.now() - started < timeoutMs) {
        const target = findReleasedNavigationTarget(current, actionXmlid);
        if (target) return target;
        await page.waitForTimeout(50);
      }
      throw new Error(`released navigation target missing: ${actionXmlid}`);
    },
    async targetByMenuXmlid(menuXmlid, actionXmlid = '', timeoutMs = 45000) {
      const started = Date.now();
      while (Date.now() - started < timeoutMs) {
        const target = findReleasedNavigationTargetByMenuXmlid(current, menuXmlid, actionXmlid);
        if (target) return target;
        await page.waitForTimeout(50);
      }
      throw new Error(`released navigation menu target missing: ${menuXmlid}`);
    },
  };
}

export function applyReleasedNavigationTarget(targets, keys, released) {
  for (const key of keys) {
    if (!targets[key]) continue;
    for (const field of ['action_id', 'menu_id', 'route', 'scene_key', 'entry_target', 'entry_target_type']) {
      if (released[field] !== undefined) targets[key][field] = released[field];
    }
  }
}
