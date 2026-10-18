#!/usr/bin/env bash
set -euo pipefail

# Batch C: the entry shared secret is a deployment credential.  It is never
# committed; refuse to render an entry that would send an empty signature.
: "${SC_ENTRY_SHARED_SECRET:?SC_ENTRY_SHARED_SECRET must be injected per deployment}"
: "${SC_ENTRY_ROUTE_VERSION:?SC_ENTRY_ROUTE_VERSION must be injected per deployment}"

envsubst '$SC_PROXY_DEFAULT_UPSTREAM $SC_PROXY_PLATFORM_UPSTREAM $SC_ENTRY_ROUTE_VERSION $SC_ENTRY_SHARED_SECRET $SC_ENTRY_PLATFORM_STRIP' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

# Batch C: the runtime contract names namespaces, never a database.  The entry
# decides the namespace from the path; the frontend only consumes it.
printf 'window.__SC_RUNTIME_CONFIG__ = Object.freeze({"entryContract":"v2","routeVersion":"%s","namespaces":{"platform":"/platform-admin","tenant":"/t"}});\n' \
  "${SC_ENTRY_ROUTE_VERSION:-}" > /usr/share/nginx/html/runtime-config.js

exec /usr/sbin/nginx -g 'daemon off;'
