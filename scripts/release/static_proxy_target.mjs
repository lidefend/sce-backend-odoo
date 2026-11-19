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

export function upstreamRequestPath(rawUrl, basePath, entryPrefix = '') {
  const request = new URL(String(rawUrl || '/'), 'http://static-proxy.local')
  const base = normalizeProxyBasePath(basePath)
  const prefix = normalizeProxyBasePath(entryPrefix)
  if (prefix) {
    const parts = request.pathname.split('/').filter(Boolean)
    const prefixParts = prefix.split('/').filter(Boolean)
    const hasLocale = /^[a-z]{2}(?:_[A-Z]{2})?$/.test(parts[0] || '')
    const offset = hasLocale ? 1 : 0
    if (prefixParts.every((part, index) => parts[offset + index] === part)) {
      const upstreamPath = `/${parts.slice(offset + prefixParts.length).join('/')}`
      return `${upstreamPath}${request.search}`
    }
  }
  if (
    base
    && new RegExp(
      `^/(?:[a-z]{2}(?:_[A-Z]{2})?)?${escapeRegExp(base)}/(?:api|web)(/|$)`,
    ).test(request.pathname)
  ) {
    return `${request.pathname}${request.search}`
  }
  if (!base || request.pathname === base || request.pathname.startsWith(`${base}/`)) {
    return `${request.pathname}${request.search}`
  }
  return `${base}${request.pathname.startsWith('/') ? request.pathname : `/${request.pathname}`}${request.search}`
}

export function isBackendRequestPath(rawPath) {
  const requestPath = String(rawPath || '').split('?')[0]
  return (
    requestPath.startsWith('/api/')
    || requestPath === '/web'
    || requestPath.startsWith('/web/')
    || /^\/(?:[a-z]{2}(?:_[A-Z]{2})?\/)?(?:t\/[^/]+\/)?(?:api|web)(\/|$)/.test(requestPath)
  )
}

export function proxyResponseHeaders(headers, basePath, upstreamOrigin = '') {
  let next = headers
  const base = normalizeProxyBasePath(basePath)
  if (headers && Array.isArray(headers['set-cookie']) && base) {
    const upstreamCookiePath = `${base}/`
    const cookiePath = new RegExp(`;\\s*Path=${escapeRegExp(upstreamCookiePath)}`, 'i')
    next = {
      ...headers,
      'set-cookie': headers['set-cookie'].map((cookie) => cookie.replace(cookiePath, '; Path=/')),
    }
  }
  const location = String(next?.location || '').trim()
  if (location && upstreamOrigin) {
    try {
      const resolved = new URL(location, upstreamOrigin)
      if (resolved.origin === upstreamOrigin) {
        next = {
          ...next,
          location: `${resolved.pathname}${resolved.search}${resolved.hash}`,
        }
      }
    } catch {
      // Preserve an upstream location that is not a valid URL instead of
      // inventing a local redirect target.
    }
  }
  return next
}
