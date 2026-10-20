#!/usr/bin/env node
'use strict';

const http = require('http');

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:18081';
const ENTRY_NS = process.env.ENTRY_NS || 'demo';
const LOGIN = process.env.E2E_LOGIN || 'demo_pm';
const PASSWORD = process.env.E2E_PASSWORD || '123456';

function request(path, payload, token) {
  return new Promise((resolve, reject) => {
    const u = new URL(BASE_URL);
    const body = JSON.stringify(payload || {});
    const headers = {
      'Content-Type': 'application/json',
      'X-Anonymous-Intent': '1',
      'Content-Length': Buffer.byteLength(body),
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const req = http.request(
      {
        hostname: u.hostname,
        port: u.port || 80,
        path: `/t/${ENTRY_NS}${path}`,
        method: 'POST',
        headers,
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          let parsed = {};
          try {
            parsed = JSON.parse(data || '{}');
          } catch {
            parsed = { raw: data };
          }
          resolve({ status: res.statusCode || 0, body: parsed });
        });
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

function assert(cond, message) {
  if (!cond) {
    throw new Error(message);
  }
}

async function main() {
  const loginResp = await request('/api/v1/intent', {
    intent: 'login',
    params: { login: LOGIN, password: PASSWORD },
  });
  assert(loginResp.status === 200 && loginResp.body.ok === true, 'login failed');
  const token = (((loginResp.body || {}).data || {}).session || {}).token || '';
  assert(!!token, 'login response missing token');

  const initResp = await request(
    '/api/v1/intent',
    {
      intent: 'system.init',
      params: {
        scene: 'web',
        with_preload: false,
        scene_ready_mode: 'registry',
        with: ['workspace_home'],
      },
    },
    token
  );
  assert(initResp.status === 200 && initResp.body.ok === true, 'system.init failed');
  const data = (initResp.body && initResp.body.data) || {};
  assert(data.user && data.user.id, 'system.init missing user');
  assert(data.role_surface || data.role_surface_map, 'system.init missing role surface');
  assert(data.default_route, 'system.init missing default_route');
  assert(data.capabilities || data.capability_groups, 'system.init missing capabilities');
  assert(data.navigation, 'system.init missing navigation');

  const workResp = await request(
    '/api/v1/intent',
    { intent: 'my.work.summary', params: {} },
    token
  );
  assert(workResp.status === 200 && workResp.body.ok === true, 'my.work.summary failed');

  console.log(
    JSON.stringify(
      {
        role: LOGIN,
        login: 'ok',
        system_init: 'ok',
        contract: {
          has_role_surface: !!(data.role_surface || data.role_surface_map),
          has_default_route: !!data.default_route,
          has_capabilities: !!(data.capabilities || data.capability_groups),
          has_navigation: !!data.navigation,
        },
        my_work_summary: 'ok',
      },
      null,
      2
    )
  );
}

main().catch((err) => {
  console.error(`[demo_role_startup_smoke] FAIL(${LOGIN}): ${err.message}`);
  process.exit(1);
});
