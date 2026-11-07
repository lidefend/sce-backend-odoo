function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function normalizeProxyBasePath(value) {
  const raw = String(value || '').trim()
  if (!raw || raw === '/') return ''
  if (!raw.startsWith('/') || raw.startsWith('//') || /[?#\s]/.test(raw)) {
    throw new Error('API_PROXY_BASE_PATH must be one absolute path')
  }
  return raw.replace(/\/+$/, '')
}

export function upstreamRequestPath(rawUrl, basePath) {
  const request = new URL(String(rawUrl || '/'), 'http://static-proxy.local')
  const base = normalizeProxyBasePath(basePath)
  if (!base || request.pathname === base || request.pathname.startsWith(`${base}/`)) {
    return `${request.pathname}${request.search}`
  }
  return `${base}${request.pathname.startsWith('/') ? request.pathname : `/${request.pathname}`}${request.search}`
}

export function proxyResponseHeaders(headers, basePath) {
  const base = normalizeProxyBasePath(basePath)
  if (!base || !headers || !Array.isArray(headers['set-cookie'])) return headers
  const upstreamCookiePath = `${base}/`
  const cookiePath = new RegExp(`;\\s*Path=${escapeRegExp(upstreamCookiePath)}`, 'i')
  return {
    ...headers,
    'set-cookie': headers['set-cookie'].map((cookie) => cookie.replace(cookiePath, '; Path=/')),
  }
}
