#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SOURCE = path.join(ROOT, 'frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts');
const source = fs.readFileSync(SOURCE, 'utf8');

function assertContains(token, message) {
  if (!source.includes(token)) {
    throw new Error(message);
  }
}

assertContains('const viewOrchestrationHudSummary = computed(', 'missing view orchestration HUD summary');
assertContains('current.business_config_contracts', 'HUD must consume applied orchestration contracts');
assertContains("label: '页面编排已应用'", 'HUD must show whether orchestration applied');
assertContains("label: '页面编排配置数'", 'HUD must show applied orchestration contract count');
assertContains("label: '页面编排名称'", 'HUD must show applied orchestration contract names');
assertContains("label: '历史策略覆盖'", 'HUD must show historical field policy overlay state');

console.log('[contract_form_view_orchestration_hud_smoke] PASS');
